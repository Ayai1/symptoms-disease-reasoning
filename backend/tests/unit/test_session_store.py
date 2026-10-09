from __future__ import annotations

import pytest

from app.sessions.store import InMemorySessionStore, SessionCapacityError


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _store(clock: FakeClock, **kwargs: float) -> InMemorySessionStore:
    params: dict[str, float] = {
        "idle_ttl_seconds": 1800,
        "absolute_ttl_seconds": 7200,
        "max_sessions": 3,
    }
    params.update(kwargs)
    return InMemorySessionStore(
        idle_ttl_seconds=params["idle_ttl_seconds"],
        absolute_ttl_seconds=params["absolute_ttl_seconds"],
        max_sessions=int(params["max_sessions"]),
        clock=clock,
    )


def test_create_and_get() -> None:
    clock = FakeClock()
    store = _store(clock)
    session = store.create(region="IN", age_band=None, sex="unspecified")
    assert store.get(session.id) is session
    assert len(session.id) >= 40


def test_idle_expiry() -> None:
    clock = FakeClock()
    store = _store(clock)
    session = store.create(region="IN", age_band=None, sex="unspecified")
    clock.now += 1799
    assert store.get(session.id) is not None  # refreshes idle timer
    clock.now += 1799
    assert store.get(session.id) is not None
    clock.now += 1800
    assert store.get(session.id) is None


def test_absolute_expiry_despite_activity() -> None:
    clock = FakeClock()
    store = _store(clock)
    session = store.create(region="IN", age_band=None, sex="unspecified")
    for _ in range(4):
        clock.now += 1500
        assert store.get(session.id) is not None
    clock.now += 1500  # 7500 s after creation, beyond the 7200 s absolute limit
    assert store.get(session.id) is None


def test_delete_is_idempotent() -> None:
    store = _store(FakeClock())
    session = store.create(region="IN", age_band=None, sex="unspecified")
    assert store.delete(session.id) is True
    assert store.delete(session.id) is False
    assert store.get(session.id) is None


def test_capacity_purges_expired_before_failing() -> None:
    clock = FakeClock()
    store = _store(clock)
    for _ in range(3):
        store.create(region="IN", age_band=None, sex="unspecified")
    with pytest.raises(SessionCapacityError):
        store.create(region="IN", age_band=None, sex="unspecified")
    clock.now += 7200
    store.create(region="IN", age_band=None, sex="unspecified")
    assert len(store) == 1


def test_session_holds_no_text_fields() -> None:
    store = _store(FakeClock())
    session = store.create(region="IN", age_band=None, sex="unspecified")
    for value in vars(session).values():
        assert not (isinstance(value, str) and " " in value)
