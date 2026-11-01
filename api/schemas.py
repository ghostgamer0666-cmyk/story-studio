from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CharacterAudioInfo(BaseModel):
    slot_id: str
    character_name: str
    role_type: str = "supporting"
    filename: str
    file_path: str
    duration_sec: float = 0.0
    transcript: str = ""
    confidence: float = 1.0
    matched_after_segment_id: Optional[int] = None

class AmbiguousMatchItem(BaseModel):
    slot_id: str
    filename: str
    detected_transcript: str
    suggested_character_name: str
    suggested_role_type: str
    suggested_after_narrator_text: str
    confidence: float

class StoryChoiceOption(BaseModel):
    key: str
    text: str
    consequence_hint: str

class ScenePreviewItem(BaseModel):
    scene_id: int
    speaker: str
    time_range: str
    location_label: str
    action: str
    camera: str
    sfx: List[str] = []
    text: str
    preview_url: Optional[str] = None

class CharacterCardItem(BaseModel):
    character_id: str
    name: str
    role_type: str
    outfit_color: str
    accessory: str
    avatar_url: str

class ProjectStatusResponse(BaseModel):
    project_id: str
    project_name: str
    genre: str
    status: str
    progress: int = Field(default=0, ge=0, le=100)
    current_step_label: str
    step_index: int = 1
    error_message: Optional[str] = None
    ambiguous_matches: List[AmbiguousMatchItem] = []
    video_url: Optional[str] = None
    master_audio_url: Optional[str] = None
    first_scene_preview_url: Optional[str] = None
    duration_sec: Optional[float] = None
    interactive_choices: List[StoryChoiceOption] = []
    scene_count: int = 0
    narrator_transcript_preview: Optional[str] = None
    scenes_preview: List[ScenePreviewItem] = []
    character_cards: List[CharacterCardItem] = []

class ConfirmCharacterMappingRequest(BaseModel):
    mappings: Dict[str, Dict[str, str]]
```eof
