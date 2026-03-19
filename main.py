# -*- coding: utf-8 -*-
"""
agri-news-brief main.py (production)

✅ 코드 작동 요약 (운영/실행 흐름)

- GitHub Actions에서 KST 기준 매일 실행되며(스케줄/수동), 실행 윈도우(기본 24h) 내 기사를 수집합니다.
- Naver News Search API로 섹션/키워드별 쿼리를 생성하고, 페이지네이션(MAX_PAGES_PER_QUERY)까지 순회하며 기사 후보를 모읍니다.
- URL/언론사명 정규화, 섹션 내/전체 중복 제거(사건키), UX 필터(오탐·광고·시위/보이콧 등) 적용 후 점수화하여 섹션별 상위 기사만 선정합니다.
- OpenAI 요약은 배치 분할 + 재시도 + 캐시를 적용해 비용/실패율을 줄이고, 기사별 요약을 안정적으로 채웁니다.
- 결과로 HTML 브리핑을 빌드하여 docs/archive/YYYY-MM-DD.html 및 docs/index.html을 업데이트하고, 아카이브 링크 404를 방지합니다.
- 상태/메타(예: .agri_state.json, manifest 등)는 레포에 저장되어 전날 fallback 및 재실행 시 일관성을 유지합니다.
- 카카오톡 메시지는 섹션별 핵심 2개 중심으로 구성하여 전송하며, 실패 시(옵션) 전체 워크플로우 실패를 막는 fail-open 동작이 가능합니다.

주요 ENV: NAVER_CLIENT_ID/SECRET, OPENAI_API_KEY/OPENAI_MODEL(및 MAX_OUTPUT_TOKENS/REASONING_EFFORT), KAKAO_REST_API_KEY/REFRESH_TOKEN, FORCE_RUN_ANYDAY 등
"""

import os
import re

def _strip_swipe_hint_blocks(html: str) -> str:
    """Remove the swipe hint ('좌우 스와이프로 날짜 이동') from HTML."""
    if not html:
        return html
    if ("스와이프로" not in html) and ("swipeHint" not in html):
        return html
    html2 = html
    html2 = re.sub(r'(?is)\s*<div[^>]*(?:id|class)=["\']swipeHint[^"\']*["\'][^>]*>.*?</div>\s*', '\n', html2)
    html2 = re.sub(r'(?is)\s*<div[^>]*>.*?좌우\s*스와이프로\s*날짜\s*이동.*?</div>\s*', '\n', html2)
    html2 = re.sub(r'(?is)\s*<div[^>]*>.*?스와이프로\s*날짜\s*이동.*?</div>\s*', '\n', html2)
    return html2

import json
import base64
import html
import difflib
import logging
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, date, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Sequence, TypedDict
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, quote

import requests  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
import threading

from collector import (
    NaverClientConfig,
    naver_news_search as _collector_naver_news_search,
    naver_news_search_paged as _collector_naver_news_search_paged,
    naver_web_search as _collector_naver_web_search,
)
from io_github import (
    github_api_headers as _io_github_api_headers,
    github_get_file as _io_github_get_file,
    github_list_dir as _io_github_list_dir,
    github_put_file as _io_github_put_file,
)
from orchestrator import OrchestratorContext, OrchestratorHandlers, execute_orchestration
from ranking import sort_key_major_first as _ranking_sort_key_major_first
from retry_utils import exponential_backoff, retry_after_or_backoff
from schemas import GithubDirItem, NaverSearchResponse
from ux_patch import build_archive_ux_html

JsonDict = dict[str, Any]


SectionConfig = dict[str, Any]


SummaryCacheEntry = dict[str, str]


# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agri-brief")

# -----------------------------
# Log sanitization (secrets / huge bodies)
# -----------------------------
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'("access_token"\s*:\s*")[^"]+(")', re.I), r'\1***\2'),
    (re.compile(r'("refresh_token"\s*:\s*")[^"]+(")', re.I), r'\1***\2'),
    (re.compile(r'("client_secret"\s*:\s*")[^"]+(")', re.I), r'\1***\2'),
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-_.]+', re.I), r'\1***'),
]

def _safe_body(text: str, limit: int = 500) -> str:
    s = (text or "").strip()
    for pat, rep in _SECRET_PATTERNS:
        try:
            s = pat.sub(rep, s)
        except Exception:
            pass
    if len(s) > limit:
        s = s[:limit] + "…(truncated)"
    return s

def _log_http_error(prefix: str, r: requests.Response) -> None:
    try:
        body = _safe_body(getattr(r, "text", ""), limit=500)
    except Exception:
        body = "(unavailable)"
    try:
        url = getattr(r, "url", "")
    except Exception:
        url = ""
    log.error("%s status=%s url=%s body=%s", prefix, getattr(r, "status_code", "?"), url, body)

# -----------------------------
# Manifest normalization (defensive)
# -----------------------------
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _normalize_manifest(manifest: object | None) -> JsonDict:
    """Normalize an archive manifest dict.

    Historically, various parts of this project expect a dict with a 'dates' list.
    This helper keeps backward compatibility and prevents crashes if the manifest
    is missing/invalid.
    """
    if manifest is None:
        manifest = {}
    if not isinstance(manifest, dict):
        manifest = {}
    dates = manifest.get("dates", [])
    if not isinstance(dates, list):
        dates = []
    clean = []
    seen = set()
    for d in dates:
        if not isinstance(d, str):
            continue
        d = d.strip()
        if not _ISO_DATE_RE.match(d):
            continue
        if d in seen:
            continue
        seen.add(d)
        clean.append(d)
    out: JsonDict = dict(manifest)
    out["dates"] = clean
    out["count"] = len(clean)
    # optional metadata
    if "version" not in out:
        out["version"] = 1
    return out

# -----------------------------
# HTTP session
# -----------------------------
SESSION = requests.Session()
_SESSION_LOCAL = threading.local()

def _configure_session(s: requests.Session) -> requests.Session:
    """Configure a Session once: connection pooling + light retries for GET/HEAD."""
    if getattr(s, "_agri_configured", False):
        return s
    retry = Retry(
        total=int(os.getenv("HTTP_RETRY_TOTAL", "3")),
        connect=int(os.getenv("HTTP_RETRY_CONNECT", "3")),
        read=int(os.getenv("HTTP_RETRY_READ", "3")),
        backoff_factor=float(os.getenv("HTTP_RETRY_BACKOFF", "0.3")),
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD", "OPTIONS"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    try:
        s.mount("https://", adapter)
        s.mount("http://", adapter)
    except Exception:
        pass
    try:
        s.headers.update({"User-Agent": "agri-news-brief-bot"})
    except Exception:
        pass
    setattr(s, "_agri_configured", True)
    return s

_configure_session(SESSION)

def http_session() -> requests.Session:
    """Thread-safe session accessor.
    - When NAVER_MAX_WORKERS>1, use per-thread Session to avoid cross-thread issues.
    """
    try:
        if int(os.getenv("NAVER_MAX_WORKERS", "1")) > 1:
            s = getattr(_SESSION_LOCAL, "session", None)
            if s is None:
                s = requests.Session()
                _configure_session(s)
                _SESSION_LOCAL.session = s
            return s
    except Exception:
        pass
    return SESSION


# -----------------------------
# Config
# -----------------------------
KST = timezone(timedelta(hours=9))
REPORT_HOUR_KST = int(os.getenv("REPORT_HOUR_KST", os.getenv("RUN_HOUR_KST", "7")))
WINDOW_MIN_HOURS = int(os.getenv("WINDOW_MIN_HOURS", "0"))  # 최소 후보 수집 윈도우(시간, 기본 0=윈도우 확장 없음)
CROSSDAY_DEDUPE_DAYS = int(os.getenv("CROSSDAY_DEDUPE_DAYS", "7"))  # 최근 N일 URL/사건키 중복 방지
CROSSDAY_DEDUPE_ENABLED_ENV = (os.getenv("CROSSDAY_DEDUPE_ENABLED", "true").strip().lower() == "true")

# 최근 히스토리(크로스데이 중복 방지) - main()에서 state를 읽어 채움
CROSSDAY_DEDUPE_ENABLED = False
RECENT_HISTORY_CANON: set[str] = set()
RECENT_HISTORY_NORM: set[str] = set()

MAX_PER_SECTION = int(os.getenv("MAX_PER_SECTION", os.getenv("MAX_ARTICLES_PER_SECTION", "5")))
MAX_PER_SECTION = max(1, min(MAX_PER_SECTION, int(os.getenv("MAX_PER_SECTION_CAP", "20"))))

# 최소 기사 수(섹션별)
MIN_PER_SECTION = int(os.getenv("MIN_PER_SECTION", os.getenv("MIN_ARTICLES_PER_SECTION", "0")) or 0)
MIN_PER_SECTION = max(0, min(MIN_PER_SECTION, MAX_PER_SECTION))

# 기존 ENV(MAX_PAGES_PER_QUERY)는 "상한(cap)"으로만 유지한다.
# - 기본 수집은 1페이지 유지
# - 필요할 때만 추가 페이지(2..N)를 조건부로 호출
MAX_PAGES_PER_QUERY = int((os.getenv("MAX_PAGES_PER_QUERY", "1") or "1").strip() or 1)
MAX_PAGES_PER_QUERY = max(1, min(MAX_PAGES_PER_QUERY, int(os.getenv("MAX_PAGES_PER_QUERY_CAP", "10"))))

# --- Conditional pagination safety (BASE=1 page, only use extra pages when needed)
# ✅ daily_v7.yml과 정합:
# - MAX_PAGES_PER_QUERY는 워크플로우/운영에서 넉넉히 잡아도 되고(예: 4),
#   본 코드는 이를 '최대 허용치'로만 사용한다.
# - 기본은 1페이지, 섹션별 후보 풀이 부족할 때만 2페이지(start=51) 등을 추가 호출한다.
COND_PAGING_BASE_PAGES = int(os.getenv("COND_PAGING_BASE_PAGES", "1") or 1)
COND_PAGING_BASE_PAGES = max(1, min(COND_PAGING_BASE_PAGES, MAX_PAGES_PER_QUERY))

# 기본값은 2페이지까지만(=1→2) 보강하되,
# 필요 시 ENV로 늘릴 수 있게 한다(상한은 MAX_PAGES_PER_QUERY).
COND_PAGING_MAX_PAGES = int(os.getenv("COND_PAGING_MAX_PAGES", "2") or 2)
COND_PAGING_MAX_PAGES = max(COND_PAGING_BASE_PAGES, min(COND_PAGING_MAX_PAGES, MAX_PAGES_PER_QUERY))
COND_PAGING_ENABLED = (COND_PAGING_MAX_PAGES > COND_PAGING_BASE_PAGES)

# 섹션당 '추가 호출'에 참여할 쿼리 수 상한(기본: MAX_PER_SECTION+1)
_default_qcap = max(3, min(10, MAX_PER_SECTION + 1))
COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION = int(os.getenv("COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION", str(_default_qcap)) or _default_qcap)
COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION = max(0, min(COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION, 25))
# pool 부족 시 1페이지 추가 수집에 사용할 '보강 쿼리' 수 상한(기본: 6)
_default_fbqcap = max(0, min(10, MAX_PER_SECTION + 1))
COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION = int(os.getenv("COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION", str(min(6, _default_fbqcap))) or 6)
COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION = max(0, min(COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION, 20))

# pest 섹션은 실행형 병해충 기사를 놓치지 않기 위해 보강 쿼리를 항상 병합한다(하드코딩 URL 아님)
PEST_ALWAYS_ON_RECALL_QUERIES = [
    "과수화상병 방제", "과수화상병 약제 공급", "과수화상병 정밀예찰", "과수화상병 전수조사",
    "토마토뿔나방 방제", "토마토뿔나방 약제 지원", "토마토뿔나방 전수조사",
    "월동 병해충 방제", "병해충 현장지도", "병해충 예찰",
    "과수화상병", "과수화상병 약제", "과수화상병 방제 계획", "토마토뿔나방",
]
# pest는 page1 결과가 충분해 보여도 실행형 기사가 page2에 숨어있는 경우가 잦아
# always-on recall 쿼리에 한해 최소 page2를 선제적으로 1회 보강한다.
PEST_ALWAYS_ON_PAGE2_ENABLED = os.getenv("PEST_ALWAYS_ON_PAGE2_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")
PEST_ALWAYS_ON_PAGE2_QUERY_CAP = int(os.getenv("PEST_ALWAYS_ON_PAGE2_QUERY_CAP", "4") or 4)
PEST_ALWAYS_ON_PAGE2_QUERY_CAP = max(0, min(PEST_ALWAYS_ON_PAGE2_QUERY_CAP, 10))
# news API 미색인/지연에 대비해 pest는 web 검색(webkr)도 소량 보강한다.
PEST_WEB_RECALL_ENABLED = os.getenv("PEST_WEB_RECALL_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")
PEST_WEB_RECALL_QUERY_CAP = int(os.getenv("PEST_WEB_RECALL_QUERY_CAP", "3") or 3)
PEST_WEB_RECALL_QUERY_CAP = max(0, min(PEST_WEB_RECALL_QUERY_CAP, 8))
WEB_RECALL_ENABLED = os.getenv("WEB_RECALL_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")
WEB_RECALL_QUERY_CAP_PER_SECTION = int(os.getenv("WEB_RECALL_QUERY_CAP_PER_SECTION", "2") or 2)
WEB_RECALL_QUERY_CAP_PER_SECTION = max(0, min(WEB_RECALL_QUERY_CAP_PER_SECTION, 8))
WEB_RECALL_DISPLAY = int(os.getenv("WEB_RECALL_DISPLAY", "10") or 10)
WEB_RECALL_DISPLAY = max(5, min(WEB_RECALL_DISPLAY, 20))
GOOGLE_NEWS_RECALL_ENABLED = os.getenv("GOOGLE_NEWS_RECALL_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")
GOOGLE_NEWS_RECALL_QUERY_CAP_PER_SECTION = int(os.getenv("GOOGLE_NEWS_RECALL_QUERY_CAP_PER_SECTION", "3") or 3)
GOOGLE_NEWS_RECALL_QUERY_CAP_PER_SECTION = max(0, min(GOOGLE_NEWS_RECALL_QUERY_CAP_PER_SECTION, 8))
GOOGLE_NEWS_RECALL_ITEM_CAP = int(os.getenv("GOOGLE_NEWS_RECALL_ITEM_CAP", "8") or 8)
GOOGLE_NEWS_RECALL_ITEM_CAP = max(3, min(GOOGLE_NEWS_RECALL_ITEM_CAP, 20))
GOOGLE_NEWS_RECALL_MIN_AGE_DAYS = int(os.getenv("GOOGLE_NEWS_RECALL_MIN_AGE_DAYS", "5") or 5)
GOOGLE_NEWS_RECALL_MIN_AGE_DAYS = max(1, min(GOOGLE_NEWS_RECALL_MIN_AGE_DAYS, 90))


# 전체 런에서 추가 호출 예산(기본: qcap*2)
_default_budget = max(6, min(30, COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION * 2))
COND_PAGING_EXTRA_CALL_BUDGET_TOTAL = int(os.getenv("COND_PAGING_EXTRA_CALL_BUDGET_TOTAL", str(_default_budget)) or _default_budget)
COND_PAGING_EXTRA_CALL_BUDGET_TOTAL = max(0, min(COND_PAGING_EXTRA_CALL_BUDGET_TOTAL, 80))
_default_reserved_calls = min(2, COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION)
COND_PAGING_RESERVED_CALLS_PER_SECTION = int(
    os.getenv("COND_PAGING_RESERVED_CALLS_PER_SECTION", str(_default_reserved_calls)) or _default_reserved_calls
)
COND_PAGING_RESERVED_CALLS_PER_SECTION = max(0, min(COND_PAGING_RESERVED_CALLS_PER_SECTION, 8))
# 후보가 충분히 많은데(예: 50개+) 선택이 적은 날은 '품질이 낮은 날'일 가능성이 크므로
# 추가 페이지를 무의미하게 호출하지 않도록 상한을 둔다.
_default_trigger_cap = max(25, min(120, MAX_PER_SECTION * 8))
COND_PAGING_TRIGGER_CANDIDATE_CAP = int(os.getenv("COND_PAGING_TRIGGER_CANDIDATE_CAP", str(_default_trigger_cap)) or _default_trigger_cap)
COND_PAGING_TRIGGER_CANDIDATE_CAP = max(5, min(COND_PAGING_TRIGGER_CANDIDATE_CAP, 250))


# --- Recall backfill (broad-query + diversity guardrails)
# 목적: '쿼리 설계'에만 의존해 후보가 누락되는 문제를 줄이기 위해,
#       후보 풀이 부족할 때(또는 특정 신호가 0일 때) 소량의 광역 쿼리를 추가로 수집한다.
#       (스코어링/선정 로직은 그대로 두고, 후보(Recall)만 안정화)
RECALL_BACKFILL_ENABLED = os.getenv("RECALL_BACKFILL_ENABLED", "1").strip().lower() in ("1","true","yes","y")
RECALL_QUERY_CAP_PER_SECTION = int(os.getenv("RECALL_QUERY_CAP_PER_SECTION", "6") or 6)
RECALL_QUERY_CAP_PER_SECTION = max(0, min(RECALL_QUERY_CAP_PER_SECTION, 20))

# 1페이지 결과가 꽉 찬(=50건) 쿼리는 2페이지에 유의미한 '윈도우 내' 기사가 남아 있을 가능성이 높다.
# 후보 풀이 부족할 때만, 상위 N개 쿼리에 대해 page2를 우선적으로 시도한다.
RECALL_HIGH_VOLUME_PAGE2_QUERIES = int(os.getenv("RECALL_HIGH_VOLUME_PAGE2_QUERIES", "2") or 2)
RECALL_HIGH_VOLUME_PAGE2_QUERIES = max(0, min(RECALL_HIGH_VOLUME_PAGE2_QUERIES, 8))

# 전역 섹션 재분류(섹션별로 재스코어링 후 best section으로 이동)
GLOBAL_SECTION_REASSIGN_ENABLED = os.getenv("GLOBAL_SECTION_REASSIGN_ENABLED", "1").strip().lower() in ("1","true","yes","y")
GLOBAL_SECTION_REASSIGN_MIN_GAIN = float(os.getenv("GLOBAL_SECTION_REASSIGN_MIN_GAIN", "0.8") or 0.8)
GLOBAL_SECTION_REASSIGN_MIN_GAIN = max(0.0, min(GLOBAL_SECTION_REASSIGN_MIN_GAIN, 5.0))

# 최근 실험적 보정(쿼리-기사 정합성 게이트 / 키워드 강도 추가 보정)은
# 기본값을 OFF로 두고, 운영에서 필요 시 ENV로 켜서 점진 적용한다.
QUERY_ARTICLE_MATCH_GATE_ENABLED = os.getenv("QUERY_ARTICLE_MATCH_GATE_ENABLED", "0").strip().lower() in ("1", "true", "yes", "y")
SCORING_KEYWORD_STRENGTH_BOOST_ENABLED = os.getenv("SCORING_KEYWORD_STRENGTH_BOOST_ENABLED", "0").strip().lower() in ("1", "true", "yes", "y")
SCORING_TITLE_SIGNAL_BONUS_ENABLED = os.getenv("SCORING_TITLE_SIGNAL_BONUS_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")

# 섹션 배치 안정화: 최종 선발/전역 재분류 시 section-fit 신호를 함께 본다.
SECTION_FIT_MIN_FOR_TOP = float(os.getenv("SECTION_FIT_MIN_FOR_TOP", "0.8") or 0.8)
SECTION_FIT_MIN_FOR_TOP = max(0.0, min(SECTION_FIT_MIN_FOR_TOP, 5.0))
SECTION_REASSIGN_FIT_GUARD = float(os.getenv("SECTION_REASSIGN_FIT_GUARD", "0.8") or 0.8)
SECTION_REASSIGN_FIT_GUARD = max(0.0, min(SECTION_REASSIGN_FIT_GUARD, 5.0))
# 섹션 재배치 보강: section-fit 우위가 충분히 크면 score 미세열세여도 dist/policy로 이동 허용
SECTION_REASSIGN_STRONG_FIT_DELTA = float(os.getenv("SECTION_REASSIGN_STRONG_FIT_DELTA", "1.2") or 1.2)
SECTION_REASSIGN_STRONG_FIT_DELTA = max(0.0, min(SECTION_REASSIGN_STRONG_FIT_DELTA, 5.0))
SECTION_REASSIGN_STRONG_FIT_SCORE_TOL = float(os.getenv("SECTION_REASSIGN_STRONG_FIT_SCORE_TOL", "0.8") or 0.8)
SECTION_REASSIGN_STRONG_FIT_SCORE_TOL = max(0.0, min(SECTION_REASSIGN_STRONG_FIT_SCORE_TOL, 4.0))

# 다양성(coverage) 보강: 중복은 아니지만 '비슷한 기사'가 연속으로 올라오는 것을 완화(MMR).
MMR_DIVERSITY_ENABLED = os.getenv("MMR_DIVERSITY_ENABLED", "1").strip().lower() in ("1","true","yes","y")
MMR_DIVERSITY_LAMBDA = float(os.getenv("MMR_DIVERSITY_LAMBDA", "1.15") or 1.15)
MMR_DIVERSITY_LAMBDA = max(0.0, min(MMR_DIVERSITY_LAMBDA, 3.0))
MMR_DIVERSITY_MIN_POOL = int(os.getenv("MMR_DIVERSITY_MIN_POOL", "12") or 12)
MMR_DIVERSITY_MIN_POOL = max(0, min(MMR_DIVERSITY_MIN_POOL, 80))

_COND_PAGING_LOCK = threading.Lock()
_COND_PAGING_EXTRA_CALLS_USED = 0
_COND_PAGING_EXTRA_CALLS_BY_SECTION: dict[str, int] = {}

def reset_extra_call_budget() -> None:
    """Reset extra recall/page2 call budget for a fresh collection run."""
    global _COND_PAGING_EXTRA_CALLS_USED, _COND_PAGING_EXTRA_CALLS_BY_SECTION
    with _COND_PAGING_LOCK:
        _COND_PAGING_EXTRA_CALLS_USED = 0
        _COND_PAGING_EXTRA_CALLS_BY_SECTION = {}

def _extra_call_budget_sections() -> list[str]:
    try:
        keys = [str(sec.get("key") or "").strip() for sec in (SECTIONS or []) if str(sec.get("key") or "").strip()]
    except Exception:
        keys = []
    return keys or ["policy", "supply", "dist", "pest"]

def _reserved_extra_calls_per_section() -> int:
    section_count = max(1, len(_extra_call_budget_sections()))
    return min(COND_PAGING_RESERVED_CALLS_PER_SECTION, COND_PAGING_EXTRA_CALL_BUDGET_TOTAL // section_count)

def _reserved_extra_calls_needed_by_others(section_key: str) -> int:
    reserve = _reserved_extra_calls_per_section()
    if reserve <= 0:
        return 0
    need = 0
    for key in _extra_call_budget_sections():
        if key == section_key:
            continue
        used = int(_COND_PAGING_EXTRA_CALLS_BY_SECTION.get(key, 0) or 0)
        need += max(0, reserve - used)
    return need

def _take_extra_call_budget_for_section(section_key: str, n: int = 1, *, require_cond_paging: bool = True) -> bool:
    """Spend extra-call budget while preserving a small reserve for each section."""
    global _COND_PAGING_EXTRA_CALLS_USED
    if require_cond_paging and not COND_PAGING_ENABLED:
        return False
    section_key = (section_key or "").strip() or "_default"
    n = max(1, int(n or 1))
    with _COND_PAGING_LOCK:
        if _COND_PAGING_EXTRA_CALLS_USED + n > COND_PAGING_EXTRA_CALL_BUDGET_TOTAL:
            return False
        used_by_section = int(_COND_PAGING_EXTRA_CALLS_BY_SECTION.get(section_key, 0) or 0)
        reserve = _reserved_extra_calls_per_section()
        if used_by_section + n > reserve:
            reserved_for_others = _reserved_extra_calls_needed_by_others(section_key)
            shared_limit = COND_PAGING_EXTRA_CALL_BUDGET_TOTAL - reserved_for_others
            if _COND_PAGING_EXTRA_CALLS_USED + n > shared_limit:
                return False
        _COND_PAGING_EXTRA_CALLS_USED += n
        _COND_PAGING_EXTRA_CALLS_BY_SECTION[section_key] = used_by_section + n
        return True

def _take_extra_call_budget(n: int = 1, *, require_cond_paging: bool = True) -> bool:
    """Return True if we can spend extra call budget (thread-safe)."""
    global _COND_PAGING_EXTRA_CALLS_USED
    if require_cond_paging and not COND_PAGING_ENABLED:
        return False
    n = max(1, int(n or 1))
    with _COND_PAGING_LOCK:
        if _COND_PAGING_EXTRA_CALLS_USED + n > COND_PAGING_EXTRA_CALL_BUDGET_TOTAL:
            return False
        _COND_PAGING_EXTRA_CALLS_USED += n
        return True

def _cond_paging_take_budget(n: int = 1) -> bool:
    """Return True if we can spend extra-page call budget (thread-safe)."""
    return _take_extra_call_budget(n, require_cond_paging=True)

def _cond_paging_take_budget_for_section(section_key: str, n: int = 1) -> bool:
    """Return True if a section can spend extra-page call budget."""
    return _take_extra_call_budget_for_section(section_key, n, require_cond_paging=True)

DEBUG_SELECTION = os.getenv("DEBUG_SELECTION", "0") == "1"
DEBUG_REPORT = os.getenv("DEBUG_REPORT", "0") == "1"
DEBUG_REPORT_MAX_CANDIDATES = int(os.getenv("DEBUG_REPORT_MAX_CANDIDATES", "25"))
DEBUG_REPORT_MAX_REJECTS = int(os.getenv("DEBUG_REPORT_MAX_REJECTS", "120"))
DEBUG_REPORT_WRITE_JSON = (os.getenv("DEBUG_REPORT_WRITE_JSON", "1") == "1") if DEBUG_REPORT else False
REPORT_DATE_OVERRIDE = os.getenv("REPORT_DATE_OVERRIDE", "").strip()

# Debug report data (embedded into HTML when DEBUG_REPORT=1)
_DEBUG_LOCK = threading.Lock()
_DEBUG_QUERY_CONTEXT = threading.local()
DEBUG_DATA: JsonDict = {
    "generated_at_kst": None,
    "build_tag": os.getenv("BUILD_TAG", ""),
    "filter_rejects": [],  # list[{section, reason, press, domain, title, url}]
    "sections": {},        # section_key -> {threshold, core_min, total_candidates, total_selected, top: [...]}
    "collections": {},     # section_key -> {queries, hits, paging, recall, ...}
}

def dbg_add_filter_reject(section: str, reason: str, title: str, url: str, domain: str, press: str) -> None:
    if not DEBUG_REPORT:
        return
    try:
        item = {
            "section": section,
            "reason": reason,
            "press": press or "",
            "domain": (domain or ""),
            "title": (title or "")[:160],
            "url": (url or "")[:500],
            "source_query": str(getattr(_DEBUG_QUERY_CONTEXT, "query", "") or "")[:120],
            "source_channel": str(getattr(_DEBUG_QUERY_CONTEXT, "channel", "") or "")[:40],
        }
        with _DEBUG_LOCK:
            if len(DEBUG_DATA["filter_rejects"]) < DEBUG_REPORT_MAX_REJECTS:
                DEBUG_DATA["filter_rejects"].append(item)
    except Exception:
        pass


def dbg_set_current_query(query: str = "", channel: str = "") -> None:
    try:
        _DEBUG_QUERY_CONTEXT.query = str(query or "")
        _DEBUG_QUERY_CONTEXT.channel = str(channel or "")
    except Exception:
        return


def dbg_clear_current_query() -> None:
    try:
        _DEBUG_QUERY_CONTEXT.query = ""
        _DEBUG_QUERY_CONTEXT.channel = ""
    except Exception:
        return


def dbg_set_section(section: str, payload: JsonDict) -> None:
    if not DEBUG_REPORT:
        return
    try:
        with _DEBUG_LOCK:
            DEBUG_DATA["sections"][section] = payload
    except Exception:
        pass


def dbg_set_collection(section: str, payload: JsonDict) -> None:
    """수집 단계 메타(쿼리/페이지/히트/리콜)를 디버그 리포트에 저장."""
    if not DEBUG_REPORT:
        return
    try:
        with _DEBUG_LOCK:
            DEBUG_DATA["collections"][section] = payload
    except Exception:
        pass


def reset_debug_report() -> None:
    if not DEBUG_REPORT:
        return
    try:
        with _DEBUG_LOCK:
            DEBUG_DATA["generated_at_kst"] = datetime.now(KST).isoformat(timespec="seconds")
            DEBUG_DATA["build_tag"] = BUILD_TAG
            DEBUG_DATA["filter_rejects"] = []
            DEBUG_DATA["sections"] = {}
            DEBUG_DATA["collections"] = {}
    except Exception:
        pass


STATE_FILE_PATH = ".agri_state.json"
ARCHIVE_MANIFEST_PATH = ".agri_archive.json"
DOCS_INDEX_PATH = "docs/index.html"
DOCS_ARCHIVE_DIR = "docs/archive"
DOCS_SEARCH_INDEX_PATH = "docs/search_index.json"
DOCS_ARCHIVE_MANIFEST_JSON_PATH = "docs/archive_manifest.json"
MAX_SEARCH_DATES = int(os.getenv("MAX_SEARCH_DATES", "180"))
MAX_SEARCH_ITEMS = int(os.getenv("MAX_SEARCH_ITEMS", "6000"))

# Build marker (for verifying deployed code)
def _compute_build_tag() -> str:
    # 1) Prefer explicit env injection (from GitHub Actions)

    env = (os.getenv("BUILD_TAG") or "").strip()
    if env and not env.startswith("v0-"):
        return env

    # 2) Try git describe (works best when tags are fetched)
    try:
        import subprocess

        def _run(cmd: list[str]) -> str:
            return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()

        # Shallow checkouts often miss tags; try fetching tags (safe no-op if not a git repo)
        try:
            _run(["git", "fetch", "--tags", "--force"])
        except Exception:
            pass

        try:
            return _run(["git", "describe", "--tags", "--match", "v[0-9]*", "--always", "--abbrev=7"])
        except Exception:
            pass
    except Exception:
        pass

    # If env was provided but was a generic fallback (v0-*), keep it as a fallback
    if env:
        return env

    # 3) Fallbacks (still stable/unique per run)
    sha = (os.getenv("GITHUB_SHA") or "").strip()
    sha7 = sha[:7] if sha else ""
    run_no = (os.getenv("GITHUB_RUN_NUMBER") or "").strip()

    if run_no and sha7:
        return f"v0-{run_no}-{sha7}"
    if sha7:
        return f"v0-{sha7}"

    import time
    return time.strftime("v0-local-%Y%m%d%H%M%S", time.gmtime())


BUILD_TAG = _compute_build_tag()
RENDERED_AT_KST = datetime.now(KST).isoformat(timespec="seconds")

# Keep debug report in sync
try:
    DEBUG_DATA["build_tag"] = BUILD_TAG
    DEBUG_DATA["generated_at_kst"] = RENDERED_AT_KST
except Exception:
    pass
# Optional: extra RSS sources (comma-separated). If empty, RSS fetching is skipped.
DEFAULT_WHITELIST_RSS_URLS = [
    "http://www.wonyesanup.co.kr/rss/allArticle.xml",
]
WHITELIST_RSS_URLS: list[str] = []
for _rss_url in list(DEFAULT_WHITELIST_RSS_URLS) + [u.strip() for u in os.getenv("WHITELIST_RSS_URLS", "").split(",") if u.strip()]:
    if _rss_url and _rss_url not in WHITELIST_RSS_URLS:
        WHITELIST_RSS_URLS.append(_rss_url)





DEFAULT_REPO = (os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY") or "").strip()
GH_TOKEN = (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()

# GitHub content read/write target (separate prod vs dev branches).
GH_CONTENT_REF = (os.getenv("GH_CONTENT_REF") or "main").strip() or "main"
GH_CONTENT_BRANCH = (os.getenv("GH_CONTENT_BRANCH") or GH_CONTENT_REF).strip() or GH_CONTENT_REF

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

# -----------------------------
# Naver rate limit / retry
# -----------------------------
NAVER_MIN_INTERVAL_SEC = float(os.getenv("NAVER_MIN_INTERVAL_SEC", "0.35"))  # 최소 호출 간격(초)
NAVER_MAX_RETRIES = int(os.getenv("NAVER_MAX_RETRIES", "6"))
NAVER_BACKOFF_MAX_SEC = float(os.getenv("NAVER_BACKOFF_MAX_SEC", "20"))
NAVER_MAX_WORKERS = int(os.getenv("NAVER_MAX_WORKERS", "2"))  # 동시 요청 수(속도제한 회피용)

_NAVER_LOCK = threading.Lock()
_NAVER_LAST_CALL = 0.0

def _naver_throttle() -> None:
    """전역 최소 간격을 보장(멀티스레드 안전).
    ⚠️ 병목 방지: sleep은 락 밖에서 수행.
    """
    global _NAVER_LAST_CALL
    wait = 0.0
    with _NAVER_LOCK:
        now = time.monotonic()
        wait = NAVER_MIN_INTERVAL_SEC - (now - _NAVER_LAST_CALL)
        if wait < 0:
            wait = 0.0
        _NAVER_LAST_CALL = now + wait
    if wait > 0:
        time.sleep(wait)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_MAX_OUTPUT_TOKENS = int((os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "0") or "0").strip() or 0)
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "").strip()
OPENAI_TEXT_VERBOSITY = os.getenv("OPENAI_TEXT_VERBOSITY", "").strip()
OPENAI_BATCH_SIZE = int((os.getenv("OPENAI_BATCH_SIZE", "25") or "25").strip() or 25)
OPENAI_BATCH_SIZE = max(5, min(OPENAI_BATCH_SIZE, 80))
OPENAI_SUMMARY_CACHE_PATH = os.getenv("OPENAI_SUMMARY_CACHE_PATH", ".agri_summary_cache.json").strip() or ".agri_summary_cache.json"
OPENAI_SUMMARY_CACHE_MAX = int((os.getenv("OPENAI_SUMMARY_CACHE_MAX", "2000") or "2000").strip() or 2000)
OPENAI_SUMMARY_CACHE_MAX = max(200, min(OPENAI_SUMMARY_CACHE_MAX, 20000))
OPENAI_RETRY_MAX = int((os.getenv("OPENAI_RETRY_MAX", "3") or "3").strip() or 3)
OPENAI_RETRY_MAX = max(1, min(OPENAI_RETRY_MAX, 8))

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "").strip()
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "").strip()
KAKAO_STATUS_FILE = os.getenv("KAKAO_STATUS_FILE", "").strip()
KAKAO_INCLUDE_LINK_IN_TEXT = os.getenv("KAKAO_INCLUDE_LINK_IN_TEXT", "false").strip().lower() in ("1", "true", "yes")
KAKAO_FAIL_OPEN = os.getenv("KAKAO_FAIL_OPEN", "true").strip().lower() in ("1", "true", "yes", "y")
MAINTENANCE_SEND_KAKAO = os.getenv("MAINTENANCE_SEND_KAKAO", "false").strip().lower() in ("1","true","yes","y")

PAGES_BASE_URL_OVERRIDE = os.getenv("PAGES_BASE_URL", "").strip()
BRIEF_VIEW_URL = os.getenv("BRIEF_VIEW_URL", "").strip()

# Dev verification mode: overwrite a fixed preview page instead of creating dated archives.
DEV_SINGLE_PAGE_MODE = os.getenv("DEV_SINGLE_PAGE_MODE", "false").strip().lower() in ("1", "true", "yes", "y")
DEV_SINGLE_PAGE_PATH = (os.getenv("DEV_SINGLE_PAGE_PATH", "").strip() or "docs/dev/index.html")
DEV_SINGLE_PAGE_URL_PATH = (os.getenv("DEV_SINGLE_PAGE_URL_PATH", "").strip() or "index.html")
DEV_SINGLE_PAGE_VERSION_PATH = (os.getenv("DEV_SINGLE_PAGE_VERSION_PATH", "").strip() or "")
DEV_SINGLE_PAGE_VERSION_URL_PATH = (os.getenv("DEV_SINGLE_PAGE_VERSION_URL_PATH", "").strip() or "")
DEV_PREVIEW_ASSET_BASE_URL = (os.getenv("DEV_PREVIEW_ASSET_BASE_URL", "").strip() or "").rstrip("/")


FORCE_REPORT_DATE = os.getenv("FORCE_REPORT_DATE", "").strip()  # YYYY-MM-DD
FORCE_RUN_ANYDAY = os.getenv("FORCE_RUN_ANYDAY", "false").strip().lower() in ("1", "true", "yes")
FORCE_END_NOW = os.getenv("FORCE_END_NOW", "false").strip().lower() in ("1", "true", "yes")
STRICT_KAKAO_LINK_CHECK = os.getenv("STRICT_KAKAO_LINK_CHECK", "false").strip().lower() in ("1", "true", "yes")

# Backfill rebuild (최근 N일 아카이브를 재생성하여 필터/스코어 개선을 과거 페이지에도 반영)
# - 기본 OFF (0). 필요할 때 workflow env로 켜서 사용.
BACKFILL_REBUILD_DAYS = int((os.getenv("BACKFILL_REBUILD_DAYS", "0") or "0").strip() or 0)
BACKFILL_REBUILD_DAYS_MAX = int((os.getenv("BACKFILL_REBUILD_DAYS_MAX", "120") or "120").strip() or 120)
BACKFILL_REBUILD_DAYS_MAX = max(0, min(BACKFILL_REBUILD_DAYS_MAX, 400))
BACKFILL_REBUILD_DAYS = max(0, min(BACKFILL_REBUILD_DAYS, BACKFILL_REBUILD_DAYS_MAX))
BACKFILL_REBUILD_CREATE_MISSING = os.getenv("BACKFILL_REBUILD_CREATE_MISSING", "false").strip().lower() in ("1","true","yes","y")
BACKFILL_START_DATE = (os.getenv("BACKFILL_START_DATE", "") or "").strip()
BACKFILL_END_DATE = (os.getenv("BACKFILL_END_DATE", "") or "").strip()
BACKFILL_REBUILD_SLEEP_SEC = float((os.getenv("BACKFILL_REBUILD_SLEEP_SEC", "0.2") or "0.2").strip() or 0.2)
BACKFILL_REBUILD_SLEEP_SEC = max(0.0, min(BACKFILL_REBUILD_SLEEP_SEC, 3.0))
BACKFILL_REBUILD_SKIP_OPENAI = os.getenv("BACKFILL_REBUILD_SKIP_OPENAI", "false").strip().lower() in ("1", "true", "yes", "y")


# UX patch (과거 아카이브에 UI/UX 업데이트를 '패치'로 반영: 스와이프/로딩/스티키 nav 등)
# - 기본: 최근 30일만 패치
UX_PATCH_DAYS = int((os.getenv("UX_PATCH_DAYS", "30") or "30").strip() or 30)
UX_PATCH_DAYS = max(0, min(UX_PATCH_DAYS, 365))

EXTRA_HOLIDAYS = set([s.strip() for s in os.getenv("EXTRA_HOLIDAYS", "").split(",") if s.strip()])
EXCLUDE_HOLIDAYS = set([s.strip() for s in os.getenv("EXCLUDE_HOLIDAYS", "").split(",") if s.strip()])

# -----------------------------
# Domain blocks / terms
# -----------------------------
BLOCKED_DOMAINS = {
    "wikitree.co.kr",
    "theqoo.net",
    "instiz.net",
    "namu.wiki",
    "allurekorea.com",
    "vogue.co.kr",
    "marieclairekorea.com",
    "cosmopolitan.co.kr",
    "gqkorea.co.kr",
}

AGRI_STRONG_TERMS = [
    "가락시장", "도매시장", "공판장", "경락", "경락가", "경매", "청과", "산지", "출하", "물량", "반입",
    "산지유통", "APC", "산지유통센터", "선별", "CA저장", "저장고", "저장량",
    "시세", "도매가격", "소매가격", "가격", "수급", "수급동향", "작황", "생산량", "재배", "수확", "면적",
    "농림축산식품부", "농식품부", "aT", "한국농수산식품유통공사", "농관원", "국립농산물품질관리원",
    "검역", "할당관세", "수입", "수출", "관세", "통관", "원산지", "부정유통", "온라인 도매시장",
    "비축미", "정부", "대책", "지원", "할인지원", "성수품",
    "병해충", "방제", "약제", "살포", "예찰", "과수화상병", "탄저병", "동해", "냉해", "월동",
]

OFFTOPIC_HINTS = [
    "배우", "아이돌", "드라마", "영화", "예능", "콘서트", "팬", "뮤직",
    "국회", "총선", "검찰", "재판", "탄핵", "정당",
    "코스피", "코스닥", "주가", "급등", "급락", "비트코인", "환율",
    "여행", "관광", "호텔", "리조트", "레스토랑", "와인", "해변", "휴양",
]

# 공통 제외(광고/구인/부동산/도박 등) - text는 lower() 상태
BAN_KWS = [
    # 구인/채용
    "구인", "채용", "모집공고", "아르바이트", "알바", "인턴",
    # 부동산
    "부동산", "분양", "오피스텔", "청약", "전세", "월세",
    # 금융/도박 스팸
    "대출", "보험", "카지노", "바카라", "토토", "도박",
    # 기타 스팸성
    "스팸",
]



# -----------------------------
# Additional hard filters / controls (2026-02 hotfix)
# -----------------------------
# 오피니언/사설/칼럼 등은 브리핑 대상에서 제외(원예수급 실무 신호가 약하고 노이즈가 큼)
OPINION_BAN_TERMS = [
    "[사설]", "사설", "칼럼", "오피니언", "기고", "독자기고", "기자수첩",
    "일기", "농막일기", "수필", "에세이", "연재", "기행",
    "만평", "데스크칼럼", "횡설수설", "기자의 시선", "논단",
]

# 지역 동정/기부/장학/발전기금 등 커뮤니티성 기사 제외용(특히 ○○농협 + 기금전달류 오탐 방지)
COMMUNITY_DONATION_TERMS = [
    "발전기금", "교육발전기금", "장학금", "장학", "성금", "기탁", "후원금",
    "기부금", "성품", "쌀기부", "나눔", "봉사활동", "후원", "기부",
]

# 원예수급과 무관한 산업/금융/바이오 오탐 방지(농업 맥락이 약하면 컷)
HARD_OFFTOPIC_TERMS = [
    "반도체", "배터리", "2차전지", "코스피", "코스닥", "주식", "채권", "가상자산", "비트코인",
    "부동산", "금리", "환율", "증시", "ipo", "상장", "인수합병", "m&a",
    "바이오", "임상", "의약", "제약", "세포", "항암", "유전자", "플랫폼",
    "의사과학",
    "의사과학자",
    "의사과학원",
    "의사공학",
    "의과학",
    "의과학원",
    "전기차",
    "자동차",
    "캐즘",
    "테슬라",
    "충전",
    "완성차",
]

# 수산물(생선/양식) 단독 이슈는 원예 브리핑에서 제외
# - 단, '농수산물' 같은 중립 표현 때문에 과도 차단되지 않도록 전용 중립 표현을 제거 후 판단한다.
FISHERY_STRICT_TERMS = [
    "수산", "수산물", "어업", "양식", "어획", "수협", "활어", "선어", "어류", "수산시장",
    "생선", "어선", "원양", "연근해", "수산업", "해산물", "수산가공",
    "옥돔", "갈치", "고등어", "오징어", "명태", "대게", "참치", "광어", "우럭", "전복", "해삼",
]
FISHERY_NEUTRAL_PHRASES = [
    "농수산물", "농축수산물", "농수산식품",
]

# 금융/산업 일반 기사(농협은행/NH투자/주가/실적 등) 오탐 차단용
FINANCE_STRICT_TERMS = [
    "농협은행", "nh투자", "nh 투자", "증권", "은행", "보험", "카드", "캐피탈",
    "주가", "배당", "배당금", "실적", "매출", "영업이익", "순이익", "주주", "상장",
    "ipo", "공모", "채권", "금리", "환율", "부동산", "코스피", "코스닥",
]

# 현재는 원예수급부 관리 품목 전체를 동일한 대상으로 본다.
# 특정 품목을 전역에서 하드 제외하지 않는다.
EXCLUDED_ITEMS: list[str] = []
GLOBAL_RETAIL_PROTEST_HINTS = [
    "target", "타깃", "walmart", "월마트", "costco", "코스트코",
    "starbucks", "스타벅스", "boycott", "보이콧", "시위", "protest",
    "매장", "retail", "소매", "전역",
]

KOREA_CONTEXT_HINTS = [
    "국내", "한국", "우리나라", "농협", "지자체", "군", "시", "도", "농가", "산지", "가락시장",
    "농식품부", "aT", "농관원", "대한민국", "설", "명절",
]

WHOLESALE_MARKET_TERMS = ["가락시장", "도매시장", "공판장", "경락", "경매", "반입", "중도매"]


# -----------------------------
# Policy domains
# -----------------------------
POLICY_DOMAINS = {
    "korea.kr",
    "mafra.go.kr",
    "at.or.kr",
    "naqs.go.kr",
    "krei.re.kr",
}

ALLOWED_GO_KR = {
    "mafra.go.kr",
    "customs.go.kr",
    "kostat.go.kr",
    "moef.go.kr",
    "kma.go.kr",
}

AGRI_POLICY_KEYWORDS = [
    "농축수산물", "농축산물", "성수품", "할인지원", "할당관세", "검역",
    "수급", "가격", "과일", "비축미", "원산지", "정책", "대책", "브리핑", "보도자료"
]


# 전력/에너지/유틸리티(전력 도매시장 등) 동음이의어 오탐 방지용 컨텍스트
ENERGY_CONTEXT_TERMS = [
    "전력", "전력망", "전력계통", "전력계통", "발전", "발전소", "발전량", "송전", "배전",
    "전기요금", "요금", "정산", "유틸리티", "에너지", "가스", "수소", "전력시장", "전력 도매시장",
    "도매시장 거래", "전력 소매시장", "계통", "계통운영", "수요반응", "전력거래소", "kpx",
    "옥토퍼스", "octopus", "크라켄", "kraken", "유틸리티 os", "운영체제(os)",
]

# '도매시장'이 비농산물(전력/에너지/금융 등) 기사에서 쓰이는 경우를 걸러내기 위한 디스앰비규에이터
# - text는 lower()로 처리되므로, 여기도 소문자/한글 그대로 사용
AGRI_WHOLESALE_DISAMBIGUATORS = [
    "농산물", "농수산물", "청과", "가락시장", "공판장", "도매시장법인", "경락", "경락가",
    "중도매인", "시장도매인", "반입", "경매", "산지", "apc", "산지유통", "산지유통센터",
    "농협", "원예농협", "과수농협", "청과물",
]

# 축산물(한우/돼지고기/계란 등) 단독 이슈는 원예 브리핑에서 제외(완전 배제)
# - '농축산물/농림축산식품부' 같은 중립 표현만으로는 제외하지 않도록, 보수적으로 판단한다.
LIVESTOCK_STRICT_TERMS = [
    "축산물", "축산", "가축", "도축", "도계", "사료", "축산업", "낙농", "양돈", "양계",
    "한우", "한돈", "우육", "돈육", "소고기", "돼지고기", "닭고기", "계란", "달걀", "우유", "치즈",
    "젖소", "소", "돼지", "닭", "오리",
]
# 농축산 정책/행정 일반 표현(오탐 방지 목적) — 제거 후 판단에 사용
LIVESTOCK_NEUTRAL_PHRASES = [
    "농축산물", "농축수산물", "농림축산식품부", "농림축산", "농축산", "농축수산",
]
# 원예/농산물(비축산) 강신호(축산 단독인지 판단용)
HORTI_CORE_GENERAL_TERMS = [
    "원예", "과수", "화훼", "절화", "과일", "채소", "청과", "시설채소", "하우스", "비가림",
    "자조금", "원예자조금", "과수자조금", "국화", "장미",
]
SUPPLY_GENERAL_MUST_TERMS = [
    "원예", "과수", "과일", "화훼", "절화", "생화", "시설채소", "과채",
]


def _ordered_unique_terms(values: Any) -> list[str]:
    out: list[str] = []
    for value in (values or []):
        term = str(value or "").strip()
        if term and term not in out:
            out.append(term)
    return out


COMMODITY_REGISTRY = [
    {
        "topic": "사과",
        "rep_term": "사과",
        "display_name": "사과",
        "aliases": ["사과"],
        "focus_terms": ["사과"],
        "brief_tags": ["사과"],
        "supply_queries": ["사과 수급", "사과 가격", "사과 작황", "사과 저장", "사과 출하"],
        "feature_profile": "orchard",
    },
    {
        "topic": "배",
        "rep_term": "배",
        "display_name": "배",
        "aliases": ["신고배", "나주배", "배 과일", "배(과일)"],
        "focus_terms": ["배 과일", "신고배", "나주배"],
        "tag_terms": ["배", "배 과일", "신고배", "나주배"],
        "brief_tags": ["배"],
        "supply_queries": ["배 과일 수급", "배 과일 가격", "배 과일 작황", "배 과일 저장", "배 과일 출하"],
        "feature_profile": "orchard",
    },
    {
        "topic": "단감",
        "rep_term": "단감",
        "display_name": "단감",
        "aliases": ["단감"],
        "focus_terms": ["단감"],
        "brief_tags": ["단감"],
        "supply_queries": ["단감 수급", "단감 가격", "단감 작황"],
        "feature_profile": "orchard",
    },
    {
        "topic": "감/곶감",
        "rep_term": "곶감",
        "display_name": "곶감",
        "aliases": ["떫은감", "곶감"],
        "focus_terms": ["곶감", "떫은감"],
        "brief_tags": ["곶감"],
        "supply_queries": ["곶감 수급", "떫은감 작황"],
        "feature_profile": "orchard",
    },
    {
        "topic": "감귤/만감",
        "rep_term": "감귤",
        "display_name": "감귤",
        "aliases": ["감귤", "만감", "만감류", "한라봉", "레드향", "천혜향", "황금향", "만다린", "클레멘틴"],
        "focus_terms": ["감귤", "만감", "한라봉", "레드향", "천혜향"],
        "brief_tags": ["감귤"],
        "supply_queries": [
            "감귤 수급", "감귤 가격", "감귤 작황", "감귤 관세", "감귤 무관세", "제주 감귤 관세",
            "만다린 관세", "감귤 FTA", "만감류 출하", "한라봉 출하", "레드향 출하", "천혜향 출하",
        ],
        "feature_profile": "citrus",
    },
    {
        "topic": "포도",
        "rep_term": "포도",
        "display_name": "포도",
        "aliases": ["포도", "샤인머스캣", "\uC0E4\uC778\uBA38\uC2A4\uCF13"],
        "focus_terms": ["포도", "샤인머스캣", "\uC0E4\uC778\uBA38\uC2A4\uCF13"],
        "brief_tags": ["포도"],
        "supply_queries": ["포도 수급", "포도 가격", "포도 작황", "샤인머스캣 수급", "샤인머스캣 가격", "샤인머스캣 작황"],
        "feature_profile": "orchard",
    },
    {
        "topic": "키위",
        "rep_term": "키위",
        "display_name": "키위",
        "aliases": ["키위", "참다래"],
        "focus_terms": ["키위", "참다래"],
        "brief_tags": ["키위"],
        "supply_queries": ["키위 수급", "키위 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "유자",
        "rep_term": "유자",
        "display_name": "유자",
        "aliases": ["유자"],
        "focus_terms": ["유자"],
        "brief_tags": ["유자"],
        "supply_queries": ["유자 수급", "유자 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "밤",
        "rep_term": "알밤",
        "display_name": "밤",
        "aliases": ["알밤"],
        "focus_terms": ["알밤"],
        "brief_tags": ["밤"],
        "supply_queries": ["알밤 수급", "알밤 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "자두",
        "rep_term": "자두",
        "display_name": "자두",
        "aliases": ["자두"],
        "focus_terms": ["자두"],
        "brief_tags": ["자두"],
        "supply_queries": ["자두 수급", "자두 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "복숭아",
        "rep_term": "복숭아",
        "display_name": "복숭아",
        "aliases": ["복숭아"],
        "focus_terms": ["복숭아"],
        "brief_tags": ["복숭아"],
        "supply_queries": ["복숭아 수급", "복숭아 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "매실",
        "rep_term": "매실",
        "display_name": "매실",
        "aliases": ["매실"],
        "focus_terms": ["매실"],
        "brief_tags": ["매실"],
        "supply_queries": ["매실 수급", "매실 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "딸기",
        "rep_term": "딸기",
        "display_name": "딸기",
        "aliases": ["딸기"],
        "focus_terms": ["딸기"],
        "brief_tags": ["딸기"],
        "supply_queries": ["딸기 수급", "딸기 가격", "딸기 작황"],
        "feature_profile": "greenhouse",
    },
    {
        "topic": "토마토",
        "rep_term": "토마토",
        "display_name": "토마토",
        "aliases": ["토마토", "방울토마토", "대추방울토마토"],
        "focus_terms": ["토마토", "방울토마토", "대추방울토마토"],
        "brief_tags": ["토마토"],
        "supply_queries": ["토마토 수급", "토마토 가격", "토마토 작황", "방울토마토 가격", "대추방울토마토 가격"],
        "feature_profile": "greenhouse",
    },
    {
        "topic": "수박",
        "rep_term": "수박",
        "display_name": "수박",
        "aliases": ["수박"],
        "focus_terms": ["수박"],
        "brief_tags": ["수박"],
        "supply_queries": ["수박 수급", "수박 도매가격", "수박 작황"],
        "feature_profile": "orchard",
    },
    {
        "topic": "호박",
        "rep_term": "호박",
        "display_name": "호박",
        "aliases": ["호박", "애호박", "단호박", "쥬키니", "주키니"],
        "focus_terms": ["호박", "애호박", "단호박", "쥬키니"],
        "brief_tags": ["호박"],
        "supply_queries": ["호박 가격", "애호박 수급", "애호박 가격", "단호박 가격", "쥬키니 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "피망",
        "rep_term": "피망",
        "display_name": "피망",
        "aliases": ["피망"],
        "focus_terms": ["피망"],
        "brief_tags": ["피망"],
        "supply_queries": ["피망 수급", "피망 가격"],
        "feature_profile": "orchard",
    },
    {
        "topic": "멜론",
        "rep_term": "멜론",
        "display_name": "멜론",
        "aliases": ["머스크멜론", "네트멜론", "얼스멜론", "하미과", "칸탈루프", "허니듀", "멜론"],
        "focus_terms": ["멜론", "머스크멜론", "네트멜론", "얼스멜론"],
        "brief_tags": ["멜론"],
        "supply_queries": ["멜론 출하", "멜론 도매가격", "멜론 작황", "멜론 재배", "머스크멜론 출하", "머스크멜론 도매가격"],
        "feature_profile": "greenhouse",
    },
    {
        "topic": "파프리카",
        "rep_term": "파프리카",
        "display_name": "파프리카",
        "aliases": ["파프리카"],
        "focus_terms": ["파프리카"],
        "brief_tags": ["파프리카"],
        "supply_queries": ["파프리카 수급", "파프리카 가격", "파프리카 수출"],
        "feature_profile": "greenhouse",
    },
    {
        "topic": "참외",
        "rep_term": "참외",
        "display_name": "참외",
        "aliases": ["참외"],
        "focus_terms": ["참외"],
        "brief_tags": ["참외"],
        "supply_queries": ["참외 수급", "참외 가격"],
        "feature_profile": "greenhouse",
    },
    {
        "topic": "오이",
        "rep_term": "오이",
        "display_name": "오이",
        "aliases": ["오이"],
        "focus_terms": ["오이"],
        "brief_tags": ["오이"],
        "supply_queries": ["오이 수급", "오이 가격", "오이 작황"],
        "feature_profile": "greenhouse",
    },
    {
        "topic": "상추",
        "rep_term": "상추",
        "display_name": "상추",
        "aliases": ["상추"],
        "focus_terms": ["상추"],
        "brief_tags": ["상추"],
        "supply_queries": ["상추 수급", "상추 가격", "상추 작황"],
        "feature_profile": "orchard",
    },
    {
        "topic": "고추",
        "rep_term": "고추",
        "display_name": "고추",
        "aliases": ["고추", "풋고추", "청양고추"],
        "focus_terms": ["고추", "풋고추", "청양고추"],
        "brief_tags": ["고추"],
        "supply_queries": ["풋고추 수급", "풋고추 가격", "고추 작황"],
        "feature_profile": "greenhouse",
    },
    {
        "topic": "화훼",
        "rep_term": "화훼",
        "display_name": "화훼",
        "aliases": ["화훼", "절화", "국화", "장미", "백합", "생화", "꽃시장", "화훼공판장"],
        "focus_terms": ["화훼", "절화", "생화", "꽃시장", "화훼공판장"],
        "brief_tags": ["화훼"],
        "supply_queries": [
            "화훼 가격", "절화 가격", "화훼 수급", "화훼자조금",
            "화훼 경매", "절화 경매", "화훼공판장 경매", "꽃시장 경매",
            "국화 경매", "장미 경매", "백합 가격", "생화 출하",
        ],
        "feature_profile": "flower",
    },
]


def _commodity_alias_terms(entry: JsonDict) -> list[str]:
    return _ordered_unique_terms(entry.get("aliases") or [])


def _commodity_must_terms(entry: JsonDict) -> list[str]:
    values = list(_commodity_alias_terms(entry))
    values.extend(entry.get("must_terms") or [])
    return _ordered_unique_terms(values)


def _commodity_focus_terms(entry: JsonDict) -> list[str]:
    values = list(entry.get("focus_terms") or [])
    if not values:
        values.extend(_commodity_alias_terms(entry))
    return _ordered_unique_terms(values)


def _commodity_tag_terms(entry: JsonDict) -> list[str]:
    values = list(entry.get("tag_terms") or [])
    if not values:
        values.extend(_commodity_alias_terms(entry))
        values.append(entry.get("topic") or "")
    return _ordered_unique_terms(values)


def _commodity_rep_term(entry: JsonDict) -> str:
    rep = str(entry.get("rep_term") or "").strip()
    if rep:
        return rep
    aliases = _commodity_alias_terms(entry)
    if aliases:
        return aliases[0]
    return str(entry.get("topic") or "").split("/")[0].strip()


ITEM_COMMODITY_TOPICS = [
    (str(entry.get("topic") or "").strip(), _commodity_alias_terms(entry))
    for entry in COMMODITY_REGISTRY
    if str(entry.get("topic") or "").strip()
]
ITEM_TOPIC_REP_BY_NAME = {
    str(entry.get("topic") or "").strip(): _commodity_rep_term(entry)
    for entry in COMMODITY_REGISTRY
    if str(entry.get("topic") or "").strip()
}
COMMODITY_FEATURE_PROFILE_BY_TERM_L = {
    (term or "").strip().lower(): str(entry.get("feature_profile") or "default").strip().lower() or "default"
    for entry in COMMODITY_REGISTRY
    for term in _ordered_unique_terms(
        [entry.get("topic") or "", _commodity_rep_term(entry)]
        + _commodity_alias_terms(entry)
        + _commodity_focus_terms(entry)
        + _commodity_tag_terms(entry)
        + list(entry.get("brief_tags") or [])
    )
    if (term or "").strip()
}
HORTI_CORE_MARKERS = _ordered_unique_terms(
    list(HORTI_CORE_GENERAL_TERMS)
    + [term for entry in COMMODITY_REGISTRY for term in _commodity_alias_terms(entry)]
    + [term for entry in COMMODITY_REGISTRY for term in _commodity_focus_terms(entry)]
)

COMMODITY_REGISTRY_BY_TOPIC = {
    str(entry.get("topic") or "").strip(): entry
    for entry in COMMODITY_REGISTRY
    if str(entry.get("topic") or "").strip()
}

MANAGED_COMMODITY_GROUP_SPECS: list[dict[str, Any]] = [
    {
        "key": "root_leaf",
        "title": "엽근채류",
        "color": "#0f766e",
        "items": [
            {"key": "radish", "label": "무", "short_label": "무", "program_core": True, "aliases": ["월동무", "봄무", "고랭지무"], "context_terms": ["무 가격", "무 수급", "무 도매가격", "무 작황", "무 출하", "무 재배"]},
            {"key": "napa_cabbage", "label": "배추", "short_label": "배추", "program_core": True, "aliases": ["배추", "봄배추", "김장배추"]},
            {"key": "potato", "label": "감자", "short_label": "감자", "program_core": True, "aliases": ["감자", "봄감자", "수미감자"]},
            {"key": "carrot", "label": "당근", "short_label": "당근", "program_core": True, "aliases": ["당근", "제주당근", "햇당근"]},
            {"key": "cabbage", "label": "양배추", "short_label": "양배추", "program_core": False, "aliases": ["양배추"]},
        ],
    },
    {
        "key": "seasoning_veg",
        "title": "양념채소류",
        "color": "#b45309",
        "items": [
            {"key": "onion", "label": "양파", "short_label": "양파", "program_core": True, "aliases": ["양파", "햇양파"]},
            {"key": "garlic", "label": "마늘", "short_label": "마늘", "program_core": True, "aliases": ["마늘", "깐마늘", "난지형 마늘", "한지형 마늘"]},
            {"key": "dry_red_pepper", "label": "건고추", "short_label": "건고추", "program_core": True, "aliases": ["건고추", "건조고추", "건고추값"], "context_terms": ["건고추 가격", "건고추 수급", "건고추 작황"]},
            {"key": "green_onion", "label": "대파", "short_label": "대파", "program_core": True, "aliases": ["대파", "쪽파"]},
            {"key": "ginger", "label": "생강", "short_label": "생강", "program_core": False, "aliases": ["생강"]},
        ],
    },
    {
        "key": "fruit_veg",
        "title": "과채류",
        "color": "#6d28d9",
        "items": [
            {"key": "tomato", "label": "토마토", "short_label": "토마토", "program_core": True, "registry_topics": ["토마토"]},
            {"key": "cucumber", "label": "오이", "short_label": "오이", "program_core": True, "registry_topics": ["오이"]},
            {"key": "green_pepper", "label": "풋고추", "short_label": "풋고추", "program_core": True, "aliases": ["풋고추", "청양고추", "꽈리고추"], "context_terms": ["고추 가격", "고추 수급", "고추 작황"]},
            {"key": "zucchini", "label": "애호박(쥬키니)", "short_label": "애호박", "program_core": True, "aliases": ["애호박", "쥬키니", "주키니"], "context_terms": ["애호박 가격", "애호박 수급", "쥬키니 가격"]},
            {"key": "oriental_melon", "label": "참외", "short_label": "참외", "program_core": False, "registry_topics": ["참외"]},
            {"key": "lettuce", "label": "상추", "short_label": "상추", "program_core": False, "registry_topics": ["상추"]},
            {"key": "strawberry", "label": "딸기", "short_label": "딸기", "program_core": False, "registry_topics": ["딸기"]},
            {"key": "eggplant", "label": "가지", "short_label": "가지", "program_core": True, "aliases": ["가지"], "context_terms": ["가지 가격", "가지 수급", "가지 작황", "가지 출하", "가지 재배"]},
            {"key": "paprika", "label": "파프리카", "short_label": "파프리카", "program_core": False, "registry_topics": ["파프리카"]},
            {"key": "muskmelon", "label": "멜론", "short_label": "멜론", "program_core": False, "registry_topics": ["멜론"]},
        ],
    },
    {
        "key": "fruit_flower",
        "title": "과수화훼류",
        "color": "#1d4ed8",
        "items": [
            {"key": "apple", "label": "사과", "short_label": "사과", "program_core": True, "registry_topics": ["사과"]},
            {"key": "pear", "label": "배", "short_label": "배", "program_core": True, "registry_topics": ["배"]},
            {"key": "persimmon", "label": "감/곶감", "short_label": "감", "program_core": False, "registry_topics": ["감/곶감"], "aliases": ["떫은감", "곶감", "반건시"], "context_terms": ["감 가격", "감 수급", "감 작황"]},
            {"key": "sweet_persimmon", "label": "단감", "short_label": "단감", "program_core": True, "registry_topics": ["단감"]},
            {"key": "peach", "label": "복숭아", "short_label": "복숭아", "program_core": False, "registry_topics": ["복숭아"]},
            {"key": "grape", "label": "포도(샤인머스캣)", "short_label": "포도", "program_core": True, "registry_topics": ["포도"]},
            {"key": "citrus", "label": "감귤(만감류)", "short_label": "감귤", "program_core": True, "registry_topics": ["감귤/만감"]},
            {"key": "maesil", "label": "매실", "short_label": "매실", "program_core": False, "registry_topics": ["매실"]},
            {"key": "citron", "label": "유자", "short_label": "유자", "program_core": False, "registry_topics": ["유자"]},
            {"key": "kiwifruit", "label": "참다래", "short_label": "참다래", "program_core": False, "registry_topics": ["키위"], "aliases": ["참다래"]},
            {"key": "chestnut", "label": "밤", "short_label": "밤", "program_core": False, "registry_topics": ["밤"]},
            {"key": "flowers", "label": "화훼", "short_label": "화훼", "program_core": False, "registry_topics": ["화훼"]},
            {"key": "plum", "label": "자두", "short_label": "자두", "program_core": False, "registry_topics": ["자두"]},
        ],
    },
]


def _build_managed_commodity_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    order_index = 0
    for group_order, group in enumerate(MANAGED_COMMODITY_GROUP_SPECS):
        group_key = str(group.get("key") or "").strip()
        group_title = str(group.get("title") or "").strip()
        group_color = str(group.get("color") or "#475569").strip() or "#475569"
        for item_order, spec in enumerate(group.get("items") or []):
            order_index += 1
            registry_topics = _ordered_unique_terms(spec.get("registry_topics") or [])
            registry_terms: list[str] = []
            for topic_name in registry_topics:
                entry = COMMODITY_REGISTRY_BY_TOPIC.get(topic_name)
                if not entry:
                    continue
                registry_terms.extend(
                    _ordered_unique_terms(
                        [entry.get("topic") or "", entry.get("display_name") or "", _commodity_rep_term(entry)]
                        + _commodity_alias_terms(entry)
                        + _commodity_focus_terms(entry)
                        + _commodity_tag_terms(entry)
                        + list(entry.get("brief_tags") or [])
                    )
                )
            match_terms = _ordered_unique_terms(list(spec.get("aliases") or []) + registry_terms)
            catalog.append(
                {
                    "key": str(spec.get("key") or "").strip(),
                    "label": str(spec.get("label") or "").strip(),
                    "short_label": str(spec.get("short_label") or spec.get("label") or "").strip(),
                    "group_key": group_key,
                    "group_title": group_title,
                    "group_color": group_color,
                    "group_order": group_order,
                    "item_order": item_order,
                    "order": order_index,
                    "program_core": bool(spec.get("program_core", False)),
                    "registry_topics": registry_topics,
                    "match_terms": match_terms,
                    "context_terms": _ordered_unique_terms(spec.get("context_terms") or []),
                }
            )
    return catalog


MANAGED_COMMODITY_CATALOG = _build_managed_commodity_catalog()
MANAGED_COMMODITY_BY_KEY = {str(item.get("key") or "").strip(): item for item in MANAGED_COMMODITY_CATALOG}
MANAGED_COMMODITY_KEY_BY_REGISTRY_TOPIC = {
    topic: item["key"]
    for item in MANAGED_COMMODITY_CATALOG
    for topic in item.get("registry_topics") or []
}


def _managed_only_commodity_items() -> list[dict[str, Any]]:
    return [item for item in MANAGED_COMMODITY_CATALOG if not list(item.get("registry_topics") or [])]


def _managed_commodity_base_terms(item: dict[str, Any], limit: int = 2) -> list[str]:
    values: list[str] = []
    label = str(item.get("label") or "").strip()
    short_label = str(item.get("short_label") or "").strip()
    plain_label = re.sub(r"\s*\([^)]*\)", "", label).strip()
    for term in [short_label, plain_label, label] + list(item.get("match_terms") or []):
        term_s = str(term or "").strip()
        if len(term_s) < 2 or term_s in values:
            continue
        values.append(term_s)
        if len(values) >= max(1, int(limit or 0)):
            break
    return values


def _managed_commodity_topic_terms(item: dict[str, Any]) -> list[str]:
    values: list[str] = []
    label = str(item.get("label") or "").strip()
    short_label = str(item.get("short_label") or "").strip()
    if len(label) >= 2:
        values.append(label)
    if len(short_label) >= 2:
        values.append(short_label)
    if len(short_label) == 1:
        values.extend([f"{short_label}값", f"{short_label} 가격", f"{short_label} 수급"])
    values.extend(item.get("match_terms") or [])
    values.extend(item.get("context_terms") or [])
    return _ordered_unique_terms(values)


def _managed_commodity_supply_query_buckets(item: dict[str, Any]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "market": [],
        "field": [],
        "response": [],
    }
    for term in item.get("context_terms") or []:
        term_s = str(term or "").strip()
        if not term_s:
            continue
        if any(sig in term_s for sig in ("가격", "도매가격", "수급")):
            buckets["market"].append(term_s)
        elif any(sig in term_s for sig in ("생육", "작황", "재배", "농가", "기후")):
            buckets["field"].append(term_s)
        else:
            buckets["response"].append(term_s)

    for base in _managed_commodity_base_terms(item, limit=2):
        buckets["market"].extend(
            [
                f"{base} 수급",
                f"{base} 가격",
                f"{base} 도매가격",
            ]
        )
        buckets["field"].extend(
            [
                f"{base} 생육",
                f"{base} 재배",
                f"{base} 작황",
                f"{base} 농가",
                f"{base} 산업",
                f"{base} 기후변화",
            ]
        )
        buckets["response"].extend(
            [
                f"{base} 소비 대책",
                f"{base} 소비 촉진",
                f"{base} 가격 하락",
                f"{base} 산지 물량",
                f"{base} 출하",
            ]
        )
        if bool(item.get("program_core")):
            buckets["response"].extend(
                [
                    f"{base} 수급 안정",
                    f"{base} 가격 안정",
                    f"{base} 출하 조절",
                ]
            )
    return {
        key: _ordered_unique_terms(values)
        for key, values in buckets.items()
    }


def _managed_commodity_supply_queries(item: dict[str, Any]) -> list[str]:
    buckets = _managed_commodity_supply_query_buckets(item)
    return _ordered_unique_terms(
        list(buckets.get("market") or [])
        + list(buckets.get("field") or [])
        + list(buckets.get("response") or [])
    )


def _managed_commodity_pest_queries(item: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for idx, base in enumerate(_managed_commodity_base_terms(item, limit=2)):
        out.append(f"{base} 병해충")
        out.append(f"{base} 방제")
        out.append(f"{base} 예찰")
        out.append(f"{base} 약제 공급")
        out.append(f"{base} 정밀예찰")
        out.append(f"{base} 선충")
        if idx == 0:
            out.append(f"{base} 냉해")
            out.append(f"{base} 생육 관리")
            out.append(f"{base} 피해")
            out.append(f"{base} 무상 공급")
            out.append(f"{base} 전수조사")
            out.append(f"{base} 현장지도")
    return _ordered_unique_terms(out)


def _managed_commodity_must_terms(item: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for term in item.get("match_terms") or []:
        term = str(term or "").strip()
        if len(term) >= 2:
            values.append(term)
    values.extend(item.get("context_terms") or [])
    return _ordered_unique_terms(values)


MANAGED_ONLY_COMMODITY_ITEMS = _managed_only_commodity_items()
MANAGED_ONLY_COMMODITY_TOPICS = [
    (str(item.get("label") or "").strip(), _managed_commodity_topic_terms(item))
    for item in MANAGED_ONLY_COMMODITY_ITEMS
    if str(item.get("label") or "").strip()
]
MANAGED_ONLY_SUPPLY_QUERIES = _ordered_unique_terms(
    query
    for item in MANAGED_ONLY_COMMODITY_ITEMS
    for query in _managed_commodity_supply_queries(item)
)
MANAGED_ONLY_SUPPLY_MUST_TERMS = _ordered_unique_terms(
    term
    for item in MANAGED_ONLY_COMMODITY_ITEMS
    for term in _managed_commodity_must_terms(item)
)
MANAGED_PEST_RECALL_QUERIES = _ordered_unique_terms(
    query
    for item in MANAGED_COMMODITY_CATALOG
    for query in _managed_commodity_pest_queries(item)
)
MANAGED_PEST_PRIMARY_CORE_QUERIES = _ordered_unique_terms(
    queries[0]
    for item in MANAGED_COMMODITY_CATALOG
    if bool(item.get("program_core"))
    for queries in [_managed_commodity_pest_queries(item)]
    if queries
)
MANAGED_PEST_PRIMARY_OTHER_QUERIES = _ordered_unique_terms(
    queries[0]
    for item in MANAGED_COMMODITY_CATALOG
    if not bool(item.get("program_core"))
    for queries in [_managed_commodity_pest_queries(item)]
    if queries
)
MANAGED_PEST_ROTATING_QUERIES = _ordered_unique_terms(
    query
    for item in MANAGED_COMMODITY_CATALOG
    for idx, query in enumerate(_managed_commodity_pest_queries(item))
    if idx > 0
)
MANAGED_PEST_ROTATING_QUERY_CAP = 18
MANAGED_SECTION_PRIMARY_QUERY_CAP = {
    "supply": 16,
    "policy": 12,
    "dist": 12,
}
MANAGED_SECTION_PRIMARY_CORE_BONUS_CAP = {
    "supply": 4,
    "policy": 3,
    "dist": 3,
}
MANAGED_SECTION_ROTATING_QUERY_CAP = {
    "supply": 10,
    "policy": 8,
    "dist": 8,
}


def _rotated_query_slice(queries: list[str], seed: int, cap: int) -> list[str]:
    if not queries or cap <= 0:
        return []
    if cap >= len(queries):
        return list(queries)
    start = seed % len(queries)
    ordered = list(queries[start:]) + list(queries[:start])
    return ordered[:cap]


def _interleave_ordered_groups(*groups: Sequence[str]) -> list[str]:
    normalized_groups: list[list[str]] = []
    for group in groups:
        normalized: list[str] = []
        for value in group or []:
            value_s = str(value or "").strip()
            if value_s:
                normalized.append(value_s)
        if normalized:
            normalized_groups.append(normalized)
    if not normalized_groups:
        return []

    out: list[str] = []
    max_len = max(len(group) for group in normalized_groups)
    for idx in range(max_len):
        for group in normalized_groups:
            if idx >= len(group):
                continue
            value = group[idx]
            if value not in out:
                out.append(value)
    return out


MANAGED_GROUP_RECALL_QUERY_BANK: dict[str, dict[str, list[str]]] = {
    "supply": {
        "root_leaf": ["노지채소 수급", "노지채소 가격", "월동채소 가격", "겨울채소 소비 대책"],
        "seasoning_veg": ["양념채소 수급", "양념채소 가격", "양념채소 소비 대책"],
        "fruit_flower": ["과수 수급", "과수 생육", "과수 농가", "과수 기후변화"],
        "fruit_veg": ["시설채소 수급", "시설채소 가격", "시설채소 생육"],
    },
    "policy": {
        "root_leaf": ["채소 물가 특별관리", "채소 수급 안정", "노지채소 가격 안정", "채소 가격안정 지원사업", "채소 수급 관리센터"],
        "seasoning_veg": ["양념채소 물가 특별관리", "양념채소 수급 안정", "양념채소 가격안정 지원사업"],
        "fruit_flower": ["과수 물가 특별관리", "과수 수급 안정", "과수 정책", "과수 가격안정 지원사업", "과수 시범사업"],
        "fruit_veg": ["시설채소 수급 안정", "시설채소 정책", "시설채소 가격안정 지원사업", "시설채소 시범사업"],
    },
    "dist": {
        "root_leaf": ["노지채소 유통", "노지채소 소비 대책", "노지채소 도매가격"],
        "seasoning_veg": ["양념채소 유통", "양념채소 소비 촉진", "양념채소 공동판매"],
        "fruit_flower": ["과수 유통", "과수 공동판매", "과수 온라인 유통채널"],
        "fruit_veg": ["시설채소 유통", "시설채소 공동판매", "시설채소 온라인 유통채널"],
    },
}


def _balanced_managed_catalog_items() -> list[dict[str, Any]]:
    grouped_items: list[list[dict[str, Any]]] = []
    for group in MANAGED_COMMODITY_GROUP_SPECS:
        group_key = str(group.get("key") or "").strip()
        items = [
            item
            for item in MANAGED_COMMODITY_CATALOG
            if str(item.get("group_key") or "").strip() == group_key
        ]
        items.sort(
            key=lambda item: (
                0 if item.get("program_core") else 1,
                int(item.get("item_order") or 0),
                int(item.get("order") or 0),
            )
        )
        if items:
            grouped_items.append(items)
    if not grouped_items:
        return list(MANAGED_COMMODITY_CATALOG)

    out: list[dict[str, Any]] = []
    max_len = max(len(items) for items in grouped_items)
    for idx in range(max_len):
        for items in grouped_items:
            if idx < len(items):
                out.append(items[idx])
    return out


def _pick_rotated_item_queries(
    queries: Sequence[str],
    seed: int,
    order: int,
    count: int,
    phase: int = 0,
) -> list[str]:
    normalized = _ordered_unique_terms(
        str(query or "").strip()
        for query in (queries or [])
        if str(query or "").strip()
    )
    if not normalized or count <= 0:
        return []
    if count >= len(normalized):
        return list(normalized)
    start = (seed + (order * 5) + (phase * 7)) % len(normalized)
    ordered = list(normalized[start:]) + list(normalized[:start])
    return ordered[:count]


def _managed_group_recall_queries(section_key: str, seed: int) -> list[str]:
    bank = MANAGED_GROUP_RECALL_QUERY_BANK.get(str(section_key or "").strip(), {})
    if not bank:
        return []
    out: list[str] = []
    for idx, group in enumerate(MANAGED_COMMODITY_GROUP_SPECS):
        group_key = str(group.get("key") or "").strip()
        queries = bank.get(group_key) or []
        out.extend(_pick_rotated_item_queries(queries, seed, idx + 1, 1))
    return _ordered_unique_terms(out)


def _managed_commodity_policy_queries(item: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for base in _managed_commodity_base_terms(item, limit=2):
        out.append(f"{base} 수급 안정")
        out.append(f"{base} 가격 안정")
        out.append(f"{base} 가격안정 지원사업")
        out.append(f"{base} 가격안정 대책")
        out.append(f"{base} 최저 가격 지원")
        out.append(f"{base} 가격 폭락 방지")
        out.append(f"{base} 수급 안정 대책")
        out.append(f"{base} 건의안")
        out.append(f"{base} 건의안 발의")
        out.append(f"{base} 특별관리")
        out.append(f"{base} 물가 특별관리")
        out.append(f"{base} 정책")
        out.append(f"{base} 제도 개선")
        out.append(f"{base} 협의체")
        out.append(f"{base} 수급 관리센터")
        out.append(f"{base} 시범사업")
        out.append(f"{base} 할인지원")
        out.append(f"{base} 검역")
    return _ordered_unique_terms(out)


def _managed_commodity_dist_queries(item: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for base in _managed_commodity_base_terms(item, limit=2):
        out.append(f"{base} 경매")
        out.append(f"{base} 공판장")
        out.append(f"{base} 산지유통")
        out.append(f"{base} 유통현장")
        out.append(f"{base} 도매가격")
        out.append(f"{base} 소비 대책")
        out.append(f"{base} 공동판매")
        out.append(f"{base} 직거래")
        out.append(f"{base} 통합마케팅")
        out.append(f"{base} 온라인 유통채널")
        out.append(f"{base} 온라인도매시장 거래")
        out.append(f"{base} 출하비용 보전")
        out.append(f"{base} 물량 통합관리")
        out.append(f"{base} 수출 선적")
        out.append(f"{base} 선적식")
        out.append(f"{base} 수출 지원 허브")
    return _ordered_unique_terms(out)


def _managed_section_query_builder(section_key: str) -> Callable[[dict[str, Any]], list[str]] | None:
    if section_key == "supply":
        return _managed_commodity_supply_queries
    if section_key == "policy":
        return _managed_commodity_policy_queries
    if section_key == "dist":
        return _managed_commodity_dist_queries
    if section_key == "pest":
        return _managed_commodity_pest_queries
    return None


def _managed_section_primary_queries(section_key: str, include_all: bool = False) -> list[str]:
    builder = _managed_section_query_builder(section_key)
    if builder is None:
        return []
    out: list[str] = []
    for item in MANAGED_COMMODITY_CATALOG:
        if section_key != "pest" and (not include_all) and not bool(item.get("program_core")):
            continue
        queries = builder(item)
        if queries and queries[0] not in out:
            out.append(queries[0])
    return out


def _managed_section_rotating_queries(section_key: str) -> list[str]:
    builder = _managed_section_query_builder(section_key)
    if builder is None:
        return []
    out: list[str] = []
    for item in MANAGED_COMMODITY_CATALOG:
        queries = builder(item)
        if not queries:
            continue
        for idx, query in enumerate(queries):
            if section_key == "pest":
                if idx == 0:
                    continue
            elif bool(item.get("program_core")) and idx == 0:
                continue
            if query not in out:
                out.append(query)
    return out


def build_managed_section_recall_queries(section_key: str, anchor_dt: datetime | None) -> list[str]:
    seed = 0
    try:
        if anchor_dt is not None:
            seed = int(anchor_dt.date().toordinal())
    except Exception:
        seed = 0
    section_key = str(section_key or "").strip()
    if section_key == "pest":
        rotating_queries = _managed_section_rotating_queries(section_key)
        return _ordered_unique_terms(
            list(MANAGED_PEST_PRIMARY_CORE_QUERIES)
            + list(MANAGED_PEST_PRIMARY_OTHER_QUERIES)
            + _rotated_query_slice(list(rotating_queries), seed, MANAGED_PEST_ROTATING_QUERY_CAP)
        )
    items = _balanced_managed_catalog_items()
    group_queries = _managed_group_recall_queries(section_key, seed)
    if section_key == "supply":
        balanced_queries: list[str] = []
        for item in items:
            order = int(item.get("order") or 0)
            buckets = _managed_commodity_supply_query_buckets(item)
            balanced_queries.extend(
                _pick_rotated_item_queries(buckets.get("market") or [], seed, order, 1, phase=0)
            )
            balanced_queries.extend(
                _pick_rotated_item_queries(buckets.get("field") or [], seed, order, 1, phase=1)
            )
            if item.get("program_core"):
                balanced_queries.extend(
                    _pick_rotated_item_queries(buckets.get("response") or [], seed, order, 1, phase=2)
                )
        return _ordered_unique_terms(list(group_queries) + balanced_queries)

    builder = _managed_section_query_builder(section_key)
    if builder is None:
        return []

    balanced_queries: list[str] = []
    for item in items:
        order = int(item.get("order") or 0)
        balanced_queries.extend(
            _pick_rotated_item_queries(builder(item), seed, order, 1, phase=0)
        )

    if section_key in ("policy", "dist"):
        return _ordered_unique_terms(list(group_queries) + balanced_queries)
    return _ordered_unique_terms(balanced_queries)


def build_managed_pest_recall_queries(anchor_dt: datetime | None) -> list[str]:
    return build_managed_section_recall_queries("pest", anchor_dt)

MANAGED_ONLY_TOPIC_REP_BY_NAME = {
    str(item.get("label") or "").strip(): str(item.get("short_label") or item.get("label") or "").strip()
    for item in MANAGED_ONLY_COMMODITY_ITEMS
    if str(item.get("label") or "").strip()
}
ALL_ITEM_COMMODITY_TOPICS = list(ITEM_COMMODITY_TOPICS) + list(MANAGED_ONLY_COMMODITY_TOPICS)
HORTI_CORE_MARKERS = _ordered_unique_terms(
    list(HORTI_CORE_MARKERS)
    + [term for _topic, terms in MANAGED_ONLY_COMMODITY_TOPICS for term in terms]
)


def _commodity_tags_in_text(text: str, limit: int = 9) -> list[str]:
    txt = (text or "").lower()
    if not txt:
        return []
    cap = max(0, int(limit or 0))
    if cap == 0:
        return []

    out: list[str] = []
    for entry in COMMODITY_REGISTRY:
        topic = str(entry.get("topic") or "").strip()
        matched = False

        for term in _commodity_tag_terms(entry):
            term_l = (term or "").strip().lower()
            if len(term_l) >= 2 and term_l in txt:
                matched = True
                break

        if not matched:
            if topic == "배":
                matched = any(p.search(txt) for p in _SINGLE_TERM_CONTEXT_PATTERNS["배"])
            elif topic == "밤":
                matched = any(p.search(txt) for p in _SINGLE_TERM_CONTEXT_PATTERNS["밤"])
            elif topic == "화훼":
                matched = any(p.search(txt) for p in _SINGLE_TERM_CONTEXT_PATTERNS["꽃"])
            elif topic == "감귤/만감":
                matched = any(p.search(txt) for p in _SINGLE_TERM_CONTEXT_PATTERNS["귤"])

        if not matched:
            continue

        for tag in _ordered_unique_terms(list(entry.get("brief_tags") or []) + [str(entry.get("display_name") or "").strip()]):
            tag = (tag or "").strip()
            if tag and tag not in out:
                out.append(tag)
            if len(out) >= cap:
                return out
    for item in MANAGED_ONLY_COMMODITY_ITEMS:
        label = str(item.get("label") or "").strip()
        if not label or label in out:
            continue
        if _managed_commodity_matches_text(item, txt):
            out.append(label)
            if len(out) >= cap:
                return out
    return out


SUPPLY_ITEM_QUERIES = _ordered_unique_terms(
    q
    for entry in COMMODITY_REGISTRY
    for q in (entry.get("supply_queries") or [])
)
SUPPLY_ITEM_QUERIES = _ordered_unique_terms(
    list(SUPPLY_ITEM_QUERIES) + list(MANAGED_ONLY_SUPPLY_QUERIES)
)
SUPPLY_ITEM_MUST_TERMS = _ordered_unique_terms(
    term
    for entry in COMMODITY_REGISTRY
    for term in _commodity_must_terms(entry)
)
SUPPLY_ITEM_MUST_TERMS = _ordered_unique_terms(
    list(SUPPLY_ITEM_MUST_TERMS) + list(MANAGED_ONLY_SUPPLY_MUST_TERMS)
)
SUPPLY_CONTEXT_QUERIES = [
    "과수 묘목 품귀",
    "과수 묘목",
    "산불 과수",
    "기후변화 과수",
    "과수 농가 울상",
]
SUPPLY_TITLE_FOCUS_TERMS_L = [
    term.lower()
    for term in _ordered_unique_terms(
        ["과일", "채소", "농산물", "청과", "수급", "작황", "출하", "반입", "경락"]
        + [term for entry in COMMODITY_REGISTRY for term in _commodity_focus_terms(entry)]
        + [term for _topic, terms in MANAGED_ONLY_COMMODITY_TOPICS for term in terms]
    )
]
MACRO_POLICY_KEEP_TERMS = _ordered_unique_terms(
    ["농산물", "농식품", "농식품부", "과일", "채소", "공급", "수급", "안정", "안정화"]
    + [term for entry in COMMODITY_REGISTRY for term in _commodity_focus_terms(entry)]
    + [term for _topic, terms in MANAGED_ONLY_COMMODITY_TOPICS for term in terms]
)
POLICY_MARKET_BRIEF_QUERIES = [
    "농축산물 가격 동향",
    "농산물 가격 동향",
    "과일 채소 가격 동향",
    "과일류 가격 동향",
    "농산물 수급 동향",
    "농식품부 수급 점검",
    "농식품부 가격 점검",
    "농산물 가격 전반 하락",
    "과일류 가격 전년 대비",
    "농산물 수급 영향 제한적",
    "정부 가용물량 과일",
]
POLICY_MARKET_BRIEF_RECALL_SIGNALS = ["가격 동향", "수급 영향", "전년 대비", "가용물량", "점검 결과", "영향 제한적"]
POLICY_MAJOR_ISSUE_QUERIES = [
    "농식품부 농산물 유통 전문가 협의체",
    "농산물 유통 전문가 협의체",
    "농산물 유통 구조 개선",
    "농산물 가격 결정 구조 개선",
    "농산물 최소가격 보전제",
    "주요 농산물 가격안정 지원사업",
    "농산물 가격안정 지원사업",
    "농산물 최저 가격 지원사업",
    "농산물 가격 폭락 방지 대책",
    "농산물 수급 안정 대책",
    "농산물 수급 안정 건의안",
    "농산물 가격안정 건의안",
    "농업용 면세유 대책",
    "농업용 면세유 가격 대책",
    "농산물 생산비 지원 대책",
    "농산물 특별관리 품목",
    "농산물 광역 수급 관리센터",
    "농산물 광역수급관리센터",
    "농산물 수급 관리센터",
    "원예 시범사업",
]

# -----------------------------
# Sections
# -----------------------------
SECTIONS: list[SectionConfig] = [
    {
        "key": "supply",
        "title": "품목 및 수급 동향",
        "color": "#0f766e",
        "queries": list(SUPPLY_ITEM_QUERIES) + list(SUPPLY_CONTEXT_QUERIES),
        "must_terms": list(SUPPLY_GENERAL_MUST_TERMS) + list(SUPPLY_ITEM_MUST_TERMS),
    },
    {
        "key": "policy",
        "title": "정책 및 주요 이슈",
        "color": "#1d4ed8",
        "queries": [
            "농식품부 정책브리핑", "농식품부 보도자료 농산물", "정책브리핑 농축수산물", "농축수산물 할인지원",
            "성수품 가격 안정 대책", "할당관세 과일 검역", "원산지 단속 농산물", "온라인 도매시장 농식품부",
            "설 이후 과일 가격 하락", "사과 배 가격 하락", "성수품 물가 과일", "차례상 물가 과일",
            "소비자물가 과일 사과 배", "KOSIS 소비자물가 사과 배", "물가정보 설 과일",
        ] + list(POLICY_MARKET_BRIEF_QUERIES) + list(POLICY_MAJOR_ISSUE_QUERIES),
        "must_terms": [
            "정책", "대책", "지원", "할인", "할당관세", "검역", "보도자료", "브리핑", "온라인 도매시장",
            "원산지", "물가", "가격", "상승", "하락", "급등", "성수품", "차례상", "소비자물가", "물가지수",
            "통계", "KOSIS",
            "협의체", "위원회", "출범", "특별관리", "최소가격", "보전제",
            "제도 개선", "제도개선", "구조 개선", "구조개선", "가격 결정 구조",
        ],
    },
    {
        "key": "dist",
        "title": "유통 및 현장 (도매시장/APC/수출)",
        "color": "#6d28d9",
        "queries": [
            "가락시장 청과 경락",
            "가락시장 경락가",
            "도매시장 청과 경락",
            "도매시장 반입량",
            "도매시장 수급",
            "공영도매시장 경매",
            "공판장 청과 경매",
            "시장도매인제 도매시장",
            "온라인 도매시장 청과",
            "온라인 도매시장 제도 개선",
            "도매시장 제도 개선",
            "품목농협 산지유통",
            "원예농협 산지유통",
            "농협 연합판매사업 직거래",
            "연합판매사업 직거래",
            "연합판매사업 직거래 활성화",
            "품목농협 공동선별",
            "품목농협 경제사업",
            "원예농협 경제사업",
            "품목농협 조합원 실익",
            "농산물 판로 확대",
            "농산물 공동구매",
            "농산물 직거래 장터",
            "농산물 유통 거점",
            "푸드통합지원센터 직거래",
            "원예농협 지도 구매 유통 가공",
            "품목농협 지도 구매 유통 가공",
            "과수 전문 품목농협",
            "산지유통센터 준공",
            "스마트 농산물 산지유통센터 준공",
            "스마트 APC 준공",
            "APC 산지유통센터 준공",
            "APC 저온저장",
            "CA저장 과일",
            "농산물 수출 검역",
            "과일 수출 검역",
            "통관 과일 검역",
            "수출업계 간담회 농식품부",
            "비관세장벽 수출 농식품부",
            "농산물 수출 선적",
            "과일 수출 선적",
            "농산물 선적식",
            "농산물 온라인도매시장 거래",
            "농산물 출하비용 보전",
            "농산물 수출 지원 허브",
            "통합마케팅 출하",
            "농산물 광역수급관리센터",
            "광역수급관리센터 수급 관리",
            "화훼공판장 경매",
            "절화 경매",
        ],
        "must_terms": [
            "가락시장",
            "도매시장",
            "공영도매시장",
            "공판장",
            "청과",
            "경락",
            "경락가",
            "경매",
            "반입",
            "시장도매인",
            "온라인 도매시장",
            "산지유통",
            "산지유통센터",
            "apc",
            "스마트 apc",
            "직거래",
            "연합판매사업",
            "광역수급관리센터",
            "수급관리센터",
            "준공",
            "저온저장",
            "ca저장",
            "저장고",
            "수출",
            "선적",
            "수출길",
            "검역",
            "통관",
            "화훼",
            "절화",
            "화훼공판장",
        ],
    },
    {
        "key": "pest",
        "title": "생육 리스크 및 방제",
        "color": "#b45309",
        "queries": [
            "과수화상병 방제", "탄저병 방제", "월동 해충 방제",
            "냉해 동해 과수 피해", "병해충 예찰 방제", "생육 관리 저온피해",
        ],
        "must_terms": ["방제", "병해충", "약제", "살포", "예찰", "과수화상병", "탄저병", "냉해", "동해", "저온피해", "서리", "생육", "월동"],
    },
]


# -----------------------------
# Topic diversity
# -----------------------------
NON_ITEM_COMMODITY_TOPICS = [
    ("도매시장", ["가락시장", "도매시장", "공영도매시장", "공판장", "청과", "경락", "경매", "반입", "중도매인", "시장도매인", "온라인 도매시장"]),
    ("APC/산지유통", ["apc", "산지유통", "산지유통센터", "선별", "저온", "저장", "ca저장", "물류"]),
    ("수출/검역", ["수출", "검역", "통관", "수입검역", "잔류농약"]),
    ("정책", ["대책", "지원", "보도자료", "브리핑", "할당관세", "할인지원", "원산지", "단속", "고시", "개정"]),
    ("병해충", ["병해충", "방제", "예찰", "약제", "살포", "과수화상병", "탄저병", "노균병", "냉해", "동해", "저온피해", "생육"]),
]
COMMODITY_TOPICS = list(ITEM_COMMODITY_TOPICS) + list(NON_ITEM_COMMODITY_TOPICS)
COMMODITY_TOPICS = list(ALL_ITEM_COMMODITY_TOPICS) + list(NON_ITEM_COMMODITY_TOPICS)

# Alias for generalized topic signals & fallback query generation
TOPICS = COMMODITY_TOPICS
TOPIC_REP_BY_NAME_L = dict(ITEM_TOPIC_REP_BY_NAME)
TOPIC_REP_BY_NAME_L.update(MANAGED_ONLY_TOPIC_REP_BY_NAME)
TOPIC_REP_BY_NAME_L.update({
    name: ((terms[0] if terms else (name.split("/")[0] if name else "")).strip())
    for name, terms in NON_ITEM_COMMODITY_TOPICS
})
TOPIC_REP_BY_TERM_L = {
    (term or "").strip().lower(): (TOPIC_REP_BY_NAME_L.get(name) or (name.split("/")[0] if name else "")).strip().lower()
    for name, terms in TOPICS
    for term in ([name] + list(terms or []))
    if (term or "").strip()
}
# -----------------------------
# Cross-topic signals (generalized)
# -----------------------------
# 전체 토픽 키워드(소문자). 특정 기사/이슈에 맞춘 하드코딩이 아니라,
# '품목(원예) 신호' + '무역/정책 신호'가 함께 나올 때 핵심성을 일반적으로 올려준다.
ALL_TOPIC_TERMS_L = sorted({
    (t or "").strip().lower()
    for _tn, _terms in TOPICS
    for t in (_terms or [])
    if (t or "").strip()
})
NON_ITEM_TOPIC_NAMES = {"도매시장", "APC/산지유통", "수출/검역", "정책", "병해충"}
HORTI_ITEM_TERMS_L = sorted({
    (t or "").strip().lower()
    for _tn, _terms in TOPICS
    if _tn not in NON_ITEM_TOPIC_NAMES
    for t in (_terms or [])
    if (t or "").strip()
})

TRADE_POLICY_TERMS_L = [
    "수입", "수입산", "수입 과일", "수입 농산물",
    "관세", "할당관세", "무관세", "fta", "통관", "검역", "수입검역",
    "보세", "보세구역", "반입", "반출", "수입신고", "관세청",
]

TRADE_IMPACT_TERMS_L = [
    "잠식", "대체", "경쟁", "타격", "우려", "압박", "충격",
    "가격 하락", "가격 상승", "수급", "물량", "재고", "출하",
    "국내산", "농가", "생산자", "산지",
]


# -----------------------------
# Data model
# -----------------------------
@dataclass
class Article:
    section: str
    title: str
    description: str
    link: str
    originallink: str
    pub_dt_kst: datetime
    domain: str
    press: str
    norm_key: str
    title_key: str
    canon_url: str
    topic: str
    is_core: bool = False
    score: float = 0.0
    summary: str = ""
    forced_section: str = ""
    origin_section: str = ""
    source_query: str = ""
    source_channel: str = ""
    selection_stage: str = ""
    selection_note: str = ""
    selection_fit_score: float = 0.0
    reassigned_from: str = ""

    @property
    def url(self) -> str:
        return self.originallink or self.link or self.canon_url


_LAST_COMMODITY_BOARD_SOURCE_BY_SECTION: dict[str, list["Article"]] = {}


def _set_last_commodity_board_source(source: dict[str, list["Article"]] | None) -> None:
    global _LAST_COMMODITY_BOARD_SOURCE_BY_SECTION
    data: dict[str, list["Article"]] = {}
    for sec in SECTIONS:
        key = str(sec.get("key") or "").strip()
        if not key:
            continue
        items = []
        for article in (source or {}).get(key, []) or []:
            if isinstance(article, Article):
                items.append(article)
        data[key] = items
    _LAST_COMMODITY_BOARD_SOURCE_BY_SECTION = data


def _get_last_commodity_board_source() -> dict[str, list["Article"]]:
    data = _LAST_COMMODITY_BOARD_SOURCE_BY_SECTION or {}
    return {
        str(sec.get("key") or "").strip(): list(data.get(str(sec.get("key") or "").strip(), []) or [])
        for sec in SECTIONS
        if str(sec.get("key") or "").strip()
    }


def build_managed_commodity_board_source_by_section(
    by_section: dict[str, list["Article"]],
    per_section_cap: int | None = None,
) -> dict[str, list["Article"]]:
    cap = max(24, int(per_section_cap or max(MAX_PER_SECTION * 18, 120)))
    out: dict[str, list["Article"]] = {}
    for sec in SECTIONS:
        section_key = str(sec.get("key") or "").strip()
        picked: list[Article] = []
        seen_keys: set[str] = set()
        for article in sorted(by_section.get(section_key, []) or [], key=_sort_key_major_first, reverse=True):
            if not isinstance(article, Article):
                continue
            if not managed_commodity_keys_for_article(article):
                continue
            if _postbuild_article_reject_reason(article, section_key):
                continue
            dedupe_key = article.canon_url or article.norm_key or article.title_key or article.url
            if not dedupe_key or dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            picked.append(article)
            if len(picked) >= cap:
                break
        out[section_key] = picked
    return out


# -----------------------------
# Utilities
# -----------------------------
def now_kst() -> datetime:
    return datetime.now(tz=KST)

def dt_kst(d: date, hour: int) -> datetime:
    return datetime(d.year, d.month, d.day, hour, 0, 0, tzinfo=KST)

def parse_pubdate_to_kst(pubdate_str: str) -> datetime:
    try:
        dt = parsedate_to_datetime(pubdate_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST)
    except Exception:
        return datetime.min.replace(tzinfo=KST)


def _best_effort_article_pubdate_kst(url: str) -> datetime | None:
    """Best-effort article publish datetime extraction (KST).

    - 1차: URL 패턴(예: newsis NISXYYYYMMDD)에서 날짜 추정
    - 2차: 본문 HTML 메타태그에서 datetime 추출(가벼운 regex)
    """
    try:
        u = str(url or "").strip()
        if not u:
            return None

        m = re.search(r"NISX(\d{8})", u)
        if m:
            ds = m.group(1)
            d = datetime.strptime(ds, "%Y%m%d").date()
            return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=KST)

        r = http_session().get(u, timeout=12)
        if not r.ok:
            return None
        txt = r.text or ""

        pats = [
            r'article:published_time"\s*content="([^"]+)"',
            r'property="og:published_time"\s*content="([^"]+)"',
            r'name="pubdate"\s*content="([^"]+)"',
            r'itemprop="datePublished"\s*content="([^"]+)"',
            r'"datePublished"\s*:\s*"([^"]+)"',
        ]
        cand = None
        for ptn in pats:
            mm = re.search(ptn, txt, flags=re.I)
            if mm:
                cand = (mm.group(1) or "").strip()
                break
        if not cand:
            return None

        cand2 = cand.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cand2)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            return dt.astimezone(KST)
        except Exception:
            pass

        m2 = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})(?:\s+[T]?(\d{1,2}):(\d{2}))?", cand)
        if m2:
            yy, mo, dd = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            hh = int(m2.group(4)) if m2.group(4) else 12
            mi = int(m2.group(5)) if m2.group(5) else 0
            return datetime(yy, mo, dd, hh, mi, 0, tzinfo=KST)
    except Exception:
        return None
    return None


def _date_hint_from_url(url: str) -> date | None:
    try:
        parsed = urlparse(str(url or "").strip())
        path = parsed.path or ""
        for ptn in (r"/(20\d{2})/(\d{2})/(\d{2})(?:/|$)", r"/article/(20\d{2})(\d{2})(\d{2})\d*"):
            mm = re.search(ptn, path)
            if not mm:
                continue
            yy, mo, dd = int(mm.group(1)), int(mm.group(2)), int(mm.group(3))
            return date(yy, mo, dd)
        mm2 = re.search(r"(20\d{2})(\d{2})(\d{2})", path)
        if mm2:
            yy, mo, dd = int(mm2.group(1)), int(mm2.group(2)), int(mm2.group(3))
            return date(yy, mo, dd)
    except Exception:
        return None
    return None


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url: str) -> str:
    """URL의 도메인(호스트명).
    - m., www. 같은 일반 서브도메인은 제거해 매체 매핑/중복키/필터가 일관되게 동작하도록 한다.
    """
    try:
        u = urlparse(url)
        host = (u.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host.startswith("m."):
            host = host[2:]
        return host
    except Exception:
        return ""

def strip_tracking_params(url: str) -> str:
    try:
        u = urlparse(url)
        q = [(k, v) for (k, v) in parse_qsl(u.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in ("gclid", "fbclid", "igshid", "ref", "outurl", "nclick")]
        new_q = urlencode(q, doseq=True)
        return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))
    except Exception:
        return url

def canonicalize_url(url: str) -> str:
    url = strip_tracking_params(url or "").strip()
    if not url:
        return ""
    try:
        u = urlparse(url)
        host = (u.hostname or "").lower()
        for pfx in ("www.", "m.", "mobile."):
            if host.startswith(pfx):
                host = host[len(pfx):]
        scheme = "https" if u.scheme in ("http", "https") else "https"
        netloc = host
        path = u.path or "/"
        frag = ""
        return urlunparse((scheme, netloc, path, "", u.query or "", frag))
    except Exception:
        return url

def norm_title_key(title: str) -> str:
    t = (title or "").lower()
    t = re.sub(r"\[[^\]]+\]", " ", t)
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"[^0-9a-z가-힣]+", "", t)
    return t[:90]

# -----------------------------
# Story-level dedupe (title + description)
# - 목적: 동일 보도자료/브리핑이 여러 매체(연합뉴스/이데일리/파이낸셜뉴스 등)로 반복될 때 1건만 남기기
# - 제목만으로는 못 잡는 "같은 내용 다른 제목" 중복을 줄이기 위해 사용
# - dist(유통/현장) 섹션은 보도자료 중복이 많아, '스토리 시그니처' + 앵커 기반 판정을 우선 적용
# -----------------------------
_STORY_ANCHORS = (
    "서울시", "농수산물", "농산물", "부적합", "가락시장", "도매시장", "공판장", "공영도매시장",
    "경락", "경매", "반입", "수거", "수거검사", "불시", "검사", "휴일", "심야",
    "원산지", "부정유통", "단속", "검역", "통관", "수출",
    "유가", "상토", "난방비", "운송비", "꽃샘추위", "한파", "냉해", "동해",
    "잔류농약", "방사능", "식품안전", "위해", "유통", "차단", "사전", "폐기",
)

_SUPPLY_EVENT_ANCHOR_GROUPS = (
    ("유가", ("유가", "국제유가", "유류비", "기름값")),
    ("상토", ("상토", "원예용 상토")),
    ("난방", ("난방비", "난방", "연료비")),
    ("운송", ("운송비", "물류비", "해상운임")),
    ("저온", ("꽃샘추위", "한파", "저온", "냉해", "동해", "서리")),
    ("자재", ("농자재", "자재비", "비료", "포장재")),
    ("블라인드", ("블라인드", "블라인드 테스트", "테스트", "시식")),
    ("선호", ("선호도", "선호", "호응")),
    ("비교", ("비교", "대결", "대조")),
    ("품질", ("품질", "경쟁력", "맛", "당도", "압도", "평가")),
    ("수입산", ("수입산", "수입", "만다린", "국내산")),
)
_SUPPLY_ORG_PROMO_RX = re.compile(r"(?:\(?사\)?\s*)?([가-힣]{2,20}(?:연합회|협회|농협|원예농협|조합|공선회))")
_SUPPLY_ORG_PROMO_TERMS = (
    "홍보", "제철", "출하 시기", "출하시기", "선보여", "선봬", "소개", "진수", "민속촌",
)
_AGRI_ORG_EVENT_RX = _SUPPLY_ORG_PROMO_RX
_DIST_COOP_ORG_RX = re.compile(r"([가-힣]{2,12})\s*농협")
_DIST_COOP_HEADQUARTERS_RX = re.compile(r"농협\s*([가-힣]{2,12})본부")
_POLICY_EVENT_AGENCY_GROUPS = (
    ("mafra", ("농식품부", "농림축산식품부")),
    ("at", ("aT", "한국농수산식품유통공사")),
    ("kcs", ("관세청",)),
    ("qia", ("검역본부", "농림축산검역본부")),
    ("seoul", ("서울시",)),
    ("gyeonggi", ("경기도",)),
    ("policybrief", ("정책브리핑",)),
    ("krei", ("krei", "한국농촌경제연구원")),
)
_POLICY_EVENT_ANCHOR_GROUPS = (
    ("discount", ("할인", "할인지원", "특판")),
    ("stabilize", ("수급안정", "가격 안정", "가격안정", "공급", "비축", "방출")),
    ("tariff", ("할당관세", "관세", "무관세", "fta")),
    ("quarantine", ("검역", "통관", "수입신고")),
    ("origin", ("원산지", "부정유통", "단속", "적발")),
    ("shipping", ("출하비용", "출하 비용", "보전", "보전금", "보전사업")),
    ("macro", ("물가", "소비자물가", "성수품", "차례상", "물가지수")),
)
_EVENT_KEY_SECTIONS = frozenset({"supply", "dist", "policy"})

def _norm_story_text(title: str, desc: str) -> str:
    s = f"{title or ''} {desc or ''}".lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^0-9a-z가-힣 ]+", " ", s)
    return s.replace(" ", "")

def _trigrams(s: str) -> set[str]:
    if not s:
        return set()
    if len(s) <= 3:
        return {s}
    return {s[i:i+3] for i in range(len(s) - 2)}

def _jaccard_legacy(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def _anchor_hits(title: str, desc: str) -> set[str]:
    txt = f"{title or ''} {desc or ''}"
    return {w for w in _STORY_ANCHORS if w in txt}

def _story_text(a: "Article") -> tuple[str, str]:
    # description이 비어있는 매체가 있어 summary를 보조로 사용
    desc = (a.description or "") if isinstance(a.description, str) else ""
    if (not desc.strip()) and bool(a.summary):
        desc = str(getattr(a, "summary", "") or "")
    return (a.title or ""), desc

def _matched_labels(text: str, groups: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    t = (text or "").lower()
    if not t:
        return []
    return [label for label, terms in groups if any(term.lower() in t for term in terms)]

def _dist_sales_channel_group_key(title: str, desc: str) -> str:
    src = (title or "") + " " + (desc or "")
    compact = re.sub(r"\s+", "", src)
    for rx in (_DIST_COOP_HEADQUARTERS_RX, _DIST_COOP_ORG_RX):
        m = rx.search(src) or rx.search(compact)
        if m:
            return re.sub(r"\s+", "", m.group(1).lower())
    regs = sorted(_region_set(src))
    if regs:
        return re.sub(r"\s+", "", regs[0].lower())
    return ""

def _dist_story_signature(title: str, desc: str) -> str | None:
    text = f"{title or ''} {desc or ''}".lower()
    if not text:
        return None
    compact = re.sub(r"\s+", "", text)
    # ✅ 서울시-가락시장-부적합 농수산물(잔류농약/방사능/수거검사/불시검사) 같은 보도자료 다매체 중복을 강하게 제거
    if "서울시" in text and "가락시장" in text and ("농수산물" in text or "농산물" in text):
        if ("부적합" in text or "잔류농약" in text or "방사능" in text) and ("수거" in text or "검사" in text or "불시" in text):
            return "SIG:SEOUL_FOODSAFETY_GARAK"

    if "서울시" in text and ("부적합" in text or "잔류농약" in text or "방사능" in text) and ("농수산물" in text or "농산물" in text):
        if ("유통" in text or "반입" in text) and ("차단" in text or "검사" in text or "수거" in text or "점검" in text):
            return "SIG:SEOUL_FOODSAFETY"

    if ("원산지" in text or "부정유통" in text) and ("단속" in text or "적발" in text) and ("농산물" in text or "농수산물" in text):
        if "서울시" in text:
            return "SIG:SEOUL_ORIGIN_ENFORCE"

    if ("한국청과" in text or "한국 청과" in text) and ("출하비용" in text or "출하 비용" in text):
        if ("보전" in text or "보전금" in text or "보전사업" in text or "기준가격" in text) and ("가락시장" in text or "도매법인" in text or "경락" in text or "출하농가" in text):
            return "SIG:KOREA_CHEONGGWA_SUPPORT"

    if ("apc" in text or "산지유통센터" in text or "산지유통" in text) and any(k in text for k in ("준공", "준공식", "개장", "개소", "문 열", "가동", "준비", "스마트")):
        m = re.search(r"([가-힣]{2,12})\s*농협", (title or "") + " " + (desc or ""))
        if m:
            org = f"{m.group(1)}농협"
            return f"EV:APC:{org}"
        regs = sorted(_region_set(text))
        loc = regs[0] if regs else ""
        return f"EV:APC:{loc}"

    if ("원스톱수출지원허브" in compact or ("수출지원허브" in compact and "원스톱" in compact)) and ("k-푸드" in text or "k푸드" in compact):
        return "EV:DIST:KFOOD_EXPORT_HUB"

    if is_dist_supply_management_center_context(title, desc):
        regs = sorted(_region_set(text))
        loc = regs[0] if regs else ""
        return f"EV:DIST:SUPPLY_CENTER:{loc or 'center'}"

    sales_channel_signature_like = is_dist_sales_channel_ops_context(title, desc) or (
        ("연합판매사업" in text) and count_any(text, [w.lower() for w in ("직거래", "평가회", "워크숍")]) >= 2
    )
    if sales_channel_signature_like:
        sales_group = _dist_sales_channel_group_key(title, desc)
        if sales_group:
            return f"EV:DIST:SALES_CHANNEL:{sales_group}"
        regs = sorted(_region_set(text))
        loc = regs[0] if regs else ""
        return f"EV:DIST:SALES_CHANNEL:{loc or 'joint_sales'}"

    if is_dist_market_ops_context(title, desc):
        if "온라인도매시장" in compact or "온라인 도매시장" in text:
            return "EV:DIST:ONLINE_WHOLESALE_OPS"

    if is_local_agri_org_feature_context(title, desc):
        org_match = _AGRI_ORG_EVENT_RX.search((title or "") + " " + (desc or ""))
        if org_match:
            org_key = re.sub(r"\s+", "", org_match.group(1).lower())
            return f"EV:DIST:{org_key}:ORG_FEATURE"

    return None

def _policy_story_signature(title: str, desc: str, dom: str = "", press: str = "") -> str | None:
    text = f"{title or ''} {desc or ''}".lower()
    if not text:
        return None

    d = normalize_host(dom or "")
    p = (press or "").strip()
    action_labels = _matched_labels(text, _POLICY_EVENT_ANCHOR_GROUPS)
    if not action_labels:
        return None

    explicit_official = (
        policy_domain_override(d, text)
        or (d in OFFICIAL_HOSTS)
        or any(d.endswith("." + h) for h in OFFICIAL_HOSTS)
        or (p in ("정책브리핑", "농식품부"))
        or is_policy_announcement_issue(text, d, p)
        or is_supply_stabilization_policy_context(text, d, p)
    )
    if not explicit_official:
        return None

    agency_labels = _matched_labels(text, _POLICY_EVENT_AGENCY_GROUPS)
    agency_key = agency_labels[0] if agency_labels else (d or (p.lower() if p else "policy"))

    if is_supply_stabilization_policy_context(text, d, p):
        return f"EV:POLICY:{agency_key}:SUPPLY_STABILIZE"
    if len(action_labels) >= 2:
        return f"EV:POLICY:{agency_key}:{':'.join(sorted(action_labels)[:2])}"
    if action_labels[0] in {"tariff", "quarantine", "origin", "shipping", "macro"}:
        return f"EV:POLICY:{agency_key}:{action_labels[0]}"
    return None

def _supply_story_signature(title: str, desc: str) -> str | None:
    text = f"{title or ''} {desc or ''}".lower()
    try:
        topic, topic_sc = best_topic_and_score(title or "", desc or "")
    except Exception:
        topic, topic_sc = ("", 0.0)

    topic_bucket = ""
    floral_terms = ("화훼", "꽃", "절화", "국화", "장미", "백합", "카네이션")
    if any(term in text for term in floral_terms):
        topic_bucket = "화훼"
    elif topic in _HORTI_TOPICS_SET and topic_sc >= 1.2:
        topic_bucket = topic
    else:
        return None

    if topic_bucket != "화훼" and is_supply_input_cost_pressure_context(title, desc):
        return f"EV:SUPPLY:{topic_bucket}:INPUT_COST_PRESSURE"

    labels = _matched_labels(text, _SUPPLY_EVENT_ANCHOR_GROUPS)
    if topic_bucket == "화훼":
        cost_like = sum(1 for label in ("유가", "상토", "난방", "운송", "자재") if label in labels)
        if cost_like >= 2 or (cost_like >= 1 and "저온" in labels):
            return "EV:SUPPLY:화훼:COST_PRESSURE"
    quality_compare_like = supply_feature_context_kind(title, desc) == "quality"
    quality_labels = sum(1 for label in ("블라인드", "선호", "비교", "품질", "수입산") if label in labels)
    if quality_compare_like and quality_labels >= 2 and (("수입산" in labels) or ("비교" in labels) or ("블라인드" in labels)):
        return f"EV:SUPPLY:{topic_bucket}:QUALITY_COMPARE"
    org_match = _AGRI_ORG_EVENT_RX.search((title or "") + " " + (desc or ""))
    promo_hits = count_any(text, [w.lower() for w in _SUPPLY_ORG_PROMO_TERMS])
    if org_match and promo_hits >= 2:
        org_key = re.sub(r"\s+", "", org_match.group(1).lower())
        return f"EV:SUPPLY:{topic_bucket}:{org_key}:PROMO_EVENT"
    if len(labels) < 2:
        return None
    return f"EV:SUPPLY:{topic_bucket}:{':'.join(sorted(labels)[:2])}"


def _section_story_signature(section_key: str, title: str, desc: str, dom: str = "", press: str = "") -> str | None:
    if section_key == "supply":
        return _supply_story_signature(title, desc)
    if section_key == "dist":
        return _dist_story_signature(title, desc)
    if section_key == "policy":
        return _policy_story_signature(title, desc, dom, press)
    return None


def _event_key(a: "Article", section_key: str) -> str | None:
    """섹션별 선언적 이벤트 시그니처를 우선 적용해 사실상 같은 이슈를 묶는다."""
    try:
        title = a.title or ""
        desc = a.description or ""
        return _section_story_signature(
            section_key,
            title,
            desc,
            getattr(a, "domain", "") or "",
            getattr(a, "press", "") or "",
        )
    except Exception:
        return None
    return None


def _dedupe_prefer_bonus(a: "Article", section_key: str) -> float:
    """중복(이벤트 키) 내에서 1건만 남길 때의 '선호' 보정.
    - 특정 매체(단일) 편향이 아니라, 티어/유형(방송 vs 통신/라운드업) 중심으로 안정화한다.
    - 같은 이벤트라면 방송(특히 전국) 1건을 남기고, 통신 '소식/브리프'는 밀어낸다.
    """
    try:
        p = (getattr(a, "press", "") or "").strip()
        d = normalize_host(getattr(a, "domain", "") or "")
        title = (getattr(a, "title", "") or "")
        desc = (getattr(a, "description", "") or "")
        txt = (title + " " + desc).lower()

        b = 0.0

        pri = press_priority(p, d)
        b += {3: 1.8, 2: 0.6, 1: 0.0}.get(pri, 0.0)

        # 전국 방송사(중앙) 우선
        if p in BROADCAST_PRESS:
            b += 1.4

        # 지역 방송(예: JIBS)은 통신보다는 우선, 전국 방송보다는 낮게
        if p in ("JIBS", "JIBS제주방송", "JIBS 제주방송") or d.endswith("jibstv.com"):
            b += 0.4

        # 통신/온라인 서비스는 중복 그룹에서는 후순위(기사량/라운드업 빈도)
        if p in WIRE_SERVICES:
            b -= 0.8

        # '○○소식/제주소식' 같은 라운드업은 중복 그룹에서는 후순위
        if ("제주소식" in title) or title.strip().endswith("소식"):
            b -= 1.2

        if ("포토뉴스" in title) or ("포토" in title):
            b -= 2.0

        # dist에서 로컬 단신/공지형이면 중복 그룹에서 강하게 밀어냄
        if section_key == "dist" and is_local_brief_text(title, desc, "dist"):
            b -= 2.0
        if section_key == "dist" and is_dist_sales_channel_ops_context(title, desc):
            if ("연합판매사업" in txt) and ("직거래" in txt):
                b += 1.2
            if ("직거래" in title) and (("활성화" in title) or ("워크숍" in title)):
                b += 2.0
            if "농심천심운동" in txt:
                b -= 1.0
            if p in WIRE_SERVICES:
                b -= 1.2

        if section_key == "policy":
            if policy_domain_override(d, txt) or (d in OFFICIAL_HOSTS) or any(d.endswith("." + h) for h in OFFICIAL_HOSTS):
                b += 1.4
            if p in ("정책브리핑", "농식품부", "관세청", "농림축산검역본부", "검역본부", "한국농수산식품유통공사"):
                b += 0.8

        # 농업 전문/현장 매체 시장 리포트는 살리는 편(중복 그룹에서도)
        if p in AGRI_TRADE_PRESS or d in AGRI_TRADE_HOSTS:
            b += 0.8

        return b
    except Exception:
        return 0.0


def _dedupe_by_event_key(items: list["Article"], section_key: str) -> list["Article"]:
    """이벤트 키 기준으로 중복 후보를 1건만 남긴다(점수/티어/최신 순)."""
    if not items:
        return items

    best: dict[str, "Article"] = {}
    for a in items:
        k = _event_key(a, section_key)
        if not k:
            continue
        cur = best.get(k)
        if cur is None:
            best[k] = a
            continue
        cand = (float(getattr(a, "score", 0.0) or 0.0) + _dedupe_prefer_bonus(a, section_key), press_priority(a.press, a.domain), getattr(a, "pub_dt_kst", None))
        prev = (float(getattr(cur, "score", 0.0) or 0.0) + _dedupe_prefer_bonus(cur, section_key), press_priority(cur.press, cur.domain), getattr(cur, "pub_dt_kst", None))
        if cand > prev:
            best[k] = a

    if not best:
        return items

    out: list["Article"] = []
    for a in items:
        k = _event_key(a, section_key)
        if k and best.get(k) is not a:
            continue
        out.append(a)
    return out

def _has_trade_signal(txt: str) -> bool:
    t = (txt or "").lower()
    return any(x in t for x in (
        "관세", "할당관세", "무관세", "fta", "수입", "통관", "검역", "보세", "보세구역",
        "추천 취소", "집중관리", "관리 강화", "판매가격 보고", "유통 의무"
    ))


def _is_similar_story(a: "Article", b: "Article", section_key: str) -> bool:
    at, ad = _story_text(a)
    bt, bd = _story_text(b)
    a_txt = f"{at} {ad}"
    b_txt = f"{bt} {bd}"

    # supply/policy: 무역/관세/FTA/수입 신호 유무가 다르면 같은 이슈로 묶지 않음(핵심 이슈 누락 방지)
    if section_key in ("supply", "policy"):
        if _has_trade_signal(a_txt) != _has_trade_signal(b_txt):
            return False

    if section_key == "dist":
        a_scope = dist_market_disruption_scope(at, ad)
        b_scope = dist_market_disruption_scope(bt, bd)
        if a_scope and b_scope and {a_scope, b_scope} == {"systemic", "commodity_aftershock"}:
            return False

    if section_key == "supply":
        a_feature = supply_feature_context_kind(at, ad)
        b_feature = supply_feature_context_kind(bt, bd)
        if a_feature and b_feature:
            a_issue_bucket = supply_issue_context_bucket(at, ad)
            b_issue_bucket = supply_issue_context_bucket(bt, bd)
            if a_issue_bucket and b_issue_bucket and a_issue_bucket != b_issue_bucket:
                return False
            a_rep_terms = {TOPIC_REP_BY_TERM_L.get(term, term) for term in HORTI_ITEM_TERMS_L if term in a_txt}
            b_rep_terms = {TOPIC_REP_BY_TERM_L.get(term, term) for term in HORTI_ITEM_TERMS_L if term in b_txt}
            if not a_rep_terms:
                a_topic = (getattr(a, "topic", "") or "").strip()
                if a_topic:
                    a_rep_terms = {a_topic}
            if not b_rep_terms:
                b_topic = (getattr(b, "topic", "") or "").strip()
                if b_topic:
                    b_rep_terms = {b_topic}
            if a_rep_terms and b_rep_terms and not (a_rep_terms & b_rep_terms):
                if (not has_direct_supply_chain_signal(a_txt)) and (not has_direct_supply_chain_signal(b_txt)):
                    return False

    if section_key == "pest":
        a_region = _pest_region_or_fallback_key(a)
        b_region = _pest_region_or_fallback_key(b)
        if a_region and b_region and a_region != b_region:
            if is_pest_control_policy_context(a_txt) and is_pest_control_policy_context(b_txt):
                return False
    # 0) 제목/요약 기반 근접 중복(타매체 재전송/표기 차이) 보강
    try:
        if _near_duplicate_title(a, b, section_key):
            return True
    except Exception:
        pass


    # 1) 섹션별 선언형 이벤트 시그니처가 있으면 우선 적용
    if section_key in _EVENT_KEY_SECTIONS:
        sa = _section_story_signature(section_key, at, ad, getattr(a, "domain", "") or "", getattr(a, "press", "") or "")
        sb = _section_story_signature(section_key, bt, bd, getattr(b, "domain", "") or "", getattr(b, "press", "") or "")
        if sa and sb and sa == sb:
            return True


    # 2) 앵커 겹침 + 3-gram Jaccard(섹션별 임계치)
    ah = getattr(a, "_story_anchors", None)
    if ah is None:
        ah = _anchor_hits(at, ad)
        setattr(a, "_story_anchors", ah)
    bh = getattr(b, "_story_anchors", None)
    if bh is None:
        bh = _anchor_hits(bt, bd)
        setattr(b, "_story_anchors", bh)

    inter = ah & bh
    if section_key == "dist":
        # dist는 보도자료 중복이 많으므로 앵커 조건을 조금 완화
        if len(ah) < 3 or len(bh) < 3 or len(inter) < 2:
            return False
        thr = 0.18
    elif section_key in ("supply", "policy"):
        if len(ah) < 2 or len(bh) < 2 or len(inter) < 1:
            return False
        thr = 0.30
    else:
        if len(ah) < 2 or len(bh) < 2 or len(inter) < 1:
            return False
        thr = 0.26

    ta = getattr(a, "_story_tri", None)
    if ta is None:
        ta = _trigrams(_norm_story_text(at, ad))
        setattr(a, "_story_tri", ta)
    tb = getattr(b, "_story_tri", None)
    if tb is None:
        tb = _trigrams(_norm_story_text(bt, bd))
        setattr(b, "_story_tri", tb)

    return _jaccard(ta, tb) >= thr


def _title_bigram_set(s: str) -> set[str]:
    s = (s or "").strip()
    if len(s) < 2:
        return set()
    # 연속 2글자(바이그램) 기반 유사도: 특수문자 제거된 title_key에 잘 맞음
    return {s[i:i+2] for i in range(len(s) - 1)}

def _is_similar_title(k1: str, k2: str) -> bool:
    """제목 중복(유사) 판정.
    - 목적: 같은 이슈가 타매체로 반복될 때 core/final에서 중복 제거
    - 입력은 norm_title_key()로 정규화된 문자열을 가정(공백/특수문자 제거)
    """
    a = (k1 or "").strip()
    b = (k2 or "").strip()
    if not a or not b:
        return False
    if a == b:
        return True

    # 너무 짧은 키는 오탐 위험이 크므로, 포함관계만 제한적으로 허용
    la, lb = len(a), len(b)
    shorter, longer = (a, b) if la <= lb else (b, a)
    ls, ll = len(shorter), len(longer)

    if ls < 10:
        # 10글자 미만은 사실상 제목 키로 신뢰하기 어려움
        return False

    # 포함관계: 짧은 키가 긴 키에 포함되고 길이 차이가 크지 않으면 동일 이슈로 봄
    if shorter in longer and (ls / ll) >= 0.78:
        return True

    # 문자열 유사도(SequenceMatcher)
    try:
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        if ratio >= 0.90:
            return True
        # 경계 영역은 바이그램 자카드로 추가 확인(긴 제목에서만)
        if ratio >= 0.86 and min(la, lb) >= 18:
            ba = _title_bigram_set(a)
            bb = _title_bigram_set(b)
            if ba and bb:
                jac = len(ba & bb) / max(1, len(ba | bb))
                if jac >= 0.82:
                    return True
    except Exception:
        pass

    return False


# -----------------------------
# Topic detection (robust)
# - 1글자 키워드(배/밤/꽃/귤/쌀 등)는 오탐이 잦아 "맥락 패턴"으로만 매칭
# - topic은 카드에 노출되므로, 품목 분류 정확도가 매우 중요
# -----------------------------
_SINGLE_TERM_CONTEXT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    # 과일 '배' (배터리/배당/배달/배기/배포 등 오탐 방지)
    "배": [
        re.compile(r"(?:^|[\s\W])배(?:값|가격|시세|수급|출하|저장|작황|재배|농가)"),
        re.compile(r"(?:^|[\s\W])배(?:\s*(?:산업|생육|과원|개화|착과|꽃눈|휴면|생산|수확|저온|냉해|기후변화))"),
        re.compile(r"(?:^|[\s\W])배\s+과일"),
        re.compile(r"신고배"),
        re.compile(r"나주배"),
    ],
    # '밤'(night) 오탐 방지: 알밤/밤값/밤(농산물 맥락)
    "밤": [
        re.compile(r"(?:^|[\s\W])밤(?:값|가격|시세|수급|출하|작황|재배|농가)"),
        re.compile(r"알밤"),
    ],
    # '꽃'(일반 단어지만 화훼 기사에서 빈번): 꽃값/절화/경매 등과 함께
    "꽃": [
        re.compile(r"(?:^|[\s\W])꽃(?:값|가격|시세)"),
        re.compile(r"(?:^|[\s\W])꽃\s*(경매|도매|소매|시장)"),
        re.compile(r"절화"),
        re.compile(r"생화"),
    ],
    # '귤' (감귤 맥락)
    "귤": [
        re.compile(r"(?:^|[\s\W])귤(?:값|가격|시세|수급|출하|작황|재배|농가)"),
        re.compile(r"감귤"),
        re.compile(r"만감"),
    ],
    # '쌀'은 원예는 아니지만 기존 로직 유지(쌀값/비축미 등)
    "쌀": [
        re.compile(r"(?:^|[\s\W])쌀(?:값|가격|시세|수급)"),
        re.compile(r"비축미"),
        re.compile(r"rpc"),
    ],
}

_HORTI_TOPICS_SET = {topic for topic, _terms in ALL_ITEM_COMMODITY_TOPICS}

_MANAGED_COMMODITY_CONTEXT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "radish": [
        re.compile(r"(?:^|[\s\W])무(?:값|가격|시세|수급|출하|작황|재배|농가|도매가격)"),
        re.compile(r"월동무"),
        re.compile(r"고랭지무"),
    ],
    "pear": list(_SINGLE_TERM_CONTEXT_PATTERNS["배"]),
    "persimmon": [
        re.compile(r"떫은감"),
        re.compile(r"곶감"),
        re.compile(r"반건시"),
        re.compile(r"감말랭이"),
        re.compile(r"(?:^|[\s\W])감(?:값|가격|시세|수급|출하|작황|재배|농가)"),
    ],
    "chestnut": list(_SINGLE_TERM_CONTEXT_PATTERNS["밤"]),
    "dry_red_pepper": [
        re.compile(r"건고추"),
        re.compile(r"건조고추"),
        re.compile(r"고추건조"),
    ],
    "green_pepper": [
        re.compile(r"풋고추"),
        re.compile(r"청양고추"),
        re.compile(r"꽈리고추"),
        re.compile(r"오이고추"),
        re.compile(r"(?:^|[\s\W])고추(?:값|가격|시세|수급|출하|작황|재배|농가)"),
    ],
    "zucchini": [
        re.compile(r"애호박"),
        re.compile(r"쥬키니"),
        re.compile(r"주키니"),
    ],
    "eggplant": [
        re.compile(r"(?:^|[\s\W])가지(?:값|가격|시세|수급|출하|작황|재배|농가)"),
        re.compile(r"가지\s*(농가|재배|출하|도매|경락)"),
    ],
}

_MANAGED_COMMODITY_SECTION_LABELS = {
    "supply": "수급",
    "policy": "정책",
    "dist": "유통",
    "pest": "리스크",
}


def _managed_commodity_matches_text(item: dict[str, Any], text: str, topic: str = "") -> bool:
    txt = (text or "").lower()
    if not txt:
        return False

    key = str(item.get("key") or "").strip()
    if key == "carrot" and "당근" in txt and not is_edible_carrot_context(txt):
        return False
    if key == "potato" and "감자" in txt and not is_fresh_potato_context(txt):
        return False
    if key == "eggplant" and "가지" in txt and not is_edible_eggplant_context(txt):
        return False
    registry_topics = [str(v or "").strip() for v in (item.get("registry_topics") or []) if str(v or "").strip()]
    if topic and topic in registry_topics:
        return True

    for term in item.get("match_terms") or []:
        term_l = str(term or "").strip().lower()
        if key == "napa_cabbage" and term_l == "배추":
            if re.search(r"(?<!양)배추", txt):
                return True
            continue
        if len(term_l) >= 2 and term_l in txt:
            return True

    for term in item.get("context_terms") or []:
        term_l = str(term or "").strip().lower()
        if term_l and term_l in txt:
            return True

    for pattern in _MANAGED_COMMODITY_CONTEXT_PATTERNS.get(key, []):
        if pattern.search(txt):
            return True
    return False


def managed_commodity_keys_for_text(title: str, desc: str, topic: str = "") -> list[str]:
    txt = f"{title or ''} {desc or ''}".lower()
    topic_name = str(topic or "").strip()
    matched: list[str] = []

    for item in MANAGED_COMMODITY_CATALOG:
        key = str(item.get("key") or "").strip()
        if not key or key in matched:
            continue
        if _managed_commodity_matches_text(item, txt, topic_name):
            matched.append(key)
    return matched


def managed_commodity_keys_for_article(article: "Article") -> list[str]:
    return managed_commodity_keys_for_text(
        getattr(article, "title", "") or "",
        getattr(article, "description", "") or "",
        getattr(article, "topic", "") or "",
    )


def _managed_commodity_match_summary(title: str, desc: str, topic: str = "") -> dict[str, Any]:
    keys = managed_commodity_keys_for_text(title, desc, topic)
    program_core_keys = [
        key
        for key in keys
        if bool((MANAGED_COMMODITY_BY_KEY.get(key) or {}).get("program_core"))
    ]
    return {
        "keys": keys,
        "count": len(keys),
        "program_core_keys": program_core_keys,
        "program_core_count": len(program_core_keys),
        "has_program_core": bool(program_core_keys),
    }


def _managed_commodity_item_for_seed(seed: str) -> dict[str, Any] | None:
    seed_s = str(seed or "").strip()
    if not seed_s:
        return None
    seed_l = seed_s.lower()
    for item in MANAGED_COMMODITY_CATALOG:
        exact_terms = _ordered_unique_terms(
            [
                item.get("short_label") or "",
                re.sub(r"\s*\([^)]*\)", "", str(item.get("label") or "")).strip(),
                item.get("label") or "",
            ]
            + list(item.get("match_terms") or [])
            + list(item.get("registry_topics") or [])
        )
        if seed_l in {str(term or "").strip().lower() for term in exact_terms if str(term or "").strip()}:
            return item
    rep = TOPIC_REP_BY_TERM_L.get(seed_s.lower(), seed_s)
    keys = managed_commodity_keys_for_text(seed_s, "", rep)
    if not keys:
        return None
    return MANAGED_COMMODITY_BY_KEY.get(keys[0])

def _topic_scores(title: str, desc: str) -> dict[str, float]:
    t = (title + " " + desc).lower()
    tl = (title or "").lower()
    scores: dict[str, float] = {}

    for topic, words in COMMODITY_TOPICS:
        sc = 0.0
        if topic == "가지" and not is_edible_eggplant_context(t):
            continue
        if topic == "멜론" and not is_edible_melon_context(t):
            # 멜론(음원 플랫폼) 오탐 방지
            continue

        if topic == "당근" and not is_edible_carrot_context(t):
            # 당근(플랫폼/앱) 동음이의어 오탐 방지
            continue

        if topic == "감자" and not is_fresh_potato_context(t):
            # 감튀/감자튀김 등 가공·외식 문맥 오탐 방지
            continue


        if topic == "피망" and not is_edible_pimang_context(t):
            # 피망(게임/브랜드) 오탐 방지
            continue

        if topic == "사과" and not is_edible_apple_context(t):
            # 사과(과일) 동음이의어(사과대/사과문 등) 오탐 방지
            continue

        if topic == "사과" and any(x in t for x in ("의사과학", "의사과학자", "의사과학원", "의사공학", "의과학", "의과학원")):
            # '의사과학자/의사과학원' 등은 '사과(apple)'가 아니라 의료/학문 용어(부분문자열) 오탐
            continue


        # 기본(2글자 이상 키워드): 부분문자열 매칭
        for w in words:
            wl = (w or "").lower()
            if len(wl) < 2:
                continue
            if wl in t:
                sc += 1.0
                if wl in tl:
                    sc += 0.4

        # 1글자 키워드: 맥락 패턴으로만 보강
        # - topic 자체가 1글자 품목을 포함할 수 있어 topic명을 기반으로 패턴을 선택
        if topic == "배":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["배"]):
                sc += 1.8
        if topic == "밤":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["밤"]):
                sc += 1.6
        if topic == "화훼":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["꽃"]):
                sc += 1.3
        if topic == "감귤/만감":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["귤"]):
                sc += 1.1
        if topic == "쌀":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["쌀"]):
                sc += 1.2

        if sc > 0:
            scores[topic] = sc
    # ✅ 정책 강신호(관세/통관/보세/할당관세/정부)면 '정책' 토픽 가중치 부여
    POLICY_STRONG_TERMS = (
        "관세", "할당관세", "무관세", "fta", "통관", "수입신고", "보세", "보세구역", "반출", "반입",
        "관세청", "기재부", "농식품부", "정부", "대책", "지원", "단속", "고시", "개정", "시행",
    )
    if any(x in t for x in POLICY_STRONG_TERMS):
        scores["정책"] = scores.get("정책", 0.0) + 4.5


    return scores

def best_topic_and_score(title: str, desc: str) -> tuple[str, float]:
    scores = _topic_scores(title, desc)
    if not scores:
        return "기타", 0.0
    # 최고 점수 topic, 동점이면 '품목(원예)'를 우선(정책/도매시장보다 앞서 표시)
    best_topic = None
    best_sc = -1.0
    for topic, sc in scores.items():
        if sc > best_sc:
            best_topic, best_sc = topic, sc
        elif sc == best_sc and best_topic is not None:
            if topic in _HORTI_TOPICS_SET and best_topic not in _HORTI_TOPICS_SET:
                best_topic = topic
    return best_topic or "기타", float(best_sc)

def best_horti_score(title: str, desc: str) -> float:
    scores = _topic_scores(title, desc)
    horti = [sc for t, sc in scores.items() if t in _HORTI_TOPICS_SET]
    best = max(horti) if horti else 0.0
    managed_summary = _managed_commodity_match_summary(title, desc)
    managed_count = int(managed_summary.get("count") or 0)
    program_core_count = int(managed_summary.get("program_core_count") or 0)
    if managed_count:
        best = max(best, 1.0 + (0.32 * managed_count) + (0.28 * program_core_count))
    title_managed_summary = _managed_commodity_match_summary(title, "")
    title_managed_count = int(title_managed_summary.get("count") or 0)
    title_program_core_count = int(title_managed_summary.get("program_core_count") or 0)
    if title_managed_count:
        best = max(best, 1.25 + (0.38 * title_managed_count) + (0.32 * title_program_core_count))
    return best

def extract_topic(title: str, desc: str) -> str:
    topic, _ = best_topic_and_score(title, desc)
    if topic not in _HORTI_TOPICS_SET:
        title_managed_summary = _managed_commodity_match_summary(title, "")
        managed_summary = title_managed_summary if title_managed_summary.get("count") else _managed_commodity_match_summary(title, desc)
        keys = list(managed_summary.get("keys") or [])
        if keys:
            item = MANAGED_COMMODITY_BY_KEY.get(str(keys[0]) or "") or {}
            registry_topics = [str(v or "").strip() for v in (item.get("registry_topics") or []) if str(v or "").strip()]
            managed_topic = registry_topics[0] if registry_topics else str(item.get("short_label") or item.get("label") or "").strip()
            if managed_topic:
                return managed_topic
    return topic

def make_norm_key(canon_url: str, press: str, title_key: str) -> str:
    if canon_url:
        h = hashlib.sha1(canon_url.encode("utf-8")).hexdigest()[:16]
        return f"url:{h}"
    base = f"{(press or '').strip()}|{title_key}"
    h = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    return f"pt:{h}"

def has_any(text: str, words: list[str] | tuple[str, ...] | set[str]) -> bool:
    return any(w in text for w in words)

def count_any(text: str, words: list[str] | tuple[str, ...] | set[str]) -> int:
    return sum(1 for w in words if w in text)


def has_apc_agri_context(text: str) -> bool:
    """APC 오탐(UPS/전원장비 등)을 막기 위해, '농업/산지유통' 문맥일 때만 APC로 인정."""
    t = (text or "").lower()
    if "apc" not in t:
        return False

    # strong: APC와 함께 나오면 거의 농산물 산지유통 문맥으로 볼 수 있는 신호
    strong_hints = (
        "산지유통", "산지유통센터", "농산물산지유통센터",
        "선별", "선별장", "선과", "선과장", "집하", "집하장",
        "저온", "저온저장", "저장고", "ca저장",
        "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
        "농협", "조합", "출하", "출하량",
        "원예", "과수", "청과", "농산물", "과일", "채소", "화훼",
    )
    # weak: 단독으로는 약하지만 APC와 함께 2개 이상이면 농업 현장 맥락일 가능성이 높음
    weak_hints = (
        "유통", "물류", "저장", "선별기", "비파괴", "공선", "공동선별",
        "산지", "생산자", "농가", "작목반", "조합원",
    )

    strong_hit = count_any(t, [h.lower() for h in strong_hints])
    weak_hit = count_any(t, [h.lower() for h in weak_hints])

    if strong_hit >= 1:
        return True
    return weak_hit >= 2

# -----------------------------
# Melon safety guards
# - '멜론'은 음원 플랫폼(멜론)과 동음이의어라 오탐이 잦다.
# - '먹는 멜론' 맥락(재배/출하/작황/농가/도매시장 등)일 때만 품목으로 인정한다.
# -----------------------------
_MELON_MUSIC_MARKERS = [
    "멜론차트", "음원", "스트리밍", "뮤직", "앨범", "가수", "노래", "신곡",
    "top100", "top 100", "멜론티켓", "콘서트", "공연", "팬미팅", "이용권",
    "카카오엔터", "카카오 엔터", "멜론앱", "멜론 앱", "멜론 서비스",
]
_MELON_EDIBLE_MARKERS = [
    "과일", "과채", "시설", "하우스", "비가림", "재배", "농가", "작황", "수확", "출하",
    "도매", "도매가격", "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
    "산지", "산지유통", "산지유통센터", "apc", "선별", "저온", "저장", "ca저장",
    "수급", "시세", "수출", "검역", "통관", "잔류농약",
]
_MELON_VARIETY_MARKERS = [
    "머스크멜론", "네트멜론", "얼스멜론", "하미과", "칸탈루프", "허니듀",
]

def is_edible_melon_context(text: str) -> bool:
    """Return True only when '멜론' clearly means the edible fruit (not the music service).

    Heuristics:
      - Always accept if a melon variety marker is present (머스크멜론 등)
      - If strong music/entertainment markers exist (멜론차트/음원/앨범 등),
        require *strong* edible markers; otherwise reject.
      - Accept edible context when at least one agri/produce marker exists OR
        when '멜론 값/가격/시세/도매가격' 같은 가격 패턴이 나타나고 음악마커가 없을 때.
    """
    t = (text or "").lower()
    if "멜론" not in t:
        return False

    # 품종/유형이 명시되면 거의 100% 과일
    if any(v.lower() in t for v in _MELON_VARIETY_MARKERS):
        return True

    music_hit = any(w.lower() in t for w in _MELON_MUSIC_MARKERS)

    # 농업/유통/품질 신호(가격 단어 단독은 제외)
    edible_hit = any(w.lower() in t for w in _MELON_EDIBLE_MARKERS)

    # 가격 패턴(멜론 값/가격/시세/도매가격 등)이 있으면, 음악마커가 없을 때만 과일로 인정
    price_pat = bool(re.search(r"멜론\s*(값|가격|시세|도매가격|출하가|경락가)", t))
    if price_pat and not music_hit:
        edible_hit = True

    # 음악/엔터 맥락이 강한데 먹는 멜론 신호가 없으면 오탐으로 판단
    if music_hit and not edible_hit:
        return False

    return edible_hit

# -----------------------------
# Pimang safety guards
# - '피망'은 게임/브랜드(피망/pmang/뉴맞고 등)로도 매우 자주 등장한다.
# - 채소(피망/파프리카) 맥락이 확실할 때만 품목으로 인정한다.
# -----------------------------
_PIMANG_GAME_MARKERS = [
    "pmang", "피망게임", "뉴맞고", "맞고", "고스톱", "고포류", "포커", "네오위즈", "게임", "보드게임", "모바일게임",
    "팝업", "스타필드", "코엑스", "이벤트", "출시", "업데이트",
]
_PIMANG_EDIBLE_MARKERS = [
    "채소", "과채", "파프리카", "피망(채소)", "농산물", "원예", "재배", "농가", "작황", "수확", "출하",
    "도매", "도매가격", "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
    "산지", "산지유통", "산지유통센터", "apc", "선별", "저온", "저장", "ca저장",
    "수급", "시세", "가격", "수출", "검역", "통관",
]

def is_edible_pimang_context(text: str) -> bool:
    """Return True only when '피망' clearly refers to the edible vegetable (bell pepper).

    - If '파프리카/채소/농산물/재배/출하/도매시장' 등 식품/농업 마커가 있으면 통과.
    - 게임/엔터 마커가 강한데 식품 마커가 없으면 오탐으로 차단.
    - '피망 가격/시세/도매가격/출하' 패턴은 게임 마커가 없을 때만 식품으로 인정.
    """
    t = (text or "").lower()
    if "피망" not in t:
        return False

    edible_hit = any(w.lower() in t for w in _PIMANG_EDIBLE_MARKERS)
    game_hit = any(w.lower() in t for w in _PIMANG_GAME_MARKERS)

    price_pat = bool(re.search(r"피망\s*(값|가격|시세|도매가격|출하가|경락가)", t))
    if price_pat and not game_hit:
        edible_hit = True

    if game_hit and not edible_hit:
        return False

    return edible_hit


_POTATO_PROCESSED_MARKERS = [
    "감튀", "감자튀김", "감자 튀김", "프렌치프라이", "프렌치 프라이", "해시브라운", "웨지감자",
    "감자칩", "포테이토칩", "패스트푸드", "햄버거", "버거킹", "맥도날드", "롯데리아",
]
_POTATO_FRESH_MARKERS = [
    "농산물", "원예", "채소", "산지", "농가", "재배", "작황", "수확", "출하", "반입",
    "도매", "도매가격", "가락시장", "도매시장", "공판장", "경락", "경매", "수급", "시세",
    "저장", "물량", "씨감자", "봄감자", "수미감자", "감자 수급", "감자 가격",
    "감자 작황", "감자 재배", "감자 출하", "감자 도매가격", "검역", "통관", "수출",
]


def is_fresh_potato_context(text: str) -> bool:
    """Return True only when '감자' clearly refers to fresh produce / horticulture."""
    t = (text or "").lower()
    if "감자" not in t:
        return False

    fresh_hit = any(w.lower() in t for w in _POTATO_FRESH_MARKERS)
    processed_hit = any(w.lower() in t for w in _POTATO_PROCESSED_MARKERS)
    price_pat = bool(re.search(r"감자\s*(값|가격|시세|도매가격|출하가|경락가|수급|작황|재배)", t))
    if price_pat:
        fresh_hit = True

    if processed_hit and not fresh_hit:
        return False

    return fresh_hit


_CARROT_PLATFORM_MARKERS = [
    "당근마켓", "당근 마켓", "당근앱", "당근 앱", "지역 커뮤니티", "커뮤니티 앱", "동네생활",
    "중고거래", "포장주문", "치킨", "bhc", "할인", "쿠폰", "주문", "입점", "배달",
]
_CARROT_EDIBLE_MARKERS = [
    "농산물", "채소", "원예", "산지", "농가", "재배", "수확", "출하", "반입",
    "도매", "도매가격", "가락시장", "도매시장", "공판장", "경락", "경매",
    "제주당근", "햇당근", "월동당근", "당근 가격", "당근 수급", "당근 시세",
    "당근 재배", "당근 출하", "당근 도매가격",
]


def is_edible_carrot_context(text: str) -> bool:
    """Return True only when '당근' clearly refers to fresh produce."""
    t = (text or "").lower()
    if "당근" not in t:
        return False
    edible_hit = any(w.lower() in t for w in _CARROT_EDIBLE_MARKERS)
    platform_hit = any(w.lower() in t for w in _CARROT_PLATFORM_MARKERS)
    if platform_hit and not edible_hit:
        return False
    return edible_hit


_EGGPLANT_NON_EDIBLE_MARKERS = [
    "가지말", "가지 말", "가지마",
    "한 가지", "두 가지", "세 가지", "네 가지", "다섯 가지", "몇 가지", "여러 가지",
    "한가지", "두가지", "세가지", "네가지", "다섯가지", "몇가지", "여러가지",
    "나뭇가지", "곁가지", "잔가지", "가지치기", "가지 끝", "가지끝",
]
_EGGPLANT_EDIBLE_MARKERS = [
    "농산물", "채소", "과채", "원예", "산지", "생산", "생육", "재배", "농가", "시설", "하우스",
    "도매시장", "공판장", "경매", "수급", "출하", "출하량", "작황", "시세", "가격", "도매", "유통", "병해충",
    "가지 가격", "가지 수급", "가지 시세", "가지 출하", "가지 출하량", "가지 작황", "가지 생육",
    "가지 재배", "가지 농가", "가지 도매", "가지 경매", "가지 유통", "가지 병해충",
    "시설가지", "노지가지", "가지 품목", "가지 산지", "가지 생산",
]
_EGGPLANT_NON_EDIBLE_RX = re.compile(
    r"가지\s*말(?:까|고|라|자|라고)?|"
    r"(?:한|두|세|네|다섯|몇|여러)\s*가지|"
    r"(?:잎|줄기)\s*[·,/]\s*가지|"
    r"가지\s*[·,/]\s*(?:꽃|열매)|"
    r"(?:사과|배|과수|나무).{0,12}(?:잎|줄기|가지|꽃|열매)"
)


def is_edible_eggplant_context(text: str) -> bool:
    """Return True only when '가지' clearly refers to the vegetable crop."""
    t = (text or "").lower()
    if "가지" not in t:
        return False
    edible_hit = any(w.lower() in t for w in _EGGPLANT_EDIBLE_MARKERS)
    non_edible_hit = any(w.lower() in t for w in _EGGPLANT_NON_EDIBLE_MARKERS) or (_EGGPLANT_NON_EDIBLE_RX.search(t) is not None)
    price_pat = bool(re.search(r"가지\s*(가격|시세|수급|출하(?:량)?|작황|생육|재배|농가|도매|경매|유통|병해충|품목)", t))
    if price_pat:
        edible_hit = True
    if non_edible_hit and not edible_hit:
        return False
    return edible_hit


_APPLE_APOLOGY_MARKERS = (
    "사과문", "사과했다", "사과합니다", "사과드립니다", "공식 사과", "대국민 사과", "유감",
    "사과 요구", "사과를 요구", "사과 촉구", "사과하라", "사과해야", "사과하고", "사과할",
    "반쪽짜리 사과", "진정성 없는 사과", "늦은 사과",
)
_APPLE_APOLOGY_RX = re.compile(
    r"(반쪽짜리|대국민|공식|진정성 없는|늦은|거듭|재차)\s*사과|"
    r"사과\s*(요구|촉구|하라|해야|입장|거부|논란)"
)
_APPLE_FRUIT_MARKERS = (
    "과일", "과수", "과원", "사과나무", "부사", "후지", "홍로", "감홍", "아오리", "시나노",
    "가락시장", "도매시장", "공판장", "청과", "경락", "경매", "산지", "농가", "재배", "수확",
    "apc", "산지유통",
)
_APPLE_FRUIT_NEAR_RX = re.compile(
    r"사과(?:\s*값|\s*가격|\s*시세|\s*수급|\s*출하|\s*작황|\s*재고|\s*저장|\s*선별)"
)


def has_apple_fruit_context(text: str) -> bool:
    t = (text or "").lower()
    if "사과" not in t:
        return False
    if any(m in t for m in _APPLE_FRUIT_MARKERS):
        return True
    return _APPLE_FRUIT_NEAR_RX.search(t) is not None


def is_apple_apology_context(text: str) -> bool:
    """Return True when '사과' is clearly an apology, not the fruit."""
    t = (text or "").lower()
    if "사과" not in t:
        return False
    if has_apple_fruit_context(t):
        return False
    if any(m in t for m in _APPLE_APOLOGY_MARKERS):
        return True
    return _APPLE_APOLOGY_RX.search(t) is not None


def is_edible_apple_context(text: str) -> bool:
    """Return True only when '사과' clearly refers to the fruit (apple).

    주요 오탐:
    - 사과(謝過): 사과문/사과하다/공식 사과 등
    - 사과대/사회과학(교육/입시 기사에서 '사과대' = 사회과학대학)
    - 의사과학/의사과학자 등 부분문자열(이미 별도 방어가 있으나 여기서도 방어)

    판정 원칙:
    - 부정(오탐) 마커가 강하고 농업/시장 마커가 없으면 False
    - '가격/시세/수급/출하/도매시장/과수/과일/농가' 등 실무 마커가 있으면 True
    """
    t = (text or "").lower()
    if "사과" not in t:
        return False

    # 1) 강한 오탐(사회과학대학 약칭 등)
    hard_false = (
        "사과대", "사과대학", "사회과학", "사회과학대", "사회과학대학", "사과계열", "사과 계열"
    )
    if any(w in t for w in hard_false):
        # 단, 과일/도매/수급 마커가 충분히 있으면 예외적으로 True
        strong_pos = ("과일", "과수", "가락시장", "도매시장", "공판장", "청과", "경락", "출하", "작황", "수급", "시세", "가격", "농가", "산지")
        if not any(w in t for w in strong_pos):
            return False

    # 2) 의사과학(부분문자열) 오탐
    if any(x in t for x in ("의사과학", "의사과학자", "의사과학원", "의사공학", "의과학", "의과학원")):
        return False

    # 3) '사과(謝過)' 오탐: 사과문/사과하다/공식 사과 등
    if is_apple_apology_context(t):
        return False

    # 4) 긍정 판단: 실무 마커가 1개 이상이면 True
    if has_apple_fruit_context(t):
        return True

    # 여기까지 왔으면 '사과' 단독 등장 가능성이 높으므로 False
    return False


# --- 해외 원예/화훼 업계 '원격 해외' 기사 차단(국내 실무와 무관한 경우) ---
_FOREIGN_REMOTE_MARKERS = [
    "콜롬비아","미국","중국","일본","베트남","태국","인도","호주","뉴질랜드","유럽","eu","러시아","우크라이나",
    "브라질","칠레","페루","멕시코","캐나다","인도네시아","필리핀","말레이시아","싱가포르","남아공","케냐",
    "네덜란드","스페인","프랑스","독일","영국","trump","트럼프",
]
_KOREA_STRONG_CONTEXT = [
    "국내","한국","우리나라","농협","농식품부","농림축산식품부","aT","가락시장","도매시장","공판장","청과","산지유통","산지유통센터",
]

# -----------------------------
# Extra context guards
# -----------------------------
_RETAIL_PROMO_STORE_HINTS = [
    "백화점", "대형마트", "마트", "이마트", "홈플러스", "롯데마트", "코스트코", "쿠팡", "ssg", "신세계", "롯데백화점",
]
_RETAIL_PROMO_DEAL_HINTS = [
    "프로모션", "할인", "세일", "특가", "쿠폰", "카드", "적립", "포인트", "행사", "1+1", "2+1", "n+1", "기획전",
]
def is_retail_promo_context(text: str) -> bool:
    """대형 유통(백화점/마트) 프로모션성 기사인지 판단.
    - dist(유통/현장)에서 '도매/공판장' 맥락 없이 이런 기사가 들어오는 것을 차단한다.
    """
    t = (text or "").lower()
    store = any(w.lower() in t for w in _RETAIL_PROMO_STORE_HINTS)
    deal = any(w.lower() in t for w in _RETAIL_PROMO_DEAL_HINTS)
    # 너무 일반적인 '행사' 오탐을 줄이기 위해, 가격/할인 계열이 함께 있을 때만 True
    if store and deal:
        return True
    return False
_RETAIL_SALES_TREND_MARKERS = [
    "매출", "판매", "판매량", "판매비중", "비중", "데이터", "분석", "트렌드", "나침반",
    "무인", "무인과일", "과일가게", "판매점", "매장", "소매", "편의점", "마트", "백화점",
    "프랜차이즈", "체인", "온라인몰", "구매", "소비",
]
_RETAIL_SALES_TREND_EXCLUDE: list[str] = [
    # 거시 물가/통계는 policy에서 다루므로 제외하지 않음(아래 로직에서 따로 판단)
]
def is_retail_sales_trend_context(text: str) -> bool:
    """소매/리테일 판매 데이터 기반 트렌드 기사 판정.
    - 예: '매출/판매 데이터/분석/트렌드/랭킹' 중심의 소비 트렌드 기사
    - 목적: 이런 유형은 '정책 및 주요 이슈'으로 과흡수되지 않도록 supply 쪽으로 남기기
    """
    t = (text or "").lower()
    if not t:
        return False

    retail_terms = [
        "매출", "판매", "판매량", "판매량", "판매 데이터", "데이터", "분석", "트렌드", "랭킹", "top", "순위",
        "리테일", "소매", "마트", "편의점", "유통업계", "오프라인", "온라인몰", "이커머스", "쿠팡", "네이버쇼핑",
        "매장", "프로모션", "행사", "구매", "소비", "장바구니",
    ]
    # 너무 범용적인 '데이터' 단독은 제외(노이즈 방지)
    if not any(k in t for k in retail_terms):
        return False

    horti_terms = [
        "과일", "과수", "채소", "원예", "농산물", "사과", "배", "딸기", "포도", "감귤", "만감류",
        "샤인머스캣", "키위", "참다래", "복숭아", "자두", "감", "토마토", "파프리카", "오이", "참외",
    ]
    if not any(k in t for k in horti_terms):
        return False

    # 정책/제도 기사로 볼 만한 강신호가 있으면 소매 트렌드로 보지 않는다(오분류 방지)
    policy_hard = ["대책", "지원", "단속", "점검", "회의", "발표", "추진", "법", "제도", "개정", "관세", "검역", "규제"]
    if any(k in t for k in policy_hard) and ("매출" not in t and "판매" not in t):
        return False

    return True


# -----------------------------
# Flower consumer-trend helpers (화훼 소비/선물 트렌드 기사)
# -----------------------------
_FLOWER_TREND_CORE_MARKERS = [
    "화훼", "꽃", "꽃다발", "절화", "생화", "플라워", "보태니컬", "화원", "꽃집", "꽃시장",
    "장미", "튤립", "카네이션", "국화", "프리지아",
]

_FLOWER_TREND_TREND_MARKERS = [
    "트렌드", "인기", "유행", "소비", "선물", "기념일", "밸런타인", "졸업", "입학",
    "화이트데이", "프로포즈", "선호", "랭킹", "주목", "판매", "매출", "레고", "콜라보", "논란",
]

_FLOWER_TREND_AGRI_MARKERS = [
    "화훼", "절화", "생화", "꽃시장", "경매", "도매", "공판장", "화훼자조금", "농가", "출하",
]

_FLOWER_TREND_EXCLUDE_MARKERS = [
    "축제", "박람회", "전시회", "공연", "콘서트", "포토존", "야경", "관광", "여행", "데이트코스",
    "연예", "아이돌", "드라마", "배우", "인플루언서", "셀럽", "패션",
    "창업", "프랜차이즈", "카페 창업", "매장 오픈",
    "게임", "피규어", "애니메이션", "캐릭터 굿즈",
]

_FLOWER_TREND_NOISE_MARKERS = [
    "레고", "보태니컬", "장난감", "블록", "시상식", "유재석", "셀럽", "연예인", "굿즈",
]
_FLOWER_NOVELTY_EVENT_MARKERS = [
    "시상식", "대상", "연예대상", "연말 시상식", "레드카펫", "셀럽", "연예인", "유재석", "굿즈", "레고", "보태니컬", "장난감",
]
_FLOWER_NOVELTY_MARKET_SIGNAL_MARKERS = [
    "가격", "시세", "경매", "경락", "경락가", "반입", "출하", "물량", "작황", "재배", "산지",
    "도매시장", "공판장", "꽃시장", "수급", "유통", "저온", "보관",
]
_FLOWER_NOVELTY_ASSOCIATION_MARKERS = [
    "협회", "화원협회", "상처", "반발", "비판", "논란", "불만", "생존권", "무색",
]

def is_flower_consumer_trend_context(text: str) -> bool:
    """화훼 '소비/선물 트렌드' 유형(예: 레고 꽃다발 논란/꽃다발 선물 트렌드)을 판정한다.
    - 품목 및 수급 동향(supply)에서 '화훼 이슈'로 비핵심(하단) 편입하는 용도.
    - 관광/축제/연예/창업성 노이즈는 제외.
    """
    t = (text or "").lower()
    if any(w.lower() in t for w in _FLOWER_TREND_EXCLUDE_MARKERS):
        return False
    if any(w.lower() in t for w in _FLOWER_TREND_NOISE_MARKERS):
        return False
    core_hits = sum(1 for w in _FLOWER_TREND_CORE_MARKERS if w.lower() in t)
    trend_hits = sum(1 for w in _FLOWER_TREND_TREND_MARKERS if w.lower() in t)
    agri_hits = sum(1 for w in _FLOWER_TREND_AGRI_MARKERS if w.lower() in t)
    # 최소 조건: 화훼 계열 1개 이상 + 트렌드/소비 1개 이상 + 실제 화훼 유통/농가 맥락 1개 이상
    if core_hits >= 1 and trend_hits >= 1 and agri_hits >= 1:
        return True
    return False


def is_flower_novelty_noise_context(title: str, desc: str) -> bool:
    """장난감/연예/라이프스타일성 '꽃다발' 기사를 원예 기사에서 배제한다."""
    title_l = (title or "").lower()
    desc_l = (desc or "").lower()
    text = f"{title_l} {desc_l}".strip()
    if not text:
        return False
    novelty_hits = count_any(text, [w.lower() for w in _FLOWER_TREND_NOISE_MARKERS])
    bouquet_hits = count_any(text, [w.lower() for w in ("꽃다발", "부케", "플라워", "꽃 선물", "꽃다발 선물")])
    event_hits = count_any(text, [w.lower() for w in _FLOWER_NOVELTY_EVENT_MARKERS])
    market_signal_hits = count_any(text, [w.lower() for w in _FLOWER_NOVELTY_MARKET_SIGNAL_MARKERS])
    association_hits = count_any(text, [w.lower() for w in _FLOWER_NOVELTY_ASSOCIATION_MARKERS])
    if any(phrase in text for phrase in ("장난감 꽃", "생화 너무 비싸", "레고 꽃", "조화 시장")) and market_signal_hits <= 1:
        return True
    if novelty_hits == 0 and event_hits == 0:
        return False
    if bouquet_hits == 0 and not ("꽃" in title_l and event_hits >= 1):
        return False
    if market_signal_hits >= 2:
        return False
    if event_hits >= 1 and market_signal_hits == 0:
        return True
    if novelty_hits >= 1 and bouquet_hits >= 1 and market_signal_hits <= 1 and association_hits >= 1:
        return True
    return False


# -----------------------------
# Consumer / non-agri noise helpers
# -----------------------------
_FASTFOOD_BRAND_MARKERS = [
    "빅맥", "맥도날드", "버거킹", "롯데리아", "맘스터치", "kfc", "서브웨이",
    "와퍼", "맥런치", "후렌치후라이", "프렌치후라이",
]
_FASTFOOD_PRICE_MARKERS = [
    "가격 인상", "가격인상", "인상", "값 올", "가격 올", "요금 인상", "조정", "물가지수", "물가 부담",
]

def is_fastfood_price_context(text: str) -> bool:
    """햄버거/패스트푸드 프랜차이즈 가격 인상/물가 기사(농산물 브리핑 관점에서 노이즈)를 판정."""
    t = (text or "").lower()
    # 제목/본문에 '빅맥'이 있으면 거의 항상 프랜차이즈 가격 기사
    if "빅맥" in t:
        return True
    if any(b.lower() in t for b in _FASTFOOD_BRAND_MARKERS) and any(m.lower() in t for m in _FASTFOOD_PRICE_MARKERS):
        return True
    # '햄버거 물가지수' 류도 제외(대부분 외식 물가 기사)
    if ("햄버거" in t and "물가지수" in t) or ("햄버거" in t and "가격" in t and "인상" in t):
        return True
    return False

_FRUIT_FOODSERVICE_EVENT_BRANDS = [
    "애슐리", "애슐리퀸즈", "이랜드이츠", "뷔페", "외식", "매장", "방문", "대기 시간", "대기시간",
]
_FRUIT_FOODSERVICE_EVENT_MARKERS = [
    "딸기축제", "딸기 축제", "시즌", "시즌행사", "행사", "프로모션", "디저트", "메뉴", "바스켓",
    "투입", "톤", "콘텐츠", "재방문",
]


# 거시경제/무역/일반 소비물가 기사 중 '농산물' 단어만 스치듯 포함된 노이즈 차단용
_WEAK_HORTI_MARKERS = (
    "농산물", "농식품", "먹거리", "식재료", "물가", "장바구니", "소비자물가", "성수품"
)
_STRONG_HORTI_MARKERS = (
    "사과", "배", "감귤", "만감", "딸기", "포도", "참외", "오이", "토마토", "파프리카", "자두", "매실", "밤", "복숭아",
    "가락시장", "도매시장", "공판장", "경락", "경매", "반입", "출하", "재고", "저장", "저온", "산지", "작황", "선별"
)

def is_macro_trade_noise_context(text: str) -> bool:
    """국제통상/산업 기사에서 농산물이 주변적으로만 언급되는 경우를 차단."""
    t = (text or "").lower()
    if not t:
        return False

    geo_trade = ("트럼프", "미국", "중국", "eu", "유럽", "관세", "보복관세", "301조", "상호관세", "fta", "ustr", "통상")
    industry = ("반도체", "자동차", "배터리", "철강", "석유화학", "조선", "플랫폼", "ai", "인공지능")
    weak_horti = ("농산물", "농식품", "식품", "먹거리")
    strong_horti = _STRONG_HORTI_MARKERS + ("원예", "과수", "채소", "화훼", "절화", "청과")

    geo_hit = count_any(t, [w.lower() for w in geo_trade])
    ind_hit = count_any(t, [w.lower() for w in industry])
    weak_hit = count_any(t, [w.lower() for w in weak_horti])
    strong_hit = count_any(t, [w.lower() for w in strong_horti])

    if geo_hit >= 2 and ind_hit >= 1 and weak_hit >= 1 and strong_hit == 0:
        return True
    if geo_hit >= 1 and ind_hit >= 2 and ("농산물" in t or "농식품" in t) and strong_hit == 0:
        return True
    return False

def is_general_consumer_price_noise(text: str) -> bool:
    """장바구니/CPI 나열형 기사 중 원예 수급 신호가 약한 경우를 차단."""
    t = (text or "").lower()
    if not t:
        return False
    basket_terms = ("전기요금", "가스요금", "통신비", "휘발유", "교통비", "월세", "외식비", "가공식품", "공공요금")
    weak_hit = count_any(t, [w.lower() for w in _WEAK_HORTI_MARKERS])
    strong_hit = count_any(t, [w.lower() for w in _STRONG_HORTI_MARKERS])
    basket_hit = count_any(t, [w.lower() for w in basket_terms])

    if basket_hit >= 2 and weak_hit >= 1 and strong_hit == 0:
        return True
    if ("장바구니" in t or "소비자물가" in t or "물가지수" in t) and basket_hit >= 1 and strong_hit == 0:
        return True
    return False

def is_policy_announcement_issue(text: str, dom: str = "", press: str = "") -> bool:
    """정책/기관 발표성 기사인지 판정(공급/유통 섹션 과다 유입 방지용).
    단, 일반 언론의 '품목 가격/수급' 중심 기사까지 과하게 policy로 보내지 않도록 시장/품목 강신호는 예외 처리.
    """
    t = (text or "").lower()
    d = normalize_host(dom or "")
    p = (press or "").strip()
    if not t:
        return False

    if is_policy_market_brief_context(t, d, p):
        return True

    official = (d in POLICY_DOMAINS) or (p in ("정책브리핑", "농식품부"))
    agency_terms = ("농식품부", "농림축산식품부", "정부", "기재부", "관세청", "검역본부", "aT", "농관원")
    policy_action_terms = (
        "대책", "지원", "할인지원", "점검", "회의", "간담회", "발표", "추진", "시행", "협의", "예산",
        "수급안정", "안정 대책", "긴급", "대응", "관계부처", "지시",
        "관리", "강화", "단속", "보세", "보세구역", "할당관세", "반입", "보관", "창고", "장기 보관"
    )
    market_terms = ("가락시장", "도매시장", "공판장", "경락", "반입", "출하", "재고", "저장", "작황", "산지", "시세")
    commodity_terms = ("사과", "배", "감귤", "만감", "딸기", "포도", "참외", "오이", "토마토", "파프리카", "자두", "매실", "밤")
    agency_hit = count_any(t, [w.lower() for w in agency_terms])
    action_hit = count_any(t, [w.lower() for w in policy_action_terms])
    market_hit = count_any(t, [w.lower() for w in market_terms])
    commodity_hit = count_any(t, [w.lower() for w in commodity_terms])
    price_move = (("가격" in t) or ("시세" in t)) and any(k in t for k in ("상승", "하락", "급등", "급락", "약세", "강세"))

    # 일반언론의 품목/시장 가격기사(예: 사과·배 가격 흐름)는 supply에 남긴다.
    # 단, '할당관세/보세구역/관세청/통관/추천서/추징' 등 강한 행정·제도 신호가 있으면
    # 품목 단어가 일부 포함돼도 정책 기사로 분류한다(예: 수입품 할당관세 악용/관리 강화).
    strong_admin_terms = (
        "할당관세", "관세청", "보세", "보세구역", "수입신고", "통관", "추천서", "추천", "추천 취소",
        "집중관리", "지정", "의무", "신속 유통", "추징", "가산세", "단속", "관리 강화"
    )
    strong_admin_hit = count_any(t, [w.lower() for w in strong_admin_terms])

    if strong_admin_hit == 0:
        # '품목+시장/가격'이 핵심인 일반 기사만 supply에 남김
        if (commodity_hit >= 1 and (market_hit >= 1 or price_move)):
            if not official:
                return False
        # 원예 점수만 높고 정책 실행/행정 신호가 약한 경우(단순 품목 언급)도 supply로 남김
        if best_horti_score("", t) >= 2.2 and action_hit < 2 and agency_hit < 1:
            if not official:
                return False

    if official:
        return (agency_hit + action_hit) >= 1

    # 비공식 도메인이어도 정부/부처 발표성 재인용 기사면 policy 라우팅
    if agency_hit >= 1 and action_hit >= 2 and market_hit == 0 and not price_move:
        return True

    return False

def is_generic_import_item_context(text: str) -> bool:
    """가공/수입 원재료·축산 등 '범품목(식품원료)' 위주의 정책 기사 맥락인지.
    - '냉동딸기/설탕/커피생두/코코아'처럼 원예 품목 단어가 포함돼도,
      기사 본질이 '제도·통관·할당관세 운영'이면 policy가 자연스러운 케이스를 포착한다.
    """
    t = (text or "").lower()
    if not t:
        return False
    generic_items = (
        "설탕", "커피", "생두", "코코아", "코코아가루", "식품원료", "원재료",
        "냉동딸기", "냉동육", "냉동소고기", "냉동돼지고기", "닭고기", "돼지고기", "소고기", "축산물",
        "담합", "과징금", "공정거래위원회", "공정위"
    )
    admin_terms = ("할당관세", "보세", "보세구역", "통관", "수입신고", "추천서", "추징", "가산세", "관세청")
    return (count_any(t, [w.lower() for w in generic_items]) >= 1) and (count_any(t, [w.lower() for w in admin_terms]) >= 1)



def is_supply_stabilization_policy_context(text: str, dom: str = "", press: str = "") -> bool:
    """Return True for policy-style supply stabilization stories.

    These are typically import/discount/release actions routed through
    ministries or retail channels, so they fit policy better than supply.
    """
    t = (text or "").lower()
    if not t:
        return False

    d = normalize_host(dom or "")
    p = (press or "").strip()
    livestock_terms = (
        "축산물", "계란", "달걀", "신선란", "닭고기", "한우", "한돈", "돼지고기", "소고기",
        "우유", "낙농", "양계", "양돈",
    )
    agency_terms = (
        "정부", "농식품부", "농림축산식품부", "기재부", "관세청",
        "aT", "한국농수산식품유통공사", "농협",
    )
    stabilization_terms = (
        "수급", "수급 관리", "가격 안정", "가격안정", "공급", "물량", "비축", "방출",
        "수입", "할당관세", "할인지원", "할인 행사", "할인행사", "납품", "판매",
        "대책", "안정", "특판",
    )
    retail_terms = (
        "홈플러스", "메가마트", "이마트", "롯데마트", "하나로마트",
        "대형마트", "편의점", "온라인", "한판",
    )

    livestock_hit = count_any(t, [w.lower() for w in livestock_terms])
    agency_hit = count_any(t, [w.lower() for w in agency_terms])
    stabilization_hit = count_any(t, [w.lower() for w in stabilization_terms])
    retail_hit = count_any(t, [w.lower() for w in retail_terms])
    official = policy_domain_override(d, t) or (d in POLICY_DOMAINS) or (p in ("정책브리핑", "농식품부"))

    if livestock_hit >= 1 and stabilization_hit >= 2 and (agency_hit >= 1 or retail_hit >= 1 or official):
        return True
    if official and stabilization_hit >= 2 and retail_hit >= 1:
        return True
    return False


def is_policy_market_brief_context(text: str, dom: str = "", press: str = "") -> bool:
    """기관발 농축산물 가격·수급 점검/브리핑 기사인지 판정.
    - 개별 품목 수급 기사와 달리 여러 품목을 한 번에 점검하고,
      농식품부/정부 발표와 가격 추이·변수 설명이 함께 붙는 유형을 policy로 본다.
    - 실제 파이프라인은 네이버 title+description snippet을 쓰므로,
      본문형 표현 대신 "농축산물/대체로/전년 대비/영향 제한적" 같은 요약 패턴도 함께 본다.
    """
    t = (text or "").lower()
    if not t:
        return False

    if is_macro_trade_noise_context(t):
        return False

    d = normalize_host(dom or "")
    p = (press or "").strip()
    officialish = policy_domain_override(d, t) or (d in POLICY_DOMAINS) or (p in ("정책브리핑", "농식품부"))
    agency_terms = (
        "농식품부", "농림축산식품부", "정부", "기재부", "관세청", "aT", "한국농수산식품유통공사",
    )
    broad_item_terms = (
        "농축산물", "농산물", "축산물", "과일", "과일류", "채소", "채소류", "먹거리", "장바구니",
        "사과", "배", "감귤", "딸기", "포도", "상추", "오이", "애호박", "청양고추",
        "돼지고기", "소고기", "계란", "달걀",
    )
    aggregate_terms = ("농축산물", "농산물", "과일류", "채소류", "과일", "채소", "먹거리")
    price_terms = ("가격", "물가", "하락세", "상승세", "강세", "약세", "안정세", "오름세", "내림세")
    brief_terms = (
        "점검 결과", "점검결과", "상황 점검", "수급 점검", "브리핑", "발표", "동향", "추이", "흐름",
        "전주 대비", "전주에 비해", "전년 대비", "전월 대비", "평년 대비", "대체로",
    )
    comparison_terms = ("대체로", "전주 대비", "전주에 비해", "전년 대비", "전월 대비", "평년 대비", "낮은 수준", "높은 수준", "제한적")
    driver_terms = ("중동", "전쟁", "유가", "환율", "변수", "영향", "수급", "공급", "분산 출하", "정부 가용물량")
    wholesale_terms = ("가락시장", "도매시장", "공판장", "경락", "경매", "반입")

    agency_hit = count_any(t, [w.lower() for w in agency_terms])
    item_hit = count_any(t, [w.lower() for w in broad_item_terms])
    aggregate_hit = count_any(t, [w.lower() for w in aggregate_terms])
    price_hit = count_any(t, [w.lower() for w in price_terms])
    brief_hit = count_any(t, [w.lower() for w in brief_terms])
    comparison_hit = count_any(t, [w.lower() for w in comparison_terms])
    driver_hit = count_any(t, [w.lower() for w in driver_terms])
    wholesale_hit = count_any(t, [w.lower() for w in wholesale_terms])

    if wholesale_hit >= 1 and brief_hit == 0 and agency_hit == 0 and not officialish and aggregate_hit == 0:
        return False

    if (officialish or agency_hit >= 1) and price_hit >= 1 and brief_hit >= 1 and item_hit >= 2:
        return True

    if is_broad_macro_price_context("", t) and (officialish or agency_hit >= 1) and (brief_hit >= 1 or driver_hit >= 2):
        return True

    if is_broad_macro_price_context("", t) and aggregate_hit >= 1 and item_hit >= 3 and comparison_hit >= 2 and driver_hit >= 1:
        return True

    return False

def is_trade_policy_issue(text: str) -> bool:
    """통상/관세/검역/통관 등 '정책·제도' 성격이 강한 이슈인지(섹션 재배치/가중치 보정용).
    - 단, 특정 품목(감귤/만감류 등) 수급/가격/출하 맥락이 강하면 supply에 남길 수 있도록
      최종 이동 판단은 별도(commodity 강도)로 한다.
    """
    t = (text or "").lower()
    if not t:
        return False

    # 핵심 통상/제도 키워드
    trade_terms = (
        "관세", "무관세", "할당관세", "fta", "통상", "비관세", "무역", "무역법", "301조",
        "수입", "수출", "검역", "검역요건", "통관", "원산지", "세이프가드", "반덤핑"
    )
    # 이슈를 '정책'으로 만드는 촉발 단어(대응/기준/의무/단속/교육 등)
    action_terms = (
        "대응", "촉각", "대책", "강화", "단속", "관리", "의무", "지정", "요건", "기준", "교육", "점검",
        "취소", "의무화", "협의", "건의", "국회", "정부", "관계부처"
    )

    trade_hit = count_any(t, [w.lower() for w in trade_terms])
    action_hit = count_any(t, [w.lower() for w in action_terms])

    # 최소 2개 이상(관세+수출, 관세+fta, 통상+검역 등)의 조합이면서,
    # 제도/대응 맥락(action)이 1개 이상이면 policy 성격으로 본다.
    if trade_hit >= 2 and action_hit >= 1:
        return True

    # 약한 조합 보완: '관세' + ('수출' 또는 '수입') + ('업체/요건/대응') 류는 자주 정책 기사다.
    if ("관세" in t) and ("수출" in t or "수입" in t) and ("업체" in t or "요건" in t or "대응" in t or "촉각" in t):
        return True

    return False


def is_pest_control_policy_context(text: str) -> bool:
    """병해충 기사 중 '정책 일반'보다 '방제 실무' 성격이 강한지 판정.
    - 지자체/기관 발표가 포함돼도, 본문 중심이 예찰·약제·방제 실행이면 pest를 우선한다.
    """
    t = (text or "").lower()
    if not t:
        return False

    strict_hits = count_any(t, [w.lower() for w in PEST_STRICT_TERMS])
    weather_hits = count_any(t, [w.lower() for w in PEST_WEATHER_TERMS])
    horti_hits = count_any(t, [w.lower() for w in PEST_HORTI_TERMS])
    action_hits = count_any(t, [w.lower() for w in ("전수조사", "정밀예찰", "예찰", "방제", "살포", "약제", "무상공급", "집중방제", "긴급방제", "확산 차단")])
    policy_hits = count_any(t, [w.lower() for w in ("정책", "대책", "조례", "예산", "브리핑", "보도자료", "법", "개정", "관세", "통관")])
    local_gov_hits = count_any(t, [w.lower() for w in ("시", "도", "시청", "도청", "군", "군청", "구", "구청", "지자체")])

    # 명시 해충명(예: 토마토뿔나방) 패턴 보강
    named_pest = re.search(r"[가-힣]{1,8}(나방|진딧물|응애|노린재|총채벌레|깍지벌레|선충)", t) is not None

    pest_signal = (strict_hits >= 1) or (weather_hits >= 1) or named_pest
    # 정책 일반(관세/통상) 신호가 과한 경우는 제외
    if policy_hits >= 4 and ("관세" in t or "통관" in t or "수입" in t):
        return False

    # 지자체/기관 보도자료 형식이라도 병해충 이슈가 명확하면 pest 우선 유지.
    # (예: "과수화상병 확산", "토마토뿔나방 발생")
    return (horti_hits >= 1) and pest_signal and ((action_hits >= 1) or (local_gov_hits >= 1 and strict_hits >= 1))


_PEST_ACTION_TERMS = (
    "전수조사", "정밀예찰", "예찰", "방제", "살포", "약제", "무상공급", "집중방제", "긴급방제", "확산 차단",
)
_PEST_ROUNDUP_TITLE_PREFIX_RX = re.compile(r"^\[[^\]]{1,40}\]")
_PEST_ROUNDUP_TITLE_TERMS = (
    "여기는", "오늘", "이 시각", "개막", "축제", "대회", "공연", "전시", "날씨", "교통", "외", "등",
)


def _has_named_pest_signal(text: str) -> bool:
    t = (text or "").lower()
    return re.search(r"[가-힣]{1,8}(나방|진딧물|응애|노린재|총채벌레|깍지벌레|선충)", t) is not None


def _pest_title_signal_count(title: str) -> int:
    t = (title or "").lower()
    hits = count_any(t, [w.lower() for w in PEST_TITLE_CORE_TERMS])
    hits += count_any(t, [w.lower() for w in PEST_WEATHER_TERMS])
    if _has_named_pest_signal(t):
        hits += 1
    return hits


def is_roundup_digest_title(title: str) -> bool:
    raw = (title or "").strip()
    t = raw.lower()
    if not t:
        return False
    bracketed = _PEST_ROUNDUP_TITLE_PREFIX_RX.search(raw) is not None
    roundup_hits = count_any(t, [w.lower() for w in _PEST_ROUNDUP_TITLE_TERMS])
    tail_digest = t.endswith(" 외") or t.endswith("외") or t.endswith(" 등") or t.endswith("등")
    return (bracketed and roundup_hits >= 1) or (roundup_hits >= 2 and tail_digest)


def is_pest_story_focus_strong(title: str, desc: str) -> bool:
    t = f"{title or ''} {desc or ''}".lower()
    strict_hits = count_any(t, [w.lower() for w in PEST_STRICT_TERMS])
    weather_hits = count_any(t, [w.lower() for w in PEST_WEATHER_TERMS])
    managed_count = int(_managed_commodity_match_summary(title, desc).get("count") or 0)
    horti_hits = count_any(t, [w.lower() for w in PEST_HORTI_TERMS]) + managed_count
    action_hits = count_any(t, [w.lower() for w in _PEST_ACTION_TERMS])
    total_signal = strict_hits + weather_hits
    if horti_hits == 0 or total_signal == 0:
        return False
    if _pest_title_signal_count(title) >= 1:
        return True
    if is_roundup_digest_title(title):
        return False
    return total_signal >= 2 and action_hits >= 2

def is_local_agri_policy_program_context(text: str) -> bool:
    """지자체의 농산물 정책 프로그램(지원/보전/시범사업) 맥락인지 판정."""
    t = (text or "").lower()
    if not t:
        return False

    local_gov_terms = ["서울시", "경기도", "도청", "시청", "군청", "구청", "지자체", "특별자치도"]
    policy_program_terms = ["정책", "시행", "추진", "지원", "보전", "사업", "시범", "전국 최초", "예산", "보조", "확대"]
    agri_market_terms = ["농산물", "도매시장", "출하", "경락", "원예", "과수", "농가"]
    local_gov_named = re.search(r"(?:^|[\s·,，])(?:[가-힣]{2,12}(?:특별자치시|특별자치도|광역시|특별시|시|군|구|도))(?=$|[\s·,，])", text or "") is not None

    return (
        (count_any(t, [w.lower() for w in local_gov_terms]) >= 1 or local_gov_named)
        and count_any(t, [w.lower() for w in policy_program_terms]) >= 2
        and count_any(t, [w.lower() for w in agri_market_terms]) >= 1
    )


_POLICY_LOCAL_PRICE_SUPPORT_ACTOR_TERMS = (
    "서울시", "경기도", "강원도", "충남도", "전남도", "도청", "시청", "군청", "구청",
    "지자체", "특별자치도", "특별자치시", "농협", "원예농협", "품목농협",
)
_POLICY_LOCAL_PRICE_SUPPORT_TERMS = (
    "가격안정", "가격 안정", "최저가격", "최저 가격", "최소가격", "보전", "보전금",
    "차액", "차액 지원", "지원금", "수급 안정", "수급안정", "시장가", "보장",
    "신청 접수", "지원사업", "관리위원회",
)
_POLICY_LOCAL_PRICE_SUPPORT_AGRI_TERMS = (
    "농산물", "원예", "과수", "과일", "채소", "화훼", "농가", "출하", "수급",
)


def is_policy_local_price_support_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    actor_hits = count_any(txt, [w.lower() for w in _POLICY_LOCAL_PRICE_SUPPORT_ACTOR_TERMS])
    if re.search(r"(?:^|[\s·,，])(?:[가-힣]{2,12}(?:특별자치시|특별자치도|광역시|특별시|시|군|구|도))(?=$|[\s·,，])", ttl):
        actor_hits += 1
    elif re.search(r"(?:^|[\s·,，])(?:[가-힣]{2,12}(?:특별자치시|특별자치도|광역시|특별시|시|군|구|도))(?=$|[\s·,，])", desc or ""):
        actor_hits += 1
    support_hits = count_any(txt, [w.lower() for w in _POLICY_LOCAL_PRICE_SUPPORT_TERMS])
    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    agri_hits = count_any(txt, [w.lower() for w in _POLICY_LOCAL_PRICE_SUPPORT_AGRI_TERMS]) + managed_count
    title_support_hits = count_any((ttl or "").lower(), [w.lower() for w in ("가격안정", "최저가격", "최저 가격", "보전", "지원")])
    return (
        actor_hits >= 1
        and agri_hits >= 1
        and (
            support_hits >= 2
            or (support_hits >= 1 and title_support_hits >= 1)
        )
    )


_LOCAL_AGRI_ORG_IN_TITLE_RX = re.compile(
    r"(?:^|[\s·,，])(?:[가-힣]{2,4}\s+)?[가-힣]{2,12}(?:(?:품목\s*)?농협|원예\s*농협|영농조합법인|농업회사법인|조합|작목반|공선회)(?=$|[\s·,，])"
)
_LOCAL_AGRI_ORG_TERMS = (
    "농협", "품목농협", "품목 농협", "원예농협", "원예 농협", "작목반", "공선회", "연합사업단", "영농조합법인", "농업회사법인", "조합",
)
_LOCAL_AGRI_ORG_PROMO_TERMS = (
    "경제사업", "농가실익", "실익", "증진", "활발", "활성화", "성과", "판로", "브랜드",
    "우수", "참여", "인증", "전략품목", "매출", "실적",
)
_LOCAL_AGRI_ORG_FIELD_TERMS = (
    "수출", "선적", "선적식", "검역", "통관", "공동선별", "공선출하", "판로", "판매", "유통",
    "산지유통", "산지유통센터", "apc", "선별", "브랜드",
)
_DIRECT_SUPPLY_SIGNAL_TERMS = (
    "수급", "작황", "출하", "반입", "경락", "경매", "저장", "재고", "생산", "생산량", "물량",
)
_LOCAL_AGRI_INFRA_SELECTION_TERMS = (
    "육성지구", "선정", "지정", "공모", "계획", "기반 시설", "기반시설", "확충", "연계",
)
_LOCAL_AGRI_INFRA_TERMS = (
    "스마트농업", "스마트 농업", "농산물산지유통센터", "산지유통센터", "apc", "인프라",
)
_LOCAL_AGRI_INFRA_OPERATION_TERMS = (
    "준공", "완공", "개장", "개소", "가동", "선별", "선과", "저온", "저온저장",
    "저장고", "경락", "반입", "수출", "검역",
)


_SUPPLY_WEAK_TAIL_PROMO_TERMS = (
    "홍보", "선보여", "소개", "공략", "판촉", "행사", "축제", "시식", "접점", "민속촌",
    "제철 홍보", "출하 시기 홍보",
)
_SUPPLY_WEAK_TAIL_VISIT_TERMS = (
    "격려", "방문", "시찰", "찾아", "현장", "점검", "청취",
)
_SUPPLY_WEAK_TAIL_OFFICIAL_TERMS = (
    "원장", "시장", "군수", "구청장", "도지사", "지사", "청장", "본부장", "센터장",
)
_SUPPLY_TOURISM_EVENT_TERMS = (
    "축제", "축제장", "관광", "여행", "나들이", "투어", "맛보러", "놀러오세요",
    "가볼까", "체험", "명소", "방문객", "먹거리", "겨울재미",
)
_SUPPLY_TOURISM_KEEP_TERMS = (
    "가격", "시세", "수급", "작황", "생육", "출하", "물량", "반입", "경락", "경매",
    "재고", "저장", "냉해", "저온", "피해", "농가", "산지", "도매시장", "공판장",
)
_SUPPLY_PROMO_FEATURE_SEASON_TERMS = (
    "제철", "출하 시기", "출하시기", "출하 집중", "집중되는", "수확", "봄으로 넘어가는 시기", "주요 출하 시기",
)

def is_supply_org_promo_feature_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_supply_stabilization_policy_context(txt) or is_policy_market_brief_context(txt):
        return False

    org_hit = (_LOCAL_AGRI_ORG_IN_TITLE_RX.search(ttl) is not None) or (
        count_any(txt, [w.lower() for w in _LOCAL_AGRI_ORG_TERMS]) >= 1
    )
    if not org_hit:
        return False

    title_item_hits = count_any(ttl.lower(), HORTI_ITEM_TERMS_L)
    try:
        topic, topic_sc = best_topic_and_score(ttl, desc or "")
    except Exception:
        topic, topic_sc = ("", 0.0)
    horti_sc = best_horti_score(ttl, desc or "")
    horti_hit = title_item_hits >= 1 or horti_sc >= 1.8 or (topic in _HORTI_TOPICS_SET and topic_sc >= 1.2)
    if not horti_hit:
        return False

    promo_hits = count_any(txt, [w.lower() for w in _SUPPLY_ORG_PROMO_TERMS])
    season_hits = count_any(txt, [w.lower() for w in _SUPPLY_PROMO_FEATURE_SEASON_TERMS])
    official_hits = count_any(ttl.lower(), [w.lower() for w in _SUPPLY_WEAK_TAIL_OFFICIAL_TERMS])
    visit_hits = count_any(txt, [w.lower() for w in _SUPPLY_WEAK_TAIL_VISIT_TERMS])
    if official_hits >= 1 and visit_hits >= 2:
        return False

    return promo_hits >= 2 and (season_hits >= 1 or has_direct_supply_chain_signal(txt) or title_item_hits >= 1)


def is_supply_tourism_event_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if has_direct_supply_chain_signal(txt):
        return False
    if is_supply_price_outlook_context(title, desc):
        return False
    if is_supply_stabilization_policy_context(txt) or is_policy_market_brief_context(txt):
        return False

    tourism_hits = count_any(txt, [w.lower() for w in _SUPPLY_TOURISM_EVENT_TERMS])
    title_tourism_hits = count_any((ttl or "").lower(), [w.lower() for w in _SUPPLY_TOURISM_EVENT_TERMS])
    if tourism_hits == 0 and title_tourism_hits == 0:
        return False

    keep_hits = count_any(txt, [w.lower() for w in _SUPPLY_TOURISM_KEEP_TERMS])
    horti_hits = count_any(txt, HORTI_ITEM_TERMS_L)
    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    if horti_hits == 0 and managed_count == 0 and best_horti_score(title, desc) < 1.8:
        return False

    return keep_hits == 0 and (title_tourism_hits >= 1 or tourism_hits >= 2)


def is_local_agri_org_feature_context(title: str, desc: str) -> bool:
    """지역 농협/조합의 성과·판로 소개형 기사인지 판정.
    - 공급(supply)의 품목 feature성 홍보는 제외하고,
      유통/현장(dist) 쪽 지역 성과·판로 소개형만 잡는다.
    """
    if is_supply_org_promo_feature_context(title, desc):
        return False

    ttl = title or ""
    ttl_compact = re.sub(r"\s+", "", ttl)
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    org_hit = (_LOCAL_AGRI_ORG_IN_TITLE_RX.search(ttl) is not None) or (_LOCAL_AGRI_ORG_IN_TITLE_RX.search(ttl_compact) is not None) or (
        count_any(txt, [w.lower() for w in _LOCAL_AGRI_ORG_TERMS]) >= 1
    )
    promo_hit = count_any(txt, [w.lower() for w in _LOCAL_AGRI_ORG_PROMO_TERMS])
    field_hit = count_any(txt, [w.lower() for w in _LOCAL_AGRI_ORG_FIELD_TERMS])
    try:
        topic, topic_sc = best_topic_and_score(ttl, desc or "")
    except Exception:
        topic, topic_sc = ("", 0.0)
    horti_hit = (best_horti_score(ttl, desc or "") >= 1.1) or (topic in _HORTI_TOPICS_SET and topic_sc >= 1.0)
    agri_terms = ("농산물", "원예", "과수", "과일", "채소", "화훼", "농가", "샤인머스캣", "포도", "사과", "배", "GAP")
    agri_hit = count_any(txt, [w.lower() for w in agri_terms]) >= 1
    return org_hit and promo_hit >= 2 and field_hit >= 1 and (horti_hit or agri_hit)


_DIST_LOCAL_FIELD_PROFILE_TITLE_TERMS = (
    "\ud488\ubaa9\ub18d\ud611", "\uc6d0\uc608\ub18d\ud611", "\uc0b0\uc9c0\uc720\ud1b5", "\uacf5\ub3d9\uc120\ubcc4", "\uacf5\uc120\ucd9c\ud558", "\uacbd\uc81c\uc0ac\uc5c5",
)
_DIST_LOCAL_FIELD_PROFILE_BODY_TERMS = (
    "\uc0b0\uc9c0\uc720\ud1b5", "\uacf5\ub3d9\uc120\ubcc4", "\uacf5\uc120\ucd9c\ud558", "\uacf5\ub3d9\ud310\ub9e4", "\ud310\ub85c", "\uc720\ud1b5", "\ucd9c\ud558", "\uacbd\uc81c\uc0ac\uc5c5", "\ube0c\ub79c\ub4dc", "\ub18d\uac00\uc2e4\uc775", "\uc9c0\uc5ed\uacbd\uc81c", "\uc9c0\uc5ed \uacbd\uc81c", "\uc120\ub3c4",
    "\uad6c\ub9e4", "\uac00\uacf5", "\uc9c0\ub3c4\uc0ac\uc5c5", "\uc870\ud569\uc6d0 \uc2e4\uc775", "\uc2e4\uc775", "\uacfc\uc218 \uc804\ubb38",
)
_DIST_MARKET_OPS_MARKET_TERMS = (
    "\uc628\ub77c\uc778\ub3c4\ub9e4\uc2dc\uc7a5", "\uc628\ub77c\uc778 \ub3c4\ub9e4\uc2dc\uc7a5", "\ub18d\uc218\uc0b0\ubb3c \uc628\ub77c\uc778\ub3c4\ub9e4\uc2dc\uc7a5",
    "\ub18d\uc218\uc0b0\ubb3c \uc628\ub77c\uc778 \ub3c4\ub9e4\uc2dc\uc7a5", "\ub3c4\ub9e4\uc2dc\uc7a5", "\uc2dc\uc7a5\uad00\ub9ac\uc6b4\uc601\uc704\uc6d0\ud68c",
    "\uad11\uc5ed\uc218\uae09\uad00\ub9ac\uc13c\ud130", "\uc218\uae09\uad00\ub9ac\uc13c\ud130",
)
_DIST_MARKET_OPS_TERMS = (
    "\uc81c\ub3c4\uac1c\uc120", "\ud65c\uc131\ud654", "\ub0b4\uc2e4\ud654", "\uc2dc\uc7a5\uad00\ub9ac\uc6b4\uc601\uc704\uc6d0\ud68c", "\uc6b4\uc601\uc704\uc6d0\ud68c",
    "\uac70\ub798\uc2e4\uc801", "\uc804\uc218\uc870\uc0ac", "\uc774\uc6a9\uc790", "\ud310\ub9e4\uc790", "\uad6c\ub9e4\uc790", "\uc2dc\uc7a5 \ucc38\uc5ec\uc790",
    "\uc2dc\uc7a5\uc6b4\uc601\uc790", "\ubc1c\uc804\ubc29\uc548", "\uac1c\uc120\ubc29\uc548", "tf", "\ubc95\ub960", "\ubcf8\ud68c\uc758", "\ud1b5\uacfc",
    "\uc218\uae09 \uad00\ub9ac", "\uc120\uc81c \uad00\ub9ac", "\uc2dc\ubc94\uc0ac\uc5c5",
)
_DIST_SUPPLY_MANAGEMENT_CENTER_TERMS = (
    "\uad11\uc5ed\uc218\uae09\uad00\ub9ac\uc13c\ud130", "\uc218\uae09\uad00\ub9ac\uc13c\ud130", "\uc218\uae09 \uad00\ub9ac", "\uc120\uc81c \uad00\ub9ac",
)
_DIST_SUPPLY_MANAGEMENT_OPS_TERMS = (
    "\uac1c\uc18c", "\uac1c\uc18c\uc2dd", "\uc2dc\ubc94\uc0ac\uc5c5", "\uc6b4\uc601", "\ube44\ucd95", "\ud3d0\uae30", "\ucd9c\ud558 \uc870\uc808",
)
_DIST_SALES_CHANNEL_OPS_TERMS = (
    "\uc5f0\ud569\ud310\ub9e4\uc0ac\uc5c5", "\uc9c1\uac70\ub798", "\uc9c1\uac70\ub798 \uc7a5\ud130", "\uacf5\ub3d9\ud310\ub9e4", "\uacf5\ub3d9\uad6c\ub9e4", "\ud310\ub9e4\uc0ac\uc5c5", "\ud310\ub85c \ud655\ub300", "\uc720\ud1b5 \ud65c\uc131\ud654",
    "\ud1b5\ud569\uc720\ud1b5", "\ud1b5\ud569 \uad00\ub9ac", "\ud1b5\ud569\uad00\ub9ac", "\ubb3c\ub7c9 \ud1b5\ud569\uad00\ub9ac", "\ud68c\uc6d0 \ubb3c\ub7c9",
    "\uacf5\ub3d9\ubb3c\ub958", "\uacf5\ub3d9 \ub9c8\ucf00\ud305", "\ubb3c\ub958\u00b7\ub9c8\ucf00\ud305", "\ubb3c\ub958 \ub9c8\ucf00\ud305",
    "\uc628\ub77c\uc778 \uc720\ud1b5\ucc44\ub110", "\uc628\ub77c\uc778 \ud310\ub9e4", "\uc628\ub77c\uc778 \ud310\ub85c", "\uc720\ud1b5\ucc44\ub110", "\ucc44\ub110 \ud655\ub300", "\uc0b0\uc9c0\uc720\ud1b5 \uacbd\uc7c1\ub825", "\uc720\ud1b5 \uac70\uc810", "\uc0b0\uc9c0\uc720\ud1b5 \uac70\uc810",
    "\uac70\ub798\ucc98 \ub2e4\ubcc0\ud654", "\uc720\ud1b5 \ub2e4\ubcc0\ud654", "\ud310\ub9e4 \ud655\ub300", "\uc18c\ube44 \ucd09\uc9c4",
)
_DIST_SALES_CHANNEL_ACTOR_TERMS = (
    "\ub18d\ud611", "\ub18d\ud611\uc911\uc559\ud68c", "\ub18d\ud611\uacbd\uc81c\uc9c0\uc8fc", "\uac15\uc6d0\ub18d\ud611", "\uc9c0\uc5ed\ub18d\ud611", "\ud488\ubaa9\ub18d\ud611", "\uc6d0\uc608\ub18d\ud611",
    "\ub18d\uc5c5\uc720\ud1b5\ubc95\uc778\uc911\uc559\uc5f0\ud569\ud68c", "\ubc95\uc778\uc911\uc559\uc5f0\ud569\ud68c", "\ub18d\uc5c5\uc720\ud1b5\ubc95\uc778", "\ub18d\uc0b0\ubb3c\uc720\ud1b5\ubc95\uc778",
    "\uc720\ud1b5\ubc95\uc778", "\ub3c4\ub9e4\ubc95\uc778", "\uccad\uacfc\ubc95\uc778", "\uacf5\ub3d9\uc0ac\uc5c5\ubc95\uc778", "\ud478\ub4dc\ud1b5\ud569\uc9c0\uc6d0\uc13c\ud130", "\ub85c\uceec\ud478\ub4dc\ud1b5\ud569\uc9c0\uc6d0\uc13c\ud130", "\uba39\uac70\ub9ac\ud1b5\ud569\uc9c0\uc6d0\uc13c\ud130",
)
_HORTI_MARKET_ACTION_TERMS = (
    "\uc218\ub9e4", "\ub9e4\uc785", "\uacf5\ub3d9\uad6c\ub9e4", "\uacf5\ub3d9\ud310\ub9e4", "\uc9c1\uac70\ub798", "\uc9c1\uac70\ub798 \uc7a5\ud130", "\ud310\ub85c", "\ud310\ub85c \ud655\ub300",
    "\uc720\ud1b5 \uac70\uc810", "\uc0b0\uc9c0\uc720\ud1b5", "\uc0b0\uc9c0\uc720\ud1b5 \uac70\uc810", "\uc218\ucd9c", "\uc120\uc801", "\ucd9c\ud558", "\uacf5\ub3d9\uc120\ubcc4",
)
_POLICY_HORTI_DIRECT_ANCHOR_TERMS = (
    "\ub18d\uc0b0\ubb3c", "\uacfc\uc77c", "\ucc44\uc18c", "\uc6d0\uc608", "\uacfc\uc218", "\ud654\ud6fc", "\uacfc\ucc44", "\ub3c4\ub9e4\uc2dc\uc7a5",
    "\uacf5\ud310\uc7a5", "\uac00\ub77d\uc2dc\uc7a5", "\uc0b0\uc9c0\uc720\ud1b5", "\uc0b0\uc9c0\uc720\ud1b5\uc13c\ud130", "apc", "\ud488\ubaa9\ub18d\ud611", "\uc6d0\uc608\ub18d\ud611",
)
_POLICY_HORTI_MIXED_KEEP_TERMS = (
    "\ud560\uc778", "\ud560\uc778\uc9c0\uc6d0", "\ubd80\uc815\uc218\uae09", "\uc2e0\uace0\uc13c\ud130", "\uc6d0\uc0b0\uc9c0", "\uac80\uc5ed", "\ud1b5\uad00",
    "\uc218\uc785", "\uad00\uc138", "\uc720\ud1b5", "\uac00\uaca9", "\uc218\uae09", "\ucd9c\ud558",
)
_POLICY_EVENT_TAIL_TERMS = (
    "\uc138\ubbf8\ub098", "\ud3ec\ub7fc", "\uc124\uba85\ud68c", "\uac04\ub2f4\ud68c", "\ud589\uc0ac", "\uac1c\ucd5c", "\uac15\uc5f0",
    "\uc0c1\ub2f4", "\uc0c1\ub2f4\ud68c", "\ucee8\uc124\ud305", "1:1 \uc0c1\ub2f4", "\uc6cc\ud06c\uc20d",
)
_POLICY_EVENT_KEEP_TERMS = (
    "\uc5c5\ubb34\ubcf4\uace0", "\uc5c5\ubb34\uacc4\ud68d", "\ub300\ucc45", "\uc2dc\ud589", "\ucd94\uc9c4", "\uac1c\ud3b8", "\uac1c\uc815", "\uc608\uc0b0",
    "\ubc95\ub960", "\ubcf8\ud68c\uc758", "\uc804\uc218\uc870\uc0ac", "tf", "\uc81c\ub3c4\uac1c\uc120", "\ud65c\uc131\ud654", "\ub0b4\uc2e4\ud654",
    "\uc2dc\uc7a5\uad00\ub9ac\uc6b4\uc601\uc704\uc6d0\ud68c", "\uc810\uac80", "\ub300\uc751\ubc29\uc548",
)


def is_dist_local_field_profile_context(title: str, desc: str) -> bool:
    """Return True for local hortic coop profiles with real distribution/field value."""
    ttl = (title or "").lower()
    ttl_compact = re.sub(r"\s+", "", ttl)
    txt = f"{title or ''} {desc or ''}".lower()
    if not txt:
        return False

    org_hit = (_LOCAL_AGRI_ORG_IN_TITLE_RX.search(title or "") is not None) or (_LOCAL_AGRI_ORG_IN_TITLE_RX.search(ttl_compact) is not None) or (
        count_any(txt, [w.lower() for w in _LOCAL_AGRI_ORG_TERMS]) >= 1
    )
    if not org_hit:
        return False

    org_title_hits = count_any(ttl, [w.lower() for w in ("\ud488\ubaa9\ub18d\ud611", "\uc6d0\uc608\ub18d\ud611")]) + count_any(ttl_compact, [w.lower() for w in ("\ud488\ubaa9\ub18d\ud611", "\uc6d0\uc608\ub18d\ud611")])
    field_title_hits = count_any(ttl, [w.lower() for w in _DIST_LOCAL_FIELD_PROFILE_TITLE_TERMS]) + count_any(ttl_compact, [w.lower() for w in _DIST_LOCAL_FIELD_PROFILE_TITLE_TERMS])
    field_body_hits = count_any(txt, [w.lower() for w in _DIST_LOCAL_FIELD_PROFILE_BODY_TERMS])
    market_hits = count_any(
        txt,
        [w.lower() for w in ("\uac00\ub77d\uc2dc\uc7a5", "\ub3c4\ub9e4\uc2dc\uc7a5", "\uacf5\ud310\uc7a5", "\uacf5\uc601\ub3c4\ub9e4\uc2dc\uc7a5", "\uacbd\ub77d", "\uacbd\ub9e4", "\ubc18\uc785", "\uc628\ub77c\uc778 \ub3c4\ub9e4\uc2dc\uc7a5", "\uc0b0\uc9c0\uc720\ud1b5", "\uc0b0\uc9c0\uc720\ud1b5\uc13c\ud130")],
    )
    if has_apc_agri_context(txt):
        market_hits += 1

    horti_hits = count_any(txt, HORTI_ITEM_TERMS_L)
    horti_sc = best_horti_score(title or "", desc or "")
    profile_hits = count_any(txt, [w.lower() for w in ("\uc9c0\uc5ed\uacbd\uc81c", "\uc120\ub3c4", "\ube0c\ub79c\ub4dc", "\uacbd\uc81c\uc0ac\uc5c5", "\ub18d\uac00\uc2e4\uc775", "\ud310\ub85c", "\uc720\ud1b5", "\ucd9c\ud558")])
    title_profile_hits = count_any(ttl, [w.lower() for w in ("\uc9c0\uc5ed\uacbd\uc81c \uc120\ub3c4", "\uc9c0\uc5ed\uacbd\uc81c \uc120\ub3c4\ud558\ub294")]) + count_any(
        ttl_compact,
        [w.lower() for w in ("\uc9c0\uc5ed\uacbd\uc81c\uc120\ub3c4", "\uc9c0\uc5ed\uacbd\uc81c\uc120\ub3c4\ud558\ub294")],
    )
    coop_field_hits = count_any(
        txt,
        [w.lower() for w in ("\uad6c\ub9e4", "\uac00\uacf5", "\uc9c0\ub3c4\uc0ac\uc5c5", "\uc870\ud569\uc6d0 \uc2e4\uc775", "\uc2e4\uc775", "\uc9c0\uc5ed \uacbd\uc81c", "\uacfc\uc218 \uc804\ubb38")],
    )
    horti_org_hits = count_any(txt, [w.lower() for w in ("\uacfc\uc218", "\uc0ac\uacfc", "\ubc30", "\ud3ec\ub3c4", "\uac10\uade4", "\uc6d0\uc608", "\ub18d\uc0b0\ubb3c", "\ub18d\uac00")])

    if org_title_hits >= 1 and (horti_hits >= 1 or horti_sc >= 1.4 or horti_org_hits >= 1):
        if field_title_hits >= 1 and (market_hits >= 1 or profile_hits >= 2):
            return True
        if title_profile_hits >= 1 and (field_body_hits >= 1 or market_hits >= 1 or coop_field_hits >= 1):
            return True
        if field_body_hits >= 3 and profile_hits >= 2:
            return True
        if field_title_hits >= 1 and market_hits >= 1 and (field_body_hits + coop_field_hits) >= 1:
            return True
    return False


def is_dist_market_ops_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """Return True for market-operation / online wholesale reform stories that fit dist."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom):
        return False

    market_hits = count_any(txt, [w.lower() for w in _DIST_MARKET_OPS_MARKET_TERMS])
    ops_hits = count_any(txt, [w.lower() for w in _DIST_MARKET_OPS_TERMS])
    actor_hits = count_any(
        txt,
        [w.lower() for w in ("aT", "\ud55c\uad6d\ub18d\uc218\uc0b0\uc2dd\ud488\uc720\ud1b5\uacf5\uc0ac", "\ub18d\uc2dd\ud488\ubd80", "\ub18d\ub9bc\ucd95\uc0b0\uc2dd\ud488\ubd80", "\uc2dc\uc7a5\uc6b4\uc601\uc790")],
    )
    agri_hits = count_any(
        txt,
        [w.lower() for w in ("\ub18d\uc0b0\ubb3c", "\ub18d\uc218\uc0b0\ubb3c", "\uc6d0\uc608", "\uacfc\uc218", "\uacfc\uc77c", "\ucc44\uc18c", "\uc0b0\uc9c0\uc720\ud1b5", "\ub3c4\ub9e4\uc2dc\uc7a5", "aT")],
    )
    event_hits = count_any(txt, [w.lower() for w in ("\uc138\ubbf8\ub098", "\ud3ec\ub7fc", "\uc124\uba85\ud68c", "\uac04\ub2f4\ud68c", "\ud589\uc0ac", "\uac1c\ucd5c")])

    if market_hits == 0 or ops_hits < 2:
        return False
    if event_hits >= 2 and ops_hits < 3:
        return False
    return actor_hits >= 1 or agri_hits >= 2


def is_dist_supply_management_center_context(title: str, desc: str) -> bool:
    """Return True for supply-management center operation stories that fit dist."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    center_hits = count_any(txt, [w.lower() for w in _DIST_SUPPLY_MANAGEMENT_CENTER_TERMS])
    ops_hits = count_any(txt, [w.lower() for w in _DIST_SUPPLY_MANAGEMENT_OPS_TERMS])
    agri_hits = count_any(
        txt,
        [w.lower() for w in ("\ub18d\uc0b0\ubb3c", "\ucc44\uc18c", "\ubc30\ucd94", "\ubb34", "\uc0b0\uc9c0", "\uc720\ud1b5", "\uc218\uae09")],
    )
    return center_hits >= 2 and agri_hits >= 1 and ops_hits >= 1


def is_dist_sales_channel_ops_context(title: str, desc: str) -> bool:
    """Return True for agri joint-sales/direct-trade operation stories that fit dist."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    channel_hits = count_any(txt, [w.lower() for w in _DIST_SALES_CHANNEL_OPS_TERMS])
    actor_hits = count_any(txt, [w.lower() for w in _DIST_SALES_CHANNEL_ACTOR_TERMS])
    agri_hits = count_any(txt, [w.lower() for w in ("\ub18d\uc5c5", "\ub18d\uc0b0\ubb3c", "\ub18d\uac00", "\uc720\ud1b5", "\ud310\ub85c", "\uc0b0\uc9c0\uc720\ud1b5", "\uac00\ub77d\uc2dc\uc7a5", "\ub3c4\ub9e4\uc2dc\uc7a5")])
    market_hits = count_any(txt, [w.lower() for w in ("\uac00\ub77d\uc2dc\uc7a5", "\ub3c4\ub9e4\uc2dc\uc7a5", "\uacf5\ud310\uc7a5", "\uc0b0\uc9c0\uc720\ud1b5", "\ucd9c\ud558", "\ubb3c\ub958", "\uc720\ud1b5\ucc44\ub110")])
    event_hits = count_any(txt, [w.lower() for w in ("\ud3c9\uac00\ud68c", "\uc6cc\ud06c\uc20d", "\ud68c\uc758", "\uac04\ub2f4\ud68c")])
    title_hits = count_any(
        ttl.lower(),
        [w.lower() for w in ("\uc5f0\ud569\ud310\ub9e4\uc0ac\uc5c5", "\uc9c1\uac70\ub798", "\ud310\ub9e4\uc0ac\uc5c5", "\ud1b5\ud569\uc720\ud1b5", "\ubb3c\ub7c9 \ud1b5\ud569\uad00\ub9ac", "\uc18c\ube44 \ucd09\uc9c4", "\uc628\ub77c\uc778 \ud310\ub9e4", "\uac70\ub798\ucc98 \ub2e4\ubcc0\ud654")]
    )
    return actor_hits >= 1 and (
        (
            channel_hits >= 2
            and (agri_hits >= 2 or market_hits >= 1 or (title_hits >= 1 and event_hits >= 1))
        )
        or (channel_hits >= 1 and title_hits >= 1 and agri_hits >= 1)
    )


def is_horti_market_action_context(title: str, desc: str) -> bool:
    txt = f"{title or ''} {desc or ''}".lower()
    if not txt:
        return False
    action_hits = count_any(txt, [w.lower() for w in _HORTI_MARKET_ACTION_TERMS])
    if action_hits == 0:
        return False
    managed_count = int(_managed_commodity_match_summary(title or "", desc or "").get("count") or 0)
    agri_hits = count_any(
        txt,
        [w.lower() for w in ("\ub18d\uc0b0\ubb3c", "\ub18d\uc5c5", "\ub18d\uac00", "\uc720\ud1b5", "\ud310\ub85c", "\uc0b0\uc9c0\uc720\ud1b5", "\ucd9c\ud558", "\uc218\ucd9c")],
    ) + managed_count
    return agri_hits >= 1 or best_horti_score(title or "", desc or "") >= 1.2


def _policy_horti_anchor_stats(title: str, desc: str, dom: str = "", press: str = "") -> dict[str, Any]:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    price_collapse_issue = is_policy_price_collapse_issue_context(ttl, desc or "")
    direct_anchor_hits = count_any(txt, [w.lower() for w in _POLICY_HORTI_DIRECT_ANCHOR_TERMS])
    title_anchor_hits = count_any((ttl or "").lower(), [w.lower() for w in _POLICY_HORTI_DIRECT_ANCHOR_TERMS])
    market_hits = count_any(
        txt,
        [w.lower() for w in ("\ub3c4\ub9e4\uc2dc\uc7a5", "\uacf5\ud310\uc7a5", "\uac00\ub77d\uc2dc\uc7a5", "\uc0b0\uc9c0\uc720\ud1b5", "\uc0b0\uc9c0\uc720\ud1b5\uc13c\ud130", "\uc720\ud1b5", "\ud310\ub85c", "apc")],
    )
    if has_apc_agri_context(txt):
        market_hits += 1
    mixed_keep_hits = 0
    if "\ub18d\ucd95\uc0b0\ubb3c" in txt:
        mixed_keep_hits = count_any(txt, [w.lower() for w in _POLICY_HORTI_MIXED_KEEP_TERMS])

    txt_wo_neutral = txt
    for phrase in LIVESTOCK_NEUTRAL_PHRASES:
        txt_wo_neutral = txt_wo_neutral.replace((phrase or "").lower(), "")
    livestock_hits = count_any(txt_wo_neutral, [t.lower() for t in LIVESTOCK_STRICT_TERMS])
    title_livestock_hits = count_any((ttl or "").lower(), [t.lower() for t in LIVESTOCK_STRICT_TERMS])
    livestock_core = ("\ucd95\uc0b0\ubb3c" in txt_wo_neutral) or any(
        w in txt_wo_neutral
        for w in ("\ud55c\uc6b0", "\ub3fc\uc9c0", "\ub3fc\uc9c0\uace0\uae30", "\uc18c\uace0\uae30", "\uacc4\ub780", "\ub2ed\uace0\uae30", "asf", "ai ", "ai\u00b7", "ai,", "\uad6c\uc81c\uc5ed", "\uc870\ub958\uc778\ud50c\ub8e8\uc5d4\uc790")
    )
    horti_sc = best_horti_score(ttl, desc or "")
    anchor_ok = (
        managed_count >= 1
        or direct_anchor_hits >= 1
        or market_hits >= 1
        or price_collapse_issue
        or ("\ub18d\ucd95\uc0b0\ubb3c" in txt and mixed_keep_hits >= 2)
        or (livestock_hits == 0 and horti_sc >= 1.8)
    )
    livestock_dominant = (
        livestock_core
        and livestock_hits >= 1
        and managed_count == 0
        and market_hits == 0
        and mixed_keep_hits == 0
        and (
            direct_anchor_hits == 0
            or (
                title_livestock_hits >= 1
                and title_anchor_hits <= 1
                and direct_anchor_hits <= 1
            )
        )
    )
    return {
        "anchor_ok": bool(anchor_ok),
        "livestock_dominant": bool(livestock_dominant),
        "managed_count": managed_count,
        "direct_anchor_hits": direct_anchor_hits,
        "mixed_keep_hits": mixed_keep_hits,
        "market_hits": market_hits,
    }


def policy_has_horti_anchor(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    return bool(_policy_horti_anchor_stats(title, desc, dom, press).get("anchor_ok"))


def is_policy_livestock_dominant_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    return bool(_policy_horti_anchor_stats(title, desc, dom, press).get("livestock_dominant"))


_TITLE_LIVESTOCK_CORE_TERMS = (
    "축산물", "한우", "한돈", "우육", "돈육", "소고기", "돼지고기", "닭고기",
    "계란", "달걀", "우유", "낙농", "양돈", "양계", "축산법", "축산정책", "asf", "구제역", "조류인플루엔자",
)
_TITLE_HORTI_DIRECT_TERMS = (
    "농산물", "원예", "과수", "과일", "채소", "화훼", "청과",
    "사과", "배", "감귤", "딸기", "포도", "오이", "토마토", "고추", "파프리카",
    "상추", "양파", "마늘", "배추", "무", "참외", "키위", "자두", "복숭아",
)
_AGRI_TRAINING_RECRUITMENT_TERMS = (
    "농업대학", "농업 대학", "농민대학", "귀농대학", "아카데미",
    "신입생 모집", "교육생 모집", "수강생 모집", "과정 모집", "교육 과정",
)
_AGRI_ORG_RENAME_TERMS = (
    "명칭 변경", "명칭변경", "사명 변경", "사명변경",
)
_POLICY_FOREST_ADMIN_TERMS = (
    "산불", "산불방지", "산불 방지", "산불예방", "산불 예방", "산림", "산림청", "임업",
)
_POLICY_BUDGET_DRIVE_TERMS = (
    "국가투자예산", "예산 확보", "예산확보", "확보 총력", "전략사업", "전략 사업",
    "신규사업", "신규 사업", "사업 발굴", "현안 사업",
)
_DIST_POLITICAL_VISIT_TITLE_TERMS = (
    "정청래", "의원", "대표", "후보", "예비후보", "위원장", "당대표",
    "국힘", "국민의힘", "민주당", "더불어민주당",
)
_DIST_POLITICAL_VISIT_TERMS = (
    "찾은", "찾아", "방문", "현장행보", "민심", "민생 속으로", "시동", "공약",
    "비상계엄", "탄핵", "계엄", "사과하라", "선거", "지선", "총선",
)
_DIST_POLITICAL_VISIT_KEEP_TERMS = (
    "가격", "수급", "경락", "경매", "반입", "출하", "하역", "물량", "운영",
    "제도개선", "제도 개선", "tf", "검역", "원산지", "단속", "온라인 도매시장",
    "산지유통", "산지유통센터",
)
_DIST_LOCAL_CROP_STRATEGY_TERMS = (
    "지역특화작목", "특화작목", "전략작목", "미래전략", "육성지구",
    "스마트농업", "스마트 농업", "중심지", "도약",
)
_PEST_INPUT_MARKETING_TERMS = (
    "허위", "과대광고", "광고", "온라인", "표시", "비료", "영양제", "자재",
)
_SUPPLY_PRICE_OUTLOOK_GROUP_TERMS = (
    "저장채소", "시설채소", "과채류", "채소류", "과일류", "양념채소", "엽채류",
)
_SUPPLY_PRICE_OUTLOOK_TREND_TERMS = (
    "상승", "하락", "약세", "강세", "오르고", "내리고", "줄 듯", "늘 듯",
    "전망", "재배면적", "생산량", "작황", "출하",
)


def is_title_livestock_dominant_context(title: str, desc: str = "") -> bool:
    ttl = (title or "").lower()
    desc_l = (desc or "").lower()
    if not ttl:
        return False
    ttl_wo_neutral = ttl
    for phrase in LIVESTOCK_NEUTRAL_PHRASES:
        ttl_wo_neutral = ttl_wo_neutral.replace((phrase or "").lower(), "")
    title_livestock_hits = count_any(ttl_wo_neutral, [w.lower() for w in _TITLE_LIVESTOCK_CORE_TERMS])
    livestock_core_in_title = ("축산물" in ttl_wo_neutral) or ("축산" in ttl_wo_neutral) or any(w in ttl_wo_neutral for w in ("한우", "한돈", "돼지고기", "소고기", "계란", "달걀"))
    title_horti_hits = count_any(ttl, [w.lower() for w in _TITLE_HORTI_DIRECT_TERMS]) + count_any(ttl, HORTI_ITEM_TERMS_L)
    managed_count = int(_managed_commodity_match_summary(title or "", "").get("count") or 0)
    market_hits = count_any(ttl_wo_neutral, [w.lower() for w in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "apc")])
    desc_horti_hits = count_any(desc_l, [w.lower() for w in _TITLE_HORTI_DIRECT_TERMS]) + count_any(desc_l, HORTI_ITEM_TERMS_L)
    macro_mix_keep = desc_horti_hits >= 1 and (
        is_broad_macro_price_context(title or "", desc or "")
        or count_any(f"{ttl} {desc_l}", [w.lower() for w in ("농축산물", "물가", "수급", "안정", "할인지원", "성수품")]) >= 1
    )
    return (
        livestock_core_in_title
        and title_livestock_hits >= 1
        and title_horti_hits == 0
        and managed_count == 0
        and market_hits == 0
        and best_horti_score(title or "", "") < 1.2
        and (not macro_mix_keep)
    )


def is_agri_training_recruitment_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    training_hits = count_any(txt, [w.lower() for w in _AGRI_TRAINING_RECRUITMENT_TERMS])
    if training_hits == 0:
        return False
    keep_hits = count_any(
        txt,
        [w.lower() for w in ("가격", "수급", "출하", "경락", "경매", "도매시장", "공판장", "가락시장", "산지유통", "직거래", "연합판매사업", "가격안정", "검역", "통관", "선적", "병해충", "방제", "예찰")],
    )
    return keep_hits < 2


def is_agri_org_rename_context(title: str, desc: str) -> bool:
    txt = f"{title or ''} {desc or ''}".lower()
    if not txt:
        return False
    rename_hits = count_any(txt, [w.lower() for w in _AGRI_ORG_RENAME_TERMS])
    if rename_hits == 0:
        return False
    keep_hits = count_any(
        txt,
        [w.lower() for w in ("가격", "수급", "출하", "경락", "경매", "도매시장", "공판장", "가락시장", "산지유통", "판매사업", "연합판매사업", "직거래", "가격안정", "검역", "통관", "선적")],
    )
    return keep_hits < 2


def is_policy_forest_admin_noise_context(title: str, desc: str) -> bool:
    txt = f"{title or ''} {desc or ''}".lower()
    if not txt:
        return False
    forest_hits = count_any(txt, [w.lower() for w in _POLICY_FOREST_ADMIN_TERMS])
    if forest_hits == 0:
        return False
    keep_hits = count_any(txt, [w.lower() for w in ("과수", "사과", "배", "감귤", "딸기", "채소", "원예", "농산물", "묘목")])
    return keep_hits == 0 and best_horti_score(title or "", desc or "") < 1.6


def is_policy_budget_drive_noise_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    budget_hits = count_any(txt, [w.lower() for w in _POLICY_BUDGET_DRIVE_TERMS])
    if budget_hits == 0:
        return False
    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    keep_hits = count_any(
        txt,
        [w.lower() for w in ("가격안정", "가격 안정", "수급", "출하비용", "보전", "최소가격", "할인지원", "검역", "원산지", "단속", "도매시장", "공판장", "가락시장", "농산물", "원예", "과수", "과일", "채소")],
    ) + managed_count
    return keep_hits < 3 and _LOCAL_GEO_PATTERN.search(ttl) is not None


def is_dist_political_visit_context(title: str, desc: str) -> bool:
    ttl = (title or "").lower()
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    venue_hits = count_any(ttl, [w.lower() for w in ("가락시장", "도매시장", "공판장", "시장")])
    if venue_hits == 0:
        return False
    actor_hits = count_any(ttl, [w.lower() for w in _DIST_POLITICAL_VISIT_TITLE_TERMS])
    politics_hits = count_any(txt, [w.lower() for w in _DIST_POLITICAL_VISIT_TERMS])
    keep_hits = count_any(txt, [w.lower() for w in _DIST_POLITICAL_VISIT_KEEP_TERMS])
    agri_hits = count_any(txt, [w.lower() for w in ("농산물", "원예", "과수", "과일", "채소", "화훼")])
    title_keep_hits = count_any(ttl, [w.lower() for w in ("가격", "수급", "경락", "경매", "반입", "출하", "하역", "운영", "제도개선", "제도 개선")])
    title_visit_hits = count_any(ttl, [w.lower() for w in ("찾은", "찾아", "방문", "민심", "지선", "시동", "사과하라", "계엄")])
    if venue_hits >= 1 and title_keep_hits == 0 and agri_hits == 0:
        if (actor_hits >= 1 or politics_hits >= 2) and politics_hits >= 1 and keep_hits < 2:
            return True
        if count_any(ttl, [w.lower() for w in ("찾은", "찾아", "방문")]) >= 1 and count_any(ttl, [w.lower() for w in ("민심", "지선", "시동", "사과하라", "계엄")]) >= 1:
            return True
    return False


def is_dist_local_crop_strategy_noise_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    strategy_hits = count_any(txt, [w.lower() for w in _DIST_LOCAL_CROP_STRATEGY_TERMS])
    if strategy_hits == 0:
        return False
    if _LOCAL_REGION_IN_TITLE_RX.search(ttl) is None and strategy_hits < 2:
        return False
    if is_dist_market_ops_context(title, desc) or is_dist_supply_management_center_context(title, desc) or is_dist_sales_channel_ops_context(title, desc):
        return False
    if is_dist_market_disruption_context(title, desc) or is_dist_export_shipping_context(title, desc):
        return False
    keep_hits = count_any(
        txt,
        [w.lower() for w in ("도매시장", "공판장", "가락시장", "경락", "경매", "반입", "산지유통", "산지유통센터", "apc", "선별", "저온", "물류", "직거래", "연합판매사업", "판매사업", "검역", "통관", "선적", "출하")],
    )
    return keep_hits < 2


def is_pest_input_marketing_noise_context(title: str, desc: str) -> bool:
    ttl = (title or "").lower()
    txt = f"{title or ''} {desc or ''}".lower()
    if not txt:
        return False
    marketing_hits = count_any(txt, [w.lower() for w in _PEST_INPUT_MARKETING_TERMS])
    if marketing_hits < 2:
        return False
    named_pest = re.search(r"[가-힣]{1,8}(나방|진딧물|응애|노린재|총채벌레|깍지벌레|선충)", txt) is not None
    disease_hits = count_any(txt, [w.lower() for w in ("과수화상병", "탄저병", "역병", "노균병", "흰가루병", "냉해", "동해", "병해충", "방제", "예찰")])
    action_hits = count_any(txt, [w.lower() for w in _PEST_ACTION_TERMS])
    deceptive_hits = count_any(txt, [w.lower() for w in ("허위", "과대광고", "광고", "온라인", "표시")])
    title_real_pest_hits = count_any((title or "").lower(), [w.lower() for w in ("과수화상병", "탄저병", "역병", "노균병", "흰가루병", "병해충", "방제", "예찰", "냉해", "동해")])
    if ("비료" in ttl) and count_any(ttl, [w.lower() for w in ("허위", "과대광고", "광고", "온라인", "표시")]) >= 1 and title_real_pest_hits == 0:
        return True
    return (not named_pest) and disease_hits == 0 and action_hits < 2 and ("비료" in txt) and deceptive_hits >= 2 and title_real_pest_hits == 0


def is_supply_price_outlook_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    group_hits = count_any(txt, [w.lower() for w in _SUPPLY_PRICE_OUTLOOK_GROUP_TERMS])
    trend_hits = count_any(txt, [w.lower() for w in _SUPPLY_PRICE_OUTLOOK_TREND_TERMS])
    price_hits = count_any(txt, [w.lower() for w in ("가격", "시세", "수급", "재배면적", "생산량", "출하", "작황")])
    title_trend_hits = count_any(ttl.lower(), [w.lower() for w in _SUPPLY_PRICE_OUTLOOK_TREND_TERMS])
    return (managed_count >= 2 or group_hits >= 1) and (price_hits >= 2 or trend_hits >= 3) and (title_trend_hits >= 1 or best_horti_score(ttl, "") >= 1.2)


_DIST_FIELD_MARKET_RESPONSE_TERMS = (
    "소비대책", "소비 대책", "소비 촉진", "현장", "유통현장", "도매가격", "가격 약세", "산지 물량", "판로", "공동 대응",
)
_DIST_FIELD_MARKET_RESPONSE_TITLE_TERMS = (
    "노지채소", "겨울 노지채소", "소비대책", "소비 촉진", "현장", "도매가격", "가격 약세",
)
_DIST_FIELD_MARKET_RESPONSE_DISTRESS_TERMS = (
    "약세", "하락", "침체", "부진", "재고", "물량", "가격 약세", "도매가격 약세",
)
_DIST_FIELD_MARKET_RESPONSE_AGRI_TERMS = (
    "농산물", "농업", "산지", "채소", "노지채소", "겨울 노지채소", "도매가격", "유통", "농가",
)


def is_dist_field_market_response_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """Return True for field-level agri market response stories that should fit dist."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom):
        return False

    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    agri_hits = count_any(txt, [w.lower() for w in _DIST_FIELD_MARKET_RESPONSE_AGRI_TERMS]) + managed_count
    response_hits = count_any(txt, [w.lower() for w in _DIST_FIELD_MARKET_RESPONSE_TERMS])
    distress_hits = count_any(txt, [w.lower() for w in _DIST_FIELD_MARKET_RESPONSE_DISTRESS_TERMS])
    title_hits = count_any(ttl.lower(), [w.lower() for w in _DIST_FIELD_MARKET_RESPONSE_TITLE_TERMS])
    trade_press = ((press or "").strip() in AGRI_TRADE_PRESS) or (normalize_host(dom or "") in AGRI_TRADE_HOSTS)

    return agri_hits >= 2 and response_hits >= 2 and distress_hits >= 1 and (trade_press or title_hits >= 1)


def is_policy_event_tail_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """Return True for event/seminar style policy tails that should yield to stronger policy briefs."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom):
        return False
    event_hits = count_any(txt, [w.lower() for w in _POLICY_EVENT_TAIL_TERMS])
    if event_hits == 0:
        return False
    if count_any(txt, [w.lower() for w in _POLICY_EVENT_KEEP_TERMS]) >= 1:
        return False
    actor_hits = count_any(
        txt,
        [w.lower() for w in ("\ub18d\uc2dd\ud488\ubd80", "\ub18d\ub9bc\ucd95\uc0b0\uc2dd\ud488\ubd80", "aT", "\ud55c\uad6d\ub18d\uc218\uc0b0\uc2dd\ud488\uc720\ud1b5\uacf5\uc0ac", "\uc7a5\uad00", "\uc815\ucc45\uad00")],
    )
    return actor_hits >= 1


_POLICY_MAJOR_ISSUE_ACTOR_TERMS = (
    "농식품부", "농림축산식품부", "정부", "국회", "국회의원", "의원",
    "관세청", "검역본부", "농관원", "aT", "한국농수산식품유통공사",
)
_POLICY_MAJOR_ISSUE_AGRI_TERMS = (
    "농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "청과",
    "유통", "도매시장", "공판장", "가락시장", "산지유통", "산지유통센터", "온라인 도매시장",
)
_POLICY_MAJOR_ISSUE_TERMS = (
    "협의체", "전문가 협의체", "위원회", "출범", "발족", "특별관리", "집중관리",
    "제도 개선", "제도개선", "구조 개선", "구조개선", "유통 구조 개선", "가격 결정 구조",
    "최소가격", "최소가격 보전제", "보전제", "가격안정제",
    "개선 계획", "개선안", "개편안", "도입", "제안", "촉구", "대응 방안",
    "가격 폭락", "가격폭락", "가격 붕괴", "가격붕괴", "폭락 방지",
    "수급 안정 대책", "수급안정 대책", "대책 촉구", "대책 마련",
    "건의안", "건의안 발의", "대정부 건의안",
    "관리 강화", "모니터링", "물가지수", "소비자물가지수", "실태조사",
)
_POLICY_MAJOR_ISSUE_TITLE_TERMS = (
    "협의체", "위원회", "출범", "특별관리", "최소가격", "보전제",
    "제도 개선", "제도개선", "구조 개선", "구조개선", "가격 결정 구조",
    "가격 폭락", "가격폭락", "가격 붕괴", "가격붕괴", "폭락 방지",
    "대책 촉구", "건의안", "건의안 발의",
)
_POLICY_MAJOR_ISSUE_PROPOSAL_TERMS = (
    "제안", "촉구", "도입", "법안", "개정안", "최소가격", "보전제", "가격안정제", "특별관리",
    "건의안", "건의안 발의", "대정부 건의안", "결의안", "대책 촉구", "대책 마련",
)

_POLICY_PRICE_COLLAPSE_TERMS = (
    "가격 폭락", "가격폭락", "가격 붕괴", "가격붕괴", "폭락 방지",
    "가격 급락", "가격급락", "가격 하락", "가격하락", "수급 안정",
)
_POLICY_PRICE_COLLAPSE_TITLE_TERMS = (
    "가격 폭락", "가격폭락", "가격 붕괴", "가격붕괴", "폭락 방지",
    "수급 안정", "수급안정",
)
_POLICY_PRICE_COLLAPSE_ACTION_TERMS = (
    "대책 촉구", "대책 마련", "마련 촉구", "촉구", "건의안", "건의안 발의",
    "대정부 건의안", "건의", "요구", "발의",
)
_POLICY_PRICE_COLLAPSE_ACTOR_TERMS = (
    "국회", "국회의원", "의원", "도의원", "시의원", "군의원", "구의원",
    "농민", "농민들", "농가", "농가들", "생산자", "생산자들", "재배농가",
    "연합회", "협회", "대정부", "정부",
)


def is_policy_price_collapse_issue_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    agri_hits = count_any(txt, [w.lower() for w in _POLICY_MAJOR_ISSUE_AGRI_TERMS]) + managed_count
    title_item_hits = count_any((ttl or "").lower(), [w.lower() for w in _TITLE_HORTI_DIRECT_TERMS])
    if managed_count == 0 and agri_hits == 0 and title_item_hits == 0:
        return False

    price_hits = count_any(txt, [w.lower() for w in _POLICY_PRICE_COLLAPSE_TERMS])
    title_price_hits = count_any((ttl or "").lower(), [w.lower() for w in _POLICY_PRICE_COLLAPSE_TITLE_TERMS])
    action_hits = count_any(txt, [w.lower() for w in _POLICY_PRICE_COLLAPSE_ACTION_TERMS])
    actor_hits = count_any(txt, [w.lower() for w in _POLICY_PRICE_COLLAPSE_ACTOR_TERMS])
    if re.search(r"(?:^|[\s\"'“”‘’])(?:[가-힣]{2,20})(?:국회의원|도의원|시의원|군의원|구의원|의원)", ttl):
        actor_hits += 1
    policy_hits = count_any(txt, [w.lower() for w in ("정부", "대정부", "국회", "농식품부", "농림축산식품부")])
    return (
        (price_hits >= 2 or (price_hits >= 1 and title_price_hits >= 1))
        and action_hits >= 1
        and (actor_hits >= 1 or policy_hits >= 1 or managed_count >= 1 or title_item_hits >= 1)
    )


def is_policy_major_issue_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """Return True for agriculture-facing policy/major-issue stories beyond narrow official briefs."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    dom_norm = normalize_host(dom or "")
    press_norm = (press or "").strip()

    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom_norm):
        return False
    if is_retail_sales_trend_context(txt):
        return False
    if is_dist_export_shipping_context(ttl, desc or ""):
        return False
    if is_dist_export_field_context(ttl, desc or "", dom_norm, press_norm):
        return False
    if is_dist_market_ops_context(ttl, desc or "", dom_norm, press_norm):
        return False
    if is_dist_supply_management_center_context(ttl, desc or ""):
        return False
    if is_dist_sales_channel_ops_context(ttl, desc or ""):
        return False
    if is_dist_field_market_response_context(ttl, desc or "", dom_norm, press_norm):
        return False
    if is_policy_general_macro_tail_context(ttl, desc or "", dom_norm, press_norm):
        return False
    if is_policy_event_tail_context(ttl, desc or "", dom_norm, press_norm):
        return False

    if is_supply_stabilization_policy_context(txt, dom_norm, press_norm):
        return True
    if is_policy_market_brief_context(txt, dom_norm, press_norm):
        return True
    if is_policy_export_support_brief_context(ttl, desc or "", dom_norm, press_norm):
        return True
    if is_policy_local_price_support_context(ttl, desc or ""):
        return True
    if is_local_agri_policy_program_context(txt):
        return True
    if is_policy_price_collapse_issue_context(ttl, desc or ""):
        return True

    managed_summary = _managed_commodity_match_summary(ttl, desc or "")
    managed_count = int(managed_summary.get("count") or 0)
    agri_hits = count_any(txt, [w.lower() for w in _POLICY_MAJOR_ISSUE_AGRI_TERMS])
    if agri_hits == 0 and managed_count == 0:
        return False

    actor_hits = count_any(txt, [w.lower() for w in _POLICY_MAJOR_ISSUE_ACTOR_TERMS])
    issue_hits = count_any(txt, [w.lower() for w in _POLICY_MAJOR_ISSUE_TERMS])
    title_issue_hits = count_any((ttl or "").lower(), [w.lower() for w in _POLICY_MAJOR_ISSUE_TITLE_TERMS])
    proposal_hits = count_any(txt, [w.lower() for w in _POLICY_MAJOR_ISSUE_PROPOSAL_TERMS])
    officialish = (
        policy_domain_override(dom_norm, txt)
        or (dom_norm in POLICY_DOMAINS)
        or (dom_norm in OFFICIAL_HOSTS)
        or any(dom_norm.endswith("." + h) for h in OFFICIAL_HOSTS)
        or (press_norm in ("정책브리핑", "농식품부"))
    )

    if officialish and (issue_hits >= 1 or title_issue_hits >= 1):
        return True
    if actor_hits >= 1 and issue_hits >= 2:
        return True
    if actor_hits >= 2 and (title_issue_hits >= 1 or proposal_hits >= 1):
        return True
    if proposal_hits >= 2 and (agri_hits >= 1 or managed_count >= 1):
        return True
    if title_issue_hits >= 2 and issue_hits >= 2 and (agri_hits >= 1 or managed_count >= 1):
        return True
    return False


_DIST_LOCAL_ORG_PROFILE_TITLE_TERMS = (
    "우수조합", "전이용", "이용하면", "농업경제사업 대상", "사업 대상", "대상]",
    "작지만 강한", "작지만 강한 농협", "부상",
)
_DIST_LOCAL_ORG_PROFILE_BODY_TERMS = (
    "우수조합", "전이용", "이익입니다", "조합원이 주인", "조합원", "사업 대상", "수상", "시상",
    "경제사업", "농가실익", "실익 증진", "활발한", "작지만 강한", "부상",
)


def is_dist_local_org_tail_context(title: str, desc: str) -> bool:
    """유통(dist)에서 굳이 채울 필요가 없는 지역 농협 성과/홍보형 tail 기사 판정."""
    ttl = (title or "").lower()
    ttl_compact = re.sub(r"\s+", "", title or "")
    txt = f"{title or ''} {desc or ''}".lower()
    if not txt:
        return False
    org_hit = (_LOCAL_AGRI_ORG_IN_TITLE_RX.search(title or "") is not None) or (_LOCAL_AGRI_ORG_IN_TITLE_RX.search(ttl_compact) is not None) or (
        count_any(txt, [w.lower() for w in _LOCAL_AGRI_ORG_TERMS]) >= 1
    )
    if not org_hit:
        return False
    if is_dist_local_field_profile_context(title, desc):
        return False
    if is_dist_export_shipping_context(title, desc) or is_dist_market_disruption_context(title, desc):
        return False

    title_profile_hits = count_any(ttl, [w.lower() for w in _DIST_LOCAL_ORG_PROFILE_TITLE_TERMS]) + count_any(
        ttl_compact.lower(),
        [re.sub(r"\s+", "", w.lower()) for w in _DIST_LOCAL_ORG_PROFILE_TITLE_TERMS],
    )
    body_profile_hits = count_any(txt, [w.lower() for w in _DIST_LOCAL_ORG_PROFILE_BODY_TERMS])
    market_hits = count_any(
        txt,
        [w.lower() for w in ("가락시장", "도매시장", "공판장", "공영도매시장", "경락", "경매", "반입", "온라인 도매시장")],
    )
    if has_apc_agri_context(txt):
        market_hits += 1

    if title_profile_hits >= 1 and market_hits < 2:
        return True
    if body_profile_hits >= 2 and market_hits < 2:
        return True
    return False


_DIST_MACRO_EXPORT_NOISE_TERMS = (
    "k-푸드", "k푸드", "비관세장벽", "관세 위협", "관세위협", "수출 1000억", "1000억 달러",
    "160억달러", "160억 달러", "수출 비상",
)
_DIST_MACRO_LOGISTICS_NOISE_TERMS = (
    "해운", "항공", "동시 마비", "물류 마비", "중동 전쟁", "전쟁 여파", "유가 급등",
)
_DIST_MACRO_EXPORT_CONCRETE_KEEP_TERMS = (
    "도매시장", "공판장", "가락시장", "온라인 도매시장", "산지유통", "산지유통센터", "apc",
    "공동선별", "공선출하", "선적", "검역", "통관", "원산지", "반입", "경락", "경매", "연합판매사업", "직거래",
)
_DIST_MACRO_EXPORT_KEEP_TERMS = (
    "농산물", "원예", "과수", "과일", "채소", "화훼", "도매시장", "공판장", "가락시장", "산지유통",
    "산지유통센터", "apc", "공동선별", "공선출하", "선적", "컨테이너 경매", "원물", "농가", "출하",
)
_DIST_CAMPAIGN_NOISE_TERMS = (
    "캠페인", "선포식", "발대식", "협의회", "공원묘원", "조화근절",
)
_DIST_CONSUMER_TAIL_TERMS = (
    "샐러드", "급식", "군급식", "군대", "장병", "식단", "메뉴", "뷔페",
    "디저트", "외식", "카페", "브런치", "레시피", "밀키트",
)


def is_dist_macro_export_noise_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_dist_export_support_hub_context(title, desc, dom, press):
        return False
    if is_dist_export_field_context(title, desc, dom, press):
        return False
    macro_hits = count_any(txt, [w.lower() for w in _DIST_MACRO_EXPORT_NOISE_TERMS]) + count_any(
        txt,
        [w.lower() for w in _DIST_MACRO_LOGISTICS_NOISE_TERMS],
    )
    if macro_hits == 0:
        return False
    title_signature_hits = count_any(
        (ttl or "").lower(),
        [w.lower() for w in _DIST_EXPORT_FIELD_MACRO_SIGNATURE_TERMS],
    )
    title_concrete_keep_hits = count_any(
        (ttl or "").lower(),
        [w.lower() for w in _DIST_MACRO_EXPORT_CONCRETE_KEEP_TERMS],
    )
    if title_signature_hits >= 2 and title_concrete_keep_hits == 0:
        return True
    concrete_keep_hits = count_any(
        txt,
        [w.lower() for w in _DIST_MACRO_EXPORT_CONCRETE_KEEP_TERMS],
    )
    if concrete_keep_hits >= 1:
        return False
    if is_dist_export_shipping_context(ttl, desc or ""):
        return False
    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    agri_anchor_hits = count_any(txt, [w.lower() for w in ("농산물", "원예", "과수", "과일", "채소", "화훼", "산지유통", "apc")]) + managed_count
    market_hits = count_any(txt, [w.lower() for w in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "물류")])
    title_macro_hits = count_any((ttl or "").lower(), [w.lower() for w in _DIST_MACRO_EXPORT_NOISE_TERMS]) + count_any(
        (ttl or "").lower(),
        [w.lower() for w in _DIST_MACRO_LOGISTICS_NOISE_TERMS],
    )
    if title_macro_hits >= 1 and market_hits == 0 and agri_anchor_hits <= 2:
        return True
    return market_hits == 0 and (agri_anchor_hits <= 1 or best_horti_score(ttl, desc or "") < 2.0)


def is_dist_campaign_noise_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    campaign_hits = count_any(txt, [w.lower() for w in _DIST_CAMPAIGN_NOISE_TERMS])
    if campaign_hits == 0:
        return False
    if is_dist_sales_channel_ops_context(ttl, desc or "") or is_dist_supply_management_center_context(ttl, desc or ""):
        return False
    if is_dist_market_ops_context(ttl, desc or "", "", "") or is_dist_field_market_response_context(ttl, desc or "", "", ""):
        return False
    market_hits = count_any(txt, [w.lower() for w in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "apc", "선적", "출하")])
    return market_hits == 0


def is_dist_consumer_tail_context(title: str, desc: str) -> bool:
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_retail_promo_context(txt) or is_fruit_foodservice_event_context(txt) or is_flower_consumer_trend_context(txt):
        return True
    if is_dist_market_ops_context(title, desc, "", "") or is_dist_supply_management_center_context(title, desc) or is_dist_sales_channel_ops_context(title, desc):
        return False
    if is_dist_market_disruption_context(title, desc) or is_dist_export_shipping_context(title, desc):
        return False
    market_hits = count_any(
        txt,
        [w.lower() for w in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "직거래", "선적", "통관", "검역")],
    ) + (1 if has_apc_agri_context(txt) else 0)
    consumer_hits = count_any(txt, [w.lower() for w in _DIST_CONSUMER_TAIL_TERMS])
    title_consumer_hits = count_any((ttl or "").lower(), [w.lower() for w in _DIST_CONSUMER_TAIL_TERMS])
    return market_hits == 0 and (consumer_hits >= 2 or title_consumer_hits >= 1)


def is_dist_export_support_hub_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """Return True for operational export-support hub stories that fit dist."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    compact = re.sub(r"\s+", "", txt)
    if not txt:
        return False
    hub_hits = 0
    if "원스톱수출지원허브" in compact:
        hub_hits += 2
    elif "수출지원허브" in compact:
        hub_hits += 1
    if "원스톱" in txt and ("허브" in txt or "desk" in compact or "데스크" in txt):
        hub_hits += 1
    if hub_hits == 0:
        return False
    actor_hits = count_any(txt, [w.lower() for w in ("aT", "한국농수산식품유통공사", "농식품부", "농림축산식품부", "관계부처")])
    support_hits = count_any(txt, [w.lower() for w in ("애로", "애로사항", "바로 해결", "해결", "원스톱", "지원", "허브", "원스톱 지원")])
    export_hits = count_any(txt, [w.lower() for w in ("수출", "판로", "해외")])
    agri_hits = count_any(txt, [w.lower() for w in ("농산물", "농식품", "k-푸드", "k푸드", "원예", "과수", "과일", "채소", "화훼", "aT", "한국농수산식품유통공사")])
    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom):
        return False
    return actor_hits >= 1 and support_hits >= 3 and export_hits >= 1 and agri_hits >= 1


def is_supply_weak_tail_context(title: str, desc: str) -> bool:
    """Return True for weak supply-tail stories that should not block stronger item features.

    Generalized patterns:
    - official visit/encouragement field stories with weak title-level supply signal
    - local agri-org performance/promo stories that are not commodity feature stories
    """
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    ttl_l = ttl.lower()
    if not txt:
        return False
    if is_agri_training_recruitment_context(title, desc):
        return True
    if is_agri_org_rename_context(title, desc):
        return True
    if is_dist_political_visit_context(title, desc):
        return True
    if is_supply_stabilization_policy_context(txt) or is_policy_market_brief_context(txt):
        return False
    if is_supply_tourism_event_context(title, desc):
        return True
    if is_supply_org_promo_feature_context(title, desc):
        return False

    title_core_hits = count_any(ttl_l, [t.lower() for t in SUPPLY_TITLE_CORE_TERMS])
    promo_hits = count_any(txt, [w.lower() for w in _SUPPLY_WEAK_TAIL_PROMO_TERMS])
    visit_hits = count_any(txt, [w.lower() for w in _SUPPLY_WEAK_TAIL_VISIT_TERMS])
    official_hits = count_any(ttl_l, [w.lower() for w in _SUPPLY_WEAK_TAIL_OFFICIAL_TERMS])

    if official_hits >= 1 and visit_hits >= 2 and title_core_hits == 0:
        return True

    if is_local_agri_org_feature_context(title, desc):
        return True

    if promo_hits >= 2 and visit_hits >= 1 and title_core_hits == 0:
        return True

    if is_supply_feature_article(title, desc):
        return False

    return False

_DIST_EXPORT_SHIPPING_TERMS = (
    "수출", "선적", "선적식", "수출길", "수출 확대", "해외 수출", "판로",
)
_DIST_EXPORT_CHAIN_TERMS = (
    "검역", "통관", "공동선별", "공선출하", "산지유통", "산지유통센터", "apc", "물류", "브랜드", "농협", "조합",
)
_DIST_EXPORT_DESTINATION_RX = re.compile(r"[가-힣A-Za-z]{2,12}행")
_DIST_MARKET_DISRUPTION_MARKET_TERMS = (
    "가락시장", "구리도매시장", "도매시장", "공영도매시장", "공판장", "시장도매인", "중도매인",
)
_DIST_MARKET_DISRUPTION_TERMS = (
    "동시 휴업", "동시휴업", "휴업", "휴장", "휴무", "중단", "파행", "차질", "셧다운",
)
_DIST_MARKET_DISRUPTION_IMPACT_TERMS = (
    "출하쏠림", "출하 쏠림", "출하조절", "출하 조절", "반입", "반입량", "경락", "경락값",
    "가격", "가격 휘청", "가격 흔들", "폐기량", "출하 농민", "산지", "물량",
)


_REMOTE_FOREIGN_TRADE_TERMS = (
    "상호무역협정", "무역협정", "자유무역협정", "fta", "무역정책", "관세", "상호관세", "보복관세",
    "검역", "통관", "원산지", "수입", "수출", "시장개방", "교역", "서명", "체결",
)
_REMOTE_FOREIGN_SHIPPING_TERMS = (
    "선박", "항구", "항만", "운송", "해운", "해상운송", "연안운송", "운임",
)
_REMOTE_FOREIGN_TRADE_DOMESTIC_HINTS = (
    "국내", "한국", "우리나라", "농산물", "농식품", "원예", "과수", "과일", "채소", "화훼",
    "가락시장", "도매시장", "공판장", "농협", "농식품부", "aT",
)
_DIST_EXPORT_FIELD_TERMS = (
    "수출", "수출시장", "수출 확대", "수출 다변화", "시장 다변화", "k-푸드", "k푸드", "판로", "바이어",
)
_DIST_EXPORT_FIELD_MARKET_TERMS = (
    "유통", "유통 구조", "유통 개혁", "유통 혁신", "온라인 도매시장", "도매시장", "직거래", "플랫폼", "물류", "현장",
)
_DIST_EXPORT_FIELD_INTERVIEW_TERMS = (
    "인터뷰", "대담", "현장", "사장", "대표", "회장", "본부장", "총괄",
)
_DIST_EXPORT_FIELD_POLICY_HEAVY_TERMS = (
    "장관", "농식품부", "발표", "전략", "계획", "대책", "브리핑", "회의", "예산", "추진",
)
_DIST_EXPORT_FIELD_MACRO_SIGNATURE_TERMS = (
    "비관세장벽", "수출 1000억", "1000억 달러", "160억달러", "160억 달러", "k-푸드", "k푸드",
)
_DIST_EXPORT_FIELD_MACRO_POLICY_TERMS = (
    "비관세장벽", "비관세조치", "ntb", "ntbs", "ntm", "ntms", "위생", "검역", "기술 표준", "esg", "신시장", "플러스",
)
_DIST_EXPORT_FIELD_RESPONSE_TERMS = (
    "간담회", "현장간담회", "애로", "애로 해소", "애로 해결", "상시 접수", "상시접수", "사례 공유",
    "사례", "n-데스크", "ndesk", "공장", "원스톱", "수출업계", "업계 간담회", "기업 지원",
)
_POLICY_EXPORT_SUPPORT_TERMS = (
    "농식품부", "장관", "전략", "정책", "발표", "브리핑", "추진", "개혁", "혁신", "ai", "유통", "식품산업",
)
_POLICY_EXPORT_SUPPORT_EXPORT_TERMS = (
    "k-푸드", "k푸드", "수출", "수출 목표", "수출 확대", "수출시장", "식품산업",
)
_POLICY_EXPORT_BARRIER_TERMS = (
    "비관세장벽", "애로", "애로 해소", "수출업계", "수출조직", "간담회", "현장간담회",
    "상시 애로", "n-데스크", "n desk", "적극 대응",
)
_NON_HORTI_PROCESSED_EXPORT_MARKERS = (
    "kgc", "kgc인삼공사", "정관장", "인삼공사", "홍삼", "인삼", "건강기능식품", "건기식", "건강식품",
)
_NON_HORTI_PROCESSED_EXPORT_ALLOW_MARKERS = (
    "농산물", "원예", "과수", "과일", "채소", "화훼", "청과", "산지",
    "도매시장", "공판장", "가락시장", "온라인 도매시장", "산지유통", "산지유통센터",
    "at", "한국농수산식품유통공사",
    "사과", "배", "감귤", "포도", "딸기", "토마토", "오이", "파프리카", "고추",
    "무", "배추", "양파", "마늘", "대파", "생강", "가지", "상추", "깻잎", "시금치",
    "미나리", "당근", "브로콜리", "양배추", "감자", "고구마", "복숭아", "참외",
    "멜론", "키위", "참다래", "국화", "장미", "백합", "카네이션",
)


def is_remote_foreign_trade_brief_context(title: str, desc: str, dom: str = "") -> bool:
    """Return True for foreign-to-foreign trade briefs without domestic horticulture relevance."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    foreign_hits = count_any(txt, [w.lower() for w in _FOREIGN_REMOTE_MARKERS])
    trade_hits = count_any(txt, [w.lower() for w in _REMOTE_FOREIGN_TRADE_TERMS])
    shipping_hits = count_any(txt, [w.lower() for w in _REMOTE_FOREIGN_SHIPPING_TERMS])
    domestic_hits = count_any(txt, [w.lower() for w in _REMOTE_FOREIGN_TRADE_DOMESTIC_HINTS])
    horti_sc = best_horti_score(ttl, desc or "")
    horti_title_sc = best_horti_score(ttl, "")
    dom_norm = normalize_host(dom or "")
    foreign_shipping_like = shipping_hits >= 2 and any(w in txt for w in ("백악관", "미국", "美", "미 항구", "미항구", "미 선박", "미선박"))

    if foreign_hits < 2 and not foreign_shipping_like:
        return False
    if (trade_hits + shipping_hits) < 2:
        return False
    if horti_sc >= 1.8 or horti_title_sc >= 1.4:
        return False
    if domestic_hits >= 2:
        return False
    if ("국내" in txt or "한국" in txt or "우리나라" in txt) and any(
        w in txt for w in ("농산물", "농식품", "원예", "과수", "과일", "채소", "화훼", "가락시장", "도매시장", "공판장", "농협", "농식품부", "aT")
    ):
        return False
    return (dom_norm == "dream.kotra.or.kr") or (foreign_hits >= 3) or foreign_shipping_like


def is_non_horti_processed_export_context(title: str, desc: str) -> bool:
    """Return True for processed-food export briefs with no horticulture anchor."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    marker_hits = count_any(txt, [w.lower() for w in _NON_HORTI_PROCESSED_EXPORT_MARKERS])
    if marker_hits == 0:
        return False
    if count_any(txt, [w.lower() for w in _NON_HORTI_PROCESSED_EXPORT_ALLOW_MARKERS]) >= 1:
        return False
    try:
        topic, topic_sc = best_topic_and_score(ttl, desc or "")
    except Exception:
        topic, topic_sc = ("", 0.0)
    if topic in _HORTI_TOPICS_SET and topic_sc >= 1.0:
        return False
    return best_horti_score(ttl, desc or "") < 1.2


def is_dist_export_field_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """Return True for export-field / distribution-channel stories that belong in dist."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    dom_norm = normalize_host(dom or "")
    if not txt:
        return False
    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom):
        return False
    if dom_norm in POLICY_BRIEF_ONLY_DOMAINS and count_any(txt, [w.lower() for w in _POLICY_EXPORT_SUPPORT_TERMS]) >= 2:
        return False
    if is_policy_market_brief_context(txt, dom, press) or is_supply_stabilization_policy_context(txt, dom, press):
        return False
    if is_non_horti_processed_export_context(ttl, desc or ""):
        return False

    export_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_FIELD_TERMS])
    market_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_FIELD_MARKET_TERMS])
    interview_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_FIELD_INTERVIEW_TERMS])
    policy_heavy_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_FIELD_POLICY_HEAVY_TERMS])
    agri_hits = count_any(txt, [w.lower() for w in ("농산물", "농식품", "원예", "과수", "과일", "채소", "화훼", "aT", "한국농수산식품유통공사")])
    org_hits = count_any(txt, [w.lower() for w in ("aT 사장", "at 사장", "한국농수산식품유통공사", "aT", "at")])
    managed_count = int(_managed_commodity_match_summary(ttl, desc or "").get("count") or 0)
    item_hits = count_any(txt, HORTI_ITEM_TERMS_L)
    response_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_FIELD_RESPONSE_TERMS])
    title_signature_hits = count_any((ttl or "").lower(), [w.lower() for w in _DIST_EXPORT_FIELD_MACRO_SIGNATURE_TERMS])
    macro_barrier_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_FIELD_MACRO_POLICY_TERMS])

    if export_hits == 0 or market_hits == 0:
        return False
    if agri_hits == 0 and org_hits == 0:
        return False
    if title_signature_hits >= 2 and managed_count == 0 and item_hits == 0 and response_hits < 2:
        return False
    if macro_barrier_hits >= 4 and managed_count == 0 and item_hits == 0 and response_hits < 2:
        return False
    if policy_heavy_hits >= 3 and interview_hits == 0 and market_hits < 2:
        return False
    return market_hits >= 2 or (market_hits >= 1 and interview_hits >= 1)


def is_policy_export_support_brief_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """Return True for official-looking export support/promotion policy briefs that should stay in policy."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom):
        return False
    if is_non_horti_processed_export_context(ttl, desc or ""):
        return False

    policy_hits = count_any(txt, [w.lower() for w in _POLICY_EXPORT_SUPPORT_TERMS])
    export_hits = count_any(txt, [w.lower() for w in _POLICY_EXPORT_SUPPORT_EXPORT_TERMS])
    barrier_hits = count_any(txt, [w.lower() for w in _POLICY_EXPORT_BARRIER_TERMS])
    agri_hits = count_any(txt, [w.lower() for w in ("\ub18d\uc2dd\ud488", "\ub18d\uc0b0\ubb3c", "\uc2dd\ud488\uc0b0\uc5c5", "k-\ud478\ub4dc", "k\ud478\ub4dc")])
    item_hits = count_any(txt, HORTI_ITEM_TERMS_L)
    dom_norm = normalize_host(dom or "")
    officialish = policy_domain_override(dom_norm, txt) or (dom_norm in POLICY_DOMAINS) or any(dom_norm.endswith("." + h) for h in POLICY_DOMAINS) or (press in ("\uc815\ucc45\ube0c\ub9ac\ud551", "\ub18d\uc2dd\ud488\ubd80"))
    actor_hits = count_any(txt, [w.lower() for w in ("\ub18d\uc2dd\ud488\ubd80", "\ub18d\ub9bc\ucd95\uc0b0\uc2dd\ud488\ubd80", "\uc7a5\uad00", "\ucc28\uad00", "\uad6d\ud68c", "\uc704\uc6d0\ud68c", "\uc5c5\ubb34\uacc4\ud68d", "\uc815\ubd80", "\uad00\uacc4\ubd80\ucc98", "at", "\ud55c\uad6d\ub18d\uc218\uc0b0\uc2dd\ud488\uc720\ud1b5\uacf5\uc0ac")])
    eventish_hits = count_any(txt, [w.lower() for w in ("\uc138\ubbf8\ub098", "\ud3ec\ub7fc", "\uc124\uba85\ud68c", "\uac04\ub2f4\ud68c", "\ud589\uc0ac", "\uac1c\ucd5c")])
    actor_anchor = officialish or actor_hits >= 2 or (actor_hits >= 1 and agri_hits >= 1)
    strong_barrier_response = actor_anchor and export_hits >= 1 and barrier_hits >= 2 and (agri_hits >= 1 or item_hits >= 1)

    if strong_barrier_response:
        return True
    if is_policy_event_tail_context(ttl, desc or "", dom, press):
        return False
    if is_dist_export_field_context(ttl, desc or "", dom, press):
        return False
    if eventish_hits >= 1 and (not officialish) and actor_hits < 2:
        return False
    return export_hits >= 2 and policy_hits >= 2 and agri_hits >= 1 and actor_anchor


def is_dist_export_shipping_context(title: str, desc: str) -> bool:
    """Return True for hortic export/shipping stories that fit dist better than supply."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_policy_market_brief_context(txt) or is_supply_stabilization_policy_context(txt):
        return False

    title_item_hits = count_any(ttl.lower(), HORTI_ITEM_TERMS_L)
    try:
        topic, topic_sc = best_topic_and_score(ttl, desc or "")
    except Exception:
        topic, topic_sc = ("", 0.0)
    horti_sc = best_horti_score(ttl, desc or "")
    horti_title_sc = best_horti_score(ttl, "")
    horti_hit = (
        title_item_hits >= 1
        or horti_title_sc >= 1.2
        or horti_sc >= 1.8
        or (topic in _HORTI_TOPICS_SET and topic_sc >= 1.1)
    )
    if not horti_hit:
        return False

    export_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_SHIPPING_TERMS])
    chain_hits = count_any(txt, [w.lower() for w in _DIST_EXPORT_CHAIN_TERMS])
    shipping_hits = count_any(txt, [w.lower() for w in ("선적", "선적식", "수출길", "해외 수출")])
    destination_hit = _DIST_EXPORT_DESTINATION_RX.search(ttl) is not None
    return export_hits >= 1 and (shipping_hits >= 1 or destination_hit or chain_hits >= 2)


def is_dist_market_disruption_context(title: str, desc: str) -> bool:
    """도매시장 운영 충격으로 산지/가격 흐름이 흔들리는 유통 기사인지 판정."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False
    if is_policy_market_brief_context(txt) or is_supply_stabilization_policy_context(txt):
        return False

    market_hits = count_any(txt, [w.lower() for w in _DIST_MARKET_DISRUPTION_MARKET_TERMS])
    disruption_hits = count_any(txt, [w.lower() for w in _DIST_MARKET_DISRUPTION_TERMS])
    impact_hits = count_any(txt, [w.lower() for w in _DIST_MARKET_DISRUPTION_IMPACT_TERMS])
    horti_sc = best_horti_score(ttl, desc or "")
    horti_title_sc = best_horti_score(ttl, "")
    agri_hits = count_any(txt, [w.lower() for w in ("농산물", "과채류", "과일", "채소", "청과", "산지", "출하 농민")])

    if market_hits == 0 or disruption_hits == 0 or impact_hits == 0:
        return False
    return (horti_sc >= 1.6) or (horti_title_sc >= 1.2) or (agri_hits >= 1)


def dist_market_disruption_scope(title: str, desc: str) -> str:
    """Return a coarse scope label for dist market-disruption stories."""
    if not is_dist_market_disruption_context(title, desc):
        return ""

    ttl = (title or "").lower()
    txt = f"{ttl} {desc or ''}".lower()
    systemic_core_hits = count_any(
        txt,
        [w.lower() for w in ("수도권", "도매시장 첫", "출하쏠림", "과채류")],
    )
    market_operation_hits = count_any(
        txt,
        [w.lower() for w in ("도매시장", "동시 휴업", "동시휴업", "가락", "구리")],
    )
    if ("도매시장 첫" in ttl) or systemic_core_hits >= 2 or (systemic_core_hits >= 1 and market_operation_hits >= 2):
        return "systemic"

    commodity_hits = count_any(txt, HORTI_ITEM_TERMS_L)
    aftermath_hits = count_any(
        txt,
        [w.lower() for w in ("폐기량", "경락값", "경락가", "가격", "시세", "출하량", "출하 조정")],
    )
    if commodity_hits >= 1 and aftermath_hits >= 2:
        return "commodity_aftershock"
    return "market_disruption"


_POLICY_GENERAL_MACRO_AGRI_TERMS = (
    "농산물", "농업", "농식품", "농식품부", "원예", "과수", "과일", "채소", "화훼", "청과",
    "사과", "배", "감귤", "딸기", "포도", "참외", "오이", "토마토", "파프리카",
)


def is_policy_general_macro_tail_context(title: str, desc: str, dom: str = "", press: str = "") -> bool:
    """정책(policy)에서 굳이 올릴 필요 없는 광역 경제대응/거시 기사 tail 판정."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    d = normalize_host(dom or "")
    p = (press or "").strip()
    if is_supply_stabilization_policy_context(txt, d, p):
        return False
    if is_dist_export_shipping_context(title, desc) or is_dist_market_disruption_context(title, desc):
        return True

    officialish = policy_domain_override(d, txt) or (d in POLICY_DOMAINS) or (p in ("정책브리핑", "농식품부"))
    if officialish:
        return False

    macro_like = is_macro_policy_issue(txt) or is_broad_macro_price_context(title, desc) or is_policy_announcement_issue(txt, d, p)
    if not macro_like:
        return False

    agri_hits = count_any(txt, [w.lower() for w in _POLICY_GENERAL_MACRO_AGRI_TERMS])
    title_agri_hits = count_any(ttl.lower(), [w.lower() for w in _POLICY_GENERAL_MACRO_AGRI_TERMS])
    market_hits = count_any(txt, [w.lower() for w in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "apc")])
    horti_sc = best_horti_score(ttl, desc or "")
    regional_macro_hits = count_any(
        txt,
        [w.lower() for w in ("부·울·경", "부울경", "부산", "울산", "경남", "민생안정", "특별기간", "긴급 대응", "총동원", "빨간불", "경제")],
    )
    title_macro_hits = count_any(
        ttl.lower(),
        [w.lower() for w in ("긴급 대응", "빨간불", "민생", "특별기간", "총동원", "경제")],
    )

    if market_hits >= 1:
        return False
    if agri_hits >= 3 and (title_agri_hits >= 1 or horti_sc >= 1.8):
        return False
    if _LOCAL_GEO_PATTERN.search(ttl) and agri_hits < 3:
        return True
    if count_any(ttl.lower(), [w.lower() for w in ("부·울·경", "부울경", "긴급 대응", "빨간불")]) >= 2 and title_agri_hits == 0 and market_hits == 0:
        return True
    if regional_macro_hits >= 2 and title_agri_hits == 0 and market_hits == 0 and agri_hits <= 3:
        return True
    return agri_hits <= 1 and title_agri_hits == 0 and horti_sc < 1.6 and title_macro_hits >= 1


def has_direct_supply_chain_signal(text: str) -> bool:
    t = (text or "").lower()
    if not t:
        return False
    market_terms = ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "apc")
    if count_any(t, [w.lower() for w in market_terms]) >= 1:
        return True
    return count_any(t, [w.lower() for w in _DIRECT_SUPPLY_SIGNAL_TERMS]) >= 2


_SUPPLY_FEATURE_FIELD_TERMS = (
    "생육", "생육적온", "재배", "작황", "농가", "농장", "산지", "생산자", "하우스", "시설",
    "수확", "착과", "난방", "난방비", "연료비", "유가", "한파", "냉해", "동해", "꽃샘추위",
)
_SUPPLY_FEATURE_QUALITY_TERMS = (
    "품질", "경쟁력", "선호도", "블라인드", "비교", "평가", "맛", "당도", "시식", "압도",
    "수입산", "수입", "만다린", "국내산",
)
_SUPPLY_FEATURE_ISSUE_TITLE_TERMS = (
    "대책", "시급", "과제", "진단", "점검", "취재수첩", "기획", "현장", "회복", "비상",
)
_SUPPLY_FEATURE_ISSUE_ACTION_TERMS = (
    "\uB300\uCC45", "\uB300\uC751", "\uD574\uBC95", "\uBCF4\uC644", "\uD68C\uBCF5", "\uAC1C\uC120", "\uC815\uC0C1\uD654", "\uD655\uBCF4", "\uC9C0\uC6D0", "\uC870\uC808",
    "\uC885\uD569\uACC4\uD68D", "\uACE0\uAE09\uD654", "\uAC1C\uBC1C", "\uBCF4\uAE09", "\uD3D0\uC6D0 \uC9C0\uC6D0",
)
_SUPPLY_FEATURE_ISSUE_DISTRESS_TERMS = (
    "\uBD80\uB2F4", "\uAE09\uB77D", "\uD558\uB77D", "\uD3ED\uB77D", "\uC815\uCCB4", "\uCE68\uCCB4", "\uC704\uAE30", "\uBE44\uC0C1", "\uC6B0\uB824", "\uD53C\uD574",
    "\uC190\uC2E4", "\uD3EC\uAE30", "\uC5B4\uB824\uC6C0", "\uD638\uC18C", "\uC0DD\uC0B0\uBE44", "\uB09C\uBC29\uBE44", "\uBA74\uC138\uC720", "\uC81C\uAC12", "\uC18C\uBE44\uC790 \uC678\uBA74",
    "\uC0DD\uC0B0\uACFC\uC789", "\uACFC\uC789\uC0DD\uC0B0", "\uC6D0\uAC00", "\uBBF8\uC219\uACFC", "\uD3D0\uC6D0", "\uC2E0\uB8B0 \uC2E4\uCD94", "\uB5A8\uC5B4\uC9C4",
    "\uC6B8\uC0C1", "\uD488\uADC0", "\uBB3C\uB7C9 \uBD80\uC871", "\uC218\uAE09 \uCC28\uC9C8",
)
_SUPPLY_FEATURE_ISSUE_INPUT_TERMS = (
    "\uBB18\uBAA9", "\uBB18\uBAA9\uB09C", "\uC885\uBB18", "\uBAA8\uC885", "\uC721\uBB18", "\uD488\uADC0",
)
_SUPPLY_FEATURE_ISSUE_CLIMATE_TERMS = (
    "\uC0B0\uBD88", "\uB300\uD615 \uC0B0\uBD88", "\uAE30\uD6C4\uBCC0\uD654", "\uC774\uC0C1\uAE30\uD6C4", "\uD3ED\uC5FC", "\uACE0\uC628", "\uD55C\uD30C", "\uB0C9\uD574", "\uC11C\uB9AC",
)
_SUPPLY_INPUT_COST_PRESSURE_TERMS = (
    "유가", "국제유가", "유류비", "기름값", "면세유", "면세 등유", "등유",
    "난방", "난방비", "연료비", "보일러", "기름보일러",
)
_SUPPLY_FEATURE_ISSUE_EXPORT_TERMS = (
    "\uc218\ucd9c", "\uc218\ucd9c\uae38", "\uc218\ucd9c \ud655\ub300", "\uc120\uc801", "\uac80\uc5ed", "\ud1b5\uad00", "\ud310\ub85c", "\ud574\uc678\uc2dc\uc7a5", "\ud574\uc678 \uc218\uc694",
)
_SUPPLY_FEATURE_ISSUE_RECOVERY_TERMS = (
    "\ud68c\ubcf5", "\ubc18\ub4f1", "\uc815\uc0c1\ud654", "\uac00\uaca9 \ud68c\ubcf5", "\uc2dc\uc138 \ud68c\ubcf5", "\uc81c\uac12", "\ud68c\ubcf5\uc138",
)
_SUPPLY_FEATURE_ISSUE_FARM_TERMS = (
    "\ub18d\uac00", "\uc0b0\uc9c0", "\uc8fc\uc0b0\uc9c0", "\uc0dd\uc0b0\uc790", "\uc7ac\ubc30\ub18d\uac00", "\uacfc\uc6d0", "\uc2dc\uc124", "\uc0dd\uc0b0\ube44", "\ub09c\ubc29\ube44", "\uba74\uc138\uc720",
)
_SUPPLY_FEATURE_ISSUE_TRADE_TERMS = (
    "\uad00\uc138", "\ud560\ub2f9\uad00\uc138", "\ubb34\uad00\uc138", "fta", "\ud1b5\uc0c1", "\uc218\uc785", "\ud1b5\uad00", "\uac80\uc5ed", "\ube44\uad00\uc138\uc7a5\ubcbd",
)
_SUPPLY_FEATURE_ISSUE_TRADE_IMPACT_TERMS = (
    "\ud0c0\uaca9", "\uc7a0\uc2dd", "\uc555\ubc15", "\ucda9\uaca9", "\uacbd\uc7c1", "\uc5b4\ub824\uc6c0", "\ubd80\ub2f4", "\uc601\ud5a5", "\ub300\uc751", "\uc0b0\uc5c5", "\ub18d\uac00",
)


def supply_issue_context_bucket(title: str, desc: str) -> str | None:
    """품목 중심 심층 이슈 기사인지 판정하고 이슈 버킷을 반환."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt or is_fruit_foodservice_event_context(txt):
        return None
    if is_supply_stabilization_policy_context(txt) or is_policy_market_brief_context(txt):
        return None
    if is_local_agri_policy_program_context(txt):
        return None
    if is_supply_org_promo_feature_context(title, desc):
        return None

    horti_sc = best_horti_score(ttl, desc or "")
    horti_title_sc = best_horti_score(ttl, "")
    item_hits = count_any(txt, HORTI_ITEM_TERMS_L)
    title_item_hits = count_any(ttl.lower(), HORTI_ITEM_TERMS_L)

    title_export_hits = count_any(ttl.lower(), [w.lower() for w in _SUPPLY_FEATURE_ISSUE_EXPORT_TERMS])
    title_issue_hits = count_any(ttl.lower(), [w.lower() for w in _SUPPLY_FEATURE_ISSUE_TITLE_TERMS])
    export_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_EXPORT_TERMS])
    issue_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_TITLE_TERMS])
    recovery_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_RECOVERY_TERMS])
    farm_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_FARM_TERMS])
    distress_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_DISTRESS_TERMS])
    title_distress_hits = count_any(ttl.lower(), [w.lower() for w in _SUPPLY_FEATURE_ISSUE_DISTRESS_TERMS])
    action_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_ACTION_TERMS])
    input_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_INPUT_TERMS])
    climate_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_CLIMATE_TERMS])
    trade_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_TRADE_TERMS])
    title_trade_hits = count_any(ttl.lower(), [w.lower() for w in _SUPPLY_FEATURE_ISSUE_TRADE_TERMS])
    hard_trade_terms = [w.lower() for w in ("관세", "할당관세", "무관세", "fta", "통상", "비관세장벽", "통관", "검역")]
    hard_trade_hits = count_any(txt, hard_trade_terms)
    title_hard_trade_hits = count_any(ttl.lower(), hard_trade_terms)
    trade_impact_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_TRADE_IMPACT_TERMS])
    strong_item_context = title_item_hits >= 1 or horti_title_sc >= 1.2 or horti_sc >= 2.2
    shock_issue = (
        (strong_item_context or (farm_hits >= 1 and (input_hits >= 1 or climate_hits >= 1)))
        and input_hits >= 1
        and (climate_hits >= 1 or distress_hits >= 1 or title_distress_hits >= 1)
    )
    trade_pressure_issue = (
        strong_item_context
        and hard_trade_hits >= 1
        and title_hard_trade_hits >= 1
        and trade_hits >= 1
        and (title_item_hits >= 1 or horti_title_sc >= 1.0)
        and (trade_impact_hits >= 1 or distress_hits >= 1 or action_hits >= 1)
    )
    if item_hits == 0 and horti_sc < 1.8 and not shock_issue:
        return None
    if title_issue_hits == 0 and issue_hits < 2 and not shock_issue and not trade_pressure_issue:
        return None

    if title_export_hits >= 1 and (title_item_hits >= 1 or horti_title_sc >= 1.0 or horti_sc >= 1.8) and title_issue_hits >= 1 and (title_distress_hits >= 1 or distress_hits >= 1 or action_hits >= 1):
        return "export_recovery"

    if export_hits >= 1 and (recovery_hits >= 1 or distress_hits >= 1) and (title_issue_hits >= 1 or action_hits >= 1):
        return "export_recovery"
    if farm_hits >= 1 and distress_hits >= 1 and (title_issue_hits >= 1 or action_hits >= 1):
        return "farm_action"
    if trade_pressure_issue:
        return "commodity_issue"
    if shock_issue:
        return "commodity_issue"
    has_issue_frame = title_issue_hits >= 1 or issue_hits >= 3
    issue_follow_through = (
        distress_hits >= 2
        or (distress_hits >= 1 and action_hits >= 1)
        or action_hits >= 2
        or (title_issue_hits >= 2 and issue_hits >= 3)
    )
    if strong_item_context and has_issue_frame and issue_follow_through:
        return "commodity_issue"
    return None


def supply_feature_context_kind(title: str, desc: str) -> str | None:
    """품목 중심 현장/품질/제철 feature 기사 판정."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt or is_fruit_foodservice_event_context(txt):
        return None
    if is_agri_training_recruitment_context(title, desc):
        return None
    if is_agri_org_rename_context(title, desc):
        return None
    if is_supply_tourism_event_context(title, desc):
        return None

    horti_sc = best_horti_score(ttl, desc or "")
    horti_title_sc = best_horti_score(ttl, "")
    item_hits = count_any(txt, HORTI_ITEM_TERMS_L)
    title_item_hits = count_any(ttl.lower(), HORTI_ITEM_TERMS_L)
    title_core_hits = count_any(ttl.lower(), [w.lower() for w in SUPPLY_TITLE_CORE_TERMS])
    issue_bucket = supply_issue_context_bucket(title, desc)
    if item_hits == 0 and horti_sc < 1.8 and not issue_bucket:
        return None

    if is_supply_org_promo_feature_context(title, desc):
        return "promo"
    if issue_bucket:
        return "issue"

    field_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_FIELD_TERMS])
    quality_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_QUALITY_TERMS])
    compare_hits = count_any(txt, [w.lower() for w in ("수입산", "수입", "만다린", "비교", "블라인드", "선호도")])
    agri_hits = count_any(txt, [w.lower() for w in ("농가", "농장", "생산지", "재배", "시설", "과원")])
    visit_hits = count_any(txt, [w.lower() for w in _SUPPLY_WEAK_TAIL_VISIT_TERMS])
    official_hits = count_any(ttl.lower(), [w.lower() for w in _SUPPLY_WEAK_TAIL_OFFICIAL_TERMS])

    if (title_item_hits >= 1) or (horti_title_sc >= 1.2) or (horti_sc >= 2.0):
        if official_hits >= 1 and visit_hits >= 2 and title_core_hits == 0:
            return None
        if field_hits >= 2 and (agri_hits >= 1 or horti_sc >= 2.2):
            return "field"
        if quality_hits >= 2 and compare_hits >= 1:
            return "quality"
    return None


def is_supply_input_cost_pressure_context(title: str, desc: str) -> bool:
    txt = f"{title or ''} {desc or ''}".lower()
    if not txt or is_fruit_foodservice_event_context(txt):
        return False
    try:
        topic, topic_sc = best_topic_and_score(title or "", desc or "")
    except Exception:
        topic, topic_sc = ("", 0.0)
    if topic not in _HORTI_TOPICS_SET or topic_sc < 1.2:
        return False
    feature_kind = supply_feature_context_kind(title, desc)
    issue_bucket = supply_issue_context_bucket(title, desc)
    if feature_kind not in {"field", "issue"} and issue_bucket != "commodity_issue":
        return False
    cost_hits = count_any(txt, [w.lower() for w in _SUPPLY_INPUT_COST_PRESSURE_TERMS])
    distress_hits = count_any(txt, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_DISTRESS_TERMS])
    return cost_hits >= 2 and distress_hits >= 1


def is_supply_feature_article(title: str, desc: str) -> bool:
    txt = f"{title or ''} {desc or ''}".lower()
    return bool(supply_feature_context_kind(title, desc) or is_flower_consumer_trend_context(txt))

def is_local_agri_infra_designation_context(title: str, desc: str) -> bool:
    """지역 단위 농업 인프라 '선정/지정/계획' 기사인지 판정.
    - 실제 가동/준공이 아닌 기획·선정 단계의 지역 이슈는 dist 일반 기사로는 남겨도 core로는 올리지 않는다.
    """
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt or _LOCAL_REGION_IN_TITLE_RX.search(ttl) is None:
        return False

    infra_hit = count_any(txt, [w.lower() for w in _LOCAL_AGRI_INFRA_TERMS])
    selection_hit = count_any(txt, [w.lower() for w in _LOCAL_AGRI_INFRA_SELECTION_TERMS])
    operation_hit = count_any(txt, [w.lower() for w in _LOCAL_AGRI_INFRA_OPERATION_TERMS])
    return infra_hit >= 1 and selection_hit >= 2 and operation_hit == 0


def is_broad_macro_price_context(title: str, desc: str) -> bool:
    """거시 물가/장바구니형 기사인지 판단.
    - 개별 품목 수급 기사와 달리, 여러 먹거리 품목을 한 번에 다루며
      물가/환율/유가/정부 안정화 같은 거시 문맥이 함께 붙는 경우를 잡는다.
    """
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt:
        return False

    macro_hits = count_any(txt, [w.lower() for w in ("물가", "소비자물가", "물가지수", "cpi", "장바구니", "밥상", "먹거리", "체감물가", "고물가")])
    price_hits = count_any(txt, [w.lower() for w in ("가격", "급등", "상승", "하락", "들썩", "불안")])
    item_hits = count_any(txt, [w.lower() for w in ("사과", "배", "감귤", "딸기", "채소", "과일", "농산물", "축산물", "돼지고기", "소고기", "계란", "달걀", "쌀")])
    driver_hits = count_any(txt, [w.lower() for w in ("농식품부", "정부", "할인지원", "안정화", "공급", "수급", "유가", "환율", "통계", "kosis")])

    if macro_hits == 0 and ("가격" in txt) and item_hits >= 2 and driver_hits >= 1:
        macro_hits = 1

    if macro_hits == 0 or price_hits == 0:
        return False
    if item_hits >= 2:
        return True
    if item_hits >= 1 and driver_hits >= 1:
        return True
    return False


def is_fruit_foodservice_event_context(text: str) -> bool:
    """과일(특히 딸기 등) '외식/뷔페/프랜차이즈 시즌행사'형 기사 판정.
    - 공급/작황/도매시장 수급 신호보다 소비 이벤트 성격이 강해 '품목 및 수급'의 핵심(core)에서 제외/감점.
    """
    t = (text or "").lower()
    brand_hit = any(w.lower() in t for w in _FRUIT_FOODSERVICE_EVENT_BRANDS)
    marker_hit = any(w.lower() in t for w in _FRUIT_FOODSERVICE_EVENT_MARKERS)
    # '딸기' 등 과일 키워드가 함께 있을 때만 활성화(일반 외식 기사 오탐 방지)
    fruit_hit = any(k in t for k in ("딸기", "과일", "생딸기", "딸기 디저트"))
    return fruit_hit and (brand_hit or marker_hit)

def is_remote_foreign_horti(text: str) -> bool:
    """해외 원예/화훼 업계(특히 특정 국가 내 시장/관세 이슈) 기사 중,
    국내(한국) 수급/유통/정책과 직접 연결이 약한 경우를 제외한다.

    - 해외국가 마커 + 원예/화훼 마커가 있고,
    - '국내/한국/농협/도매시장' 같은 강한 국내 맥락이 없으면 원격 해외로 간주.
    - 단, 한국 수출/검역/통관과 명시적으로 연결된 경우는 통과.
    """
    t = (text or "").lower()
    if not any(w.lower() in t for w in _FOREIGN_REMOTE_MARKERS):
        return False
    if not any(w in t for w in ("원예","과수","과일","채소","화훼","절화","꽃","floriculture")):
        return False

    # 한국과 직접 연결(수출/검역/통관/수입) 신호가 있으면 원격 해외로 보지 않음
    if any(w in t for w in ("수출","수입","통관","검역","수입검역","수출길", "관세")) and any(k.lower() in t for k in _KOREA_STRONG_CONTEXT):
        return False

    # 강한 국내 맥락이 없으면 제외
    if not any(k.lower() in t for k in _KOREA_STRONG_CONTEXT):
        return True

    return False



def is_blocked_domain(dom: str) -> bool:
    if not dom:
        return False
    dom = dom.lower()
    if dom in BLOCKED_DOMAINS:
        return True
    for b in BLOCKED_DOMAINS:
        if dom.endswith("." + b):
            return True
    return False

def agri_strength_score(text: str) -> int:
    return count_any(text, AGRI_STRONG_TERMS)


def _section_must_terms_lower(section_conf: JsonDict) -> list[str]:
    """Return cached lower-cased must_terms for a section config."""
    if not isinstance(section_conf, dict):
        return []
    cached = section_conf.get("_must_terms_lower")
    if isinstance(cached, list):
        return cached
    out = [str(t).lower() for t in (section_conf.get("must_terms") or []) if str(t).strip()]
    # lightweight cache on in-memory config dict
    section_conf["_must_terms_lower"] = out
    return out


def keyword_strength(text: str, section_conf: JsonDict) -> int:
    """섹션 관련 키워드 강도(정수).
    - 섹션 must_terms 포함 여부(1차) + 농산물 강키워드(AGRI_STRONG_TERMS) 기반 점수
    - dist/pest에서 낚시성 기사 제거에 사용
    """
    if not section_conf:
        return agri_strength_score(text)
    must = _section_must_terms_lower(section_conf)
    return count_any(text, must) + agri_strength_score(text)

def section_fit_score(title: str, desc: str, section_conf: JsonDict) -> float:
    """해당 기사가 섹션 의도와 얼마나 맞는지(0+).
    - must_terms 텍스트 히트 + 제목 히트(가중)
    - 원예 핵심 신호를 약하게 추가해 완전 비관련 기사 상단 배치를 줄임
    """
    txt = f"{title or ''} {desc or ''}".lower()
    ttl = (title or "").lower()
    must = _section_must_terms_lower(section_conf) if section_conf else []
    must_t = count_any(txt, must) if must else 0
    must_h = count_any(ttl, must) if must else 0
    base = (0.18 * must_t) + (0.40 * must_h)
    # 완전 무관 기사 방어용 약한 보정
    base += 0.10 * min(6, agri_strength_score(txt))
    key = str(section_conf.get("key")) if isinstance(section_conf, dict) else ""
    broad_macro_price = is_broad_macro_price_context(title, desc)
    policy_stabilization = is_supply_stabilization_policy_context(txt)
    policy_market_brief = is_policy_market_brief_context(txt)
    policy_major_issue = is_policy_major_issue_context(title, desc)
    managed_summary = _managed_commodity_match_summary(title, desc)
    managed_count = int(managed_summary.get("count") or 0)
    program_core_count = int(managed_summary.get("program_core_count") or 0)
    dist_supply_center = is_dist_supply_management_center_context(title, desc)
    dist_sales_channel_ops = is_dist_sales_channel_ops_context(title, desc)
    dist_field_market_response = is_dist_field_market_response_context(title, desc)
    dist_anchor_hits = count_any(
        txt,
        [t.lower() for t in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "온라인 도매시장")],
    )
    if key == "policy":
        if is_title_livestock_dominant_context(title, desc):
            base -= 1.4
        if is_policy_forest_admin_noise_context(title, desc):
            base -= 1.2
        if is_policy_budget_drive_noise_context(title, desc):
            base -= 1.1
        if is_macro_policy_issue(txt):
            base += 0.9
            if broad_macro_price:
                base += 0.6
            if policy_stabilization:
                base += 0.85
            if policy_market_brief:
                base += 0.95
        if policy_major_issue:
            base += 1.05
        if is_policy_export_support_brief_context(title, desc):
            base += 0.85
        if is_dist_export_field_context(title, desc):
            base -= 0.9
        if dist_field_market_response:
            base -= 0.85
        if managed_count and (is_macro_policy_issue(txt) or policy_stabilization or policy_market_brief or policy_major_issue or is_policy_export_support_brief_context(title, desc)):
            base += min(0.56, 0.12 * managed_count)
            base += min(0.36, 0.16 * program_core_count)
    elif key == "dist":
        if is_dist_political_visit_context(title, desc):
            base -= 1.4
        if is_local_agri_infra_designation_context(title, desc):
            base -= 1.1
        if is_dist_local_crop_strategy_noise_context(title, desc):
            base -= 1.2
        if is_dist_export_shipping_context(title, desc):
            base += 1.15
        if is_dist_export_field_context(title, desc):
            base += 1.05
        if is_dist_export_support_hub_context(title, desc):
            base += 1.0
        if dist_supply_center:
            base += 1.1
        if dist_sales_channel_ops:
            base += 1.15
        if dist_field_market_response:
            base += 1.25
        dist_disruption_scope = dist_market_disruption_scope(title, desc)
        if dist_disruption_scope == "systemic":
            base += 1.9
        elif dist_disruption_scope == "market_disruption":
            base += 1.25
        elif dist_disruption_scope == "commodity_aftershock":
            base += 0.65
        if is_local_agri_org_feature_context(title, desc):
            if is_dist_local_field_profile_context(title, desc):
                base += 0.55
            elif is_dist_local_org_tail_context(title, desc):
                base -= 0.9
            else:
                base += 0.25
        if managed_count and (dist_anchor_hits >= 1 or is_dist_export_shipping_context(title, desc) or is_dist_export_field_context(title, desc) or dist_field_market_response):
            base += min(0.52, 0.12 * managed_count)
            base += min(0.32, 0.14 * program_core_count)
    elif key == "supply":
        feature_kind = supply_feature_context_kind(title, desc)
        if is_supply_price_outlook_context(title, desc):
            base += 0.78
        if is_title_livestock_dominant_context(title, desc):
            base -= 1.3
        if feature_kind == "field":
            base += 0.55
        elif feature_kind == "quality":
            base += 0.45
        elif feature_kind == "promo":
            base += 0.38
        if is_local_agri_org_feature_context(title, desc):
            base -= 1.0
        if is_dist_export_shipping_context(title, desc):
            base -= 1.45
        if dist_supply_center:
            base -= 0.95
        if dist_sales_channel_ops:
            base -= 1.15
        if dist_field_market_response:
            base -= 1.15
        if is_supply_weak_tail_context(title, desc):
            base -= 1.1
        if policy_stabilization:
            base -= 1.1
        if policy_market_brief:
            base -= 1.35
        if broad_macro_price and ((not has_direct_supply_chain_signal(txt)) or policy_market_brief):
            base -= 1.0
        if is_macro_policy_issue(txt) and count_any((title or "").lower(), [t.lower() for t in ("과일", "과수", "채소", "화훼", "농산물", "청과")]) == 0 and best_horti_score(title or "", "") < 1.6 and best_horti_score(title or "", desc or "") < 1.8 and ((not has_direct_supply_chain_signal(txt)) or policy_market_brief):
            base -= 0.6
        if managed_count:
            base += min(0.72, 0.15 * managed_count)
            base += min(0.48, 0.22 * program_core_count)
    elif key == "pest":
        if is_pest_input_marketing_noise_context(title, desc):
            base -= 1.3
        if is_pest_story_focus_strong(title, desc):
            base += 0.75
        if is_pest_control_policy_context(txt):
            base += 0.55
        if any(w in txt for w in ("냉해", "동해", "서리", "저온", "병해충", "방제")):
            base += 0.35
        if managed_count:
            base += min(0.50, 0.12 * managed_count)
            base += min(0.32, 0.16 * program_core_count)
    return round(base, 3)

def off_topic_penalty(text: str) -> int:
    return count_any(text, OFFTOPIC_HINTS)

def korea_context_score(text: str) -> int:
    return count_any(text, KOREA_CONTEXT_HINTS)

def global_retail_protest_penalty(text: str) -> int:
    return count_any(text.lower(), GLOBAL_RETAIL_PROTEST_HINTS)

# -----------------------------
# Section signal weights (원예수급 핵심성 가중치)
# - '키워드 강도'를 단순 카운트가 아니라 가중치 합으로 반영
# -----------------------------
def weighted_hits(text: str, weight_map: dict[str, float]) -> float:
    return sum(w for k, w in weight_map.items() if k in text)

_NUMERIC_HINT_RE = re.compile(r"\d")
_UNIT_HINT_RE = re.compile(r"(kg|톤|t\b|%|억원|만원|원|달러)")

SUPPLY_WEIGHT_MAP = {
    # 수급/가격 핵심
    '수급': 4.0, '가격': 4.0, '시세': 3.5, '경락가': 3.5, '도매가격': 3.0, '소매가격': 3.0,
    # 생산/출하/재고
    '작황': 3.0, '생산': 2.5, '생산량': 3.0, '출하': 3.0, '물량': 2.5, '반입': 2.0,
    '재고': 3.0, '저장': 2.5, 'ca저장': 2.5,
    # 변동성/리스크
    '급등': 2.5, '폭등': 2.5, '급락': 2.0, '하락': 1.5, '대란': 2.0, '비상': 2.0,
    '전망': 1.2, '동향': 1.0, '평년': 1.0, '전년': 1.0, '대비': 0.8,

    '화훼': 1.8,
    '절화': 1.6,
    '꽃': 1.5,
    '자조금': 1.2,
    '딸기': 1.2,
    '파프리카': 1.2,
    '참외': 1.1,
    '키위': 1.1,
    '유자': 1.1,
    '단감': 1.1,
    '곶감': 1.1,
    '밤': 1.0,
    '자두': 1.0,
    '복숭아': 1.0,
    '매실': 1.0,
    '만감': 0.9,
    '만감류': 0.9,
    '한라봉': 0.9,
    '레드향': 0.9,
    '천혜향': 0.9,
}

DIST_WEIGHT_MAP = {
    '가락시장': 3.5, '도매시장': 3.0, '공판장': 2.8, '경락': 2.8, '경매': 2.5, '청과': 1.5,
    '반입': 2.2, '중도매인': 2.0, '시장도매인': 2.0, '물류': 2.0, '유통센터': 1.5,
    '온라인도매시장': 2.6, '온라인 도매시장': 2.6,
    'apc': 2.0, '선별': 1.8, '저온': 1.2, '저장': 1.2, '원산지': 2.0, '부정유통': 2.0,
    '수출': 2.1, '선적': 2.3, '선적식': 1.6, '수출길': 1.9, '검역': 1.8, '통관': 1.6, '판로': 1.2, '공동선별': 1.4, '공선출하': 1.4,

    '산지유통센터': 2.4,
    '산지유통': 2.0,
    '준공': 1.2,
    '완공': 1.2,
    '자동화': 1.5,
    '스마트': 1.0,
    'ai': 0.7,
    '디지털': 0.9,
    '통합': 0.8,
    '브랜드': 1.6,
    '판매농협': 1.2,
    '원예농협': 1.6,
    '작목반': 1.2,
    '자조금': 1.4,
    '화훼': 1.2,
    '절화': 1.1,
    '꽃': 1.1,
    '조화': 1.2,
    '플라스틱': 0.6,
    '묘지': 0.5,
    '공원묘원': 0.7,
    '소비촉진': 1.0,
    '캠페인': 0.5,
}

POLICY_WEIGHT_MAP = {
    '대책': 3.0, '지원': 2.8, '할인지원': 3.0, '할당관세': 3.0, '검역': 2.5, '단속': 2.3,
    '고시': 2.0, '개정': 2.0, '발표': 1.8, '추진': 1.8, '확대': 1.3, '연장': 1.3,
    '예산': 1.8, '브리핑': 2.0, '보도자료': 1.8,
    # ✅ 주요 이슈(물가/가격) 확장
    '물가': 3.0,
    '가격': 2.4,
    '성수품': 2.2,
    '차례상': 2.4,
    '소비자물가': 2.4,
    '물가지수': 2.0,
    '통계': 1.2,
    'kosis': 2.0,
    '상승': 0.9,
    '하락': 1.0,
    '급등': 1.1,
    '협의체': 2.4,
    '위원회': 1.8,
    '출범': 1.7,
    '특별관리': 2.2,
    '최소가격': 2.8,
    '보전제': 2.8,
    '제도개선': 2.4,
    '제도 개선': 2.4,
    '구조개선': 2.2,
    '구조 개선': 2.2,
    '가격 결정 구조': 2.2,
}

PEST_WEIGHT_MAP = {
    '병해충': 3.5, '방제': 3.0, '예찰': 2.5, '농약': 2.3, '살포': 2.0,
    '과수화상병': 4.0, '탄저병': 3.0, '역병': 2.8, '노균병': 2.8, '흰가루병': 2.8,
    '진딧물': 2.5, '응애': 2.3, '노린재': 2.3, '총채벌레': 2.3,
    '냉해': 2.8, '동해': 2.8, '한파': 1.8, '서리': 1.8,
}


# -----------------------------
# NH (농협) relevance boost (농협 경제지주/임직원 대상 최적화)
# - '농협'은 범위가 넓어 무조건 가산하면 행사/금융 오탐이 늘 수 있으므로
#   (1) 강신호(경제지주/하나로마트/농협몰 등)는 크게 가산
#   (2) 약신호(농협 단독)는 수급/유통/정책 핵심 단어와 동시 등장할 때만 소폭 가산
# -----------------------------
NH_STRONG_TERMS = [
    "농협경제지주", "경제지주", "농협유통", "하나로마트", "농협몰",
    "농협공판장", "농협 공판장", "조합공판장",
]
# '농수산물 온라인도매시장'은 주체가 다양하므로, 농협 단서와 함께 나오면 강하게 가산
NH_STRONG_COOCUR_TERMS = ["온라인도매시장", "농수산물 온라인도매시장", "온라인 도매시장"]

NH_WEAK_TERMS = ["농협", "nh", "농협중앙회", "지역농협", "원예농협"]

# 농협 키워드가 있어도 실무와 무관한 경우(금융/행사/동정 등)는 가산 금지(또는 간접 감점)
NH_OFFTOPIC_TERMS = [
    "농협은행", "nh농협은행", "nh투자증권", "농협카드", "nh카드",
    "금융", "대출", "적금", "예금", "펀드", "보험", "주가",
    "봉사", "기부", "후원", "시상", "축제", "행사", "동정", "간담회", "협의회", "세미나",
]

NH_COOCUR_SUPPLY = ["가격", "수급", "작황", "출하", "물량", "반입", "경락", "경락가", "도매", "재고", "저장"]
NH_COOCUR_DIST   = ["도매시장", "가락시장", "공판장", "경매", "경락", "반입", "물류", "유통센터", "온라인도매시장"]
NH_COOCUR_POLICY = ["대책", "지원", "할인", "비축", "물가", "성수품", "관세", "수입", "검역", "통관", "단속", "브리핑"]

def nh_boost(text: str, section_key: str) -> float:
    t = (text or "").lower()
    if any(k.lower() in t for k in NH_OFFTOPIC_TERMS):
        return 0.0

    strong = any(k.lower() in t for k in NH_STRONG_TERMS)
    weak = any(k.lower() in t for k in NH_WEAK_TERMS)

    # 강신호: 경제지주/하나로마트/농협몰/공판장 등
    if strong:
        return 6.0 if section_key in ("dist", "policy", "supply") else 3.5

    # 온라인도매시장은 농협 단서와 동반될 때만 강하게
    if any(k.lower() in t for k in NH_STRONG_COOCUR_TERMS) and weak:
        return 3.2 if section_key in ("dist", "policy") else 2.0

    # 약신호: '농협'만 있을 경우 -> 섹션 핵심 단어와 함께일 때만 소폭 가산
    if weak:
        co = NH_COOCUR_SUPPLY if section_key == "supply" else NH_COOCUR_DIST if section_key == "dist" else NH_COOCUR_POLICY
        if sum(1 for k in co if k in t) >= 1:
            return 2.2

    return 0.0


# -----------------------------
# De-prioritize meeting/visit/PR-heavy articles (품질 보정)
# - '방문/협의회/간담회/업무협약'류는 실무 의사결정 신호(가격/수급/물량/대책)가 약한 경우가 많음
# -----------------------------
EVENTY_TERMS = ["방문", "시찰", "간담회", "협의회", "세미나", "토론회", "업무협약", "협약", "mou", "설명회", "발대식", "기념식", "캠페인"]
TECH_TREND_TERMS = ["스마트팜", "ai", "로봇", "자율", "연중생산", "수직농장", "빅데이터", "디지털", "혁신"]

def eventy_penalty(text: str, title: str, section_key: str) -> float:
    t = (text or "").lower()
    ttl = (title or "").lower()
    hits = count_any(t, [k.lower() for k in EVENTY_TERMS])
    tech = count_any(t, [k.lower() for k in TECH_TREND_TERMS])

    if hits == 0 and tech == 0:
        return 0.0

    # 실무 신호가 충분하면 패널티 최소화
    strong_terms = _SECTION_EVENT_STRONG_TERMS_MAP.get(section_key, ())
    title_terms = _SECTION_TITLE_CORE_TERMS_MAP.get(section_key, ())
    strong_signal = count_any(t, [k.lower() for k in strong_terms]) + count_any(ttl, [k.lower() for k in title_terms])
    if strong_signal >= 2:
        return 0.0
    if strong_signal == 1:
        # pest: '협의회/간담회/회의/교육' 등 행정 일정성 기사 상단 배치 억제
        if section_key == "pest" and any(w in t for w in ("협의회", "간담회", "회의", "설명회", "교육", "워크숍", "세미나")):
            return 2.0
        return 1.2
    # 시찰/협의회/방문/기술트렌드만 있는 경우는 더 크게 감점
    return 2.8 + 0.6 * max(0, hits - 1) + 0.4 * tech

SUPPLY_TITLE_CORE_TERMS = ('수급','가격','시세','경락가','작황','출하','재고','저장','물량')
DIST_TITLE_CORE_TERMS = ('가락시장','도매시장','공판장','경락','경매','반입','중도매인','시장도매인','apc','원산지','산지유통','산지유통센터','온라인도매시장','온라인 도매시장','수출','선적','수출길','검역','통관')
POLICY_TITLE_CORE_TERMS = (
    '대책','지원','할당관세','검역','단속','고시','개정','브리핑','보도자료','물가','가격','성수품','차례상','소비자물가','물가지수','통계','kosis',
    '협의체','위원회','출범','특별관리','최소가격','보전제','제도개선','제도 개선','구조개선','구조 개선',
)
PEST_TITLE_CORE_TERMS = ('병해충','방제','예찰','과수화상병','탄저병','냉해','동해','약제','농약')
_SECTION_TITLE_CORE_TERMS_MAP = {
    "supply": SUPPLY_TITLE_CORE_TERMS,
    "dist": DIST_TITLE_CORE_TERMS,
    "policy": POLICY_TITLE_CORE_TERMS,
    "pest": PEST_TITLE_CORE_TERMS,
}
_SECTION_EVENT_STRONG_TERMS_MAP = {
    "supply": tuple(NH_COOCUR_SUPPLY),
    "dist": tuple(NH_COOCUR_DIST),
    "policy": tuple(NH_COOCUR_POLICY),
    "pest": PEST_TITLE_CORE_TERMS,
}

def governance_interview_penalty(text: str, title: str, section_key: str, horti_sc: float, market_hits: int) -> float:
    """행정/정치/인터뷰성 기사(도지사/민선/도정 등)가 '부분 언급'만으로 상단에 올라오는 것을 억제."""
    t = (text or "").lower()
    ttl = (title or "").lower()
    # 제목에서의 품목/원예 신호(본문 일부 언급 오탐 방지)
    horti_title_sc = best_horti_score(title or "", "")

    roles = ("도지사", "지사", "시장", "군수", "도의회", "도의원", "시의회", "국회의원", "도정", "시정", "군정", "행정")
    adminish = ("민선", "도청", "시청", "군청", "정무", "공약", "관광", "복지", "청년", "교육", "교통", "soc")

    if not (any(r in ttl for r in roles) or any(r in ttl for r in adminish)):
        return 0.0

    strong_terms = ("할인", "할인지원", "할당관세", "수급", "가격", "출하", "재고",
                    "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
                    "원산지", "부정유통", "단속", "검역", "통관", "수출")
    strong_hits = count_any(t, [s.lower() for s in strong_terms])

    # 예외: 제목에도 품목/시장 신호가 있고 실무 신호가 강하면 약한 감점만
    if strong_hits >= 2 and (market_hits >= 1 or horti_title_sc >= 1.6) and (horti_sc >= 2.2 or ("농산물" in t) or ("농식품" in t)):
        return 0.8

    # 제목 품목 신호가 약하면(=본문 일부 언급) 감점을 키워 상단/코어 진입을 거의 막는다.
    if horti_title_sc < 1.4 and market_hits == 0:
        return 4.0 if section_key in ("supply", "policy", "dist") else 3.0

    if horti_sc >= 2.6 and strong_hits >= 1:
        return 1.6

    # 기본 감점
    return 3.2 if section_key in ("supply", "policy", "dist") else 2.5



# -----------------------------
# Local brief detection (티어 기반 하단/제외용)
# -----------------------------
# 목표: 특정 매체를 찍어 누르는 것이 아니라, '지역 단신/지자체 행정 공지형' 패턴 자체를 잡아낸다.
# - 예: ○○시/○○군/○○구 + (지원/추진/협약/개최/모집/선정/간담회...) 류
# - 단, '자조금(원예)' 같이 실무 핵심 이슈는 예외로 살린다.
_LOCAL_REGION_IN_TITLE_RX = re.compile(r"[가-힣]{2,}(?:시|군|구|읍|면)")
_LOCAL_BRIEF_PUNCT_RX = re.compile(r"[，,·•]|\s[-–—]\s")
_LOCAL_ADMINISH_TERMS = (
    "지원", "추진", "확대", "구축", "조성", "개선", "강화", "점검", "단속", "시범", "공모", "선정", "모집",
    "협약", "간담회", "설명회", "회의", "교육", "워크숍", "세미나", "발대식", "출범", "개최", "행사",
    "방문", "현장", "개관", "개장", "준공", "착공", "완공", "기부", "전달", "기탁", "투입", "예산", "억원"
)
# dist에서 '로컬 단신'으로 보기 싫은 유형을 더 강하게 걸러야 하는 이유:
# - 후보가 적은 날, 이런 단신이 1~2위를 차지하면 진짜 체크해야 할 이슈(예: 원예 자조금)가 아래로 밀린다.
_DIST_STRONG_ANCHORS = (
    "가락시장", "도매시장", "공판장", "공영도매시장", "경락", "경매", "반입",
    "도매법인", "중도매", "시장도매인", "산지유통", "산지유통센터", "apc",
    "원산지", "부정유통", "단속", "검역", "통관", "수출", "온라인 도매시장",
)

# 공직자(시장/군수/구청장/도지사 등) 동정성/현장점검성 기사 탐지
# - '도매시장'이 들어가도 실제로는 지자체 동정 기사인 경우가 많아, dist 상단을 오염시키는 원인.
# - 특정 매체가 아니라 '패턴'을 기준으로 판정한다.
_LOCAL_OFFICIAL_IN_TITLE_RX = re.compile(r"(?:^|[\s·,，])(?:[가-힣]{2,4}\s+)?[가-힣]{2,4}\s+(?:시장|군수|구청장|도지사|지사)(?=$|[\s·,，])")
_LOCAL_OFFICIAL_MEETING_TERMS = (
    "현장간부회의", "간부회의", "현장회의", "업무보고", "주재", "점검", "현장점검", "방문", "현장 방문",
    "청취", "애로사항", "간담회", "설명회", "회의",
)
_LOCAL_NATIONAL_LEVEL_HINTS = ("국회", "장관", "농식품부", "정부", "국정", "법안", "개정", "예산", "대책", "대응")

def is_local_brief_text(title: str, desc: str, section_key: str) -> bool:
    """지역 단신(지자체 행정 공지형) 여부.
    - 특정 매체가 아니라 '패턴'을 기준으로 판정한다.
    - dist에서만 보수적으로 사용(다른 섹션까지 과도하게 줄이지 않기 위함).
    """
    if section_key != "dist":
        return False

    if is_dist_local_field_profile_context(title, desc):
        return False

    ttl = (title or "")
    txt = ((title or "") + " " + (desc or "")).lower()
    ttl_l = (title or "").lower()

    # 예외: 원예 자조금은 반드시 체크(지역기사라도 실무 핵심)
    if "자조금" in txt and count_any(txt, [t.lower() for t in ("원예","과수","화훼","과일","채소","청과","사과","배","감귤","딸기","고추","오이","포도")]) >= 1:
        return False

    # 제목에 지역 단위(시/군/구/읍/면) 표기가 없으면 로컬 단신으로 보지 않음
    # 단, '안산 시장'처럼 (지자체장) 표기는 있는데 '안산시'가 없는 케이스가 있어 보완한다.
    if (_LOCAL_REGION_IN_TITLE_RX.search(ttl) is None) and (_LOCAL_OFFICIAL_IN_TITLE_RX.search(ttl) is None):
        if not is_local_agri_org_feature_context(title, desc):
            return False

    # 제목이 '○○시, ...' / '○○군·...' 같은 단신형 구두점 패턴이면 강한 신호
    punct = _LOCAL_BRIEF_PUNCT_RX.search(ttl) is not None

    # 지자체 행정/공지형 단어(지원/추진/협약/모집...)가 제목/본문에 있으면 단신 가능성↑
    adminish_hits = count_any(txt, [t.lower() for t in _LOCAL_ADMINISH_TERMS])

    if (not punct) and adminish_hits == 0:
        # 지역 표기만 있다고 단신으로 보진 않음(오탐 방지)
        return False

    # 제목/본문에 도매·유통 '강 앵커'가 있으면 로컬 단신으로 단정하지 않음
    # 단, '○○ 시장/군수 … 도매시장 현장간부회의/점검'류는 앵커가 있어도 실무 핵심도가 낮은 동정성 기사이므로
    # 로컬 단신으로 간주(빈칸 메우기용으로만 남도록)한다.
    official_meeting = (_LOCAL_OFFICIAL_IN_TITLE_RX.search(ttl) is not None) and (count_any(txt, [t.lower() for t in _LOCAL_OFFICIAL_MEETING_TERMS]) >= 1)
    if count_any(txt, [t.lower() for t in _LOCAL_NATIONAL_LEVEL_HINTS]) >= 1:
        official_meeting = False


    # 예산/투입/사업비/억원 등 '지자체 사업 종합' 단신은(특히 통신·지방면) 유통 핵심 이슈를 밀어내는 경우가 많아
    # 도매시장/공판장/경락/수출 같은 강 앵커가 뚜렷하지 않으면 로컬 단신으로 본다.
    if ("투입" in txt or "예산" in txt or "사업비" in txt or "억원" in txt) and re.search(r"\d{2,5}\s*억", txt):
        strong_market = count_any(txt, [t.lower() for t in ("가락시장","도매시장","공판장","공영도매시장","경락","경매","반입","수출","검역","통관")])
        if strong_market == 0 and not has_apc_agri_context(txt):
            return True

    if any(w.lower() in txt for w in _DIST_STRONG_ANCHORS):
        if not official_meeting:
            return False
    if has_apc_agri_context(txt) and (not official_meeting):
        return False
    # 공직자 동정 + 회의/점검/방문이면 로컬 단신으로 처리
    if official_meeting:
        return True

    # 지역 농협/조합 성과 소개형 수출·판로 기사는 dist에서 핵심 현장 이슈보다 후순위로 본다.
    if is_local_agri_org_feature_context(title, desc):
        strong_market = count_any(txt, [t.lower() for t in ("가락시장","도매시장","공판장","공영도매시장","경락","경매","반입","온라인 도매시장")])
        if strong_market == 0 and not has_apc_agri_context(txt):
            return True

    # 제목의 원예/도매 신호가 약하면(=본문 일부 언급) 단신으로 간주
    if best_horti_score(title or "", "") < 1.6 and count_any(ttl_l, [t.lower() for t in _DIST_STRONG_ANCHORS]) == 0:
        return True

    # 그 외는 보수적으로 False
    return False


def title_signal_bonus(title: str) -> float:
    t = (title or '').lower()
    bonus = 0.0
    if _NUMERIC_HINT_RE.search(t):
        bonus += 0.8
    if _UNIT_HINT_RE.search(t):
        bonus += 0.8
    return bonus


# -----------------------------
# Dedupe index
# -----------------------------
class DedupeIndex:
    def __init__(self) -> None:
        self.seen_norm: set[str] = set()
        self.seen_canon: set[str] = set()
        self.seen_press_title: set[str] = set()

    def add_and_check(self, canon_url: str, press: str, title_key: str, norm_key: str) -> bool:
        if norm_key in self.seen_norm:
            return False
        if canon_url:
            h = hashlib.sha1(canon_url.encode("utf-8")).hexdigest()[:16]
            if h in self.seen_canon:
                return False
        pt = f"{(press or '').strip()}|{title_key}"
        if pt in self.seen_press_title:
            return False

        self.seen_norm.add(norm_key)
        if canon_url:
            self.seen_canon.add(hashlib.sha1(canon_url.encode("utf-8")).hexdigest()[:16])
        self.seen_press_title.add(pt)
        return True


# -----------------------------
# Press mapping (✅ 2번: 아주뉴스/스포츠서울 추가)
# -----------------------------
def normalize_host(host: str) -> str:
    h = (host or "").lower().strip()
    for pfx in ("www.", "m.", "mobile."):
        if h.startswith(pfx):
            h = h[len(pfx):]
    return h

PRESS_HOST_MAP = {
    # 중앙/경제/통신
    "yna.co.kr": "연합뉴스",
    "mk.co.kr": "매일경제",
    "mt.co.kr": "머니투데이",
    "fnnews.com": "파이낸셜뉴스",
    "fntimes.com": "한국금융신문",
    "sedaily.com": "서울경제",
    "hankyung.com": "한국경제",
    "joongang.co.kr": "중앙일보",
    "chosun.com": "조선일보",
    "donga.com": "동아일보",
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "kmib.co.kr": "국민일보",
    "seoul.co.kr": "서울신문",
    "news1.kr": "뉴스1",
    "newsis.com": "뉴시스",
    "newsgn.com": "뉴스경남",
    "www.newsgn.com": "뉴스경남",
    "newspim.com": "뉴스핌",
    "edaily.co.kr": "이데일리",
    "asiae.co.kr": "아시아경제",
    "heraldcorp.com": "헤럴드경제",

    # 방송
    "kbs.co.kr": "KBS",
    "sbs.co.kr": "SBS",
    "imbc.com": "MBC",
    "ytn.co.kr": "YTN",
    "jtbc.co.kr": "JTBC",
    "mbn.co.kr": "MBN",

    # 농업/전문지(중요)
    "nongmin.com": "농민신문",
    "farmnmarket.com": "팜&마켓",
    "youngnong.co.kr": "한국영농신문",
    "www.youngnong.co.kr": "한국영농신문",
    "wonyesanup.co.kr": "원예산업신문",
    "www.wonyesanup.co.kr": "원예산업신문",
    "amnews.co.kr": "농축유통신문",
    "www.amnews.co.kr": "농축유통신문",
    "ikpnews.net": "한국농정신문",
    "www.ikpnews.net": "한국농정신문",
    "cooknchefnews.com": "쿡앤셰프",
    "breaknews.com": "브레이크뉴스",
    "www.breaknews.com": "브레이크뉴스",
    "jnilbo.com": "진일보",
    "www.jnilbo.com": "진일보",
    "kado.net": "강원도민일보",
    "www.kado.net": "강원도민일보",
    "chungnamilbo.co.kr": "충남일보",
    "www.chungnamilbo.co.kr": "충남일보",
    "jeonmin.co.kr": "전민일보",
    "www.jeonmin.co.kr": "전민일보",
    "busan.com": "부산일보",
    "www.busan.com": "부산일보",
    "kwnews.co.kr": "강원일보",
    "www.kwnews.co.kr": "강원일보",
    "idomin.com": "경남도민일보",
    "www.idomin.com": "경남도민일보",
    "etoday.co.kr": "이투데이",
    "www.etoday.co.kr": "이투데이",
    "kukinews.com": "쿠키뉴스",
    "www.kukinews.com": "쿠키뉴스",
    "enewstoday.co.kr": "이뉴스투데이",
    "www.enewstoday.co.kr": "이뉴스투데이",
    "kyeongin.com": "경인일보",
    "www.kyeongin.com": "경인일보",
    "hankooki.com": "데일리한국",
    "daily.hankooki.com": "데일리한국",
    "bokuennews.com": "보건신문",
    "www.bokuennews.com": "보건신문",
    "jmbc.co.kr": "전주MBC",
    "www.jmbc.co.kr": "전주MBC",
    "kjmbc.co.kr": "광주MBC",
    "www.kjmbc.co.kr": "광주MBC",
    "chmbc.co.kr": "춘천MBC",
    "www.chmbc.co.kr": "춘천MBC",
    "jndn.com": "전남매일",
    "www.jndn.com": "전남매일",
    "knnews.co.kr": "경남신문",
    "www.knnews.co.kr": "경남신문",
    "gnnews.co.kr": "경남일보",
    "www.gnnews.co.kr": "경남일보",
    "ksilbo.co.kr": "경상일보",
    "www.ksilbo.co.kr": "경상일보",
    "shinailbo.co.kr": "신아일보",
    "www.shinailbo.co.kr": "신아일보",
    "yonhapnewstv.co.kr": "연합뉴스TV",
    "www.yonhapnewstv.co.kr": "연합뉴스TV",

    # ✅ (추가) 아주뉴스/아주경제
    "ajunews.com": "아주경제",
    "ajunews.co.kr": "아주경제",
    "ajunews.kr": "아주경제",

    # ✅ (추가) 스포츠서울 (co.kr 케이스 포함)
    "sportsseoul.com": "스포츠서울",
    "sportsseoul.co.kr": "스포츠서울",

    # ✅ (추가) 영문 도메인→공식 한글 매체명
    "dailian.co.kr": "데일리안",
    "m.dailian.co.kr": "데일리안",
    "mdilbo.com": "무등일보",
    "sjbnews.com": "새전북신문",
    "jbnews.com": "중부매일",
    "joongdo.co.kr": "중도일보",
    "gukjenews.com": "국제뉴스",


    # 요청 매체(영문→한글)
    "mediajeju.com": "미디어제주",
    "pointdaily.co.kr": "포인트데일리",
    "metroseoul.co.kr": "메트로신문",
    "newdaily.co.kr": "뉴데일리경제",
    "biz.newdaily.co.kr": "뉴데일리경제",

    # 정책기관/연구기관
    "korea.kr": "정책브리핑",
    "mafra.go.kr": "농식품부",
    "at.or.kr": "aT",
    "dream.kotra.or.kr": "대한무역투자진흥공사",
    "naqs.go.kr": "농관원",
    "krei.re.kr": "KREI",
    "agrinet.co.kr": "한국농어민신문",
    "www.agrinet.co.kr": "한국농어민신문",
    "nocutnews.co.kr": "노컷뉴스",
    "ohmynews.com": "오마이뉴스",
    "pressian.com": "프레시안",
    "hankookilbo.com": "한국일보",
    "segye.com": "세계일보",
    "munhwa.com": "문화일보",
    "dt.co.kr": "디지털타임스",
    "etnews.com": "전자신문",
    "zdnet.co.kr": "지디넷코리아",
    "bloter.net": "블로터",
    "thebell.co.kr": "더벨",
    "sisajournal.com": "시사저널",
    "mediatoday.co.kr": "미디어오늘",
    "aflnews.co.kr": "농수축산신문",
    "www.aflnews.co.kr": "농수축산신문",
    "nongup.net": "농업정보신문",
    "www.nongup.net": "농업정보신문",
}

ABBR_MAP = {
    "mk": "매일경제",
    "mt": "머니투데이",
    "fntimes": "한국금융신문",
    "mbn": "MBN",
    "ytn": "YTN",
    "jtbc": "JTBC",
    "kbs": "KBS",
    "mbc": "MBC",
    "sbs": "SBS",
    "ajunews": "아주경제",
    "sportsseoul": "스포츠서울",
    "dailian": "데일리안",
    "mdilbo": "무등일보",
    "sjbnews": "새전북신문",
    "jbnews": "중부매일",
    "joongdo": "중도일보",
    "gukjenews": "국제뉴스",
    "agrinet": "한국농어민신문",
    "nocutnews": "노컷뉴스",
    "ohmynews": "오마이뉴스",
    "pressian": "프레시안",
    "hankookilbo": "한국일보",
    "segye": "세계일보",
    "munhwa": "문화일보",
    "dt": "디지털타임스",
    "etnews": "전자신문",
    "zdnet": "지디넷코리아",
    "bloter": "블로터",
    "thebell": "더벨",
    "sisajournal": "시사저널",
    "mediatoday": "미디어오늘",
    "newdaily": "뉴데일리경제",
    "youngnong": "한국영농신문",
    "wonyesanup": "원예산업신문",
    "amnews": "농축유통신문",
    "ikpnews": "한국농정신문",
    "cooknchefnews": "쿡앤셰프",
    "breaknews": "브레이크뉴스",
    "jnilbo": "진일보",
    "kado": "강원도민일보",
    "chungnamilbo": "충남일보",
    "jeonmin": "전민일보",
    "busan": "부산일보",
    "kwnews": "강원일보",
    "idomin": "경남도민일보",
    "etoday": "이투데이",
    "kukinews": "쿠키뉴스",
    "enewstoday": "이뉴스투데이",
    "kyeongin": "경인일보",
    "hankooki": "데일리한국",
    "bokuennews": "보건신문",
    "jmbc": "전주MBC",
    "kjmbc": "광주MBC",
    "chmbc": "춘천MBC",
    "jndn": "전남매일",
    "knnews": "경남신문",
    "gnnews": "경남일보",
    "ksilbo": "경상일보",
    "shinailbo": "신아일보",
    "yonhapnewstv": "연합뉴스TV",
}

def press_name_from_url(url: str) -> str:
    host = normalize_host(domain_of(url))
    if not host:
        return "미상"

    # 1) exact
    if host in PRESS_HOST_MAP:
        return PRESS_HOST_MAP[host]

    # 2) suffix match
    for k, v in PRESS_HOST_MAP.items():
        if host.endswith("." + k):
            return v

    # 3) 2단계 TLD 처리(co.kr 등)
    parts = host.split(".")
    if len(parts) >= 3 and parts[-1] == "kr" and parts[-2] in ("co", "or", "go", "ac", "re", "ne", "pe"):
        brand = parts[-3]
    elif len(parts) >= 2:
        brand = parts[-2]
    else:
        brand = host

    # 4) 약어 치환
    if brand in ABBR_MAP:
        return ABBR_MAP[brand]

    # 5) fallback
    # (CO 등) 최상위 도메인 조각이 매체명으로 떨어지는 경우 방어
    if brand in ("co", "go", "or", "ne", "ac", "re", "pe", "kr", "com", "net"):
        return "미상"
    return brand.upper() if len(brand) <= 6 else brand


def normalize_press_label(press: str, url: str = "") -> str:
    """Normalize publisher labels to canonical Korean press names.

    Some feeds may provide raw/english publisher labels (e.g., "newdaily").
    Apply alias + host-based normalization so rendering and dedupe stay consistent.
    """
    p = (press or "").strip()
    if not p:
        return press_name_from_url(url)

    p_compact = re.sub(r"\s+", "", p.lower())
    alias = {
        "newdaily": "\ub274\ub370\uc77c\ub9ac\uacbd\uc81c",
        "\ub274\ub370\uc77c\ub9ac": "\ub274\ub370\uc77c\ub9ac\uacbd\uc81c",
        "\ub274\ub370\uc77c\ub9ac\uacbd\uc81c": "\ub274\ub370\uc77c\ub9ac\uacbd\uc81c",
        "amnews": "\ub18d\ucd95\uc720\ud1b5\uc2e0\ubb38",
        "ikpnews": "\ud55c\uad6d\ub18d\uc815\uc2e0\ubb38",
        "fntimes": "\ud55c\uad6d\uae08\uc735\uc2e0\ubb38",
    }
    if p_compact in alias:
        return alias[p_compact]

    mapped = ""
    if url:
        try:
            mapped = press_name_from_url(url)
        except Exception:
            mapped = ""

    if "." in p and "/" not in p and " " not in p:
        try:
            return press_name_from_url("https://" + p)
        except Exception:
            return mapped or p

    if mapped and mapped != "미상" and re.fullmatch(r"[a-z0-9._-]+", p_compact):
        return mapped
    return p


# -----------------------------
# Press priority (중요도)
# -----------------------------
MAFRA_HOSTS = {"mafra.go.kr"}
POLICY_TOP_HOSTS = {"korea.kr", "mafra.go.kr", "at.or.kr", "naqs.go.kr", "krei.re.kr"}

# (4) 중요도 우선순위:
#   3: 중앙지/일간지/경제지 + 농민신문 + 방송사 + 농식품부·정책브리핑(최상)
#   2: 중소매체/지방언론/전문지/지자체·연구기관(중간)
#   1: 그 외(인터넷/기타)
TOP_TIER_PRESS = {
    "세계일보",
    "연합뉴스",
    "중앙일보", "동아일보", "조선일보", "한겨레", "경향신문", "국민일보", "서울신문",
    "매일경제", "머니투데이", "서울경제", "한국경제", "파이낸셜뉴스", "이데일리", "아시아경제", "헤럴드경제",
    "KBS", "MBC", "SBS", "YTN", "JTBC", "MBN",
    "농민신문",
    "정책브리핑", "농식품부",
    # 기관/공공(농업 관련)
    "aT", "농관원", "KREI",
}

MID_TIER_PRESS = {
    # 농업·유통 전문/중소 매체(필요시 추가 가능)
    "팜&마켓",
    "아주경제",
    # 스포츠서울은 한글 표기만 유지(중요도는 낮게)
    "데일리안",

    "한국농어민신문",
    "농수축산신문",
    "농업정보신문",
    "뉴스1",
    "뉴시스",
    "뉴스핌",
}

_UGC_HOST_HINTS = ("blog.", "tistory.", "brunch.", "post.naver.", "cafe.naver.", "youtube.", "youtu.be")

def press_priority(press: str, domain: str) -> int:
    """
    3: 중앙지/일간지/경제지 + 농민신문 + 방송사 + 농식품부·정책브리핑(최상)
    2: 중소매체/지방언론/전문지/지자체·연구기관(중간)
    1: 그 외(인터넷/기타)
    """
    p = (press or "").strip()
    d = (domain or "").lower()

    # 최상: 농식품부/정책브리핑 및 주요 농업기관
    if d in MAFRA_HOSTS or d.endswith(".mafra.go.kr") or p == "농식품부":
        return 3
    if d == "korea.kr" or p == "정책브리핑":
        return 3
    if d in POLICY_TOP_HOSTS or any(d.endswith("." + h) for h in POLICY_TOP_HOSTS):
        return 3
    if p in TOP_TIER_PRESS:
        return 3

    # 중간: 농업전문/중소/지방/연구·지자체
    if p in MID_TIER_PRESS:
        return 2
    if d.endswith(".go.kr") or d.endswith(".re.kr") or d in ALLOWED_GO_KR:
        return 2
    if p and ("방송" in p and p not in TOP_TIER_PRESS):
        return 2

    # UGC/커뮤니티성
    if any(h in d for h in _UGC_HOST_HINTS):
        return 1

    return 1

# -----------------------------
# Press tier/weight (정밀 가중치)
# - press_priority는 정렬용(3/2/1)로 유지하되, 스코어에는 더 세밀한 press_weight를 반영
# -----------------------------
# 최상위: 공식 정책/기관 (농식품부, 정책브리핑, aT, 농관원, KREI 등)
OFFICIAL_HOSTS = {
    'korea.kr', 'mafra.go.kr', 'at.or.kr', 'naqs.go.kr', 'krei.re.kr',
    # 참고용(정책/통계):
    'kostat.go.kr', 'customs.go.kr', 'moef.go.kr', 'kma.go.kr',
}

# 최상위 언론(중앙지/일간지/경제지/통신) + 방송 + 농민신문
MAJOR_PRESS = {
    "세계일보",
    '연합뉴스',
    '중앙일보', '동아일보', '조선일보', '한겨레', '경향신문', '국민일보', '서울신문',
    '매일경제', '머니투데이', '서울경제', '한국경제', '파이낸셜뉴스', '이데일리', '아시아경제', '헤럴드경제',
    'KBS', 'MBC', 'SBS', 'YTN', 'JTBC', 'MBN',
    # 종편/보도채널 (필요시 매핑 확대)
    'TV조선', '채널A', '연합뉴스TV', 'OBS',
    '농민신문',
}


BROADCAST_PRESS = {
    'KBS', 'MBC', 'SBS', 'YTN', 'JTBC', 'MBN',
    'TV조선', '채널A', '연합뉴스TV', 'OBS',
}

# 통신/온라인 뉴스 서비스(기사량이 많아 과대표집되기 쉬움): '가점'이 아니라 품질/이슈로 평가
WIRE_SERVICES = {"뉴스1", "뉴시스", "뉴스핌"}

# 농업 전문/현장 매체(원예·유통 실무에서 참고 가치가 높음) — 너무 과도하게 밀어주진 않되, '하단 고착'을 방지
AGRI_TRADE_PRESS = {"농민신문", "농수축산신문", "농업정보신문", "팜&마켓", "한국농어민신문"}
AGRI_TRADE_HOSTS = {"afnews.co.kr", "agrinet.co.kr", "farmnmarket.com", "nongmin.com"}
# 중간: 농업 전문지/지방/중소/연구·지자체
MID_PRESS_HINTS = (
    '농업', '팜', '축산', '유통', '식품', '경남', '전북', '전남', '충북', '충남', '강원', '제주',
)

LOW_QUALITY_PRESS = {
    # 지나치게 가십/클릭 유도 성향이 강한 경우(필요 시 추가)
    "팜&마켓",
    # '포인트데일리',
}

# 지역지(로컬) 중 과대표집 시 체감 품질을 떨어뜨린 사례가 있었던 매체는 별도 감점/티어 하향
REGIONAL_LOW_TIER_PRESS = {
    "새전북신문",
}

def press_tier(press: str, domain: str) -> int:
    """
    4: 공식 정책/기관(농식품부, 정책브리핑 등)
    3: 중앙지/일간지/경제지/통신 + 방송 + 농민신문
    2: 중소/지방/전문지/지자체·연구기관
    1: 그 외(인터넷/UGC/기타)
    """
    p = (press or '').strip()
    d = normalize_host(domain or '')
    d = (d or '').lower()

    # UGC/커뮤니티/블로그는 최하
    if any(h in d for h in _UGC_HOST_HINTS):
        return 1


    # ✅ 특정 로컬 매체(과대표집 방지): 중간 티어 힌트와 무관하게 최하 티어로 분류
    if p in REGIONAL_LOW_TIER_PRESS:
        return 1
    # 공식(정책/기관) 우선
    if d in OFFICIAL_HOSTS or any(d.endswith('.' + h) for h in OFFICIAL_HOSTS):
        return 4
    if p in ('농식품부', '정책브리핑', 'aT', '농관원', 'KREI'):
        return 4

    # 주요 언론
    if p in MAJOR_PRESS:
        return 3

    # 지자체/연구기관(.go.kr/.re.kr) 및 중간 티어 힌트
    if d.endswith('.go.kr') or d.endswith('.re.kr') or d in ALLOWED_GO_KR:
        return 2
    if p in MID_TIER_PRESS:
        return 2
    if p and ('방송' in p and p not in MAJOR_PRESS):
        return 2
    if any(h in p for h in MID_PRESS_HINTS):
        return 2

    return 1

def press_weight(press: str, domain: str) -> float:
    """스코어 가중치(정밀)."""
    t = press_tier(press, domain)
    # 기본 가중치: 공식 > 주요언론 > 중간 > 기타
    w = {4: 12.5, 3: 9.5, 2: 4.5, 1: -2.0}.get(t, -2.0)
    p = (press or '').strip()
    d = (domain or '').lower()
    # 로컬 매체(특정): 기본 가중치에 추가 감점(핵심 상단 잠식 방지)
    if p in REGIONAL_LOW_TIER_PRESS:
        w -= 2.4

    # 통신/공식은 기사 생산량이 많아도 핵심성 높음: 약간 추가
    if p == '연합뉴스':
        w += 0.8
    if d in ('korea.kr', 'mafra.go.kr'):
        w += 1.0

    # 농업 전문 매체는 '현장 정보' 가치가 있어 소폭 가점(단, 로컬 단신 필터/임계치로 과대표집 방지)
    if p in AGRI_TRADE_PRESS or normalize_host(d) in AGRI_TRADE_HOSTS:
        w += 1.2

    # 통신/온라인 서비스는 기사량이 많아 상단을 잠식하기 쉬움: 약간 감점(이슈 점수로 승부)
    if p in WIRE_SERVICES:
        w -= 0.8
    if p in LOW_QUALITY_PRESS:
        w -= 2.0
    # UGC 계열은 감점
    if any(h in d for h in _UGC_HOST_HINTS):
        w -= 3.0
    # 알 수 없는 짧은 약어(브랜드)로 추정되는 경우(지방/인터넷 재전송) 소폭 감점
    if (p == "미상") or (p.isupper() and len(p) <= 6 and p not in ("KREI", "KBS", "MBC", "SBS", "YTN", "JTBC", "MBN")):
        w -= 1.0
    return w


# -----------------------------
# Extra quality controls (도메인/지역농협 동정 기사 보정)
# -----------------------------
LOW_QUALITY_DOMAINS = {
    # 클릭/재전송/중복이 잦았던 도메인들(필요 시 추가)
    "m.sportsseoul.com", "sportsseoul.com",
    "www.onews.tv", "onews.tv",
}

POLICY_BRIEF_ONLY_DOMAINS = {
    "cooknchefnews.com",
}
def low_quality_domain_penalty(domain: str) -> float:
    d = normalize_host(domain or "")
    if not d:
        return 0.0
    if d in LOW_QUALITY_DOMAINS:
        return 3.5
    return 0.0

_LOCAL_COOP_RX = re.compile(r"[가-힣]{2,10}농협")

def local_coop_penalty(text: str, press: str, domain: str, section_key: str) -> float:
    """지역 단위 농협(지점/조합) 동정성 기사 감점.
    - 농민신문은 '지역농협 소식'이 많아 원예수급 핵심에서 밀려야 하는 경우가 있어 보정.
    - 단, 경제지주/공판장/하나로마트/온라인도매시장 등 '실무 신호'가 있으면 감점하지 않는다.
    """
    t = (text or "").lower()
    # 실무 신호가 있으면 감점하지 않음
    if any(k.lower() in t for k in NH_STRONG_TERMS) or any(k.lower() in t for k in NH_STRONG_COOCUR_TERMS):
        return 0.0
    if any(k in t for k in ("공판장", "가락시장", "도매시장", "경락", "경락가", "반입", "출하", "수급", "가격")):
        return 0.0

    if not _LOCAL_COOP_RX.search(t):
        return 0.0

    # '○○농협' + 행사/동정/기부성 기사 패널티
    if any(w in t for w in ("기부", "후원", "봉사", "행사", "축제", "시상", "간담회", "협의회", "설명회", "업무협약", "mou")):
        return 4.2 if section_key in ("supply", "dist", "policy") else 2.8

    # 단순 지역 소식은 소폭 감점
    return 2.0 if section_key in ("supply", "dist", "policy") else 1.2


def _sort_key_major_first(a: Article) -> Any:
    # 점수(관련성/품질)를 1순위로, 매체 티어는 2순위로 반영
    return _ranking_sort_key_major_first(a, press_priority)

# -----------------------------
# Business day / holidays
# -----------------------------
def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def is_korean_holiday(d: date) -> bool:
    s = d.isoformat()
    if s in EXCLUDE_HOLIDAYS:
        return False
    if s in EXTRA_HOLIDAYS:
        return True
    try:
        import holidays
        kr_factory = getattr(holidays, "KR", None)
        if kr_factory is None:
            return False
        kr = kr_factory(years=[d.year], observed=True)
        return d in kr
    except Exception:
        return False

def is_business_day_kr(d: date) -> bool:
    if is_weekend(d):
        return False
    if is_korean_holiday(d):
        return False
    return True

def previous_business_day(d: date) -> date:
    cur = d - timedelta(days=1)
    while not is_business_day_kr(cur):
        cur -= timedelta(days=1)
    return cur


# -----------------------------
# GitHub Contents API helpers
# -----------------------------
def github_api_headers(token: str) -> dict[str, str]:
    return _io_github_api_headers(token)


def _resolve_github_ref(ref: str | None) -> str:
    v = str(ref or "").strip()
    if not v or v == "main":
        return GH_CONTENT_REF
    return v


def _resolve_github_branch(branch: str | None) -> str:
    v = str(branch or "").strip()
    if not v or v == "main":
        return GH_CONTENT_BRANCH
    return v


def _normalize_repo_path(path: str) -> str:
    p = str(path or "").replace("\\", "/")
    parts = [x for x in p.split("/") if x and x != "."]
    return "/".join(parts)


def _dev_single_page_version_repo_path() -> str:
    configured = _normalize_repo_path(DEV_SINGLE_PAGE_VERSION_PATH)
    if configured:
        return configured
    preview_path = _normalize_repo_path(DEV_SINGLE_PAGE_PATH or "docs/dev/index.html")
    head, _, _tail = preview_path.rpartition("/")
    return f"{head}/version.json" if head else "version.json"


def _dev_single_page_version_url(site_path: str) -> str:
    rel = (DEV_SINGLE_PAGE_VERSION_URL_PATH or "version.json").strip() or "version.json"
    return _dev_single_page_asset_url(rel, site_path)


def _dev_single_page_asset_base_url() -> str:
    base = (DEV_PREVIEW_ASSET_BASE_URL or "").strip().rstrip("/")
    if not base:
        return ""
    if base.startswith(("http://", "https://")):
        return base
    log.warning("[WARN] DEV_PREVIEW_ASSET_BASE_URL invalid (no http/https): %s", base)
    return ""


def _dev_single_page_asset_url(rel_path: str, site_path: str) -> str:
    rel = (rel_path or "").strip().lstrip("/")
    base = _dev_single_page_asset_base_url()
    if base:
        return f"{base}/{rel}" if rel else base
    return build_site_url(site_path, rel)


def _dev_single_page_debug_repo_path(report_date: str) -> str:
    preview_path = _normalize_repo_path(DEV_SINGLE_PAGE_PATH or "docs/dev/index.html")
    head, _, _tail = preview_path.rpartition("/")
    return f"{head}/debug/{report_date}.json" if head else f"debug/{report_date}.json"


def _dev_single_page_debug_url(report_date: str, site_path: str) -> str:
    return _dev_single_page_asset_url(f"debug/{report_date}.json", site_path)


def _dev_single_page_archive_repo_path(report_date: str) -> str:
    preview_path = _normalize_repo_path(DEV_SINGLE_PAGE_PATH or "docs/dev/index.html")
    head, _, _tail = preview_path.rpartition("/")
    archive_dir = f"{head}/archive" if head else "archive"
    return f"{archive_dir}/{report_date}.html"


def _dev_single_page_archive_manifest_repo_path() -> str:
    preview_path = _normalize_repo_path(DEV_SINGLE_PAGE_PATH or "docs/dev/index.html")
    head, _, _tail = preview_path.rpartition("/")
    return f"{head}/archive_manifest.json" if head else "archive_manifest.json"


def _dev_single_page_archive_manifest_url(site_path: str) -> str:
    return _dev_single_page_asset_url("archive_manifest.json", site_path)


def _dev_single_page_archive_url(report_date: str, site_path: str, cache_bust: bool = False) -> str:
    base = build_site_url(site_path, DEV_SINGLE_PAGE_URL_PATH or "index.html")
    url = base
    report_date_s = str(report_date or "").strip()
    if report_date_s:
        url = f"{base}?date={quote(report_date_s)}"
    if not cache_bust:
        return url
    v = re.sub(r"[^0-9A-Za-z_-]", "", str(BUILD_TAG or ""))[:24] or now_kst().strftime("%Y%m%d%H%M")
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}v={v}"


def _assert_dev_single_page_write_path(path: str) -> None:
    """Fail fast when dev single-page mode attempts to write non-preview paths."""
    if not DEV_SINGLE_PAGE_MODE:
        return
    allowed = _normalize_repo_path(DEV_SINGLE_PAGE_PATH or "docs/dev/index.html")
    allowed_paths = {
        allowed,
        _dev_single_page_version_repo_path(),
        _dev_single_page_archive_manifest_repo_path(),
    }
    allowed_debug_dir = _dev_single_page_debug_repo_path("_marker_").rsplit("_marker_.json", 1)[0]
    allowed_archive_dir = _dev_single_page_archive_repo_path("_marker_").rsplit("_marker_.html", 1)[0]
    target = _normalize_repo_path(path)
    if target in allowed_paths:
        return
    if allowed_debug_dir and target.startswith(allowed_debug_dir) and target.endswith(".json"):
        return
    if allowed_archive_dir and target.startswith(allowed_archive_dir) and target.endswith(".html"):
        return
    allowed_text = ", ".join(
        sorted(p for p in allowed_paths if p)
        + ([allowed_debug_dir + "*.json"] if allowed_debug_dir else [])
        + ([allowed_archive_dir + "*.html"] if allowed_archive_dir else [])
    )
    raise RuntimeError(
        f"[DEV GUARD] blocked write path '{target}'. allowed paths: '{allowed_text}' (DEV_SINGLE_PAGE_MODE=true)"
    )



def github_get_file(repo: str, path: str, token: str, ref: str = "main") -> tuple[str | None, str | None]:
    return _io_github_get_file(
        repo,
        path,
        token,
        ref=_resolve_github_ref(ref),
        session_factory=http_session,
        log_http_error=_log_http_error,
    )


def github_list_dir(repo: str, dir_path: str, token: str, ref: str = "main") -> list[GithubDirItem]:
    """List a directory via GitHub Contents API. Returns [] on 404."""
    return _io_github_list_dir(
        repo,
        dir_path,
        token,
        ref=_resolve_github_ref(ref),
        session_factory=http_session,
        log_http_error=_log_http_error,
    )


def github_put_file(repo: str, path: str, content: str, token: str, message: str, sha: str | None = None, branch: str = "main") -> JsonDict:
    _assert_dev_single_page_write_path(path)
    return _io_github_put_file(
        repo,
        path,
        content,
        token,
        message,
        sha=sha,
        branch=_resolve_github_branch(branch),
        session_factory=http_session,
        logger=log,
        log_http_error=_log_http_error,
        strip_html_fn=_strip_swipe_hint_blocks,
    )


def github_put_file_if_changed(
    repo: str,
    path: str,
    content: str,
    token: str,
    message: str,
    sha: str | None = None,
    branch: str = "main",
    old_raw: str | None = None,
) -> bool:
    """Write a file only when content changed.

    Returns:
      True  -> wrote via GitHub PUT
      False -> skipped (no semantic content change)
    """
    _assert_dev_single_page_write_path(path)
    cmp_new = content
    if isinstance(cmp_new, str) and path.endswith(".html"):
        cmp_new = _strip_swipe_hint_blocks(cmp_new)

    if old_raw is None:
        try:
            old_raw, fetched_sha = github_get_file(repo, path, token, ref=branch)
        except Exception:
            old_raw, fetched_sha = None, None
        if not sha:
            sha = fetched_sha

    if (old_raw or "").strip() == (cmp_new or "").strip():
        return False

    github_put_file(repo, path, content, token, message, sha=sha, branch=branch)
    return True

def archive_page_exists(repo: str, token: str, d: str) -> bool:
    path = f"{DOCS_ARCHIVE_DIR}/{d}.html"
    _raw, sha = github_get_file(repo, path, token, ref="main")
    return sha is not None

# -----------------------------
# Manifest date sanitize / archive existence verification (✅ 3~4번: 404 방지)
# -----------------------------
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def is_iso_date_str(s: str) -> bool:
    s = (s or "").strip()
    if not _ISO_DATE_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False

def sanitize_dates(dates: list[str]) -> list[str]:
    out = []
    for d in (dates or []):
        if not isinstance(d, str):
            continue
        d = d.strip()
        if is_iso_date_str(d):
            out.append(d)
    return sorted(set(out))

def verify_recent_archive_dates(repo: str, token: str, dates_desc: list[str], report_date: str,
                                verify_n: int = 120, max_workers: int = 8) -> list[str]:
    """최근 N개(기본 120개)만 GitHub에 실제 파일 존재 여부를 확인해, UI에 노출되는 링크 404를 방지한다.
    최적화:
    - 기존: 날짜마다 Contents API를 호출(최대 verify_n번)
    - 개선: docs/archive 디렉터리를 1회 listing → set으로 존재여부 확인
    - listing 실패 시에만 기존 방식(날짜별 확인)으로 fallback
    """
    head = (dates_desc or [])[:verify_n]
    if not head:
        return []

    # 이번 실행에서 생성/업로드하므로 존재한다고 간주.
    if report_date and report_date not in head:
        head = [report_date] + head

    try:
        items = github_list_dir(repo, DOCS_ARCHIVE_DIR, token, ref="main")
        names = {it.get("name") for it in items if isinstance(it, dict)}
        avail_dates = set()
        for nm in names:
            if not isinstance(nm, str) or not nm.endswith(".html"):
                continue
            d = nm[:-5]
            if is_iso_date_str(d):
                avail_dates.add(d)

        verified = []
        for d in head:
            if d == report_date:
                verified.append(d)
            elif d in avail_dates:
                verified.append(d)
        return verified

    except Exception as e:
        log.warning("[WARN] archive directory listing failed; fallback to per-date checks: %s", e)

    from concurrent.futures import ThreadPoolExecutor

    to_check = [d for d in head if d != report_date]
    exists: dict[str, bool] = {}

    def _check(d: str) -> bool:
        try:
            return archive_page_exists(repo, token, d)
        except Exception as e2:
            log.warning("[WARN] archive exists check failed for %s: %s", d, e2)
            return False

    if to_check:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for d, ok in zip(to_check, ex.map(_check, to_check)):
                exists[d] = ok

    verified = []
    for d in head:
        if d == report_date:
            verified.append(d)
        else:
            if exists.get(d, False):
                verified.append(d)
    return verified



# -----------------------------
# State / archive manifest
# -----------------------------

def load_state(repo: str, token: str) -> JsonDict:
    raw, _sha = github_get_file(repo, STATE_FILE_PATH, token, ref="main")
    if not raw:
        return {"last_end_iso": None}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {"last_end_iso": None}
    except Exception:
        return {"last_end_iso": None}

def _parse_ymd(s: str) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        return None

def normalize_recent_items(recent_items: Any, base_day: date) -> list[JsonDict]:
    """state.recent_items를 표준화하고, base_day 기준 최근 N일만 남긴다."""
    if not isinstance(recent_items, list):
        return []
    cutoff = base_day - timedelta(days=max(CROSSDAY_DEDUPE_DAYS, 0))
    out: list[JsonDict] = []
    for it in recent_items:
        if not isinstance(it, dict):
            continue
        canon = (it.get("canon") or it.get("url") or "").strip()
        norm = (it.get("norm") or it.get("norm_key") or "").strip()
        d = _parse_ymd(str(it.get("date") or ""))
        if not d:
            continue
        if d < cutoff:
            continue
        if not (canon or norm):
            continue
        out.append({"date": d.isoformat(), "canon": canon, "norm": norm})
    # 키 중복 제거(최근 것을 우선)
    uniq = {}
    for it in sorted(out, key=lambda x: x.get("date", ""), reverse=True):
        k = it.get("norm") or it.get("canon")
        if not k:
            continue
        if k not in uniq:
            uniq[k] = it
    # 파일 크기 제한
    return list(sorted(uniq.values(), key=lambda x: x.get("date", ""), reverse=True))[:2000]


def rebuild_recent_items_for_report_date(existing_recent_items: Any, by_section: dict[str, list[Article]] | None, report_date: str, base_day: date) -> list[JsonDict]:
    """Build cross-day dedupe history deterministically for the current report_date.

    Why:
    - 같은 날짜(report_date)를 재실행할 때 기존 state.recent_items에 남아 있던
      "이전 실행의 선택 결과"가 섞이면, 이번 실행 최종 산출물과 state가 불일치할 수 있다.
    - 불일치가 누적되면 다음 실행에서 CROSSDAY_DEDUPE가 실제 노출되지 않은 URL까지
      이미 노출된 것으로 간주해 후보를 과차단할 수 있다.

    Rule:
    1) 기존 recent_items를 정규화
    2) report_date 항목은 전부 제거(해당 일자의 히스토리는 재생성)
    3) 이번 실행의 최종 by_section 산출물만 report_date로 추가
    4) 다시 정규화/중복제거
    """
    base = normalize_recent_items(existing_recent_items if isinstance(existing_recent_items, list) else [], base_day)

    # 재실행 안정화: 동일 report_date의 기존 잔존 기록 제거
    kept = [it for it in base if str(it.get("date") or "") != str(report_date)]

    merged = list(kept)
    if isinstance(by_section, dict):
        for _sec_items in by_section.values():
            for a in (_sec_items or []):
                try:
                    merged.append({
                        "date": report_date,
                        "canon": getattr(a, "canon_url", None),
                        "norm": getattr(a, "norm_key", None),
                    })
                except Exception:
                    pass

    return normalize_recent_items(merged, base_day)

def save_state(repo: str, token: str, last_end: datetime, recent_items: list[JsonDict] | None = None) -> None:
    # 기존 state를 읽어 스키마 확장에 대응(호환성 유지)
    old = load_state(repo, token)
    base_day = last_end.astimezone(KST).date()

    if recent_items is None:
        recent_items = normalize_recent_items(old.get("recent_items", []), base_day)
    else:
        recent_items = normalize_recent_items(recent_items, base_day)

    payload: JsonDict = {
        "last_end_iso": last_end.isoformat(),
        "recent_keep_days": CROSSDAY_DEDUPE_DAYS,
        "recent_items": recent_items,
    }
    raw_new = json.dumps(payload, ensure_ascii=False, indent=2)
    _raw_old, sha = github_get_file(repo, STATE_FILE_PATH, token, ref="main")
    github_put_file_if_changed(repo, STATE_FILE_PATH, raw_new, token,
                               "Update state", sha=sha, branch="main", old_raw=_raw_old)

# --- per-run cache: manifest dates (DESC) ---
_MANIFEST_DATES_DESC_CACHE: dict[str, list[str]] = {}

def _get_manifest_dates_desc_cached(repo: str, token: str) -> list[str]:
    """Return archive dates DESC from archive manifest (.agri_archive.json).

    This list should represent navigable dates (business days), and is used to rebuild navRow
    so navigation never points to non-existent (holiday) pages.
    """
    key = f"{repo}"
    if key in _MANIFEST_DATES_DESC_CACHE:
        return _MANIFEST_DATES_DESC_CACHE[key]
    try:
        manifest, _sha = load_archive_manifest(repo, token)
        manifest = _normalize_manifest(manifest)
        dates = manifest.get("dates", []) or []
        dates_desc = sorted(set(sanitize_dates(list(dates))), reverse=True)
    except Exception:
        dates_desc = []
    _MANIFEST_DATES_DESC_CACHE[key] = dates_desc
    return dates_desc

def load_archive_manifest(repo: str, token: str) -> tuple[JsonDict, str | None]:
    raw, sha = github_get_file(repo, ARCHIVE_MANIFEST_PATH, token, ref="main")
    if not raw:
        return {"dates": []}, sha
    try:
        return _normalize_manifest(json.loads(raw)), sha
    except Exception:
        return {"dates": []}, sha

def save_archive_manifest(repo: str, token: str, manifest: JsonDict, sha: str | None) -> None:
    manifest = _normalize_manifest(manifest)
    body = json.dumps(manifest, ensure_ascii=False, indent=2)
    github_put_file_if_changed(repo, ARCHIVE_MANIFEST_PATH, body, token,
                               "Update archive manifest", sha=sha, branch="main")
    # Keep per-run cache aligned with what we just saved.
    _MANIFEST_DATES_DESC_CACHE[f"{repo}"] = sorted(set(sanitize_dates(list(manifest.get("dates", []) or []))), reverse=True)





def save_docs_archive_manifest(repo: str, token: str, dates: list[str]) -> bool:
    """Publish archive date manifest to docs/ so client JS can avoid 404 navigation.

    Output path: docs/archive_manifest.json
    Format: {"version":1,"updated_at_kst":"...","dates":["YYYY-MM-DD", ...]} (dates are DESC sorted)

    Returns:
      True  -> updated docs/archive_manifest.json
      False -> skipped (dates unchanged) or failed
    """
    try:
        clean = [d for d in (dates or []) if isinstance(d, str) and is_iso_date_str(d)]
        clean = sorted(set(clean), reverse=True)

        _raw_old, sha_old = github_get_file(repo, DOCS_ARCHIVE_MANIFEST_JSON_PATH, token, ref="main")
        old_dates: list[str] = []
        if _raw_old:
            try:
                old_obj = json.loads(_raw_old)
                if isinstance(old_obj, dict):
                    old_dates = sorted(set(sanitize_dates(list(old_obj.get("dates", []) or []))), reverse=True)
            except Exception:
                old_dates = []

        if old_dates == clean:
            return False

        payload: JsonDict = {
            "version": 1,
            "updated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
            "dates": clean,
        }
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        github_put_file(repo, DOCS_ARCHIVE_MANIFEST_JSON_PATH, body, token, "Update archive manifest", sha=sha_old, branch="main")
        return True
    except Exception as e:
        log.warning("[WARN] save_docs_archive_manifest failed: %s", e)
        return False


def load_search_index(repo: str, token: str) -> tuple[JsonDict, str | None]:
    raw, sha = github_get_file(repo, DOCS_SEARCH_INDEX_PATH, token, ref="main")
    if not raw:
        return {"version": 1, "updated_at": "", "items": []}, sha
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            obj = {"version": 1, "items": obj}
        if not isinstance(obj, dict):
            obj = {"version": 1, "items": []}
        items = obj.get("items", [])
        if not isinstance(items, list):
            items = []
        obj["items"] = items
        obj.setdefault("version", 1)
        obj.setdefault("updated_at", "")
        return obj, sha
    except Exception:
        return {"version": 1, "updated_at": "", "items": []}, sha


def save_search_index(repo: str, token: str, idx: JsonDict, sha: str | None) -> None:
    if not isinstance(idx, dict):
        idx = {"version": 1, "updated_at": "", "items": []}
    idx["version"] = 1
    idx["updated_at"] = datetime.now(tz=KST).isoformat()
    items = idx.get("items", [])
    if not isinstance(items, list):
        items = []
    # cap size
    if len(items) > MAX_SEARCH_ITEMS:
        items = items[:MAX_SEARCH_ITEMS]
        idx["items"] = items

    github_put_file(repo, DOCS_SEARCH_INDEX_PATH, json.dumps(idx, ensure_ascii=False, indent=2), token,
                    "Update search index", sha=sha, branch="main")


def _make_search_items_for_day(report_date: str, by_section: dict[str, list[Any]], site_path: str) -> list[JsonDict]:
    """Build search-index items for a single report day.

    `by_section` normally contains lists of Article objects (our internal dataclass),
    but some legacy paths may pass dict-like items. Support both.
    NOTE: Keep output schema stable for index.html JS (press_tier, summary truncation, etc.).
    """
    def _get(a: object, key: str, default: Any = "") -> Any:
        if isinstance(a, dict):
            return a.get(key, default)
        return getattr(a, key, default)

    items: list[JsonDict] = []
    for sec in SECTIONS:
        key = sec["key"]
        stitle = sec["title"]
        archive_href = build_site_url(site_path, f"archive/{report_date}.html") + f"#sec-{key}"
        lst = by_section.get(key, []) or []
        for i, a in enumerate(lst, start=1):
            url = (_get(a, "link") or _get(a, "url") or _get(a, "originallink") or "").strip()
            title = (_get(a, "title") or "").strip()
            press = (_get(a, "press") or _get(a, "publisher") or _get(a, "company") or "").strip()
            summary = (_get(a, "summary") or _get(a, "desc") or _get(a, "description") or "").strip()

            score_raw = _get(a, "score", 0.0)
            try:
                score = float(score_raw or 0.0)
            except Exception:
                score = 0.0

            dom = urlparse(url).netloc if url else ""
            tier = int(press_tier(press, dom))
            _id = hashlib.md5(f"{report_date}|{key}|{url}|{title}".encode("utf-8")).hexdigest()[:12]

            items.append({
                "id": _id,
                "date": report_date,
                "section": key,
                "section_title": stitle,
                "rank": i,
                "title": title,
                "press": press,
                "summary": summary[:180],
                "url": url,
                "archive": archive_href,
                "score": score,
                "press_tier": tier,
            })
    return items

def update_search_index(existing: JsonDict, report_date: str, by_section: dict[str, list[Any]], site_path: str) -> JsonDict:
    if not isinstance(existing, dict):
        existing = {"version": 1, "updated_at": "", "items": []}
    items = existing.get("items", [])
    if not isinstance(items, list):
        items = []

    # remove existing day entries
    items = [x for x in items if isinstance(x, dict) and x.get("date") != report_date]

    # add today's
    items = _make_search_items_for_day(report_date, by_section, site_path) + items

    # keep last MAX_SEARCH_DATES distinct dates
    def _date_key(d: str) -> date:
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return date.min

    date_values = [str(x.get("date")) for x in items if isinstance(x, dict) and isinstance(x.get("date"), str)]
    dates_desc = sorted(set(date_values), key=_date_key, reverse=True)
    keep_dates = set(dates_desc[:MAX_SEARCH_DATES])

    items = [x for x in items if isinstance(x, dict) and x.get("date") in keep_dates]

    # sort: newer date, higher press_tier, higher score
    def _sort(x: JsonDict) -> tuple[int, int, float, int]:
        d = x.get("date") or ""
        try:
            di = int(d.replace("-", ""))
        except Exception:
            di = 0
        return (di, int(x.get("press_tier") or 0), float(x.get("score") or 0.0), -int(x.get("rank") or 999))

    items.sort(key=_sort, reverse=True)

    # cap items
    if len(items) > MAX_SEARCH_ITEMS:
        items = items[:MAX_SEARCH_ITEMS]

    existing["items"] = items
    return existing




# -----------------------------
# Naver News search
# -----------------------------
def _naver_client_cfg() -> NaverClientConfig:
    return NaverClientConfig(
        client_id=NAVER_CLIENT_ID,
        client_secret=NAVER_CLIENT_SECRET,
        max_retries=NAVER_MAX_RETRIES,
        backoff_max_sec=NAVER_BACKOFF_MAX_SEC,
    )


def naver_news_search(query: str, display: int = 40, start: int = 1, sort: str = "date") -> NaverSearchResponse:
    return _collector_naver_news_search(
        cfg=_naver_client_cfg(),
        query=query,
        display=display,
        start=start,
        sort=sort,
        session_factory=http_session,
        throttle_fn=_naver_throttle,
        logger=log,
        log_http_error=_log_http_error,
    )


def naver_news_search_paged(query: str, display: int = 50, pages: int = 1, sort: str = "date") -> NaverSearchResponse:
    return _collector_naver_news_search_paged(
        cfg=_naver_client_cfg(),
        query=query,
        display=display,
        pages=pages,
        sort=sort,
        session_factory=http_session,
        throttle_fn=_naver_throttle,
        logger=log,
        log_http_error=_log_http_error,
    )

# -----------------------------
# Relevance / scoring
# -----------------------------
def naver_web_search(query: str, display: int = 10, start: int = 1, sort: str = "date") -> NaverSearchResponse:
    return _collector_naver_web_search(
        cfg=_naver_client_cfg(),
        query=query,
        display=display,
        start=start,
        sort=sort,
        session_factory=http_session,
        throttle_fn=_naver_throttle,
        logger=log,
        log_http_error=_log_http_error,
    )


def section_must_terms_ok(text: str, must_terms: list[str] | tuple[str, ...] | set[str]) -> bool:
    return has_any(text, must_terms)

def policy_domain_override(dom: str, text: str) -> bool:
    if dom in POLICY_DOMAINS or dom in ALLOWED_GO_KR or dom.endswith(".re.kr"):
        return has_any(text, [k.lower() for k in AGRI_POLICY_KEYWORDS])
    return False

_LOCAL_GEO_PATTERN = re.compile(r"[가-힣]{2,6}(군|시|구|도)\b")



# --- pest(병해충/방제) 정교화: 농업 맥락 없는 "방역/생활해충" 오탐 감소 ---
PEST_STRICT_TERMS = [
    # 병해
    "과수화상병", "탄저병", "역병", "잿빛곰팡이", "흰가루병", "노균병", "세균", "바이러스", "병반",
    # 해충
    "해충", "진딧물", "응애", "노린재", "나방", "총채벌레", "선충", "깍지벌레",
    # 방제/예찰/약제
    "병해충", "방제", "예찰", "방제약", "약제", "농약", "살포", "살충", "살균", "훈증",
]
PEST_WEATHER_TERMS = ["냉해", "동해", "서리", "한파", "저온피해"]
PEST_AGRI_CONTEXT_TERMS = [
    "농작물", "농업", "농가", "재배", "과수", "과원", "시설", "하우스",
    "사과", "배", "감귤", "포도", "딸기", "복숭아", "고추", "오이", "쌀", "벼",
]
PEST_HORTI_TERMS = [
    # 원예/과수/시설채소 중심(벼 방제 제외 판단용)
    "원예", "과수", "과원", "시설", "하우스", "비가림", "재배",
    "사과", "배", "감귤", "포도", "딸기", "복숭아", "단감", "곶감", "참다래", "키위",
    "오이", "고추", "풋고추", "토마토", "파프리카", "상추", "마늘",
    "화훼", "국화", "장미",
]
PEST_RICE_TERMS = [
    # 양곡(벼) 병해충/방제(양곡부 별도 운영 시 불필요한 경우가 많아 pest 섹션에서 제외)
    "논", "벼", "이앙", "벼멸구", "멸구", "먹노린재", "멸강나방",
    "도열병", "흰잎마름병", "키다리병", "잎집무늬마름병", "줄무늬잎마름병",
]
PEST_OFFTOPIC_TERMS = [
    # 사람/도시 방역성 기사(농업과 무관한 경우 차단)
    "코로나", "독감", "감염병", "방역", "방역당국", "모기", "진드기", "말라리아", "뎅기",
    # 생활 해충/건물 해충
    "바퀴", "흰개미", "개미",
    "보건소", "질병관리청", "방역소독", "소독", "소독차", "방역차", "특별방역", "시민", "주민",
    "학교", "어린이집", "환자", "감염",
]


def is_strong_horti_opinion_context(title: str, desc: str, dom: str = "", press: str = "", section_key: str = "") -> bool:
    """Allow a narrow subset of commodity-focused analysis/opinion stories into recall."""
    ttl = title or ""
    txt = f"{ttl} {desc or ''}".lower()
    if not txt or str(section_key or "").strip() not in ("supply", "policy", "dist"):
        return False
    if is_remote_foreign_trade_brief_context(ttl, desc or "", dom):
        return False

    managed_summary = _managed_commodity_match_summary(ttl, desc or "")
    managed_count = int(managed_summary.get("count") or 0)
    horti_sc = best_horti_score(ttl, desc or "")
    if managed_count == 0 and horti_sc < 1.6:
        return False

    analysis_hits = count_any(
        txt,
        [w.lower() for w in ("산업", "농가", "생육", "재배", "작황", "수급", "출하", "저장", "생산", "기후변화", "냉해", "저온", "피해", "현장", "대책")],
    )
    if analysis_hits < 2:
        return False
    if count_any(ttl.lower(), [w.lower() for w in ("인터뷰", "행사", "간담회", "세미나", "포럼", "개최")]) >= 1:
        return False

    if section_key == "policy":
        return analysis_hits >= 3 and count_any(txt, [w.lower() for w in ("정책", "제도", "대책", "개선")]) >= 1
    if section_key == "dist":
        return is_dist_field_market_response_context(ttl, desc or "", dom, press)
    return True


def is_relevant(title: str, desc: str, dom: str, url: str, section_conf: JsonDict, press: str) -> bool:
    """섹션별 1차 필터(관련도/노이즈 컷).

    핵심 목표:
    - 동음이의어(배=배터리/배당, 밤=야간 등) 오탐을 강하게 차단
    - 지방 행사/동정/캠페인성 노이즈를 억제(단, 유통·현장/APC/산지유통/화훼 현장성은 예외 허용)
    - policy는 공식 소스/기관 기반을 우선
    """
    ttl = (title or "")
    desc = (desc or "")
    text = (ttl + " " + desc).lower()

    dom = normalize_host(dom or "")
    key = section_conf["key"]
    macro_policy_like = is_macro_policy_issue(text)
    broad_macro_price = is_broad_macro_price_context(title, desc)
    policy_market_brief = is_policy_market_brief_context(text, dom, press)
    policy_major_issue = is_policy_major_issue_context(title, desc, dom, press)
    local_org_feature = is_local_agri_org_feature_context(title, desc)
    policy_macro_keep = (
        key == "policy"
        and (
            policy_market_brief
            or policy_major_issue
            or broad_macro_price
            or (
                macro_policy_like
                and count_any(
                    text,
                    [w.lower() for w in ("농산물", "농식품", "농식품부", "과일", "채소", "사과", "배", "감귤", "딸기", "만감", "포도", "공급", "수급", "안정화")],
                ) >= 2
            )
        )
    )

    def _reject(reason: str) -> bool:
        # debug: collect why an item was filtered out
        dbg_add_filter_reject(key, reason, ttl, url, dom, press)
        return False
    # HARD BLOCK: 패스트푸드(빅맥/맥도날드 등) 가격 인상/외식 물가 기사(농산물 브리핑 노이즈)
    if is_fastfood_price_context(text):
        return _reject("hardblock_fastfood_price")

    # HARD BLOCK: 국제통상/산업 일반 기사에서 농산물이 부수적으로만 등장하는 경우
    if is_macro_trade_noise_context(text):
        return _reject("hardblock_macro_trade_noise")
    if is_remote_foreign_trade_brief_context(ttl, desc, dom):
        return _reject("remote_foreign_trade_brief")
    if key in ("supply", "policy") and is_flower_novelty_noise_context(ttl, desc):
        return _reject("flower_novelty_noise")

    # HARD BLOCK: 일반 소비자물가/가계지출 나열 기사(원예 수급 신호 약함)
    if is_general_consumer_price_noise(text):
        if best_horti_score(ttl, desc) < 1.8 and (not macro_policy_like) and (not broad_macro_price):
            return _reject("hardblock_consumer_price_noise")

    # URL/경로 기반 보정(지역/로컬 섹션 등)
    url = (url or "").strip()
    try:
        _path = urlparse(url).path.lower()
    except Exception:
        _path = ""

    # dist(유통/현장)에서 대형 유통(백화점/마트) 프로모션성 기사 차단
    # - '도매시장/공판장/경락' 같은 도매 맥락이 없으면 유통(도매) 섹션과 무관하므로 제외
    if key == "dist" and is_retail_promo_context(text):
        has_wholesale = any(t.lower() in text for t in WHOLESALE_MARKET_TERMS) or ("공판장" in text) or ("온라인 도매시장" in text)
        has_agri = any(t.lower() in text for t in ("농산물","농식품","농업","원예","과수","과일","채소","화훼","절화","청과"))
        if not has_wholesale:
            return _reject("dist_retail_promo_no_wholesale")
        # 아주 드물게 도매시장 행사 기사일 수 있으므로, 도매+농업 맥락이 함께 있을 때만 통과
        if not has_agri:
            return _reject("dist_retail_promo_no_agri")

    # dist: "오늘, 서울시" 등 지자체 행사/캠페인성 알림 기사 차단(도매시장 문구가 있어도 핵심성 낮음)
    if key == "dist":
        ttl_l2 = ttl.lower()
        if ("오늘, 서울시" in ttl_l2) or ("서울청년문화패스" in ttl_l2) or ("서울청년" in ttl_l2 and "패스" in ttl_l2):
            return _reject("dist_city_notice_event")
        if is_policy_export_support_brief_context(ttl, desc, dom, press):
            return _reject("dist_policy_export_support_brief")
        if is_dist_consumer_tail_context(ttl, desc):
            return _reject("dist_consumer_tail")

        # 농산물시장 이전/현대화/재배치는 유통·현장 핵심 이슈로 우선 허용
        if ("농산물" in text and "시장" in text) and any(w in text for w in ("이전", "옮긴", "이전지", "현대화", "재배치", "신설", "개장", "개소")):
            return True


    # 오피니언/사설/칼럼은 브리핑 대상에서 제외
    ttl_l = ttl.lower()
    if any(w.lower() in ttl_l for w in OPINION_BAN_TERMS):
        if not is_strong_horti_opinion_context(ttl, desc, dom, press, key):
            return _reject("opinion_or_editorial")

    # ✅ 사건/역사/정치성(예: 제주4.3) 인터뷰/스토리는 원예 브리핑 핵심 목적과 무관하므로 전체 섹션에서 배제
    if any(t in ttl_l for t in ("제주4.3", "제주4·3", "4.3의", "4·3")):
        return _reject("hardblock_jeju43_any_section")


    # 공통 제외(광고/구인/부동산 등)
    if any(k in text for k in BAN_KWS):
        return _reject("ban_keywords")

    # ✅ '멜론' 동음이의어(음원 플랫폼) 오탐 차단:
    # - '먹는 멜론' 맥락(재배/출하/작황/농가/도매시장 등)일 때만 통과
    if "멜론" in text and not is_edible_melon_context(text):
        return _reject("melon_non_edible_context")
    if "당근" in text and not is_edible_carrot_context(text):
        return _reject("carrot_non_edible_context")
    if "감자" in text and not is_fresh_potato_context(text):
        return _reject("potato_non_fresh_context")
    if key in ("supply", "policy", "dist") and is_non_horti_processed_export_context(ttl, desc):
        return _reject("non_horti_processed_export_context")
    # ✅ '피망' 동음이의어(게임/브랜드) 오탐 차단:
    # - 채소/농업 맥락일 때만 통과
    if "피망" in text and not is_edible_pimang_context(text):
        return _reject("pimang_non_edible_context")
    if is_apple_apology_context(text):
        return _reject("apple_apology_context")
    # ✅ '사과' 동음이의어(사과대/사과문 등) 오탐 차단: 과일/시장 맥락일 때만 통과
    if "사과" in text and not is_edible_apple_context(text) and (not policy_macro_keep):
        return _reject("apple_non_edible_context")
    if key in ("supply", "policy", "dist") and is_agri_training_recruitment_context(ttl, desc):
        return _reject("agri_training_recruitment")
    if key in ("supply", "dist") and is_dist_political_visit_context(ttl, desc):
        return _reject("market_political_visit_noise")
    if key == "supply" and is_agri_org_rename_context(ttl, desc):
        return _reject("agri_org_admin_noise")
    if key in ("supply", "policy", "dist") and is_title_livestock_dominant_context(ttl, desc):
        return _reject("livestock_title_dominant")


    # ✅ 축산물(한우/돼지고기/계란 등) 단독 이슈는 원예 브리핑 목적과 다르므로 완전 배제
    # - 단, '농림축산식품부/농축산물' 같은 중립 표현만으로는 오탐하지 않도록 해당 문구를 제거 후 판단한다.
    _t2 = text
    for _ph in LIVESTOCK_NEUTRAL_PHRASES:
        _t2 = _t2.replace(_ph.lower(), "")
    # 원예/농산물(비축산) 신호(자조금 자체는 축산도 존재하므로 여기선 제외)
    _horti_non_livestock = [
        "원예","과수","화훼","절화","과일","채소","청과","시설채소","하우스","비가림",
        "사과","배","감귤","포도","딸기","고추","오이","토마토","파프리카","상추",
        "단감","곶감","참다래","키위","샤인머스캣","만감","한라봉","레드향","천혜향",
        "국화","장미",
    ]
    livestock_hits = count_any(_t2, [t.lower() for t in LIVESTOCK_STRICT_TERMS])
    horti_hits_pre = count_any(_t2, [t.lower() for t in _horti_non_livestock])
    horti_sc_pre = best_horti_score(ttl, desc)
    # 축산 강신호(축산물/한우/돼지고기/계란 등) + 원예 신호 거의 없음 → 완전 배제
    livestock_core = ("축산물" in _t2) or any(w in _t2 for w in ("한우","한돈","우육","돈육","소고기","돼지고기","닭고기","계란","달걀","우유","낙농","양돈","양계"))
    policy_stabilization_keep = (key == "policy") and is_supply_stabilization_policy_context(text, dom, press)
    policy_market_brief_keep = (key == "policy") and policy_market_brief
    if livestock_core and (livestock_hits >= 1) and (horti_hits_pre == 0) and (horti_sc_pre < 1.2) and (not policy_macro_keep) and (not policy_stabilization_keep) and (not policy_market_brief_keep):
        return _reject("livestock_only")

    # ✅ 수산물 단독 이슈(옥돔/갈치/어업/양식 등)는 원예 브리핑 목적과 달라 배제
    _t3 = text
    for _ph in FISHERY_NEUTRAL_PHRASES:
        _t3 = _t3.replace(_ph.lower(), "")
    fishery_hits = count_any(_t3, [t.lower() for t in FISHERY_STRICT_TERMS])
    horti_hits_pre_f = count_any(_t3, [t.lower() for t in _horti_non_livestock])
    if fishery_hits >= 2 and horti_hits_pre_f == 0 and horti_sc_pre < 1.3:
        return _reject("fishery_only")

    # 수산 고유 어종/어업 키워드가 제목에 직접 등장하고 원예 신호가 약하면 우선 배제
    fishery_title_hits = count_any(ttl.lower(), [t.lower() for t in FISHERY_STRICT_TERMS])
    if fishery_title_hits >= 1 and best_horti_score(ttl, "") < 1.2:
        return _reject("fishery_title_only")

    # ✅ 해외 원예/화훼 업계 '원격 해외' 기사(국내 맥락 없음)는 실무와 거리가 멀어 제외
    if key in ("supply", "dist") and is_remote_foreign_horti(text):
        return _reject("remote_foreign_horti")


    # (미리) 원예/도매 맥락 점검( must_terms 예외처리에 사용 )
    horti_sc = best_horti_score(ttl, desc)
    supply_feature_kind = supply_feature_context_kind(ttl, desc)

    # ✅ APC는 UPS/전원장비 문맥으로도 자주 등장하므로, '농업/산지유통' 문맥일 때만 인정한다.
    market_ctx_terms = ["가락시장", "도매시장", "공판장", "청과", "경락", "경락가", "반입", "중도매인", "시장도매인", "온라인 도매시장", "산지유통", "산지유통센터"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    # (주의) 가격/물량/재고 등은 산업/IT 기사에도 흔한 범용 단어이므로, 원예 코어가 아니라 '신호(signal)'로만 사용한다.
    supply_signal_terms = ["가격", "시세", "수급", "작황", "출하", "반입", "물량", "재고", "경락", "경락가", "경매"]
    signal_hits = count_any(text, [t.lower() for t in supply_signal_terms])

    # 원예 코어(범용 단어 제외) — must_terms 실패 시 예외(살리기) 판단에만 사용
    horti_core_terms = ["원예", "과수", "화훼", "절화", "과채", "시설채소", "하우스", "비가림", "재배", "선별", "산지유통", "산지유통센터", "원예농협", "과수농협", "청과"]
    horti_core_hits = count_any(text, [t.lower() for t in horti_core_terms])

    # (강제 컷) 산업/금융/바이오 오탐: 농업/원예 맥락이 약하면 제외
    off_hits = count_any(text, [t.lower() for t in HARD_OFFTOPIC_TERMS])
    agri_ctx_hits = count_any(text, [t.lower() for t in ("농업", "농산물", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화")])
    if local_org_feature:
        agri_ctx_hits = max(agri_ctx_hits, 1)
    if key == "policy" and broad_macro_price:
        # Broad macro price watches still count as agri/policy context even with FX terms.
        agri_ctx_hits = max(agri_ctx_hits, 1)

    # (강제 컷) 전력/에너지/유틸리티 '도매시장/수급' 동음이의어 오탐 차단
    energy_hits = count_any(text, [t.lower() for t in ENERGY_CONTEXT_TERMS])

    # '도매시장'은 전력/금융 등에서도 흔히 등장하므로, 농산물 유통 디스앰비규에이터가 없으면 보수적으로 차단한다.
    has_wholesale_disambig = False
    if ("도매시장" in text) or (market_hits > 0):
        has_wholesale_disambig = any(t in text for t in AGRI_WHOLESALE_DISAMBIGUATORS)

    # 전력/에너지 문맥이 강한데(>=2) 농업/원예 문맥이 전무하면, '도매시장/수급' 단어가 있어도 비농산물로 판단
    # - 가격/수급/재고 같은 범용 단어로 horti_sc가 올라가도 통과하지 않도록, 점수 조건을 두지 않는다.
    if energy_hits >= 2 and market_hits > 0 and (not has_wholesale_disambig) and agri_ctx_hits == 0 and horti_core_hits == 0:
        return _reject("energy_market_offtopic")

    # dist에서 '도매시장'이 등장했는데 유통 디스앰비규에이터가 없으면(전력/금융 등 동음이의어 가능성),
    # 에너지 문맥이 조금이라도 있거나 농업 문맥이 없으면 차단한다.
    if key == "dist" and ("도매시장" in text) and (not has_wholesale_disambig):
        if (
            (energy_hits >= 1 or agri_ctx_hits == 0)
            and (not is_dist_export_field_context(ttl, desc, dom, press))
            and (not is_dist_market_ops_context(ttl, desc, dom, press))
        ):
            return _reject("dist_wholesale_ambiguous_no_agri")

    # supply에서도 '전력 수급/에너지 가격' 류는 '수급/가격' 단어로 오탐되므로 컷(보수적)
    if key == "supply" and energy_hits >= 2 and agri_ctx_hits == 0 and horti_core_hits == 0:
        return _reject("energy_supply_offtopic")

    if off_hits >= 2 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.6:
        if not (key == "dist" and is_dist_export_field_context(ttl, desc, dom, press)):
            return _reject("hard_offtopic_no_agri_context")

    # dist는 '선별/저온/유통' 같은 단어가 바이오/의과학 기사에도 등장해 누수가 잦다.
    # 오프토픽(바이오/의과학/플랫폼 등) 신호가 1개라도 있고 농업/시장 맥락이 없으면 강하게 컷한다.
    if key == "dist" and off_hits >= 1 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 2.2 and (not is_dist_export_field_context(ttl, desc, dom, press)):
        return _reject("dist_offtopic_no_agri_context")

    # 금융/산업 기사(농협은행/증권/주가/실적 등) 오탐 차단
    fin_hits = count_any(text, [t.lower() for t in FINANCE_STRICT_TERMS])
    if fin_hits >= 1 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.8:
        return _reject("finance_strict_no_agri_context")

    # 서울경제(sedaily) 등 경제지 일반 기사 오탐 방지:
    # - 경제/정책 섹션 검색 시 '농협/가격' 등의 단어로 비관련 기사가 섞이는 경우가 있어,
    #   원예/도매/정책 강신호가 없는 경우는 컷한다.
    if normalize_host(dom).endswith("sedaily.com"):
        if agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.8 and (not broad_macro_price) and (supply_feature_kind is None):
            return _reject("sedaily_no_agri_context")

    # news1 로컬(/local/) 기사 과다 유입 방지:
    # - 'APC' 같은 단어만으로는 지역 단신이 많이 유입되므로,
    #   도매/유통 인프라(선별/저온/저장/물류/준공/가동 등) 또는 도매시장 강신호가 함께 있을 때만 통과
    if normalize_host(dom).endswith("news1.kr") and ("/local/" in _path):
        # ✅ 자조금(특히 원예) 이슈는 지역기사라도 반드시 체크 대상: 인프라/도매 앵커가 약해도 통과
        if "자조금" in text and count_any(text, [t.lower() for t in ("원예","과수","화훼","과일","채소","청과","사과","배","감귤","딸기","고추","오이","포도")]) >= 1:
            return True
        infra_terms = ["준공", "완공", "가동", "확충", "확대", "선별", "저온", "저장", "ca저장", "물류", "통관", "검역", "수출", "원산지", "부정유통", "단속"]
        has_infra = any(t.lower() in text for t in infra_terms)
        has_wholesale = any(t in text for t in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "중도매인", "시장도매인", "온라인 도매시장"))
        has_apc = has_apc_agri_context(text) or ("산지유통" in text) or ("산지유통센터" in text)

        local_ok = (
            (market_hits >= 2)
            or (has_wholesale and horti_core_hits >= 2)
            or (has_apc and has_infra and horti_sc >= 1.6)
            or is_dist_market_ops_context(ttl, desc, dom, press)
            or is_dist_supply_management_center_context(ttl, desc)
            or is_dist_sales_channel_ops_context(ttl, desc)
        )
        if not local_ok:
            return _reject("news1_local_weak_context")

    # dist 섹션 정치/역사/사건 인터뷰성 기사 누수 방지(본문 일부 농업 언급으로 상단 유입되는 케이스 차단)
    # 예: '제주4.3/희생자/보상' 등 사건·정치성 인터뷰가 /society/ 경로로 들어오며
    #      본문에 '수급/APC/온라인 도매시장'이 한두 문장 섞여 dist 핵심으로 오르는 케이스를 차단.
    if key == "dist":
        # HARD BLOCK: 사건/역사(예: 제주4.3) 인터뷰/기사는 본문에 APC/수급 언급이 섞여도 dist에 노출하지 않는다.
        if any(t in ttl_l for t in ("제주4.3", "제주4·3", "4.3의", "4·3")):
            return _reject("dist_hardblock_jeju43")

        # 군(郡) 단위 지역 단신/행정 동정성 기사 억제:
        # - 제목에 ○○군/군청/군수 등 지방 행정 신호가 있고,
        # - 제목에 도매/유통 앵커가 없고,
        # - 본문에도 도매/유통 실무 신호가 약하면 dist에서 제외
        _countyish = (re.search(r"[가-힣]{2,}군", ttl) is not None) or ("군청" in ttl_l) or ("군수" in ttl_l)
        if _countyish:
            _title_dist_anchor = count_any(ttl_l, [t.lower() for t in (
                "도매시장", "공판장", "가락시장", "경락", "경매", "반입",
                "도매법인", "중도매", "시장도매인",
                "산지유통", "산지유통센터", "apc",
                "물류", "저온", "저장", "선별", "집하", "출하", "온라인 도매시장",
                "원산지", "부정유통", "단속", "검역", "통관", "수출"
            )])
            if (_title_dist_anchor == 0) and (market_hits == 0) and (not has_apc_agri_context(text)):
                return _reject("dist_county_local_weak_dist_signal")


        horti_title_sc = best_horti_score(ttl, "")

        # 제목 기반 앵커(도매/유통/농업) — 제목에 앵커가 없으면 '본문 일부 언급' 오탐 가능성이 높다.
        dist_anchor_in_title = count_any(ttl_l, [t.lower() for t in (
            "도매시장", "공판장", "가락시장", "경락", "경매", "반입",
            "도매법인", "중도매", "시장도매인",
            "산지유통", "산지유통센터", "apc",
            "원산지", "부정유통", "단속", "검역", "통관", "수출", "자조금"
        )])
        agri_anchor_in_title = count_any(ttl_l, [t.lower() for t in (
            "농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화", "청과",
            "사과", "배", "감귤", "딸기", "고추", "오이", "포도", "월동채소"
        )])

        # (강) 사건/정치/역사 이슈가 제목에 있으면, 본문에 시장 키워드가 섞여도 dist에서 제외(핵심/비핵심 모두 차단)
        # - '제주4.3' 같은 명백한 사건 키워드는 dist 핵심으로 절대 올리면 안 됨.
        hard_politics_terms = (
            "제주4.3", "제주4·3", "4.3의", "4·3", "희생자", "추모", "보상",
            "탄핵", "계엄", "내란", "참사", "특별법"
        )
        hard_hits = count_any(ttl_l, [t.lower() for t in hard_politics_terms])
        if hard_hits >= 1 and ("/society/" in _path or "/politics/" in _path or "/the300/" in _path):
            if dist_anchor_in_title == 0 and agri_anchor_in_title == 0:
                return _reject("dist_politics_hard_title")

        # (약) 정치/사건성 단어가 있고 제목 앵커가 매우 약하며 시장 맥락도 없으면 dist에서 제외
        politics_title_terms = (
            "4.3", "제주4.3", "희생자", "보상", "추모", "내란", "탄핵", "계엄", "정당", "총선", "대선", "국회",
            "검찰", "재판", "선고", "구속", "기소", "특별법", "사건", "참사"
        )
        politics_hits = count_any(ttl_l, [t.lower() for t in politics_title_terms])
        if politics_hits >= 1 and ("/society/" in _path or "/politics/" in _path or "/the300/" in _path):
            if dist_anchor_in_title == 0 and agri_anchor_in_title == 0 and horti_title_sc < 1.3 and market_hits == 0:
                return _reject("dist_politics_heavy_title")


    # 지역 동정/기금전달(특히 ○○농협 + 발전기금/장학금 등) 오탐 제거
    if _LOCAL_COOP_RX.search(text) and any(w.lower() in text for w in COMMUNITY_DONATION_TERMS):
        hard_ctx_terms = ["가락시장","도매시장","공판장","경락","경매","반입","중도매인","시장도매인","수출","검역","통관","원산지","단속","부정유통","수급","가격","시세","출하","재고","저장","선별","저온","물류"]
        hard_hits = count_any(text, [t.lower() for t in hard_ctx_terms])
        if hard_hits == 0 and horti_sc < 2.4:
            return _reject("local_coop_donation")

    # 정책 섹션만 정책기관/공공 도메인 허용(단, 방제(pest)는 지방 이슈가 많아 예외 허용)
    # ✅ (5) pest 섹션은 지자체/연구기관(.go.kr/.re.kr) 기사도 허용
    # 정책/기관 도메인은 다른 섹션에서 수집될 수 있으나, 최종적으로 policy 섹션으로 강제 라우팅한다.
    # 따라서 여기서 컷하지 않는다(누락 방지). 단, 일반 .go.kr/.re.kr은 노이즈가 많아 기존처럼 차단.
    if dom in POLICY_DOMAINS and key not in ("policy", "pest"):
        return True

    if (
        dom in ALLOWED_GO_KR
        or dom.endswith(".re.kr")
        or dom.endswith(".go.kr")
    ) and key not in ("policy", "pest"):
        return False

    # 섹션 must-term 통과 여부(단, supply/dist는 '강한 원예/도매 맥락'이면 예외 허용)
    if not section_must_terms_ok(text, section_conf["must_terms"]):
        if key == "policy":
            # 병해충 실행형 문맥은 policy 수집 단계에서 누락시키지 않는다(후단에서 pest로 이동).
            if is_pest_control_policy_context(text):
                pass
            elif policy_market_brief or policy_major_issue or macro_policy_like or broad_macro_price or is_supply_stabilization_policy_context(text, dom, press) or is_policy_export_support_brief_context(ttl, desc, dom, press):
                pass
            # policy는 도메인 override가 있음
            elif not policy_domain_override(dom, text):
                return _reject("must_terms_fail_policy")
        else:
            if key == "pest":
                pest_managed_count = int(_managed_commodity_match_summary(ttl, desc).get("count") or 0)
                pest_signal_hits = count_any(text, [t.lower() for t in PEST_STRICT_TERMS]) + count_any(text, [t.lower() for t in PEST_WEATHER_TERMS])
                if is_pest_story_focus_strong(ttl, desc) or (pest_managed_count >= 1 and pest_signal_hits >= 1):
                    pass
                else:
                    return _reject("must_terms_fail")
                # pest는 여기서 통과했으면 추가 must-term 컷을 적용하지 않는다.
                pass
            # supply/dist에서 APC/산지유통/화훼 현장성이 강하면 must_terms 미통과라도 살린다
            dist_soft_ok = (market_hits >= 1) or has_apc_agri_context(text) or ("산지유통센터" in text) or ("원예농협" in text) or ("화훼" in text) or ("절화" in text) or ("자조금" in text) or local_org_feature or is_horti_market_action_context(ttl, desc)
            if key == "supply" and supply_feature_kind is not None:
                dist_soft_ok = True
            if key == "dist":
                if (("유통" in text) or ("도매" in text) or ("출하" in text) or ("하역" in text) or ("물류" in text)) and (horti_sc >= 1.8 or agri_ctx_hits >= 1):
                    dist_soft_ok = True
                if is_dist_export_field_context(ttl, desc, dom, press):
                    dist_soft_ok = True
                if is_dist_field_market_response_context(ttl, desc, dom, press):
                    dist_soft_ok = True
            if key != "pest" and not ((horti_sc >= 2.0) or (horti_core_hits >= 3) or dist_soft_ok):
                return _reject("must_terms_fail")

    # (핵심) 원예수급 관련성 게이트:
    # - 네이버 검색 쿼리의 동음이의어(배=배터리/배당, 밤=야간 등)로 인한 오탐을 강하게 차단
    if key == "supply":
        # 공급(supply) 섹션은 '범용 단어(가격/물량/재고)'만 있는 산업/IT 기사를 강하게 차단한다.
        # 통과 조건(택1):
        # - 품목/원예 점수(horti_sc)가 충분히 강함
        # - 도매/산지유통/시장 맥락(market_hits) 존재
        # - 농업/농산물 맥락(agri_ctx_hits) + 수급 신호(signal_hits) 동시 존재
        supply_ok = (horti_sc >= 1.3) or (market_hits >= 1) or (agri_ctx_hits >= 1 and signal_hits >= 1) or (supply_feature_kind is not None)
        if is_policy_export_support_brief_context(ttl, desc, dom, press):
            return True
        if not supply_ok:
            return _reject("supply_context_gate")

        if policy_market_brief:
            return _reject("supply_policy_market_brief")

        title_supply_core_hits = count_any(ttl.lower(), [t.lower() for t in SUPPLY_TITLE_CORE_TERMS])
        if is_dist_export_shipping_context(ttl, desc) and (not has_direct_supply_chain_signal(text)) and market_hits == 0 and title_supply_core_hits == 0:
            return _reject("supply_dist_export_shipping")
        if is_dist_export_field_context(ttl, desc, dom, press) and (not has_direct_supply_chain_signal(text)) and market_hits == 0 and title_supply_core_hits == 0:
            return _reject("supply_dist_export_field")
        if is_dist_field_market_response_context(ttl, desc, dom, press) and (not has_direct_supply_chain_signal(text)) and market_hits == 0 and title_supply_core_hits == 0:
            return _reject("supply_dist_field_market_response")

        if broad_macro_price and (not has_direct_supply_chain_signal(text)):
            title_focus_hits = count_any(ttl.lower(), SUPPLY_TITLE_FOCUS_TERMS_L)
            if title_focus_hits < 2 and best_horti_score(ttl, "") < 2.0:
                return _reject("supply_macro_price_watch")

        # URL이 IT/테크 섹션인데 농업/시장 맥락이 약하면 컷(범용 단어 오탐 방지)
        if any(p in _path for p in ("/it/", "/tech/", "/future/", "/science/", "/game/", "/culture/")):
            if agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 2.2:
                return _reject("supply_tech_path_no_agri")

    # 정책(policy): 공식 도메인/정책브리핑이 아닌 경우 '농식품/농산물 맥락' 필수 + 경제/금융 정책 오탐 차단
    if key == "policy":
        # 수출/선적형 품목 유통 기사는 policy보다 dist가 자연스럽다.
        policy_anchor_stats = _policy_horti_anchor_stats(ttl, desc, dom, press)
        policy_anchor_ok = bool(policy_anchor_stats.get("anchor_ok"))
        policy_mixed_keep = ("농축산물" in text) and int(policy_anchor_stats.get("mixed_keep_hits") or 0) >= 2
        if is_policy_forest_admin_noise_context(ttl, desc):
            return _reject("policy_forest_admin_noise")
        if is_policy_budget_drive_noise_context(ttl, desc):
            return _reject("policy_budget_drive_noise")
        if policy_anchor_stats.get("livestock_dominant") and not policy_mixed_keep:
            return _reject("policy_livestock_only")
        if is_policy_local_price_support_context(ttl, desc):
            return True
        if is_dist_export_shipping_context(ttl, desc):
            return _reject("policy_dist_export_shipping")
        if is_dist_export_field_context(ttl, desc, dom, press):
            return _reject("policy_dist_export_field")
        if is_dist_market_disruption_context(ttl, desc):
            return _reject("policy_dist_market_disruption")
        if is_policy_general_macro_tail_context(ttl, desc, dom, press):
            return _reject("policy_macro_general_economy")
        regional_macro_title_hits = count_any(ttl.lower(), [w.lower() for w in ("부·울·경", "부울경", "긴급 대응", "빨간불", "민생 안정", "특별기간")])
        policy_anchor_hits = count_any(text, [w.lower() for w in ("농산물", "과일", "채소", "원예", "과수", "화훼", "도매시장", "공판장", "가락시장", "산지유통", "산지유통센터")])
        if regional_macro_title_hits >= 2 and policy_anchor_hits == 0 and best_horti_score(ttl, desc) < 1.4:
            return _reject("policy_regional_macro_noise")
        # 병해충 실행형 기사는 수집 단계에서 누락시키지 않고 후단 재분류/정리에서 pest로 보낸다.
        if is_pest_control_policy_context(text):
            return True
        if is_supply_stabilization_policy_context(text, dom, press):
            return True
        if policy_market_brief:
            return True
        if is_policy_export_support_brief_context(ttl, desc, dom, press):
            return True
        if policy_major_issue:
            return True

        is_official = policy_domain_override(dom, text) or (normalize_host(dom) in OFFICIAL_HOSTS) or any(normalize_host(dom).endswith("." + h) for h in OFFICIAL_HOSTS)

        if not is_official:
            # 소매 매출/판매 데이터 기반 트렌드 기사는 policy가 아니라 supply로 보내는 것이 자연스럽다
            if is_retail_sales_trend_context(text):
                return _reject("policy_retail_sales_trend")
            policy_signal_terms = ["가격 안정", "성수품", "할인지원", "할당관세", "검역", "원산지", "수입", "수출", "관세", "도매시장", "온라인 도매시장", "유통", "수급"]
            agri_base = count_any(text, [t.lower() for t in ("농식품", "농산물", "농업")])
            sig = count_any(text, [t.lower() for t in policy_signal_terms])
            if (not policy_market_brief) and (not policy_major_issue) and (not macro_policy_like) and (not broad_macro_price) and not (policy_anchor_ok or (agri_base >= 1 and sig >= 1)):
                return _reject("policy_context_gate")

        # 금융/산업 일반 정책 오탐 차단
        policy_off = ["금리", "주택", "부동산", "코스피", "코스닥", "주식", "채권", "가상자산", "원화", "환율", "반도체", "배터리"]
        if any(w in text for w in policy_off):
            if not (broad_macro_price or (horti_sc >= 1.8) or (market_hits >= 1) or ("농산물" in text and "가격" in text)):
                return _reject("policy_offtopic_gate")

        # 식품안전/위생 단독 이슈는 원예수급과 거리가 있어 제외
        # (단, 도매시장/원산지 단속/검역 등 '유통·단속'과 직접 결합되거나,
        #  품목/수급 신호가 매우 강할 때만 허용)
        safety_terms = ["식품안전", "위생", "haccp", "식중독", "표시기준", "유통기한", "알레르기"]
        if any(w in text for w in safety_terms):
            safety_ok = False
            if market_hits >= 2:
                safety_ok = True
            if (("원산지" in text) or ("부정유통" in text) or ("단속" in text) or ("검역" in text)) and market_hits >= 1:
                safety_ok = True
            if (horti_sc >= 2.6) and ("농산물" in text) and (("가격" in text) or ("수급" in text) or ("출하" in text)):
                safety_ok = True
            if not safety_ok:
                return _reject("policy_food_safety_only")
            # 영농부산물/파쇄 등 행정성 사업 안내는 원예수급 브리핑에서 제외(정 없을 때도 굳이 채우지 않음)
            admin_terms = ["영농부산물", "안전처리", "파쇄", "파쇄기", "소각", "잔가지"]
            if any(w in text for w in admin_terms):
                if market_hits == 0 and horti_sc < 2.2:
                    return _reject("policy_admin_notice")


        # 정책 섹션: 지방 행사성/지역 단신을 강하게 배제(주요 매체는 일부 허용)
        is_major = press_priority(press, dom) >= 2
        if (not is_major) and _LOCAL_GEO_PATTERN.search(ttl):
            return _reject("policy_local_minor")

    # 유통/현장(dist): '농산물/원예 유통' 맥락이 없는 일반 물류/유통/브랜드 기사는 강하게 차단
    if key == "dist":
        agri_anchor_terms = ("농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화", "청과")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])
        if is_dist_political_visit_context(ttl, desc):
            return _reject("dist_political_visit")
        if is_local_agri_infra_designation_context(ttl, desc):
            return _reject("dist_local_infra_designation")
        if is_dist_local_crop_strategy_noise_context(ttl, desc):
            return _reject("dist_local_crop_strategy")

        # 소프트/하드 신호 분리(일반어: 브랜드/통합/조화/꽃 등은 제거)
        dist_soft = ["산지유통", "산지유통센터", "원예농협", "과수농협", "판매농협", "작목반", "화훼", "절화", "자조금", "하나로마트", "온라인 도매시장", "유통", "도매", "도매법인", "하역", "하역비", "하역대란", "출하", "집하", "물류센터"]
        dist_hard = ["가락시장", "도매시장", "공판장", "공영도매시장", "청과", "경락", "경락가", "경매", "반입",
                     "도매법인", "하역", "하역비", "하역대란", "출하",
                     "중도매인", "시장도매인",
                     "선별", "저온", "저온저장", "저장고", "ca저장", "물류",
                     "원산지", "부정유통", "단속",
                     "검역", "통관", "수출"]
        soft_hits = count_any(text, [t.lower() for t in dist_soft])
        hard_hits = count_any(text, [t.lower() for t in dist_hard])

        # APC는 농업 문맥일 때만 soft 신호로 카운트
        apc_ctx = has_apc_agri_context(text)
        dist_export_shipping = is_dist_export_shipping_context(ttl, desc)
        dist_export_field = is_dist_export_field_context(ttl, desc, dom, press)
        dist_export_support_hub = is_dist_export_support_hub_context(title, desc, dom, press)
        dist_field_market_response = is_dist_field_market_response_context(ttl, desc, dom, press)
        dist_local_field_profile = is_dist_local_field_profile_context(title, desc)
        dist_local_org_tail = is_dist_local_org_tail_context(title, desc)
        if dist_local_org_tail:
            return _reject("dist_local_org_profile")
        if is_dist_macro_export_noise_context(title, desc, dom, press):
            return _reject("dist_macro_export_noise")
        if is_dist_campaign_noise_context(title, desc):
            return _reject("dist_campaign_noise")
        if dist_export_support_hub:
            return True
        if apc_ctx:
            soft_hits += 1
        if local_org_feature and not dist_local_org_tail:
            soft_hits += 1
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if dist_local_field_profile:
            soft_hits = max(soft_hits, 2)
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if is_dist_supply_management_center_context(title, desc):
            soft_hits = max(soft_hits, 2)
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if is_dist_sales_channel_ops_context(title, desc):
            soft_hits = max(soft_hits, 2)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if dist_export_shipping:
            soft_hits = max(soft_hits, 1)
            hard_hits = max(hard_hits, 2)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if dist_export_field:
            soft_hits = max(soft_hits, 1)
            hard_hits = max(hard_hits, 2)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if dist_export_support_hub:
            soft_hits = max(soft_hits, 2)
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if dist_field_market_response:
            soft_hits = max(soft_hits, 2)
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)

        # 농산물 시장 이전/현대화/재배치 성격 기사는 유통·현장으로 허용
        relocation_hint = any(w in text for w in ("이전", "옮긴", "이전지", "현대화", "재배치", "신설", "개장", "개소"))
        agri_market_relocation = ("농산물" in text and "시장" in text and relocation_hint)

        if (soft_hits + hard_hits) < 1 and (not agri_market_relocation):
            return _reject("dist_context_gate")

        # ✅ 가장 중요한 원칙: '농산물/원예' 앵커가 없고(agri_anchor_hits==0),
        # 도매시장/산지유통/품목 점수도 약하면 일반 물류/경제 기사로 보고 컷
        if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 1.6 and (not local_org_feature):
            return _reject("dist_no_agri_anchor")

        # 수출/검역/원산지 단속 등 '운영/집행' 키워드만으로 걸린 일반 기사 차단
        dist_ops_terms = ["원산지", "부정유통", "단속", "검역", "통관", "수출"]
        dist_market_terms = ["가락시장", "도매시장", "공판장", "공영도매시장", "청과", "경락", "경매", "반입",
                             "중도매인", "시장도매인", "온라인 도매시장", "산지유통", "산지유통센터"]
        ops_hits = count_any(text, [t.lower() for t in dist_ops_terms])
        title_market_hits = count_any(ttl.lower(), [t.lower() for t in dist_market_terms])
        title_ops_hits = count_any(ttl.lower(), [t.lower() for t in dist_ops_terms])

        if (ops_hits >= 1 and hard_hits >= 1 and market_hits == 0 and (not apc_ctx)
                and agri_anchor_hits == 0 and horti_sc < 1.9 and title_market_hits == 0 and (not local_org_feature)):
            return _reject("dist_ops_only_generic")

        # 방송/종합지 지역단신이 dist로 유입되는 경우 추가 차단(실제 도매/APC/수출 현장 신호가 약할 때)
        if ((press or "").strip() in BROADCAST_PRESS and _LOCAL_GEO_PATTERN.search(ttl)):
            if market_hits == 0 and (not apc_ctx) and horti_sc < 2.1 and title_market_hits == 0 and title_ops_hits <= 1:
                return _reject("dist_local_broadcast_weak")

        # URL이 IT/테크 섹션인데 농업 맥락이 약하면 컷
        if any(p in _path for p in ("/it/", "/tech/", "/future/", "/science/", "/game/", "/culture/")):
            if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 2.2:
                return _reject("dist_tech_path_no_agri")

        # '산지유통/APC/농협/화훼' 같은 소프트 신호만 있을 땐,
        # 인프라/유통 강신호(준공/가동/선별/저온/저장/물류/원산지/검역/수출 등) + 농업 앵커/품목 신호가 함께 있어야 통과
        if hard_hits == 0:
            infra_terms = ["준공", "완공", "가동", "확충", "확대", "선별", "저온", "저온저장", "저장고", "ca저장", "물류", "원산지", "검역", "수출"]
            has_infra = any(w in text for w in infra_terms)

            # soft-only는 (인프라 + (농업앵커 or 품목점수)) 또는 (품목점수 매우 강함 + soft 2개 이상)에서만 허용
            if not (
                local_org_feature
                or is_dist_sales_channel_ops_context(title, desc)
                or dist_field_market_response
                or (has_infra and (agri_anchor_hits >= 1 or horti_sc >= 1.9 or apc_ctx))
                or (horti_sc >= 2.8 and soft_hits >= 2)
            ):
                return _reject("dist_soft_without_infra")
# 병해충/방제(pest) 섹션 정교화: 농업 맥락 없는 방역/생활해충/벼 방제 오탐 제거 + 신호 강도 조건
    if key == "pest":
        if is_pest_input_marketing_noise_context(ttl, desc):
            return _reject("pest_input_marketing_noise")
        managed_count = int(_managed_commodity_match_summary(ttl, desc).get("count") or 0)
        agri_ctx_hits = count_any(text, [t.lower() for t in PEST_AGRI_CONTEXT_TERMS]) + managed_count
        if agri_ctx_hits < 1:
            return _reject("pest_no_agri_context")

        rice_hits = count_any(text, [t.lower() for t in PEST_RICE_TERMS])
        strict_hits = count_any(text, [t.lower() for t in PEST_STRICT_TERMS])
        weather_hits = count_any(text, [t.lower() for t in PEST_WEATHER_TERMS])
        horti_hits = count_any(text, [t.lower() for t in PEST_HORTI_TERMS]) + managed_count

        # 벼 병해충은 원예수급부와 거리가 멀어 기본 제외(원예 신호 동반 시만 허용)
        if rice_hits >= 1 and horti_hits == 0:
            return _reject("pest_rice_only")

        # 방제/병해충 신호가 너무 약하면 제외
        if (strict_hits + weather_hits) < 1:
            return _reject("pest_weak_signal")
        if not is_pest_story_focus_strong(ttl, desc):
            return _reject("pest_partial_mention")

    return True

def compute_rank_score(title: str, desc: str, dom: str, pub_dt_kst: datetime, section_conf: JsonDict, press: str) -> float:
    """중요도 스코어.
    목표:
    - 원예수급(과수/화훼/시설채소) 실무에 직접 영향을 주는 의사결정 신호(가격/물량/대책/검역/방제)를 최우선
    - 언론매체 가중치: 공식(정책/기관) > 중앙·일간·경제·방송·농민신문 > 중소/지방 > 인터넷
    - 농협(경제지주/공판장/하나로/온라인도매) 관련성 반영
    - 지방 방제/협의회/행사성 기사 상단 배치 억제 + 중복 이슈 억제
    """
    text = (title + " " + desc).lower()
    title_l = (title or "").lower()

    # (핵심) 원예수급/품목 신호 점수(품목 라벨 + 오탐 억제)
    horti_sc = best_horti_score(title, desc)
    horti_title_sc = best_horti_score(title, "")
    key_strength = keyword_strength(text, section_conf) if SCORING_KEYWORD_STRENGTH_BOOST_ENABLED else 0
    market_ctx_terms = ["가락시장", "도매시장", "공판장", "청과", "경락", "경락가", "반입", "온라인도매시장", "온라인 도매시장", "산지유통", "산지유통센터"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1
    macro_policy_like = is_macro_policy_issue(text)
    broad_macro_price = is_broad_macro_price_context(title, desc)
    local_org_feature = is_local_agri_org_feature_context(title, desc)
    dist_local_field_profile = is_dist_local_field_profile_context(title, desc)
    dist_local_org_tail = is_dist_local_org_tail_context(title, desc)
    infra_designation = is_local_agri_infra_designation_context(title, desc)
    dist_supply_center = is_dist_supply_management_center_context(title, desc)
    dist_sales_channel_ops = is_dist_sales_channel_ops_context(title, desc)
    dist_field_market_response = is_dist_field_market_response_context(title, desc, dom, press)
    direct_supply_story = has_direct_supply_chain_signal(text)
    supply_feature_kind = supply_feature_context_kind(title, desc)
    supply_issue_bucket = supply_issue_context_bucket(title, desc)
    dist_market_disruption = is_dist_market_disruption_context(title, desc)
    dist_disruption_scope = dist_market_disruption_scope(title, desc)
    dist_market_ops = is_dist_market_ops_context(title, desc, dom, press)
    policy_stabilization = is_supply_stabilization_policy_context(text, dom, press)
    policy_market_brief = is_policy_market_brief_context(text, dom, press)
    policy_major_issue = is_policy_major_issue_context(title, desc, dom, press)
    policy_price_collapse_issue = is_policy_price_collapse_issue_context(title, desc)
    policy_general_macro_tail = is_policy_general_macro_tail_context(title, desc, dom, press)
    policy_event_tail = is_policy_event_tail_context(title, desc, dom, press)
    dist_export_field = is_dist_export_field_context(title, desc, dom, press)
    policy_export_support_brief = is_policy_export_support_brief_context(title, desc, dom, press)
    managed_summary = _managed_commodity_match_summary(title, desc)
    managed_count = int(managed_summary.get("count") or 0)
    program_core_count = int(managed_summary.get("program_core_count") or 0)

    strength = agri_strength_score(text)
    korea = korea_context_score(text)
    offp = off_topic_penalty(text)

    # 기본: 강신호(원예수급/유통/정책/방제) 기반
    score = 0.0
    score += 0.55 * strength
    score += 0.25 * korea
    score -= 0.70 * offp
    if SCORING_TITLE_SIGNAL_BONUS_ENABLED:
        score += title_signal_bonus(title)



    # trade_policy_core_boost: 품목(토픽) + 무역/정책(관세/FTA/통관/수입) + 영향(수급/가격/잠식 등) 조합이면 핵심성 가산
    trade_terms = ("관세", "할당관세", "무관세", "fta", "통관", "보세", "수입", "검역")
    impact_terms = ("수급", "가격", "물량", "잠식", "경쟁", "타격", "부추", "압박", "급등", "급락")
    if any(x in text for x in trade_terms) and any(x in text for x in impact_terms):
        if any(_term in text for _tn,_terms in TOPICS for _term in _terms[:3]):
            score += 1.6
    # 지방 "인구감소/생활인구" 예산 기사(원예 키워드가 섞여도 핵심성 낮음) 감점
    if ("인구감소" in text) or ("생활인구" in text):
        score -= 6.0
    # "오늘, 서울시"류 알림성 기사 감점
    if ("오늘, 서울시" in title_l) or ("서울청년문화패스" in title_l):
        score -= 1.8

    # -----------------------------
    # Generalized boost: '원예 품목 신호' + '무역/정책(관세/무관세/FTA/수입/통관/검역 등)' + '시장 영향' 조합
    # 특정 기사 하나를 위해 키워드를 추가하는 방식이 아니라,
    # 전반적으로 "수입/관세 이슈가 품목 수급에 미치는 영향" 기사들을 더 잘 끌어올리기 위한 규칙이다.
    horti_hits = count_any(text, HORTI_ITEM_TERMS_L)
    trade_hits = count_any(text, TRADE_POLICY_TERMS_L)
    impact_hits = count_any(text, TRADE_IMPACT_TERMS_L)

    if horti_hits > 0 and trade_hits > 0:
        score += 1.6 + min(1.2, 0.35 * trade_hits)
        if impact_hits > 0:
            score += 1.0

    # 섹션별 키워드 가중치
    key = section_conf["key"]

    # 섹션 must_terms를 점수에 소폭 반영(제목 히트 우선)해 섹션 적합도를 안정화
    must_terms_l = _section_must_terms_lower(section_conf)
    if must_terms_l:
        must_title_hits = count_any(title_l, must_terms_l)
        must_text_hits = count_any(text, must_terms_l)
        score += min(1.8, (0.35 * must_title_hits) + (0.12 * must_text_hits))

    if key == "supply":
        score += weighted_hits(text, SUPPLY_WEIGHT_MAP)
        score += min(2.2, 0.25 * key_strength)
        score += count_any(title_l, [t.lower() for t in SUPPLY_TITLE_CORE_TERMS]) * 1.2
        if is_supply_price_outlook_context(title, desc):
            score += 2.3
        if supply_feature_kind == "issue":
            score += 2.8
            if supply_issue_bucket == "export_recovery":
                score += 1.9
            elif supply_issue_bucket == "farm_action":
                score += 0.7
            elif supply_issue_bucket == "commodity_issue":
                score += 1.4
                shock_hits = count_any(text, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_INPUT_TERMS]) + count_any(text, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_CLIMATE_TERMS])
                if shock_hits >= 2:
                    score += 0.9
            if horti_title_sc >= 1.4:
                score += 0.6
        elif supply_feature_kind == "field":
            score += 2.4
            if horti_title_sc >= 1.8:
                score += 0.9
        elif supply_feature_kind == "quality":
            score += 2.1
            if horti_title_sc >= 1.8:
                score += 0.6
        elif supply_feature_kind == "promo":
            score += 1.8
            if horti_title_sc >= 1.4:
                score += 0.5
        # 지자체 정책 프로그램(출하비용 보전/시범사업 등)은 supply보다 policy 성격이 강함
        if is_local_agri_policy_program_context(text):
            score -= 4.0
        if policy_stabilization:
            score -= 5.4
        if policy_market_brief:
            score -= 6.2
        if local_org_feature:
            score -= 4.8
        if dist_market_ops:
            score -= 4.2
        if dist_supply_center:
            score -= 4.4
        if dist_sales_channel_ops:
            score -= 4.8
        if dist_field_market_response:
            score -= 9.0
        if is_dist_export_shipping_context(title, desc) and supply_issue_bucket != "export_recovery":
            score -= 5.0
        if dist_export_field and supply_issue_bucket != "export_recovery":
            score -= 4.6
        if dist_market_disruption:
            score -= 4.6
        if is_supply_weak_tail_context(title, desc):
            score -= 5.6
        if is_agri_training_recruitment_context(title, desc):
            score -= 8.2
        if is_agri_org_rename_context(title, desc):
            score -= 7.0
        if is_title_livestock_dominant_context(title, desc):
            score -= 9.0
        if broad_macro_price and ((not direct_supply_story) or policy_market_brief):
            score -= 5.0
        if macro_policy_like and count_any(title_l, [t.lower() for t in ("과일", "과수", "채소", "화훼", "농산물", "청과")]) == 0 and horti_title_sc < 1.6 and horti_sc < 1.8 and ((not direct_supply_story) or policy_market_brief):
            score -= 4.2
        if managed_count:
            score += min(2.0, 0.34 * managed_count)
            score += min(2.2, 1.05 * program_core_count)
    elif key == "dist":
        score += weighted_hits(text, DIST_WEIGHT_MAP)
        score += min(2.0, 0.22 * key_strength)
        score += count_any(title_l, [t.lower() for t in DIST_TITLE_CORE_TERMS]) * 1.2
        if is_dist_political_visit_context(title, desc):
            score -= 10.0
        if is_local_agri_infra_designation_context(title, desc):
            score -= 8.0
        if is_dist_local_crop_strategy_noise_context(title, desc):
            score -= 7.2
        # 지자체 정책 프로그램성 기사(보전/지원/시범사업)는 dist보다 policy 우선
        if is_local_agri_policy_program_context(text):
            score -= 2.0
        # ✅ 농업 전문/현장 매체의 '시장 현장/대목장' 리포트는 유통(현장) 실무 체크 가치가 높다.
        # - 도매시장/APC 키워드가 없어도 '현장/대목장/판매' 맥락이면 점수를 보강해 하단 고착을 방지한다.
        if press in AGRI_TRADE_PRESS or normalize_host(dom) in AGRI_TRADE_HOSTS:
            if has_any(title_l, ["대목장", "대목", "현장", "어땠나", "판매", "시장", "반응"]):
                score += 3.2

        # dist에서 '지자체 공지/지역 단신'으로 판정되면 점수 감점(후순위/빈칸메우기용)
        if is_local_brief_text(title, desc, "dist"):
            score -= 3.5
        if dist_local_org_tail:
            score -= 6.2
        if is_dist_macro_export_noise_context(title, desc, dom, press):
            score -= 8.4
        if is_dist_campaign_noise_context(title, desc):
            score -= 7.2
        elif dist_local_field_profile:
            score += 2.2
        if dist_market_ops:
            score += 8.8
        if dist_supply_center:
            score += 7.2
        if dist_sales_channel_ops:
            score += 7.6
            if managed_count:
                score += min(1.4, 0.35 * managed_count)
            if ("연합판매사업" in text) and ("직거래" in text):
                score += 3.2
        if dist_field_market_response:
            score += 8.8
            if managed_count:
                score += min(1.2, 0.30 * managed_count)
        elif local_org_feature:
            score += 0.6
        if is_dist_export_shipping_context(title, desc):
            score += 4.4
        if dist_export_field:
            score += 4.0
            export_resolution_hits = count_any(
                text,
                [t.lower() for t in ("비관세장벽", "애로", "애로 해결", "간담회", "현장간담회", "원스톱", "n-데스크", "n desk", "상시 애로")],
            )
            if export_resolution_hits >= 2 and horti_sc >= 1.2:
                score += 3.2
        if is_dist_export_support_hub_context(title, desc, dom, press):
            score += 5.6
        if dist_market_disruption:
            score += 4.8
        if infra_designation:
            score -= 3.0
        if managed_count and (market_hits >= 1 or dist_market_ops or dist_supply_center or dist_sales_channel_ops or dist_field_market_response or dist_export_field or dist_market_disruption):
            score += min(1.2, 0.22 * managed_count)
            score += min(0.9, 0.42 * program_core_count)
    elif key == "policy":
        score += weighted_hits(text, POLICY_WEIGHT_MAP)
        score += min(1.8, 0.20 * key_strength)
        score += count_any(title_l, [t.lower() for t in POLICY_TITLE_CORE_TERMS]) * 1.2
        if is_title_livestock_dominant_context(title, desc):
            score -= 10.0
        if is_policy_forest_admin_noise_context(title, desc):
            score -= 8.6
        if is_policy_budget_drive_noise_context(title, desc):
            score -= 7.8
        if policy_major_issue:
            score += 5.8
            score += 0.9 * count_any(title_l, [t.lower() for t in _POLICY_MAJOR_ISSUE_TITLE_TERMS])
        if policy_price_collapse_issue:
            score += 2.8
        if dist_market_disruption:
            score -= 7.0
        if dist_market_ops:
            score -= 8.0
        if dist_supply_center:
            score -= 10.0
        if dist_sales_channel_ops:
            score -= 9.0
        if dist_field_market_response:
            score -= 7.4
        if dist_export_field:
            score -= 5.8
        # 도매시장/농산물시장 인프라 이전 이슈는 정책보다 유통 성격이 더 강하므로 policy 감점
        if ("농산물" in text and "시장" in text) and any(w in text for w in ("이전", "옮긴", "이전지", "현대화", "재배치", "신설", "개장", "개소")):
            score -= 2.8
        # 지자체의 농산물 정책 프로그램(지원/보전/시범사업)은 policy 우선
        if is_local_agri_policy_program_context(text):
            score += 6.4
        if is_policy_local_price_support_context(title, desc):
            score += 4.8
        if policy_stabilization:
            score += 5.4
        if policy_market_brief:
            score += 4.8
        if policy_export_support_brief:
            score += 10.0
        # 공식 정책 소스 추가 가점
        if normalize_host(dom) in OFFICIAL_HOSTS or press in ("농식품부", "정책브리핑"):
            score += 3.0
        if macro_policy_like:
            score += 4.2
        if broad_macro_price:
            score += 2.4
        if policy_general_macro_tail:
            score -= 6.4
        if policy_event_tail:
            score -= 8.4
        if managed_count and (macro_policy_like or policy_stabilization or policy_market_brief or policy_major_issue or policy_export_support_brief):
            score += min(1.2, 0.22 * managed_count)
            score += min(1.0, 0.45 * program_core_count)
    elif key == "pest":
        score += weighted_hits(text, PEST_WEIGHT_MAP)
        score += min(1.8, 0.22 * key_strength)
        if is_pest_input_marketing_noise_context(title, desc):
            score -= 9.0
        pest_title_hits = _pest_title_signal_count(title_l)
        score += pest_title_hits * 1.1
        if pest_title_hits == 0:
            score -= 3.4
        # 지자체 발표 기사라도 방제 실행(예찰/약제/살포/전수조사) 맥락이 강하면 pest 우선
        if is_pest_control_policy_context(text):
            score += 2.8

        # 과수화상병/탄저병/냉해/동해 등 과수 리스크는 최우선(과수화훼팀 관점)
        if "과수화상병" in text:
            score += 6.0
        if "탄저병" in text:
            score += 3.0
        if any(w in text for w in ("냉해", "동해", "저온피해", "서리")):
            score += 2.4

        # 수필/일기/연재/칼럼성(개인 에세이) + 정치/외교 제목은 pest 핵심성에서 멀어 감점
        # - 본문에 병해충 사례가 있더라도 '핵심2'로 올라가지 않도록 점수도 함께 낮춘다.
        narrative_terms = ("일기", "농막일기", "수필", "에세이", "연재", "칼럼", "오피니언", "기고")
        if any(w in text for w in narrative_terms) or any(w in title_l for w in narrative_terms):
            score -= 3.8

        foreign_politics = ("트럼프", "바이든", "푸틴", "시진핑", "백악관", "미국 대통령")
        if any(w in title_l for w in foreign_politics):
            # 제목이 정치/외교이고 방제 신호가 제목에서 드러나지 않으면 추가 감점
            if count_any(title_l, [t.lower() for t in PEST_STRICT_TERMS]) == 0 and count_any(title_l, [t.lower() for t in PEST_WEATHER_TERMS]) == 0:
                score -= 4.2
        # 양곡(벼) 방제는 제외: 남아있더라도 강하게 감점
        rice_hits = count_any(text, [t.lower() for t in PEST_RICE_TERMS])
        horti_hits = count_any(text, [t.lower() for t in PEST_HORTI_TERMS])
        if rice_hits >= 1 and horti_hits == 0:
            title_pest_hits = count_any(title_l, [t.lower() for t in ("병해충", "방제", "예찰", "약제", "과수화상병", "탄저병")])
            # 벼 기사라도 병해충/방제가 제목·본문에서 명확하면 완전 배제하지 않고 보수 감점
            score -= 2.6 if title_pest_hits >= 1 else 7.0
        if managed_count:
            score += min(1.4, 0.24 * managed_count)
            score += min(1.2, 0.65 * program_core_count)

    # 언론/기관 가중치
    score += press_weight(press, dom)

    # ✅ dist(유통/현장): 전문 매체(농업/유통) 실무 신호를 더 반영하고, 통신(연합뉴스)이 상단을 과도하게 잠식하는 경우를 억제
    if key == "dist":
        wholesale_hits = count_any(text, [t.lower() for t in WHOLESALE_MARKET_TERMS])
        apc_ctx = has_apc_agri_context(text)
        dist_anchor = market_hits + wholesale_hits + (1 if apc_ctx else 0)
        if dist_disruption_scope == "systemic":
            score += 12.0
        elif dist_disruption_scope == "market_disruption":
            score += 4.2
        elif dist_disruption_scope == "commodity_aftershock":
            score -= 1.0
        # APC/산지유통 인프라 기사(준공/가동/선별/저장)는 dist 실무 가치가 높아 소폭 가점
        if apc_ctx and any(w in text for w in ("준공", "완공", "개장", "개소", "가동", "선별", "선과", "저온", "저온저장", "저장고", "ca저장")):
            score += 1.4
            if (press or "").strip() in AGRI_TRADE_PRESS or normalize_host(dom) in AGRI_TRADE_HOSTS:
                score += 0.6    # 연합뉴스는 범용 기사량이 많아 dist 상단을 잠식하기 쉬움: 기본 감점 + 앵커 약하면 추가 감점
        if (press or "").strip() == "연합뉴스":
            score -= 1.8
            if dist_anchor < 2:
                score -= 1.4
        # 농업 전문/현장 매체는 '도매/현장' 정보 가치가 높아 추가 가점
        if (press or "").strip() in AGRI_TRADE_PRESS or normalize_host(dom) in AGRI_TRADE_HOSTS:
            if dist_anchor >= 1:
                score += 2.2
            if any(w in title_l for w in ("가락시장", "도매시장", "공판장", "경락", "경매", "반입", "산지유통", "산지유통센터", "apc", "수출", "검역", "통관")):
                score += 1.0

        # 도매시장/농산물시장 인프라·이전·현대화 이슈는 유통·현장 섹션 우선
        relocation_terms = ("이전", "옮긴", "이전지", "현대화", "재배치", "확장", "신설", "개장", "개소")
        if any(w in text for w in ("도매시장", "공영도매시장", "공판장")):
            if any(w in text for w in relocation_terms):
                score += 2.4
            if any(w in title_l for w in relocation_terms):
                score += 1.2
        # '농산물 시장 이전'처럼 도매시장 단어가 없더라도 유통 인프라 재편 맥락을 반영
        if ("농산물" in text and "시장" in text) and any(w in text for w in relocation_terms):
            score += 3.4
            if any(w in title_l for w in relocation_terms):
                score += 1.4

    # ✅ 중앙지/방송사(티어3) 추가 가점: 공신력/파급력 높은 이슈를 상단에 더 잘 반영
    _pt = press_tier(press, dom)
    if _pt == 3:
        score += 0.9
        if (press or '').strip() in BROADCAST_PRESS:
            score += 0.4

    # 도메인 품질 패널티
    score -= low_quality_domain_penalty(dom)

    # ✅ 자조금(특히 원예) 이슈는 실무 체크 우선: dist/policy 우선 가점
    if "자조금" in text:
        # 원예/과수/화훼/청과 맥락이 있으면 강하게 가점(축산 자조금은 is_relevant에서 배제됨)
        if any(w in text for w in ("원예","과수","화훼","절화","과일","채소","청과","사과","배","감귤","딸기","고추","오이","포도")) or horti_sc >= 1.4:
            if key in ("dist", "policy"):
                score += 2.6
                # 제목에 자조금이 명시된 이슈는 체크 우선(핵심성 가점)
                if "자조금" in title_l:
                    score += 1.6
            elif key == "supply":
                score += 2.0
            else:
                score += 1.2

    # ✅ 소비자 물가/장바구니류(농산물 일부 언급) 기사: 참고용으로는 두되 핵심에서 밀리도록 감점
    consumer_price_terms = ("장바구니", "밥상", "물가", "소비자물가", "외식물가", "대형마트", "마트", "할인행사")
    if any(w in text for w in consumer_price_terms):
        if market_hits == 0 and horti_sc < 2.2 and key in ("supply", "dist"):
            score -= 2.4

    # ✅ 스포츠동아(지역 단신/캠페인)류는 하단 배치(필요시만 백필로 노출)
    if ("sports.donga.com" in dom) or (press == "스포츠동아"):
        if market_hits == 0 and horti_sc < 2.4:
            score -= 3.4
        else:
            score -= 1.4

    # ✅ dist에서 군(郡) 단위 지역 단신/행정 동정성 기사 추가 억제(News1 자조금 같은 핵심 이슈가 아래로 밀리는 것을 방지)
    if key == "dist":
        if (re.search(r"[가-힣]{2,}군", title) is not None) or ("군청" in title_l) or ("군수" in title_l):
            if market_hits == 0 and (not has_apc_agri_context(text)):
                score -= 5.0

    # ✅ dist에서 '지역 단신/지자체 공지형' 기사(시·군·구 + 지원/추진/협약/모집...)는
    # - 후보가 적은 날 상단(핵심2)로 올라와 진짜 체크해야 할 이슈(예: 원예 자조금)를 밀어내는 문제가 있어
    #   점수 단계에서 미세하게 더 감점한다. (선택 단계에서도 2개 이상 채워졌으면 추가 제외)
    if key == "dist" and is_local_brief_text(title, desc, key):
        score -= 4.2

    # 농협(경제지주/공판장 등) 관련성 가점
    score += nh_boost(text, key)

    # 행사/동정성 패널티(실무 신호 약하면 감점)
    event_pen = eventy_penalty(text, title, key)
    if key == "dist" and dist_local_field_profile:
        event_pen = min(event_pen, 0.8)
    if key == "dist" and dist_market_ops:
        event_pen = min(event_pen, 0.5)
    if key == "dist" and (dist_supply_center or dist_sales_channel_ops):
        event_pen = min(event_pen, 0.5)
    score -= event_pen

    # 행정/정치 인터뷰성(도지사/시장 등) 기사 상단 배치 억제
    score -= governance_interview_penalty(text, title, key, horti_sc, market_hits)

    # 지역 단위 농협 동정성 기사 패널티(특히 농민신문 지역농협 소식 과다 방지)
    local_coop_pen = local_coop_penalty(text, press, dom, key)
    if key == "dist" and dist_local_field_profile:
        local_coop_pen = min(local_coop_pen, 0.4)
    if key == "dist" and (dist_supply_center or dist_sales_channel_ops):
        local_coop_pen = min(local_coop_pen, 0.4)
    score -= local_coop_pen
    # '영농부산물/안전처리/파쇄' 등 사업설명·행정성 정책은 하단 배치(정 없을 때만)
    if any(w in text for w in ("영농부산물", "안전처리", "파쇄", "파쇄기", "소각", "잔가지")):
        if market_hits == 0 and horti_sc < 2.0:
            score -= 3.5

    # 식품안전/위생 단독 이슈는 원예수급 핵심에서 멀어 감점(도매시장/품목 신호가 있으면 유지)
    if any(w in text for w in ("식품안전", "위생", "haccp", "식중독")):
        if market_hits == 0 and horti_sc < 1.8 and count_any(text, [t.lower() for t in ("농산물", "원산지", "검역", "도매시장")]) < 1:
            score -= 3.0

    # 최신성: 48시간 내 기사 보정(너무 과도하지 않게)
    try:
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        age_h = (now_kst - pub_dt_kst).total_seconds() / 3600.0
        if age_h <= 8:
            score += 0.8
        elif age_h <= 24:
            score += 0.4
        elif age_h <= 48:
            score += 0.2
    except Exception:
        pass

    # supply 섹션: 외식/뷔페/프랜차이즈 '딸기축제' 류는 소비 이벤트 성격이 강해 핵심 신호에서 감점
    if section_conf.get("key") == "supply" and is_fruit_foodservice_event_context(text):
        score -= 2.8

    # 전 섹션: 패스트푸드 가격 기사 방어(필터를 통과하더라도 점수 하락)
    if is_fastfood_price_context(text):
        score -= 6.0

    return round(score, 3)
def _token_set(s: str) -> set[str]:
    s = (s or "").lower()
    toks = re.findall(r"[0-9a-z가-힣]{2,}", s)
    return {t for t in toks if t not in ("기사", "뉴스", "농산물", "농업", "정부", "지자체")}


# --- Near-duplicate suppression (특히 지방 방제/협의회 기사 중복 방지) ---
# ✅ Region detection (conservative) — avoid false positives like '당도/가격도/수급도/출하도'
_PROVINCE_NAMES = [
    "서울특별시","부산광역시","대구광역시","인천광역시","광주광역시","대전광역시","울산광역시","세종특별자치시",
    "경기도","강원특별자치도","충청북도","충청남도","전라북도","전라남도","경상북도","경상남도","제주특별자치도",
]
_PROVINCE_ALIAS_NAMES = [
    "서울시","부산시","대구시","인천시","광주시","대전시","울산시","세종시",
    "강원도","강원자치도","충북도","충남도","전북도","전남도","경북도","경남도","제주도",
]
_PROVINCE_RX = re.compile("|".join(map(re.escape, sorted(set(_PROVINCE_NAMES + _PROVINCE_ALIAS_NAMES), key=len, reverse=True))))

# 시/군/구/읍/면 단위는 오탐이 많아 '도'는 제외하고, 단어 경계에 가깝게만 매칭
_CITY_COUNTY_RX = re.compile(r"(?:(?<=\s)|^)([가-힣]{2,})(시|군|구|읍|면)(?=\s|$|[\]\[\)\(\.,·!\?\"'“”‘’:/-])")

# _REGION_RX: ordered scan helper for pest de-dup (province + city/county tokens).
# NOTE: keep conservative to avoid false positives; used only for grouping, not for relevance filtering.
_REGION_RX = re.compile(r"(?:" + _PROVINCE_RX.pattern + r")|(?:" + _CITY_COUNTY_RX.pattern + r")")


# 지역처럼 보이지만 실제로는 농업/기사 용어인 경우가 많아 제외(보수적)
_REGION_STOP_PREFIX = {
    "방제","예찰","지원","대책","정책","수급","출하","가격","물량","품질","생산","소비","확대","감소",
    "개최","진행","발표","추진","확보","개선","강화","단속","점검","조사","확산","주의","경보","전망",
}

def _region_set(s: str) -> set[str]:
    s = (s or "")
    out: set[str] = set()

    # 1) 광역/도 단위는 명시 리스트만 허용
    for mm in _PROVINCE_RX.finditer(s):
        out.add(mm.group(0))

    # 2) 시/군/구/읍/면 단위는 보수적으로 추출(오탐 방지)
    for mm in _CITY_COUNTY_RX.finditer(s):
        stem = mm.group(1)
        suf = mm.group(2)
        if stem in _REGION_STOP_PREFIX:
            continue
        out.add(f"{stem}{suf}")

    return out
_BARE_REGION_RX = re.compile(r"([가-힣]{2,6})(?=(?:\s*)?(?:농업기술센터|농기센터|군청|시청|구청|농업기술원|농업기술과))")
_ATTACHED_REGION_RX = re.compile(r"([가-힣]{2,16}(?:군|시|구|도))(?=(?:농업기술센터|농기센터|농업기술원|농업기술과|농기원|이|가|은|는|에서|에|와|과|,))")

_PEST_CORE_TOKENS = {
    "병해충","방제","예찰","과수화상병","탄저병","냉해","동해","월동","약제","농약","살포","방역"
}
_SUPPLY_CORE_TOKENS = {"수급","가격","시세","경락","경락가","작황","출하","재고","저장","물량","반입"}
def _collect_supply_commodity_tokens() -> set[str]:
    out: set[str] = set()
    for entry in COMMODITY_REGISTRY:
        if not isinstance(entry, dict):
            continue
        for key in ("topic", "rep_term", "display_name"):
            term = str(entry.get(key) or "").strip()
            if len(term) >= 2:
                out.add(term)
        for key in ("aliases", "focus_terms", "brief_tags"):
            for term in entry.get(key) or []:
                term_s = str(term or "").strip()
                if len(term_s) >= 2:
                    out.add(term_s)
    for item in MANAGED_ONLY_COMMODITY_ITEMS:
        label = str(item.get("label") or "").strip()
        short_label = str(item.get("short_label") or "").strip()
        if len(label) >= 2:
            out.add(label)
        if len(short_label) >= 2:
            out.add(short_label)
        for term in _managed_commodity_topic_terms(item):
            term_s = str(term or "").strip()
            if len(term_s) >= 2:
                out.add(term_s)
    out.update({"쌀", "비축미"})
    return out

_SUPPLY_COMMODITY_TOKENS = _collect_supply_commodity_tokens()

_DIST_CORE_TOKENS = {"가락시장","도매시장","공판장","경락","경매","반입","중도매인","시장도매인","apc","물류","유통","온라인도매시장"}
_POLICY_CORE_TOKENS = {"대책","지원","할인","할인지원","할당관세","검역","통관","단속","고시","개정","보도자료","브리핑","예산","확대","연장"}

def _pest_region_key(title: str) -> str:
    """pest 섹션 중복 억제를 위한 대표 지역 키.
    - 읍/면 등 하위 단위가 있어도 같은 군/시/구로 묶이도록 우선 군/시/구를 선택
    - 없으면 첫 지역 토큰(도 등) 사용
    """
    t = title or ""
    attached = _ATTACHED_REGION_RX.search(t)
    if attached:
        return attached.group(1)
    ms = list(_REGION_RX.finditer(t))
    if not ms:
        # 군/시/구가 명시되지 않지만 "장수 농업기술센터"처럼 자주 등장하는 패턴 보완
        m2 = _BARE_REGION_RX.search(t)
        if m2:
            return m2.group(1)
        return ""
    # 1) 가장 먼저 등장하는 군/시/구(읍/면 제외)를 대표로
    for m in ms:
        r = m.group(0)
        if r.endswith(("군", "시", "구")):
            return r
    # 2) 군/시/구가 없으면 첫 토큰(도/광역시 등)
    return ms[0].group(0)


_PEST_FOOTPRINT_DISEASE_TERMS: dict[str, tuple[str, ...]] = {
    "fireblight": ("과수화상병",),
    "tomato_moth": ("토마토뿔나방",),
    "anthracnose": ("탄저병",),
    "winter_pest": ("월동해충", "월동 해충", "돌발 해충", "돌발해충"),
    "general_pest": ("병해충",),
}


def _normalize_pest_region_token(region: str) -> str:
    token = str(region or "").strip()
    if not token:
        return ""
    token = re.sub(r"(특별자치시|특별자치도|광역시|특별시)$", "", token)
    token = re.sub(r"(시|군|구|도)$", "", token)
    return token or str(region or "").strip()


def _pest_region_or_fallback_key(a: "Article") -> str:
    region_key = _pest_region_key(a.title or "")
    if region_key:
        return _normalize_pest_region_token(region_key)
    attached = _ATTACHED_REGION_RX.search((a.title or "") + " " + (a.description or ""))
    if attached:
        return _normalize_pest_region_token(attached.group(1))
    region_candidates = sorted(_region_set((a.title or "") + " " + (a.description or "")))
    return _normalize_pest_region_token(region_candidates[0]) if region_candidates else ""


def _pest_article_commodity_keys(a: "Article") -> tuple[str, ...]:
    cached = getattr(a, "_pest_diversity_keys", None)
    if cached is None:
        try:
            cached = tuple(managed_commodity_keys_for_article(a))
        except Exception:
            cached = ()
        if not cached:
            text = ((a.title or "") + " " + (a.description or "")).lower()
            inferred = sorted(
                {
                    TOPIC_REP_BY_TERM_L.get(term, term)
                    for term in HORTI_ITEM_TERMS_L
                    if term in text
                }
            )
            if inferred:
                cached = tuple(inferred[:3])
        if not cached:
            topic = str(getattr(a, "topic", "") or "").strip()
            if topic in _HORTI_TOPICS_SET:
                cached = (topic,)
        setattr(a, "_pest_diversity_keys", cached)
    return tuple(cached or ())


def _pest_article_disease_keys(a: "Article") -> tuple[str, ...]:
    cached = getattr(a, "_pest_disease_keys", None)
    if cached is None:
        text = ((a.title or "") + " " + (a.description or "")).lower()
        cached = tuple(
            key
            for key, terms in _PEST_FOOTPRINT_DISEASE_TERMS.items()
            if any(term in text for term in terms)
        )
        setattr(a, "_pest_disease_keys", cached)
    return tuple(cached or ())


def _pest_story_footprint_tokens(a: "Article") -> tuple[str, ...]:
    cached = getattr(a, "_pest_footprint_tokens", None)
    if cached is None:
        region_key = _pest_region_or_fallback_key(a)
        commodity_keys = _pest_article_commodity_keys(a)
        disease_keys = _pest_article_disease_keys(a)
        tokens: set[str] = set()
        if region_key:
            for key in commodity_keys:
                tokens.add(f"region:{region_key}|commodity:{key}")
            for key in disease_keys:
                tokens.add(f"region:{region_key}|disease:{key}")
            if not tokens:
                tokens.add(f"region:{region_key}")
        elif commodity_keys and disease_keys:
            for commodity_key in commodity_keys:
                for disease_key in disease_keys:
                    tokens.add(f"commodity:{commodity_key}|disease:{disease_key}")
        cached = tuple(sorted(tokens))
        setattr(a, "_pest_footprint_tokens", cached)
    return tuple(cached or ())


def _pest_has_same_footprint(a: "Article", b: "Article") -> bool:
    return bool(set(_pest_story_footprint_tokens(a)) & set(_pest_story_footprint_tokens(b)))


_POLICY_FOOTPRINT_KIND_TERMS: dict[str, tuple[str, ...]] = {
    "supply_center": ("광역 수급 관리센터", "광역수급관리센터", "수급 관리센터", "수급관리센터"),
    "pilot_program": ("시범사업", "시범 사업"),
    "price_support": (
        "가격안정",
        "가격 안정",
        "최저가격",
        "최저 가격",
        "최소가격",
        "보전",
        "보전금",
        "차액 지원",
        "지원사업",
    ),
    "discount_support": ("할인 지원", "할인지원", "할인쿠폰", "할인 쿠폰"),
    "fruit_snack": ("과일간식", "과일 간식"),
}


def _normalize_policy_region_token(region: str) -> str:
    token = str(region or "").strip()
    if not token:
        return ""
    token = re.sub(r"(특별자치시|특별자치도|광역시|특별시)$", "", token)
    token = re.sub(r"(시|군|구|도)$", "", token)
    return token or str(region or "").strip()


def _policy_region_or_fallback_key(a: "Article") -> str:
    region_candidates = sorted(_region_set((a.title or "") + " " + (a.description or "")))
    for region in region_candidates:
        token = _normalize_policy_region_token(region)
        if token:
            return token
    attached = _ATTACHED_REGION_RX.search((a.title or "") + " " + (a.description or ""))
    if attached:
        return _normalize_policy_region_token(attached.group(1))
    return ""


def _policy_article_commodity_keys(a: "Article") -> tuple[str, ...]:
    cached = getattr(a, "_policy_diversity_keys", None)
    if cached is None:
        try:
            cached = tuple(managed_commodity_keys_for_article(a))
        except Exception:
            cached = ()
        if not cached:
            text = ((a.title or "") + " " + (a.description or "")).lower()
            inferred = sorted(
                {
                    TOPIC_REP_BY_TERM_L.get(term, term)
                    for term in HORTI_ITEM_TERMS_L
                    if term in text
                }
            )
            if inferred:
                cached = tuple(inferred[:3])
        if not cached:
            topic = str(getattr(a, "topic", "") or "").strip()
            if topic in _HORTI_TOPICS_SET:
                cached = (topic,)
        setattr(a, "_policy_diversity_keys", cached)
    return tuple(cached or ())


def _policy_story_kind(a: "Article") -> str:
    cached = getattr(a, "_policy_story_kind", None)
    if cached is None:
        text = ((a.title or "") + " " + (a.description or "")).lower()
        cached = ""
        for kind, terms in _POLICY_FOOTPRINT_KIND_TERMS.items():
            if any(term in text for term in terms):
                cached = kind
                break
        setattr(a, "_policy_story_kind", cached)
    return str(cached or "")


def _policy_story_footprint_tokens(a: "Article") -> tuple[str, ...]:
    cached = getattr(a, "_policy_footprint_tokens", None)
    if cached is None:
        region_key = _policy_region_or_fallback_key(a)
        commodity_keys = _policy_article_commodity_keys(a)
        story_kind = _policy_story_kind(a)
        tokens: set[str] = set()
        if region_key and story_kind:
            tokens.add(f"region:{region_key}|kind:{story_kind}")
            for commodity_key in commodity_keys:
                tokens.add(f"region:{region_key}|kind:{story_kind}|commodity:{commodity_key}")
        elif region_key:
            for commodity_key in commodity_keys:
                tokens.add(f"region:{region_key}|commodity:{commodity_key}")
            if not tokens:
                tokens.add(f"region:{region_key}")
        elif story_kind and commodity_keys:
            for commodity_key in commodity_keys:
                tokens.add(f"kind:{story_kind}|commodity:{commodity_key}")
        cached = tuple(sorted(tokens))
        setattr(a, "_policy_footprint_tokens", cached)
    return tuple(cached or ())


def _policy_has_same_footprint(a: "Article", b: "Article") -> bool:
    return bool(set(_policy_story_footprint_tokens(a)) & set(_policy_story_footprint_tokens(b)))


def _near_duplicate_title(a: "Article", b: "Article", section_key: str) -> bool:
    """URL이 달라도 '사실상 같은 이슈'로 보이는 제목 중복을 억제한다.
    - 특히 pest(병해충/방제) 섹션에서 같은 지자체 방제 이슈가 여러 건 뜨는 문제를 완화.
    """
    ta = _token_set(a.title)
    tb = _token_set(b.title)
    jac = _jaccard(ta, tb)

    # 제목이 다르더라도 본문(요약)까지 포함하면 사실상 같은 이슈인 경우가 많음(타매체 재전송/공동취재)
    ta2 = _token_set((a.title or "") + " " + (a.description or ""))
    tb2 = _token_set((b.title or "") + " " + (b.description or ""))
    jac2 = _jaccard(ta2, tb2)
    if jac2 >= 0.62:
        return True

    # 문자열 유사도(표기 차이/특수문자 차이 보완)
    sa = re.sub(r"\s+", "", (a.title_key or a.title or "")).lower()
    sb = re.sub(r"\s+", "", (b.title_key or b.title or "")).lower()
    try:
        if sa and sb and difflib.SequenceMatcher(None, sa, sb).ratio() >= 0.88:
            return True
    except Exception:
        pass

    # 강한 중복(거의 동일)
    if jac >= 0.72:
        return True

    ra = _region_set((a.title or "") + " " + (a.description or ""))
    rb = _region_set((b.title or "") + " " + (b.description or ""))
    if section_key == "pest":
        ra = {_normalize_pest_region_token(x) for x in ra if _normalize_pest_region_token(x)}
        rb = {_normalize_pest_region_token(x) for x in rb if _normalize_pest_region_token(x)}
        a_region_key = _pest_region_or_fallback_key(a)
        b_region_key = _pest_region_or_fallback_key(b)
        if a_region_key:
            ra.add(a_region_key)
        if b_region_key:
            rb.add(b_region_key)
    elif section_key == "policy":
        ra = {_normalize_policy_region_token(x) for x in ra if _normalize_policy_region_token(x)}
        rb = {_normalize_policy_region_token(x) for x in rb if _normalize_policy_region_token(x)}
        a_region_key = _policy_region_or_fallback_key(a)
        b_region_key = _policy_region_or_fallback_key(b)
        if a_region_key:
            ra.add(a_region_key)
        if b_region_key:
            rb.add(b_region_key)
    same_region = bool(ra & rb)

    if section_key == "pest":
        common_core = len((ta & tb) & _PEST_CORE_TOKENS)
        a_text = ((a.title or "") + " " + (a.description or "")).lower()
        b_text = ((b.title or "") + " " + (b.description or "")).lower()
        same_disease = any(
            term in a_text and term in b_text
            for term in ("과수화상병", "탄저병", "냉해", "동해", "토마토뿔나방", "월동해충")
        )
        same_commodity = bool(set(_pest_article_commodity_keys(a)) & set(_pest_article_commodity_keys(b)))
        pest_action_terms = [w.lower() for w in ("사전 방제", "사전방제", "방제", "예찰", "약제", "무상 공급", "무상공급", "예방교육", "확산 차단")]
        a_action_hits = count_any(a_text, pest_action_terms)
        b_action_hits = count_any(b_text, pest_action_terms)
        if same_region and same_disease and a_action_hits >= 1 and b_action_hits >= 1:
            return True
        if same_region and same_commodity and a_action_hits >= 1 and b_action_hits >= 1:
            return True
        if _pest_has_same_footprint(a, b) and a_action_hits >= 1 and b_action_hits >= 1:
            return True
        # 같은 지자체 + 방제/병해충 키워드가 충분히 겹치면(기사만 다르고 내용이 같은 경우가 많음)
        if same_region and common_core >= 2 and jac >= 0.45:
            return True
        # '방제/예찰/약제' + 같은 지역이면 더 관대하게 중복 판단
        if same_region and common_core >= 1 and jac >= 0.52:
            return True

    if section_key == "supply":
        common_core = len((ta & tb) & _SUPPLY_CORE_TOKENS)
        common_cmd = len((ta & tb) & _SUPPLY_COMMODITY_TOKENS)
        if common_cmd >= 1 and common_core >= 2 and jac >= 0.50:
            return True

    if section_key == "dist":
        common_core = len((ta & tb) & _DIST_CORE_TOKENS)
        a_text = ((a.title or "") + " " + (a.description or "")).lower()
        b_text = ((b.title or "") + " " + (b.description or "")).lower()
        sales_channel_terms = [w.lower() for w in ("연합판매사업", "직거래", "평가회", "워크숍")]
        a_sales_hits = count_any(a_text, sales_channel_terms)
        b_sales_hits = count_any(b_text, sales_channel_terms)
        sales_group_a = _dist_sales_channel_group_key(a.title or "", a.description or "")
        sales_group_b = _dist_sales_channel_group_key(b.title or "", b.description or "")
        same_sales_group = bool(sales_group_a and sales_group_b and sales_group_a == sales_group_b)
        if (same_region or same_sales_group) and ("연합판매사업" in a_text) and ("연합판매사업" in b_text) and a_sales_hits >= 2 and b_sales_hits >= 2:
            return True
        if (same_region or common_core >= 2) and jac >= 0.50:
            return True

    if section_key == "policy":
        common_core = len((ta & tb) & _POLICY_CORE_TOKENS)
        story_kind_a = _policy_story_kind(a)
        story_kind_b = _policy_story_kind(b)
        same_kind = story_kind_a and (story_kind_a == story_kind_b)
        commodity_keys_a = set(_policy_article_commodity_keys(a))
        commodity_keys_b = set(_policy_article_commodity_keys(b))
        same_commodity = bool(commodity_keys_a & commodity_keys_b)
        if _policy_has_same_footprint(a, b) and (common_core >= 1 or jac >= 0.34 or jac2 >= 0.42):
            return True
        if same_region and same_kind:
            if same_commodity and (common_core >= 1 or jac >= 0.34):
                return True
            if (not commodity_keys_a) and (not commodity_keys_b) and story_kind_a in {"price_support", "pilot_program", "supply_center"}:
                if common_core >= 1 or jac >= 0.22 or jac2 >= 0.28:
                    return True
            if common_core >= 2 and jac >= 0.34:
                return True
        if common_core >= 2 and jac >= 0.55:
            return True

    return False

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def _is_policy_official(a: "Article") -> bool:
    """정책 섹션에서 '공식 발표/공지'로 취급할 소스."""
    dom = normalize_host(a.domain)
    p = (a.press or "").strip()

    if dom in OFFICIAL_HOSTS or any(dom.endswith("." + h) for h in OFFICIAL_HOSTS):
        return True

    # 도메인 매핑이 불완전할 수 있어, 기관명 기반도 보강
    if p in ("농식품부", "정책브리핑", "aT", "농관원", "KREI", "농촌진흥청", "가락시장"):
        return True

    return False

# -----------------------------
# Headline gate constants
# -----------------------------
# 코어(핵심 2)로 올리기엔 부적절한 헤드라인 패턴(칼럼/기고/행사/인물/홍보성)
_HEADLINE_STOPWORDS = [
    "칼럼", "기고", "사설", "오피니언", "독자기고", "기자수첩",
    "일기", "농막일기", "수필", "에세이", "연재", "기행",
    "인터뷰", "interview", "대담", "신간", "책", "추천", "여행", "맛집",
    "포토", "화보", "영상", "스케치", "행사", "축제", "기념", "시상",
    "봉사", "후원", "기부", "캠페인", "발대식", "선포식", "협약", "mou",
    "인물", "동정", "취임", "인사", "부고", "결혼", "개업",
]

def _headline_gate(a: "Article", section_key: str) -> bool:
    """코어(핵심2)로 올릴 자격이 있는지(섹션별).

    원칙:
    - 코어는 "농산물/원예 맥락"이 확실한 기사만(부분 언급/인터뷰/행정 단신은 하단)
    - APC는 농업 문맥일 때만 인정
    """
    title = (a.title or "").lower()
    text = (a.title + " " + a.description).lower()
    if section_key == "dist" and is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
        return True

    # (핵심) 코어2는 "정말 핵심"만 올리기 위해, 품목/도매/원예 신호를 재확인
    horti_sc = best_horti_score(a.title or "", a.description or "")
    horti_title_sc = best_horti_score(a.title or "", "")
    market_ctx_terms = ["가락시장", "도매시장", "공판장", "청과", "경락", "경락가", "반입", "중도매인", "시장도매인", "온라인 도매시장", "산지유통", "산지유통센터"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    agri_anchor_terms = ("농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화", "청과")
    agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])

    # 공통: 칼럼/기고/인물/행사성은 코어에서 제외
    if has_any(title, [w.lower() for w in _HEADLINE_STOPWORDS]):
        return False

    # 공통: 행정/정치 인터뷰·동정성(도지사/시장 등) 기사에 대한 코어 차단(부분 언급 오탐 방지)
    poli_roles = ("도지사", "지사", "시장", "군수", "도의회", "도의원", "시의회", "국회의원", "도정", "시정", "군정", "행정")
    if any(r in title for r in poli_roles):
        strong_keep = ("할인", "할인지원", "할당관세", "수급", "가격", "출하", "재고",
                       "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
                       "원산지", "부정유통", "단속", "검역", "통관", "수출")
        # 농산물 맥락이 강하고(앵커/시장/품목) + 실무 신호가 명확할 때만 예외적으로 코어 허용
        if not (((market_hits >= 1) or (horti_title_sc >= 1.6) or (agri_anchor_hits >= 2 and horti_title_sc >= 1.3))
                and count_any(text, [t.lower() for t in strong_keep]) >= 2):
            return False


    # 공통: 기사 전체가 '지자체 행정/인터뷰' 성격인데 품목이 일부 문단에만 등장하는 경우를 코어에서 제외
    adminish = ("도청", "시청", "군청", "도의회", "시의회", "정무", "민선", "도정", "시정", "군정", "행정",
                "관광", "복지", "청년", "교육", "교통", "SOC", "공약", "인사")
    if any(w in title for w in adminish) or any(w in text for w in adminish):
        # 제목에서 품목/원예 신호가 약한 행정/인터뷰성 기사는 (본문 일부 언급 오탐 가능) 코어에서 제외
        if horti_title_sc < 1.4 and market_hits == 0:
            return False
        strong_keep2 = ("할인", "할인지원", "할당관세", "수급", "가격", "출하", "재고",
                        "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
                        "원산지", "부정유통", "단속", "검역", "통관", "수출")
        if count_any(text, [t.lower() for t in strong_keep2]) < 2 and market_hits == 0 and horti_sc < 2.8:
            return False

    if section_key == "supply":
        if is_dist_political_visit_context(a.title or "", a.description or ""):
            return False
        if is_agri_training_recruitment_context(a.title or "", a.description or ""):
            return False
        if is_agri_org_rename_context(a.title or "", a.description or ""):
            return False
        if is_title_livestock_dominant_context(a.title or "", a.description or ""):
            return False
        signal_terms = ["가격", "시세", "수급", "작황", "생산", "출하", "반입", "물량", "재고", "경락", "경매"]

        # ✅ 핵심2는 "제목(헤드라인)"에서 농산물/품목 맥락이 드러나야 한다.
        # - 행정/인터뷰 기사(본문 한 문단 언급) 오탐을 막기 위해 title-only 품목 점수를 함께 본다.
        horti_title_sc = best_horti_score(a.title or "", "")

        if not has_any(text, [t.lower() for t in signal_terms]):
            return False

        # 시장/도매 신호가 있으면 코어 가능(단, 제목 품질은 이미 위에서 걸러짐)
        if market_hits >= 1:
            return True

        # 품목 점수가 강해도, 제목에서 품목/원예 신호가 약하면(=본문 일부 언급) 코어 불가
        if horti_sc >= 2.3 and horti_title_sc >= 1.6:
            return True

        # 농산물 앵커가 충분히 있고 제목 품목 점수가 중간 이상이면 허용
        if agri_anchor_hits >= 2 and horti_title_sc >= 1.3:
            return True

        return False

    if section_key == "policy":
        if is_title_livestock_dominant_context(a.title or "", a.description or ""):
            return False
        if is_policy_forest_admin_noise_context(a.title or "", a.description or ""):
            return False
        if is_policy_budget_drive_noise_context(a.title or "", a.description or ""):
            return False
        if _is_policy_official(a):
            return True
        action_terms = ["대책", "지원", "할인", "할당관세", "검역", "고시", "개정", "발표", "추진", "확대", "연장", "단속", "브리핑", "보도자료", "예산"]
        ctx_terms = ["농산물", "농업", "농식품", "과일", "채소", "수급", "가격", "유통", "원산지", "도매시장", "공영도매시장", "수출", "검역"]

        # 식품안전/위생 단독(도매/품목 신호 없음)은 코어에서 제외
        if any(w in text for w in ("식품안전", "위생", "haccp", "식중독")) and (market_hits == 0) and (horti_sc < 2.0) and (agri_anchor_hits == 0):
            return False

        # 정책 코어는 '정책 액션' + '농식품/유통 맥락'이 동시 충족되어야 함
        return has_any(text, [t.lower() for t in action_terms]) and has_any(text, [t.lower() for t in ctx_terms]) and ((horti_sc >= 1.8) or (market_hits >= 1) or (agri_anchor_hits >= 2))

    if section_key == "dist":
        # 유통 코어는 '도매시장/산지유통/APC/단속/검역' 등 강신호가 충분하고,
        # 농산물/원예/시장 맥락이 함께 있을 때만 허용
        if is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            return True
        if is_dist_political_visit_context(a.title or "", a.description or ""):
            return False
        if is_local_agri_infra_designation_context(a.title or "", a.description or ""):
            return False
        if is_dist_local_crop_strategy_noise_context(a.title or "", a.description or ""):
            return False
        dist_terms = ["가락시장", "도매시장", "공판장", "공영도매시장", "청과", "경락", "경락가", "경매", "반입",
                      "중도매인", "시장도매인", "온라인 도매시장",
                      "선별", "저온", "저온저장", "저장고", "ca저장", "물류",
                      "수출", "선적", "선적식", "수출길", "검역", "통관", "원산지", "부정유통", "단속", "산지유통", "산지유통센터"]
        dist_hits = count_any(text, [t.lower() for t in dist_terms])
        apc_ctx = has_apc_agri_context(text)
        if apc_ctx:
            dist_hits += 1
        if is_dist_supply_management_center_context(a.title or "", a.description or ""):
            dist_hits = max(dist_hits, 2)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if is_dist_sales_channel_ops_context(a.title or "", a.description or ""):
            dist_hits = max(dist_hits, 2)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            dist_hits = max(dist_hits, 2)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        # ✅ 지역 단신/지자체 공지형 기사(dist)는 핵심2로 올리지 않는다.
        if is_local_brief_text(a.title or "", a.description or "", section_key):
            return False
        if is_local_agri_infra_designation_context(a.title or "", a.description or ""):
            return False

        # '수출/검역/통관/원산지 단속'만으로 걸린 일반 기사 누수 방지(시장/APC/원예 맥락 없는 경우)
        ops_terms = ("원산지", "부정유통", "단속", "검역", "통관", "수출")
        ops_hits = count_any(text, [t.lower() for t in ops_terms])
        if (ops_hits >= 1 and market_hits == 0 and (not apc_ctx)
                and agri_anchor_hits == 0 and horti_sc < 2.0):
            return False

        # 방송사 지역기사의 '부분 언급' 누수 방지(KBS/SBS 등)
        if ((a.press or "").strip() in BROADCAST_PRESS and _LOCAL_GEO_PATTERN.search(a.title or "")):
            title_market_hits = count_any(title, [t.lower() for t in ("가락시장", "도매시장", "공판장", "공영도매시장",
                                                                      "경락", "경매", "반입", "산지유통", "산지유통센터", "apc")])
            if title_market_hits == 0 and (not apc_ctx) and horti_sc < 2.2 and horti_title_sc < 1.6:
                return False

        # dist_hits(도매/유통 강신호)가 부족하면 기본적으로 코어 불가
        # 단, APC 인프라 기사나 농업 전문/현장 매체의 '시장 현장/대목장' 리포트는 예외 허용
        if dist_hits < 2:
            if is_dist_export_shipping_context(a.title or "", a.description or ""):
                return True
            if is_dist_export_field_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                return True
            if is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                return True
            if apc_ctx and any(w in text for w in ("준공", "완공", "개장", "개소", "가동", "선별", "선과", "저온", "저장고", "ca저장")):
                return True
            if ((a.press in AGRI_TRADE_PRESS or normalize_host(a.domain or "") in AGRI_TRADE_HOSTS)
                    and has_any(title, ["대목장", "대목", "현장", "어땠나", "판매", "시장"])
                    and (horti_title_sc >= 1.4 or horti_sc >= 2.0)):
                return True
            return False
        return (agri_anchor_hits >= 1) or (horti_sc >= 2.0) or (market_hits >= 1) or apc_ctx
    if section_key == "pest":
        if is_pest_input_marketing_noise_context(a.title or "", a.description or ""):
            return False
        # 농업 맥락 + 병해충/방제(또는 냉해/동해 피해) 가시적이어야 코어
        if not has_any(text, [t.lower() for t in PEST_AGRI_CONTEXT_TERMS]):
            return False
        # 코어는 '헤드라인'에서 병해충/방제/기상피해 신호가 드러나야 한다(수필/일기/정치 제목 누수 방지).
        title_hits = count_any(title, [t.lower() for t in PEST_STRICT_TERMS]) + count_any(title, [t.lower() for t in PEST_WEATHER_TERMS])
        if title_hits == 0:
            return False

        strict_hits = count_any(text, [t.lower() for t in PEST_STRICT_TERMS])
        weather_hits = count_any(text, [t.lower() for t in PEST_WEATHER_TERMS])
        return (strict_hits >= 2) or (strict_hits >= 1 and weather_hits >= 1) or (weather_hits >= 2)

    return True
def _headline_gate_relaxed(a: "Article", section_key: str) -> bool:
    """코어가 아닌 일반 선택에서의 '헤드라인 품질' 게이트(완화).
    - 목적: 낚시/인물/행사/홍보성 헤드라인이 상단을 차지하는 것을 방지
    - 1차 필터(is_relevant)가 이미 강하게 거르고 있으므로, 여기서는 '제목 품질' 중심으로만 최소 차단한다.
    """
    title = (a.title or "").lower()
    text = (a.title + " " + a.description).lower()
    if section_key == "dist" and is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
        return True

    # 1) 칼럼/사설/기고/인물/부고/인사류는 코어가 아니어도 상단 노출을 막는다(거의 항상 노이즈)
    hard_stop = ("칼럼", "사설", "오피니언", "기고", "독자기고", "기자수첩",
    "일기", "농막일기", "수필", "에세이", "연재", "기행",
                 "인터뷰", "interview", "대담", "인물", "동정", "부고", "결혼", "취임", "인사", "개업")
    if any(w.lower() in title for w in hard_stop):
        return False

    # 2) '행사/캠페인/시상/축제/발대식/선포식' 등은 dist(현장) 섹션에선 일부 의미가 있을 수 있어
    #    dist는 더 완화하고, 나머지 섹션은 강한 수급/정책/시장 신호가 없으면 컷
    eventy = ("행사", "축제", "기념", "시상", "봉사", "후원", "기부", "캠페인", "발대식", "선포식", "협약", "mou")
    if any(w.lower() in title for w in eventy):
        if section_key != "dist":
            strong_keep_terms = ("가격", "시세", "수급", "작황", "출하", "물량", "재고", "저장",
                                 "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
                                 "검역", "통관", "원산지", "단속", "부정유통", "할당관세", "할인지원", "대책", "보도자료", "브리핑")
            if not any(t.lower() in text for t in strong_keep_terms):
                return False
        elif is_dist_campaign_noise_context(a.title or "", a.description or ""):
            return False

    # 3) 섹션별 최소 맥락 재확인(아주 느슨하게)
    horti_sc = best_horti_score(a.title or "", a.description or "")
    horti_title_sc = best_horti_score(a.title or "", "")
    market_ctx_terms = ["가락시장", "도매시장", "공판장", "청과", "경락", "경락가", "반입", "중도매인", "시장도매인", "온라인 도매시장", "산지유통", "산지유통센터"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    if section_key == "policy":
        if is_title_livestock_dominant_context(a.title or "", a.description or ""):
            return False
        if is_policy_forest_admin_noise_context(a.title or "", a.description or ""):
            return False
        if is_policy_budget_drive_noise_context(a.title or "", a.description or ""):
            return False
        if is_agri_training_recruitment_context(a.title or "", a.description or ""):
            return False
        # 공식 소스는 최대한 살림
        try:
            if _is_policy_official(a):
                return True
        except Exception:
            pass
        if is_broad_macro_price_context(a.title or "", a.description or ""):
            return True
        if is_policy_major_issue_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            return True
        if is_policy_export_support_brief_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            return True
        if is_policy_local_price_support_context(a.title or "", a.description or ""):
            return True
        # 정책 섹션은 최소한 '정책 액션' + '농식품 맥락'이 있어야 함(완화 버전)
        action_terms = ("대책", "지원", "할인", "할당관세", "검역", "고시", "개정", "단속", "브리핑", "보도자료", "예산")
        ctx_terms = ("농산물", "농식품", "농업", "과일", "채소", "수급", "가격", "유통", "원산지", "도매시장", "온라인 도매시장")
        if (not any(t.lower() in text for t in action_terms)) and (horti_sc < 1.6) and (market_hits == 0):
            return False
        if not any(t.lower() in text for t in ctx_terms):
            return False
        return True

    if section_key == "supply":
        if is_dist_political_visit_context(a.title or "", a.description or ""):
            return False
        if is_agri_training_recruitment_context(a.title or "", a.description or ""):
            return False
        if is_agri_org_rename_context(a.title or "", a.description or ""):
            return False
        if is_title_livestock_dominant_context(a.title or "", a.description or ""):
            return False
        # supply는 '품목/농산물 앵커' + '수급 신호' 결합이 약한 기사(단순 언급)를 하단으로 밀기 위해 더 보수적으로 본다.
        agri_anchor_terms = ("농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화", "청과")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])
        signal_terms = ("가격", "시세", "수급", "작황", "출하", "반입", "물량", "재고", "경락", "경매")
        supply_feature_kind = supply_feature_context_kind(a.title or "", a.description or "")

        sig_hits = count_any(text, [t.lower() for t in signal_terms])

        # 제목에서 품목/원예 신호가 거의 없고(본문 일부 언급 가능), 행정/인터뷰성 헤드라인이면 상단 노출(특히 core 보완 단계)에서 제외
        horti_title_sc = best_horti_score(a.title or "", "")
        adminish_title = ("민선", "도정", "시정", "군정", "행정", "도청", "시청", "군청", "공약", "정무", "인터뷰")
        if any(w.lower() in title for w in adminish_title) and market_hits == 0 and horti_title_sc < 1.2:
            return False

        # 시장 맥락도 없고, 품목점수도 약하고, 신호도 약하면 제외(2~3개에서 자연 종료 가능)
        if market_hits == 0 and horti_sc < 1.2 and agri_anchor_hits == 0 and sig_hits == 0:
            return False

        # '품목만 언급' 수준(신호 없음)인 기사는 score가 높아도 상단 노출을 막기 위해 컷(단, horti_sc가 매우 강하면 예외)
        if sig_hits == 0 and market_hits == 0 and horti_sc < 2.4 and supply_feature_kind is None:
            return False

        return True

    if section_key == "dist":
        if is_agri_training_recruitment_context(a.title or "", a.description or ""):
            return False
        if dist_market_disruption_scope(a.title or "", a.description or "") == "systemic":
            return True
        if is_dist_political_visit_context(a.title or "", a.description or ""):
            return False
        if is_local_agri_infra_designation_context(a.title or "", a.description or ""):
            return False
        if is_dist_local_crop_strategy_noise_context(a.title or "", a.description or ""):
            return False
        if is_dist_macro_export_noise_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            return False
        if is_dist_campaign_noise_context(a.title or "", a.description or ""):
            return False
        if is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            return True
        # dist는 is_relevant가 있어도 '일반 물류/유통/단속' 누수가 있어, 완화 게이트에서도 맥락을 한 번 더 본다.
        agri_anchor_terms = ("농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화", "청과")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])
        dist_hard = ("가락시장", "도매시장", "공판장", "공영도매시장", "청과", "경락", "경매", "반입",
                     "중도매인", "시장도매인", "온라인 도매시장",
                     "선별", "저온", "저온저장", "저장고", "ca저장", "원산지", "부정유통", "단속", "검역", "통관", "수출", "물류",
                     "산지유통", "산지유통센터")
        hard_hits = count_any(text, [t.lower() for t in dist_hard])
        apc_ctx = has_apc_agri_context(text)
        local_org_feature = is_local_agri_org_feature_context(a.title or "", a.description or "")
        dist_export_field = is_dist_export_field_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip())
        field_market_response = is_dist_field_market_response_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip())
        if apc_ctx:
            hard_hits += 1
        if local_org_feature:
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if dist_export_field:
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if field_market_response:
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if is_dist_supply_management_center_context(a.title or "", a.description or ""):
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if is_dist_sales_channel_ops_context(a.title or "", a.description or ""):
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)
        if is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            hard_hits = max(hard_hits, 1)
            agri_anchor_hits = max(agri_anchor_hits, 1)

        # 농업 앵커도 없고 시장/품목도 약하면 제외
        if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 1.6:
            return False

        # 운영/집행 키워드만 있는 일반 기사 누수 차단
        ops_terms = ("원산지", "부정유통", "단속", "검역", "통관", "수출")
        ops_hits = count_any(text, [t.lower() for t in ops_terms])
        if ops_hits >= 1 and market_hits == 0 and (not apc_ctx) and agri_anchor_hits == 0 and horti_sc < 2.0:
            return False

        # 방송사 지역기사의 약한 유통 문맥은 제외
        if ((a.press or "").strip() in BROADCAST_PRESS and _LOCAL_GEO_PATTERN.search(a.title or "")):
            title_market_hits = count_any(title, [t.lower() for t in ("가락시장", "도매시장", "공판장", "공영도매시장",
                                                                      "경락", "경매", "반입", "산지유통", "산지유통센터", "apc")])
            if title_market_hits == 0 and (not apc_ctx) and horti_sc < 2.1 and horti_title_sc < 1.5:
                return False

        # 하드 신호가 거의 없고 soft(추상)만 있으면 제외(억지 채움 방지)
        if hard_hits == 0 and horti_sc < 2.2:
            return False
        return True

    # pest는 is_relevant에서 맥락을 확인하므로, 여기서는 제목 품질만 관리
    if section_key == "pest":
        if is_pest_input_marketing_noise_context(a.title or "", a.description or ""):
            return False
        title_signal = _pest_title_signal_count(a.title or "")
        if title_signal == 0 and not is_pest_control_policy_context(text):
            return False
        return is_pest_story_focus_strong(a.title or "", a.description or "") or is_pest_control_policy_context(text)

    return True


# -----------------------------
# Selection threshold
# -----------------------------
# 섹션별 최소 스코어 기준선(너무 약한 기사는 후보 풀에서 제외)
BASE_MIN_SCORE = {
    "supply": 7.0,
    "policy": 7.0,
    "dist": 7.2,
    "pest": 6.6,
}

def _dist_selection_reference_score(candidates_sorted: list["Article"]) -> float:
    if not candidates_sorted:
        return BASE_MIN_SCORE.get("dist", 7.2)
    unique_candidates = _dedupe_by_event_key(list(candidates_sorted), "dist")
    top_scores = [float(getattr(a, "score", 0.0) or 0.0) for a in unique_candidates[:5]]
    ref = top_scores[0]
    best_gap = 0.0
    ref_idx = 0
    for idx in range(len(top_scores) - 1):
        gap = top_scores[idx] - top_scores[idx + 1]
        if gap > best_gap:
            best_gap = gap
            ref_idx = idx + 1
    if best_gap >= 7.0 and 0 <= ref_idx < len(top_scores):
        ref = top_scores[ref_idx]
    elif len(top_scores) >= 2 and (top_scores[0] - top_scores[1]) >= 7.5:
        ref = top_scores[1]
    return ref


def _selection_reference_score(candidates_sorted: list["Article"], section_key: str) -> float:
    if not candidates_sorted:
        return BASE_MIN_SCORE.get(section_key, 6.0)
    if section_key == "dist":
        return _dist_selection_reference_score(candidates_sorted)

    unique_candidates = _dedupe_by_event_key(list(candidates_sorted), section_key)
    top_scores = [float(getattr(a, "score", 0.0) or 0.0) for a in unique_candidates[:5]]
    if not top_scores:
        return BASE_MIN_SCORE.get(section_key, 6.0)

    ref = top_scores[0]
    gap_cut = {
        "supply": 8.0,
        "policy": 7.0,
        "pest": 5.8,
    }.get(section_key, 7.0)
    base_floor = BASE_MIN_SCORE.get(section_key, 6.0) + 0.8

    if len(top_scores) >= 2 and (top_scores[0] - top_scores[1]) >= gap_cut and top_scores[1] >= base_floor:
        ref = top_scores[1]
    elif len(top_scores) >= 3 and (top_scores[0] - top_scores[2]) >= (gap_cut + 2.0) and top_scores[2] >= base_floor:
        ref = top_scores[2]
    return ref


def _dynamic_threshold(candidates_sorted: list["Article"], section_key: str) -> float:
    """상위 기사 분포에 맞춰 동적으로 임계치를 잡아 '약한 기사'를 컷한다.
    - 최상위(best)에서 일정 마진을 빼고, 섹션별 최소선(BASE_MIN_SCORE)보다 낮아지지 않게.
    - policy는 저티어 소스 1건이 임계치를 과도하게 끌어올리지 않도록 비저티어 최고점을 우선 본다.
    """
    if not candidates_sorted:
        return BASE_MIN_SCORE.get(section_key, 6.0)

    best_article = candidates_sorted[0]
    if section_key == "policy":
        for cand in candidates_sorted:
            d = normalize_host(getattr(cand, "domain", "") or "")
            p = (getattr(cand, "press", "") or "").strip()
            if (p not in LOW_QUALITY_PRESS) and (d not in LOW_QUALITY_DOMAINS):
                best_article = cand
                break

    best = _selection_reference_score(candidates_sorted, section_key)
    margin = 8.0 if section_key in ("supply", "policy", "dist") else 7.0
    thr = max(BASE_MIN_SCORE.get(section_key, 6.0), best - margin)

    unique_candidates = _dedupe_by_event_key(list(candidates_sorted), section_key)
    unique_n = len(unique_candidates)
    relief = 0.0
    if section_key == "policy":
        if unique_n <= 4:
            relief = 4.0
        elif unique_n <= 8:
            relief = 2.2
    elif section_key == "pest":
        if unique_n <= 4:
            relief = 3.0
        elif unique_n <= 8:
            relief = 1.6
    elif section_key == "supply":
        if unique_n <= 5:
            relief = 1.4
    elif section_key == "dist":
        if unique_n <= 4:
            relief = 1.6
    if relief > 0:
        thr = max(BASE_MIN_SCORE.get(section_key, 6.0), thr - relief)
    return thr

def select_top_articles(candidates: list[Article], section_key: str, max_n: int) -> list[Article]:
    """섹션별 기사 선택.

    설계 원칙
    - '없으면 없는 대로' : 저품질/억지 채우기 금지(최소 개수 강제 X)
    - 핵심 2건(core)은 엄격 게이트(품목/원예/도매/정책 신호 + 제목 품질) 통과만 부여
    - 나머지 기사도 동적 임계치(threshold) 이상만 채택
    - 매체 편향 완화: 출처 캡(지방/인터넷 과다 방지) + 중복/유사 제목 제거
    """
    if not candidates:
        return []

    # 초기화
    for a in candidates:
        a.is_core = False
        a.selection_stage = ""
        a.selection_note = ""
        a.selection_fit_score = 0.0

    candidates_sorted = sorted(candidates, key=_sort_key_major_first, reverse=True)

    # 동적 임계치: 상위권 점수가 낮은 날은 더 엄격하게 컷하여 '억지 채움'을 막는다
    thr = _dynamic_threshold(candidates_sorted, section_key)

    # 임계치 이상 후보만 사용(없으면 빈 리스트)
    pool = [a for a in candidates_sorted if a.score >= thr]


    # dist/supply: 동일 이슈(APC 준공, 공급비용 압박 후속 리포트 등)가 여러 건 반복될 때
    # '이벤트 키'로 먼저 1차 클러스터링하여 중복으로 핵심이 밀리는 문제를 완화한다.
    if section_key in _EVENT_KEY_SECTIONS:
        pool = _dedupe_by_event_key(pool, section_key)

    if not pool:
        return []

    # 섹션 적합도(section-fit)가 매우 낮은 후보는 상단 선발에서 제외(단, 점수가 충분히 높으면 유지)
    sec_conf = next((x for x in SECTIONS if x.get("key") == section_key), {})
    def _record_selection(a: Article, stage: str, note: str = "") -> None:
        a.selection_stage = str(stage or "")
        a.selection_note = str(note or "")
        try:
            a.selection_fit_score = round(section_fit_score(a.title or "", a.description or "", sec_conf), 3)
        except Exception:
            a.selection_fit_score = 0.0

    fit_filtered: list[Article] = []
    for a in pool:
        fit_sc = section_fit_score(a.title or "", a.description or "", sec_conf)
        if (fit_sc >= SECTION_FIT_MIN_FOR_TOP) or (float(getattr(a, "score", 0.0) or 0.0) >= (thr + 1.2)):
            fit_filtered.append(a)
    if fit_filtered:
        pool = fit_filtered

    # '최대 max_n'은 상한(cap)이며, 뒤쪽 약한 기사로 억지 채우기 방지를 위해 tail-cut을 둔다
    best_score = float(getattr(pool[0], "score", 0.0) or 0.0)
    tail_ref_score = _selection_reference_score(pool, section_key)
    # 섹션별로 꼬리 허용폭을 다르게(유통/현장(dist)은 누수 방지를 위해 더 엄격)
    tail_margin_by_section = {
        "supply": 3.6,
        "policy": 3.8,
        "dist": 3.4,
        "pest": 3.6,
    }
    tail_margin = tail_margin_by_section.get(section_key, 3.6)

    # 페이지 노출량을 늘릴 때(예: MAX_PER_SECTION=5) "핵심2" 외 일반 기사도 적절히 포함되도록
    # tail-cut 폭을 넓힌다. (core 선정 로직/점수는 그대로 유지)
    if MAX_PER_SECTION >= 5:
        try:
            extra = float(os.getenv("PAGE_TAIL_MARGIN_EXTRA", "4.0") or 0.0)
        except Exception:
            extra = 4.0
        extra = max(0.0, min(extra, 12.0))
        tail_margin += extra

    tail_cut = max(thr, tail_ref_score - tail_margin)

    # 출처 캡(지방/인터넷 과다 방지)
    tier_count = {1: 0, 2: 0, 3: 0}
    wire_count = 0  # 통신/온라인 서비스 과대표집 방지
    # 더 보수적으로(사용자 피드백: 지방지/인터넷 비중 과다)
    base_tier2_cap = 2 if section_key in ("supply", "policy") else 3
    small_pool = len(pool) <= max(max_n + 1, 6)
    thin_pool = len(pool) <= max(max_n * 2, 8)
    tier1_cap = 1 + (1 if small_pool and section_key in ("policy", "dist", "pest") else 0)
    tier2_cap = base_tier2_cap + (1 if thin_pool else 0)

    def _source_ok_local(a: Article) -> bool:
        nonlocal wire_count
        # dist에서 통신/온라인 서비스는 상단을 잠식하기 쉬워 1건만 허용
        if section_key == "dist" and (a.press or "").strip() in WIRE_SERVICES:
            if wire_count >= 1:
                return False
        t = press_priority(a.press, a.domain)
        if t == 1:
            return tier_count[1] < tier1_cap
        if t == 2:
            return tier_count[2] < tier2_cap
        return True

    def _source_take(a: Article) -> None:
        nonlocal wire_count
        if section_key == "dist" and (a.press or "").strip() in WIRE_SERVICES:
            wire_count += 1
        t = press_priority(a.press, a.domain)
        if t in tier_count:
            tier_count[t] += 1

    # 코어 후보: 임계치 + 코어 최소점(더 엄격)
    core_min_by_section = {
        "supply": 7.8,
        "policy": 7.8,
        "dist": 8.2,
        "pest": 7.0,
    }
    core_min = max(thr, core_min_by_section.get(section_key, thr))
    core_fit_min_by_section = {
        "supply": 1.4,
        "policy": 1.4,
        "dist": 1.6,
        "pest": 1.2,
    }
    core_fit_min = core_fit_min_by_section.get(section_key, 1.2)
    core: list[Article] = []
    used_title_keys: set[str] = set()
    used_url_keys: set[str] = set()

    # 코어(핵심2)에서 농업 전문 인터넷 매체가 과도하게 잠식하지 않도록(다양성),
    # supply/policy에서는 trade-press 코어를 1건으로 제한(필요시 완화)
    trade_core_cap = 1 if section_key in ("supply", "policy") else 2
    trade_core_count = 0
    def _is_trade_press(a: Article) -> bool:
        try:
            d = normalize_host(a.domain or "")
        except Exception:
            d = (a.domain or "").lower()
        return ((a.press or "").strip() in AGRI_TRADE_PRESS) or (d in AGRI_TRADE_HOSTS)

    def _dup_key(a: Article) -> str:
        return a.norm_key or a.canon_url or a.title_key

    managed_key_cache: dict[str, tuple[str, ...]] = {}
    managed_primary_cache: dict[str, str] = {}

    def _managed_keys(a: Article) -> tuple[str, ...]:
        cache_key = _dup_key(a)
        keys = managed_key_cache.get(cache_key)
        if keys is None:
            keys = tuple(managed_commodity_keys_for_article(a))
            managed_key_cache[cache_key] = keys
        return keys

    def _managed_primary_key(a: Article) -> str:
        cache_key = _dup_key(a)
        key = managed_primary_cache.get(cache_key)
        if key is None:
            keys = list(_managed_keys(a))
            primary = ""
            for cand in keys:
                if bool((MANAGED_COMMODITY_BY_KEY.get(cand) or {}).get("program_core")):
                    primary = cand
                    break
            if not primary and keys:
                primary = keys[0]
            managed_primary_cache[cache_key] = primary
            key = primary
        return key

    pool_managed_primary_keys = {primary for primary in (_managed_primary_key(a) for a in pool) if primary}

    def _managed_repeat_too_close(a: Article, selected: list[Article], score_gap_override: float | None = None) -> bool:
        primary = _managed_primary_key(a)
        if not primary or not selected:
            return False
        selected_primary_keys = {key for key in (_managed_primary_key(b) for b in selected) if key}
        if primary not in selected_primary_keys:
            return False
        remaining_primaries = pool_managed_primary_keys - selected_primary_keys
        if not remaining_primaries:
            return False
        same_primary = [b for b in selected if _managed_primary_key(b) == primary]
        if not same_primary:
            return False
        best_same_score = max(float(getattr(b, "score", 0.0) or 0.0) for b in same_primary)
        best_same_fit = max(section_fit_score(b.title or "", b.description or "", sec_conf) for b in same_primary)
        score_gap = float(getattr(a, "score", 0.0) or 0.0) - best_same_score
        fit_gap = section_fit_score(a.title or "", a.description or "", sec_conf) - best_same_fit
        gap_need = score_gap_override
        if gap_need is None:
            gap_need = 1.8 if section_key == "supply" else 1.4 if section_key in ("dist", "policy") else 1.2
        if score_gap >= gap_need:
            return False
        return fit_gap < 0.45

    def _managed_overlap_penalty(a: Article, selected: list[Article]) -> float:
        if not selected:
            return 0.0
        keys_a = set(_managed_keys(a))
        if not keys_a:
            return 0.0
        primary_a = _managed_primary_key(a)
        penalty = 0.0
        for b in selected:
            keys_b = set(_managed_keys(b))
            if not keys_b:
                continue
            overlap = len(keys_a & keys_b)
            if overlap == 0:
                continue
            same_primary = bool(primary_a and primary_a == _managed_primary_key(b))
            penalty = max(penalty, min(1.4, (0.28 * overlap) + (0.68 if same_primary else 0.22)))
        return penalty

    def _is_low_core_source(a: Article) -> bool:
        d = normalize_host(a.domain or "")
        p = (a.press or "").strip()
        return (p in LOW_QUALITY_PRESS) or (d in LOW_QUALITY_DOMAINS)

    non_low_core_scores = [float(getattr(a, "score", 0.0) or 0.0) for a in pool if not _is_low_core_source(a)]
    best_non_low_core_score = max(non_low_core_scores) if non_low_core_scores else None
    strong_non_low_core_count = sum(1 for a in pool if (not _is_low_core_source(a)) and float(getattr(a, "score", 0.0) or 0.0) >= core_min)

    def _low_core_allowed(a: Article) -> bool:
        if not _is_low_core_source(a):
            return True
        if section_key == "policy":
            return False
        sc = float(getattr(a, "score", 0.0) or 0.0)
        if best_non_low_core_score is None:
            return sc >= (core_min + 2.6)
        if strong_non_low_core_count >= 2:
            return sc >= (best_non_low_core_score + 1.0)
        return sc >= (best_non_low_core_score + 0.6)

    def _already_used(a: Article) -> bool:
        k = _dup_key(a)
        return (k in used_title_keys) or (bool(a.canon_url) and a.canon_url in used_url_keys)

    def _mark_used(a: Article) -> None:
        used_title_keys.add(_dup_key(a))
        if a.canon_url:
            used_url_keys.add(a.canon_url)

    def _is_supply_feature_tail_story(a: Article) -> bool:
        if section_key != "supply":
            return False
        txt_local = ((a.title or "") + " " + (a.description or "")).lower()
        if has_direct_supply_chain_signal(txt_local):
            return False
        return bool(supply_feature_context_kind(a.title or "", a.description or "") or is_flower_consumer_trend_context(txt_local))

    def _is_supply_low_value_macro_brief(a: Article) -> bool:
        if section_key != "supply":
            return False
        txt_local = ((a.title or "") + " " + (a.description or "")).lower()
        dom_local = normalize_host(a.domain or "")
        pr_local = (a.press or "").strip()
        ttl_local = (a.title or "").lower()
        if press_priority(a.press, a.domain) == 1 and (("농축산물" in ttl_local) or ("농산물" in ttl_local)) and any(t in txt_local for t in ("전주 대비", "전년 대비", "평년 대비", "대체로")):
            return True
        if has_direct_supply_chain_signal(txt_local):
            return False
        if is_supply_feature_article(a.title or "", a.description or ""):
            return False
        if not is_broad_macro_price_context(a.title or "", a.description or ""):
            return False
        if is_policy_market_brief_context(txt_local, dom_local, pr_local):
            return True
        aggregate_hits = count_any(
            txt_local,
            [t.lower() for t in ("농축산물", "농산물", "과일류", "채소류", "과일", "채소", "전주 대비", "전년 대비", "평년 대비", "대체로")],
        )
        return press_priority(a.press, a.domain) == 1 and aggregate_hits >= 3

    def _is_supply_weak_tail_story(a: Article) -> bool:
        if section_key != "supply":
            return False
        return is_supply_weak_tail_context(a.title or "", a.description or "") or _is_supply_low_value_macro_brief(a)

    def _supply_feature_topic_repeat(a: Article, selected: list[Article]) -> bool:
        if not _is_supply_feature_tail_story(a):
            return False
        topic_name = (a.topic or "").strip()
        if not topic_name:
            return False
        a_issue_bucket = supply_issue_context_bucket(a.title or "", a.description or "")
        for b in selected:
            if (b.topic or "").strip() != topic_name:
                continue
            if not _is_supply_feature_tail_story(b):
                continue
            b_issue_bucket = supply_issue_context_bucket(b.title or "", b.description or "")
            if a_issue_bucket and b_issue_bucket and a_issue_bucket != b_issue_bucket:
                continue
            return True
        return False

    def _is_supply_policy_like_tail_story(a: Article) -> bool:
        if section_key != "supply":
            return False
        txt_local = ((a.title or "") + " " + (a.description or "")).lower()
        title_local = (a.title or "").lower()
        dom_local = normalize_host(a.domain or "")
        pr_local = (a.press or "").strip()
        issue_bucket = supply_issue_context_bucket(a.title or "", a.description or "")
        if issue_bucket:
            return False
        strong_item_context = (
            count_any(title_local, HORTI_ITEM_TERMS_L) >= 1
            or best_horti_score(a.title or "", "") >= 1.2
            or best_horti_score(a.title or "", a.description or "") >= 2.2
        )
        trade_hits = count_any(txt_local, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_TRADE_TERMS])
        hard_trade_terms = [w.lower() for w in ("관세", "할당관세", "무관세", "fta", "통상", "비관세장벽", "통관", "검역")]
        title_trade_hits = count_any(title_local, hard_trade_terms)
        hard_trade_hits = count_any(txt_local, hard_trade_terms)
        trade_impact_hits = count_any(txt_local, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_TRADE_IMPACT_TERMS])
        if strong_item_context and title_trade_hits >= 1 and hard_trade_hits >= 1 and trade_hits >= 1 and trade_impact_hits >= 1:
            return False
        if is_supply_stabilization_policy_context(txt_local, dom_local, pr_local):
            return True
        if is_policy_market_brief_context(txt_local, dom_local, pr_local):
            return True
        return (a.topic or "").strip() == "정책"
    def _is_supply_dist_like_tail_story(a: Article) -> bool:
        if section_key != "supply":
            return False
        txt_local = ((a.title or "") + " " + (a.description or "")).lower()
        dom_local = normalize_host(a.domain or "")
        pr_local = (a.press or "").strip()
        if has_direct_supply_chain_signal(txt_local):
            return False
        issue_bucket = supply_issue_context_bucket(a.title or "", a.description or "")
        if issue_bucket == "export_recovery":
            return False
        return is_dist_export_shipping_context(a.title or "", a.description or "") or is_dist_export_field_context(a.title or "", a.description or "", dom_local, pr_local) or is_dist_market_disruption_context(a.title or "", a.description or "")

    def _is_dist_weak_tail_story(a: Article) -> bool:
        if section_key != "dist":
            return False
        if is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
            has_stronger_ops_alt = any(
                (b is not a)
                and (
                    is_dist_market_ops_context(b.title or "", b.description or "", normalize_host(b.domain or ""), (b.press or "").strip())
                    or is_dist_supply_management_center_context(b.title or "", b.description or "")
                    or is_dist_sales_channel_ops_context(b.title or "", b.description or "")
                )
                for b in candidates_sorted
            )
            if has_stronger_ops_alt:
                return True
        return (
            is_dist_political_visit_context(a.title or "", a.description or "")
            or is_local_agri_infra_designation_context(a.title or "", a.description or "")
            or is_dist_local_crop_strategy_noise_context(a.title or "", a.description or "")
            or is_dist_local_org_tail_context(a.title or "", a.description or "")
            or is_dist_consumer_tail_context(a.title or "", a.description or "")
            or is_dist_macro_export_noise_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip())
            or is_dist_campaign_noise_context(a.title or "", a.description or "")
        )

    def _is_policy_weak_tail_story(a: Article) -> bool:
        if section_key != "policy":
            return False
        dom_local = normalize_host(a.domain or "")
        pr_local = (a.press or "").strip()
        return is_policy_general_macro_tail_context(
            a.title or "",
            a.description or "",
            dom_local,
            pr_local,
        ) or is_policy_event_tail_context(
            a.title or "",
            a.description or "",
            dom_local,
            pr_local,
        ) or is_title_livestock_dominant_context(
            a.title or "",
            a.description or "",
        ) or is_policy_forest_admin_noise_context(
            a.title or "",
            a.description or "",
        ) or is_policy_budget_drive_noise_context(
            a.title or "",
            a.description or "",
        )

    def _is_policy_noncore_only_story(a: Article) -> bool:
        if section_key != "policy":
            return False
        dom_local = normalize_host(a.domain or "")
        if dom_local not in POLICY_BRIEF_ONLY_DOMAINS:
            return False
        if press_priority(a.press, a.domain) >= 2:
            return False
        return is_policy_export_support_brief_context(
            a.title or "",
            a.description or "",
            dom_local,
            (a.press or "").strip(),
        )

    def _underfill_candidate_rank(a: Article) -> tuple[Any, ...] | None:
        txt_local = ((a.title or "") + " " + (a.description or "")).lower()
        dom_local = normalize_host(a.domain or "")
        pr_local = (a.press or "").strip()
        fit_sc = section_fit_score(a.title or "", a.description or "", sec_conf)
        tier = press_priority(a.press, a.domain)
        pub_sort = getattr(a, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST)
        if section_key == "supply":
            signal_hits = count_any(
                txt_local,
                [t.lower() for t in ("가격", "시세", "수급", "작황", "출하", "반입", "물량", "재고", "경락", "경매")],
            )
            feature_kind = supply_feature_context_kind(a.title or "", a.description or "")
            issue_bucket = supply_issue_context_bucket(a.title or "", a.description or "")
            price_outlook = is_supply_price_outlook_context(a.title or "", a.description or "")
            shock_issue = issue_bucket == "commodity_issue" and (
                count_any(txt_local, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_INPUT_TERMS])
                + count_any(txt_local, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_CLIMATE_TERMS])
            ) >= 2
            feature_like = feature_kind is not None
            direct_supply = has_direct_supply_chain_signal(txt_local)
            broad_macro = is_broad_macro_price_context(a.title or "", a.description or "")
            horti_sc = best_horti_score(a.title or "", a.description or "")
            horti_title_sc = best_horti_score(a.title or "", "")
            if _is_supply_policy_like_tail_story(a) or _is_supply_dist_like_tail_story(a) or _is_supply_weak_tail_story(a):
                return None
            if broad_macro and tier == 1 and (not direct_supply) and (not feature_like):
                return None
            if not (
                feature_like
                or direct_supply
                or price_outlook
                or (fit_sc >= 1.3 and signal_hits >= 2 and (horti_sc >= 1.8 or horti_title_sc >= 1.2))
            ):
                return None
            return (
                1 if direct_supply else 0,
                1 if price_outlook else 0,
                1 if shock_issue else 0,
                1 if feature_kind == "issue" else 0,
                1 if issue_bucket == "export_recovery" else 0,
                1 if feature_kind == "field" else 0,
                1 if feature_kind == "quality" else 0,
                1 if feature_kind == "promo" else 0,
                0 if broad_macro and (not direct_supply) else 1,
                1 if tier >= 2 else 0,
                round(fit_sc, 3),
                round(horti_sc, 3),
                round(float(getattr(a, "score", 0.0) or 0.0), 3),
                pub_sort,
            )
        if section_key == "dist":
            market_anchor_hits = count_any(
                txt_local,
                [t.lower() for t in ("가락시장", "도매시장", "공판장", "공영도매시장", "경락", "경매", "반입", "온라인도매시장", "온라인 도매시장", "산지유통", "산지유통센터")],
            )
            apc_ctx_local = has_apc_agri_context(txt_local)
            if apc_ctx_local:
                market_anchor_hits += 1
            market_disruption = is_dist_market_disruption_context(a.title or "", a.description or "")
            disruption_scope = dist_market_disruption_scope(a.title or "", a.description or "")
            disruption_rank = 2 if disruption_scope == "systemic" else 1 if market_disruption else 0
            market_ops = is_dist_market_ops_context(a.title or "", a.description or "", dom_local, pr_local)
            supply_center = is_dist_supply_management_center_context(a.title or "", a.description or "")
            sales_channel_ops = is_dist_sales_channel_ops_context(a.title or "", a.description or "")
            field_market_response = is_dist_field_market_response_context(a.title or "", a.description or "", dom_local, pr_local)
            export_shipping = is_dist_export_shipping_context(a.title or "", a.description or "")
            export_field = is_dist_export_field_context(a.title or "", a.description or "", dom_local, pr_local)
            export_support_hub = is_dist_export_support_hub_context(a.title or "", a.description or "", dom_local, pr_local)
            if _is_dist_weak_tail_story(a):
                return None
            local_org_feature = is_local_agri_org_feature_context(a.title or "", a.description or "")
            local_field_profile = is_dist_local_field_profile_context(a.title or "", a.description or "")
            strong_local_org = local_field_profile or (local_org_feature and apc_ctx_local)
            if field_market_response:
                market_anchor_hits = max(market_anchor_hits, 1)
            if local_field_profile:
                market_anchor_hits = max(market_anchor_hits, 1)
            if not (
                disruption_rank
                or market_ops
                or supply_center
                or sales_channel_ops
                or field_market_response
                or local_field_profile
                or export_shipping
                or export_field
                or export_support_hub
                or strong_local_org
                or market_anchor_hits >= 2
                or (fit_sc >= 1.6 and market_anchor_hits >= 1)
            ):
                return None
            return (
                disruption_rank,
                1 if market_ops else 0,
                1 if supply_center else 0,
                1 if sales_channel_ops else 0,
                1 if field_market_response else 0,
                1 if market_anchor_hits >= 2 else 0,
                1 if local_field_profile else 0,
                1 if strong_local_org else 0,
                1 if export_support_hub else 0,
                1 if export_field else 0,
                1 if export_shipping else 0,
                1 if tier >= 2 else 0,
                round(fit_sc, 3),
                round(float(getattr(a, "score", 0.0) or 0.0), 3),
                pub_sort,
            )
        if section_key == "policy":
            officialish = policy_domain_override(dom_local, txt_local) or (dom_local in POLICY_DOMAINS) or (pr_local in ("정책브리핑", "농식품부"))
            market_brief = is_policy_market_brief_context(txt_local, dom_local, pr_local)
            stabilization = is_supply_stabilization_policy_context(txt_local, dom_local, pr_local)
            announcement = is_policy_announcement_issue(txt_local, dom_local, pr_local)
            macro = is_macro_policy_issue(txt_local)
            major_issue = is_policy_major_issue_context(a.title or "", a.description or "", dom_local, pr_local)
            export_support_brief = is_policy_export_support_brief_context(a.title or "", a.description or "", dom_local, pr_local)
            local_price_support = is_policy_local_price_support_context(a.title or "", a.description or "")
            price_collapse_issue = is_policy_price_collapse_issue_context(a.title or "", a.description or "")
            local_program = is_local_agri_policy_program_context(txt_local)
            policy_anchor_stats = _policy_horti_anchor_stats(a.title or "", a.description or "", dom_local, pr_local)
            if policy_anchor_stats.get("livestock_dominant"):
                return None
            if _is_policy_weak_tail_story(a):
                return None
            if is_retail_sales_trend_context(txt_local):
                return None
            if not (market_brief or stabilization or announcement or macro or major_issue or export_support_brief or local_price_support or local_program):
                return None
            if (not export_support_brief) and (not policy_anchor_stats.get("anchor_ok")):
                return None
            if tier < 2 and (not officialish) and (not export_support_brief) and (not local_price_support) and (not local_program) and (not major_issue):
                return None
            if fit_sc < 1.2 and (not officialish) and (not market_brief) and (not export_support_brief) and (not local_price_support) and (not local_program) and (not major_issue):
                return None
            return (
                1 if officialish else 0,
                1 if local_price_support else 0,
                1 if price_collapse_issue else 0,
                1 if local_program else 0,
                1 if major_issue else 0,
                1 if export_support_brief else 0,
                1 if market_brief else 0,
                1 if stabilization else 0,
                1 if announcement else 0,
                1 if macro else 0,
                1 if tier >= 2 else 0,
                round(fit_sc, 3),
                round(float(getattr(a, "score", 0.0) or 0.0), 3),
                pub_sort,
            )
        if section_key == "pest":
            if not (is_pest_story_focus_strong(a.title or "", a.description or "") or is_pest_control_policy_context(txt_local)):
                return None
            return (
                1 if is_pest_control_policy_context(txt_local) else 0,
                1 if tier >= 2 else 0,
                round(float(getattr(a, "score", 0.0) or 0.0), 3),
                pub_sort,
            )
        return None

    def _is_policy_tail_candidate(a: Article) -> bool:
        if section_key != "policy":
            return True
        txt_local = ((a.title or "") + " " + (a.description or "")).lower()
        dom_local = normalize_host(a.domain or "")
        pr_local = (a.press or "").strip()
        if _is_policy_weak_tail_story(a):
            return False
        if is_retail_sales_trend_context(txt_local):
            return False
        market_brief = is_policy_market_brief_context(txt_local, dom_local, pr_local)
        stabilization = is_supply_stabilization_policy_context(txt_local, dom_local, pr_local)
        announcement = is_policy_announcement_issue(txt_local, dom_local, pr_local)
        major_issue = is_policy_major_issue_context(a.title or "", a.description or "", dom_local, pr_local)
        export_support_brief = is_policy_export_support_brief_context(a.title or "", a.description or "", dom_local, pr_local)
        local_price_support = is_policy_local_price_support_context(a.title or "", a.description or "")
        local_program = is_local_agri_policy_program_context(txt_local)
        policy_anchor_stats = _policy_horti_anchor_stats(a.title or "", a.description or "", dom_local, pr_local)
        if policy_anchor_stats.get("livestock_dominant"):
            return False
        if not (
            market_brief
            or stabilization
            or announcement
            or major_issue
            or export_support_brief
            or local_price_support
            or local_program
        ):
            return False
        if (not export_support_brief) and (not policy_anchor_stats.get("anchor_ok")):
            return False
        if press_priority(a.press, a.domain) < 2 and not (
            _is_policy_official(a)
            or market_brief
            or local_price_support
            or local_program
            or major_issue
            or export_support_brief
        ):
            return False
        return True

    def _is_strong_underfill_candidate(a: Article) -> bool:
        return _underfill_candidate_rank(a) is not None

    # 1) 엄격 코어 2개
    if section_key == "dist":
        for a in pool:
            if len(core) >= 1:
                break
            if dist_market_disruption_scope(a.title or "", a.description or "") != "systemic":
                continue
            if a.score < core_min:
                continue
            if _already_used(a):
                continue
            if not _low_core_allowed(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if not _source_ok_local(a):
                continue
            a.is_core = True
            _record_selection(a, "core")
            core.append(a)
            _mark_used(a)
            _source_take(a)
    for a in pool:
        if len(core) >= 2:
            break
        if a.score < core_min:
            continue
        if _already_used(a):
            continue
        if not _low_core_allowed(a):
            continue
        # dist: 지역 단신/공지형은 core 후보에서 제외(진짜 이슈가 밀리는 것을 방지)
        if section_key == "dist" and is_local_brief_text(a.title or "", a.description or "", section_key):
            continue
        if section_key == "dist" and _is_dist_weak_tail_story(a):
            continue
        if section_key == "policy" and _is_policy_weak_tail_story(a):
            continue
        if section_key == "policy" and _is_policy_noncore_only_story(a):
            continue
        if section_key == "dist" and (is_local_agri_infra_designation_context(a.title or "", a.description or "") or is_local_agri_org_feature_context(a.title or "", a.description or "")):
            continue
        if section_key == "supply" and (is_flower_consumer_trend_context((a.title + " " + a.description).lower()) or is_fruit_foodservice_event_context((a.title + " " + a.description).lower())):
            continue
        if section_key == "supply":
            mix = (a.title + " " + a.description).lower()
            dom = normalize_host(a.domain or "")
            pr = (a.press or "").strip()
            try:
                _h = best_horti_score(a.title or "", a.description or "")
            except Exception:
                _h = 0.0
            # ✅ 정책/통상성 강하고 품목 영향이 약한 기사(제도/통관/할당관세 등)는
            # supply '핵심2'를 잠식하지 않도록 제외한다. (policy 섹션에서 다룸)
            if is_generic_import_item_context(mix):
                continue
            if is_supply_stabilization_policy_context(mix, dom, pr):
                continue
            if is_policy_market_brief_context(mix, dom, pr):
                continue
            if is_policy_announcement_issue(mix, dom, pr):
                continue
            if is_trade_policy_issue(mix) and _h < 2.2:
                continue
            if is_macro_policy_issue(mix) and count_any((a.title or "").lower(), [t.lower() for t in ("과일", "과수", "채소", "화훼", "농산물", "청과")]) == 0 and best_horti_score(a.title or "", "") < 1.6 and best_horti_score(a.title or "", a.description or "") < 1.8 and ((not has_direct_supply_chain_signal(mix)) or is_policy_market_brief_context(mix, dom, pr)):
                continue
            if is_local_agri_org_feature_context(a.title or "", a.description or ""):
                continue
            if _is_supply_dist_like_tail_story(a):
                continue
            if _is_supply_weak_tail_story(a):
                continue
            # supply 핵심2는 품목 수급 중심으로 구성: topic이 정책이면 core에서 제외
            if (a.topic or "").strip() == "정책":
                continue
        fit_sc_core = section_fit_score(a.title or "", a.description or "", sec_conf)
        if fit_sc_core < core_fit_min and a.score < (core_min + 1.8):
            continue
        if not _headline_gate(a, section_key):
            continue
        if any(_is_similar_title(a.title_key, b.title_key) for b in core):
            continue
        if any(_is_similar_story(a, b, section_key) for b in core):
            continue
        if _managed_repeat_too_close(a, core):
            continue
        # policy 섹션: 로컬/저티어(1) 매체가 "핵심2"를 잠식하지 않도록 core 후보에서 제외
        if section_key == "policy" and press_priority(a.press, a.domain) == 1:
            mix_local = ((a.title or "") + " " + (a.description or "")).lower()
            if not is_policy_market_brief_context(mix_local, normalize_host(a.domain or ""), (a.press or "").strip()):
                continue
        if _is_trade_press(a) and trade_core_count >= trade_core_cap:
            continue

        if not _source_ok_local(a):
            continue

        a.is_core = True
        _record_selection(a, "core")
        core.append(a)
        _mark_used(a)
        _source_take(a)
        if _is_trade_press(a):
            trade_core_count += 1

    # 2) 코어 부족 시: 약간 완화(여전히 임계치 이상 + 중복 제거) — 하지만 억지 채움 금지
    if len(core) < 2:
        for a in pool:
            if len(core) >= 2:
                break
            # dist 완화 선발 임계값: APC 인프라/시설 기사(준공/가동/선별/저온저장 등)는 소폭 완화
            text = ((a.title or "") + " " + (a.description or "")).lower()
            apc_ctx_local = has_apc_agri_context(text)
            dist_eff_thr = thr
            if section_key == "dist" and apc_ctx_local and any(w in text for w in ("준공","완공","개장","개소","가동","선별","선과","저온","저온저장","저장고","ca저장")):
                dist_eff_thr = max(0.0, thr - 0.8)
            if a.score < dist_eff_thr:
                continue
            if _already_used(a):
                continue
            if not _low_core_allowed(a):
                continue
            # dist: 지역 단신/공지형은 core 후보에서 제외
            if section_key == "dist" and is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            if section_key == "dist" and _is_dist_weak_tail_story(a):
                continue
            if section_key == "policy" and _is_policy_weak_tail_story(a):
                continue
            if section_key == "policy" and _is_policy_noncore_only_story(a):
                continue
            if section_key == "dist" and (is_local_agri_infra_designation_context(a.title or "", a.description or "") or is_local_agri_org_feature_context(a.title or "", a.description or "")):
                continue
            if section_key == "supply" and is_flower_consumer_trend_context((a.title + " " + a.description).lower()):
                continue
            if section_key == "supply":
                dom = normalize_host(a.domain or "")
                pr = (a.press or "").strip()
                if is_supply_stabilization_policy_context(text, dom, pr):
                    continue
                if is_policy_market_brief_context(text, dom, pr):
                    continue
                if is_local_agri_org_feature_context(a.title or "", a.description or ""):
                    continue
                if _is_supply_dist_like_tail_story(a):
                    continue
                if _is_supply_weak_tail_story(a):
                    continue
                if (a.topic or "").strip() == "정책":
                    continue
            # 원산지/단속/검역/수출 키워드만으로 걸린 일반 기사 누수 방지(시장/APC 앵커가 없으면 제외)
            ops_hits = count_any(text, [t.lower() for t in ("원산지","부정유통","단속","검역","통관","수출")])
            market_anchor_hits = count_any(text, [t.lower() for t in ("가락시장","도매시장","공판장","공영도매시장","경락","경매","반입","온라인 도매시장","산지유통","산지유통센터")])
            apc_ctx_local = has_apc_agri_context(text)
            agri_anchor_hits_local = count_any(text, [t.lower() for t in ("농산물","농업","농식품","원예","과수","과일","채소","화훼","절화","청과")])
            if ops_hits >= 1 and market_anchor_hits == 0 and (not apc_ctx_local) and agri_anchor_hits_local == 0 and best_horti_score(a.title or "", a.description or "") < 1.9:
                continue
            fit_sc_core = section_fit_score(a.title or "", a.description or "", sec_conf)
            if fit_sc_core < (core_fit_min - 0.1) and a.score < (core_min + 1.2):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in core):
                continue
            if _managed_repeat_too_close(a, core, score_gap_override=1.2):
                continue
            # policy 섹션: 로컬/저티어(1) 매체가 "핵심2"를 잠식하지 않도록 core 후보에서 제외
            if section_key == "policy" and press_priority(a.press, a.domain) == 1:
                mix_local = ((a.title or "") + " " + (a.description or "")).lower()
                if not is_policy_market_brief_context(mix_local, normalize_host(a.domain or ""), (a.press or "").strip()):
                    continue
            if _is_trade_press(a) and trade_core_count >= trade_core_cap:
                continue

            if not _source_ok_local(a):
                continue

            a.is_core = True
            _record_selection(a, "core")
            core.append(a)
            _mark_used(a)
            _source_take(a)

    # policy는 저티어 core를 막은 뒤에도 메이저 소스 핵심이 0건으로 비지 않게 1건은 백필한다.
    if section_key == "policy" and len(core) == 0:
        for a in pool:
            if _already_used(a):
                continue
            if _is_policy_weak_tail_story(a):
                continue
            if _is_policy_noncore_only_story(a):
                continue
            if _is_low_core_source(a) or press_priority(a.press, a.domain) < 2:
                continue
            fit_sc_core = section_fit_score(a.title or "", a.description or "", sec_conf)
            if fit_sc_core < (core_fit_min - 0.2) and a.score < max(thr, core_min - 0.8):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in core):
                continue
            if any(_is_similar_story(a, b, section_key) for b in core):
                continue
            if _managed_repeat_too_close(a, core, score_gap_override=1.0):
                continue
            if _is_trade_press(a) and trade_core_count >= trade_core_cap:
                continue
            if not _source_ok_local(a):
                continue
            a.is_core = True
            _record_selection(a, "core")
            core.append(a)
            _mark_used(a)
            _source_take(a)
            if _is_trade_press(a):
                trade_core_count += 1
            break

    # 3) 유통(dist) 섹션: 강한 현장 앵커(도매시장/공영도매/APC 준공/선별/저온/물류/원산지 단속/수출 검역 등) 0~2건 추가
    final: list[Article] = []
    for a in core:
        final.append(a)

    if section_key == "dist":
        anchor_terms = ("가락시장", "도매시장", "공영도매시장", "공판장", "청과", "경락", "경매", "반입",
                        "산지유통", "산지유통센터", "선별", "저온", "저온저장", "저장고", "ca저장", "물류",
                        "원산지", "부정유통", "단속", "검역", "통관", "수출", "온라인 도매시장", "하나로마트", "자조금")
        anchors = 0
        for a in pool:
            if anchors >= 2:
                break
            if a in final:
                continue
            if _already_used(a):
                continue
            # 지역 단신/공지형은 dist 앵커 추가 단계에서도 제외
            if is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            if _is_dist_weak_tail_story(a):
                continue
            text = (a.title + " " + a.description).lower()
            local_org_feature = is_local_agri_org_feature_context(a.title or "", a.description or "")
            local_field_profile = is_dist_local_field_profile_context(a.title or "", a.description or "")
            field_market_response = is_dist_field_market_response_context(
                a.title or "",
                a.description or "",
                normalize_host(a.domain or ""),
                (a.press or "").strip(),
            )
            strong_local_org = local_field_profile or (local_org_feature and has_apc_agri_context(text))
            has_anchor = any(t.lower() in text for t in anchor_terms) or has_apc_agri_context(text) or strong_local_org or field_market_response
            if not has_anchor:
                continue
            # 추가 안전장치: 농산물/원예 앵커가 약하면 '일반 물류/경제'로 보고 제외
            agri_anchor_hits = count_any(text, [t.lower() for t in ("농산물","농업","농식품","원예","과수","과일","채소","화훼","절화","청과")])
            if agri_anchor_hits == 0 and (not field_market_response) and best_horti_score(a.title, a.description) < 1.8 and count_any(text, [t.lower() for t in ("가락시장","도매시장","공판장","공영도매시장","경락","경매","반입","온라인 도매시장","산지유통","산지유통센터")]) == 0:
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if not _source_ok_local(a):
                continue
            if a.score < thr:
                continue

            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            if _managed_repeat_too_close(a, final, score_gap_override=1.0):
                continue

            if _supply_feature_topic_repeat(a, final):
                continue
            _record_selection(a, "dist_anchor_backfill")
            final.append(a)
            _mark_used(a)
            _source_take(a)
            anchors += 1


# 4) 나머지(최대 max_n): 임계치 이상 + 출처 캡 + 중복 제거
    if MMR_DIVERSITY_ENABLED and len(pool) >= MMR_DIVERSITY_MIN_POOL and (max_n - len(final)) >= 2:
        # ✅ MMR(soft diversity): 중복은 아니지만 '비슷한 기사' 연속 노출을 완화
        def _mmr_tri(a: Article) -> set[str]:
            tri = getattr(a, "_story_tri", None)
            if tri is None:
                at, ad = _story_text(a)
                tri = _trigrams(_norm_story_text(at, ad))
                setattr(a, "_story_tri", tri)
            return tri

        eligible: list[Article] = []
        for a in pool:
            if a in final:
                continue
            # dist: 이미 2건 이상 확보된 상태에서는 지역 단신/공지형 기사는 추가하지 않음(빈칸 메우기용으로만 허용)
            if section_key == "dist" and len(final) >= 2 and is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            if section_key == "dist" and _is_dist_weak_tail_story(a):
                continue
            if section_key == "policy" and _is_policy_weak_tail_story(a):
                continue
            if section_key == "policy" and not _is_policy_tail_candidate(a):
                continue
            # 점수 꼬리(tail)가 약하면 추가하지 않는다(필요시 2~3개로 종료)
            if a.score < tail_cut:
                continue
            if _already_used(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            # 출처 캡은 MMR 선발에서도 유지(선정 시점에 다시 확인)
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            if _managed_repeat_too_close(a, final, score_gap_override=1.0):
                continue
            if _supply_feature_topic_repeat(a, final):
                continue
            if _is_supply_policy_like_tail_story(a):
                continue
            if _is_supply_dist_like_tail_story(a):
                continue
            if _is_supply_weak_tail_story(a):
                continue
            eligible.append(a)

        while len(final) < max_n and eligible:
            sel_tris = [_mmr_tri(x) for x in final] if final else []
            best: Article | None = None
            best_tuple: tuple[float, float, tuple[int, Any | datetime]] | None = None

            for a in eligible:
                # 출처 캡/중복/유사 스토리/헤드라인 게이트는 "선정 시점"에도 유지
                if not _source_ok_local(a):
                    continue
                if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                    continue
                if any(_is_similar_story(a, b, section_key) for b in final):
                    continue
                if _managed_repeat_too_close(a, final, score_gap_override=0.9):
                    continue
                if section_key == "policy" and not _is_policy_tail_candidate(a):
                    continue

                if _supply_feature_topic_repeat(a, final):
                    continue
                if _is_supply_policy_like_tail_story(a):
                    continue
                if _is_supply_dist_like_tail_story(a):
                    continue
                if _is_supply_weak_tail_story(a):
                    continue
                tri_a = _mmr_tri(a)
                max_sim = 0.0
                if sel_tris and tri_a:
                    for tri_b in sel_tris:
                        max_sim = max(max_sim, _jaccard(tri_a, tri_b))

                # penalty scale(3.0)은 점수 스케일(약 6~16)에 맞춘 보수적 기본값
                commodity_overlap_penalty = _managed_overlap_penalty(a, final)
                mmr_val = float(getattr(a, "score", 0.0) or 0.0) - (MMR_DIVERSITY_LAMBDA * 3.0 * max_sim) - commodity_overlap_penalty

                # tie-breaker: 본 점수/매체/최신 순
                tie = (press_priority(a.press, a.domain), getattr(a, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST))
                cand = (mmr_val, float(getattr(a, "score", 0.0) or 0.0) - (0.35 * commodity_overlap_penalty), tie)

                if best is None or best_tuple is None or cand > best_tuple:
                    best = a
                    best_tuple = cand

            if best is None:
                break

            _record_selection(best, "tail")
            final.append(best)
            _mark_used(best)
            _source_take(best)
            eligible = [x for x in eligible if x is not best]

    else:
        for a in pool:
            if len(final) >= max_n:
                break
            if a in final:
                continue
            # dist: 이미 2건 이상 확보된 상태에서는 지역 단신/공지형 기사는 추가하지 않음(빈칸 메우기용으로만 허용)
            if section_key == "dist" and len(final) >= 2 and is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            if section_key == "dist" and _is_dist_weak_tail_story(a):
                continue
            if section_key == "policy" and _is_policy_weak_tail_story(a):
                continue
            if section_key == "policy" and not _is_policy_tail_candidate(a):
                continue
            # 점수 꼬리(tail)가 약하면 추가하지 않는다(필요시 2~3개로 종료)
            if a.score < tail_cut:
                continue
            if _already_used(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if not _source_ok_local(a):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            if _managed_repeat_too_close(a, final, score_gap_override=0.9):
                continue
            if _supply_feature_topic_repeat(a, final):
                continue
            if _is_supply_policy_like_tail_story(a):
                continue
            if _is_supply_dist_like_tail_story(a):
                continue
            if _is_supply_weak_tail_story(a):
                continue
            _record_selection(a, "tail")
            final.append(a)
            _mark_used(a)
            _source_take(a)
# 4.2) dist(유통/현장) 섹션 소프트 백필:
    # - 어떤 날은 동적 임계치/꼬리 컷으로 1~2건만 남는 경우가 있음.
    # - 이때 '지방지라도 내용이 유의미한 기사'를 하단에 1~2건 정도 추가 노출(억지 채움은 금지).
    if section_key == "dist" and len(final) < min(3, max_n):
        need = min(3, max_n) - len(final)
        # 임계치보다 살짝 완화하되, BASE_MIN_SCORE 아래로는 내려가지 않음
        relax_cut = max(BASE_MIN_SCORE.get("dist", 7.2) - 0.6, thr - 2.0)
        # 출처 캡도 아주 소폭 완화(로컬 1건 추가 허용)
        tier1_cap_relax = max(tier1_cap, 2)
        tier2_cap_relax = max(tier2_cap, 4)

        def _source_ok_relaxed(a: Article) -> bool:
            t = press_priority(a.press, a.domain)
            if t == 1:
                return tier_count[1] < tier1_cap_relax
            if t == 2:
                return tier_count[2] < tier2_cap_relax
            return True

        for a in candidates_sorted:
            if need <= 0 or len(final) >= max_n:
                break
            if a in final:
                continue
            local_field_profile = is_dist_local_field_profile_context(a.title or "", a.description or "")
            systemic_disruption = dist_market_disruption_scope(a.title or "", a.description or "") == "systemic"
            effective_cut = -20.0 if local_field_profile else max(BASE_MIN_SCORE.get("dist", 7.2) - 0.6, thr - 5.0) if systemic_disruption else relax_cut
            if a.score < effective_cut:
                continue
            if _already_used(a):
                continue
            if _is_dist_weak_tail_story(a):
                continue
            # 정치/사건성 제목 누수는 다시 한번 방어(점수는 높아도 dist 핵심과 무관한 경우가 있음)
            ttl_l = (a.title or "").lower()
            if any(w in ttl_l for w in ("제주4.3", "4.3", "희생자", "보상", "내란", "탄핵", "계엄")) and best_horti_score(a.title or "", "") < 1.3:
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if not _source_ok_relaxed(a):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            a.is_core = False
            _record_selection(a, "dist_underfill")
            final.append(a)
            _mark_used(a)
            _source_take(a)
            need -= 1
    # 4.3) dist(유통/현장) 섹션 로컬 조직 기사 백필:
    # - 유통 핵심이 거의 비는 날에만, APC/수출 등 실무 앵커가 붙은 경우에 한해 제한적으로 허용한다.
    if section_key == "dist" and len(final) == 0:
        local_relax_cut = max(5.8, BASE_MIN_SCORE.get("dist", 7.2) - 1.2)
        for a in candidates_sorted:
            if len(final) >= max_n:
                break
            if a in final:
                continue
            if not is_local_agri_org_feature_context(a.title or "", a.description or ""):
                continue
            if _is_dist_weak_tail_story(a):
                continue
            txt_local = ((a.title or "") + " " + (a.description or "")).lower()
            if not (has_apc_agri_context(txt_local) or is_dist_export_shipping_context(a.title or "", a.description or "")):
                continue
            if a.score < local_relax_cut:
                continue
            if _already_used(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if not _source_ok_local(a):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            a.is_core = False
            _record_selection(a, "dist_local_backfill")
            final.append(a)
            _mark_used(a)
            _source_take(a)
            break

    # 4.5) supply 보강: section이 비는 날에는 품목 feature 기사 0~1건을 하단에 보강한다.
    # - 특정 품목만 우대하지 않고, 공급/현장/품질형 기사 전반에 공통 적용
    # - 이미 뽑힌 품목과 다른 topic을 우선해 품목 다양성을 유지
    if section_key == "supply" and len(final) < max_n:
        added = 0
        max_feature_backfill = min(2, max_n - len(final))
        selected_topics = {(x.topic or "").strip() for x in final if (x.topic or "").strip()}
        relax_cut = max(BASE_MIN_SCORE.get("supply", 7.0) - 0.6, thr - 2.8, 0.0)
        for prefer_unseen_topic in (True, False):
            if added >= max_feature_backfill or len(final) >= max_n:
                break
            for a in candidates_sorted:
                if added >= max_feature_backfill or len(final) >= max_n:
                    break
                if a in final:
                    continue
                if _already_used(a):
                    continue
                if a.score < relax_cut:
                    continue
                txt2 = (a.title + " " + a.description).lower()
                feature_kind = supply_feature_context_kind(a.title or "", a.description or "")
                flower_trend = is_flower_consumer_trend_context(txt2)
                if feature_kind is None and not flower_trend:
                    continue
                topic_name = (a.topic or "").strip()
                if prefer_unseen_topic and topic_name and topic_name in selected_topics:
                    continue
                if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                    continue
                if any(_is_similar_story(a, b, section_key) for b in final):
                    continue
                if _supply_feature_topic_repeat(a, final):
                    continue
                if _is_supply_policy_like_tail_story(a):
                    continue
                if _is_supply_dist_like_tail_story(a):
                    continue
                if _is_supply_weak_tail_story(a):
                    continue
                if not _headline_gate_relaxed(a, section_key):
                    continue
                if not _source_ok_local(a):
                    continue

                a.is_core = False
                _record_selection(a, "supply_feature_backfill")
                final.append(a)
                _mark_used(a)
                _source_take(a)
                if topic_name:
                    selected_topics.add(topic_name)
                added += 1

    if section_key == "supply" and len(final) >= max_n:
        feature_target = min(2, max_n)
        current_feature_count = sum(1 for x in final if is_supply_feature_article(x.title or "", x.description or ""))
        if current_feature_count < feature_target:
            selected_topics = {(x.topic or "").strip() for x in final if (x.topic or "").strip()}
            relax_cut = max(BASE_MIN_SCORE.get("supply", 7.0) - 0.6, thr - 2.8, 0.0)
            swaps_needed = feature_target - current_feature_count
            for prefer_unseen_topic in (True, False):
                if swaps_needed <= 0:
                    break
                for a in candidates_sorted:
                    if swaps_needed <= 0:
                        break
                    if a in final:
                        continue
                    if _already_used(a):
                        continue
                    if a.score < relax_cut:
                        continue
                    if not is_supply_feature_article(a.title or "", a.description or ""):
                        continue
                    topic_name = (a.topic or "").strip()
                    if prefer_unseen_topic and topic_name and topic_name in selected_topics:
                        continue
                    if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                        continue
                    if any(_is_similar_story(a, b, section_key) for b in final):
                        continue
                    if _supply_feature_topic_repeat(a, final):
                        continue
                    if _is_supply_policy_like_tail_story(a):
                        continue
                    if _is_supply_dist_like_tail_story(a):
                        continue
                    if _is_supply_weak_tail_story(a):
                        continue
                    if not _headline_gate_relaxed(a, section_key):
                        continue
                    victim_idxs = [
                        i for i, x in enumerate(final)
                        if (not getattr(x, "is_core", False)) and (not is_supply_feature_article(x.title or "", x.description or ""))
                    ]
                    if not victim_idxs:
                        continue
                    weak_victim_idxs = [i for i in victim_idxs if _is_supply_weak_tail_story(final[i]) or _is_supply_dist_like_tail_story(final[i])]
                    ranked_victim_idxs = weak_victim_idxs if weak_victim_idxs else victim_idxs
                    repl_idx = min(
                        ranked_victim_idxs,
                        key=lambda i: (
                            float(getattr(final[i], "score", 0.0) or 0.0),
                            1 if has_direct_supply_chain_signal(((final[i].title or "") + " " + (final[i].description or "")).lower()) else 0,
                            section_fit_score(final[i].title or "", final[i].description or "", sec_conf),
                        ),
                    )
                    victim = final[repl_idx]
                    required_margin = 0.2 if (_is_supply_weak_tail_story(victim) or _is_supply_dist_like_tail_story(victim)) else 1.2
                    if float(getattr(a, "score", 0.0) or 0.0) + required_margin < float(getattr(victim, "score", 0.0) or 0.0):
                        continue
                    _record_selection(a, "supply_feature_swap", f"replaced:{getattr(victim, 'selection_stage', '') or 'tail'}")
                    final[repl_idx] = a
                    _mark_used(a)
                    _source_take(a)
                    if topic_name:
                        selected_topics.add(topic_name)
                    swaps_needed -= 1

    # 4.6) underfill 강신호 백필:
    # - 섹션이 2~3건 수준에서 끝날 때, threshold/tail-cut 바로 아래의 강한 기사 1건을 추가로 살린다.
    # - dist도 시장 충격/현장 기사 쪽으로 1건 보강하고, policy는 공공/기관발 강기사 중심으로만 보강한다.
    strong_underfill_target_by_section = {"supply": 3, "policy": 3, "dist": 5, "pest": 3}
    strong_underfill_target = min(max_n, strong_underfill_target_by_section.get(section_key, 0))
    if strong_underfill_target and len(final) < strong_underfill_target:
        need = strong_underfill_target - len(final)
        relax_margin_by_section = {
            "supply": 4.2,
            "policy": 2.2,
            "dist": 5.0,
            "pest": 3.2,
        }
        relax_floor_offset_by_section = {
            "supply": 0.4,
            "policy": 0.5,
            "dist": 0.5,
            "pest": 0.6,
        }
        relax_cut = max(
            BASE_MIN_SCORE.get(section_key, 6.0) + relax_floor_offset_by_section.get(section_key, 0.0),
            thr - relax_margin_by_section.get(section_key, 2.4),
        )
        tier1_cap_relax = max(tier1_cap, 5 if section_key == "dist" else 2)
        tier2_cap_relax = max(tier2_cap, 3 if section_key in ("supply", "policy") else 4)

        def _underfill_score_cut(a: Article) -> float:
            cut = relax_cut
            txt_local = ((a.title or "") + " " + (a.description or "")).lower()
            if section_key == "supply":
                issue_bucket = supply_issue_context_bucket(a.title or "", a.description or "")
                shock_hits = count_any(txt_local, [w.lower() for w in _SUPPLY_FEATURE_ISSUE_INPUT_TERMS]) + count_any(
                    txt_local,
                    [w.lower() for w in _SUPPLY_FEATURE_ISSUE_CLIMATE_TERMS],
                )
                if issue_bucket == "commodity_issue" and shock_hits >= 2 and press_priority(a.press, a.domain) >= 2:
                    cut = min(cut, max(BASE_MIN_SCORE.get("supply", 6.0) + 0.4, thr - 11.5))
            elif section_key == "policy":
                if is_policy_local_price_support_context(a.title or "", a.description or ""):
                    cut = min(cut, max(BASE_MIN_SCORE.get("policy", 6.0) + 0.4, thr - 10.5))
            elif section_key == "dist":
                if is_dist_local_field_profile_context(a.title or "", a.description or ""):
                    return -20.0
                if is_dist_market_ops_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                    return -20.0
                if is_dist_supply_management_center_context(a.title or "", a.description or ""):
                    return -20.0
                if is_dist_sales_channel_ops_context(a.title or "", a.description or ""):
                    return -20.0
                if is_dist_export_support_hub_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                    return min(cut, max(BASE_MIN_SCORE.get("dist", 6.0) + 0.2, thr - 10.0))
                if is_dist_export_field_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                    return min(cut, max(BASE_MIN_SCORE.get("dist", 6.0) + 0.2, thr - 14.0))
                if dist_market_disruption_scope(a.title or "", a.description or "") == "systemic":
                    cut = min(cut, max(BASE_MIN_SCORE.get("dist", 6.0) + 0.5, thr - 5.0))
            elif section_key == "pest":
                if is_pest_control_policy_context(txt_local):
                    cut = min(cut, max(BASE_MIN_SCORE.get("pest", 6.6) + 0.2, thr - 7.0))
            return cut

        def _source_ok_underfill(a: Article) -> bool:
            t = press_priority(a.press, a.domain)
            if t == 1:
                return tier_count[1] < tier1_cap_relax
            if t == 2:
                return tier_count[2] < tier2_cap_relax
            return True

        ranked_underfill: list[tuple[tuple[Any, ...], Article]] = []
        for a in candidates_sorted:
            if a in final:
                continue
            if a.score < _underfill_score_cut(a):
                continue
            if _already_used(a):
                continue
            if section_key == "policy" and _is_policy_weak_tail_story(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            rank = _underfill_candidate_rank(a)
            if rank is None:
                continue
            ranked_underfill.append((rank, a))

        ranked_underfill.sort(key=lambda item: item[0], reverse=True)

        while need > 0 and len(final) < max_n:
            picked_any = False
            for _, a in ranked_underfill:
                if a in final:
                    continue
                if _already_used(a):
                    continue
                if not _source_ok_underfill(a):
                    continue
                if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                    continue
                if any(_is_similar_story(a, b, section_key) for b in final):
                    continue
                if _supply_feature_topic_repeat(a, final):
                    continue
                a.is_core = False
                _record_selection(a, "underfill")
                final.append(a)
                _mark_used(a)
                _source_take(a)
                need -= 1
                picked_any = True
                break
            if not picked_any:
                break

    # 4.7) policy 수출지원 단신 보강:
    # - 정책 섹션이 비는 날에는 수출지원 정책 단신 1건을 하단에만 제한적으로 허용한다.
    if section_key == "policy" and len(final) < min(max_n, 4):
        has_export_support_tail = any(
            is_policy_export_support_brief_context(
                a.title or "",
                a.description or "",
                normalize_host(a.domain or ""),
                (a.press or "").strip(),
            )
            for a in final
        )
        if not has_export_support_tail:
            policy_tail_cut = max(BASE_MIN_SCORE.get("policy", 6.0) + 0.5, thr - 10.0)
            ranked_policy_tail: list[tuple[tuple[Any, ...], Article]] = []
            for a in candidates_sorted:
                if a in final:
                    continue
                if _already_used(a):
                    continue
                dom_local = normalize_host(a.domain or "")
                pr_local = (a.press or "").strip()
                policy_anchor_stats = _policy_horti_anchor_stats(a.title or "", a.description or "", dom_local, pr_local)
                if policy_anchor_stats.get("livestock_dominant"):
                    continue
                if not is_policy_export_support_brief_context(a.title or "", a.description or "", dom_local, pr_local):
                    continue
                if float(getattr(a, "score", 0.0) or 0.0) < policy_tail_cut:
                    continue
                if _is_policy_weak_tail_story(a):
                    continue
                if not _headline_gate_relaxed(a, section_key):
                    continue
                if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                    continue
                if any(_is_similar_story(a, b, section_key) for b in final):
                    continue
                fit_sc = section_fit_score(a.title or "", a.description or "", sec_conf)
                tier = press_priority(a.press, a.domain)
                pub_sort = getattr(a, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST)
                ranked_policy_tail.append((
                    (
                        1 if tier >= 2 else 0,
                        round(fit_sc, 3),
                        round(float(getattr(a, "score", 0.0) or 0.0), 3),
                        pub_sort,
                    ),
                    a,
                ))

            ranked_policy_tail.sort(key=lambda item: item[0], reverse=True)
            for _, a in ranked_policy_tail:
                if len(final) >= max_n:
                    break
                if a in final:
                    continue
                if _already_used(a):
                    continue
                if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                    continue
                if any(_is_similar_story(a, b, section_key) for b in final):
                    continue
                a.is_core = False
                _record_selection(a, "policy_export_support_backfill")
                final.append(a)
                _mark_used(a)
                _source_take(a)
                break

    # 4.8) policy 주요이슈 보강:
    # - 정책 섹션이 2~3건에서 비는 날에는, 공식/의사결정형 '주요 이슈' 기사 1~2건을 하단에 보강한다.
    if section_key == "policy" and len(final) < min(max_n, 4):
        target = min(max_n, 4)
        policy_issue_tail_cut = max(BASE_MIN_SCORE.get("policy", 6.0) + 0.5, thr - 14.0)
        ranked_policy_issue_tail: list[tuple[tuple[Any, ...], Article]] = []
        for a in candidates_sorted:
            if a in final:
                continue
            if _already_used(a):
                continue
            dom_local = normalize_host(a.domain or "")
            pr_local = (a.press or "").strip()
            policy_anchor_stats = _policy_horti_anchor_stats(a.title or "", a.description or "", dom_local, pr_local)
            if policy_anchor_stats.get("livestock_dominant"):
                continue
            if is_policy_export_support_brief_context(a.title or "", a.description or "", dom_local, pr_local):
                continue
            if not is_policy_major_issue_context(a.title or "", a.description or "", dom_local, pr_local):
                continue
            if not policy_anchor_stats.get("anchor_ok"):
                continue
            if float(getattr(a, "score", 0.0) or 0.0) < policy_issue_tail_cut:
                continue
            if _is_policy_weak_tail_story(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            fit_sc = section_fit_score(a.title or "", a.description or "", sec_conf)
            tier = press_priority(a.press, a.domain)
            local_price_support = is_policy_local_price_support_context(a.title or "", a.description or "")
            price_collapse_issue = is_policy_price_collapse_issue_context(a.title or "", a.description or "")
            local_program = is_local_agri_policy_program_context(((a.title or "") + " " + (a.description or "")).lower())
            pub_sort = getattr(a, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST)
            ranked_policy_issue_tail.append((
                (
                    1 if local_price_support else 0,
                    1 if price_collapse_issue else 0,
                    1 if local_program else 0,
                    1 if _is_policy_official(a) else 0,
                    1 if tier >= 2 else 0,
                    round(fit_sc, 3),
                    round(float(getattr(a, "score", 0.0) or 0.0), 3),
                    pub_sort,
                ),
                a,
            ))

        ranked_policy_issue_tail.sort(key=lambda item: item[0], reverse=True)
        for _, a in ranked_policy_issue_tail:
            if len(final) >= target or len(final) >= max_n:
                break
            if a in final:
                continue
            if _already_used(a):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            a.is_core = False
            _record_selection(a, "policy_major_issue_backfill")
            final.append(a)
            _mark_used(a)
            _source_take(a)


    # 강제 섹션 이동 기사(예: policy->pest)는 최종 노출에서 사라지지 않도록 우선 포함 보장
    forced_items = [a for a in candidates_sorted if getattr(a, "forced_section", "") == section_key]
    for fa in forced_items:
        if fa in final:
            continue
        if len(final) < max_n:
            _record_selection(fa, "forced_section", getattr(fa, "forced_section", "") or section_key)
            final.append(fa)
            continue
        # 공간이 없으면 최하위 점수 1건을 대체
        if final:
            repl_idx = min(range(len(final)), key=lambda i: float(getattr(final[i], "score", 0.0) or 0.0))
            _record_selection(fa, "forced_section", getattr(fa, "forced_section", "") or section_key)
            final[repl_idx] = fa

    # pest 섹션 안전장치: 방제 실행형 문맥 기사(예찰/약제/전수조사 등)가 최종 선발에서 밀려 사라지지 않도록 보장
    if section_key == "pest":
        exec_like = [a for a in candidates_sorted if is_pest_control_policy_context(((a.title or "") + " " + (a.description or "")).lower())]
        keep_exec = []
        for a in final:
            try:
                if is_pest_control_policy_context(((a.title or "") + " " + (a.description or "")).lower()):
                    keep_exec.append(a)
            except Exception:
                pass

        # 실행형 기사 최대 2건까지 보장
        need_exec = max(0, min(2, max_n) - len(keep_exec))
        if need_exec > 0:
            for ea in exec_like:
                if need_exec <= 0:
                    break
                if ea in final:
                    continue
                if any(_is_similar_story(ea, x, section_key) for x in final):
                    continue
                if len(final) < max_n:
                    _record_selection(ea, "pest_exec_backfill")
                    final.append(ea)
                    need_exec -= 1
                    continue
                if final:
                    # 이미 들어간 실행형 후보를 다시 밀어내지 않도록 non-exec 최하위부터 교체
                    non_exec_idx = [i for i, x in enumerate(final) if not is_pest_control_policy_context(((x.title or "") + " " + (x.description or "")).lower())]
                    if non_exec_idx:
                        repl_idx = min(non_exec_idx, key=lambda i: float(getattr(final[i], "score", 0.0) or 0.0))
                    else:
                        repl_idx = min(range(len(final)), key=lambda i: float(getattr(final[i], "score", 0.0) or 0.0))
                    _record_selection(ea, "pest_exec_swap")
                    final[repl_idx] = ea
                    need_exec -= 1

    # pest 섹션 지역 다변화 보강: underfill일 때는 서로 다른 지역의 실행형 기사도 1~2건 더 허용
    if section_key == "pest" and len(final) < min(4, max_n):
        target = min(4, max_n)
        relax_cut = max(BASE_MIN_SCORE.get("pest", 6.6), thr - 3.2)
        tier1_cap_relax = max(tier1_cap, 3)
        tier2_cap_relax = max(tier2_cap, 4)
        selected_regions = {_pest_region_or_fallback_key(x) for x in final if _pest_region_or_fallback_key(x)}
        selected_footprints = {token for x in final for token in _pest_story_footprint_tokens(x)}

        def _source_ok_pest_region(a: Article) -> bool:
            t = press_priority(a.press, a.domain)
            if t == 1:
                return tier_count[1] < tier1_cap_relax
            if t == 2:
                return tier_count[2] < tier2_cap_relax
            return True

        for a in candidates_sorted:
            if len(final) >= target or len(final) >= max_n:
                break
            if a in final:
                continue
            if a.score < relax_cut:
                continue
            if _already_used(a):
                continue
            if section_key == "policy" and _is_policy_weak_tail_story(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if not _source_ok_pest_region(a):
                continue
            txt_local = ((a.title or "") + " " + (a.description or "")).lower()
            if not (is_pest_control_policy_context(txt_local) or is_pest_story_focus_strong(a.title or "", a.description or "")):
                continue
            region_key = _pest_region_or_fallback_key(a)
            if not region_key or region_key in selected_regions:
                continue
            footprint_tokens = set(_pest_story_footprint_tokens(a))
            if footprint_tokens and (footprint_tokens & selected_footprints):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            a.is_core = False
            _record_selection(a, "pest_region_backfill")
            final.append(a)
            _mark_used(a)
            _source_take(a)
            selected_regions.add(region_key)
            selected_footprints.update(footprint_tokens)
    # 마지막 안전장치: 동일 URL 중복 제거
    seen = set()
    deduped: list[Article] = []
    for a in final:
        k = a.canon_url or _dup_key(a)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(a)

    if section_key == "pest":
        pest_unique: list[Article] = []
        selected_footprints: set[str] = set()
        for a in deduped:
            footprint_tokens = set(_pest_story_footprint_tokens(a))
            if footprint_tokens and (footprint_tokens & selected_footprints):
                continue
            if any(_is_similar_story(a, b, "pest") for b in pest_unique):
                continue
            pest_unique.append(a)
            selected_footprints.update(footprint_tokens)

        target = min(4, max_n)
        if len(pest_unique) < target:
            refill_cut = max(BASE_MIN_SCORE.get("pest", 6.6), thr - 10.5)

            selected_regions = {_pest_region_or_fallback_key(x) for x in pest_unique if _pest_region_or_fallback_key(x)}
            selected_commodity_keys = {key for x in pest_unique for key in _pest_article_commodity_keys(x)}
            selected_footprints = {token for x in pest_unique for token in _pest_story_footprint_tokens(x)}

            def _rank_pest_diversity_candidate(a: Article, allow_same_footprint: bool) -> tuple[tuple[Any, ...], str, tuple[str, ...], tuple[str, ...]] | None:
                if a in pest_unique:
                    return None
                if float(getattr(a, "score", 0.0) or 0.0) < refill_cut:
                    return None
                if any((a.canon_url or _dup_key(a)) == (b.canon_url or _dup_key(b)) for b in pest_unique):
                    return None
                if any(_is_similar_title(a.title_key, b.title_key) for b in pest_unique):
                    return None
                if any(_is_similar_story(a, b, "pest") for b in pest_unique):
                    return None
                if not _headline_gate_relaxed(a, "pest"):
                    return None
                txt_local = ((a.title or "") + " " + (a.description or "")).lower()
                if not (is_pest_control_policy_context(txt_local) or is_pest_story_focus_strong(a.title or "", a.description or "")):
                    return None
                region_key = _pest_region_or_fallback_key(a)
                commodity_keys = _pest_article_commodity_keys(a)
                footprint_tokens = _pest_story_footprint_tokens(a)
                has_new_region = 1 if region_key and region_key not in selected_regions else 0
                has_new_commodity = 1 if commodity_keys and not (set(commodity_keys) & selected_commodity_keys) else 0
                has_new_footprint = 1 if footprint_tokens and not (set(footprint_tokens) & selected_footprints) else 0
                if footprint_tokens and (set(footprint_tokens) & selected_footprints):
                    return None
                if not allow_same_footprint and not (has_new_region or has_new_commodity or has_new_footprint):
                    return None
                tier = press_priority(a.press, a.domain)
                pub_sort = getattr(a, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST)
                return (
                    (
                        has_new_footprint,
                        has_new_commodity,
                        has_new_region,
                        1 if is_pest_control_policy_context(txt_local) else 0,
                        1 if tier >= 2 else 0,
                        round(float(getattr(a, "score", 0.0) or 0.0), 3),
                        pub_sort,
                    ),
                    region_key,
                    commodity_keys,
                    footprint_tokens,
                )

            for allow_same_footprint in (False, True):
                if len(pest_unique) >= target:
                    break
                ranked_refill: list[tuple[tuple[Any, ...], Article, str, tuple[str, ...], tuple[str, ...]]] = []
                for a in candidates_sorted:
                    ranked = _rank_pest_diversity_candidate(a, allow_same_footprint)
                    if ranked is None:
                        continue
                    ranked_refill.append((ranked[0], a, ranked[1], ranked[2], ranked[3]))
                ranked_refill.sort(key=lambda item: item[0], reverse=True)
                for _, a, region_key, commodity_keys, footprint_tokens in ranked_refill:
                    if len(pest_unique) >= target:
                        break
                    if a in pest_unique:
                        continue
                    if any((a.canon_url or _dup_key(a)) == (b.canon_url or _dup_key(b)) for b in pest_unique):
                        continue
                    if any(_is_similar_title(a.title_key, b.title_key) for b in pest_unique):
                        continue
                    if any(_is_similar_story(a, b, "pest") for b in pest_unique):
                        continue
                    if footprint_tokens and (set(footprint_tokens) & selected_footprints):
                        continue
                    _record_selection(a, "pest_diversity_backfill")
                    pest_unique.append(a)
                    if region_key:
                        selected_regions.add(region_key)
                    selected_commodity_keys.update(commodity_keys)
                    selected_footprints.update(footprint_tokens)
        deduped = pest_unique

    forced_final_items = [a for a in candidates_sorted if getattr(a, "forced_section", "") == section_key]
    for fa in forced_final_items:
        fa_key = fa.canon_url or _dup_key(fa)
        if any((x.canon_url or _dup_key(x)) == fa_key for x in deduped):
            continue
        if len(deduped) < max_n:
            _record_selection(fa, "forced_section", getattr(fa, "forced_section", "") or section_key)
            deduped.append(fa)
            continue
        if deduped:
            repl_idx = min(range(len(deduped)), key=lambda i: float(getattr(deduped[i], "score", 0.0) or 0.0))
            _record_selection(fa, "forced_section", getattr(fa, "forced_section", "") or section_key)
            deduped[repl_idx] = fa
    if forced_final_items:
        forced_keys = {a.canon_url or _dup_key(a) for a in forced_final_items}
        forced_selected = [a for a in deduped if (a.canon_url or _dup_key(a)) in forced_keys]
        non_forced_selected = [a for a in deduped if (a.canon_url or _dup_key(a)) not in forced_keys]
        deduped = forced_selected + non_forced_selected

    # Debug report payload (top candidates + selection decisions)
    if DEBUG_REPORT:
        try:
            selected_keys = set()
            selected_final = deduped[:max_n]
            for _a in selected_final:
                selected_keys.add(_a.canon_url or _a.norm_key or _a.title_key)

            top_n = max(5, min(DEBUG_REPORT_MAX_CANDIDATES, 60))
            top_candidates = candidates_sorted[:top_n]

            def _signals(a: Article) -> JsonDict:
                txt = (a.title + " " + a.description).lower()
                return {
                    "horti_sc": round(best_horti_score(a.title, a.description), 2),
                    "market_hits": (count_any(txt, [t.lower() for t in ("가락시장","도매시장","공판장","청과","경락","경매","반입","온라인 도매시장","산지유통","산지유통센터")]) + (1 if has_apc_agri_context(txt) else 0)),
                    "strength": round(agri_strength_score(txt), 2),
                    "korea": round(korea_context_score(txt), 2),
                    "offtopic_pen": round(off_topic_penalty(txt), 2),
                    "press_tier": press_tier(a.press, a.domain),
                    "press_weight": round(press_weight(a.press, a.domain), 2),
                }

            def _best_effort_reason(a: Article) -> str:
                if a.score < thr:
                    return "below_threshold"
                if not _headline_gate_relaxed(a, section_key):
                    return "headline_gate"
                if a.score < tail_cut:
                    return "tail_cut"
                if section_key == "supply":
                    if _is_supply_policy_like_tail_story(a):
                        return "supply_policy_like"
                    if _is_supply_dist_like_tail_story(a):
                        return "supply_dist_like"
                    if is_supply_tourism_event_context(a.title or "", a.description or ""):
                        return "supply_tourism_event"
                    if _is_supply_low_value_macro_brief(a):
                        return "supply_macro_brief"
                    if _is_supply_weak_tail_story(a):
                        return "weak_tail"
                    if _supply_feature_topic_repeat(a, selected_final):
                        return "topic_repeat"
                if section_key == "policy":
                    if is_dist_market_disruption_context(a.title or "", a.description or ""):
                        return "policy_dist_market_disruption"
                    if is_policy_general_macro_tail_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                        return "policy_macro_general_economy"
                    if is_policy_event_tail_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                        return "policy_event_tail"
                    if not _is_policy_tail_candidate(a):
                        return "policy_tail_gate"
                if section_key == "dist":
                    if is_dist_consumer_tail_context(a.title or "", a.description or ""):
                        return "dist_consumer_tail"
                    if is_dist_local_crop_strategy_noise_context(a.title or "", a.description or ""):
                        return "dist_local_crop_strategy"
                    if is_dist_macro_export_noise_context(a.title or "", a.description or "", normalize_host(a.domain or ""), (a.press or "").strip()):
                        return "dist_macro_export_noise"
                    if _is_dist_weak_tail_story(a):
                        return "dist_local_org_profile"
                if any(_is_similar_title(a.title_key, b.title_key) for b in selected_final):
                    return "similar_title"
                if any(_is_similar_story(a, b, section_key) for b in selected_final):
                    return "similar_story"
                if not _source_ok_local(a):
                    return "source_cap"
                return "not_selected"

            top_rows = []
            for a in top_candidates:
                k = a.canon_url or a.norm_key or a.title_key
                sel = k in selected_keys
                fit_score = float(getattr(a, "selection_fit_score", 0.0) or 0.0)
                if fit_score <= 0.0:
                    try:
                        fit_score = round(section_fit_score(a.title or "", a.description or "", sec_conf), 3)
                    except Exception:
                        fit_score = 0.0
                top_rows.append({
                    "selected": bool(sel),
                    "is_core": bool(getattr(a, "is_core", False)) if sel else False,
                    "score": round(a.score, 2),
                    "tier": press_priority(a.press, a.domain),
                    "press": a.press,
                    "domain": a.domain,
                    "title": (a.title or "")[:160],
                    "url": (a.originallink or a.link or "")[:500],
                    "reason": "" if sel else _best_effort_reason(a),
                    "fit_score": round(float(fit_score or 0.0), 3),
                    "selection_stage": str(getattr(a, "selection_stage", "") or "") if sel else "",
                    "selection_note": str(getattr(a, "selection_note", "") or "") if sel else "",
                    "origin_section": str(getattr(a, "origin_section", "") or getattr(a, "section", "") or section_key),
                    "reassigned_from": str(getattr(a, "reassigned_from", "") or ""),
                    "source_query": str(getattr(a, "source_query", "") or "")[:120],
                    "source_channel": str(getattr(a, "source_channel", "") or "")[:40],
                    "signals": _signals(a),
                })

            payload: JsonDict = {
                "threshold": round(thr, 2),
                "tail_cut": round(tail_cut, 2),
                "core_min": round(core_min, 2),
                "total_candidates": len(candidates),
                "total_selected": len(selected_final),
                "top": top_rows,
                "coverage_ledger": _build_seed_coverage_ledger(
                    section_key,
                    list(
                        dict.fromkeys(
                            [str(getattr(a, "source_query", "") or "").strip() for a in candidates_sorted if str(getattr(a, "source_query", "") or "").strip()]
                            + list(sec_conf.get("queries") or [])
                        )
                    ),
                    candidates_sorted,
                    selected_articles=selected_final,
                ),
            }
            dbg_set_section(section_key, payload)
        except Exception:
            pass


    return deduped[:max_n]



def _missing_supply_feature_reps(
    candidates_sorted: list["Article"],
    thr: float,
    max_n: int,
    seed_queries: list[str] | None = None,
) -> list[str]:
    if max_n <= 0:
        return []
    pool = [a for a in candidates_sorted if float(getattr(a, "score", 0.0) or 0.0) >= float(thr or 0.0)]
    preview = select_top_articles(pool, "supply", max_n) if pool else []
    base_seed_queries = list(seed_queries or SUPPLY_ITEM_QUERIES)
    query_reps = [
        TOPIC_REP_BY_TERM_L.get((seed or "").strip().lower(), (seed or "").strip().lower())
        for seed in _extract_seed_terms_from_queries(base_seed_queries, limit=max(8, max_n * 3))
        if (seed or "").strip()
    ]
    if not query_reps:
        return []

    feature_reps = {
        (TOPIC_REP_BY_NAME_L.get((a.topic or "").strip()) or (a.topic or "").strip()).lower()
        for a in preview
        if (a.topic or "").strip() and is_supply_feature_article(a.title or "", a.description or "")
    }
    preview_rep_hits: dict[str, int] = {rep: 0 for rep in query_reps}
    for art in preview:
        for rep in query_reps:
            if _article_matches_seed_term(art, rep):
                preview_rep_hits[rep] = preview_rep_hits.get(rep, 0) + 1

    if len(preview) < max_n:
        return [rep for rep in query_reps if rep and preview_rep_hits.get(rep, 0) == 0]

    non_feature_tail = any(
        (not getattr(a, "is_core", False)) and (not is_supply_feature_article(a.title or "", a.description or ""))
        for a in preview
    )
    if not non_feature_tail:
        return []
    return [rep for rep in query_reps if rep and rep not in feature_reps]

def _needs_supply_feature_refresh(
    candidates_sorted: list["Article"],
    thr: float,
    max_n: int,
    seed_queries: list[str] | None = None,
) -> bool:
    return bool(_missing_supply_feature_reps(candidates_sorted, thr, max_n, seed_queries=seed_queries))

# -----------------------------
# Optional RSS ingestion (공식/신뢰 소스 보강)
# - WHITELIST_RSS_URLS 환경변수에 RSS URL을 넣으면 해당 소스에서 기사 후보를 추가한다.
# - 기본은 OFF(빈 값)이며, 기존 Naver OpenAPI 기반 파이프라인은 그대로 유지한다.
# -----------------------------
def fetch_rss_items(rss_url: str) -> list[JsonDict]:
    try:
        r = http_session().get(rss_url, timeout=20)
        if not r.ok:
            return []
        txt = r.text
        import xml.etree.ElementTree as ET
        root = ET.fromstring(txt)
        items = []
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            desc = (it.findtext("description") or "").strip()
            pub = (it.findtext("pubDate") or "").strip()
            items.append({"title": title, "link": link, "description": desc, "pubDate": pub})
        return items
    except Exception:
        return []

def _rss_pub_to_kst(pub: str) -> datetime | None:
    # RSS pubDate? ??? ??? ????? ??(?? ? None)
    if not pub:
        return None
    pub = str(pub or "").strip()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ):
        try:
            dt = datetime.strptime(pub, fmt)
            if dt.tzinfo is None:
                if fmt.startswith("%Y-"):
                    dt = dt.replace(tzinfo=KST)
                else:
                    dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(KST)
        except Exception:
            continue
    return None


_GOOGLE_NEWS_DECODE_CACHE: dict[str, str] = {}
_GOOGLE_NEWS_DECODE_LOCK = threading.Lock()


def should_use_google_news_recall(end_kst: datetime) -> bool:
    if not GOOGLE_NEWS_RECALL_ENABLED:
        return False
    try:
        age_days = (datetime.now(KST).date() - end_kst.astimezone(KST).date()).days
    except Exception:
        return False
    return age_days >= GOOGLE_NEWS_RECALL_MIN_AGE_DAYS


def build_google_news_rss_search_url(query: str, start_kst: datetime, end_kst: datetime) -> str:
    # Google News RSS supports coarse after:/before: filters. Keep the window slightly wider
    # than our exact KST cutoff and let the normal pubDate filter enforce the final boundary.
    after_day = (start_kst.astimezone(KST).date() - timedelta(days=1)).isoformat()
    before_day = (end_kst.astimezone(KST).date() + timedelta(days=1)).isoformat()
    full_query = f"{(query or '').strip()} after:{after_day} before:{before_day}".strip()
    return (
        "https://news.google.com/rss/search?q="
        + quote(full_query)
        + "&hl=ko&gl=KR&ceid=KR:ko"
    )


def _extract_google_news_base64(source_url: str) -> str:
    try:
        parsed = urlparse(source_url)
        path = [p for p in (parsed.path or "").split("/") if p]
        if parsed.hostname != "news.google.com" or len(path) < 2:
            return ""
        if path[-2] not in ("articles", "read"):
            return ""
        return path[-1]
    except Exception:
        return ""


def decode_google_news_url(source_url: str) -> str:
    base64_str = _extract_google_news_base64(source_url)
    if not base64_str:
        return source_url
    with _GOOGLE_NEWS_DECODE_LOCK:
        cached = _GOOGLE_NEWS_DECODE_CACHE.get(base64_str)
    if cached:
        return cached

    decoded = source_url
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        article_url = f"https://news.google.com/rss/articles/{base64_str}"
        r = http_session().get(article_url, headers=headers, timeout=20)
        if r.ok:
            sig_m = re.search(r'data-n-a-sg="([^"]+)"', r.text or "")
            ts_m = re.search(r'data-n-a-ts="([^"]+)"', r.text or "")
            if sig_m and ts_m:
                payload = [
                    "Fbv4je",
                    (
                        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,'
                        'null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
                        f'"{base64_str}",{ts_m.group(1)},"{sig_m.group(1)}"]'
                    ),
                ]
                batched = http_session().post(
                    "https://news.google.com/_/DotsSplashUi/data/batchexecute",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "User-Agent": "Mozilla/5.0",
                    },
                    data=f"f.req={quote(json.dumps([[payload]]))}",
                    timeout=20,
                )
                if batched.ok:
                    parts = (batched.text or "").split("\n\n", 1)
                    if len(parts) == 2:
                        decoded_json = json.loads(parts[1])
                        if decoded_json and len(decoded_json[0]) >= 3:
                            decoded = json.loads(decoded_json[0][2])[1]
    except Exception:
        decoded = source_url

    decoded = strip_tracking_params(decoded or source_url)
    with _GOOGLE_NEWS_DECODE_LOCK:
        _GOOGLE_NEWS_DECODE_CACHE[base64_str] = decoded
    return decoded


def fetch_google_news_search_items(
    query: str,
    start_kst: datetime,
    end_kst: datetime,
    item_cap: int | None = None,
) -> list[JsonDict]:
    cap = max(1, int(item_cap or GOOGLE_NEWS_RECALL_ITEM_CAP or 0))
    url = build_google_news_rss_search_url(query, start_kst, end_kst)
    try:
        r = http_session().get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if not r.ok:
            return []
        import xml.etree.ElementTree as ET

        root = ET.fromstring(r.text)
        items: list[JsonDict] = []
        for it in root.findall(".//item"):
            title = clean_text(it.findtext("title") or "")
            google_link = (it.findtext("link") or "").strip()
            if not title or not google_link:
                continue
            source = clean_text(it.findtext("source") or "")
            if source and title.endswith(f" - {source}"):
                title = title[: -(len(source) + 3)].strip()
            desc = clean_text(re.sub(r"<[^>]+>", " ", it.findtext("description") or ""))
            direct_link = decode_google_news_url(google_link)
            items.append(
                {
                    "title": title,
                    "description": desc,
                    "link": direct_link,
                    "originallink": direct_link,
                    "google_link": google_link,
                    "source": source,
                    "pubDate": (it.findtext("pubDate") or "").strip(),
                }
            )
            if len(items) >= cap:
                break
        return items
    except Exception:
        return []

def collect_rss_candidates(section_conf: SectionConfig, start_kst: datetime, end_kst: datetime) -> list[Article]:
    if not WHITELIST_RSS_URLS:
        return []
    out: list[Article] = []
    _local_dedupe = DedupeIndex()
    effective_start_kst = start_kst
    try:
        min_hours = WINDOW_MIN_HOURS
        if min_hours and min_hours > 0:
            min_start = end_kst - timedelta(hours=min_hours)
            if min_start < effective_start_kst:
                effective_start_kst = min_start
    except Exception:
        effective_start_kst = start_kst
    for rss in WHITELIST_RSS_URLS:
        for it in fetch_rss_items(rss):
            title = clean_text(it.get("title", ""))
            desc = clean_text(it.get("description", ""))
            link = strip_tracking_params(it.get("link", "") or "")
            pub = _rss_pub_to_kst(it.get("pubDate", ""))
            if not pub:
                # 날짜가 없으면 윈도우 밖일 수 있으므로 제외
                continue
            if pub < effective_start_kst or pub >= end_kst:
                continue
            dom = domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue
            press = normalize_press_label(press_name_from_url(link), link)
            dbg_set_current_query("", "rss")
            try:
                if not is_relevant(title, desc, dom, link, section_conf, press):
                    continue
            finally:
                dbg_clear_current_query()
            canon = canonicalize_url(link)
            title_key = norm_title_key(title)
            topic = extract_topic(title, desc)
            norm_key = make_norm_key(canon, press, title_key)

            if CROSSDAY_DEDUPE_ENABLED and (canon in RECENT_HISTORY_CANON or norm_key in RECENT_HISTORY_NORM):
                continue

            if not _local_dedupe.add_and_check(canon, press, title_key, norm_key):
                continue
            score = compute_rank_score(title, desc, dom, pub, section_conf, press)
            out.append(Article(
                section=section_conf["key"],
                title=title,
                description=desc,
                link=link,
                originallink=link,
                domain=dom,
                press=press,
                pub_dt_kst=pub,
                title_key=title_key,
                canon_url=canon,
                norm_key=norm_key,
                topic=topic,
                score=score,
                summary="",
                origin_section=section_conf["key"],
                source_channel="rss",
            ))
    return out


# -----------------------------
# Recall backfill helpers (broad-query safety net)
# -----------------------------
_RECALL_SIGNALS_BY_SECTION = {
    "supply": ["\ubb34\uad00\uc138", "\uc218\uc785", "\uad00\uc138", "FTA", "\ud560\ub2f9\uad00\uc138", "\ubb18\ubaa9", "\ud488\uadc0", "\uc0b0\ubd88", "\uae30\ud6c4\ubcc0\ud654"],
    "policy": list(POLICY_MARKET_BRIEF_RECALL_SIGNALS) + ["\ub300\ucc45", "\uc9c0\uc6d0", "\ud560\ub2f9\uad00\uc138", "\uac80\uc5ed", "\uad00\uc138", "\ubb34\uad00\uc138", "\uc218\uc785"],
    "dist": ["\ub3c4\ub9e4\uc2dc\uc7a5", "\uc628\ub77c\uc778 \ub3c4\ub9e4\uc2dc\uc7a5", "\uc81c\ub3c4 \uac1c\uc120", "\uc0b0\uc9c0\uc720\ud1b5", "\uacf5\ub3d9\uc120\ubcc4", "\ud488\ubaa9\ub18d\ud611", "\uc6d0\uc608\ub18d\ud611", "\uc6d0\uc0b0\uc9c0", "\ub2e8\uc18d", "\uac80\uc5ed", "\ud1b5\uad00", "\uc218\ucd9c", "\uc120\uc801", "\ud310\ub85c", "\ubb3c\ub958", "\uc870\ud569\uc6d0 \uc2e4\uc775", "\uac00\uacf5", "\uad6c\ub9e4", "\uc9c0\ub3c4\uc0ac\uc5c5", "\uc9c0\uc5ed\uacbd\uc81c"],
    "pest": ["\ubcd1\ud574\ucda9", "\ubc29\uc81c", "\uc608\ucc30", "\uac80\uc5ed", "\uc57d\uc81c \uacf5\uae09", "\ubb34\uc0c1 \uacf5\uae09", "\uc815\ubc00\uc608\ucc30", "\uc804\uc218\uc870\uc0ac", "\ud604\uc7a5\uc9c0\ub3c4", "\uc6d4\ub3d9"],
}

def _extract_seed_terms_from_queries(queries: list[str], limit: int = 6) -> list[str]:
    """쿼리 리스트에서 '대표 품목/키워드(첫 토큰)'를 추출.
    - 예: '배 과일 수급' -> '배', '샤인머스캣 가격' -> '샤인머스캣'
    - 개선: 앞쪽 query에 편향되지 않도록 전체 query를 순회하고 고르게 seed를 수집.
    - 개선: 유사 품목군(감귤/만감류/천혜향 등)은 대표 seed로 묶어 cap을 아낀다.
    """
    raw_terms: list[str] = []
    if not queries:
        return raw_terms
    cap = max(0, int(limit or 0))
    if cap == 0:
        return raw_terms
    skip = {"과일", "채소", "농산물", "농식품", "수급", "가격", "유통", "정책", "검역", "수입", "수입산", "무관세", "관세", "fta", "통관", "할당관세"}
    for q in queries:
        q = (q or "").strip().lower()
        if not q:
            continue
        tok = ""

        for t in re.findall(r"[0-9a-z가-힣]+", q):
            if not t or t in skip:
                continue
            rep = TOPIC_REP_BY_TERM_L.get(t)
            if rep:
                tok = rep
                break

        if not tok:
            for t in re.findall(r"[0-9a-z가-힣]{2,}", q):
                if t in skip:
                    continue
                tok = TOPIC_REP_BY_TERM_L.get(t, t)
                break

        if not tok:
            continue
        if tok not in raw_terms:
            raw_terms.append(tok)
    if len(raw_terms) <= cap:
        return raw_terms

    picked_idx: list[int] = []
    span = len(raw_terms) - 1
    out: list[str] = []
    for i in range(cap):
        idx = int(round(i * span / max(1, cap - 1)))
        while idx in picked_idx and idx + 1 < len(raw_terms):
            idx += 1
        if idx in picked_idx:
            for alt in range(len(raw_terms)):
                if alt not in picked_idx:
                    idx = alt
                    break
        picked_idx.append(idx)
        out.append(raw_terms[idx])
    return out[:cap]

_QUERY_TOKEN_STOPWORDS = {
    "수급", "가격", "작황", "출하", "정책", "브리핑", "보도자료", "농산물", "농식품", "과일", "채소",
    "동향", "이슈", "대책", "지원", "검역", "유통", "현장", "방제", "병해충",
    "수입", "수입산", "무관세", "관세", "fta", "통관", "할당관세",
}

def _query_tokens(q: str) -> list[str]:
    """쿼리에서 의미 있는 토큰만 추출(스팸성 광역 쿼리 정밀도 보정용)."""
    toks = re.findall(r"[0-9a-z가-힣]{2,}", (q or "").lower())
    out: list[str] = []
    for t in toks:
        if t in _QUERY_TOKEN_STOPWORDS:
            continue
        if t not in out:
            out.append(t)
    return out

def _query_article_match_ok(q: str, title: str, desc: str, section_key: str) -> bool:
    """쿼리-기사 정합성 체크.

    - 광역/보강 쿼리에서 발생하는 오탐을 줄이기 위해, 의미 토큰이 기사 텍스트에 최소 1개 이상 포함되는지 확인.
    - 다만 policy 섹션은 공공기관 브리핑이 제목/본문 표현이 변형되는 경우가 있어 완화 기준 적용.
    """
    toks = _query_tokens(q)
    if not toks:
        return True
    txt = f"{title or ''} {desc or ''}".lower()
    hit = sum(1 for t in toks if t in txt)
    if section_key == "policy":
        return hit >= 1
    # 의미 토큰이 3개 이상인 긴 쿼리는 최소 2개 매칭 요구
    need = 2 if len(toks) >= 3 else 1
    return hit >= need

def _seed_terms_from_topics(candidates_sorted: list["Article"], thr: float, cap: int = 4) -> list[str]:
    """pool 내 토픽 분포에서 seed term을 만든다.
    - 상위 토픽 2개 + (가능하면) 커버가 0인 토픽 1~2개를 섞어 '누락형'을 포착
    """
    cap = max(1, int(cap or 1))
    topic_cnt: dict[str, int] = {}
    for a in (candidates_sorted or []):
        if float(getattr(a, "score", 0.0) or 0.0) < float(thr or 0.0):
            continue
        tn = (getattr(a, "topic", "") or "").strip()
        if not tn:
            continue
        topic_cnt[tn] = topic_cnt.get(tn, 0) + 1

    # TOPICS는 (topic_name, synonyms) 형태
    # topic_name이 '감귤/만감'이면 synonyms[0]이 '감귤' 식으로 매핑되어 있음.
    out: list[str] = []

    # 1) 상위 토픽 2개
    top_topics = sorted(topic_cnt.items(), key=lambda x: x[1], reverse=True)[:2]
    for tn, _ in top_topics:
        for name, syns in TOPICS:
            if name == tn:
                term = (TOPIC_REP_BY_NAME_L.get(tn) or (syns[0] if syns else (tn.split("/")[0] if tn else ""))).strip()
                if term and term not in out:
                    out.append(term)
                break

    # 2) 커버가 0인 토픽(가능하면 1~2개)
    missing_terms: list[str] = []
    skip_topics = {"도매시장", "APC/산지유통", "수출/검역"}  # 섹션/시그널 쿼리로 이미 잘 잡히는 편
    for name, syns in TOPICS:
        if name in skip_topics:
            continue
        if topic_cnt.get(name, 0) >= 1:
            continue
        term = (TOPIC_REP_BY_NAME_L.get(name) or (syns[0] if syns else (name.split("/")[0] if name else ""))).strip()
        if term and term not in out and term not in missing_terms:
            missing_terms.append(term)
        if len(missing_terms) >= 2:
            break
    out.extend(missing_terms)

    # cap
    out2: list[str] = []
    for t in out:
        if t and t not in out2:
            out2.append(t)
        if len(out2) >= cap:
            break
    return out2

def _topic_terms_for_seed(seed: str) -> list[str]:
    """Expand a representative seed into its known topic terms."""
    seed_l = (seed or "").strip().lower()
    if not seed_l:
        return []
    rep = TOPIC_REP_BY_TERM_L.get(seed_l, seed_l)
    out: list[str] = []
    for name, syns in TOPICS:
        name_l = (name or "").strip().lower()
        rep_l = ((TOPIC_REP_BY_NAME_L.get(name) or (syns[0] if syns else (name.split("/")[0] if name else ""))) or "").strip().lower()
        if rep_l not in {rep, seed_l} and name_l not in {rep, seed_l}:
            continue
        for term in [name] + list(syns or []):
            term_l = (term or "").strip().lower()
            if term_l and term_l not in out:
                out.append(term_l)
    if rep and rep not in out:
        out.insert(0, rep)
    return out or [rep]


def _supply_feature_profile(seed: str) -> str:
    seed_l = (seed or "").strip().lower()
    if not seed_l:
        return "default"
    rep = TOPIC_REP_BY_TERM_L.get(seed_l, seed_l)
    return COMMODITY_FEATURE_PROFILE_BY_TERM_L.get(seed_l) or COMMODITY_FEATURE_PROFILE_BY_TERM_L.get(rep) or "default"


def _managed_seed_priority_bucket(seed: str) -> int:
    item = _managed_commodity_item_for_seed(seed)
    if not item:
        return 2
    return 0 if bool(item.get("program_core")) else 1


def _ordered_managed_seed_terms(seeds: list[str]) -> list[str]:
    def _group_balanced_seed_order(seed_items: list[tuple[dict[str, Any], str]]) -> list[str]:
        if not seed_items:
            return []
        default_group_order = [str(group.get("key") or "").strip() for group in MANAGED_COMMODITY_GROUP_SPECS if str(group.get("key") or "").strip()]
        grouped: dict[str, list[str]] = {}
        for item, seed_s in seed_items:
            group_key = str(item.get("group_key") or "").strip() or "_managed"
            if group_key not in grouped:
                grouped[group_key] = []
            if seed_s not in grouped[group_key]:
                grouped[group_key].append(seed_s)
        group_order = [group_key for group_key in default_group_order if group_key in grouped]
        group_order.extend(group_key for group_key in grouped.keys() if group_key not in group_order)
        out: list[str] = []
        pending = True
        while pending:
            pending = False
            for group_key in group_order:
                values = grouped.get(group_key) or []
                if not values:
                    continue
                pending = True
                out.append(values.pop(0))
        return out

    other_terms: list[str] = []
    seen_item_keys: set[str] = set()
    core_seed_items: list[tuple[dict[str, Any], str]] = []
    managed_seed_items: list[tuple[dict[str, Any], str]] = []
    for seed in seeds:
        seed_s = (seed or "").strip()
        if not seed_s:
            continue
        item = _managed_commodity_item_for_seed(seed_s)
        if not item:
            if seed_s not in other_terms:
                other_terms.append(seed_s)
            continue
        item_key = str(item.get("key") or "").strip()
        if not item_key or item_key in seen_item_keys:
            continue
        seen_item_keys.add(item_key)
        bucket = core_seed_items if bool(item.get("program_core")) else managed_seed_items
        bucket.append((item, seed_s))

    core_terms = _group_balanced_seed_order(core_seed_items)
    managed_terms = _group_balanced_seed_order(managed_seed_items)
    return _interleave_ordered_groups(core_terms, managed_terms, other_terms)


def _diversify_supply_focus_seeds(seeds: list[str], limit: int) -> list[str]:
    cap = max(0, int(limit or 0))
    if cap == 0:
        return []

    out: list[str] = []
    seen_profiles: set[str] = set()
    for seed in (seeds or []):
        seed = (seed or "").strip()
        if not seed:
            continue
        profile = _supply_feature_profile(seed)
        if profile in seen_profiles:
            continue
        out.append(seed)
        seen_profiles.add(profile)
        if len(out) >= cap:
            return out

    for seed in (seeds or []):
        seed = (seed or "").strip()
        if not seed or seed in out:
            continue
        out.append(seed)
        if len(out) >= cap:
            break
    return out


def _select_supply_feature_focus_seeds(seeds: list[str], limit: int) -> list[str]:
    cap = max(0, int(limit or 0))
    if cap == 0:
        return []

    feature_profiles = {"greenhouse", "citrus", "flower"}
    featured_seeds = [
        seed for seed in (seeds or [])
        if _supply_feature_profile(seed) in feature_profiles
    ]
    if featured_seeds:
        out: list[str] = []
        seen_profiles: set[str] = set()
        for seed in featured_seeds:
            profile = _supply_feature_profile(seed)
            if out and profile in seen_profiles:
                continue
            out.append(seed)
            seen_profiles.add(profile)
            if len(out) >= cap:
                return out
        if out:
            return out

    return _diversify_supply_focus_seeds(seeds, cap)

def _article_matches_seed_term(article: "Article", seed: str) -> bool:
    if not isinstance(article, Article):
        return False

    seed_l = (seed or "").strip().lower()
    if not seed_l:
        return False
    rep = TOPIC_REP_BY_TERM_L.get(seed_l, seed_l)
    topic_name = (getattr(article, "topic", "") or "").strip()
    topic_rep = (TOPIC_REP_BY_NAME_L.get(topic_name) or topic_name).strip().lower()
    title = getattr(article, "title", "") or ""
    desc = getattr(article, "description", "") or ""
    title_l = title.lower()
    text_l = f"{title} {desc}".lower()
    terms = [term for term in _topic_terms_for_seed(seed) if term]
    title_hits = sum(1 for term in terms if term in title_l)
    text_hits = sum(1 for term in terms if term in text_l)

    if topic_rep == rep:
        return True
    if title_hits >= 1:
        return True
    if text_hits >= 1 and is_supply_feature_article(title, desc):
        return True
    return False

def _prioritize_supply_recall_seeds(
    query_seed_terms: list[str],
    topic_seed_terms: list[str],
    candidates_sorted: list["Article"],
    thr: float,
) -> tuple[list[str], dict[str, int]]:
    """Prefer item seeds that are missing from the current supply pool."""
    seed_order: list[str] = []
    for seed in list(query_seed_terms or []) + list(topic_seed_terms or []):
        seed = (seed or "").strip()
        if seed and seed not in seed_order:
            seed_order.append(seed)

    pool_seed_hits: dict[str, int] = {seed: 0 for seed in seed_order}
    for art in (candidates_sorted or []):
        if float(getattr(art, "score", 0.0) or 0.0) < float(thr or 0.0):
            continue
        for seed in seed_order:
            if _article_matches_seed_term(art, seed):
                pool_seed_hits[seed] = pool_seed_hits.get(seed, 0) + 1

    def _balanced_missing_seed_order(seeds: list[str]) -> list[str]:
        return _ordered_managed_seed_terms(seeds)

    missing_query = _balanced_missing_seed_order([seed for seed in (query_seed_terms or []) if pool_seed_hits.get(seed, 0) == 0])
    covered_query = [seed for seed in (query_seed_terms or []) if pool_seed_hits.get(seed, 0) > 0]
    missing_topic = _balanced_missing_seed_order([
        seed for seed in (topic_seed_terms or [])
        if seed not in (query_seed_terms or []) and pool_seed_hits.get(seed, 0) == 0
    ])
    covered_topic = [
        seed for seed in (topic_seed_terms or [])
        if seed not in (query_seed_terms or []) and pool_seed_hits.get(seed, 0) > 0
    ]

    prioritized: list[str] = []
    for seed in missing_query + covered_query + missing_topic + covered_topic:
        seed = (seed or "").strip()
        if seed and seed not in prioritized:
            prioritized.append(seed)
    return prioritized, pool_seed_hits


def _article_matches_coverage_seed(article: "Article", seed: str, section_key: str = "") -> bool:
    if not isinstance(article, Article):
        return False
    seed_l = (seed or "").strip().lower()
    if not seed_l:
        return False
    if section_key == "supply":
        return _article_matches_seed_term(article, seed)

    rep = TOPIC_REP_BY_TERM_L.get(seed_l, seed_l)
    topic_name = (getattr(article, "topic", "") or "").strip()
    topic_rep = (TOPIC_REP_BY_NAME_L.get(topic_name) or topic_name).strip().lower()
    title = getattr(article, "title", "") or ""
    desc = getattr(article, "description", "") or ""
    title_l = title.lower()
    text_l = f"{title} {desc}".lower()
    terms = [term for term in _topic_terms_for_seed(seed) if term]
    title_hits = sum(1 for term in terms if term in title_l)
    text_hits = sum(1 for term in terms if term in text_l)
    managed_count = int(_managed_commodity_match_summary(title, desc, topic_name).get("count") or 0)

    if topic_rep == rep:
        return True
    if title_hits >= 1:
        return True
    if text_hits == 0:
        return False

    if section_key == "policy":
        policy_hits = count_any(
            text_l,
            [w.lower() for w in ("정책", "대책", "지원", "보전", "브리핑", "수급", "건의안", "촉구", "제도", "관리센터")],
        )
        return policy_hits >= 1 or managed_count >= 1 or best_horti_score(title, desc) >= 1.2
    if section_key == "dist":
        dist_hits = count_any(
            text_l,
            [w.lower() for w in ("도매시장", "공판장", "가락시장", "경락", "경매", "반입", "산지유통", "선적", "검역", "통관", "직거래", "판로", "유통")],
        ) + (1 if has_apc_agri_context(text_l) else 0)
        return dist_hits >= 1 or managed_count >= 1
    if section_key == "pest":
        pest_hits = count_any(
            text_l,
            [w.lower() for w in ("방제", "병해충", "약제", "예찰", "과수화상병", "탄저병", "냉해", "동해", "저온피해")],
        )
        return pest_hits >= 1 or managed_count >= 1
    return text_hits >= 1


def _coverage_seed_terms_for_section(
    section_key: str,
    queries: Sequence[str] | None,
    recall_meta: JsonDict | None = None,
    limit: int = 12,
) -> list[str]:
    out: list[str] = []
    max_limit = max(1, int(limit or 1))
    if isinstance(recall_meta, dict):
        for key in ("feature_focus_seeds", "prioritized_seeds", "seed_terms", "topic_seed_terms", "query_seed_terms"):
            for seed in list(recall_meta.get(key) or []):
                seed_s = str(seed or "").strip()
                if seed_s and seed_s not in out:
                    out.append(seed_s)
                if len(out) >= max_limit:
                    return out
    seed_limit = max(max_limit * 2, 12)
    for seed in _extract_seed_terms_from_queries(list(queries or []), limit=seed_limit):
        seed_s = str(seed or "").strip()
        if seed_s and seed_s not in out:
            out.append(seed_s)
        if len(out) >= max_limit:
            break
    return out[:max_limit]


def _build_seed_coverage_ledger(
    section_key: str,
    queries: Sequence[str] | None,
    articles: Sequence["Article"] | None,
    recall_meta: JsonDict | None = None,
    selected_articles: Sequence["Article"] | None = None,
    limit: int = 12,
) -> list[JsonDict]:
    seeds = _coverage_seed_terms_for_section(section_key, queries, recall_meta, limit=limit)
    if not seeds:
        return []

    rows: list[JsonDict] = []
    article_list = [a for a in list(articles or []) if isinstance(a, Article)]
    selected_list = [a for a in list(selected_articles or []) if isinstance(a, Article)]
    for seed in seeds:
        seed_l = (seed or "").strip().lower()
        rep = TOPIC_REP_BY_TERM_L.get(seed_l, seed_l)
        item_hits = 0
        selected_hits = 0
        sample_title = ""
        for art in article_list:
            if not _article_matches_coverage_seed(art, seed, section_key):
                continue
            item_hits += 1
            if not sample_title:
                sample_title = (art.title or "")[:100]
        for art in selected_list:
            if _article_matches_coverage_seed(art, seed, section_key):
                selected_hits += 1
        rows.append(
            {
                "seed": str(seed or ""),
                "rep": str(rep or ""),
                "hits": int(item_hits),
                "selected_hits": int(selected_hits),
                "missing": bool(item_hits == 0),
                "sample_title": sample_title,
            }
        )
    return rows


def _recall_common_queries(section_key: str, report_date: str | None = None) -> list[str]:
    _ = report_date
    common: list[str] = []
    if section_key == "supply":
        common = [
            "농산물 가격 동향",
            "농산물 수급 동향",
            "과일 가격",
            "채소 가격",
            "과일 수급",
            "채소 수급",
            "농산물 출하 동향",
            "화훼 경매",
            "절화 경매",
            "꽃시장 경매",
        ]
    elif section_key == "policy":
        common = list(POLICY_MARKET_BRIEF_QUERIES) + [
            "농식품부 농산물 수급 점검",
            "농식품부 가격 점검",
            "농산물 소비자물가",
            "농산물 수급 안정 대책",
            "농산물 가격안정 지원",
            "농산물 최저가격 지원",
            "농산물 가격안정 지원사업",
            "농식품부 농산물 유통 전문가 협의체",
            "농산물 유통 구조 개선",
            "농산물 최소가격 보전제",
            "온라인 도매시장 정책",
            "농식품부 원예",
        ]
    elif section_key == "dist":
        common = [
            "도매시장 경매",
            "공판장 경매",
            "가락시장 경락",
            "온라인 도매시장 제도 개선",
            "도매시장 제도 개선",
            "품목농협 산지유통",
            "원예농협 산지유통",
            "연합판매사업 직거래",
            "농산물 판로 확대",
            "농산물 공동구매",
            "농산물 직거래 장터",
            "농산물 유통 거점",
            "푸드통합지원센터 직거래",
            "산지유통센터",
            "스마트 APC",
            "농산물 광역수급관리센터",
        ]
    elif section_key == "pest":
        common = [
            "과수 병해충 방제",
            "병해충 예찰",
            "검역 병해충",
            "과수화상병 예방",
            "과수화상병 방제 계획",
            "과수화상병 약제 공급",
            "탄저병 방제",
            "월동 병해충 예찰",
            "시설채소 방제",
            "토마토뿔나방 약제 지원",
            "토마토뿔나방 전수조사",
        ]
    return _dedupe_queries(common)


def _managed_recall_anchor_dt(report_date: str | None) -> datetime | None:
    try:
        day = datetime.strptime(str(report_date or "").strip(), "%Y-%m-%d").date()
        return datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=KST)
    except Exception:
        return None


def _recall_common_queries(section_key: str, report_date: str | None = None) -> list[str]:  # type: ignore[no-redef]
    common: list[str] = []
    if section_key == "supply":
        common = [
            "농산물 가격 동향",
            "농산물 수급 동향",
            "경락값 분석",
            "과일 가격",
            "채소 가격",
            "과일 수급",
            "채소 수급",
            "농산물 출하 동향",
            "화훼 경매",
            "절화 경매",
            "꽃시장 경매",
        ]
    elif section_key == "policy":
        common = list(POLICY_MARKET_BRIEF_QUERIES) + [
            "농식품부 농산물 수급 점검",
            "농식품부 가격 점검",
            "농산물 소비자물가",
            "농산물 수급 안정 대책",
            "농산물 가격안정 지원",
            "농산물 최저가격 지원",
            "농산물 가격안정 지원사업",
            "주요 농산물 가격안정 지원사업",
            "농산물 가격 폭락 방지 대책",
            "농산물 수급 안정 건의안",
            "농산물 가격안정 건의안",
            "농산물 생산비 지원 대책",
            "농업용 면세유 대책",
            "농업용 면세유 가격 대책",
            "농식품부 농산물 유통 전문가 협의체",
            "농산물 유통 구조 개선",
            "농산물 최소가격 보전제",
            "농산물 광역 수급 관리센터",
            "농산물 광역수급관리센터",
            "농산물 수급 관리센터",
            "원예 시범사업",
            "온라인 도매시장 정책",
            "농식품부 예산",
        ]
    elif section_key == "dist":
        common = [
            "가락시장 경매",
            "도매시장 경매",
            "공판장 경매",
            "가락시장 경락",
            "초매식",
            "첫 경매",
            "경매 시작",
            "온라인 도매시장 제도 개선",
            "도매시장 제도 개선",
            "품목농협 계통 유통",
            "원예농협 계통 유통",
            "통합마케팅 직거래",
            "농산물 판로 확대",
            "농산물 공동구매",
            "농산물 직거래 장터",
            "농산물 유통 거점",
            "푸드통합지원센터 직거래",
            "광역유통센터",
            "스마트 APC",
            "농산물 광역수급관리센터",
            "농산물 온라인도매시장 거래",
            "농산물 출하비용 보전",
            "농산물 통합마케팅 출하",
            "농산물 선적식",
            "농산물 수출 지원 허브",
        ]
    elif section_key == "pest":
        common = [
            "과수 병해충 방제",
            "병해충 예찰",
            "검역 병해충",
            "과수화상병 예찰",
            "과수화상병 방제 계획",
            "과수화상병 약제 공급",
            "과수화상병 정밀예찰",
            "과수화상병 무상 공급",
            "응애 방제",
            "월동 병해충 예찰",
            "월동 병해충 방제",
            "시설채소 방제",
            "토마토뿔나방 약제 지원",
            "토마토뿔나방 전수조사",
            "병해충 현장지도",
        ]
    managed_common = build_managed_section_recall_queries(section_key, _managed_recall_anchor_dt(report_date))
    if managed_common:
        common = list(common) + list(managed_common)
    return _dedupe_queries(common)


def _build_web_recall_queries(
    section_key: str,
    fallback_queries: Sequence[str] | None,
    recall_meta: JsonDict | None = None,
) -> list[str]:
    if not WEB_RECALL_ENABLED or WEB_RECALL_QUERY_CAP_PER_SECTION <= 0:
        return []
    out: list[str] = []
    for q in list(fallback_queries or []):
        if len(out) >= WEB_RECALL_QUERY_CAP_PER_SECTION:
            break
        qn = (q or "").strip()
        if qn and qn not in out:
            out.append(qn)
    for q in _recall_common_queries(section_key):
        if len(out) >= WEB_RECALL_QUERY_CAP_PER_SECTION:
            break
        qn = (q or "").strip()
        if qn and qn not in out:
            out.append(qn)
    if isinstance(recall_meta, dict):
        recall_meta["web_queries"] = list(out)
    return out


def _build_recall_fallback_queries(
    section_key: str,
    section_conf: JsonDict,
    candidates_sorted: list["Article"],
    thr: float,
    report_date: str | None = None,
) -> tuple[list[str], JsonDict]:
    """후보 수 부족을 줄이기 위한 '광역 보강 쿼리'를 생성.
    반환: (queries, meta)
    - meta는 DEBUG_REPORT에서 확인 가능하도록 요약만 남긴다.
    """
    meta: JsonDict = {"seed_terms": [], "reason": [], "queries": []}
    if not RECALL_BACKFILL_ENABLED:
        return [], meta

    section_key = str(section_key or "")
    base_queries = list(section_conf.get("queries") or [])
    signals = _RECALL_SIGNALS_BY_SECTION.get(section_key, [])

    topic_seed_terms: list[str] = []
    query_seed_terms: list[str] = []
    prioritized_seeds: list[str] = []
    feature_refresh_seeds: list[str] = []
    try:
        topic_seed_terms.extend(_seed_terms_from_topics(candidates_sorted, thr, cap=4))
    except Exception:
        pass
    try:
        query_seed_limit = max(8, min(18, RECALL_QUERY_CAP_PER_SECTION * 3))
        query_seed_terms.extend(_extract_seed_terms_from_queries(base_queries, limit=query_seed_limit))
    except Exception:
        pass

    seed_source = list(topic_seed_terms) + list(query_seed_terms)
    if section_key == "supply":
        prioritized_seeds, pool_seed_hits = _prioritize_supply_recall_seeds(
            query_seed_terms,
            topic_seed_terms,
            candidates_sorted,
            thr,
        )
        if prioritized_seeds:
            seed_source = list(prioritized_seeds)
        meta["pool_seed_hits"] = dict(pool_seed_hits)
        section_max_n = max(1, int(section_conf.get("max_n") or MAX_PER_SECTION or 0))
        refresh_reps = _missing_supply_feature_reps(candidates_sorted, thr, section_max_n, seed_queries=base_queries)
        refresh_rep_set = set(refresh_reps)
        feature_refresh_seeds = [
            seed for seed in (prioritized_seeds or query_seed_terms)
            if TOPIC_REP_BY_TERM_L.get((seed or "").strip().lower(), (seed or "").strip().lower()) in refresh_rep_set
        ]
        if feature_refresh_seeds:
            meta["feature_refresh_seeds"] = list(feature_refresh_seeds)
    seed_terms: list[str] = []
    for t in seed_source:
        t = (t or "").strip()
        if not t:
            continue
        if t not in seed_terms:
            seed_terms.append(t)
        if len(seed_terms) >= max(8, RECALL_QUERY_CAP_PER_SECTION * 2):
            break
    meta["seed_terms"] = list(seed_terms)
    meta["topic_seed_terms"] = list(topic_seed_terms)
    meta["query_seed_terms"] = list(query_seed_terms)
    meta["report_date"] = str(report_date or "")

    has_trade = False
    if section_key in ("supply", "policy"):
        try:
            for a in (candidates_sorted or [])[:40]:
                if float(getattr(a, "score", 0.0) or 0.0) < float(thr or 0.0):
                    continue
                if _has_trade_signal(f"{a.title} {a.description}"):
                    has_trade = True
                    break
        except Exception:
            has_trade = False
        if not has_trade:
            meta["reason"].append("no_trade_signal_in_pool")

    out: list[str] = []

    def _add_query(q: str) -> None:
        q = (q or "").strip()
        if not q:
            return
        if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
            return
        if q in base_queries or q in out:
            return
        out.append(q)

    def _supply_signal_priority(seed: str) -> list[str]:
        profile = _supply_feature_profile(seed)
        if profile == "citrus":
            return ["품질", "제철", "수입산 비교", "출하 시기", "선호도", "만다린 비교", "작황"]
        if profile == "greenhouse":
            return ["생육", "난방", "농가", "작황", "품질"]
        if profile == "flower":
            return ["농가", "난방", "작황", "품질"]
        return ["작황", "생육", "품질", "농가"]

    common_queries = _recall_common_queries(section_key, report_date)
    meta["common_queries"] = list(common_queries)
    if section_key != "supply" and ((not candidates_sorted) or len(candidates_sorted) < 3):
        starter_cap = 3 if section_key == "pest" else 2 if section_key in ("policy", "dist") else 1
        for q in common_queries[:starter_cap]:
            _add_query(q)

    if section_key == "supply":
        prioritized_seeds = [t for t in (prioritized_seeds or seed_terms) if t]
        meta["prioritized_seeds"] = list(prioritized_seeds)

        sig_plan: dict[str, list[str]] = {}
        for t in prioritized_seeds:
            sig_plan[t] = list(_supply_signal_priority(t))

        if feature_refresh_seeds:
            focus_seed_cap = max(1, min(len(feature_refresh_seeds), max(2, RECALL_QUERY_CAP_PER_SECTION // 3)))
            zero_hit_focus_seeds = [
                seed for seed in feature_refresh_seeds
                if int(pool_seed_hits.get(seed, 0) or 0) == 0
            ]
            focus_seeds = _select_supply_feature_focus_seeds(
                zero_hit_focus_seeds or feature_refresh_seeds,
                focus_seed_cap,
            )
            meta["feature_focus_seeds"] = list(focus_seeds)
            for sig_round in range(2):
                for t in focus_seeds:
                    sigs = sig_plan.get(t) or []
                    if sig_round >= len(sigs):
                        continue
                    _add_query(f"{t} {sigs[sig_round]}")

        max_rounds = max((len(v) for v in sig_plan.values()), default=0)
        for round_idx in range(max_rounds):
            if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                break
            for t in prioritized_seeds:
                if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                    break
                sigs = sig_plan.get(t) or []
                if round_idx >= len(sigs):
                    continue
                _add_query(f"{t} {sigs[round_idx]}")
    else:
        for t in seed_terms:
            if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                break
            _add_query(t)

        for t in seed_terms:
            if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                break
            sigs = list(signals)
            if section_key == "policy" and not has_trade:
                sigs = list(POLICY_MARKET_BRIEF_RECALL_SIGNALS) + sigs
            added_for_term = 0
            signal_cap = 3 if section_key == "pest" else 2
            for sig in sigs:
                if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                    break
                if not sig:
                    continue
                q = f"{t} {sig}".strip()
                if q in base_queries or q in out:
                    continue
                out.append(q)
                added_for_term += 1
                if added_for_term >= signal_cap:
                    break

    if len(out) < RECALL_QUERY_CAP_PER_SECTION:
        if section_key == "supply":
            expanded_seed_limit = max(12, min(18, RECALL_QUERY_CAP_PER_SECTION * 4))
            expanded_feature_seeds = [
                t for t in _extract_seed_terms_from_queries(base_queries, limit=expanded_seed_limit)
                if t and t not in prioritized_seeds
            ]
            meta["fallback_feature_seeds"] = list(expanded_feature_seeds)
            for t in expanded_feature_seeds:
                if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                    break
                for sig in _supply_signal_priority(t)[:2]:
                    if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                        break
                    _add_query(f"{t} {sig}")

    for q in common_queries:
        if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
            break
        if q in base_queries or q in out:
            continue
        out.append(q)

    if common_queries:
        first_common = next((q for q in common_queries if q and q not in base_queries), "")
        if first_common and first_common not in out:
            if len(out) >= RECALL_QUERY_CAP_PER_SECTION and out:
                replace_idx = len(out) - 1
                protected_seed = ""
                if section_key == "supply":
                    focus_seeds = [str(seed or "").strip() for seed in (meta.get("feature_focus_seeds") or []) if str(seed or "").strip()]
                    if len(focus_seeds) == 1:
                        protected_seed = focus_seeds[0]
                seed_counts: dict[str, int] = {}
                for q in out:
                    seed = (q or "").split()[0] if (q or "").split() else (q or "")
                    seed_counts[seed] = seed_counts.get(seed, 0) + 1
                for idx in range(len(out) - 1, -1, -1):
                    seed = (out[idx] or "").split()[0] if (out[idx] or "").split() else (out[idx] or "")
                    if protected_seed and seed == protected_seed and seed_counts.get(seed, 0) <= 2:
                        continue
                    if seed_counts.get(seed, 0) > 1:
                        replace_idx = idx
                        break
                out[replace_idx] = first_common
            elif len(out) < RECALL_QUERY_CAP_PER_SECTION:
                out.append(first_common)

    meta["queries"] = list(out)
    return out, meta

def _dedupe_queries(queries: list[str]) -> list[str]:
    """Normalize and deduplicate query list while preserving order."""
    out: list[str] = []
    seen: set[str] = set()
    for q in (queries or []):
        qn = re.sub(r"\s+", " ", str(q or "")).strip()
        if not qn:
            continue
        k = qn.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(qn)
    return out

def collect_candidates_for_section(section_conf: SectionConfig, start_kst: datetime, end_kst: datetime) -> list[Article]:
    """Collect candidates for a section.

    기본 동작은 1페이지(=기존과 동일)이며, 아래 조건을 만족할 때에만 일부 쿼리에 대해 2페이지(start=51)를 추가 호출한다.
    - COND_PAGING_ENABLED(상한 2페이지 허용) AND
    - 후보 풀(pool: dynamic threshold 이상)이 max_n 미만 AND
    - 후보 개수 자체가 너무 적음(=품질 문제가 아니라 풀 부족 가능성) AND
    - (안전) 총 추가 호출수/섹션당 추가쿼리수가 예산 내
    """
    queries = _dedupe_queries(section_conf.get("queries") or [])
    section_key = str(section_conf.get("key") or "")
    if section_key in ("supply", "policy", "dist"):
        queries = _dedupe_queries(
            list(queries) + list(build_managed_section_recall_queries(section_key, start_kst))
        )
    # pest는 pool 충분 여부와 무관하게 실행형 방제 + 품목 기반 보강 쿼리를 병합해 누락을 줄인다.
    if section_key == "pest":
        managed_pest_queries = build_managed_pest_recall_queries(start_kst)
        queries = _dedupe_queries(
            list(queries)
            + list(PEST_ALWAYS_ON_RECALL_QUERIES)
            + list(managed_pest_queries)
        )
    items: list[Article] = []
    _local_dedupe = DedupeIndex()  # 섹션 내부 dedupe (전역은 최종 선택 단계에서)
    max_n = MAX_PER_SECTION

    effective_start_kst = start_kst
    try:
        min_hours = WINDOW_MIN_HOURS
        if min_hours and min_hours > 0:
            min_start = end_kst - timedelta(hours=min_hours)
            if min_start < effective_start_kst:
                effective_start_kst = min_start
    except Exception:
        effective_start_kst = start_kst

    hits_by_query: dict[str, int] = {}
    google_hits_by_query: dict[str, int] = {}

    api_items_by_query: dict[str, int] = {}    # raw items returned by API per query (before time/relevance filters)
    page1_full_queries: set[str] = set()       # API returned full display(=50) on page1 -> high volume hint
    recall_meta: JsonDict = {}                  # recall backfill metadata (for debug)
    last_fallback_queries: list[str] = []

    def _ingest_naver_items(q: str, data: NaverSearchResponse) -> None:
        nonlocal items, _local_dedupe
        if not isinstance(data, dict):
            return
        for it in (data.get("items", []) or []):
            title = clean_text(it.get("title", ""))
            desc = clean_text(it.get("description", ""))
            link = strip_tracking_params(it.get("link", "") or "")
            origin = strip_tracking_params(it.get("originallink", "") or link)
            pub = parse_pubdate_to_kst(it.get("pubDate", ""))

            # 수집 단계와 후반 정리 단계의 윈도우 기준을 반드시 동일하게 유지
            # (불일치 시 "수집됐다가 후반에 삭제"되는 회귀가 발생할 수 있음)
            if pub < effective_start_kst or pub >= end_kst:
                continue

            dom = domain_of(origin) or domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue

            press = normalize_press_label(press_name_from_url(origin or link), (origin or link))
            dbg_set_current_query(q, "naver_api")
            try:
                if not is_relevant(title, desc, dom, (origin or link), section_conf, press):
                    continue
            finally:
                dbg_clear_current_query()

            # 쿼리-기사 정합성 체크(옵트인): broad/recall 쿼리에서 제목만 비슷한 오탐 유입 억제
            if QUERY_ARTICLE_MATCH_GATE_ENABLED and (not _query_article_match_ok(q, title, desc, section_key)):
                continue

            canon = canonicalize_url(origin or link)
            title_key = norm_title_key(title)
            topic = extract_topic(title, desc)
            norm_key = make_norm_key(canon, press, title_key)

            # 크로스데이(최근 N일) 중복 방지: 72h 윈도우 확장 시 같은 기사가 반복 노출되는 것 최소화
            if CROSSDAY_DEDUPE_ENABLED and (canon in RECENT_HISTORY_CANON or norm_key in RECENT_HISTORY_NORM):
                continue

            if not _local_dedupe.add_and_check(canon, press, title_key, norm_key):
                continue

            art = Article(
                section=section_key,
                title=title,
                description=desc,
                link=link,
                originallink=origin,
                pub_dt_kst=pub,
                domain=dom,
                press=press,
                norm_key=norm_key,
                title_key=title_key,
                canon_url=canon,
                topic=topic,
                origin_section=section_key,
                source_query=q,
                source_channel="naver_api",
            )
            art.score = compute_rank_score(title, desc, dom, pub, section_conf, press)
            items.append(art)
            hits_by_query[q] = hits_by_query.get(q, 0) + 1

    def _ingest_web_items(q: str, data: NaverSearchResponse) -> None:
        nonlocal items, _local_dedupe
        if not isinstance(data, dict):
            return
        for it in (data.get("items", []) or []):
            title = clean_text(it.get("title", ""))
            desc = clean_text(it.get("description", ""))
            link = strip_tracking_params(it.get("link", "") or "")
            origin = link
            if not link:
                continue

            pub = parse_pubdate_to_kst(it.get("pubDate", ""))
            if pub <= datetime.min.replace(tzinfo=KST):
                pub2 = _best_effort_article_pubdate_kst(origin or link)
                pub = pub2 if isinstance(pub2, datetime) else pub
            if pub <= datetime.min.replace(tzinfo=KST):
                continue
            if pub < effective_start_kst or pub >= end_kst:
                continue

            dom = domain_of(origin) or domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue

            press = normalize_press_label(press_name_from_url(origin or link), (origin or link))
            dbg_set_current_query(q, "web")
            try:
                if not is_relevant(title, desc, dom, (origin or link), section_conf, press):
                    continue
            finally:
                dbg_clear_current_query()
            if QUERY_ARTICLE_MATCH_GATE_ENABLED and (not _query_article_match_ok(q, title, desc, section_key)):
                continue

            canon = canonicalize_url(origin or link)
            title_key = norm_title_key(title)
            topic = extract_topic(title, desc)
            norm_key = make_norm_key(canon, press, title_key)

            if CROSSDAY_DEDUPE_ENABLED and (canon in RECENT_HISTORY_CANON or norm_key in RECENT_HISTORY_NORM):
                continue
            if not _local_dedupe.add_and_check(canon, press, title_key, norm_key):
                continue

            art = Article(
                section=section_key,
                title=title,
                description=desc,
                link=link,
                originallink=origin,
                pub_dt_kst=pub,
                domain=dom,
                press=press,
                norm_key=norm_key,
                title_key=title_key,
                canon_url=canon,
                topic=topic,
                origin_section=section_key,
                source_query=q,
                source_channel="web",
            )
            art.score = compute_rank_score(title, desc, dom, pub, section_conf, press)
            items.append(art)
            hits_by_query[q] = hits_by_query.get(q, 0) + 1

    def _ingest_google_news_items(q: str, rows: Sequence[JsonDict]) -> None:
        nonlocal items, _local_dedupe
        for it in list(rows or []):
            title = clean_text(it.get("title", ""))
            desc = clean_text(it.get("description", ""))
            link = strip_tracking_params(it.get("link", "") or "")
            origin = strip_tracking_params(it.get("originallink", "") or link)
            if not title or not origin:
                continue

            pub = _rss_pub_to_kst(it.get("pubDate", ""))
            if (not pub) or pub < effective_start_kst or pub >= end_kst:
                pub2 = _best_effort_article_pubdate_kst(origin or link)
                if isinstance(pub2, datetime):
                    pub = pub2
            if (not pub) or pub < effective_start_kst or pub >= end_kst:
                hinted = _date_hint_from_url(origin or link)
                if isinstance(hinted, date):
                    hint_hour = 6 if hinted == end_kst.astimezone(KST).date() else 12
                    pub = datetime(hinted.year, hinted.month, hinted.day, hint_hour, 0, 0, tzinfo=KST)
            if not pub:
                continue
            if pub < effective_start_kst or pub >= end_kst:
                continue

            dom = domain_of(origin) or domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue

            source_press = clean_text(it.get("source", ""))
            press_seed = source_press or press_name_from_url(origin or link)
            press = normalize_press_label(press_seed, (origin or link))
            dbg_set_current_query(q, "google_news")
            try:
                if not is_relevant(title, desc, dom, (origin or link), section_conf, press):
                    continue
            finally:
                dbg_clear_current_query()
            if QUERY_ARTICLE_MATCH_GATE_ENABLED and (not _query_article_match_ok(q, title, desc, section_key)):
                continue

            canon = canonicalize_url(origin or link)
            title_key = norm_title_key(title)
            topic = extract_topic(title, desc)
            norm_key = make_norm_key(canon, press, title_key)

            if CROSSDAY_DEDUPE_ENABLED and (canon in RECENT_HISTORY_CANON or norm_key in RECENT_HISTORY_NORM):
                continue
            if not _local_dedupe.add_and_check(canon, press, title_key, norm_key):
                continue

            art = Article(
                section=section_key,
                title=title,
                description=desc,
                link=link or origin,
                originallink=origin,
                pub_dt_kst=pub,
                domain=dom,
                press=press,
                norm_key=norm_key,
                title_key=title_key,
                canon_url=canon,
                topic=topic,
                origin_section=section_key,
                source_query=q,
                source_channel="google_news",
            )
            art.score = compute_rank_score(title, desc, dom, pub, section_conf, press)
            items.append(art)
            google_hits_by_query[q] = google_hits_by_query.get(q, 0) + 1

    # -----------------------------
    # 1) Base pass: always 1 page
    # -----------------------------
    def fetch_page1(q: str) -> tuple[str, NaverSearchResponse]:
        return q, naver_news_search_paged(q, display=50, pages=COND_PAGING_BASE_PAGES, sort="date")

    if queries:
        max_workers = min(NAVER_MAX_WORKERS, max(1, len(queries)))
        futures = []
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for q in queries:
                futures.append(ex.submit(fetch_page1, q))

            for fut in as_completed(futures):
                try:
                    _q, data = fut.result()
                except Exception as e:
                    log.warning("[WARN] query failed: %s", e)
                    continue
                try:
                    _n_items = len((data.get('items', []) or [])) if isinstance(data, dict) else 0
                    api_items_by_query[_q] = api_items_by_query.get(_q, 0) + _n_items
                    if COND_PAGING_BASE_PAGES == 1 and _n_items >= 50:
                        page1_full_queries.add(_q)
                except Exception:
                    pass
                _ingest_naver_items(_q, data)

    # pest 섹션 리콜 보강: always-on 쿼리는 page2(start=51)를 선제적으로 1회 수집
    # - 조건부 페이징(need_more)과 별도로 동작시켜, page1 상위 기사에 가려진 실행형 기사를 보강한다.
    try:
        if (
            section_key == "pest"
            and PEST_ALWAYS_ON_PAGE2_ENABLED
            and COND_PAGING_ENABLED
            and COND_PAGING_MAX_PAGES >= 2
            and queries
            and PEST_ALWAYS_ON_PAGE2_QUERY_CAP > 0
        ):
            always_qs = [q for q in queries if q in set(PEST_ALWAYS_ON_RECALL_QUERIES)]
            # NOTE: 전역 extra-call budget은 supply/policy에서 먼저 소진될 수 있어,
            # pest always-on page2 보강은 별도 소량 cap으로 독립 수행한다.
            # (실행형 병해충 기사 리콜 안정화 목적)
            for q in always_qs[:PEST_ALWAYS_ON_PAGE2_QUERY_CAP]:
                try:
                    data_p2 = naver_news_search(q, display=50, start=51, sort="date")
                except Exception as e:
                    log.warning("[WARN] pest always-on page2 query failed: %s", e)
                    continue
                _ingest_naver_items(q, data_p2)
    except Exception:
        pass

    # pest 섹션 리콜 보강(2): naver web 검색(webkr) 소량 수집
    # - 뉴스 인덱스 지연/누락 시에도 기사 URL을 확보하기 위한 안전망
    try:
        if section_key == "pest" and PEST_WEB_RECALL_ENABLED and queries and PEST_WEB_RECALL_QUERY_CAP > 0:
            always_qs = [q for q in queries if q in set(PEST_ALWAYS_ON_RECALL_QUERIES)]
            for q in always_qs[:PEST_WEB_RECALL_QUERY_CAP]:
                try:
                    data_w = naver_web_search(q, display=10, start=1, sort="date")
                except Exception as e:
                    log.warning("[WARN] pest web recall query failed: %s", e)
                    continue
                _ingest_web_items(q, data_w)
    except Exception:
        pass

    # Optional RSS candidates (신뢰 소스 보강)
    try:
        items.extend(collect_rss_candidates(section_conf, start_kst, end_kst))
    except Exception:
        pass

    # 최종 안전장치: 수집 경로(RSS/추가소스)와 무관하게 윈도우 밖 기사는 제외
    items = [a for a in items if (a.pub_dt_kst is not None) and (effective_start_kst <= a.pub_dt_kst < end_kst)]
    items.sort(key=_sort_key_major_first, reverse=True)

    # -----------------------------
    # 2) Conditional extra pass: only when pool is lacking
    # -----------------------------
    try:
        recall_candidate = bool(RECALL_BACKFILL_ENABLED and COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION > 0 and queries)
        paging_candidate = bool(COND_PAGING_ENABLED and COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION > 0 and queries)
        if recall_candidate or paging_candidate:
            candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
            thr = _dynamic_threshold(candidates_sorted, section_key)
            supply_feature_refresh = False
            if section_key == "supply":
                try:
                    supply_feature_refresh = _needs_supply_feature_refresh(candidates_sorted, thr, max_n, seed_queries=queries)
                except Exception:
                    supply_feature_refresh = False

            # 후보가 많더라도 supply가 feature-light 상태면 targeted recall은 허용한다.
            if len(items) <= COND_PAGING_TRIGGER_CANDIDATE_CAP or supply_feature_refresh:
                pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)

                # 최소 목표(환경설정 반영): MIN_PER_SECTION이 0이면 3을 기본으로
                min_n = (MIN_PER_SECTION if MIN_PER_SECTION > 0 else 3)
                min_n = max(1, min(min_n, max_n))

                # pool이 부족하거나(특히 min 미달), 후보 수도 넉넉치 않을 때만 보강
                need_more = (pool_cnt < min_n) or (pool_cnt < max_n and len(items) < max(12, max_n * 3)) or supply_feature_refresh
                if need_more:
                    fallback_qs: list[str] = []
                    if recall_candidate:
                        # fallback recall은 1페이지 보강이므로, page2 활성화 여부와 무관하게 수행한다.
                        fallback_qs, recall_meta = _build_recall_fallback_queries(
                            section_key,
                            section_conf,
                            candidates_sorted,
                            thr,
                            report_date=end_kst.date().isoformat(),
                        )
                        last_fallback_queries = list(fallback_qs)
                        if fallback_qs:
                            fallback_added = 0
                            for fq in fallback_qs:
                                if fq in queries:
                                    continue
                                if fallback_added >= COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION:
                                    break
                                if not _take_extra_call_budget_for_section(section_key, 1, require_cond_paging=False):
                                    break
                                try:
                                    dataF = naver_news_search_paged(fq, display=50, pages=1, sort="date")
                                except Exception as e:
                                    log.warning("[WARN] fallback query failed: %s", e)
                                    continue
                                _ingest_naver_items(fq, dataF)
                                fallback_added += 1

                            if fallback_added > 0:
                                items = [a for a in items if (a.pub_dt_kst is not None) and (effective_start_kst <= a.pub_dt_kst < end_kst)]
                                items.sort(key=_sort_key_major_first, reverse=True)

                    if paging_candidate:
                        # 어떤 쿼리에 추가 페이지를 붙일지 선택
                        # - 1페이지에서 hit가 있었던 쿼리 우선 (추가 페이지도 성과 가능성이 큼)
                        # - 그래도 부족하면 섹션 쿼리 리스트 앞쪽(일반/범용)에서 최소 seed를 채움
                        _qpos = {q: i for i, q in enumerate(queries)}
                        ranked = sorted(list(queries), key=lambda q: ((1 if (q in page1_full_queries) else 0), hits_by_query.get(q, 0), -_qpos.get(q, 0)), reverse=True)

                        picked: list[str] = []
                        for q in ranked:
                            if hits_by_query.get(q, 0) <= 0:
                                continue
                            picked.append(q)
                            if len(picked) >= COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION:
                                break

                        min_seed = min(3, COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION)
                        if len(picked) < min_seed:
                            for q in queries:
                                if q in picked:
                                    continue
                                picked.append(q)
                                if len(picked) >= min_seed:
                                    break

                        # 추가 페이지 수집 (2..COND_PAGING_MAX_PAGES) — 예산/조기종료 포함
                        extra_added = 0
                        pages_tried = 0

                        for q in picked:
                            # 이미 충분해지면 그만
                            candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
                            thr = _dynamic_threshold(candidates_sorted, section_key)
                            pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)
                            if pool_cnt >= max_n:
                                break

                            for p in range(COND_PAGING_BASE_PAGES + 1, COND_PAGING_MAX_PAGES + 1):
                                if not _cond_paging_take_budget_for_section(section_key, 1):
                                    break
                                st = 1 + ((p - 1) * 50)  # 2페이지=51, 3페이지=101 ...
                                pages_tried += 1
                                try:
                                    dataN = naver_news_search(q, display=50, start=st, sort="date")
                                except Exception as e:
                                    log.warning("[WARN] query page%d failed: %s", p, e)
                                    continue

                                before = len(items)
                                _ingest_naver_items(q, dataN)
                                extra_added += max(0, len(items) - before)

                                # 조기 종료: pool이 충분해지면 그만
                                candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
                                thr = _dynamic_threshold(candidates_sorted, section_key)
                                pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)

                                # 후보가 충분히 커졌거나 pool 목표 도달 시 중단
                                if pool_cnt >= max_n or len(items) >= COND_PAGING_TRIGGER_CANDIDATE_CAP:
                                    break

                            if not COND_PAGING_ENABLED:
                                break

                        if extra_added > 0:
                            log.info(
                                "[COND_PAGING] section=%s added=%d pages_tried=%d budget=%d/%d",
                                section_key, extra_added, pages_tried, _COND_PAGING_EXTRA_CALLS_USED, COND_PAGING_EXTRA_CALL_BUDGET_TOTAL
                            )
                            items = [a for a in items if (a.pub_dt_kst is not None) and (effective_start_kst <= a.pub_dt_kst < end_kst)]
                            items.sort(key=_sort_key_major_first, reverse=True)

                    web_recall_candidate = bool(
                        section_key in ("supply", "policy", "dist")
                        and WEB_RECALL_ENABLED
                        and WEB_RECALL_QUERY_CAP_PER_SECTION > 0
                    )
                    if web_recall_candidate:
                        candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
                        thr = _dynamic_threshold(candidates_sorted, section_key)
                        pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)
                        still_need_web = (pool_cnt < min_n) or (len(items) == 0)
                        if still_need_web:
                            web_qs = _build_web_recall_queries(section_key, fallback_qs or last_fallback_queries, recall_meta)
                            if web_qs:
                                web_added = 0
                                for wq in web_qs:
                                    if not _take_extra_call_budget_for_section(section_key, 1, require_cond_paging=False):
                                        break
                                    try:
                                        data_w = naver_web_search(wq, display=WEB_RECALL_DISPLAY, start=1, sort="date")
                                    except Exception as e:
                                        log.warning("[WARN] web recall query failed: %s", e)
                                        continue
                                    before = len(items)
                                    _ingest_web_items(wq, data_w)
                                    web_added += max(0, len(items) - before)
                                if web_added > 0:
                                    items = [a for a in items if (a.pub_dt_kst is not None) and (effective_start_kst <= a.pub_dt_kst < end_kst)]
                                    items.sort(key=_sort_key_major_first, reverse=True)
                                recall_meta["web_added"] = int(web_added)

                    google_recall_candidate = bool(
                        should_use_google_news_recall(end_kst)
                        and GOOGLE_NEWS_RECALL_QUERY_CAP_PER_SECTION > 0
                    )
                    if google_recall_candidate:
                        candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
                        thr = _dynamic_threshold(candidates_sorted, section_key)
                        pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)
                        still_need_google = (pool_cnt < min_n) or (len(items) < max(3, min_n))
                        if still_need_google:
                            google_qs = _build_web_recall_queries(section_key, fallback_qs or last_fallback_queries, None)
                            google_qs = list(google_qs[:GOOGLE_NEWS_RECALL_QUERY_CAP_PER_SECTION])
                            if google_qs:
                                recall_meta["google_news_queries"] = list(google_qs)
                                google_added = 0
                                for gq in google_qs:
                                    rows = fetch_google_news_search_items(
                                        gq,
                                        effective_start_kst,
                                        end_kst,
                                        item_cap=GOOGLE_NEWS_RECALL_ITEM_CAP,
                                    )
                                    before = len(items)
                                    _ingest_google_news_items(gq, rows)
                                    google_added += max(0, len(items) - before)
                                if google_added > 0:
                                    items = [a for a in items if (a.pub_dt_kst is not None) and (effective_start_kst <= a.pub_dt_kst < end_kst)]
                                    items.sort(key=_sort_key_major_first, reverse=True)
                                recall_meta["google_news_added"] = int(google_added)
    except Exception:
        # extra pass should never break the pipeline
        pass


    # Debug: collection meta (queries/hits/recall) -> docs/debug/YYYY-MM-DD.json
    if DEBUG_REPORT:
        try:
            hits_top = sorted(list(hits_by_query.items()), key=lambda x: x[1], reverse=True)[:15]
            api_top = sorted(list(api_items_by_query.items()), key=lambda x: x[1], reverse=True)[:15]
            google_top = sorted(list(google_hits_by_query.items()), key=lambda x: x[1], reverse=True)[:15]
            meta = {
                "effective_window": {
                    "start_kst": effective_start_kst.isoformat() if isinstance(effective_start_kst, datetime) else str(effective_start_kst),
                    "end_kst": end_kst.isoformat() if isinstance(end_kst, datetime) else str(end_kst),
                },
                "base_queries_n": int(len(queries)),
                "base_queries": list(queries[:30]),
                "api_items_top": api_top,
                "window_hits_top": hits_top,
                "google_hits_top": google_top,
                "page1_full_queries": sorted(list(page1_full_queries))[:20],
                "recall_meta": recall_meta if isinstance(recall_meta, dict) else {},
                "items_total": int(len(items)),
                "seed_coverage": _build_seed_coverage_ledger(
                    section_key,
                    queries,
                    items,
                    recall_meta=recall_meta if isinstance(recall_meta, dict) else None,
                ),
                "cond_paging": {
                    "enabled": bool(COND_PAGING_ENABLED),
                    "base_pages": int(COND_PAGING_BASE_PAGES),
                    "max_pages": int(COND_PAGING_MAX_PAGES),
                    "budget_used": int(_COND_PAGING_EXTRA_CALLS_USED),
                    "budget_total": int(COND_PAGING_EXTRA_CALL_BUDGET_TOTAL),
                },
            }
            dbg_set_collection(section_key, meta)
        except Exception:
            pass

    return items

# -----------------------------
# Referenced reports (KREI 이슈+ 등) 자동 포함
# -----------------------------
_KREI_ISSUE_RX = re.compile(r"이슈\+\s*제?\s*(\d{1,4})\s*호")

def _extract_krei_issue_refs(by_section: dict[str, list["Article"]]) -> dict[int, datetime]:
    """기사 텍스트에서 '이슈+ 제NN호'를 찾아 (issue_no -> 대표 pub_dt)로 반환."""
    out: dict[int, datetime] = {}
    for lst in by_section.values():
        for a in (lst or []):
            text = f"{a.title} {a.description}"
            for m in _KREI_ISSUE_RX.finditer(text):
                try:
                    n = int(m.group(1))
                except Exception:
                    continue
                pub = getattr(a, "pub_dt_kst", None)
                if not isinstance(pub, datetime):
                    continue
                # 가장 최근(대표) pub_dt를 사용
                if (n not in out) or (pub > out[n]):
                    out[n] = pub
    return out

def _pick_best_web_item(items: list[Any], issue_no: int) -> dict[str, Any] | None:
    """KREI 이슈+ 링크 후보 중 최적 1개를 선택."""
    if not items:
        return None
    best = None
    for it in items:
        link = strip_tracking_params((it.get("link") or "")).strip()
        if not link:
            continue
        dom = normalize_host(domain_of(link) or "")
        if not dom:
            continue
        # KREI 도메인 우선
        if ("krei.re.kr" in dom) or ("repository.krei.re.kr" in dom):
            score = 3
        else:
            score = 0
        t = clean_text(it.get("title", ""))
        d = clean_text(it.get("description", ""))
        blob = (t + " " + d).lower()
        if str(issue_no) in blob:
            score += 1
        if "이슈+" in blob or "issue+" in blob:
            score += 1
        if best is None or score > best[0]:
            best = (score, it)
    return best[1] if best else None

def _maybe_add_krei_issues_to_policy(raw_by_section: dict[str, list["Article"]], start_kst: datetime, end_kst: datetime) -> None:
    """기사에서 언급된 KREI 이슈+ 보고서를 찾아 policy 섹션에 추가."""
    refs = _extract_krei_issue_refs(raw_by_section)
    if not refs:
        return

    _local_dedupe = DedupeIndex()
    policy_conf = None
    for s in SECTIONS:
        if s.get("key") == "policy":
            policy_conf = s
            break
    if not policy_conf:
        return

    # 과도한 호출 방지: 최대 3건까지만
    for issue_no, ref_pub in list(sorted(refs.items(), key=lambda x: x[0]))[:3]:
        try:
            q = f'한국농촌경제연구원 "이슈+" 제{issue_no}호'
            data = naver_web_search(q, display=10, start=1, sort="date")
            it = _pick_best_web_item(data.get("items", []) if isinstance(data, dict) else [], issue_no)
            if not it:
                continue

            title = clean_text(it.get("title", "")) or f"KREI 이슈+ 제{issue_no}호"
            desc = clean_text(it.get("description", "")) or ""
            link = strip_tracking_params(it.get("link", "") or "")
            if not link:
                continue
            dom = domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue

            press = "KREI"
            canon = canonicalize_url(link)
            title_key = norm_title_key(title)
            topic = "보고서"
            norm_key = make_norm_key(canon, press, title_key)

            # 크로스데이(최근 N일) 중복 방지: 72h 윈도우 확장 시 같은 기사가 반복 노출되는 것 최소화
            if CROSSDAY_DEDUPE_ENABLED and (canon in RECENT_HISTORY_CANON or norm_key in RECENT_HISTORY_NORM):
                continue

            if not _local_dedupe.add_and_check(canon, press, title_key, norm_key):
                continue

            a = Article(
                section="policy",
                title=f"[보고서] {title}",
                description=desc,
                link=link,
                originallink=link,
                pub_dt_kst=ref_pub,  # 기사에서 언급된 날짜를 대표로
                domain=dom,
                press=press,
                norm_key=norm_key,
                title_key=title_key,
                canon_url=canon,
                topic=topic,
                origin_section="policy",
                source_query=str(issue_no),
                source_channel="krei_issue",
            )
            a.score = compute_rank_score(a.title, a.description, dom, ref_pub, policy_conf, press)

            raw_by_section.setdefault("policy", []).append(a)

        except Exception as e:
            log.warning("[WARN] add KREI issue report failed: issue=%s err=%s", issue_no, e)



def is_macro_policy_issue(text: str) -> bool:
    """'주요 이슈' 성격의 물가/가격 기사인지 판단.
    - 정책 발표(대책/지원 등) 형태가 아니어도, 성수품(사과/배 등) 가격/물가 흐름은 policy 섹션에서 다룬다.
    - 특히 명절(설/추석) 전후 가격 급등·급락 이슈는 '주요 이슈'로 취급한다.
    - 단, 국제통상/산업 일반 기사나 소비자물가 나열형 기사는 제외한다.
    """
    t = (text or "").lower()
    if not t:
        return False

    if is_macro_trade_noise_context(t):
        return False
    agri_macro_keep = tuple(MACRO_POLICY_KEEP_TERMS)
    if is_general_consumer_price_noise(t) and best_horti_score("", t) < 1.6 and count_any(t, [w.lower() for w in agri_macro_keep]) == 0:
        return False

    # 1) 물가/통계/성수품 신호(명시적)
    macro_terms = ("물가", "소비자물가", "물가지수", "cpi", "kosis", "차례상", "성수품", "체감", "물가정보")
    macro_hit = count_any(t, [w.lower() for w in macro_terms])

    # 2) 명절 전후 가격 이슈(암시적) — '물가' 단어가 없어도 주요 이슈로 라우팅
    if macro_hit == 0 and any(w in t for w in ("설", "명절", "추석", "대목")):
        if ("가격" in t) and ("상승" in t or "하락" in t or "급등" in t or "급락" in t):
            macro_hit = 1

    if macro_hit < 1:
        return False

    if ("가격" not in t) and ("상승" not in t) and ("하락" not in t) and ("급등" not in t) and ("급락" not in t):
        return False

    # 농업/원예 맥락 또는 원예 점수
    try:
        horti = best_horti_score("", t)
    except Exception:
        horti = 0.0

    # 너무 약한 경우(일반 소비 기사) 방지: 원예 점수 또는 품목/농산물 키워드 필요
    if horti >= 1.4:
        return True
    if any(w in t for w in MACRO_POLICY_KEEP_TERMS):
        return True

    return False


def _global_section_reassign(raw_by_section: dict[str, list["Article"]], start_kst: datetime, end_kst: datetime) -> int:
    """후보를 섹션별로 수집한 뒤, 모든 섹션 기준으로 재평가하여 best section으로 이동.
    - 목적: '어떤 쿼리로 잡혔는지'에 좌우되는 오분류를 줄이고, 누락(특히 policy/dist)도 완화
    - 원칙: (1) 강한 이동 근거(점수 이득 + 최소 맥락)일 때만 이동 (2) pest는 기본 유지
    """
    if not GLOBAL_SECTION_REASSIGN_ENABLED:
        return 0

    conf_by_key = {str(x.get("key")): x for x in (SECTIONS or []) if isinstance(x, dict)}
    keys = [k for k in ("supply", "dist", "policy", "pest") if k in conf_by_key]

    moved = 0
    # flatten
    all_items: list[Article] = []
    for k, lst in (raw_by_section or {}).items():
        for a in (lst or []):
            if not isinstance(a, Article):
                continue
            # ensure section attr
            if not getattr(a, "section", None):
                a.section = str(k)
            all_items.append(a)

    # rebuild containers
    new_by: dict[str, list[Article]] = {k: [] for k in conf_by_key.keys()}
    # local dedupe per section after move
    local_dedupe_by: dict[str, DedupeIndex] = {k: DedupeIndex() for k in conf_by_key.keys()}

    def _remember_reassign(a: Article, prev_section: str) -> None:
        prev = str(prev_section or "")
        if not prev:
            return
        if not getattr(a, "origin_section", ""):
            a.origin_section = prev
        a.reassigned_from = prev

    for a in all_items:
        cur = str(getattr(a, "section", "") or "")
        if cur not in conf_by_key:
            cur = "supply" if "supply" in conf_by_key else (keys[0] if keys else cur)

        # pest는 기본 유지(섹션 스코어링보다 컨텍스트 판정이 중요)
        if cur == "pest":
            target = "pest"
            di = local_dedupe_by.get(target)
            if di and di.add_and_check(a.canon_url, a.press, a.title_key, a.norm_key):
                new_by.setdefault(target, []).append(a)
            continue

        txt = ((a.title or "") + " " + (a.description or "")).lower()
        dom = normalize_host(getattr(a, "domain", "") or "")
        press = (getattr(a, "press", "") or "").strip()
        url = getattr(a, "canon_url", None) or getattr(a, "originallink", None) or getattr(a, "link", None) or ""

        cur_score = float(getattr(a, "score", 0.0) or 0.0)
        best_key = cur
        best_score = cur_score
        cur_fit = section_fit_score(a.title, a.description, conf_by_key.get(cur, {}))
        best_fit_key = cur
        best_fit_score = float(cur_fit)
        cand_scores: dict[str, float] = {cur: cur_score}
        cand_fits: dict[str, float] = {cur: float(cur_fit)}
        strong_pest_context = is_pest_control_policy_context(txt)
        local_org_feature = is_local_agri_org_feature_context(a.title or "", a.description or "")
        dist_market_disruption = is_dist_market_disruption_context(a.title or "", a.description or "")
        dist_market_ops_like = is_dist_market_ops_context(a.title or "", a.description or "", dom, press)
        dist_supply_center_like = is_dist_supply_management_center_context(a.title or "", a.description or "")
        dist_sales_channel_ops_like = is_dist_sales_channel_ops_context(a.title or "", a.description or "")
        dist_local_org_tail = is_dist_local_org_tail_context(a.title or "", a.description or "")
        dist_export_support_hub_like = is_dist_export_support_hub_context(a.title or "", a.description or "", dom, press)
        macro_policy_like = is_macro_policy_issue(txt)
        broad_macro_price = is_broad_macro_price_context(a.title or "", a.description or "")
        direct_supply_story = has_direct_supply_chain_signal(txt)
        policy_stabilization_like = is_supply_stabilization_policy_context(txt, dom, press)
        policy_market_brief_like = is_policy_market_brief_context(txt, dom, press)
        policy_major_issue_like = is_policy_major_issue_context(a.title or "", a.description or "", dom, press)
        policy_general_macro_tail = is_policy_general_macro_tail_context(a.title or "", a.description or "", dom, press)
        dist_export_field_like = is_dist_export_field_context(a.title or "", a.description or "", dom, press)
        policy_export_support_like = is_policy_export_support_brief_context(a.title or "", a.description or "", dom, press)

        # candidate set: current + (supply/dist/policy/pest)
        cand_keys = []
        for k in (cur, "policy", "dist", "supply", "pest"):
            if k in conf_by_key and k not in cand_keys:
                cand_keys.append(k)

        for k in cand_keys:
            if k == cur:
                continue

            # quick prefilter (reduce false moves)
            if k == "dist":
                dist_like = count_any(txt, [t.lower() for t in ("도매시장","공판장","가락시장","경락","경매","반입","산지유통","산지유통센터","apc","물류","원산지","단속","검역","통관","수출","선적","수출길","유통","도매")])
                strong_local_org = local_org_feature and (not dist_local_org_tail) and has_apc_agri_context(txt)
                if is_dist_macro_export_noise_context(a.title or "", a.description or "", dom, press):
                    continue
                if is_dist_campaign_noise_context(a.title or "", a.description or ""):
                    continue
                if is_dist_political_visit_context(a.title or "", a.description or ""):
                    continue
                if is_local_agri_infra_designation_context(a.title or "", a.description or ""):
                    continue
                if is_dist_local_crop_strategy_noise_context(a.title or "", a.description or ""):
                    continue
                if dist_like < 2 and (not has_apc_agri_context(txt)) and (not strong_local_org) and (not is_dist_export_shipping_context(a.title, a.description)) and (not dist_export_field_like) and (not dist_market_disruption) and (not dist_market_ops_like) and (not dist_supply_center_like) and (not dist_sales_channel_ops_like):
                    continue
            if k == "policy":
                # 정책성 문맥이 거의 없으면 이동 후보에서 제외(단, 공식 도메인은 예외)
                # - 통상/관세/검역/통관 기사도 policy 후보로 포함(품목 맥락이 약할 때)
                # - 지자체 농산물 정책 프로그램(지원/보전/시범사업)은 policy 이동 후보로 허용
                _policy_like = False
                policy_anchor_stats = _policy_horti_anchor_stats(a.title or "", a.description or "", dom, press)
                try:
                    _h = best_horti_score(a.title or "", a.description or "")
                except Exception:
                    _h = 0.0
                if is_policy_announcement_issue(txt, dom, press) or policy_market_brief_like or policy_major_issue_like or macro_policy_like or broad_macro_price or policy_stabilization_like or policy_export_support_like:
                    _policy_like = True
                elif is_trade_policy_issue(txt) and (not dist_export_field_like) and _h < 2.2:
                    _policy_like = True
                elif is_local_agri_policy_program_context(txt):
                    _policy_like = True

                if policy_general_macro_tail or dist_export_field_like:
                    _policy_like = False
                if policy_anchor_stats.get("livestock_dominant"):
                    _policy_like = False
                if _policy_like and (not policy_export_support_like) and (not policy_anchor_stats.get("anchor_ok")):
                    _policy_like = False
                if not _policy_like:
                    try:
                        if not _is_policy_official(a):
                            continue
                    except Exception:
                        continue
            if k == "pest":
                # 병해충/방제 강신호 + 원예 맥락이 있을 때만 pest 이동 후보로 허용
                if not strong_pest_context:
                    continue

            try:
                conf = conf_by_key[k]
                if not is_relevant(a.title, a.description, dom, url, conf, press):
                    continue
                sc = compute_rank_score(a.title, a.description, dom, a.pub_dt_kst, conf, press)
                fit_new = section_fit_score(a.title, a.description, conf)
            except Exception:
                continue

            cand_scores[k] = float(sc)
            cand_fits[k] = float(fit_new)

            # 재분류는 score뿐 아니라 section-fit 개선이 있어야 우선 허용
            if fit_new + SECTION_REASSIGN_FIT_GUARD < cur_fit:
                continue

            if fit_new > best_fit_score:
                best_fit_score = float(fit_new)
                best_fit_key = k

            if sc > best_score:
                best_score = float(sc)
                best_key = k

        # 병해충 실행형 문맥은 policy/기타 섹션 점수와 무관하게 pest를 우선 고정한다.
        force_move_to_pest = (cur != "pest") and strong_pest_context and ("pest" in conf_by_key)
        prefer_move_to_dist = (
            cur != "dist"
            and (dist_market_disruption or dist_market_ops_like or dist_supply_center_like or dist_sales_channel_ops_like or is_dist_export_shipping_context(a.title, a.description) or dist_export_field_like or dist_export_support_hub_like or (local_org_feature and (not dist_local_org_tail) and has_apc_agri_context(txt)))
            and ("dist" in cand_scores)
            and (
                (dist_market_ops_like or dist_supply_center_like or dist_sales_channel_ops_like or dist_export_support_hub_like)
                or (
                    (cand_fits.get("dist", float("-inf")) + 0.2 >= cur_fit)
                    and (cand_scores.get("dist", float("-inf")) + 1.0 >= cur_score)
                )
            )
        )
        preserve_dist_owner = (
            cur == "dist"
            and (
                dist_market_disruption
                or dist_market_ops_like
                or dist_supply_center_like
                or dist_sales_channel_ops_like
                or is_dist_export_shipping_context(a.title, a.description)
                or dist_export_field_like
                or dist_export_support_hub_like
                or (local_org_feature and (not dist_local_org_tail) and has_apc_agri_context(txt))
            )
        )
        prefer_move_to_policy = (
            cur != "policy"
            and (policy_market_brief_like or policy_major_issue_like or macro_policy_like or broad_macro_price or policy_stabilization_like or policy_export_support_like)
            and (not policy_general_macro_tail)
            and (not dist_export_field_like)
            and (not dist_market_ops_like)
            and (not dist_supply_center_like)
            and (not dist_sales_channel_ops_like)
            and ((not direct_supply_story) or policy_market_brief_like or policy_major_issue_like or policy_export_support_like)
            and ("policy" in cand_scores)
            and (cand_fits.get("policy", float("-inf")) + 0.2 >= cur_fit)
            and (cand_scores.get("policy", float("-inf")) + 0.6 >= cur_score)
        )
        if preserve_dist_owner:
            if best_key in ("supply", "policy"):
                best_key = cur
                best_score = cur_score
            if best_fit_key in ("supply", "policy"):
                best_fit_key = cur
                best_fit_score = cur_fit
            prefer_move_to_policy = False

        # 이동 기준: 점수 이득이 충분할 때만(오분류/진동 방지)
        if force_move_to_pest:
            try:
                pest_conf = conf_by_key["pest"]
                if is_relevant(a.title, a.description, dom, url, pest_conf, press):
                    pest_score = compute_rank_score(a.title, a.description, dom, a.pub_dt_kst, pest_conf, press)
                    _remember_reassign(a, cur)
                    a.section = "pest"
                    a.score = float(pest_score)
                    moved += 1
            except Exception:
                pass
        elif prefer_move_to_dist:
            _remember_reassign(a, cur)
            a.section = "dist"
            a.score = float(cand_scores["dist"])
            moved += 1
        elif prefer_move_to_policy:
            _remember_reassign(a, cur)
            a.section = "policy"
            a.score = float(cand_scores["policy"])
            moved += 1
        elif best_key != cur and (best_score - cur_score) >= GLOBAL_SECTION_REASSIGN_MIN_GAIN:
            _remember_reassign(a, cur)
            a.section = best_key
            a.score = best_score
            moved += 1
        elif (
            best_fit_key != cur
            and best_fit_key in ("dist", "policy")
            and (best_fit_score - cur_fit) >= SECTION_REASSIGN_STRONG_FIT_DELTA
            and (best_score + SECTION_REASSIGN_STRONG_FIT_SCORE_TOL) >= cur_score
        ):
            try:
                conf_fit = conf_by_key.get(best_fit_key)
                if conf_fit and is_relevant(a.title, a.description, dom, url, conf_fit, press):
                    _remember_reassign(a, cur)
                    a.section = best_fit_key
                    a.score = compute_rank_score(a.title, a.description, dom, a.pub_dt_kst, conf_fit, press)
                    moved += 1
            except Exception:
                pass

        target = a.section
        di = local_dedupe_by.get(target)
        if di and di.add_and_check(a.canon_url, a.press, a.title_key, a.norm_key):
            new_by.setdefault(target, []).append(a)

    # write back
    for k in list(raw_by_section.keys()):
        raw_by_section[k] = new_by.get(k, [])

    # ensure keys exist
    for k in new_by.keys():
        raw_by_section.setdefault(k, new_by.get(k, []))

    return moved


def _enforce_pest_priority_over_policy(raw_by_section: dict[str, list["Article"]]) -> int:
    """강한 병해충 실행 문맥 기사는 policy 잔류를 허용하지 않고 pest로 우선 이동한다."""
    if not isinstance(raw_by_section, dict):
        return 0
    policy_items = list(raw_by_section.get("policy", []) or [])
    if not policy_items:
        return 0

    moved = 0
    keep_policy: list[Article] = []
    pest_items = list(raw_by_section.get("pest", []) or [])
    pest_idx = DedupeIndex()
    for _a in pest_items:
        try:
            pest_idx.add_and_check(_a.canon_url, _a.press, _a.title_key, _a.norm_key)
        except Exception:
            pass

    pest_conf = next((x for x in (SECTIONS or []) if isinstance(x, dict) and x.get("key") == "pest"), None)

    for a in policy_items:
        txt = ((a.title or "") + " " + (a.description or "")).lower()
        if not is_pest_control_policy_context(txt):
            keep_policy.append(a)
            continue

        d = normalize_host(getattr(a, "domain", "") or "")
        p = (getattr(a, "press", "") or "").strip()
        url = getattr(a, "canon_url", None) or getattr(a, "originallink", None) or getattr(a, "link", None) or ""
        ok = True
        if pest_conf is not None:
            try:
                ok = is_relevant(a.title, a.description, d, url, pest_conf, p)
            except Exception:
                ok = True
        if not ok:
            keep_policy.append(a)
            continue

        prev_section = str(getattr(a, "section", "") or "policy")
        if not getattr(a, "origin_section", ""):
            a.origin_section = prev_section
        if prev_section != "pest":
            a.reassigned_from = prev_section
        a.section = "pest"
        a.forced_section = "pest"
        if pest_conf is not None:
            try:
                a.score = compute_rank_score(a.title, a.description, d, a.pub_dt_kst, pest_conf, p)
            except Exception:
                pass
        # 최종 노출에서 밀려 사라지지 않도록, policy->pest 강제 이동분에는 소폭 우선순위 보정
        try:
            a.score = float(getattr(a, "score", 0.0) or 0.0) + 4.0
        except Exception:
            pass

        if pest_idx.add_and_check(a.canon_url, a.press, a.title_key, a.norm_key):
            pest_items.append(a)
        else:
            # 중복키가 이미 있으면 더 높은 점수 기사로 교체(강제 이동분 소실 방지)
            for i, ex in enumerate(pest_items):
                same = False
                try:
                    same = bool((a.canon_url and ex.canon_url and a.canon_url == ex.canon_url) or (a.norm_key and ex.norm_key and a.norm_key == ex.norm_key))
                except Exception:
                    same = False
                if same:
                    ex_sc = float(getattr(ex, "score", 0.0) or 0.0)
                    if float(getattr(a, "score", 0.0) or 0.0) > ex_sc:
                        pest_items[i] = a
                    break
        moved += 1

    if moved:
        raw_by_section["policy"] = keep_policy
        raw_by_section["pest"] = pest_items
    return moved


def _postbuild_article_reject_reason(a: "Article", section_key: str) -> str:
    text = ((a.title or "") + " " + (a.description or "")).lower()
    if is_apple_apology_context(text):
        return "apple_apology_context"
    if "당근" in text and not is_edible_carrot_context(text):
        return "carrot_non_edible_context"
    if section_key in ("supply", "policy", "dist") and is_agri_training_recruitment_context(a.title or "", a.description or ""):
        return "agri_training_recruitment"
    if section_key == "supply" and is_agri_org_rename_context(a.title or "", a.description or ""):
        return "agri_org_admin_noise"
    if section_key in ("supply", "policy") and is_title_livestock_dominant_context(a.title or "", a.description or ""):
        return "livestock_title_dominant"
    if section_key == "policy":
        if is_policy_forest_admin_noise_context(a.title or "", a.description or ""):
            return "policy_forest_admin_noise"
        if is_policy_budget_drive_noise_context(a.title or "", a.description or ""):
            return "policy_budget_drive_noise"
    if section_key == "dist":
        if is_dist_political_visit_context(a.title or "", a.description or ""):
            return "dist_political_visit"
        if is_local_agri_infra_designation_context(a.title or "", a.description or ""):
            return "dist_local_infra_designation"
        if is_dist_local_crop_strategy_noise_context(a.title or "", a.description or ""):
            return "dist_local_crop_strategy"
    if section_key in ("supply", "policy"):
        if is_flower_novelty_noise_context(a.title or "", a.description or ""):
            return "flower_novelty_noise"
        if any(phrase in text for phrase in ("장난감 꽃", "생화 너무 비싸", "레고 꽃다발", "조화(가짜 꽃)")):
            return "flower_novelty_noise"
    if section_key == "pest":
        if is_pest_input_marketing_noise_context(a.title or "", a.description or ""):
            return "pest_input_marketing_noise"
        if not is_pest_story_focus_strong(a.title or "", a.description or ""):
            return "pest_partial_mention"
    return ""


def _debug_article_signals(a: "Article") -> JsonDict:
    txt = ((a.title or "") + " " + (a.description or "")).lower()
    return {
        "horti_sc": round(best_horti_score(a.title or "", a.description or ""), 2),
        "market_hits": (
            count_any(txt, [t.lower() for t in ("가락시장", "도매시장", "공판장", "청과", "경락", "경매", "반입", "온라인 도매시장", "산지유통", "산지유통센터")])
            + (1 if has_apc_agri_context(txt) else 0)
        ),
        "strength": round(agri_strength_score(txt), 2),
        "korea": round(korea_context_score(txt), 2),
        "offtopic_pen": round(off_topic_penalty(txt), 2),
        "press_tier": press_tier(a.press, a.domain),
        "press_weight": round(press_weight(a.press, a.domain), 2),
    }


def _debug_row_from_article(a: "Article", section_key: str, section_conf: JsonDict | None = None, *, selected: bool, reason: str = "") -> JsonDict:
    fit_score = float(getattr(a, "selection_fit_score", 0.0) or 0.0)
    if fit_score <= 0.0:
        try:
            fit_score = round(section_fit_score(a.title or "", a.description or "", section_conf or {}), 3)
        except Exception:
            fit_score = 0.0
    stage = str(getattr(a, "selection_stage", "") or "")
    if (not selected) and reason:
        stage = str(reason or "")
    return {
        "selected": bool(selected),
        "is_core": bool(getattr(a, "is_core", False)) if selected else False,
        "score": round(float(getattr(a, "score", 0.0) or 0.0), 2),
        "tier": press_priority(a.press, a.domain),
        "press": a.press,
        "domain": a.domain,
        "title": (a.title or "")[:160],
        "url": (a.originallink or a.link or "")[:500],
        "reason": str(reason or ""),
        "fit_score": round(float(fit_score or 0.0), 3),
        "selection_stage": stage,
        "selection_note": str(getattr(a, "selection_note", "") or "") if selected else "",
        "origin_section": str(getattr(a, "origin_section", "") or getattr(a, "section", "") or section_key),
        "reassigned_from": str(getattr(a, "reassigned_from", "") or ""),
        "source_query": str(getattr(a, "source_query", "") or "")[:120],
        "source_channel": str(getattr(a, "source_channel", "") or "")[:40],
        "signals": _debug_article_signals(a),
    }


def _mark_debug_postbuild_reject(section_key: str, article: "Article", reason: str) -> None:
    try:
        payload = (DEBUG_DATA.get("sections") or {}).get(str(section_key))
        if not isinstance(payload, dict):
            return
        rows = payload.get("top")
        if not isinstance(rows, list):
            return
        target_url = (article.originallink or article.link or "")[:500]
        target_title = (article.title or "")[:160]
        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            same = False
            if target_url and row.get("url") == target_url:
                same = True
            elif target_title and row.get("title") == target_title:
                same = True
            if not same:
                continue
            row["selected"] = False
            row["is_core"] = False
            row["reason"] = str(reason or "postbuild_reject")
            row["selection_stage"] = str(reason or "postbuild_reject")
            row["selection_note"] = ""
            changed = True
        if changed:
            payload["total_selected"] = sum(1 for row in rows if isinstance(row, dict) and row.get("selected"))
    except Exception:
        return


def _sync_debug_with_final_sections(final_by_section: dict[str, list["Article"]]) -> None:
    try:
        sections = DEBUG_DATA.get("sections")
        if not isinstance(sections, dict):
            return
        for section_key, payload in list(sections.items()):
            if not isinstance(payload, dict):
                continue
            section_conf = next((s for s in (SECTIONS or []) if isinstance(s, dict) and s.get("key") == str(section_key)), {})
            rows = payload.get("top")
            if not isinstance(rows, list):
                continue
            final_items = [a for a in (final_by_section.get(str(section_key)) or []) if isinstance(a, Article)]
            final_by_key = {
                (
                    (a.originallink or a.link or "")[:500],
                    (a.title or "")[:160],
                ): a
                for a in final_items
            }
            seen_final_keys = set()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_key = ((row.get("url") or "")[:500], (row.get("title") or "")[:160])
                final_article = final_by_key.get(row_key)
                is_sel = final_article is not None
                row["selected"] = bool(is_sel)
                if not is_sel:
                    row["is_core"] = False
                    if not row.get("reason"):
                        row["reason"] = "postbuild_pruned"
                    row["selection_stage"] = str(row.get("reason") or "postbuild_pruned")
                    row["selection_note"] = ""
                else:
                    row.update(_debug_row_from_article(final_article, str(section_key), section_conf, selected=True))
                    seen_final_keys.add(row_key)
            for row_key, final_article in final_by_key.items():
                if row_key in seen_final_keys:
                    continue
                rows.append(_debug_row_from_article(final_article, str(section_key), section_conf, selected=True))
            payload["total_selected"] = sum(1 for row in rows if isinstance(row, dict) and row.get("selected"))
    except Exception:
        return


def _rebalance_underfilled_dist_from_supply(final_by_section: dict[str, list["Article"]]) -> int:
    if not isinstance(final_by_section, dict):
        return 0
    dist_conf = next((s for s in SECTIONS if s.get("key") == "dist"), None)
    supply_conf = next((s for s in SECTIONS if s.get("key") == "supply"), None)
    if not dist_conf or not supply_conf:
        return 0

    dist_items = [a for a in (final_by_section.get("dist") or []) if isinstance(a, Article)]
    supply_items = [a for a in (final_by_section.get("supply") or []) if isinstance(a, Article)]
    dist_target = min(MAX_PER_SECTION, 3)
    if len(dist_items) >= dist_target or len(supply_items) <= 2:
        return 0

    ranked: list[tuple[tuple[Any, ...], float, Article]] = []
    for a in supply_items:
        txt = ((a.title or "") + " " + (a.description or "")).lower()
        dom = normalize_host(a.domain or "")
        press = (a.press or "").strip()
        url = a.canon_url or a.originallink or a.link or ""
        try:
            if not is_relevant(a.title or "", a.description or "", dom, url, dist_conf, press):
                continue
            dist_score = float(compute_rank_score(a.title or "", a.description or "", dom, a.pub_dt_kst, dist_conf, press))
        except Exception:
            continue
        if is_dist_macro_export_noise_context(a.title or "", a.description or "", dom, press):
            continue
        if is_dist_campaign_noise_context(a.title or "", a.description or ""):
            continue
        fit_dist = section_fit_score(a.title or "", a.description or "", dist_conf)
        fit_supply = section_fit_score(a.title or "", a.description or "", supply_conf)
        market_ops = is_dist_market_ops_context(a.title or "", a.description or "", dom, press)
        supply_center = is_dist_supply_management_center_context(a.title or "", a.description or "")
        sales_channel = is_dist_sales_channel_ops_context(a.title or "", a.description or "")
        field_response = is_dist_field_market_response_context(a.title or "", a.description or "", dom, press)
        export_shipping = is_dist_export_shipping_context(a.title or "", a.description or "")
        export_field = is_dist_export_field_context(a.title or "", a.description or "", dom, press)
        local_field = is_dist_local_field_profile_context(a.title or "", a.description or "")
        systemic = 1 if dist_market_disruption_scope(a.title or "", a.description or "") == "systemic" else 0
        hub_hint = 1 if any(term in txt for term in ("\uc720\ud1b5 \uac70\uc810", "\uc0b0\uc9c0\uc720\ud1b5 \uac70\uc810")) else 0
        action_hint = 1 if is_horti_market_action_context(a.title or "", a.description or "") else 0
        strong_signal = systemic or market_ops or supply_center or sales_channel or field_response or export_shipping or export_field or local_field or hub_hint or action_hint
        if not strong_signal and fit_dist < 1.25:
            continue
        if (not strong_signal) and (fit_dist + 0.15 < fit_supply):
            continue
        ranked.append((
            (
                1 if systemic else 0,
                1 if market_ops else 0,
                1 if supply_center else 0,
                1 if sales_channel else 0,
                1 if field_response else 0,
                1 if local_field else 0,
                1 if export_field else 0,
                1 if export_shipping else 0,
                1 if hub_hint else 0,
                1 if action_hint else 0,
                round(fit_dist - fit_supply, 3),
                round(fit_dist, 3),
                round(dist_score, 3),
                1 if press_priority(a.press, a.domain) >= 2 else 0,
                getattr(a, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST),
            ),
            dist_score,
            a,
        ))

    ranked.sort(key=lambda item: item[0], reverse=True)
    moved = 0
    moved_keys = set()
    keep_supply = list(supply_items)
    for _, dist_score, a in ranked:
        if len(dist_items) >= dist_target or len(keep_supply) <= 2:
            break
        a_key = a.canon_url or a.link or a.title_key
        if a_key in moved_keys:
            continue
        if any((x.canon_url or x.link or x.title_key) == a_key for x in dist_items):
            continue
        keep_supply = [x for x in keep_supply if (x.canon_url or x.link or x.title_key) != a_key]
        if not getattr(a, "origin_section", ""):
            a.origin_section = a.section or "supply"
        a.reassigned_from = a.section or "supply"
        a.section = "dist"
        a.score = float(dist_score)
        a.selection_stage = "cross_section_dist_backfill"
        a.selection_note = "supply_to_dist_underfill"
        a.selection_fit_score = round(fit_dist, 3)
        dist_items.append(a)
        moved_keys.add(a_key)
        moved += 1

    if moved:
        final_by_section["supply"] = keep_supply
        final_by_section["dist"] = dist_items
    return moved


def _audit_final_sections(final_by_section: dict[str, list["Article"]]) -> int:
    if not isinstance(final_by_section, dict):
        return 0
    pruned = 0
    for key, items in list((final_by_section or {}).items()):
        keep: list[Article] = []
        for a in (items or []):
            if not isinstance(a, Article):
                continue
            reason = _postbuild_article_reject_reason(a, str(key))
            if reason:
                pruned += 1
                _mark_debug_postbuild_reject(str(key), a, reason)
                log.info("[AUDIT] drop section=%s reason=%s title=%s", key, reason, (a.title or "")[:120])
                continue
            keep.append(a)
        final_by_section[str(key)] = keep
    return pruned

def collect_all_sections(start_kst: datetime, end_kst: datetime) -> dict[str, list[Article]]:
    reset_extra_call_budget()
    reset_debug_report()
    raw_by_section: dict[str, list[Article]] = {}
    board_source_by_section: dict[str, list[Article]] = {str(sec.get("key") or "").strip(): [] for sec in SECTIONS if str(sec.get("key") or "").strip()}

    ordered = sorted(SECTIONS, key=lambda s: 0 if s["key"] == "policy" else 1)
    for sec in ordered:
        raw_by_section[sec["key"]] = collect_candidates_for_section(sec, start_kst, end_kst)

    # 기사에서 언급된 보고서/자료(KREI 이슈+ 등)를 policy 섹션에 자동 보완
    try:
        _maybe_add_krei_issues_to_policy(raw_by_section, start_kst, end_kst)
    except Exception as e:
        log.warning("[WARN] report augmentation failed: %s", e)

    # ✅ 정책/기관 도메인(정책브리핑/농식품부/aT/농관원/KREI 등)은 수급/유통 쿼리에도 걸릴 수 있다.
    #    수집 단계에서는 살려두되, 최종 섹션은 policy로 강제 이동(누락/오분류 방지).
    policy_conf = next((s for s in SECTIONS if s.get("key") == "policy"), None)
    if policy_conf is not None:
        moved = 0
        for sk, lst in list(raw_by_section.items()):
            if sk == "policy" or not lst:
                continue
            keep = []
            for a in lst:
                try:
                    d = normalize_host(a.domain)
                except Exception:
                    d = (a.domain or "").lower()
                p = (a.press or "").strip()
                _mix_text = (a.title + " " + a.description).lower()
                dist_export_field_like = is_dist_export_field_context(a.title or "", a.description or "", d, p)
                dist_market_ops_like = is_dist_market_ops_context(a.title or "", a.description or "", d, p)
                dist_supply_center_like = is_dist_supply_management_center_context(a.title or "", a.description or "")
                dist_sales_channel_ops_like = is_dist_sales_channel_ops_context(a.title or "", a.description or "")
                policy_export_support_like = is_policy_export_support_brief_context(a.title or "", a.description or "", d, p)
                # policy-like(정책/통상/제도) 기사면 policy로 이동
                trade_like = False
                try:
                    _h = best_horti_score(a.title or "", a.description or "")
                except Exception:
                    _h = 0.0
                if is_trade_policy_issue(_mix_text) and (not dist_export_field_like) and _h < 2.2:
                    # dist 앵커(도매시장/APC/경락/반입 등)가 강하면 dist로 남겨야 하므로 여기서 이동하지 않음
                    _dist_hits = count_any(_mix_text, [t.lower() for t in (
                        "가락시장","도매시장","공판장","공영도매시장","경락","경매","반입",
                        "산지유통","산지유통센터","apc","도매법인","중도매","시장도매인",
                        "물류","물류센터","출하","집하"
                    )])
                    if _dist_hits < 2 and (not has_apc_agri_context(_mix_text)):
                        trade_like = True

                policy_general_macro_tail = is_policy_general_macro_tail_context(a.title or "", a.description or "", d, p)
                policy_agri_anchor_hits = count_any(
                    _mix_text,
                    [w.lower() for w in ("농산물", "농업", "농가", "원예", "과수", "과일", "채소", "화훼", "도매시장", "공판장", "가락시장", "산지유통", "산지유통센터", "면세유", "비료")],
                )
                move_to_policy = False
                if is_policy_announcement_issue(_mix_text, d, p) or is_policy_market_brief_context(_mix_text, d, p) or trade_like or is_supply_stabilization_policy_context(_mix_text, d, p) or policy_export_support_like:
                    move_to_policy = True
                elif is_macro_policy_issue(_mix_text) and (not policy_general_macro_tail):
                    if policy_agri_anchor_hits >= 2 or policy_domain_override(d, _mix_text) or (is_trade_policy_issue(_mix_text) and (not dist_export_field_like)):
                        move_to_policy = True
                if dist_export_field_like or dist_market_ops_like or dist_supply_center_like or dist_sales_channel_ops_like:
                    move_to_policy = False

                if move_to_policy:

                    a.section = "policy"
                    # policy 섹션 기준으로 재스코어링
                    try:
                        a.score = compute_rank_score(a.title, a.description, d, a.pub_dt_kst, policy_conf, p)
                    except Exception:
                        pass
                    raw_by_section.setdefault("policy", []).append(a)
                    moved += 1
                else:
                    keep.append(a)
            raw_by_section[sk] = keep
        if moved:
            # policy 내부에서도 섹션-내 dedupe를 한번 더 적용
            try:
                _p_dedupe = DedupeIndex()
                uniq = []
                for a in raw_by_section.get("policy", []):
                    if _p_dedupe.add_and_check(a.canon_url, a.press, a.title_key, a.norm_key):
                        uniq.append(a)
                raw_by_section["policy"] = uniq
            except Exception:
                pass


    # ✅ 섹션 재조정(rebalancing)
    # - policy가 '판매 데이터 기반 소비 트렌드/소매 분석' 기사로 과밀해지는 것을 방지
    # - dist가 비는 날(도매시장/APC 기사 표현이 간접적인 경우) supply에서 dist로 이동시켜 누락을 줄임
    supply_conf = next((s for s in SECTIONS if s.get("key") == "supply"), None)
    dist_conf = next((s for s in SECTIONS if s.get("key") == "dist"), None)

    if supply_conf is not None and policy_conf is not None:
        moved_ps = 0
        keep_policy = []
        for a in raw_by_section.get("policy", []) or []:
            txt = (a.title + " " + a.description).lower()
            d = normalize_host(a.domain or "")
            p = (a.press or "").strip()
            tpc = (a.topic or "").strip()
            # topic이 '정책' 성격이면 policy를 유지 (섹션/태그 불일치 방지)
            if tpc and ("정책" in tpc or tpc in ("정부", "제도", "법", "관세", "예산", "지원")):
                keep_policy.append(a)
                continue
            # 소매 매출/판매 데이터 기반 트렌드(예: 무인 과일가게 판매 데이터)는 supply가 자연스러움
            if is_retail_sales_trend_context(txt) and (not policy_domain_override(d, txt)):
                # supply로 재평가해서 통과할 때만 이동
                try:
                    if is_relevant(a.title, a.description, d, a.canon_url or a.url, supply_conf, p):
                        a.section = "supply"
                        a.score = compute_rank_score(a.title, a.description, d, a.pub_dt_kst, supply_conf, p)
                        raw_by_section.setdefault("supply", []).append(a)
                        moved_ps += 1
                        continue
                except Exception:
                    pass
            keep_policy.append(a)
        raw_by_section["policy"] = keep_policy
        if moved_ps:
            log.info("[REBALANCE] moved %d retail-sales-trend item(s): policy -> supply", moved_ps)

    if dist_conf is not None and supply_conf is not None:
        # dist 후보가 너무 적으면 supply에서 '유통/도매/APC/수출' 신호가 강한 기사를 dist로 이동
        dist_now = len(raw_by_section.get("dist", []) or [])
        if dist_now < 4:
            moved_sd = 0
            keep_supply = []
            for a in raw_by_section.get("supply", []) or []:
                txt = (a.title + " " + a.description).lower()
                d = normalize_host(a.domain or "")
                p = (a.press or "").strip()

                # dist-like 판정(보수적): 유통/도매/APC/도매법인/하역/물류/수출/검역 등 + 원예 맥락
                dist_like_hits = count_any(txt, [t.lower() for t in (
                    "가락시장","도매시장","공판장","공영도매시장","경락","경매","반입",
                    "산지유통","산지유통센터","apc","도매법인","중도매","시장도매인",
                    "하역","하역비","하역대란","물류","물류센터","출하","집하",
                    "원산지","부정유통","단속","검역","통관","수출","선적","수출길","유통","도매"
                )])
                if is_dist_export_shipping_context(a.title, a.description):
                    dist_like_hits = max(dist_like_hits, 3)
                if is_dist_export_field_context(a.title, a.description, d, p):
                    dist_like_hits = max(dist_like_hits, 3)
                agri_media_bonus = 1 if d in {"agrinet.co.kr","nongmin.com","aflnews.co.kr","farminsight.net"} else 0
                dist_min_hits = 2 if agri_media_bonus else 3
                # 농업전문매체 기사라도 유통/도매/APC/출하/물류 신호가 최소 2개는 있어야 dist로 이동
                if dist_like_hits >= dist_min_hits and (best_horti_score(a.title, a.description) >= 1.6 or count_any(txt, [t.lower() for t in ("농산물","농식품","원예","과수","과일","채소","청과","화훼","절화")]) >= 1):
                    # dist 기준으로도 통과할 때만 이동
                    try:
                        if is_relevant(a.title, a.description, d, a.canon_url or a.url, dist_conf, p):
                            a.section = "dist"
                            a.score = compute_rank_score(a.title, a.description, d, a.pub_dt_kst, dist_conf, p)
                            raw_by_section.setdefault("dist", []).append(a)
                            moved_sd += 1
                            continue
                    except Exception:
                        pass
                keep_supply.append(a)
            raw_by_section["supply"] = keep_supply
            if moved_sd:
                log.info("[REBALANCE] moved %d dist-like item(s): supply -> dist", moved_sd)

    # -----------------------------
    # Topic↔Section 일관성 강제 (정책/통상/관세·통관 집행 이슈는 policy 섹션으로)
    #
    # 기존에는 a.topic == "정책"일 때만 이동을 시도해,
    # 실제로는 관세/통관/정부 조치 기사인데 topic이 '정책'으로 분류되지 않은 경우
    # (예: 뉴스핌 관세/보세구역 기사)가 supply에 남는 문제가 있었다.
    #
    # 개선: topic이 '정책'이 아니더라도,
    #       (1) 통상/관세/검역/통관 정책성(is_trade_policy_issue 등)이 강하고
    #       (2) 원예/품목 직접성(best_horti_score)이 약하면
    # policy로 이동한다. 단, 감귤/만감류처럼 품목 영향이 강하면 supply에 남길 수 있다.
    # -----------------------------
    moved_topic = 0
    for _sec_key in list(raw_by_section.keys()):
        items = raw_by_section.get(_sec_key, []) or []
        if not items:
            continue
        keep_items: list[Article] = []
        for a in items:
            # 이미 policy면 유지
            if a.section == "policy":
                keep_items.append(a)
                continue

            tpc = (a.topic or "").strip()
            mix = (a.title + " " + a.description).lower()
            d = normalize_host(a.domain or "")
            p = (a.press or "").strip()
            dist_export_field_like = is_dist_export_field_context(a.title or "", a.description or "", d, p)
            dist_market_ops_like = is_dist_market_ops_context(a.title or "", a.description or "", d, p)
            dist_supply_center_like = is_dist_supply_management_center_context(a.title or "", a.description or "")
            dist_sales_channel_ops_like = is_dist_sales_channel_ops_context(a.title or "", a.description or "")
            policy_export_support_like = is_policy_export_support_brief_context(a.title or "", a.description or "", d, p)
            policy_major_issue_like = is_policy_major_issue_context(a.title or "", a.description or "", d, p)
            remote_foreign_trade_like = is_remote_foreign_trade_brief_context(a.title or "", a.description or "", d)

            # 정책/통상/관세·통관 이슈 판정(빠른 판정)
            policy_like = (
                (tpc == "정책")
                or is_generic_import_item_context(mix)
                or is_supply_stabilization_policy_context(mix, d, p)
                or (is_trade_policy_issue(mix) and (not dist_export_field_like))
                or is_policy_announcement_issue(mix, d, p)
                or is_policy_market_brief_context(mix, d, p)
                or policy_major_issue_like
                or is_macro_policy_issue(mix)
                or policy_export_support_like
            )
            if remote_foreign_trade_like or dist_export_field_like or dist_market_ops_like or dist_supply_center_like or dist_sales_channel_ops_like:
                policy_like = False

            if not policy_like:
                keep_items.append(a)
                continue

            # 품목(원예) 직접성 평가: 강하면 supply 유지(토픽만 교정)
            try:
                bt, bs = best_topic_and_score(a.title, a.description)
            except Exception:
                bt, bs = ("", 0.0)

            try:
                horti_sc = best_horti_score(a.title, a.description)
            except Exception:
                horti_sc = 0.0

            # ✅ 품목 영향이 충분히 강하면(토픽+원예점수) 섹션 이동 방지
            if bt and bs >= 2.4 and horti_sc >= 2.2:
                a.topic = bt
                keep_items.append(a)
                continue

            # 그 외(정책성 강 + 품목 직접성 약)는 policy로 이동
            a.section = "policy"
            raw_by_section.setdefault("policy", []).append(a)
            moved_topic += 1
            continue

        raw_by_section[_sec_key] = keep_items
    if moved_topic:
        log.info("[REBALANCE] moved %d item(s) by policy-like override: -> policy", moved_topic)

    # ✅ Global section reassignment (best section by rescoring; reduces query-driven misplacement)
    try:
        if GLOBAL_SECTION_REASSIGN_ENABLED:
            moved_global = _global_section_reassign(raw_by_section, start_kst, end_kst)
            if moved_global:
                log.info("[REASSIGN] moved %d item(s) by global rescoring", moved_global)
    except Exception as e:
        log.warning("[WARN] global section reassignment failed: %s", e)

    # 안전장치: policy에 남아있는 병해충 실행형 문맥을 최종 선택 전 pest로 강제 정리
    try:
        moved_pf = _enforce_pest_priority_over_policy(raw_by_section)
        if moved_pf:
            log.info("[REBALANCE] moved %d pest-context item(s): policy -> pest", moved_pf)
    except Exception as e:
        log.warning("[WARN] pest-priority rebalance failed: %s", e)

    board_source_by_section = build_managed_commodity_board_source_by_section(raw_by_section)
    final_by_section: dict[str, list[Article]] = {}
    global_dedupe = DedupeIndex()

    # ✅ 전역 dedupe는 '후보 수집'이 아니라 '최종 선택'에서 적용(섹션 간 누락 방지)
    for sec in SECTIONS:
        key = sec["key"]
        candidates = raw_by_section.get(key, [])

        # 섹션 내부 품질/임계치/근접중복 억제는 기존 로직 유지하되,
        # 전역 dedupe로 인해 스킵될 수 있으니 여유분을 더 뽑아둔다.
        buffer_n = max(MAX_PER_SECTION * 8, 60)
        pre = select_top_articles(candidates, key, buffer_n)

        picked: list[Article] = []
        for a in pre:
            reason = _postbuild_article_reject_reason(a, key)
            if reason:
                log.info("[AUDIT] drop section=%s reason=%s title=%s", key, reason, (a.title or "")[:120])
                continue
            if global_dedupe.add_and_check(a.canon_url, a.press, a.title_key, a.norm_key):
                picked.append(a)
                if len(picked) >= MAX_PER_SECTION:
                    break

        final_by_section[key] = picked
        if DEBUG_SELECTION:
            top = sorted(candidates, key=_sort_key_major_first, reverse=True)[:12]
            log.info("[DEBUG] section=%s candidates=%d selected=%d", key, len(candidates), len(final_by_section[key]))
            for a in top:
                try:
                    nh = nh_boost((a.title + " " + a.description).lower(), key)
                except Exception:
                    nh = 0.0
                rk = _pest_region_key(a.title) if key == "pest" else ""
                log.info("  [DEBUG] %.2f pr=%s tier=%d region=%s nh=%.1f title=%s",
                         a.score, press_priority(a.press, a.domain), press_tier(a.press, a.domain),
                         rk, nh, a.title[:120])


    try:
        moved_dist = _rebalance_underfilled_dist_from_supply(final_by_section)
        if moved_dist:
            log.info("[REBALANCE] moved %d item(s) to underfilled dist from supply", moved_dist)
    except Exception as e:
        log.warning("[WARN] dist underfill rebalance failed: %s", e)

    pruned_final = _audit_final_sections(final_by_section)
    if pruned_final:
        log.info("[AUDIT] pruned %d final item(s) after section assembly", pruned_final)
    _sync_debug_with_final_sections(final_by_section)
    _set_last_commodity_board_source(board_source_by_section)

    return final_by_section


# -----------------------------
# OpenAI summaries (optional)
# -----------------------------
def openai_extract_text(resp_json: JsonDict) -> str:
    try:
        out = resp_json.get("output", [])
        if not out:
            return ""
        for block in out:
            for c in block.get("content", []):
                if c.get("type") in ("output_text", "text") and "text" in c:
                    return str(c["text"])
        return ""
    except Exception:
        return ""

def load_summary_cache(repo: str, token: str) -> dict[str, SummaryCacheEntry | str]:
    """요약 캐시를 repo 파일에서 로드.
    구조:
      { norm_key: {"s": "요약", "t": "2026-02-22T..."} }
    """
    path = OPENAI_SUMMARY_CACHE_PATH
    raw, _sha = github_get_file(repo, path, token, ref="main")
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def _prune_summary_cache(cache: dict[str, SummaryCacheEntry | str]) -> dict[str, SummaryCacheEntry]:
    if not isinstance(cache, dict) or not cache:
        return {}
    items = []
    for k, v in cache.items():
        if not k:
            continue
        if isinstance(v, str):
            s = v.strip()
            t = ""
        elif isinstance(v, dict):
            s = str(v.get("s", "") or "").strip()
            t = str(v.get("t", "") or "").strip()
        else:
            continue
        if not s:
            continue
        items.append((t, k, {"s": s, "t": t}))
    items.sort(key=lambda x: x[0], reverse=True)
    kept = {}
    for _t, k, v in items[:OPENAI_SUMMARY_CACHE_MAX]:
        kept[k] = v
    return kept

def save_summary_cache(repo: str, token: str, cache: dict[str, SummaryCacheEntry | str]) -> None:
    path = OPENAI_SUMMARY_CACHE_PATH
    cache2 = _prune_summary_cache(cache or {})
    raw_new = json.dumps(cache2, ensure_ascii=False, indent=2)
    raw_old, sha = github_get_file(repo, path, token, ref="main")
    if (raw_old or "").strip() == raw_new.strip():
        return
    github_put_file(repo, path, raw_new, token, f"Update summary cache ({len(cache2)})", sha=sha, branch="main")

def _openai_summarize_rows(rows: list[JsonDict]) -> dict[str, str]:
    """OpenAI Responses API를 호출해 rows를 요약.
    출력 형식: 각 줄 'id\t요약'
    """
    if not OPENAI_API_KEY or not rows:
        return {}

    system = (
        "너는 농협 경제지주 원예수급부(과수화훼) 실무자를 위한 '농산물 뉴스 요약가'다.\n"
        "- 절대 상상/추정으로 사실을 만들지 마라.\n"
        "- 각 기사 요약은 2문장 내, 110~200자 내. 핵심 팩트 중심.\n"
        "출력 형식: 각 줄 'id\t요약' 형태로만 출력."
    )
    user = "기사 목록(JSON):\n" + json.dumps(rows, ensure_ascii=False)

    payload: JsonDict = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if OPENAI_MAX_OUTPUT_TOKENS and OPENAI_MAX_OUTPUT_TOKENS > 0:
        payload["max_output_tokens"] = int(OPENAI_MAX_OUTPUT_TOKENS)
    if OPENAI_REASONING_EFFORT:
        payload["reasoning"] = {"effort": OPENAI_REASONING_EFFORT}
    if OPENAI_TEXT_VERBOSITY:
        payload["text"] = {"verbosity": OPENAI_TEXT_VERBOSITY}

    simplified = False  # HTTP 400 시 optional 파라미터 제거 후 1회 재시도

    last_resp = None
    for attempt in range(max(1, OPENAI_RETRY_MAX)):
        try:
            r = http_session().post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=70,
            )
        except Exception as exc:
            backoff = exponential_backoff(attempt, base=0.8, cap=20.0, jitter=0.4)
            log.warning("[OpenAI] network error (attempt %d/%d): %s -> sleep %.1fs", attempt+1, OPENAI_RETRY_MAX, exc, backoff)
            time.sleep(backoff)
            continue

        last_resp = r
        if r.ok:
            text = openai_extract_text(r.json()).strip()
            out = {}
            for line in text.splitlines():
                if "\t" not in line:
                    continue
                k, v = line.split("\t", 1)
                k = k.strip()
                v = v.strip()
                if k and v:
                    out[k] = v
            return out

        if r.status_code == 429 or r.status_code in (500, 502, 503, 504):
            backoff = retry_after_or_backoff(r.headers, attempt, base=0.8, cap=20.0, jitter=0.4)
            log.warning("[OpenAI] transient HTTP %s (attempt %d/%d) -> sleep %.1fs", r.status_code, attempt+1, OPENAI_RETRY_MAX, backoff)
            time.sleep(backoff)
            continue

        # HTTP 400: 모델/옵션 파라미터 불일치(예: reasoning/text 옵션 미지원) 가능
        # - optional 파라미터(reasoning/text)를 제거하고 1회만 재시도한다.
        if r.status_code == 400 and (("reasoning" in payload) or ("text" in payload)) and (not simplified):
            simplified = True
            payload.pop("reasoning", None)
            payload.pop("text", None)
            log.warning("[OpenAI] HTTP 400 -> retry once without optional params: %s", _safe_body(getattr(r, "text", ""), limit=400))
            time.sleep(0.6)
            continue

        log.warning("[OpenAI] summarize skipped: %s", _safe_body(getattr(r, "text", ""), limit=500))
        return {}

    if last_resp is not None:
        log.warning("[OpenAI] summarize failed after retries: %s", _safe_body(getattr(last_resp, "text", ""), limit=500))
    return {}

def openai_summarize_batch(articles: list[Article], cache: dict[str, SummaryCacheEntry | str] | None = None) -> dict[str, str]:
    """기사들을 배치로 요약. cache가 있으면 캐시된 키는 호출에서 제외."""
    if not OPENAI_API_KEY or not articles:
        return {}

    cache = cache or {}
    now_iso = datetime.now(tz=KST).isoformat()

    to_sum = []
    for a in articles:
        ck = cache.get(a.norm_key)
        if isinstance(ck, dict) and str(ck.get("s", "")).strip():
            continue
        if isinstance(ck, str) and ck.strip():
            continue
        to_sum.append(a)

    if not to_sum:
        return {}

    rows_all = []
    for a in to_sum:
        rows_all.append({
            "id": a.norm_key,
            "press": a.press,
            "title": a.title[:180],
            "desc": a.description[:260],
            "section": a.section,
            "url": a.originallink or a.link,
        })

    mapping = {}
    bs = max(5, int(OPENAI_BATCH_SIZE or 25))
    for i in range(0, len(rows_all), bs):
        rows = rows_all[i:i+bs]
        part = _openai_summarize_rows(rows)
        if part:
            mapping.update(part)
            for k, v in part.items():
                if k and v:
                    cache[k] = {"s": v, "t": now_iso}

    return mapping

def fill_summaries(by_section: dict[str, list[Article]], cache: dict[str, SummaryCacheEntry | str] | None = None, allow_openai: bool = True) -> dict[str, list[Article]]:
    all_articles: list[Article] = []
    for sec in SECTIONS:
        all_articles.extend(by_section.get(sec["key"], []))

    cache = cache or {}
    mapping = openai_summarize_batch(all_articles, cache=cache) if allow_openai else {}

    for a in all_articles:
        s = ""
        ck = cache.get(a.norm_key)
        if isinstance(ck, dict):
            s = str(ck.get("s", "") or "").strip()
        elif isinstance(ck, str):
            s = ck.strip()

        if not s:
            s = (mapping.get(a.norm_key) or "").strip()

        if not s:
            s = a.description.strip() or a.title.strip()
        a.summary = s
    return by_section


# -----------------------------
# GitHub Pages path helpers (✅ 4번: 404 방지)
# -----------------------------
def get_site_path(repo: str) -> str:
    """
    GitHub Pages 프로젝트 사이트의 base path를 결정.
    - 일반 프로젝트: https://owner.github.io/REPO/  -> site_path="/REPO/"
    - 사용자/조직 사이트: https://owner.github.io/ -> repo_name이 *.github.io 일 수 있음 -> site_path="/"
    """
    _owner, name = repo.split("/", 1)
    if name.lower().endswith(".github.io"):
        return "/"
    return f"/{name}/"

def build_site_url(site_path: str, rel: str) -> str:
    site_path = site_path if site_path.endswith("/") else site_path + "/"
    rel = rel.lstrip("/")
    return site_path + rel



def get_run_site_path(repo: str) -> str:
    site_path = get_site_path(repo)
    if not DEV_SINGLE_PAGE_MODE:
        return site_path
    try:
        preview_url = get_pages_base_url(repo)
        preview_path = (urlparse(preview_url).path or "/").rstrip("/")
        if not preview_path:
            return "/"
        return preview_path + "/"
    except Exception:
        return site_path

def build_daily_url(base_url: str, report_date: str, cache_bust: bool = False, rel_path: str = "") -> str:
    """Build daily URL; defaults to archive path, or uses rel_path for single-page preview mode."""
    base = str(base_url or "").rstrip("/")
    if rel_path:
        url = f"{base}/{str(rel_path).lstrip('/')}"
    else:
        url = f"{base}/archive/{report_date}.html"
    if not cache_bust:
        return url
    v = re.sub(r"[^0-9A-Za-z_-]", "", str(BUILD_TAG or ""))[:24] or now_kst().strftime("%Y%m%d%H%M")
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}v={v}"


# -----------------------------
# Rendering (HTML)
# -----------------------------
def esc(s: str) -> str:
    return html.escape(s or "")

def display_section_title(title: str) -> str:
    # 표준화: 과거 페이지의 섹션 표기를 최신 포맷으로 통일
    if not title:
        return ""
    t = str(title)
    if t.startswith("유통 및 현장"):
        return "유통 및 현장"
    if t == "정책 및 주요 이슈":
        return "정책 및 주요 이슈"
    return t



def _normalize_existing_chipbar_titles(html_text: str) -> str:
    """Normalize chipbar title labels on already-existing chipbars (do not require rebuild).

    Some older archived pages already have a chipbar generated by older code, so
    `display_section_title()` did not run and long labels (e.g. "유통 및 현장 (...)")
    remain. This function updates only the visible label text inside `.chipTitle`.
    """
    if not html_text or 'class="chipTitle"' not in html_text:
        return html_text

    def _repl(m: re.Match[str]) -> str:
        prefix, inner, suffix = m.group(1), m.group(2), m.group(3)
        raw = html.unescape(inner or "")
        norm = display_section_title(raw)
        if norm == raw:
            return m.group(0)
        return prefix + esc(norm) + suffix

    # chipTitle content should not include '<', so use a safe class-specific pattern
    return re.sub(r'(<span\s+class="chipTitle">)([^<]*)(</span>)', _repl, html_text, flags=re.I)

def _rebuild_missing_chipbar_from_sections(html_text: str) -> str:
    """Rebuild chipbar from section blocks when broken legacy pages lost it.

    This is a safety net for old archived HTML that may be missing the chipbar
    due to previous patch bugs. New pages always include chipbar in the template.
    """
    if not html_text:
        return html_text
    if ('class="chipbar"' in html_text and 'class="chips"' in html_text):
        return html_text

    try:
        conf_by_key = {str(x.get("key")): x for x in (SECTIONS or []) if isinstance(x, dict)}
    except Exception:
        conf_by_key = {}

    chips = []
    for m in re.finditer(r"<section[^>]+id=[\"\']sec-([^\"\']+)[\"\'][^>]*>(.*?)</section>", html_text, flags=re.I | re.S):
        key = (m.group(1) or "").strip()
        body = m.group(2) or ""
        conf = conf_by_key.get(key, {})
        title = str(conf.get("title") or key)
        color = str(conf.get("color") or "#cbd5e1")
        cnt_m = re.search(r"<div[^>]*class=[\"\']secCount[\"\'][^>]*>\s*(\d+)\s*건\s*</div>", body, flags=re.I | re.S)
        n = int(cnt_m.group(1)) if cnt_m else 0
        chips.append((key, title, n, color))

    if not chips:
        return html_text

    parts = []
    for k, title, n, color in chips:
        parts.append(
            f'<a class="chip" style="border-color:{color};" href="#sec-{k}">'
            f'<span class="chipTitle">{esc(display_section_title(title))}</span><span class="chipN">{n}</span></a>'
        )
    chips_html = "\n".join(parts)
    chipbar_block = (
        '    <div class="chipbar">\n'
        '      <div class="chipwrap">\n'
        f'        <div class="chips" data-swipe-ignore="1">{chips_html}</div>\n'
        '      </div>\n'
        '    </div>\n'
    )
    html_new, n_ins = re.subn(r"(\n\s*<div class=\"wrap\">)", "\n" + chipbar_block + r"\1", html_text, count=1, flags=re.I)
    return html_new if n_ins else html_text


def fmt_dt(dt_: datetime) -> str:
    return dt_.strftime("%m/%d %H:%M")

def short_date_label(iso_date: str) -> str:
    return iso_date[2:] if len(iso_date) == 10 else iso_date

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]

def weekday_label(iso_date: str) -> str:
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
        return WEEKDAY_KR[d.weekday()]
    except Exception:
        return ""

def render_debug_report_html(report_date: str, site_path: str) -> str:
    """HTML 하단에 삽입되는 디버그 리포트(옵션).
    활성화: 환경변수 DEBUG_REPORT=1
    - 후보 상위 N개 점수/신호/선정여부
    - 필터링 단계에서 제외된 일부 기사와 사유
    - (옵션) docs/debug/YYYY-MM-DD.json 링크
    """
    if not DEBUG_REPORT:
        return ""

    with _DEBUG_LOCK:
        data: JsonDict = {
            "generated_at_kst": DEBUG_DATA.get("generated_at_kst"),
            "build_tag": DEBUG_DATA.get("build_tag"),
            "filter_rejects": list(DEBUG_DATA.get("filter_rejects", [])),
            "sections": dict(DEBUG_DATA.get("sections", {})),
        }

    # 요약(사유 카운트)
    reason_count: dict[str, int] = {}
    filter_rejects = data["filter_rejects"] if isinstance(data.get("filter_rejects"), list) else []
    for r in filter_rejects:
        reason = r.get("reason", "unknown")
        reason_count[reason] = reason_count.get(reason, 0) + 1
    reason_items = sorted(reason_count.items(), key=lambda x: x[1], reverse=True)[:12]

    # JSON 링크(작성 옵션이 켜져 있을 때만)
    json_href = ""
    if DEBUG_REPORT_WRITE_JSON:
        if DEV_SINGLE_PAGE_MODE:
            json_href = _dev_single_page_debug_url(report_date, site_path)
        else:
            json_href = build_site_url(site_path, f"debug/{report_date}.json")

    def _kv(label: str, value: str) -> str:
        return f"<span class='dbgkv'><b>{esc(label)}:</b> {esc(value)}</span>"

    # 섹션 테이블
    sec_blocks = []
    section_payloads = data["sections"] if isinstance(data.get("sections"), dict) else {}
    for sec_key, payload in section_payloads.items():
        top = payload.get("top", [])
        rows = []
        for it in top:
            sig = it.get("signals", {}) or {}
            badge = "✅" if it.get("selected") else "—"
            core = "핵심" if it.get("is_core") else ""
            rows.append(
                "<tr>"
                f"<td class='c'>{badge}</td>"
                f"<td class='c'>{esc(core)}</td>"
                f"<td class='r'>{it.get('score','')}</td>"
                f"<td class='c'>{it.get('tier','')}</td>"
                f"<td>{esc(it.get('press',''))}</td>"
                f"<td class='muted'>{esc(it.get('domain',''))}</td>"
                f"<td class='r'>{sig.get('horti_sc','')}</td>"
                f"<td class='r'>{sig.get('market_hits','')}</td>"
                f"<td class='r'>{sig.get('strength','')}</td>"
                f"<td class='r'>{sig.get('offtopic_pen','')}</td>"
                f"<td class='muted'>{esc(it.get('reason',''))}</td>"
                f"<td><a href='{esc(it.get('url',''))}' target='_blank' rel='noopener'>{esc(it.get('title',''))}</a></td>"
                "</tr>"
            )
        rows_html = "".join(rows) if rows else "<tr><td colspan='12' class='muted'>표시할 후보가 없습니다.</td></tr>"

        sec_blocks.append(f"""
        <div class="dbgSec">
          <div class="dbgSecHead">
            <b>{esc(sec_key)}</b>
            <span class="muted">candidates={payload.get('total_candidates','?')} selected={payload.get('total_selected','?')} thr={payload.get('threshold','?')} tail={payload.get('tail_cut','?')} core_min={payload.get('core_min','?')}</span>
          </div>
          <div class="dbgTableWrap">
            <table class="dbgTable">
              <thead>
                <tr>
                  <th class="c">선정</th><th class="c">핵심</th><th class="r">점수</th><th class="c">Tier</th>
                  <th>매체</th><th>도메인</th>
                  <th class="r">품목</th><th class="r">시장</th><th class="r">강신호</th><th class="r">오프</th>
                  <th>미선정 사유</th><th>제목</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>
        """)

    # 필터링 제외 표(상위 일부)
    rej_rows = []
    for r in data["filter_rejects"][:min(len(data["filter_rejects"]), 60)]:
        rej_rows.append(
            "<tr>"
            f"<td class='c'>{esc(r.get('section',''))}</td>"
            f"<td class='muted'>{esc(r.get('reason',''))}</td>"
            f"<td>{esc(r.get('press',''))}</td>"
            f"<td class='muted'>{esc(r.get('domain',''))}</td>"
            f"<td><a href='{esc(r.get('url',''))}' target='_blank' rel='noopener'>{esc(r.get('title',''))}</a></td>"
            "</tr>"
        )
    rej_html = "".join(rej_rows) if rej_rows else "<tr><td colspan='5' class='muted'>필터링 제외 로그가 없습니다.</td></tr>"

    reason_line = ", ".join([f"{k}({v})" for k, v in reason_items]) if reason_items else "—"

    meta_line = " ".join([
        _kv("DEBUG_REPORT", "1"),
        _kv("BUILD_TAG", str(data.get("build_tag", ""))),
        _kv("generated_at_kst", str(data.get("generated_at_kst", ""))),
    ])

    link_line = ""
    if json_href:
        link_line = f"<div class='dbgLinks'><a href='{esc(json_href)}' target='_blank' rel='noopener'>debug json 보기</a></div>"

    return f"""
    <style>
      details.dbgWrap {{ margin-top:24px; padding-top:16px; border-top:1px dashed var(--line); }}
      details.dbgWrap summary {{ cursor:pointer; font-weight:700; }}
      .dbgMeta {{ margin:10px 0 8px; display:flex; flex-wrap:wrap; gap:8px; }}
      .dbgkv {{ background:#f8fafc; border:1px solid var(--line); padding:6px 8px; border-radius:10px; font-size:12px; }}
      .dbgLinks a {{ font-size:12px; color:var(--btn); }}
      .dbgSec {{ margin-top:16px; }}
      .dbgSecHead {{ display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
      .dbgTableWrap {{ max-width:100%; overflow-x:auto; overflow-y:visible; -webkit-overflow-scrolling:touch; border:1px solid var(--line); border-radius:12px; margin-top:8px; }}
      table.dbgTable {{ width:100%; border-collapse:collapse; font-size:12px; min-width:980px; }}
      table.dbgTable th, table.dbgTable td {{ border-bottom:1px solid var(--line); padding:6px 8px; vertical-align:top; }}
      table.dbgTable th {{ background:#f9fafb; }}
      .dbgTable .c {{ text-align:center; white-space:nowrap; }}
      .dbgTable .r {{ text-align:right; white-space:nowrap; }}
      .muted {{ color:var(--muted); }}
    </style>
    <details class="dbgWrap">
      <summary>디버그 리포트 (선정/필터 로그)</summary>
      {link_line}
      <div class="dbgMeta">{meta_line}</div>
      <div class="muted" style="font-size:12px;">필터링 제외 사유 상위: {esc(reason_line)}</div>
      {''.join(sec_blocks)}
      <div class="dbgSec">
        <div class="dbgSecHead"><b>필터링 제외(샘플)</b><span class="muted">최대 60건 표시</span></div>
        <div class="dbgTableWrap">
          <table class="dbgTable">
            <thead><tr><th class="c">섹션</th><th>사유</th><th>매체</th><th>도메인</th><th>제목</th></tr></thead>
            <tbody>{rej_html}</tbody>
          </table>
        </div>
      </div>
    </details>
    """


def make_section_insight(section_key: str, arts: list[Article]) -> tuple[str, list[str]]:
    """섹션 상단에 노출할 '한 줄 인사이트'와 태그.
    LLM 요약이 없어도 일관되게 동작하도록 휴리스틱 기반.
    """
    if not arts:
        return ("", [])
    txt = " ".join([(a.title or "") + " " + (a.description or "") for a in arts]).lower()

    tags: list[str] = []
    line = ""

    def add_tag(t: str) -> None:
        if t and t not in tags and len(tags) < 6:
            tags.append(t)

    if section_key == "pest":
        if "과수화상병" in txt:
            line = "과수화상병 리스크/대응 이슈가 핵심입니다."
            add_tag("과수화상병")
        elif "탄저병" in txt:
            line = "탄저병 등 주요 병해 대응 정보가 중심입니다."
            add_tag("탄저병")
        elif any(w in txt for w in ("냉해","동해","서리","저온")):
            line = "저온·냉/동해 피해 및 대비 정보가 중요합니다."
            add_tag("냉/동해")
        else:
            line = "생육 리스크와 병해충 방제 동향을 함께 점검하세요."
            add_tag("생육리스크")
        # 주요 품목 태그
        for c in _commodity_tags_in_text(txt, limit=9):
            add_tag(c)
    elif section_key == "supply":
        # 가격/수급 방향성
        if any(w in txt for w in ("상승","강세","오름","급등")):
            line = "가격 상승(강세) 신호가 포착됩니다."
            add_tag("가격↑")
        elif any(w in txt for w in ("하락","약세","내림","급락")):
            line = "가격 하락(약세) 신호가 포착됩니다."
            add_tag("가격↓")
        else:
            line = "수급/작황/출하 변수를 중심으로 확인하세요."
            add_tag("수급")
        for c in _commodity_tags_in_text(txt, limit=9):
            add_tag(c)
    elif section_key == "dist":
        line = "도매시장·공판장·유통현장 이슈를 점검하세요."
        for t in ("가락시장","도매시장","공판장","경락","반입","온라인도매시장","원산지","검역","통관"):
            if t.lower() in txt:
                add_tag(t)
    elif section_key == "policy":
        line = "대책·제도·협의체·시장 구조 변화 등 주요 이슈를 확인하세요."
        for t in ("지원","할인지원","할당관세","검역","통관","단속","고시","개정","브리핑","협의체","출범","보전제","특별관리"):
            if t.lower() in txt:
                add_tag(t)
    else:
        line = ""
    return (line, tags)


_COMMODITY_BOARD_SECTION_RANK = {"supply": 4, "dist": 3, "policy": 2, "pest": 1}


def _commodity_board_term_hits(text: str, terms: Sequence[str]) -> int:
    txt = str(text or "").lower()
    if not txt:
        return 0
    seen: set[str] = set()
    hits = 0
    for term in terms or []:
        term_l = str(term or "").strip().lower()
        if len(term_l) < 2 or term_l in seen:
            continue
        seen.add(term_l)
        if term_l in txt:
            hits += 1
    return hits


def _commodity_board_item_article_metrics(item: dict[str, Any], article: Article) -> dict[str, Any]:
    item_key = str(item.get("key") or "").strip()
    title = str(getattr(article, "title", "") or "")
    desc = str(getattr(article, "description", "") or "")
    title_l = title.lower()
    body_l = f"{title} {desc}".lower()
    base_terms = _managed_commodity_base_terms(item, limit=6)
    context_terms = _ordered_unique_terms(list(item.get("context_terms") or []) + list(item.get("match_terms") or []))
    matched_keys = managed_commodity_keys_for_article(article)
    match_count = len(matched_keys)
    single_focus = 1 if item_key and matched_keys == [item_key] else 0
    title_primary_hits = _commodity_board_term_hits(title_l, base_terms)
    title_context_hits = _commodity_board_term_hits(title_l, context_terms)
    body_primary_hits = _commodity_board_term_hits(body_l, base_terms)
    body_context_hits = _commodity_board_term_hits(body_l, context_terms)
    section_key = str(getattr(article, "section", "") or "").strip()
    board_score = (
        (float(getattr(article, "score", 0.0) or 0.0) * 0.35)
        + (title_primary_hits * 42.0)
        + (title_context_hits * 12.0)
        + (body_primary_hits * 8.0)
        + (body_context_hits * 3.0)
        + (14.0 if single_focus else 0.0)
        + (6.0 if getattr(article, "is_core", False) else 0.0)
        + (_COMMODITY_BOARD_SECTION_RANK.get(section_key, 0) * 2.0)
        + (4.0 if item.get("program_core") and section_key == "supply" else 0.0)
        - (max(0, match_count - 1) * 6.0)
    )
    return {
        "board_score": board_score,
        "title_primary_hits": title_primary_hits,
        "title_context_hits": title_context_hits,
        "body_primary_hits": body_primary_hits,
        "body_context_hits": body_context_hits,
        "single_focus": single_focus,
        "match_count": match_count,
        "section_rank": _COMMODITY_BOARD_SECTION_RANK.get(section_key, 0),
    }


def _commodity_board_item_article_sort_key(item: dict[str, Any], article: Article) -> tuple[Any, ...]:
    metrics = _commodity_board_item_article_metrics(item, article)
    return (
        float(metrics["board_score"]),
        int(metrics["title_primary_hits"]),
        int(metrics["single_focus"]),
        int(metrics["body_primary_hits"]),
        1 if getattr(article, "is_core", False) else 0,
        int(metrics["section_rank"]),
        float(getattr(article, "score", 0.0) or 0.0),
        getattr(article, "pub_dt_kst", datetime.min.replace(tzinfo=KST)),
    )


def _dedupe_articles_for_commodity_board(item: dict[str, Any], articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    out: list[Article] = []
    for article in sorted(
        articles,
        key=lambda a: _commodity_board_item_article_sort_key(item, a),
        reverse=True,
    ):
        key = article.canon_url or article.norm_key or article.title_key or article.url
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(article)
    return out


def build_managed_commodity_board_context(by_section: dict[str, list[Article]]) -> dict[str, Any]:
    secondary_preview_limit = 2
    item_state: dict[str, dict[str, Any]] = {
        str(item.get("key") or "").strip(): {**item, "articles": []}
        for item in MANAGED_COMMODITY_CATALOG
    }

    for sec in SECTIONS:
        for article in by_section.get(sec["key"], []) or []:
            for key in managed_commodity_keys_for_article(article):
                payload = item_state.get(key)
                if payload is None:
                    continue
                payload["articles"].append(article)

    active_items = 0
    active_program_items = 0
    for payload in item_state.values():
        articles = _dedupe_articles_for_commodity_board(payload, payload.get("articles") or [])
        payload["articles"] = articles
        payload["article_count"] = len(articles)
        payload["core_count"] = sum(1 for article in articles if getattr(article, "is_core", False))
        payload["active"] = bool(articles)
        payload["top_article"] = articles[0] if articles else None
        payload["top_article_board_score"] = (
            float(_commodity_board_item_article_metrics(payload, articles[0]).get("board_score", 0.0))
            if articles else 0.0
        )
        payload["preview_articles"] = articles[: 1 + secondary_preview_limit]
        payload["secondary_articles"] = articles[1 : 1 + secondary_preview_limit]
        payload["secondary_article_count"] = len(payload["secondary_articles"])
        payload["extra_articles"] = articles[1 + secondary_preview_limit :]
        payload["more_article_count"] = len(payload["extra_articles"])
        payload["section_keys"] = _ordered_unique_terms([str(getattr(article, "section", "") or "") for article in articles])
        if payload["active"]:
            active_items += 1
            if payload.get("program_core"):
                active_program_items += 1

    groups: list[dict[str, Any]] = []
    for group in MANAGED_COMMODITY_GROUP_SPECS:
        items = [item_state[str(spec.get("key") or "").strip()] for spec in group.get("items") or [] if str(spec.get("key") or "").strip() in item_state]
        active_group_items = [item for item in items if item.get("active")]
        inactive_group_items = [item for item in items if not item.get("active")]
        active_group_items.sort(
            key=lambda item: (
                0 if item.get("program_core") else 1,
                -float(item.get("top_article_board_score") or 0.0),
                -int(item.get("core_count") or 0),
                -int(item.get("article_count") or 0),
                int(item.get("order") or 0),
            )
        )
        inactive_group_items.sort(
            key=lambda item: (
                0 if item.get("program_core") else 1,
                int(item.get("order") or 0),
            )
        )
        groups.append(
            {
                "key": str(group.get("key") or "").strip(),
                "title": str(group.get("title") or "").strip(),
                "color": str(group.get("color") or "#475569").strip() or "#475569",
                "items": active_group_items,
                "active_items": active_group_items,
                "inactive_items": inactive_group_items,
                "item_total": len(items),
                "active_count": len(active_group_items),
                "inactive_count": len(inactive_group_items),
                "program_core_total": sum(1 for item in items if item.get("program_core")),
                "program_core_active": sum(1 for item in active_group_items if item.get("program_core")),
                "article_count": sum(int(item.get("article_count") or 0) for item in active_group_items),
            }
        )

    return {
        "groups": groups,
        "managed_total": len(MANAGED_COMMODITY_CATALOG),
        "program_total": sum(1 for item in MANAGED_COMMODITY_CATALOG if item.get("program_core")),
        "active_total": active_items,
        "active_program_total": active_program_items,
    }


def _hex_to_rgba(color: str, alpha: float) -> str:
    value = str(color or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6 or re.fullmatch(r"[0-9a-fA-F]{6}", value) is None:
        return f"rgba(15,23,42,{max(0.0, min(alpha, 1.0)):.3f})"
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red},{green},{blue},{max(0.0, min(alpha, 1.0)):.3f})"


def render_managed_commodity_board_nav_html(board_ctx: dict[str, Any]) -> str:
    groups = list(board_ctx.get("groups") or [])
    nav_terms: list[str] = []
    for group in groups:
        group_color = str(group.get("color") or "#475569")
        nav_terms.append(
            f'<a class="commodityGroupChip" data-swipe-ignore="1" '
            f'style="--group-chip-color:{esc(group_color)};--group-chip-soft:{esc(_hex_to_rgba(group_color, 0.12))};--group-chip-border:{esc(_hex_to_rgba(group_color, 0.38))};" '
            f'href="#commodity-group-{esc(str(group.get("key") or ""))}">'
            f'{esc(str(group.get("title") or ""))}<span>{int(group.get("active_count") or 0)}</span></a>'
        )
    return (
        '<div class="chipbar commodityBoardNav" data-view-pane-anchor="commodity">'
        '<div class="chipwrap">'
        f'<div class="commodityGroupNav">{"".join(nav_terms)}</div>'
        '</div>'
        '</div>'
    )


def render_managed_commodity_board_html(board_ctx: dict[str, Any]) -> str:
    groups = list(board_ctx.get("groups") or [])
    group_blocks: list[str] = []
    for group in groups:
        group_color = str(group.get("color") or "#475569")
        group_soft_bg = _hex_to_rgba(group_color, 0.07)
        group_soft_border = _hex_to_rgba(group_color, 0.22)
        item_cards: list[str] = []
        for item in group.get("active_items") or group.get("items") or []:
            badge_html = '<span class="commodityBadge core">수급사업</span>' if item.get("program_core") else ''
            signal_html = "".join(
                f'<span class="commoditySig" data-section="{esc(sec_key)}">{esc(_MANAGED_COMMODITY_SECTION_LABELS.get(sec_key, sec_key))}</span>'
                for sec_key in (item.get("section_keys") or [])
                if sec_key
            )
            primary_article = item.get("top_article") if isinstance(item.get("top_article"), Article) else None
            secondary_articles = [article for article in (item.get("secondary_articles") or []) if isinstance(article, Article)]
            extra_articles = [article for article in (item.get("extra_articles") or []) if isinstance(article, Article)]
            if primary_article:
                primary_section_key = str(getattr(primary_article, "section", "") or "").strip()
                primary_press_label = str(getattr(primary_article, "press", "") or "").strip()
                primary_meta_terms = [
                    term
                    for term in (
                        _MANAGED_COMMODITY_SECTION_LABELS.get(primary_section_key, primary_section_key),
                        primary_press_label,
                        fmt_dt(getattr(primary_article, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST)),
                    )
                    if term
                ]
                secondary_links = "".join(
                    f"""
                    <a class="commoditySupportStory" data-swipe-ignore="1" href="{esc(article.url)}" target="_top" rel="noopener">
                      <span class="commoditySupportLabel">{esc(_MANAGED_COMMODITY_SECTION_LABELS.get(str(getattr(article, "section", "") or "").strip(), str(getattr(article, "section", "") or "").strip()))}</span>
                      <span class="commoditySupportText">{esc(article.title)}</span>
                    </a>
                    """
                    for article in secondary_articles
                )
                extra_links = "".join(
                    f"""
                    <a class="commodityMoreStory" data-swipe-ignore="1" href="{esc(article.url)}" target="_top" rel="noopener">
                      <span class="commoditySupportLabel">{esc(_MANAGED_COMMODITY_SECTION_LABELS.get(str(getattr(article, "section", "") or "").strip(), str(getattr(article, "section", "") or "").strip()))}</span>
                      <span class="commoditySupportText">{esc(article.title)}</span>
                    </a>
                    """
                    for article in extra_articles
                )
                more_count = int(item.get("more_article_count") or 0)
                more_html = (
                    f"""
                    <details class="commodityMoreWrap" data-swipe-ignore="1">
                      <summary class="commodityMoreSummary" data-swipe-ignore="1">관련 기사 {more_count}건 더 보기</summary>
                      <div class="commodityMoreList">{extra_links}</div>
                    </details>
                    """
                    if more_count > 0 else ""
                )
                secondary_html = (
                    f"""
                    <div class="commoditySupportList">
                      <div class="commoditySupportTitle">추가 기사</div>
                      {secondary_links}
                    </div>
                    """
                    if secondary_links else ""
                )
                story_html = f"""
                <div class="commodityStoryCluster">
                  <div class="commodityPrimaryCard">
                    <div class="commodityPrimaryKicker">대표 기사</div>
                    <a class="commodityPrimaryStory" data-swipe-ignore="1" href="{esc(primary_article.url)}" target="_top" rel="noopener">{esc(primary_article.title)}</a>
                    <div class="commodityPrimaryMeta">{esc(" · ".join(primary_meta_terms))}</div>
                  </div>
                  {secondary_html}
                  {more_html}
                </div>
                """
            else:
                story_html = '<div class="commodityStoryMuted">아직 연결된 대표 기사가 없습니다.</div>'
            item_cards.append(
                f"""
                <article id="commodity-{esc(str(item.get('key') or ''))}" class="commodityTile{' isActive' if item.get('active') else ''}">
                  <div class="commodityTileTop">
                    <div class="commodityTileName">{esc(str(item.get('label') or ''))}</div>
                    {badge_html}
                  </div>
                  <div class="commodityTileMeta">
                    <span>기사 {int(item.get('article_count') or 0)}건</span>
                    <span>핵심 {int(item.get('core_count') or 0)}건</span>
                  </div>
                  <div class="commoditySignals">{signal_html or '<span class="commoditySig muted">미노출</span>'}</div>
                  {story_html}
                </article>
                """
            )

        inactive_chips = "".join(
            (
                f'<span class="commodityMiniChip{" isCore" if item.get("program_core") else ""}">'
                f'{esc(str(item.get("label") or ""))}</span>'
            )
            for item in (group.get("inactive_items") or [])
        )
        inactive_html = (
            f"""
            <div class="commodityInactive">
              <div class="commodityInactiveTitle">미연결 품목 {int(group.get('inactive_count') or 0)}개</div>
              <div class="commodityMiniGrid">{inactive_chips}</div>
            </div>
            """
            if inactive_chips else ""
        )
        empty_group_html = '<div class="empty commodityGroupEmpty">오늘 연결된 품목 기사가 없습니다.</div>' if not item_cards else ""
        group_blocks.append(
            f"""
            <section id="commodity-group-{esc(str(group.get('key') or ''))}" class="commodityGroupBlock" style="--commodity-group-color:{esc(group_color)};--commodity-group-soft:{esc(group_soft_bg)};--commodity-group-border:{esc(group_soft_border)};">
              <div class="commodityGroupHead">
                <div class="commodityGroupTitleWrap">
                  <span class="commodityGroupDot" style="background:{esc(group_color)}"></span>
                  <h3>{esc(str(group.get('title') or ''))}</h3>
                </div>
                <div class="commodityGroupMeta">활성 품목 {int(group.get('active_count') or 0)} / {int(group.get('item_total') or 0)} · 수급사업 {int(group.get('program_core_active') or 0)} / {int(group.get('program_core_total') or 0)}</div>
              </div>
              <div class="commodityGrid">
                {''.join(item_cards)}
              </div>
              {inactive_html}
              {empty_group_html}
            </section>
            """
        )

    return f"""
    <section id="commodity-board" class="commodityBoard" aria-labelledby="commodityBoardTitle">
      <div class="commodityHead">
        <div class="commodityHeadMain">
          <div class="commodityEyebrow">원예수급부 전체 관리 품목</div>
          <h2 id="commodityBoardTitle">전체 품목 보드</h2>
          <div class="commodityLead">품목별 관련 기사 풀을 먼저 넓게 모아 보여줍니다. 오늘의 브리핑은 이 기사 풀 안에서 선발되며, 수급사업 품목은 별도 배지로 강조합니다.</div>
        </div>
        <div class="commodityHeadStats" aria-label="품목 보드 요약">
          <div class="commodityHeadStat">
            <span class="commodityHeadStatLabel">전체 관리</span>
            <strong>{int(board_ctx.get('managed_total') or 0)}개</strong>
          </div>
          <div class="commodityHeadStat">
            <span class="commodityHeadStatLabel">오늘 연결</span>
            <strong>{int(board_ctx.get('active_total') or 0)}개</strong>
          </div>
          <div class="commodityHeadStat">
            <span class="commodityHeadStatLabel">수급사업 연결</span>
            <strong>{int(board_ctx.get('active_program_total') or 0)}개</strong>
          </div>
        </div>
      </div>
      {render_managed_commodity_board_nav_html(board_ctx)}
      {''.join(group_blocks)}
    </section>
    """

def render_daily_page(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict[str, list[Article]],
                      archive_dates_desc: list[str], site_path: str,
                      board_source_by_section: dict[str, list[Article]] | None = None) -> str:
    # 상단 칩 카운트 + 섹션별 중요도 정렬
    chips = []
    total = 0
    for sec in SECTIONS:
        lst = sorted(by_section.get(sec["key"], []), key=lambda a: ((1 if getattr(a, "is_core", False) else 0),) + _sort_key_major_first(a), reverse=True)
        by_section[sec["key"]] = lst
        n = len(lst)
        total += n
        chips.append((sec["key"], sec["title"], n, sec["color"]))

    is_dev_preview = DEV_SINGLE_PAGE_MODE
    preview_href = _dev_single_page_archive_url("", site_path) if is_dev_preview else site_path

    # prev/next: dev 미리보기는 단일 페이지이므로 운영 아카이브 링크를 만들지 않는다.
    prev_href = None
    next_href = None
    if report_date in archive_dates_desc:
        idx = archive_dates_desc.index(report_date)
        # prev(더 과거) = idx+1
        if idx + 1 < len(archive_dates_desc):
            prev_href = (
                _dev_single_page_archive_url(archive_dates_desc[idx + 1], site_path)
                if is_dev_preview else
                build_site_url(site_path, f"archive/{archive_dates_desc[idx+1]}.html")
            )
        # next(더 최신) = idx-1
        if idx - 1 >= 0:
            next_href = (
                _dev_single_page_archive_url(archive_dates_desc[idx - 1], site_path)
                if is_dev_preview else
                build_site_url(site_path, f"archive/{archive_dates_desc[idx-1]}.html")
            )

    # 날짜 select (value도 절대경로)
    if is_dev_preview:
        options = []
        for d in archive_dates_desc[:120]:
            sel = " selected" if d == report_date else ""
            options.append(
                f'<option value="{esc(_dev_single_page_archive_url(d, site_path))}"{sel}>'
                f'{esc(short_date_label(d))} ({esc(weekday_label(d))}) [DEV]</option>'
            )
        if not options:
            options_html = f'<option value="{esc(preview_href)}" selected>{esc(short_date_label(report_date))} [DEV]</option>'
        else:
            options_html = "\n".join(options)
    else:
        options = []
        for d in archive_dates_desc[:120]:
            sel = " selected" if d == report_date else ""
            options.append(
                f'<option value="{esc(build_site_url(site_path, f"archive/{d}.html"))}"{sel}>'
                f'{esc(short_date_label(d))} ({esc(weekday_label(d))})</option>'
            )
        if not options:
            options_html = f'<option value="{esc(build_site_url(site_path, f"archive/{report_date}.html"))}" selected>{esc(short_date_label(report_date))}</option>'
        else:
            options_html = "\n".join(options)

    def chip_html(k: str, title: str, n: int, color: str) -> str:
        chip_soft = _hex_to_rgba(color, 0.12)
        chip_border = _hex_to_rgba(color, 0.36)
        return (
            f'<a class="chip" style="--chip-color:{color};--chip-soft:{chip_soft};--chip-border:{chip_border};" href="#sec-{k}">'
            f'<span class="chipTitle">{esc(display_section_title(title))}</span><span class="chipN">{n}</span></a>'
        )

    chips_html = "\n".join([chip_html(*c) for c in chips])
    briefing_nav_html = (
        '<div class="chipbar briefingChipbar" data-view-pane-anchor="briefing">'
        '<div class="chipwrap">'
        f'<div class="chips" data-swipe-ignore="1">{chips_html}</div>'
        '</div>'
        '</div>'
    )
    commodity_board_ctx = build_managed_commodity_board_context(board_source_by_section or _get_last_commodity_board_source() or by_section)
    commodity_board_html = render_managed_commodity_board_html(commodity_board_ctx)
    briefing_active_sections = sum(1 for sec in SECTIONS if by_section.get(sec["key"]))
    briefing_core_total = sum(
        1
        for sec in SECTIONS
        for article in (by_section.get(sec["key"], []) or [])
        if getattr(article, "is_core", False)
    )
    briefing_hero_html = f"""
    <section class="briefingHero" aria-labelledby="briefingHeroTitle">
      <div class="briefingHeroMain">
        <div class="briefingEyebrow">오늘 꼭 확인할 핵심 기사</div>
        <h2 id="briefingHeroTitle">오늘의 브리핑</h2>
        <div class="briefingLead">섹션별 핵심 기사를 한 번에 훑고 바로 원문으로 이동할 수 있게 정리했습니다. 아래 섹션 칩을 누르면 원하는 영역으로 즉시 이동합니다.</div>
      </div>
      <div class="briefingHeroStats" aria-label="브리핑 요약">
        <div class="briefingHeroStat">
          <span class="briefingHeroStatLabel">섹션</span>
          <strong>{briefing_active_sections}개</strong>
        </div>
        <div class="briefingHeroStat">
          <span class="briefingHeroStatLabel">기사</span>
          <strong>{total}건</strong>
        </div>
        <div class="briefingHeroStat">
          <span class="briefingHeroStatLabel">핵심</span>
          <strong>{briefing_core_total}건</strong>
        </div>
      </div>
    </section>
    """
    view_tabs_html = f"""
      <div class="viewTabs" role="tablist" aria-label="보기 전환">
        <button class="viewTab isActive" data-view-tab="briefing" type="button" role="tab" aria-selected="true" aria-controls="view-briefing">
          <span class="viewTabEyebrow">핵심 요약</span>
          <span class="viewTabTitle">오늘의 브리핑</span>
          <span class="viewTabDesc">섹션별 핵심 기사와 바로가기를 한눈에 확인합니다.</span>
          <span class="viewTabStats">
            <span class="viewTabStat"><strong>{briefing_active_sections}</strong>개 섹션</span>
            <span class="viewTabStat"><strong>{total}</strong>건 기사</span>
          </span>
        </button>
        <button class="viewTab" data-view-tab="commodity" type="button" role="tab" aria-selected="false" aria-controls="view-commodity">
          <span class="viewTabEyebrow">품목 추적</span>
          <span class="viewTabTitle">전체 품목 보드</span>
          <span class="viewTabDesc">품목별 관련 기사 풀과 대표 이슈를 바로 파악합니다.</span>
          <span class="viewTabStats">
            <span class="viewTabStat"><strong>{int(commodity_board_ctx.get('active_total') or 0)}</strong>개 연결 품목</span>
            <span class="viewTabStat"><strong>{int(commodity_board_ctx.get('active_program_total') or 0)}</strong>개 수급사업</span>
          </span>
        </button>
      </div>
    """

    # ✅ (2) 섹션 렌더: 더 이상 숨김(<details>) 사용하지 않고 '전부' 노출
    # ✅ (2) 섹션 내 기사는 중요도 순(이미 정렬됨)
    section_blocks: list[str] = []
    for sec in SECTIONS:
        key = sec["key"]
        title = sec["title"]
        color = sec["color"]
        lst = by_section.get(key, [])

        def render_card(a: Article, is_core: bool) -> str:
            url = a.originallink or a.link
            summary_html = "<br>".join(esc(a.summary).splitlines())
            core_badge = '<span class="badgeCore">핵심</span>' if is_core else ""
            return f"""
            <div class=\"card\" style=\"border-left-color:{color}\">
              <div class=\"cardTop\">
                <div class=\"meta\">
                  {core_badge}
                  <span class=\"press\">{esc(a.press)}</span>
                  <span class=\"dot\">·</span>
                  <span class=\"time\">{esc(fmt_dt(a.pub_dt_kst))}</span>
                  <span class=\"dot\">·</span>
                  <span class=\"topic\">{esc(a.topic)}</span>
                </div>
              <a class=\"btnOpen\" data-swipe-ignore=\"1\" href=\"{esc(url)}\" target=\"_top\" rel=\"noopener\">원문 열기</a>
              </div>
              <div class=\"ttl\">{esc(a.title)}</div>
              <div class=\"sum\">{summary_html}</div>
            </div>
            """

        if not lst:
            body_html = '<div class="empty">해당사항 없음</div>'
        else:
            body_html = "\n".join([render_card(a, getattr(a, "is_core", False)) for a in lst])

        section_blocks.append(
            f"""
            <section id=\"sec-{key}\" class=\"sec\">
              <div class=\"secHead\" style=\"border-left:8px solid {color};\">
                <div class=\"secTitle\">
                  <span class=\"dotColor\" style=\"background:{color}\"></span>
                  {esc(title)}
                </div>
                <div class=\"secCount\">{len(lst)}건</div>
              </div>
              <div class=\"secBody\">{body_html}</div>
            </section>
            """
        )

    sections_html = "\n".join(section_blocks)

    dev_version_url = _dev_single_page_version_url(site_path) if is_dev_preview else ""
    dev_archive_manifest_url = _dev_single_page_archive_manifest_url(site_path) if is_dev_preview else ""
    dev_badge_text = " [DEV]" if DEV_SINGLE_PAGE_MODE else ""
    dev_sub_text = " · 개발 버전 미리보기" if DEV_SINGLE_PAGE_MODE else ""
    if is_dev_preview:
        dev_sub_text += f" · build {BUILD_TAG}"
    dev_badge_html = '<span class="envBadge">DEV</span>' if DEV_SINGLE_PAGE_MODE else ""
    dev_meta_html = ""
    dev_refresh_js = ""
    dev_footer_html = ""
    if is_dev_preview:
        dev_meta_html = (
            f'  <meta name="agri-rendered-at-kst" content="{esc(RENDERED_AT_KST)}" />\n'
            f'  <meta name="agri-dev-version-url" content="{esc(dev_version_url)}" />'
        )
        dev_footer_html = (
            f'<div class="footer footerMeta">* DEV build {esc(BUILD_TAG)} · 생성 {esc(RENDERED_AT_KST)}</div>'
        )
        dev_refresh_js = f"""
      var currentBuild = {json.dumps(BUILD_TAG)};
      var devVersionUrl = {json.dumps(dev_version_url)};
      function syncLatestDevBuild() {{
        if (window.top && window.top !== window) return;
        if (!devVersionUrl || !window.fetch) return;
        var bustUrl = devVersionUrl + (devVersionUrl.indexOf("?") >= 0 ? "&" : "?") + "_ts=" + Date.now();
        fetch(bustUrl, {{ cache: "no-store" }}).then(function(r) {{ return (r && r.ok) ? r.json() : null; }}).then(function(data) {{ if (!data || typeof data.build_tag !== "string") return; var latest = data.build_tag; if (!latest || latest === currentBuild) return; var u = new URL(window.location.href); if (u.searchParams.get("v") === latest) return; u.searchParams.set("v", latest); window.location.replace(u.toString()); }}).catch(function() {{}});
      }}
      syncLatestDevBuild();
"""
    page_title = f"[{report_date} 농산물 뉴스 Brief]{dev_badge_text}"
    period = f"{start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}"
    home_href = preview_href if is_dev_preview else site_path
    nav_target_attr = ' target="_top"' if is_dev_preview else ""
    home_label = "DEV 미리보기" if is_dev_preview else "아카이브"
    def nav_btn(href: str | None, label: str, empty_msg: str, nav_key: str) -> str:
        if href:
            return f'<a class="navBtn" data-nav="{esc(nav_key)}" href="{esc(href)}"{nav_target_attr}>{esc(label)}</a>'
        # ✅ (3) 없는 페이지로 링크하지 않고 알림으로 처리
        return f'<button class="navBtn disabled" data-nav="{esc(nav_key)}" type="button" data-msg="{esc(empty_msg)}">{esc(label)}</button>'


    debug_html = render_debug_report_html(report_date, site_path) if DEBUG_REPORT else ""

    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <meta http-equiv=\"Cache-Control\" content=\"no-cache, no-store, must-revalidate\" />
  <meta http-equiv=\"Pragma\" content=\"no-cache\" />
  <meta http-equiv=\"Expires\" content=\"0\" />
  <meta name=\"agri-build\" content=\"{BUILD_TAG}\" />
{dev_meta_html}
  <title>{esc(page_title)}</title>
  <style>
    :root {{
      --bg:#ffffff;
      --text:#111827;
      --muted:#6b7280;
      --line:#e5e7eb;
      --card:#ffffff;
      --chip:#f8fafc;
      --btn:#1d4ed8;
      --btnHover:#1e40af;
      --btnBg:#ffffff;
      --shadow:0 4px 12px rgba(17,24,39,.08);
      --page-max:1220px;
      --topbar-height:172px;
      --chipbar-height:58px;
      --nav-chip-height:40px;
      --sticky-nav-offset:188px;
      --anchor-offset:248px;
    }}
    *{{box-sizing:border-box}}
    html {{
      scroll-behavior:smooth;
      scroll-padding-top: var(--anchor-offset);
    }}
    body{{margin:0;background:var(--bg); color:var(--text);
         font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, \"Noto Sans KR\", Arial;}}
    .wrap{{max-width:var(--page-max) !important;margin:0 auto !important;padding:18px 20px 80px !important;touch-action:pan-y;overscroll-behavior-x:contain;}}
    .topbar{{position:sticky;top:0;background:rgba(255,255,255,0.94);backdrop-filter:saturate(180%) blur(10px);
            border-bottom:1px solid var(--line); z-index:10;}}
    .topin{{max-width:var(--page-max);margin:0 auto;padding:12px 20px;display:grid;grid-template-columns:1fr;gap:10px;align-items:start}}
    h1{{margin:0;font-size:18px;letter-spacing:-0.2px}}
    .sub{{color:var(--muted);font-size:12.5px;margin-top:4px}}
    .envBadge{{display:inline-flex;align-items:center;justify-content:center;margin-left:8px;padding:2px 8px;border-radius:999px;background:#fff7ed;border:1px solid #fdba74;color:#9a3412;font-size:11px;font-weight:900;vertical-align:middle}}
    .navRow{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;width:100%}}
    .navRow > *{{min-width:0}}
    .navBtn{{white-space:nowrap}}
    .navBtn{{display:inline-flex;align-items:center;justify-content:center;
            height:36px;padding:0 12px;border:1px solid var(--line);border-radius:10px;
            background:#fff;color:#111827;text-decoration:none;font-size:13px; cursor:pointer;}}
    .navBtn:hover{{border-color:#cbd5e1}}
    .navBtn.navArchive{{background:#eef5ff !important;border-color:#b7d4ff !important;color:#1d4ed8 !important;font-weight:800}}
    .navBtn.navArchive:hover{{filter:brightness(0.98)}}
    /* fallback: first nav button */
    .navRow > a.navBtn:first-child{{background:#eef5ff !important;border-color:#b7d4ff !important;color:#1d4ed8 !important;font-weight:800}}

    .navBtn.disabled{{opacity:.45;cursor:pointer}}
    .dateSelWrap{{display:inline-flex;align-items:center;gap:6px}}
    select{{height:36px;border:1px solid var(--line);border-radius:10px;padding:0 10px;background:#fff;font-size:13px;
            width:165px; max-width:165px;}}
    @media (max-width: 520px) {{
      select{{width:145px; max-width:145px;}}
    }}

    .viewTabs{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:18px;align-items:stretch}}
    .viewTab{{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;gap:12px;min-height:132px;padding:18px 20px;border-radius:22px;border:1px solid #dbe4ee;background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);color:#0f172a;cursor:pointer;text-align:left;box-shadow:0 12px 28px rgba(15,23,42,.08);transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease}}
    .viewTab:hover{{transform:translateY(-1px);border-color:#bfdbfe;box-shadow:0 18px 36px rgba(15,23,42,.12)}}
    .viewTab.isActive{{background:linear-gradient(135deg,#0f172a 0%,#1d4ed8 100%);color:#fff;border-color:#0f172a;box-shadow:0 20px 40px rgba(29,78,216,.24)}}
    .viewTabEyebrow{{display:inline-flex;align-items:center;min-height:24px;padding:0 9px;border-radius:999px;background:rgba(14,165,233,.1);color:#075985;font-size:11px;font-weight:900;letter-spacing:.02em}}
    .viewTab.isActive .viewTabEyebrow{{background:rgba(255,255,255,.16);color:#e0f2fe}}
    .viewTabTitle{{font-size:24px;font-weight:900;letter-spacing:-0.5px;line-height:1.1}}
    .viewTabDesc{{max-width:420px;font-size:13px;line-height:1.55;color:#475569}}
    .viewTab.isActive .viewTabDesc{{color:rgba(255,255,255,.88)}}
    .viewTabStats{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:auto}}
    .viewTabStat{{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 11px;border-radius:999px;background:#eef2ff;color:#1e293b;font-size:12px;font-weight:800}}
    .viewTabStat strong{{font-size:13px}}
    .viewTab.isActive .viewTabStat{{background:rgba(255,255,255,.16);color:#fff}}

    .briefingHero{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:flex-start;margin-top:14px;padding:22px;border:1px solid #dbe4ee;border-radius:22px;background:radial-gradient(circle at top left, rgba(191,219,254,.75), transparent 34%),linear-gradient(135deg,#eff6ff 0%,#ffffff 56%,#f8fafc 100%);box-shadow:0 14px 34px rgba(15,23,42,.08)}}
    .briefingHeroMain{{min-width:0}}
    .briefingEyebrow{{display:inline-flex;align-items:center;min-height:26px;padding:0 10px;border-radius:999px;background:#0f172a;color:#fff;font-size:11px;font-weight:900;letter-spacing:.02em}}
    .briefingHero h2{{margin:10px 0 0;font-size:30px;line-height:1.05;letter-spacing:-0.8px}}
    .briefingLead{{margin-top:10px;max-width:720px;color:#334155;font-size:14px;line-height:1.65}}
    .briefingHeroStats{{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}}
    .briefingHeroStat{{display:flex;flex-direction:column;justify-content:center;min-width:110px;min-height:82px;padding:14px 16px;border-radius:18px;border:1px solid rgba(148,163,184,.25);background:rgba(255,255,255,.92);box-shadow:0 10px 24px rgba(15,23,42,.06)}}
    .briefingHeroStatLabel{{color:#64748b;font-size:11px;font-weight:900;letter-spacing:.04em}}
    .briefingHeroStat strong{{margin-top:6px;color:#0f172a;font-size:22px;font-weight:900;letter-spacing:-0.4px}}

    /* briefing chip bar */
    .chipbar{{position:relative;z-index:2;border:1px solid var(--line);border-radius:16px;background:rgba(248,250,252,.96);box-shadow:0 14px 32px rgba(15,23,42,.10);backdrop-filter:saturate(180%) blur(10px);overflow:hidden;}}
    .briefingChipbar{{margin:16px 0 0}}
    .commodityBoardNav{{margin:18px 18px 20px}}
    .chipwrap{{max-width:var(--page-max);margin:0 auto;padding:10px 18px;}}
    .chips,.commodityGroupNav{{display:flex;gap:10px;align-items:center;justify-content:flex-start;width:100%;}}
    .chips{{flex-wrap:wrap;overflow-x:auto; -webkit-overflow-scrolling:touch;}}
    .chips::-webkit-scrollbar{{height:8px}}
    .commodityGroupNav{{flex-wrap:wrap;}}
    .chip,.commodityGroupChip{{text-decoration:none;border:1px solid var(--chip-border, var(--group-chip-border, var(--line)));border-radius:999px;
          background:linear-gradient(180deg,var(--chip-soft, var(--group-chip-soft, var(--chip))) 0%, #ffffff 100%);font-size:13px;color:#111827;display:inline-flex;gap:8px;align-items:center;justify-content:center;min-width:0;min-height:var(--nav-chip-height);padding:0 16px;font-weight:900;box-shadow:inset 0 1px 0 rgba(255,255,255,.72);white-space:nowrap}}
    .chip:hover{{border-color:var(--chip-color, #cbd5e1);transform:translateY(-1px)}}
    .chipTitle{{font-weight:800;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
    .chipN,.commodityGroupChip span{{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;text-align:center;color:#fff;padding:0 8px;border-radius:999px;font-size:11px}}
    .chipN{{background:var(--chip-color, #111827)}}
    .chipDock{{position:fixed;top:var(--sticky-nav-offset);left:0;right:0;z-index:11;pointer-events:none;opacity:0;transform:translateY(-8px);transition:opacity .18s ease, transform .18s ease}}
    .chipDock.isVisible{{opacity:1;transform:translateY(0);pointer-events:auto}}
    .chipDockInner{{max-width:var(--page-max);margin:0 auto;padding:0 20px}}
    .chipDock .chipbar{{margin:0;box-shadow:0 18px 38px rgba(15,23,42,.14);background:rgba(248,250,252,.98)}}
    .chipDock .briefingChipbar,
    .chipDock .commodityBoardNav{{margin:0}}
    body.quickNavOpen{{overflow:hidden}}
    .mobileQuickNav{{display:none}}
    .mobileQuickNavToggle{{pointer-events:none;opacity:0;transform:translateY(8px);transition:opacity .18s ease, transform .18s ease}}
    .mobileQuickNav.isVisible .mobileQuickNavToggle{{pointer-events:auto;opacity:1;transform:translateY(0)}}
    .mobileQuickNavSheet{{position:fixed;inset:0;display:none;z-index:14}}
    .mobileQuickNavSheet.isOpen{{display:block}}
    .mobileQuickNavBackdrop{{position:absolute;inset:0;border:0;background:rgba(15,23,42,.42)}}
    .mobileQuickNavPanel{{position:absolute;left:12px;right:12px;bottom:14px;padding:16px;border:1px solid #dbe4ee;border-radius:24px;background:#ffffff;box-shadow:0 22px 56px rgba(15,23,42,.24)}}
    .mobileQuickNavHead{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}}
    .mobileQuickNavHead strong{{font-size:15px;letter-spacing:-0.2px}}
    .mobileQuickNavClose{{display:inline-flex;align-items:center;justify-content:center;min-height:34px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:#fff;color:#111827;font-size:12px;font-weight:800}}
    .mobileQuickNavBody .chipbar{{border:none;background:transparent;box-shadow:none;overflow:visible}}
    .mobileQuickNavBody .chipwrap{{padding:0;max-width:none}}
    .mobileQuickNavBody .chips,
    .mobileQuickNavBody .commodityGroupNav{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;justify-content:stretch;overflow:visible}}
    .mobileQuickNavBody .chip,
    .mobileQuickNavBody .commodityGroupChip{{width:100%;justify-content:space-between;min-height:48px;padding:0 14px;border-radius:18px;font-size:13px;box-shadow:0 10px 24px rgba(15,23,42,.12)}}

    .viewPane{{display:none}}
    .viewPane.isActive{{display:block}}
    .briefingPane{{margin-top:14px}}
    .commodityPane{{margin-top:14px}}

    .commodityBoard{{margin-top:14px;border:1px solid #dbe4ee;border-radius:22px;background:linear-gradient(180deg,#fff 0%,#f8fafc 100%);box-shadow:0 16px 34px rgba(15,23,42,.08);overflow:visible}}
    .commodityHead{{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:flex-start;gap:18px;padding:22px 22px 16px;border-bottom:1px solid rgba(229,231,235,.9);background:linear-gradient(135deg,#ffffff 0%,#f8fafc 68%,#f0fdf4 100%);overflow:hidden;isolation:isolate}}
    .commodityHead::after{{content:"";position:absolute;inset:-24% -6% -22% 48%;background:radial-gradient(circle at 50% 46%, rgba(110,231,183,.62) 0%, rgba(125,211,252,.26) 33%, rgba(255,255,255,0) 72%);pointer-events:none;z-index:0}}
    .commodityHeadMain{{position:relative;z-index:1;min-width:0}}
    .commodityHead h2{{margin:8px 0 0;font-size:30px;line-height:1.05;letter-spacing:-0.7px}}
    .commodityLead{{margin-top:10px;max-width:720px;color:#334155;font-size:14px;line-height:1.65}}
    .commodityEyebrow{{display:inline-flex;align-items:center;min-height:26px;padding:0 10px;border-radius:999px;background:#ecfeff;border:1px solid #99f6e4;color:#115e59;font-size:11px;font-weight:900;letter-spacing:.02em}}
    .commodityHeadStats{{position:relative;z-index:1;display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}}
    .commodityHeadStat{{display:flex;flex-direction:column;justify-content:center;min-width:110px;min-height:82px;padding:14px 16px;border-radius:18px;border:1px solid rgba(148,163,184,.24);background:rgba(255,255,255,.95);box-shadow:0 10px 24px rgba(15,23,42,.06)}}
    .commodityHeadStatLabel{{color:#64748b;font-size:11px;font-weight:900;letter-spacing:.04em}}
    .commodityHeadStat strong{{margin-top:6px;color:#0f172a;font-size:22px;font-weight:900;letter-spacing:-0.4px}}
    .commodityBadge{{display:inline-flex;align-items:center;justify-content:center;height:22px;padding:0 9px;border-radius:999px;font-size:11px;font-weight:900;white-space:nowrap}}
    .commodityBadge.core{{background:#dbeafe;color:#1d4ed8;border:1px solid #93c5fd}}
    .commoditySignals{{display:flex;flex-wrap:wrap;gap:6px;min-height:24px}}
    .commoditySig{{display:inline-flex;align-items:center;justify-content:center;height:22px;padding:0 8px;border-radius:999px;background:#eef2ff;color:#3730a3;font-size:11px;font-weight:800}}
    .commoditySig[data-section="supply"]{{background:#ccfbf1;color:#115e59}}
    .commoditySig[data-section="policy"]{{background:#dbeafe;color:#1d4ed8}}
    .commoditySig[data-section="dist"]{{background:#ede9fe;color:#6d28d9}}
    .commoditySig[data-section="pest"]{{background:#ffedd5;color:#b45309}}
    .commoditySig.muted{{background:#f8fafc;color:#94a3b8}}
    .commodityStoryCluster{{display:flex;flex-direction:column;gap:10px}}
    .commodityPrimaryCard{{padding:12px;border:1px solid #dbe4ee;border-radius:16px;background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%)}}
    .commodityPrimaryKicker{{display:inline-flex;align-items:center;justify-content:center;min-height:22px;padding:0 8px;border-radius:999px;background:#0f172a;color:#fff;font-size:10px;font-weight:900;letter-spacing:.02em}}
    .commodityPrimaryStory{{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-top:8px;color:#0f172a;font-size:14px;font-weight:900;line-height:1.52;text-decoration:none}}
    .commodityPrimaryStory:hover{{text-decoration:underline}}
    .commodityPrimaryMeta{{margin-top:7px;color:#64748b;font-size:11px;font-weight:700}}
    .commoditySupportList{{display:flex;flex-direction:column;gap:8px}}
    .commoditySupportTitle{{color:#64748b;font-size:11px;font-weight:900;letter-spacing:.02em}}
    .commoditySupportStory,.commodityMoreStory{{display:flex;align-items:flex-start;gap:8px;padding:9px 10px;border-radius:14px;border:1px solid #dbe4ee;background:#fff;color:#0f172a;text-decoration:none}}
    .commoditySupportStory:hover,.commodityMoreStory:hover{{border-color:#cbd5e1}}
    .commoditySupportLabel{{display:inline-flex;align-items:center;justify-content:center;min-height:20px;padding:0 7px;border-radius:999px;background:#eef2ff;color:#3730a3;font-size:10px;font-weight:900;flex:0 0 auto}}
    .commoditySupportText{{display:block;min-width:0;font-size:12px;line-height:1.5}}
    .commodityMoreWrap{{border:1px dashed #cbd5e1;border-radius:14px;background:#f8fafc}}
    .commodityMoreSummary{{list-style:none;cursor:pointer;padding:10px 12px;color:#334155;font-size:12px;font-weight:900}}
    .commodityMoreSummary::-webkit-details-marker{{display:none}}
    .commodityMoreList{{display:flex;flex-direction:column;gap:8px;padding:0 10px 10px}}
    .commodityStoryMuted{{padding:11px 12px;border:1px dashed #dbe4ee;border-radius:14px;background:#f8fafc;color:#94a3b8;font-size:12px}}
    .commodityBoardNav{{border-color:#cfe0f4;background:rgba(255,255,255,.98);box-shadow:0 18px 36px rgba(15,23,42,.12)}}
    .commodityGroupChip:hover{{border-color:var(--group-chip-color, #334155);transform:translateY(-1px)}}
    .commodityGroupChip{{border-color:var(--group-chip-border, var(--line));background:linear-gradient(180deg,var(--group-chip-soft, var(--chip)) 0%, #ffffff 100%);}}
    .commodityGroupChip span{{background:var(--group-chip-color, #111827)}}
    .commodityGroupBlock{{margin:0 18px 20px;padding:20px;border:1px solid var(--commodity-group-border, #dbe4ee);border-left:4px solid var(--commodity-group-color, #475569);border-radius:22px;background:linear-gradient(180deg,var(--commodity-group-soft, #f8fafc) 0%, #ffffff 100%);box-shadow:0 16px 34px rgba(15,23,42,.07), inset 0 1px 0 rgba(255,255,255,.8);scroll-margin-top:calc(var(--anchor-offset) + 28px)}}
    .commodityGroupHead{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0 0 14px;border-bottom:1px solid var(--commodity-group-border, #dbe4ee);margin-bottom:16px}}
    .commodityGroupTitleWrap{{display:flex;align-items:center;gap:10px}}
    .commodityGroupTitleWrap h3{{margin:0;font-size:16px}}
    .commodityGroupDot{{width:12px;height:12px;border-radius:999px;box-shadow:0 0 0 8px var(--commodity-group-soft, rgba(15,23,42,.06))}}
    .commodityGroupMeta{{color:#64748b;font-size:12px;font-weight:700}}
    .commodityGrid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
    .commodityTile{{display:flex;flex-direction:column;gap:9px;padding:13px;border:1px solid #dbe4ee;border-radius:16px;background:#fff}}
    .commodityTile.isActive{{border-color:#86efac;box-shadow:0 8px 24px rgba(15,118,110,.08)}}
    .commodityTileTop{{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}}
    .commodityTileName{{font-size:16px;font-weight:900;line-height:1.35}}
    .commodityTileMeta{{display:flex;gap:10px;flex-wrap:wrap;color:#64748b;font-size:12px;font-weight:700}}
    .commodityInactive{{margin-top:12px;padding:12px;border:1px dashed #dbe4ee;border-radius:14px;background:#f8fafc}}
    .commodityInactiveTitle{{color:#64748b;font-size:12px;font-weight:800;margin-bottom:8px}}
    .commodityMiniGrid{{display:flex;flex-wrap:wrap;gap:8px}}
    .commodityMiniChip{{display:inline-flex;align-items:center;justify-content:center;min-height:30px;padding:0 10px;border-radius:999px;border:1px solid #dbe4ee;background:#fff;color:#475569;font-size:12px;font-weight:700}}
    .commodityMiniChip.isCore{{border-color:#93c5fd;background:#eff6ff;color:#1d4ed8}}
    .commodityEmpty{{padding:20px 18px 22px}}
    .commodityGroupEmpty{{margin-top:10px;padding:14px 12px;border:1px dashed #dbe4ee;border-radius:14px;background:#f8fafc;color:#64748b;font-size:13px}}

    .sec{{margin-top:14px !important;border:1px solid var(--line);border-radius:14px !important;overflow:hidden;background:var(--card);
          scroll-margin-top: calc(var(--anchor-offset) + 18px);
    }}
    .secHead{{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:#fafafa;border-bottom:1px solid var(--line)}}
    .secTitle{{font-size:15px;font-weight:900;display:flex;align-items:center;gap:10px}}
    .dotColor{{width:10px;height:10px;border-radius:999px}}
    .secCount{{font-size:12px;color:var(--muted);background:#fff;border:1px solid var(--line);padding:4px 10px;border-radius:999px}}
    .secBody{{padding:12px 12px 14px}}
    .card{{border:1px solid var(--line);border-left:5px solid #334155;border-radius:14px;padding:12px;margin:10px 0;background:#fff}}
    .cardTop{{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}}
    .meta{{color:var(--muted);font-size:12px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
    .press{{color:#111827;font-weight:900}}
    .dot{{opacity:.5}}
    .topic{{background:#f3f4f6;border:1px solid var(--line);padding:2px 8px;border-radius:999px;font-size:11.5px;color:#111827}}
    .ttl{{margin-top:8px;font-size:15px;line-height:1.35;font-weight:900}}
    .sum{{margin-top:8px;color:#374151;font-size:13px;line-height:1.55}}

    .badgeCore {{
      display:inline-flex; align-items:center; justify-content:center;
      height:18px; padding:0 8px; border-radius:999px;
      background:#111827; color:#fff; font-size:11px; font-weight:900;
      margin-right:2px;
    }}

    .btnOpen{{display:inline-flex;align-items:center;justify-content:center;
             height:38px;padding:0 16px;border-radius:12px;border:1px solid var(--btn);
             background:var(--btn);color:#fff;text-decoration:none;font-size:13px;font-weight:900}}
    .btnOpen:hover{{background:var(--btnHover);border-color:var(--btnHover)}}

    .empty{{color:var(--muted);font-size:13px;padding:10px 2px}}
    .footer{{margin-top:18px;color:var(--muted);font-size:12px}}
    .footerMeta{{margin-top:8px;font-family:ui-monospace, SFMono-Regular, Consolas, monospace}}
    .swipeHint{{display:none;align-items:center;justify-content:center;gap:8px;margin:8px 0 2px;color:var(--muted);font-size:12px;user-select:none;opacity:.9;transition:opacity .25s ease, transform .25s ease}}
    .swipeHint.show{{display:flex}}
    .swipeHint.hide{{opacity:0;transform:translateY(-4px)}}
    .swipeHint .arrow{{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border:1px solid var(--line);border-radius:999px;background:var(--btnBg, #fff);font-size:11px;line-height:1}}
    .swipeHint .txt{{letter-spacing:-0.1px}}
    .swipeHint .pill{{padding:2px 8px;border:1px dashed var(--line);border-radius:999px;background:rgba(255,255,255,.02)}}
    @media (hover:hover) and (pointer:fine){{ .swipeHint{{display:none !important;}} }}
    @media (prefers-reduced-motion: reduce){{ .swipeHint{{transition:none}} }}
    .navLoading{{display:none;align-items:center;justify-content:center;margin:4px 0 0;color:var(--muted);font-size:12px}}
    .navLoading.show{{display:flex}}
    .navLoading .badge{{padding:3px 10px;border:1px solid var(--line);border-radius:999px;background:var(--btnBg, #fff);box-shadow:var(--shadow, 0 4px 12px rgba(17,24,39,.08))}}
    .navRow{{transition:transform .18s ease, opacity .18s ease}}
    .navRow.swipeActive{{transition:none}}
    .navRow.swipeSettling{{transition:transform .18s ease, opacity .18s ease}}
    @media (max-width: 900px) and (hover: none), (max-width: 900px) and (pointer: coarse){{
      .chipDock{{display:none}}
      .chips,.commodityGroupNav{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;justify-content:stretch;overflow:visible}}
      .chip,.commodityGroupChip{{width:100%;justify-content:space-between;min-height:48px;padding:0 14px;border-radius:18px}}
      .chipN,.commodityGroupChip span{{min-width:24px;height:24px;padding:0 7px}}
      .mobileQuickNav{{display:block;position:fixed;right:14px;bottom:18px;z-index:13}}
      .mobileQuickNavToggle{{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:0 14px;border:1px solid #0f172a;border-radius:999px;background:#0f172a;color:#fff;font-size:13px;font-weight:900;box-shadow:0 18px 38px rgba(15,23,42,.28)}}
    }}
    @media (max-width: 840px){{
      .topbar{{background:rgba(255,255,255,0.98);backdrop-filter:none}}
      .wrap{{padding:16px 16px 72px !important}}
      .topin{{padding:12px 16px}}
      .chipDockInner{{padding:0 16px}}
      .commodityGrid{{grid-template-columns:repeat(2,minmax(0,1fr))}}
    }}
    @media (max-width: 640px){{
      .wrap{{padding:12px 12px 64px !important}}
      .topin{{gap:8px}}
      .navRow{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px}}
      .navRow > .navBtn:first-child{{grid-column:1}}
      .navRow > .navBtn:nth-child(2){{grid-column:2}}
      .navRow > .dateSelWrap{{grid-column:1; width:100%}}
      .navRow > .navBtn:last-child{{grid-column:2}}
      .dateSelWrap{{width:100%}}
      .dateSelWrap select{{width:100%;max-width:none}}
      .viewTabs{{grid-template-columns:repeat(2,minmax(0,1fr));gap:4px;margin-top:12px;padding:4px;border:1px solid #dbe4ee;border-radius:18px;background:#f8fafc}}
      .viewTab{{min-height:auto;padding:10px 12px;border:none;border-radius:14px;gap:4px;box-shadow:none;align-items:center;justify-content:center;background:transparent}}
      .viewTab:hover{{transform:none;box-shadow:none;border-color:transparent}}
      .viewTab.isActive{{box-shadow:0 10px 22px rgba(29,78,216,.22)}}
      .viewTabEyebrow{{display:none}}
      .viewTabTitle{{width:100%;font-size:17px;letter-spacing:-0.35px;text-align:center}}
      .viewTabDesc{{display:none}}
      .viewTabStats{{display:none}}
      .briefingPane,.commodityPane{{margin-top:12px}}
      .briefingHero{{grid-template-columns:1fr;padding:0;border:none;border-radius:0;gap:10px;background:transparent;box-shadow:none}}
      .briefingEyebrow,.commodityEyebrow{{min-height:22px;padding:0 8px;font-size:10px}}
      .briefingHero h2{{font-size:26px;letter-spacing:-0.6px}}
      .briefingLead,.commodityLead{{margin-top:8px;font-size:13px;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
      .briefingHeroStats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;width:100%;justify-content:flex-start}}
      .briefingHeroStat{{min-width:0;min-height:0;padding:10px 10px 11px;border-radius:14px;box-shadow:none;border:1px solid #e2e8f0;background:#f8fafc}}
      .briefingHeroStatLabel{{font-size:10px}}
      .briefingHeroStat strong{{margin-top:4px;font-size:18px}}
      .briefingChipbar{{margin:12px 0 18px}}
      .commodityBoardNav{{margin:10px 0 16px}}
      .chipDock{{display:none}}
      .chipbar{{border:none;border-radius:0;background:transparent;box-shadow:none;overflow:visible}}
      .chipwrap{{padding:0}}
      .chips,.commodityGroupNav{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;justify-content:stretch;overflow:visible}}
      .chip,.commodityGroupChip{{width:100%;justify-content:space-between;min-height:48px;padding:0 14px;font-size:13px;border-radius:18px;box-shadow:0 10px 24px rgba(15,23,42,.10)}}
      .chipN,.commodityGroupChip span{{min-width:24px;height:24px;padding:0 7px}}
      .mobileQuickNav{{display:block;position:fixed;right:14px;bottom:18px;z-index:13}}
      .mobileQuickNavToggle{{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:0 14px;border:1px solid #0f172a;border-radius:999px;background:#0f172a;color:#fff;font-size:13px;font-weight:900;box-shadow:0 18px 38px rgba(15,23,42,.28)}}
      .commodityBoard{{margin-top:8px;border:none;border-radius:0;background:transparent;box-shadow:none}}
      .commodityHead{{grid-template-columns:1fr;padding:0;border-bottom:none;background:transparent;overflow:visible}}
      .commodityHead::after{{display:none}}
      .commodityHead h2{{font-size:26px;letter-spacing:-0.6px}}
      .commodityHeadStats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;width:100%;justify-content:flex-start}}
      .commodityHeadStat{{min-width:0;min-height:0;padding:10px 10px 11px;border-radius:14px;box-shadow:none;border:1px solid #e2e8f0;background:#f8fafc}}
      .commodityHeadStatLabel{{font-size:10px}}
      .commodityHeadStat strong{{margin-top:4px;font-size:18px}}
      .commodityGrid{{grid-template-columns:1fr}}
      .commodityGroupBlock{{margin:0 0 20px;padding:0;border:none;border-radius:0;background:transparent;box-shadow:none}}
      .commodityGroupHead{{display:block;padding:0 0 10px;border-bottom:none;margin-bottom:12px}}
      .commodityGroupMeta{{margin-top:6px}}
      .commodityTile{{padding:14px;border-radius:18px;box-shadow:0 12px 26px rgba(15,23,42,.08)}}
      .commodityInactive{{padding:0;border:none;background:transparent}}
      .commodityInactiveTitle{{margin-bottom:10px}}
      .sec{{margin-top:18px !important;border:none;border-radius:0 !important;overflow:visible;background:transparent}}
      .secHead{{padding:0 0 10px;background:transparent;border-bottom:none}}
      .secBody{{padding:0}}
      .card{{margin:0 0 12px;padding:14px;border-radius:18px;box-shadow:0 12px 26px rgba(15,23,42,.08)}}
      .commoditySupportStory,.commodityMoreStory{{width:100%}}
      .commoditySupportText{{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}}
      .commodityMiniGrid{{gap:6px}}
    }}
  </style>
</head>
<body>
  <div class=\"topbar\">
    <div class=\"topin\">
      <div>
        <h1>{esc(page_title)}{dev_badge_html}</h1>
        <div class=\"sub\">기간: {esc(period)} · 기사 {total}건{esc(dev_sub_text)}</div>
      </div>
      <div class=\"navRow\">
        <a class=\"navBtn navArchive\" data-nav=\"archive\" href=\"{esc(home_href)}\" title=\"날짜별 아카이브 목록\"{nav_target_attr}>{esc(home_label)}</a>
        {nav_btn(prev_href, "◀ 이전", "이전 브리핑이 없습니다.", "prev")}
        <div class=\"dateSelWrap\">
          <select id=\"dateSelect\" aria-label=\"날짜 선택\">
            {options_html}
          </select>
        </div>
        {nav_btn(next_href, "다음 ▶", "다음 브리핑이 없습니다.", "next")}
      </div>
      <div id=\"swipeHint\" class=\"swipeHint\" aria-hidden=\"true\">
        <span class=\"arrow\">◀</span>
        <span class=\"txt pill\">좌우 스와이프로 날짜 이동</span>
        <span class=\"arrow\">▶</span>
      </div>
      <div id=\"navLoading\" class=\"navLoading\" aria-live=\"polite\" aria-atomic=\"true\">
        <span class=\"badge\">날짜 이동 중…</span>
      </div>
    </div>
  </div>
  <div id=\"chipDock\" class=\"chipDock\" aria-hidden=\"true\">
    <div id=\"chipDockInner\" class=\"chipDockInner\"></div>
  </div>
  <div id=\"mobileQuickNav\" class=\"mobileQuickNav\" aria-hidden=\"true\">
    <button id=\"mobileQuickNavToggle\" class=\"mobileQuickNavToggle\" type=\"button\" data-swipe-ignore=\"1\">
      <span id=\"mobileQuickNavToggleLabel\">섹션 이동</span>
    </button>
  </div>
  <div id=\"mobileQuickNavSheet\" class=\"mobileQuickNavSheet\" aria-hidden=\"true\">
    <button id=\"mobileQuickNavBackdrop\" class=\"mobileQuickNavBackdrop\" type=\"button\" aria-label=\"빠른 이동 닫기\" data-swipe-ignore=\"1\"></button>
    <section class=\"mobileQuickNavPanel\" aria-labelledby=\"mobileQuickNavTitle\">
      <div class=\"mobileQuickNavHead\">
        <strong id=\"mobileQuickNavTitle\">섹션 바로가기</strong>
        <button id=\"mobileQuickNavClose\" class=\"mobileQuickNavClose\" type=\"button\" data-swipe-ignore=\"1\">닫기</button>
      </div>
      <div id=\"mobileQuickNavBody\" class=\"mobileQuickNavBody\"></div>
    </section>
  </div>

  <div class=\"wrap\">
    {view_tabs_html}
    <section id=\"view-briefing\" class=\"viewPane briefingPane isActive\" data-view-pane=\"briefing\" role=\"tabpanel\">
      {briefing_hero_html}
      {briefing_nav_html}
      {sections_html}
    </section>
    <section id=\"view-commodity\" class=\"viewPane commodityPane\" data-view-pane=\"commodity\" role=\"tabpanel\" aria-hidden=\"true\">
      {commodity_board_html}
    </section>
    <div class=\"footer\">* 자동 수집 결과입니다. 핵심 확인은 “원문 열기”로 원문을 확인하세요.</div>
    {dev_footer_html}
  </div>

  <script>
    (function() {{
{dev_refresh_js}
      var isDevPreviewPage = {json.dumps(is_dev_preview)};
      var devLoaderHref = {json.dumps(preview_href)};
      var devArchiveManifestUrl = {json.dumps(dev_archive_manifest_url)};
      var currentReportDate = {json.dumps(report_date)};
      var rootEl = document.documentElement;
      var topbarEl = document.querySelector(".topbar");
      var chipDockEl = document.getElementById("chipDock");
      var chipDockInnerEl = document.getElementById("chipDockInner");
      var mobileQuickNavEl = document.getElementById("mobileQuickNav");
      var mobileQuickNavToggleEl = document.getElementById("mobileQuickNavToggle");
      var mobileQuickNavToggleLabelEl = document.getElementById("mobileQuickNavToggleLabel");
      var mobileQuickNavSheetEl = document.getElementById("mobileQuickNavSheet");
      var mobileQuickNavBackdropEl = document.getElementById("mobileQuickNavBackdrop");
      var mobileQuickNavCloseEl = document.getElementById("mobileQuickNavClose");
      var mobileQuickNavBodyEl = document.getElementById("mobileQuickNavBody");
      var mobileQuickNavTitleEl = document.getElementById("mobileQuickNavTitle");
      function isCompactViewport() {{
        try {{
          return window.matchMedia("(max-width: 900px) and (hover: none), (max-width: 900px) and (pointer: coarse), (max-width: 640px)").matches;
        }} catch (e) {{}}
        var coarsePointer = false;
        try {{
          coarsePointer = !!(navigator && typeof navigator.maxTouchPoints === "number" && navigator.maxTouchPoints > 0);
        }} catch (e) {{}}
        return window.innerWidth <= (coarsePointer ? 900 : 640);
      }}
      function getActivePane() {{
        return document.querySelector('.viewPane.isActive[data-view-pane]');
      }}
      function getActiveChipbar() {{
        var pane = getActivePane();
        if (!pane) return null;
        return pane.querySelector('.chipbar[data-view-pane-anchor]');
      }}
      function getActiveQuickNavMeta(activeChipbar) {{
        var anchor = activeChipbar ? (activeChipbar.getAttribute("data-view-pane-anchor") || "") : "";
        if (anchor === "commodity") {{
          return {{
            toggle: "품목군 이동",
            title: "품목군 바로가기",
          }};
        }}
        return {{
          toggle: "섹션 이동",
          title: "섹션 바로가기",
        }};
      }}
      function closeMobileQuickNavSheet() {{
        if (mobileQuickNavSheetEl) {{
          mobileQuickNavSheetEl.classList.remove("isOpen");
          mobileQuickNavSheetEl.setAttribute("aria-hidden", "true");
        }}
        try {{
          document.body.classList.remove("quickNavOpen");
        }} catch (e) {{}}
      }}
      function openMobileQuickNavSheet() {{
        if (!mobileQuickNavSheetEl) return;
        mobileQuickNavSheetEl.classList.add("isOpen");
        mobileQuickNavSheetEl.setAttribute("aria-hidden", "false");
        try {{
          document.body.classList.add("quickNavOpen");
        }} catch (e) {{}}
      }}

      function syncStickyOffsets() {{
        if (!rootEl || !topbarEl) return;
        var topbarHeight = Math.ceil(topbarEl.getBoundingClientRect().height || topbarEl.offsetHeight || 0);
        if (!topbarHeight) return;
        var activeChipbar = getActiveChipbar();
        var compactViewport = isCompactViewport();
        var chipbarHeight = Math.ceil(activeChipbar && !compactViewport ? (activeChipbar.getBoundingClientRect().height || activeChipbar.offsetHeight || 0) : 0);
        rootEl.style.setProperty("--topbar-height", topbarHeight + "px");
        rootEl.style.setProperty("--chipbar-height", chipbarHeight + "px");
        rootEl.style.setProperty("--sticky-nav-offset", (topbarHeight + 12) + "px");
        rootEl.style.setProperty("--anchor-offset", (topbarHeight + (compactViewport ? 20 : chipbarHeight + 30)) + "px");
      }}

      function syncFloatingChipbar() {{
        if (!chipDockEl || !chipDockInnerEl || !topbarEl) return;
        if (isCompactViewport()) {{
          chipDockEl.classList.remove("isVisible");
          chipDockEl.setAttribute("aria-hidden", "true");
          chipDockEl.dataset.source = "";
          chipDockInnerEl.innerHTML = "";
          return;
        }}
        var activeChipbar = getActiveChipbar();
        if (!activeChipbar) {{
          chipDockEl.classList.remove("isVisible");
          chipDockEl.setAttribute("aria-hidden", "true");
          chipDockEl.dataset.source = "";
          chipDockInnerEl.innerHTML = "";
          return;
        }}
        var topbarHeight = Math.ceil(topbarEl.getBoundingClientRect().height || topbarEl.offsetHeight || 0);
        var dockTop = topbarHeight + 12;
        var chipbarHeight = Math.ceil(activeChipbar.getBoundingClientRect().height || activeChipbar.offsetHeight || 0);
        if (chipbarHeight) {{
          rootEl.style.setProperty("--chipbar-height", chipbarHeight + "px");
          rootEl.style.setProperty("--anchor-offset", (topbarHeight + chipbarHeight + 30) + "px");
        }}
        var sourceKey = [
          activeChipbar.getAttribute("data-view-pane-anchor") || "",
          activeChipbar.className || "",
          activeChipbar.querySelectorAll("a").length,
        ].join("|");
        if (chipDockEl.dataset.source !== sourceKey) {{
          chipDockInnerEl.innerHTML = activeChipbar.outerHTML;
          chipDockEl.dataset.source = sourceKey;
        }}
        var rect = activeChipbar.getBoundingClientRect();
        var shouldShow = rect.top < dockTop && rect.bottom <= dockTop;
        chipDockEl.classList.toggle("isVisible", shouldShow);
        chipDockEl.setAttribute("aria-hidden", shouldShow ? "false" : "true");
      }}
      function syncMobileQuickNav() {{
        if (!mobileQuickNavEl || !mobileQuickNavToggleEl || !mobileQuickNavSheetEl || !mobileQuickNavBodyEl) return;
        var mobileViewport = isCompactViewport();
        var activeChipbar = getActiveChipbar();
        if (!mobileViewport || !activeChipbar) {{
          mobileQuickNavEl.classList.remove("isVisible");
          mobileQuickNavEl.setAttribute("aria-hidden", "true");
          mobileQuickNavEl.dataset.source = "";
          mobileQuickNavBodyEl.innerHTML = "";
          closeMobileQuickNavSheet();
          return;
        }}
        var meta = getActiveQuickNavMeta(activeChipbar);
        if (mobileQuickNavToggleLabelEl) mobileQuickNavToggleLabelEl.textContent = meta.toggle;
        if (mobileQuickNavTitleEl) mobileQuickNavTitleEl.textContent = meta.title;
        var sourceKey = [
          activeChipbar.getAttribute("data-view-pane-anchor") || "",
          activeChipbar.className || "",
          activeChipbar.querySelectorAll("a").length,
        ].join("|");
        if (mobileQuickNavEl.dataset.source !== sourceKey) {{
          mobileQuickNavBodyEl.innerHTML = activeChipbar.outerHTML;
          mobileQuickNavEl.dataset.source = sourceKey;
        }}
        var topbarHeight = Math.ceil(topbarEl.getBoundingClientRect().height || topbarEl.offsetHeight || 0);
        var rect = activeChipbar.getBoundingClientRect();
        var shouldShow = rect.bottom <= (topbarHeight + 8);
        mobileQuickNavEl.classList.toggle("isVisible", shouldShow);
        mobileQuickNavEl.setAttribute("aria-hidden", shouldShow ? "false" : "true");
      }}

      syncStickyOffsets();
      syncFloatingChipbar();
      syncMobileQuickNav();
      window.addEventListener("load", syncStickyOffsets);
      window.addEventListener("load", syncFloatingChipbar);
      window.addEventListener("load", syncMobileQuickNav);
      window.addEventListener("resize", syncStickyOffsets);
      window.addEventListener("resize", syncFloatingChipbar);
      window.addEventListener("resize", syncMobileQuickNav);
      window.addEventListener("scroll", syncFloatingChipbar, {{ passive: true }});
      window.addEventListener("scroll", syncMobileQuickNav, {{ passive: true }});

      function currentPageHref() {{
        try {{
          if (window.top && window.top !== window) {{
            return String(window.top.location.href || "");
          }}
        }} catch (e) {{}}
        return String(window.location.href || "");
      }}

      function navigateToUrl(url) {{
        if (!url) return;
        try {{
          if (window.top && window.top !== window) {{
            window.top.location.href = url;
            return;
          }}
        }} catch (e) {{}}
        window.location.href = url;
      }}

      var sel = document.getElementById("dateSelect");
      if (sel) {{
        sel.setAttribute("data-swipe-ignore", "1");
        sel.addEventListener("change", function() {{
          var v = sel.value;
          if (v) {{
            var ld = document.getElementById("navLoading");
            if (ld) ld.classList.add("show");
            gotoUrlChecked(v, "해당 날짜의 브리핑이 없습니다.");
          }}
        }});
      }}

      // ✅ (3) prev/next가 없을 때 404로 이동하지 않도록 알림 처리
      var btns = document.querySelectorAll("button.navBtn[data-msg]");
      btns.forEach(function(b) {{
        b.setAttribute("data-swipe-ignore", "1");
        b.addEventListener("click", function() {{
          var msg = b.getAttribute("data-msg") || "이동할 페이지가 없습니다.";
          alert(msg);
        }});
      }});

      var viewTabs = Array.prototype.slice.call(document.querySelectorAll(".viewTab[data-view-tab]"));
      var viewPanes = Array.prototype.slice.call(document.querySelectorAll(".viewPane[data-view-pane]"));

      function activateView(viewKey, opts) {{
        opts = opts || {{}};
        viewPanes.forEach(function(pane) {{
          var active = pane.getAttribute("data-view-pane") === viewKey;
          pane.classList.toggle("isActive", active);
          pane.setAttribute("aria-hidden", active ? "false" : "true");
        }});
        viewTabs.forEach(function(tab) {{
          var active = tab.getAttribute("data-view-tab") === viewKey;
          tab.classList.toggle("isActive", active);
          tab.setAttribute("aria-selected", active ? "true" : "false");
        }});
        syncStickyOffsets();
        syncFloatingChipbar();
        syncMobileQuickNav();
        closeMobileQuickNavSheet();

        if (opts.skipHistory) return;
        try {{
          var url = new URL(window.location.href);
          if (viewKey === "commodity") {{
            url.searchParams.set("view", "commodity");
            if ((url.hash || "").indexOf("#sec-") === 0) {{
              url.hash = "";
            }}
          }} else {{
            url.searchParams.delete("view");
            if ((url.hash || "").indexOf("#commodity") === 0) {{
              url.hash = "";
            }}
          }}
          window.history.replaceState(null, "", url.toString());
        }} catch (e) {{}}
      }}

      function resolveInitialView() {{
        try {{
          var hash = (window.location.hash || "").replace(/^#/, "");
          if (hash === "commodity-board" || hash.indexOf("commodity-") === 0) return "commodity";
          if (hash.indexOf("sec-") === 0) return "briefing";
          var url = new URL(window.location.href);
          var view = (url.searchParams.get("view") || "").toLowerCase();
          if (view === "commodity" || view === "briefing") return view;
        }} catch (e) {{}}
        return "briefing";
      }}

      viewTabs.forEach(function(tab) {{
        tab.setAttribute("data-swipe-ignore", "1");
        tab.addEventListener("click", function() {{
          activateView(tab.getAttribute("data-view-tab") || "briefing");
        }});
      }});

      window.addEventListener("hashchange", function() {{
        activateView(resolveInitialView(), {{ skipHistory: true }});
      }});

      if (mobileQuickNavToggleEl) {{
        mobileQuickNavToggleEl.setAttribute("data-swipe-ignore", "1");
        mobileQuickNavToggleEl.addEventListener("click", function() {{
          if (mobileQuickNavSheetEl && mobileQuickNavSheetEl.classList.contains("isOpen")) {{
            closeMobileQuickNavSheet();
          }} else {{
            syncMobileQuickNav();
            openMobileQuickNavSheet();
          }}
        }});
      }}
      if (mobileQuickNavBackdropEl) {{
        mobileQuickNavBackdropEl.setAttribute("data-swipe-ignore", "1");
        mobileQuickNavBackdropEl.addEventListener("click", closeMobileQuickNavSheet);
      }}
      if (mobileQuickNavCloseEl) {{
        mobileQuickNavCloseEl.setAttribute("data-swipe-ignore", "1");
        mobileQuickNavCloseEl.addEventListener("click", closeMobileQuickNavSheet);
      }}
      if (mobileQuickNavBodyEl) {{
        mobileQuickNavBodyEl.addEventListener("click", function(ev) {{
          var target = ev.target;
          if (target && target.closest && target.closest("a")) {{
            closeMobileQuickNavSheet();
          }}
        }});
      }}
      document.addEventListener("keydown", function(ev) {{
        if ((ev.key || "") === "Escape") closeMobileQuickNavSheet();
      }});

      activateView(resolveInitialView(), {{ skipHistory: true }});

      // ✅ (4) 모바일 좌/우 스와이프로 이전/다음 날짜 이동 (기사 영역 우선 / topbar 제스처 차단)
      var navRow = document.querySelector(".navRow");
      var prevNav = navRow ? navRow.querySelector('[data-nav="prev"]') : null;
      var nextNav = navRow ? navRow.querySelector('[data-nav="next"]') : null;
      // fallback: old pages without data-nav
      if (navRow) {{
        if (!prevNav) {{
          Array.prototype.forEach.call(navRow.querySelectorAll(".navBtn,button.navBtn"), function(el) {{
            if (!prevNav && (el.textContent||"").indexOf("이전")>=0) prevNav = el;
          }});
        }}
        if (!nextNav) {{
          Array.prototype.forEach.call(navRow.querySelectorAll(".navBtn,button.navBtn"), function(el) {{
            if (!nextNav && (el.textContent||"").indexOf("다음")>=0) nextNav = el;
          }});
        }}
      }}
      var swipeHint = document.getElementById("swipeHint");
      var navLoading = document.getElementById("navLoading");
      var isNavigating = false;

      function _bindNavClick(el, delta, msg) {{
        if (!el || !el.addEventListener) return;
        try {{ el.setAttribute && el.setAttribute("data-swipe-ignore", "1"); }} catch (e) {{}}
        try {{
          el.addEventListener("click", function(ev) {{
            try {{ ev.preventDefault(); }} catch (e2) {{}}
            try {{ gotoByOffset(delta, msg); }} catch (e3) {{}}
          }});
        }} catch (e4) {{}}
      }}
      _bindNavClick(prevNav, +1, "이전 브리핑이 없습니다.");
      _bindNavClick(nextNav, -1, "다음 브리핑이 없습니다.");

      function hasHref(el) {{
        return !!(el && el.tagName && el.tagName.toLowerCase() === "a" && (el.getAttribute("href") || ""));
      }}

      function showNavLoading() {{
        if (navLoading) navLoading.classList.add("show");
        try {{ setTimeout(function(){{ hideNavLoading(); }}, 1500); }} catch(e) {{}}
      }}

      function hideNavLoading() {{
        if (navLoading) navLoading.classList.remove("show");
      }}

      function showNoBrief(el, fallbackMsg) {{
        var msg = fallbackMsg || "이동할 페이지가 없습니다.";
        try {{
          if (el && el.getAttribute) {{
            msg = el.getAttribute("data-msg") || el.getAttribute("title") || msg;
          }}
        }} catch (e) {{}}
        hideNavLoading();
        try {{ alert(msg); }} catch (e2) {{}}
      }}

      function isBlockedTarget(target) {{
        if (!target || !target.closest) return false;
        if (target.closest('[data-swipe-ignore="1"]')) return true;
        // 상단(topbar: 아카이브/이전/날짜/다음/섹션칩)에서의 제스처는 페이지 스와이프 금지
        if (target.closest(".topbar")) return true;
        if (target.closest("a[href],select,input,textarea,button,[contenteditable=\\"true\\"]")) return true;
        return false;
      }}

      function navigateBy(el) {{
        if (!el || isNavigating) return;
        if (el.tagName && el.tagName.toLowerCase() === "a") {{
          var href = el.getAttribute("href");
          if (href) {{
            isNavigating = true;
            showNavLoading();
            navigateToUrl(href);
            return;
          }}
        }}
        try {{
          el.click();
        }} catch (e) {{}}
      }}



// ✅ 404 방지: 실제 존재하는 아카이브 목록으로 드롭다운/이전/다음/스와이프를 재정렬한다.
var __manifestDates = null;
var __rootPrefix = null;

function _getRootPrefix() {{
  if (__rootPrefix) return __rootPrefix;
  try {{
    if (isDevPreviewPage && devLoaderHref) {{
      var devUrl = new URL(devLoaderHref, currentPageHref());
      __rootPrefix = devUrl.origin + devUrl.pathname.replace(/[^/]*$/, "");
      return __rootPrefix;
    }}
    var href = currentPageHref();
    var i = href.indexOf("/archive/");
    if (i >= 0) {{
      __rootPrefix = href.slice(0, i + 1);
      return __rootPrefix;
    }}
    // fallback: current directory
    var p = href.replace(/[#?].*$/, "");
    __rootPrefix = p.substring(0, p.lastIndexOf("/") + 1);
    return __rootPrefix;
  }} catch (e) {{
    return "/";
  }}
}}

function _dateToUrl(d) {{
  if (isDevPreviewPage) {{
    return devLoaderHref + "?date=" + encodeURIComponent(d);
  }}
  return _getRootPrefix() + "archive/" + d + ".html";
}}

function _extractDate(s) {{
  if (!s) return "";
  var str = String(s);
  var param = str.match(/[?&]date=(\\d{{4}}-\\d{{2}}-\\d{{2}})(?:[&#]|$)/);
  if (param && param[1]) return param[1];
  var m = str.match(/(\\d{{4}}-\\d{{2}}-\\d{{2}})\\.html/);
  if (m && m[1]) return m[1];
  if (/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(str)) return str;
  return "";
}}

function _currentDateIso() {{
  return _extractDate(currentPageHref()) || currentReportDate;
}}

function _getDatesFromSelect() {{
  var sel = document.getElementById("dateSelect");
  if (!sel) return [];
  var ds = [];
  for (var i = 0; i < sel.options.length; i++) {{
    var opt = sel.options[i];
    var v = (opt && opt.value) ? opt.value : "";
    var d = _extractDate(v) || _extractDate((opt && opt.textContent) ? opt.textContent : "");
    if (d) ds.push(d);
  }}
  ds = Array.from(new Set(ds));
  ds.sort(); ds.reverse();
  return ds;
}}

function _setSelectDates(dates) {{
  var sel = document.getElementById("dateSelect");
  if (!sel) return;
  var cur = _currentDateIso();
  try {{ sel.innerHTML = ""; }} catch (e) {{}}
  for (var i = 0; i < dates.length; i++) {{
    var d = dates[i];
    var opt = document.createElement("option");
    opt.value = _dateToUrl(d);
    opt.textContent = d;
    if (d === cur) opt.selected = true;
    sel.appendChild(opt);
  }}
}}

async function _fetchManifestDates() {{
  try {{
    var url = isDevPreviewPage ? devArchiveManifestUrl : (_getRootPrefix() + "archive_manifest.json");
    var r = await fetch(url, {{ cache: "no-store" }});
    if (!r || !r.ok) return null;
    var obj = await r.json();
    var dates = (obj && obj.dates) ? obj.dates : null;
    if (!dates || !Array.isArray(dates)) return null;
    var clean = [];
    for (var i = 0; i < dates.length; i++) {{
      var d = dates[i];
      if (typeof d === "string" && /^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(d)) clean.push(d);
    }}
    clean = Array.from(new Set(clean));
    clean.sort(); clean.reverse();
    return clean;
  }} catch (e) {{
    return null;
  }}
}}

async function _ensureDates() {{
  if (__manifestDates && __manifestDates.length) return __manifestDates;
  var dates = await _fetchManifestDates();
  if (dates && dates.length) {{
    __manifestDates = dates;
    _setSelectDates(dates);
    return __manifestDates;
  }}
  __manifestDates = _getDatesFromSelect();
  return __manifestDates;
}}

async function _urlExists(url) {{
  try {{
    var r = await fetch(url, {{ method: "HEAD", cache: "no-store" }});
    if (r && r.ok) return true;
  }} catch (e) {{}}
  try {{
    var r2 = await fetch(url, {{ method: "GET", cache: "no-store" }});
    return !!(r2 && r2.ok);
  }} catch (e2) {{}}
  return false;
}}

async function gotoUrlChecked(url, msg) {{
  if (!url || isNavigating) return;
  var dates = await _ensureDates();
  var d = _extractDate(url);
  if (d) url = _dateToUrl(d);

  // If manifest/derived list exists and date is not in it, block early
  if (d && dates && dates.length && dates.indexOf(d) < 0) {{
    showNoBrief(null, msg || "해당 날짜의 브리핑이 없습니다.");
    return;
  }}

  if (isDevPreviewPage) {{
    isNavigating = true;
    showNavLoading();
    navigateToUrl(url);
    return;
  }}

  var ok = await _urlExists(url);
  if (ok) {{
    isNavigating = true;
    showNavLoading();
    navigateToUrl(url);
    return;
  }}
  showNoBrief(null, msg || "해당 날짜의 브리핑이 없습니다.");
  // restore selection
  try {{
    var sel = document.getElementById("dateSelect");
    if (sel) {{
      var cur = _currentDateIso();
      for (var i = 0; i < sel.options.length; i++) {{
        var dd = _extractDate(sel.options[i].value) || _extractDate(sel.options[i].textContent || "");
        if (dd && dd === cur) sel.selectedIndex = i;
      }}
    }}
  }} catch (e) {{}}
}}

async function gotoByOffset(delta, msg) {{
  var dates = await _ensureDates();
  if (!dates || !dates.length) {{ showNoBrief(null, msg || "이동할 브리핑이 없습니다."); return; }}
  var cur = _currentDateIso();
  var idx = dates.indexOf(cur);
  if (idx < 0) idx = 0;
  var step = (delta >= 0) ? 1 : -1;
  var j = idx + delta;
  while (j >= 0 && j < dates.length) {{
    var d = dates[j];
    var url = _dateToUrl(d);
    if (isDevPreviewPage) {{
      if (isNavigating) return;
      isNavigating = true;
      showNavLoading();
      navigateToUrl(url);
      return;
    }}
    // Always verify existence (manifest can be stale; Pages deploy can lag)
    var ok = await _urlExists(url);
    if (ok) {{
      if (isNavigating) return;
      isNavigating = true;
      showNavLoading();
      navigateToUrl(url);
      return;
    }}
    j += step;
  }}
  showNoBrief(null, msg || (delta > 0 ? "이전 브리핑이 없습니다." : "다음 브리핑이 없습니다."));
}}

// non-blocking: try to load manifest & prune date list
try {{ _ensureDates(); }} catch (e) {{}}

      function resetNavRowFeedback() {{
        if (!navRow) return;
        navRow.style.transform = "";
        navRow.style.opacity = "";
      }}

      var sx = 0, sy = 0, st = 0, blocked = false;
      var swipeActive = false;
      var swipeSuppressSelection = false;
      var swipeTarget = null;
      var swipePointerId = null;
      var swipeRootUserSelect = "";
      var swipeRootWebkitUserSelect = "";
      var swipeBodyCursor = "";
      var wheelSwipeDx = 0;
      var wheelSwipeDy = 0;
      var wheelSwipeAt = 0;
      var wheelSwipeLockUntil = 0;
      var swipeArea = document.querySelector(".wrap") || document.documentElement || document.body || document;

      function getSwipePoint(e, phase) {{
        try {{
          if (!e) return null;
          if (phase !== "end" && e.touches && e.touches.length === 1) {{
            return {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
          }}
          if (phase === "end" && e.changedTouches && e.changedTouches.length === 1) {{
            return {{ x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY }};
          }}
          if (typeof e.clientX === "number" && typeof e.clientY === "number") {{
            return {{ x: e.clientX, y: e.clientY }};
          }}
        }} catch (_evtErr) {{}}
        return null;
      }}

      function resetSwipeState() {{
        try {{
          if (swipeArea && swipeArea.releasePointerCapture && swipePointerId !== null) {{
            swipeArea.releasePointerCapture(swipePointerId);
          }}
        }} catch (_releaseErr) {{}}
        setDesktopSwipeMode(false);
        swipeActive = false;
        blocked = false;
        swipeTarget = null;
        swipePointerId = null;
      }}

      function setDesktopSwipeMode(active) {{
        var root = document.documentElement;
        try {{
          if (active) {{
            if (swipeSuppressSelection) return;
            swipeSuppressSelection = true;
            swipeRootUserSelect = (root && root.style) ? (root.style.userSelect || "") : "";
            swipeRootWebkitUserSelect = (root && root.style) ? (root.style.webkitUserSelect || "") : "";
            swipeBodyCursor = (document.body && document.body.style) ? (document.body.style.cursor || "") : "";
            if (root && root.style) {{
              root.style.userSelect = "none";
              root.style.webkitUserSelect = "none";
            }}
            if (document.body && document.body.style) {{
              document.body.style.cursor = "grabbing";
            }}
            return;
          }}
          if (!swipeSuppressSelection) return;
          swipeSuppressSelection = false;
          if (root && root.style) {{
            root.style.userSelect = swipeRootUserSelect;
            root.style.webkitUserSelect = swipeRootWebkitUserSelect;
          }}
          if (document.body && document.body.style) {{
            document.body.style.cursor = swipeBodyCursor;
          }}
        }} catch (_desktopSwipeErr) {{}}
      }}

      function resetWheelSwipe() {{
        wheelSwipeDx = 0;
        wheelSwipeDy = 0;
        wheelSwipeAt = 0;
      }}

      function handleWheelSwipe(e) {{
        if (!e || isNavigating) return;
        if (e.ctrlKey) return;
        if (isBlockedTarget(e.target)) return;
        var now = Date.now();
        if (wheelSwipeLockUntil && now < wheelSwipeLockUntil) return;
        if (!wheelSwipeAt || (now - wheelSwipeAt) > 240) {{
          resetWheelSwipe();
        }}
        wheelSwipeAt = now;
        wheelSwipeDx += Number(e.deltaX || 0);
        wheelSwipeDy += Number(e.deltaY || 0);
        if (Math.abs(wheelSwipeDx) < 120) return;
        if (Math.abs(wheelSwipeDx) < Math.abs(wheelSwipeDy) * 1.25) return;
        wheelSwipeLockUntil = now + 700;
        try {{
          if (e.cancelable && e.preventDefault) e.preventDefault();
        }} catch (_wheelPreventErr) {{}}
        var totalDx = wheelSwipeDx;
        resetWheelSwipe();
        if (totalDx > 0) {{
          gotoByOffset(-1, "\ub2e4\uc74c \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.");
        }} else {{
          gotoByOffset(+1, "\uc774\uc804 \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.");
        }}
      }}

      function beginSwipe(e) {{
        if (!swipeArea) return;
        if (e && e.pointerType === "mouse" && typeof e.button === "number" && e.button !== 0) return;
        if (e && !e.pointerType && typeof e.button === "number" && e.button !== 0) return;
        var point = getSwipePoint(e, "start");
        if (!point) return;
        blocked = isBlockedTarget(e ? e.target : null);
        if (blocked) {{
          swipeActive = false;
          swipeTarget = null;
          swipePointerId = null;
          return;
        }}
        if (e && (e.pointerType === "mouse" || (!e.pointerType && !e.touches))) {{
          setDesktopSwipeMode(true);
        }}
        swipeActive = true;
        swipeTarget = e ? (e.target || null) : null;
        swipePointerId = (e && typeof e.pointerId === "number") ? e.pointerId : null;
        sx = point.x;
        sy = point.y;
        st = Date.now();
        try {{
          if (swipeArea.setPointerCapture && swipePointerId !== null) {{
            swipeArea.setPointerCapture(swipePointerId);
          }}
        }} catch (_captureErr) {{}}
      }}

      function endSwipe(e) {{
        if (!swipeActive) return;
        if (swipePointerId !== null && e && typeof e.pointerId === "number" && e.pointerId !== swipePointerId) return;
        var point = getSwipePoint(e, "end");
        var startedBlocked = blocked;
        var startedDesktopSwipe = swipeSuppressSelection;
        var startedTarget = swipeTarget;
        resetSwipeState();
        if (!point) return;
        if (startedBlocked || isBlockedTarget(e ? e.target : null) || isBlockedTarget(startedTarget)) return;
        try {{
          var selection = window.getSelection ? window.getSelection() : null;
          var selected = selection ? String(selection) : "";
          if (startedDesktopSwipe && selection && selection.removeAllRanges) {{
            selection.removeAllRanges();
            selected = "";
          }}
          if (selected && selected.trim()) return;
        }} catch (_selectionErr) {{}}
        var dx = point.x - sx;
        var dy = point.y - sy;
        var dt = Date.now() - st;
        if (dt > 900 || Math.abs(dx) < 90 || Math.abs(dx) < Math.abs(dy) * 1.4) return;
        if (dx < 0) {{
          gotoByOffset(-1, "\ub2e4\uc74c \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.");
        }} else {{
          gotoByOffset(+1, "\uc774\uc804 \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.");
        }}
      }}

      if (window.PointerEvent) {{
        swipeArea.addEventListener("pointerdown", function(e) {{
          beginSwipe(e);
        }}, {{ passive: true }});
        window.addEventListener("pointerup", function(e) {{
          endSwipe(e);
        }}, {{ passive: true }});
        window.addEventListener("pointercancel", function() {{
          resetSwipeState();
        }}, {{ passive: true }});
      }}

      swipeArea.addEventListener("touchstart", function(e) {{
        if (window.PointerEvent) return;
        beginSwipe(e);
      }}, {{ passive: true }});

      swipeArea.addEventListener("touchend", function(e) {{
        if (window.PointerEvent) return;
        endSwipe(e);
      }}, {{ passive: true }});

      swipeArea.addEventListener("mousedown", function(e) {{
        if (window.PointerEvent) return;
        beginSwipe(e);
      }});

      window.addEventListener("mouseup", function(e) {{
        if (window.PointerEvent) return;
        endSwipe(e);
      }});

      swipeArea.addEventListener("dragstart", function(e) {{
        if (!swipeActive && !swipeSuppressSelection) return;
        try {{
          if (e && e.preventDefault) e.preventDefault();
        }} catch (_dragErr) {{}}
      }});

      swipeArea.addEventListener("wheel", function(e) {{
        handleWheelSwipe(e);
      }}, {{ passive: false }});

      window.addEventListener("blur", function() {{
        resetSwipeState();
        resetWheelSwipe();
      }});

      document.addEventListener("keydown", function(e) {{
        if (!e) return;
        if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
        if (isBlockedTarget(e.target)) return;
        if (e.key === "ArrowLeft") {{
          if (hasHref(prevNav)) {{
            showNavLoading();
            navigateBy(prevNav);
          }} else {{
            showNoBrief(prevNav, "이전 브리핑이 없습니다.");
          }}
        }} else if (e.key === "ArrowRight") {{
          if (hasHref(nextNav)) {{
            showNavLoading();
            navigateBy(nextNav);
          }} else {{
            showNoBrief(nextNav, "다음 브리핑이 없습니다.");
          }}
        }}
      }});

      window.addEventListener("pageshow", function() {{
        isNavigating = false;
        hideNavLoading();
        resetNavRowFeedback();
      }});

      // 힌트는 1번만 잠깐 노출(가독성 유지)
      (function maybeShowSwipeHint() {{
        if (!swipeHint) return;
        try {{
          var k = "agri_swipe_hint_shown";
          if (window.sessionStorage && sessionStorage.getItem(k) === "1") {{
            swipeHint.style.display = "none";
            return;
          }}
          swipeHint.style.display = "flex";
          if (window.sessionStorage) sessionStorage.setItem(k, "1");
          window.setTimeout(function() {{
            swipeHint.style.display = "none";
          }}, 1200);
        }} catch (e) {{}}
      }})();
}})();
  </script>
  <!-- build: {BUILD_TAG} -->
{debug_html}
</body>
</html>
"""


def render_index_page(manifest: JsonDict, site_path: str) -> str:
    manifest = _normalize_manifest(manifest)

    def is_valid_iso_date(s: str) -> bool:
        s = (s or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return False
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except Exception:
            return False

    def pretty_date_kr(iso_date: str) -> str:
        try:
            d = datetime.strptime(iso_date, "%Y-%m-%d").date()
            return f"{d.year}년 {d.month}월 {d.day}일"
        except Exception:
            return iso_date

    raw_dates = manifest.get("dates", [])
    dates = [d for d in raw_dates if isinstance(d, str) and is_valid_iso_date(d)]
    dates = sorted(set(dates), reverse=True)

    latest = dates[0] if dates else None
    latest_link = build_site_url(site_path, f"archive/{latest}.html") if latest else None

    cards = []
    for d in dates[:90]:
        href = build_site_url(site_path, f"archive/{d}.html")
        wd = weekday_label(d)
        cards.append(f"""
          <a class="card" href="{esc(href)}">
            <div class="dt">{esc(pretty_date_kr(d))}</div>
            <div class="meta">{esc(d)} · {esc(wd)}요일</div>
          </a>
        """)

    cards_html = "\n".join(cards) if cards else '<div class="empty">아카이브가 아직 없습니다.</div>'

    latest_btn_html = (
        f'<a class="btn" href="{esc(latest_link)}">최신 브리핑 열기</a>'
        if latest_link
        else '<button class="btn disabled" type="button" data-msg="최신 브리핑이 아직 없습니다.">최신 브리핑 열기</button>'
    )

    search_json_url = build_site_url(site_path, "search_index.json")

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <meta name="agri-build" content="{BUILD_TAG}" />
  <title>농산물 뉴스 브리핑</title>
  <style>
    :root {{
      --bg:#ffffff;
      --text:#111827;
      --muted:#6b7280;
      --line:#e5e7eb;
      --btn:#1d4ed8;
      --btnHover:#1e40af;
      --chip:#f3f4f6;
      --mark:#fef08a;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;background:var(--bg);color:var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Noto Sans KR", Arial;}}
    .wrap{{max-width:1040px;margin:0 auto;padding:26px 16px 70px}}
    h1{{margin:0;font-size:22px;letter-spacing:-0.2px}}
    .sub{{color:var(--muted);margin-top:8px;font-size:13px;line-height:1.5}}
    .btn{{display:inline-flex;align-items:center;justify-content:center;margin-top:14px;text-decoration:none;color:#fff;
         border:1px solid var(--btn);padding:10px 14px;border-radius:12px;background:var(--btn);font-weight:900; cursor:pointer; user-select:none}}
    .btn:hover{{background:var(--btnHover);border-color:var(--btnHover)}}
    .btn.disabled{{opacity:.5; cursor:pointer}}
    .btn.ghost{{background:#fff;color:var(--btn);border-color:var(--line)}}
    .btn.ghost:hover{{border-color:#cbd5e1;background:#f8fafc}}

    .panel{{margin-top:18px;border:1px solid var(--line);border-radius:16px;background:#fff;padding:14px}}
    .panelTitle{{font-weight:900;margin-bottom:10px;display:flex;gap:10px;align-items:center;justify-content:space-between}}
    .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
    @media (max-width: 820px) {{ .grid{{grid-template-columns:repeat(2,1fr);}} }}
    @media (max-width: 520px) {{ .grid{{grid-template-columns:1fr;}} }}

    .card{{display:block;text-decoration:none;border:1px solid var(--line);border-radius:14px;padding:12px;
          background:#ffffff;color:var(--text)}}
    .card:hover{{border-color:#cbd5e1}}
    .dt{{font-size:15px;font-weight:900}}
    .meta{{margin-top:6px;color:var(--muted);font-size:12px}}
    .empty{{color:var(--muted);font-size:13px}}

    /* search */
    .searchRow{{display:flex;gap:10px;align-items:center}}
    .searchInput{{flex:1;border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:14px}}
    .searchInput:focus{{outline:none;border-color:#93c5fd;box-shadow:0 0 0 3px rgba(59,130,246,.12)}}

    .filters{{margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
    .sel,.date{{border:1px solid var(--line);border-radius:12px;padding:8px 10px;font-size:13px;background:#fff}}
    .sel:focus,.date:focus{{outline:none;border-color:#93c5fd;box-shadow:0 0 0 3px rgba(59,130,246,.12)}}
    .chip{{display:inline-flex;align-items:center;gap:6px;background:var(--chip);border:1px solid var(--line);
          padding:3px 8px;border-radius:999px;font-size:11px;color:#374151}}
    .chip b{{font-weight:900}}
    .hint{{margin-top:8px;color:var(--muted);font-size:12px;line-height:1.4}}
    .metaLine{{margin-top:10px;color:var(--muted);font-size:12px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}}
    .metaLeft{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}

    mark{{background:var(--mark);padding:0 2px;border-radius:4px}}

    .results{{margin-top:10px;display:flex;flex-direction:column;gap:10px}}
    .result{{border:1px solid var(--line);border-radius:14px;padding:12px;background:#fff}}
    .rTop{{display:flex;flex-wrap:wrap;gap:6px;align-items:center}}
    .rTitle{{margin-top:6px;font-weight:900;font-size:14px;line-height:1.35}}
    .rSum{{margin-top:6px;color:#374151;font-size:13px;line-height:1.45}}
    .rLinks{{margin-top:9px;display:flex;gap:12px;font-size:12px}}
    .rLinks a{{color:var(--btn);text-decoration:none;font-weight:900}}
    .rLinks a:hover{{text-decoration:underline}}

    .pager{{margin-top:10px;display:flex;gap:8px;align-items:center;justify-content:flex-end;flex-wrap:wrap}}
    .pager .pbtn{{padding:8px 10px;border-radius:12px;border:1px solid var(--line);background:#fff;cursor:pointer;font-weight:900;color:#111827}}
    .pager .pbtn:hover{{border-color:#cbd5e1;background:#f8fafc}}
    .pager .pbtn[disabled]{{opacity:.5;cursor:not-allowed}}
    .pager .pinfo{{color:var(--muted);font-size:12px;margin-right:auto}}

    .groupHdr{{margin-top:8px;font-weight:900;font-size:13px;color:#111827}}
    .groupWrap{{display:flex;flex-direction:column;gap:10px}}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>농산물 뉴스 브리핑</h1>
    <div class="sub">최신 브리핑과 날짜별 아카이브를 제공합니다. (키워드 검색 · 기간/섹션 필터 · 정렬 지원)</div>

    {latest_btn_html}

    <div class="panel">
      <div class="panelTitle">
        <span>키워드 검색</span>
        <span style="color:var(--muted);font-size:12px;font-weight:700">* 2글자 이상부터 결과 표시</span>
      </div>

      <div class="searchRow">
        <input id="q" class="searchInput" type="search" placeholder="예: 사과 가격, 샤인머스캣 수급, 생육 리스크 방제" />
        <button id="clearBtn" class="btn" style="margin-top:0;padding:10px 12px;" type="button">초기화</button>
      </div>

      <div class="filters">
        <select id="secSel" class="sel" title="섹션">
          <option value="">전체 섹션</option>
        </select>

        <select id="sortSel" class="sel" title="정렬">
          <option value="relevance">관련도순</option>
          <option value="date">최신순</option>
          <option value="press">매체 중요도순</option>
          <option value="score">선정 점수순</option>
        </select>

        <span class="chip"><b>기간</b></span>
        <input id="fromDate" class="date" type="date" />
        <span style="color:var(--muted);font-size:12px;">~</span>
        <input id="toDate" class="date" type="date" />

        <button id="quick7" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">7일</button>
        <button id="quick30" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">30일</button>
        <button id="quick90" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">90일</button>
        <button id="quickAll" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">전체</button>

        <label class="chip" style="cursor:pointer">
          <input id="groupToggle" type="checkbox" style="margin:0" />
          날짜별 그룹
        </label>
      </div>

      <div class="hint">검색 대상: 제목/요약/언론사/섹션/날짜.  (예: "사과 가격" 처럼 띄어쓰기를 하면 모든 단어가 포함된 기사만 표시됩니다.)</div>

      <div class="metaLine">
        <div id="metaLeft" class="metaLeft"></div>
        <div id="metaRight" style="color:var(--muted)"></div>
      </div>

      <div id="results" class="results"></div>
      <div id="pager" class="pager" style="display:none"></div>
    </div>

    <div class="panel">
      <div class="panelTitle">날짜별 아카이브</div>
      <div class="grid">
        {cards_html}
      </div>
    </div>
  </div>

  <script>
    (function() {{
      // disabled latest button -> alert
      var b = document.querySelector("button.btn.disabled[data-msg]");
      if (b) {{
        b.addEventListener("click", function() {{
          alert(b.getAttribute("data-msg") || "이동할 페이지가 없습니다.");
        }});
      }}

      var input = document.getElementById("q");
      var clearBtn = document.getElementById("clearBtn");
      var secSel = document.getElementById("secSel");
      var sortSel = document.getElementById("sortSel");
      var fromDate = document.getElementById("fromDate");
      var toDate = document.getElementById("toDate");
      var quick7 = document.getElementById("quick7");
      var quick30 = document.getElementById("quick30");
      var quick90 = document.getElementById("quick90");
      var quickAll = document.getElementById("quickAll");
      var groupToggle = document.getElementById("groupToggle");

      var metaLeft = document.getElementById("metaLeft");
      var metaRight = document.getElementById("metaRight");
      var box = document.getElementById("results");
      var pager = document.getElementById("pager");

      var DATA = null;
      var LOADING = false;

      var PAGE_SIZE = 20;
      var PAGE = 1;

      function escHtml(s) {{
        return (s || "").replace(/[&<>"']/g, function(c) {{
          return ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}})[c] || c;
        }});
      }}
      function norm(s) {{ return (s || "").toLowerCase(); }}

      function escapeRegExp(s) {{
        return (s || "").replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&");
      }}

      function highlight(text, tokens) {{
        var out = escHtml(text || "");
        for (var i=0; i<tokens.length; i++) {{
          var t = tokens[i];
          if (!t || t.length < 2) continue;
          try {{
            var re = new RegExp(escapeRegExp(t), "gi");
            out = out.replace(re, function(m) {{ return "<mark>" + m + "</mark>"; }});
          }} catch(e) {{}}
        }}
        return out;
      }}

      function debounce(fn, ms) {{
        var t = null;
        return function() {{
          var args = arguments;
          clearTimeout(t);
          t = setTimeout(function() {{ fn.apply(null, args); }}, ms);
        }}
      }}

      function ymdToInt(s) {{
        if (!s) return 0;
        return parseInt(String(s).replaceAll("-", ""), 10) || 0;
      }}

      function setQuickRange(days) {{
        if (!DATA) return;
        var maxD = DATA.max_date || "";
        if (!maxD) return;
        var maxI = ymdToInt(maxD);
        var yyyy = parseInt(maxD.slice(0,4),10);
        var mm = parseInt(maxD.slice(5,7),10);
        var dd = parseInt(maxD.slice(8,10),10);
        var dt = new Date(Date.UTC(yyyy, mm-1, dd));
        if (days === null) {{
          fromDate.value = DATA.min_date || "";
          toDate.value = DATA.max_date || "";
          return;
        }}
        var from = new Date(dt.getTime() - (days-1) * 24*3600*1000);
        var fy = from.getUTCFullYear();
        var fm = String(from.getUTCMonth()+1).padStart(2,"0");
        var fd = String(from.getUTCDate()).padStart(2,"0");
        fromDate.value = fy + "-" + fm + "-" + fd;
        toDate.value = DATA.max_date || "";
      }}

      function setMeta(tokens, resCount, showCount) {{
        metaLeft.innerHTML = "";
        var q = (input.value || "").trim();
        if (!q || q.length < 2) {{
          metaRight.textContent = "";
          return;
        }}
        // chips
        metaLeft.innerHTML += "<span class='chip'><b>검색</b> " + escHtml(q) + "</span>";
        var secV = secSel.value || "";
        if (secV) metaLeft.innerHTML += "<span class='chip'><b>섹션</b> " + escHtml(secSel.options[secSel.selectedIndex].text) + "</span>";
        var fr = fromDate.value || "";
        var to = toDate.value || "";
        if (fr || to) metaLeft.innerHTML += "<span class='chip'><b>기간</b> " + escHtml(fr||"…") + " ~ " + escHtml(to||"…") + "</span>";
        metaLeft.innerHTML += "<span class='chip'><b>정렬</b> " + escHtml(sortSel.options[sortSel.selectedIndex].text) + "</span>";

        metaRight.textContent = "총 " + resCount + "건 · " + showCount + "건 표시";
      }}

      function computeRelevance(it, tokens) {{
        var t = norm(it.title || "");
        var s = norm(it.summary || "");
        var p = norm(it.press || "");
        var sec = norm(it.section_title || it.section || "");
        var base = 0;

        // token match (AND)
        var match = 0;
        for (var i=0; i<tokens.length; i++) {{
          var tok = tokens[i];
          if (!tok) continue;
          var inTitle = t.indexOf(tok) !== -1;
          var inSum = s.indexOf(tok) !== -1;
          var inMeta = p.indexOf(tok) !== -1 || sec.indexOf(tok) !== -1;
          if (inTitle || inSum || inMeta) match += 1;
          if (inTitle) base += 70;
          else if (inSum) base += 40;
          else if (inMeta) base += 15;
        }}

        // press tier / score
        var pt = parseInt(it.press_tier || 0, 10) || 0;
        var sc = parseFloat(it.score || 0) || 0;
        base += pt * 18;
        base += Math.min(30, sc); // score cap
        base += match * 10;
        return base;
      }}

      function filterItems(tokens) {{
        var items = (DATA && DATA.items) ? DATA.items : [];
        var res = [];

        var q = (input.value || "").trim();
        if (!q || q.length < 2) return res;

        // AND search
        for (var i=0; i<items.length; i++) {{
          var it = items[i] || {{}};
          var hay = norm((it.title||"") + " " + (it.summary||"") + " " + (it.press||"") + " " + (it.section_title||"") + " " + (it.date||""));
          var ok = true;
          for (var j=0; j<tokens.length; j++) {{
            if (hay.indexOf(tokens[j]) === -1) {{ ok = false; break; }}
          }}
          if (!ok) continue;

          // section
          var secV = secSel.value || "";
          if (secV && String(it.section||"") !== secV) continue;

          // date range
          var di = ymdToInt(it.date || "");
          var fr = ymdToInt(fromDate.value || "");
          var to = ymdToInt(toDate.value || "");
          if (fr && di < fr) continue;
          if (to && di > to) continue;

          // precompute relevance
          it._rel = computeRelevance(it, tokens);
          res.push(it);
        }}
        return res;
      }}

      function sortItems(list) {{
        var mode = sortSel.value || "relevance";
        list.sort(function(a,b) {{
          var da = ymdToInt(a.date||"");
          var db = ymdToInt(b.date||"");
          var pa = parseInt(a.press_tier||0,10)||0;
          var pb = parseInt(b.press_tier||0,10)||0;
          var sa = parseFloat(a.score||0)||0;
          var sb = parseFloat(b.score||0)||0;
          var ra = parseFloat(a._rel||0)||0;
          var rb = parseFloat(b._rel||0)||0;

          if (mode === "date") {{
            if (db !== da) return db - da;
            if (pb !== pa) return pb - pa;
            return sb - sa;
          }}
          if (mode === "press") {{
            if (pb !== pa) return pb - pa;
            if (db !== da) return db - da;
            return rb - ra;
          }}
          if (mode === "score") {{
            if (sb !== sa) return sb - sa;
            if (pb !== pa) return pb - pa;
            return db - da;
          }}
          // relevance
          if (rb !== ra) return rb - ra;
          if (pb !== pa) return pb - pa;
          return db - da;
        }});
      }}

      function renderPager(total) {{
        var totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        if (total <= PAGE_SIZE) {{
          pager.style.display = "none";
          pager.innerHTML = "";
          return;
        }}
        pager.style.display = "flex";
        var prevDis = (PAGE <= 1) ? "disabled" : "";
        var nextDis = (PAGE >= totalPages) ? "disabled" : "";

        pager.innerHTML = ""
          + "<div class='pinfo'>페이지 " + PAGE + " / " + totalPages + "</div>"
          + "<button class='pbtn' id='prevBtn' " + prevDis + ">이전</button>"
          + "<button class='pbtn' id='nextBtn' " + nextDis + ">다음</button>";

        var prevBtn = document.getElementById("prevBtn");
        var nextBtn = document.getElementById("nextBtn");
        if (prevBtn) prevBtn.addEventListener("click", function(){{ if (PAGE>1) {{ PAGE--; runSearch(); }} }});
        if (nextBtn) nextBtn.addEventListener("click", function(){{ if (PAGE<totalPages) {{ PAGE++; runSearch(); }} }});
      }}

      function renderList(res, tokens) {{
        var start = (PAGE - 1) * PAGE_SIZE;
        var slice = res.slice(start, start + PAGE_SIZE);

        if (slice.length === 0) {{
          box.innerHTML = "<div class='empty'>검색 결과가 없습니다.</div>";
          renderPager(0);
          setMeta(tokens, res.length, 0);
          return;
        }}

        var html = "";
        for (var k=0; k<slice.length; k++) {{
          var r = slice[k];
          var date = escHtml(r.date || "");
          var sec = escHtml(r.section_title || r.section || "");
          var press = escHtml(r.press || "");
          var title = highlight(r.title || "", tokens);
          var sum = highlight(r.summary || "", tokens);

          var aHref = r.archive || "";
          var uHref = r.url || "";

          var tier = parseInt(r.press_tier||0,10)||0;
          var tierLabel = tier>=4 ? "공식" : (tier>=3 ? "주요" : (tier>=2 ? "지역/전문" : "기타"));
          html += "<div class='result'>"
               +  "<div class='rTop'>"
               +    "<span class='chip'>" + date + "</span>"
               +    "<span class='chip'>" + sec + "</span>"
               +    (press ? "<span class='chip'>" + press + "</span>" : "")
               +    "<span class='chip'><b>" + tierLabel + "</b></span>"
               +  "</div>"
               +  "<div class='rTitle'>" + title + "</div>"
               +  (sum ? "<div class='rSum'>" + sum + "</div>" : "")
               +  "<div class='rLinks'>"
               +    (aHref ? "<a href='" + aHref + "'>브리핑 보기</a>" : "")
               +    (uHref ? "<a href='" + uHref + "' target='_blank' rel='noopener'>원문 열기</a>" : "")
               +  "</div>"
               + "</div>";
        }}
        box.innerHTML = html;
        renderPager(res.length);
        setMeta(tokens, res.length, slice.length);
      }}

      function renderGrouped(res, tokens) {{
        var start = (PAGE - 1) * PAGE_SIZE;
        var slice = res.slice(start, start + PAGE_SIZE);
        if (slice.length === 0) {{
          box.innerHTML = "<div class='empty'>검색 결과가 없습니다.</div>";
          renderPager(0);
          setMeta(tokens, res.length, 0);
          return;
        }}
        var groups = {{}};
        for (var i=0;i<slice.length;i++) {{
          var d = slice[i].date || "";
          if (!groups[d]) groups[d] = [];
          groups[d].push(slice[i]);
        }}
        var dates = Object.keys(groups).sort(function(a,b){{return ymdToInt(b)-ymdToInt(a);}});
        var html = "<div class='groupWrap'>";
        for (var gi=0; gi<dates.length; gi++) {{
          var d = dates[gi];
          html += "<div class='groupHdr'>" + escHtml(d) + "</div>";
          var arr = groups[d] || [];
          for (var k=0; k<arr.length; k++) {{
            var r = arr[k];
            var sec = escHtml(r.section_title || r.section || "");
            var press = escHtml(r.press || "");
            var title = highlight(r.title || "", tokens);
            var sum = highlight(r.summary || "", tokens);
            var aHref = r.archive || "";
            var uHref = r.url || "";
            var tier = parseInt(r.press_tier||0,10)||0;
            var tierLabel = tier>=4 ? "공식" : (tier>=3 ? "주요" : (tier>=2 ? "지역/전문" : "기타"));

            html += "<div class='result'>"
                 +  "<div class='rTop'>"
                 +    "<span class='chip'>" + sec + "</span>"
                 +    (press ? "<span class='chip'>" + press + "</span>" : "")
                 +    "<span class='chip'><b>" + tierLabel + "</b></span>"
                 +  "</div>"
                 +  "<div class='rTitle'>" + title + "</div>"
                 +  (sum ? "<div class='rSum'>" + sum + "</div>" : "")
                 +  "<div class='rLinks'>"
                 +    (aHref ? "<a href='" + aHref + "'>브리핑 보기</a>" : "")
                 +    (uHref ? "<a href='" + uHref + "' target='_blank' rel='noopener'>원문 열기</a>" : "")
                 +  "</div>"
                 + "</div>";
          }}
        }}
        html += "</div>";
        box.innerHTML = html;
        renderPager(res.length);
        setMeta(tokens, res.length, slice.length);
      }}

      function runSearch() {{
        var q = (input.value || "").trim();
        if (!q || q.length < 2) {{
          box.innerHTML = "";
          metaLeft.innerHTML = "";
          metaRight.textContent = "";
          pager.style.display = "none";
          return;
        }}
        if (!DATA) {{
          metaLeft.innerHTML = "<span class='chip'><b>안내</b> 검색 인덱스를 불러오는 중입니다...</span>";
          return;
        }}

        var tokens = q.split(/\\s+/).map(function(x){{return norm(x);}}).filter(Boolean);
        var res = filterItems(tokens);
        sortItems(res);

        if (PAGE < 1) PAGE = 1;
        var totalPages = Math.max(1, Math.ceil(res.length / PAGE_SIZE));
        if (PAGE > totalPages) PAGE = totalPages;

        if (groupToggle && groupToggle.checked) renderGrouped(res, tokens);
        else renderList(res, tokens);
      }}

      function resetAll() {{
        if (input) input.value = "";
        if (secSel) secSel.value = "";
        if (sortSel) sortSel.value = "relevance";
        if (groupToggle) groupToggle.checked = false;
        if (DATA) {{
          fromDate.value = DATA.min_date || "";
          toDate.value = DATA.max_date || "";
        }} else {{
          fromDate.value = "";
          toDate.value = "";
        }}
        PAGE = 1;
        box.innerHTML = "";
        metaLeft.innerHTML = "";
        metaRight.textContent = "";
        pager.style.display = "none";
        if (input) input.focus();
      }}

      async function ensureData() {{
        if (DATA || LOADING) return;
        LOADING = true;
        metaLeft.innerHTML = "<span class='chip'><b>안내</b> 검색 인덱스를 불러오는 중...</span>";
        try {{
          var url = "{esc(search_json_url)}" + "?t=" + Date.now(); // cache bust
          var r = await fetch(url, {{cache: "no-store"}});
          if (!r.ok) throw new Error("HTTP " + r.status);
          DATA = await r.json();

          // compute min/max date
          var items = DATA.items || [];
          var minD = "", maxD = "";
          for (var i=0;i<items.length;i++) {{
            var d = items[i].date || "";
            if (!d) continue;
            if (!minD || ymdToInt(d) < ymdToInt(minD)) minD = d;
            if (!maxD || ymdToInt(d) > ymdToInt(maxD)) maxD = d;
          }}
          DATA.min_date = minD;
          DATA.max_date = maxD;

          // build section options
          var map = {{}};
          for (var i=0;i<items.length;i++) {{
            var it = items[i]||{{}};
            if (!it.section) continue;
            if (!map[it.section]) map[it.section] = it.section_title || it.section;
          }}
          var keys = Object.keys(map).sort();
          for (var i=0;i<keys.length;i++) {{
            var k = keys[i];
            var opt = document.createElement("option");
            opt.value = k;
            opt.textContent = map[k];
            secSel.appendChild(opt);
          }}

          // default date: last 30 days
          if (minD && maxD) {{
            fromDate.value = minD;
            toDate.value = maxD;
            setQuickRange(30);
          }}

          metaLeft.innerHTML = "<span class='chip'><b>준비 완료</b> 키워드를 입력하세요</span>";
          metaRight.textContent = "인덱스 " + items.length + "건";
        }} catch(e) {{
          DATA = null;
          metaLeft.innerHTML = "<span class='chip'><b>오류</b> 검색 인덱스를 불러오지 못했습니다. 새로고침 후 다시 시도하세요.</span>";
          metaRight.textContent = "";
        }} finally {{
          LOADING = false;
        }}
      }}

      // events
      if (input) {{
        input.addEventListener("focus", function() {{ ensureData(); }});
        input.addEventListener("input", debounce(function() {{
          ensureData();
          PAGE = 1;
          runSearch();
        }}, 160));
        input.addEventListener("keydown", function(ev) {{
          if (ev.key === "Enter") {{
            ensureData();
            PAGE = 1;
            runSearch();
          }}
        }});
      }}
      if (clearBtn) clearBtn.addEventListener("click", function() {{ resetAll(); }});
      if (secSel) secSel.addEventListener("change", function() {{ PAGE = 1; runSearch(); }});
      if (sortSel) sortSel.addEventListener("change", function() {{ PAGE = 1; runSearch(); }});
      if (fromDate) fromDate.addEventListener("change", function() {{ PAGE = 1; runSearch(); }});
      if (toDate) toDate.addEventListener("change", function() {{ PAGE = 1; runSearch(); }});
      if (groupToggle) groupToggle.addEventListener("change", function() {{ PAGE = 1; runSearch(); }});

      if (quick7) quick7.addEventListener("click", function() {{ ensureData(); setQuickRange(7); PAGE=1; runSearch(); }});
      if (quick30) quick30.addEventListener("click", function() {{ ensureData(); setQuickRange(30); PAGE=1; runSearch(); }});
      if (quick90) quick90.addEventListener("click", function() {{ ensureData(); setQuickRange(90); PAGE=1; runSearch(); }});
      if (quickAll) quickAll.addEventListener("click", function() {{ ensureData(); setQuickRange(null); PAGE=1; runSearch(); }});
    }})();
  </script>
</body>
</html>
"""



def get_pages_base_url(repo: str) -> str:
    owner, name = repo.split("/", 1)

    # ✅ 사용자/조직 사이트(owner.github.io)는 repo path가 붙지 않음
    if name.lower().endswith(".github.io"):
        default_url = f"https://{owner.lower()}.github.io"
    else:
        default_url = f"https://{owner.lower()}.github.io/{name}".rstrip("/")

    env_url = (PAGES_BASE_URL_OVERRIDE or BRIEF_VIEW_URL).strip().rstrip("/")
    if not env_url:
        return default_url

    bad = ("gist.github.com", "raw.githubusercontent.com")
    if any(b in env_url for b in bad):
        log.warning("[WARN] PAGES_BASE_URL/BRIEF_VIEW_URL points to gist/raw. Ignoring and using default: %s", default_url)
        return default_url

    if not env_url.startswith("http://") and not env_url.startswith("https://"):
        log.warning("[WARN] PAGES_BASE_URL/BRIEF_VIEW_URL invalid (no http/https). Ignoring and using default: %s", default_url)
        return default_url

    return env_url

def ensure_not_gist(url: str, label: str) -> None:
    if "gist.github.com" in url or "raw.githubusercontent.com" in url:
        raise RuntimeError(f"[FATAL] {label} points to gist/raw: {url}")

def ensure_absolute_http_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        raise RuntimeError("Kakao web_url is empty (PAGES_BASE_URL or computed URL failed).")
    p = urlparse(u)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise RuntimeError(f"Kakao web_url must be absolute http(s) URL. Got: {u}")
    host = (p.hostname or "").lower()
    if host == "gist.github.com":
        raise RuntimeError(f"Kakao web_url is pointing to gist. Fix PAGES_BASE_URL / Kakao domain settings. Got: {u}")
    return u

def log_kakao_link(url: str) -> None:
    try:
        p = urlparse(url)
        log.info("[KAKAO LINK] %s (host=%s)", url, p.netloc)
    except Exception:
        log.info("[KAKAO LINK] %s", url)

# -----------------------------
# Kakao message (✅ 1번: 브리핑의 '핵심2'와 동일)
# -----------------------------
KAKAO_MESSAGE_SECTION_ORDER = ["supply", "policy", "dist", "pest"]

def _get_section_conf(key: str) -> SectionConfig | None:
    for s in SECTIONS:
        if s["key"] == key:
            return s
    return None


def _kakao_pick_core2(lst: list[Article]) -> list[Article]:
    """카톡 메시지에는 섹션별 2꼭지만 노출.
    - core(핵심) 2개가 있으면 그것을 우선
    - core가 없으면 '억지 채움'을 피하기 위해 일정 점수 이상만 제한적으로 노출
    """
    if not lst:
        return []
    core = [a for a in lst if getattr(a, "is_core", False)]
    if core:
        return core[:2]

    # fallback: 상단 기사 중에서도 최소 점수 기준을 통과한 것만
    picked: list[Article] = []
    for a in lst:
        if a.score < 7.0:
            continue
        # supply 섹션에서는 외식/딸기축제(소비 이벤트)류를 카톡 '핵심2' 대체 후보에서 제외
        if (a.section or "") == "supply" and is_fruit_foodservice_event_context(((a.title or "") + " " + (a.description or "")).lower()):
            continue
        # 안전망: 패스트푸드 가격 기사는 제외
        if is_fastfood_price_context(((a.title or "") + " " + (a.description or "")).lower()):
            continue
        picked.append(a)
        if len(picked) >= 2:
            break
    return picked


def build_kakao_message(report_date: str, by_section: dict[str, list["Article"]]) -> str:
    """카카오톡 '나에게 보내기'용 1개 메시지 텍스트 생성.
    - 각 섹션별 '핵심 2개'만 노출(브리핑 페이지의 core2와 동일)
    - 항목 내부 줄바꿈은 하지 않고, 섹션 사이만 한 줄 띄움(가독성)
    """
    def _shorten(s: str, n: int = 78) -> str:
        s = (s or "").strip()
        s = re.sub(r"\s+", " ", s)
        if len(s) <= n:
            return s
        return s[: max(0, n-1)].rstrip() + "…"

    order = list(KAKAO_MESSAGE_SECTION_ORDER) if isinstance(KAKAO_MESSAGE_SECTION_ORDER, list) else ["supply", "policy", "dist", "pest"]
    parts: list[str] = []
    header = f"농산물 뉴스 브리핑 ({report_date})"
    if DEV_SINGLE_PAGE_MODE:
        header = "[DEV] " + header + " - 개발 테스트 버전(운영 아님)"
    parts.append(header)

    for key in order:
        conf = _get_section_conf(key)
        sec_title = conf.get("title") if isinstance(conf, dict) else key
        parts.append(f"\n[{sec_title}]")

        lst = by_section.get(key, []) if isinstance(by_section, dict) else []
        picks = _kakao_pick_core2(lst)

        if not picks:
            parts.append("- (해당 없음)")
            continue

        for i, a in enumerate(picks, start=1):
            press = (getattr(a, "press", "") or "").strip() or press_name_from_url(getattr(a, "originallink", "") or getattr(a, "link", ""))
            press = press or "미상"
            title = _shorten(getattr(a, "title", ""), 78)
            parts.append(f"{i}. ({press}) {title}")

    out = "\n".join(parts).strip()
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out


# -----------------------------
# Kakao API
# -----------------------------
class KakaoNonRetryableError(RuntimeError):
    pass


def _kakao_error_details(r: Any) -> tuple[str, str, str]:
    try:
        data = r.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    err = str(data.get("error") or "").strip()
    desc = str(data.get("error_description") or data.get("msg") or data.get("message") or "").strip()
    code = str(data.get("error_code") or data.get("code") or "").strip()
    return err, desc, code


def _raise_kakao_non_retryable_if_needed(r: Any, context: str) -> None:
    err, desc, code = _kakao_error_details(r)
    if err in {"invalid_client", "invalid_grant", "insufficient_scope", "access_denied"}:
        detail = desc or f"HTTP {getattr(r, 'status_code', '?')}"
        if code:
            detail = f"{detail} (code={code})"
        raise KakaoNonRetryableError(f"{context}: {err}: {detail}")


def _log_kakao_fail_open(exc: Exception) -> None:
    if isinstance(exc, KakaoNonRetryableError):
        log.warning("[KAKAO] skipped due to non-retryable auth/config issue (fail-open): %s", exc)
        return
    log.error("[KAKAO] send failed but continue (fail-open): %s", exc)


def _write_kakao_send_status(status: str) -> None:
    path = (KAKAO_STATUS_FILE or "").strip()
    if not path:
        return
    status_text = (status or "unknown").strip() or "unknown"
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(status_text + "\n")
    except Exception as exc:
        log.warning("[WARN] failed to write Kakao status file: %s", exc)


def _kakao_send_status_for_exception(exc: Exception) -> str:
    if isinstance(exc, KakaoNonRetryableError):
        return "failed_non_retryable"
    return "failed"


def kakao_refresh_access_token() -> str:
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        raise RuntimeError("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN not set")

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN,
    }
    if KAKAO_CLIENT_SECRET:
        data["client_secret"] = KAKAO_CLIENT_SECRET

    r = http_session().post(url, data=data, timeout=30)
    if not r.ok:
        _raise_kakao_non_retryable_if_needed(r, "Kakao token refresh failed")
        _log_http_error("[KAKAO TOKEN ERROR]", r)
        r.raise_for_status()
    j = r.json()
    return str(j["access_token"])

def kakao_send_to_me(text: str, web_url: str) -> None:
    web_url = ensure_absolute_http_url(web_url)
    log_kakao_link(web_url)
    ensure_not_gist(web_url, "Kakao web_url")

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

    max_try = max(1, int(os.getenv("KAKAO_RETRY_MAX", "3")))
    max_try = max(1, min(max_try, 6))

    last_resp = None
    last_exc = None

    access_token = kakao_refresh_access_token()

    for attempt in range(max_try):
        headers = {"Authorization": f"Bearer {access_token}"}
        template = {
            "object_type": "text",
            "text": text,
            "link": {"web_url": web_url, "mobile_web_url": web_url},
            "button_title": "브리핑 열기",
        }

        try:
            r = http_session().post(
                url,
                headers=headers,
                data={"template_object": json.dumps(template, ensure_ascii=False)},
                timeout=35,
            )
        except Exception as exc:
            last_exc = exc
            backoff = exponential_backoff(attempt, base=0.8, cap=15.0, jitter=0.4)
            log.warning("[KAKAO SEND] network error (attempt %d/%d): %s -> sleep %.1fs", attempt+1, max_try, exc, backoff)
            time.sleep(backoff)
            continue

        last_resp = r

        if r.ok:
            return

        if r.status_code in (401, 403):
            _raise_kakao_non_retryable_if_needed(r, "Kakao send auth failed")
            _log_http_error("[KAKAO SEND AUTH ERROR]", r)
            access_token = kakao_refresh_access_token()
            continue

        if r.status_code == 429 or r.status_code in (500, 502, 503, 504):
            backoff = retry_after_or_backoff(r.headers, attempt, base=0.8, cap=15.0, jitter=0.4)
            log.warning("[KAKAO SEND] transient HTTP %s (attempt %d/%d) -> sleep %.1fs", r.status_code, attempt+1, max_try, backoff)
            time.sleep(backoff)
            continue

        _raise_kakao_non_retryable_if_needed(r, "Kakao send failed")
        _log_http_error("[KAKAO SEND ERROR]", r)
        r.raise_for_status()

    if last_resp is not None:
        _raise_kakao_non_retryable_if_needed(last_resp, "Kakao send failed")
        _log_http_error("[KAKAO SEND ERROR]", last_resp)
        last_resp.raise_for_status()
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Kakao send failed without response")

# -----------------------------
# Window calculation
# -----------------------------
def _parse_force_report_date(s: str) -> date | None:
    """Parse FORCE_REPORT_DATE in multiple common formats.

    Accepted:
      - YYYY-MM-DD (e.g., 2026-02-20)
      - YYYYMMDD   (e.g., 20260220)
      - YYYY/MM/DD (e.g., 2026/02/20)
      - YYYY.MM.DD (e.g., 2026.02.20)
    """
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{4})\.(\d{2})\.(\d{2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return date(y, mo, d)
    raise ValueError(f"Invalid FORCE_REPORT_DATE='{s}'. Use YYYY-MM-DD or YYYYMMDD (e.g., 2026-02-20).")



def compute_end_kst() -> datetime:
    """End timestamp (KST) for collection window.
    운영 기본은 항상 KST 07:00 컷오프에 스냅한다.
    FORCE_END_NOW는 디버그/수동재생성(= FORCE_REPORT_DATE 존재)일 때만 허용한다.
    """
    # FORCE_END_NOW 안전장치:
    # 실운영에서 실수로 true가 남아 있어도 윈도우가 '실행시각'까지 늘어나지 않도록 제한.
    if FORCE_END_NOW and FORCE_REPORT_DATE:
        return now_kst()
    elif FORCE_END_NOW and (not FORCE_REPORT_DATE):
        try:
            log.warning("[WARN] FORCE_END_NOW ignored (requires FORCE_REPORT_DATE for safe use)")
        except Exception:
            pass

    # ✅ 특정 날짜 재생성: FORCE_REPORT_DATE가 있으면 해당 날짜의 cutoff(07:00 KST)로 end_kst를 고정
    #    (FORCE_END_NOW=true인 경우는 예외: 디버그 목적)
    if FORCE_REPORT_DATE and (not FORCE_END_NOW):
        try:
            d = _parse_force_report_date(FORCE_REPORT_DATE)
            if d is None:
                raise ValueError("invalid FORCE_REPORT_DATE")
            return dt_kst(d, REPORT_HOUR_KST)
        except Exception as e:
            try:
                log.warning("[WARN] Invalid FORCE_REPORT_DATE=%s (%s)", FORCE_REPORT_DATE, e)
            except Exception:
                pass

    n = now_kst()
    cutoff_today = n.replace(hour=REPORT_HOUR_KST, minute=0, second=0, microsecond=0)

    # workflow_dispatch(수동 실행) + 날짜 미입력: 무조건 오늘 07:00으로 고정
    try:
        if (os.getenv("GITHUB_EVENT_NAME", "").strip().lower() == "workflow_dispatch") and (not FORCE_REPORT_DATE):
            return cutoff_today
    except Exception:
        pass

    # 일반/스케줄 실행: 07:00 이전이면 직전 07:00, 이후면 오늘 07:00
    if n < cutoff_today:
        return cutoff_today - timedelta(days=1)
    return cutoff_today

def compute_window(repo: str, token: str, end_kst: datetime) -> tuple[datetime, datetime]:

    # 안전장치: 운영 기본은 end_kst를 항상 07:00 cutoff 경계로 유지
    # (예: 외부 호출/패치 로직 중 now()가 들어와도 윈도우 오염 방지)
    if not (FORCE_END_NOW and FORCE_REPORT_DATE):
        ek = end_kst.astimezone(KST)
        cutoff_of_end_day = ek.replace(hour=REPORT_HOUR_KST, minute=0, second=0, microsecond=0)
        if ek != cutoff_of_end_day:
            if ek < cutoff_of_end_day:
                end_kst = cutoff_of_end_day - timedelta(days=1)
            else:
                end_kst = cutoff_of_end_day
    prev_bd = previous_business_day(end_kst.date())
    prev_cutoff = dt_kst(prev_bd, REPORT_HOUR_KST)

    # ✅ 수동/테스트 재생성(FORCE_REPORT_DATE)에서는 state(last_end)에 영향받지 않도록
    #    '직전 영업일 07:00 ~ end_kst' 범위로 고정한다(휴일/주말 연휴 백필 포함).
    if FORCE_REPORT_DATE:
        start = prev_cutoff
        if start >= end_kst:
            start = end_kst - timedelta(hours=24)
        return start, end_kst

    start = prev_cutoff

    if start >= end_kst:
        start = end_kst - timedelta(hours=24)

    return start, end_kst


# -----------------------------
# Main
# -----------------------------


# -----------------------------
# Backfill archive navigation (fix: older pages missing "다음 ▶" when new day is added)
# - GitHub Pages는 정적 HTML이므로, 기존 아카이브 페이지(예: 02-22)는 다음날(02-23) 생성 후에도 자동으로 업데이트되지 않는다.
# - 해결: 매 실행마다 report_date의 "인접" 아카이브(전날/다음날) 1~2개를 읽어 navRow(이전/다음 버튼 + 날짜 드롭다운)만 갱신한다.
# -----------------------------

_NAVROW_OPEN_RE = re.compile(r'<div[^>]*\bclass\s*=\s*["\']navRow["\'][^>]*>', re.I)

def _find_div_block(html_text: str, open_match_start: int) -> tuple[int, int] | None:
    """Given start index of a <div ...> opening tag, find the matching </div> end index (balanced by <div>/</div>).
    Returns (start, end) where end is exclusive.
    """
    if open_match_start < 0 or open_match_start >= len(html_text):
        return None

    token_re = re.compile(r"</div\s*>|<div\b", re.I)
    depth = 0
    started = False
    end = None

    for m in token_re.finditer(html_text, open_match_start):
        tok = m.group(0).lower()
        if tok.startswith("<div"):
            depth += 1
            started = True
        else:  # </div>
            if started:
                depth -= 1
                if depth <= 0:
                    end = m.end()
                    break

    if end is None:
        return None
    return (open_match_start, end)

def _extract_navrow_block(html_text: str) -> tuple[int, int, str] | None:
    m = _NAVROW_OPEN_RE.search(html_text or "")
    if not m:
        return None
    rng = _find_div_block(html_text, m.start())
    if not rng:
        return None
    s, e = rng
    return (s, e, html_text[s:e])

def _build_navrow_html_for_date(cur_date: str, archive_dates_desc: list[str], site_path: str) -> str:
    """Build the navRow HTML (archive button + prev/next + date select) for a given date.

    IMPORTANT: archive_dates_desc must contain ONLY dates that have an existing archive page.
    This prevents navigating to non-existent (holiday/missing) pages and avoids 404.
    """
    prev_href: str | None = None
    next_href: str | None = None

    if cur_date in archive_dates_desc:
        idx = archive_dates_desc.index(cur_date)
        # prev (older) = idx+1
        if idx + 1 < len(archive_dates_desc):
            prev_href = build_site_url(site_path, f"archive/{archive_dates_desc[idx+1]}.html")
        # next (newer) = idx-1
        if idx - 1 >= 0:
            next_href = build_site_url(site_path, f"archive/{archive_dates_desc[idx-1]}.html")

    # date select options (limit for performance)
    options = []
    for d in archive_dates_desc[:120]:
        sel = " selected" if d == cur_date else ""
        options.append(
            f'<option value="{esc(build_site_url(site_path, f"archive/{d}.html"))}"{sel}>'
            f'{esc(short_date_label(d))} ({esc(weekday_label(d))})</option>'
        )
    options_html = "\n".join(options) if options else (
        f'<option value="{esc(build_site_url(site_path, f"archive/{cur_date}.html"))}" selected>'
        f'{esc(short_date_label(cur_date))}</option>'
    )

    def nav_btn(href: str | None, label: str, msg: str, nav_key: str) -> str:
        if href:
            return f'<a class="navBtn" data-nav="{esc(nav_key)}" href="{esc(href)}">{esc(label)}</a>'
        return f'<button class="navBtn disabled" type="button" data-nav="{esc(nav_key)}" data-msg="{esc(msg)}">{esc(label)}</button>'

    home_href = site_path

    return (
        '<div class="navRow">\n'
        f'  <a class="navBtn navArchive" data-nav="archive" href="{esc(home_href)}" title="날짜별 아카이브 목록">아카이브</a>\n'
        f'  {nav_btn(prev_href, "◀ 이전", "이전 브리핑이 없습니다.", "prev")}\n'
        '  <div class="dateSelWrap">\n'
        '    <select id="dateSelect" aria-label="날짜 선택">\n'
        f'      {options_html}\n'
        '    </select>\n'
        '  </div>\n'
        f'  {nav_btn(next_href, "다음 ▶", "다음 브리핑이 없습니다.", "next")}\n'
        '</div>'
    )


def render_nav_row(cur_date: str, archive_dates_desc: list[str], site_path: str) -> str:
    """Compat helper used by UX patcher."""
    return _build_navrow_html_for_date(cur_date, archive_dates_desc, site_path)

def patch_archive_page_nav(repo: str, token: str, target_date: str, archive_dates_desc: list[str], site_path: str) -> bool:
    """Patch docs/archive/{target_date}.html navRow (prev/next + dropdown) in-place. Returns True if updated."""
    if not repo or not token or not target_date:
        return False
    path = f"{DOCS_ARCHIVE_DIR}/{target_date}.html"
    raw, sha = github_get_file(repo, path, token, ref="main")
    if not raw or not sha:
        return False

    got = _extract_navrow_block(raw)
    if not got:
        return False
    s, e, old_block = got

    new_block = _build_navrow_html_for_date(target_date, archive_dates_desc, site_path)

    # Skip if identical (avoid unnecessary commits)
    if old_block.strip() == new_block.strip():
        return False

    new_html = raw[:s] + new_block + raw[e:]
    github_put_file(repo, path, new_html, token, f"Backfill archive nav {target_date}", sha=sha, branch="main")
    return True



# UX patch run-level cache: list existing archive dates once to rebuild navRow without 404
_UX_NAV_DATES_DESC: list[str] | None = None
def _get_ux_nav_dates_desc(repo: str, token: str) -> list[str]:
    global _UX_NAV_DATES_DESC
    if _UX_NAV_DATES_DESC is None:
        try:
            s = _list_archive_dates(repo, token)
            _UX_NAV_DATES_DESC = sorted(set(sanitize_dates(list(s))), reverse=True)
        except Exception:
            _UX_NAV_DATES_DESC = []
    return _UX_NAV_DATES_DESC

def patch_archive_page_ux(repo: str, token: str, iso_date: str, site_path: str) -> bool:
    """Patch existing archive HTML to normalize UI/UX in-place."""
    try:
        path = f"{DOCS_ARCHIVE_DIR}/{iso_date}.html"
        raw, sha = github_get_file(repo, path, token, ref="main")
        if not raw or not sha:
            return False

        html_new = build_archive_ux_html(
            raw,
            iso_date=iso_date,
            site_path=site_path,
            strip_swipe_hint_blocks=_strip_swipe_hint_blocks,
            rebuild_missing_chipbar_from_sections=_rebuild_missing_chipbar_from_sections,
            normalize_existing_chipbar_titles=_normalize_existing_chipbar_titles,
            get_ux_nav_dates_desc=lambda: _get_ux_nav_dates_desc(repo, token),
            extract_navrow_block=_extract_navrow_block,
            render_nav_row=render_nav_row,
            get_manifest_dates_desc_cached=lambda: _get_manifest_dates_desc_cached(repo, token),
            build_navrow_html_for_date=_build_navrow_html_for_date,
            warn=lambda msg: log.warning("%s", msg),
        )
        if not html_new:
            return False

        github_put_file(repo, path, html_new, token, f"UX patch {iso_date}", sha=sha, branch="main")
        return True
    except Exception as e:
        log.warning("[WARN] ux patch failed for %s: %s", iso_date, e)
        return False


def backfill_neighbor_archive_nav(repo: str, token: str, report_date: str, archive_dates_desc: list[str], site_path: str, max_neighbors: int = 2) -> None:
    """Backfill navRow for report_date's neighbors so older pages can navigate forward to newly generated pages."""
    if not repo or not token or not report_date:
        return
    if not archive_dates_desc or report_date not in archive_dates_desc:
        return

    idx = archive_dates_desc.index(report_date)
    targets: list[str] = []
    # (1) 전날/더 과거 페이지: "다음 ▶"가 report_date로 연결되도록(이번 이슈의 핵심)
    if idx + 1 < len(archive_dates_desc):
        targets.append(archive_dates_desc[idx + 1])
    # (2) 다음날/더 최신 페이지: out-of-order 재생성 시 prev/next가 꼬이지 않도록 방어
    if idx - 1 >= 0:
        targets.append(archive_dates_desc[idx - 1])

    # Dedup + cap
    uniq = []
    for d in targets:
        if d not in uniq and d != report_date:
            uniq.append(d)
    uniq = uniq[:max(0, max_neighbors)]

    for d in uniq:
        try:
            updated = patch_archive_page_nav(repo, token, d, archive_dates_desc, site_path)
            if updated:
                log.info("[NAV BACKFILL] patched %s (neighbor of %s)", d, report_date)
        except Exception as e:
            log.warning("[WARN] nav backfill failed for %s: %s", d, e)

# -----------------------------
# Backfill rebuild recent archives (최근 N일 아카이브 재생성)
# - 필터/스코어/티어 개선이 생겼을 때 과거 N일 페이지에도 자동 반영
# - 기본: BACKFILL_REBUILD_DAYS=0 (OFF)
# - 주의: N이 크면 Naver/OpenAI 호출량이 커질 수 있음
# -----------------------------

def _compute_window_for_report_date(report_date: str) -> tuple[datetime, datetime]:
    """FORCE_REPORT_DATE 모드와 동일한 방식으로 윈도우를 계산한다.
    - end: report_date 07:00(KST)
    - start: 직전 영업일 07:00(KST) (연휴/주말이면 더 길어질 수 있음)
    """
    d = date.fromisoformat(report_date)
    end_kst = dt_kst(d, REPORT_HOUR_KST)
    prev_bd = previous_business_day(d)
    start_kst = dt_kst(prev_bd, REPORT_HOUR_KST)
    if start_kst >= end_kst:
        start_kst = end_kst - timedelta(hours=24)
    return start_kst, end_kst


def backfill_rebuild_recent_archives(
    repo: str,
    token: str,
    report_date: str,
    archive_dates_desc: list[str],
    site_path: str,
    summary_cache: JsonDict,
    search_idx: JsonDict,
) -> JsonDict:
    """최근 BACKFILL_REBUILD_DAYS 만큼의 과거 아카이브를 재생성하여 커밋한다.
    - daily html (docs/archive/YYYY-MM-DD.html) 업데이트
    - docs/search_index.json 엔트리도 해당 날짜로 재생성
    - 카카오 전송/manifest/state는 건드리지 않는다(오늘자에서만 처리)
    """
    days = int(BACKFILL_REBUILD_DAYS or 0)
    use_range = bool((BACKFILL_START_DATE or "").strip() or (BACKFILL_END_DATE or "").strip())
    if use_range:
        log.info("[BACKFILL] range mode enabled: %s ~ %s (days_arg=%s create_missing=%s)", BACKFILL_START_DATE or "", BACKFILL_END_DATE or "", days, BACKFILL_REBUILD_CREATE_MISSING)
    if days <= 0 and not use_range:
        return search_idx
    # range 모드에서는 backfill_days=0이어도 BACKFILL_START_DATE~BACKFILL_END_DATE를 기준으로 재생성한다.
    if not repo or not token:
        return search_idx

    try:
        today = date.fromisoformat(report_date)
    except Exception:
        return search_idx

        # Determine existing archive dates from docs/archive listing (avoid relying on manifest correctness)
    avail: set[str] = set()
    try:
        items = github_list_dir(repo, DOCS_ARCHIVE_DIR, token, ref="main")
        for it in (items or []):
            nm = it.get("name") if isinstance(it, dict) else None
            if isinstance(nm, str) and nm.endswith(".html"):
                dd = nm[:-5]
                if is_iso_date_str(dd):
                    avail.add(dd)
    except Exception as e:
        log.warning("[BACKFILL] archive dir listing failed; fallback to manifest-derived list: %s", e)
        avail = set(archive_dates_desc or [])

    if (not avail) and (not BACKFILL_REBUILD_CREATE_MISSING):
        log.warning("[BACKFILL] no available archive dates found; skip backfill rebuild (create_missing=false)")
        return search_idx

    # rebuild targets: report_date 제외, (1) BACKFILL_START_DATE~BACKFILL_END_DATE 범위 또는 (2) 과거 N일
    create_missing = bool(BACKFILL_REBUILD_CREATE_MISSING)
    # start_date 지정 시(기간 재생성 모드) 누락 파일 생성이 기본값이 되도록 보정
    if BACKFILL_START_DATE and (not create_missing):
        create_missing = True
    start_d = None
    end_d = None
    if BACKFILL_END_DATE:
        try:
            end_d = date.fromisoformat(BACKFILL_END_DATE)
        except Exception:
            end_d = None
    if end_d is None:
        end_d = today - timedelta(days=1)
    if BACKFILL_START_DATE:
        try:
            start_d = date.fromisoformat(BACKFILL_START_DATE)
        except Exception:
            start_d = None
    if start_d is None:
        start_d = end_d - timedelta(days=max(0, days - 1))

    total_days = (end_d - start_d).days + 1
    if total_days > BACKFILL_REBUILD_DAYS_MAX and BACKFILL_REBUILD_DAYS_MAX > 0:
        log.warning("[BACKFILL] requested %d day(s) exceeds cap %d; trimming", total_days, BACKFILL_REBUILD_DAYS_MAX)
        start_d = end_d - timedelta(days=BACKFILL_REBUILD_DAYS_MAX - 1)

    targets: list[str] = []
    cur = end_d
    while cur >= start_d:
        d = cur.isoformat()
        if d == report_date:
            cur -= timedelta(days=1)
            continue
        if (not create_missing) and (d not in avail):
            cur -= timedelta(days=1)
            continue
        targets.append(d)
        cur -= timedelta(days=1)

    if not targets:
        return search_idx


    # ✅ Prevent 404: exclude non-business days from navigation/date list by default
    include_nonbiz = (os.getenv("BACKFILL_INCLUDE_NONBUSINESS_DAYS", "false") or "").strip().lower() in ("1", "true", "yes", "y")
    if (not include_nonbiz) and (not FORCE_RUN_ANYDAY):
        try:
            targets = [d for d in targets if is_business_day_kr(date.fromisoformat(d))]
        except Exception:
            pass

    # navigation pool: existing archives + targets + report_date
    nav_pool = set((archive_dates_desc or [])) | set(targets) | {report_date}
    if (not include_nonbiz) and (not FORCE_RUN_ANYDAY):
        try:
            nav_pool = {d for d in nav_pool if is_business_day_kr(date.fromisoformat(d))}
        except Exception:
            pass
    nav_dates_desc = sorted(nav_pool, reverse=True)

    log.info("[BACKFILL] available archives=%d | rebuild %d day(s): %s", len(avail), len(targets), ", ".join(targets))

    for d in targets:
        try:
            start_kst, end_kst = _compute_window_for_report_date(d)
            log.info("[BACKFILL] %s window: %s ~ %s", d, start_kst.isoformat(), end_kst.isoformat())

            # ✅ 정책: 주말/공휴일은 백필에서도 기본 스킵 (필요 시 FORCE_RUN_ANYDAY=true로 허용)
            try:
                if (not FORCE_RUN_ANYDAY) and (not is_business_day_kr(date.fromisoformat(d))):
                    log.info("[BACKFILL] skip non-business day: %s", d)
                    continue
            except Exception:
                pass

            bf_by_section = collect_all_sections(start_kst, end_kst)

            # 요약은 비용/레이트리밋이 걸릴 수 있어 옵션 제공(기본: 수행). skip_openai=True여도 캐시로 요약을 채울 수 있게 allow_openai로 제어.
            bf_by_section = fill_summaries(
                bf_by_section,
                cache=summary_cache,
                allow_openai=(not BACKFILL_REBUILD_SKIP_OPENAI),
            )

            bf_html = render_daily_page(d, start_kst, end_kst, bf_by_section, nav_dates_desc, site_path)

            bf_path = f"{DOCS_ARCHIVE_DIR}/{d}.html"
            raw_old, sha_old = github_get_file(repo, bf_path, token, ref="main")
            github_put_file(repo, bf_path, bf_html, token, f"Backfill rebuild {d}", sha=sha_old, branch="main")
            log.info("[BACKFILL PUT] %s", bf_path)

            if DEBUG_REPORT and DEBUG_REPORT_WRITE_JSON:
                try:
                    DEBUG_DATA["generated_at_kst"] = datetime.now(KST).isoformat(timespec="seconds")
                    debug_path = f"docs/debug/{d}.json"
                    debug_json = json.dumps(DEBUG_DATA, ensure_ascii=False, indent=2)
                    _raw_dbg_old, sha_dbg_old = github_get_file(repo, debug_path, token, ref="main")
                    github_put_file(repo, debug_path, debug_json, token, f"Backfill debug report {d}", sha=sha_dbg_old, branch="main")
                    log.info("[BACKFILL PUT] %s", debug_path)
                except Exception as e:
                    log.warning("[BACKFILL] debug upload failed for %s: %s", d, e)

            # search index update for that day
            search_idx = update_search_index(search_idx, d, bf_by_section, site_path)

            if BACKFILL_REBUILD_SLEEP_SEC and BACKFILL_REBUILD_SLEEP_SEC > 0:
                time.sleep(BACKFILL_REBUILD_SLEEP_SEC)

        except Exception as e:
            log.warning("[BACKFILL] failed for %s: %s", d, e)
            continue

    return search_idx



# -----------------------------
# Maintenance helpers (rebuild/backfill) - no Kakao, no state update
# -----------------------------

def _list_archive_dates(repo: str, token: str) -> set[str]:
    """Return set of YYYY-MM-DD existing under docs/archive (best-effort)."""
    dset: set[str] = set()
    try:
        items = github_list_dir(repo, DOCS_ARCHIVE_DIR, token, ref="main")
        for it in (items or []):
            nm = it.get("name") if isinstance(it, dict) else None
            if isinstance(nm, str) and nm.endswith(".html"):
                dd = nm[:-5]
                if is_iso_date_str(dd):
                    dset.add(dd)
    except Exception:
        pass
    return dset


def _list_dev_preview_archive_dates(repo: str, token: str) -> set[str]:
    dset: set[str] = set()
    if not DEV_SINGLE_PAGE_MODE:
        return dset
    archive_dir = _dev_single_page_archive_repo_path("_marker_").rpartition("/")[0]
    preview_ref = GH_CONTENT_BRANCH or GH_CONTENT_REF or "main"
    try:
        items = github_list_dir(repo, archive_dir, token, ref=preview_ref)
        for it in (items or []):
            nm = it.get("name") if isinstance(it, dict) else None
            if isinstance(nm, str) and nm.endswith(".html"):
                dd = nm[:-5]
                if is_iso_date_str(dd):
                    dset.add(dd)
    except Exception:
        pass
    return dset


def _maybe_ux_patch(repo: str, token: str, base_iso: str, site_path: str) -> None:
    """Optionally apply UX patch to last UX_PATCH_DAYS pages starting at base_iso.

    In strict mode, fail the run if any page patch throws an exception.
    Strict mode is enabled when:
      - UX_PATCH_STRICT=true, OR
      - MAINTENANCE_TASK=ux_patch (the dedicated UX patch workflow)
    """
    try:
        days = int(UX_PATCH_DAYS or 0)
    except Exception:
        days = 0
    if days <= 0:
        return
    try:
        base = date.fromisoformat(base_iso)
    except Exception:
        return

    patched = 0
    skipped = 0
    failed = 0

    for i in range(0, days):
        d2 = (base - timedelta(days=i)).isoformat()
        try:
            if patch_archive_page_ux(repo, token, d2, site_path):
                patched += 1
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            log.warning("[WARN] ux patch failed for %s: %s", d2, e)
            skipped += 1

    log.info("[UX PATCH] patched=%d skipped=%d (days=%d)", patched, skipped, days)

    strict_env = str(os.getenv("UX_PATCH_STRICT", "")).strip().lower()
    strict = (strict_env in ("1", "true", "yes", "y")) or (str(os.getenv("MAINTENANCE_TASK", "")).strip().lower() == "ux_patch")
    if strict and failed > 0:
        raise SystemExit(1)


def build_dev_preview_version_json(report_date: str) -> str:
    asset_base = _dev_single_page_asset_base_url()
    payload: JsonDict = {
        "build_tag": BUILD_TAG,
        "generated_at_kst": RENDERED_AT_KST,
        "report_date": report_date,
        "preview_path": _normalize_repo_path(DEV_SINGLE_PAGE_PATH or "docs/dev/index.html"),
        "content_ref": GH_CONTENT_REF,
        "content_branch": GH_CONTENT_BRANCH,
        "asset_base_url": asset_base,
    }
    if asset_base:
        payload["preview_url"] = f"{asset_base}/index.html"
        payload["version_url"] = f"{asset_base}/version.json"
        payload["debug_url"] = f"{asset_base}/debug/{report_date}.json"
        payload["archive_manifest_url"] = f"{asset_base}/archive_manifest.json"
        payload["archive_base_url"] = f"{asset_base}/archive"
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def maintenance_rebuild_date(repo: str, token: str, report_date: str, site_path: str, allow_openai: bool = True) -> None:
    """Rebuild a single date page (docs/archive/YYYY-MM-DD.html) and refresh index/search. No Kakao, no state."""
    if not report_date or not is_iso_date_str(report_date):
        raise ValueError("report_date must be YYYY-MM-DD")
    # business-day guard (override with FORCE_RUN_ANYDAY)
    try:
        if (not FORCE_RUN_ANYDAY) and (not is_business_day_kr(date.fromisoformat(report_date))):
            log.info("[MAINT] rebuild_date skip non-business day: %s", report_date)
            return
    except Exception:
        pass

    start_kst, end_kst = _compute_window_for_report_date(report_date)
    log.info("[MAINT] rebuild_date %s window: %s ~ %s", report_date, start_kst.isoformat(), end_kst.isoformat())

    # collect + summarize
    by_section = collect_all_sections(start_kst, end_kst)
    summary_cache = load_summary_cache(repo, token)
    by_section = fill_summaries(by_section, cache=summary_cache, allow_openai=allow_openai)

    # nav dates from actual archive listing
    avail = _list_dev_preview_archive_dates(repo, token) if DEV_SINGLE_PAGE_MODE else _list_archive_dates(repo, token)
    avail.add(report_date)
    archive_dates_desc = sorted(avail, reverse=True)

    # render
    daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, archive_dates_desc, site_path)

    if DEV_SINGLE_PAGE_MODE:
        preview_ref = GH_CONTENT_BRANCH or GH_CONTENT_REF or "main"
        version_path = _dev_single_page_version_repo_path()
        version_json = build_dev_preview_version_json(report_date)
        _raw_version_old, sha_version = github_get_file(repo, version_path, token, ref=preview_ref)
        github_put_file(repo, version_path, version_json, token, f"Update dev preview version {report_date}", sha=sha_version, branch=preview_ref)
        log.info("[MAINT PUT] %s", version_path)

        preview_path = DEV_SINGLE_PAGE_PATH or "docs/dev/index.html"
        _raw_preview_old, sha_preview = github_get_file(repo, preview_path, token, ref=preview_ref)
        github_put_file(repo, preview_path, daily_html, token, f"Update dev preview {report_date}", sha=sha_preview, branch=preview_ref)
        log.info("[MAINT PUT] %s", preview_path)

        archive_path = _dev_single_page_archive_repo_path(report_date)
        _raw_archive_old, sha_archive = github_get_file(repo, archive_path, token, ref=preview_ref)
        github_put_file(repo, archive_path, daily_html, token, f"Archive dev preview {report_date}", sha=sha_archive, branch=preview_ref)
        log.info("[MAINT PUT] %s", archive_path)

        archive_manifest = {
            "version": 1,
            "count": len(archive_dates_desc),
            "latest": report_date,
            "generated_at_kst": RENDERED_AT_KST,
            "dates": sorted(set(sanitize_dates(list(archive_dates_desc)))),
        }
        archive_manifest_path = _dev_single_page_archive_manifest_repo_path()
        archive_manifest_json = json.dumps(archive_manifest, ensure_ascii=False, indent=2) + "\n"
        _raw_archive_manifest_old, sha_archive_manifest = github_get_file(repo, archive_manifest_path, token, ref=preview_ref)
        github_put_file(
            repo,
            archive_manifest_path,
            archive_manifest_json,
            token,
            f"Update dev preview archive manifest {report_date}",
            sha=sha_archive_manifest,
            branch=preview_ref,
        )
        log.info("[MAINT PUT] %s", archive_manifest_path)

        if DEBUG_REPORT and DEBUG_REPORT_WRITE_JSON:
            try:
                DEBUG_DATA["generated_at_kst"] = datetime.now(KST).isoformat(timespec="seconds")
                debug_path = _dev_single_page_debug_repo_path(report_date)
                debug_json = json.dumps(DEBUG_DATA, ensure_ascii=False, indent=2)
                _raw_dbg_old, sha_dbg_old = github_get_file(repo, debug_path, token, ref=preview_ref)
                github_put_file(repo, debug_path, debug_json, token, f"Update dev preview debug {report_date}", sha=sha_dbg_old, branch=preview_ref)
                log.info("[MAINT PUT] %s", debug_path)
            except Exception as e:
                log.warning("[WARN] dev preview debug upload failed: %s", e)

        if MAINTENANCE_SEND_KAKAO:
            try:
                base_url = get_pages_base_url(repo).rstrip("/")
                daily_url = _dev_single_page_archive_url(report_date, base_url, cache_bust=True)
                daily_url = ensure_absolute_http_url(daily_url)
                kakao_text = build_kakao_message(report_date, by_section)
                if KAKAO_INCLUDE_LINK_IN_TEXT:
                    kakao_text = kakao_text + "\n" + daily_url
                log_kakao_link(daily_url)
                kakao_send_to_me(kakao_text, daily_url)
                _write_kakao_send_status("success")
                log.info("[OK] Kakao message sent (maintenance rebuild_date, single-page). URL=%s", daily_url)
            except Exception as e:
                _write_kakao_send_status(_kakao_send_status_for_exception(e))
                if KAKAO_FAIL_OPEN:
                    _log_kakao_fail_open(e)
                else:
                    raise
        return

    daily_path = f"{DOCS_ARCHIVE_DIR}/{report_date}.html"
    _raw_daily_old, sha_old = github_get_file(repo, daily_path, token, ref="main")
    github_put_file(repo, daily_path, daily_html, token, f"Rebuild date {report_date}", sha=sha_old, branch="main")
    log.info("[MAINT PUT] %s", daily_path)

    # Optional: debug report JSON (maintenance rebuild_date)
    if DEBUG_REPORT and DEBUG_REPORT_WRITE_JSON:
        try:
            DEBUG_DATA["generated_at_kst"] = datetime.now(KST).isoformat(timespec="seconds")
            debug_path = f"docs/debug/{report_date}.json"
            debug_json = json.dumps(DEBUG_DATA, ensure_ascii=False, indent=2)
            _raw_dbg_old, sha_dbg_old = github_get_file(repo, debug_path, token, ref="main")
            github_put_file(repo, debug_path, debug_json, token, f"Debug report {report_date}", sha=sha_dbg_old, branch="main")
            log.info("[MAINT PUT] %s", debug_path)
        except Exception as e:
            log.warning("[WARN] debug report upload failed: %s", e)

    # update search index
    search_idx, ssha = load_search_index(repo, token)
    search_idx = update_search_index(search_idx, report_date, by_section, site_path)
    save_search_index(repo, token, search_idx, ssha)

    # refresh index based on archive listing
    avail2 = _list_archive_dates(repo, token)
    avail2.add(report_date)
    archive_dates_desc2 = sorted(avail2, reverse=True)
    index_html = render_index_page({"dates": archive_dates_desc2}, site_path)
    raw_i, sha_i = github_get_file(repo, DOCS_INDEX_PATH, token, ref="main")
    github_put_file(repo, DOCS_INDEX_PATH, index_html, token, f"Update index {report_date}", sha=sha_i, branch="main")


    # refresh archive manifest files (.agri_archive.json + docs/archive_manifest.json)
    try:
        avail3 = _list_archive_dates(repo, token)
        avail3.add(report_date)
        dates_sorted = sorted(set(sanitize_dates(list(avail3))))
        manifest3, msha3 = load_archive_manifest(repo, token)
        manifest3 = _normalize_manifest(manifest3)
        manifest3["dates"] = dates_sorted
        save_archive_manifest(repo, token, manifest3, msha3)
        save_docs_archive_manifest(repo, token, dates_sorted)
    except Exception as e:
        log.warning("[WARN] manifest update after rebuild_date failed: %s", e)

    # neighbor nav repair (older pages may miss next/prev)
    try:
        backfill_neighbor_archive_nav(repo, token, report_date, archive_dates_desc2, site_path)
    except Exception as e:
        log.warning("[WARN] neighbor nav backfill failed: %s", e)

    # optional UX patch sweep
    _maybe_ux_patch(repo, token, report_date, site_path)

    # save summary cache (rebuild may create new summaries)
    try:
        save_summary_cache(repo, token, summary_cache)
    except Exception as e:
        log.warning("[WARN] save_summary_cache after rebuild_date failed: %s", e)


    # optional Kakao send (maintenance rebuild_date)
    if MAINTENANCE_SEND_KAKAO:
        try:
            base_url = get_pages_base_url(repo).rstrip("/")
            daily_url = build_daily_url(base_url, report_date, cache_bust=True)
            daily_url = ensure_absolute_http_url(daily_url)
            kakao_text = build_kakao_message(report_date, by_section)
            if KAKAO_INCLUDE_LINK_IN_TEXT:
                kakao_text = kakao_text + "\n" + daily_url
            log_kakao_link(daily_url)
            kakao_send_to_me(kakao_text, daily_url)
            _write_kakao_send_status("success")
            log.info("[OK] Kakao message sent (maintenance rebuild_date). URL=%s", daily_url)
        except Exception as e:
            _write_kakao_send_status(_kakao_send_status_for_exception(e))
            if KAKAO_FAIL_OPEN:
                _log_kakao_fail_open(e)
            else:
                raise

def maintenance_backfill_rebuild(repo: str, token: str, base_date_iso: str, site_path: str) -> None:
    """Backfill rebuild recent archives (excludes base_date itself). No Kakao, no state."""
    if not base_date_iso or not is_iso_date_str(base_date_iso):
        raise ValueError("base_date_iso must be YYYY-MM-DD")
    # if base date is weekend/holiday and not allowed, shift to previous business day
    try:
        bd = date.fromisoformat(base_date_iso)
        if (not FORCE_RUN_ANYDAY) and (not is_business_day_kr(bd)):
            bd2 = previous_business_day(bd)
            base_date_iso = bd2.isoformat()
            log.info("[MAINT] backfill base shifted to previous business day: %s", base_date_iso)
    except Exception:
        pass

    summary_cache = load_summary_cache(repo, token)
    search_idx, ssha = load_search_index(repo, token)

    avail = _list_archive_dates(repo, token)
    avail.add(base_date_iso)
    archive_dates_desc = sorted(avail, reverse=True)

    search_idx = backfill_rebuild_recent_archives(
        repo, token, base_date_iso, archive_dates_desc, site_path, summary_cache, search_idx
    )
    save_search_index(repo, token, search_idx, ssha)

    # index refresh (in case create_missing enabled)
    avail2 = _list_archive_dates(repo, token)
    avail2.add(base_date_iso)
    archive_dates_desc2 = sorted(avail2, reverse=True)
    index_html = render_index_page({"dates": archive_dates_desc2}, site_path)
    raw_i, sha_i = github_get_file(repo, DOCS_INDEX_PATH, token, ref="main")
    github_put_file(repo, DOCS_INDEX_PATH, index_html, token, f"Update index after backfill {base_date_iso}", sha=sha_i, branch="main")


    # refresh archive manifest files (.agri_archive.json + docs/archive_manifest.json)
    try:
        dates_sorted = sorted(set(sanitize_dates(list(avail2))))
        manifest3, msha3 = load_archive_manifest(repo, token)
        manifest3 = _normalize_manifest(manifest3)
        manifest3["dates"] = dates_sorted
        save_archive_manifest(repo, token, manifest3, msha3)
        save_docs_archive_manifest(repo, token, dates_sorted)
    except Exception as e:
        log.warning("[WARN] manifest update after maintenance backfill failed: %s", e)

    # neighbor nav repair (older pages may miss next/prev)
    try:
        backfill_neighbor_archive_nav(repo, token, base_date_iso, archive_dates_desc2, site_path)
    except Exception as e:
        log.warning("[WARN] neighbor nav backfill failed: %s", e)

    # optional UX patch sweep
    _maybe_ux_patch(repo, token, base_date_iso, site_path)

    # save summary cache (backfill may create new summaries)
    try:
        save_summary_cache(repo, token, summary_cache)
    except Exception as e:
        log.warning("[WARN] save_summary_cache after backfill failed: %s", e)







def main() -> None:
    log.info("[BUILD] %s", BUILD_TAG)
    _write_kakao_send_status("not_attempted")
    if not DEFAULT_REPO:
        raise RuntimeError("GITHUB_REPO or GITHUB_REPOSITORY is not set (e.g., ORGNAME/agri-news-brief)")
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is not set")

    maintenance_task = (os.getenv("MAINTENANCE_TASK", "") or "").strip().lower()

    repo = DEFAULT_REPO
    end_kst = compute_end_kst()

    # Route top-level flow via orchestrator policy (side-effect free dispatch only).
    dispatch = {"action": ""}

    def _mark_dispatch(action: str) -> None:
        dispatch["action"] = action

    ctx = OrchestratorContext(
        repo=repo,
        end_kst=end_kst,
        maintenance_task=maintenance_task,
        force_report_date=FORCE_REPORT_DATE,
        force_run_anyday=FORCE_RUN_ANYDAY,
        naver_ready=bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET),
        kakao_ready=bool(KAKAO_REST_API_KEY and KAKAO_REFRESH_TOKEN),
    )
    handlers = OrchestratorHandlers(
        run_ux_patch=lambda _repo, _end: _mark_dispatch("ux_patch"),
        run_maintenance_rebuild=lambda _repo, _end, task: _mark_dispatch(task),
        run_force_rebuild=lambda _repo, _end: _mark_dispatch("force_rebuild"),
        run_daily=lambda _repo, _end, _task: _mark_dispatch("daily"),
        is_business_day=lambda dt: is_business_day_kr(dt.date()),
        on_skip_non_business=lambda _end: _mark_dispatch("skip_non_business"),
    )
    execute_orchestration(ctx, handlers)
    if dispatch.get("action") == "skip_non_business":
        log.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date().isoformat())
        return

    # -----------------------------
    # Maintenance-only tasks
    # -----------------------------
    if maintenance_task == "ux_patch":
        # 과거 아카이브 UI/UX 패치만 수행하고 종료(브리핑 생성/카톡 발송 없음)
        try:
            site_path = get_run_site_path(repo)
        except Exception:
            site_path = "/"

        try:
            base_d = _parse_force_report_date(FORCE_REPORT_DATE) if FORCE_REPORT_DATE else end_kst.date()
        except Exception:
            base_d = end_kst.date()

        days = int(UX_PATCH_DAYS or 0)
        if days <= 0:
            log.info("[UX PATCH] days=0 -> nothing to do")
            return

        ux_patched = 0
        ux_skipped = 0
        for i in range(0, days):
            d2 = ((base_d or end_kst.date()) - timedelta(days=i)).isoformat()
            try:
                if patch_archive_page_ux(repo, GH_TOKEN, d2, site_path):
                    ux_patched += 1
                else:
                    ux_skipped += 1
            except Exception:
                ux_skipped += 1
        log.info("[UX PATCH] patched=%d skipped=%d (days=%d)", ux_patched, ux_skipped, days)
        return

    # -----------------------------
    # Maintenance tasks (rebuild/backfill) - no Kakao, no state update
    # -----------------------------
    if maintenance_task in ("rebuild_date", "backfill_rebuild"):
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
        try:
            site_path = get_run_site_path(repo)
        except Exception:
            site_path = "/"

        if maintenance_task == "rebuild_date":
            if not FORCE_REPORT_DATE:
                raise RuntimeError("FORCE_REPORT_DATE(force_report_date) is required for task=rebuild_date")
            d_iso = str(FORCE_REPORT_DATE).strip()
            maintenance_rebuild_date(repo, GH_TOKEN, d_iso, site_path, allow_openai=True)
            return

        # maintenance_task == "backfill_rebuild"
        base_iso = ""
        try:
            base_iso = str(FORCE_REPORT_DATE).strip() if FORCE_REPORT_DATE else end_kst.date().isoformat()
        except Exception:
            base_iso = end_kst.date().isoformat()
        maintenance_backfill_rebuild(repo, GH_TOKEN, base_iso, site_path)
        return

    # -----------------------------
    # Manual rebuild (workflow_dispatch force_report_date)
    # - Use the same safe path as maintenance: correct window, no Kakao, no state update
    # -----------------------------
    if FORCE_REPORT_DATE:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
        try:
            site_path = get_run_site_path(repo)
        except Exception:
            site_path = "/"
        d_iso = ""
        try:
            d_iso = str(FORCE_REPORT_DATE).strip()
        except Exception:
            d_iso = str(FORCE_REPORT_DATE).strip()
        maintenance_rebuild_date(repo, GH_TOKEN, d_iso, site_path, allow_openai=True)
        return

    # Normal run requires external API credentials
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        raise RuntimeError("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN is not set")

    is_bd = is_business_day_kr(end_kst.date())
    if (not FORCE_RUN_ANYDAY) and (not is_bd):
        log.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date().isoformat())
        return

    start_kst, end_kst = compute_window(repo, GH_TOKEN, end_kst)
    log.info("[INFO] Window KST: %s ~ %s", start_kst.isoformat(), end_kst.isoformat())

    force_iso = ""
    if FORCE_REPORT_DATE:
        try:
            force_iso = _parse_force_report_date(FORCE_REPORT_DATE).isoformat()
        except Exception:
            force_iso = ""
    report_date = REPORT_DATE_OVERRIDE or force_iso or end_kst.date().isoformat()

    # -----------------------------
    # 72h 슬라이딩 윈도우 + 크로스데이(최근 N일) 중복 방지 초기화
    # - FORCE_REPORT_DATE(수동 재생성) / maintenance에서는 중복 방지를 기본 OFF(재현성/작업 편의)
    # - 정상 daily run에서만 ON (필요 시 env CROSSDAY_DEDUPE_ENABLED로 끄기)
    global CROSSDAY_DEDUPE_ENABLED, RECENT_HISTORY_CANON, RECENT_HISTORY_NORM
    CROSSDAY_DEDUPE_ENABLED = bool(CROSSDAY_DEDUPE_ENABLED_ENV) and (maintenance_task == "") and (not bool(FORCE_REPORT_DATE))
    if CROSSDAY_DEDUPE_ENABLED:
        try:
            _st = load_state(repo, GH_TOKEN)
            _recent = normalize_recent_items(_st.get("recent_items", []), end_kst.date())
            RECENT_HISTORY_CANON = set([it.get("canon","") for it in _recent if it.get("canon")])
            RECENT_HISTORY_NORM = set([it.get("norm","") for it in _recent if it.get("norm")])
        except Exception:
            RECENT_HISTORY_CANON = set()
            RECENT_HISTORY_NORM = set()
    else:
        RECENT_HISTORY_CANON = set()
        RECENT_HISTORY_NORM = set()

    # Kakao absolute URL
    base_url = get_pages_base_url(repo).rstrip("/")
    daily_url = build_daily_url(base_url, report_date, cache_bust=True)
    daily_url = ensure_absolute_http_url(daily_url)
    log.info("[INFO] Report date: %s (override=%s) -> %s", report_date, bool(REPORT_DATE_OVERRIDE or force_iso), daily_url)

    ensure_not_gist(base_url, "base_url")
    ensure_not_gist(daily_url, "daily_url")

    # site path (✅ 4번: 404 방지 링크용)
    site_path = get_run_site_path(repo)

    # 최근 아카이브 UI/UX 패치 (스와이프/스티키/로딩 배지)
    if UX_PATCH_DAYS and int(UX_PATCH_DAYS) > 0:
        try:
            base = date.fromisoformat(report_date)
            ux_patched = 0
            ux_skipped = 0
            for i in range(0, int(UX_PATCH_DAYS)):
                d2 = (base - timedelta(days=i)).isoformat()
                if patch_archive_page_ux(repo, GH_TOKEN, d2, site_path):
                    ux_patched += 1
                else:
                    ux_skipped += 1
            log.info("[UX PATCH] patched=%d skipped=%d (days=%d)", ux_patched, ux_skipped, int(UX_PATCH_DAYS))
        except Exception as e:
            log.warning("[WARN] UX PATCH failed: %s", e)

    # manifest load + sanitize (manifest는 유지하되, UI 날짜 목록은 docs/archive 실제 파일을 기준으로 만든다)
    manifest, msha = load_archive_manifest(repo, GH_TOKEN)
    manifest = _normalize_manifest(manifest)

    # ✅ UI 날짜 목록: docs/archive 디렉터리 listing 기반(날짜 셀렉트/이전/다음 일관성 보장)
    avail_dates: set[str] = set()
    try:
        items = github_list_dir(repo, DOCS_ARCHIVE_DIR, GH_TOKEN, ref="main")
        for it in (items or []):
            nm = it.get("name") if isinstance(it, dict) else None
            if isinstance(nm, str) and nm.endswith(".html"):
                dd = nm[:-5]
                if is_iso_date_str(dd):
                    avail_dates.add(dd)
    except Exception as e:
        log.warning("[WARN] archive listing failed; treat as empty to avoid stale 404 links: %s", e)
        avail_dates = set()

    avail_dates.add(report_date)
    archive_dates_desc = sorted(avail_dates, reverse=True)
    # (비활성화) 기간 범위를 강제로 드롭다운에 표시하지 않습니다.
    # 실제로 생성된 docs/archive 파일 목록(listing)만 드롭다운/이전/다음에 반영합니다.
    manifest["dates"] = sorted(set(sanitize_dates(list(avail_dates))))

    # collect + summarize
    by_section = collect_all_sections(start_kst, end_kst)
    summary_cache = load_summary_cache(repo, GH_TOKEN)
    by_section = fill_summaries(by_section, cache=summary_cache)
    try:
        save_summary_cache(repo, GH_TOKEN, summary_cache)
    except Exception as e:
        log.warning("[WARN] save_summary_cache failed: %s", e)

    # render (✅ 2번: 전체 노출 / 중요도 정렬)
    daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, archive_dates_desc, site_path)

    # Optional: debug report JSON (for diagnosis)
    if DEBUG_REPORT and DEBUG_REPORT_WRITE_JSON:
        try:
            DEBUG_DATA["generated_at_kst"] = datetime.now(KST).isoformat(timespec="seconds")
            debug_path = f"docs/debug/{report_date}.json"
            debug_json = json.dumps(DEBUG_DATA, ensure_ascii=False, indent=2)
            _raw_dbg_old, sha_dbg_old = github_get_file(repo, debug_path, GH_TOKEN, ref="main")
            github_put_file(repo, debug_path, debug_json, GH_TOKEN, f"Update debug report {report_date}", sha=sha_dbg_old, branch="main")
        except Exception as e:
            log.warning("debug report upload failed: %s", e)

    # index는 404 방지를 위해 "검증된 날짜"만 노출
    index_manifest = {"dates": archive_dates_desc}
    index_html = render_index_page(index_manifest, site_path)

    # update keyword search index (docs/search_index.json)
    search_idx, ssha = load_search_index(repo, GH_TOKEN)
    search_idx = update_search_index(search_idx, report_date, by_section, site_path)
    # (옵션) 백필 재생성: 과거 페이지/검색 인덱스까지 최신 로직으로 재생성
    try:
        search_idx = backfill_rebuild_recent_archives(repo, GH_TOKEN, report_date, archive_dates_desc, site_path, summary_cache, search_idx)
        # ✅ backfill 후: 새로 생성된 docs/archive 파일을 기준으로 날짜 목록/이전/다음/드롭다운을 즉시 갱신
        try:
            dset = set()
            items_bf = github_list_dir(repo, DOCS_ARCHIVE_DIR, GH_TOKEN, ref="main")
            for it in (items_bf or []):
                nm = it.get("name") if isinstance(it, dict) else None
                if isinstance(nm, str) and nm.endswith(".html"):
                    dd = nm[:-5]
                    if is_iso_date_str(dd):
                        dset.add(dd)
            dset.add(report_date)
            # listing이 일시적으로 비어도, 기간 재생성 모드라면 범위 기반 목록으로 fallback
            if (not dset) and (BACKFILL_START_DATE or BACKFILL_END_DATE):
                try:
                    s = date.fromisoformat(BACKFILL_START_DATE) if BACKFILL_START_DATE else None
                except Exception:
                    s = None
                try:
                    e2 = date.fromisoformat(BACKFILL_END_DATE) if BACKFILL_END_DATE else date.fromisoformat(report_date)
                except Exception:
                    e2 = date.fromisoformat(report_date)
                if s is not None and e2 is not None and s <= e2:
                    cur = e2
                    while cur >= s:
                        dset.add(cur.isoformat())
                        cur -= timedelta(days=1)
            archive_dates_desc = sorted(dset, reverse=True)
            manifest["dates"] = sorted(set(sanitize_dates(list(dset))))
            # 오늘 페이지도 최신 날짜목록으로 다시 렌더(◀ 이전 링크/스와이프/드롭다운 통일)
            daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, archive_dates_desc, site_path)
        except Exception as e2:
            log.warning("[WARN] refresh archive dates after backfill failed: %s", e2)
    except Exception as e:
        log.warning("[WARN] backfill rebuild failed: %s", e)
    # ✅ backfill 후 요약 캐시 저장(백필에서 새로 생성된 요약 반영)
    try:
        save_summary_cache(repo, GH_TOKEN, summary_cache)
    except Exception as e2:
        log.warning("[WARN] save_summary_cache after backfill failed: %s", e2)

    save_search_index(repo, GH_TOKEN, search_idx, ssha)


    # write daily
    daily_path = f"{DOCS_ARCHIVE_DIR}/{report_date}.html"
    _raw_old, sha_old = github_get_file(repo, daily_path, GH_TOKEN, ref="main")
    github_put_file(repo, daily_path, daily_html, GH_TOKEN, f"Add daily brief {report_date}", sha=sha_old, branch="main")

    # write index
    _raw_old2, sha_old2 = github_get_file(repo, DOCS_INDEX_PATH, GH_TOKEN, ref="main")

    github_put_file(repo, DOCS_INDEX_PATH, index_html, GH_TOKEN, f"Update index {report_date}", sha=sha_old2, branch="main")


    # backfill neighbor archive nav (fix: older pages missing "다음 ▶" after new day is generated)
    try:
        backfill_neighbor_archive_nav(repo, GH_TOKEN, report_date, archive_dates_desc, site_path)
    except Exception as e:
        log.warning("[WARN] backfill_neighbor_archive_nav failed: %s", e)

    # ---- manifest & index hygiene ----
    # Build a date list ONLY from existing docs/archive/*.html to avoid 404 navigation
    try:
        avail = _list_archive_dates(repo, GH_TOKEN)
        avail.add(report_date)
        dates_sorted = sorted(set(sanitize_dates(list(avail))))
    except Exception as e:
        log.warning("[WARN] list archives for manifest failed: %s", e)
        dates_sorted = [report_date] if is_iso_date_str(report_date) else []

    # Ensure manifest object exists
    try:
        _m = manifest if isinstance(manifest, dict) else {"dates": []}
    except Exception:
        _m = {"dates": []}
    try:
        _m = _normalize_manifest(_m)
    except Exception:
        if not isinstance(_m, dict):
            _m = {"dates": []}
        _m.setdefault("dates", [])
    _m["dates"] = dates_sorted
    manifest = _m

    # Save manifests (.agri_archive.json + docs/archive_manifest.json)
    try:
        save_archive_manifest(repo, GH_TOKEN, manifest, msha)
    except Exception as e:
        log.warning("[WARN] save_archive_manifest failed: %s", e)
    try:
        save_docs_archive_manifest(repo, GH_TOKEN, dates_sorted)
    except Exception as e:
        log.warning("[WARN] save_docs_archive_manifest failed: %s", e)

    # Re-render index using manifest dates (avoid listing dates without pages)
    try:
        dates_desc_fixed = sorted(set(dates_sorted or []), reverse=True)
        index_html_fixed = render_index_page({"dates": dates_desc_fixed}, site_path)
        _raw_i_fix, sha_i_fix = github_get_file(repo, DOCS_INDEX_PATH, GH_TOKEN, ref="main")
        github_put_file(repo, DOCS_INDEX_PATH, index_html_fixed, GH_TOKEN, f"Update index (fixed) {report_date}", sha=sha_i_fix, branch="main")
    except Exception as e:
        log.warning("[WARN] index re-render after manifest refresh failed: %s", e)

    # Update state (cross-day dedupe history) before Kakao send
    # - 동일 report_date 재실행 시 state/report mismatch가 누적되지 않도록,
    #   해당 날짜 기록을 "최종 by_section 결과"로 매번 재생성한다.
    recent_items2 = None
    try:
        st0 = load_state(repo, GH_TOKEN)
        base_day = end_kst.astimezone(KST).date()
        recent_items2 = rebuild_recent_items_for_report_date(
            st0.get("recent_items", []),
            by_section,
            report_date,
            base_day,
        )
    except Exception:
        recent_items2 = None
    try:
        save_state(repo, GH_TOKEN, end_kst, recent_items=recent_items2)
    except Exception as e:
        log.warning("[WARN] save_state failed: %s", e)

    # Kakao message (핵심2)
    kakao_text = build_kakao_message(report_date, by_section)
    if KAKAO_INCLUDE_LINK_IN_TEXT:
        kakao_text = kakao_text + "\n" + daily_url

    if STRICT_KAKAO_LINK_CHECK:
        parsed = urlparse(daily_url)
        if not parsed.scheme.startswith("http") or not parsed.netloc:
            raise RuntimeError(f"[FATAL] daily_url invalid: {daily_url}")

    daily_url = ensure_absolute_http_url(daily_url)
    log_kakao_link(daily_url)
    try:
        kakao_send_to_me(kakao_text, daily_url)
        _write_kakao_send_status("success")
        log.info("[OK] Kakao message sent. URL=%s", daily_url)
    except Exception as e:
        _write_kakao_send_status(_kakao_send_status_for_exception(e))
        if KAKAO_FAIL_OPEN:
            _log_kakao_fail_open(e)
        else:
            raise



if __name__ == "__main__":
    main()

