from __future__ import annotations

import base64
import os
import time
from typing import Any, Callable

from observability import metric_inc
from retry_utils import exponential_backoff, retry_after_or_backoff
from schemas import GithubDirItem, GithubPutRequest, ensure_dict, ensure_github_dir_items


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


def _is_large_file_response(j: JsonDict) -> bool:
    """Contents API가 본문을 비워서 돌려준 응답인지(=1MB 초과 파일) 판별."""
    if str(j.get("encoding") or "").lower() == "none":
        return True
    try:
        return int(j.get("size") or 0) > 0
    except (TypeError, ValueError):
        return False


def github_get_blob_text(
    repo: str,
    sha: str,
    token: str,
    *,
    session_factory: SessionFactory,
    log_http_error: HttpErrorLogger,
) -> str:
    """Blobs API(최대 100MB)로 본문을 받아온다. 실패해도 예외 없이 ""를 돌려준다."""
    url = f"https://api.github.com/repos/{repo}/git/blobs/{sha}"
    try:
        r = session_factory().get(url, headers=github_api_headers(token), timeout=60)
        if not r.ok:
            metric_inc("github.get.blob_error", status=str(r.status_code))
            log_http_error("[GitHub BLOB GET ERROR]", r)
            return ""
        j = ensure_dict(r.json())
        content_b64 = str(j.get("content", "") or "")
        if not content_b64:
            metric_inc("github.get.blob_empty")
            return ""
        metric_inc("github.get.blob_success")
        return base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception:
        metric_inc("github.get.blob_error", status="exception")
        return ""


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
        metric_inc("github.get.miss")
        return None, None
    if not r.ok:
        metric_inc("github.get.error", status=str(r.status_code))
        log_http_error("[GitHub GET ERROR]", r)
        r.raise_for_status()
    j = ensure_dict(r.json())
    content_b64 = str(j.get("content", "") or "")
    sha_raw = j.get("sha")
    sha = str(sha_raw) if isinstance(sha_raw, (str, int)) else None
    raw = base64.b64decode(content_b64).decode("utf-8", errors="replace") if content_b64 else ""
    # 1MB 초과 파일은 Contents API가 content=""(encoding="none")로 돌려준다.
    # 그대로 빈 문자열을 넘기면 호출부가 "파일 없음"으로 오해해 기존 내용을 덮어쓴다.
    if not raw and sha and _is_large_file_response(j):
        metric_inc("github.get.large_file")
        raw = github_get_blob_text(
            repo,
            sha,
            token,
            session_factory=session_factory,
            log_http_error=log_http_error,
        )
    metric_inc("github.get.success")
    return raw, sha


def github_list_dir(
    repo: str,
    dir_path: str,
    token: str,
    *,
    ref: str = "main",
    session_factory: SessionFactory,
    log_http_error: HttpErrorLogger,
) -> list[GithubDirItem]:
    url = f"https://api.github.com/repos/{repo}/contents/{dir_path}"
    r = session_factory().get(url, headers=github_api_headers(token), params={"ref": ref}, timeout=30)
    if r.status_code == 404:
        metric_inc("github.list.miss")
        return []
    if not r.ok:
        metric_inc("github.list.error", status=str(r.status_code))
        log_http_error("[GitHub LIST ERROR]", r)
        r.raise_for_status()
    metric_inc("github.list.success")
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

    try:
        max_try = max(2, int(os.getenv("GH_PUT_MAX_RETRIES", "4")))
    except (ValueError, TypeError):
        max_try = 4
    max_try = max(2, min(max_try, 10))

    last_resp = None
    sha_refresh_count = 0
    _MAX_SHA_REFRESHES = 2

    for attempt in range(max_try):
        try:
            r = session_factory().put(url, headers=github_api_headers(token), json=payload, timeout=40)
        except Exception as exc:
            metric_inc("github.put.retry", reason="network")
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
            metric_inc("github.put.success")
            return ensure_dict(r.json())

        last_resp = r

        if r.status_code == 409 and sha_refresh_count < _MAX_SHA_REFRESHES:
            metric_inc("github.put.conflict")
            try:
                _raw, latest_sha = github_get_file(
                    repo,
                    path,
                    token,
                    ref=branch,
                    session_factory=session_factory,
                    log_http_error=log_http_error,
                )
            except Exception as exc:
                logger.warning("[GitHub PUT] SHA refresh failed (attempt %d): %s", sha_refresh_count + 1, exc)
                latest_sha = None
            if latest_sha:
                payload["sha"] = latest_sha
                sha_refresh_count += 1
                metric_inc("github.put.conflict_refreshed")
                continue
            else:
                logger.warning("[GitHub PUT] 409 conflict but SHA refresh returned None (attempt %d)", sha_refresh_count + 1)

        if r.status_code == 429 or r.status_code in (500, 502, 503, 504):
            metric_inc("github.put.retry", reason="http", status=str(r.status_code))
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
        metric_inc("github.put.error", status=str(getattr(last_resp, "status_code", "?")))
        log_http_error("[GitHub PUT ERROR]", last_resp)
        last_resp.raise_for_status()

    metric_inc("github.put.error", status="no_response")
    raise RuntimeError("GitHub PUT failed without response")
