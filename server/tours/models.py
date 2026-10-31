"""Checkpoint tour v1: additive to the unimplemented legacy reconstruction draft."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Scene(Strict):
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    asset_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    projection: Literal['photo', 'cylindrical'] = 'photo'
    coverage_degrees: float | None = Field(default=None, ge=30, le=360)
    coverage_source: Literal['unknown', 'user_provisional', 'user_calibrated'] = 'unknown'
    @model_validator(mode='after')
    def calibration(self):
        if self.projection == 'cylindrical' and (self.coverage_degrees is None or self.coverage_source == 'unknown'):
            raise ValueError('Cylindrical projection needs explicit, labelled coverage.')
        if self.projection == 'photo' and (self.coverage_degrees is not None or self.coverage_source != 'unknown'):
            raise ValueError('Ordinary photos have no panorama coverage.')
        return self

class SceneView(Scene):
    image_url: str
    thumbnail_url: str

class AudioProvenance(Strict):
    source_label: str = Field(min_length=3,max_length=200)
    rights: Literal['owned','licensed']
    rights_note: str = Field(min_length=3,max_length=500)

class AudioTrack(AudioProvenance):
    asset_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    url: str
    content_type: Literal['audio/wav'] = 'audio/wav'
    duration_seconds: float = Field(gt=0,le=180)
    channels: Literal[1,2]
    sample_rate: int = Field(ge=8000,le=48000)
    sample_width: Literal[2] = 2

class SceneNarration(Strict):
    scene_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    locale: Literal['en','vi']
    transcript: str = Field(default='',max_length=2000)
    track: AudioTrack

class Audio(Strict):
    status: Literal['unavailable','partial','ready'] = 'unavailable'
    narration: list[SceneNarration] | None = Field(default=None,max_length=20)
    music: AudioTrack | None = None
    source: Literal['none','user_uploaded'] = 'none'


class Manifest(Strict):
    schema_version: Literal['checkpoint-tour-v1'] = 'checkpoint-tour-v1'
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    revision: int = Field(ge=1)
    status: Literal['draft', 'published']
    title: str = Field(min_length=1, max_length=150)
    locale: Literal['en','vi']
    scenes: list[SceneView] = Field(min_length=1,max_length=20)
    start_scene_id: str
    audio: Audio = Field(default_factory=Audio)
    credits: list[str]
    @model_validator(mode='after')
    def start_exists(self):
        ids = [s.id for s in self.scenes]
        if len(set(ids)) != len(ids) or self.start_scene_id not in ids:
            raise ValueError('Scene IDs must be unique and contain the start scene.')
        narrations = self.audio.narration or []
        bindings = [(n.scene_id,n.locale) for n in narrations]
        if len(set(bindings)) != len(bindings) or any(n.scene_id not in ids for n in narrations):
            raise ValueError('Narration must reference unique existing scene/locale pairs.')
        has_audio = bool(narrations or self.audio.music)
        complete = all(any(n.scene_id==id and n.locale==self.locale for n in narrations) for id in ids)
        expected = 'ready' if complete else 'partial' if has_audio else 'unavailable'
        if self.audio.status != expected or self.audio.source != ('user_uploaded' if has_audio else 'none'):
            raise ValueError('Audio availability/source must match actual referenced tracks.')
        return self

class CreateDraft(Strict):
    asset_ids: list[str] = Field(min_length=1,max_length=20)
    title: str = Field(default='Untitled tour',min_length=1,max_length=150)
    text: str = Field(default='',max_length=2000)
    locale: Literal['en','vi'] = 'en'
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')

class Revision(Strict):
    revision: int = Field(ge=1)

class EditDraft(Revision):
    title: str = Field(min_length=1,max_length=150)
    locale: Literal['en','vi']
    scenes: list[Scene] = Field(min_length=1,max_length=20)
    start_scene_id: str

class Chat(Revision):
    text: str = Field(min_length=1,max_length=2000)
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')
    locale: Literal['en','vi'] = 'en'
    scene_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')

class Rename(Strict):
    scene_id: str
    name: str
    description: str | None

class TourReply(Strict):
    reply: str
    changes: list[Rename]
    order: list[str] | None
    start_scene_id: str | None


class NarrationBinding(Strict):
    scene_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    asset_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    locale: Literal['en','vi']
    transcript: str = Field(default='',max_length=2000)

class AudioUpdate(Revision):
    music_asset_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    narration: list[NarrationBinding] = Field(default_factory=list,max_length=20)
