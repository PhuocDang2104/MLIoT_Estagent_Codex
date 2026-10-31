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

class Audio(Strict):
    status: Literal['unavailable'] = 'unavailable'
    narration: None = None
    music: None = None
    source: Literal['none'] = 'none'

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

class Rename(Strict):
    scene_id: str
    name: str
    description: str | None

class TourReply(Strict):
    reply: str
    changes: list[Rename]
    order: list[str] | None
    start_scene_id: str | None
