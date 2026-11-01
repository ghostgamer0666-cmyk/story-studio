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
            print(f"[AudioAnalyzer] Whisper modeli yüklenemedi: {exc}")
            return None
    return _WHISPER_INSTANCE

def convert_to_standard_wav(input_path: str, output_wav_path: str, sample_rate: int = 16000) -> bool:
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
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        duration = n_frames / float(sr) if sr > 0 else 0.0
        raw_bytes = wf.readframes(n_frames)
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return samples, sr, round(duration, 3)

def compute_30fps_lipsync_envelope(samples: np.ndarray, sample_rate: int, fps: int = 30) -> List[int]:
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
            print(f"[AudioAnalyzer] STT hatası: {exc}")

    return detect_acoustic_segments_fallback(samples, sample_rate, duration)

def infer_character_identity_and_placement(
    char_item: Dict[str, Any],
    char_index: int,
    total_chars: int,
    narrator_segments: List[Dict[str, Any]],
) -> Tuple[str, str, int, float, str]:
    raw_name = (char_item.get("character_name") or "").strip()
    orig_file = Path(char_item.get("original_filename") or "").stem.lower()
    role_type = (char_item.get
