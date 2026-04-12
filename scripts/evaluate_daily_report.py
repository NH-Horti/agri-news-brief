from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from io_github import github_get_file, github_put_file
from report_eval import (
    build_selection_feedback_payload,
    evaluate_report,
    load_snapshot_payload,
    render_evaluation_markdown,
    render_summary_feedback_text,
    result_to_history_entry,
    write_json,
    write_text,
)


LOG = logging.getLogger("evaluate_daily_report")


def _session_factory() -> requests.Session:
    return requests.Session()


def _log_http_error(prefix: str, response: Any) -> None:
    try:
        detail = response.text
    except Exception:
        detail = "<no-body>"
    LOG.error("%s status=%s body=%s", prefix, getattr(response, "status_code", "?"), detail[:500])


def _default_output_dir() -> Path:
    return ROOT / "reports" / "evals"


def fetch_remote_text(repo: str, token: str, ref: str, remote_path: str) -> str:
    raw, _sha = github_get_file(
        repo,
        remote_path,
        token,
        ref=ref,
        session_factory=_session_factory,
        log_http_error=_log_http_error,
    )
    if raw is None:
        raise RuntimeError(f"Remote file not found: repo={repo} ref={ref} path={remote_path}")
    return raw


def _publish_text(repo: str, token: str, branch: str, remote_path: str, body: str, message: str) -> None:
    old_body, sha = github_get_file(
        repo,
        remote_path,
        token,
        ref=branch,
        session_factory=_session_factory,
        log_http_error=_log_http_error,
    )
    if old_body is not None and old_body.strip() == body.strip():
        LOG.info("Unchanged: %s", remote_path)
        return
    github_put_file(
        repo,
        remote_path,
        body,
        token,
        message,
        sha=sha,
        branch=branch,
        session_factory=_session_factory,
        logger=LOG,
        log_http_error=_log_http_error,
    )
    LOG.info("Published: %s", remote_path)


def _load_history(repo: str, token: str, branch: str, remote_path: str) -> dict[str, Any]:
    raw, _sha = github_get_file(
        repo,
        remote_path,
        token,
        ref=branch,
        session_factory=_session_factory,
        log_http_error=_log_http_error,
    )
    if not raw:
        return {"reports": []}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"reports": []}
    if not isinstance(payload, dict):
        return {"reports": []}
    reports = payload.get("reports", [])
    if not isinstance(reports, list):
        payload["reports"] = []
    return payload


def _upsert_history(history: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    reports = history.get("reports", [])
    if not isinstance(reports, list):
        reports = []
    report_date = str(entry.get("report_date", "") or "").strip()
    reports = [row for row in reports if not (isinstance(row, dict) and str(row.get("report_date", "") or "").strip() == report_date)]
    reports.append(entry)
    reports.sort(key=lambda row: str(row.get("report_date", "") or ""), reverse=True)
    history["reports"] = reports[:180]
    history["updated_at_kst"] = entry.get("generated_at_kst")
    return history


def _load_local_history(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"reports": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"reports": []}
    if not isinstance(payload, dict):
        return {"reports": []}
    if not isinstance(payload.get("reports", []), list):
        payload["reports"] = []
    return payload


def _resolve_report_date(snapshot_payload: dict[str, Any], requested: str) -> str:
    value = str(requested or "").strip()
    if value:
        return value
    return str(snapshot_payload.get("report_date", "") or "").strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a generated daily report and optionally publish eval artifacts.")
    parser.add_argument("--report-date", default="")
    parser.add_argument("--snapshot-path", required=True)
    parser.add_argument("--html-path", default="")
    parser.add_argument("--repo", default="")
    parser.add_argument("--token", default="")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--remote-html-path", default="")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--feedback-out", default="")
    parser.add_argument("--selection-feedback-out", default="")
    parser.add_argument("--publish-branch", default="")
    parser.add_argument("--publish-prefix", default="docs/evals")
    parser.add_argument("--fail-under", type=float, default=0.0)
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = build_parser().parse_args()

    snapshot_payload = load_snapshot_payload(args.snapshot_path)
    report_date = _resolve_report_date(snapshot_payload, args.report_date)
    if not report_date:
        raise RuntimeError("Could not resolve report_date from --report-date or snapshot payload.")

    html_text = ""
    if args.html_path:
        html_text = Path(args.html_path).read_text(encoding="utf-8")
    else:
        if not (args.repo and args.token):
            raise RuntimeError("--html-path is required when --repo/--token is not provided.")
        remote_html_path = args.remote_html_path or f"docs/archive/{report_date}.html"
        html_text = fetch_remote_text(args.repo, args.token, args.ref, remote_html_path)

    result = evaluate_report(report_date, html_text, snapshot_payload)
    markdown = render_evaluation_markdown(result)
    feedback_text = render_summary_feedback_text(result)
    selection_feedback_payload = build_selection_feedback_payload(result)

    output_dir = _default_output_dir()
    output_json = Path(args.output_json) if args.output_json else output_dir / f"{report_date}.json"
    output_md = Path(args.output_md) if args.output_md else output_dir / f"{report_date}.md"
    feedback_out = Path(args.feedback_out) if args.feedback_out else output_dir / "latest-feedback.txt"
    selection_feedback_out = (
        Path(args.selection_feedback_out)
        if args.selection_feedback_out
        else output_dir / "latest-selection-feedback.json"
    )
    latest_json = output_json.with_name("latest.json")
    latest_md = output_md.with_name("latest.md")
    history_out = output_json.with_name("history.json")

    write_json(output_json, result)
    write_text(output_md, markdown)
    write_text(feedback_out, feedback_text)
    write_json(selection_feedback_out, selection_feedback_payload)
    write_json(latest_json, result)
    write_text(latest_md, markdown)
    history_payload = _upsert_history(_load_local_history(history_out), result_to_history_entry(result))
    write_json(history_out, history_payload)

    if args.publish_branch:
        if not (args.repo and args.token):
            raise RuntimeError("--repo and --token are required when --publish-branch is set.")
        prefix = str(args.publish_prefix or "docs/evals").strip().strip("/")
        history_path = f"{prefix}/history.json"
        remote_history_payload = _load_history(args.repo, args.token, args.publish_branch, history_path)
        remote_history_payload = _upsert_history(remote_history_payload, result_to_history_entry(result))

        json_body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        history_body = json.dumps(remote_history_payload, ensure_ascii=False, indent=2) + "\n"

        _publish_text(args.repo, args.token, args.publish_branch, f"{prefix}/{report_date}.json", json_body, f"Update eval JSON ({report_date})")
        _publish_text(args.repo, args.token, args.publish_branch, f"{prefix}/{report_date}.md", markdown, f"Update eval summary ({report_date})")
        _publish_text(args.repo, args.token, args.publish_branch, f"{prefix}/latest.json", json_body, f"Update latest eval ({report_date})")
        _publish_text(args.repo, args.token, args.publish_branch, f"{prefix}/latest.md", markdown, f"Update latest eval summary ({report_date})")
        _publish_text(args.repo, args.token, args.publish_branch, f"{prefix}/latest-feedback.txt", feedback_text, f"Update summary feedback ({report_date})")
        _publish_text(
            args.repo,
            args.token,
            args.publish_branch,
            f"{prefix}/latest-selection-feedback.json",
            json.dumps(selection_feedback_payload, ensure_ascii=False, indent=2) + "\n",
            f"Update selection feedback ({report_date})",
        )
        _publish_text(args.repo, args.token, args.publish_branch, history_path, history_body, f"Update eval history ({report_date})")

    print(markdown)
    if args.fail_under and float(result.get("overall_score", 0.0)) < float(args.fail_under):
        LOG.error(
            "Overall score %.2f is below fail-under %.2f",
            float(result.get("overall_score", 0.0)),
            float(args.fail_under),
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
