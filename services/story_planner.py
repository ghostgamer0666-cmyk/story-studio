import json
from typing import Dict, Any, List, Optional

import config

LOCATION_KEYWORDS = {
    "forest_night": ["orman", "ağaç", "çalılık", "patika", "kamp", "dağ", "yaprak", "karanlık orman"],
    "abandoned_street": ["sokak", "cadde", "yol", "araba", "köşe", "lamba", "şehir", "bina", "dışarı"],
    "dark_corridor": ["koridor", "kapı", "merdiven", "kat", "apartman", "hastane", "okul", "bodrum", "tünel"],
    "bunker_room": ["sığınak", "depo", "mahzen", "kilitli", "demir kapı", "erzak", "telsiz", "barikat"],
    "sci_fi_lab": ["laboratuvar", "istasyon", "uzay", "ekran", "bilgisayar", "kapsül", "deney", "reaktör", "gemisi"],
    "living_room": ["ev", "oda", "salon", "pencere", "koltuk", "masa", "telefon", "yatak", "mutfak"],
}

GENRE_DEFAULT_LOCATIONS = {
    "horror": ["dark_corridor", "living_room", "forest_night"],
    "zombie": ["abandoned_street", "bunker_room", "dark_corridor"],
    "survival": ["forest_night", "bunker_room", "abandoned_street"],
    "mystery": ["living_room", "dark_corridor", "abandoned_street"],
    "scifi": ["sci_fi_lab", "dark_corridor", "bunker_room"],
    "adventure": ["forest_night", "abandoned_street", "dark_corridor"],
}

LOCATION_LABELS_TR = {
    "forest_night": "Gece Ormanı",
    "abandoned_street": "Terk Edilmiş Sokak",
    "dark_corridor": "Karanlık Koridor",
    "bunker_room": "Yeraltı Sığınağı",
    "sci_fi_lab": "Bilim Kurgu İstasyonu",
    "living_room": "Loş Oda",
}

ACTION_RULES = [
    ("open_door", ["kapı", "kapıyı", "kilit", "kolu", "açtı", "araladı", "içeri girdi"]),
    ("check_phone", ["telefon", "mesaj", "ekran", "bildirim", "aradı", "çalıyor", "sinyal"]),
    ("run", ["koş", "kaç", "hızla", "fırladı", "peşinden", "kovala", "uzaklaştı"]),
    ("walk", ["yürü", "adım", "ilerle", "yaklaştı", "koridorda", "sokakta", "gitti", "geldi"]),
    ("hide", ["saklan", "gizlen", "çömel", "arkasına", "masanın", "dolabın", "nefesini tuttu"]),
    ("react_fear", ["kork", "ürper", "titredi", "çığlık", "dehşet", "şok", "donakaldı", "panik"]),
    ("look_around", ["bak", "etraf", "gördü", "izle", "fener", "karanlığa", "göz", "ses geldi"]),
]

EMOTION_RULES = [
    ("scared", ["kork", "dehşet", "titredi", "ürper", "panik", "endişe", "karanlık", "tehlike"]),
    ("shocked", ["birden", "aniden", "şok", "inanamadı", "çığlık", "patlama", "kırıldı"]),
    ("suspicious", ["gizem", "acaba", "garip", "tuhaf", "fısıltı", "gölge", "iz", "kim"]),
    ("determined", ["karar", "cesaret", "kurtul", "mücadele", "hazır", "plan", "başar"]),
]

SFX_RULES = [
    ("door_creak", ["kapı", "kapıyı", "gıcırtı", "kilit", "açıldı", "aralandı"]),
    ("phone_ring", ["telefon", "mesaj", "bildirim", "çaldı", "titreşim", "telsiz"]),
    ("footsteps_run", ["koş", "kaç", "hızla", "kovala"]),
    ("footsteps_walk", ["adım", "yürü", "yaklaştı", "ayak sesi", "koridorda"]),
    ("monster_growl", ["zombi", "canavar", "yaratık", "hırıltı", "kükreme", "pençe", "enfekte"]),
    ("glass_break", ["cam", "pencere", "kırıldı", "parçalandı"]),
    ("heartbeat", ["kalp", "kalbi", "nefes", "korku", "panik", "sessizlik", "gerilim"]),
    ("rain_thunder", ["yağmur", "fırtına", "şimşek", "gök gürültüsü", "rüzgar"]),
    ("alarm_siren", ["alarm", "siren", "uyarı", "acil", "kırmızı ışık", "tehlike"]),
]

GENRE_CHOICES_TEMPLATES = {
    "horror": [
        {"key": "A", "text": "Gıcırdayan bodrum kapısını aralayıp feneri içeri tut", "consequence_hint": "Sesin kaynağını doğrudan göreceksin ama kaçış yolun daralacak"},
        {"key": "B", "text": "Işıkları kapatıp dolabın arkasına saklanarak bekle", "consequence_hint": "Gölge yanından geçebilir veya seni fark edebilir"},
        {"key": "C", "text": "Arka pencereden karanlık bahçeye atlayıp uzaklaş", "consequence_hint": "Evden çıkacaksın ancak dışarıda ne olduğunu bilmiyorsun"},
    ],
    "zombie": [
        {"key": "A", "text": "Demir kapıyı barikatla kapatıp çatı katına çık", "consequence_hint": "Yüksekten yardım sinyali gönderebilirsin ama etrafın sarılabilir"},
        {"key": "B", "text": "Sokaktaki terk edilmiş aracın anahtarını bulup çalıştır", "consequence_hint": "Motor sesi sürüleri çekecek ama hızla bölgeden çıkabilirsin"},
        {"key": "C", "text": "Yeraltı metro tünelinden güvenli bölgeye yürü", "consequence_hint": "Sürüden gizleneceksin fakat karanlık tünelde cephanen az"},
    ],
    "survival": [
        {"key": "A", "text": "Uzaktan gelen telsiz sinyalinin olduğu tepeye tırman", "consequence_hint": "Kurtarma ekibine ulaşabilirsin ama fırtına yaklaşıyor"},
        {"key": "B", "text": "Mağarada ateş yakıp geceyi güvenli şekilde geçir", "consequence_hint": "Enerjini koruyacaksın ancak duman yerini belli edebilir"},
        {"key": "C", "text": "Nehir kıyısını takip ederek eski kampa in", "consequence_hint": "Su ve erzak bulma şansın yüksek ama buzlu zemin tehlikeli"},
    ],
    "mystery": [
        {"key": "A", "text": "Masadaki şifreli günlüğü açıp son sayfayı oku", "consequence_hint": "Şüphelinin gerçek kimliğini öğreneceksin"},
        {"key": "B", "text": "Gizli kameranın kayıtlarını incelemek için güvenlik odasına gir", "consequence_hint": "Olay anını göreceksin ama içeride biri olabilir"},
        {"key": "C", "text": "Yağmur altında kaçan yabancıyı sessizce takip et", "consequence_hint": "İzini kaybetmeden nereye gittiğini bulacaksın"},
    ],
    "scifi": [
        {"key": "A", "text": "Ana bilgisayara bağlanıp karantina kilidini devre dışı bırak", "consequence_hint": "Kapılar açılacak ama sistem alarm verecek"},
        {"key": "B", "text": "Kaçış kapsülüne binip yörünge istasyonundan ayrıl", "consequence_hint": "Hayatta kalacaksın ancak mürettebatın sırrı içeride kalacak"},
        {"key": "C", "text": "Reaktör odasına inip enerji kaynağını manuel başlat", "consequence_hint": "İstasyonu kurtarabilirsin ama radyasyon seviyesi yükseliyor"},
    ],
    "adventure": [
        {"key": "A", "text": "Antik tapınağın taş kapısındaki sembolleri çevir", "consequence_hint": "Gizli hazine odası açılacak ama tuzaklar aktif olabilir"},
        {"key": "B", "text": "Asma köprüden karşı uçuruma hızla geç", "consequence_hint": "Kestirme yoldan hedefe ulaşacaksın"},
        {"key": "C", "text": "Haritadaki gizli mağara geçidini kullan", "consequence_hint": "Fırtınadan korunarak dağın diğer yamacına çıkacaksın"},
    ],
}


def detect_location(text: str, genre: str, scene_index: int) -> str:
    lower_txt = text.lower()
    for loc_id, keywords in LOCATION_KEYWORDS.items():
        if any(kw in lower_txt for kw in keywords):
            return loc_id
    defaults = GENRE_DEFAULT_LOCATIONS.get(genre, GENRE_DEFAULT_LOCATIONS["horror"])
    return defaults[scene_index % len(defaults)]


def detect_action(text: str, item_type: str) -> str:
    lower_txt = text.lower()
    for action_id, keywords in ACTION_RULES:
        if any(kw in lower_txt for kw in keywords):
            return action_id
    if item_type == "character_dialogue":
        return "talk"
    return "walk" if len(lower_txt) > 35 else "look_around"


def detect_emotion(text: str, genre: str, role_type: str) -> str:
    if role_type == "monster":
        return "monster_rage"
    lower_txt = text.lower()
    for emo_id, keywords in EMOTION_RULES:
        if any(kw in lower_txt for kw in keywords):
            return emo_id
    if genre in ("horror", "zombie"):
        return "scared"
    return "determined"


def detect_camera_motion(action: str, emotion: str, item_type: str, scene_index: int) -> str:
    if emotion in ("scared", "shocked") and action in ("react_fear", "run"):
        return "camera_shake"
    if item_type == "character_dialogue":
        return "fast_zoom_face"
    if action in ("walk", "run"):
        return "pan_follow"
    if action in ("open_door", "check_phone"):
        return "slow_zoom_in"
    return "wide_establish" if scene_index == 0 else "slow_zoom_in"


def detect_sfx_triggers(text: str, action: str, genre: str, start_sec: float, duration_sec: float) -> List[Dict[str, Any]]:
    lower_txt = text.lower()
    triggers = []
    added_types = set()

    for sfx_type, keywords in SFX_RULES:
        if any(kw in lower_txt for kw in keywords):
            triggers.append({
                "sfx_type": sfx_type,
                "trigger_sec": round(start_sec + 0.1, 2),
                "duration_sec": round(min(2.5, duration_sec), 2),
                "volume": 0.65,
            })
            added_types.add(sfx_type)

    if action == "open_door" and "door_creak" not in added_types:
        triggers.append({
            "sfx_type": "door_creak",
            "trigger_sec": round(start_sec + 0.15, 2),
            "duration_sec": 1.6,
            "volume": 0.65,
        })
    elif action == "run" and "footsteps_run" not in added_types:
        triggers.append({
            "sfx_type": "footsteps_run",
            "trigger_sec": round(start_sec, 2),
            "duration_sec": round(duration_sec, 2),
            "volume": 0.55,
        })
    elif action == "walk" and "footsteps_walk" not in added_types:
        triggers.append({
            "sfx_type": "footsteps_walk",
            "trigger_sec": round(start_sec, 2),
            "duration_sec": round(duration_sec, 2),
            "volume": 0.45,
        })
    elif action == "check_phone" and "phone_ring" not in added_types:
        triggers.append({
            "sfx_type": "phone_ring",
            "trigger_sec": round(start_sec + 0.1, 2),
            "duration_sec": 1.4,
            "volume": 0.60,
        })

    if not triggers and genre in ("horror", "zombie"):
        triggers.append({
            "sfx_type": "heartbeat",
            "trigger_sec": round(start_sec, 2),
            "duration_sec": round(min(3.0, duration_sec), 2),
            "volume": 0.40,
        })

    return triggers


def detect_hud_overlay(text: str, action: str, location: str, scene_index: int, previous_choice: Optional[str]) -> Optional[Dict[str, str]]:
    lower_txt = text.lower()
    if scene_index == 0 and previous_choice in ("A", "B", "C"):
        return {
            "type": "choice_continuation",
            "title": f"ÖNCEKİ KARAR: {previous_choice} ŞIKKI",
            "subtitle": "Hikâye izleyici seçimine göre devam ediyor",
        }
    if action == "check_phone" or any(k in lower_txt for k in ["telefon", "mesaj", "bildirim", "sinyal"]):
        return {
            "type": "phone_alert",
            "title": "📱 YENİ BİLDİRİM",
            "subtitle": "Bilinmeyen Numara: 'Oradan hemen çık!'",
        }
    if any(k in lower_txt for k in ["tehlike", "dikkat", "uyarı", "zombi", "canavar", "alarm"]):
        return {
            "type": "danger_warning",
            "title": "⚠️ YÜKSEK TEHLİKE",
            "subtitle": "Yakında hareketlilik algılandı",
        }
    if scene_index == 0:
        return {
            "type": "location_stamp",
            "title": f"📍 {LOCATION_LABELS_TR.get(location, 'Bilinmeyen Bölge')}",
            "subtitle": "Saat 03:14 • Kayıt Başladı",
        }
    return None


def build_cast_roster(analyzed_characters: List[Dict[str, Any]], genre: str) -> List[Dict[str, Any]]:
    roster = []
    has_main = any(c.get("role_type") == "main" for c in analyzed_characters)

    if not has_main:
        roster.append({
            "character_id": "protagonist_main",
            "name": "Ana Karakter",
            "role_type": "main",
            "outfit_color": "#3b82f6",
            "hair_style": "short_dark",
            "accessory": "flashlight" if genre in ("horror", "zombie", "survival") else "backpack",
        })

    palette = ["#10b981", "#f59e0b", "#ec4899", "#06b6d4", "#a855f7"]
    for idx, ch in enumerate(analyzed_characters):
        role = ch.get("role_type", "supporting")
        color = "#ef4444" if role == "monster" else palette[idx % len(palette)]
        roster.append({
            "character_id": ch["slot_id"],
            "name": ch["character_name"],
            "role_type": role,
            "outfit_color": color,
            "hair_style": "monster_spikes" if role == "monster" else "medium_styled",
            "accessory": "claws" if role == "monster" else "jacket",
        })

    return roster


def generate_story_plan(project_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    project_id = project_data["project_id"]
    genre = project_data.get("genre", "horror")
    previous_choice = project_data.get("previous_choice")

    master_timeline = analysis_result.get("master_timeline", [])
    analyzed_chars = analysis_result.get("characters", [])
    total_duration = float(analysis_result.get("total_duration_sec", 0.0))

    cast_roster = build_cast_roster(analyzed_chars, genre)
    main_char_id = next((c["character_id"] for c in cast_roster if c["role_type"] == "main"), cast_roster[0]["character_id"])

    scenes = []
    scenes_preview = []

    for idx, item in enumerate(master_timeline):
        text = item.get("text", "")
        item_type = item.get("type", "narrator")
        start_sec = float(item.get("timeline_start_sec", 0.0))
        end_sec = float(item.get("timeline_end_sec", start_sec + 2.0))
        dur_sec = max(0.4, round(end_sec - start_sec, 3))

        location = detect_location(text, genre, idx)
        action = detect_action(text, item_type)
        role_type = item.get("role_type", "narrator")
        emotion = detect_emotion(text, genre, role_type)
        camera = detect_camera_motion(action, emotion, item_type, idx)
        sfx_list = detect_sfx_triggers(text, action, genre, start_sec, dur_sec)
        hud_overlay = detect_hud_overlay(text, action, location, idx, previous_choice)

        active_characters_in_scene = []
        if item_type == "character_dialogue":
            speaker_slot_id = item.get("item_id")
            active_characters_in_scene.append({
                "character_id": speaker_slot_id,
                "speaker_name": item.get("speaker", "Karakter"),
                "role_type": role_type,
                "position": "center_right" if role_type != "main" else "center_left",
                "action": "talk",
                "emotion": emotion,
                "is_speaking": True,
                "lipsync_30fps": item.get("lipsync_30fps", []),
            })
            if speaker_slot_id != main_char_id:
                active_characters_in_scene.append({
                    "character_id": main_char_id,
                    "speaker_name": "Ana Karakter",
                    "role_type": "main",
                    "position": "left",
                    "action": "look_around",
                    "emotion": "scared" if role_type == "monster" else "neutral",
                    "is_speaking": False,
                    "lipsync_30fps": [],
                })
        else:
            active_characters_in_scene.append({
                "character_id": main_char_id,
                "speaker_name": "Ana Karakter",
                "role_type": "main",
                "position": "center",
                "action": action,
                "emotion": emotion,
                "is_speaking": False,
                "lipsync_30fps": [],
            })
            lower_t = text.lower()
            if any(k in lower_t for k in ["zombi", "canavar", "yaratık", "gölge", "biri", "arkasında"]):
                monster_char = next((c for c in cast_roster if c["role_type"] == "monster"), None)
                m_id = monster_char["character_id"] if monster_char else "shadow_threat"
                active_characters_in_scene.append({
                    "character_id": m_id,
                    "speaker_name": "Tehdit / Gölge",
                    "role_type": "monster",
                    "position": "right_back",
                    "action": "walk",
                    "emotion": "monster_rage",
                    "is_speaking": False,
                    "lipsync_30fps": [],
                })

        scene_obj = {
            "scene_id": idx + 1,
            "timeline_item_id": item.get("item_id"),
            "type": item_type,
            "speaker": item.get("speaker", "narrator"),
            "text": text,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration_sec": dur_sec,
            "start_frame": int(round(start_sec * config.VIDEO_FPS)),
            "end_frame": int(round(end_sec * config.VIDEO_FPS)),
            "location": location,
            "location_label": LOCATION_LABELS_TR.get(location, "Mekân"),
            "primary_action": action,
            "primary_emotion": emotion,
            "camera_motion": camera,
            "characters": active_characters_in_scene,
            "sfx_triggers": sfx_list,
            "hud_overlay": hud_overlay,
            "props": {
                "has_door": action == "open_door" or "kapı" in text.lower(),
                "has_phone": action == "check_phone" or "telefon" in text.lower(),
                "has_flashlight": genre in ("horror", "zombie", "survival"),
            },
        }
        scenes.append(scene_obj)

        scenes_preview.append({
            "scene_id": idx + 1,
            "speaker": "Anlatıcı" if item_type == "narrator" else item.get("speaker", "Karakter"),
            "time_range": f"{start_sec:.1f}s - {end_sec:.1f}s",
            "location_label": LOCATION_LABELS_TR.get(location, location),
            "action": action,
            "camera": camera,
            "sfx": [s["sfx_type"] for s in sfx_list],
            "text": text,
        })

    interactive_choices = GENRE_CHOICES_TEMPLATES.get(genre, GENRE_CHOICES_TEMPLATES["horror"])
    choice_outro_duration = 3.5
    final_video_duration = round(total_duration + choice_outro_duration, 3)

    story_plan = {
        "project_id": project_id,
        "project_name": project_data.get("project_name", "Hikâye"),
        "genre": genre,
        "previous_choice": previous_choice,
        "fps": config.VIDEO_FPS,
        "resolution": {"width": config.VIDEO_WIDTH, "height": config.VIDEO_HEIGHT},
        "audio_duration_sec": total_duration,
        "choice_outro_duration_sec": choice_outro_duration,
        "total_video_duration_sec": final_video_duration,
        "cast_roster": cast_roster,
        "scenes": scenes,
        "scenes_preview": scenes_preview,
        "interactive_choices": interactive_choices,
        "ambient_music_style": f"{genre}_dark_ambient",
    }

    plan_file = config.CACHE_DIR / f"{project_id}_scene_plan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(story_plan, f, ensure_ascii=False, indent=2)

    return story_plan
```eof
