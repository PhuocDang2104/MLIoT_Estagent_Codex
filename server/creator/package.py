"""Published Creator package schema; independent of the historical core draft."""
from typing import Literal
from pydantic import Field
from .models import Model, Fact, Link, Script


class Anchor(Model):
    position: tuple[float, float, float]
    room_id: str
    dollhouse_visible: bool = True
    heading: float = Field(default=0, ge=-180, le=180, allow_inf_nan=False)
    accuracy: Literal['approximate', 'measured'] = 'approximate'


class GeometryMetadata(Model):
    units: Literal['meters']
    up_axis: Literal['Y']
    scale: Literal['assumed', 'measured']
    builder: str
    plan_sha256: str


class Geometry(Model):
    asset_id: str
    anchors: dict[str, Anchor]
    metadata: GeometryMetadata | None = None


class Room(Model):
    checkpoint_id: str
    room_id: str
    asset_id: str
    label: str
    yaw: float = Field(ge=-180, le=180)
    summary: str
    facts: list[Fact]
    estimated: bool
    projection: Literal['photo', 'equirectangular']
    anchor: Anchor


class Audio(Model):
    checkpoint_id: str
    asset_id: str
    duration: float = Field(gt=0, le=600)


class Narration(Script):
    audio: list[Audio] = Field(min_length=2, max_length=13)


class Music(Model):
    id: str
    project_id: str
    name: str
    kind: Literal['music']
    mime: Literal['audio/wav']
    size: int
    sha256: str
    width: int
    height: int
    duration: float
    credit: str = Field(min_length=1)
    warning: str | None


class Asset(Model):
    id: str
    kind: Literal['panorama', 'model', 'music', 'narration']
    mime: str
    name: str


class Hotspot(Link):
    label: str
    target_yaw: float


class PublishedTour(Model):
    version: Literal[1]
    id: str
    generation_id: str
    name: str
    locale: Literal['vi', 'en']
    rooms: list[Room] = Field(min_length=1, max_length=12)
    connections: list[Link]
    navigation: list[Hotspot]
    itinerary: list[str]
    model: Geometry
    narration: Narration
    music: Music
    approved: Literal[True]
    ai_voice_disclosure: Literal[True]
    published_at: str
    public_id: str
    assets: list[Asset]
