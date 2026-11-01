import os
import subprocess
from pathlib import Path
from typing import Dict, Any

import config
from services.animation_engine import iter_project_video_frames


def render_project_mp4(project_data: Dict[str, Any], story_plan: Dict[str, Any]) -> str:
    """
    Aşama 8 Ana Fonksiyonu:
    - 2D animasyon karelerini (Generator) bellek doldurmadan FFmpeg'e borular (pipe).
    - Master ses dosyası ile senkronize eder.
    - iPhone Safari uyumlu yuv420p, H.264, AAC MP4 çıktısını üretir.
    """
    project_id = project_data["project_id"]
    fps = int(story_plan.get("fps", config.VIDEO_FPS))
    width = config.VIDEO_WIDTH
    height = config.VIDEO_HEIGHT

    master_audio_path = story_plan.get("master_audio_path")
    output_mp4_path = config.EXPORTS_DIR / f"{project_id}.mp4"

    if output_mp4_path.exists():
        output_mp4_path.unlink()

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
    ]

    if master_audio_path and Path(master_audio_path).exists():
        ffmpeg_cmd.extend(["-i", str(master_audio_path)])

    ffmpeg_cmd.extend([
        "-c:v", config.VIDEO_CODEC,
        "-pix_fmt", config.PIXEL_FORMAT,
        "-profile:v", "high",
        "-level", "4.0",
        "-b:v", "3200k",
        "-preset", "medium",
        "-movflags", "+faststart",
    ])

    if master_audio_path and Path(master_audio_path).exists():
        ffmpeg_cmd.extend(["-c:a", config.AUDIO_CODEC, "-b:a", "192k"])

    ffmpeg_cmd.append(str(output_mp4_path))

    print(f"[VideoRenderer] FFmpeg render başlatılıyor: {output_mp4_path}")

    process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        frame_generator = iter_project_video_frames(story_plan)
        for current_idx, total_frames, frame_img in frame_generator:
            raw_bytes = frame_img.tobytes()
            process.stdin.write(raw_bytes)

            if current_idx % 30 == 0:
                pct = int((current_idx / float(total_frames)) * 100)
                print(f"[VideoRenderer] Render ilerleme: %{pct} ({current_idx}/{total_frames} kare)")

        process.stdin.close()
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="ignore")[-800:]
            raise RuntimeError(f"FFmpeg render hatası (kod {process.returncode}): {err_msg}")

    except Exception as exc:
        if process.poll() is None:
            process.kill()
        raise RuntimeError(f"Video render işleminde hata: {exc}")

    if not output_mp4_path.exists() or output_mp4_path.stat().st_size < 1000:
        raise RuntimeError("Video dosyası oluşturulamadı veya boş.")

    print(f"[VideoRenderer] Render başarıyla tamamlandı: {output_mp4_path}")
    return f"/exports/{project_id}.mp4"
```eof
