import pytest
from server.file_lock import acquire, release


def test_worker_lock_excludes_another_handle_and_releases(tmp_path):
    path=tmp_path/'worker.lock'
    with path.open('a+b') as first, path.open('a+b') as second:
        acquire(first)
        with pytest.raises(BlockingIOError):acquire(second)
        release(first)
        acquire(second)
    with path.open('a+b') as restarted:
        acquire(restarted)
        release(restarted)
