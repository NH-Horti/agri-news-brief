#!/usr/bin/env python3
"""Compare two placement JSON files produced by PLACEMENT_ONLY mode.

Usage:
    python scripts/placement_diff.py <baseline.json> <current.json>

Outputs a per-section diff:
    - REMOVED: articles present in baseline but not in current
    - ADDED:   articles present in current but not in baseline
    - KEPT:    articles in both
    - Unique ratio (distinct titles / total selected)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _ident(row: dict[str, Any]) -> str:
    """Identity for matching rows across runs (norm_key preferred, fallback title)."""
    nk = str(row.get("norm_key") or "").strip()
    if nk:
        return nk
    return str(row.get("title") or "").strip()[:120]


def _title_short(row: dict[str, Any], width: int = 80) -> str:
    t = str(row.get("title") or "").strip()
    if len(t) > width:
        return t[: width - 1] + "…"
    return t


def _unique_ratio(rows: list[dict[str, Any]]) -> tuple[int, int, float]:
    if not rows:
        return 0, 0, 0.0
    titles = [_title_short(r, 200) for r in rows]
    uniq = len(set(titles))
    total = len(titles)
    return uniq, total, (uniq / total) if total > 0 else 0.0


def diff_section(
    name: str,
    base_rows: list[dict[str, Any]],
    curr_rows: list[dict[str, Any]],
) -> None:
    base_map = {_ident(r): r for r in base_rows}
    curr_map = {_ident(r): r for r in curr_rows}
    base_ids = list(base_map.keys())
    curr_ids = list(curr_map.keys())

    removed = [base_map[i] for i in base_ids if i not in curr_map]
    added = [curr_map[i] for i in curr_ids if i not in base_map]
    kept = [curr_map[i] for i in curr_ids if i in base_map]

    b_uniq, b_total, b_ratio = _unique_ratio(base_rows)
    c_uniq, c_total, c_ratio = _unique_ratio(curr_rows)

    print(f"\n=== {name.upper()} ===")
    print(
        f"  baseline: {b_total}건 (unique {b_uniq}, {b_ratio*100:.0f}%) → "
        f"current: {c_total}건 (unique {c_uniq}, {c_ratio*100:.0f}%)"
    )
    print(f"  REMOVED ({len(removed)}건):")
    for r in removed:
        sc = r.get("score", 0.0)
        fit = r.get("fit", 0.0)
        press = r.get("press") or ""
        print(f"    - [score {sc:>5.2f} fit {fit:>4.2f}] [{press}] {_title_short(r)}")
    print(f"  ADDED ({len(added)}건):")
    for r in added:
        sc = r.get("score", 0.0)
        fit = r.get("fit", 0.0)
        press = r.get("press") or ""
        print(f"    + [score {sc:>5.2f} fit {fit:>4.2f}] [{press}] {_title_short(r)}")
    if kept:
        print(f"  KEPT ({len(kept)}건):")
        for r in kept[:5]:
            sc = r.get("score", 0.0)
            press = r.get("press") or ""
            print(f"      [score {sc:>5.2f}] [{press}] {_title_short(r)}")
        if len(kept) > 5:
            print(f"      ... and {len(kept) - 5} more")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    baseline_path = argv[1]
    current_path = argv[2]
    if not Path(baseline_path).exists():
        print(f"error: baseline not found: {baseline_path}", file=sys.stderr)
        return 2
    if not Path(current_path).exists():
        print(f"error: current not found: {current_path}", file=sys.stderr)
        return 2

    baseline = _load(baseline_path)
    current = _load(current_path)

    print(f"Baseline: {baseline_path} ({baseline.get('report_date', '?')})")
    print(f"Current:  {current_path} ({current.get('report_date', '?')})")
    print(
        f"Total selected: {baseline.get('total_selected', 0)} → "
        f"{current.get('total_selected', 0)}"
    )

    base_sections = baseline.get("sections", {}) or {}
    curr_sections = current.get("sections", {}) or {}
    all_keys = list(dict.fromkeys(list(base_sections.keys()) + list(curr_sections.keys())))

    for key in all_keys:
        diff_section(key, base_sections.get(key, []) or [], curr_sections.get(key, []) or [])

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
