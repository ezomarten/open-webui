from open_webui.socket.utils import get_cleanup_poll_interval


def test_get_cleanup_poll_interval_stays_within_lock_timeout():
    assert get_cleanup_poll_interval(60, 120) == 30


def test_get_cleanup_poll_interval_uses_cleanup_timeout_when_shorter():
    assert get_cleanup_poll_interval(60, 10) == 10


def test_get_cleanup_poll_interval_never_returns_less_than_one_second():
    assert get_cleanup_poll_interval(1, 120) == 1
    assert get_cleanup_poll_interval(0, 120) == 120
