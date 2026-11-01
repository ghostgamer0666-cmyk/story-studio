import json
import math
import textwrap
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Generator

from PIL import Image, ImageDraw, ImageFont

import config
from services.character_system import (
    generate_location_background,
    draw_character_rig,
)

_FONT_CACHE: Dict[int, ImageFont.FreeTypeFont] = {}


def get_ui_font(size: int = 32) -> ImageFont.ImageFont:
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]

    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for fp in font_candidates:
        if Path(fp).exists():
            try:
                f = ImageFont.truetype(fp, size=size)
                _FONT_CACHE[size] = f
                return f
            except Exception:
                pass

    default_font = ImageFont.load_default()
    _FONT_CACHE[size] = default_font
    return default_font


def compute_character_stage_transform(
    char_scene_data: Dict[str, Any],
    local_frame: int,
    total_scene_frames: int,
) -> Tuple[int, int, float, int]:
    pos_name = char_scene_data.get("position", "center")
    action = char_scene_data.get("action", "idle")
    progress = min(1.0, max(0.0, local_frame / float(max(1, total_scene_frames))))

    base_positions = {
        "center": (540, 1560, 1.05, 1),
        "center_left": (370, 1560, 1.05, 1),
        "center_right": (710, 1560, 1.05, -1),
        "left": (260, 1580, 0.98, 1),
        "right_back": (820, 1470, 0.86, -1),
    }
    base_x, base_y, base_scale, facing = base_positions.get(pos_name, (540, 1560, 1.05, 1))

    if action == "walk":
        travel_px = int((progress - 0.5) * 220 * facing)
        base_x += travel_px
    elif action == "run":
        travel_px = int((progress - 0.5) * 360 * facing)
        base_x += travel_px
    elif action == "open_door":
        base_x = int(base_x + (540 - base_x) * min(1.0, progress * 1.3))
        base_scale = base_scale * (1.0 - 0.06 * progress)
    elif action == "hide":
        crouch = int(min(1.0, progress * 2.0) * 95)
        base_y += crouch

    return base_x, base_y, base_scale, facing


def get_mouth_level_for_frame(char_scene_data: Dict[str, Any], local_frame: int) -> int:
    if not char_scene_data.get("is_speaking", False):
        return 0

    curve = char_scene_data.get("lipsync_30fps") or []
    if not curve:
        return (local_frame // 3) % 4 + 1

    if 0 <= local_frame < len(curve):
        return int(curve[local_frame])
    return 0


def draw_interactive_props_layer(
    canvas: Image.Image,
    scene: Dict[str, Any],
    local_frame: int,
    total_scene_frames: int,
):
    draw = ImageDraw.Draw(canvas, "RGBA")
    props = scene.get("props", {})
    action = scene.get("primary_action", "idle")
    progress = min(1.0, max(0.0, local_frame / float(max(1, total_scene_frames))))

    if props.get("has_door") and action == "open_door":
        open_ratio = min(1.0, progress * 1.4)
        gap_w = int(open_ratio * 130)
        draw.rectangle([415, 565, 415 + gap_w, 1380], fill=(255, 220, 120, 95))

    if scene.get("primary_emotion") in ("scared", "shocked", "monster_rage"):
        pulse = int(35 + 25 * abs(math.sin(local_frame * 0.25)))
        draw.rectangle([0, 0, config.VIDEO_WIDTH, 110], fill=(180, 20, 20, pulse))
        draw.rectangle([0, config.VIDEO_HEIGHT - 110, config.VIDEO_WIDTH, config.VIDEO_HEIGHT], fill=(180, 20, 20, pulse))


def apply_camera_transform(
    frame_img: Image.Image,
    camera_motion: str,
    local_frame: int,
    total_scene_frames: int,
) -> Image.Image:
    w, h = frame_img.size
    progress = min(1.0, max(0.0, local_frame / float(max(1, total_scene_frames))))

    zoom = 1.0
    offset_x = 0.0
    offset_y = 0.0

    if camera_motion == "slow_zoom_in":
        zoom = 1.0 + 0.14 * progress
    elif camera_motion == "fast_zoom_face":
        zoom = 1.0 + 0.22 * min(1.0, progress * 2.4)
        offset_y = -95.0 * min(1.0, progress * 2.4)
    elif camera_motion == "pan_follow":
        zoom = 1.10
        offset_x = (progress - 0.5) * 90.0
    elif camera_motion == "camera_shake":
        zoom = 1.08
        decay = max(0.25, 1.0 - progress * 0.5)
        offset_x = math.sin(local_frame * 1.8) * 18.0 * decay
        offset_y = math.cos(local_frame * 2.3) * 14.0 * decay
    elif camera_motion == "wide_establish":
        zoom = 1.04 - 0.04 * progress

    if zoom <= 1.002 and abs(offset_x) < 1.0 and abs(offset_y) < 1.0:
        return frame_img

    crop_w = int(w / zoom)
    crop_h = int(h / zoom)

    cx = (w // 2) + int(offset_x)
    cy = (h // 2) + int(offset_y)

    left = max(0, min(w - crop_w, cx - crop_w // 2))
    top = max(0, min(h - crop_h, cy - crop_h // 2))
    right = left + crop_w
    bottom = top + crop_h

    cropped = frame_img.crop((left, top, right, bottom))
    return cropped.resize((w, h), Image.Resampling.BILINEAR)


def draw_hud_and_subtitles(
    canvas: Image.Image,
    scene: Dict[str, Any],
    local_frame: int,
):
    draw = ImageDraw.Draw(canvas, "RGBA")
    w, h = canvas.size

    hud = scene.get("hud_overlay")
    if hud:
        slide_progress = min(1.0, local_frame / 10.0)
        hud_y = int(-120 + 210 * slide_progress)

        hud_type = hud.get("type", "location_stamp")
        border_col = (99, 102, 241, 235)
        if hud_type == "danger_warning":
            border_col = (239, 68, 68, 240)
        elif hud_type == "phone_alert":
            border_col = (16, 185, 129, 240)

        draw.rounded_rectangle(
            [70, hud_y, w - 70, hud_y + 135],
            radius=22,
            fill=(15, 23, 42, 225),
            outline=border_col,
            width=4,
        )
        font_title = get_ui_font(30)
        font_sub = get_ui_font(24)
        draw.text((105, hud_y + 24), hud.get("title", ""), fill=(248, 250, 252, 255), font=font_title)
        draw.text((105, hud_y + 72), hud.get("subtitle", ""), fill=(148, 163, 184, 255), font=font_sub)

    text = (scene.get("text") or "").strip()
    if text:
        speaker = scene.get("speaker", "narrator")
        is_char = scene.get("type") == "character_dialogue"
        speaker_label = f"🗣️ {speaker}" if is_char else "🎙️ Anlatıcı"
        badge_col = (236, 72, 153, 235) if is_char else (99, 102, 241, 235)

        box_top = h - 360
        box_bottom = h - 110
        draw.rounded_rectangle(
            [56, box_top, w - 56, box_bottom],
            radius=26,
            fill=(9, 13, 22, 218),
            outline=(51, 65, 85, 220),
            width=3,
        )

        draw.rounded_rectangle(
            [84, box_top - 22, 340, box_top + 26],
            radius=12,
            fill=badge_col,
        )
        font_badge = get_ui_font(24)
        draw.text((102, box_top - 12), speaker_label, fill=(255, 255, 255, 255), font=font_badge)

        font_sub = get_ui_font(31)
        wrapped_lines = textwrap.wrap(text, width=38)[:4]
        line_y = box_top + 45
        for line in wrapped_lines:
            draw.text((88, line_y), line, fill=(248, 250, 252, 255), font=font_sub)
            line_y += 44


def render_scene_frame(
    scene: Dict[str, Any],
    rigs_by_id: Dict[str, Dict[str, Any]],
    local_frame: int,
    total_scene_frames: int,
) -> Image.Image:
    loc_id = scene.get("location", "dark_corridor")
    canvas = generate_location_background(loc_id, config.VIDEO_WIDTH, config.VIDEO_HEIGHT).copy()

    draw_interactive_props_layer(canvas, scene, local_frame, total_scene_frames)

    chars = scene.get("characters", [])
    props = scene.get("props", {})

    for ch in chars:
        cid = ch.get("character_id")
        rig = rigs_by_id.get(cid) or next(iter(rigs_by_id.values()))
        cx, fy, sc, facing = compute_character_stage_transform(ch, local_frame, total_scene_frames)
        mouth_level = get_mouth_level_for_frame(ch, local_frame)

        draw_character_rig(
            canvas=canvas,
            rig=rig,
            center_x=cx,
            feet_y=fy,
            scale=sc,
            action=ch.get("action", "idle"),
            emotion=ch.get("emotion", "neutral"),
            mouth_open_level=mouth_level,
            frame_idx=local_frame,
            facing=facing,
            has_flashlight=bool(props.get("has_flashlight")) and rig.get("role_type") == "main",
        )

    camera_motion = scene.get("camera_motion", "slow_zoom_in")
    transformed = apply_camera_transform(canvas, camera_motion, local_frame, total_scene_frames)
    draw_hud_and_subtitles(transformed, scene, local_frame)

    return transformed.convert("RGB")


def render_interactive_choice_outro_frame(
    story_plan: Dict[str, Any],
    outro_local_frame: int,
    outro_total_frames: int,
    last_bg_location: str = "dark_corridor",
) -> Image.Image:
    bg = generate_location_background(last_bg_location, config.VIDEO_WIDTH, config.VIDEO_HEIGHT).copy()
    draw = ImageDraw.Draw(bg, "RGBA")
    w, h = bg.size

    draw.rectangle([0, 0, w, h], fill=(6, 9, 18, 215))

    font_header = get_ui_font(42)
    font_sub = get_ui_font(28)
    font_opt = get_ui_font(30)
    font_hint = get_ui_font(22)

    draw.text((90, 260), "🔀 HİKÂYE NASIL DEVAM ETSİN?", fill=(248, 250, 252, 255), font=font_header)
    draw.text((90, 325), "Yorumlara A, B veya C yazın • En çok oy alan şık yeni bölüm olacak!", fill=(165, 180, 252, 255), font=font_sub)

    choices = story_plan.get("interactive_choices", [])
    start_y = 470

    for idx, ch in enumerate(choices[:3]):
        appear_frame = idx * 8
        if outro_local_frame < appear_frame:
            continue

        anim_prog = min(1.0, (outro_local_frame - appear_frame) / 10.0)
        card_y = start_y + idx * 310 + int((1.0 - anim_prog) * 50)

        draw.rounded_rectangle(
            [75, card_y, w - 75, card_y + 260],
            radius=28,
            fill=(19, 27, 46, 240),
            outline=(99, 102, 241, 255),
            width=4,
        )

        draw.rounded_rectangle(
            [110, card_y + 35, 190, card_y + 115],
            radius=18,
            fill=(99, 102, 241, 255),
        )
        draw.text((136, card_y + 52), ch.get("key", "A"), fill=(255, 255, 255, 255), font=font_header)

        wrapped_opt = textwrap.wrap(ch.get("text", ""), width=28)[:2]
        ty = card_y + 35
        for line in wrapped_opt:
            draw.text((220, ty), line, fill=(248, 250, 252, 255), font=font_opt)
            ty += 40

        hint_txt = ch.get("consequence_hint", "")
        if hint_txt:
            wrapped_hint = textwrap.wrap(f"💡 {hint_txt}", width=38)[:2]
            hy = card_y + 145
            for hline in wrapped_hint:
                draw.text((115, hy), hline, fill=(148, 163, 184, 255), font=font_hint)
                hy += 32

    rem_ratio = max(0.0, 1.0 - (outro_local_frame / float(max(1, outro_total_frames))))
    bar_w = int((w - 150) * rem_ratio)
    draw.rounded_rectangle([75, h - 180, w - 75, h - 150], radius=12, fill=(30, 41, 59, 255))
    if bar_w > 10:
        draw.rounded_rectangle([75, h - 180, 75 + bar_w, h - 150], radius=12, fill=(236, 72, 153, 255))

    return bg.convert("RGB")


def iter_project_video_frames(story_plan: Dict[str, Any]) -> Generator[Tuple[int, int, Image.Image], None, None]:
    fps = int(story_plan.get("fps", config.VIDEO_FPS))
    scenes = story_plan.get("scenes", [])
    rigs_by_id = story_plan.get("rigs_by_id", {})
    outro_sec = float(story_plan.get("choice_outro_duration_sec", 3.5))
    outro_frames = max(1, int(round(outro_sec * fps)))

    scene_frame_counts = []
    for sc in scenes:
        dur = max(0.4, float(sc.get("duration_sec", 2.0)))
        scene_frame_counts.append(max(1, int(round(dur * fps))))

    total_frames = sum(scene_frame_counts) + outro_frames
    global_frame_idx = 0
    last_location = "dark_corridor"

    for sc, sc_frames in zip(scenes, scene_frame_counts):
        last_location = sc.get("location", "dark_corridor")
        for local_f in range(sc_frames):
            frame_img = render_scene_frame(sc, rigs_by_id, local_f, sc_frames)
            global_frame_idx += 1
            yield global_frame_idx, total_frames, frame_img

    for outro_f in range(outro_frames):
        frame_img = render_interactive_choice_outro_frame(
            story_plan, outro_f, outro_frames, last_bg_location=last_location
        )
        global_frame_idx += 1
        yield global_frame_idx, total_frames, frame_img


def prepare_animation_timeline(project_data: Dict[str, Any], story_plan: Dict[str, Any]) -> Dict[str, Any]:
    project_id = project_data["project_id"]
    fps = int(story_plan.get("fps", config.VIDEO_FPS))
    scenes = story_plan.get("scenes", [])
    rigs_by_id = story_plan.get("rigs_by_id", {})

    preview_map: Dict[int, str] = {}
    total_scene_frames_sum = 0

    for sc in scenes:
        dur = max(0.4, float(sc.get("duration_sec", 2.0)))
        sc_frames = max(1, int(round(dur * fps)))
        total_scene_frames_sum += sc_frames

        mid_frame = sc_frames // 2
        animated_img = render_scene_frame(sc, rigs_by_id, mid_frame, sc_frames)

        filename = f"{project_id}_anim_scene_{sc['scene_id']}.png"
        out_path = config.EXPORTS_DIR / filename
        animated_img.save(out_path, format="PNG")
        url = f"/exports/{filename}"
        sc["preview_image_url"] = url
        preview_map[sc["scene_id"]] = url

    outro_frames = max(1, int(round(float(story_plan.get("choice_outro_duration_sec", 3.5)) * fps)))
    last_loc = scenes[-1].get("location", "dark_corridor") if scenes else "dark_corridor"
    outro_img = render_interactive_choice_outro_frame(story_plan, outro_frames // 2, outro_frames, last_loc)
    outro_filename = f"{project_id}_choice_outro.png"
    outro_img.save(config.EXPORTS_DIR / outro_filename, format="PNG")
    story_plan["choice_outro_preview_url"] = f"/exports/{outro_filename}"

    for sp in story_plan.get("scenes_preview", []):
        sid = sp.get("scene_id")
        if sid in preview_map:
            sp["preview_url"] = preview_map[sid]

    story_plan["first_scene_preview_url"] = preview_map.get(1, story_plan.get("first_scene_preview_url"))
    story_plan["total_frames"] = total_scene_frames_sum + outro_frames
    story_plan["animation_ready"] = True

    plan_file = config.CACHE_DIR / f"{project_id}_scene_plan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(story_plan, f, ensure_ascii=False, indent=2)

    return story_plan
```eof
