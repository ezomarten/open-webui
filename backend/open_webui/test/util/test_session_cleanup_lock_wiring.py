"""Source-grep regression tests guarding the session-cleanup-lock fork wiring.

This fork instantiates a dedicated ``RedisLock`` for the periodic
SESSION_POOL cleanup task so multiple replicas don't both reap entries
concurrently. The lock + the periodic task wiring lives in
``socket/main.py``; see FORK_NOTES.md, maintenance record 2026-05-26.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '# fork:session-cleanup-lock'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_socket_main_instantiates_session_cleanup_lock():
    source = _read('backend', 'open_webui', 'socket', 'main.py')

    assert 'session_cleanup_lock = RedisLock(' in source
    assert 'session_aquire_func = session_cleanup_lock.aquire_lock' in source
    assert 'session_renew_func = session_cleanup_lock.renew_lock' in source
    assert 'session_release_func = session_cleanup_lock.release_lock' in source


def test_socket_main_runs_periodic_cleanup_under_lock():
    source = _read('backend', 'open_webui', 'socket', 'main.py')

    assert 'async def periodic_session_pool_cleanup(' in source
    assert 'session_aquire_func()' in source
    assert 'session_renew_func()' in source
    assert 'session_release_func()' in source


def test_socket_main_carries_sentinel():
    source = _read('backend', 'open_webui', 'socket', 'main.py')

    # One sentinel near the lock instantiation + one above the periodic task.
    assert source.count(SENTINEL) >= 2
