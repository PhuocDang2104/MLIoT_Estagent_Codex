from pathlib import Path
import pytest
from server.assistant.app import create_app


def test_renderer_selection_is_explicit(tmp_path):
    base={'VIDEO_EXPORT_ENABLED':'1','VIDEO_EXPORT_LOCAL_QA':'1'}
    app=create_app(db_path=tmp_path/'native'/'state.sqlite',env=base|{'VIDEO_EXPORT_RENDERER':'ffmpeg'})
    assert callable(app.state.close_video_exports)
    app.state.narration.close()
    app.state.close_video_exports()
    with pytest.raises(ValueError,match='VIDEO_EXPORT_HYPERFRAMES'):
        create_app(db_path=tmp_path/'hf'/'state.sqlite',env=base)
    with pytest.raises(ValueError,match='VIDEO_EXPORT_RENDERER'):
        create_app(db_path=tmp_path/'wrong'/'state.sqlite',env=base|{'VIDEO_EXPORT_RENDERER':'auto'})
