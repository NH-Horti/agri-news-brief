from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main
from report_eval import BRIEFING_SURFACE, evaluate_report, parse_report_html


SECTION_KEYS = ("supply", "policy", "dist", "pest")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected an object in {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _article_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    raw_by_section = snapshot.get("raw_by_section", {})
    if not isinstance(raw_by_section, dict):
        raise ValueError("Snapshot is missing raw_by_section")
    for rows in raw_by_section.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for value in (row.get("canon_url"), row.get("originallink"), row.get("link")):
                raw_url = str(value or "").strip()
                if not raw_url:
                    continue
                index.setdefault(raw_url, row)
                canonical = main.canonicalize_url(raw_url)
                if canonical:
                    index.setdefault(canonical, row)
    return index


def _build_sections(
    manifest: dict[str, Any], snapshot: dict[str, Any]
) -> dict[str, list[main.Article]]:
    source_index = _article_index(snapshot)
    manifest_sections = manifest.get("sections", {})
    if not isinstance(manifest_sections, dict):
        raise ValueError("Manifest is missing sections")

    selected: dict[str, list[main.Article]] = {}
    used_links: set[str] = set()
    for section in SECTION_KEYS:
        rows = manifest_sections.get(section, [])
        if not isinstance(rows, list) or len(rows) != 5:
            raise ValueError(f"Curated section {section} must contain exactly five cards")
        articles: list[main.Article] = []
        for position, choice in enumerate(rows, start=1):
            if not isinstance(choice, dict):
                raise ValueError(f"Invalid curated row in {section}")
            requested_url = str(choice.get("url") or "").strip()
            canonical = main.canonicalize_url(requested_url)
            source = source_index.get(requested_url) or source_index.get(canonical)
            if source is None:
                raise ValueError(f"Curated source is not present in the replay snapshot: {requested_url}")
            identity = str(source.get("norm_key") or canonical or requested_url)
            if identity in used_links:
                raise ValueError(f"Duplicate curated story: {requested_url}")
            used_links.add(identity)

            article = main.Article(**main._replay_article_dict_to_kwargs(source))
            article.section = section
            article.forced_section = section
            article.title = str(choice.get("title") or article.title).strip()
            article.title_key = main.norm_title_key(article.title)
            article.summary = str(choice.get("summary") or "").strip()
            article.is_core = bool(choice.get("is_core"))
            article.selection_stage = (
                "manual_editorial_recovery_core"
                if article.is_core
                else "manual_editorial_recovery_tail"
            )
            article.selection_note = f"curated_2026_07_28_position_{position}"
            article.selection_fit_score = max(float(article.selection_fit_score or 0.0), 5.0)
            article.score = max(float(article.score or 0.0), 50.0 - position)
            if len(article.summary) < 55:
                raise ValueError(f"Curated summary is too short: {article.title}")
            articles.append(article)
        if sum(1 for article in articles if article.is_core) != 3:
            raise ValueError(f"Curated section {section} must contain exactly three core cards")
        selected[section] = articles
    return selected


def _archive_dates(docs_root: Path, report_date: str) -> list[str]:
    dates = {report_date}
    for path in (docs_root / "archive").glob("*.html"):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem):
            dates.add(path.stem)
    return sorted(dates, reverse=True)


def _preserve_ga4_measurement_id(index_path: Path) -> None:
    if main.GA4_MEASUREMENT_ID or not index_path.exists():
        return
    existing_index = index_path.read_text(encoding="utf-8")
    match = re.search(r"googletagmanager\.com/gtag/js\?id=([A-Z0-9-]+)", existing_index)
    if match:
        main.GA4_MEASUREMENT_ID = match.group(1)


def _clean_generated_html(html_text: str) -> str:
    return "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"


def render_curated_briefing(manifest_path: Path, repo_root: Path) -> Path:
    manifest = _load_json(manifest_path)
    report_date = str(manifest.get("report_date") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_date):
        raise ValueError("Manifest report_date must be YYYY-MM-DD")
    snapshot_path = repo_root / str(manifest.get("source_snapshot") or "")
    snapshot = _load_json(snapshot_path)
    if str(snapshot.get("report_date") or "") != report_date:
        raise ValueError("Manifest and snapshot dates do not match")

    window = snapshot.get("window", {})
    if not isinstance(window, dict):
        raise ValueError("Snapshot is missing its collection window")
    start_kst = datetime.fromisoformat(str(window.get("start_kst")))
    end_kst = datetime.fromisoformat(str(window.get("end_kst")))
    docs_root = repo_root / "docs"
    configured_ga4 = str(manifest.get("ga4_measurement_id") or "").strip()
    if configured_ga4:
        main.GA4_MEASUREMENT_ID = configured_ga4
    _preserve_ga4_measurement_id(docs_root / "index.html")
    dates_desc = _archive_dates(docs_root, report_date)
    site_path = str(manifest.get("site_path") or "").strip()
    if not site_path:
        raise ValueError("Manifest site_path is required")
    sections = _build_sections(manifest, snapshot)
    html_text = _clean_generated_html(main.render_daily_page(
        report_date,
        start_kst,
        end_kst,
        sections,
        dates_desc,
        site_path,
    ))

    briefing_rows = [
        row for row in parse_report_html(html_text) if row.surface == BRIEFING_SURFACE
    ]
    section_counts = {
        section: sum(1 for row in briefing_rows if row.section == section)
        for section in SECTION_KEYS
    }
    core_counts = {
        section: sum(1 for row in briefing_rows if row.section == section and row.is_core)
        for section in SECTION_KEYS
    }
    if len(briefing_rows) != 20 or any(count != 5 for count in section_counts.values()):
        raise RuntimeError(
            f"Render finalization changed the curated 20-card edition: {section_counts}"
        )
    if any(count < 2 for count in core_counts.values()):
        raise RuntimeError(f"Render finalization removed required core coverage: {core_counts}")

    deterministic = evaluate_report(report_date, html_text, snapshot)
    operational_score = float(deterministic.get("operational_score", 0.0) or 0.0)
    reader_score = float(deterministic.get("reader_quality_score", 0.0) or 0.0)
    if operational_score < 89.0 or reader_score < 89.0:
        raise RuntimeError(
            f"Curated edition failed deterministic recovery floors: operational={operational_score}, reader={reader_score}"
        )

    archive_path = docs_root / "archive" / f"{report_date}.html"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(html_text, encoding="utf-8")

    index_html = _clean_generated_html(
        main.render_index_page({"dates": dates_desc}, site_path)
    )
    (docs_root / "index.html").write_text(index_html, encoding="utf-8")
    _write_json(
        docs_root / "archive_manifest.json",
        {
            "version": 1,
            "updated_at_kst": datetime.now(main.KST).isoformat(timespec="seconds"),
            "dates": dates_desc,
        },
    )
    _write_json(repo_root / ".agri_archive.json", {"dates": sorted(dates_desc)})

    audit_path = docs_root / "evals" / f"{report_date}-curated-recovery.json"
    _write_json(
        audit_path,
        {
            "report_date": report_date,
            "status": "manual_editorial_recovery",
            "generated_at_kst": datetime.now(main.KST).isoformat(timespec="seconds"),
            "recovery_reason": manifest.get("recovery_reason"),
            "review_checks": manifest.get("review_checks", {}),
            "section_counts": section_counts,
            "core_counts": core_counts,
            "operational_score": operational_score,
            "reader_quality_score": reader_score,
            "scores": deterministic.get("scores", {}),
            "counts": deterministic.get("counts", {}),
            "selected": manifest.get("sections", {}),
        },
    )
    return archive_path


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="Render an audited, manually curated recovery briefing")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    output_path = render_curated_briefing(args.manifest.resolve(), args.repo_root.resolve())
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
