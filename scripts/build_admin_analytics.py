from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


KST = timezone(timedelta(hours=9))
DEFAULT_DAYS = 120
DEFAULT_WINDOWS = (7, 30, 90)
DATA_API_BASE = "https://analyticsdata.googleapis.com/v1beta"
_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class AnalyticsContext:
    property_id: str
    access_token: str
    start_date: str
    end_date: str


def _strip_inline_env_comment(raw: str) -> str:
    out: list[str] = []
    in_single = False
    in_double = False
    for index, char in enumerate(raw):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == "#" and not in_single and not in_double:
            prev = raw[index - 1] if index > 0 else " "
            if prev.isspace():
                break
        out.append(char)
    return "".join(out).strip()


def _unquote_env_value(raw: str) -> str:
    text = str(raw or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        body = text[1:-1]
        if text[0] == '"':
            body = (
                body.replace(r"\\", "\\")
                .replace(r"\"", '"')
                .replace(r"\n", "\n")
                .replace(r"\r", "\r")
                .replace(r"\t", "\t")
            )
        return body
    return _strip_inline_env_comment(text)


def load_env_files(raw_paths: str) -> list[str]:
    loaded_paths: list[str] = []
    seen: set[str] = set()
    for raw in [part.strip() for part in str(raw_paths or "").split(os.pathsep) if part.strip()]:
        path = Path(raw)
        if not path.is_absolute():
            path = Path.cwd() / path
        key = str(path.resolve(strict=False))
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        changed = False
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key_raw, value_raw = line.split("=", 1)
            env_key = key_raw.strip()
            if not _ENV_KEY_RE.match(env_key):
                continue
            if env_key not in os.environ:
                os.environ[env_key] = _unquote_env_value(value_raw)
                changed = True
        if changed:
            loaded_paths.append(str(path))
    return loaded_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build static admin analytics data files.")
    parser.add_argument("--output-dir", default="docs/admin/data", help="Output directory for JSON files.")
    parser.add_argument("--search-index", default="docs/search_index.json", help="Path to search index JSON.")
    parser.add_argument("--property-id", default="", help="GA4 property id.")
    parser.add_argument("--days", type=int, default=int(os.getenv("ADMIN_ANALYTICS_DAYS", str(DEFAULT_DAYS)) or DEFAULT_DAYS))
    parser.add_argument("--env-file", default=os.getenv("AGRI_ENV_FILE", "").strip(), help="Optional env file path(s) to load before reading GA4 settings.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when configuration or query warnings are present.")
    return parser.parse_args()


def today_kst() -> date:
    return datetime.now(KST).date()


def iso_date(value: date) -> str:
    return value.isoformat()


def normalize_report_date(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) == 8 and raw.isdigit():
        raw = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def to_number(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def to_int(value: Any) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: Any) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        old_raw = path.read_text(encoding="utf-8")
    except OSError:
        old_raw = None
    if old_raw == raw:
        return False
    path.write_text(raw, encoding="utf-8")
    return True


def load_search_index(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path, {"items": []})
    items = payload.get("items", []) if isinstance(payload, dict) else []
    mapping: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        article_id = str(item.get("id") or "").strip()
        if not article_id:
            continue
        mapping[article_id] = item
    return mapping


def build_empty_outputs(warnings: list[str]) -> dict[str, Any]:
    generated_at = datetime.now(KST).isoformat(timespec="seconds")
    return {
        "summary": {
            "generated_at": generated_at,
            "windows": {},
        },
        "timeseries": {
            "generated_at": generated_at,
            "daily": [],
        },
        "top_articles": {
            "generated_at": generated_at,
            "rows": [],
        },
        "navigation": {
            "generated_at": generated_at,
            "section_jump": [],
            "view_switch": [],
            "archive_nav": [],
        },
        "search_terms": {
            "generated_at": generated_at,
            "rows": [],
        },
        "health": {
            "generated_at": generated_at,
            "collection": {
                "tracking_enabled": False,
                "last_event_at": "",
                "tracking_build_id": "",
            },
            "pipeline": {
                "last_success_at": generated_at,
                "status": "warning" if warnings else "ok",
            },
            "warnings": warnings,
        },
    }


def resolve_access_token(warnings: list[str]) -> str:
    direct_token = os.getenv("GA4_ACCESS_TOKEN", "").strip()
    if direct_token:
        return direct_token

    service_account_json = os.getenv("GA4_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_file = os.getenv("GA4_SERVICE_ACCOUNT_FILE", "").strip() or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if not service_account_json and not service_account_file:
        warnings.append("GA4 credentials are not configured. Set GA4_ACCESS_TOKEN or GA4_SERVICE_ACCOUNT_JSON.")
        return ""

    try:
        from google.auth.transport.requests import Request  # type: ignore[import-not-found]
        from google.oauth2 import service_account  # type: ignore[import-not-found]
    except Exception:
        warnings.append("google-auth is not available, so service account credentials cannot be used.")
        return ""

    info: dict[str, Any] | None = None
    if service_account_json:
        try:
            info = json.loads(service_account_json)
        except Exception:
            warnings.append("GA4_SERVICE_ACCOUNT_JSON is not valid JSON.")
            return ""
    elif service_account_file:
        try:
            info = json.loads(Path(service_account_file).read_text(encoding="utf-8"))
        except Exception:
            warnings.append("GA4 service account file could not be read.")
            return ""

    try:
        credentials = service_account.Credentials.from_service_account_info(
            info or {},
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        credentials.refresh(Request())
        token = str(credentials.token or "").strip()
        if not token:
            warnings.append("GA4 service account token refresh returned an empty token.")
        return token
    except Exception as exc:
        warnings.append(f"GA4 service account auth failed: {exc}")
        return ""


def build_context(args: argparse.Namespace, warnings: list[str]) -> AnalyticsContext | None:
    property_id = str(args.property_id or os.getenv("GA4_PROPERTY_ID", "")).strip()
    if not property_id:
        warnings.append("GA4_PROPERTY_ID is not configured.")
        return None

    token = resolve_access_token(warnings)
    if not token:
        return None

    end = today_kst()
    days = max(7, min(int(args.days or DEFAULT_DAYS), 365))
    start = end - timedelta(days=days - 1)
    return AnalyticsContext(
        property_id=property_id,
        access_token=token,
        start_date=iso_date(start),
        end_date=iso_date(end),
    )


def run_report_all(
    ctx: AnalyticsContext,
    dimensions: list[str],
    metrics: list[str],
    *,
    dimension_filter: dict[str, Any] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    limit = 100000
    endpoint = f"{DATA_API_BASE}/properties/{ctx.property_id}:runReport"

    while True:
        payload: dict[str, Any] = {
            "dimensions": [{"name": name} for name in dimensions],
            "metrics": [{"name": name} for name in metrics],
            "dateRanges": [{
                "startDate": start_date or ctx.start_date,
                "endDate": end_date or ctx.end_date,
            }],
            "limit": str(limit),
            "offset": str(offset),
        }
        if dimension_filter:
            payload["dimensionFilter"] = dimension_filter

        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {ctx.access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        batch = data.get("rows", []) if isinstance(data, dict) else []
        if not isinstance(batch, list) or not batch:
            break

        for row in batch:
            if not isinstance(row, dict):
                continue
            row_obj: dict[str, Any] = {}
            dim_values = row.get("dimensionValues", []) or []
            metric_values = row.get("metricValues", []) or []
            for index, name in enumerate(dimensions):
                raw = dim_values[index]["value"] if index < len(dim_values) and isinstance(dim_values[index], dict) else ""
                row_obj[name] = raw
            for index, name in enumerate(metrics):
                raw = metric_values[index]["value"] if index < len(metric_values) and isinstance(metric_values[index], dict) else ""
                row_obj[name] = raw
            rows.append(row_obj)

        if len(batch) < limit:
            break
        offset += len(batch)

    return rows


def exact_event_filter(event_name: str) -> dict[str, Any]:
    return {
        "filter": {
            "fieldName": "eventName",
            "stringFilter": {
                "matchType": "EXACT",
                "value": event_name,
            },
        }
    }


def event_in_list_filter(event_names: list[str]) -> dict[str, Any]:
    return {
        "filter": {
            "fieldName": "eventName",
            "inListFilter": {
                "values": event_names,
            },
        }
    }


def to_iso_from_ga(value: str) -> str:
    raw = normalize_report_date(value)
    if len(raw) == 10:
        return raw
    return ""


def query_timeseries(ctx: AnalyticsContext, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        rows = run_report_all(
            ctx,
            ["date"],
            ["sessions", "activeUsers", "screenPageViews", "averageSessionDuration"],
        )
    except Exception as exc:
        warnings.append(f"Failed to query timeseries metrics: {exc}")
        return []

    by_date: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = to_iso_from_ga(str(row.get("date") or ""))
        if not day:
            continue
        by_date[day] = {
            "date": day,
            "visits": to_int(row.get("sessions")),
            "users": to_int(row.get("activeUsers")),
            "pageviews": to_int(row.get("screenPageViews")),
            "avg_engagement_sec": round(to_number(row.get("averageSessionDuration")), 2),
            "page_view_home": 0,
            "page_view_archive": 0,
        }

    try:
        page_view_rows = run_report_all(
            ctx,
            ["date", "customEvent:page_type"],
            ["eventCount"],
            dimension_filter=exact_event_filter("page_view"),
        )
        for row in page_view_rows:
            day = to_iso_from_ga(str(row.get("date") or ""))
            page_type = str(row.get("customEvent:page_type") or "").strip()
            if not day or day not in by_date:
                continue
            if page_type == "home":
                by_date[day]["page_view_home"] += to_int(row.get("eventCount"))
            elif page_type == "archive":
                by_date[day]["page_view_archive"] += to_int(row.get("eventCount"))
    except Exception as exc:
        warnings.append(f"Failed to query page_view custom dimensions: {exc}")

    return [by_date[key] for key in sorted(by_date)]


def query_article_rows(ctx: AnalyticsContext, search_index: dict[str, dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    try:
        rows = run_report_all(
            ctx,
            [
                "date",
                "customEvent:article_id",
                "customEvent:article_title",
                "customEvent:report_date",
                "customEvent:section",
                "customEvent:surface",
                "customEvent:target_domain",
            ],
            ["eventCount", "totalUsers"],
            dimension_filter=exact_event_filter("article_open"),
        )
    except Exception as exc:
        warnings.append(f"Failed to query article_open rows: {exc}")
        return []

    items: list[dict[str, Any]] = []
    for row in rows:
        day = to_iso_from_ga(str(row.get("date") or ""))
        article_id = str(row.get("customEvent:article_id") or "").strip()
        meta = search_index.get(article_id, {})
        items.append({
            "date": day,
            "article_id": article_id,
            "title": str(meta.get("title") or row.get("customEvent:article_title") or "").strip(),
            "report_date": str(meta.get("date") or row.get("customEvent:report_date") or "").strip(),
            "section": str(meta.get("section") or row.get("customEvent:section") or "").strip(),
            "surface": str(row.get("customEvent:surface") or "").strip(),
            "target_domain": str(row.get("customEvent:target_domain") or "").strip(),
            "clicks": to_int(row.get("eventCount")),
            "users": to_int(row.get("totalUsers")),
            "archive_url": str(meta.get("archive") or "").strip(),
            "source_url": str(meta.get("url") or "").strip(),
        })
    return items


def query_search_rows(ctx: AnalyticsContext, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        rows = run_report_all(
            ctx,
            [
                "date",
                "customEvent:query",
                "customEvent:section_filter",
                "customEvent:result_count",
            ],
            ["eventCount"],
            dimension_filter=exact_event_filter("search_submit"),
        )
    except Exception as exc:
        warnings.append(f"Failed to query search_submit rows: {exc}")
        return []

    return [{
        "date": to_iso_from_ga(str(row.get("date") or "")),
        "query": str(row.get("customEvent:query") or "").strip(),
        "section_filter": str(row.get("customEvent:section_filter") or "").strip(),
        "result_count": to_int(row.get("customEvent:result_count")),
        "count": to_int(row.get("eventCount")),
    } for row in rows]


def query_navigation_rows(ctx: AnalyticsContext, warnings: list[str]) -> dict[str, list[dict[str, Any]]]:
    try:
        rows = run_report_all(
            ctx,
            [
                "date",
                "eventName",
                "customEvent:section",
                "customEvent:surface",
                "customEvent:from_view",
                "customEvent:to_view",
                "customEvent:nav_type",
                "customEvent:from_date",
                "customEvent:to_date",
            ],
            ["eventCount"],
            dimension_filter=event_in_list_filter(["section_jump", "view_tab_switch", "archive_nav"]),
        )
    except Exception as exc:
        warnings.append(f"Failed to query navigation events: {exc}")
        return {
            "section_jump": [],
            "view_switch": [],
            "archive_nav": [],
        }

    section_jump: list[dict[str, Any]] = []
    view_switch: list[dict[str, Any]] = []
    archive_nav: list[dict[str, Any]] = []

    for row in rows:
        event_name = str(row.get("eventName") or "").strip()
        base = {
            "date": to_iso_from_ga(str(row.get("date") or "")),
            "count": to_int(row.get("eventCount")),
        }
        if event_name == "section_jump":
            section_jump.append({
                **base,
                "section": str(row.get("customEvent:section") or "").strip(),
                "surface": str(row.get("customEvent:surface") or "").strip(),
            })
        elif event_name == "view_tab_switch":
            view_switch.append({
                **base,
                "from_view": str(row.get("customEvent:from_view") or "").strip(),
                "to_view": str(row.get("customEvent:to_view") or "").strip(),
            })
        elif event_name == "archive_nav":
            archive_nav.append({
                **base,
                "nav_type": str(row.get("customEvent:nav_type") or "").strip(),
                "from_date": normalize_report_date(str(row.get("customEvent:from_date") or "")),
                "to_date": normalize_report_date(str(row.get("customEvent:to_date") or "")),
            })

    return {
        "section_jump": section_jump,
        "view_switch": view_switch,
        "archive_nav": archive_nav,
    }


def query_window_totals(ctx: AnalyticsContext, days: int, warnings: list[str]) -> dict[str, Any]:
    end = today_kst()
    start = end - timedelta(days=days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)

    def total_metrics(start_date: date, end_date: date) -> dict[str, Any]:
        rows = run_report_all(
            ctx,
            [],
            ["sessions", "activeUsers", "screenPageViews", "averageSessionDuration"],
            start_date=iso_date(start_date),
            end_date=iso_date(end_date),
        )
        totals = rows[0] if rows else {}
        article_rows = run_report_all(
            ctx,
            [],
            ["eventCount"],
            dimension_filter=exact_event_filter("article_open"),
            start_date=iso_date(start_date),
            end_date=iso_date(end_date),
        )
        article_clicks = to_int(article_rows[0].get("eventCount")) if article_rows else 0
        pageviews = to_int(totals.get("screenPageViews"))
        return {
            "visits": to_int(totals.get("sessions")),
            "users": to_int(totals.get("activeUsers")),
            "pageviews": pageviews,
            "article_clicks": article_clicks,
            "article_ctr": round((article_clicks / pageviews), 6) if pageviews else 0.0,
            "avg_engagement_sec": round(to_number(totals.get("averageSessionDuration")), 2),
        }

    try:
        return {
            "totals": total_metrics(start, end),
            "prev": total_metrics(prev_start, prev_end),
            "range": {
                "from": iso_date(start),
                "to": iso_date(end),
            },
        }
    except Exception as exc:
        warnings.append(f"Failed to query summary window {days}d: {exc}")
        return {
            "totals": {},
            "prev": {},
            "range": {
                "from": iso_date(start),
                "to": iso_date(end),
            },
        }


def build_outputs(ctx: AnalyticsContext | None, search_index: dict[str, dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    if ctx is None:
        return build_empty_outputs(warnings)

    generated_at = datetime.now(KST).isoformat(timespec="seconds")
    timeseries = query_timeseries(ctx, warnings)
    article_rows = query_article_rows(ctx, search_index, warnings)
    search_rows = query_search_rows(ctx, warnings)
    navigation = query_navigation_rows(ctx, warnings)

    windows: dict[str, Any] = {}
    for window in DEFAULT_WINDOWS:
        windows[str(window)] = query_window_totals(ctx, window, warnings)

    tracking_enabled = bool(article_rows or search_rows or navigation["section_jump"] or timeseries)
    last_event_candidates = [row.get("date") for row in article_rows + search_rows + navigation["section_jump"] + navigation["archive_nav"] if row.get("date")]
    last_event_at = max(last_event_candidates) if last_event_candidates else ""

    status = "ok"
    if warnings:
        status = "warning"

    return {
        "summary": {
            "generated_at": generated_at,
            "windows": windows,
        },
        "timeseries": {
            "generated_at": generated_at,
            "daily": timeseries,
        },
        "top_articles": {
            "generated_at": generated_at,
            "rows": article_rows,
        },
        "navigation": {
            "generated_at": generated_at,
            "section_jump": navigation["section_jump"],
            "view_switch": navigation["view_switch"],
            "archive_nav": navigation["archive_nav"],
        },
        "search_terms": {
            "generated_at": generated_at,
            "rows": search_rows,
        },
        "health": {
            "generated_at": generated_at,
            "collection": {
                "tracking_enabled": tracking_enabled,
                "last_event_at": last_event_at,
                "tracking_build_id": "",
            },
            "pipeline": {
                "last_success_at": generated_at,
                "status": status,
            },
            "warnings": warnings,
        },
    }


def main() -> int:
    args = parse_args()
    loaded_env = load_env_files(args.env_file)
    if loaded_env:
        print(f"[admin-analytics] loaded env file(s): {', '.join(Path(path).name for path in loaded_env)}")
    warnings: list[str] = []
    search_index = load_search_index(Path(args.search_index))
    ctx = build_context(args, warnings)
    outputs = build_outputs(ctx, search_index, warnings)

    output_dir = Path(args.output_dir)
    write_json(output_dir / "summary.json", outputs["summary"])
    write_json(output_dir / "timeseries.json", outputs["timeseries"])
    write_json(output_dir / "top_articles.json", outputs["top_articles"])
    write_json(output_dir / "navigation.json", outputs["navigation"])
    write_json(output_dir / "search_terms.json", outputs["search_terms"])
    write_json(output_dir / "health.json", outputs["health"])
    for warning in warnings:
        print(f"[admin-analytics] warning: {warning}", file=sys.stderr)
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
