from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable

from observability import metric_inc
from retry_utils import exponential_backoff, retry_after_or_backoff
from schemas import NaverSearchParams, NaverSearchResponse, ensure_naver_response


SessionFactory = Callable[[], Any]
ThrottleFn = Callable[[], None]


@dataclass(frozen=True)
class NaverClientConfig:
    client_id: str
    client_secret: str
    max_retries: int = 3
    backoff_max_sec: float = 12.0


def _require_creds(cfg: NaverClientConfig) -> None:
    if not cfg.client_id or not cfg.client_secret:
        metric_inc("collector.credentials_missing")
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set")


def _naver_search(
    endpoint: str,
    *,
    cfg: NaverClientConfig,
    query: str,
    display: int,
    start: int,
    sort: str,
    session_factory: SessionFactory,
    throttle_fn: ThrottleFn,
    logger: Any,
    log_http_error: Callable[[str, Any], None],
    log_prefix: str,
) -> NaverSearchResponse:
    _require_creds(cfg)

    url = f"https://openapi.naver.com/v1/search/{endpoint}.json"
    headers = {"X-Naver-Client-Id": cfg.client_id, "X-Naver-Client-Secret": cfg.client_secret}
    params = NaverSearchParams(query=query, display=display, start=start, sort=sort).to_request_params()

    retries = max(1, int(cfg.max_retries or 1))
    last_err = None

    for attempt in range(retries):
        try:
            throttle_fn()
            r = session_factory().get(url, headers=headers, params=params, timeout=25)

            data: NaverSearchResponse
            try:
                data = ensure_naver_response(r.json())
            except Exception:
                data = {"items": []}

            is_rate = (r.status_code == 429) or (str(data.get("errorCode", "")) == "012")
            if r.ok and not is_rate:
                metric_inc("collector.success", endpoint=endpoint)
                return data

            if is_rate:
                metric_inc("collector.retry", endpoint=endpoint, reason="rate_limit")
                backoff = retry_after_or_backoff(
                    r.headers,
                    attempt,
                    base=1.0,
                    cap=float(cfg.backoff_max_sec),
                    jitter=0.4,
                )
                msg = data.get("errorMessage") or data.get("message")
                logger.warning(
                    "%s rate-limited (attempt %d/%d). sleep %.1fs. %s",
                    log_prefix,
                    attempt + 1,
                    retries,
                    backoff,
                    (msg or ""),
                )
                time.sleep(backoff)
                continue

            if not r.ok:
                metric_inc("collector.http_error", endpoint=endpoint, status=str(r.status_code))
                log_http_error(f"{log_prefix} ERROR", r)
                r.raise_for_status()

            return {"items": []}

        except Exception as e:
            last_err = e
            metric_inc("collector.retry", endpoint=endpoint, reason="exception")
            backoff = exponential_backoff(attempt, base=1.0, cap=float(cfg.backoff_max_sec), jitter=0.4)
            logger.warning(
                "%s transient error (attempt %d/%d): %s -> sleep %.1fs",
                log_prefix,
                attempt + 1,
                retries,
                e,
                backoff,
            )
            time.sleep(backoff)

    metric_inc("collector.giveup", endpoint=endpoint)
    logger.error("%s giving up after retries: query=%s (last=%s)", log_prefix, query, last_err)
    return {"items": []}


def naver_news_search(
    *,
    cfg: NaverClientConfig,
    query: str,
    display: int = 40,
    start: int = 1,
    sort: str = "date",
    session_factory: SessionFactory,
    throttle_fn: ThrottleFn,
    logger: Any,
    log_http_error: Callable[[str, Any], None],
) -> NaverSearchResponse:
    return _naver_search(
        "news",
        cfg=cfg,
        query=query,
        display=display,
        start=start,
        sort=sort,
        session_factory=session_factory,
        throttle_fn=throttle_fn,
        logger=logger,
        log_http_error=log_http_error,
        log_prefix="[NAVER]",
    )


def naver_web_search(
    *,
    cfg: NaverClientConfig,
    query: str,
    display: int = 10,
    start: int = 1,
    sort: str = "date",
    session_factory: SessionFactory,
    throttle_fn: ThrottleFn,
    logger: Any,
    log_http_error: Callable[[str, Any], None],
) -> NaverSearchResponse:
    # Keep behavior aligned with news search for consistency.
    return _naver_search(
        "webkr",
        cfg=cfg,
        query=query,
        display=display,
        start=start,
        sort=sort,
        session_factory=session_factory,
        throttle_fn=throttle_fn,
        logger=logger,
        log_http_error=log_http_error,
        log_prefix="[NAVER-WEB]",
    )


def naver_news_search_paged(
    *,
    cfg: NaverClientConfig,
    query: str,
    display: int = 50,
    pages: int = 1,
    sort: str = "date",
    session_factory: SessionFactory,
    throttle_fn: ThrottleFn,
    logger: Any,
    log_http_error: Callable[[str, Any], None],
) -> NaverSearchResponse:
    pages = max(1, int(pages or 1))
    display = max(1, int(display or 1))

    items: list[dict[str, Any]] = []
    last_meta: NaverSearchResponse = {"items": []}

    for i in range(pages):
        st = 1 + (i * display)
        data = naver_news_search(
            cfg=cfg,
            query=query,
            display=display,
            start=st,
            sort=sort,
            session_factory=session_factory,
            throttle_fn=throttle_fn,
            logger=logger,
            log_http_error=log_http_error,
        )
        last_meta = data
        chunk = last_meta.get("items", []) or []
        if not chunk:
            break
        items.extend([dict(x) for x in chunk])
        if len(chunk) < display:
            break

    metric_inc("collector.paged_calls", endpoint="news", pages=str(pages))
    metric_inc("collector.paged_items", endpoint="news", value=len(items))

    out = dict(last_meta)
    out["items"] = items
    return ensure_naver_response(out)

