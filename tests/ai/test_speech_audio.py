import struct
import pytest
from server.creator.speech_audio import finalize_wav
from server.creator.store import wav_duration
from tests.ai.creator_fixtures import wav


def test_provider_streaming_header_is_finalized_but_uploads_stay_strict():
    original=wav()
    streamed=bytearray(original)
    struct.pack_into('<I',streamed,4,0xffffffff)
    struct.pack_into('<I',streamed,40,0xffffffff)
    with pytest.raises(ValueError):wav_duration(bytes(streamed))
    normalized=finalize_wav(bytes(streamed))
    assert normalized==original and wav_duration(normalized)>0
    assert finalize_wav(original)==original


def test_actual_truncation_is_not_hidden():
    with pytest.raises(ValueError,match='truncated'):
        finalize_wav(wav()[:-100])
