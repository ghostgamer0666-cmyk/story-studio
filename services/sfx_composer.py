import os
import wave
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np

import config

MASTER_SR = 44100


def convert_to_hq_mono_wav(input_path: str, output_wav_path: str, sample_rate: int = MASTER_SR) -> bool:
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
        print(f"[SFXComposer] FFmpeg HQ WAV dönüştürme hatası: {exc}")
        return False


def load_wav_float32(wav_path: str) -> np.ndarray:
    if not Path(wav_path).exists():
        return np.zeros(0, dtype=np.float32)
    with wave.open(str(wav_path), "rb") as wf:
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return samples


def save_stereo_wav_int16(output_path: str, left_channel: np.ndarray, right_channel: np.ndarray, sample_rate: int = MASTER_SR):
    length = min(len(left_channel), len(right_channel))
    stereo = np.empty(length * 2, dtype=np.int16)

    l_clipped = np.clip(left_channel[:length], -0.98, 0.98)
    r_clipped = np.clip(right_channel[:length], -0.98, 0.98)

    stereo[0::2] = (l_clipped * 32767.0).astype(np.int16)
    stereo[1::2] = (r_clipped * 32767.0).astype(np.int16)

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo.tobytes())


def generate_ambient_drone_bed(duration_sec: float, genre: str, sr: int = MASTER_SR) -> Tuple[np.ndarray, np.ndarray]:
    total_samples = max(1, int(duration_sec * sr))
    t = np.linspace(0.0, duration_sec, total_samples, endpoint=False, dtype=np.float32)

    genre_freqs = {
        "horror": (55.0, 82.41, 116.54),
        "zombie": (49.0, 73.42, 98.0),
        "survival": (65.41, 98.0, 130.81),
        "mystery": (61.74, 92.50, 110.0),
        "scifi": (58.27, 87.31, 116.54),
        "adventure": (73.42, 110.0, 146.83),
    }
    f1, f2, f3 = genre_freqs.get(genre, genre_freqs["horror"])

    slow_lfo = 0.5 + 0.5 * np.sin(2.0 * np.pi * 0.14 * t)
    slow_lfo2 = 0.5 + 0.5 * np.cos(2.0 * np.pi * 0.09 * t)

    left = (
        0.45 * np.sin(2.0 * np.pi * f1 * t)
        + 0.30 * np.sin(2.0 * np.pi * f2 * t) * slow_lfo
        + 0.20 * np.sin(2.0 * np.pi * (f3 + 0.4) * t) * slow_lfo2
    )
    right = (
        0.45 * np.sin(2.0 * np.pi * f1 * t)
        + 0.30 * np.sin(2.0 * np.pi * (f2 + 0.3) * t) * slow_lfo2
        + 0.20 * np.sin(2.0 * np.pi * f3 * t) * slow_lfo
    )

    rng = np.random.default_rng(42)
    noise = rng.normal(0.0, 0.04, total_samples).astype(np.float32)
    kernel = np.ones(64, dtype=np.float32) / 64.0
    smooth_noise = np.convolve(noise, kernel, mode="same")

    left = (left + smooth_noise) * 0.16
    right = (right + smooth_noise) * 0.16

    return left.astype(np.float32), right.astype(np.float32)


def synthesize_sfx_clip(sfx_type: str, duration_sec: float, sr: int = MASTER_SR) -> np.ndarray:
    dur = max(0.3, min(4.0, float(duration_sec)))
    n = int(dur * sr)
    t = np.linspace(0.0, dur, n, endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(abs(hash(sfx_type)) % 10000)

    if sfx_type == "door_creak":
        mod = np.sin(2.0 * np.pi * 3.2 * t) * 45.0
        freq = np.linspace(240.0, 145.0, n, dtype=np.float32) + mod
        phase = np.cumsum(freq / sr) * 2.0 * np.pi
        wave_sig = np.sin(phase) + 0.4 * np.sin(phase * 2.1)
        env = np.sin(np.linspace(0.0, np.pi, n, dtype=np.float32)) ** 0.7
        return (wave_sig * env * 0.35).astype(np.float32)

    if sfx_type in ("footsteps_walk", "footsteps_run"):
        step_interval = 0.48 if sfx_type == "footsteps_walk" else 0.27
        out = np.zeros(n, dtype=np.float32)
        step_samples = int(step_interval * sr)
        hit_len = min(int(0.09 * sr), step_samples)
        ht = np.linspace(0.0, hit_len / sr, hit_len, endpoint=False, dtype=np.float32)
        thud = np.sin(2.0 * np.pi * 95.0 * np.exp(-ht * 22.0) * ht)
        crunch = rng.normal(0.0, 0.4, hit_len).astype(np.float32) * np.exp(-ht * 35.0)
        step_wave = (thud * 0.7 + crunch * 0.5) * np.exp(-ht * 18.0)

        for start_idx in range(0, n - hit_len, step_samples):
            out[start_idx : start_idx + hit_len] += step_wave
        return (out * 0.55).astype(np.float32)

    if sfx_type == "phone_ring":
        tone1 = np.sin(2.0 * np.pi * 880.0 * t) + 0.5 * np.sin(2.0 * np.pi * 1320.0 * t)
        gate = ((np.sin(2.0 * np.pi * 6.0 * t) > 0).astype(np.float32))
        env = np.exp(-t * 1.2)
        return (tone1 * gate * env * 0.30).astype(np.float32)

    if sfx_type == "heartbeat":
        out = np.zeros(n, dtype=np.float32)
        beat_period = int(0.85 * sr)
        pulse_len = int(0.14 * sr)
        pt = np.linspace(0.0, pulse_len / sr, pulse_len, endpoint=False, dtype=np.float32)
        lub = np.sin(2.0 * np.pi * 52.0 * pt) * np.exp(-pt * 20.0)
        dub = np.sin(2.0 * np.pi * 44.0 * pt) * np.exp(-pt * 24.0) * 0.75

        for idx in range(0, n - pulse_len, beat_period):
            out[idx : idx + pulse_len] += lub
            dub_idx = idx + int(0.22 * sr)
            if dub_idx + pulse_len < n:
                out[dub_idx : dub_idx + pulse_len] += dub
        return (out * 0.65).astype(np.float32)

    if sfx_type == "monster_growl":
        base_f = np.linspace(85.0, 58.0, n, dtype=np.float32) + np.sin(2.0 * np.pi * 18.0 * t) * 8.0
        phase = np.cumsum(base_f / sr) * 2.0 * np.pi
        growl = np.sin(phase) + 0.6 * np.sin(phase * 1.5) + 0.3 * rng.normal(0.0, 0.3, n).astype(np.float32)
        env = np.sin(np.linspace(0.0, np.pi, n, dtype=np.float32))
        return (growl * env * 0.42).astype(np.float32)

    if sfx_type == "glass_break":
        burst = rng.normal(0.0, 0.6, n).astype(np.float32) * np.exp(-t * 7.5)
        shards = (
            np.sin(2.0 * np.pi * 2400.0 * t)
            + np.sin(2.0 * np.pi * 3150.0 * t)
            + np.sin(2.0 * np.pi * 4100.0 * t)
        ) * np.exp(-t * 9.0)
        return ((burst + shards * 0.4) * 0.45).astype(np.float32)

    if sfx_type == "alarm_siren":
        siren_f = 620.0 + 240.0 * np.sin(2.0 * np.pi * 1.8 * t)
        phase = np.cumsum(siren_f / sr) * 2.0 * np.pi
        return (np.sin(phase) * 0.28).astype(np.float32)

    rumble = rng.normal(0.0, 0.5, n).astype(np.float32)
    kernel = np.ones(48, dtype=np.float32) / 48.0
    filtered = np.convolve(rumble, kernel, mode="same") * np.exp(-t * 1.1)
    return (filtered * 0.50).astype(np.float32)


def compose_project_master_audio(
    project_data: Dict[str, Any],
    analysis_result: Dict[str, Any],
    story_plan: Dict[str, Any],
) -> Dict[str, Any]:
    project_id = project_data["project_id"]
    genre = project_data.get("genre", "horror")
    work_dir = config.UPLOADS_DIR / project_id
    work_dir.mkdir(parents=True, exist_ok=True)

    total_video_dur = float(story_plan.get("total_video_duration_sec", 10.0))
    total_samples = max(MASTER_SR, int(math.ceil(total_video_dur * MASTER_SR)))

    voice_track = np.zeros(total_samples, dtype=np.float32)
    speech_envelope = np.zeros(total_samples, dtype=np.float32)

    narrator_src = project_data["narrator_audio_path"]
    narrator_hq_wav = work_dir / "narrator_44k.wav"
    convert_to_hq_mono_wav(narrator_src, str(narrator_hq_wav), MASTER_SR)
    narr_samples = load_wav_float32(str(narrator_hq_wav))

    char_hq_map: Dict[str, np.ndarray] = {}
    for ch in analysis_result.get("characters", []):
        slot_id = ch["slot_id"]
        ch_src = ch["file_path"]
        ch_hq_wav = work_dir / f"{slot_id}_44k.wav"
        if convert_to_hq_mono_wav(ch_src, str(ch_hq_wav), MASTER_SR):
            char_hq_map[slot_id] = load_wav_float32(str(ch_hq_wav))

    master_timeline = analysis_result.get("master_timeline", [])

    for item in master_timeline:
        item_type = item.get("type", "narrator")
        tl_start = float(item.get("timeline_start_sec", 0.0))
        tl_end = float(item.get("timeline_end_sec", tl_start + 1.0))
        dst_start = max(0, int(tl_start * MASTER_SR))
        dst_end = min(total_samples, int(tl_end * MASTER_SR))
        target_len = max(0, dst_end - dst_start)
        if target_len <= 0:
            continue

        if item_type == "narrator":
            src_s = max(0, int(float(item.get("source_start_sec", 0.0)) * MASTER_SR))
            src_e = min(len(narr_samples), int(float(item.get("source_end_sec", 0.0)) * MASTER_SR))
            clip = narr_samples[src_s:src_e]
        else:
            slot_id = item.get("item_id", "")
            clip = char_hq_map.get(slot_id, np.zeros(0, dtype=np.float32))

        copy_len = min(target_len, len(clip))
        if copy_len > 0:
            voice_track[dst_start : dst_start + copy_len] += clip[:copy_len]
            speech_envelope[dst_start : dst_start + copy_len] = 1.0

    peak_voice = float(np.max(np.abs(voice_track))) if len(voice_track) > 0 else 0.0
    if peak_voice > 1e-4:
        voice_track = (voice_track / peak_voice) * 0.88

    sfx_left = np.zeros(total_samples, dtype=np.float32)
    sfx_right = np.zeros(total_samples, dtype=np.float32)
    total_sfx_events = 0

    for sc in story_plan.get("scenes", []):
        for trig in sc.get("sfx_triggers", []):
            sfx_type = trig.get("sfx_type", "heartbeat")
            trig_sec = float(trig.get("trigger_sec", sc.get("start_sec", 0.0)))
            dur_sec = float(trig.get("duration_sec", 1.5))
            vol = float(trig.get("volume", 0.5))

            sfx_clip = synthesize_sfx_clip(sfx_type, dur_sec, MASTER_SR) * vol
            s_idx = max(0, int(trig_sec * MASTER_SR))
            e_idx = min(total_samples, s_idx + len(sfx_clip))
            c_len = max(0, e_idx - s_idx)

            if c_len > 0:
                sfx_left[s_idx:e_idx] += sfx_clip[:c_len] * 0.95
                sfx_right[s_idx:e_idx] += sfx_clip[:c_len] * 1.05
                total_sfx_events += 1

    audio_end_sec = float(story_plan.get("audio_duration_sec", total_video_dur - 3.5))
    outro_idx = max(0, min(total_samples - 1, int(audio_end_sec * MASTER_SR)))
    outro_whoosh = synthesize_sfx_clip("heartbeat", 3.0, MASTER_SR) * 0.55
    ow_len = min(len(outro_whoosh), total_samples - outro_idx)
    if ow_len > 0:
        sfx_left[outro_idx : outro_idx + ow_len] += outro_whoosh[:ow_len]
        sfx_right[outro_idx : outro_idx + ow_len] += outro_whoosh[:ow_len]

    bg_left, bg_right = generate_ambient_drone_bed(total_video_dur, genre, MASTER_SR)

    duck_Window = int(0.25 * MASTER_SR)
    if duck_Window > 1:
        smooth_speech = np.convolve(
            speech_envelope,
            np.ones(duck_Window, dtype=np.float32) / float(duck_Window),
            mode="same",
        )
    else:
        smooth_speech = speech_envelope

    duck_gain = 1.0 - 0.68 * np.clip(smooth_speech, 0.0, 1.0)
    sfx_duck_gain = 1.0 - 0.40 * np.clip(smooth_speech, 0.0, 1.0)

    final_left = voice_track + (bg_left * duck_gain) + (sfx_left * sfx_duck_gain)
    final_right = voice_track + (bg_right * duck_gain) + (sfx_right * sfx_duck_gain)

    max_amp = max(float(np.max(np.abs(final_left))), float(np.max(np.abs(final_right))), 1e-4)
    if max_amp > 0.96:
        scale_factor = 0.95 / max_amp
        final_left *= scale_factor
        final_right *= scale_factor

    master_filename = f"{project_id}_master_audio.wav"
    master_out_path = config.EXPORTS_DIR / master_filename
    save_stereo_wav_int16(str(master_out_path), final_left, final_right, MASTER_SR)

    master_url = f"/exports/{master_filename}"
    story_plan["master_audio_path"] = str(master_out_path)
    story_plan["master_audio_url"] = master_url
    story_plan["total_sfx_events"] = total_sfx_events

    plan_file = config.CACHE_DIR / f"{project_id}_scene_plan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        import json
        json.dump(story_plan, f, ensure_ascii=False, indent=2)

    return story_plan
```eof
