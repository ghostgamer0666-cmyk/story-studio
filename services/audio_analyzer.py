import os
import json
import math
import wave
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np

import config

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

_WHISPER_INSTANCE = None


def get_whisper_model():
    """Açık kaynaklı faster-whisper modelini CPU üzerinde (int8) tek seferlik yükler."""
    global _WHISPER_INSTANCE
    if not WHISPER_AVAILABLE:
        return None
    if _WHISPER_INSTANCE is None:
        try:
            model_size = os.environ.get("WHISPER_MODEL_SIZE", "base")
            _WHISPER_INSTANCE = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=2,
            )
        except Exception as exc:
            print(f"[AudioAnalyzer] Whisper modeli yüklenemedi, yerel akustik analiz kullanılacak: {exc}")
            return None
    return _WHISPER_INSTANCE


def convert_to_standard_wav(input_path: str, output_wav_path: str, sample_rate: int = 16000) -> bool:
    """
    Kullanıcının yüklediği MP3, M4A, WAV, AAC, OGG ses dosyasını
    orijinalini bozmadan analiz için 16kHz Mono 16-bit PCM WAV formatına dönüştürür.
    """
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            str(output_wav_path),
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return Path(output_wav_path).exists()
    except Exception as exc:
        print(f"[AudioAnalyzer] FFmpeg WAV dönüştürme hatası: {exc}")
        return False


def read_wav_samples(wav_path: str) -> Tuple[np.ndarray, int, float]:
    """WAV dosyasından normalize edilmiş (-1.0 .. 1.0) numpy dizisi, sample rate ve süreyi döner."""
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        duration = n_frames / float(sr) if sr > 0 else 0.0
        raw_bytes = wf.readframes(n_frames)
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return samples, sr, round(duration, 3)


def compute_30fps_lipsync_envelope(samples: np.ndarray, sample_rate: int, fps: int = 30) -> List[int]:
    """
    Saniyede 30 kare (30 FPS) için sesin anlık RMS şiddetini hesaplar.
    Her kare için 0..5 arasında ağız açıklık (viseme) seviyesi döner:
      0 = Tamamen kapalı (Sessiz)
      1 = Hafif aralık
      2 = Orta açık (Normal konuşma)
      3 = Geniş açık (A, E)
      4 = Yuvarlak (O, U)
      5 = Maksimum açık (Bağırma / Vurgu)
    """
    if len(samples) == 0 or sample_rate <= 0:
        return []

    total_duration = len(samples) / float(sample_rate)
    total_frames = max(1, int(math.ceil(total_duration * fps)))
    samples_per_frame = max(1, int(sample_rate / fps))

    rms_values = []
    for frame_idx in range(total_frames):
        start_i = frame_idx * samples_per_frame
        end_i = min(len(samples), start_i + samples_per_frame)
        chunk = samples[start_i:end_i]
        if len(chunk) == 0:
            rms_values.append(0.0)
        else:
            rms = float(np.sqrt(np.mean(chunk * chunk)))
            rms_values.append(rms)

    peak_rms = max(rms_values) if rms_values else 0.0
    if peak_rms < 1e-4:
        return [0] * total_frames

    mouth_timeline = []
    noise_floor = max(0.012, peak_rms * 0.08)

    for rms in rms_values:
        if rms <= noise_floor:
            mouth_timeline.append(0)
        else:
            norm = min(1.0, (rms - noise_floor) / max(1e-4, (peak_rms * 0.85 - noise_floor)))
            if norm < 0.20:
                mouth_timeline.append(1)
            elif norm < 0.45:
                mouth_timeline.append(2)
            elif norm < 0.70:
                mouth_timeline.append(3)
            elif norm < 0.88:
                mouth_timeline.append(4)
            else:
                mouth_timeline.append(5)

    return mouth_timeline


def detect_acoustic_segments_fallback(samples: np.ndarray, sample_rate: int, duration: float) -> List[Dict[str, Any]]:
    """
    Whisper modeli çalışmadığında devreye giren akustik sessizlik ve enerji tabanlı cümle zamanlama motoru.
    """
    if duration <= 0.1 or len(samples) == 0:
        return [{"segment_id": 1, "start_sec": 0.0, "end_sec": max(1.0, duration), "text": "Anlatım bölümü 1"}]

    window_sec = 0.1
    win_len = max(1, int(sample_rate * window_sec))
    num_wins = max(1, len(samples) // win_len)

    energies = []
    for i in range(num_wins):
        seg = samples[i * win_len : (i + 1) * win_len]
        energies.append(float(np.sqrt(np.mean(seg * seg))))

    max_e = max(energies) if energies else 0.0
    threshold = max(0.01, max_e * 0.12)

    segments = []
    in_speech = False
    seg_start = 0.0
    silence_count = 0

    for i, e in enumerate(energies):
        t = round(i * window_sec, 2)
        if e >= threshold:
            if not in_speech:
                in_speech = True
                seg_start = max(0.0, t - 0.1)
            silence_count = 0
        else:
            if in_speech:
                silence_count += 1
                if silence_count >= 4 or (t - seg_start) >= 6.0:
                    seg_end = round(t, 2)
                    if seg_end - seg_start >= 0.8:
                        segments.append({
                            "segment_id": len(segments) + 1,
                            "start_sec": seg_start,
                            "end_sec": seg_end,
                            "text": f"Hikâye anlatım kesiti {len(segments) + 1}",
                        })
                    in_speech = False
                    silence_count = 0

    if in_speech and (duration - seg_start) >= 0.5:
        segments.append({
            "segment_id": len(segments) + 1,
            "start_sec": round(seg_start, 2),
            "end_sec": round(duration, 2),
            "text": f"Hikâye anlatım kesiti {len(segments) + 1}",
        })

    if not segments:
        chunk_len = 4.5
        curr = 0.0
        idx = 1
        while curr < duration:
            nxt = min(duration, round(curr + chunk_len, 2))
            if nxt - curr >= 0.5 or idx == 1:
                segments.append({
                    "segment_id": idx,
                    "start_sec": round(curr, 2),
                    "end_sec": round(nxt, 2),
                    "text": f"Hikâye anlatım kesiti {idx}",
                })
                idx += 1
            curr = nxt

    return segments


def transcribe_audio_with_timestamps(wav_path: str, samples: np.ndarray, sample_rate: int, duration: float) -> List[Dict[str, Any]]:
    """Ses dosyasını Türkçe metne ve cümle bazlı başlangıç/bitiş zaman damgalarına dönüştürür."""
    model = get_whisper_model()
    if model is not None:
        try:
            segments_gen, _ = model.transcribe(
                str(wav_path),
                language="tr",
                beam_size=2,
                word_timestamps=True,
                vad_filter=True,
            )
            extracted = []
            for seg in segments_gen:
                clean_text = (seg.text or "").strip()
                if not clean_text:
                    continue
                words_list = []
                if getattr(seg, "words", None):
                    for w in seg.words:
                        words_list.append({
                            "word": (w.word or "").strip(),
                            "start": round(float(w.start), 2),
                            "end": round(float(w.end), 2),
                        })
                extracted.append({
                    "segment_id": len(extracted) + 1,
                    "start_sec": round(float(seg.start), 2),
                    "end_sec": round(float(seg.end), 2),
                    "text": clean_text,
                    "words": words_list,
                })
            if extracted:
                return extracted
        except Exception as exc:
            print(f"[AudioAnalyzer] STT sırasında hata, akustik segmentasyona geçiliyor: {exc}")

    return detect_acoustic_segments_fallback(samples, sample_rate, duration)


def infer_character_identity_and_placement(
    char_item: Dict[str, Any],
    char_index: int,
    total_chars: int,
    narrator_segments: List[Dict[str, Any]],
) -> Tuple[str, str, int, float, str]:
    """
    Karakter ses dosyasının adını, kullanıcının girdiği ismi ve anlatıcı cümlelerini inceleyerek
    hangi karaktere ait olduğunu ve hangi anlatıcı cümlesinden sonra gireceğini belirler.
    """
    raw_name = (char_item.get("character_name") or "").strip()
    orig_file = Path(char_item.get("original_filename") or "").stem.lower()
    role_type = (char_item.get("role_type") or "supporting").strip()

    combined_hint = f"{raw_name.lower()} {orig_file}"

    confidence = 0.88
    if any(k in combined_hint for k in ["canavar", "zombi", "yaratik", "monster", "zombie", "hayalet", "ses"]):
        role_type = "monster"
        if not raw_name or raw_name.startswith("karakter_"):
            raw_name = "Canavar"
    elif any(k in combined_hint for k in ["ana", "main", "kahraman", "ali", "efe", "mert", "elena", "ben"]):
        role_type = "main"
        if not raw_name or raw_name.startswith("karakter_"):
            raw_name = "Ana Karakter"
    elif any(k in combined_hint for k in ["yan", "arkadas", "doktor", "polis", "asker", "komutan", "yabanci"]):
        role_type = "supporting"

    generic_patterns = ["karakter_", "audio", "recording", "ses", "voice", "track", "kayıt", "kayit", "yeni"]
    is_generic = any(raw_name.lower().startswith(p) for p in generic_patterns) or len(raw_name) < 2

    if is_generic:
        confidence = 0.60

    if not narrator_segments:
        return (raw_name or f"Karakter {char_index + 1}", role_type, 1, confidence, "Hikâye başlangıcı")

    speech_verbs = ["dedi", "söyledi", "bağırdı", "fısıldadı", "sordu", "cevap", "seslendi", "inledi", "hırladı", "konuştu"]
    matched_seg_id = None

    for seg in narrator_segments:
        txt_lower = seg["text"].lower()
        if raw_name and len(raw_name) >= 3 and not is_generic and raw_name.lower() in txt_lower:
            matched_seg_id = seg["segment_id"]
            confidence = max(confidence, 0.94)
            break
        if any(v in txt_lower for v in speech_verbs):
            matched_seg_id = seg["segment_id"]
            break

    if matched_seg_id is None:
        n_segs = len(narrator_segments)
        target_pos = min(n_segs - 1, int(((char_index + 1) / float(total_chars + 1)) * n_segs))
        matched_seg_id = narrator_segments[target_pos]["segment_id"]

    matched_text = narrator_segments[min(len(narrator_segments) - 1, matched_seg_id - 1)]["text"]
    return (raw_name or f"Karakter {char_index + 1}", role_type, matched_seg_id, round(confidence, 2), matched_text)


def build_master_audio_timeline(
    narrator_segments: List[Dict[str, Any]],
    narrator_duration: float,
    analyzed_characters: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Anlatıcı segmentleri ile kullanıcının yüklediği karakter seslerini
    hiçbir sesi kesmeden tek bir birleşik zaman çizelgesine (Master Timeline) yerleştirir.
    """
    timeline: List[Dict[str, Any]] = []
    current_time = 0.0

    chars_by_seg: Dict[int, List[Dict[str, Any]]] = {}
    for ch in analyzed_characters:
        after_id = int(ch.get("matched_after_segment_id") or 1)
        chars_by_seg.setdefault(after_id, []).append(ch)

    for seg in narrator_segments:
        seg_id = seg["segment_id"]
        orig_start = float(seg["start_sec"])
        orig_end = float(seg["end_sec"])
        seg_dur = max(0.5, round(orig_end - orig_start, 3))

        timeline.append({
            "item_id": f"narr_{seg_id}",
            "type": "narrator",
            "speaker": "narrator",
            "role_type": "narrator",
            "text": seg["text"],
            "source_start_sec": orig_start,
            "source_end_sec": orig_end,
            "timeline_start_sec": round(current_time, 3),
            "timeline_end_sec": round(current_time + seg_dur, 3),
            "duration_sec": seg_dur,
        })
        current_time += seg_dur

        if seg_id in chars_by_seg:
            for ch in chars_by_seg[seg_id]:
                ch_dur = max(0.4, float(ch.get("duration_sec") or 1.5))
                current_time += 0.15
                ch_start = round(current_time, 3)
                ch_end = round(current_time + ch_dur, 3)

                ch["timeline_start_sec"] = ch_start
                ch["timeline_end_sec"] = ch_end

                timeline.append({
                    "item_id": ch["slot_id"],
                    "type": "character_dialogue",
                    "speaker": ch["character_name"],
                    "role_type": ch["role_type"],
                    "text": ch.get("transcript") or f"[{ch['character_name']} konuşması]",
                    "source_start_sec": 0.0,
                    "source_end_sec": ch_dur,
                    "timeline_start_sec": ch_start,
                    "timeline_end_sec": ch_end,
                    "duration_sec": ch_dur,
                    "lipsync_30fps": ch.get("lipsync_30fps", []),
                    "file_path": ch.get("file_path"),
                    "wav_path": ch.get("wav_path"),
                })
                current_time = ch_end + 0.15

    total_timeline_duration = max(narrator_duration, round(current_time, 3))
    return timeline, total_timeline_duration


def analyze_project_audios(project_data: Dict[str, Any], force_confirm: bool = False) -> Dict[str, Any]:
    """
    Aşama 3 Ana Motoru:
    Anlatıcı ve karakter seslerini analiz eder, zaman damgalarını ve 30 FPS lip-sync verisini çıkarır.
    """
    project_id = project_data["project_id"]
    work_dir = config.UPLOADS_DIR / project_id
    work_dir.mkdir(parents=True, exist_ok=True)

    narrator_src = project_data["narrator_audio_path"]
    narrator_wav = work_dir / "narrator_16k.wav"

    if not convert_to_standard_wav(narrator_src, str(narrator_wav)):
        raise RuntimeError("Anlatıcı ses dosyası okunamadı veya FFmpeg ile işlenemedi.")

    narr_samples, narr_sr, narr_duration = read_wav_samples(str(narrator_wav))
    narrator_segments = transcribe_audio_with_timestamps(
        str(narrator_wav), narr_samples, narr_sr, narr_duration
    )

    raw_characters = project_data.get("characters", [])
    analyzed_characters = []
    ambiguous_matches = []

    for idx, ch_item in enumerate(raw_characters):
        slot_id = ch_item["slot_id"]
        ch_src = ch_item["file_path"]
        ch_wav = work_dir / f"{slot_id}_16k.wav"

        if not convert_to_standard_wav(ch_src, str(ch_wav)):
            raise RuntimeError(f"Karakter ses dosyası ({ch_item.get('original_filename')}) işlenemedi.")

        ch_samples, ch_sr, ch_duration = read_wav_samples(str(ch_wav))
        ch_segs = transcribe_audio_with_timestamps(str(ch_wav), ch_samples, ch_sr, ch_duration)
        ch_transcript = " ".join(s["text"] for s in ch_segs).strip()
        lipsync_curve = compute_30fps_lipsync_envelope(ch_samples, ch_sr, fps=config.VIDEO_FPS)

        char_name, role_type, after_seg_id, conf, matched_narr_text = infer_character_identity_and_placement(
            ch_item, idx, len(raw_characters), narrator_segments
        )

        if force_confirm or ch_item.get("user_confirmed"):
            conf = 1.0

        analyzed_ch = {
            "slot_id": slot_id,
            "character_name": char_name,
            "role_type": role_type,
            "original_filename": ch_item.get("original_filename", ""),
            "file_path": ch_src,
            "wav_path": str(ch_wav),
            "duration_sec": ch_duration,
            "transcript": ch_transcript or f"[{char_name} konuşması]",
            "confidence": conf,
            "matched_after_segment_id": after_seg_id,
            "lipsync_30fps": lipsync_curve,
            "user_confirmed": bool(force_confirm or ch_item.get("user_confirmed")),
        }
        analyzed_characters.append(analyzed_ch)

        if conf < 0.75 and not analyzed_ch["user_confirmed"]:
            ambiguous_matches.append({
                "slot_id": slot_id,
                "filename": ch_item.get("original_filename", slot_id),
                "detected_transcript": analyzed_ch["transcript"],
                "suggested_character_name": char_name,
                "suggested_role_type": role_type,
                "suggested_after_narrator_text": matched_narr_text,
                "confidence": conf,
            })

    master_timeline, total_duration = build_master_audio_timeline(
        narrator_segments, narr_duration, analyzed_characters
    )

    analysis_result = {
        "project_id": project_id,
        "narrator_wav_path": str(narrator_wav),
        "narrator_duration_sec": narr_duration,
        "narrator_segments": narrator_segments,
        "characters": analyzed_characters,
        "ambiguous_matches": ambiguous_matches,
        "master_timeline": master_timeline,
        "total_duration_sec": total_duration,
    }

    analysis_file = config.CACHE_DIR / f"{project_id}_analysis.json"
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    return analysis_result
