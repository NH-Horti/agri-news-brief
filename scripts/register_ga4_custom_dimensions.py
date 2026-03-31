from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from build_admin_analytics import load_env_files


ADMIN_API_BASE = "https://analyticsadmin.googleapis.com/v1alpha"
EDIT_SCOPE = "https://www.googleapis.com/auth/analytics.edit"


@dataclass(frozen=True)
class CustomDimensionSpec:
    parameter_name: str
    display_name: str
    description: str


CUSTOM_DIMENSIONS: tuple[CustomDimensionSpec, ...] = (
    CustomDimensionSpec("page_type", "Page type", "Page category for the generated brief."),
    CustomDimensionSpec("report_date", "Report date", "Report date attached to tracked events."),
    CustomDimensionSpec("view_mode", "View mode", "Current page view mode."),
    CustomDimensionSpec("build_id", "Build ID", "Generated build identifier."),
    CustomDimensionSpec("article_id", "Article ID", "Stable article identifier."),
    CustomDimensionSpec("article_title", "Article title", "Article title at click time."),
    CustomDimensionSpec("section", "Section", "Brief section or category."),
    CustomDimensionSpec("surface", "Surface", "UI surface that emitted the event."),
    CustomDimensionSpec("target_domain", "Target domain", "Destination hostname for article clicks."),
    CustomDimensionSpec("article_rank", "Article rank", "Article rank within the rendered list."),
    CustomDimensionSpec("query", "Search query", "Submitted search query."),
    CustomDimensionSpec("query_length", "Query length", "Length of the submitted query."),
    CustomDimensionSpec("result_count", "Result count", "Search result count."),
    CustomDimensionSpec("section_filter", "Section filter", "Applied section filter in search."),
    CustomDimensionSpec("sort_mode", "Sort mode", "Applied sort mode in search."),
    CustomDimensionSpec("group_mode", "Group mode", "Grouped or flat search mode."),
    CustomDimensionSpec("from_view", "From view", "Previous view before switch."),
    CustomDimensionSpec("to_view", "To view", "Next view after switch."),
    CustomDimensionSpec("nav_type", "Navigation type", "Archive navigation trigger type."),
    CustomDimensionSpec("from_date", "From date", "Origin report date for archive navigation."),
    CustomDimensionSpec("to_date", "To date", "Destination report date for archive navigation."),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register GA4 custom dimensions required by the admin dashboard.")
    parser.add_argument("--property-id", default="", help="GA4 property id. Defaults to GA4_PROPERTY_ID.")
    parser.add_argument("--env-file", default=os.getenv("AGRI_ENV_FILE", "").strip(), help="Optional env file path(s) to load before reading GA4 settings.")
    parser.add_argument("--dry-run", action="store_true", help="Show missing dimensions without creating them.")
    parser.add_argument("--list-only", action="store_true", help="List existing and missing dimensions, then exit.")
    return parser.parse_args()


def resolve_access_token() -> str:
    direct_token = os.getenv("GA4_ACCESS_TOKEN", "").strip()
    if direct_token:
        return direct_token

    service_account_json = os.getenv("GA4_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_file = os.getenv("GA4_SERVICE_ACCOUNT_FILE", "").strip() or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if not service_account_json and not service_account_file:
        raise RuntimeError("Set GA4_SERVICE_ACCOUNT_JSON, GA4_SERVICE_ACCOUNT_FILE, GOOGLE_APPLICATION_CREDENTIALS, or GA4_ACCESS_TOKEN.")

    try:
        from google.auth.transport.requests import Request  # type: ignore[import-not-found]
        from google.oauth2 import service_account  # type: ignore[import-not-found]
    except Exception as exc:
        raise RuntimeError("google-auth is required to use service account credentials.") from exc

    info: dict[str, Any]
    if service_account_json:
        try:
            info = json.loads(service_account_json)
        except Exception as exc:
            raise RuntimeError("GA4_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc
    else:
        try:
            info = json.loads(Path(service_account_file).read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError("GA4 service account file could not be read.") from exc

    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=[EDIT_SCOPE],
    )
    credentials.refresh(Request())
    token = str(credentials.token or "").strip()
    if not token:
        raise RuntimeError("Service account token refresh returned an empty token.")
    return token


def request_json(method: str, url: str, token: str, *, json_body: dict[str, Any] | None = None, params: dict[str, str] | None = None) -> dict[str, Any]:
    response = requests.request(
        method,
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=json_body,
        params=params,
        timeout=60,
    )
    if not response.ok:
        detail = response.text.strip()
        raise RuntimeError(f"{method} {url} failed with HTTP {response.status_code}: {detail}")
    data = response.json()
    return data if isinstance(data, dict) else {}


def list_custom_dimensions(property_id: str, token: str) -> list[dict[str, Any]]:
    url = f"{ADMIN_API_BASE}/properties/{property_id}/customDimensions"
    items: list[dict[str, Any]] = []
    page_token = ""
    while True:
        params = {"pageSize": "200"}
        if page_token:
            params["pageToken"] = page_token
        payload = request_json("GET", url, token, params=params)
        batch = payload.get("customDimensions", [])
        if isinstance(batch, list):
            items.extend(item for item in batch if isinstance(item, dict))
        page_token = str(payload.get("nextPageToken") or "").strip()
        if not page_token:
            break
    return items


def create_custom_dimension(property_id: str, token: str, spec: CustomDimensionSpec) -> dict[str, Any]:
    url = f"{ADMIN_API_BASE}/properties/{property_id}/customDimensions"
    body = {
        "parameterName": spec.parameter_name,
        "displayName": spec.display_name,
        "description": spec.description,
        "scope": "EVENT",
    }
    return request_json("POST", url, token, json_body=body)


def main() -> int:
    args = parse_args()
    loaded_env = load_env_files(args.env_file)
    if loaded_env:
        print(f"[ga4-custom-dimensions] loaded env file(s): {', '.join(Path(path).name for path in loaded_env)}")

    property_id = str(args.property_id or os.getenv("GA4_PROPERTY_ID", "")).strip()
    if not property_id:
        print("[ga4-custom-dimensions] error: GA4_PROPERTY_ID is not configured.", file=sys.stderr)
        return 1

    try:
        token = resolve_access_token()
    except Exception as exc:
        print(f"[ga4-custom-dimensions] error: {exc}", file=sys.stderr)
        return 1

    try:
        existing = list_custom_dimensions(property_id, token)
    except Exception as exc:
        print(f"[ga4-custom-dimensions] error: {exc}", file=sys.stderr)
        return 1

    existing_by_parameter = {
        str(item.get("parameterName") or "").strip(): item
        for item in existing
        if str(item.get("parameterName") or "").strip()
    }

    missing = [spec for spec in CUSTOM_DIMENSIONS if spec.parameter_name not in existing_by_parameter]
    print(f"[ga4-custom-dimensions] property={property_id} existing={len(existing_by_parameter)} target={len(CUSTOM_DIMENSIONS)} missing={len(missing)}")

    for spec in CUSTOM_DIMENSIONS:
        current = existing_by_parameter.get(spec.parameter_name)
        if current:
            display_name = str(current.get("displayName") or "").strip()
            scope = str(current.get("scope") or "").strip()
            note = ""
            if display_name and display_name != spec.display_name:
                note = f" display='{display_name}'"
            if scope and scope != "EVENT":
                note += f" scope='{scope}'"
            print(f"[skip] {spec.parameter_name}{note}")
        else:
            action = "would-create" if args.dry_run or args.list_only else "create"
            print(f"[{action}] {spec.parameter_name} -> {spec.display_name}")

    if args.list_only or args.dry_run:
        return 0

    created = 0
    for spec in missing:
        try:
            create_custom_dimension(property_id, token, spec)
            created += 1
            print(f"[created] {spec.parameter_name}")
        except Exception as exc:
            print(f"[ga4-custom-dimensions] error: failed to create {spec.parameter_name}: {exc}", file=sys.stderr)
            return 1

    print(f"[ga4-custom-dimensions] done: created={created} skipped={len(CUSTOM_DIMENSIONS) - created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
