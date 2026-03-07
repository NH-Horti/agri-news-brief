from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
import logging
import threading
from typing import Any


log = logging.getLogger("agri-brief")


def _metric_key(name: str, tags: dict[str, str]) -> str:
    if not tags:
        return name
    parts = [f"{k}={v}" for k, v in sorted(tags.items())]
    return f"{name}|" + ",".join(parts)


@dataclass
class MetricsRegistry:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def inc(self, name: str, value: int = 1, **tags: str) -> None:
        key = _metric_key(name, {k: str(v) for k, v in tags.items()})
        with self._lock:
            self._counters[key] = int(self._counters.get(key, 0)) + int(value)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()


METRICS = MetricsRegistry()


def metric_inc(name: str, value: int = 1, **tags: str) -> None:
    METRICS.inc(name, value=value, **tags)


def log_event(event: str, **payload: Any) -> None:
    body = {"event": event, **payload}
    try:
        log.info("[OBS] %s", json.dumps(body, ensure_ascii=False, sort_keys=True))
    except Exception:
        log.info("[OBS] event=%s payload=%s", event, body)


def flush_metrics(event: str = "metrics_snapshot", *, clear: bool = False) -> dict[str, int]:
    snap = METRICS.snapshot()
    log_event(event, metrics=snap)
    if clear:
        METRICS.clear()
    return snap