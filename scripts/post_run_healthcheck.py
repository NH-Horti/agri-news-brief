#!/usr/bin/env python3
"""Post-run deployment healthcheck for GitHub Actions.

Checks:
- Required files exist on target content branch.
- Optional URL host/path constraints.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def _fail(msg: str) -> None:
    print(f"[HEALTHCHECK] ERROR: {msg}")
    raise SystemExit(1)


def _build_headers(token: str) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "agri-news-brief-healthcheck",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _github_file_exists(repo: str, token: str, ref: str, path: str) -> bool:
    safe_path = "/".join([p for p in path.replace("\\", "/").split("/") if p and p != "."])
    encoded_path = urllib.parse.quote(safe_path)
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={urllib.parse.quote(ref)}"
    req = urllib.request.Request(url, headers=_build_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            return isinstance(payload, dict) and str(payload.get("type", "")) == "file"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        _fail(f"GitHub API HTTP {exc.code} while checking '{safe_path}'")
    except Exception as exc:  # pragma: no cover - defensive
        _fail(f"GitHub API error while checking '{safe_path}': {exc}")
    return False


def _validate_url(url: str, expected_host: str, expected_path_prefix: str) -> None:
    if not url:
        return

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        _fail(f"Invalid URL: {url}")

    if expected_host and (parsed.hostname or "").lower() != expected_host.lower():
        _fail(
            f"URL host mismatch. expected={expected_host}, got={(parsed.hostname or '').lower()}, url={url}"
        )

    if expected_path_prefix:
        prefix = expected_path_prefix if expected_path_prefix.startswith("/") else f"/{expected_path_prefix}"
        if not parsed.path.startswith(prefix):
            _fail(f"URL path mismatch. expected_prefix={prefix}, got={parsed.path}, url={url}")



def main() -> None:
    repo = _env("GITHUB_REPOSITORY")
    token = _env("GITHUB_TOKEN") or _env("GH_TOKEN")
    ref = _env("HEALTHCHECK_CONTENT_REF", "main")

    expected_files_raw = _env("HEALTHCHECK_EXPECTED_FILES")
    expected_files = [x.strip() for x in expected_files_raw.split(",") if x.strip()]
    if not repo:
        _fail("GITHUB_REPOSITORY is required")
    if not token:
        _fail("GITHUB_TOKEN or GH_TOKEN is required")
    if not expected_files:
        _fail("HEALTHCHECK_EXPECTED_FILES is required")

    base_url = _env("HEALTHCHECK_BASE_URL")
    rel_path = _env("HEALTHCHECK_URL_REL_PATH")
    expected_url = _env("HEALTHCHECK_EXPECTED_URL")
    if not expected_url and base_url:
        if rel_path:
            expected_url = f"{base_url.rstrip('/')}/{rel_path.lstrip('/')}"
        else:
            expected_url = base_url

    _validate_url(
        expected_url,
        expected_host=_env("HEALTHCHECK_EXPECTED_HOST"),
        expected_path_prefix=_env("HEALTHCHECK_EXPECTED_PATH_PREFIX"),
    )

    missing: list[str] = []
    for path in expected_files:
        if _github_file_exists(repo, token, ref, path):
            print(f"[HEALTHCHECK] OK file exists: {path} (ref={ref})")
        else:
            missing.append(path)

    if missing:
        _fail(f"Missing expected files on ref '{ref}': {', '.join(missing)}")

    if expected_url:
        print(f"[HEALTHCHECK] OK URL validated: {expected_url}")


if __name__ == "__main__":
    main()
