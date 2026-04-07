"""Replay snapshot serialization and schema validation.

This module handles saving / loading replay snapshots that allow
rebuilding a briefing page without hitting the Naver API or OpenAI.
Snapshot files are versioned JSON with deterministic structure.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

# ── schema version ──────────────────────────────────────────────────
# Bump SNAPSHOT_SCHEMA_VERSION when the snapshot payload structure
# changes in a backward-incompatible way (new required fields, renamed
# keys, etc.).  SNAPSHOT_MIN_COMPAT_VERSION is the oldest version that
# the current code can still read.
SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_MIN_COMPAT_VERSION = 1

KST = timezone(timedelta(hours=9))

# type aliases (kept local so this module has zero coupling to main.py)
JsonDict = dict[str, Any]
SummaryCacheEntry = dict[str, str]

# ── Article ↔ dict helpers ──────────────────────────────────────────
# These work with *any* object that has the expected attributes (duck
# typing) so main.py does **not** need to export the Article class.

_ARTICLE_STR_FIELDS = (
    "section", "title", "description", "link", "originallink",
    "domain", "press", "norm_key", "title_key", "canon_url", "topic",
    "summary", "forced_section", "origin_section", "source_query",
    "source_channel", "selection_stage", "selection_note", "reassigned_from",
)

_ARTICLE_FLOAT_FIELDS = ("score", "selection_fit_score")

_ARTICLE_BOOL_FIELDS = ("is_core",)


def article_to_snapshot_dict(article: Any) -> JsonDict:
    """Serialize an Article-like object to a plain dict for JSON."""
    pub = getattr(article, "pub_dt_kst", None)
    if not isinstance(pub, datetime):
        pub = datetime.min.replace(tzinfo=KST)
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=KST)
    d: JsonDict = {"pub_dt_kst": pub.astimezone(KST).isoformat()}
    for f in _ARTICLE_STR_FIELDS:
        d[f] = str(getattr(article, f, "") or "")
    for f in _ARTICLE_FLOAT_FIELDS:
        d[f] = float(getattr(article, f, 0.0) or 0.0)
    for f in _ARTICLE_BOOL_FIELDS:
        d[f] = bool(getattr(article, f, False))
    return d


def _parse_datetime(value: Any) -> datetime:
    """Parse an ISO datetime string (or passthrough datetime) → KST."""
    if isinstance(value, datetime):
        return value.astimezone(KST) if value.tzinfo else value.replace(tzinfo=KST)
    raw = str(value or "").strip()
    if not raw:
        return datetime.min.replace(tzinfo=KST)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    except Exception:
        return datetime.min.replace(tzinfo=KST)


def article_dict_to_kwargs(payload: Any) -> JsonDict:
    """Convert a snapshot dict back to keyword-args for Article(...)."""
    data = payload if isinstance(payload, dict) else {}
    kw: JsonDict = {"pub_dt_kst": _parse_datetime(data.get("pub_dt_kst"))}
    for f in _ARTICLE_STR_FIELDS:
        kw[f] = str(data.get(f, "") or "")
    for f in _ARTICLE_FLOAT_FIELDS:
        kw[f] = float(data.get(f, 0.0) or 0.0)
    for f in _ARTICLE_BOOL_FIELDS:
        kw[f] = bool(data.get(f, False))
    # Warn on missing critical fields
    if not kw.get("title") and not kw.get("link"):
        log.warning("[REPLAY] article missing both title and link: %s", {k: kw.get(k) for k in ("section", "norm_key", "press")})
    elif not kw.get("title"):
        log.warning("[REPLAY] article missing title: link=%s", kw.get("link", "")[:80])
    return kw


# ── summary-cache subset ────────────────────────────────────────────

def extract_summary_cache_for_articles(
    by_section: dict[str, list[Any]] | None,
    cache: dict[str, SummaryCacheEntry | str] | None,
) -> dict[str, SummaryCacheEntry | str]:
    """Return the subset of *cache* that covers articles in *by_section*."""
    keys = {
        str(getattr(a, "norm_key", "") or "")
        for lst in (by_section or {}).values()
        for a in (lst or [])
        if str(getattr(a, "norm_key", "") or "").strip()
    }
    out: dict[str, SummaryCacheEntry | str] = {}
    for key in sorted(keys):
        value = (cache or {}).get(key)
        if isinstance(value, str):
            if value.strip():
                out[key] = value.strip()
        elif isinstance(value, dict):
            text = str(value.get("s", "") or "").strip()
            if text:
                out[key] = {"s": text, "t": str(value.get("t", "") or "").strip()}
    return out


# ── path resolution ─────────────────────────────────────────────────

def resolve_snapshot_path(
    report_date: str,
    *,
    local_output_path_fn: Callable[[str, str], Path] | None = None,
    content_branch: str = "main",
    is_local: bool = False,
) -> Path:
    """Determine where to read/write a snapshot file.

    Priority:
      1. ``REPLAY_SNAPSHOT_PATH`` env var (exact path)
      2. ``REPLAY_SNAPSHOT_DIR`` env var (directory)
      3. local dry-run layout (if *is_local* and *local_output_path_fn*)
      4. working-directory fallback
    """
    raw_path = str(os.getenv("REPLAY_SNAPSHOT_PATH", "") or "").strip()
    if raw_path:
        p = Path(raw_path)
        return p if p.is_absolute() else (Path.cwd() / p)

    raw_dir = str(os.getenv("REPLAY_SNAPSHOT_DIR", "") or "").strip()
    if raw_dir:
        base = Path(raw_dir)
        if not base.is_absolute():
            base = Path.cwd() / base
        return base / f"{report_date}.snapshot.json"

    if is_local and local_output_path_fn is not None:
        return local_output_path_fn(f".agri_replay/{report_date}.snapshot.json", content_branch)

    return Path.cwd() / ".agri_replay" / f"{report_date}.snapshot.json"


# ── save ────────────────────────────────────────────────────────────

def save_snapshot(
    report_date: str,
    start_kst: datetime,
    end_kst: datetime,
    raw_by_section: dict[str, list[Any]],
    section_keys: list[str],
    *,
    summary_cache: dict[str, SummaryCacheEntry | str] | None = None,
    debug_payload: JsonDict | None = None,
    build_tag: str = "",
    content_ref: str = "",
    content_branch: str = "",
    target: Path | None = None,
    local_output_path_fn: Callable[[str, str], Path] | None = None,
    is_local: bool = False,
) -> Path:
    """Write a replay snapshot JSON file and return the path."""
    if target is None:
        target = resolve_snapshot_path(
            report_date,
            local_output_path_fn=local_output_path_fn,
            content_branch=content_branch,
            is_local=is_local,
        )
    target.parent.mkdir(parents=True, exist_ok=True)

    payload: JsonDict = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "version": SNAPSHOT_SCHEMA_VERSION,  # back-compat alias
        "report_date": str(report_date or "").strip(),
        "created_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "build_tag": build_tag,
        "content_ref": content_ref,
        "content_branch": content_branch,
        "window": {
            "start_kst": start_kst.astimezone(KST).isoformat() if isinstance(start_kst, datetime) else str(start_kst),
            "end_kst": end_kst.astimezone(KST).isoformat() if isinstance(end_kst, datetime) else str(end_kst),
        },
        "raw_by_section": {
            key: [
                article_to_snapshot_dict(a)
                for a in (raw_by_section or {}).get(key, []) or []
            ]
            for key in section_keys
            if key
        },
        "summary_cache": extract_summary_cache_for_articles(raw_by_section, summary_cache),
        "debug": debug_payload if isinstance(debug_payload, dict) else {},
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


# ── load + validate ─────────────────────────────────────────────────

class SnapshotVersionError(RuntimeError):
    """Raised when a snapshot file has an incompatible schema version."""


def load_snapshot(
    report_date: str,
    section_keys: list[str],
    article_factory: Callable[[JsonDict], Any],
    *,
    target: Path | None = None,
    local_output_path_fn: Callable[[str, str], Path] | None = None,
    content_branch: str = "main",
    is_local: bool = False,
) -> tuple[dict[str, list[Any]], datetime, datetime, dict[str, SummaryCacheEntry | str], JsonDict, Path]:
    """Load and validate a replay snapshot.

    Parameters
    ----------
    article_factory:
        Callable that takes a kwargs dict and returns an Article instance.
        This avoids importing Article directly.

    Returns
    -------
    (raw_by_section, start_kst, end_kst, summary_cache, debug, path)
    """
    if target is None:
        target = resolve_snapshot_path(
            report_date,
            local_output_path_fn=local_output_path_fn,
            content_branch=content_branch,
            is_local=is_local,
        )
    if not target.is_file():
        raise RuntimeError(f"Replay snapshot not found: {target}")

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Replay snapshot read failed: {target} ({exc})") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"Replay snapshot is invalid JSON object: {target}")

    # ── schema version check ────────────────────────────────────────
    file_version = int(payload.get("schema_version") or payload.get("version") or 0)
    if file_version < SNAPSHOT_MIN_COMPAT_VERSION:
        raise SnapshotVersionError(
            f"Snapshot schema version {file_version} is too old "
            f"(minimum compatible: {SNAPSHOT_MIN_COMPAT_VERSION}, "
            f"current: {SNAPSHOT_SCHEMA_VERSION}). "
            f"Please regenerate the snapshot with a live build. "
            f"Path: {target}"
        )
    if file_version > SNAPSHOT_SCHEMA_VERSION:
        log.warning(
            "[REPLAY] Snapshot schema version %d is newer than code version %d. "
            "Proceeding with best-effort load.  Path: %s",
            file_version, SNAPSHOT_SCHEMA_VERSION, target,
        )

    # ── report date check ───────────────────────────────────────────
    snapshot_report_date = str(payload.get("report_date", "") or "").strip()
    if snapshot_report_date and report_date and snapshot_report_date != report_date:
        raise RuntimeError(
            f"Replay snapshot date mismatch: "
            f"requested={report_date} snapshot={snapshot_report_date} path={target}"
        )

    # ── articles ────────────────────────────────────────────────────
    raw_payload = payload.get("raw_by_section", {})
    raw_by_section: dict[str, list[Any]] = {}
    for key in section_keys:
        if not key:
            continue
        rows = raw_payload.get(key, []) if isinstance(raw_payload, dict) else []
        articles = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            kw = article_dict_to_kwargs(item)
            if not kw.get("title") and not kw.get("link"):
                log.warning("[REPLAY] skipping corrupt article (no title+link) in section=%s", key)
                continue
            articles.append(article_factory(kw))
        raw_by_section[key] = articles

    # ── window ──────────────────────────────────────────────────────
    window = payload.get("window", {})
    start_kst = _parse_datetime(window.get("start_kst") if isinstance(window, dict) else None)
    end_kst = _parse_datetime(window.get("end_kst") if isinstance(window, dict) else None)

    summary_cache = payload.get("summary_cache", {})
    debug_payload = payload.get("debug", {})
    return (
        raw_by_section,
        start_kst,
        end_kst,
        summary_cache if isinstance(summary_cache, dict) else {},
        debug_payload if isinstance(debug_payload, dict) else {},
        target,
    )
