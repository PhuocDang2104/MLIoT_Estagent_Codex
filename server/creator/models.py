from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ProjectInput(Model):
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=10, max_length=6000)
    locale: Literal['vi', 'en'] = 'vi'
    voice: Literal['coral', 'alloy', 'onyx'] = 'coral'
    panorama_confirmed: bool = False
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')

    @field_validator('name', 'description', mode='before')
    @classmethod
    def trim(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Empty text')
        return value.strip()


class Fact(Model):
    text: str = Field(min_length=1, max_length=500)
    provenance: Literal['verified', 'observed', 'inferred', 'unknown']
    source: str = Field(min_length=1, max_length=100)


class Brief(Model):
    summary: str = Field(max_length=1500)
    facts: list[Fact] = Field(max_length=30)
    missing: list[str] = Field(max_length=20)


class Observation(Model):
    label: str = Field(min_length=1, max_length=100)
    room_type: str = Field(max_length=80)
    summary: str = Field(max_length=1200)
    facts: list[Fact] = Field(max_length=20)
    uncertainty: list[str] = Field(max_length=10)


class Segment(Model):
    checkpoint_id: str
    text: str = Field(min_length=1, max_length=1800)
    sources: list[str] = Field(min_length=1)


class Script(Model):
    introduction: str = Field(min_length=1, max_length=1800)
    segments: list[Segment] = Field(min_length=1, max_length=12)


class RoomEdit(Model):
    checkpoint_id: str = Field(pattern=r'^cp[0-9]{2}$')
    label: str = Field(min_length=1, max_length=100)
    yaw: float = Field(ge=-180, le=180, allow_inf_nan=False)


class Link(Model):
    source: str = Field(pattern=r'^cp[0-9]{2}$')
    target: str = Field(pattern=r'^cp[0-9]{2}$')
    yaw: float = Field(ge=-180, le=180, allow_inf_nan=False)
    pitch: float = Field(ge=-90, le=90, allow_inf_nan=False)


class Review(Model):
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')
    kind: Literal['spatial', 'final']
    decision: Literal['approve', 'reject']
    rooms: list[RoomEdit] = Field(default_factory=list, max_length=12)
    connections: list[Link] = Field(default_factory=list, max_length=132)
    scripts: list[Segment] = Field(default_factory=list, max_length=12)


class Action(Model):
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')


class ViewerQuestion(Action):
    question: str = Field(min_length=1, max_length=1000)
    checkpoint_id: str = Field(pattern=r'^cp[0-9]{2}$')


class ViewerAnswer(Model):
    text: str = Field(min_length=1, max_length=2500)
    navigate_to: str | None
