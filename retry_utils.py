from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Mapping
import random


def exponential_backoff(attempt: int, *, base: float = 0.8, cap: float = 20.0, jitter: float = 0.4) -> float:
    """Return an exponential backoff delay with bounded random jitter."""
    a = max(0, int(attempt))
    b = max(0.0, float(base))
    c = max(0.1, float(cap))
    j = max(0.0, float(jitter))
    delay = (b * (2**a)) + random.uniform(0.0, j)
    return float(min(c, delay))


def parse_retry_after(headers: Mapping[str, str] | None) -> float:
    if not headers:
        return 0.0

    raw = str(headers.get("Retry-After", "") or "").strip()
    if not raw:
        return 0.0

    try:
        return max(0.0, float(raw))
    except Exception:
        pass

    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (dt - now).total_seconds())
    except Exception:
        return 0.0


def retry_after_or_backoff(
    headers: Mapping[str, str] | None,
    attempt: int,
    *,
    base: float = 0.8,
    cap: float = 20.0,
    jitter: float = 0.4,
) -> float:
    ra = parse_retry_after(headers)
    if ra > 0:
        return ra
    return exponential_backoff(attempt, base=base, cap=cap, jitter=jitter)
