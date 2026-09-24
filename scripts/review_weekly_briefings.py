"""Final offline weekly comparison: one replay per date, never a paid API call.

Run only after code changes and tests are complete. A nonempty output directory
is refused to prevent accidental repeat runs or overwriting reviewed evidence.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def offline_env(day: str, output: Path) -> dict[str, str]:
    return {
        "LOCAL_DRY_RUN": "true", "LOCAL_OUTPUT_DIR": str(output),
        "FORCE_REPORT_DATE": day, "FORCE_RUN_ANYDAY": "true",
        "MAINTENANCE_SEND_KAKAO": "false", "REPLAY_ALLOW_OPENAI": "false",
        "REPLAY_WRITE_SNAPSHOT": "false", "HF_SEMANTIC_RERANK_ENABLED": "false",
        "HF_TOKEN": "", "OPENAI_API_KEY": "", "GH_TOKEN": "", "GITHUB_TOKEN": "",
        "KAKAO_REST_API_KEY": "", "KAKAO_REFRESH_TOKEN": "",
        "SELECTION_FEEDBACK_PATH": "", "OPENAI_SUMMARY_FEEDBACK_PATH": "",
        "PLACEMENT_ONLY": "false", "DEBUG_REPORT": "0", "DEBUG_REPORT_WRITE_JSON": "0",
        "REPLAY_SNAPSHOT_PATH": str(ROOT / "docs/replay" / f"{day}.snapshot.json"),
        "PYTHONIOENCODING": "utf-8",
    }


def review_day(day: str, output: Path) -> None:
    os.environ.update(offline_env(day, output))
    attempts: list[str] = []

    def deny_network(*args, **kwargs):
        attempts.append("blocked")
        raise RuntimeError("Weekly final review is offline; network is disabled")

    # Even an accidentally enabled API integration cannot incur a charge.
    with patch.object(socket.socket, "connect", deny_network), patch.object(socket, "create_connection", deny_network):
        import main
        import report_eval
        snapshot_path = Path(os.environ["REPLAY_SNAPSHOT_PATH"])
        snapshot = report_eval.load_snapshot_payload(snapshot_path)
        original_html = (ROOT / "docs/archive" / f"{day}.html").read_text(encoding="utf-8")
        baseline = report_eval.evaluate_report(day, original_html, snapshot)
        write_json(output / "before.json", baseline)
        # Use only the historical snapshot cache, not summaries/feedback from
        # later dates in the working tree. The replay rescoring path is unchanged.
        with patch.object(main, "load_summary_cache", return_value={}):
            sections, _cache, start, end = main._build_sections_for_report(
                "NH-Horti/agri-news-brief", "", day,
                datetime.min.replace(tzinfo=main.KST), datetime.min.replace(tzinfo=main.KST),
                allow_openai=False, replay_snapshot=True,
            )
        main._finalize_sections_for_render(sections)
        rebuilt_html = main.render_daily_page(day, start, end, sections, [day], "/agri-news-brief")
        (output / "briefing.html").write_text(rebuilt_html, encoding="utf-8")
        after = report_eval.evaluate_report(day, rebuilt_html, snapshot)
        write_json(output / "after.json", after)
        (output / "after.md").write_text(report_eval.render_evaluation_markdown(after), encoding="utf-8")
        saved = json.loads((ROOT / "docs/evals" / f"{day}.json").read_text(encoding="utf-8"))

        def titles(text):
            return [{"section": a.section, "title": a.title, "is_core": a.is_core, "href": a.href}
                    for a in report_eval.parse_report_html(text) if a.surface == report_eval.BRIEFING_SURFACE]

        result = {
            "date": day, "saved_score": saved["overall_score"],
            "saved_editorial": {k: saved.get("editorial", {}).get(k) for k in ("status", "score", "reason")},
            "before_score": baseline["overall_score"], "after_score": after["overall_score"],
            "before_cards": titles(original_html), "after_cards": titles(rebuilt_html),
            "before_metrics": baseline["metrics"], "after_metrics": after["metrics"],
            "snapshot_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
            "original_html_sha256": hashlib.sha256(original_html.encode()).hexdigest(),
            "network_attempts": len(attempts), "paid_calls": 0,
            "replay_runs": 1, "deterministic_evaluations": 2,
            "new_editorial_evaluation": "not_run_offline",
        }
        write_json(output / "comparison.json", result)
        if attempts:
            raise RuntimeError(f"Offline review blocked {len(attempts)} network attempts; inspect the log")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--finalize", action="store_true", help="Run the final offline comparison after tests")
    parser.add_argument("--worker-date", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_date:
        review_day(args.worker_date, args.output.resolve())
        return 0
    if not args.finalize or not args.start or not args.end or args.start > args.end:
        parser.error("--finalize and an ordered --start/--end range are required")
    days = [args.start + timedelta(days=i) for i in range((args.end - args.start).days + 1)]
    days = [d.isoformat() for d in days if d.weekday() < 5]
    if not days:
        parser.error("The range contains no weekdays")
    for day in days:
        for relative in (f"docs/replay/{day}.snapshot.json", f"docs/archive/{day}.html", f"docs/evals/{day}.json"):
            if not (ROOT / relative).is_file():
                parser.error(f"Missing historical input: {relative}")
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Output directory is nonempty; reuse its results instead of repeating the final review")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"dates": days, "status": "running", "mode": "offline_snapshot_replay",
                "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(ROOT.glob("*.py"))}, "results": []}
    write_json(output / "manifest.json", manifest)
    for day in days:
        day_output = output / day
        day_output.mkdir()
        print(f"Final replay and comparison: {day}", flush=True)
        with (day_output / "run.log").open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker-date", day, "--output", str(day_output)],
                cwd=ROOT, env={**os.environ, **offline_env(day, day_output)}, stdout=log, stderr=subprocess.STDOUT,
            )
        if completed.returncode:
            manifest.update(status="failed", failed_date=day)
            write_json(output / "manifest.json", manifest)
            raise RuntimeError(f"Review failed for {day}: {day_output / 'run.log'}")
        row = json.loads((day_output / "comparison.json").read_text(encoding="utf-8"))
        manifest["results"].append({k: row[k] for k in ("date", "saved_score", "before_score", "after_score", "paid_calls", "network_attempts")})
        write_json(output / "manifest.json", manifest)
    manifest["status"] = "complete"
    write_json(output / "manifest.json", manifest)
    print(json.dumps(manifest["results"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
