from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main  # noqa: E402
from observability import METRICS  # noqa: E402
from replay import load_snapshot  # noqa: E402


LOG = logging.getLogger("compare_hf_rerank")


@dataclass(frozen=True)
class SnapshotRef:
    label: str
    ref: str
    remote_path: str
    url: str


def _section_keys(selected: list[str] | None = None) -> list[str]:
    keys = [str(sec.get("key") or "").strip() for sec in main.SECTIONS if str(sec.get("key") or "").strip()]
    if not selected:
        return keys
    selected_set = {str(key or "").strip() for key in selected if str(key or "").strip()}
    return [key for key in keys if key in selected_set]


def _article_id(article: Any) -> str:
    return (
        str(getattr(article, "canon_url", "") or "").strip()
        or str(getattr(article, "norm_key", "") or "").strip()
        or f"{str(getattr(article, 'press', '') or '').strip()}|{str(getattr(article, 'title_key', '') or '').strip()}"
        or str(getattr(article, "title", "") or "").strip()
    )


def _article_summary(article: Any) -> dict[str, Any]:
    return {
        "id": _article_id(article),
        "title": str(getattr(article, "title", "") or "")[:200],
        "press": str(getattr(article, "press", "") or ""),
        "score": round(float(getattr(article, "score", 0.0) or 0.0), 3),
        "semantic_boost": round(float(getattr(article, "semantic_boost", 0.0) or 0.0), 6),
        "semantic_similarity": round(float(getattr(article, "semantic_similarity", 0.0) or 0.0), 6),
        "semantic_model": str(getattr(article, "semantic_model", "") or ""),
        "is_core": bool(getattr(article, "is_core", False)),
        "selection_stage": str(getattr(article, "selection_stage", "") or ""),
    }


def _candidate_snapshot_refs(repo: str, report_date: str, snapshot_source: str) -> list[SnapshotRef]:
    refs: list[SnapshotRef] = []
    if snapshot_source in ("auto", "dev"):
        remote_path = f"docs/dev/replay/{report_date}.snapshot.json"
        refs.append(
            SnapshotRef(
                label="dev-preview",
                ref="codex/dev-preview",
                remote_path=remote_path,
                url=f"https://raw.githubusercontent.com/{repo}/codex/dev-preview/{remote_path}",
            )
        )
    if snapshot_source in ("auto", "prod"):
        remote_path = f"docs/replay/{report_date}.snapshot.json"
        refs.append(
            SnapshotRef(
                label="main",
                ref="main",
                remote_path=remote_path,
                url=f"https://raw.githubusercontent.com/{repo}/main/{remote_path}",
            )
        )
    return refs


def _fetch_snapshot_text(repo: str, report_date: str, snapshot_source: str, timeout_sec: float) -> tuple[str, SnapshotRef]:
    session = requests.Session()
    errors: list[str] = []
    for ref in _candidate_snapshot_refs(repo, report_date, snapshot_source):
        try:
            response = session.get(ref.url, timeout=max(5.0, float(timeout_sec)))
        except Exception as exc:
            errors.append(f"{ref.label}: {exc}")
            continue
        if response.status_code == 404:
            continue
        if not response.ok:
            errors.append(f"{ref.label}: HTTP {response.status_code}")
            continue
        text = str(response.text or "")
        if text.strip():
            return text, ref
        errors.append(f"{ref.label}: empty body")
    detail = "; ".join(errors) if errors else "no matching snapshot URL"
    raise RuntimeError(f"Replay snapshot fetch failed for {report_date}: {detail}")


def _load_snapshot_from_text(report_date: str, snapshot_text: str) -> tuple[dict[str, list[Any]], Any, Any]:
    with tempfile.TemporaryDirectory(prefix="hf-compare-") as tmpdir:
        snapshot_path = Path(tmpdir) / f"{report_date}.snapshot.json"
        snapshot_path.write_text(snapshot_text, encoding="utf-8")
        raw_by_section, start_kst, end_kst, _summary_cache, _debug, _loaded_path = load_snapshot(
            report_date,
            _section_keys(),
            article_factory=lambda kw: main.Article(**kw),
            target=snapshot_path,
        )
        return raw_by_section, start_kst, end_kst


def _configure_hf(*, enabled: bool, token: str, model: str) -> tuple[str, bool, str]:
    prev = (
        str(getattr(main, "HF_API_TOKEN", "") or ""),
        bool(getattr(main, "HF_SEMANTIC_RERANK_ENABLED", False)),
        str(getattr(main, "HF_SEMANTIC_MODEL", "") or ""),
    )
    main.HF_API_TOKEN = str(token or "")
    main.HF_SEMANTIC_RERANK_ENABLED = bool(enabled and token)
    if model:
        main.HF_SEMANTIC_MODEL = str(model)
    return prev


def _restore_hf(prev: tuple[str, bool, str]) -> None:
    main.HF_API_TOKEN, main.HF_SEMANTIC_RERANK_ENABLED, main.HF_SEMANTIC_MODEL = prev


def _group_metric_keys(metrics: dict[str, int]) -> dict[str, int]:
    grouped: dict[str, int] = defaultdict(int)
    for key, value in (metrics or {}).items():
        base = str(key).split("|", 1)[0]
        grouped[base] += int(value or 0)
    return dict(sorted(grouped.items()))


def _run_selection_mode(
    raw_by_section: dict[str, list[Any]],
    *,
    max_items: int,
    sections: list[str],
    candidate_cap: int,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for section_key in sections:
        articles = list(raw_by_section.get(section_key, []) or [])
        if candidate_cap > 0:
            articles = sorted(articles, key=main._sort_key_major_first, reverse=True)[:candidate_cap]
        selected = main.select_top_articles(articles, section_key, max_items)
        out[section_key] = [_article_summary(article) for article in selected]
    return out


def _run_full_mode(
    raw_by_section: dict[str, list[Any]],
    start_kst: Any,
    end_kst: Any,
    sections: list[str],
) -> dict[str, list[dict[str, Any]]]:
    built = main.build_sections_from_raw(raw_by_section, start_kst, end_kst)
    return {
        section_key: [_article_summary(article) for article in (built.get(section_key, []) or [])]
        for section_key in sections
    }


def _run_once(
    *,
    snapshot_text: str,
    report_date: str,
    mode: str,
    max_items: int,
    sections: list[str],
    candidate_cap: int,
    hf_enabled: bool,
    hf_token: str,
    hf_model: str,
) -> dict[str, Any]:
    prev = _configure_hf(enabled=hf_enabled, token=hf_token, model=hf_model)
    METRICS.clear()
    try:
        raw_by_section, start_kst, end_kst = _load_snapshot_from_text(report_date, snapshot_text)
        if mode == "full":
            section_rows = _run_full_mode(raw_by_section, start_kst, end_kst, sections=sections)
        else:
            section_rows = _run_selection_mode(
                raw_by_section,
                max_items=max_items,
                sections=sections,
                candidate_cap=candidate_cap,
            )
        metrics = METRICS.snapshot()
    finally:
        METRICS.clear()
        _restore_hf(prev)

    nonzero_boost_articles = sum(
        1
        for rows in section_rows.values()
        for row in rows
        if abs(float(row.get("semantic_boost") or 0.0)) > 0.0
    )
    return {
        "snapshot_path": "<temporary>",
        "sections": section_rows,
        "metrics": metrics,
        "metrics_grouped": _group_metric_keys(metrics),
        "nonzero_boost_articles": nonzero_boost_articles,
        "hf_enabled_requested": bool(hf_enabled),
        "hf_token_present": bool(hf_token),
        "hf_model": hf_model if hf_enabled else "",
    }


def _compare_sections(
    baseline_rows: list[dict[str, Any]],
    hf_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_ids = [str(row.get("id") or "") for row in baseline_rows]
    hf_ids = [str(row.get("id") or "") for row in hf_rows]
    max_len = max(len(baseline_rows), len(hf_rows))
    slot_changes: list[dict[str, Any]] = []
    for idx in range(max_len):
        base_row = baseline_rows[idx] if idx < len(baseline_rows) else {}
        hf_row = hf_rows[idx] if idx < len(hf_rows) else {}
        if str(base_row.get("id") or "") == str(hf_row.get("id") or ""):
            continue
        slot_changes.append(
            {
                "position": idx + 1,
                "baseline_title": str(base_row.get("title") or ""),
                "hf_title": str(hf_row.get("title") or ""),
                "baseline_id": str(base_row.get("id") or ""),
                "hf_id": str(hf_row.get("id") or ""),
            }
        )

    boosted_selected = [
        {
            "title": str(row.get("title") or ""),
            "semantic_boost": float(row.get("semantic_boost") or 0.0),
            "semantic_similarity": float(row.get("semantic_similarity") or 0.0),
        }
        for row in hf_rows
        if abs(float(row.get("semantic_boost") or 0.0)) > 0.0
    ]

    return {
        "changed": baseline_ids != hf_ids,
        "baseline_ids": baseline_ids,
        "hf_ids": hf_ids,
        "slot_changes": slot_changes,
        "boosted_selected": boosted_selected,
        "boosted_selected_count": len(boosted_selected),
    }


def _build_report(args: argparse.Namespace) -> dict[str, Any]:
    snapshot_text, snapshot_ref = _fetch_snapshot_text(
        args.repo,
        args.report_date,
        args.snapshot_source,
        args.timeout_sec,
    )
    hf_token = str(args.hf_token or os.getenv("HF_TOKEN") or "").strip()
    hf_model = str(args.hf_model or os.getenv("HF_SEMANTIC_MODEL") or "intfloat/multilingual-e5-large").strip()
    target_sections = _section_keys(args.sections)

    baseline = _run_once(
        snapshot_text=snapshot_text,
        report_date=args.report_date,
        mode=args.mode,
        max_items=args.max_items,
        sections=target_sections,
        candidate_cap=args.candidate_cap,
        hf_enabled=False,
        hf_token="",
        hf_model=hf_model,
    )
    if hf_token:
        hf_run = _run_once(
            snapshot_text=snapshot_text,
            report_date=args.report_date,
            mode=args.mode,
            max_items=args.max_items,
            sections=target_sections,
            candidate_cap=args.candidate_cap,
            hf_enabled=True,
            hf_token=hf_token,
            hf_model=hf_model,
        )
    else:
        hf_run = deepcopy(baseline)
        hf_run["hf_enabled_requested"] = False
        hf_run["hf_token_present"] = False
        hf_run["hf_model"] = ""

    per_section = {
        section_key: _compare_sections(
            baseline["sections"].get(section_key, []),
            hf_run["sections"].get(section_key, []),
        )
        for section_key in target_sections
    }
    changed_sections = [key for key, diff in per_section.items() if diff.get("changed")]
    changed_slots = sum(len(diff.get("slot_changes") or []) for diff in per_section.values())

    return {
        "report_date": args.report_date,
        "mode": args.mode,
        "max_items": int(args.max_items),
        "candidate_cap": int(args.candidate_cap),
        "sections_requested": target_sections,
        "snapshot": {
            "source": snapshot_ref.label,
            "ref": snapshot_ref.ref,
            "remote_path": snapshot_ref.remote_path,
            "url": snapshot_ref.url,
        },
        "hf": {
            "token_present": bool(hf_token),
            "model": hf_model if hf_token else "",
            "baseline_metrics": baseline["metrics"],
            "baseline_metrics_grouped": baseline["metrics_grouped"],
            "run_metrics": hf_run["metrics"],
            "run_metrics_grouped": hf_run["metrics_grouped"],
            "nonzero_boost_articles": int(hf_run["nonzero_boost_articles"]),
        },
        "summary": {
            "changed_sections": changed_sections,
            "changed_section_count": len(changed_sections),
            "changed_slots": changed_slots,
        },
        "sections": per_section,
        "baseline": baseline["sections"],
        "hf_run": hf_run["sections"],
    }


def _render_text(report: dict[str, Any]) -> str:
    lines = [
        f"HF rerank compare report_date={report['report_date']} mode={report['mode']} max_items={report['max_items']} candidate_cap={report['candidate_cap']}",
        f"snapshot={report['snapshot']['source']} ref={report['snapshot']['ref']} path={report['snapshot']['remote_path']}",
        f"hf_token_present={report['hf']['token_present']} model={report['hf']['model'] or '-'}",
        f"hf_metrics={json.dumps(report['hf']['run_metrics_grouped'], ensure_ascii=False, sort_keys=True)}",
        f"changed_sections={report['summary']['changed_section_count']} changed_slots={report['summary']['changed_slots']}",
        "",
    ]
    for section_key in report.get("sections_requested", []):
        section = report["sections"][section_key]
        lines.append(
            f"[{section_key}] changed={section['changed']} boosted_selected={section['boosted_selected_count']}"
        )
        for change in section.get("slot_changes", [])[:5]:
            lines.append(
                f"  slot {change['position']}: "
                f"baseline={change['baseline_title'][:80]} | hf={change['hf_title'][:80]}"
            )
        for boosted in section.get("boosted_selected", [])[:5]:
            lines.append(
                f"  boost={boosted['semantic_boost']:.6f} sim={boosted['semantic_similarity']:.6f} "
                f"title={boosted['title'][:90]}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare replay snapshot article selection with HF reranking off/on.")
    parser.add_argument("--report-date", required=True, help="Report date in YYYY-MM-DD format.")
    parser.add_argument("--repo", default="NH-Horti/agri-news-brief")
    parser.add_argument("--snapshot-source", choices=("auto", "dev", "prod"), default="auto")
    parser.add_argument("--mode", choices=("selection", "full"), default="selection")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--candidate-cap", type=int, default=80)
    parser.add_argument("--sections", nargs="*", default=[])
    parser.add_argument("--hf-token", default="")
    parser.add_argument("--hf-model", default="")
    parser.add_argument("--timeout-sec", type=float, default=30.0)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-text", default="")
    return parser


def main_cli() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main.log.setLevel(logging.WARNING)
    parser = build_parser()
    args = parser.parse_args()
    report = _build_report(args)
    rendered = _render_text(report)

    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_text:
        Path(args.output_text).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_text).write_text(rendered, encoding="utf-8")

    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
