import hashlib
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .provider import VOICES

class Generate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    draft_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    scene_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    revision: int = Field(ge=1)
    locale: Literal['en','vi']
    voice: str = 'coral'
    text: str = Field(min_length=1,max_length=2000)
    approved: Literal[True]
    script_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')

    @model_validator(mode='after')
    def review(self):
        if self.voice not in VOICES or not self.text.strip():
            raise ValueError('Select a built-in voice and a non-empty approved script')
        if self.text != self.text.strip():
            raise ValueError('Remove leading/trailing whitespace and approve the exact script again')
        if hashlib.sha256(self.text.encode()).hexdigest()!=self.script_sha256:
            raise ValueError('Approved script hash differs from input text')
        return self

class Attach(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=1)
