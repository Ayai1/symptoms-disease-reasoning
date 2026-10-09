from __future__ import annotations

from app.core.rate_limit import SlidingWindowLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_limit_then_blocks() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(3, 60, clock=clock)
    assert [limiter.hit("a")[0] for _ in range(3)] == [True, True, True]
    allowed, retry_after = limiter.hit("a")
    assert not allowed
    assert retry_after == 60


def test_window_slides() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(2, 60, clock=clock)
    limiter.hit("a")
    clock.now = 30
    limiter.hit("a")
    clock.now = 59
    assert limiter.hit("a")[0] is False
    clock.now = 60.5
    assert limiter.hit("a")[0] is True


def test_keys_are_independent() -> None:
    limiter = SlidingWindowLimiter(1, 60, clock=FakeClock())
    assert limiter.hit("a")[0]
    assert limiter.hit("b")[0]
    assert not limiter.hit("a")[0]


def test_key_count_is_bounded() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(1, 60, max_keys=10, clock=clock)
    for i in range(100):
        clock.now = i
        limiter.hit(f"k{i}")
    assert len(limiter._hits) <= 10
