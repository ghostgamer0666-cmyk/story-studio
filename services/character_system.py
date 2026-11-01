import json
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFilter

import config

SKIN_TONES = [
    (245, 214, 190),
    (232, 192, 160),
    (210, 166, 132),
    (184, 135, 102),
]

HAIR_COLORS = [
    (28, 30, 38),
    (74, 48, 32),
    (138, 75, 38),
    (210, 170, 95),
    (95, 35, 45),
]

PANTS_COLORS = [
    (30, 41, 59),
    (45, 55, 72),
    (39, 39, 42),
    (54, 47, 40),
]


def hex_to_rgb(hex_str: str, default: Tuple[int, int, int] = (99, 102, 241)) -> Tuple[int, int, int]:
    if not hex_str:
        return default
    h = hex_str.lstrip("#")
    if len(h) == 6:
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except Exception:
            return default
    return default


def darken_rgb(rgb: Tuple[int, int, int], factor: float = 0.7) -> Tuple[int, int, int]:
    return (
        max(0, int(rgb[0] * factor)),
        max(0, int(rgb[1] * factor)),
        max(0, int(rgb[2] * factor)),
    )


def lighten_rgb(rgb: Tuple[int, int, int], factor: float = 1.25) -> Tuple[int, int, int]:
    return (
        min(255, int(rgb[0] * factor)),
        min(255, int(rgb[1] * factor)),
        min(255, int(rgb[2] * factor)),
    )


def get_character_registry_path() -> Path:
    return config.CACHE_DIR / "character_registry.json"


def load_character_registry() -> Dict[str, Any]:
    reg_path = get_character_registry_path()
    if reg_path.exists():
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_character_registry(registry: Dict[str, Any]):
    reg_path = get_character_registry_path()
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


def get_or_create_consistent_rig(char_info: Dict[str, Any], genre: str) -> Dict[str, Any]:
    registry = load_character_registry()
    name_key = (char_info.get("name") or "Karakter").strip().lower()
    role_type = char_info.get("role_type", "supporting")
    reg_id = f"{name_key}_{role_type}"

    if reg_id in registry:
        rig = registry[reg_id]
        rig["character_id"] = char_info.get("character_id", rig.get("character_id", reg_id))
        return rig

    digest = int(hashlib.md5(reg_id.encode("utf-8")).hexdigest()[:8], 16)

    if role_type == "monster":
        skin_rgb = (118, 148, 112) if genre == "zombie" else (92, 88, 115)
        hair_rgb = (25, 30, 25)
        outfit_rgb = (120, 28, 28)
        pants_rgb = (35, 30, 35)
        eye_rgb = (239, 68, 68)
        hair_style = "monster_spikes"
        accessory = "claws"
    else:
        skin_rgb = SKIN_TONES[digest % len(SKIN_TONES)]
        hair_rgb = HAIR_COLORS[(digest // 3) % len(HAIR_COLORS)]
        outfit_rgb = hex_to_rgb(char_info.get("outfit_color", "#3b82f6"))
        pants_rgb = PANTS_COLORS[(digest // 7) % len(PANTS_COLORS)]
        eye_rgb = (30, 41, 59)
        hair_style = char_info.get("hair_style") or ("short_dark" if digest % 2 == 0 else "medium_styled")
        accessory = char_info.get("accessory") or ("flashlight" if role_type == "main" else "jacket")

    rig_spec = {
        "registry_id": reg_id,
        "character_id": char_info.get("character_id", reg_id),
        "name": char_info.get("name", "Karakter"),
        "role_type": role_type,
        "skin_rgb": list(skin_rgb),
        "hair_rgb": list(hair_rgb),
        "outfit_rgb": list(outfit_rgb),
        "pants_rgb": list(pants_rgb),
        "shoe_rgb": [24, 24, 32],
        "eye_rgb": list(eye_rgb),
        "hair_style": hair_style,
        "accessory": accessory,
        "height_scale": 1.08 if role_type == "monster" else (1.0 if role_type == "main" else 0.96),
    }

    registry[reg_id] = rig_spec
    save_character_registry(registry)
    return rig_spec


def generate_location_background(location_id: str, width: int = 1080, height: int = 1920) -> Image.Image:
    cache_file = config.CACHE_DIR / f"bg_{location_id}_{width}x{height}.png"
    if cache_file.exists():
        try:
            return Image.open(cache_file).convert("RGBA")
        except Exception:
            pass

    img = Image.new("RGBA", (width, height), (10, 14, 24, 255))
    draw = ImageDraw.Draw(img)

    palettes = {
        "forest_night": ((7, 13, 28), (15, 32, 42), (12, 24, 20)),
        "abandoned_street": ((14, 17, 30), (30, 32, 48), (22, 24, 30)),
        "dark_corridor": ((16, 12, 24), (32, 24, 42), (24, 18, 28)),
        "bunker_room": ((18, 22, 20), (34, 42, 38), (25, 29, 27)),
        "sci_fi_lab": ((8, 20, 38), (16, 44, 72), (14, 28, 46)),
        "living_room": ((22, 18, 32), (44, 34, 56), (30, 22, 36)),
    }
    top_c, mid_c, floor_c = palettes.get(location_id, palettes["dark_corridor"])
    horizon_y = int(height * 0.72)

    for y in range(0, horizon_y, 4):
        ratio = y / float(max(1, horizon_y))
        r = int(top_c[0] + (mid_c[0] - top_c[0]) * ratio)
        g = int(top_c[1] + (mid_c[1] - top_c[1]) * ratio)
        b = int(top_c[2] + (mid_c[2] - top_c[2]) * ratio)
        draw.rectangle([0, y, width, y + 4], fill=(r, g, b, 255))

    draw.rectangle([0, horizon_y, width, height], fill=(*floor_c, 255))
    draw.line([(0, horizon_y), (width, horizon_y)], fill=(60, 75, 95, 180), width=4)

    if location_id == "forest_night":
        draw.ellipse([width - 280, 160, width - 110, 330], fill=(220, 235, 255, 210))
        for tx in [70, 230, 420, 660, 850, 990]:
            draw.rectangle([tx, 340, tx + 46, horizon_y + 20], fill=(9, 17, 22, 255))
    elif location_id == "abandoned_street":
        for bx, by, bw in [(30, 280, 340), (370, 420, 310), (710, 240, 340)]:
            draw.rectangle([bx, by, bx + bw, horizon_y], fill=(18, 22, 34, 255), outline=(40, 48, 68, 255), width=3)
    elif location_id in ("dark_corridor", "living_room", "bunker_room"):
        draw.rectangle([220, 360, width - 220, horizon_y], fill=(20, 16, 30, 255), outline=(58, 52, 78, 255), width=4)

    img.save(cache_file, format="PNG")
    return img


def draw_character_rig(
    canvas: Image.Image,
    rig: Dict[str, Any],
    center_x: int,
    feet_y: int,
    scale: float = 1.0,
    action: str = "idle",
    emotion: str = "neutral",
    mouth_open_level: int = 0,
    frame_idx: int = 0,
    facing: int = 1,
    has_flashlight: bool = False,
):
    draw = ImageDraw.Draw(canvas, "RGBA")
    s = scale * float(rig.get("height_scale", 1.0))

    skin = tuple(rig.get("skin_rgb", [240, 208, 184]))
    skin_dark = darken_rgb(skin, 0.82)
    hair = tuple(rig.get("hair_rgb", [30, 32, 40]))
    outfit = tuple(rig.get("outfit_rgb", [59, 130, 246]))
    outfit_dark = darken_rgb(outfit, 0.72)
    pants = tuple(rig.get("pants_rgb", [30, 41, 59]))
    shoes = tuple(rig.get("shoe_rgb", [20, 20, 28]))
    eye_col = tuple(rig.get("eye_rgb", [30, 41, 59]))

    phase = frame_idx * 0.28
    leg_swing = 0.0
    arm_swing = 0.0
    bob_y = int(math.sin(phase * 0.5) * 4 * s)

    if action == "walk":
        leg_swing = math.sin(phase) * 28 * s
        arm_swing = -math.sin(phase) * 24 * s
        bob_y = int(abs(math.cos(phase)) * 10 * s)
    elif action == "run":
        leg_swing = math.sin(phase * 1.6) * 48 * s
        arm_swing = -math.sin(phase * 1.6) * 42 * s
        bob_y = int(abs(math.cos(phase * 1.6)) * 16 * s)

    hip_y = feet_y - int(190 * s) + bob_y
    torso_top_y = hip_y - int(185 * s)
    head_center_y = torso_top_y - int(78 * s)

    # Gölge
    draw.ellipse([center_x - int(95 * s), feet_y - int(12 * s), center_x + int(95 * s), feet_y + int(12 * s)], fill=(0, 0, 0, 115))

    # Bacaklar
    left_foot_x = center_x - int(28 * s) + int(leg_swing)
    right_foot_x = center_x + int(28 * s) - int(leg_swing)
    draw.line([(center_x - int(22 * s), hip_y), (left_foot_x, feet_y - int(16 * s))], fill=darken_rgb(pants, 0.8), width=max(8, int(34 * s)))
    draw.line([(center_x + int(22 * s), hip_y), (right_foot_x, feet_y - int(16 * s))], fill=pants, width=max(8, int(34 * s)))

    # Gövde
    draw.rounded_rectangle([center_x - int(64 * s), torso_top_y, center_x + int(64 * s), hip_y + int(15 * s)], radius=int(24 * s), fill=outfit, outline=outfit_dark, width=3)

    # Kafa
    draw.ellipse([center_x - int(66 * s), head_center_y - int(72 * s), center_x + int(66 * s), head_center_y + int(72 * s)], fill=skin, outline=skin_dark, width=3)
    draw.chord([center_x - int(72 * s), head_center_y - int(84 * s), center_x + int(72 * s), head_center_y + int(10 * s)], start=180, end=360, fill=hair)

    # Gözler
    draw.ellipse([center_x - int(34 * s), head_center_y - int(20 * s), center_x - int(14 * s), head_center_y], fill=(250, 250, 252, 255))
    draw.ellipse([center_x + int(14 * s), head_center_y - int(20 * s), center_x + int(34 * s), head_center_y], fill=(250, 250, 252, 255))
    draw.ellipse([center_x - int(26 * s), head_center_y - int(16 * s), center_x - int(18 * s), head_center_y - int(8 * s)], fill=eye_col)
    draw.ellipse([center_x + int(18 * s), head_center_y - int(16 * s), center_x + int(26 * s), head_center_y - int(8 * s)], fill=eye_col)

    # Ağız / Lip-sync
    mouth_y = head_center_y + int(30 * s)
    level = max(0, min(5, int(mouth_open_level)))
    if level == 0:
        draw.line([(center_x - int(14 * s), mouth_y), (center_x + int(14 * s), mouth_y)], fill=(75, 40, 45, 255), width=3)
    else:
        mw = int((12 + level * 3) * s)
        mh = int((4 + level * 4) * s)
        draw.rounded_rectangle([center_x - mw, mouth_y - mh // 2, center_x + mw, mouth_y + mh], radius=6, fill=(110, 24, 36, 255))

    # Fener
    if has_flashlight:
        fl_x2 = center_x + int(110 * s * facing)
        draw.polygon([(center_x + int(78 * s), head_center_y + int(20 * s)), (fl_x2 + int(200 * s * facing), head_center_y - int(80 * s)), (fl_x2 + int(200 * s * facing), head_center_y + int(120 * s))], fill=(254, 240, 138, 48))


def render_character_avatar_card(rig: Dict[str, Any], project_id: str) -> str:
    card_w, card_h = 360, 480
    img = Image.new("RGBA", (card_w, card_h), (19, 27, 46, 255))
    draw_character_rig(canvas=img, rig=rig, center_x=card_w // 2, feet_y=card_h - 35, scale=0.72, action="idle", emotion="determined", mouth_open_level=2, frame_idx=0, facing=1, has_flashlight=(rig.get("accessory") == "flashlight"))
    filename = f"{project_id}_char_{rig['character_id']}.png"
    out_path = config.EXPORTS_DIR / filename
    img.convert("RGB").save(out_path, format="PNG")
    return f"/exports/{filename}"


def render_scene_keyframe_preview(scene: Dict[str, Any], rigs_by_id: Dict[str, Dict[str, Any]], project_id: str) -> str:
    loc_id = scene.get("location", "dark_corridor")
    bg_img = generate_location_background(loc_id, config.VIDEO_WIDTH, config.VIDEO_HEIGHT).copy()
    chars = scene.get("characters", [])
    props = scene.get("props", {})

    pos_map = {"center": (540, 1560), "center_left": (360, 1560), "center_right": (720, 1560), "left": (270, 1580), "right_back": (810, 1470)}

    for ch in chars:
        cid = ch.get("character_id")
        rig = rigs_by_id.get(cid) or next(iter(rigs_by_id.values()))
        pos_name = ch.get("position", "center")
        cx, fy = pos_map.get(pos_name, (540, 1560))
        draw_character_rig(canvas=bg_img, rig=rig, center_x=cx, feet_y=fy, scale=1.0, action=ch.get("action", "idle"), emotion=ch.get("emotion", "neutral"), mouth_open_level=3 if ch.get("is_speaking") else 0, frame_idx=5, facing=-1 if "right" in pos_name else 1, has_flashlight=bool(props.get("has_flashlight")))

    filename = f"{project_id}_scene_{scene['scene_id']}.png"
    out_path = config.EXPORTS_DIR / filename
    bg_img.convert("RGB").save(out_path, format="PNG")
    return f"/exports/{filename}"


def prepare_visual_assets(project_data: Dict[str, Any], story_plan: Dict[str, Any]) -> Dict[str, Any]:
    project_id = project_data["project_id"]
    genre = project_data.get("genre", "horror")
    cast_roster = story_plan.get("cast_roster", [])
    scenes = story_plan.get("scenes", [])

    rigs_by_id = {}
    character_cards = []

    for member in cast_roster:
        rig = get_or_create_consistent_rig(member, genre)
        cid = member["character_id"]
        rigs_by_id[cid] = rig
        avatar_url = render_character_avatar_card(rig, project_id)
        character_cards.append({
            "character_id": cid,
            "name": rig["name"],
            "role_type": rig["role_type"],
            "outfit_color": member.get("outfit_color", "#3b82f6"),
            "accessory": rig["accessory"],
            "avatar_url": avatar_url,
        })

    preview_map = {}
    for sc in scenes:
        sc_url = render_scene_keyframe_preview(sc, rigs_by_id, project_id)
        sc["preview_image_url"] = sc_url
        preview_map[sc["scene_id"]] = sc_url

    for sp in story_plan.get("scenes_preview", []):
        sid = sp.get("scene_id")
        if sid in preview_map:
            sp["preview_url"] = preview_map[sid]

    story_plan["rigs_by_id"] = rigs_by_id
    story_plan["character_cards"] = character_cards
    story_plan["first_scene_preview_url"] = preview_map.get(1)

    plan_file = config.CACHE_DIR / f"{project_id}_scene_plan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(story_plan, f, ensure_ascii=False, indent=2)

    return story_plan
```eof
