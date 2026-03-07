from __future__ import annotations

from typing import Any, Callable


PressPriorityFn = Callable[[str, str], int]


def sort_key_major_first(article: Any, press_priority_fn: PressPriorityFn) -> tuple[float, int, Any]:
    """Stable major sort key: score > press priority > publication datetime."""
    return (
        getattr(article, "score", 0.0),
        int(press_priority_fn(getattr(article, "press", ""), getattr(article, "domain", ""))),
        getattr(article, "pub_dt_kst", None),
    )
