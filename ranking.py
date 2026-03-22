from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


PressPriorityFn = Callable[[str, str], int]

# Sentinel used when pub_dt_kst is missing so that tuple comparison never
# hits a TypeError (None vs datetime).  Epoch-start pushes articles without
# a timestamp to the end of the list.
_EPOCH = datetime(1970, 1, 1)


def sort_key_major_first(article: Any, press_priority_fn: PressPriorityFn) -> tuple[float, int, datetime]:
    """Stable major sort key: score > press priority > publication datetime."""
    pub = getattr(article, "pub_dt_kst", None)
    return (
        getattr(article, "score", 0.0),
        int(press_priority_fn(getattr(article, "press", ""), getattr(article, "domain", ""))),
        pub if isinstance(pub, datetime) else _EPOCH,
    )
