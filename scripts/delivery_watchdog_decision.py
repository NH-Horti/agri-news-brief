from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
DELIVERY_DEADLINE = time(7, 0)
STALE_RECOVERY_CUTOFF = time(6, 30)
HARD_RECOVERY_CUTOFF = time(6, 40)


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _same_report_date(created_at: object, report_date: str) -> bool:
    parsed = _parse_timestamp(created_at)
    return bool(parsed and parsed.astimezone(KST).date().isoformat() == report_date)


def _receipt_timestamp(receipt: dict[str, Any]) -> datetime | None:
    return _parse_timestamp(receipt.get("sent_at_kst") or receipt.get("confirmed_at_kst"))


def decide_delivery_action(
    receipt: dict[str, Any],
    runs_payload: dict[str, Any],
    *,
    now: datetime,
    report_date: str,
    dry_run: bool = False,
    stale_after_minutes: int = 25,
    hard_cutoff_minimum_age: int = 10,
    recovery_limit: int = 2,
) -> dict[str, Any]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_kst = now.astimezone(KST)
    report_day = date.fromisoformat(report_date)
    deadline = datetime.combine(report_day, DELIVERY_DEADLINE, tzinfo=KST)
    stale_cutoff = datetime.combine(report_day, STALE_RECOVERY_CUTOFF, tzinfo=KST)
    hard_cutoff = datetime.combine(report_day, HARD_RECOVERY_CUTOFF, tzinfo=KST)

    receipt_status = str(receipt.get("status") or "").strip().lower()
    sent_at = _receipt_timestamp(receipt)
    if receipt_status == "success":
        on_time = sent_at <= deadline if sent_at is not None else None
        result = (
            "delivery-confirmed-on-time"
            if on_time is True
            else "delivery-confirmed-late"
            if on_time is False
            else "delivery-confirmed-time-unknown"
        )
        return {
            "result": result,
            "action": "none",
            "report_date": report_date,
            "receipt_status": receipt_status,
            "receipt_timestamp": sent_at.isoformat() if sent_at else "",
            "delivery_on_time": on_time,
            "run_id": "",
            "run_url": "",
            "run_status": "not_checked",
            "run_conclusion": "not_checked",
            "run_age_minutes": 0,
            "recovery_run_count": 0,
        }

    all_runs = runs_payload.get("workflow_runs", [])
    if not isinstance(all_runs, list):
        all_runs = []
    matching_runs = [
        row
        for row in all_runs
        if isinstance(row, dict) and _same_report_date(row.get("created_at"), report_date)
    ]
    matching_runs.sort(key=lambda row: str(row.get("created_at") or ""))
    latest = matching_runs[-1] if matching_runs else {}
    recovery_run_count = sum(
        1
        for row in matching_runs
        if "recovery=true" in str(row.get("display_title") or "")
    )
    run_status = str(latest.get("status") or "missing")
    run_conclusion = str(latest.get("conclusion") or ("pending" if latest else "missing"))
    run_created = _parse_timestamp(latest.get("created_at"))
    run_age_minutes = (
        max(0, int((now - run_created.astimezone(now.tzinfo)).total_seconds() // 60))
        if run_created is not None
        else 0
    )
    base = {
        "report_date": report_date,
        "receipt_status": receipt_status or "missing",
        "receipt_timestamp": "",
        "delivery_on_time": None,
        "run_id": str(latest.get("id") or ""),
        "run_url": str(latest.get("html_url") or ""),
        "run_status": run_status,
        "run_conclusion": run_conclusion,
        "run_age_minutes": run_age_minutes,
        "recovery_run_count": recovery_run_count,
    }

    if run_status in {"queued", "in_progress"}:
        stale = now_kst >= stale_cutoff and run_age_minutes >= stale_after_minutes
        hard_deadline_stale = now_kst >= hard_cutoff and run_age_minutes >= hard_cutoff_minimum_age
        if stale or hard_deadline_stale:
            return {**base, "result": "stale-daily-run", "action": "cancel_and_dispatch"}
        return {**base, "result": "daily-run-active", "action": "wait"}
    if dry_run:
        return {**base, "result": "delivery-missing-dry-run", "action": "none"}
    if recovery_run_count >= recovery_limit:
        return {**base, "result": "recovery-attempt-limit-reached", "action": "none"}
    return {**base, "result": "delivery-missing", "action": "dispatch"}


def _load_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide the daily briefing delivery recovery action")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--runs", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--now", default="")
    parser.add_argument("--dry-run", default="false")
    args = parser.parse_args()

    now = _parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        parser.error("--now must be an ISO-8601 timestamp")
    decision = decide_delivery_action(
        _load_json(args.receipt),
        _load_json(args.runs),
        now=now,
        report_date=args.report_date,
        dry_run=str(args.dry_run).strip().lower() in {"1", "true", "yes"},
    )
    print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
