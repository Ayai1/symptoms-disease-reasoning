"""Session state with idle and absolute expiry.

Sessions hold no free text: only region/age band/sex chosen by the user,
red-flag signal IDs and rule IDs (see DECISIONS.md D-014), and counters.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

Clock = Callable[[], float]
SessionStatus = Literal["active", "locked"]
LockReason = Literal["emergency", "self_harm"]


@dataclass
class Session:
    id: str
    created_at: float
    last_seen: float
    region: str
    age_band: str | None
    sex: str
    status: SessionStatus = "active"
    lock_reason: LockReason | None = None
    turn_count: int = 0
    signals: set[str] = field(default_factory=set)
    fired_rule_ids: set[str] = field(default_factory=set)


class SessionStore(Protocol):
    def create(self, *, region: str, age_band: str | None, sex: str) -> Session: ...

    def get(self, session_id: str) -> Session | None: ...

    def save(self, session: Session) -> None: ...

    def delete(self, session_id: str) -> bool: ...

    def expires_at(self, session: Session) -> float: ...

    def purge_expired(self) -> int: ...

    def __len__(self) -> int: ...


class SessionCapacityError(RuntimeError):
    """Raised when the store is full of live sessions."""


class InMemorySessionStore:
    def __init__(
        self,
        *,
        idle_ttl_seconds: float,
        absolute_ttl_seconds: float,
        max_sessions: int,
        clock: Clock = time.time,
        purge_interval_seconds: float = 60.0,
    ) -> None:
        self.idle_ttl = idle_ttl_seconds
        self.absolute_ttl = absolute_ttl_seconds
        self.max_sessions = max_sessions
        self._clock = clock
        self._purge_interval = purge_interval_seconds
        self._last_purge = clock()
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._sessions)

    def expires_at(self, session: Session) -> float:
        return min(session.last_seen + self.idle_ttl, session.created_at + self.absolute_ttl)

    def _expired(self, session: Session, now: float) -> bool:
        return now >= self.expires_at(session)

    def create(self, *, region: str, age_band: str | None, sex: str) -> Session:
        now = self._clock()
        with self._lock:
            if now - self._last_purge >= self._purge_interval:
                self._purge_locked(now)
            if len(self._sessions) >= self.max_sessions:
                self._purge_locked(now)
                if len(self._sessions) >= self.max_sessions:
                    raise SessionCapacityError("session store is full")
            session_id = secrets.token_urlsafe(32)
            session = Session(
                id=session_id,
                created_at=now,
                last_seen=now,
                region=region,
                age_band=age_band,
                sex=sex,
            )
            self._sessions[session_id] = session
            return session

    def get(self, session_id: str) -> Session | None:
        """Return a live session and refresh its idle timer, or None."""
        now = self._clock()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if self._expired(session, now):
                del self._sessions[session_id]
                return None
            session.last_seen = now
            return session

    def save(self, session: Session) -> None:
        with self._lock:
            if session.id in self._sessions:
                self._sessions[session.id] = session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def purge_expired(self) -> int:
        with self._lock:
            return self._purge_locked(self._clock())

    def _purge_locked(self, now: float) -> int:
        expired = [sid for sid, s in self._sessions.items() if self._expired(s, now)]
        for sid in expired:
            del self._sessions[sid]
        self._last_purge = now
        return len(expired)
