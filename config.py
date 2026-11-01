import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
CACHE_DIR = STORAGE_DIR / "cache"
EXPORTS_DIR = STORAGE_DIR / "exports"

for directory in [UPLOADS_DIR, CACHE_DIR, EXPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
PIXEL_FORMAT = "yuv420p"

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".mp4"}
MAX_UPLOAD_SIZE_MB = 100

STORY_GENRES = [
    {"id": "horror", "name": "Korku & Gerilim", "theme_color": "#ef4444"},
    {"id": "zombie", "name": "Zombi & Salgın", "theme_color": "#84cc16"},
    {"id": "survival", "name": "Hayatta Kalma", "theme_color": "#f97316"},
    {"id": "mystery", "name": "Gizem & Dedektif", "theme_color": "#8b5cf6"},
    {"id": "scifi", "name": "Bilim Kurgu", "theme_color": "#06b6d4"},
    {"id": "adventure", "name": "Macera & Aksiyon", "theme_color": "#eab308"},
]
```eof
