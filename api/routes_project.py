import os
import json
import uuid
import time
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

import config
from api.schemas import (
    ProjectStatusResponse,
    ConfirmCharacterMappingRequest,
)
from services.audio_analyzer import analyze_project_audios
from services.story_planner import generate_story_plan
from services.character_system import prepare_visual_assets
from services.animation_engine import prepare_animation_timeline
from services.sfx_composer import compose_project_master_audio
from services.video_renderer import render_project_mp4

router = APIRouter(prefix="/api", tags=["projects"])

PROJECTS_DB: dict = {}


def save_project_state(project_id: str):
    if project_id not in PROJECTS_DB:
        return
    state_file = config.CACHE_DIR / f"{project_id}_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(PROJECTS_DB[project_id], f, ensure_ascii=False, indent=2)


def load_project_state(project_id: str) -> Optional[dict]:
    if project_id in PROJECTS_DB:
        return PROJECTS_DB[project_id]
    state_file = config.CACHE_DIR / f"{project_id}_state.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            PROJECTS_DB[project_id] = data
            return data
    return None


def validate_audio_file(upload_file: UploadFile) -> str:
    if not upload_file.filename:
        raise HTTPException(status_code=400, detail="Dosya adı bulunamadı.")
    ext = Path(upload_file.filename).suffix.lower()
    if ext not in config.ALLOWED_AUDIO_EXTENSIONS:
        allowed_str = ", ".join(sorted(config.ALLOWED_AUDIO_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen ses formatı ({ext}). Desteklenenler: {allowed_str}",
        )
    return ext


def run_story_pipeline(project_id: str, force_confirm: bool = False):
    project = load_project_state(project_id)
    if not project:
        return

    try:
        project["status"] = "analyzing_audio"
        project["progress"] = 15
        project["step_index"] = 1
        project["current_step_label"] = "Anlatıcı ve karakter sesleri analiz ediliyor, zaman damgaları çıkarılıyor..."
        save_project_state(project_id)

        analysis = analyze_project_audios(project, force_confirm=force_confirm)

        narr_segs = analysis.get("narrator_segments", [])
        preview_txt = " ".join(s.get("text", "") for s in narr_segs[:3]).strip()
        project["narrator_transcript_preview"] = preview_txt or "Ses zaman damgaları çıkarıldı."
        project["characters"] = analysis.get("characters", [])
        project["duration_sec"] = analysis.get("total_duration_sec", 0.0)

        ambiguous = analysis.get("ambiguous_matches", [])
        if ambiguous and not force_confirm:
            project["ambiguous_matches"] = ambiguous
            project["status"] = "awaiting_confirmation"
            project["progress"] = 25
            project["step_index"] = 1
            project["current_step_label"] = "Karakter ses eşleştirmesi için onayınız bekleniyor..."
            save_project_state(project_id)
            return

        project["ambiguous_matches"] = []

        # AŞAMA 4: Hikâye ve Sahne Planlama
        project["status"] = "planning_story"
        project["progress"] = 35
        project["step_index"] = 1
        project["current_step_label"] = "Hikâye analiz ediliyor: Mekânlar, kamera açıları ve SFX planlanıyor..."
        save_project_state(project_id)

        story_plan = generate_story_plan(project, analysis)

        # AŞAMA 5: Karakter Tutarlılığı, 2D Rig ve Arka Plan Üretimi
        project["status"] = "building_characters"
        project["progress"] = 55
        project["step_index"] = 2
        project["current_step_label"] = "Tutarlı 2D karakter rigleri ve 1080x1920 sahne arka planları çiziliyor..."
        save_project_state(project_id)

        story_plan = prepare_visual_assets(project, story_plan)

        # AŞAMA 6: 2D Animasyon Motoru
        project["status"] = "animating"
        project["progress"] = 75
        project["step_index"] = 3
        project["current_step_label"] = "30 FPS 2D eklem animasyonu, lip-sync, kamera hareketleri ve HUD işleniyor..."
        save_project_state(project_id)

        story_plan = prepare_animation_timeline(project, story_plan)

        # AŞAMA 7: Otomatik Ses Sistemi
        project["status"] = "composing_audio"
        project["progress"] = 88
        project["step_index"] = 4
        project["current_step_label"] = "Orijinal sesler korunarak SFX ve atmosfer müziği miksleniyor (Audio Ducking)..."
        save_project_state(project_id)

        story_plan = compose_project_master_audio(project, analysis, story_plan)

        # AŞAMA 8: Video Render Sistemi (FFmpeg MP4)
        project["status"] = "rendering_video"
        project["progress"] = 94
        project["step_index"] = 5
        project["current_step_label"] = "1080x1920 30 FPS H.264 MP4 video render ediliyor..."
        save_project_state(project_id)

        video_url = render_project_mp4(project, story_plan)

        project["scene_count"] = len(story_plan.get("scenes", []))
        project["scenes_preview"] = story_plan.get("scenes_preview", [])
        project["character_cards"] = story_plan.get("character_cards", [])
        project["first_scene_preview_url"] = story_plan.get("first_scene_preview_url")
        project["master_audio_url"] = story_plan.get("master_audio_url")
        project["video_url"] = video_url
        project["interactive_choices"] = story_plan.get("interactive_choices", [])
        project["duration_sec"] = story_plan.get("total_video_duration_sec", project["duration_sec"])

        project["status"] = "completed"
        project["progress"] = 100
        project["step_index"] = 5
        project["current_step_label"] = "Tam Otomatik 2D Animasyon Videosu Hazır!"
        save_project_state(project_id)

    except Exception as exc:
        project["status"] = "failed"
        project["error_message"] = str(exc)
        project["current_step_label"] = f"Hata: {str(exc)}"
        save_project_state(project_id)


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "studio": "Full Auto Story Animation Studio",
        "stage": 8,
        "resolution": f"{config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}",
        "fps": config.VIDEO_FPS,
        "genres": config.STORY_GENRES,
    }


@router.post("/projects/create", response_model=ProjectStatusResponse)
async def create_project(
    background_tasks: BackgroundTasks,
    project_name: str = Form(...),
    genre: str = Form("horror"),
    previous_choice: Optional[str] = Form(None),
    character_metadata: str = Form("[]"),
    narrator_audio: UploadFile = File(...),
    character_audios: Optional[List[UploadFile]] = File(default=None),
):
    validate_audio_file(narrator_audio)

    project_id = uuid.uuid4().hex[:12]
    project_upload_dir = config.UPLOADS_DIR / project_id
    project_upload_dir.mkdir(parents=True, exist_ok=True)

    narrator_ext = Path(narrator_audio.filename).suffix.lower()
    narrator_safe_name = f"narrator_original{narrator_ext}"
    narrator_path = project_upload_dir / narrator_safe_name

    with open(narrator_path, "wb") as buffer:
        shutil.copyfileobj(narrator_audio.file, buffer)

    try:
        parsed_meta = json.loads(character_metadata)
        if not isinstance(parsed_meta, list):
            parsed_meta = []
    except Exception:
        parsed_meta = []

    saved_characters = []
    if character_audios:
        for idx, char_file in enumerate(character_audios):
            if not char_file or not char_file.filename:
                continue
            ext = validate_audio_file(char_file)
            meta = parsed_meta[idx] if idx < len(parsed_meta) else {}
            raw_char_name = meta.get("character_name", "").strip()
            if not raw_char_name:
                raw_char_name = Path(char_file.filename).stem

            role_type = meta.get("role_type", "supporting")
            slot_id = f"char_{idx + 1}"
            safe_filename = f"{slot_id}_{Path(char_file.filename).stem}{ext}"
            char_path = project_upload_dir / safe_filename

            with open(char_path, "wb") as buffer:
                shutil.copyfileobj(char_file.file, buffer)

            saved_characters.append(
                {
                    "slot_id": slot_id,
                    "character_name": raw_char_name,
                    "role_type": role_type,
                    "original_filename": char_file.filename,
                    "file_path": str(char_path),
                    "user_confirmed": False,
                }
            )

    project_data = {
        "project_id": project_id,
        "project_name": project_name.strip() or "İsimsiz Hikâye",
        "genre": genre,
        "previous_choice": previous_choice,
        "narrator_audio_path": str(narrator_path),
        "narrator_original_filename": narrator_audio.filename,
        "characters": saved_characters,
        "status": "queued",
        "progress": 5,
        "step_index": 1,
        "current_step_label": "Ses dosyaları sunucuya alındı, analiz başlatılıyor...",
        "error_message": None,
        "ambiguous_matches": [],
        "video_url": None,
        "master_audio_url": None,
        "first_scene_preview_url": None,
        "duration_sec": None,
        "interactive_choices": [],
        "scene_count": 0,
        "narrator_transcript_preview": None,
        "scenes_preview": [],
        "character_cards": [],
        "created_at": time.time(),
    }

    PROJECTS_DB[project_id] = project_data
    save_project_state(project_id)
    background_tasks.add_task(run_story_pipeline, project_id, False)

    return ProjectStatusResponse(**project_data)


@router.get("/projects/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(project_id: str):
    project = load_project_state(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")
    return ProjectStatusResponse(**project)


@router.post("/projects/{project_id}/confirm-characters", response_model=ProjectStatusResponse)
async def confirm_character_mappings(
    project_id: str,
    payload: ConfirmCharacterMappingRequest,
    background_tasks: BackgroundTasks,
):
    project = load_project_state(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    for char_item in project.get("characters", []):
        slot_id = char_item["slot_id"]
        if slot_id in payload.mappings:
            char_item["character_name"] = payload.mappings[slot_id].get(
                "character_name", char_item["character_name"]
            )
            char_item["role_type"] = payload.mappings[slot_id].get(
                "role_type", char_item["role_type"]
            )
        char_item["user_confirmed"] = True

    project["ambiguous_matches"] = []
    project["status"] = "analyzing_audio"
    project["current_step_label"] = "Karakter eşleştirmesi onaylandı, animasyon ve video üretiliyor..."
    save_project_state(project_id)

    background_tasks.add_task(run_story_pipeline, project_id, True)
    return ProjectStatusResponse(**project)


@router.get("/projects/{project_id}/download")
async def download_project_video(project_id: str):
    project = load_project_state(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı.")

    video_path = config.EXPORTS_DIR / f"{project_id}.mp4"
    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail="MP4 video dosyası henüz oluşturulmadı.",
        )

    safe_title = "".join(
        c if c.isalnum() or c in ("-", "_") else "_" for c in project["project_name"]
    )
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"{safe_title}_{project_id}.mp4",
    )
```eof
