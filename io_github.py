from __future__ import annotations

import base64
import os
import time
from typing import Any, Callable

from retry_utils import exponential_backoff, retry_after_or_backoff
from schemas import GithubPutRequest, ensure_dict, ensure_github_dir_items


JsonDict = dict[str, Any]
SessionFactory = Callable[[], Any]
HttpErrorLogger = Callable[[str, Any], None]
StripHtmlFn = Callable[[str], str]


def github_api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "agri-news-brief-bot",
    }


def github_get_file(
    repo: str,
    path: str,
    token: str,
    *,
    ref: str = "main",
    session_factory: SessionFactory,
    log_http_error: HttpErrorLogger,
) -> tuple[str | None, str | None]:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    r = session_factory().get(url, headers=github_api_headers(token), params={"ref": ref}, timeout=30)
    if r.status_code == 404:
        return None, None
    if not r.ok:
        log_http_error("[GitHub GET ERROR]", r)
        r.raise_for_status()
    j = ensure_dict(r.json())
    content_b64 = str(j.get("content", "") or "")
    sha_raw = j.get("sha")
    sha = str(sha_raw) if isinstance(sha_raw, (str, int)) else None
    raw = base64.b64decode(content_b64).decode("utf-8", errors="replace") if content_b64 else ""
    return raw, sha


def github_list_dir(
    repo: str,
    dir_path: str,
    token: str,
    *,
    ref: str = "main",
    session_factory: SessionFactory,
    log_http_error: HttpErrorLogger,
) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/contents/{dir_path}"
    r = session_factory().get(url, headers=github_api_headers(token), params={"ref": ref}, timeout=30)
    if r.status_code == 404:
        return []
    if not r.ok:
        log_http_error("[GitHub LIST ERROR]", r)
        r.raise_for_status()
    return ensure_github_dir_items(r.json())


def github_put_file(
    repo: str,
    path: str,
    content: str,
    token: str,
    message: str,
    *,
    sha: str | None = None,
    branch: str = "main",
    session_factory: SessionFactory,
    logger: Any,
    log_http_error: HttpErrorLogger,
    strip_html_fn: StripHtmlFn | None = None,
) -> JsonDict:
    if isinstance(content, str) and path.endswith(".html") and strip_html_fn is not None:
        content = strip_html_fn(content)

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    request_body = GithubPutRequest(
        message=message,
        content_b64=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        branch=branch,
        sha=sha,
    )
    payload: JsonDict = request_body.to_request_json()

    max_try = max(2, int(os.getenv("GH_PUT_MAX_RETRIES", "4")))
    max_try = max(2, min(max_try, 10))

    last_resp = None
    refreshed_sha = False

    for attempt in range(max_try):
        try:
            r = session_factory().put(url, headers=github_api_headers(token), json=payload, timeout=40)
        except Exception as exc:
            backoff = exponential_backoff(attempt, base=0.8, cap=20.0, jitter=0.4)
            logger.warning(
                "[GitHub PUT] transient network error (attempt %d/%d): %s -> sleep %.1fs",
                attempt + 1,
                max_try,
                exc,
                backoff,
            )
            time.sleep(backoff)
            continue

        if r.ok:
            return ensure_dict(r.json())

        last_resp = r

        if r.status_code == 409 and not refreshed_sha:
            try:
                _raw, latest_sha = github_get_file(
                    repo,
                    path,
                    token,
                    ref=branch,
                    session_factory=session_factory,
                    log_http_error=log_http_error,
                )
            except Exception:
                latest_sha = None
            if latest_sha:
                payload["sha"] = latest_sha
                refreshed_sha = True
                continue

        if r.status_code == 429 or r.status_code in (500, 502, 503, 504):
            backoff = retry_after_or_backoff(r.headers, attempt, base=0.8, cap=20.0, jitter=0.4)
            logger.warning(
                "[GitHub PUT] transient HTTP %s (attempt %d/%d) -> sleep %.1fs",
                r.status_code,
                attempt + 1,
                max_try,
                backoff,
            )
            time.sleep(backoff)
            continue

        break

    if last_resp is not None:
        log_http_error("[GitHub PUT ERROR]", last_resp)
        last_resp.raise_for_status()
    raise RuntimeError("GitHub PUT failed without response")