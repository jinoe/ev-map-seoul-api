import time
from threading import Lock
from typing import Any

_store: dict[str, tuple[Any, float]] = {}
_lock = Lock()


def get(key: str, ttl: float) -> Any | None:
    with _lock:
        entry = _store.get(key)
    if entry is None:
        return None
    value, ts = entry
    if time.monotonic() - ts > ttl:
        with _lock:
            _store.pop(key, None)
        return None
    return value


def set(key: str, value: Any) -> None:
    with _lock:
        _store[key] = (value, time.monotonic())


def invalidate(prefix: str = "") -> None:
    with _lock:
        keys = [k for k in _store if k.startswith(prefix)]
        for k in keys:
            del _store[k]
