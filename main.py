# -*- coding: utf-8 -*-
"""
agri-news-brief main.py (production)

??肄붾뱶 ?묐룞 ?붿빟 (?댁쁺/?ㅽ뻾 ?먮쫫)

- GitHub Actions?먯꽌 KST 湲곗? 留ㅼ씪 ?ㅽ뻾?섎ŉ(?ㅼ?以??섎룞), ?ㅽ뻾 ?덈룄??湲곕낯 24h) ??湲곗궗瑜??섏쭛?⑸땲??
- Naver News Search API濡??뱀뀡/?ㅼ썙?쒕퀎 荑쇰━瑜??앹꽦?섍퀬, ?섏씠吏?ㅼ씠??MAX_PAGES_PER_QUERY)源뚯? ?쒗쉶?섎ŉ 湲곗궗 ?꾨낫瑜?紐⑥쓭?덈떎.
- URL/?몃줎?щ챸 ?뺢퇋?? ?뱀뀡 ???꾩껜 以묐났 ?쒓굅(?ш굔??, UX ?꾪꽣(?ㅽ깘쨌愿묎퀬쨌?쒖쐞/蹂댁씠肄??? ?곸슜 ???먯닔?뷀븯???뱀뀡蹂??곸쐞 湲곗궗留??좎젙?⑸땲??
- OpenAI ?붿빟? 諛곗튂 遺꾪븷 + ?ъ떆??+ 罹먯떆瑜??곸슜??鍮꾩슜/?ㅽ뙣?⑥쓣 以꾩씠怨? 湲곗궗蹂??붿빟???덉젙?곸쑝濡?梨꾩썎?덈떎.
- 寃곌낵濡?HTML 釉뚮━?묒쓣 鍮뚮뱶?섏뿬 docs/archive/YYYY-MM-DD.html 諛?docs/index.html???낅뜲?댄듃?섍퀬, ?꾩뭅?대툕 留곹겕 404瑜?諛⑹??⑸땲??
- ?곹깭/硫뷀?(?? .agri_state.json, manifest ?????덊룷????λ릺???꾨궇 fallback 諛??ъ떎?????쇨??깆쓣 ?좎??⑸땲??
- 移댁뭅?ㅽ넚 硫붿떆吏???뱀뀡蹂??듭떖 2媛?以묒떖?쇰줈 援ъ꽦?섏뿬 ?꾩넚?섎ŉ, ?ㅽ뙣 ???듭뀡) ?꾩껜 ?뚰겕?뚮줈???ㅽ뙣瑜?留됰뒗 fail-open ?숈옉??媛?ν빀?덈떎.

二쇱슂 ENV: NAVER_CLIENT_ID/SECRET, OPENAI_API_KEY/OPENAI_MODEL(諛?MAX_OUTPUT_TOKENS/REASONING_EFFORT), KAKAO_REST_API_KEY/REFRESH_TOKEN, FORCE_RUN_ANYDAY ??
"""

import os
import re

def _strip_swipe_hint_blocks(html: str) -> str:
    """Remove swipe-hint helper blocks from HTML for stable diffs."""
    if not html:
        return html

    if ("swipeHint" not in html) and ("swipe" not in html.lower()):
        return html

    html2 = html
    html2 = re.sub(
        r'(?is)\s*<div[^>]*(?:id|class)=["\']swipeHint[^"\']*["\'][^>]*>.*?</div>\s*',
        '\n',
        html2,
    )
    html2 = re.sub(
        r'(?is)\s*<div[^>]*>.*?swipe.*?(?:date|day|move).*?</div>\s*',
        '\n',
        html2,
    )
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
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import requests
from requests.adapters import HTTPAdapter
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
from observability import flush_metrics, log_event, metric_inc
from orchestrator import OrchestratorContext, OrchestratorHandlers, execute_orchestration
from ranking import sort_key_major_first as _ranking_sort_key_major_first
from retry_utils import exponential_backoff, retry_after_or_backoff
from ux_patch import (
    build_archive_ux_html,
)


# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agri-brief")

# -----------------------------
# Log sanitization (secrets / huge bodies)
# -----------------------------
_SECRET_PATTERNS = [
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
        s = s[:limit] + "??truncated)"
    return s

def _log_http_error(prefix: str, r: requests.Response):
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

def _normalize_manifest(manifest):
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
    out = dict(manifest)
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

def http_session():
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
WINDOW_MIN_HOURS = int(os.getenv("WINDOW_MIN_HOURS", "72"))  # 理쒖냼 ?꾨낫 ?섏쭛 ?덈룄???쒓컙)
CROSSDAY_DEDUPE_DAYS = int(os.getenv("CROSSDAY_DEDUPE_DAYS", "7"))  # 理쒓렐 N??URL/?ш굔??以묐났 諛⑹?
CROSSDAY_DEDUPE_ENABLED_ENV = (os.getenv("CROSSDAY_DEDUPE_ENABLED", "true").strip().lower() == "true")

# 理쒓렐 ?덉뒪?좊━(?щ줈?ㅻ뜲??以묐났 諛⑹?) - main()?먯꽌 state瑜??쎌뼱 梨꾩?
CROSSDAY_DEDUPE_ENABLED = False
RECENT_HISTORY_CANON: set[str] = set()
RECENT_HISTORY_NORM: set[str] = set()

MAX_PER_SECTION = int(os.getenv("MAX_PER_SECTION", os.getenv("MAX_ARTICLES_PER_SECTION", "5")))
MAX_PER_SECTION = max(1, min(MAX_PER_SECTION, int(os.getenv("MAX_PER_SECTION_CAP", "20"))))

# 理쒖냼 湲곗궗 ???뱀뀡蹂?
MIN_PER_SECTION = int(os.getenv("MIN_PER_SECTION", os.getenv("MIN_ARTICLES_PER_SECTION", "0")) or 0)
MIN_PER_SECTION = max(0, min(MIN_PER_SECTION, MAX_PER_SECTION))

# 湲곗〈 ENV(MAX_PAGES_PER_QUERY)??"?곹븳(cap)"?쇰줈留??좎??쒕떎.
# - 湲곕낯 ?섏쭛? 1?섏씠吏 ?좎?
# - ?꾩슂???뚮쭔 異붽? ?섏씠吏(2..N)瑜?議곌굔遺濡??몄텧
MAX_PAGES_PER_QUERY = int((os.getenv("MAX_PAGES_PER_QUERY", "1") or "1").strip() or 1)
MAX_PAGES_PER_QUERY = max(1, min(MAX_PAGES_PER_QUERY, int(os.getenv("MAX_PAGES_PER_QUERY_CAP", "10"))))

# --- Conditional pagination safety (BASE=1 page, only use extra pages when needed)
# ??daily_v7.yml怨??뺥빀:
# - MAX_PAGES_PER_QUERY???뚰겕?뚮줈???댁쁺?먯꽌 ?됰꼮???≪븘???섍퀬(?? 4),
#   蹂?肄붾뱶???대? '理쒕? ?덉슜移?濡쒕쭔 ?ъ슜?쒕떎.
# - 湲곕낯? 1?섏씠吏, ?뱀뀡蹂??꾨낫 ???遺議깊븷 ?뚮쭔 2?섏씠吏(start=51) ?깆쓣 異붽? ?몄텧?쒕떎.
COND_PAGING_BASE_PAGES = int(os.getenv("COND_PAGING_BASE_PAGES", "1") or 1)
COND_PAGING_BASE_PAGES = max(1, min(COND_PAGING_BASE_PAGES, MAX_PAGES_PER_QUERY))

# 湲곕낯媛믪? 2?섏씠吏源뚯?留?=1??) 蹂닿컯?섎릺,
# ?꾩슂 ??ENV濡??섎┫ ???덇쾶 ?쒕떎(?곹븳? MAX_PAGES_PER_QUERY).
COND_PAGING_MAX_PAGES = int(os.getenv("COND_PAGING_MAX_PAGES", "2") or 2)
COND_PAGING_MAX_PAGES = max(COND_PAGING_BASE_PAGES, min(COND_PAGING_MAX_PAGES, MAX_PAGES_PER_QUERY))
COND_PAGING_ENABLED = (COND_PAGING_MAX_PAGES > COND_PAGING_BASE_PAGES)

# ?뱀뀡??'異붽? ?몄텧'??李몄뿬??荑쇰━ ???곹븳(湲곕낯: MAX_PER_SECTION+1)
_default_qcap = max(3, min(10, MAX_PER_SECTION + 1))
COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION = int(os.getenv("COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION", str(_default_qcap)) or _default_qcap)
COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION = max(0, min(COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION, 25))
# pool 遺議???1?섏씠吏 異붽? ?섏쭛???ъ슜??'蹂닿컯 荑쇰━' ???곹븳(湲곕낯: 6)
_default_fbqcap = max(0, min(10, MAX_PER_SECTION + 1))
COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION = int(os.getenv("COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION", str(min(6, _default_fbqcap))) or 6)
COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION = max(0, min(COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION, 20))

# pest ?뱀뀡? ?ㅽ뻾??蹂묓빐異?湲곗궗瑜??볦튂吏 ?딄린 ?꾪빐 蹂닿컯 荑쇰━瑜???긽 蹂묓빀?쒕떎(?섎뱶肄붾뵫 URL ?꾨떂)
PEST_ALWAYS_ON_RECALL_QUERIES = [
    "怨쇱닔?붿긽蹂?, "怨쇱닔?붿긽蹂?諛⑹젣", "怨쇱닔?붿긽蹂??쎌젣",
    "?좊쭏?좊퓭?섎갑", "?좊쭏?좊퓭?섎갑 諛⑹젣", "蹂묓빐異??덉같",
]
# pest??page1 寃곌낵媛 異⑸텇??蹂댁뿬???ㅽ뻾??湲곗궗媛 page2???⑥뼱?덈뒗 寃쎌슦媛 ??븘
# always-on recall 荑쇰━???쒗빐 理쒖냼 page2瑜??좎젣?곸쑝濡?1??蹂닿컯?쒕떎.
PEST_ALWAYS_ON_PAGE2_ENABLED = os.getenv("PEST_ALWAYS_ON_PAGE2_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")
PEST_ALWAYS_ON_PAGE2_QUERY_CAP = int(os.getenv("PEST_ALWAYS_ON_PAGE2_QUERY_CAP", "3") or 3)
PEST_ALWAYS_ON_PAGE2_QUERY_CAP = max(0, min(PEST_ALWAYS_ON_PAGE2_QUERY_CAP, 10))
# news API 誘몄깋??吏?곗뿉 ?鍮꾪빐 pest??web 寃??webkr)???뚮웾 蹂닿컯?쒕떎.
PEST_WEB_RECALL_ENABLED = os.getenv("PEST_WEB_RECALL_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")
PEST_WEB_RECALL_QUERY_CAP = int(os.getenv("PEST_WEB_RECALL_QUERY_CAP", "2") or 2)
PEST_WEB_RECALL_QUERY_CAP = max(0, min(PEST_WEB_RECALL_QUERY_CAP, 8))


# ?꾩껜 ?곗뿉??異붽? ?몄텧 ?덉궛(湲곕낯: qcap*2)
_default_budget = max(6, min(30, COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION * 2))
COND_PAGING_EXTRA_CALL_BUDGET_TOTAL = int(os.getenv("COND_PAGING_EXTRA_CALL_BUDGET_TOTAL", str(_default_budget)) or _default_budget)
COND_PAGING_EXTRA_CALL_BUDGET_TOTAL = max(0, min(COND_PAGING_EXTRA_CALL_BUDGET_TOTAL, 80))

# ?꾨낫媛 異⑸텇??留롮????? 50媛?) ?좏깮???곸? ?좎? '?덉쭏????? ????媛?μ꽦???щ?濡?
# 異붽? ?섏씠吏瑜?臾댁쓽誘명븯寃??몄텧?섏? ?딅룄濡??곹븳???붾떎.
_default_trigger_cap = max(25, min(120, MAX_PER_SECTION * 8))
COND_PAGING_TRIGGER_CANDIDATE_CAP = int(os.getenv("COND_PAGING_TRIGGER_CANDIDATE_CAP", str(_default_trigger_cap)) or _default_trigger_cap)
COND_PAGING_TRIGGER_CANDIDATE_CAP = max(5, min(COND_PAGING_TRIGGER_CANDIDATE_CAP, 250))


# --- Recall backfill (broad-query + diversity guardrails)
# 紐⑹쟻: '荑쇰━ ?ㅺ퀎'?먮쭔 ?섏〈???꾨낫媛 ?꾨씫?섎뒗 臾몄젣瑜?以꾩씠湲??꾪빐,
#       ?꾨낫 ???遺議깊븷 ???먮뒗 ?뱀젙 ?좏샇媛 0???? ?뚮웾??愿묒뿭 荑쇰━瑜?異붽?濡??섏쭛?쒕떎.
#       (?ㅼ퐫?대쭅/?좎젙 濡쒖쭅? 洹몃?濡??먭퀬, ?꾨낫(Recall)留??덉젙??
RECALL_BACKFILL_ENABLED = os.getenv("RECALL_BACKFILL_ENABLED", "1").strip().lower() in ("1","true","yes","y")
RECALL_QUERY_CAP_PER_SECTION = int(os.getenv("RECALL_QUERY_CAP_PER_SECTION", "6") or 6)
RECALL_QUERY_CAP_PER_SECTION = max(0, min(RECALL_QUERY_CAP_PER_SECTION, 20))

# 1?섏씠吏 寃곌낵媛 苑?李?=50嫄? 荑쇰━??2?섏씠吏???좎쓽誘명븳 '?덈룄???? 湲곗궗媛 ?⑥븘 ?덉쓣 媛?μ꽦???믩떎.
# ?꾨낫 ???遺議깊븷 ?뚮쭔, ?곸쐞 N媛?荑쇰━?????page2瑜??곗꽑?곸쑝濡??쒕룄?쒕떎.
RECALL_HIGH_VOLUME_PAGE2_QUERIES = int(os.getenv("RECALL_HIGH_VOLUME_PAGE2_QUERIES", "2") or 2)
RECALL_HIGH_VOLUME_PAGE2_QUERIES = max(0, min(RECALL_HIGH_VOLUME_PAGE2_QUERIES, 8))

# ?꾩뿭 ?뱀뀡 ?щ텇瑜??뱀뀡蹂꾨줈 ?ъ뒪肄붿뼱留???best section?쇰줈 ?대룞)
GLOBAL_SECTION_REASSIGN_ENABLED = os.getenv("GLOBAL_SECTION_REASSIGN_ENABLED", "1").strip().lower() in ("1","true","yes","y")
GLOBAL_SECTION_REASSIGN_MIN_GAIN = float(os.getenv("GLOBAL_SECTION_REASSIGN_MIN_GAIN", "0.8") or 0.8)
GLOBAL_SECTION_REASSIGN_MIN_GAIN = max(0.0, min(GLOBAL_SECTION_REASSIGN_MIN_GAIN, 5.0))

# 理쒓렐 ?ㅽ뿕??蹂댁젙(荑쇰━-湲곗궗 ?뺥빀??寃뚯씠??/ ?ㅼ썙??媛뺣룄 異붽? 蹂댁젙)?
# 湲곕낯媛믪쓣 OFF濡??먭퀬, ?댁쁺?먯꽌 ?꾩슂 ??ENV濡?耳쒖꽌 ?먯쭊 ?곸슜?쒕떎.
QUERY_ARTICLE_MATCH_GATE_ENABLED = os.getenv("QUERY_ARTICLE_MATCH_GATE_ENABLED", "0").strip().lower() in ("1", "true", "yes", "y")
SCORING_KEYWORD_STRENGTH_BOOST_ENABLED = os.getenv("SCORING_KEYWORD_STRENGTH_BOOST_ENABLED", "0").strip().lower() in ("1", "true", "yes", "y")
SCORING_TITLE_SIGNAL_BONUS_ENABLED = os.getenv("SCORING_TITLE_SIGNAL_BONUS_ENABLED", "1").strip().lower() in ("1", "true", "yes", "y")

# ?뱀뀡 諛곗튂 ?덉젙?? 理쒖쥌 ?좊컻/?꾩뿭 ?щ텇瑜???section-fit ?좏샇瑜??④퍡 蹂몃떎.
SECTION_FIT_MIN_FOR_TOP = float(os.getenv("SECTION_FIT_MIN_FOR_TOP", "0.8") or 0.8)
SECTION_FIT_MIN_FOR_TOP = max(0.0, min(SECTION_FIT_MIN_FOR_TOP, 5.0))
SECTION_REASSIGN_FIT_GUARD = float(os.getenv("SECTION_REASSIGN_FIT_GUARD", "0.8") or 0.8)
SECTION_REASSIGN_FIT_GUARD = max(0.0, min(SECTION_REASSIGN_FIT_GUARD, 5.0))
# ?뱀뀡 ?щ같移?蹂닿컯: section-fit ?곗쐞媛 異⑸텇???щ㈃ score 誘몄꽭?댁꽭?щ룄 dist/policy濡??대룞 ?덉슜
SECTION_REASSIGN_STRONG_FIT_DELTA = float(os.getenv("SECTION_REASSIGN_STRONG_FIT_DELTA", "1.2") or 1.2)
SECTION_REASSIGN_STRONG_FIT_DELTA = max(0.0, min(SECTION_REASSIGN_STRONG_FIT_DELTA, 5.0))
SECTION_REASSIGN_STRONG_FIT_SCORE_TOL = float(os.getenv("SECTION_REASSIGN_STRONG_FIT_SCORE_TOL", "0.8") or 0.8)
SECTION_REASSIGN_STRONG_FIT_SCORE_TOL = max(0.0, min(SECTION_REASSIGN_STRONG_FIT_SCORE_TOL, 4.0))

# ?ㅼ뼇??coverage) 蹂닿컯: 以묐났? ?꾨땲吏留?'鍮꾩듂??湲곗궗'媛 ?곗냽?쇰줈 ?щ씪?ㅻ뒗 寃껋쓣 ?꾪솕(MMR).
MMR_DIVERSITY_ENABLED = os.getenv("MMR_DIVERSITY_ENABLED", "1").strip().lower() in ("1","true","yes","y")
MMR_DIVERSITY_LAMBDA = float(os.getenv("MMR_DIVERSITY_LAMBDA", "1.15") or 1.15)
MMR_DIVERSITY_LAMBDA = max(0.0, min(MMR_DIVERSITY_LAMBDA, 3.0))
MMR_DIVERSITY_MIN_POOL = int(os.getenv("MMR_DIVERSITY_MIN_POOL", "12") or 12)
MMR_DIVERSITY_MIN_POOL = max(0, min(MMR_DIVERSITY_MIN_POOL, 80))

_COND_PAGING_LOCK = threading.Lock()
_COND_PAGING_EXTRA_CALLS_USED = 0

def _cond_paging_take_budget(n: int = 1) -> bool:
    """Return True if we can spend extra-page call budget (thread-safe)."""
    global _COND_PAGING_EXTRA_CALLS_USED
    if not COND_PAGING_ENABLED:
        return False
    n = max(1, int(n or 1))
    with _COND_PAGING_LOCK:
        if _COND_PAGING_EXTRA_CALLS_USED + n > COND_PAGING_EXTRA_CALL_BUDGET_TOTAL:
            return False
        _COND_PAGING_EXTRA_CALLS_USED += n
        return True

DEBUG_SELECTION = os.getenv("DEBUG_SELECTION", "0") == "1"
DEBUG_REPORT = os.getenv("DEBUG_REPORT", "0") == "1"
DEBUG_REPORT_MAX_CANDIDATES = int(os.getenv("DEBUG_REPORT_MAX_CANDIDATES", "25"))
DEBUG_REPORT_MAX_REJECTS = int(os.getenv("DEBUG_REPORT_MAX_REJECTS", "120"))
DEBUG_REPORT_WRITE_JSON = (os.getenv("DEBUG_REPORT_WRITE_JSON", "1") == "1") if DEBUG_REPORT else False
REPORT_DATE_OVERRIDE = os.getenv("REPORT_DATE_OVERRIDE", "").strip()

# Debug report data (embedded into HTML when DEBUG_REPORT=1)
_DEBUG_LOCK = threading.Lock()
DEBUG_DATA = {
    "generated_at_kst": None,
    "build_tag": os.getenv("BUILD_TAG", ""),
    "filter_rejects": [],  # list[{section, reason, press, domain, title, url}]
    "sections": {},        # section_key -> {threshold, core_min, total_candidates, total_selected, top: [...]}
    "collections": {},     # section_key -> {queries, hits, paging, recall, ...}
}

def dbg_add_filter_reject(section: str, reason: str, title: str, url: str, domain: str, press: str):
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
        }
        with _DEBUG_LOCK:
            if len(DEBUG_DATA["filter_rejects"]) < DEBUG_REPORT_MAX_REJECTS:
                DEBUG_DATA["filter_rejects"].append(item)
    except Exception:
        pass


def dbg_set_section(section: str, payload: dict):
    if not DEBUG_REPORT:
        return
    try:
        with _DEBUG_LOCK:
            DEBUG_DATA["sections"][section] = payload
    except Exception:
        pass


def dbg_set_collection(section: str, payload: dict):
    """?섏쭛 ?④퀎 硫뷀?(荑쇰━/?섏씠吏/?덊듃/由ъ퐳)瑜??붾쾭洹?由ы룷?몄뿉 ???"""
    if not DEBUG_REPORT:
        return
    try:
        with _DEBUG_LOCK:
            DEBUG_DATA["collections"][section] = payload
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

        def _run(cmd):
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

# Keep debug report in sync
try:
    DEBUG_DATA["build_tag"] = BUILD_TAG
except Exception:
    pass
# Optional: extra RSS sources (comma-separated). If empty, RSS fetching is skipped.
WHITELIST_RSS_URLS = [u.strip() for u in os.getenv("WHITELIST_RSS_URLS", "").split(",") if u.strip()]





DEFAULT_REPO = (os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY") or "").strip()
GH_TOKEN = (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

# -----------------------------
# Naver rate limit / retry
# -----------------------------
NAVER_MIN_INTERVAL_SEC = float(os.getenv("NAVER_MIN_INTERVAL_SEC", "0.35"))  # 理쒖냼 ?몄텧 媛꾧꺽(珥?
NAVER_MAX_RETRIES = int(os.getenv("NAVER_MAX_RETRIES", "6"))
NAVER_BACKOFF_MAX_SEC = float(os.getenv("NAVER_BACKOFF_MAX_SEC", "20"))
NAVER_MAX_WORKERS = int(os.getenv("NAVER_MAX_WORKERS", "2"))  # ?숈떆 ?붿껌 ???띾룄?쒗븳 ?뚰뵾??

_NAVER_LOCK = threading.Lock()
_NAVER_LAST_CALL = 0.0

def _naver_throttle():
    """?꾩뿭 理쒖냼 媛꾧꺽??蹂댁옣(硫?곗뒪?덈뱶 ?덉쟾).
    ?좑툘 蹂묐ぉ 諛⑹?: sleep? ??諛뽰뿉???섑뻾.
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
KAKAO_INCLUDE_LINK_IN_TEXT = os.getenv("KAKAO_INCLUDE_LINK_IN_TEXT", "false").strip().lower() in ("1", "true", "yes")
KAKAO_FAIL_OPEN = os.getenv("KAKAO_FAIL_OPEN", "true").strip().lower() in ("1", "true", "yes", "y")
MAINTENANCE_SEND_KAKAO = os.getenv("MAINTENANCE_SEND_KAKAO", "false").strip().lower() in ("1","true","yes","y")


FORCE_REPORT_DATE = os.getenv("FORCE_REPORT_DATE", "").strip()  # YYYY-MM-DD
FORCE_RUN_ANYDAY = os.getenv("FORCE_RUN_ANYDAY", "false").strip().lower() in ("1", "true", "yes")
FORCE_END_NOW = os.getenv("FORCE_END_NOW", "false").strip().lower() in ("1", "true", "yes")
STRICT_KAKAO_LINK_CHECK = os.getenv("STRICT_KAKAO_LINK_CHECK", "false").strip().lower() in ("1", "true", "yes")

# Backfill rebuild (理쒓렐 N???꾩뭅?대툕瑜??ъ깮?깊븯???꾪꽣/?ㅼ퐫??媛쒖꽑??怨쇨굅 ?섏씠吏?먮룄 諛섏쁺)
# - 湲곕낯 OFF (0). ?꾩슂????workflow env濡?耳쒖꽌 ?ъ슜.
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


# UX patch (怨쇨굅 ?꾩뭅?대툕??UI/UX ?낅뜲?댄듃瑜?'?⑥튂'濡?諛섏쁺: ?ㅼ??댄봽/濡쒕뵫/?ㅽ떚??nav ??
# - 湲곕낯: 理쒓렐 30?쇰쭔 ?⑥튂
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
    "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈씫媛", "寃쎈ℓ", "泥?낵", "?곗?", "異쒗븯", "臾쇰웾", "諛섏엯",
    "?곗??좏넻", "APC", "?곗??좏넻?쇳꽣", "?좊퀎", "CA???, "??κ퀬", "??λ웾",
    "?쒖꽭", "?꾨ℓ媛寃?, "?뚮ℓ媛寃?, "媛寃?, "?섍툒", "?섍툒?숉뼢", "?묓솴", "?앹궛??, "?щ같", "?섑솗", "硫댁쟻",
    "?띾┝異뺤궛?앺뭹遺", "?띿떇?덈?", "aT", "?쒓뎅?띿닔?곗떇?덉쑀?듦났??, "?띻???, "援?┰?띿궛臾쇳뭹吏덇?由ъ썝",
    "寃??, "?좊떦愿??, "?섏엯", "?섏텧", "愿??, "?듦?", "?먯궛吏", "遺?뺤쑀??, "?⑤씪???꾨ℓ?쒖옣",
    "鍮꾩텞誘?, "?뺣?", "?梨?, "吏??, "?좎씤吏??, "?깆닔??,
    "蹂묓빐異?, "諛⑹젣", "?쎌젣", "?댄룷", "?덉같", "怨쇱닔?붿긽蹂?, "?꾩?蹂?, "?숉빐", "?됲빐", "?붾룞",
]

OFFTOPIC_HINTS = [
    "諛곗슦", "?꾩씠??, "?쒕씪留?, "?곹솕", "?덈뒫", "肄섏꽌??, "??, "裕ㅼ쭅",
    "援?쉶", "珥앹꽑", "寃李?, "?ы뙋", "?꾪빑", "?뺣떦",
    "肄붿뒪??, "肄붿뒪??, "二쇨?", "湲됰벑", "湲됰씫", "鍮꾪듃肄붿씤", "?섏쑉",
    "?ы뻾", "愿愿?, "?명뀛", "由ъ“??, "?덉뒪?좊옉", "???, "?대?", "?댁뼇",
]

# 怨듯넻 ?쒖쇅(愿묎퀬/援ъ씤/遺?숈궛/?꾨컯 ?? - text??lower() ?곹깭
BAN_KWS = [
    # 援ъ씤/梨꾩슜
    "援ъ씤", "梨꾩슜", "紐⑥쭛怨듦퀬", "?꾨Ⅴ諛붿씠??, "?뚮컮", "?명꽩",
    # 遺?숈궛
    "遺?숈궛", "遺꾩뼇", "?ㅽ뵾?ㅽ뀛", "泥?빟", "?꾩꽭", "?붿꽭",
    # 湲덉쑖/?꾨컯 ?ㅽ뙵
    "?異?, "蹂댄뿕", "移댁???, "諛붿뭅??, "?좏넗", "?꾨컯",
    # 湲고? ?ㅽ뙵??
    "?ㅽ뙵",
]



# -----------------------------
# Additional hard filters / controls (2026-02 hotfix)
# -----------------------------
# ?ㅽ뵾?덉뼵/?ъ꽕/移쇰읆 ?깆? 釉뚮━????곸뿉???쒖쇅(?먯삁?섍툒 ?ㅻТ ?좏샇媛 ?쏀븯怨??몄씠利덇? ??
OPINION_BAN_TERMS = [
    "[?ъ꽕]", "?ъ꽕", "移쇰읆", "?ㅽ뵾?덉뼵", "湲곌퀬", "?낆옄湲곌퀬", "湲곗옄?섏꺽",
    "?쇨린", "?띾쭑?쇨린", "?섑븘", "?먯꽭??, "?곗옱", "湲고뻾", 
    "留뚰룊", "?곗뒪?ъ뭡??, "?≪꽕?섏꽕", "湲곗옄???쒖꽑", "?쇰떒",
]

# 吏???숈젙/湲곕?/?ν븰/諛쒖쟾湲곌툑 ??而ㅻ??덊떚??湲곗궗 ?쒖쇅???뱁엳 ?뗢뿃?랁삊 + 湲곌툑?꾨떖瑜??ㅽ깘 諛⑹?)
COMMUNITY_DONATION_TERMS = [
    "諛쒖쟾湲곌툑", "援먯쑁諛쒖쟾湲곌툑", "?ν븰湲?, "?ν븰", "?깃툑", "湲고긽", "?꾩썝湲?,
    "湲곕?湲?, "?깊뭹", "?湲곕?", "?섎닎", "遊됱궗?쒕룞", "?꾩썝", "湲곕?",
]

# ?먯삁?섍툒怨?臾닿????곗뾽/湲덉쑖/諛붿씠???ㅽ깘 諛⑹?(?띿뾽 留λ씫???쏀븯硫?而?
HARD_OFFTOPIC_TERMS = [
    "諛섎룄泥?, "諛고꽣由?, "2李⑥쟾吏", "肄붿뒪??, "肄붿뒪??, "二쇱떇", "梨꾧텒", "媛?곸옄??, "鍮꾪듃肄붿씤",
    "遺?숈궛", "湲덈━", "?섏쑉", "利앹떆", "ipo", "?곸옣", "?몄닔?⑸퀝", "m&a",
    "諛붿씠??, "?꾩긽", "?섏빟", "?쒖빟", "?명룷", "??븫", "?좎쟾??, "?뚮옯??,
    "?섏궗怨쇳븰",
    "?섏궗怨쇳븰??,
    "?섏궗怨쇳븰??,
    "?섏궗怨듯븰",
    "?섍낵??,
    "?섍낵?숈썝",
    "?꾧린李?,
    "?먮룞李?,
    "罹먯쬁",
    "?뚯뒳??,
    "異⑹쟾",
    "?꾩꽦李?,
]


# ?꾨젰/?먮꼫吏/?좏떥由ы떚(?꾨젰 ?꾨ℓ?쒖옣 ?? ?숈쓬?댁쓽???ㅽ깘 諛⑹???而⑦뀓?ㅽ듃
ENERGY_CONTEXT_TERMS = [
    "?꾨젰", "?꾨젰留?, "?꾨젰怨꾪넻", "?꾨젰怨꾪넻", "諛쒖쟾", "諛쒖쟾??, "諛쒖쟾??, "?≪쟾", "諛곗쟾",
    "?꾧린?붽툑", "?붽툑", "?뺤궛", "?좏떥由ы떚", "?먮꼫吏", "媛??, "?섏냼", "?꾨젰?쒖옣", "?꾨젰 ?꾨ℓ?쒖옣",
    "?꾨ℓ?쒖옣 嫄곕옒", "?꾨젰 ?뚮ℓ?쒖옣", "怨꾪넻", "怨꾪넻?댁쁺", "?섏슂諛섏쓳", "?꾨젰嫄곕옒??, "kpx",
    "?ν넗?쇱뒪", "octopus", "?щ씪耳?, "kraken", "?좏떥由ы떚 os", "?댁쁺泥댁젣(os)",
]

# '?꾨ℓ?쒖옣'??鍮꾨냽?곕Ъ(?꾨젰/?먮꼫吏/湲덉쑖 ?? 湲곗궗?먯꽌 ?곗씠??寃쎌슦瑜?嫄몃윭?닿린 ?꾪븳 ?붿뒪?곕퉬洹쒖뿉?댄꽣
# - text??lower()濡?泥섎━?섎?濡? ?ш린???뚮Ц???쒓? 洹몃?濡??ъ슜
AGRI_WHOLESALE_DISAMBIGUATORS = [
    "?띿궛臾?, "?띿닔?곕Ъ", "泥?낵", "媛?쎌떆??, "怨듯뙋??, "?꾨ℓ?쒖옣踰뺤씤", "寃쎈씫", "寃쎈씫媛",
    "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "諛섏엯", "寃쎈ℓ", "?곗?", "apc", "?곗??좏넻", "?곗??좏넻?쇳꽣",
    "?랁삊", "?먯삁?랁삊", "怨쇱닔?랁삊", "泥?낵臾?,
]

# 異뺤궛臾??쒖슦/?쇱?怨좉린/怨꾨? ?? ?⑤룆 ?댁뒋???먯삁 釉뚮━?묒뿉???쒖쇅(?꾩쟾 諛곗젣)
# - '?띿텞?곕Ъ/?띾┝異뺤궛?앺뭹遺' 媛숈? 以묐┰ ?쒗쁽留뚯쑝濡쒕뒗 ?쒖쇅?섏? ?딅룄濡? 蹂댁닔?곸쑝濡??먮떒?쒕떎.
LIVESTOCK_STRICT_TERMS = [
    "異뺤궛臾?, "異뺤궛", "媛異?, "?꾩텞", "?꾧퀎", "?щ즺", "異뺤궛??, "?숇냽", "?묐룉", "?묎퀎",
    "?쒖슦", "?쒕룉", "?곗쑁", "?덉쑁", "?뚭퀬湲?, "?쇱?怨좉린", "??퀬湲?, "怨꾨?", "?ш?", "?곗쑀", "移섏쫰",
    "?뽰냼", "??, "?쇱?", "??, "?ㅻ━",
]
# ?띿텞???뺤콉/?됱젙 ?쇰컲 ?쒗쁽(?ㅽ깘 諛⑹? 紐⑹쟻) ???쒓굅 ???먮떒???ъ슜
LIVESTOCK_NEUTRAL_PHRASES = [
    "?띿텞?곕Ъ", "?띿텞?섏궛臾?, "?띾┝異뺤궛?앺뭹遺", "?띾┝異뺤궛", "?띿텞??, "?띿텞?섏궛",
]
# ?먯삁/?띿궛臾?鍮꾩텞?? 媛뺤떊??異뺤궛 ?⑤룆?몄? ?먮떒??
HORTI_CORE_MARKERS = [
    "?먯삁", "怨쇱닔", "?뷀쎕", "?덊솕", "怨쇱씪", "梨꾩냼", "泥?낵", "?쒖꽕梨꾩냼", "?섏슦??, "鍮꾧?由?,
    "?ш낵", "諛?, "媛먭랠", "?щ룄", "?멸린", "怨좎텛", "?ㅼ씠", "?좊쭏??, "?뚰봽由ъ뭅", "?곸텛",
    "?④컧", "怨띔컧", "李몃떎??, "?ㅼ쐞", "?ㅼ씤癒몄뒪罹?, "留뚭컧", "?쒕씪遊?, "?덈뱶??, "泥쒗삙??,
    "?먯“湲?, "?먯삁?먯“湲?, "怨쇱닔?먯“湲?, "?뷀쎕", "援?솕", "?λ?",
]

# ?섏궛臾??앹꽑/?묒떇) ?⑤룆 ?댁뒋???먯삁 釉뚮━?묒뿉???쒖쇅
# - ?? '?띿닔?곕Ъ' 媛숈? 以묐┰ ?쒗쁽 ?뚮Ц??怨쇰룄 李⑤떒?섏? ?딅룄濡??꾩슜 以묐┰ ?쒗쁽???쒓굅 ???먮떒?쒕떎.
FISHERY_STRICT_TERMS = [
    "?섏궛", "?섏궛臾?, "?댁뾽", "?묒떇", "?댄쉷", "?섑삊", "?쒖뼱", "?좎뼱", "?대쪟", "?섏궛?쒖옣",
    "?앹꽑", "?댁꽑", "?먯뼇", "?곌렐??, "?섏궛??, "?댁궛臾?, "?섏궛媛怨?,
    "?λ룘", "媛덉튂", "怨좊벑??, "?ㅼ쭠??, "紐낇깭", "?寃?, "李몄튂", "愿묒뼱", "?곕윮", "?꾨났", "?댁궪",
]
FISHERY_NEUTRAL_PHRASES = [
    "?띿닔?곕Ъ", "?띿텞?섏궛臾?, "?띿닔?곗떇??,
]

# 湲덉쑖/?곗뾽 ?쇰컲 湲곗궗(?랁삊???NH?ъ옄/二쇨?/?ㅼ쟻 ?? ?ㅽ깘 李⑤떒??
FINANCE_STRICT_TERMS = [
    "?랁삊???, "nh?ъ옄", "nh ?ъ옄", "利앷텒", "???, "蹂댄뿕", "移대뱶", "罹먰뵾??,
    "二쇨?", "諛곕떦", "諛곕떦湲?, "?ㅼ쟻", "留ㅼ텧", "?곸뾽?댁씡", "?쒖씠??, "二쇱＜", "?곸옣",
    "ipo", "怨듬え", "梨꾧텒", "湲덈━", "?섏쑉", "遺?숈궛", "肄붿뒪??, "肄붿뒪??,
]
# ?꾩옱 愿?щ룄媛 ??? ?덈ぉ(???놁쓣 ?뚮쭔 ?섎떒???⑤룄濡?媛뺢컧??
EXCLUDED_ITEMS = ["留덈뒛", "?묓뙆"]
GLOBAL_RETAIL_PROTEST_HINTS = [
    "target", "?源?, "walmart", "?붾쭏??, "costco", "肄붿뒪?몄퐫",
    "starbucks", "?ㅽ?踰낆뒪", "boycott", "蹂댁씠肄?, "?쒖쐞", "protest",
    "留ㅼ옣", "retail", "?뚮ℓ", "?꾩뿭",
]

KOREA_CONTEXT_HINTS = [
    "援?궡", "?쒓뎅", "?곕━?섎씪", "?랁삊", "吏?먯껜", "援?, "??, "??, "?띻?", "?곗?", "媛?쎌떆??,
    "?띿떇?덈?", "aT", "?띻???, "??쒕?援?, "??, "紐낆젅",
]

WHOLESALE_MARKET_TERMS = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯", "以묐룄留?]


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
    "?띿텞?섏궛臾?, "?띿텞?곕Ъ", "?깆닔??, "?좎씤吏??, "?좊떦愿??, "寃??,
    "?섍툒", "媛寃?, "怨쇱씪", "鍮꾩텞誘?, "?먯궛吏", "?뺤콉", "?梨?, "釉뚮━??, "蹂대룄?먮즺"
]


# -----------------------------
# Sections
# -----------------------------
SECTIONS = [
    {
        "key": "supply",
        "title": "?덈ぉ 諛??섍툒 ?숉뼢",
        "color": "#0f766e",
        "queries": [
            "?ш낵 ?섍툒",
            "?ш낵 媛寃?,
            "?ш낵 ?묓솴",
            "?ш낵 ???,
            "?ш낵 異쒗븯",
            "諛?怨쇱씪 ?섍툒",
            "諛?怨쇱씪 媛寃?,
            "諛?怨쇱씪 ?묓솴",
            "諛?怨쇱씪 ???,
            "諛?怨쇱씪 異쒗븯",
            "媛먭랠 ?섍툒",
            "媛먭랠 媛寃?,
            "媛먭랠 ?묓솴",
            "留뚭컧瑜?異쒗븯",
            "?쒕씪遊?異쒗븯",
            "?덈뱶??異쒗븯",
            "泥쒗삙??異쒗븯",
            "?щ룄 ?섍툒",
            "?щ룄 媛寃?,
            "?щ룄 ?묓솴",
            "?ㅼ씤癒몄뒪罹??섍툒",
            "?ㅼ씤癒몄뒪罹?媛寃?,
            "?ㅼ씤癒몄뒪罹??묓솴",
            "?④컧 ?섍툒",
            "?④컧 媛寃?,
            "?④컧 ?묓솴",
            "怨띔컧 ?섍툒",
            "?レ?媛??묓솴",
            "?ㅼ쐞 ?섍툒",
            "?ㅼ쐞 媛寃?,
            "?좎옄 ?섍툒",
            "?좎옄 媛寃?,
            "?뚮갇 ?섍툒",
            "?뚮갇 媛寃?,
            "?먮몢 ?섍툒",
            "?먮몢 媛寃?,
            "蹂듭댂???섍툒",
            "蹂듭댂??媛寃?,
            "留ㅼ떎 ?섍툒",
            "留ㅼ떎 媛寃?,
            "?멸린 ?섍툒",
            "?멸린 媛寃?,
            "?멸린 ?묓솴",
            "?뚰봽由ъ뭅 ?섍툒",
            "?뚰봽由ъ뭅 媛寃?,
            "?뚰봽由ъ뭅 ?섏텧",
            "李몄쇅 ?섍툒",
            "李몄쇅 媛寃?,
            "?ㅼ씠 ?섍툒",
            "?ㅼ씠 媛寃?,
            "?ㅼ씠 ?묓솴",
            "?뗪퀬異??섍툒",
            "?뗪퀬異?媛寃?,
            "?좊쭏???섍툒",
            "?좊쭏??媛寃?,
            "?좊쭏???묓솴",
            "諛⑹슱?좊쭏??媛寃?,
            "?異붾갑?명넗留덊넗 媛寃?,
            "?섎컯 ?섍툒",
            "?섎컯 ?꾨ℓ媛寃?,
            "?섎컯 ?묓솴",
            "?몃컯 媛寃?,
            "?좏샇諛??섍툒",
            "?좏샇諛?媛寃?,
            "?⑦샇諛?媛寃?,
            "伊ы궎??媛寃?,
            "?쇰쭩 ?섍툒",
            "?쇰쭩 媛寃?,
            "硫쒕줎 異쒗븯",
            "硫쒕줎 ?꾨ℓ媛寃?,
            "硫쒕줎 ?묓솴",
            "硫쒕줎 ?щ같",
            "癒몄뒪?щ찞濡?異쒗븯",
            "癒몄뒪?щ찞濡??꾨ℓ媛寃?,
            "怨좎텛 ?묓솴",
            "?뷀쎕 媛寃?,
            "?덊솕 媛寃?,
            "苑??뚮퉬",
            "?뷀쎕 ?섍툒",
            "?뷀쎕?먯“湲?,
            "苑껊떎諛??좊Ъ",
            "苑껊떎諛??좊Ъ ?몃젋??,
            "苑껊떎諛??뚮퉬",
            "?덇퀬 苑?,
            "?덇퀬 苑껊떎諛?,
            "?덇퀬 蹂댄깭?덉뺄",
            "蹂댄깭?덉뺄 ?쒕━利?苑?,
            "?λ궃媛?苑껊떎諛??뷀쎕",
            "?뷀쎕 ?뚮퉬 ?몃젋??,
            "?앺솕 苑껊떎諛??뚮퉬",
            "苑껊떎諛??좊Ъ ?щ씪吏??쒕?",
            "?덉깉 ?뚭퀬???덇퀬 苑?,
        ],
        "must_terms": [
            "?먯삁",
            "怨쇱닔",
            "怨쇱씪",
            "?뷀쎕",
            "?덊솕",
            "苑껊떎諛?,
            "?앺솕",
            "遺耳",
            "?뚮씪??,
            "?덇퀬",
            "?쒖꽕梨꾩냼",
            "怨쇱콈",
            "?ш낵",
            "媛먭랠",
            "留뚭컧",
            "?쒕씪遊?,
            "?덈뱶??,
            "泥쒗삙??,
            "?щ룄",
            "?ㅼ씤癒몄뒪罹?,
            "?④컧",
            "?レ?媛?,
            "怨띔컧",
            "?ㅼ쐞",
            "李몃떎??,
            "?좎옄",
            "?뚮갇",
            "?먮몢",
            "蹂듭댂??,
            "留ㅼ떎",
            "?멸린",
            "?뚰봽由ъ뭅",
            "李몄쇅",
            "?ㅼ씠",
            "?뗪퀬異?,
            "怨좎텛",
            "?좊쭏??,
            "諛⑹슱?좊쭏??,
            "?異붾갑?명넗留덊넗",
            "?섎컯",
            "?몃컯",
            "?좏샇諛?,
            "?⑦샇諛?,
            "伊ы궎??,
            "?쇰쭩",
            "硫쒕줎",
            "癒몄뒪?щ찞濡?,
            "?ㅽ듃硫쒕줎",
            "?쇱뒪硫쒕줎",
            "?섎?怨?,
            "移명깉猷⑦봽",
            "?덈땲?",
            "?좉퀬諛?,
            "?섏＜諛?,
            "諛?怨쇱씪",
        ],
    },
    {
        "key": "policy",
        "title": "?뺤콉 諛?二쇱슂 ?댁뒋",
        "color": "#1d4ed8",
        "queries": [
            "?띿떇?덈? ?뺤콉釉뚮━??, "?띿떇?덈? 蹂대룄?먮즺 ?띿궛臾?, "?뺤콉釉뚮━???띿텞?섏궛臾?, "?띿텞?섏궛臾??좎씤吏??,
            "?깆닔??媛寃??덉젙 ?梨?, "?좊떦愿??怨쇱씪 寃??, "?먯궛吏 ?⑥냽 ?띿궛臾?, "?⑤씪???꾨ℓ?쒖옣 ?띿떇?덈?",
            "???댄썑 怨쇱씪 媛寃??섎씫", "?ш낵 諛?媛寃??섎씫", "?깆닔??臾쇨? 怨쇱씪", "李⑤???臾쇨? 怨쇱씪",
            "?뚮퉬?먮Ъ媛 怨쇱씪 ?ш낵 諛?, "KOSIS ?뚮퉬?먮Ъ媛 ?ш낵 諛?, "臾쇨??뺣낫 ??怨쇱씪",
        ],
        "must_terms": ["?뺤콉", "?梨?, "吏??, "?좎씤", "?좊떦愿??, "寃??, "蹂대룄?먮즺", "釉뚮━??, "?⑤씪???꾨ℓ?쒖옣", "?먯궛吏", "臾쇨?", "媛寃?, "?곸듅", "?섎씫", "湲됰벑", "?깆닔??, "李⑤???, "?뚮퉬?먮Ъ媛", "臾쇨?吏??, "?듦퀎", "KOSIS"],
    },
    {
        "key": "dist",
        "title": "?좏넻 諛??꾩옣 (?꾨ℓ?쒖옣/APC/?섏텧)",
        "color": "#6d28d9",
        "queries": [
            "媛?쎌떆??泥?낵 寃쎈씫",
            "媛?쎌떆??寃쎈씫媛",
            "?꾨ℓ?쒖옣 泥?낵 寃쎈씫",
            "?꾨ℓ?쒖옣 諛섏엯??,
            "?꾨ℓ?쒖옣 ?섍툒",
            "怨듭쁺?꾨ℓ?쒖옣 寃쎈ℓ",
            "怨듯뙋??泥?낵 寃쎈ℓ",
            "?쒖옣?꾨ℓ?몄젣 ?꾨ℓ?쒖옣",
            "?⑤씪???꾨ℓ?쒖옣 泥?낵",
            "?곗??좏넻?쇳꽣 以怨?,
            "?ㅻ쭏???띿궛臾??곗??좏넻?쇳꽣 以怨?,
            "?ㅻ쭏??APC 以怨?,
            "APC ?곗??좏넻?쇳꽣 以怨?,
            "APC ??⑥???,
            "CA???怨쇱씪",
            "?먯궛吏 ?쒖떆 ?⑥냽 ?띿궛臾?,
            "遺?뺤쑀???⑥냽 ?띿궛臾?,
            "?띿궛臾??섏텧 寃??,
            "怨쇱씪 ?섏텧 寃??,
            "?듦? 怨쇱씪 寃??,
            "?뷀쎕怨듯뙋??寃쎈ℓ",
            "?덊솕 寃쎈ℓ",
            "?뷀쎕?먯“湲?,
        ],
        "must_terms": [
            "媛?쎌떆??,
            "?꾨ℓ?쒖옣",
            "怨듭쁺?꾨ℓ?쒖옣",
            "怨듯뙋??,
            "泥?낵",
            "寃쎈씫",
            "寃쎈씫媛",
            "寃쎈ℓ",
            "諛섏엯",
            "?쒖옣?꾨ℓ??,
            "?⑤씪???꾨ℓ?쒖옣",
            "?곗??좏넻",
            "?곗??좏넻?쇳꽣",
            "apc",
            "?ㅻ쭏??apc",
            "以怨?,
            "??⑥???,
            "ca???,
            "??κ퀬",
            "?섏텧",
            "寃??,
            "?듦?",
            "?먯궛吏",
            "遺?뺤쑀??,
            "?⑥냽",
            "?뷀쎕",
            "?덊솕",
            "?뷀쎕怨듯뙋??,
            "?먯“湲?,
        ],
    },
    {
        "key": "pest",
        "title": "蹂묓빐異?諛?諛⑹젣",
        "color": "#b45309",
        "queries": [
            "怨쇱닔?붿긽蹂?諛⑹젣", "?꾩?蹂?諛⑹젣", "?붾룞 ?댁땐 諛⑹젣",
            "?됲빐 ?숉빐 怨쇱닔 ?쇳빐", "蹂묓빐異??덉같 諛⑹젣",
        ],
        "must_terms": ["諛⑹젣", "蹂묓빐異?, "?쎌젣", "?댄룷", "?덉같", "怨쇱닔?붿긽蹂?, "?꾩?蹂?, "?됲빐", "?숉빐", "?붾룞"],
    },
]


# -----------------------------
# Topic diversity
# -----------------------------
COMMODITY_TOPICS = [
    ("?ш낵", ["?ш낵"]),
    ("諛?, ["?좉퀬諛?, "?섏＜諛?, "諛?怨쇱씪", "諛?怨쇱씪)"]),
    ("?④컧", ["?④컧"]),
    ("媛?怨띔컧", ["?レ?媛?, "怨띔컧"]),
    ("媛먭랠/留뚭컧", ["媛먭랠", "留뚭컧", "留뚭컧瑜?, "?쒕씪遊?, "?덈뱶??, "泥쒗삙??, "?⑷툑??, "留뚮떎由?, "?대젅硫섑떞", "臾닿???, "FTA"]),
    ("?щ룄", ["?щ룄", "?ㅼ씤癒몄뒪罹?]),
    ("?ㅼ쐞", ["?ㅼ쐞", "李몃떎??]),
    ("?좎옄", ["?좎옄"]),
    ("諛?, ["?뚮갇"]),
    ("?먮몢", ["?먮몢"]),
    ("蹂듭댂??, ["蹂듭댂??]),
    ("留ㅼ떎", ["留ㅼ떎"]),
    ("?멸린", ["?멸린"]),
    ("?좊쭏??, ["?좊쭏??, "諛⑹슱?좊쭏??, "?異붾갑?명넗留덊넗"]),
    ("?섎컯", ["?섎컯"]),
    ("?몃컯", ["?몃컯", "?좏샇諛?, "?⑦샇諛?, "伊ы궎??, "二쇳궎??]),
    ("?쇰쭩", ["?쇰쭩"]),
    ("硫쒕줎", ["癒몄뒪?щ찞濡?, "?ㅽ듃硫쒕줎", "?쇱뒪硫쒕줎", "?섎?怨?, "移명깉猷⑦봽", "?덈땲?", "硫쒕줎"]),
    ("?뚰봽由ъ뭅", ["?뚰봽由ъ뭅"]),
    ("李몄쇅", ["李몄쇅"]),
    ("?ㅼ씠", ["?ㅼ씠"]),
    ("怨좎텛", ["怨좎텛", "?뗪퀬異?, "泥?뼇怨좎텛"]),
    ("?뷀쎕", ["?뷀쎕", "?덊솕", "援?솕", "?λ?", "諛깊빀", "苑껊떎諛?, "?앺솕", "遺耳", "?뚮씪??]),
    ("?꾨ℓ?쒖옣", ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듭쁺?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "寃쎈ℓ", "諛섏엯", "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣"]),
    ("APC/?곗??좏넻", ["apc", "?곗??좏넻", "?곗??좏넻?쇳꽣", "?좊퀎", "???, "???, "ca???, "臾쇰쪟"]),
    ("?섏텧/寃??, ["?섏텧", "寃??, "?듦?", "?섏엯寃??, "?붾쪟?띿빟"]),
    ("?뺤콉", ["?梨?, "吏??, "蹂대룄?먮즺", "釉뚮━??, "?좊떦愿??, "?좎씤吏??, "?먯궛吏", "?⑥냽", "怨좎떆", "媛쒖젙"]),
    ("蹂묓빐異?, ["蹂묓빐異?, "諛⑹젣", "?덉같", "?쎌젣", "?댄룷", "怨쇱닔?붿긽蹂?, "?꾩?蹂?, "?멸퇏蹂?, "?됲빐", "?숉빐"]),
]

# Alias for generalized topic signals & fallback query generation
TOPICS = COMMODITY_TOPICS
# -----------------------------
# Cross-topic signals (generalized)
# -----------------------------
# ?꾩껜 ?좏뵿 ?ㅼ썙???뚮Ц??. ?뱀젙 湲곗궗/?댁뒋??留욎텣 ?섎뱶肄붾뵫???꾨땲??
# '?덈ぉ(?먯삁) ?좏샇' + '臾댁뿭/?뺤콉 ?좏샇'媛 ?④퍡 ?섏삱 ???듭떖?깆쓣 ?쇰컲?곸쑝濡??щ젮以??
ALL_TOPIC_TERMS_L = sorted({
    (t or "").strip().lower()
    for _tn, _terms in TOPICS
    for t in (_terms or [])
    if (t or "").strip()
})

TRADE_POLICY_TERMS_L = [
    "?섏엯", "?섏엯??, "?섏엯 怨쇱씪", "?섏엯 ?띿궛臾?,
    "愿??, "?좊떦愿??, "臾닿???, "fta", "?듦?", "寃??, "?섏엯寃??,
    "蹂댁꽭", "蹂댁꽭援ъ뿭", "諛섏엯", "諛섏텧", "?섏엯?좉퀬", "愿?몄껌",
]

TRADE_IMPACT_TERMS_L = [
    "?좎떇", "?泥?, "寃쎌웳", "?寃?, "?곕젮", "?뺣컯", "異⑷꺽",
    "媛寃??섎씫", "媛寃??곸듅", "?섍툒", "臾쇰웾", "?ш퀬", "異쒗븯",
    "援?궡??, "?띻?", "?앹궛??, "?곗?",
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

    - 1李? URL ?⑦꽩(?? newsis NISXYYYYMMDD)?먯꽌 ?좎쭨 異붿젙
    - 2李? 蹂몃Ц HTML 硫뷀??쒓렇?먯꽌 datetime 異붿텧(媛踰쇱슫 regex)
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


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url: str) -> str:
    """URL???꾨찓???몄뒪?몃챸).
    - m., www. 媛숈? ?쇰컲 ?쒕툕?꾨찓?몄? ?쒓굅??留ㅼ껜 留ㅽ븨/以묐났???꾪꽣媛 ?쇨??섍쾶 ?숈옉?섎룄濡??쒕떎.
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
    t = re.sub(r"[^0-9a-z媛-??+", "", t)
    return t[:90]

# -----------------------------
# Story-level dedupe (title + description)
# - 紐⑹쟻: ?숈씪 蹂대룄?먮즺/釉뚮━?묒씠 ?щ윭 留ㅼ껜(?고빀?댁뒪/?대뜲?쇰━/?뚯씠?몄뀥?댁뒪 ??濡?諛섎났????1嫄대쭔 ?④린湲?
# - ?쒕ぉ留뚯쑝濡쒕뒗 紐??〓뒗 "媛숈? ?댁슜 ?ㅻⅨ ?쒕ぉ" 以묐났??以꾩씠湲??꾪빐 ?ъ슜
# - dist(?좏넻/?꾩옣) ?뱀뀡? 蹂대룄?먮즺 以묐났??留롮븘, '?ㅽ넗由??쒓렇?덉쿂' + ?듭빱 湲곕컲 ?먯젙???곗꽑 ?곸슜
# -----------------------------
_STORY_ANCHORS = (
    "?쒖슱??, "?띿닔?곕Ъ", "?띿궛臾?, "遺?곹빀", "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣",
    "寃쎈씫", "寃쎈ℓ", "諛섏엯", "?섍굅", "?섍굅寃??, "遺덉떆", "寃??, "?댁씪", "?ъ빞",
    "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧",
    "?붾쪟?띿빟", "諛⑹궗??, "?앺뭹?덉쟾", "?꾪빐", "?좏넻", "李⑤떒", "?ъ쟾", "?먭린",
)

def _norm_story_text(title: str, desc: str) -> str:
    s = f"{title or ''} {desc or ''}".lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^0-9a-z媛-??]+", " ", s)
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
    # description??鍮꾩뼱?덈뒗 留ㅼ껜媛 ?덉뼱 summary瑜?蹂댁“濡??ъ슜
    desc = (a.description or "") if isinstance(a.description, str) else ""
    if (not desc.strip()) and getattr(a, "summary", ""):
        desc = str(getattr(a, "summary", "") or "")
    return (a.title or ""), desc

def _dist_story_signature(text: str) -> str | None:
    # ???쒖슱??媛?쎌떆??遺?곹빀 ?띿닔?곕Ъ(?붾쪟?띿빟/諛⑹궗???섍굅寃??遺덉떆寃?? 媛숈? 蹂대룄?먮즺 ?ㅻℓ泥?以묐났??媛뺥븯寃??쒓굅
    if "?쒖슱?? in text and "媛?쎌떆?? in text and ("?띿닔?곕Ъ" in text or "?띿궛臾? in text):
        if ("遺?곹빀" in text or "?붾쪟?띿빟" in text or "諛⑹궗?? in text) and ("?섍굅" in text or "寃?? in text or "遺덉떆" in text):
            return "SIG:SEOUL_FOODSAFETY_GARAK"

    # ???쒖슱??遺?곹빀 ?띿닔?곕Ъ ?좏넻 李⑤떒(媛?쎌떆???멸툒???놁뼱?? 蹂대룄?먮즺 ?ㅻℓ泥?以묐났???쒓굅
    if "?쒖슱?? in text and ("遺?곹빀" in text or "?붾쪟?띿빟" in text or "諛⑹궗?? in text) and ("?띿닔?곕Ъ" in text or "?띿궛臾? in text):
        if ("?좏넻" in text or "諛섏엯" in text) and ("李⑤떒" in text or "寃?? in text or "?섍굅" in text or "?먭?" in text):
            return "SIG:SEOUL_FOODSAFETY"

    # ?쇰컲?? '?먯궛吏 ?⑥냽', '遺?뺤쑀???⑥냽' 媛숈? 蹂대룄?먮즺???ㅻℓ泥?以묐났????븘 ?쒓렇?덉쿂濡?臾띕뒗??
    if ("?먯궛吏" in text or "遺?뺤쑀?? in text) and ("?⑥냽" in text or "?곷컻" in text) and ("?띿궛臾? in text or "?띿닔?곕Ъ" in text):
        if "?쒖슱?? in text:
            return "SIG:SEOUL_ORIGIN_ENFORCE"

    # ???쒓뎅泥?낵 異쒗븯鍮꾩슜 蹂댁쟾?ъ뾽(媛?쎌떆???꾨ℓ踰뺤씤) 湲곗궗 ?ㅻℓ泥?以묐났 ?쒓굅
    if ("?쒓뎅泥?낵" in text or "?쒓뎅 泥?낵" in text) and ("異쒗븯鍮꾩슜" in text or "異쒗븯 鍮꾩슜" in text):
        if ("蹂댁쟾" in text or "蹂댁쟾湲? in text or "蹂댁쟾?ъ뾽" in text or "湲곗?媛寃? in text) and ("媛?쎌떆?? in text or "?꾨ℓ踰뺤씤" in text or "寃쎈씫" in text or "異쒗븯?띻?" in text):
            return "SIG:KOREA_CHEONGGWA_SUPPORT"

    return None



def _event_key(a: "Article", section_key: str) -> str | None:
    """?뱀뀡蹂?'?ъ떎??媛숈? ?댁뒋'瑜???媛뺥븯寃?臾띔린 ?꾪븳 ?대깽????
    - ?쒕ぉ???ㅻⅤ?붾씪??媛숈? ?대깽??APC 以怨?媛쒖옣 ??硫?1嫄대쭔 ?④꺼 ?듭떖??蹂댄샇?쒕떎.
    """
    try:
        text = ((a.title or "") + " " + (a.description or "")).lower()

        # 1) APC 以怨?媛쒖옣/媛??媛쒖냼 ???대깽???랁삊/吏???⑥쐞 臾띠쓬)
        if ("apc" in text or "?곗??좏넻?쇳꽣" in text or "?곗??좏넻" in text) and any(k in text for k in ("以怨?, "以怨듭떇", "媛쒖옣", "媛쒖냼", "臾???, "媛??, "以鍮?, "?ㅻ쭏??)):
            m = re.search(r"([媛-??{2,12})\s*?랁삊", (a.title or "") + " " + (a.description or ""))
            if m:
                org = f"{m.group(1)}?랁삊"
                return f"EV:APC:{org}"
            regs = sorted(_region_set(text))
            loc = regs[0] if regs else ""
            return f"EV:APC:{loc}"

        # 2) ?쒖슱??遺?곹빀 ?띿닔?곕Ъ ?좏넻 李⑤떒(蹂대룄?먮즺 ?ㅻℓ泥?以묐났)
        if "?쒖슱?? in text and ("遺?곹빀" in text or "?붾쪟?띿빟" in text or "諛⑹궗?? in text) and ("?띿닔?곕Ъ" in text or "?띿궛臾? in text):
            if ("?좏넻" in text or "諛섏엯" in text) and ("李⑤떒" in text or "寃?? in text or "?섍굅" in text or "?먭?" in text):
                return "EV:SEOUL_FOODSAFETY"

    except Exception:
        return None

    return None



def _dedupe_prefer_bonus(a: "Article", section_key: str) -> float:
    """以묐났(?대깽???? ?댁뿉??1嫄대쭔 ?④만 ?뚯쓽 '?좏샇' 蹂댁젙.
    - ?뱀젙 留ㅼ껜(?⑥씪) ?명뼢???꾨땲?? ?곗뼱/?좏삎(諛⑹넚 vs ?듭떊/?쇱슫?쒖뾽) 以묒떖?쇰줈 ?덉젙?뷀븳??
    - 媛숈? ?대깽?몃씪硫?諛⑹넚(?뱁엳 ?꾧뎅) 1嫄댁쓣 ?④린怨? ?듭떊 '?뚯떇/釉뚮━????諛?대궦??
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

        # ?꾧뎅 諛⑹넚??以묒븰) ?곗꽑
        if p in BROADCAST_PRESS:
            b += 1.4

        # 吏??諛⑹넚(?? JIBS)? ?듭떊蹂대떎???곗꽑, ?꾧뎅 諛⑹넚蹂대떎????쾶
        if p in ("JIBS", "JIBS?쒖＜諛⑹넚", "JIBS ?쒖＜諛⑹넚") or d.endswith("jibstv.com"):
            b += 0.4

        # ?듭떊/?⑤씪???쒕퉬?ㅻ뒗 以묐났 洹몃９?먯꽌???꾩닚??湲곗궗???쇱슫?쒖뾽 鍮덈룄)
        if p in WIRE_SERVICES:
            b -= 0.8

        # '?뗢뿃?뚯떇/?쒖＜?뚯떇' 媛숈? ?쇱슫?쒖뾽? 以묐났 洹몃９?먯꽌???꾩닚??
        if ("?쒖＜?뚯떇" in title) or title.strip().endswith("?뚯떇"):
            b -= 1.2

        # dist?먯꽌 濡쒖뺄 ?⑥떊/怨듭??뺤씠硫?以묐났 洹몃９?먯꽌 媛뺥븯寃?諛?대깂
        if section_key == "dist" and is_local_brief_text(title, desc, "dist"):
            b -= 2.0

        # ?띿뾽 ?꾨Ц/?꾩옣 留ㅼ껜 ?쒖옣 由ы룷?몃뒗 ?대━????以묐났 洹몃９?먯꽌??
        if p in AGRI_TRADE_PRESS or d in AGRI_TRADE_HOSTS:
            b += 0.8

        return b
    except Exception:
        return 0.0


def _dedupe_by_event_key(items: list["Article"], section_key: str) -> list["Article"]:
    """?대깽????湲곗??쇰줈 以묐났 ?꾨낫瑜?1嫄대쭔 ?④릿???먯닔/?곗뼱/理쒖떊 ??."""
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
        "愿??, "?좊떦愿??, "臾닿???, "fta", "?섏엯", "?듦?", "寃??, "蹂댁꽭", "蹂댁꽭援ъ뿭",
        "異붿쿇 痍⑥냼", "吏묒쨷愿由?, "愿由?媛뺥솕", "?먮ℓ媛寃?蹂닿퀬", "?좏넻 ?섎Т"
    ))


def _is_similar_story(a: "Article", b: "Article", section_key: str) -> bool:
    at, ad = _story_text(a)
    bt, bd = _story_text(b)
    a_txt = f"{at} {ad}"
    b_txt = f"{bt} {bd}"

    # supply/policy: 臾댁뿭/愿??FTA/?섏엯 ?좏샇 ?좊Т媛 ?ㅻⅤ硫?媛숈? ?댁뒋濡?臾띠? ?딆쓬(?듭떖 ?댁뒋 ?꾨씫 諛⑹?)
    if section_key in ("supply", "policy"):
        if _has_trade_signal(a_txt) != _has_trade_signal(b_txt):
            return False

    # 0) ?쒕ぉ/?붿빟 湲곕컲 洹쇱젒 以묐났(?留ㅼ껜 ?ъ쟾???쒓린 李⑥씠) 蹂닿컯
    try:
        if _near_duplicate_title(a, b, section_key):
            return True
    except Exception:
        pass


    # 1) dist??'?쒓렇?덉쿂' ?곗꽑
    if section_key == "dist":
        sa = _dist_story_signature(a_txt)
        sb = _dist_story_signature(b_txt)
        if sa and sb and sa == sb:
            return True

    # 2) ?듭빱 寃뱀묠 + 3-gram Jaccard(?뱀뀡蹂??꾧퀎移?
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
        # dist??蹂대룄?먮즺 以묐났??留롮쑝誘濡??듭빱 議곌굔??議곌툑 ?꾪솕
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
    # ?곗냽 2湲??諛붿씠洹몃옩) 湲곕컲 ?좎궗?? ?뱀닔臾몄옄 ?쒓굅??title_key????留욎쓬
    return {s[i:i+2] for i in range(len(s) - 1)}

def _is_similar_title(k1: str, k2: str) -> bool:
    """?쒕ぉ 以묐났(?좎궗) ?먯젙.
    - 紐⑹쟻: 媛숈? ?댁뒋媛 ?留ㅼ껜濡?諛섎났????core/final?먯꽌 以묐났 ?쒓굅
    - ?낅젰? norm_title_key()濡??뺢퇋?붾맂 臾몄옄?댁쓣 媛??怨듬갚/?뱀닔臾몄옄 ?쒓굅)
    """
    a = (k1 or "").strip()
    b = (k2 or "").strip()
    if not a or not b:
        return False
    if a == b:
        return True

    # ?덈Т 吏㏃? ?ㅻ뒗 ?ㅽ깘 ?꾪뿕???щ?濡? ?ы븿愿怨꾨쭔 ?쒗븳?곸쑝濡??덉슜
    la, lb = len(a), len(b)
    shorter, longer = (a, b) if la <= lb else (b, a)
    ls, ll = len(shorter), len(longer)

    if ls < 10:
        # 10湲??誘몃쭔? ?ъ떎???쒕ぉ ?ㅻ줈 ?좊ː?섍린 ?대젮?
        return False

    # ?ы븿愿怨? 吏㏃? ?ㅺ? 湲??ㅼ뿉 ?ы븿?섍퀬 湲몄씠 李⑥씠媛 ?ъ? ?딆쑝硫??숈씪 ?댁뒋濡?遊?
    if shorter in longer and (ls / ll) >= 0.78:
        return True

    # 臾몄옄???좎궗??SequenceMatcher)
    try:
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        if ratio >= 0.90:
            return True
        # 寃쎄퀎 ?곸뿭? 諛붿씠洹몃옩 ?먯뭅?쒕줈 異붽? ?뺤씤(湲??쒕ぉ?먯꽌留?
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
# - 1湲???ㅼ썙??諛?諛?苑?洹?? ?????ㅽ깘????븘 "留λ씫 ?⑦꽩"?쇰줈留?留ㅼ묶
# - topic? 移대뱶???몄텧?섎?濡? ?덈ぉ 遺꾨쪟 ?뺥솗?꾧? 留ㅼ슦 以묒슂
# -----------------------------
_SINGLE_TERM_CONTEXT_PATTERNS: dict[str, list[re.Pattern]] = {
    # 怨쇱씪 '諛? (諛고꽣由?諛곕떦/諛곕떖/諛곌린/諛고룷 ???ㅽ깘 諛⑹?)
    "諛?: [
        re.compile(r"(?:^|[\s\W])諛??:媛?媛寃??쒖꽭|?섍툒|異쒗븯|????묓솴|?щ같|?띻?)"),
        re.compile(r"(?:^|[\s\W])諛?s+怨쇱씪"),
        re.compile(r"?좉퀬諛?),
    ],
    # '諛?(night) ?ㅽ깘 諛⑹?: ?뚮갇/諛ㅺ컪/諛??띿궛臾?留λ씫)
    "諛?: [
        re.compile(r"(?:^|[\s\W])諛??:媛?媛寃??쒖꽭|?섍툒|異쒗븯|?묓솴|?щ같|?띻?)"),
        re.compile(r"?뚮갇"),
    ],
    # '苑?(?쇰컲 ?⑥뼱吏留??뷀쎕 湲곗궗?먯꽌 鍮덈쾲): 苑껉컪/?덊솕/寃쎈ℓ ?깃낵 ?④퍡
    "苑?: [
        re.compile(r"(?:^|[\s\W])苑??:媛?媛寃??쒖꽭)"),
        re.compile(r"(?:^|[\s\W])苑?s*(寃쎈ℓ|?꾨ℓ|?뚮ℓ|?쒖옣)"),
        re.compile(r"苑껊떎諛?),
        re.compile(r"遺耳"),
    ],
    # '洹? (媛먭랠 留λ씫)
    "洹?: [
        re.compile(r"(?:^|[\s\W])洹??:媛?媛寃??쒖꽭|?섍툒|異쒗븯|?묓솴|?щ같|?띻?)"),
        re.compile(r"媛먭랠"),
        re.compile(r"留뚭컧"),
    ],
    # '?'? ?먯삁???꾨땲吏留?湲곗〈 濡쒖쭅 ?좎?(?媛?鍮꾩텞誘???
    "?": [
        re.compile(r"(?:^|[\s\W])?(?:媛?媛寃??쒖꽭|?섍툒)"),
        re.compile(r"鍮꾩텞誘?),
        re.compile(r"rpc"),
    ],
}

_HORTI_TOPICS_SET = {
    "?뷀쎕", "?ш낵", "諛?, "媛먭랠/留뚭컧", "?④컧", "媛?怨띔컧", "?ㅼ쐞", "?좎옄", "?щ룄",
    "諛?, "?먮몢", "蹂듭댂??, "留ㅼ떎", "?멸린", "?뚰봽由ъ뭅", "李몄쇅", "?ㅼ씠", "怨좎텛",
    "?좊쭏??,
    "?섎컯",
    "?몃컯",
    "?쇰쭩",
    "硫쒕줎",
}

def _topic_scores(title: str, desc: str) -> dict[str, float]:
    t = (title + " " + desc).lower()
    tl = (title or "").lower()
    scores: dict[str, float] = {}

    for topic, words in COMMODITY_TOPICS:
        sc = 0.0
        if topic == "硫쒕줎" and not is_edible_melon_context(t):
            # 硫쒕줎(?뚯썝 ?뚮옯?? ?ㅽ깘 諛⑹?
            continue


        if topic == "?쇰쭩" and not is_edible_pimang_context(t):
            # ?쇰쭩(寃뚯엫/釉뚮옖?? ?ㅽ깘 諛⑹?
            continue

        if topic == "?ш낵" and not is_edible_apple_context(t):
            # ?ш낵(怨쇱씪) ?숈쓬?댁쓽???ш낵?/?ш낵臾??? ?ㅽ깘 諛⑹?
            continue

        if topic == "?ш낵" and any(x in t for x in ("?섏궗怨쇳븰", "?섏궗怨쇳븰??, "?섏궗怨쇳븰??, "?섏궗怨듯븰", "?섍낵??, "?섍낵?숈썝")):
            # '?섏궗怨쇳븰???섏궗怨쇳븰?? ?깆? '?ш낵(apple)'媛 ?꾨땲???섎즺/?숇Ц ?⑹뼱(遺遺꾨Ц?먯뿴) ?ㅽ깘
            continue


        # 湲곕낯(2湲???댁긽 ?ㅼ썙??: 遺遺꾨Ц?먯뿴 留ㅼ묶
        for w in words:
            wl = (w or "").lower()
            if len(wl) < 2:
                continue
            if wl in t:
                sc += 1.0
                if wl in tl:
                    sc += 0.4

        # 1湲???ㅼ썙?? 留λ씫 ?⑦꽩?쇰줈留?蹂닿컯
        # - topic ?먯껜媛 1湲???덈ぉ???ы븿?????덉뼱 topic紐낆쓣 湲곕컲?쇰줈 ?⑦꽩???좏깮
        if topic == "諛?:
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["諛?]):
                sc += 1.8
        if topic == "諛?:
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["諛?]):
                sc += 1.6
        if topic == "?뷀쎕":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["苑?]):
                sc += 1.3
        if topic == "媛먭랠/留뚭컧":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["洹?]):
                sc += 1.1
        if topic == "?":
            if any(p.search(t) for p in _SINGLE_TERM_CONTEXT_PATTERNS["?"]):
                sc += 1.2

        if sc > 0:
            scores[topic] = sc
    # ???뺤콉 媛뺤떊??愿???듦?/蹂댁꽭/?좊떦愿???뺣?)硫?'?뺤콉' ?좏뵿 媛以묒튂 遺??
    POLICY_STRONG_TERMS = (
        "愿??, "?좊떦愿??, "臾닿???, "fta", "?듦?", "?섏엯?좉퀬", "蹂댁꽭", "蹂댁꽭援ъ뿭", "諛섏텧", "諛섏엯",
        "愿?몄껌", "湲곗옱遺", "?띿떇?덈?", "?뺣?", "?梨?, "吏??, "?⑥냽", "怨좎떆", "媛쒖젙", "?쒗뻾",
    )
    if any(x in t for x in POLICY_STRONG_TERMS):
        scores["?뺤콉"] = scores.get("?뺤콉", 0.0) + 4.5


    return scores

def best_topic_and_score(title: str, desc: str) -> tuple[str, float]:
    scores = _topic_scores(title, desc)
    if not scores:
        return "湲고?", 0.0
    # 理쒓퀬 ?먯닔 topic, ?숈젏?대㈃ '?덈ぉ(?먯삁)'瑜??곗꽑(?뺤콉/?꾨ℓ?쒖옣蹂대떎 ?욎꽌 ?쒖떆)
    best_topic = None
    best_sc = -1.0
    for topic, sc in scores.items():
        if sc > best_sc:
            best_topic, best_sc = topic, sc
        elif sc == best_sc and best_topic is not None:
            if topic in _HORTI_TOPICS_SET and best_topic not in _HORTI_TOPICS_SET:
                best_topic = topic
    return best_topic or "湲고?", float(best_sc)

def best_horti_score(title: str, desc: str) -> float:
    scores = _topic_scores(title, desc)
    horti = [sc for t, sc in scores.items() if t in _HORTI_TOPICS_SET]
    return max(horti) if horti else 0.0

def extract_topic(title: str, desc: str) -> str:
    topic, _ = best_topic_and_score(title, desc)
    return topic

def make_norm_key(canon_url: str, press: str, title_key: str) -> str:
    if canon_url:
        h = hashlib.sha1(canon_url.encode("utf-8")).hexdigest()[:16]
        return f"url:{h}"
    base = f"{(press or '').strip()}|{title_key}"
    h = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    return f"pt:{h}"

def has_any(text: str, words) -> bool:
    return any(w in text for w in words)

def count_any(text: str, words) -> int:
    return sum(1 for w in words if w in text)


def has_apc_agri_context(text: str) -> bool:
    """APC ?ㅽ깘(UPS/?꾩썝?λ퉬 ????留됯린 ?꾪빐, '?띿뾽/?곗??좏넻' 臾몃㎘???뚮쭔 APC濡??몄젙."""
    t = (text or "").lower()
    if "apc" not in t:
        return False

    # strong: APC? ?④퍡 ?섏삤硫?嫄곗쓽 ?띿궛臾??곗??좏넻 臾몃㎘?쇰줈 蹂????덈뒗 ?좏샇
    strong_hints = (
        "?곗??좏넻", "?곗??좏넻?쇳꽣", "?띿궛臾쇱궛吏?좏넻?쇳꽣",
        "?좊퀎", "?좊퀎??, "?좉낵", "?좉낵??, "吏묓븯", "吏묓븯??,
        "???, "??⑥???, "??κ퀬", "ca???,
        "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
        "?랁삊", "議고빀", "異쒗븯", "異쒗븯??,
        "?먯삁", "怨쇱닔", "泥?낵", "?띿궛臾?, "怨쇱씪", "梨꾩냼", "?뷀쎕",
    )
    # weak: ?⑤룆?쇰줈???쏀븯吏留?APC? ?④퍡 2媛??댁긽?대㈃ ?띿뾽 ?꾩옣 留λ씫??媛?μ꽦???믪쓬
    weak_hints = (
        "?좏넻", "臾쇰쪟", "???, "?좊퀎湲?, "鍮꾪뙆愿?, "怨듭꽑", "怨듬룞?좊퀎",
        "?곗?", "?앹궛??, "?띻?", "?묐ぉ諛?, "議고빀??,
    )

    strong_hit = count_any(t, [h.lower() for h in strong_hints])
    weak_hit = count_any(t, [h.lower() for h in weak_hints])

    if strong_hit >= 1:
        return True
    return weak_hit >= 2

# -----------------------------
# Melon safety guards
# - '硫쒕줎'? ?뚯썝 ?뚮옯??硫쒕줎)怨??숈쓬?댁쓽?대씪 ?ㅽ깘????떎.
# - '癒밸뒗 硫쒕줎' 留λ씫(?щ같/異쒗븯/?묓솴/?띻?/?꾨ℓ?쒖옣 ?????뚮쭔 ?덈ぉ?쇰줈 ?몄젙?쒕떎.
# -----------------------------
_MELON_MUSIC_MARKERS = [
    "硫쒕줎李⑦듃", "?뚯썝", "?ㅽ듃由щ컢", "裕ㅼ쭅", "?⑤쾾", "媛??, "?몃옒", "?좉끝",
    "top100", "top 100", "硫쒕줎?곗폆", "肄섏꽌??, "怨듭뿰", "?щ???, "?댁슜沅?,
    "移댁뭅?ㅼ뿏??, "移댁뭅???뷀꽣", "硫쒕줎??, "硫쒕줎 ??, "硫쒕줎 ?쒕퉬??,
]
_MELON_EDIBLE_MARKERS = [
    "怨쇱씪", "怨쇱콈", "?쒖꽕", "?섏슦??, "鍮꾧?由?, "?щ같", "?띻?", "?묓솴", "?섑솗", "異쒗븯",
    "?꾨ℓ", "?꾨ℓ媛寃?, "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
    "?곗?", "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc", "?좊퀎", "???, "???, "ca???,
    "?섍툒", "?쒖꽭", "?섏텧", "寃??, "?듦?", "?붾쪟?띿빟",
]
_MELON_VARIETY_MARKERS = [
    "癒몄뒪?щ찞濡?, "?ㅽ듃硫쒕줎", "?쇱뒪硫쒕줎", "?섎?怨?, "移명깉猷⑦봽", "?덈땲?",
]

def is_edible_melon_context(text: str) -> bool:
    """Return True only when '硫쒕줎' clearly means the edible fruit (not the music service).

    Heuristics:
      - Always accept if a melon variety marker is present (癒몄뒪?щ찞濡???
      - If strong music/entertainment markers exist (硫쒕줎李⑦듃/?뚯썝/?⑤쾾 ??,
        require *strong* edible markers; otherwise reject.
      - Accept edible context when at least one agri/produce marker exists OR
        when '硫쒕줎 媛?媛寃??쒖꽭/?꾨ℓ媛寃? 媛숈? 媛寃??⑦꽩???섑??섍퀬 ?뚯븙留덉빱媛 ?놁쓣 ??
    """
    t = (text or "").lower()
    if "硫쒕줎" not in t:
        return False

    # ?덉쥌/?좏삎??紐낆떆?섎㈃ 嫄곗쓽 100% 怨쇱씪
    if any(v.lower() in t for v in _MELON_VARIETY_MARKERS):
        return True

    music_hit = any(w.lower() in t for w in _MELON_MUSIC_MARKERS)

    # ?띿뾽/?좏넻/?덉쭏 ?좏샇(媛寃??⑥뼱 ?⑤룆? ?쒖쇅)
    edible_hit = any(w.lower() in t for w in _MELON_EDIBLE_MARKERS)

    # 媛寃??⑦꽩(硫쒕줎 媛?媛寃??쒖꽭/?꾨ℓ媛寃??????덉쑝硫? ?뚯븙留덉빱媛 ?놁쓣 ?뚮쭔 怨쇱씪濡??몄젙
    price_pat = bool(re.search(r"硫쒕줎\s*(媛?媛寃??쒖꽭|?꾨ℓ媛寃?異쒗븯媛|寃쎈씫媛)", t))
    if price_pat and not music_hit:
        edible_hit = True

    # ?뚯븙/?뷀꽣 留λ씫??媛뺥븳??癒밸뒗 硫쒕줎 ?좏샇媛 ?놁쑝硫??ㅽ깘?쇰줈 ?먮떒
    if music_hit and not edible_hit:
        return False

    return edible_hit

# -----------------------------
# Pimang safety guards
# - '?쇰쭩'? 寃뚯엫/釉뚮옖???쇰쭩/pmang/?대쭪怨???濡쒕룄 留ㅼ슦 ?먯＜ ?깆옣?쒕떎.
# - 梨꾩냼(?쇰쭩/?뚰봽由ъ뭅) 留λ씫???뺤떎???뚮쭔 ?덈ぉ?쇰줈 ?몄젙?쒕떎.
# -----------------------------
_PIMANG_GAME_MARKERS = [
    "pmang", "?쇰쭩寃뚯엫", "?대쭪怨?, "留욊퀬", "怨좎뒪??, "怨좏룷瑜?, "?ъ빱", "?ㅼ삤?꾩쫰", "寃뚯엫", "蹂대뱶寃뚯엫", "紐⑤컮?쇨쾶??,
    "?앹뾽", "?ㅽ??꾨뱶", "肄붿뿊??, "?대깽??, "異쒖떆", "?낅뜲?댄듃",
]
_PIMANG_EDIBLE_MARKERS = [
    "梨꾩냼", "怨쇱콈", "?뚰봽由ъ뭅", "?쇰쭩(梨꾩냼)", "?띿궛臾?, "?먯삁", "?щ같", "?띻?", "?묓솴", "?섑솗", "異쒗븯",
    "?꾨ℓ", "?꾨ℓ媛寃?, "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
    "?곗?", "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc", "?좊퀎", "???, "???, "ca???,
    "?섍툒", "?쒖꽭", "媛寃?, "?섏텧", "寃??, "?듦?",
]

def is_edible_pimang_context(text: str) -> bool:
    """Return True only when '?쇰쭩' clearly refers to the edible vegetable (bell pepper).

    - If '?뚰봽由ъ뭅/梨꾩냼/?띿궛臾??щ같/異쒗븯/?꾨ℓ?쒖옣' ???앺뭹/?띿뾽 留덉빱媛 ?덉쑝硫??듦낵.
    - 寃뚯엫/?뷀꽣 留덉빱媛 媛뺥븳???앺뭹 留덉빱媛 ?놁쑝硫??ㅽ깘?쇰줈 李⑤떒.
    - '?쇰쭩 媛寃??쒖꽭/?꾨ℓ媛寃?異쒗븯' ?⑦꽩? 寃뚯엫 留덉빱媛 ?놁쓣 ?뚮쭔 ?앺뭹?쇰줈 ?몄젙.
    """
    t = (text or "").lower()
    if "?쇰쭩" not in t:
        return False

    edible_hit = any(w.lower() in t for w in _PIMANG_EDIBLE_MARKERS)
    game_hit = any(w.lower() in t for w in _PIMANG_GAME_MARKERS)

    price_pat = bool(re.search(r"?쇰쭩\s*(媛?媛寃??쒖꽭|?꾨ℓ媛寃?異쒗븯媛|寃쎈씫媛)", t))
    if price_pat and not game_hit:
        edible_hit = True

    if game_hit and not edible_hit:
        return False

    return edible_hit








def is_edible_apple_context(text: str) -> bool:
    """Return True only when '?ш낵' clearly refers to the fruit (apple).

    二쇱슂 ?ㅽ깘:
    - ?ш낵(玉앶걥): ?ш낵臾??ш낵?섎떎/怨듭떇 ?ш낵 ??
    - ?ш낵?/?ы쉶怨쇳븰(援먯쑁/?낆떆 湲곗궗?먯꽌 '?ш낵?' = ?ы쉶怨쇳븰???
    - ?섏궗怨쇳븰/?섏궗怨쇳븰????遺遺꾨Ц?먯뿴(?대? 蹂꾨룄 諛⑹뼱媛 ?덉쑝???ш린?쒕룄 諛⑹뼱)

    ?먯젙 ?먯튃:
    - 遺???ㅽ깘) 留덉빱媛 媛뺥븯怨??띿뾽/?쒖옣 留덉빱媛 ?놁쑝硫?False
    - '媛寃??쒖꽭/?섍툒/異쒗븯/?꾨ℓ?쒖옣/怨쇱닔/怨쇱씪/?띻?' ???ㅻТ 留덉빱媛 ?덉쑝硫?True
    """
    t = (text or "").lower()
    if "?ш낵" not in t:
        return False

    # 1) 媛뺥븳 ?ㅽ깘(?ы쉶怨쇳븰????쎌묶 ??
    hard_false = (
        "?ш낵?", "?ш낵???, "?ы쉶怨쇳븰", "?ы쉶怨쇳븰?", "?ы쉶怨쇳븰???, "?ш낵怨꾩뿴", "?ш낵 怨꾩뿴"
    )
    if any(w in t for w in hard_false):
        # ?? 怨쇱씪/?꾨ℓ/?섍툒 留덉빱媛 異⑸텇???덉쑝硫??덉쇅?곸쑝濡?True
        strong_pos = ("怨쇱씪", "怨쇱닔", "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "異쒗븯", "?묓솴", "?섍툒", "?쒖꽭", "媛寃?, "?띻?", "?곗?")
        if not any(w in t for w in strong_pos):
            return False

    # 2) ?섏궗怨쇳븰(遺遺꾨Ц?먯뿴) ?ㅽ깘
    if any(x in t for x in ("?섏궗怨쇳븰", "?섏궗怨쇳븰??, "?섏궗怨쇳븰??, "?섏궗怨듯븰", "?섍낵??, "?섍낵?숈썝")):
        return False

    # 3) '?ш낵(玉앶걥)' ?ㅽ깘: ?ш낵臾??ш낵?섎떎/怨듭떇 ?ш낵 ??
    apology_markers = (
        "?ш낵臾?, "?ш낵?덈떎", "?ш낵?⑸땲??, "?ш낵?쒕┰?덈떎", "怨듭떇 ?ш낵", "?좉컧", "?ш낵 ?붽뎄", "?ш낵瑜??붽뎄",
        "?ш낵??, "?ш낵?섍퀬", "?ш낵??
    )
    # 怨쇱씪 留λ씫 留덉빱
    fruit_markers = (
        "怨쇱씪", "怨쇱닔", "怨쇱썝", "?ш낵?섎Т", "遺??, "?꾩?", "?띾줈", "媛먰솉", "?꾩삤由?, "?쒕굹??,
        "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "寃쎈ℓ", "?곗?", "?띻?", "?щ같", "?섑솗",
        "異쒗븯", "?묓솴", "?섍툒", "?쒖꽭", "媛寃?, "???, "?ш퀬", "?좊퀎", "apc", "?곗??좏넻"
    )
    if any(m in t for m in apology_markers) and not any(m in t for m in fruit_markers):
        return False

    # 4) 湲띿젙 ?먮떒: ?ㅻТ 留덉빱媛 1媛??댁긽?대㈃ True
    if any(m in t for m in fruit_markers):
        return True

    # 5) 蹂닿컯 ?⑦꽩: '?ш낵媛??ш낵 媛寃??ш낵 ?쒖꽭' 媛숈? ?쒗쁽
    if re.search(r"?ш낵\s*(媛?媛寃??쒖꽭|?섍툒|異쒗븯|?묓솴)", t):
        return True

    # ?ш린源뚯? ?붿쑝硫?'?ш낵' ?⑤룆 ?깆옣 媛?μ꽦???믪쑝誘濡?False
    return False


# --- ?댁쇅 ?먯삁/?뷀쎕 ?낃퀎 '?먭꺽 ?댁쇅' 湲곗궗 李⑤떒(援?궡 ?ㅻТ? 臾닿???寃쎌슦) ---
_FOREIGN_REMOTE_MARKERS = [
    "肄쒕＼鍮꾩븘","誘멸뎅","以묎뎅","?쇰낯","踰좏듃??,"?쒓뎅","?몃룄","?몄＜","?댁쭏?쒕뱶","?좊읇","eu","?ъ떆??,"?고겕?쇱씠??,
    "釉뚮씪吏?,"移좊젅","?섎（","硫뺤떆肄?,"罹먮굹??,"?몃룄?ㅼ떆??,"?꾨━?","留먮젅?댁떆??,"?깃??щⅤ","?⑥븘怨?,"耳??,
    "?ㅻ뜙???,"?ㅽ럹??,"?꾨옉??,"?낆씪","?곴뎅","trump","?몃읆??,
]
_KOREA_STRONG_CONTEXT = [
    "援?궡","?쒓뎅","?곕━?섎씪","?랁삊","?띿떇?덈?","?띾┝異뺤궛?앺뭹遺","aT","媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"泥?낵","?곗??좏넻","?곗??좏넻?쇳꽣",
]

# -----------------------------
# Extra context guards
# -----------------------------
_RETAIL_PROMO_STORE_HINTS = [
    "諛깊솕??, "??뺣쭏??, "留덊듃", "?대쭏??, "?덊뵆?ъ뒪", "濡?뜲留덊듃", "肄붿뒪?몄퐫", "荑좏뙜", "ssg", "?좎꽭怨?, "濡?뜲諛깊솕??,
]
_RETAIL_PROMO_DEAL_HINTS = [
    "?꾨줈紐⑥뀡", "?좎씤", "?몄씪", "?밴?", "荑좏룿", "移대뱶", "?곷┰", "?ъ씤??, "?됱궗", "1+1", "2+1", "n+1", "湲고쉷??,
]
def is_retail_promo_context(text: str) -> bool:
    """????좏넻(諛깊솕??留덊듃) ?꾨줈紐⑥뀡??湲곗궗?몄? ?먮떒.
    - dist(?좏넻/?꾩옣)?먯꽌 '?꾨ℓ/怨듯뙋?? 留λ씫 ?놁씠 ?대윴 湲곗궗媛 ?ㅼ뼱?ㅻ뒗 寃껋쓣 李⑤떒?쒕떎.
    """
    t = (text or "").lower()
    store = any(w.lower() in t for w in _RETAIL_PROMO_STORE_HINTS)
    deal = any(w.lower() in t for w in _RETAIL_PROMO_DEAL_HINTS)
    # ?덈Т ?쇰컲?곸씤 '?됱궗' ?ㅽ깘??以꾩씠湲??꾪빐, 媛寃??좎씤 怨꾩뿴???④퍡 ?덉쓣 ?뚮쭔 True
    if store and deal:
        return True
    return False
_RETAIL_SALES_TREND_MARKERS = [
    "留ㅼ텧", "?먮ℓ", "?먮ℓ??, "?먮ℓ鍮꾩쨷", "鍮꾩쨷", "?곗씠??, "遺꾩꽍", "?몃젋??, "?섏묠諛?,
    "臾댁씤", "臾댁씤怨쇱씪", "怨쇱씪媛寃?, "?먮ℓ??, "留ㅼ옣", "?뚮ℓ", "?몄쓽??, "留덊듃", "諛깊솕??,
    "?꾨옖李⑥씠利?, "泥댁씤", "?⑤씪?몃ぐ", "援щℓ", "?뚮퉬",
]
_RETAIL_SALES_TREND_EXCLUDE = [
    # 嫄곗떆 臾쇨?/?듦퀎??policy?먯꽌 ?ㅻ（誘濡??쒖쇅?섏? ?딆쓬(?꾨옒 濡쒖쭅?먯꽌 ?곕줈 ?먮떒)
]
def is_retail_sales_trend_context(text: str) -> bool:
    """?뚮ℓ/由ы뀒???먮ℓ ?곗씠??湲곕컲 ?몃젋??湲곗궗 ?먯젙.
    - ?? '留ㅼ텧/?먮ℓ ?곗씠??遺꾩꽍/?몃젋????궧' 以묒떖???뚮퉬 ?몃젋??湲곗궗
    - 紐⑹쟻: ?대윴 ?좏삎? '?뺤콉 諛?二쇱슂 ?댁뒋'?쇰줈 怨쇳씉?섎릺吏 ?딅룄濡?supply 履쎌쑝濡??④린湲?
    """
    t = (text or "").lower()
    if not t:
        return False

    retail_terms = [
        "留ㅼ텧", "?먮ℓ", "?먮ℓ??, "?먮ℓ??, "?먮ℓ ?곗씠??, "?곗씠??, "遺꾩꽍", "?몃젋??, "??궧", "top", "?쒖쐞",
        "由ы뀒??, "?뚮ℓ", "留덊듃", "?몄쓽??, "?좏넻?낃퀎", "?ㅽ봽?쇱씤", "?⑤씪?몃ぐ", "?댁빱癒몄뒪", "荑좏뙜", "?ㅼ씠踰꾩눥??,
        "留ㅼ옣", "?꾨줈紐⑥뀡", "?됱궗", "援щℓ", "?뚮퉬", "?λ컮援щ땲",
    ]
    # ?덈Т 踰붿슜?곸씤 '?곗씠?? ?⑤룆? ?쒖쇅(?몄씠利?諛⑹?)
    if not any(k in t for k in retail_terms):
        return False

    horti_terms = [
        "怨쇱씪", "怨쇱닔", "梨꾩냼", "?먯삁", "?띿궛臾?, "?ш낵", "諛?, "?멸린", "?щ룄", "媛먭랠", "留뚭컧瑜?,
        "?ㅼ씤癒몄뒪罹?, "?ㅼ쐞", "李몃떎??, "蹂듭댂??, "?먮몢", "媛?, "?좊쭏??, "?뚰봽由ъ뭅", "?ㅼ씠", "李몄쇅",
    ]
    if not any(k in t for k in horti_terms):
        return False

    # ?뺤콉/?쒕룄 湲곗궗濡?蹂?留뚰븳 媛뺤떊?멸? ?덉쑝硫??뚮ℓ ?몃젋?쒕줈 蹂댁? ?딅뒗???ㅻ텇瑜?諛⑹?)
    policy_hard = ["?梨?, "吏??, "?⑥냽", "?먭?", "?뚯쓽", "諛쒗몴", "異붿쭊", "踰?, "?쒕룄", "媛쒖젙", "愿??, "寃??, "洹쒖젣"]
    if any(k in t for k in policy_hard) and ("留ㅼ텧" not in t and "?먮ℓ" not in t):
        return False

    return True


# -----------------------------
# Flower consumer-trend helpers (?뷀쎕 ?뚮퉬/?좊Ъ ?몃젋??湲곗궗)
# -----------------------------
_FLOWER_TREND_CORE_MARKERS = [
    "?뷀쎕", "苑?, "苑껊떎諛?, "?덊솕", "?앺솕", "?뚮씪??, "蹂댄깭?덉뺄", "?붿썝", "苑껋쭛", "苑껋떆??,
    "?λ?", "?ㅻ┰", "移대꽕?댁뀡", "援?솕", "?꾨━吏??,
]

_FLOWER_TREND_TREND_MARKERS = [
    "?몃젋??, "?멸린", "?좏뻾", "?뚮퉬", "?좊Ъ", "湲곕뀗??, "諛몃윴???, "議몄뾽", "?낇븰",
    "?붿씠?몃뜲??, "?꾨줈?ъ쫰", "?좏샇", "??궧", "二쇰ぉ", "?먮ℓ", "留ㅼ텧", "?덇퀬", "肄쒕씪蹂?, "?쇰?",
]

_FLOWER_TREND_EXCLUDE_MARKERS = [
    "異뺤젣", "諛뺣엺??, "?꾩떆??, "怨듭뿰", "肄섏꽌??, "?ы넗議?, "?쇨꼍", "愿愿?, "?ы뻾", "?곗씠?몄퐫??,
    "?곗삁", "?꾩씠??, "?쒕씪留?, "諛곗슦", "?명뵆猷⑥뼵??, "???, "?⑥뀡",
    "李쎌뾽", "?꾨옖李⑥씠利?, "移댄럹 李쎌뾽", "留ㅼ옣 ?ㅽ뵂",
    "寃뚯엫", "?쇨퇋??, "?좊땲硫붿씠??, "罹먮┃??援우쫰",
]

def is_flower_consumer_trend_context(text: str) -> bool:
    """?뷀쎕 '?뚮퉬/?좊Ъ ?몃젋?? ?좏삎(?? ?덇퀬 苑껊떎諛??쇰?/苑껊떎諛??좊Ъ ?몃젋?????먯젙?쒕떎.
    - ?덈ぉ 諛??섍툒 ?숉뼢(supply)?먯꽌 '?뷀쎕 ?댁뒋'濡?鍮꾪빑???섎떒) ?몄엯?섎뒗 ?⑸룄.
    - 愿愿?異뺤젣/?곗삁/李쎌뾽???몄씠利덈뒗 ?쒖쇅.
    """
    t = (text or "").lower()
    if any(w.lower() in t for w in _FLOWER_TREND_EXCLUDE_MARKERS):
        return False
    core_hits = sum(1 for w in _FLOWER_TREND_CORE_MARKERS if w.lower() in t)
    trend_hits = sum(1 for w in _FLOWER_TREND_TREND_MARKERS if w.lower() in t)
    # 理쒖냼 議곌굔: 苑껊떎諛??뷀쎕 怨꾩뿴 1媛??댁긽 + ?몃젋???좊Ъ/?덇퀬 ??1媛??댁긽
    if core_hits >= 1 and trend_hits >= 1:
        return True
    # ?덇퀬+苑껊떎諛?議고빀? 媛뺥븯寃??몄젙
    if ("?덇퀬" in t and ("苑껊떎諛? in t or "蹂댄깭?덉뺄" in t)):
        return True
    return False


# -----------------------------
# Consumer / non-agri noise helpers
# -----------------------------
_FASTFOOD_BRAND_MARKERS = [
    "鍮낅㎘", "留λ룄?좊뱶", "踰꾧굅??, "濡?뜲由ъ븘", "留섏뒪?곗튂", "kfc", "?쒕툕?⑥씠",
    "???, "留λ윴移?, "?꾨젋移섑썑?쇱씠", "?꾨젋移섑썑?쇱씠",
]
_FASTFOOD_PRICE_MARKERS = [
    "媛寃??몄긽", "媛寃⑹씤??, "?몄긽", "媛???, "媛寃???, "?붽툑 ?몄긽", "議곗젙", "臾쇨?吏??, "臾쇨? 遺??,
]

def is_fastfood_price_context(text: str) -> bool:
    """?꾨쾭嫄??⑥뒪?명뫖???꾨옖李⑥씠利?媛寃??몄긽/臾쇨? 湲곗궗(?띿궛臾?釉뚮━??愿?먯뿉???몄씠利?瑜??먯젙."""
    t = (text or "").lower()
    # ?쒕ぉ/蹂몃Ц??'鍮낅㎘'???덉쑝硫?嫄곗쓽 ??긽 ?꾨옖李⑥씠利?媛寃?湲곗궗
    if "鍮낅㎘" in t:
        return True
    if any(b.lower() in t for b in _FASTFOOD_BRAND_MARKERS) and any(m.lower() in t for m in _FASTFOOD_PRICE_MARKERS):
        return True
    # '?꾨쾭嫄?臾쇨?吏?? 瑜섎룄 ?쒖쇅(?遺遺??몄떇 臾쇨? 湲곗궗)
    if ("?꾨쾭嫄? in t and "臾쇨?吏?? in t) or ("?꾨쾭嫄? in t and "媛寃? in t and "?몄긽" in t):
        return True
    return False

_FRUIT_FOODSERVICE_EVENT_BRANDS = [
    "?좎뒓由?, "?좎뒓由ы몄쫰", "?대옖?쒖씠痢?, "酉뷀럹", "?몄떇", "留ㅼ옣", "諛⑸Ц", "?湲??쒓컙", "?湲곗떆媛?,
]
_FRUIT_FOODSERVICE_EVENT_MARKERS = [
    "?멸린異뺤젣", "?멸린 異뺤젣", "?쒖쫵", "?쒖쫵?됱궗", "?됱궗", "?꾨줈紐⑥뀡", "?붿???, "硫붾돱", "諛붿뒪耳?,
    "?ъ엯", "??, "肄섑뀗痢?, "?щ갑臾?,
]


# 嫄곗떆寃쎌젣/臾댁뿭/?쇰컲 ?뚮퉬臾쇨? 湲곗궗 以?'?띿궛臾? ?⑥뼱留??ㅼ튂???ы븿???몄씠利?李⑤떒??
_WEAK_HORTI_MARKERS = (
    "?띿궛臾?, "?띿떇??, "癒밴굅由?, "?앹옱猷?, "臾쇨?", "?λ컮援щ땲", "?뚮퉬?먮Ъ媛", "?깆닔??
)
_STRONG_HORTI_MARKERS = (
    "?ш낵", "諛?, "媛먭랠", "留뚭컧", "?멸린", "?щ룄", "李몄쇅", "?ㅼ씠", "?좊쭏??, "?뚰봽由ъ뭅", "?먮몢", "留ㅼ떎", "諛?, "蹂듭댂??,
    "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯", "異쒗븯", "?ш퀬", "???, "???, "?곗?", "?묓솴", "?좊퀎"
)

def is_macro_trade_noise_context(text: str) -> bool:
    """援?젣?듭긽/?곗뾽 湲곗궗?먯꽌 ?띿궛臾쇱씠 二쇰??곸쑝濡쒕쭔 ?멸툒?섎뒗 寃쎌슦瑜?李⑤떒."""
    t = (text or "").lower()
    if not t:
        return False

    geo_trade = ("?몃읆??, "誘멸뎅", "以묎뎅", "eu", "?좊읇", "愿??, "蹂대났愿??, "301議?, "?곹샇愿??, "fta", "ustr", "?듭긽")
    industry = ("諛섎룄泥?, "?먮룞李?, "諛고꽣由?, "泥좉컯", "?앹쑀?뷀븰", "議곗꽑", "?뚮옯??, "ai", "?멸났吏??)
    weak_horti = ("?띿궛臾?, "?띿떇??, "?앺뭹", "癒밴굅由?)
    strong_horti = _STRONG_HORTI_MARKERS + ("?먯삁", "怨쇱닔", "梨꾩냼", "?뷀쎕", "?덊솕", "泥?낵")

    geo_hit = count_any(t, [w.lower() for w in geo_trade])
    ind_hit = count_any(t, [w.lower() for w in industry])
    weak_hit = count_any(t, [w.lower() for w in weak_horti])
    strong_hit = count_any(t, [w.lower() for w in strong_horti])

    if geo_hit >= 2 and ind_hit >= 1 and weak_hit >= 1 and strong_hit == 0:
        return True
    if geo_hit >= 1 and ind_hit >= 2 and ("?띿궛臾? in t or "?띿떇?? in t) and strong_hit == 0:
        return True
    return False

def is_general_consumer_price_noise(text: str) -> bool:
    """?λ컮援щ땲/CPI ?섏뿴??湲곗궗 以??먯삁 ?섍툒 ?좏샇媛 ?쏀븳 寃쎌슦瑜?李⑤떒."""
    t = (text or "").lower()
    if not t:
        return False
    basket_terms = ("?꾧린?붽툑", "媛?ㅼ슂湲?, "?듭떊鍮?, "?섎컻??, "援먰넻鍮?, "?붿꽭", "?몄떇鍮?, "媛怨듭떇??, "怨듦났?붽툑")
    weak_hit = count_any(t, [w.lower() for w in _WEAK_HORTI_MARKERS])
    strong_hit = count_any(t, [w.lower() for w in _STRONG_HORTI_MARKERS])
    basket_hit = count_any(t, [w.lower() for w in basket_terms])

    if basket_hit >= 2 and weak_hit >= 1 and strong_hit == 0:
        return True
    if ("?λ컮援щ땲" in t or "?뚮퉬?먮Ъ媛" in t or "臾쇨?吏?? in t) and basket_hit >= 1 and strong_hit == 0:
        return True
    return False

def is_policy_announcement_issue(text: str, dom: str = "", press: str = "") -> bool:
    """?뺤콉/湲곌? 諛쒗몴??湲곗궗?몄? ?먯젙(怨듦툒/?좏넻 ?뱀뀡 怨쇰떎 ?좎엯 諛⑹???.
    ?? ?쇰컲 ?몃줎??'?덈ぉ 媛寃??섍툒' 以묒떖 湲곗궗源뚯? 怨쇳븯寃?policy濡?蹂대궡吏 ?딅룄濡??쒖옣/?덈ぉ 媛뺤떊?몃뒗 ?덉쇅 泥섎━.
    """
    t = (text or "").lower()
    d = normalize_host(dom or "")
    p = (press or "").strip()
    if not t:
        return False

    official = (d in POLICY_DOMAINS) or (p in ("?뺤콉釉뚮━??, "?띿떇?덈?"))
    agency_terms = ("?띿떇?덈?", "?띾┝異뺤궛?앺뭹遺", "?뺣?", "湲곗옱遺", "愿?몄껌", "寃??낯遺", "aT", "?띻???)
    policy_action_terms = (
        "?梨?, "吏??, "?좎씤吏??, "?먭?", "?뚯쓽", "媛꾨떞??, "諛쒗몴", "異붿쭊", "?쒗뻾", "?묒쓽", "?덉궛",
        "?섍툒?덉젙", "?덉젙 ?梨?, "湲닿툒", "???, "愿怨꾨?泥?, "吏??,
        "愿由?, "媛뺥솕", "?⑥냽", "蹂댁꽭", "蹂댁꽭援ъ뿭", "?좊떦愿??, "諛섏엯", "蹂닿?", "李쎄퀬", "?κ린 蹂닿?"
    )
    market_terms = ("媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "諛섏엯", "異쒗븯", "?ш퀬", "???, "?묓솴", "?곗?", "?쒖꽭")
    commodity_terms = ("?ш낵", "諛?, "媛먭랠", "留뚭컧", "?멸린", "?щ룄", "李몄쇅", "?ㅼ씠", "?좊쭏??, "?뚰봽由ъ뭅", "?먮몢", "留ㅼ떎", "諛?)
    agency_hit = count_any(t, [w.lower() for w in agency_terms])
    action_hit = count_any(t, [w.lower() for w in policy_action_terms])
    market_hit = count_any(t, [w.lower() for w in market_terms])
    commodity_hit = count_any(t, [w.lower() for w in commodity_terms])
    price_move = (("媛寃? in t) or ("?쒖꽭" in t)) and any(k in t for k in ("?곸듅", "?섎씫", "湲됰벑", "湲됰씫", "?쎌꽭", "媛뺤꽭"))

    # ?쇰컲?몃줎???덈ぉ/?쒖옣 媛寃⑷린???? ?ш낵쨌諛?媛寃??먮쫫)??supply???④릿??
    # ?? '?좊떦愿??蹂댁꽭援ъ뿭/愿?몄껌/?듦?/異붿쿇??異붿쭠' ??媛뺥븳 ?됱젙쨌?쒕룄 ?좏샇媛 ?덉쑝硫?
    # ?덈ぉ ?⑥뼱媛 ?쇰? ?ы븿?쇰룄 ?뺤콉 湲곗궗濡?遺꾨쪟?쒕떎(?? ?섏엯???좊떦愿???낆슜/愿由?媛뺥솕).
    strong_admin_terms = (
        "?좊떦愿??, "愿?몄껌", "蹂댁꽭", "蹂댁꽭援ъ뿭", "?섏엯?좉퀬", "?듦?", "異붿쿇??, "異붿쿇", "異붿쿇 痍⑥냼",
        "吏묒쨷愿由?, "吏??, "?섎Т", "?좎냽 ?좏넻", "異붿쭠", "媛?곗꽭", "?⑥냽", "愿由?媛뺥솕"
    )
    strong_admin_hit = count_any(t, [w.lower() for w in strong_admin_terms])

    if strong_admin_hit == 0:
        # '?덈ぉ+?쒖옣/媛寃????듭떖???쇰컲 湲곗궗留?supply???④?
        if (commodity_hit >= 1 and (market_hit >= 1 or price_move)):
            if not official:
                return False
        # ?먯삁 ?먯닔留??믨퀬 ?뺤콉 ?ㅽ뻾/?됱젙 ?좏샇媛 ?쏀븳 寃쎌슦(?⑥닚 ?덈ぉ ?멸툒)??supply濡??④?
        if best_horti_score("", t) >= 2.2 and action_hit < 2 and agency_hit < 1:
            if not official:
                return False

    if official:
        return (agency_hit + action_hit) >= 1

    # 鍮꾧났???꾨찓?몄씠?대룄 ?뺣?/遺泥?諛쒗몴???ъ씤??湲곗궗硫?policy ?쇱슦??
    if agency_hit >= 1 and action_hit >= 2 and market_hit == 0 and not price_move:
        return True

    return False

def is_generic_import_item_context(text: str) -> bool:
    """媛怨??섏엯 ?먯옱猷뙿룹텞????'踰뷀뭹紐??앺뭹?먮즺)' ?꾩＜???뺤콉 湲곗궗 留λ씫?몄?.
    - '?됰룞?멸린/?ㅽ깢/而ㅽ뵾?앸몢/肄붿퐫??泥섎읆 ?먯삁 ?덈ぉ ?⑥뼱媛 ?ы븿?쇰룄,
      湲곗궗 蹂몄쭏??'?쒕룄쨌?듦?쨌?좊떦愿???댁쁺'?대㈃ policy媛 ?먯뿰?ㅻ윭??耳?댁뒪瑜??ъ갑?쒕떎.
    """
    t = (text or "").lower()
    if not t:
        return False
    generic_items = (
        "?ㅽ깢", "而ㅽ뵾", "?앸몢", "肄붿퐫??, "肄붿퐫?꾧?猷?, "?앺뭹?먮즺", "?먯옱猷?,
        "?됰룞?멸린", "?됰룞??, "?됰룞?뚭퀬湲?, "?됰룞?쇱?怨좉린", "??퀬湲?, "?쇱?怨좉린", "?뚭퀬湲?, "異뺤궛臾?,
        "?댄빀", "怨쇱쭠湲?, "怨듭젙嫄곕옒?꾩썝??, "怨듭젙??
    )
    admin_terms = ("?좊떦愿??, "蹂댁꽭", "蹂댁꽭援ъ뿭", "?듦?", "?섏엯?좉퀬", "異붿쿇??, "異붿쭠", "媛?곗꽭", "愿?몄껌")
    return (count_any(t, [w.lower() for w in generic_items]) >= 1) and (count_any(t, [w.lower() for w in admin_terms]) >= 1)


def is_trade_policy_issue(text: str) -> bool:
    """?듭긽/愿??寃???듦? ??'?뺤콉쨌?쒕룄' ?깃꺽??媛뺥븳 ?댁뒋?몄?(?뱀뀡 ?щ같移?媛以묒튂 蹂댁젙??.
    - ?? ?뱀젙 ?덈ぉ(媛먭랠/留뚭컧瑜??? ?섍툒/媛寃?異쒗븯 留λ씫??媛뺥븯硫?supply???④만 ???덈룄濡?
      理쒖쥌 ?대룞 ?먮떒? 蹂꾨룄(commodity 媛뺣룄)濡??쒕떎.
    """
    t = (text or "").lower()
    if not t:
        return False

    # ?듭떖 ?듭긽/?쒕룄 ?ㅼ썙??
    trade_terms = (
        "愿??, "臾닿???, "?좊떦愿??, "fta", "?듭긽", "鍮꾧???, "臾댁뿭", "臾댁뿭踰?, "301議?,
        "?섏엯", "?섏텧", "寃??, "寃??슂嫄?, "?듦?", "?먯궛吏", "?몄씠?꾧???, "諛섎뜡??
    )
    # ?댁뒋瑜?'?뺤콉'?쇰줈 留뚮뱶??珥됰컻 ?⑥뼱(???湲곗?/?섎Т/?⑥냽/援먯쑁 ??
    action_terms = (
        "???, "珥됯컖", "?梨?, "媛뺥솕", "?⑥냽", "愿由?, "?섎Т", "吏??, "?붽굔", "湲곗?", "援먯쑁", "?먭?",
        "痍⑥냼", "?섎Т??, "?묒쓽", "嫄댁쓽", "援?쉶", "?뺣?", "愿怨꾨?泥?
    )

    trade_hit = count_any(t, [w.lower() for w in trade_terms])
    action_hit = count_any(t, [w.lower() for w in action_terms])

    # 理쒖냼 2媛??댁긽(愿???섏텧, 愿??fta, ?듭긽+寃??????議고빀?대㈃??
    # ?쒕룄/???留λ씫(action)??1媛??댁긽?대㈃ policy ?깃꺽?쇰줈 蹂몃떎.
    if trade_hit >= 2 and action_hit >= 1:
        return True

    # ?쏀븳 議고빀 蹂댁셿: '愿?? + ('?섏텧' ?먮뒗 '?섏엯') + ('?낆껜/?붽굔/???) 瑜섎뒗 ?먯＜ ?뺤콉 湲곗궗??
    if ("愿?? in t) and ("?섏텧" in t or "?섏엯" in t) and ("?낆껜" in t or "?붽굔" in t or "??? in t or "珥됯컖" in t):
        return True

    return False


def is_pest_control_policy_context(text: str) -> bool:
    """蹂묓빐異?湲곗궗 以?'?뺤콉 ?쇰컲'蹂대떎 '諛⑹젣 ?ㅻТ' ?깃꺽??媛뺥븳吏 ?먯젙.
    - 吏?먯껜/湲곌? 諛쒗몴媛 ?ы븿?쇰룄, 蹂몃Ц 以묒떖???덉같쨌?쎌젣쨌諛⑹젣 ?ㅽ뻾?대㈃ pest瑜??곗꽑?쒕떎.
    """
    t = (text or "").lower()
    if not t:
        return False

    strict_hits = count_any(t, [w.lower() for w in PEST_STRICT_TERMS])
    weather_hits = count_any(t, [w.lower() for w in PEST_WEATHER_TERMS])
    horti_hits = count_any(t, [w.lower() for w in PEST_HORTI_TERMS])
    action_hits = count_any(t, [w.lower() for w in ("?꾩닔議곗궗", "?뺣??덉같", "?덉같", "諛⑹젣", "?댄룷", "?쎌젣", "臾댁긽怨듦툒", "吏묒쨷諛⑹젣", "湲닿툒諛⑹젣", "?뺤궛 李⑤떒")])
    policy_hits = count_any(t, [w.lower() for w in ("?뺤콉", "?梨?, "議곕?", "?덉궛", "釉뚮━??, "蹂대룄?먮즺", "踰?, "媛쒖젙", "愿??, "?듦?")])
    local_gov_hits = count_any(t, [w.lower() for w in ("??, "??, "?쒖껌", "?꾩껌", "援?, "援곗껌", "援?, "援ъ껌", "吏?먯껜")])

    # 紐낆떆 ?댁땐紐??? ?좊쭏?좊퓭?섎갑) ?⑦꽩 蹂닿컯
    named_pest = re.search(r"[媛-??{1,8}(?섎갑|吏꾨뵩臾??묒븷|?몃┛??珥앹콈踰뚮젅|源띿?踰뚮젅|?좎땐)", t) is not None

    pest_signal = (strict_hits >= 1) or (weather_hits >= 1) or named_pest
    # ?뺤콉 ?쇰컲(愿???듭긽) ?좏샇媛 怨쇳븳 寃쎌슦???쒖쇅
    if policy_hits >= 4 and ("愿?? in t or "?듦?" in t or "?섏엯" in t):
        return False

    # 吏?먯껜/湲곌? 蹂대룄?먮즺 ?뺤떇?대씪??蹂묓빐異??댁뒋媛 紐낇솗?섎㈃ pest ?곗꽑 ?좎?.
    # (?? "怨쇱닔?붿긽蹂??뺤궛", "?좊쭏?좊퓭?섎갑 諛쒖깮")
    return (horti_hits >= 1) and pest_signal and ((action_hits >= 1) or (local_gov_hits >= 1 and strict_hits >= 1))


def is_local_agri_policy_program_context(text: str) -> bool:
    """吏?먯껜???띿궛臾??뺤콉 ?꾨줈洹몃옩(吏??蹂댁쟾/?쒕쾾?ъ뾽) 留λ씫?몄? ?먯젙."""
    t = (text or "").lower()
    if not t:
        return False

    local_gov_terms = ["?쒖슱??, "寃쎄린??, "?꾩껌", "?쒖껌", "援곗껌", "援ъ껌", "吏?먯껜", "?밸퀎?먯튂??]
    policy_program_terms = ["?뺤콉", "?쒗뻾", "異붿쭊", "吏??, "蹂댁쟾", "?ъ뾽", "?쒕쾾", "?꾧뎅 理쒖큹", "?덉궛", "蹂댁“", "?뺣?"]
    agri_market_terms = ["?띿궛臾?, "?꾨ℓ?쒖옣", "異쒗븯", "寃쎈씫", "?먯삁", "怨쇱닔", "?띻?"]

    return (
        count_any(t, [w.lower() for w in local_gov_terms]) >= 1
        and count_any(t, [w.lower() for w in policy_program_terms]) >= 2
        and count_any(t, [w.lower() for w in agri_market_terms]) >= 1
    )


def is_fruit_foodservice_event_context(text: str) -> bool:
    """怨쇱씪(?뱁엳 ?멸린 ?? '?몄떇/酉뷀럹/?꾨옖李⑥씠利??쒖쫵?됱궗'??湲곗궗 ?먯젙.
    - 怨듦툒/?묓솴/?꾨ℓ?쒖옣 ?섍툒 ?좏샇蹂대떎 ?뚮퉬 ?대깽???깃꺽??媛뺥빐 '?덈ぉ 諛??섍툒'???듭떖(core)?먯꽌 ?쒖쇅/媛먯젏.
    """
    t = (text or "").lower()
    brand_hit = any(w.lower() in t for w in _FRUIT_FOODSERVICE_EVENT_BRANDS)
    marker_hit = any(w.lower() in t for w in _FRUIT_FOODSERVICE_EVENT_MARKERS)
    # '?멸린' ??怨쇱씪 ?ㅼ썙?쒓? ?④퍡 ?덉쓣 ?뚮쭔 ?쒖꽦???쇰컲 ?몄떇 湲곗궗 ?ㅽ깘 諛⑹?)
    fruit_hit = any(k in t for k in ("?멸린", "怨쇱씪", "?앸뵺湲?, "?멸린 ?붿???))
    return fruit_hit and (brand_hit or marker_hit)

def is_remote_foreign_horti(text: str) -> bool:
    """?댁쇅 ?먯삁/?뷀쎕 ?낃퀎(?뱁엳 ?뱀젙 援?? ???쒖옣/愿???댁뒋) 湲곗궗 以?
    援?궡(?쒓뎅) ?섍툒/?좏넻/?뺤콉怨?吏곸젒 ?곌껐???쏀븳 寃쎌슦瑜??쒖쇅?쒕떎.

    - ?댁쇅援?? 留덉빱 + ?먯삁/?뷀쎕 留덉빱媛 ?덇퀬,
    - '援?궡/?쒓뎅/?랁삊/?꾨ℓ?쒖옣' 媛숈? 媛뺥븳 援?궡 留λ씫???놁쑝硫??먭꺽 ?댁쇅濡?媛꾩＜.
    - ?? ?쒓뎅 ?섏텧/寃???듦?怨?紐낆떆?곸쑝濡??곌껐??寃쎌슦???듦낵.
    """
    t = (text or "").lower()
    if not any(w.lower() in t for w in _FOREIGN_REMOTE_MARKERS):
        return False
    if not any(w in t for w in ("?먯삁","怨쇱닔","怨쇱씪","梨꾩냼","?뷀쎕","?덊솕","苑?,"floriculture")):
        return False

    # ?쒓뎅怨?吏곸젒 ?곌껐(?섏텧/寃???듦?/?섏엯) ?좏샇媛 ?덉쑝硫??먭꺽 ?댁쇅濡?蹂댁? ?딆쓬
    if any(w in t for w in ("?섏텧","?섏엯","?듦?","寃??,"?섏엯寃??,"?섏텧湲?, "愿??)) and any(k.lower() in t for k in _KOREA_STRONG_CONTEXT):
        return False

    # 媛뺥븳 援?궡 留λ씫???놁쑝硫??쒖쇅
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


def _section_must_terms_lower(section_conf: dict) -> list[str]:
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


def keyword_strength(text: str, section_conf: dict) -> int:
    """?뱀뀡 愿???ㅼ썙??媛뺣룄(?뺤닔).
    - ?뱀뀡 must_terms ?ы븿 ?щ?(1李? + ?띿궛臾?媛뺥궎?뚮뱶(AGRI_STRONG_TERMS) 湲곕컲 ?먯닔
    - dist/pest?먯꽌 ?싳떆??湲곗궗 ?쒓굅???ъ슜
    """
    if not section_conf:
        return agri_strength_score(text)
    must = _section_must_terms_lower(section_conf)
    return count_any(text, must) + agri_strength_score(text)

def section_fit_score(title: str, desc: str, section_conf: dict) -> float:
    """?대떦 湲곗궗媛 ?뱀뀡 ?섎룄? ?쇰쭏??留욌뒗吏(0+).
    - must_terms ?띿뒪???덊듃 + ?쒕ぉ ?덊듃(媛以?
    - ?먯삁 ?듭떖 ?좏샇瑜??쏀븯寃?異붽????꾩쟾 鍮꾧???湲곗궗 ?곷떒 諛곗튂瑜?以꾩엫
    """
    txt = f"{title or ''} {desc or ''}".lower()
    ttl = (title or "").lower()
    must = _section_must_terms_lower(section_conf) if section_conf else []
    must_t = count_any(txt, must) if must else 0
    must_h = count_any(ttl, must) if must else 0
    base = (0.18 * must_t) + (0.40 * must_h)
    # ?꾩쟾 臾닿? 湲곗궗 諛⑹뼱???쏀븳 蹂댁젙
    base += 0.10 * min(6, agri_strength_score(txt))
    return round(base, 3)

def off_topic_penalty(text: str) -> int:
    return count_any(text, OFFTOPIC_HINTS)

def korea_context_score(text: str) -> int:
    return count_any(text, KOREA_CONTEXT_HINTS)

def global_retail_protest_penalty(text: str) -> int:
    return count_any(text.lower(), GLOBAL_RETAIL_PROTEST_HINTS)

# -----------------------------
# Section signal weights (?먯삁?섍툒 ?듭떖??媛以묒튂)
# - '?ㅼ썙??媛뺣룄'瑜??⑥닚 移댁슫?멸? ?꾨땲??媛以묒튂 ?⑹쑝濡?諛섏쁺
# -----------------------------
def weighted_hits(text: str, weight_map: dict[str, float]) -> float:
    return sum(w for k, w in weight_map.items() if k in text)

_NUMERIC_HINT_RE = re.compile(r"\d")
_UNIT_HINT_RE = re.compile(r"(kg|??t\b|%|?듭썝|留뚯썝|???щ윭)")

SUPPLY_WEIGHT_MAP = {
    # ?섍툒/媛寃??듭떖
    '?섍툒': 4.0, '媛寃?: 4.0, '?쒖꽭': 3.5, '寃쎈씫媛': 3.5, '?꾨ℓ媛寃?: 3.0, '?뚮ℓ媛寃?: 3.0,
    # ?앹궛/異쒗븯/?ш퀬
    '?묓솴': 3.0, '?앹궛': 2.5, '?앹궛??: 3.0, '異쒗븯': 3.0, '臾쇰웾': 2.5, '諛섏엯': 2.0,
    '?ш퀬': 3.0, '???: 2.5, 'ca???: 2.5,
    # 蹂?숈꽦/由ъ뒪??
    '湲됰벑': 2.5, '??벑': 2.5, '湲됰씫': 2.0, '?섎씫': 1.5, '??': 2.0, '鍮꾩긽': 2.0,
    '?꾨쭩': 1.2, '?숉뼢': 1.0, '?됰뀈': 1.0, '?꾨뀈': 1.0, '?鍮?: 0.8,

    '?뷀쎕': 1.8,
    '?덊솕': 1.6,
    '苑?: 1.5,
    '?먯“湲?: 1.2,
    '?멸린': 1.2,
    '?뚰봽由ъ뭅': 1.2,
    '李몄쇅': 1.1,
    '?ㅼ쐞': 1.1,
    '?좎옄': 1.1,
    '?④컧': 1.1,
    '怨띔컧': 1.1,
    '諛?: 1.0,
    '?먮몢': 1.0,
    '蹂듭댂??: 1.0,
    '留ㅼ떎': 1.0,
    '留뚭컧': 0.9,
    '留뚭컧瑜?: 0.9,
    '?쒕씪遊?: 0.9,
    '?덈뱶??: 0.9,
    '泥쒗삙??: 0.9,
}

DIST_WEIGHT_MAP = {
    '媛?쎌떆??: 3.5, '?꾨ℓ?쒖옣': 3.0, '怨듯뙋??: 2.8, '寃쎈씫': 2.8, '寃쎈ℓ': 2.5, '泥?낵': 1.5,
    '諛섏엯': 2.2, '以묐룄留ㅼ씤': 2.0, '?쒖옣?꾨ℓ??: 2.0, '臾쇰쪟': 2.0, '?좏넻?쇳꽣': 1.5,
    'apc': 2.0, '?좊퀎': 1.8, '???: 1.2, '???: 1.2, '?먯궛吏': 2.0, '遺?뺤쑀??: 2.0,

    '?곗??좏넻?쇳꽣': 2.4,
    '?곗??좏넻': 2.0,
    '以怨?: 1.2,
    '?꾧났': 1.2,
    '?먮룞??: 1.5,
    '?ㅻ쭏??: 1.0,
    'ai': 0.7,
    '?붿???: 0.9,
    '?듯빀': 0.8,
    '釉뚮옖??: 1.6,
    '?먮ℓ?랁삊': 1.2,
    '?먯삁?랁삊': 1.6,
    '?묐ぉ諛?: 1.2,
    '?먯“湲?: 1.4,
    '?뷀쎕': 1.2,
    '?덊솕': 1.1,
    '苑?: 1.1,
    '議고솕': 1.2,
    '?뚮씪?ㅽ떛': 0.6,
    '臾섏?': 0.5,
    '怨듭썝臾섏썝': 0.7,
    '?뚮퉬珥됱쭊': 1.0,
    '罹좏럹??: 0.5,
}

POLICY_WEIGHT_MAP = {
    '?梨?: 3.0, '吏??: 2.8, '?좎씤吏??: 3.0, '?좊떦愿??: 3.0, '寃??: 2.5, '?⑥냽': 2.3,
    '怨좎떆': 2.0, '媛쒖젙': 2.0, '諛쒗몴': 1.8, '異붿쭊': 1.8, '?뺣?': 1.3, '?곗옣': 1.3,
    '?덉궛': 1.8, '釉뚮━??: 2.0, '蹂대룄?먮즺': 1.8,
    # ??二쇱슂 ?댁뒋(臾쇨?/媛寃? ?뺤옣
    '臾쇨?': 3.0,
    '媛寃?: 2.4,
    '?깆닔??: 2.2,
    '李⑤???: 2.4,
    '?뚮퉬?먮Ъ媛': 2.4,
    '臾쇨?吏??: 2.0,
    '?듦퀎': 1.2,
    'kosis': 2.0,
    '?곸듅': 0.9,
    '?섎씫': 1.0,
    '湲됰벑': 1.1,
}

PEST_WEIGHT_MAP = {
    '蹂묓빐異?: 3.5, '諛⑹젣': 3.0, '?덉같': 2.5, '?띿빟': 2.3, '?댄룷': 2.0,
    '怨쇱닔?붿긽蹂?: 4.0, '?꾩?蹂?: 3.0, '??퀝': 2.8, '?멸퇏蹂?: 2.8, '?곌?猷⑤퀝': 2.8,
    '吏꾨뵩臾?: 2.5, '?묒븷': 2.3, '?몃┛??: 2.3, '珥앹콈踰뚮젅': 2.3,
    '?됲빐': 2.8, '?숉빐': 2.8, '?쒗뙆': 1.8, '?쒕━': 1.8,
}


# -----------------------------
# NH (?랁삊) relevance boost (?랁삊 寃쎌젣吏二??꾩쭅?????理쒖쟻??
# - '?랁삊'? 踰붿쐞媛 ?볦뼱 臾댁“嫄?媛?고븯硫??됱궗/湲덉쑖 ?ㅽ깘???????덉쑝誘濡?
#   (1) 媛뺤떊??寃쎌젣吏二??섎굹濡쒕쭏???랁삊紐??????ш쾶 媛??
#   (2) ?쎌떊???랁삊 ?⑤룆)???섍툒/?좏넻/?뺤콉 ?듭떖 ?⑥뼱? ?숈떆 ?깆옣???뚮쭔 ?뚰룺 媛??
# -----------------------------
NH_STRONG_TERMS = [
    "?랁삊寃쎌젣吏二?, "寃쎌젣吏二?, "?랁삊?좏넻", "?섎굹濡쒕쭏??, "?랁삊紐?,
    "?랁삊怨듯뙋??, "?랁삊 怨듯뙋??, "議고빀怨듯뙋??,
]
# '?띿닔?곕Ъ ?⑤씪?몃룄留ㅼ떆??? 二쇱껜媛 ?ㅼ뼇?섎?濡? ?랁삊 ?⑥꽌? ?④퍡 ?섏삤硫?媛뺥븯寃?媛??
NH_STRONG_COOCUR_TERMS = ["?⑤씪?몃룄留ㅼ떆??, "?띿닔?곕Ъ ?⑤씪?몃룄留ㅼ떆??, "?⑤씪???꾨ℓ?쒖옣"]

NH_WEAK_TERMS = ["?랁삊", "nh", "?랁삊以묒븰??, "吏??냽??, "?먯삁?랁삊"]

# ?랁삊 ?ㅼ썙?쒓? ?덉뼱???ㅻТ? 臾닿???寃쎌슦(湲덉쑖/?됱궗/?숈젙 ????媛??湲덉?(?먮뒗 媛꾩젒 媛먯젏)
NH_OFFTOPIC_TERMS = [
    "?랁삊???, "nh?랁삊???, "nh?ъ옄利앷텒", "?랁삊移대뱶", "nh移대뱶",
    "湲덉쑖", "?異?, "?곴툑", "?덇툑", "???, "蹂댄뿕", "二쇨?",
    "遊됱궗", "湲곕?", "?꾩썝", "?쒖긽", "異뺤젣", "?됱궗", "?숈젙", "媛꾨떞??, "?묒쓽??, "?몃???,
]

NH_COOCUR_SUPPLY = ["媛寃?, "?섍툒", "?묓솴", "異쒗븯", "臾쇰웾", "諛섏엯", "寃쎈씫", "寃쎈씫媛", "?꾨ℓ", "?ш퀬", "???]
NH_COOCUR_DIST   = ["?꾨ℓ?쒖옣", "媛?쎌떆??, "怨듯뙋??, "寃쎈ℓ", "寃쎈씫", "諛섏엯", "臾쇰쪟", "?좏넻?쇳꽣", "?⑤씪?몃룄留ㅼ떆??]
NH_COOCUR_POLICY = ["?梨?, "吏??, "?좎씤", "鍮꾩텞", "臾쇨?", "?깆닔??, "愿??, "?섏엯", "寃??, "?듦?", "?⑥냽", "釉뚮━??]

def nh_boost(text: str, section_key: str) -> float:
    t = (text or "").lower()
    if any(k.lower() in t for k in NH_OFFTOPIC_TERMS):
        return 0.0

    strong = any(k.lower() in t for k in NH_STRONG_TERMS)
    weak = any(k.lower() in t for k in NH_WEAK_TERMS)

    # 媛뺤떊?? 寃쎌젣吏二??섎굹濡쒕쭏???랁삊紐?怨듯뙋????
    if strong:
        return 6.0 if section_key in ("dist", "policy", "supply") else 3.5

    # ?⑤씪?몃룄留ㅼ떆?μ? ?랁삊 ?⑥꽌? ?숇컲???뚮쭔 媛뺥븯寃?
    if any(k.lower() in t for k in NH_STRONG_COOCUR_TERMS) and weak:
        return 3.2 if section_key in ("dist", "policy") else 2.0

    # ?쎌떊?? '?랁삊'留??덉쓣 寃쎌슦 -> ?뱀뀡 ?듭떖 ?⑥뼱? ?④퍡???뚮쭔 ?뚰룺 媛??
    if weak:
        co = NH_COOCUR_SUPPLY if section_key == "supply" else NH_COOCUR_DIST if section_key == "dist" else NH_COOCUR_POLICY
        if sum(1 for k in co if k in t) >= 1:
            return 2.2

    return 0.0


# -----------------------------
# De-prioritize meeting/visit/PR-heavy articles (?덉쭏 蹂댁젙)
# - '諛⑸Ц/?묒쓽??媛꾨떞???낅Т?묒빟'瑜섎뒗 ?ㅻТ ?섏궗寃곗젙 ?좏샇(媛寃??섍툒/臾쇰웾/?梨?媛 ?쏀븳 寃쎌슦媛 留롮쓬
# -----------------------------
EVENTY_TERMS = ["諛⑸Ц", "?쒖같", "媛꾨떞??, "?묒쓽??, "?몃???, "?좊줎??, "?낅Т?묒빟", "?묒빟", "mou", "?ㅻ챸??, "諛쒕???, "湲곕뀗??, "罹좏럹??]
TECH_TREND_TERMS = ["?ㅻ쭏?명뙗", "ai", "濡쒕큸", "?먯쑉", "?곗쨷?앹궛", "?섏쭅?띿옣", "鍮낅뜲?댄꽣", "?붿???, "?곸떊"]

def eventy_penalty(text: str, title: str, section_key: str) -> float:
    t = (text or "").lower()
    ttl = (title or "").lower()
    hits = count_any(t, [k.lower() for k in EVENTY_TERMS])
    tech = count_any(t, [k.lower() for k in TECH_TREND_TERMS])

    if hits == 0 and tech == 0:
        return 0.0

    # ?ㅻТ ?좏샇媛 異⑸텇?섎㈃ ?⑤꼸??理쒖냼??
    strong_signal = 0
    if section_key == "supply":
        strong_signal = count_any(t, [k.lower() for k in NH_COOCUR_SUPPLY]) + count_any(ttl, [k.lower() for k in SUPPLY_TITLE_CORE_TERMS])
    elif section_key == "dist":
        strong_signal = count_any(t, [k.lower() for k in NH_COOCUR_DIST]) + count_any(ttl, [k.lower() for k in DIST_TITLE_CORE_TERMS])
    elif section_key == "policy":
        strong_signal = count_any(t, [k.lower() for k in NH_COOCUR_POLICY]) + count_any(ttl, [k.lower() for k in POLICY_TITLE_CORE_TERMS])
    else:
        strong_signal = count_any(t, [k.lower() for k in PEST_TITLE_CORE_TERMS])

    if strong_signal >= 2:
        return 0.0
    if strong_signal == 1:
        # pest: '?묒쓽??媛꾨떞???뚯쓽/援먯쑁' ???됱젙 ?쇱젙??湲곗궗 ?곷떒 諛곗튂 ?듭젣
        if section_key == "pest" and any(w in t for w in ("?묒쓽??, "媛꾨떞??, "?뚯쓽", "?ㅻ챸??, "援먯쑁", "?뚰겕??, "?몃???)):
            return 2.0
        return 1.2
    # ?쒖같/?묒쓽??諛⑸Ц/湲곗닠?몃젋?쒕쭔 ?덈뒗 寃쎌슦?????ш쾶 媛먯젏
    return 2.8 + 0.6 * max(0, hits - 1) + 0.4 * tech

SUPPLY_TITLE_CORE_TERMS = ('?섍툒','媛寃?,'?쒖꽭','寃쎈씫媛','?묓솴','異쒗븯','?ш퀬','???,'臾쇰웾')
DIST_TITLE_CORE_TERMS = ('媛?쎌떆??,'?꾨ℓ?쒖옣','怨듯뙋??,'寃쎈씫','寃쎈ℓ','諛섏엯','以묐룄留ㅼ씤','?쒖옣?꾨ℓ??,'apc','?먯궛吏')
POLICY_TITLE_CORE_TERMS = ('?梨?,'吏??,'?좊떦愿??,'寃??,'?⑥냽','怨좎떆','媛쒖젙','釉뚮━??,'蹂대룄?먮즺','臾쇨?','媛寃?,'?깆닔??,'李⑤???,'?뚮퉬?먮Ъ媛','臾쇨?吏??,'?듦퀎','kosis')
PEST_TITLE_CORE_TERMS = ('蹂묓빐異?,'諛⑹젣','?덉같','怨쇱닔?붿긽蹂?,'?꾩?蹂?,'?됲빐','?숉빐','?쎌젣','?띿빟')

def governance_interview_penalty(text: str, title: str, section_key: str, horti_sc: float, market_hits: int) -> float:
    """?됱젙/?뺤튂/?명꽣酉곗꽦 湲곗궗(?꾩???誘쇱꽑/?꾩젙 ??媛 '遺遺??멸툒'留뚯쑝濡??곷떒???щ씪?ㅻ뒗 寃껋쓣 ?듭젣."""
    t = (text or "").lower()
    ttl = (title or "").lower()
    # ?쒕ぉ?먯꽌???덈ぉ/?먯삁 ?좏샇(蹂몃Ц ?쇰? ?멸툒 ?ㅽ깘 諛⑹?)
    horti_title_sc = best_horti_score(title or "", "")

    roles = ("?꾩???, "吏??, "?쒖옣", "援곗닔", "?꾩쓽??, "?꾩쓽??, "?쒖쓽??, "援?쉶?섏썝", "?꾩젙", "?쒖젙", "援곗젙", "?됱젙")
    adminish = ("誘쇱꽑", "?꾩껌", "?쒖껌", "援곗껌", "?뺣Т", "怨듭빟", "愿愿?, "蹂듭?", "泥?뀈", "援먯쑁", "援먰넻", "soc")

    if not (any(r in ttl for r in roles) or any(r in ttl for r in adminish)):
        return 0.0

    strong_terms = ("?좎씤", "?좎씤吏??, "?좊떦愿??, "?섍툒", "媛寃?, "異쒗븯", "?ш퀬",
                    "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                    "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧")
    strong_hits = count_any(t, [s.lower() for s in strong_terms])

    # ?덉쇅: ?쒕ぉ?먮룄 ?덈ぉ/?쒖옣 ?좏샇媛 ?덇퀬 ?ㅻТ ?좏샇媛 媛뺥븯硫??쏀븳 媛먯젏留?
    if strong_hits >= 2 and (market_hits >= 1 or horti_title_sc >= 1.6) and (horti_sc >= 2.2 or ("?띿궛臾? in t) or ("?띿떇?? in t)):
        return 0.8

    # ?쒕ぉ ?덈ぉ ?좏샇媛 ?쏀븯硫?=蹂몃Ц ?쇰? ?멸툒) 媛먯젏???ㅼ썙 ?곷떒/肄붿뼱 吏꾩엯??嫄곗쓽 留됰뒗??
    if horti_title_sc < 1.4 and market_hits == 0:
        return 4.0 if section_key in ("supply", "policy", "dist") else 3.0

    if horti_sc >= 2.6 and strong_hits >= 1:
        return 1.6

    # 湲곕낯 媛먯젏
    return 3.2 if section_key in ("supply", "policy", "dist") else 2.5



# -----------------------------
# Local brief detection (?곗뼱 湲곕컲 ?섎떒/?쒖쇅??
# -----------------------------
# 紐⑺몴: ?뱀젙 留ㅼ껜瑜?李띿뼱 ?꾨Ⅴ??寃껋씠 ?꾨땲?? '吏???⑥떊/吏?먯껜 ?됱젙 怨듭??? ?⑦꽩 ?먯껜瑜??≪븘?몃떎.
# - ?? ?뗢뿃???뗢뿃援??뗢뿃援?+ (吏??異붿쭊/?묒빟/媛쒖턀/紐⑥쭛/?좎젙/媛꾨떞??..) 瑜?
# - ?? '?먯“湲??먯삁)' 媛숈씠 ?ㅻТ ?듭떖 ?댁뒋???덉쇅濡??대┛??
_LOCAL_REGION_IN_TITLE_RX = re.compile(r"[媛-??{2,}(?:??援?援???硫?")
_LOCAL_BRIEF_PUNCT_RX = re.compile(r"[竊?쨌??|\s[-?볛?\s")
_LOCAL_ADMINISH_TERMS = (
    "吏??, "異붿쭊", "?뺣?", "援ъ텞", "議곗꽦", "媛쒖꽑", "媛뺥솕", "?먭?", "?⑥냽", "?쒕쾾", "怨듬え", "?좎젙", "紐⑥쭛",
    "?묒빟", "媛꾨떞??, "?ㅻ챸??, "?뚯쓽", "援먯쑁", "?뚰겕??, "?몃???, "諛쒕???, "異쒕쾾", "媛쒖턀", "?됱궗",
    "諛⑸Ц", "?꾩옣", "媛쒓?", "媛쒖옣", "以怨?, "李⑷났", "?꾧났", "湲곕?", "?꾨떖", "湲고긽", "?ъ엯", "?덉궛", "?듭썝"
)
# dist?먯꽌 '濡쒖뺄 ?⑥떊'?쇰줈 蹂닿린 ?レ? ?좏삎????媛뺥븯寃?嫄몃윭???섎뒗 ?댁쑀:
# - ?꾨낫媛 ?곸? ?? ?대윴 ?⑥떊??1~2?꾨? 李⑥??섎㈃ 吏꾩쭨 泥댄겕?댁빞 ???댁뒋(?? ?먯삁 ?먯“湲?媛 ?꾨옒濡?諛由곕떎.
_DIST_STRONG_ANCHORS = (
    "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣", "寃쎈씫", "寃쎈ℓ", "諛섏엯",
    "?꾨ℓ踰뺤씤", "以묐룄留?, "?쒖옣?꾨ℓ??, "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc",
    "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧", "?⑤씪???꾨ℓ?쒖옣",
)

# 怨듭쭅???쒖옣/援곗닔/援ъ껌???꾩????? ?숈젙???꾩옣?먭???湲곗궗 ?먯?
# - '?꾨ℓ?쒖옣'???ㅼ뼱媛???ㅼ젣濡쒕뒗 吏?먯껜 ?숈젙 湲곗궗??寃쎌슦媛 留롮븘, dist ?곷떒???ㅼ뿼?쒗궎???먯씤.
# - ?뱀젙 留ㅼ껜媛 ?꾨땲??'?⑦꽩'??湲곗??쇰줈 ?먯젙?쒕떎.
_LOCAL_OFFICIAL_IN_TITLE_RX = re.compile(r"(?:^|[\s쨌,竊?)(?:[媛-??{2,4}\s+)?[媛-??{2,4}\s+(?:?쒖옣|援곗닔|援ъ껌???꾩???吏??(?=$|[\s쨌,竊?)")
_LOCAL_OFFICIAL_MEETING_TERMS = (
    "?꾩옣媛꾨??뚯쓽", "媛꾨??뚯쓽", "?꾩옣?뚯쓽", "?낅Т蹂닿퀬", "二쇱옱", "?먭?", "?꾩옣?먭?", "諛⑸Ц", "?꾩옣 諛⑸Ц",
    "泥?랬", "?좊줈?ы빆", "媛꾨떞??, "?ㅻ챸??, "?뚯쓽",
)
_LOCAL_NATIONAL_LEVEL_HINTS = ("援?쉶", "?κ?", "?띿떇?덈?", "?뺣?", "援?젙", "踰뺤븞", "媛쒖젙", "?덉궛", "?梨?, "???)

def is_local_brief_text(title: str, desc: str, section_key: str) -> bool:
    """吏???⑥떊(吏?먯껜 ?됱젙 怨듭??? ?щ?.
    - ?뱀젙 留ㅼ껜媛 ?꾨땲??'?⑦꽩'??湲곗??쇰줈 ?먯젙?쒕떎.
    - dist?먯꽌留?蹂댁닔?곸쑝濡??ъ슜(?ㅻⅨ ?뱀뀡源뚯? 怨쇰룄?섍쾶 以꾩씠吏 ?딄린 ?꾪븿).
    """
    if section_key != "dist":
        return False

    ttl = (title or "")
    txt = ((title or "") + " " + (desc or "")).lower()
    ttl_l = (title or "").lower()

    # ?덉쇅: ?먯삁 ?먯“湲덉? 諛섎뱶??泥댄겕(吏??린?щ씪???ㅻТ ?듭떖)
    if "?먯“湲? in txt and count_any(txt, [t.lower() for t in ("?먯삁","怨쇱닔","?뷀쎕","怨쇱씪","梨꾩냼","泥?낵","?ш낵","諛?,"媛먭랠","?멸린","怨좎텛","?ㅼ씠","?щ룄")]) >= 1:
        return False

    # ?쒕ぉ??吏???⑥쐞(??援?援???硫? ?쒓린媛 ?놁쑝硫?濡쒖뺄 ?⑥떊?쇰줈 蹂댁? ?딆쓬
    # ?? '?덉궛 ?쒖옣'泥섎읆 (吏?먯껜?? ?쒓린???덈뒗??'?덉궛??媛 ?녿뒗 耳?댁뒪媛 ?덉뼱 蹂댁셿?쒕떎.
    if (_LOCAL_REGION_IN_TITLE_RX.search(ttl) is None) and (_LOCAL_OFFICIAL_IN_TITLE_RX.search(ttl) is None):
        return False

    # ?쒕ぉ??'?뗢뿃?? ...' / '?뗢뿃援걔?..' 媛숈? ?⑥떊??援щ몢???⑦꽩?대㈃ 媛뺥븳 ?좏샇
    punct = _LOCAL_BRIEF_PUNCT_RX.search(ttl) is not None

    # 吏?먯껜 ?됱젙/怨듭????⑥뼱(吏??異붿쭊/?묒빟/紐⑥쭛...)媛 ?쒕ぉ/蹂몃Ц???덉쑝硫??⑥떊 媛?μ꽦??
    adminish_hits = count_any(txt, [t.lower() for t in _LOCAL_ADMINISH_TERMS])

    if (not punct) and adminish_hits == 0:
        # 吏???쒓린留??덈떎怨??⑥떊?쇰줈 蹂댁쭊 ?딆쓬(?ㅽ깘 諛⑹?)
        return False

    # ?쒕ぉ/蹂몃Ц???꾨ℓ쨌?좏넻 '媛??듭빱'媛 ?덉쑝硫?濡쒖뺄 ?⑥떊?쇰줈 ?⑥젙?섏? ?딆쓬
    # ?? '?뗢뿃 ?쒖옣/援곗닔 ???꾨ℓ?쒖옣 ?꾩옣媛꾨??뚯쓽/?먭?'瑜섎뒗 ?듭빱媛 ?덉뼱???ㅻТ ?듭떖?꾧? ??? ?숈젙??湲곗궗?대?濡?
    # 濡쒖뺄 ?⑥떊?쇰줈 媛꾩＜(鍮덉뭏 硫붿슦湲곗슜?쇰줈留??⑤룄濡??쒕떎.
    official_meeting = (_LOCAL_OFFICIAL_IN_TITLE_RX.search(ttl) is not None) and (count_any(txt, [t.lower() for t in _LOCAL_OFFICIAL_MEETING_TERMS]) >= 1)
    if count_any(txt, [t.lower() for t in _LOCAL_NATIONAL_LEVEL_HINTS]) >= 1:
        official_meeting = False


    # ?덉궛/?ъ엯/?ъ뾽鍮??듭썝 ??'吏?먯껜 ?ъ뾽 醫낇빀' ?⑥떊?(?뱁엳 ?듭떊쨌吏諛⑸㈃) ?좏넻 ?듭떖 ?댁뒋瑜?諛?대궡??寃쎌슦媛 留롮븘
    # ?꾨ℓ?쒖옣/怨듯뙋??寃쎈씫/?섏텧 媛숈? 媛??듭빱媛 ?쒕졆?섏? ?딆쑝硫?濡쒖뺄 ?⑥떊?쇰줈 蹂몃떎.
    if ("?ъ엯" in txt or "?덉궛" in txt or "?ъ뾽鍮? in txt or "?듭썝" in txt) and re.search(r"\d{2,5}\s*??, txt):
        strong_market = count_any(txt, [t.lower() for t in ("媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"怨듭쁺?꾨ℓ?쒖옣","寃쎈씫","寃쎈ℓ","諛섏엯","?섏텧","寃??,"?듦?")])
        if strong_market == 0 and not has_apc_agri_context(txt):
            return True

    if any(w.lower() in txt for w in _DIST_STRONG_ANCHORS):
        if not official_meeting:
            return False
    if has_apc_agri_context(txt) and (not official_meeting):
        return False
    # 怨듭쭅???숈젙 + ?뚯쓽/?먭?/諛⑸Ц?대㈃ 濡쒖뺄 ?⑥떊?쇰줈 泥섎━
    if official_meeting:
        return True

    # ?쒕ぉ???먯삁/?꾨ℓ ?좏샇媛 ?쏀븯硫?=蹂몃Ц ?쇰? ?멸툒) ?⑥떊?쇰줈 媛꾩＜
    if best_horti_score(title or "", "") < 1.6 and count_any(ttl_l, [t.lower() for t in _DIST_STRONG_ANCHORS]) == 0:
        return True

    # 洹??몃뒗 蹂댁닔?곸쑝濡?False
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
    def __init__(self):
        self.seen_norm = set()
        self.seen_canon = set()
        self.seen_press_title = set()

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
# Press mapping (??2踰? ?꾩＜?댁뒪/?ㅽ룷痢좎꽌??異붽?)
# -----------------------------
def normalize_host(host: str) -> str:
    h = (host or "").lower().strip()
    for pfx in ("www.", "m.", "mobile."):
        if h.startswith(pfx):
            h = h[len(pfx):]
    return h

PRESS_HOST_MAP = {
    # 以묒븰/寃쎌젣/?듭떊
    "yna.co.kr": "?고빀?댁뒪",
    "mk.co.kr": "留ㅼ씪寃쎌젣",
    "mt.co.kr": "癒몃땲?щ뜲??,
    "fnnews.com": "?뚯씠?몄뀥?댁뒪",
    "sedaily.com": "?쒖슱寃쎌젣",
    "hankyung.com": "?쒓뎅寃쎌젣",
    "joongang.co.kr": "以묒븰?쇰낫",
    "chosun.com": "議곗꽑?쇰낫",
    "donga.com": "?숈븘?쇰낫",
    "hani.co.kr": "?쒓꺼??,
    "khan.co.kr": "寃쏀뼢?좊Ц",
    "kmib.co.kr": "援???쇰낫",
    "seoul.co.kr": "?쒖슱?좊Ц",
    "news1.kr": "?댁뒪1",
    "newsis.com": "?댁떆??,
    "newsgn.com": "?댁뒪寃쎈궓",
    "www.newsgn.com": "?댁뒪寃쎈궓",
    "newspim.com": "?댁뒪??,
    "edaily.co.kr": "?대뜲?쇰━",
    "asiae.co.kr": "?꾩떆?꾧꼍??,
    "heraldcorp.com": "?ㅻ윺?쒓꼍??,

    # 諛⑹넚
    "kbs.co.kr": "KBS",
    "sbs.co.kr": "SBS",
    "imbc.com": "MBC",
    "ytn.co.kr": "YTN",
    "jtbc.co.kr": "JTBC",
    "mbn.co.kr": "MBN",

    # ?띿뾽/?꾨Ц吏(以묒슂)
    "nongmin.com": "?띾??좊Ц",
    "farmnmarket.com": "??留덉폆",

    # ??(異붽?) ?꾩＜?댁뒪/?꾩＜寃쎌젣
    "ajunews.com": "?꾩＜寃쎌젣",
    "ajunews.co.kr": "?꾩＜寃쎌젣",
    "ajunews.kr": "?꾩＜寃쎌젣",

    # ??(異붽?) ?ㅽ룷痢좎꽌??(co.kr 耳?댁뒪 ?ы븿)
    "sportsseoul.com": "?ㅽ룷痢좎꽌??,
    "sportsseoul.co.kr": "?ㅽ룷痢좎꽌??,

    # ??(異붽?) ?곷Ц ?꾨찓?멤넂怨듭떇 ?쒓? 留ㅼ껜紐?
    "dailian.co.kr": "?곗씪由ъ븞",
    "m.dailian.co.kr": "?곗씪由ъ븞",
    "mdilbo.com": "臾대벑?쇰낫",
    "sjbnews.com": "?덉쟾遺곸떊臾?,
    "jbnews.com": "以묐?留ㅼ씪",
    "joongdo.co.kr": "以묐룄?쇰낫",
    "gukjenews.com": "援?젣?댁뒪",

    
    # ?붿껌 留ㅼ껜(?곷Ц?믫븳湲)
    "mediajeju.com": "誘몃뵒?댁젣二?,
    "pointdaily.co.kr": "?ъ씤?몃뜲?쇰━",
    "metroseoul.co.kr": "硫뷀듃濡쒖떊臾?,
    "newdaily.co.kr": "?대뜲?쇰━寃쎌젣",
    "biz.newdaily.co.kr": "?대뜲?쇰━寃쎌젣",

    # ?뺤콉湲곌?/?곌뎄湲곌?
    "korea.kr": "?뺤콉釉뚮━??,
    "mafra.go.kr": "?띿떇?덈?",
    "at.or.kr": "aT",
    "naqs.go.kr": "?띻???,
    "krei.re.kr": "KREI",
    "agrinet.co.kr": "?쒓뎅?띿뼱誘쇱떊臾?,
    "www.agrinet.co.kr": "?쒓뎅?띿뼱誘쇱떊臾?,
    "nocutnews.co.kr": "?몄뻔?댁뒪",
    "ohmynews.com": "?ㅻ쭏?대돱??,
    "pressian.com": "?꾨젅?쒖븞",
    "hankookilbo.com": "?쒓뎅?쇰낫",
    "segye.com": "?멸퀎?쇰낫",
    "munhwa.com": "臾명솕?쇰낫",
    "dt.co.kr": "?붿??명??꾩뒪",
    "etnews.com": "?꾩옄?좊Ц",
    "zdnet.co.kr": "吏?붾꽬肄붾━??,
    "bloter.net": "釉붾줈??,
    "thebell.co.kr": "?붾꺼",
    "sisajournal.com": "?쒖궗???,
    "mediatoday.co.kr": "誘몃뵒?댁삤??,
    "aflnews.co.kr": "?띿닔異뺤궛?좊Ц",
    "www.aflnews.co.kr": "?띿닔異뺤궛?좊Ц",
    "nongup.net": "?띿뾽?뺣낫?좊Ц",
    "www.nongup.net": "?띿뾽?뺣낫?좊Ц",
}

ABBR_MAP = {
    "mk": "留ㅼ씪寃쎌젣",
    "mt": "癒몃땲?щ뜲??,
    "mbn": "MBN",
    "ytn": "YTN",
    "jtbc": "JTBC",
    "kbs": "KBS",
    "mbc": "MBC",
    "sbs": "SBS",
    "ajunews": "?꾩＜寃쎌젣",
    "sportsseoul": "?ㅽ룷痢좎꽌??,
    "dailian": "?곗씪由ъ븞",
    "mdilbo": "臾대벑?쇰낫",
    "sjbnews": "?덉쟾遺곸떊臾?,
    "jbnews": "以묐?留ㅼ씪",
    "joongdo": "以묐룄?쇰낫",
    "gukjenews": "援?젣?댁뒪",
    "agrinet": "?쒓뎅?띿뼱誘쇱떊臾?,
    "nocutnews": "?몄뻔?댁뒪",
    "ohmynews": "?ㅻ쭏?대돱??,
    "pressian": "?꾨젅?쒖븞",
    "hankookilbo": "?쒓뎅?쇰낫",
    "segye": "?멸퀎?쇰낫",
    "munhwa": "臾명솕?쇰낫",
    "dt": "?붿??명??꾩뒪",
    "etnews": "?꾩옄?좊Ц",
    "zdnet": "吏?붾꽬肄붾━??,
    "bloter": "釉붾줈??,
    "thebell": "?붾꺼",
    "sisajournal": "?쒖궗???,
    "mediatoday": "誘몃뵒?댁삤??,
    "newdaily": "?대뜲?쇰━寃쎌젣",
}

def press_name_from_url(url: str) -> str:
    host = normalize_host(domain_of(url))
    if not host:
        return "誘몄긽"

    # 1) exact
    if host in PRESS_HOST_MAP:
        return PRESS_HOST_MAP[host]

    # 2) suffix match
    for k, v in PRESS_HOST_MAP.items():
        if host.endswith("." + k):
            return v

    # 3) 2?④퀎 TLD 泥섎━(co.kr ??
    parts = host.split(".")
    if len(parts) >= 3 and parts[-1] == "kr" and parts[-2] in ("co", "or", "go", "ac", "re", "ne", "pe"):
        brand = parts[-3]
    elif len(parts) >= 2:
        brand = parts[-2]
    else:
        brand = host

    # 4) ?쎌뼱 移섑솚
    if brand in ABBR_MAP:
        return ABBR_MAP[brand]

    # 5) fallback
    # (CO ?? 理쒖긽???꾨찓??議곌컖??留ㅼ껜紐낆쑝濡??⑥뼱吏??寃쎌슦 諛⑹뼱
    if brand in ("co", "go", "or", "ne", "ac", "re", "pe", "kr", "com", "net"):
        return "誘몄긽"
    return brand.upper() if len(brand) <= 6 else brand


def normalize_press_label(press: str, url: str = "") -> str:
    """Normalize publisher labels to canonical Korean press names.

    Some feeds may provide raw/english publisher labels (e.g., "newdaily").
    Apply a small alias normalization so rendering and dedupe stay consistent.
    """
    p = (press or "").strip()
    if not p:
        return press_name_from_url(url)

    p_compact = re.sub(r"\s+", "", p.lower())
    alias = {
        "newdaily": "?대뜲?쇰━寃쎌젣",
        "?대뜲?쇰━": "?대뜲?쇰━寃쎌젣",
        "?대뜲?쇰━寃쎌젣": "?대뜲?쇰━寃쎌젣",
    }
    if p_compact in alias:
        return alias[p_compact]

    # If a hostname is passed as press label, map it via host-based normalizer.
    if "." in p and "/" not in p and " " not in p:
        try:
            return press_name_from_url("https://" + p)
        except Exception:
            return p
    return p


# -----------------------------
# Press priority (以묒슂??
# -----------------------------
MAFRA_HOSTS = {"mafra.go.kr"}
POLICY_TOP_HOSTS = {"korea.kr", "mafra.go.kr", "at.or.kr", "naqs.go.kr", "krei.re.kr"}

# (4) 以묒슂???곗꽑?쒖쐞:
#   3: 以묒븰吏/?쇨컙吏/寃쎌젣吏 + ?띾??좊Ц + 諛⑹넚??+ ?띿떇?덈?쨌?뺤콉釉뚮━??理쒖긽)
#   2: 以묒냼留ㅼ껜/吏諛⑹뼵濡??꾨Ц吏/吏?먯껜쨌?곌뎄湲곌?(以묎컙)
#   1: 洹????명꽣??湲고?)
TOP_TIER_PRESS = {
    "?멸퀎?쇰낫",
    "?고빀?댁뒪",
    "以묒븰?쇰낫", "?숈븘?쇰낫", "議곗꽑?쇰낫", "?쒓꺼??, "寃쏀뼢?좊Ц", "援???쇰낫", "?쒖슱?좊Ц",
    "留ㅼ씪寃쎌젣", "癒몃땲?щ뜲??, "?쒖슱寃쎌젣", "?쒓뎅寃쎌젣", "?뚯씠?몄뀥?댁뒪", "?대뜲?쇰━", "?꾩떆?꾧꼍??, "?ㅻ윺?쒓꼍??,
    "KBS", "MBC", "SBS", "YTN", "JTBC", "MBN",
    "?띾??좊Ц",
    "?뺤콉釉뚮━??, "?띿떇?덈?",
    # 湲곌?/怨듦났(?띿뾽 愿??
    "aT", "?띻???, "KREI",
}

MID_TIER_PRESS = {
    # ?띿뾽쨌?좏넻 ?꾨Ц/以묒냼 留ㅼ껜(?꾩슂??異붽? 媛??
    "??留덉폆",
    "?꾩＜寃쎌젣",
    # ?ㅽ룷痢좎꽌?몄? ?쒓? ?쒓린留??좎?(以묒슂?꾨뒗 ??쾶)
    "?곗씪由ъ븞",

    "?쒓뎅?띿뼱誘쇱떊臾?,
    "?띿닔異뺤궛?좊Ц",
    "?띿뾽?뺣낫?좊Ц",
    "?댁뒪1",
    "?댁떆??,
    "?댁뒪??,
}

_UGC_HOST_HINTS = ("blog.", "tistory.", "brunch.", "post.naver.", "cafe.naver.", "youtube.", "youtu.be")

def press_priority(press: str, domain: str) -> int:
    """
    3: 以묒븰吏/?쇨컙吏/寃쎌젣吏 + ?띾??좊Ц + 諛⑹넚??+ ?띿떇?덈?쨌?뺤콉釉뚮━??理쒖긽)
    2: 以묒냼留ㅼ껜/吏諛⑹뼵濡??꾨Ц吏/吏?먯껜쨌?곌뎄湲곌?(以묎컙)
    1: 洹????명꽣??湲고?)
    """
    p = (press or "").strip()
    d = (domain or "").lower()

    # 理쒖긽: ?띿떇?덈?/?뺤콉釉뚮━??諛?二쇱슂 ?띿뾽湲곌?
    if d in MAFRA_HOSTS or d.endswith(".mafra.go.kr") or p == "?띿떇?덈?":
        return 3
    if d == "korea.kr" or p == "?뺤콉釉뚮━??:
        return 3
    if d in POLICY_TOP_HOSTS or any(d.endswith("." + h) for h in POLICY_TOP_HOSTS):
        return 3
    if p in TOP_TIER_PRESS:
        return 3

    # 以묎컙: ?띿뾽?꾨Ц/以묒냼/吏諛??곌뎄쨌吏?먯껜
    if p in MID_TIER_PRESS:
        return 2
    if d.endswith(".go.kr") or d.endswith(".re.kr") or d in ALLOWED_GO_KR:
        return 2
    if p and ("諛⑹넚" in p and p not in TOP_TIER_PRESS):
        return 2

    # UGC/而ㅻ??덊떚??
    if any(h in d for h in _UGC_HOST_HINTS):
        return 1

    return 1

# -----------------------------
# Press tier/weight (?뺣? 媛以묒튂)
# - press_priority???뺣젹??3/2/1)濡??좎??섎릺, ?ㅼ퐫?댁뿉?????몃???press_weight瑜?諛섏쁺
# -----------------------------
# 理쒖긽?? 怨듭떇 ?뺤콉/湲곌? (?띿떇?덈?, ?뺤콉釉뚮━?? aT, ?띻??? KREI ??
OFFICIAL_HOSTS = {
    'korea.kr', 'mafra.go.kr', 'at.or.kr', 'naqs.go.kr', 'krei.re.kr',
    # 李멸퀬???뺤콉/?듦퀎):
    'kostat.go.kr', 'customs.go.kr', 'moef.go.kr', 'kma.go.kr',
}

# 理쒖긽???몃줎(以묒븰吏/?쇨컙吏/寃쎌젣吏/?듭떊) + 諛⑹넚 + ?띾??좊Ц
MAJOR_PRESS = {
    "?멸퀎?쇰낫",
    '?고빀?댁뒪',
    '以묒븰?쇰낫', '?숈븘?쇰낫', '議곗꽑?쇰낫', '?쒓꺼??, '寃쏀뼢?좊Ц', '援???쇰낫', '?쒖슱?좊Ц',
    '留ㅼ씪寃쎌젣', '癒몃땲?щ뜲??, '?쒖슱寃쎌젣', '?쒓뎅寃쎌젣', '?뚯씠?몄뀥?댁뒪', '?대뜲?쇰━', '?꾩떆?꾧꼍??, '?ㅻ윺?쒓꼍??,
    'KBS', 'MBC', 'SBS', 'YTN', 'JTBC', 'MBN',
    # 醫낇렪/蹂대룄梨꾨꼸 (?꾩슂??留ㅽ븨 ?뺣?)
    'TV議곗꽑', '梨꾨꼸A', '?고빀?댁뒪TV', 'OBS',
    '?띾??좊Ц',
}


BROADCAST_PRESS = {
    'KBS', 'MBC', 'SBS', 'YTN', 'JTBC', 'MBN',
    'TV議곗꽑', '梨꾨꼸A', '?고빀?댁뒪TV', 'OBS',
}

# ?듭떊/?⑤씪???댁뒪 ?쒕퉬??湲곗궗?됱씠 留롮븘 怨쇰??쒖쭛?섍린 ?ъ?): '媛?????꾨땲???덉쭏/?댁뒋濡??됯?
WIRE_SERVICES = {"?댁뒪1", "?댁떆??, "?댁뒪??}

# ?띿뾽 ?꾨Ц/?꾩옣 留ㅼ껜(?먯삁쨌?좏넻 ?ㅻТ?먯꽌 李멸퀬 媛移섍? ?믪쓬) ???덈Т 怨쇰룄?섍쾶 諛?댁＜吏??딅릺, '?섎떒 怨좎갑'??諛⑹?
AGRI_TRADE_PRESS = {"?띾??좊Ц", "?띿닔異뺤궛?좊Ц", "?띿뾽?뺣낫?좊Ц", "??留덉폆", "?쒓뎅?띿뼱誘쇱떊臾?}
AGRI_TRADE_HOSTS = {"afnews.co.kr", "agrinet.co.kr", "farmnmarket.com", "nongmin.com"}
# 以묎컙: ?띿뾽 ?꾨Ц吏/吏諛?以묒냼/?곌뎄쨌吏?먯껜
MID_PRESS_HINTS = (
    '?띿뾽', '??, '異뺤궛', '?좏넻', '?앺뭹', '寃쎈궓', '?꾨턿', '?꾨궓', '異⑸턿', '異⑸궓', '媛뺤썝', '?쒖＜',
)

LOW_QUALITY_PRESS = {
    # 吏?섏튂寃?媛???대┃ ?좊룄 ?깊뼢??媛뺥븳 寃쎌슦(?꾩슂 ??異붽?)
    # '?ъ씤?몃뜲?쇰━',
}

# 吏???(濡쒖뺄) 以?怨쇰??쒖쭛 ??泥닿컧 ?덉쭏???⑥뼱?⑤┛ ?щ?媛 ?덉뿀??留ㅼ껜??蹂꾨룄 媛먯젏/?곗뼱 ?섑뼢
REGIONAL_LOW_TIER_PRESS = {
    "?덉쟾遺곸떊臾?,
}

def press_tier(press: str, domain: str) -> int:
    """
    4: 怨듭떇 ?뺤콉/湲곌?(?띿떇?덈?, ?뺤콉釉뚮━????
    3: 以묒븰吏/?쇨컙吏/寃쎌젣吏/?듭떊 + 諛⑹넚 + ?띾??좊Ц
    2: 以묒냼/吏諛??꾨Ц吏/吏?먯껜쨌?곌뎄湲곌?
    1: 洹????명꽣??UGC/湲고?)
    """
    p = (press or '').strip()
    d = normalize_host(domain or '')
    d = (d or '').lower()

    # UGC/而ㅻ??덊떚/釉붾줈洹몃뒗 理쒗븯
    if any(h in d for h in _UGC_HOST_HINTS):
        return 1


    # ???뱀젙 濡쒖뺄 留ㅼ껜(怨쇰??쒖쭛 諛⑹?): 以묎컙 ?곗뼱 ?뚰듃? 臾닿??섍쾶 理쒗븯 ?곗뼱濡?遺꾨쪟
    if p in REGIONAL_LOW_TIER_PRESS:
        return 1
    # 怨듭떇(?뺤콉/湲곌?) ?곗꽑
    if d in OFFICIAL_HOSTS or any(d.endswith('.' + h) for h in OFFICIAL_HOSTS):
        return 4
    if p in ('?띿떇?덈?', '?뺤콉釉뚮━??, 'aT', '?띻???, 'KREI'):
        return 4

    # 二쇱슂 ?몃줎
    if p in MAJOR_PRESS:
        return 3

    # 吏?먯껜/?곌뎄湲곌?(.go.kr/.re.kr) 諛?以묎컙 ?곗뼱 ?뚰듃
    if d.endswith('.go.kr') or d.endswith('.re.kr') or d in ALLOWED_GO_KR:
        return 2
    if p in MID_TIER_PRESS:
        return 2
    if p and ('諛⑹넚' in p and p not in MAJOR_PRESS):
        return 2
    if any(h in p for h in MID_PRESS_HINTS):
        return 2

    return 1

def press_weight(press: str, domain: str) -> float:
    """?ㅼ퐫??媛以묒튂(?뺣?)."""
    t = press_tier(press, domain)
    # 湲곕낯 媛以묒튂: 怨듭떇 > 二쇱슂?몃줎 > 以묎컙 > 湲고?
    w = {4: 12.5, 3: 9.5, 2: 4.5, 1: -2.0}.get(t, -2.0)
    p = (press or '').strip()
    d = (domain or '').lower()
    # 濡쒖뺄 留ㅼ껜(?뱀젙): 湲곕낯 媛以묒튂??異붽? 媛먯젏(?듭떖 ?곷떒 ?좎떇 諛⑹?)
    if p in REGIONAL_LOW_TIER_PRESS:
        w -= 2.4

    # ?듭떊/怨듭떇? 湲곗궗 ?앹궛?됱씠 留롮븘???듭떖???믪쓬: ?쎄컙 異붽?
    if p == '?고빀?댁뒪':
        w += 0.8
    if d in ('korea.kr', 'mafra.go.kr'):
        w += 1.0

    # ?띿뾽 ?꾨Ц 留ㅼ껜??'?꾩옣 ?뺣낫' 媛移섍? ?덉뼱 ?뚰룺 媛???? 濡쒖뺄 ?⑥떊 ?꾪꽣/?꾧퀎移섎줈 怨쇰??쒖쭛 諛⑹?)
    if p in AGRI_TRADE_PRESS or normalize_host(d) in AGRI_TRADE_HOSTS:
        w += 1.2

    # ?듭떊/?⑤씪???쒕퉬?ㅻ뒗 湲곗궗?됱씠 留롮븘 ?곷떒???좎떇?섍린 ?ъ?: ?쎄컙 媛먯젏(?댁뒋 ?먯닔濡??밸?)
    if p in WIRE_SERVICES:
        w -= 0.8
    if p in LOW_QUALITY_PRESS:
        w -= 2.0
    # UGC 怨꾩뿴? 媛먯젏
    if any(h in d for h in _UGC_HOST_HINTS):
        w -= 3.0
    # ?????녿뒗 吏㏃? ?쎌뼱(釉뚮옖??濡?異붿젙?섎뒗 寃쎌슦(吏諛??명꽣???ъ쟾?? ?뚰룺 媛먯젏
    if (p == "誘몄긽") or (p.isupper() and len(p) <= 6 and p not in ("KREI", "KBS", "MBC", "SBS", "YTN", "JTBC", "MBN")):
        w -= 1.0
    return w


# -----------------------------
# Extra quality controls (?꾨찓??吏??냽???숈젙 湲곗궗 蹂댁젙)
# -----------------------------
LOW_QUALITY_DOMAINS = {
    # ?대┃/?ъ쟾??以묐났????븯???꾨찓?몃뱾(?꾩슂 ??異붽?)
    "m.sportsseoul.com", "sportsseoul.com",
    "www.onews.tv", "onews.tv",
}

def low_quality_domain_penalty(domain: str) -> float:
    d = normalize_host(domain or "")
    if not d:
        return 0.0
    if d in LOW_QUALITY_DOMAINS:
        return 3.5
    return 0.0

_LOCAL_COOP_RX = re.compile(r"[媛-??{2,10}?랁삊")

def local_coop_penalty(text: str, press: str, domain: str, section_key: str) -> float:
    """吏???⑥쐞 ?랁삊(吏??議고빀) ?숈젙??湲곗궗 媛먯젏.
    - ?띾??좊Ц? '吏??냽???뚯떇'??留롮븘 ?먯삁?섍툒 ?듭떖?먯꽌 諛?ㅼ빞 ?섎뒗 寃쎌슦媛 ?덉뼱 蹂댁젙.
    - ?? 寃쎌젣吏二?怨듯뙋???섎굹濡쒕쭏???⑤씪?몃룄留ㅼ떆????'?ㅻТ ?좏샇'媛 ?덉쑝硫?媛먯젏?섏? ?딅뒗??
    """
    t = (text or "").lower()
    # ?ㅻТ ?좏샇媛 ?덉쑝硫?媛먯젏?섏? ?딆쓬
    if any(k.lower() in t for k in NH_STRONG_TERMS) or any(k.lower() in t for k in NH_STRONG_COOCUR_TERMS):
        return 0.0
    if any(k in t for k in ("怨듯뙋??, "媛?쎌떆??, "?꾨ℓ?쒖옣", "寃쎈씫", "寃쎈씫媛", "諛섏엯", "異쒗븯", "?섍툒", "媛寃?)):
        return 0.0

    if not _LOCAL_COOP_RX.search(t):
        return 0.0

    # '?뗢뿃?랁삊' + ?됱궗/?숈젙/湲곕???湲곗궗 ?⑤꼸??
    if any(w in t for w in ("湲곕?", "?꾩썝", "遊됱궗", "?됱궗", "異뺤젣", "?쒖긽", "媛꾨떞??, "?묒쓽??, "?ㅻ챸??, "?낅Т?묒빟", "mou")):
        return 4.2 if section_key in ("supply", "dist", "policy") else 2.8

    # ?⑥닚 吏???뚯떇? ?뚰룺 媛먯젏
    return 2.0 if section_key in ("supply", "dist", "policy") else 1.2


def _sort_key_major_first(a: Article):
    # ?먯닔(愿?⑥꽦/?덉쭏)瑜?1?쒖쐞濡? 留ㅼ껜 ?곗뼱??2?쒖쐞濡?諛섏쁺
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
        import holidays  # type: ignore
        kr = holidays.KR(years=[d.year], observed=True)
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
def github_api_headers(token: str):
    return _io_github_api_headers(token)


def github_get_file(repo: str, path: str, token: str, ref: str = "main"):
    return _io_github_get_file(
        repo,
        path,
        token,
        ref=ref,
        session_factory=http_session,
        log_http_error=_log_http_error,
    )


def github_list_dir(repo: str, dir_path: str, token: str, ref: str = "main") -> list[dict]:
    """List a directory via GitHub Contents API. Returns [] on 404."""
    return _io_github_list_dir(
        repo,
        dir_path,
        token,
        ref=ref,
        session_factory=http_session,
        log_http_error=_log_http_error,
    )


def github_put_file(repo: str, path: str, content: str, token: str, message: str, sha: str = None, branch: str = "main"):
    return _io_github_put_file(
        repo,
        path,
        content,
        token,
        message,
        sha=sha,
        branch=branch,
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
# Manifest date sanitize / archive existence verification (??3~4踰? 404 諛⑹?)
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
    """理쒓렐 N媛?湲곕낯 120媛?留?GitHub???ㅼ젣 ?뚯씪 議댁옱 ?щ?瑜??뺤씤?? UI???몄텧?섎뒗 留곹겕 404瑜?諛⑹??쒕떎.
    理쒖쟻??
    - 湲곗〈: ?좎쭨留덈떎 Contents API瑜??몄텧(理쒕? verify_n踰?
    - 媛쒖꽑: docs/archive ?붾젆?곕━瑜?1??listing ??set?쇰줈 議댁옱?щ? ?뺤씤
    - listing ?ㅽ뙣 ?쒖뿉留?湲곗〈 諛⑹떇(?좎쭨蹂??뺤씤)?쇰줈 fallback
    """
    head = (dates_desc or [])[:verify_n]
    if not head:
        return []

    # ?대쾲 ?ㅽ뻾?먯꽌 ?앹꽦/?낅줈?쒗븯誘濡?議댁옱?쒕떎怨?媛꾩＜.
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

def load_state(repo: str, token: str):
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

def normalize_recent_items(recent_items, base_day: date) -> list[dict]:
    """state.recent_items瑜??쒖??뷀븯怨? base_day 湲곗? 理쒓렐 N?쇰쭔 ?④릿??"""
    if not isinstance(recent_items, list):
        return []
    cutoff = base_day - timedelta(days=max(CROSSDAY_DEDUPE_DAYS, 0))
    out: list[dict] = []
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
    # ??以묐났 ?쒓굅(理쒓렐 寃껋쓣 ?곗꽑)
    uniq = {}
    for it in sorted(out, key=lambda x: x.get("date", ""), reverse=True):
        k = it.get("norm") or it.get("canon")
        if not k:
            continue
        if k not in uniq:
            uniq[k] = it
    # ?뚯씪 ?ш린 ?쒗븳
    return list(sorted(uniq.values(), key=lambda x: x.get("date", ""), reverse=True))[:2000]


def rebuild_recent_items_for_report_date(existing_recent_items, by_section: dict | None, report_date: str, base_day: date) -> list[dict]:
    """Build cross-day dedupe history deterministically for the current report_date.

    Why:
    - 媛숈? ?좎쭨(report_date)瑜??ъ떎?됲븷 ??湲곗〈 state.recent_items???⑥븘 ?덈뜕
      "?댁쟾 ?ㅽ뻾???좏깮 寃곌낵"媛 ?욎씠硫? ?대쾲 ?ㅽ뻾 理쒖쥌 ?곗텧臾쇨낵 state媛 遺덉씪移섑븷 ???덈떎.
    - 遺덉씪移섍? ?꾩쟻?섎㈃ ?ㅼ쓬 ?ㅽ뻾?먯꽌 CROSSDAY_DEDUPE媛 ?ㅼ젣 ?몄텧?섏? ?딆? URL源뚯?
      ?대? ?몄텧??寃껋쑝濡?媛꾩＜???꾨낫瑜?怨쇱감?⑦븷 ???덈떎.

    Rule:
    1) 湲곗〈 recent_items瑜??뺢퇋??
    2) report_date ??ぉ? ?꾨? ?쒓굅(?대떦 ?쇱옄???덉뒪?좊━???ъ깮??
    3) ?대쾲 ?ㅽ뻾??理쒖쥌 by_section ?곗텧臾쇰쭔 report_date濡?異붽?
    4) ?ㅼ떆 ?뺢퇋??以묐났?쒓굅
    """
    base = normalize_recent_items(existing_recent_items if isinstance(existing_recent_items, list) else [], base_day)

    # ?ъ떎???덉젙?? ?숈씪 report_date??湲곗〈 ?붿〈 湲곕줉 ?쒓굅
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

def save_state(repo: str, token: str, last_end: datetime, recent_items: list[dict] | None = None):
    # 湲곗〈 state瑜??쎌뼱 ?ㅽ궎留??뺤옣??????명솚???좎?)
    old = load_state(repo, token)
    base_day = last_end.astimezone(KST).date()

    if recent_items is None:
        recent_items = normalize_recent_items(old.get("recent_items", []), base_day)
    else:
        recent_items = normalize_recent_items(recent_items, base_day)

    payload = {
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

def load_archive_manifest(repo: str, token: str):
    raw, sha = github_get_file(repo, ARCHIVE_MANIFEST_PATH, token, ref="main")
    if not raw:
        return {"dates": []}, sha
    try:
        return _normalize_manifest(json.loads(raw)), sha
    except Exception:
        return {"dates": []}, sha

def save_archive_manifest(repo: str, token: str, manifest: dict, sha: str):
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

        payload = {
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


def load_search_index(repo: str, token: str):
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


def save_search_index(repo: str, token: str, idx: dict, sha: str):
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


def _make_search_items_for_day(report_date: str, by_section: dict, site_path: str) -> list[dict]:
    """Build search-index items for a single report day.

    `by_section` normally contains lists of Article objects (our internal dataclass),
    but some legacy paths may pass dict-like items. Support both.
    NOTE: Keep output schema stable for index.html JS (press_tier, summary truncation, etc.).
    """
    def _get(a, key, default=""):
        if isinstance(a, dict):
            return a.get(key, default)
        return getattr(a, key, default)

    items: list[dict] = []
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

def update_search_index(existing: dict, report_date: str, by_section: dict, site_path: str) -> dict:
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
    def _date_key(d: str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return date.min

    dates_desc = sorted({x.get("date") for x in items if isinstance(x, dict) and isinstance(x.get("date"), str)}, key=_date_key, reverse=True)
    keep_dates = set(dates_desc[:MAX_SEARCH_DATES])

    items = [x for x in items if isinstance(x, dict) and x.get("date") in keep_dates]

    # sort: newer date, higher press_tier, higher score
    def _sort(x):
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


def naver_news_search(query: str, display: int = 40, start: int = 1, sort: str = "date"):
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


def naver_news_search_paged(query: str, display: int = 50, pages: int = 1, sort: str = "date") -> dict:
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
def naver_web_search(query: str, display: int = 10, start: int = 1, sort: str = "date"):
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


def section_must_terms_ok(text: str, must_terms) -> bool:
    return has_any(text, must_terms)

def policy_domain_override(dom: str, text: str) -> bool:
    if dom in POLICY_DOMAINS or dom in ALLOWED_GO_KR or dom.endswith(".re.kr"):
        return has_any(text, [k.lower() for k in AGRI_POLICY_KEYWORDS])
    return False

_LOCAL_GEO_PATTERN = re.compile(r"[媛-??{2,6}(援???援???\b")



# --- pest(蹂묓빐異?諛⑹젣) ?뺢탳?? ?띿뾽 留λ씫 ?녿뒗 "諛⑹뿭/?앺솢?댁땐" ?ㅽ깘 媛먯냼 ---
PEST_STRICT_TERMS = [
    # 蹂묓빐
    "怨쇱닔?붿긽蹂?, "?꾩?蹂?, "??퀝", "?용튆怨고뙜??, "?곌?猷⑤퀝", "?멸퇏蹂?, "?멸퇏", "諛붿씠?ъ뒪", "蹂묐컲",
    # ?댁땐
    "?댁땐", "吏꾨뵩臾?, "?묒븷", "?몃┛??, "?섎갑", "珥앹콈踰뚮젅", "?좎땐", "源띿?踰뚮젅",
    # 諛⑹젣/?덉같/?쎌젣
    "蹂묓빐異?, "諛⑹젣", "?덉같", "諛⑹젣??, "?쎌젣", "?띿빟", "?댄룷", "?댁땐", "?닿퇏", "?덉쬆",
]
PEST_WEATHER_TERMS = ["?됲빐", "?숉빐", "?쒕━", "?쒗뙆", "??⑦뵾??]
PEST_AGRI_CONTEXT_TERMS = [
    "?띿옉臾?, "?띿뾽", "?띻?", "?щ같", "怨쇱닔", "怨쇱썝", "?쒖꽕", "?섏슦??,
    "?ш낵", "諛?, "媛먭랠", "?щ룄", "?멸린", "蹂듭댂??, "怨좎텛", "?ㅼ씠", "?", "踰?,
]
PEST_HORTI_TERMS = [
    # ?먯삁/怨쇱닔/?쒖꽕梨꾩냼 以묒떖(踰?諛⑹젣 ?쒖쇅 ?먮떒??
    "?먯삁", "怨쇱닔", "怨쇱썝", "?쒖꽕", "?섏슦??, "鍮꾧?由?, "?щ같",
    "?ш낵", "諛?, "媛먭랠", "?щ룄", "?멸린", "蹂듭댂??, "?④컧", "怨띔컧", "李몃떎??, "?ㅼ쐞",
    "?ㅼ씠", "怨좎텛", "?뗪퀬異?, "?좊쭏??, "?뚰봽由ъ뭅", "?곸텛", "留덈뒛",
    "?뷀쎕", "援?솕", "?λ?",
]
PEST_RICE_TERMS = [
    # ?묎끝(踰? 蹂묓빐異?諛⑹젣(?묎끝遺 蹂꾨룄 ?댁쁺 ??遺덊븘?뷀븳 寃쎌슦媛 留롮븘 pest ?뱀뀡?먯꽌 ?쒖쇅)
    "??, "踰?, "?댁븰", "踰쇰㈇援?, "硫멸뎄", "癒밸끂由곗옱", "硫멸컯?섎갑",
    "?꾩뿴蹂?, "?곗옂留덈쫫蹂?, "?ㅻ떎由щ퀝", "?롮쭛臾대뒳留덈쫫蹂?, "以꾨Т?ъ옂留덈쫫蹂?,
]
PEST_OFFTOPIC_TERMS = [
    # ?щ엺/?꾩떆 諛⑹뿭??湲곗궗(?띿뾽怨?臾닿???寃쎌슦 李⑤떒)
    "肄붾줈??, "?낃컧", "媛먯뿼蹂?, "諛⑹뿭", "諛⑹뿭?밴뎅", "紐④린", "吏꾨뱶湲?, "留먮씪由ъ븘", "?낃린",
    # ?앺솢 ?댁땐/嫄대Ъ ?댁땐
    "諛뷀?, "?곌컻誘?, "媛쒕?",
    "蹂닿굔??, "吏덈퀝愿由ъ껌", "諛⑹뿭?뚮룆", "?뚮룆", "?뚮룆李?, "諛⑹뿭李?, "?밸퀎諛⑹뿭", "?쒕?", "二쇰?",
    "?숆탳", "?대┛?댁쭛", "?섏옄", "媛먯뿼",
]
def is_relevant(title: str, desc: str, dom: str, url: str, section_conf: dict, press: str) -> bool:
    """?뱀뀡蹂?1李??꾪꽣(愿?⑤룄/?몄씠利?而?.

    ?듭떖 紐⑺몴:
    - ?숈쓬?댁쓽??諛?諛고꽣由?諛곕떦, 諛??쇨컙 ?? ?ㅽ깘??媛뺥븯寃?李⑤떒
    - 吏諛??됱궗/?숈젙/罹좏럹?몄꽦 ?몄씠利덈? ?듭젣(?? ?좏넻쨌?꾩옣/APC/?곗??좏넻/?뷀쎕 ?꾩옣?깆? ?덉쇅 ?덉슜)
    - policy??怨듭떇 ?뚯뒪/湲곌? 湲곕컲???곗꽑
    """
    ttl = (title or "")
    desc = (desc or "")
    text = (ttl + " " + desc).lower()

    dom = normalize_host(dom or "")
    key = section_conf["key"]

    def _reject(reason: str) -> bool:
        # debug: collect why an item was filtered out
        dbg_add_filter_reject(key, reason, ttl, url, dom, press)
        return False
    # HARD BLOCK: ?⑥뒪?명뫖??鍮낅㎘/留λ룄?좊뱶 ?? 媛寃??몄긽/?몄떇 臾쇨? 湲곗궗(?띿궛臾?釉뚮━???몄씠利?
    if is_fastfood_price_context(text):
        return _reject("hardblock_fastfood_price")

    # HARD BLOCK: 援?젣?듭긽/?곗뾽 ?쇰컲 湲곗궗?먯꽌 ?띿궛臾쇱씠 遺?섏쟻?쇰줈留??깆옣?섎뒗 寃쎌슦
    if is_macro_trade_noise_context(text):
        return _reject("hardblock_macro_trade_noise")

    # HARD BLOCK: ?쇰컲 ?뚮퉬?먮Ъ媛/媛怨꾩?異??섏뿴 湲곗궗(?먯삁 ?섍툒 ?좏샇 ?쏀븿)
    if is_general_consumer_price_noise(text):
        if best_horti_score(ttl, desc) < 1.8:
            return _reject("hardblock_consumer_price_noise")

    # URL/寃쎈줈 湲곕컲 蹂댁젙(吏??濡쒖뺄 ?뱀뀡 ??
    url = (url or "").strip()
    try:
        _path = urlparse(url).path.lower()
    except Exception:
        _path = ""

    # dist(?좏넻/?꾩옣)?먯꽌 ????좏넻(諛깊솕??留덊듃) ?꾨줈紐⑥뀡??湲곗궗 李⑤떒
    # - '?꾨ℓ?쒖옣/怨듯뙋??寃쎈씫' 媛숈? ?꾨ℓ 留λ씫???놁쑝硫??좏넻(?꾨ℓ) ?뱀뀡怨?臾닿??섎?濡??쒖쇅
    if key == "dist" and is_retail_promo_context(text):
        has_wholesale = any(t.lower() in text for t in WHOLESALE_MARKET_TERMS) or ("怨듯뙋?? in text) or ("?⑤씪???꾨ℓ?쒖옣" in text)
        has_agri = any(t.lower() in text for t in ("?띿궛臾?,"?띿떇??,"?띿뾽","?먯삁","怨쇱닔","怨쇱씪","梨꾩냼","?뷀쎕","?덊솕","泥?낵"))
        if not has_wholesale:
            return _reject("dist_retail_promo_no_wholesale")
        # ?꾩＜ ?쒕Ъ寃??꾨ℓ?쒖옣 ?됱궗 湲곗궗?????덉쑝誘濡? ?꾨ℓ+?띿뾽 留λ씫???④퍡 ?덉쓣 ?뚮쭔 ?듦낵
        if not has_agri:
            return _reject("dist_retail_promo_no_agri")

    # dist: "?ㅻ뒛, ?쒖슱?? ??吏?먯껜 ?됱궗/罹좏럹?몄꽦 ?뚮┝ 湲곗궗 李⑤떒(?꾨ℓ?쒖옣 臾멸뎄媛 ?덉뼱???듭떖????쓬)
    if key == "dist":
        ttl_l2 = ttl.lower()
        if ("?ㅻ뒛, ?쒖슱?? in ttl_l2) or ("?쒖슱泥?뀈臾명솕?⑥뒪" in ttl_l2) or ("?쒖슱泥?뀈" in ttl_l2 and "?⑥뒪" in ttl_l2):
            return _reject("dist_city_notice_event")

        # ?띿궛臾쇱떆???댁쟾/?꾨????щ같移섎뒗 ?좏넻쨌?꾩옣 ?듭떖 ?댁뒋濡??곗꽑 ?덉슜
        if ("?띿궛臾? in text and "?쒖옣" in text) and any(w in text for w in ("?댁쟾", "??릿", "?댁쟾吏", "?꾨???, "?щ같移?, "?좎꽕", "媛쒖옣", "媛쒖냼")):
            return True


    # ?ㅽ뵾?덉뼵/?ъ꽕/移쇰읆? 釉뚮━????곸뿉???쒖쇅
    ttl_l = ttl.lower()
    if any(w.lower() in ttl_l for w in OPINION_BAN_TERMS):
        return _reject("opinion_or_editorial")

    # ???ш굔/??궗/?뺤튂???? ?쒖＜4.3) ?명꽣酉??ㅽ넗由щ뒗 ?먯삁 釉뚮━???듭떖 紐⑹쟻怨?臾닿??섎?濡??꾩껜 ?뱀뀡?먯꽌 諛곗젣
    if any(t in ttl_l for t in ("?쒖＜4.3", "?쒖＜4쨌3", "4.3??, "4쨌3")):
        return _reject("hardblock_jeju43_any_section")


    # 怨듯넻 ?쒖쇅(愿묎퀬/援ъ씤/遺?숈궛 ??
    if any(k in text for k in BAN_KWS):
        return _reject("ban_keywords")

    # ???쒖쇅 ?덈ぉ(?꾩옱 愿???쒖쇅): 留덈뒛/?묓뙆 ?깆? ?ㅽ겕?섑븨 ??곸뿉???쒖쇅
    if any(w in text for w in EXCLUDED_ITEMS):
        return _reject("excluded_items")
    # ??'硫쒕줎' ?숈쓬?댁쓽???뚯썝 ?뚮옯?? ?ㅽ깘 李⑤떒:
    # - '癒밸뒗 硫쒕줎' 留λ씫(?щ같/異쒗븯/?묓솴/?띻?/?꾨ℓ?쒖옣 ?????뚮쭔 ?듦낵
    if "硫쒕줎" in text and not is_edible_melon_context(text):
        return _reject("melon_non_edible_context")
    # ??'?쇰쭩' ?숈쓬?댁쓽??寃뚯엫/釉뚮옖?? ?ㅽ깘 李⑤떒:
    # - 梨꾩냼/?띿뾽 留λ씫???뚮쭔 ?듦낵
    if "?쇰쭩" in text and not is_edible_pimang_context(text):
        return _reject("pimang_non_edible_context")
    # ??'?ш낵' ?숈쓬?댁쓽???ш낵?/?ш낵臾??? ?ㅽ깘 李⑤떒: 怨쇱씪/?쒖옣 留λ씫???뚮쭔 ?듦낵
    if "?ш낵" in text and not is_edible_apple_context(text):
        return _reject("apple_non_edible_context")


    # ??異뺤궛臾??쒖슦/?쇱?怨좉린/怨꾨? ?? ?⑤룆 ?댁뒋???먯삁 釉뚮━??紐⑹쟻怨??ㅻⅤ誘濡??꾩쟾 諛곗젣
    # - ?? '?띾┝異뺤궛?앺뭹遺/?띿텞?곕Ъ' 媛숈? 以묐┰ ?쒗쁽留뚯쑝濡쒕뒗 ?ㅽ깘?섏? ?딅룄濡??대떦 臾멸뎄瑜??쒓굅 ???먮떒?쒕떎.
    _t2 = text
    for _ph in LIVESTOCK_NEUTRAL_PHRASES:
        _t2 = _t2.replace(_ph.lower(), "")
    # ?먯삁/?띿궛臾?鍮꾩텞?? ?좏샇(?먯“湲??먯껜??異뺤궛??議댁옱?섎?濡??ш린???쒖쇅)
    _horti_non_livestock = [
        "?먯삁","怨쇱닔","?뷀쎕","?덊솕","怨쇱씪","梨꾩냼","泥?낵","?쒖꽕梨꾩냼","?섏슦??,"鍮꾧?由?,
        "?ш낵","諛?,"媛먭랠","?щ룄","?멸린","怨좎텛","?ㅼ씠","?좊쭏??,"?뚰봽由ъ뭅","?곸텛",
        "?④컧","怨띔컧","李몃떎??,"?ㅼ쐞","?ㅼ씤癒몄뒪罹?,"留뚭컧","?쒕씪遊?,"?덈뱶??,"泥쒗삙??,
        "援?솕","?λ?",
    ]
    livestock_hits = count_any(_t2, [t.lower() for t in LIVESTOCK_STRICT_TERMS])
    horti_hits_pre = count_any(_t2, [t.lower() for t in _horti_non_livestock])
    horti_sc_pre = best_horti_score(ttl, desc)
    # 異뺤궛 媛뺤떊??異뺤궛臾??쒖슦/?쇱?怨좉린/怨꾨? ?? + ?먯삁 ?좏샇 嫄곗쓽 ?놁쓬 ???꾩쟾 諛곗젣
    livestock_core = ("異뺤궛臾? in _t2) or any(w in _t2 for w in ("?쒖슦","?쒕룉","?곗쑁","?덉쑁","?뚭퀬湲?,"?쇱?怨좉린","??퀬湲?,"怨꾨?","?ш?","?곗쑀","?숇냽","?묐룉","?묎퀎"))
    if livestock_core and (livestock_hits >= 1) and (horti_hits_pre == 0) and (horti_sc_pre < 1.2):
        return _reject("livestock_only")

    # ???섏궛臾??⑤룆 ?댁뒋(?λ룘/媛덉튂/?댁뾽/?묒떇 ?????먯삁 釉뚮━??紐⑹쟻怨??щ씪 諛곗젣
    _t3 = text
    for _ph in FISHERY_NEUTRAL_PHRASES:
        _t3 = _t3.replace(_ph.lower(), "")
    fishery_hits = count_any(_t3, [t.lower() for t in FISHERY_STRICT_TERMS])
    horti_hits_pre_f = count_any(_t3, [t.lower() for t in _horti_non_livestock])
    if fishery_hits >= 2 and horti_hits_pre_f == 0 and horti_sc_pre < 1.3:
        return _reject("fishery_only")

    # ?섏궛 怨좎쑀 ?댁쥌/?댁뾽 ?ㅼ썙?쒓? ?쒕ぉ??吏곸젒 ?깆옣?섍퀬 ?먯삁 ?좏샇媛 ?쏀븯硫??곗꽑 諛곗젣
    fishery_title_hits = count_any(ttl.lower(), [t.lower() for t in FISHERY_STRICT_TERMS])
    if fishery_title_hits >= 1 and best_horti_score(ttl, "") < 1.2:
        return _reject("fishery_title_only")

    # ???댁쇅 ?먯삁/?뷀쎕 ?낃퀎 '?먭꺽 ?댁쇅' 湲곗궗(援?궡 留λ씫 ?놁쓬)???ㅻТ? 嫄곕━媛 硫???쒖쇅
    if key in ("supply", "dist") and is_remote_foreign_horti(text):
        return _reject("remote_foreign_horti")


    # (誘몃━) ?먯삁/?꾨ℓ 留λ씫 ?먭?( must_terms ?덉쇅泥섎━???ъ슜 )
    horti_sc = best_horti_score(ttl, desc)

    # ??APC??UPS/?꾩썝?λ퉬 臾몃㎘?쇰줈???먯＜ ?깆옣?섎?濡? '?띿뾽/?곗??좏넻' 臾몃㎘???뚮쭔 ?몄젙?쒕떎.
    market_ctx_terms = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "寃쎈씫媛", "諛섏엯", "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣", "?곗??좏넻", "?곗??좏넻?쇳꽣"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    # (二쇱쓽) 媛寃?臾쇰웾/?ш퀬 ?깆? ?곗뾽/IT 湲곗궗?먮룄 ?뷀븳 踰붿슜 ?⑥뼱?대?濡? ?먯삁 肄붿뼱媛 ?꾨땲??'?좏샇(signal)'濡쒕쭔 ?ъ슜?쒕떎.
    supply_signal_terms = ["媛寃?, "?쒖꽭", "?섍툒", "?묓솴", "異쒗븯", "諛섏엯", "臾쇰웾", "?ш퀬", "寃쎈씫", "寃쎈씫媛", "寃쎈ℓ"]
    signal_hits = count_any(text, [t.lower() for t in supply_signal_terms])

    # ?먯삁 肄붿뼱(踰붿슜 ?⑥뼱 ?쒖쇅) ??must_terms ?ㅽ뙣 ???덉쇅(?대━湲? ?먮떒?먮쭔 ?ъ슜
    horti_core_terms = ["?먯삁", "怨쇱닔", "?뷀쎕", "?덊솕", "怨쇱콈", "?쒖꽕梨꾩냼", "?섏슦??, "鍮꾧?由?, "?щ같", "?좊퀎", "?곗??좏넻", "?곗??좏넻?쇳꽣", "?먯삁?랁삊", "怨쇱닔?랁삊", "泥?낵"]
    horti_core_hits = count_any(text, [t.lower() for t in horti_core_terms])

    # (媛뺤젣 而? ?곗뾽/湲덉쑖/諛붿씠???ㅽ깘: ?띿뾽/?먯삁 留λ씫???쏀븯硫??쒖쇅
    off_hits = count_any(text, [t.lower() for t in HARD_OFFTOPIC_TERMS])
    agri_ctx_hits = count_any(text, [t.lower() for t in ("?띿뾽", "?띿궛臾?, "?띿떇??, "?먯삁", "怨쇱닔", "怨쇱씪", "梨꾩냼", "?뷀쎕", "?덊솕")])

    # (媛뺤젣 而? ?꾨젰/?먮꼫吏/?좏떥由ы떚 '?꾨ℓ?쒖옣/?섍툒' ?숈쓬?댁쓽???ㅽ깘 李⑤떒
    energy_hits = count_any(text, [t.lower() for t in ENERGY_CONTEXT_TERMS])

    # '?꾨ℓ?쒖옣'? ?꾨젰/湲덉쑖 ?깆뿉?쒕룄 ?뷀엳 ?깆옣?섎?濡? ?띿궛臾??좏넻 ?붿뒪?곕퉬洹쒖뿉?댄꽣媛 ?놁쑝硫?蹂댁닔?곸쑝濡?李⑤떒?쒕떎.
    has_wholesale_disambig = False
    if ("?꾨ℓ?쒖옣" in text) or (market_hits > 0):
        has_wholesale_disambig = any(t in text for t in AGRI_WHOLESALE_DISAMBIGUATORS)

    # ?꾨젰/?먮꼫吏 臾몃㎘??媛뺥븳??>=2) ?띿뾽/?먯삁 臾몃㎘???꾨Т?섎㈃, '?꾨ℓ?쒖옣/?섍툒' ?⑥뼱媛 ?덉뼱??鍮꾨냽?곕Ъ濡??먮떒
    # - 媛寃??섍툒/?ш퀬 媛숈? 踰붿슜 ?⑥뼱濡?horti_sc媛 ?щ씪媛???듦낵?섏? ?딅룄濡? ?먯닔 議곌굔???먯? ?딅뒗??
    if energy_hits >= 2 and market_hits > 0 and (not has_wholesale_disambig) and agri_ctx_hits == 0 and horti_core_hits == 0:
        return _reject("energy_market_offtopic")

    # dist?먯꽌 '?꾨ℓ?쒖옣'???깆옣?덈뒗???좏넻 ?붿뒪?곕퉬洹쒖뿉?댄꽣媛 ?놁쑝硫??꾨젰/湲덉쑖 ???숈쓬?댁쓽??媛?μ꽦),
    # ?먮꼫吏 臾몃㎘??議곌툑?대씪???덇굅???띿뾽 臾몃㎘???놁쑝硫?李⑤떒?쒕떎.
    if key == "dist" and ("?꾨ℓ?쒖옣" in text) and (not has_wholesale_disambig):
        if energy_hits >= 1 or agri_ctx_hits == 0:
            return _reject("dist_wholesale_ambiguous_no_agri")

    # supply?먯꽌??'?꾨젰 ?섍툒/?먮꼫吏 媛寃? 瑜섎뒗 '?섍툒/媛寃? ?⑥뼱濡??ㅽ깘?섎?濡?而?蹂댁닔??
    if key == "supply" and energy_hits >= 2 and agri_ctx_hits == 0 and horti_core_hits == 0:
        return _reject("energy_supply_offtopic")

    if off_hits >= 2 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.6:
        return _reject("hard_offtopic_no_agri_context")

    # dist??'?좊퀎/????좏넻' 媛숈? ?⑥뼱媛 諛붿씠???섍낵??湲곗궗?먮룄 ?깆옣???꾩닔媛 ??떎.
    # ?ㅽ봽?좏뵿(諛붿씠???섍낵???뚮옯???? ?좏샇媛 1媛쒕씪???덇퀬 ?띿뾽/?쒖옣 留λ씫???놁쑝硫?媛뺥븯寃?而룻븳??
    if key == "dist" and off_hits >= 1 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 2.2:
        return _reject("dist_offtopic_no_agri_context")

    # 湲덉쑖/?곗뾽 湲곗궗(?랁삊???利앷텒/二쇨?/?ㅼ쟻 ?? ?ㅽ깘 李⑤떒
    fin_hits = count_any(text, [t.lower() for t in FINANCE_STRICT_TERMS])
    if fin_hits >= 1 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.8:
        return _reject("finance_strict_no_agri_context")

    # ?쒖슱寃쎌젣(sedaily) ??寃쎌젣吏 ?쇰컲 湲곗궗 ?ㅽ깘 諛⑹?:
    # - 寃쎌젣/?뺤콉 ?뱀뀡 寃????'?랁삊/媛寃? ?깆쓽 ?⑥뼱濡?鍮꾧???湲곗궗媛 ?욎씠??寃쎌슦媛 ?덉뼱,
    #   ?먯삁/?꾨ℓ/?뺤콉 媛뺤떊?멸? ?녿뒗 寃쎌슦??而룻븳??
    if normalize_host(dom).endswith("sedaily.com"):
        if agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.8:
            return _reject("sedaily_no_agri_context")

    # news1 濡쒖뺄(/local/) 湲곗궗 怨쇰떎 ?좎엯 諛⑹?:
    # - 'APC' 媛숈? ?⑥뼱留뚯쑝濡쒕뒗 吏???⑥떊??留롮씠 ?좎엯?섎?濡?
    #   ?꾨ℓ/?좏넻 ?명봽???좊퀎/??????臾쇰쪟/以怨?媛???? ?먮뒗 ?꾨ℓ?쒖옣 媛뺤떊?멸? ?④퍡 ?덉쓣 ?뚮쭔 ?듦낵
    if normalize_host(dom).endswith("news1.kr") and ("/local/" in _path):
        # ???먯“湲??뱁엳 ?먯삁) ?댁뒋??吏??린?щ씪??諛섎뱶??泥댄겕 ??? ?명봽???꾨ℓ ?듭빱媛 ?쏀빐???듦낵
        if "?먯“湲? in text and count_any(text, [t.lower() for t in ("?먯삁","怨쇱닔","?뷀쎕","怨쇱씪","梨꾩냼","泥?낵","?ш낵","諛?,"媛먭랠","?멸린","怨좎텛","?ㅼ씠","?щ룄")]) >= 1:
            return True
        infra_terms = ["以怨?, "?꾧났", "媛??, "?뺤땐", "?뺣?", "?좊퀎", "???, "???, "ca???, "臾쇰쪟", "?듦?", "寃??, "?섏텧", "?먯궛吏", "遺?뺤쑀??, "?⑥냽"]
        has_infra = any(t.lower() in text for t in infra_terms)
        has_wholesale = any(t in text for t in ("媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯", "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣"))
        has_apc = has_apc_agri_context(text) or ("?곗??좏넻" in text) or ("?곗??좏넻?쇳꽣" in text)

        local_ok = (market_hits >= 2) or (has_wholesale and horti_core_hits >= 2) or (has_apc and has_infra and horti_sc >= 1.6)
        if not local_ok:
            return _reject("news1_local_weak_context")

    # dist ?뱀뀡 ?뺤튂/??궗/?ш굔 ?명꽣酉곗꽦 湲곗궗 ?꾩닔 諛⑹?(蹂몃Ц ?쇰? ?띿뾽 ?멸툒?쇰줈 ?곷떒 ?좎엯?섎뒗 耳?댁뒪 李⑤떒)
    # ?? '?쒖＜4.3/?ъ깮??蹂댁긽' ???ш굔쨌?뺤튂???명꽣酉곌? /society/ 寃쎈줈濡??ㅼ뼱?ㅻŉ
    #      蹂몃Ц??'?섍툒/APC/?⑤씪???꾨ℓ?쒖옣'???쒕몢 臾몄옣 ?욎뿬 dist ?듭떖?쇰줈 ?ㅻⅤ??耳?댁뒪瑜?李⑤떒.
    if key == "dist":
        # HARD BLOCK: ?ш굔/??궗(?? ?쒖＜4.3) ?명꽣酉?湲곗궗??蹂몃Ц??APC/?섍툒 ?멸툒???욎뿬??dist???몄텧?섏? ?딅뒗??
        if any(t in ttl_l for t in ("?쒖＜4.3", "?쒖＜4쨌3", "4.3??, "4쨌3")):
            return _reject("dist_hardblock_jeju43")

        # 援??? ?⑥쐞 吏???⑥떊/?됱젙 ?숈젙??湲곗궗 ?듭젣:
        # - ?쒕ぉ???뗢뿃援?援곗껌/援곗닔 ??吏諛??됱젙 ?좏샇媛 ?덇퀬,
        # - ?쒕ぉ???꾨ℓ/?좏넻 ?듭빱媛 ?녾퀬,
        # - 蹂몃Ц?먮룄 ?꾨ℓ/?좏넻 ?ㅻТ ?좏샇媛 ?쏀븯硫?dist?먯꽌 ?쒖쇅
        _countyish = (re.search(r"[媛-??{2,}援?, ttl) is not None) or ("援곗껌" in ttl_l) or ("援곗닔" in ttl_l)
        if _countyish:
            _title_dist_anchor = count_any(ttl_l, [t.lower() for t in (
                "?꾨ℓ?쒖옣", "怨듯뙋??, "媛?쎌떆??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                "?꾨ℓ踰뺤씤", "以묐룄留?, "?쒖옣?꾨ℓ??,
                "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc",
                "臾쇰쪟", "???, "???, "?좊퀎", "吏묓븯", "異쒗븯", "?⑤씪???꾨ℓ?쒖옣",
                "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧"
            )])
            if (_title_dist_anchor == 0) and (market_hits == 0) and (not has_apc_agri_context(text)):
                return _reject("dist_county_local_weak_dist_signal")


        horti_title_sc = best_horti_score(ttl, "")

        # ?쒕ぉ 湲곕컲 ?듭빱(?꾨ℓ/?좏넻/?띿뾽) ???쒕ぉ???듭빱媛 ?놁쑝硫?'蹂몃Ц ?쇰? ?멸툒' ?ㅽ깘 媛?μ꽦???믩떎.
        dist_anchor_in_title = count_any(ttl_l, [t.lower() for t in (
            "?꾨ℓ?쒖옣", "怨듯뙋??, "媛?쎌떆??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
            "?꾨ℓ踰뺤씤", "以묐룄留?, "?쒖옣?꾨ℓ??,
            "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc",
            "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧", "?먯“湲?
        )])
        agri_anchor_in_title = count_any(ttl_l, [t.lower() for t in (
            "?띿궛臾?, "?띿뾽", "?띿떇??, "?먯삁", "怨쇱닔", "怨쇱씪", "梨꾩냼", "?뷀쎕", "?덊솕", "泥?낵",
            "?ш낵", "諛?, "媛먭랠", "?멸린", "怨좎텛", "?ㅼ씠", "?щ룄", "?붾룞梨꾩냼"
        )])

        # (媛? ?ш굔/?뺤튂/??궗 ?댁뒋媛 ?쒕ぉ???덉쑝硫? 蹂몃Ц???쒖옣 ?ㅼ썙?쒓? ?욎뿬??dist?먯꽌 ?쒖쇅(?듭떖/鍮꾪빑??紐⑤몢 李⑤떒)
        # - '?쒖＜4.3' 媛숈? 紐낅갚???ш굔 ?ㅼ썙?쒕뒗 dist ?듭떖?쇰줈 ?덈? ?щ━硫?????
        hard_politics_terms = (
            "?쒖＜4.3", "?쒖＜4쨌3", "4.3??, "4쨌3", "?ъ깮??, "異붾え", "蹂댁긽",
            "?꾪빑", "怨꾩뾼", "?대?", "李몄궗", "?밸퀎踰?
        )
        hard_hits = count_any(ttl_l, [t.lower() for t in hard_politics_terms])
        if hard_hits >= 1 and ("/society/" in _path or "/politics/" in _path or "/the300/" in _path):
            if dist_anchor_in_title == 0 and agri_anchor_in_title == 0:
                return _reject("dist_politics_hard_title")

        # (?? ?뺤튂/?ш굔???⑥뼱媛 ?덇퀬 ?쒕ぉ ?듭빱媛 留ㅼ슦 ?쏀븯硫??쒖옣 留λ씫???놁쑝硫?dist?먯꽌 ?쒖쇅
        politics_title_terms = (
            "4.3", "?쒖＜4.3", "?ъ깮??, "蹂댁긽", "異붾え", "?대?", "?꾪빑", "怨꾩뾼", "?뺣떦", "珥앹꽑", "???, "援?쉶",
            "寃李?, "?ы뙋", "?좉퀬", "援ъ냽", "湲곗냼", "?밸퀎踰?, "?ш굔", "李몄궗"
        )
        politics_hits = count_any(ttl_l, [t.lower() for t in politics_title_terms])
        if politics_hits >= 1 and ("/society/" in _path or "/politics/" in _path or "/the300/" in _path):
            if dist_anchor_in_title == 0 and agri_anchor_in_title == 0 and horti_title_sc < 1.3 and market_hits == 0:
                return _reject("dist_politics_heavy_title")


    # 吏???숈젙/湲곌툑?꾨떖(?뱁엳 ?뗢뿃?랁삊 + 諛쒖쟾湲곌툑/?ν븰湲??? ?ㅽ깘 ?쒓굅
    if _LOCAL_COOP_RX.search(text) and any(w.lower() in text for w in COMMUNITY_DONATION_TERMS):
        hard_ctx_terms = ["媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"寃쎈씫","寃쎈ℓ","諛섏엯","以묐룄留ㅼ씤","?쒖옣?꾨ℓ??,"?섏텧","寃??,"?듦?","?먯궛吏","?⑥냽","遺?뺤쑀??,"?섍툒","媛寃?,"?쒖꽭","異쒗븯","?ш퀬","???,"?좊퀎","???,"臾쇰쪟"]
        hard_hits = count_any(text, [t.lower() for t in hard_ctx_terms])
        if hard_hits == 0 and horti_sc < 2.4:
            return _reject("local_coop_donation")

    # ?뺤콉 ?뱀뀡留??뺤콉湲곌?/怨듦났 ?꾨찓???덉슜(?? 諛⑹젣(pest)??吏諛??댁뒋媛 留롮븘 ?덉쇅 ?덉슜)
    # ??(5) pest ?뱀뀡? 吏?먯껜/?곌뎄湲곌?(.go.kr/.re.kr) 湲곗궗???덉슜
    # ?뺤콉/湲곌? ?꾨찓?몄? ?ㅻⅨ ?뱀뀡?먯꽌 ?섏쭛?????덉쑝?? 理쒖쥌?곸쑝濡?policy ?뱀뀡?쇰줈 媛뺤젣 ?쇱슦?낇븳??
    # ?곕씪???ш린??而룻븯吏 ?딅뒗???꾨씫 諛⑹?). ?? ?쇰컲 .go.kr/.re.kr? ?몄씠利덇? 留롮븘 湲곗〈泥섎읆 李⑤떒.
    if dom in POLICY_DOMAINS and key not in ("policy", "pest"):
        return True

    if (
        dom in ALLOWED_GO_KR
        or dom.endswith(".re.kr")
        or dom.endswith(".go.kr")
    ) and key not in ("policy", "pest"):
        return False

    # ?뱀뀡 must-term ?듦낵 ?щ?(?? supply/dist??'媛뺥븳 ?먯삁/?꾨ℓ 留λ씫'?대㈃ ?덉쇅 ?덉슜)
    if not section_must_terms_ok(text, section_conf["must_terms"]):
        if key == "policy":
            # 蹂묓빐異??ㅽ뻾??臾몃㎘? policy ?섏쭛 ?④퀎?먯꽌 ?꾨씫?쒗궎吏 ?딅뒗???꾨떒?먯꽌 pest濡??대룞).
            if is_pest_control_policy_context(text):
                pass
            # policy???꾨찓??override媛 ?덉쓬
            elif not policy_domain_override(dom, text):
                return _reject("must_terms_fail_policy")
        else:
            # supply/dist?먯꽌 APC/?곗??좏넻/?뷀쎕 ?꾩옣?깆씠 媛뺥븯硫?must_terms 誘명넻怨쇰씪???대┛??
            dist_soft_ok = (market_hits >= 1) or has_apc_agri_context(text) or ("?곗??좏넻?쇳꽣" in text) or ("?먯삁?랁삊" in text) or ("?뷀쎕" in text) or ("?덊솕" in text) or ("?먯“湲? in text)
            if key == "dist":
                if (("?좏넻" in text) or ("?꾨ℓ" in text) or ("異쒗븯" in text) or ("?섏뿭" in text) or ("臾쇰쪟" in text)) and (horti_sc >= 1.8 or agri_ctx_hits >= 1):
                    dist_soft_ok = True
            if not ((horti_sc >= 2.0) or (horti_core_hits >= 3) or dist_soft_ok):
                return _reject("must_terms_fail")

    # (?듭떖) ?먯삁?섍툒 愿?⑥꽦 寃뚯씠??
    # - ?ㅼ씠踰?寃??荑쇰━???숈쓬?댁쓽??諛?諛고꽣由?諛곕떦, 諛??쇨컙 ??濡??명븳 ?ㅽ깘??媛뺥븯寃?李⑤떒
    if key == "supply":
        # 怨듦툒(supply) ?뱀뀡? '踰붿슜 ?⑥뼱(媛寃?臾쇰웾/?ш퀬)'留??덈뒗 ?곗뾽/IT 湲곗궗瑜?媛뺥븯寃?李⑤떒?쒕떎.
        # ?듦낵 議곌굔(??):
        # - ?덈ぉ/?먯삁 ?먯닔(horti_sc)媛 異⑸텇??媛뺥븿
        # - ?꾨ℓ/?곗??좏넻/?쒖옣 留λ씫(market_hits) 議댁옱
        # - ?띿뾽/?띿궛臾?留λ씫(agri_ctx_hits) + ?섍툒 ?좏샇(signal_hits) ?숈떆 議댁옱
        supply_ok = (horti_sc >= 1.3) or (market_hits >= 1) or (agri_ctx_hits >= 1 and signal_hits >= 1)
        if not supply_ok:
            return _reject("supply_context_gate")

        # URL??IT/?뚰겕 ?뱀뀡?몃뜲 ?띿뾽/?쒖옣 留λ씫???쏀븯硫?而?踰붿슜 ?⑥뼱 ?ㅽ깘 諛⑹?)
        if any(p in _path for p in ("/it/", "/tech/", "/future/", "/science/", "/game/", "/culture/")):
            if agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 2.2:
                return _reject("supply_tech_path_no_agri")

    # ?뺤콉(policy): 怨듭떇 ?꾨찓???뺤콉釉뚮━?묒씠 ?꾨땶 寃쎌슦 '?띿떇???띿궛臾?留λ씫' ?꾩닔 + 寃쎌젣/湲덉쑖 ?뺤콉 ?ㅽ깘 李⑤떒
    if key == "policy":
        # 蹂묓빐異??ㅽ뻾??湲곗궗???섏쭛 ?④퀎?먯꽌 ?꾨씫?쒗궎吏 ?딄퀬 ?꾨떒 ?щ텇瑜??뺣━?먯꽌 pest濡?蹂대궦??
        if is_pest_control_policy_context(text):
            return True

        is_official = policy_domain_override(dom, text) or (normalize_host(dom) in OFFICIAL_HOSTS) or any(normalize_host(dom).endswith("." + h) for h in OFFICIAL_HOSTS)

        if not is_official:
            # ?뚮ℓ 留ㅼ텧/?먮ℓ ?곗씠??湲곕컲 ?몃젋??湲곗궗??policy媛 ?꾨땲??supply濡?蹂대궡??寃껋씠 ?먯뿰?ㅻ읇??
            if is_retail_sales_trend_context(text):
                return _reject("policy_retail_sales_trend")
            policy_signal_terms = ["媛寃??덉젙", "?깆닔??, "?좎씤吏??, "?좊떦愿??, "寃??, "?먯궛吏", "?섏엯", "?섏텧", "愿??, "?꾨ℓ?쒖옣", "?⑤씪???꾨ℓ?쒖옣", "?좏넻", "?섍툒"]
            agri_base = count_any(text, [t.lower() for t in ("?띿떇??, "?띿궛臾?, "?띿뾽")])
            sig = count_any(text, [t.lower() for t in policy_signal_terms])
            if not ((horti_sc >= 1.4) or (market_hits >= 1) or (agri_base >= 1 and sig >= 1)):
                return _reject("policy_context_gate")

        # 湲덉쑖/?곗뾽 ?쇰컲 ?뺤콉 ?ㅽ깘 李⑤떒
        policy_off = ["湲덈━", "二쇳깮", "遺?숈궛", "肄붿뒪??, "肄붿뒪??, "二쇱떇", "梨꾧텒", "媛?곸옄??, "?먰솕", "?섏쑉", "諛섎룄泥?, "諛고꽣由?]
        if any(w in text for w in policy_off):
            if not ((horti_sc >= 1.8) or (market_hits >= 1) or ("?띿궛臾? in text and "媛寃? in text)):
                return _reject("policy_offtopic_gate")

        # ?앺뭹?덉쟾/?꾩깮 ?⑤룆 ?댁뒋???먯삁?섍툒怨?嫄곕━媛 ?덉뼱 ?쒖쇅
        # (?? ?꾨ℓ?쒖옣/?먯궛吏 ?⑥냽/寃????'?좏넻쨌?⑥냽'怨?吏곸젒 寃고빀?섍굅??
        #  ?덈ぉ/?섍툒 ?좏샇媛 留ㅼ슦 媛뺥븷 ?뚮쭔 ?덉슜)
        safety_terms = ["?앺뭹?덉쟾", "?꾩깮", "haccp", "?앹쨷??, "?쒖떆湲곗?", "?좏넻湲고븳", "?뚮젅瑜닿린"]
        if any(w in text for w in safety_terms):
            safety_ok = False
            if market_hits >= 2:
                safety_ok = True
            if (("?먯궛吏" in text) or ("遺?뺤쑀?? in text) or ("?⑥냽" in text) or ("寃?? in text)) and market_hits >= 1:
                safety_ok = True
            if (horti_sc >= 2.6) and ("?띿궛臾? in text) and (("媛寃? in text) or ("?섍툒" in text) or ("異쒗븯" in text)):
                safety_ok = True
            if not safety_ok:
                return _reject("policy_food_safety_only")
            # ?곷냽遺?곕Ъ/?뚯뇙 ???됱젙???ъ뾽 ?덈궡???먯삁?섍툒 釉뚮━?묒뿉???쒖쇅(???놁쓣 ?뚮룄 援녹씠 梨꾩슦吏 ?딆쓬)
            admin_terms = ["?곷냽遺?곕Ъ", "?덉쟾泥섎━", "?뚯뇙", "?뚯뇙湲?, "?뚭컖", "?붽?吏"]
            if any(w in text for w in admin_terms):
                if market_hits == 0 and horti_sc < 2.2:
                    return _reject("policy_admin_notice")


        # ?뺤콉 ?뱀뀡: 吏諛??됱궗??吏???⑥떊??媛뺥븯寃?諛곗젣(二쇱슂 留ㅼ껜???쇰? ?덉슜)
        is_major = press_priority(press, dom) >= 2
        if (not is_major) and _LOCAL_GEO_PATTERN.search(ttl):
            return _reject("policy_local_minor")

    # ?좏넻/?꾩옣(dist): '?띿궛臾??먯삁 ?좏넻' 留λ씫???녿뒗 ?쇰컲 臾쇰쪟/?좏넻/釉뚮옖??湲곗궗??媛뺥븯寃?李⑤떒
    if key == "dist":
        agri_anchor_terms = ("?띿궛臾?, "?띿뾽", "?띿떇??, "?먯삁", "怨쇱닔", "怨쇱씪", "梨꾩냼", "?뷀쎕", "?덊솕", "泥?낵")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])

        # ?뚰봽???섎뱶 ?좏샇 遺꾨━(?쇰컲?? 釉뚮옖???듯빀/議고솕/苑??깆? ?쒓굅)
        dist_soft = ["?곗??좏넻", "?곗??좏넻?쇳꽣", "?먯삁?랁삊", "怨쇱닔?랁삊", "?먮ℓ?랁삊", "?묐ぉ諛?, "?뷀쎕", "?덊솕", "?먯“湲?, "?섎굹濡쒕쭏??, "?⑤씪???꾨ℓ?쒖옣", "?좏넻", "?꾨ℓ", "?꾨ℓ踰뺤씤", "?섏뿭", "?섏뿭鍮?, "?섏뿭??", "異쒗븯", "吏묓븯", "臾쇰쪟?쇳꽣"]
        dist_hard = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣", "泥?낵", "寃쎈씫", "寃쎈씫媛", "寃쎈ℓ", "諛섏엯",
                     "?꾨ℓ踰뺤씤", "?섏뿭", "?섏뿭鍮?, "?섏뿭??", "異쒗븯",
                     "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??,
                     "?좊퀎", "???, "??⑥???, "??κ퀬", "ca???, "臾쇰쪟",
                     "?먯궛吏", "遺?뺤쑀??, "?⑥냽",
                     "寃??, "?듦?", "?섏텧"]
        soft_hits = count_any(text, [t.lower() for t in dist_soft])
        hard_hits = count_any(text, [t.lower() for t in dist_hard])

        # APC???띿뾽 臾몃㎘???뚮쭔 soft ?좏샇濡?移댁슫??
        apc_ctx = has_apc_agri_context(text)
        if apc_ctx:
            soft_hits += 1

        # ?띿궛臾??쒖옣 ?댁쟾/?꾨????щ같移??깃꺽 湲곗궗???좏넻쨌?꾩옣?쇰줈 ?덉슜
        relocation_hint = any(w in text for w in ("?댁쟾", "??릿", "?댁쟾吏", "?꾨???, "?щ같移?, "?좎꽕", "媛쒖옣", "媛쒖냼"))
        agri_market_relocation = ("?띿궛臾? in text and "?쒖옣" in text and relocation_hint)

        if (soft_hits + hard_hits) < 1 and (not agri_market_relocation):
            return _reject("dist_context_gate")

        # ??媛??以묒슂???먯튃: '?띿궛臾??먯삁' ?듭빱媛 ?녾퀬(agri_anchor_hits==0),
        # ?꾨ℓ?쒖옣/?곗??좏넻/?덈ぉ ?먯닔???쏀븯硫??쇰컲 臾쇰쪟/寃쎌젣 湲곗궗濡?蹂닿퀬 而?
        if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 1.6:
            return _reject("dist_no_agri_anchor")

        # ?섏텧/寃???먯궛吏 ?⑥냽 ??'?댁쁺/吏묓뻾' ?ㅼ썙?쒕쭔?쇰줈 嫄몃┛ ?쇰컲 湲곗궗 李⑤떒
        dist_ops_terms = ["?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧"]
        dist_market_terms = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣", "泥?낵", "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                             "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣", "?곗??좏넻", "?곗??좏넻?쇳꽣"]
        ops_hits = count_any(text, [t.lower() for t in dist_ops_terms])
        title_market_hits = count_any(ttl.lower(), [t.lower() for t in dist_market_terms])
        title_ops_hits = count_any(ttl.lower(), [t.lower() for t in dist_ops_terms])

        if (ops_hits >= 1 and hard_hits >= 1 and market_hits == 0 and (not apc_ctx)
                and agri_anchor_hits == 0 and horti_sc < 1.9 and title_market_hits == 0):
            return _reject("dist_ops_only_generic")

        # 諛⑹넚/醫낇빀吏 吏??떒?좎씠 dist濡??좎엯?섎뒗 寃쎌슦 異붽? 李⑤떒(?ㅼ젣 ?꾨ℓ/APC/?섏텧 ?꾩옣 ?좏샇媛 ?쏀븷 ??
        if ((press or "").strip() in BROADCAST_PRESS and _LOCAL_GEO_PATTERN.search(ttl)):
            if market_hits == 0 and (not apc_ctx) and horti_sc < 2.1 and title_market_hits == 0 and title_ops_hits <= 1:
                return _reject("dist_local_broadcast_weak")

        # URL??IT/?뚰겕 ?뱀뀡?몃뜲 ?띿뾽 留λ씫???쏀븯硫?而?
        if any(p in _path for p in ("/it/", "/tech/", "/future/", "/science/", "/game/", "/culture/")):
            if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 2.2:
                return _reject("dist_tech_path_no_agri")

        # '?곗??좏넻/APC/?랁삊/?뷀쎕' 媛숈? ?뚰봽???좏샇留??덉쓣 ??
        # ?명봽???좏넻 媛뺤떊??以怨?媛???좊퀎/??????臾쇰쪟/?먯궛吏/寃???섏텧 ?? + ?띿뾽 ?듭빱/?덈ぉ ?좏샇媛 ?④퍡 ?덉뼱???듦낵
        if hard_hits == 0:
            infra_terms = ("以怨?, "?꾧났", "媛??, "?뺤땐", "?뺣?", "?좊퀎", "???, "??⑥???, "??κ퀬", "ca???, "臾쇰쪟", "?먯궛吏", "寃??, "?섏텧")
            has_infra = any(w in text for w in infra_terms)

            # soft-only??(?명봽??+ (?띿뾽?듭빱 or ?덈ぉ?먯닔)) ?먮뒗 (?덈ぉ?먯닔 留ㅼ슦 媛뺥븿 + soft 2媛??댁긽)?먯꽌留??덉슜
            if not ((has_infra and (agri_anchor_hits >= 1 or horti_sc >= 1.9 or apc_ctx)) or (horti_sc >= 2.8 and soft_hits >= 2)):
                return _reject("dist_soft_without_infra")
# 蹂묓빐異?諛⑹젣(pest) ?뱀뀡 ?뺢탳?? ?띿뾽 留λ씫 ?녿뒗 諛⑹뿭/?앺솢?댁땐/踰?諛⑹젣 ?ㅽ깘 ?쒓굅 + ?좏샇 媛뺣룄 議곌굔
    if key == "pest":
        agri_ctx_hits = count_any(text, [t.lower() for t in PEST_AGRI_CONTEXT_TERMS])
        if agri_ctx_hits < 1:
            return _reject("pest_no_agri_context")

        rice_hits = count_any(text, [t.lower() for t in PEST_RICE_TERMS])
        strict_hits = count_any(text, [t.lower() for t in PEST_STRICT_TERMS])
        weather_hits = count_any(text, [t.lower() for t in PEST_WEATHER_TERMS])
        horti_hits = count_any(text, [t.lower() for t in PEST_HORTI_TERMS])

        # 踰?蹂묓빐異⑹? ?먯삁?섍툒遺? 嫄곕━媛 硫??湲곕낯 ?쒖쇅(?먯삁 ?좏샇 ?숇컲 ?쒕쭔 ?덉슜)
        if rice_hits >= 1 and horti_hits == 0:
            return _reject("pest_rice_only")

        # 諛⑹젣/蹂묓빐異??좏샇媛 ?덈Т ?쏀븯硫??쒖쇅
        if (strict_hits + weather_hits) < 1:
            return False

    return True

def compute_rank_score(title: str, desc: str, dom: str, pub_dt_kst: datetime, section_conf: dict, press: str) -> float:
    """以묒슂???ㅼ퐫??
    紐⑺몴:
    - ?먯삁?섍툒(怨쇱닔/?뷀쎕/?쒖꽕梨꾩냼) ?ㅻТ??吏곸젒 ?곹뼢??二쇰뒗 ?섏궗寃곗젙 ?좏샇(媛寃?臾쇰웾/?梨?寃??諛⑹젣)瑜?理쒖슦??
    - ?몃줎留ㅼ껜 媛以묒튂: 怨듭떇(?뺤콉/湲곌?) > 以묒븰쨌?쇨컙쨌寃쎌젣쨌諛⑹넚쨌?띾??좊Ц > 以묒냼/吏諛?> ?명꽣??
    - ?랁삊(寃쎌젣吏二?怨듯뙋???섎굹濡??⑤씪?몃룄留? 愿?⑥꽦 諛섏쁺
    - 吏諛?諛⑹젣/?묒쓽???됱궗??湲곗궗 ?곷떒 諛곗튂 ?듭젣 + 以묐났 ?댁뒋 ?듭젣
    """
    text = (title + " " + desc).lower()
    title_l = (title or "").lower()

    # (?듭떖) ?먯삁?섍툒/?덈ぉ ?좏샇 ?먯닔(?덈ぉ ?쇰꺼 + ?ㅽ깘 ?듭젣)
    horti_sc = best_horti_score(title, desc)
    key_strength = keyword_strength(text, section_conf) if SCORING_KEYWORD_STRENGTH_BOOST_ENABLED else 0
    market_ctx_terms = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "寃쎈씫媛", "諛섏엯", "?⑤씪???꾨ℓ?쒖옣", "?곗??좏넻", "?곗??좏넻?쇳꽣"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    strength = agri_strength_score(text)
    korea = korea_context_score(text)
    offp = off_topic_penalty(text)

    # 湲곕낯: 媛뺤떊???먯삁?섍툒/?좏넻/?뺤콉/諛⑹젣) 湲곕컲
    score = 0.0
    score += 0.55 * strength
    score += 0.25 * korea
    score -= 0.70 * offp
    if SCORING_TITLE_SIGNAL_BONUS_ENABLED:
        score += title_signal_bonus(title)



    # trade_policy_core_boost: ?덈ぉ(?좏뵿) + 臾댁뿭/?뺤콉(愿??FTA/?듦?/?섏엯) + ?곹뼢(?섍툒/媛寃??좎떇 ?? 議고빀?대㈃ ?듭떖??媛??
    trade_terms = ("愿??, "?좊떦愿??, "臾닿???, "fta", "?듦?", "蹂댁꽭", "?섏엯", "寃??)
    impact_terms = ("?섍툒", "媛寃?, "臾쇰웾", "?좎떇", "寃쎌웳", "?寃?, "遺異?, "?뺣컯", "湲됰벑", "湲됰씫")
    if any(x in text for x in trade_terms) and any(x in text for x in impact_terms):
        if any(_term in text for _tn,_terms in TOPICS for _term in _terms[:3]):
            score += 1.6
    # 吏諛?"?멸뎄媛먯냼/?앺솢?멸뎄" ?덉궛 湲곗궗(?먯삁 ?ㅼ썙?쒓? ?욎뿬???듭떖????쓬) 媛먯젏
    if ("?멸뎄媛먯냼" in text) or ("?앺솢?멸뎄" in text):
        score -= 6.0
    # "?ㅻ뒛, ?쒖슱??瑜??뚮┝??湲곗궗 媛먯젏
    if ("?ㅻ뒛, ?쒖슱?? in title_l) or ("?쒖슱泥?뀈臾명솕?⑥뒪" in title_l):
        score -= 1.8
    
    # -----------------------------
    # Generalized boost: '?먯삁 ?덈ぉ ?좏샇' + '臾댁뿭/?뺤콉(愿??臾닿???FTA/?섏엯/?듦?/寃????' + '?쒖옣 ?곹뼢' 議고빀
    # ?뱀젙 湲곗궗 ?섎굹瑜??꾪빐 ?ㅼ썙?쒕? 異붽??섎뒗 諛⑹떇???꾨땲??
    # ?꾨컲?곸쑝濡?"?섏엯/愿???댁뒋媛 ?덈ぉ ?섍툒??誘몄튂???곹뼢" 湲곗궗?ㅼ쓣 ?????뚯뼱?щ━湲??꾪븳 洹쒖튃?대떎.
    horti_hits = count_any(text, ALL_TOPIC_TERMS_L)
    trade_hits = count_any(text, TRADE_POLICY_TERMS_L)
    impact_hits = count_any(text, TRADE_IMPACT_TERMS_L)

    if horti_hits > 0 and trade_hits > 0:
        score += 1.6 + min(1.2, 0.35 * trade_hits)
        if impact_hits > 0:
            score += 1.0

# ?뱀뀡蹂??ㅼ썙??媛以묒튂
    key = section_conf["key"]

    # ?뱀뀡 must_terms瑜??먯닔???뚰룺 諛섏쁺(?쒕ぉ ?덊듃 ?곗꽑)???뱀뀡 ?곹빀?꾨? ?덉젙??
    must_terms_l = _section_must_terms_lower(section_conf)
    if must_terms_l:
        must_title_hits = count_any(title_l, must_terms_l)
        must_text_hits = count_any(text, must_terms_l)
        score += min(1.8, (0.35 * must_title_hits) + (0.12 * must_text_hits))

    if key == "supply":
        score += weighted_hits(text, SUPPLY_WEIGHT_MAP)
        score += min(2.2, 0.25 * key_strength)
        score += count_any(title_l, [t.lower() for t in SUPPLY_TITLE_CORE_TERMS]) * 1.2
        # 吏?먯껜 ?뺤콉 ?꾨줈洹몃옩(異쒗븯鍮꾩슜 蹂댁쟾/?쒕쾾?ъ뾽 ??? supply蹂대떎 policy ?깃꺽??媛뺥븿
        if is_local_agri_policy_program_context(text):
            score -= 4.0
    elif key == "dist":
        score += weighted_hits(text, DIST_WEIGHT_MAP)
        score += min(2.0, 0.22 * key_strength)
        score += count_any(title_l, [t.lower() for t in DIST_TITLE_CORE_TERMS]) * 1.2
        # 吏?먯껜 ?뺤콉 ?꾨줈洹몃옩??湲곗궗(蹂댁쟾/吏???쒕쾾?ъ뾽)??dist蹂대떎 policy ?곗꽑
        if is_local_agri_policy_program_context(text):
            score -= 2.0
        # ???띿뾽 ?꾨Ц/?꾩옣 留ㅼ껜??'?쒖옣 ?꾩옣/?紐⑹옣' 由ы룷?몃뒗 ?좏넻(?꾩옣) ?ㅻТ 泥댄겕 媛移섍? ?믩떎.
        # - ?꾨ℓ?쒖옣/APC ?ㅼ썙?쒓? ?놁뼱??'?꾩옣/?紐⑹옣/?먮ℓ' 留λ씫?대㈃ ?먯닔瑜?蹂닿컯???섎떒 怨좎갑??諛⑹??쒕떎.
        if press in AGRI_TRADE_PRESS or normalize_host(dom) in AGRI_TRADE_HOSTS:
            if has_any(title_l, ["?紐⑹옣", "?紐?, "?꾩옣", "?대븷??, "?먮ℓ", "?쒖옣", "諛섏쓳"]):
                score += 3.2

        # dist?먯꽌 '吏?먯껜 怨듭?/吏???⑥떊'?쇰줈 ?먯젙?섎㈃ ?먯닔 媛먯젏(?꾩닚??鍮덉뭏硫붿슦湲곗슜)
        if is_local_brief_text(title, desc, "dist"):
            score -= 3.5

    elif key == "policy":
        score += weighted_hits(text, POLICY_WEIGHT_MAP)
        score += min(1.8, 0.20 * key_strength)
        score += count_any(title_l, [t.lower() for t in POLICY_TITLE_CORE_TERMS]) * 1.2
        # ?꾨ℓ?쒖옣/?띿궛臾쇱떆???명봽???댁쟾 ?댁뒋???뺤콉蹂대떎 ?좏넻 ?깃꺽????媛뺥븯誘濡?policy 媛먯젏
        if ("?띿궛臾? in text and "?쒖옣" in text) and any(w in text for w in ("?댁쟾", "??릿", "?댁쟾吏", "?꾨???, "?щ같移?, "?좎꽕", "媛쒖옣", "媛쒖냼")):
            score -= 2.8
        # 吏?먯껜???띿궛臾??뺤콉 ?꾨줈洹몃옩(吏??蹂댁쟾/?쒕쾾?ъ뾽)? policy ?곗꽑
        if is_local_agri_policy_program_context(text):
            score += 6.4
        # 怨듭떇 ?뺤콉 ?뚯뒪 異붽? 媛??
        if normalize_host(dom) in OFFICIAL_HOSTS or press in ("?띿떇?덈?", "?뺤콉釉뚮━??):
            score += 3.0
    elif key == "pest":
        score += weighted_hits(text, PEST_WEIGHT_MAP)
        score += min(1.8, 0.22 * key_strength)
        score += count_any(title_l, [t.lower() for t in PEST_TITLE_CORE_TERMS]) * 1.1
        # 吏?먯껜 諛쒗몴 湲곗궗?쇰룄 諛⑹젣 ?ㅽ뻾(?덉같/?쎌젣/?댄룷/?꾩닔議곗궗) 留λ씫??媛뺥븯硫?pest ?곗꽑
        if is_pest_control_policy_context(text):
            score += 2.8

        # 怨쇱닔?붿긽蹂??꾩?蹂??됲빐/?숉빐 ??怨쇱닔 由ъ뒪?щ뒗 理쒖슦??怨쇱닔?뷀쎕? 愿??
        if "怨쇱닔?붿긽蹂? in text:
            score += 6.0
        if "?꾩?蹂? in text:
            score += 3.0
        if any(w in text for w in ("?됲빐", "?숉빐", "??⑦뵾??, "?쒕━")):
            score += 2.4

        # ?섑븘/?쇨린/?곗옱/移쇰읆??媛쒖씤 ?먯꽭?? + ?뺤튂/?멸탳 ?쒕ぉ? pest ?듭떖?깆뿉??硫??媛먯젏
        # - 蹂몃Ц??蹂묓빐異??щ?媛 ?덈뜑?쇰룄 '?듭떖2'濡??щ씪媛吏 ?딅룄濡??먯닔???④퍡 ??텣??
        narrative_terms = ("?쇨린", "?띾쭑?쇨린", "?섑븘", "?먯꽭??, "?곗옱", "移쇰읆", "?ㅽ뵾?덉뼵", "湲곌퀬")
        if any(w in text for w in narrative_terms) or any(w in title_l for w in narrative_terms):
            score -= 3.8

        foreign_politics = ("?몃읆??, "諛붿씠??, "?명떞", "?쒖쭊??, "諛깆븙愿", "誘멸뎅 ??듬졊")
        if any(w in title_l for w in foreign_politics):
            # ?쒕ぉ???뺤튂/?멸탳?닿퀬 諛⑹젣 ?좏샇媛 ?쒕ぉ?먯꽌 ?쒕윭?섏? ?딆쑝硫?異붽? 媛먯젏
            if count_any(title_l, [t.lower() for t in PEST_STRICT_TERMS]) == 0 and count_any(title_l, [t.lower() for t in PEST_WEATHER_TERMS]) == 0:
                score -= 4.2
        # ?묎끝(踰? 諛⑹젣???쒖쇅: ?⑥븘?덈뜑?쇰룄 媛뺥븯寃?媛먯젏
        rice_hits = count_any(text, [t.lower() for t in PEST_RICE_TERMS])
        horti_hits = count_any(text, [t.lower() for t in PEST_HORTI_TERMS])
        if rice_hits >= 1 and horti_hits == 0:
            title_pest_hits = count_any(title_l, [t.lower() for t in ("蹂묓빐異?, "諛⑹젣", "?덉같", "?쎌젣", "怨쇱닔?붿긽蹂?, "?꾩?蹂?)])
            # 踰?湲곗궗?쇰룄 蹂묓빐異?諛⑹젣媛 ?쒕ぉ쨌蹂몃Ц?먯꽌 紐낇솗?섎㈃ ?꾩쟾 諛곗젣?섏? ?딄퀬 蹂댁닔 媛먯젏
            score -= 2.6 if title_pest_hits >= 1 else 7.0

    # ?몃줎/湲곌? 媛以묒튂
    score += press_weight(press, dom)

    # ??dist(?좏넻/?꾩옣): ?꾨Ц 留ㅼ껜(?띿뾽/?좏넻) ?ㅻТ ?좏샇瑜???諛섏쁺?섍퀬, ?듭떊(?고빀?댁뒪)???곷떒??怨쇰룄?섍쾶 ?좎떇?섎뒗 寃쎌슦瑜??듭젣
    if key == "dist":
        wholesale_hits = count_any(text, [t.lower() for t in WHOLESALE_MARKET_TERMS])
        apc_ctx = has_apc_agri_context(text)
        dist_anchor = market_hits + wholesale_hits + (1 if apc_ctx else 0)
        # APC/?곗??좏넻 ?명봽??湲곗궗(以怨?媛???좊퀎/?????dist ?ㅻТ 媛移섍? ?믪븘 ?뚰룺 媛??
        if apc_ctx and any(w in text for w in ("以怨?, "?꾧났", "媛쒖옣", "媛쒖냼", "媛??, "?좊퀎", "?좉낵", "???, "??⑥???, "??κ퀬", "ca???)):
            score += 1.4
            if (press or "").strip() in AGRI_TRADE_PRESS or normalize_host(dom) in AGRI_TRADE_HOSTS:
                score += 0.6    # ?고빀?댁뒪??踰붿슜 湲곗궗?됱씠 留롮븘 dist ?곷떒???좎떇?섍린 ?ъ?: 湲곕낯 媛먯젏 + ?듭빱 ?쏀븯硫?異붽? 媛먯젏
        if (press or "").strip() == "?고빀?댁뒪":
            score -= 1.8
            if dist_anchor < 2:
                score -= 1.4
        # ?띿뾽 ?꾨Ц/?꾩옣 留ㅼ껜??'?꾨ℓ/?꾩옣' ?뺣낫 媛移섍? ?믪븘 異붽? 媛??
        if (press or "").strip() in AGRI_TRADE_PRESS or normalize_host(dom) in AGRI_TRADE_HOSTS:
            if dist_anchor >= 1:
                score += 2.2
            if any(w in title_l for w in ("媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯", "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc", "?섏텧", "寃??, "?듦?")):
                score += 1.0

        # ?꾨ℓ?쒖옣/?띿궛臾쇱떆???명봽?셋룹씠?꽷룻쁽????댁뒋???좏넻쨌?꾩옣 ?뱀뀡 ?곗꽑
        relocation_terms = ("?댁쟾", "??릿", "?댁쟾吏", "?꾨???, "?щ같移?, "?뺤옣", "?좎꽕", "媛쒖옣", "媛쒖냼")
        if any(w in text for w in ("?꾨ℓ?쒖옣", "怨듭쁺?꾨ℓ?쒖옣", "怨듯뙋??)):
            if any(w in text for w in relocation_terms):
                score += 2.4
            if any(w in title_l for w in relocation_terms):
                score += 1.2
        # '?띿궛臾??쒖옣 ?댁쟾'泥섎읆 ?꾨ℓ?쒖옣 ?⑥뼱媛 ?녿뜑?쇰룄 ?좏넻 ?명봽???ы렪 留λ씫??諛섏쁺
        if ("?띿궛臾? in text and "?쒖옣" in text) and any(w in text for w in relocation_terms):
            score += 3.4
            if any(w in title_l for w in relocation_terms):
                score += 1.4

    # ??以묒븰吏/諛⑹넚???곗뼱3) 異붽? 媛?? 怨듭떊???뚭툒???믪? ?댁뒋瑜??곷떒??????諛섏쁺
    _pt = press_tier(press, dom)
    if _pt == 3:
        score += 0.9
        if (press or '').strip() in BROADCAST_PRESS:
            score += 0.4

    # ?꾨찓???덉쭏 ?⑤꼸??
    score -= low_quality_domain_penalty(dom)

    # ???먯“湲??뱁엳 ?먯삁) ?댁뒋???ㅻТ 泥댄겕 ?곗꽑: dist/policy ?곗꽑 媛??
    if "?먯“湲? in text:
        # ?먯삁/怨쇱닔/?뷀쎕/泥?낵 留λ씫???덉쑝硫?媛뺥븯寃?媛??異뺤궛 ?먯“湲덉? is_relevant?먯꽌 諛곗젣??
        if any(w in text for w in ("?먯삁","怨쇱닔","?뷀쎕","?덊솕","怨쇱씪","梨꾩냼","泥?낵","?ш낵","諛?,"媛먭랠","?멸린","怨좎텛","?ㅼ씠","?щ룄")) or horti_sc >= 1.4:
            if key in ("dist", "policy"):
                score += 2.6
                # ?쒕ぉ???먯“湲덉씠 紐낆떆???댁뒋??泥댄겕 ?곗꽑(?듭떖??媛??
                if "?먯“湲? in title_l:
                    score += 1.6
            elif key == "supply":
                score += 2.0
            else:
                score += 1.2

    # ???뚮퉬??臾쇨?/?λ컮援щ땲瑜??띿궛臾??쇰? ?멸툒) 湲곗궗: 李멸퀬?⑹쑝濡쒕뒗 ?먮릺 ?듭떖?먯꽌 諛由щ룄濡?媛먯젏
    consumer_price_terms = ("?λ컮援щ땲", "諛μ긽", "臾쇨?", "?뚮퉬?먮Ъ媛", "?몄떇臾쇨?", "??뺣쭏??, "留덊듃", "?좎씤?됱궗")
    if any(w in text for w in consumer_price_terms):
        if market_hits == 0 and horti_sc < 2.2 and key in ("supply", "dist"):
            score -= 2.4

    # ???ㅽ룷痢좊룞??吏???⑥떊/罹좏럹??瑜섎뒗 ?섎떒 諛곗튂(?꾩슂?쒕쭔 諛깊븘濡??몄텧)
    if ("sports.donga.com" in dom) or (press == "?ㅽ룷痢좊룞??):
        if market_hits == 0 and horti_sc < 2.4:
            score -= 3.4
        else:
            score -= 1.4

    # ??dist?먯꽌 援??? ?⑥쐞 吏???⑥떊/?됱젙 ?숈젙??湲곗궗 異붽? ?듭젣(News1 ?먯“湲?媛숈? ?듭떖 ?댁뒋媛 ?꾨옒濡?諛由щ뒗 寃껋쓣 諛⑹?)
    if key == "dist":
        if (re.search(r"[媛-??{2,}援?, title) is not None) or ("援곗껌" in title_l) or ("援곗닔" in title_l):
            if market_hits == 0 and (not has_apc_agri_context(text)):
                score -= 5.0

    # ??dist?먯꽌 '吏???⑥떊/吏?먯껜 怨듭??? 湲곗궗(?쑣룰뎔쨌援?+ 吏??異붿쭊/?묒빟/紐⑥쭛...)??
    # - ?꾨낫媛 ?곸? ???곷떒(?듭떖2)濡??щ씪? 吏꾩쭨 泥댄겕?댁빞 ???댁뒋(?? ?먯삁 ?먯“湲?瑜?諛?대궡??臾몄젣媛 ?덉뼱
    #   ?먯닔 ?④퀎?먯꽌 誘몄꽭?섍쾶 ??媛먯젏?쒕떎. (?좏깮 ?④퀎?먯꽌??2媛??댁긽 梨꾩썙議뚯쑝硫?異붽? ?쒖쇅)
    if key == "dist" and is_local_brief_text(title, desc, key):
        score -= 4.2

    # ?랁삊(寃쎌젣吏二?怨듯뙋???? 愿?⑥꽦 媛??
    score += nh_boost(text, key)

    # ?됱궗/?숈젙???⑤꼸???ㅻТ ?좏샇 ?쏀븯硫?媛먯젏)
    score -= eventy_penalty(text, title, key)

    # ?됱젙/?뺤튂 ?명꽣酉곗꽦(?꾩????쒖옣 ?? 湲곗궗 ?곷떒 諛곗튂 ?듭젣
    score -= governance_interview_penalty(text, title, key, horti_sc, market_hits)

    # 吏???⑥쐞 ?랁삊 ?숈젙??湲곗궗 ?⑤꼸???뱁엳 ?띾??좊Ц 吏??냽???뚯떇 怨쇰떎 諛⑹?)
    score -= local_coop_penalty(text, press, dom, key)
    # ???쒖쇅 ?덈ぉ(留덈뒛/?묓뙆)? ?먯닔 ?곗젙 ?댁쟾 ?④퀎?먯꽌 ?대? 而룸릺?꾨줉 ?ㅺ퀎.
    # ?뱀떆?쇰룄 ?⑥븘 ?ㅼ뼱?ㅻ㈃ 理쒗븯?⑥쑝濡?諛?대궡湲??꾪빐 媛뺥븳 ?⑤꼸?곕? 遺?ы븳??
    if any(w.lower() in text for w in EXCLUDED_ITEMS):
        score -= 100.0

    # '?곷냽遺?곕Ъ/?덉쟾泥섎━/?뚯뇙' ???ъ뾽?ㅻ챸쨌?됱젙???뺤콉? ?섎떒 諛곗튂(???놁쓣 ?뚮쭔)
    if any(w in text for w in ("?곷냽遺?곕Ъ", "?덉쟾泥섎━", "?뚯뇙", "?뚯뇙湲?, "?뚭컖", "?붽?吏")):
        if market_hits == 0 and horti_sc < 2.0:
            score -= 3.5

    # ?앺뭹?덉쟾/?꾩깮 ?⑤룆 ?댁뒋???먯삁?섍툒 ?듭떖?먯꽌 硫??媛먯젏(?꾨ℓ?쒖옣/?덈ぉ ?좏샇媛 ?덉쑝硫??좎?)
    if any(w in text for w in ("?앺뭹?덉쟾", "?꾩깮", "haccp", "?앹쨷??)):
        if market_hits == 0 and horti_sc < 1.8 and count_any(text, [t.lower() for t in ("?띿궛臾?, "?먯궛吏", "寃??, "?꾨ℓ?쒖옣")]) < 1:
            score -= 3.0

    # 理쒖떊?? 48?쒓컙 ??湲곗궗 蹂댁젙(?덈Т 怨쇰룄?섏? ?딄쾶)
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

    # supply ?뱀뀡: ?몄떇/酉뷀럹/?꾨옖李⑥씠利?'?멸린異뺤젣' 瑜섎뒗 ?뚮퉬 ?대깽???깃꺽??媛뺥빐 ?듭떖 ?좏샇?먯꽌 媛먯젏
    if section_conf.get("key") == "supply" and is_fruit_foodservice_event_context(text):
        score -= 2.8

    # ???뱀뀡: ?⑥뒪?명뫖??媛寃?湲곗궗 諛⑹뼱(?꾪꽣瑜??듦낵?섎뜑?쇰룄 ?먯닔 ?섎씫)
    if is_fastfood_price_context(text):
        score -= 6.0

    return round(score, 3)
def _token_set(s: str) -> set[str]:
    s = (s or "").lower()
    toks = re.findall(r"[0-9a-z媛-??{2,}", s)
    return {t for t in toks if t not in ("湲곗궗", "?댁뒪", "?띿궛臾?, "?띿뾽", "?뺣?", "吏?먯껜")}


# --- Near-duplicate suppression (?뱁엳 吏諛?諛⑹젣/?묒쓽??湲곗궗 以묐났 諛⑹?) ---
# ??Region detection (conservative) ??avoid false positives like '?밸룄/媛寃⑸룄/?섍툒??異쒗븯??
_PROVINCE_NAMES = [
    "?쒖슱?밸퀎??,"遺?곌킅??떆","?援ш킅??떆","?몄쿇愿묒뿭??,"愿묒＜愿묒뿭??,"??꾧킅??떆","?몄궛愿묒뿭??,"?몄쥌?밸퀎?먯튂??,
    "寃쎄린??,"媛뺤썝?밸퀎?먯튂??,"異⑹껌遺곷룄","異⑹껌?⑤룄","?꾨씪遺곷룄","?꾨씪?⑤룄","寃쎌긽遺곷룄","寃쎌긽?⑤룄","?쒖＜?밸퀎?먯튂??,
]
_PROVINCE_RX = re.compile("|".join(map(re.escape, _PROVINCE_NAMES)))

# ??援?援???硫??⑥쐞???ㅽ깘??留롮븘 '?????쒖쇅?섍퀬, ?⑥뼱 寃쎄퀎??媛源앷쾶留?留ㅼ묶
_CITY_COUNTY_RX = re.compile(r"(?:(?<=\s)|^)([媛-??{2,})(??援?援???硫?(?=\s|$|[\]\[\)\(\.,쨌!\?\"'?쒋앪섃?/-])")

# _REGION_RX: ordered scan helper for pest de-dup (province + city/county tokens).
# NOTE: keep conservative to avoid false positives; used only for grouping, not for relevance filtering.
_REGION_RX = re.compile(r"(?:" + _PROVINCE_RX.pattern + r")|(?:" + _CITY_COUNTY_RX.pattern + r")")


# 吏??쿂??蹂댁씠吏留??ㅼ젣濡쒕뒗 ?띿뾽/湲곗궗 ?⑹뼱??寃쎌슦媛 留롮븘 ?쒖쇅(蹂댁닔??
_REGION_STOP_PREFIX = {
    "諛⑹젣","?덉같","吏??,"?梨?,"?뺤콉","?섍툒","異쒗븯","媛寃?,"臾쇰웾","?덉쭏","?앹궛","?뚮퉬","?뺣?","媛먯냼",
    "媛쒖턀","吏꾪뻾","諛쒗몴","異붿쭊","?뺣낫","媛쒖꽑","媛뺥솕","?⑥냽","?먭?","議곗궗","?뺤궛","二쇱쓽","寃쎈낫","?꾨쭩",
}

def _region_set(s: str) -> set[str]:
    s = (s or "")
    out: set[str] = set()

    # 1) 愿묒뿭/???⑥쐞??紐낆떆 由ъ뒪?몃쭔 ?덉슜
    for mm in _PROVINCE_RX.finditer(s):
        out.add(mm.group(0))

    # 2) ??援?援???硫??⑥쐞??蹂댁닔?곸쑝濡?異붿텧(?ㅽ깘 諛⑹?)
    for mm in _CITY_COUNTY_RX.finditer(s):
        stem = mm.group(1)
        suf = mm.group(2)
        if stem in _REGION_STOP_PREFIX:
            continue
        out.add(f"{stem}{suf}")

    return out
_BARE_REGION_RX = re.compile(r"([媛-??{2,6})(?=(?:\s*)?(?:?띿뾽湲곗닠?쇳꽣|?띻린?쇳꽣|援곗껌|?쒖껌|援ъ껌|?띿뾽湲곗닠???띿뾽湲곗닠怨?)")

_PEST_CORE_TOKENS = {
    "蹂묓빐異?,"諛⑹젣","?덉같","怨쇱닔?붿긽蹂?,"?꾩?蹂?,"?됲빐","?숉빐","?붾룞","?쎌젣","?띿빟","?댄룷","諛⑹뿭"
}
_SUPPLY_CORE_TOKENS = {"?섍툒","媛寃?,"?쒖꽭","寃쎈씫","寃쎈씫媛","?묓솴","異쒗븯","?ш퀬","???,"臾쇰웾","諛섏엯"}
_SUPPLY_COMMODITY_TOKENS = {
    "?ш낵","諛?,"媛먭랠","留뚭컧","?쒕씪遊?,"?덈뱶??,"泥쒗삙??,"?щ룄","?ㅼ씤癒몄뒪罹?,"?ㅼ씠","怨좎텛","?뗪퀬異?,"?","鍮꾩텞誘?,"?④컧","怨띔컧"
}
_DIST_CORE_TOKENS = {"媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"寃쎈씫","寃쎈ℓ","諛섏엯","以묐룄留ㅼ씤","?쒖옣?꾨ℓ??,"apc","臾쇰쪟","?좏넻","?⑤씪?몃룄留ㅼ떆??}
_POLICY_CORE_TOKENS = {"?梨?,"吏??,"?좎씤","?좎씤吏??,"?좊떦愿??,"寃??,"?듦?","?⑥냽","怨좎떆","媛쒖젙","蹂대룄?먮즺","釉뚮━??,"?덉궛","?뺣?","?곗옣"}

def _pest_region_key(title: str) -> str:
    """pest ?뱀뀡 以묐났 ?듭젣瑜??꾪븳 ???吏????
    - ??硫????섏쐞 ?⑥쐞媛 ?덉뼱??媛숈? 援???援щ줈 臾띠씠?꾨줉 ?곗꽑 援???援щ? ?좏깮
    - ?놁쑝硫?泥?吏???좏겙(???? ?ъ슜
    """
    t = title or ""
    ms = list(_REGION_RX.finditer(t))
    if not ms:
        # 援???援ш? 紐낆떆?섏? ?딆?留?"?μ닔 ?띿뾽湲곗닠?쇳꽣"泥섎읆 ?먯＜ ?깆옣?섎뒗 ?⑦꽩 蹂댁셿
        m2 = _BARE_REGION_RX.search(t)
        if m2:
            return m2.group(1)
        return ""
    # 1) 媛??癒쇱? ?깆옣?섎뒗 援???援???硫??쒖쇅)瑜???쒕줈
    for m in ms:
        r = m.group(0)
        if r.endswith(("援?, "??, "援?)):
            return r
    # 2) 援???援ш? ?놁쑝硫?泥??좏겙(??愿묒뿭????
    return ms[0].group(0)

def _near_duplicate_title(a: "Article", b: "Article", section_key: str) -> bool:
    """URL???щ씪??'?ъ떎??媛숈? ?댁뒋'濡?蹂댁씠???쒕ぉ 以묐났???듭젣?쒕떎.
    - ?뱁엳 pest(蹂묓빐異?諛⑹젣) ?뱀뀡?먯꽌 媛숈? 吏?먯껜 諛⑹젣 ?댁뒋媛 ?щ윭 嫄??⑤뒗 臾몄젣瑜??꾪솕.
    """
    ta = _token_set(a.title)
    tb = _token_set(b.title)
    jac = _jaccard(ta, tb)

    # ?쒕ぉ???ㅻⅤ?붾씪??蹂몃Ц(?붿빟)源뚯? ?ы븿?섎㈃ ?ъ떎??媛숈? ?댁뒋??寃쎌슦媛 留롮쓬(?留ㅼ껜 ?ъ쟾??怨듬룞痍⑥옱)
    ta2 = _token_set((a.title or "") + " " + (a.description or ""))
    tb2 = _token_set((b.title or "") + " " + (b.description or ""))
    jac2 = _jaccard(ta2, tb2)
    if jac2 >= 0.62:
        return True

    # 臾몄옄???좎궗???쒓린 李⑥씠/?뱀닔臾몄옄 李⑥씠 蹂댁셿)
    sa = re.sub(r"\s+", "", (a.title_key or a.title or "")).lower()
    sb = re.sub(r"\s+", "", (b.title_key or b.title or "")).lower()
    try:
        if sa and sb and difflib.SequenceMatcher(None, sa, sb).ratio() >= 0.88:
            return True
    except Exception:
        pass

    # 媛뺥븳 以묐났(嫄곗쓽 ?숈씪)
    if jac >= 0.72:
        return True

    ra = _region_set((a.title or "") + " " + (a.description or ""))
    rb = _region_set((b.title or "") + " " + (b.description or ""))
    same_region = bool(ra & rb)

    if section_key == "pest":
        common_core = len((ta & tb) & _PEST_CORE_TOKENS)
        # 媛숈? 吏?먯껜 + 諛⑹젣/蹂묓빐異??ㅼ썙?쒓? 異⑸텇??寃뱀튂硫?湲곗궗留??ㅻⅤ怨??댁슜??媛숈? 寃쎌슦媛 留롮쓬)
        if same_region and common_core >= 2 and jac >= 0.45:
            return True
        # '諛⑹젣/?덉같/?쎌젣' + 媛숈? 吏??씠硫???愿??섍쾶 以묐났 ?먮떒
        if same_region and common_core >= 1 and jac >= 0.52:
            return True

    if section_key == "supply":
        common_core = len((ta & tb) & _SUPPLY_CORE_TOKENS)
        common_cmd = len((ta & tb) & _SUPPLY_COMMODITY_TOKENS)
        if common_cmd >= 1 and common_core >= 2 and jac >= 0.50:
            return True

    if section_key == "dist":
        common_core = len((ta & tb) & _DIST_CORE_TOKENS)
        if (same_region or common_core >= 2) and jac >= 0.50:
            return True

    if section_key == "policy":
        common_core = len((ta & tb) & _POLICY_CORE_TOKENS)
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
    """?뺤콉 ?뱀뀡?먯꽌 '怨듭떇 諛쒗몴/怨듭?'濡?痍④툒???뚯뒪."""
    dom = normalize_host(a.domain)
    p = (a.press or "").strip()

    if dom in OFFICIAL_HOSTS or any(dom.endswith("." + h) for h in OFFICIAL_HOSTS):
        return True

    # ?꾨찓??留ㅽ븨??遺덉셿?꾪븷 ???덉뼱, 湲곌?紐?湲곕컲??蹂닿컯
    if p in ("?띿떇?덈?", "?뺤콉釉뚮━??, "aT", "?띻???, "KREI", "?띿큿吏꾪씎泥?, "媛?쎌떆??):
        return True

    return False

# -----------------------------
# Headline gate constants
# -----------------------------
# 肄붿뼱(?듭떖 2)濡??щ━湲곗뿏 遺?곸젅???ㅻ뱶?쇱씤 ?⑦꽩(移쇰읆/湲곌퀬/?됱궗/?몃Ъ/?띾낫??
_HEADLINE_STOPWORDS = [
    "移쇰읆", "湲곌퀬", "?ъ꽕", "?ㅽ뵾?덉뼵", "?낆옄湲곌퀬", "湲곗옄?섏꺽",
    "?쇨린", "?띾쭑?쇨린", "?섑븘", "?먯꽭??, "?곗옱", "湲고뻾", 
    "?명꽣酉?, "???, "?좉컙", "梨?, "異붿쿇", "?ы뻾", "留쏆쭛",
    "?ы넗", "?붾낫", "?곸긽", "?ㅼ?移?, "?됱궗", "異뺤젣", "湲곕뀗", "?쒖긽",
    "遊됱궗", "?꾩썝", "湲곕?", "罹좏럹??, "諛쒕???, "?좏룷??, "?묒빟", "mou",
    "?몃Ъ", "?숈젙", "痍⑥엫", "?몄궗", "遺怨?, "寃고샎", "媛쒖뾽",
]

def _headline_gate(a: "Article", section_key: str) -> bool:
    """肄붿뼱(?듭떖2)濡??щ┫ ?먭꺽???덈뒗吏(?뱀뀡蹂?.

    ?먯튃:
    - 肄붿뼱??"?띿궛臾??먯삁 留λ씫"???뺤떎??湲곗궗留?遺遺??멸툒/?명꽣酉??됱젙 ?⑥떊? ?섎떒)
    - APC???띿뾽 臾몃㎘???뚮쭔 ?몄젙
    """
    title = (a.title or "").lower()
    text = (a.title + " " + a.description).lower()

    # (?듭떖) 肄붿뼱2??"?뺣쭚 ?듭떖"留??щ━湲??꾪빐, ?덈ぉ/?꾨ℓ/?먯삁 ?좏샇瑜??ы솗??
    horti_sc = best_horti_score(a.title or "", a.description or "")
    horti_title_sc = best_horti_score(a.title or "", "")
    market_ctx_terms = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "寃쎈씫媛", "諛섏엯", "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣", "?곗??좏넻", "?곗??좏넻?쇳꽣"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    agri_anchor_terms = ("?띿궛臾?, "?띿뾽", "?띿떇??, "?먯삁", "怨쇱닔", "怨쇱씪", "梨꾩냼", "?뷀쎕", "?덊솕", "泥?낵")
    agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])

    # 怨듯넻: 移쇰읆/湲곌퀬/?몃Ъ/?됱궗?깆? 肄붿뼱?먯꽌 ?쒖쇅
    if has_any(title, [w.lower() for w in _HEADLINE_STOPWORDS]):
        return False

    # 怨듯넻: ?됱젙/?뺤튂 ?명꽣酉걔룸룞?뺤꽦(?꾩????쒖옣 ?? 湲곗궗?????肄붿뼱 李⑤떒(遺遺??멸툒 ?ㅽ깘 諛⑹?)
    poli_roles = ("?꾩???, "吏??, "?쒖옣", "援곗닔", "?꾩쓽??, "?꾩쓽??, "?쒖쓽??, "援?쉶?섏썝", "?꾩젙", "?쒖젙", "援곗젙", "?됱젙")
    if any(r in title for r in poli_roles):
        strong_keep = ("?좎씤", "?좎씤吏??, "?좊떦愿??, "?섍툒", "媛寃?, "異쒗븯", "?ш퀬",
                       "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                       "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧")
        # ?띿궛臾?留λ씫??媛뺥븯怨??듭빱/?쒖옣/?덈ぉ) + ?ㅻТ ?좏샇媛 紐낇솗???뚮쭔 ?덉쇅?곸쑝濡?肄붿뼱 ?덉슜
        if not (((market_hits >= 1) or (horti_title_sc >= 1.6) or (agri_anchor_hits >= 2 and horti_title_sc >= 1.3))
                and count_any(text, [t.lower() for t in strong_keep]) >= 2):
            return False


    # 怨듯넻: 湲곗궗 ?꾩껜媛 '吏?먯껜 ?됱젙/?명꽣酉? ?깃꺽?몃뜲 ?덈ぉ???쇰? 臾몃떒?먮쭔 ?깆옣?섎뒗 寃쎌슦瑜?肄붿뼱?먯꽌 ?쒖쇅
    adminish = ("?꾩껌", "?쒖껌", "援곗껌", "?꾩쓽??, "?쒖쓽??, "?뺣Т", "誘쇱꽑", "?꾩젙", "?쒖젙", "援곗젙", "?됱젙",
                "愿愿?, "蹂듭?", "泥?뀈", "援먯쑁", "援먰넻", "SOC", "怨듭빟", "?몄궗")
    if any(w in title for w in adminish) or any(w in text for w in adminish):
        # ?쒕ぉ?먯꽌 ?덈ぉ/?먯삁 ?좏샇媛 ?쏀븳 ?됱젙/?명꽣酉곗꽦 湲곗궗??(蹂몃Ц ?쇰? ?멸툒 ?ㅽ깘 媛?? 肄붿뼱?먯꽌 ?쒖쇅
        if horti_title_sc < 1.4 and market_hits == 0:
            return False
        strong_keep2 = ("?좎씤", "?좎씤吏??, "?좊떦愿??, "?섍툒", "媛寃?, "異쒗븯", "?ш퀬",
                        "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                        "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧")
        if count_any(text, [t.lower() for t in strong_keep2]) < 2 and market_hits == 0 and horti_sc < 2.8:
            return False

    if section_key == "supply":
        signal_terms = ["媛寃?, "?쒖꽭", "?섍툒", "?묓솴", "?앹궛", "異쒗븯", "諛섏엯", "臾쇰웾", "?ш퀬", "寃쎈씫", "寃쎈ℓ"]

        # ???듭떖2??"?쒕ぉ(?ㅻ뱶?쇱씤)"?먯꽌 ?띿궛臾??덈ぉ 留λ씫???쒕윭?섏빞 ?쒕떎.
        # - ?됱젙/?명꽣酉?湲곗궗(蹂몃Ц ??臾몃떒 ?멸툒) ?ㅽ깘??留됯린 ?꾪빐 title-only ?덈ぉ ?먯닔瑜??④퍡 蹂몃떎.
        horti_title_sc = best_horti_score(a.title or "", "")

        if not has_any(text, [t.lower() for t in signal_terms]):
            return False

        # ?쒖옣/?꾨ℓ ?좏샇媛 ?덉쑝硫?肄붿뼱 媛???? ?쒕ぉ ?덉쭏? ?대? ?꾩뿉??嫄몃윭吏?
        if market_hits >= 1:
            return True

        # ?덈ぉ ?먯닔媛 媛뺥빐?? ?쒕ぉ?먯꽌 ?덈ぉ/?먯삁 ?좏샇媛 ?쏀븯硫?=蹂몃Ц ?쇰? ?멸툒) 肄붿뼱 遺덇?
        if horti_sc >= 2.3 and horti_title_sc >= 1.6:
            return True

        # ?띿궛臾??듭빱媛 異⑸텇???덇퀬 ?쒕ぉ ?덈ぉ ?먯닔媛 以묎컙 ?댁긽?대㈃ ?덉슜
        if agri_anchor_hits >= 2 and horti_title_sc >= 1.3:
            return True

        return False

    if section_key == "policy":
        if _is_policy_official(a):
            return True
        action_terms = ["?梨?, "吏??, "?좎씤", "?좊떦愿??, "寃??, "怨좎떆", "媛쒖젙", "諛쒗몴", "異붿쭊", "?뺣?", "?곗옣", "?⑥냽", "釉뚮━??, "蹂대룄?먮즺", "?덉궛"]
        ctx_terms = ["?띿궛臾?, "?띿뾽", "?띿떇??, "怨쇱씪", "梨꾩냼", "?섍툒", "媛寃?, "?좏넻", "?먯궛吏", "?꾨ℓ?쒖옣", "怨듭쁺?꾨ℓ?쒖옣", "?섏텧", "寃??]

        # ?앺뭹?덉쟾/?꾩깮 ?⑤룆(?꾨ℓ/?덈ぉ ?좏샇 ?놁쓬)? 肄붿뼱?먯꽌 ?쒖쇅
        if any(w in text for w in ("?앺뭹?덉쟾", "?꾩깮", "haccp", "?앹쨷??)) and (market_hits == 0) and (horti_sc < 2.0) and (agri_anchor_hits == 0):
            return False

        # ?뺤콉 肄붿뼱??'?뺤콉 ?≪뀡' + '?띿떇???좏넻 留λ씫'???숈떆 異⑹”?섏뼱????
        return has_any(text, [t.lower() for t in action_terms]) and has_any(text, [t.lower() for t in ctx_terms]) and ((horti_sc >= 1.8) or (market_hits >= 1) or (agri_anchor_hits >= 2))

    if section_key == "dist":
        # ?좏넻 肄붿뼱??'?꾨ℓ?쒖옣/?곗??좏넻/APC/?⑥냽/寃?? ??媛뺤떊?멸? 異⑸텇?섍퀬,
        # ?띿궛臾??먯삁/?쒖옣 留λ씫???④퍡 ?덉쓣 ?뚮쭔 ?덉슜
        dist_terms = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣", "泥?낵", "寃쎈씫", "寃쎈씫媛", "寃쎈ℓ", "諛섏엯",
                      "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣",
                      "?좊퀎", "???, "??⑥???, "??κ퀬", "ca???, "臾쇰쪟",
                      "?섏텧", "寃??, "?듦?", "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "?곗??좏넻", "?곗??좏넻?쇳꽣"]
        dist_hits = count_any(text, [t.lower() for t in dist_terms])
        apc_ctx = has_apc_agri_context(text)
        if apc_ctx:
            dist_hits += 1
        # ??吏???⑥떊/吏?먯껜 怨듭???湲곗궗(dist)???듭떖2濡??щ━吏 ?딅뒗??
        if is_local_brief_text(a.title or "", a.description or "", section_key):
            return False

        # '?섏텧/寃???듦?/?먯궛吏 ?⑥냽'留뚯쑝濡?嫄몃┛ ?쇰컲 湲곗궗 ?꾩닔 諛⑹?(?쒖옣/APC/?먯삁 留λ씫 ?녿뒗 寃쎌슦)
        ops_terms = ("?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧")
        ops_hits = count_any(text, [t.lower() for t in ops_terms])
        if (ops_hits >= 1 and market_hits == 0 and (not apc_ctx)
                and agri_anchor_hits == 0 and horti_sc < 2.0):
            return False

        # 諛⑹넚??吏??린?ъ쓽 '遺遺??멸툒' ?꾩닔 諛⑹?(KBS/SBS ??
        if ((a.press or "").strip() in BROADCAST_PRESS and _LOCAL_GEO_PATTERN.search(a.title or "")):
            title_market_hits = count_any(title, [t.lower() for t in ("媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣",
                                                                      "寃쎈씫", "寃쎈ℓ", "諛섏엯", "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc")])
            if title_market_hits == 0 and (not apc_ctx) and horti_sc < 2.2 and horti_title_sc < 1.6:
                return False

        # dist_hits(?꾨ℓ/?좏넻 媛뺤떊??媛 遺議깊븯硫?湲곕낯?곸쑝濡?肄붿뼱 遺덇?
        # ?? APC ?명봽??湲곗궗???띿뾽 ?꾨Ц/?꾩옣 留ㅼ껜??'?쒖옣 ?꾩옣/?紐⑹옣' 由ы룷?몃뒗 ?덉쇅 ?덉슜
        if dist_hits < 2:
            if apc_ctx and any(w in text for w in ("以怨?, "?꾧났", "媛쒖옣", "媛쒖냼", "媛??, "?좊퀎", "?좉낵", "???, "??κ퀬", "ca???)):
                return True
            if ((a.press in AGRI_TRADE_PRESS or normalize_host(a.domain or "") in AGRI_TRADE_HOSTS)
                    and has_any(title, ["?紐⑹옣", "?紐?, "?꾩옣", "?대븷??, "?먮ℓ", "?쒖옣"])
                    and (horti_title_sc >= 1.4 or horti_sc >= 2.0)):
                return True
            return False
        return (agri_anchor_hits >= 1) or (horti_sc >= 2.0) or (market_hits >= 1) or apc_ctx
    if section_key == "pest":
        # ?띿뾽 留λ씫 + 蹂묓빐異?諛⑹젣(?먮뒗 ?됲빐/?숉빐 ?쇳빐) 媛?쒖쟻?댁뼱??肄붿뼱
        if not has_any(text, [t.lower() for t in PEST_AGRI_CONTEXT_TERMS]):
            return False
        # 肄붿뼱??'?ㅻ뱶?쇱씤'?먯꽌 蹂묓빐異?諛⑹젣/湲곗긽?쇳빐 ?좏샇媛 ?쒕윭?섏빞 ?쒕떎(?섑븘/?쇨린/?뺤튂 ?쒕ぉ ?꾩닔 諛⑹?).
        title_hits = count_any(title, [t.lower() for t in PEST_STRICT_TERMS]) + count_any(title, [t.lower() for t in PEST_WEATHER_TERMS])
        if title_hits == 0:
            return False

        strict_hits = count_any(text, [t.lower() for t in PEST_STRICT_TERMS])
        weather_hits = count_any(text, [t.lower() for t in PEST_WEATHER_TERMS])
        return (strict_hits >= 2) or (strict_hits >= 1 and weather_hits >= 1) or (weather_hits >= 2)

    return True
def _headline_gate_relaxed(a: "Article", section_key: str) -> bool:
    """肄붿뼱媛 ?꾨땶 ?쇰컲 ?좏깮?먯꽌??'?ㅻ뱶?쇱씤 ?덉쭏' 寃뚯씠???꾪솕).
    - 紐⑹쟻: ?싳떆/?몃Ъ/?됱궗/?띾낫???ㅻ뱶?쇱씤???곷떒??李⑥??섎뒗 寃껋쓣 諛⑹?
    - 1李??꾪꽣(is_relevant)媛 ?대? 媛뺥븯寃?嫄곕Ⅴ怨??덉쑝誘濡? ?ш린?쒕뒗 '?쒕ぉ ?덉쭏' 以묒떖?쇰줈留?理쒖냼 李⑤떒?쒕떎.
    """
    title = (a.title or "").lower()
    text = (a.title + " " + a.description).lower()

    # 1) 移쇰읆/?ъ꽕/湲곌퀬/?몃Ъ/遺怨??몄궗瑜섎뒗 肄붿뼱媛 ?꾨땲?대룄 ?곷떒 ?몄텧??留됰뒗??嫄곗쓽 ??긽 ?몄씠利?
    hard_stop = ("移쇰읆", "?ъ꽕", "?ㅽ뵾?덉뼵", "湲곌퀬", "?낆옄湲곌퀬", "湲곗옄?섏꺽",
    "?쇨린", "?띾쭑?쇨린", "?섑븘", "?먯꽭??, "?곗옱", "湲고뻾", 
                 "?명꽣酉?, "???, "?몃Ъ", "?숈젙", "遺怨?, "寃고샎", "痍⑥엫", "?몄궗", "媛쒖뾽")
    if any(w.lower() in title for w in hard_stop):
        return False

    # 2) '?됱궗/罹좏럹???쒖긽/異뺤젣/諛쒕????좏룷?? ?깆? dist(?꾩옣) ?뱀뀡?먯꽑 ?쇰? ?섎?媛 ?덉쓣 ???덉뼱
    #    dist?????꾪솕?섍퀬, ?섎㉧吏 ?뱀뀡? 媛뺥븳 ?섍툒/?뺤콉/?쒖옣 ?좏샇媛 ?놁쑝硫?而?
    eventy = ("?됱궗", "異뺤젣", "湲곕뀗", "?쒖긽", "遊됱궗", "?꾩썝", "湲곕?", "罹좏럹??, "諛쒕???, "?좏룷??, "?묒빟", "mou")
    if any(w.lower() in title for w in eventy):
        if section_key != "dist":
            strong_keep_terms = ("媛寃?, "?쒖꽭", "?섍툒", "?묓솴", "異쒗븯", "臾쇰웾", "?ш퀬", "???,
                                 "媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                                 "寃??, "?듦?", "?먯궛吏", "?⑥냽", "遺?뺤쑀??, "?좊떦愿??, "?좎씤吏??, "?梨?, "蹂대룄?먮즺", "釉뚮━??)
            if not any(t.lower() in text for t in strong_keep_terms):
                return False

    # 3) ?뱀뀡蹂?理쒖냼 留λ씫 ?ы솗???꾩＜ ?먯뒯?섍쾶)
    horti_sc = best_horti_score(a.title or "", a.description or "")
    horti_title_sc = best_horti_score(a.title or "", "")
    market_ctx_terms = ["媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "寃쎈씫媛", "諛섏엯", "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣", "?곗??좏넻", "?곗??좏넻?쇳꽣"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    if section_key == "policy":
        # 怨듭떇 ?뚯뒪??理쒕????대┝
        try:
            if _is_policy_official(a):
                return True
        except Exception:
            pass
        # ?뺤콉 ?뱀뀡? 理쒖냼??'?뺤콉 ?≪뀡' + '?띿떇??留λ씫'???덉뼱?????꾪솕 踰꾩쟾)
        action_terms = ("?梨?, "吏??, "?좎씤", "?좊떦愿??, "寃??, "怨좎떆", "媛쒖젙", "?⑥냽", "釉뚮━??, "蹂대룄?먮즺", "?덉궛")
        ctx_terms = ("?띿궛臾?, "?띿떇??, "?띿뾽", "怨쇱씪", "梨꾩냼", "?섍툒", "媛寃?, "?좏넻", "?먯궛吏", "?꾨ℓ?쒖옣", "?⑤씪???꾨ℓ?쒖옣")
        if (not any(t.lower() in text for t in action_terms)) and (horti_sc < 1.6) and (market_hits == 0):
            return False
        if not any(t.lower() in text for t in ctx_terms):
            return False
        return True

    if section_key == "supply":
        # supply??'?덈ぉ/?띿궛臾??듭빱' + '?섍툒 ?좏샇' 寃고빀???쏀븳 湲곗궗(?⑥닚 ?멸툒)瑜??섎떒?쇰줈 諛湲??꾪빐 ??蹂댁닔?곸쑝濡?蹂몃떎.
        agri_anchor_terms = ("?띿궛臾?, "?띿뾽", "?띿떇??, "?먯삁", "怨쇱닔", "怨쇱씪", "梨꾩냼", "?뷀쎕", "?덊솕", "泥?낵")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])
        signal_terms = ("媛寃?, "?쒖꽭", "?섍툒", "?묓솴", "異쒗븯", "諛섏엯", "臾쇰웾", "?ш퀬", "寃쎈씫", "寃쎈ℓ")

        sig_hits = count_any(text, [t.lower() for t in signal_terms])

        # ?쒕ぉ?먯꽌 ?덈ぉ/?먯삁 ?좏샇媛 嫄곗쓽 ?녾퀬(蹂몃Ц ?쇰? ?멸툒 媛??, ?됱젙/?명꽣酉곗꽦 ?ㅻ뱶?쇱씤?대㈃ ?곷떒 ?몄텧(?뱁엳 core 蹂댁셿 ?④퀎)?먯꽌 ?쒖쇅
        horti_title_sc = best_horti_score(a.title or "", "")
        adminish_title = ("誘쇱꽑", "?꾩젙", "?쒖젙", "援곗젙", "?됱젙", "?꾩껌", "?쒖껌", "援곗껌", "怨듭빟", "?뺣Т", "?명꽣酉?)
        if any(w.lower() in title for w in adminish_title) and market_hits == 0 and horti_title_sc < 1.2:
            return False

        # ?쒖옣 留λ씫???녾퀬, ?덈ぉ?먯닔???쏀븯怨? ?좏샇???쏀븯硫??쒖쇅(2~3媛쒖뿉???먯뿰 醫낅즺 媛??
        if market_hits == 0 and horti_sc < 1.2 and agri_anchor_hits == 0 and sig_hits == 0:
            return False

        # '?덈ぉ留??멸툒' ?섏?(?좏샇 ?놁쓬)??湲곗궗??score媛 ?믪븘???곷떒 ?몄텧??留됯린 ?꾪빐 而??? horti_sc媛 留ㅼ슦 媛뺥븯硫??덉쇅)
        if sig_hits == 0 and market_hits == 0 and horti_sc < 2.4:
            return False

        return True

    if section_key == "dist":
        # dist??is_relevant媛 ?덉뼱??'?쇰컲 臾쇰쪟/?좏넻/?⑥냽' ?꾩닔媛 ?덉뼱, ?꾪솕 寃뚯씠?몄뿉?쒕룄 留λ씫????踰???蹂몃떎.
        agri_anchor_terms = ("?띿궛臾?, "?띿뾽", "?띿떇??, "?먯삁", "怨쇱닔", "怨쇱씪", "梨꾩냼", "?뷀쎕", "?덊솕", "泥?낵")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])
        dist_hard = ("媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣", "泥?낵", "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                     "以묐룄留ㅼ씤", "?쒖옣?꾨ℓ??, "?⑤씪???꾨ℓ?쒖옣",
                     "?좊퀎", "???, "??⑥???, "??κ퀬", "ca???, "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧", "臾쇰쪟",
                     "?곗??좏넻", "?곗??좏넻?쇳꽣")
        hard_hits = count_any(text, [t.lower() for t in dist_hard])
        apc_ctx = has_apc_agri_context(text)
        if apc_ctx:
            hard_hits += 1

        # ?띿뾽 ?듭빱???녾퀬 ?쒖옣/?덈ぉ???쏀븯硫??쒖쇅
        if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 1.6:
            return False

        # ?댁쁺/吏묓뻾 ?ㅼ썙?쒕쭔 ?덈뒗 ?쇰컲 湲곗궗 ?꾩닔 李⑤떒
        ops_terms = ("?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧")
        ops_hits = count_any(text, [t.lower() for t in ops_terms])
        if ops_hits >= 1 and market_hits == 0 and (not apc_ctx) and agri_anchor_hits == 0 and horti_sc < 2.0:
            return False

        # 諛⑹넚??吏??린?ъ쓽 ?쏀븳 ?좏넻 臾몃㎘? ?쒖쇅
        if ((a.press or "").strip() in BROADCAST_PRESS and _LOCAL_GEO_PATTERN.search(a.title or "")):
            title_market_hits = count_any(title, [t.lower() for t in ("媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듯뙋??, "怨듭쁺?꾨ℓ?쒖옣",
                                                                      "寃쎈씫", "寃쎈ℓ", "諛섏엯", "?곗??좏넻", "?곗??좏넻?쇳꽣", "apc")])
            if title_market_hits == 0 and (not apc_ctx) and horti_sc < 2.1 and horti_title_sc < 1.5:
                return False

        # ?섎뱶 ?좏샇媛 嫄곗쓽 ?녾퀬 soft(異붿긽)留??덉쑝硫??쒖쇅(?듭? 梨꾩? 諛⑹?)
        if hard_hits == 0 and horti_sc < 2.2:
            return False
        return True

    # pest??is_relevant?먯꽌 留λ씫???뺤씤?섎?濡? ?ш린?쒕뒗 ?쒕ぉ ?덉쭏留?愿由?
    return True


# -----------------------------
# Selection threshold
# -----------------------------
# ?뱀뀡蹂?理쒖냼 ?ㅼ퐫??湲곗????덈Т ?쏀븳 湲곗궗???꾨낫 ??먯꽌 ?쒖쇅)
BASE_MIN_SCORE = {
    "supply": 7.0,
    "policy": 7.0,
    "dist": 7.2,
    "pest": 6.6,
}
def _dynamic_threshold(candidates_sorted: list["Article"], section_key: str) -> float:
    """?곸쐞 湲곗궗 遺꾪룷??留욎떠 ?숈쟻?쇰줈 ?꾧퀎移섎? ?≪븘 '?쏀븳 湲곗궗'瑜?而룻븳??
    - 理쒖긽??best)?먯꽌 ?쇱젙 留덉쭊??鍮쇨퀬, ?뱀뀡蹂?理쒖냼??BASE_MIN_SCORE)蹂대떎 ??븘吏吏 ?딄쾶.
    """
    if not candidates_sorted:
        return BASE_MIN_SCORE.get(section_key, 6.0)
    best = float(getattr(candidates_sorted[0], "score", 0.0) or 0.0)
    margin = 8.0 if section_key in ("supply", "policy", "dist") else 7.0
    return max(BASE_MIN_SCORE.get(section_key, 6.0), best - margin)

def select_top_articles(candidates: list[Article], section_key: str, max_n: int) -> list[Article]:
    """?뱀뀡蹂?湲곗궗 ?좏깮.

    ?ㅺ퀎 ?먯튃
    - '?놁쑝硫??녿뒗 ?濡? : ??덉쭏/?듭? 梨꾩슦湲?湲덉?(理쒖냼 媛쒖닔 媛뺤젣 X)
    - ?듭떖 2嫄?core)? ?꾧꺽 寃뚯씠???덈ぉ/?먯삁/?꾨ℓ/?뺤콉 ?좏샇 + ?쒕ぉ ?덉쭏) ?듦낵留?遺??
    - ?섎㉧吏 湲곗궗???숈쟻 ?꾧퀎移?threshold) ?댁긽留?梨꾪깮
    - 留ㅼ껜 ?명뼢 ?꾪솕: 異쒖쿂 罹?吏諛??명꽣??怨쇰떎 諛⑹?) + 以묐났/?좎궗 ?쒕ぉ ?쒓굅
    """
    if not candidates:
        return []

    # 珥덇린??
    for a in candidates:
        a.is_core = False

    candidates_sorted = sorted(candidates, key=_sort_key_major_first, reverse=True)

    # ?숈쟻 ?꾧퀎移? ?곸쐞沅??먯닔媛 ??? ?좎? ???꾧꺽?섍쾶 而룻븯??'?듭? 梨꾩?'??留됰뒗??
    thr = _dynamic_threshold(candidates_sorted, section_key)

    # ?꾧퀎移??댁긽 ?꾨낫留??ъ슜(?놁쑝硫?鍮?由ъ뒪??
    pool = [a for a in candidates_sorted if a.score >= thr]


    # dist: ?숈씪 ?댁뒋(APC 以怨?媛쒖옣, ?쒖슱??遺?곹빀 ?좏넻 李⑤떒 ??媛 ?щ윭 留ㅼ껜濡?諛섎났?섎뒗 寃쎌슦媛 留롮븘
    # '?대깽????濡?癒쇱? 1李??대윭?ㅽ꽣留곹븯??以묐났?쇰줈 ?듭떖??諛由щ뒗 臾몄젣瑜??꾪솕?쒕떎.
    if section_key == "dist":
        pool = _dedupe_by_event_key(pool, section_key)

    if not pool:
        return []

    # ?뱀뀡 ?곹빀??section-fit)媛 留ㅼ슦 ??? ?꾨낫???곷떒 ?좊컻?먯꽌 ?쒖쇅(?? ?먯닔媛 異⑸텇???믪쑝硫??좎?)
    sec_conf = next((x for x in SECTIONS if x.get("key") == section_key), {})
    fit_filtered: list[Article] = []
    for a in pool:
        fit_sc = section_fit_score(a.title or "", a.description or "", sec_conf)
        if (fit_sc >= SECTION_FIT_MIN_FOR_TOP) or (float(getattr(a, "score", 0.0) or 0.0) >= (thr + 1.2)):
            fit_filtered.append(a)
    if fit_filtered:
        pool = fit_filtered

    # '理쒕? max_n'? ?곹븳(cap)?대ŉ, ?ㅼそ ?쏀븳 湲곗궗濡??듭? 梨꾩슦湲?諛⑹?瑜??꾪빐 tail-cut???붾떎
    best_score = float(getattr(pool[0], "score", 0.0) or 0.0)
    # ?뱀뀡蹂꾨줈 瑗щ━ ?덉슜??쓣 ?ㅻⅤ寃??좏넻/?꾩옣(dist)? ?꾩닔 諛⑹?瑜??꾪빐 ???꾧꺽)
    tail_margin_by_section = {
        "supply": 3.6,
        "policy": 3.8,
        "dist": 3.4,
        "pest": 3.6,
    }
    tail_margin = tail_margin_by_section.get(section_key, 3.6)

    # ?섏씠吏 ?몄텧?됱쓣 ?섎┫ ???? MAX_PER_SECTION=5) "?듭떖2" ???쇰컲 湲곗궗???곸젅???ы븿?섎룄濡?
    # tail-cut ??쓣 ?볧엺?? (core ?좎젙 濡쒖쭅/?먯닔??洹몃?濡??좎?)
    if MAX_PER_SECTION >= 5:
        try:
            extra = float(os.getenv("PAGE_TAIL_MARGIN_EXTRA", "4.0") or 0.0)
        except Exception:
            extra = 4.0
        extra = max(0.0, min(extra, 12.0))
        tail_margin += extra

    tail_cut = max(thr, best_score - tail_margin)

    # 異쒖쿂 罹?吏諛??명꽣??怨쇰떎 諛⑹?)
    tier_count = {1: 0, 2: 0, 3: 0}
    wire_count = 0  # ?듭떊/?⑤씪???쒕퉬??怨쇰??쒖쭛 諛⑹?
    # ??蹂댁닔?곸쑝濡??ъ슜???쇰뱶諛? 吏諛⑹?/?명꽣??鍮꾩쨷 怨쇰떎)
    tier1_cap = 1
    tier2_cap = 2 if section_key in ("supply", "policy") else 3

    def _source_ok_local(a: Article) -> bool:
        nonlocal wire_count
        # dist?먯꽌 ?듭떊/?⑤씪???쒕퉬?ㅻ뒗 ?곷떒???좎떇?섍린 ?ъ썙 1嫄대쭔 ?덉슜
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

    # 肄붿뼱 ?꾨낫: ?꾧퀎移?+ 肄붿뼱 理쒖냼?????꾧꺽)
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

    # 肄붿뼱(?듭떖2)?먯꽌 ?띿뾽 ?꾨Ц ?명꽣??留ㅼ껜媛 怨쇰룄?섍쾶 ?좎떇?섏? ?딅룄濡??ㅼ뼇??,
    # supply/policy?먯꽌??trade-press 肄붿뼱瑜?1嫄댁쑝濡??쒗븳(?꾩슂???꾪솕)
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

    def _already_used(a: Article) -> bool:
        k = _dup_key(a)
        return (k in used_title_keys) or (a.canon_url and a.canon_url in used_url_keys)

    def _mark_used(a: Article) -> None:
        used_title_keys.add(_dup_key(a))
        if a.canon_url:
            used_url_keys.add(a.canon_url)

    # 1) ?꾧꺽 肄붿뼱 2媛?
    for a in pool:
        if len(core) >= 2:
            break
        if a.score < core_min:
            continue
        if _already_used(a):
            continue
        # dist: 吏???⑥떊/怨듭??뺤? core ?꾨낫?먯꽌 ?쒖쇅(吏꾩쭨 ?댁뒋媛 諛由щ뒗 寃껋쓣 諛⑹?)
        if section_key == "dist" and is_local_brief_text(a.title or "", a.description or "", section_key):
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
            # ???뺤콉/?듭긽??媛뺥븯怨??덈ぉ ?곹뼢???쏀븳 湲곗궗(?쒕룄/?듦?/?좊떦愿??????
            # supply '?듭떖2'瑜??좎떇?섏? ?딅룄濡??쒖쇅?쒕떎. (policy ?뱀뀡?먯꽌 ?ㅻ８)
            if is_generic_import_item_context(mix):
                continue
            if is_policy_announcement_issue(mix, dom, pr):
                continue
            if is_trade_policy_issue(mix) and _h < 2.2:
                continue
            # supply ?듭떖2???덈ぉ ?섍툒 以묒떖?쇰줈 援ъ꽦: topic???뺤콉?대㈃ core?먯꽌 ?쒖쇅
            if (a.topic or "").strip() == "?뺤콉":
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
        # policy ?뱀뀡: 濡쒖뺄/??곗뼱(1) 留ㅼ껜媛 "?듭떖2"瑜??좎떇?섏? ?딅룄濡?core ?꾨낫?먯꽌 ?쒖쇅
        if section_key == "policy" and press_priority(a.press, a.domain) == 1:
            continue
        if _is_trade_press(a) and trade_core_count >= trade_core_cap:
            continue

        if not _source_ok_local(a):
            continue

        a.is_core = True
        core.append(a)
        _mark_used(a)
        _source_take(a)
        if _is_trade_press(a):
            trade_core_count += 1

    # 2) 肄붿뼱 遺議??? ?쎄컙 ?꾪솕(?ъ쟾???꾧퀎移??댁긽 + 以묐났 ?쒓굅) ???섏?留??듭? 梨꾩? 湲덉?
    if len(core) < 2:
        for a in pool:
            if len(core) >= 2:
                break
            # dist ?꾪솕 ?좊컻 ?꾧퀎媛? APC ?명봽???쒖꽕 湲곗궗(以怨?媛???좊퀎/??⑥????????뚰룺 ?꾪솕
            text = ((a.title or "") + " " + (a.description or "")).lower()
            apc_ctx_local = has_apc_agri_context(text)
            dist_eff_thr = thr
            if section_key == "dist" and apc_ctx_local and any(w in text for w in ("以怨?,"?꾧났","媛쒖옣","媛쒖냼","媛??,"?좊퀎","?좉낵","???,"??⑥???,"??κ퀬","ca???)):
                dist_eff_thr = max(0.0, thr - 0.8)
            if a.score < dist_eff_thr:
                continue
            if _already_used(a):
                continue
            # dist: 吏???⑥떊/怨듭??뺤? core ?꾨낫?먯꽌 ?쒖쇅
            if section_key == "dist" and is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            if section_key == "supply" and is_flower_consumer_trend_context((a.title + " " + a.description).lower()):
                continue
            if section_key == "supply" and (a.topic or "").strip() == "?뺤콉":
                continue
            # ?먯궛吏/?⑥냽/寃???섏텧 ?ㅼ썙?쒕쭔?쇰줈 嫄몃┛ ?쇰컲 湲곗궗 ?꾩닔 諛⑹?(?쒖옣/APC ?듭빱媛 ?놁쑝硫??쒖쇅)
            ops_hits = count_any(text, [t.lower() for t in ("?먯궛吏","遺?뺤쑀??,"?⑥냽","寃??,"?듦?","?섏텧")])
            market_anchor_hits = count_any(text, [t.lower() for t in ("媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"怨듭쁺?꾨ℓ?쒖옣","寃쎈씫","寃쎈ℓ","諛섏엯","?⑤씪???꾨ℓ?쒖옣","?곗??좏넻","?곗??좏넻?쇳꽣")])
            apc_ctx_local = has_apc_agri_context(text)
            agri_anchor_hits_local = count_any(text, [t.lower() for t in ("?띿궛臾?,"?띿뾽","?띿떇??,"?먯삁","怨쇱닔","怨쇱씪","梨꾩냼","?뷀쎕","?덊솕","泥?낵")])
            if ops_hits >= 1 and market_anchor_hits == 0 and (not apc_ctx_local) and agri_anchor_hits_local == 0 and best_horti_score(a.title or "", a.description or "") < 1.9:
                continue
            fit_sc_core = section_fit_score(a.title or "", a.description or "", sec_conf)
            if fit_sc_core < (core_fit_min - 0.1) and a.score < (core_min + 1.2):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in core):
                continue
            # policy ?뱀뀡: 濡쒖뺄/??곗뼱(1) 留ㅼ껜媛 "?듭떖2"瑜??좎떇?섏? ?딅룄濡?core ?꾨낫?먯꽌 ?쒖쇅
            if section_key == "policy" and press_priority(a.press, a.domain) == 1:
                continue
            if _is_trade_press(a) and trade_core_count >= trade_core_cap:
                continue

            if not _source_ok_local(a):
                continue

            a.is_core = True
            core.append(a)
            _mark_used(a)
            _source_take(a)

    # 3) ?좏넻(dist) ?뱀뀡: 媛뺥븳 ?꾩옣 ?듭빱(?꾨ℓ?쒖옣/怨듭쁺?꾨ℓ/APC 以怨??좊퀎/???臾쇰쪟/?먯궛吏 ?⑥냽/?섏텧 寃???? 0~2嫄?異붽?
    final: list[Article] = []
    for a in core:
        final.append(a)

    if section_key == "dist":
        anchor_terms = ("媛?쎌떆??, "?꾨ℓ?쒖옣", "怨듭쁺?꾨ℓ?쒖옣", "怨듯뙋??, "泥?낵", "寃쎈씫", "寃쎈ℓ", "諛섏엯",
                        "?곗??좏넻", "?곗??좏넻?쇳꽣", "?좊퀎", "???, "??⑥???, "??κ퀬", "ca???, "臾쇰쪟",
                        "?먯궛吏", "遺?뺤쑀??, "?⑥냽", "寃??, "?듦?", "?섏텧", "?⑤씪???꾨ℓ?쒖옣", "?섎굹濡쒕쭏??, "?먯“湲?)
        anchors = 0
        for a in pool:
            if anchors >= 2:
                break
            if a in final:
                continue
            if _already_used(a):
                continue
            # 吏???⑥떊/怨듭??뺤? dist ?듭빱 異붽? ?④퀎?먯꽌???쒖쇅
            if is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            text = (a.title + " " + a.description).lower()
            has_anchor = any(t.lower() in text for t in anchor_terms) or has_apc_agri_context(text)
            if not has_anchor:
                continue
            # 異붽? ?덉쟾?μ튂: ?띿궛臾??먯삁 ?듭빱媛 ?쏀븯硫?'?쇰컲 臾쇰쪟/寃쎌젣'濡?蹂닿퀬 ?쒖쇅
            agri_anchor_hits = count_any(text, [t.lower() for t in ("?띿궛臾?,"?띿뾽","?띿떇??,"?먯삁","怨쇱닔","怨쇱씪","梨꾩냼","?뷀쎕","?덊솕","泥?낵")])
            if agri_anchor_hits == 0 and best_horti_score(a.title, a.description) < 1.8 and count_any(text, [t.lower() for t in ("媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"怨듭쁺?꾨ℓ?쒖옣","寃쎈씫","寃쎈ℓ","諛섏엯","?⑤씪???꾨ℓ?쒖옣","?곗??좏넻","?곗??좏넻?쇳꽣")]) == 0:
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

            final.append(a)
            _mark_used(a)
            _source_take(a)
            anchors += 1

    
# 4) ?섎㉧吏(理쒕? max_n): ?꾧퀎移??댁긽 + 異쒖쿂 罹?+ 以묐났 ?쒓굅
    if MMR_DIVERSITY_ENABLED and len(pool) >= MMR_DIVERSITY_MIN_POOL and (max_n - len(final)) >= 2:
        # ??MMR(soft diversity): 以묐났? ?꾨땲吏留?'鍮꾩듂??湲곗궗' ?곗냽 ?몄텧???꾪솕
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
            # dist: ?대? 2嫄??댁긽 ?뺣낫???곹깭?먯꽌??吏???⑥떊/怨듭???湲곗궗??異붽??섏? ?딆쓬(鍮덉뭏 硫붿슦湲곗슜?쇰줈留??덉슜)
            if section_key == "dist" and len(final) >= 2 and is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            # ?먯닔 瑗щ━(tail)媛 ?쏀븯硫?異붽??섏? ?딅뒗???꾩슂??2~3媛쒕줈 醫낅즺)
            if a.score < tail_cut:
                continue
            if _already_used(a):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            # 異쒖쿂 罹≪? MMR ?좊컻?먯꽌???좎?(?좎젙 ?쒖젏???ㅼ떆 ?뺤씤)
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            eligible.append(a)

        while len(final) < max_n and eligible:
            sel_tris = [_mmr_tri(x) for x in final] if final else []
            best: Article | None = None
            best_tuple = None

            for a in eligible:
                # 異쒖쿂 罹?以묐났/?좎궗 ?ㅽ넗由??ㅻ뱶?쇱씤 寃뚯씠?몃뒗 "?좎젙 ?쒖젏"?먮룄 ?좎?
                if not _source_ok_local(a):
                    continue
                if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                    continue
                if any(_is_similar_story(a, b, section_key) for b in final):
                    continue

                tri_a = _mmr_tri(a)
                max_sim = 0.0
                if sel_tris and tri_a:
                    for tri_b in sel_tris:
                        max_sim = max(max_sim, _jaccard(tri_a, tri_b))

                # penalty scale(3.0)? ?먯닔 ?ㅼ?????6~16)??留욎텣 蹂댁닔??湲곕낯媛?
                mmr_val = float(getattr(a, "score", 0.0) or 0.0) - (MMR_DIVERSITY_LAMBDA * 3.0 * max_sim)

                # tie-breaker: 蹂??먯닔/留ㅼ껜/理쒖떊 ??
                tie = (press_priority(a.press, a.domain), getattr(a, "pub_dt_kst", None) or datetime.min.replace(tzinfo=KST))
                cand = (mmr_val, float(getattr(a, "score", 0.0) or 0.0), tie)

                if best is None or cand > best_tuple:
                    best = a
                    best_tuple = cand

            if best is None:
                break

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
            # dist: ?대? 2嫄??댁긽 ?뺣낫???곹깭?먯꽌??吏???⑥떊/怨듭???湲곗궗??異붽??섏? ?딆쓬(鍮덉뭏 硫붿슦湲곗슜?쇰줈留??덉슜)
            if section_key == "dist" and len(final) >= 2 and is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            # ?먯닔 瑗щ━(tail)媛 ?쏀븯硫?異붽??섏? ?딅뒗???꾩슂??2~3媛쒕줈 醫낅즺)
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
            final.append(a)
            _mark_used(a)
            _source_take(a)
# 4.2) dist(?좏넻/?꾩옣) ?뱀뀡 ?뚰봽??諛깊븘:
    # - ?대뼡 ?좎? ?숈쟻 ?꾧퀎移?瑗щ━ 而룹쑝濡?1~2嫄대쭔 ?⑤뒗 寃쎌슦媛 ?덉쓬.
    # - ?대븣 '吏諛⑹??쇰룄 ?댁슜???좎쓽誘명븳 湲곗궗'瑜??섎떒??1~2嫄??뺣룄 異붽? ?몄텧(?듭? 梨꾩?? 湲덉?).
    if section_key == "dist" and len(final) < min(3, max_n):
        need = min(3, max_n) - len(final)
        # ?꾧퀎移섎낫???댁쭩 ?꾪솕?섎릺, BASE_MIN_SCORE ?꾨옒濡쒕뒗 ?대젮媛吏 ?딆쓬
        relax_cut = max(BASE_MIN_SCORE.get("dist", 7.2) - 0.6, thr - 2.0)
        # 異쒖쿂 罹〓룄 ?꾩＜ ?뚰룺 ?꾪솕(濡쒖뺄 1嫄?異붽? ?덉슜)
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
            if a.score < relax_cut:
                continue
            if _already_used(a):
                continue
            # ?뺤튂/?ш굔???쒕ぉ ?꾩닔???ㅼ떆 ?쒕쾲 諛⑹뼱(?먯닔???믪븘??dist ?듭떖怨?臾닿???寃쎌슦媛 ?덉쓬)
            ttl_l = (a.title or "").lower()
            if any(w in ttl_l for w in ("?쒖＜4.3", "4.3", "?ъ깮??, "蹂댁긽", "?대?", "?꾪빑", "怨꾩뾼")) and best_horti_score(a.title or "", "") < 1.3:
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
            final.append(a)
            _mark_used(a)
            _source_take(a)
            need -= 1
    # 4.5) supply 蹂닿컯: ?뷀쎕 ?뚮퉬/?좊Ъ ?몃젋???? ?덇퀬 苑껊떎諛?苑껊떎諛??좊Ъ ?몃젋????
    # - ?덈ぉ 諛??섍툒 ?숉뼢?먯꽌留?"鍮꾪빑???쇰줈 0~1嫄??섎떒 ?몄엯
    # - core(?듭떖2)?먮뒗 ?덈? ?ы븿?섏? ?딆쓬
    if section_key == "supply" and len(final) < max_n:
        added = 0
        for a in pool:
            if added >= 1 or len(final) >= max_n:
                break
            if a in final:
                continue
            if _already_used(a):
                continue
            # ?덈Т ??? ?먯닔(?꾧퀎移??ш쾶 ?섑쉶)???쒖쇅?섎릺, ?몃젋?쒗삎? ?쎄컙 ?꾪솕
            if a.score < max(thr - 0.6, 0.0):
                continue
            txt2 = (a.title + " " + a.description).lower()
            if not is_flower_consumer_trend_context(txt2):
                continue
            # ?좏넻 ?꾨줈紐⑥뀡/愿愿??곗삁/李쎌뾽???몄씠利덈뒗 ?⑥닔?먯꽌 ?쒖쇅??
            if any(_is_similar_title(a.title_key, b.title_key) for b in final):
                continue
            if any(_is_similar_story(a, b, section_key) for b in final):
                continue
            if not _source_ok_local(a):
                continue

            a.is_core = False
            final.append(a)
            _mark_used(a)
            _source_take(a)
            added += 1

    # 媛뺤젣 ?뱀뀡 ?대룞 湲곗궗(?? policy->pest)??理쒖쥌 ?몄텧?먯꽌 ?щ씪吏吏 ?딅룄濡??곗꽑 ?ы븿 蹂댁옣
    forced_items = [a for a in candidates_sorted if getattr(a, "forced_section", "") == section_key]
    for fa in forced_items:
        if fa in final:
            continue
        if len(final) < max_n:
            final.append(fa)
            continue
        # 怨듦컙???놁쑝硫?理쒗븯???먯닔 1嫄댁쓣 ?泥?
        if final:
            repl_idx = min(range(len(final)), key=lambda i: float(getattr(final[i], "score", 0.0) or 0.0))
            final[repl_idx] = fa

    # pest ?뱀뀡 ?덉쟾?μ튂: 諛⑹젣 ?ㅽ뻾??臾몃㎘ 湲곗궗(?덉같/?쎌젣/?꾩닔議곗궗 ??媛 理쒖쥌 ?좊컻?먯꽌 諛???щ씪吏吏 ?딅룄濡?蹂댁옣
    if section_key == "pest":
        exec_like = [a for a in candidates_sorted if is_pest_control_policy_context(((a.title or "") + " " + (a.description or "")).lower())]
        keep_exec = []
        for a in final:
            try:
                if is_pest_control_policy_context(((a.title or "") + " " + (a.description or "")).lower()):
                    keep_exec.append(a)
            except Exception:
                pass

        # ?ㅽ뻾??湲곗궗 理쒕? 2嫄닿퉴吏 蹂댁옣
        need_exec = max(0, min(2, max_n) - len(keep_exec))
        if need_exec > 0:
            for ea in exec_like:
                if need_exec <= 0:
                    break
                if ea in final:
                    continue
                if len(final) < max_n:
                    final.append(ea)
                    need_exec -= 1
                    continue
                if final:
                    # ?대? ?ㅼ뼱媛??ㅽ뻾???꾨낫瑜??ㅼ떆 諛?대궡吏 ?딅룄濡?non-exec 理쒗븯?꾨???援먯껜
                    non_exec_idx = [i for i, x in enumerate(final) if not is_pest_control_policy_context(((x.title or "") + " " + (x.description or "")).lower())]
                    if non_exec_idx:
                        repl_idx = min(non_exec_idx, key=lambda i: float(getattr(final[i], "score", 0.0) or 0.0))
                    else:
                        repl_idx = min(range(len(final)), key=lambda i: float(getattr(final[i], "score", 0.0) or 0.0))
                    final[repl_idx] = ea
                    need_exec -= 1

    # 留덉?留??덉쟾?μ튂: ?숈씪 URL 以묐났 ?쒓굅
    seen = set()
    deduped: list[Article] = []
    for a in final:
        k = a.canon_url or _dup_key(a)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(a)

    # Debug report payload (top candidates + selection decisions)
    if DEBUG_REPORT:
        try:
            selected_keys = set()
            for _a in deduped[:max_n]:
                selected_keys.add(_a.canon_url or _a.norm_key or _a.title_key)

            top_n = max(5, min(DEBUG_REPORT_MAX_CANDIDATES, 60))
            top_candidates = candidates_sorted[:top_n]

            def _signals(a: Article) -> dict:
                txt = (a.title + " " + a.description).lower()
                return {
                    "horti_sc": round(best_horti_score(a.title, a.description), 2),
                    "market_hits": (count_any(txt, [t.lower() for t in ("媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"泥?낵","寃쎈씫","寃쎈ℓ","諛섏엯","?⑤씪???꾨ℓ?쒖옣","?곗??좏넻","?곗??좏넻?쇳꽣")]) + (1 if has_apc_agri_context(txt) else 0)),
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
                return "not_selected"

            top_rows = []
            for a in top_candidates:
                k = a.canon_url or a.norm_key or a.title_key
                sel = k in selected_keys
                top_rows.append({
                    "selected": bool(sel),
                    "is_core": bool(getattr(a, "is_core", False)),
                    "score": round(a.score, 2),
                    "tier": press_priority(a.press, a.domain),
                    "press": a.press,
                    "domain": a.domain,
                    "title": (a.title or "")[:160],
                    "url": (a.originallink or a.link or "")[:500],
                    "reason": "" if sel else _best_effort_reason(a),
                    "signals": _signals(a),
                })

            payload = {
                "threshold": round(thr, 2),
                "core_min": round(core_min, 2),
                "total_candidates": len(candidates),
                "total_selected": len(deduped[:max_n]),
                "top": top_rows,
            }
            dbg_set_section(section_key, payload)
        except Exception:
            pass


    return deduped[:max_n]



# -----------------------------
# Optional RSS ingestion (怨듭떇/?좊ː ?뚯뒪 蹂닿컯)
# - WHITELIST_RSS_URLS ?섍꼍蹂?섏뿉 RSS URL???ｌ쑝硫??대떦 ?뚯뒪?먯꽌 湲곗궗 ?꾨낫瑜?異붽??쒕떎.
# - 湲곕낯? OFF(鍮?媛??대ŉ, 湲곗〈 Naver OpenAPI 湲곕컲 ?뚯씠?꾨씪?몄? 洹몃?濡??좎??쒕떎.
# -----------------------------
def fetch_rss_items(rss_url: str) -> list[dict]:
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
    # RSS pubDate???뺤떇???ㅼ뼇??蹂댁닔?곸쑝濡?泥섎━(?ㅽ뙣 ??None)
    if not pub:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            dt = datetime.strptime(pub, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone(timedelta(hours=9)))
        except Exception:
            continue
    return None

def collect_rss_candidates(section_conf: dict, start_kst: datetime, end_kst: datetime) -> list["Article"]:
    if not WHITELIST_RSS_URLS:
        return []
    out: list[Article] = []
    _local_dedupe = DedupeIndex()
    for rss in WHITELIST_RSS_URLS:
        for it in fetch_rss_items(rss):
            title = clean_text(it.get("title", ""))
            desc = clean_text(it.get("description", ""))
            link = strip_tracking_params(it.get("link", "") or "")
            pub = _rss_pub_to_kst(it.get("pubDate", ""))
            if not pub:
                # ?좎쭨媛 ?놁쑝硫??덈룄??諛뽰씪 ???덉쑝誘濡??쒖쇅
                continue
            if pub < effective_start_kst or pub >= end_kst:
                continue
            dom = domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue
            press = normalize_press_label(press_name_from_url(link), link)
            if not is_relevant(title, desc, dom, link, section_conf, press):
                continue
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
            ))
    return out


# -----------------------------
# Recall backfill helpers (broad-query safety net)
# -----------------------------
_RECALL_SIGNALS_BY_SECTION = {
    "supply": ["臾닿???, "?섏엯", "愿??, "FTA", "?좊떦愿??],
    "policy": ["?梨?, "吏??, "?좊떦愿??, "寃??, "愿??, "臾닿???, "?섏엯"],
    "dist": ["?꾨ℓ?쒖옣", "?먯궛吏", "?⑥냽", "寃??, "?듦?", "?섏텧", "臾쇰쪟"],
    "pest": ["蹂묓빐異?, "諛⑹젣", "?덉같", "寃??],
}

def _extract_seed_terms_from_queries(queries: list[str], limit: int = 6) -> list[str]:
    """荑쇰━ 由ъ뒪?몄뿉??'????덈ぉ/?ㅼ썙??泥??좏겙)'瑜?異붿텧.
    - ?? '諛?怨쇱씪 ?섍툒' -> '諛?, '?ㅼ씤癒몄뒪罹?媛寃? -> '?ㅼ씤癒몄뒪罹?
    - 媛쒖꽑: ?욎そ 荑쇰━???명뼢?섏? ?딅룄濡??꾩껜 荑쇰━瑜??쒗쉶?섎ŉ 怨좊Ⅴ寃?seed瑜??섏쭛.
    - 媛쒖꽑: ?곗샂??湲고샇媛 ?ы븿??荑쇰━?먯꽌??泥??섎? ?좏겙???덉젙?곸쑝濡?異붿텧.
    """
    out: list[str] = []
    if not queries:
        return out
    cap = max(0, int(limit or 0))
    if cap == 0:
        return out
    skip = {"怨쇱씪", "梨꾩냼", "?띿궛臾?, "?띿떇??, "?섍툒", "媛寃?, "?좏넻", "?뺤콉", "寃??}
    for q in queries:
        q = (q or "").strip().lower()
        if not q:
            continue
        toks = re.findall(r"[0-9a-z媛-??{2,}", q)
        tok = ""
        for t in toks:
            if t in skip:
                continue
            tok = t
            break
        if not tok:
            continue
        if tok not in out:
            out.append(tok)
        if len(out) >= cap:
            break
    return out


_QUERY_TOKEN_STOPWORDS = {
    "?섍툒", "媛寃?, "?묓솴", "異쒗븯", "?뺤콉", "釉뚮━??, "蹂대룄?먮즺", "?띿궛臾?, "?띿떇??, "怨쇱씪", "梨꾩냼",
    "?숉뼢", "?댁뒋", "?梨?, "吏??, "寃??, "?좏넻", "?꾩옣", "諛⑹젣", "蹂묓빐異?,
}

def _query_tokens(q: str) -> list[str]:
    """荑쇰━?먯꽌 ?섎? ?덈뒗 ?좏겙留?異붿텧(?ㅽ뙵??愿묒뿭 荑쇰━ ?뺣???蹂댁젙??."""
    toks = re.findall(r"[0-9a-z媛-??{2,}", (q or "").lower())
    out: list[str] = []
    for t in toks:
        if t in _QUERY_TOKEN_STOPWORDS:
            continue
        if t not in out:
            out.append(t)
    return out

def _query_article_match_ok(q: str, title: str, desc: str, section_key: str) -> bool:
    """荑쇰━-湲곗궗 ?뺥빀??泥댄겕.

    - 愿묒뿭/蹂닿컯 荑쇰━?먯꽌 諛쒖깮?섎뒗 ?ㅽ깘??以꾩씠湲??꾪빐, ?섎? ?좏겙??湲곗궗 ?띿뒪?몄뿉 理쒖냼 1媛??댁긽 ?ы븿?섎뒗吏 ?뺤씤.
    - ?ㅻ쭔 policy ?뱀뀡? 怨듦났湲곌? 釉뚮━?묒씠 ?쒕ぉ/蹂몃Ц ?쒗쁽??蹂?뺣릺??寃쎌슦媛 ?덉뼱 ?꾪솕 湲곗? ?곸슜.
    """
    toks = _query_tokens(q)
    if not toks:
        return True
    txt = f"{title or ''} {desc or ''}".lower()
    hit = sum(1 for t in toks if t in txt)
    if section_key == "policy":
        return hit >= 1
    # ?섎? ?좏겙??3媛??댁긽??湲?荑쇰━??理쒖냼 2媛?留ㅼ묶 ?붽뎄
    need = 2 if len(toks) >= 3 else 1
    return hit >= need

def _seed_terms_from_topics(candidates_sorted: list["Article"], thr: float, cap: int = 4) -> list[str]:
    """pool ???좏뵿 遺꾪룷?먯꽌 seed term??留뚮뱺??
    - ?곸쐞 ?좏뵿 2媛?+ (媛?ν븯硫? 而ㅻ쾭媛 0???좏뵿 1~2媛쒕? ?욎뼱 '?꾨씫?????ъ갑
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

    # TOPICS??(topic_name, synonyms) ?뺥깭
    # topic_name??'媛먭랠/留뚭컧'?대㈃ synonyms[0]??'媛먭랠' ?앹쑝濡?留ㅽ븨?섏뼱 ?덉쓬.
    out: list[str] = []

    # 1) ?곸쐞 ?좏뵿 2媛?
    top_topics = sorted(topic_cnt.items(), key=lambda x: x[1], reverse=True)[:2]
    for tn, _ in top_topics:
        for name, syns in TOPICS:
            if name == tn:
                term = (syns[0] if syns else (tn.split("/")[0] if tn else "")).strip()
                if term and term not in out:
                    out.append(term)
                break

    # 2) 而ㅻ쾭媛 0???좏뵿(媛?ν븯硫?1~2媛?
    missing_terms: list[str] = []
    skip_topics = {"?꾨ℓ?쒖옣", "APC/?곗??좏넻", "?섏텧/寃??}  # ?뱀뀡/?쒓렇??荑쇰━濡??대? ???≫엳????
    for name, syns in TOPICS:
        if name in skip_topics:
            continue
        if topic_cnt.get(name, 0) >= 1:
            continue
        term = (syns[0] if syns else (name.split("/")[0] if name else "")).strip()
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

def _build_recall_fallback_queries(section_key: str, section_conf: dict, candidates_sorted: list["Article"], thr: float) -> tuple[list[str], dict]:
    """?꾨낫 ? ?꾨씫??以꾩씠湲??꾪븳 '愿묒뿭 蹂닿컯 荑쇰━'瑜??앹꽦.
    諛섑솚: (queries, meta)
    - meta??DEBUG_REPORT?먯꽌 ?뺤씤 媛?ν븯?꾨줉 ?④릿??
    """
    meta = {"seed_terms": [], "reason": [], "queries": []}
    if not RECALL_BACKFILL_ENABLED:
        return [], meta

    section_key = str(section_key or "")
    base_queries = list(section_conf.get("queries") or [])
    signals = _RECALL_SIGNALS_BY_SECTION.get(section_key, [])

    # seed terms: (1) pool ?좏뵿 湲곕컲 (2) 荑쇰━ 湲곕컲 ?좏겙
    seed_terms = []
    try:
        seed_terms.extend(_seed_terms_from_topics(candidates_sorted, thr, cap=4))
    except Exception:
        pass
    try:
        seed_terms.extend(_extract_seed_terms_from_queries(base_queries, limit=6))
    except Exception:
        pass

    # dedupe + cap
    st2: list[str] = []
    for t in seed_terms:
        t = (t or "").strip()
        if not t:
            continue
        if t not in st2:
            st2.append(t)
        if len(st2) >= 5:
            break
    seed_terms = st2
    meta["seed_terms"] = list(seed_terms)

    # trade-signal coverage check (supply/policy only)
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

    # 1) seed term ?⑤룆(愿묒뿭)
    for t in seed_terms:
        if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
            break
        if t and (t not in base_queries) and (t not in out):
            out.append(t)

    # 2) seed term + signals (?뱀뀡蹂?
    # - ?덈Т 留롮? 議고빀??留뚮뱾吏 ?딄퀬, seed??1~2媛쒕줈 ?쒗븳
    for t in seed_terms:
        if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
            break
        # supply/policy: trade 愿???좏샇 ?곗꽑
        sigs = list(signals)
        if section_key in ("supply", "policy") and not has_trade:
            sigs = ["臾닿???, "?섏엯", "愿??, "FTA", "?좊떦愿??] + sigs
        # seed??理쒕? 2媛쒕쭔
        added_for_term = 0
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
            if added_for_term >= 2:
                break

    # 3) ?뱀뀡蹂?怨듯넻(?⑹뼱媛 ?щ씪???≫엳?? 蹂닿컯 荑쇰━ 1~2媛?(cap ?댁뿉??
    if len(out) < RECALL_QUERY_CAP_PER_SECTION:
        common = []
        if section_key in ("supply", "policy"):
            common = ["留뚮떎由?臾닿???, "誘멸뎅 留뚮떎由?臾닿???, "留뚭컧瑜?臾닿???, "?섏엯 怨쇱씪 臾닿???, "?좊떦愿??怨쇱씪", "?섏엯 ?띿궛臾?愿??, "?섏엯 怨쇱씪 FTA"]
        elif section_key == "dist":
            common = ["?먯궛吏 ?⑥냽 ?띿궛臾?, "寃???듦? ?띿궛臾?, "?꾨ℓ?쒖옣 諛섏엯 ?띿궛臾?]
        elif section_key == "pest":
            common = ["怨쇱닔 蹂묓빐異?諛⑹젣", "蹂묓빐異??덉같", "寃??蹂묓빐異?]

        for q in common:
            if len(out) >= RECALL_QUERY_CAP_PER_SECTION:
                break
            if q in base_queries or q in out:
                continue
            out.append(q)

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

def collect_candidates_for_section(section_conf: dict, start_kst: datetime, end_kst: datetime) -> list[Article]:
    """Collect candidates for a section.

    湲곕낯 ?숈옉? 1?섏씠吏(=湲곗〈怨??숈씪)?대ŉ, ?꾨옒 議곌굔??留뚯”???뚯뿉留??쇰? 荑쇰━?????2?섏씠吏(start=51)瑜?異붽? ?몄텧?쒕떎.
    - COND_PAGING_ENABLED(?곹븳 2?섏씠吏 ?덉슜) AND
    - ?꾨낫 ?(pool: dynamic threshold ?댁긽)??max_n 誘몃쭔 AND
    - ?꾨낫 媛쒖닔 ?먯껜媛 ?덈Т ?곸쓬(=?덉쭏 臾몄젣媛 ?꾨땲??? 遺議?媛?μ꽦) AND
    - (?덉쟾) 珥?異붽? ?몄텧???뱀뀡??異붽?荑쇰━?섍? ?덉궛 ??
    """
    queries = _dedupe_queries(section_conf.get("queries") or [])
    # pest??pool 異⑸텇 ?щ?? 臾닿??섍쾶 ?ㅽ뻾??諛⑹젣 蹂닿컯 荑쇰━瑜?蹂묓빀???꾨씫??以꾩씤??
    if str(section_conf.get("key") or "") == "pest":
        queries = _dedupe_queries(list(queries) + list(PEST_ALWAYS_ON_RECALL_QUERIES))
    items: list[Article] = []
    _local_dedupe = DedupeIndex()  # ?뱀뀡 ?대? dedupe (?꾩뿭? 理쒖쥌 ?좏깮 ?④퀎?먯꽌)

    section_key = str(section_conf.get("key") or "")
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

    api_items_by_query: dict[str, int] = {}    # raw items returned by API per query (before time/relevance filters)
    page1_full_queries: set[str] = set()       # API returned full display(=50) on page1 -> high volume hint
    recall_meta: dict = {}                     # recall backfill metadata (for debug)

    def _ingest_naver_items(q: str, data: dict):
        nonlocal items, _local_dedupe
        if not isinstance(data, dict):
            return
        for it in (data.get("items", []) or []):
            title = clean_text(it.get("title", ""))
            desc = clean_text(it.get("description", ""))
            link = strip_tracking_params(it.get("link", "") or "")
            origin = strip_tracking_params(it.get("originallink", "") or link)
            pub = parse_pubdate_to_kst(it.get("pubDate", ""))

            # ?섏쭛 ?④퀎? ?꾨컲 ?뺣━ ?④퀎???덈룄??湲곗???諛섎뱶???숈씪?섍쾶 ?좎?
            # (遺덉씪移???"?섏쭛?먮떎媛 ?꾨컲????젣"?섎뒗 ?뚭?媛 諛쒖깮?????덉쓬)
            if pub < effective_start_kst or pub >= end_kst:
                continue

            dom = domain_of(origin) or domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue

            press = normalize_press_label(press_name_from_url(origin or link), (origin or link))
            if not is_relevant(title, desc, dom, (origin or link), section_conf, press):
                continue

            # 荑쇰━-湲곗궗 ?뺥빀??泥댄겕(?듯듃??: broad/recall 荑쇰━?먯꽌 ?쒕ぉ留?鍮꾩듂???ㅽ깘 ?좎엯 ?듭젣
            if QUERY_ARTICLE_MATCH_GATE_ENABLED and (not _query_article_match_ok(q, title, desc, section_key)):
                continue

            canon = canonicalize_url(origin or link)
            title_key = norm_title_key(title)
            topic = extract_topic(title, desc)
            norm_key = make_norm_key(canon, press, title_key)

            # ?щ줈?ㅻ뜲??理쒓렐 N?? 以묐났 諛⑹?: 72h ?덈룄???뺤옣 ??媛숈? 湲곗궗媛 諛섎났 ?몄텧?섎뒗 寃?理쒖냼??
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
            )
            art.score = compute_rank_score(title, desc, dom, pub, section_conf, press)
            items.append(art)
            hits_by_query[q] = hits_by_query.get(q, 0) + 1

    # -----------------------------
    # 1) Base pass: always 1 page
    # -----------------------------
    def fetch_page1(q: str):
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

    # pest ?뱀뀡 由ъ퐳 蹂닿컯: always-on 荑쇰━??page2(start=51)瑜??좎젣?곸쑝濡?1???섏쭛
    # - 議곌굔遺 ?섏씠吏?need_more)怨?蹂꾨룄濡??숈옉?쒖폒, page1 ?곸쐞 湲곗궗??媛?ㅼ쭊 ?ㅽ뻾??湲곗궗瑜?蹂닿컯?쒕떎.
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
            # NOTE: ?꾩뿭 extra-call budget? supply/policy?먯꽌 癒쇱? ?뚯쭊?????덉뼱,
            # pest always-on page2 蹂닿컯? 蹂꾨룄 ?뚮웾 cap?쇰줈 ?낅┰ ?섑뻾?쒕떎.
            # (?ㅽ뻾??蹂묓빐異?湲곗궗 由ъ퐳 ?덉젙??紐⑹쟻)
            for q in always_qs[:PEST_ALWAYS_ON_PAGE2_QUERY_CAP]:
                try:
                    data_p2 = naver_news_search(q, display=50, start=51, sort="date")
                except Exception as e:
                    log.warning("[WARN] pest always-on page2 query failed: %s", e)
                    continue
                _ingest_naver_items(q, data_p2)
    except Exception:
        pass

    # pest ?뱀뀡 由ъ퐳 蹂닿컯(2): naver web 寃??webkr) ?뚮웾 ?섏쭛
    # - ?댁뒪 ?몃뜳??吏???꾨씫 ?쒖뿉??湲곗궗 URL???뺣낫?섍린 ?꾪븳 ?덉쟾留?
    try:
        if section_key == "pest" and PEST_WEB_RECALL_ENABLED and queries and PEST_WEB_RECALL_QUERY_CAP > 0:
            always_qs = [q for q in queries if q in set(PEST_ALWAYS_ON_RECALL_QUERIES)]
            for q in always_qs[:PEST_WEB_RECALL_QUERY_CAP]:
                try:
                    data_w = naver_web_search(q, display=10, start=1, sort="date")
                except Exception as e:
                    log.warning("[WARN] pest web recall query failed: %s", e)
                    continue
                for it in (data_w.get("items", []) if isinstance(data_w, dict) else []):
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
                    if not is_relevant(title, desc, dom, (origin or link), section_conf, press):
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
                    )
                    art.score = compute_rank_score(title, desc, dom, pub, section_conf, press)
                    items.append(art)
                    hits_by_query[q] = hits_by_query.get(q, 0) + 1
    except Exception:
        pass

    # Optional RSS candidates (?좊ː ?뚯뒪 蹂닿컯)
    try:
        items.extend(collect_rss_candidates(section_conf, start_kst, end_kst))
    except Exception:
        pass

    # 理쒖쥌 ?덉쟾?μ튂: ?섏쭛 寃쎈줈(RSS/異붽??뚯뒪)? 臾닿??섍쾶 ?덈룄??諛?湲곗궗???쒖쇅
    items = [a for a in items if (a.pub_dt_kst is not None) and (effective_start_kst <= a.pub_dt_kst < end_kst)]
    items.sort(key=_sort_key_major_first, reverse=True)

    # -----------------------------
    # 2) Conditional extra pass: only when pool is lacking
    # -----------------------------
    try:
        if COND_PAGING_ENABLED and COND_PAGING_EXTRA_QUERY_CAP_PER_SECTION > 0 and queries:
            # ?꾨낫媛 '?덈Т 留롮????좏깮???곸? ??(?덉쭏 臾몄젣)? 異붽? ?섏씠吏媛 ?꾩??섏? ?딆쑝誘濡??ㅽ궢
            if len(items) <= COND_PAGING_TRIGGER_CANDIDATE_CAP:
                candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
                thr = _dynamic_threshold(candidates_sorted, section_key)
                pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)

                # 理쒖냼 紐⑺몴(?섍꼍?ㅼ젙 諛섏쁺): MIN_PER_SECTION??0?대㈃ 3??湲곕낯?쇰줈
                min_n = (MIN_PER_SECTION if MIN_PER_SECTION > 0 else 3)
                min_n = max(1, min(min_n, max_n))

                # pool??遺議깊븯嫄곕굹(?뱁엳 min 誘몃떖), ?꾨낫 ?섎룄 ?됰꼮移??딆쓣 ?뚮쭔 蹂닿컯
                need_more = (pool_cnt < min_n) or (pool_cnt < max_n and len(items) < max(12, max_n * 3))
                if need_more:

                    # (蹂닿컯) pool 遺議깆씪 ?뚮쭔, '臾댁뿭/愿??臾닿???FTA/?섏엯' 議고빀 荑쇰━瑜??뚮웾 異붽?濡?1?섏씠吏 ?섏쭛
                    # - ?뱀젙 湲곗궗 留욎땄???꾨땲?? ?꾨컲?곸쑝濡?"?섏엯/愿???댁뒋媛 ?덈ぉ ?섍툒??誘몄튂???곹뼢" 湲곗궗?ㅼ쓣 ???덉젙?곸쑝濡??ъ갑?섍린 ?꾪븿
                    fallback_qs, recall_meta = _build_recall_fallback_queries(section_key, section_conf, candidates_sorted, thr)

                    if fallback_qs:
                        for fq in fallback_qs:
                            if fq in queries:
                                continue
                            if not _cond_paging_take_budget(1):
                                break
                            try:
                                dataF = naver_news_search_paged(fq, display=50, pages=1, sort="date")
                            except Exception as e:
                                log.warning("[WARN] fallback query failed: %s", e)
                                continue
                            _ingest_naver_items(fq, dataF)

                        # ?ъ젙??
                        items = [a for a in items if (a.pub_dt_kst is not None) and (effective_start_kst <= a.pub_dt_kst < end_kst)]
                        items.sort(key=_sort_key_major_first, reverse=True)
                    # ?대뼡 荑쇰━??異붽? ?섏씠吏瑜?遺숈씪吏 ?좏깮
                    # - 1?섏씠吏?먯꽌 hit媛 ?덉뿀??荑쇰━ ?곗꽑 (異붽? ?섏씠吏???깃낵 媛?μ꽦????
                    # - 洹몃옒??遺議깊븯硫??뱀뀡 荑쇰━ 由ъ뒪???욎そ(?쇰컲/踰붿슜)?먯꽌 理쒖냼 seed瑜?梨꾩?
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

                    # 異붽? ?섏씠吏 ?섏쭛 (2..COND_PAGING_MAX_PAGES) ???덉궛/議곌린醫낅즺 ?ы븿
                    extra_added = 0
                    pages_tried = 0

                    for q in picked:
                        # ?대? 異⑸텇?댁?硫?洹몃쭔
                        candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
                        thr = _dynamic_threshold(candidates_sorted, section_key)
                        pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)
                        if pool_cnt >= max_n:
                            break

                        for p in range(COND_PAGING_BASE_PAGES + 1, COND_PAGING_MAX_PAGES + 1):
                            if not _cond_paging_take_budget(1):
                                break
                            st = 1 + ((p - 1) * 50)  # 2?섏씠吏=51, 3?섏씠吏=101 ...
                            pages_tried += 1
                            try:
                                dataN = naver_news_search(q, display=50, start=st, sort="date")
                            except Exception as e:
                                log.warning("[WARN] query page%d failed: %s", p, e)
                                continue

                            before = len(items)
                            _ingest_naver_items(q, dataN)
                            extra_added += max(0, len(items) - before)

                            # 議곌린 醫낅즺: pool??異⑸텇?댁?硫?洹몃쭔
                            candidates_sorted = sorted(items, key=_sort_key_major_first, reverse=True)
                            thr = _dynamic_threshold(candidates_sorted, section_key)
                            pool_cnt = sum(1 for a in candidates_sorted if getattr(a, "score", 0.0) >= thr)

                            # ?꾨낫媛 異⑸텇??而ㅼ죱嫄곕굹 pool 紐⑺몴 ?꾨떖 ??以묐떒
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
    except Exception:
        # extra pass should never break the pipeline
        pass

    
    # Debug: collection meta (queries/hits/recall) -> docs/debug/YYYY-MM-DD.json
    if DEBUG_REPORT:
        try:
            hits_top = sorted(list(hits_by_query.items()), key=lambda x: x[1], reverse=True)[:15]
            api_top = sorted(list(api_items_by_query.items()), key=lambda x: x[1], reverse=True)[:15]
            meta = {
                "effective_window": {
                    "start_kst": effective_start_kst.isoformat() if isinstance(effective_start_kst, datetime) else str(effective_start_kst),
                    "end_kst": end_kst.isoformat() if isinstance(end_kst, datetime) else str(end_kst),
                },
                "base_queries_n": int(len(queries)),
                "base_queries": list(queries[:30]),
                "api_items_top": api_top,
                "window_hits_top": hits_top,
                "page1_full_queries": sorted(list(page1_full_queries))[:20],
                "recall_meta": recall_meta if isinstance(recall_meta, dict) else {},
                "items_total": int(len(items)),
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
# Referenced reports (KREI ?댁뒋+ ?? ?먮룞 ?ы븿
# -----------------------------
_KREI_ISSUE_RX = re.compile(r"?댁뒋\+\s*??\s*(\d{1,4})\s*??)

def _extract_krei_issue_refs(by_section: dict[str, list["Article"]]) -> dict[int, datetime]:
    """湲곗궗 ?띿뒪?몄뿉??'?댁뒋+ ?쏯N??瑜?李얠븘 (issue_no -> ???pub_dt)濡?諛섑솚."""
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
                # 媛??理쒓렐(??? pub_dt瑜??ъ슜
                if (n not in out) or (pub > out[n]):
                    out[n] = pub
    return out

def _pick_best_web_item(items: list[dict], issue_no: int) -> dict | None:
    """KREI ?댁뒋+ 留곹겕 ?꾨낫 以?理쒖쟻 1媛쒕? ?좏깮."""
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
        # KREI ?꾨찓???곗꽑
        if ("krei.re.kr" in dom) or ("repository.krei.re.kr" in dom):
            score = 3
        else:
            score = 0
        t = clean_text(it.get("title", ""))
        d = clean_text(it.get("description", ""))
        blob = (t + " " + d).lower()
        if str(issue_no) in blob:
            score += 1
        if "?댁뒋+" in blob or "issue+" in blob:
            score += 1
        if best is None or score > best[0]:
            best = (score, it)
    return best[1] if best else None

def _maybe_add_krei_issues_to_policy(raw_by_section: dict[str, list["Article"]], start_kst: datetime, end_kst: datetime):
    """湲곗궗?먯꽌 ?멸툒??KREI ?댁뒋+ 蹂닿퀬?쒕? 李얠븘 policy ?뱀뀡??異붽?."""
    refs = _extract_krei_issue_refs(raw_by_section)
    if not refs:
        return

    policy_conf = None
    for s in SECTIONS:
        if s.get("key") == "policy":
            policy_conf = s
            break
    if not policy_conf:
        return

    # 怨쇰룄???몄텧 諛⑹?: 理쒕? 3嫄닿퉴吏留?
    for issue_no, ref_pub in list(sorted(refs.items(), key=lambda x: x[0]))[:3]:
        try:
            q = f'?쒓뎅?띿큿寃쎌젣?곌뎄??"?댁뒋+" ??issue_no}??
            data = naver_web_search(q, display=10, start=1, sort="date")
            it = _pick_best_web_item(data.get("items", []) if isinstance(data, dict) else [], issue_no)
            if not it:
                continue

            title = clean_text(it.get("title", "")) or f"KREI ?댁뒋+ ??issue_no}??
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
            topic = "蹂닿퀬??
            norm_key = make_norm_key(canon, press, title_key)

            # ?щ줈?ㅻ뜲??理쒓렐 N?? 以묐났 諛⑹?: 72h ?덈룄???뺤옣 ??媛숈? 湲곗궗媛 諛섎났 ?몄텧?섎뒗 寃?理쒖냼??
            if CROSSDAY_DEDUPE_ENABLED and (canon in RECENT_HISTORY_CANON or norm_key in RECENT_HISTORY_NORM):
                continue

            if not _local_dedupe.add_and_check(canon, press, title_key, norm_key):
                continue

            a = Article(
                section="policy",
                title=f"[蹂닿퀬?? {title}",
                description=desc,
                link=link,
                originallink=link,
                pub_dt_kst=ref_pub,  # 湲곗궗?먯꽌 ?멸툒???좎쭨瑜???쒕줈
                domain=dom,
                press=press,
                norm_key=norm_key,
                title_key=title_key,
                canon_url=canon,
                topic=topic,
            )
            a.score = compute_rank_score(a.title, a.description, dom, ref_pub, policy_conf, press)

            raw_by_section.setdefault("policy", []).append(a)

        except Exception as e:
            log.warning("[WARN] add KREI issue report failed: issue=%s err=%s", issue_no, e)



def is_macro_policy_issue(text: str) -> bool:
    """'二쇱슂 ?댁뒋' ?깃꺽??臾쇨?/媛寃?湲곗궗?몄? ?먮떒.
    - ?뺤콉 諛쒗몴(?梨?吏???? ?뺥깭媛 ?꾨땲?대룄, ?깆닔???ш낵/諛??? 媛寃?臾쇨? ?먮쫫? policy ?뱀뀡?먯꽌 ?ㅻ，??
    - ?뱁엳 紐낆젅(??異붿꽍) ?꾪썑 媛寃?湲됰벑쨌湲됰씫 ?댁뒋??'二쇱슂 ?댁뒋'濡?痍④툒?쒕떎.
    - ?? 援?젣?듭긽/?곗뾽 ?쇰컲 湲곗궗???뚮퉬?먮Ъ媛 ?섏뿴??湲곗궗???쒖쇅?쒕떎.
    """
    t = (text or "").lower()
    if not t:
        return False

    if is_macro_trade_noise_context(t):
        return False
    if is_general_consumer_price_noise(t) and best_horti_score("", t) < 1.6:
        return False

    # 1) 臾쇨?/?듦퀎/?깆닔???좏샇(紐낆떆??
    macro_terms = ("臾쇨?", "?뚮퉬?먮Ъ媛", "臾쇨?吏??, "cpi", "kosis", "李⑤???, "?깆닔??, "泥닿컧", "臾쇨??뺣낫")
    macro_hit = count_any(t, [w.lower() for w in macro_terms])

    # 2) 紐낆젅 ?꾪썑 媛寃??댁뒋(?붿떆?? ??'臾쇨?' ?⑥뼱媛 ?놁뼱??二쇱슂 ?댁뒋濡??쇱슦??
    if macro_hit == 0 and any(w in t for w in ("??, "紐낆젅", "異붿꽍", "?紐?)):
        if ("媛寃? in t) and ("?곸듅" in t or "?섎씫" in t or "湲됰벑" in t or "湲됰씫" in t):
            macro_hit = 1

    if macro_hit < 1:
        return False

    if ("媛寃? not in t) and ("?곸듅" not in t) and ("?섎씫" not in t) and ("湲됰벑" not in t) and ("湲됰씫" not in t):
        return False

    # ?띿뾽/?먯삁 留λ씫 ?먮뒗 ?먯삁 ?먯닔
    try:
        horti = best_horti_score("", t)
    except Exception:
        horti = 0.0

    # ?덈Т ?쏀븳 寃쎌슦(?쇰컲 ?뚮퉬 湲곗궗) 諛⑹?: ?먯삁 ?먯닔 ?먮뒗 ?덈ぉ/?띿궛臾??ㅼ썙???꾩슂
    if horti >= 1.4:
        return True
    if any(w in t for w in ("?띿궛臾?, "?띿떇??, "怨쇱씪", "梨꾩냼", "?ш낵", "諛?, "媛먭랠", "?멸린", "留뚭컧", "?щ룄")):
        return True

    return False


def _global_section_reassign(raw_by_section: dict[str, list["Article"]], start_kst: datetime, end_kst: datetime) -> int:
    """?꾨낫瑜??뱀뀡蹂꾨줈 ?섏쭛???? 紐⑤뱺 ?뱀뀡 湲곗??쇰줈 ?ы룊媛?섏뿬 best section?쇰줈 ?대룞.
    - 紐⑹쟻: '?대뼡 荑쇰━濡??≫삍?붿?'??醫뚯슦?섎뒗 ?ㅻ텇瑜섎? 以꾩씠怨? ?꾨씫(?뱁엳 policy/dist)???꾪솕
    - ?먯튃: (1) 媛뺥븳 ?대룞 洹쇨굅(?먯닔 ?대뱷 + 理쒖냼 留λ씫)???뚮쭔 ?대룞 (2) pest??湲곕낯 ?좎?
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

    for a in all_items:
        cur = str(getattr(a, "section", "") or "")
        if cur not in conf_by_key:
            cur = "supply" if "supply" in conf_by_key else (keys[0] if keys else cur)

        # pest??湲곕낯 ?좎?(?뱀뀡 ?ㅼ퐫?대쭅蹂대떎 而⑦뀓?ㅽ듃 ?먯젙??以묒슂)
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
        strong_pest_context = is_pest_control_policy_context(txt)

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
                dist_like = count_any(txt, [t.lower() for t in ("?꾨ℓ?쒖옣","怨듯뙋??,"媛?쎌떆??,"寃쎈씫","寃쎈ℓ","諛섏엯","?곗??좏넻","?곗??좏넻?쇳꽣","apc","臾쇰쪟","?먯궛吏","?⑥냽","寃??,"?듦?","?섏텧","?좏넻","?꾨ℓ")])
                if dist_like < 2 and (not has_apc_agri_context(txt)):
                    continue
            if k == "policy":
                # ?뺤콉??臾몃㎘??嫄곗쓽 ?놁쑝硫??대룞 ?꾨낫?먯꽌 ?쒖쇅(?? 怨듭떇 ?꾨찓?몄? ?덉쇅)
                # - ?듭긽/愿??寃???듦? 湲곗궗??policy ?꾨낫濡??ы븿(?덈ぉ 留λ씫???쏀븷 ??
                # - 吏?먯껜 ?띿궛臾??뺤콉 ?꾨줈洹몃옩(吏??蹂댁쟾/?쒕쾾?ъ뾽)? policy ?대룞 ?꾨낫濡??덉슜
                _policy_like = False
                try:
                    _h = best_horti_score(a.title or "", a.description or "")
                except Exception:
                    _h = 0.0
                if is_policy_announcement_issue(txt, dom, press) or is_macro_policy_issue(txt):
                    _policy_like = True
                elif is_trade_policy_issue(txt) and _h < 2.2:
                    _policy_like = True
                elif is_local_agri_policy_program_context(txt):
                    _policy_like = True

                if not _policy_like:
                    try:
                        if not _is_policy_official(a):
                            continue
                    except Exception:
                        continue
            if k == "pest":
                # 蹂묓빐異?諛⑹젣 媛뺤떊??+ ?먯삁 留λ씫???덉쓣 ?뚮쭔 pest ?대룞 ?꾨낫濡??덉슜
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

            # ?щ텇瑜섎뒗 score肉??꾨땲??section-fit 媛쒖꽑???덉뼱???곗꽑 ?덉슜
            if fit_new + SECTION_REASSIGN_FIT_GUARD < cur_fit:
                continue

            if fit_new > best_fit_score:
                best_fit_score = float(fit_new)
                best_fit_key = k

            if sc > best_score:
                best_score = float(sc)
                best_key = k

        # 蹂묓빐異??ㅽ뻾??臾몃㎘? policy/湲고? ?뱀뀡 ?먯닔? 臾닿??섍쾶 pest瑜??곗꽑 怨좎젙?쒕떎.
        force_move_to_pest = (cur != "pest") and strong_pest_context and ("pest" in conf_by_key)

        # ?대룞 湲곗?: ?먯닔 ?대뱷??異⑸텇???뚮쭔(?ㅻ텇瑜?吏꾨룞 諛⑹?)
        if force_move_to_pest:
            try:
                pest_conf = conf_by_key["pest"]
                if is_relevant(a.title, a.description, dom, url, pest_conf, press):
                    pest_score = compute_rank_score(a.title, a.description, dom, a.pub_dt_kst, pest_conf, press)
                    a.section = "pest"
                    a.score = float(pest_score)
                    moved += 1
            except Exception:
                pass
        elif best_key != cur and (best_score - cur_score) >= GLOBAL_SECTION_REASSIGN_MIN_GAIN:
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
    """媛뺥븳 蹂묓빐異??ㅽ뻾 臾몃㎘ 湲곗궗??policy ?붾쪟瑜??덉슜?섏? ?딄퀬 pest濡??곗꽑 ?대룞?쒕떎."""
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

        a.section = "pest"
        a.forced_section = "pest"
        if pest_conf is not None:
            try:
                a.score = compute_rank_score(a.title, a.description, d, a.pub_dt_kst, pest_conf, p)
            except Exception:
                pass
        # 理쒖쥌 ?몄텧?먯꽌 諛???щ씪吏吏 ?딅룄濡? policy->pest 媛뺤젣 ?대룞遺꾩뿉???뚰룺 ?곗꽑?쒖쐞 蹂댁젙
        try:
            a.score = float(getattr(a, "score", 0.0) or 0.0) + 4.0
        except Exception:
            pass

        if pest_idx.add_and_check(a.canon_url, a.press, a.title_key, a.norm_key):
            pest_items.append(a)
        else:
            # 以묐났?ㅺ? ?대? ?덉쑝硫????믪? ?먯닔 湲곗궗濡?援먯껜(媛뺤젣 ?대룞遺??뚯떎 諛⑹?)
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


def collect_all_sections(start_kst: datetime, end_kst: datetime):
    raw_by_section: dict[str, list[Article]] = {}

    ordered = sorted(SECTIONS, key=lambda s: 0 if s["key"] == "policy" else 1)
    for sec in ordered:
        raw_by_section[sec["key"]] = collect_candidates_for_section(sec, start_kst, end_kst)

    # 湲곗궗?먯꽌 ?멸툒??蹂닿퀬???먮즺(KREI ?댁뒋+ ??瑜?policy ?뱀뀡???먮룞 蹂댁셿
    try:
        _maybe_add_krei_issues_to_policy(raw_by_section, start_kst, end_kst)
    except Exception as e:
        log.warning("[WARN] report augmentation failed: %s", e)

    # ???뺤콉/湲곌? ?꾨찓???뺤콉釉뚮━???띿떇?덈?/aT/?띻???KREI ??? ?섍툒/?좏넻 荑쇰━?먮룄 嫄몃┫ ???덈떎.
    #    ?섏쭛 ?④퀎?먯꽌???대젮?먮릺, 理쒖쥌 ?뱀뀡? policy濡?媛뺤젣 ?대룞(?꾨씫/?ㅻ텇瑜?諛⑹?).
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
                # policy-like(?뺤콉/?듭긽/?쒕룄) 湲곗궗硫?policy濡??대룞
                trade_like = False
                try:
                    _h = best_horti_score(a.title or "", a.description or "")
                except Exception:
                    _h = 0.0
                if is_trade_policy_issue(_mix_text) and _h < 2.2:
                    # dist ?듭빱(?꾨ℓ?쒖옣/APC/寃쎈씫/諛섏엯 ??媛 媛뺥븯硫?dist濡??④꺼???섎?濡??ш린???대룞?섏? ?딆쓬
                    _dist_hits = count_any(_mix_text, [t.lower() for t in (
                        "媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"怨듭쁺?꾨ℓ?쒖옣","寃쎈씫","寃쎈ℓ","諛섏엯",
                        "?곗??좏넻","?곗??좏넻?쇳꽣","apc","?꾨ℓ踰뺤씤","以묐룄留?,"?쒖옣?꾨ℓ??,
                        "臾쇰쪟","臾쇰쪟?쇳꽣","異쒗븯","吏묓븯"
                    )])
                    if _dist_hits < 2 and (not has_apc_agri_context(_mix_text)):
                        trade_like = True

                if is_policy_announcement_issue(_mix_text, d, p) or is_macro_policy_issue(_mix_text) or trade_like:

                    a.section = "policy"
                    # policy ?뱀뀡 湲곗??쇰줈 ?ъ뒪肄붿뼱留?
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
            # policy ?대??먯꽌???뱀뀡-??dedupe瑜??쒕쾲 ???곸슜
            try:
                _p_dedupe = DedupeIndex()
                uniq = []
                for a in raw_by_section.get("policy", []):
                    if _p_dedupe.add_and_check(a.canon_url, a.press, a.title_key, a.norm_key):
                        uniq.append(a)
                raw_by_section["policy"] = uniq
            except Exception:
                pass


    # ???뱀뀡 ?ъ“??rebalancing)
    # - policy媛 '?먮ℓ ?곗씠??湲곕컲 ?뚮퉬 ?몃젋???뚮ℓ 遺꾩꽍' 湲곗궗濡?怨쇰??댁???寃껋쓣 諛⑹?
    # - dist媛 鍮꾨뒗 ???꾨ℓ?쒖옣/APC 湲곗궗 ?쒗쁽??媛꾩젒?곸씤 寃쎌슦) supply?먯꽌 dist濡??대룞?쒖폒 ?꾨씫??以꾩엫
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
            # topic??'?뺤콉' ?깃꺽?대㈃ policy瑜??좎? (?뱀뀡/?쒓렇 遺덉씪移?諛⑹?)
            if tpc and ("?뺤콉" in tpc or tpc in ("?뺣?", "?쒕룄", "踰?, "愿??, "?덉궛", "吏??)):
                keep_policy.append(a)
                continue
            # ?뚮ℓ 留ㅼ텧/?먮ℓ ?곗씠??湲곕컲 ?몃젋???? 臾댁씤 怨쇱씪媛寃??먮ℓ ?곗씠????supply媛 ?먯뿰?ㅻ윭?
            if is_retail_sales_trend_context(txt) and (not policy_domain_override(d, txt)):
                # supply濡??ы룊媛?댁꽌 ?듦낵???뚮쭔 ?대룞
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
        # dist ?꾨낫媛 ?덈Т ?곸쑝硫?supply?먯꽌 '?좏넻/?꾨ℓ/APC/?섏텧' ?좏샇媛 媛뺥븳 湲곗궗瑜?dist濡??대룞
        dist_now = len(raw_by_section.get("dist", []) or [])
        if dist_now < 4:
            moved_sd = 0
            keep_supply = []
            for a in raw_by_section.get("supply", []) or []:
                txt = (a.title + " " + a.description).lower()
                d = normalize_host(a.domain or "")
                p = (a.press or "").strip()

                # dist-like ?먯젙(蹂댁닔??: ?좏넻/?꾨ℓ/APC/?꾨ℓ踰뺤씤/?섏뿭/臾쇰쪟/?섏텧/寃????+ ?먯삁 留λ씫
                dist_like_hits = count_any(txt, [t.lower() for t in (
                    "媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"怨듭쁺?꾨ℓ?쒖옣","寃쎈씫","寃쎈ℓ","諛섏엯",
                    "?곗??좏넻","?곗??좏넻?쇳꽣","apc","?꾨ℓ踰뺤씤","以묐룄留?,"?쒖옣?꾨ℓ??,
                    "?섏뿭","?섏뿭鍮?,"?섏뿭??","臾쇰쪟","臾쇰쪟?쇳꽣","異쒗븯","吏묓븯",
                    "?먯궛吏","遺?뺤쑀??,"?⑥냽","寃??,"?듦?","?섏텧","?좏넻","?꾨ℓ"
                )])
                agri_media_bonus = 1 if d in {"agrinet.co.kr","nongmin.com","aflnews.co.kr","farminsight.net"} else 0
                dist_min_hits = 2 if agri_media_bonus else 3
                # ?띿뾽?꾨Ц留ㅼ껜 湲곗궗?쇰룄 ?좏넻/?꾨ℓ/APC/異쒗븯/臾쇰쪟 ?좏샇媛 理쒖냼 2媛쒕뒗 ?덉뼱??dist濡??대룞
                if dist_like_hits >= dist_min_hits and (best_horti_score(a.title, a.description) >= 1.6 or count_any(txt, [t.lower() for t in ("?띿궛臾?,"?띿떇??,"?먯삁","怨쇱닔","怨쇱씪","梨꾩냼","泥?낵","?뷀쎕","?덊솕")]) >= 1):
                    # dist 湲곗??쇰줈???듦낵???뚮쭔 ?대룞
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
    # Topic?봖ection ?쇨???媛뺤젣 (?뺤콉/?듭긽/愿?맞룻넻愿 吏묓뻾 ?댁뒋??policy ?뱀뀡?쇰줈)
    #
    # 湲곗〈?먮뒗 a.topic == "?뺤콉"???뚮쭔 ?대룞???쒕룄??
    # ?ㅼ젣濡쒕뒗 愿???듦?/?뺣? 議곗튂 湲곗궗?몃뜲 topic??'?뺤콉'?쇰줈 遺꾨쪟?섏? ?딆? 寃쎌슦
    # (?? ?댁뒪??愿??蹂댁꽭援ъ뿭 湲곗궗)媛 supply???⑤뒗 臾몄젣媛 ?덉뿀??
    #
    # 媛쒖꽑: topic??'?뺤콉'???꾨땲?붾씪??
    #       (1) ?듭긽/愿??寃???듦? ?뺤콉??is_trade_policy_issue ????媛뺥븯怨?
    #       (2) ?먯삁/?덈ぉ 吏곸젒??best_horti_score)???쏀븯硫?
    # policy濡??대룞?쒕떎. ?? 媛먭랠/留뚭컧瑜섏쿂???덈ぉ ?곹뼢??媛뺥븯硫?supply???④만 ???덈떎.
    # -----------------------------
    moved_topic = 0
    for _sec_key in list(raw_by_section.keys()):
        items = raw_by_section.get(_sec_key, []) or []
        if not items:
            continue
        keep_items: list[Article] = []
        for a in items:
            # ?대? policy硫??좎?
            if a.section == "policy":
                keep_items.append(a)
                continue

            tpc = (a.topic or "").strip()
            mix = (a.title + " " + a.description).lower()
            d = normalize_host(a.domain or "")
            p = (a.press or "").strip()

            # ?뺤콉/?듭긽/愿?맞룻넻愿 ?댁뒋 ?먯젙(鍮좊Ⅸ ?먯젙)
            policy_like = (
                (tpc == "?뺤콉")
                or is_generic_import_item_context(mix)
                or is_trade_policy_issue(mix)
                or is_policy_announcement_issue(mix, d, p)
                or is_macro_policy_issue(mix)
            )

            if not policy_like:
                keep_items.append(a)
                continue

            # ?덈ぉ(?먯삁) 吏곸젒???됯?: 媛뺥븯硫?supply ?좎?(?좏뵿留?援먯젙)
            try:
                bt, bs = best_topic_and_score(a.title, a.description)
            except Exception:
                bt, bs = ("", 0.0)

            try:
                horti_sc = best_horti_score(a.title, a.description)
            except Exception:
                horti_sc = 0.0

            # ???덈ぉ ?곹뼢??異⑸텇??媛뺥븯硫??좏뵿+?먯삁?먯닔) ?뱀뀡 ?대룞 諛⑹?
            if bt and bs >= 2.4 and horti_sc >= 2.2:
                a.topic = bt
                keep_items.append(a)
                continue

            # 洹????뺤콉??媛?+ ?덈ぉ 吏곸젒??????policy濡??대룞
            a.section = "policy"
            raw_by_section.setdefault("policy", []).append(a)
            moved_topic += 1
            continue

        raw_by_section[_sec_key] = keep_items
    if moved_topic:
        log.info("[REBALANCE] moved %d item(s) by policy-like override: -> policy", moved_topic)

    # ??Global section reassignment (best section by rescoring; reduces query-driven misplacement)
    try:
        if GLOBAL_SECTION_REASSIGN_ENABLED:
            moved_global = _global_section_reassign(raw_by_section, start_kst, end_kst)
            if moved_global:
                log.info("[REASSIGN] moved %d item(s) by global rescoring", moved_global)
    except Exception as e:
        log.warning("[WARN] global section reassignment failed: %s", e)

    # ?덉쟾?μ튂: policy???⑥븘?덈뒗 蹂묓빐異??ㅽ뻾??臾몃㎘??理쒖쥌 ?좏깮 ??pest濡?媛뺤젣 ?뺣━
    try:
        moved_pf = _enforce_pest_priority_over_policy(raw_by_section)
        if moved_pf:
            log.info("[REBALANCE] moved %d pest-context item(s): policy -> pest", moved_pf)
    except Exception as e:
        log.warning("[WARN] pest-priority rebalance failed: %s", e)

    final_by_section: dict[str, list[Article]] = {}
    global_dedupe = DedupeIndex()

    # ???꾩뿭 dedupe??'?꾨낫 ?섏쭛'???꾨땲??'理쒖쥌 ?좏깮'?먯꽌 ?곸슜(?뱀뀡 媛??꾨씫 諛⑹?)
    for sec in SECTIONS:
        key = sec["key"]
        candidates = raw_by_section.get(key, [])

        # ?뱀뀡 ?대? ?덉쭏/?꾧퀎移?洹쇱젒以묐났 ?듭젣??湲곗〈 濡쒖쭅 ?좎??섎릺,
        # ?꾩뿭 dedupe濡??명빐 ?ㅽ궢?????덉쑝???ъ쑀遺꾩쓣 ??戮묒븘?붾떎.
        buffer_n = max(MAX_PER_SECTION * 8, 60)
        pre = select_top_articles(candidates, key, buffer_n)

        picked: list[Article] = []
        for a in pre:
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


    # dist_empty_fallback_from_supply:
    # ?좏넻/?꾩옣 ?뱀뀡??鍮꾩뿀?붾뜲 supply???좏넻 ?깃꺽 湲곗궗媛 ?⑥븘 ?덉쑝硫?1嫄?蹂댁젙 ?대룞
    try:
        if (not final_by_section.get("dist")) and final_by_section.get("supply"):
            dist_conf = next((s for s in SECTIONS if s["key"] == "dist"), None)
            moved_one = None
            keep_supply2 = []
            for a in final_by_section.get("supply", []):
                txt = ((a.title or "") + " " + (a.description or "")).lower()
                d = normalize_host(a.domain or "")
                p = (a.press or "").strip()
                dist_signals = count_any(txt, [t.lower() for t in (
                    "?꾨ℓ?쒖옣","怨듯뙋??,"媛?쎌떆??,"apc","?곗??좏넻","?꾨ℓ踰뺤씤","以묐룄留?,"?쒖옣?꾨ℓ??,
                    "?섏뿭","臾쇰쪟","異쒗븯","吏묓븯","?섏텧","?듦?","寃??,"?좏넻","?꾨ℓ"
                )])
                horti_signals = count_any(txt, [t.lower() for t in ("?띿궛臾?,"?띿떇??,"?먯삁","怨쇱닔","怨쇱씪","梨꾩냼","泥?낵","?뷀쎕","?덊솕")])
                agri_media = d in {"agrinet.co.kr","nongmin.com","aflnews.co.kr","farminsight.net"}
                if moved_one is None and dist_conf and dist_signals >= (2 if agri_media else 3) and horti_signals >= 1:
                    try:
                        if is_relevant(a.title, a.description, d, a.canon_url or a.url, dist_conf, p):
                            a.section = "dist"
                            a.score = compute_rank_score(a.title, a.description, d, a.pub_dt_kst, dist_conf, p)
                            moved_one = a
                            continue
                    except Exception:
                        pass
                keep_supply2.append(a)
            if moved_one is not None:
                final_by_section["supply"] = keep_supply2
                final_by_section["dist"] = [moved_one]
                log.info("[REBALANCE] dist empty fallback moved 1 item: supply -> dist (%s)", normalize_host(moved_one.domain or ""))
    except Exception as e:
        log.warning("[WARN] dist empty fallback failed: %s", e)

    return final_by_section


def _emit_section_selection_metrics(by_section: dict[str, list[Article]], *, stage: str) -> None:
    try:
        counts: dict[str, int] = {}
        for sec in SECTIONS:
            key = sec["key"]
            counts[key] = len(by_section.get(key, []) or [])
            metric_inc("section.selected", value=counts[key], stage=stage, section=key)
        reject_count = len(DEBUG_DATA.get("filter_rejects", []) or []) if isinstance(DEBUG_DATA, dict) else 0
        metric_inc("section.filter_rejects", value=reject_count, stage=stage)
        log_event("section.selection", stage=stage, counts=counts, filter_rejects=reject_count)
    except Exception as e:
        log.warning("[WARN] section metric emit failed: %s", e)


# -----------------------------
# OpenAI summaries (optional)
# -----------------------------
def openai_extract_text(resp_json: dict) -> str:
    try:
        out = resp_json.get("output", [])
        if not out:
            return ""
        for block in out:
            for c in block.get("content", []):
                if c.get("type") in ("output_text", "text") and "text" in c:
                    return c["text"]
        return ""
    except Exception:
        return ""

def load_summary_cache(repo: str, token: str) -> dict:
    """?붿빟 罹먯떆瑜?repo ?뚯씪?먯꽌 濡쒕뱶.
    援ъ“:
      { norm_key: {"s": "?붿빟", "t": "2026-02-22T..."} }
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

def _prune_summary_cache(cache: dict) -> dict:
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

def save_summary_cache(repo: str, token: str, cache: dict):
    path = OPENAI_SUMMARY_CACHE_PATH
    cache2 = _prune_summary_cache(cache or {})
    raw_new = json.dumps(cache2, ensure_ascii=False, indent=2)
    raw_old, sha = github_get_file(repo, path, token, ref="main")
    if (raw_old or "").strip() == raw_new.strip():
        return
    github_put_file(repo, path, raw_new, token, f"Update summary cache ({len(cache2)})", sha=sha, branch="main")

def _openai_summarize_rows(rows: list[dict]) -> dict:
    """OpenAI Responses API瑜??몄텧??rows瑜??붿빟.
    異쒕젰 ?뺤떇: 媛?以?'id\t?붿빟'
    """
    if not OPENAI_API_KEY or not rows:
        return {}

    system = (
        "?덈뒗 ?랁삊 寃쎌젣吏二??먯삁?섍툒遺(怨쇱닔?뷀쎕) ?ㅻТ?먮? ?꾪븳 '?띿궛臾??댁뒪 ?붿빟媛'??\n"
        "- ?덈? ?곸긽/異붿젙?쇰줈 ?ъ떎??留뚮뱾吏 留덈씪.\n"
        "- 媛?湲곗궗 ?붿빟? 2臾몄옣 ?? 110~200???? ?듭떖 ?⑺듃 以묒떖.\n"
        "異쒕젰 ?뺤떇: 媛?以?'id\t?붿빟' ?뺥깭濡쒕쭔 異쒕젰."
    )
    user = "湲곗궗 紐⑸줉(JSON):\n" + json.dumps(rows, ensure_ascii=False)

    payload = {
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

    simplified = False  # HTTP 400 ??optional ?뚮씪誘명꽣 ?쒓굅 ??1???ъ떆??

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
            metric_inc("openai.retry", reason="network")
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
            metric_inc("openai.retry", reason="http", status=str(r.status_code))
            backoff = retry_after_or_backoff(r.headers, attempt, base=0.8, cap=20.0, jitter=0.4)
            log.warning("[OpenAI] transient HTTP %s (attempt %d/%d) -> sleep %.1fs", r.status_code, attempt+1, OPENAI_RETRY_MAX, backoff)
            time.sleep(backoff)
            continue

        # HTTP 400: 紐⑤뜽/?듭뀡 ?뚮씪誘명꽣 遺덉씪移??? reasoning/text ?듭뀡 誘몄??? 媛??
        # - optional ?뚮씪誘명꽣(reasoning/text)瑜??쒓굅?섍퀬 1?뚮쭔 ?ъ떆?꾪븳??
        if r.status_code == 400 and (("reasoning" in payload) or ("text" in payload)) and (not simplified):
            simplified = True
            payload.pop("reasoning", None)
            payload.pop("text", None)
            log.warning("[OpenAI] HTTP 400 -> retry once without optional params: %s", _safe_body(getattr(r, "text", ""), limit=400))
            time.sleep(0.6)
            continue

        metric_inc("openai.skipped", status=str(r.status_code))
        log.warning("[OpenAI] summarize skipped: %s", _safe_body(getattr(r, "text", ""), limit=500))
        return {}

    if last_resp is not None:
        metric_inc("openai.giveup")
        log.warning("[OpenAI] summarize failed after retries: %s", _safe_body(getattr(last_resp, "text", ""), limit=500))
    return {}

def openai_summarize_batch(articles: list[Article], cache: dict | None = None) -> dict:
    """湲곗궗?ㅼ쓣 諛곗튂濡??붿빟. cache媛 ?덉쑝硫?罹먯떆???ㅻ뒗 ?몄텧?먯꽌 ?쒖쇅."""
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

def fill_summaries(by_section: dict, cache: dict | None = None, allow_openai: bool = True):
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
# GitHub Pages path helpers (??4踰? 404 諛⑹?)
# -----------------------------
def get_site_path(repo: str) -> str:
    """
    GitHub Pages ?꾨줈?앺듃 ?ъ씠?몄쓽 base path瑜?寃곗젙.
    - ?쇰컲 ?꾨줈?앺듃: https://owner.github.io/REPO/  -> site_path="/REPO/"
    - ?ъ슜??議곗쭅 ?ъ씠?? https://owner.github.io/ -> repo_name??*.github.io ?????덉쓬 -> site_path="/"
    """
    _owner, name = repo.split("/", 1)
    if name.lower().endswith(".github.io"):
        return "/"
    return f"/{name}/"

def build_site_url(site_path: str, rel: str) -> str:
    site_path = site_path if site_path.endswith("/") else site_path + "/"
    rel = rel.lstrip("/")
    return site_path + rel


def build_daily_url(base_url: str, report_date: str, cache_bust: bool = False) -> str:
    """Build daily archive URL; optional cache-busting query for messenger/browser caches."""
    url = f"{str(base_url or '').rstrip('/')}/archive/{report_date}.html"
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
    # ?쒖??? 怨쇨굅 ?섏씠吏???뱀뀡 ?쒓린瑜?理쒖떊 ?щ㎎?쇰줈 ?듭씪
    if not title:
        return ""
    t = str(title)
    if t.startswith("?좏넻 諛??꾩옣"):
        return "?좏넻 諛??꾩옣"
    if t == "?뺤콉 諛?二쇱슂 ?댁뒋":
        return "?뺤콉 諛?二쇱슂 ?댁뒋"
    return t



def _normalize_existing_chipbar_titles(html_text: str) -> str:
    """Normalize chipbar title labels on already-existing chipbars (do not require rebuild).

    Some older archived pages already have a chipbar generated by older code, so
    `display_section_title()` did not run and long labels (e.g. "?좏넻 諛??꾩옣 (...)")
    remain. This function updates only the visible label text inside `.chipTitle`.
    """
    if not html_text or 'class="chipTitle"' not in html_text:
        return html_text

    def _repl(m: re.Match) -> str:
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
        cnt_m = re.search(r"<div[^>]*class=[\"\']secCount[\"\'][^>]*>\s*(\d+)\s*嫄?s*</div>", body, flags=re.I | re.S)
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

WEEKDAY_KR = ["??, "??, "??, "紐?, "湲?, "??, "??]

def weekday_label(iso_date: str) -> str:
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
        return WEEKDAY_KR[d.weekday()]
    except Exception:
        return ""

def render_debug_report_html(report_date: str, site_path: str) -> str:
    """HTML ?섎떒???쎌엯?섎뒗 ?붾쾭洹?由ы룷???듭뀡).
    ?쒖꽦?? ?섍꼍蹂??DEBUG_REPORT=1
    - ?꾨낫 ?곸쐞 N媛??먯닔/?좏샇/?좎젙?щ?
    - ?꾪꽣留??④퀎?먯꽌 ?쒖쇅???쇰? 湲곗궗? ?ъ쑀
    - (?듭뀡) docs/debug/YYYY-MM-DD.json 留곹겕
    """
    if not DEBUG_REPORT:
        return ""

    with _DEBUG_LOCK:
        data = {
            "generated_at_kst": DEBUG_DATA.get("generated_at_kst"),
            "build_tag": DEBUG_DATA.get("build_tag"),
            "filter_rejects": list(DEBUG_DATA.get("filter_rejects", [])),
            "sections": dict(DEBUG_DATA.get("sections", {})),
        }

    # ?붿빟(?ъ쑀 移댁슫??
    reason_count = {}
    for r in data["filter_rejects"]:
        reason = r.get("reason", "unknown")
        reason_count[reason] = reason_count.get(reason, 0) + 1
    reason_items = sorted(reason_count.items(), key=lambda x: x[1], reverse=True)[:12]

    # JSON 留곹겕(?묒꽦 ?듭뀡??耳쒖졇 ?덉쓣 ?뚮쭔)
    json_href = ""
    if DEBUG_REPORT_WRITE_JSON:
        json_href = build_site_url(site_path, f"debug/{report_date}.json")

    def _kv(label: str, value: str) -> str:
        return f"<span class='dbgkv'><b>{esc(label)}:</b> {esc(value)}</span>"

    # ?뱀뀡 ?뚯씠釉?
    sec_blocks = []
    for sec_key, payload in data["sections"].items():
        top = payload.get("top", [])
        rows = []
        for it in top:
            sig = it.get("signals", {}) or {}
            badge = "?? if it.get("selected") else "??
            core = "?듭떖" if it.get("is_core") else ""
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
        rows_html = "".join(rows) if rows else "<tr><td colspan='12' class='muted'>?쒖떆???꾨낫媛 ?놁뒿?덈떎.</td></tr>"

        sec_blocks.append(f"""
        <div class="dbgSec">
          <div class="dbgSecHead">
            <b>{esc(sec_key)}</b>
            <span class="muted">candidates={payload.get('total_candidates','?')} selected={payload.get('total_selected','?')} thr={payload.get('threshold','?')} core_min={payload.get('core_min','?')}</span>
          </div>
          <div class="dbgTableWrap">
            <table class="dbgTable">
              <thead>
                <tr>
                  <th class="c">?좎젙</th><th class="c">?듭떖</th><th class="r">?먯닔</th><th class="c">Tier</th>
                  <th>留ㅼ껜</th><th>?꾨찓??/th>
                  <th class="r">?덈ぉ</th><th class="r">?쒖옣</th><th class="r">媛뺤떊??/th><th class="r">?ㅽ봽</th>
                  <th>誘몄꽑???ъ쑀</th><th>?쒕ぉ</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>
        """)

    # ?꾪꽣留??쒖쇅 ???곸쐞 ?쇰?)
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
    rej_html = "".join(rej_rows) if rej_rows else "<tr><td colspan='5' class='muted'>?꾪꽣留??쒖쇅 濡쒓렇媛 ?놁뒿?덈떎.</td></tr>"

    reason_line = ", ".join([f"{k}({v})" for k, v in reason_items]) if reason_items else "??

    meta_line = " ".join([
        _kv("DEBUG_REPORT", "1"),
        _kv("BUILD_TAG", str(data.get("build_tag", ""))),
        _kv("generated_at_kst", str(data.get("generated_at_kst", ""))),
    ])

    link_line = ""
    if json_href:
        link_line = f"<div class='dbgLinks'><a href='{esc(json_href)}' target='_blank' rel='noopener'>debug json 蹂닿린</a></div>"

    return f"""
    <style>
      details.dbgWrap {{ margin-top:24px; padding-top:16px; border-top:1px dashed var(--line); }}
      details.dbgWrap summary {{ cursor:pointer; font-weight:700; }}
      .dbgMeta {{ margin:10px 0 8px; display:flex; flex-wrap:wrap; gap:8px; }}
      .dbgkv {{ background:#f8fafc; border:1px solid var(--line); padding:6px 8px; border-radius:10px; font-size:12px; }}
      .dbgLinks a {{ font-size:12px; color:var(--btn); }}
      .dbgSec {{ margin-top:16px; }}
      .dbgSecHead {{ display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
      .dbgTableWrap {{ overflow:auto; border:1px solid var(--line); border-radius:12px; margin-top:8px; }}
      table.dbgTable {{ width:100%; border-collapse:collapse; font-size:12px; min-width:980px; }}
      table.dbgTable th, table.dbgTable td {{ border-bottom:1px solid var(--line); padding:6px 8px; vertical-align:top; }}
      table.dbgTable th {{ position:sticky; top:0; background:#f9fafb; z-index:1; }}
      .dbgTable .c {{ text-align:center; white-space:nowrap; }}
      .dbgTable .r {{ text-align:right; white-space:nowrap; }}
      .muted {{ color:var(--muted); }}
    </style>
    <details class="dbgWrap">
      <summary>?붾쾭洹?由ы룷??(?좎젙/?꾪꽣 濡쒓렇)</summary>
      {link_line}
      <div class="dbgMeta">{meta_line}</div>
      <div class="muted" style="font-size:12px;">?꾪꽣留??쒖쇅 ?ъ쑀 ?곸쐞: {esc(reason_line)}</div>
      {''.join(sec_blocks)}
      <div class="dbgSec">
        <div class="dbgSecHead"><b>?꾪꽣留??쒖쇅(?섑뵆)</b><span class="muted">理쒕? 60嫄??쒖떆</span></div>
        <div class="dbgTableWrap">
          <table class="dbgTable">
            <thead><tr><th class="c">?뱀뀡</th><th>?ъ쑀</th><th>留ㅼ껜</th><th>?꾨찓??/th><th>?쒕ぉ</th></tr></thead>
            <tbody>{rej_html}</tbody>
          </table>
        </div>
      </div>
    </details>
    """


def make_section_insight(section_key: str, arts: list[Article]) -> tuple[str, list[str]]:
    """?뱀뀡 ?곷떒???몄텧??'??以??몄궗?댄듃'? ?쒓렇.
    LLM ?붿빟???놁뼱???쇨??섍쾶 ?숈옉?섎룄濡??대━?ㅽ떛 湲곕컲.
    """
    if not arts:
        return ("", [])
    txt = " ".join([(a.title or "") + " " + (a.description or "") for a in arts]).lower()

    tags: list[str] = []
    line = ""

    def add_tag(t: str):
        if t and t not in tags and len(tags) < 6:
            tags.append(t)

    if section_key == "pest":
        if "怨쇱닔?붿긽蹂? in txt:
            line = "怨쇱닔?붿긽蹂?由ъ뒪??????댁뒋媛 ?듭떖?낅땲??"
            add_tag("怨쇱닔?붿긽蹂?)
        elif "?꾩?蹂? in txt:
            line = "?꾩?蹂???二쇱슂 蹂묓빐 ????뺣낫媛 以묒떖?낅땲??"
            add_tag("?꾩?蹂?)
        elif any(w in txt for w in ("?됲빐","?숉빐","?쒕━","???)):
            line = "??㉱룸깋/?숉빐 ?쇳빐 諛??鍮??뺣낫媛 以묒슂?⑸땲??"
            add_tag("???숉빐")
        else:
            line = "蹂묓빐異??덉같/諛⑹젣 ?숉뼢???먭??섏꽭??"
            add_tag("蹂묓빐異?)
        # 二쇱슂 ?덈ぉ ?쒓렇
        for c in ("?ш낵","諛?,"媛먭랠","?щ룄","?멸린","怨좎텛","?ㅼ씠","?좊쭏??,"?뚰봽由ъ뭅"):
            if c in txt:
                add_tag(c)
    elif section_key == "supply":
        # 媛寃??섍툒 諛⑺뼢??
        if any(w in txt for w in ("?곸듅","媛뺤꽭","?ㅻ쫫","湲됰벑")):
            line = "媛寃??곸듅(媛뺤꽭) ?좏샇媛 ?ъ갑?⑸땲??"
            add_tag("媛寃⒱넁")
        elif any(w in txt for w in ("?섎씫","?쎌꽭","?대┝","湲됰씫")):
            line = "媛寃??섎씫(?쎌꽭) ?좏샇媛 ?ъ갑?⑸땲??"
            add_tag("媛寃⒱넃")
        else:
            line = "?섍툒/?묓솴/異쒗븯 蹂?섎? 以묒떖?쇰줈 ?뺤씤?섏꽭??"
            add_tag("?섍툒")
        for c in ("?ш낵","諛?,"媛먭랠","?щ룄","?멸린","怨좎텛","?ㅼ씠","?④컧","怨띔컧","?ㅼ씤癒몄뒪罹?,"留뚭컧"):
            if c in txt:
                add_tag(c)
    elif section_key == "dist":
        line = "?꾨ℓ?쒖옣쨌怨듯뙋?Β룹쑀?듯쁽???댁뒋瑜??먭??섏꽭??"
        for t in ("媛?쎌떆??,"?꾨ℓ?쒖옣","怨듯뙋??,"寃쎈씫","諛섏엯","?⑤씪?몃룄留ㅼ떆??,"?먯궛吏","寃??,"?듦?"):
            if t.lower() in txt:
                add_tag(t)
    elif section_key == "policy":
        line = "?梨?吏??寃???⑥냽 ???뺤콉 蹂???щ?瑜??뺤씤?섏꽭??"
        for t in ("吏??,"?좎씤吏??,"?좊떦愿??,"寃??,"?듦?","?⑥냽","怨좎떆","媛쒖젙","釉뚮━??):
            if t.lower() in txt:
                add_tag(t)
    else:
        line = ""
    return (line, tags)

def render_daily_page(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict,
                      archive_dates_desc: list[str], site_path: str) -> str:
    # ?곷떒 移?移댁슫??+ ?뱀뀡蹂?以묒슂???뺣젹
    chips = []
    total = 0
    for sec in SECTIONS:
        lst = sorted(by_section.get(sec["key"], []), key=lambda a: ((1 if getattr(a, "is_core", False) else 0),) + _sort_key_major_first(a), reverse=True)
        by_section[sec["key"]] = lst
        n = len(lst)
        total += n
        chips.append((sec["key"], sec["title"], n, sec["color"]))

    # prev/next: 寃利앸맂 ?좎쭨 由ъ뒪??湲곗? (?놁쓣 ?뚮뒗 '?뚮┝ 踰꾪듉'?쇰줈 404 諛⑹?)
    prev_href = None
    next_href = None
    if report_date in archive_dates_desc:
        idx = archive_dates_desc.index(report_date)
        # prev(??怨쇨굅) = idx+1
        if idx + 1 < len(archive_dates_desc):
            prev_href = build_site_url(site_path, f"archive/{archive_dates_desc[idx+1]}.html")
        # next(??理쒖떊) = idx-1
        if idx - 1 >= 0:
            next_href = build_site_url(site_path, f"archive/{archive_dates_desc[idx-1]}.html")

    # ?좎쭨 select (value???덈?寃쎈줈)
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

    def chip_html(k, title, n, color):
        return (
            f'<a class="chip" style="border-color:{color};" href="#sec-{k}">'
            f'<span class="chipTitle">{esc(display_section_title(title))}</span><span class="chipN">{n}</span></a>'
        )

    chips_html = "\n".join([chip_html(*c) for c in chips])

    # ??(2) ?뱀뀡 ?뚮뜑: ???댁긽 ?④?(<details>) ?ъ슜?섏? ?딄퀬 '?꾨?' ?몄텧
    # ??(2) ?뱀뀡 ??湲곗궗??以묒슂?????대? ?뺣젹??
    sections_html = []
    for sec in SECTIONS:
        key = sec["key"]
        title = sec["title"]
        color = sec["color"]
        lst = by_section.get(key, [])
        insight_line, insight_tags = make_section_insight(key, lst)

        def render_card(a: Article, is_core: bool):
            url = a.originallink or a.link
            summary_html = "<br>".join(esc(a.summary).splitlines())
            core_badge = '<span class="badgeCore">?듭떖</span>' if is_core else ""
            return f"""
            <div class=\"card\" style=\"border-left-color:{color}\">
              <div class=\"cardTop\">
                <div class=\"meta\">
                  {core_badge}
                  <span class=\"press\">{esc(a.press)}</span>
                  <span class=\"dot\">쨌</span>
                  <span class=\"time\">{esc(fmt_dt(a.pub_dt_kst))}</span>
                  <span class=\"dot\">쨌</span>
                  <span class=\"topic\">{esc(a.topic)}</span>
                </div>
                <a class=\"btnOpen\" href=\"{esc(url)}\" target=\"_blank\" rel=\"noopener\">?먮Ц ?닿린</a>
              </div>
              <div class=\"ttl\">{esc(a.title)}</div>
              <div class=\"sum\">{summary_html}</div>
            </div>
            """

        if not lst:
            body_html = '<div class="empty">?대떦?ы빆 ?놁쓬</div>'
        else:
            body_html = "\n".join([render_card(a, getattr(a, "is_core", False)) for a in lst])

        sections_html.append(
            f"""
            <section id=\"sec-{key}\" class=\"sec\">
              <div class=\"secHead\" style=\"border-left:8px solid {color};\">
                <div class=\"secTitle\">
                  <span class=\"dotColor\" style=\"background:{color}\"></span>
                  {esc(title)}
                </div>
                <div class=\"secCount\">{len(lst)}嫄?/div>
              </div>
              <div class=\"secBody\">{body_html}</div>
            </section>
            """
        )

    sections_html = "\n".join(sections_html)

    page_title = f"[{report_date} ?띿궛臾??댁뒪 Brief]"
    period = f"{start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}"
    home_href = site_path

    def nav_btn(href: str | None, label: str, empty_msg: str, nav_key: str):
        if href:
            return f'<a class="navBtn" data-nav="{esc(nav_key)}" href="{esc(href)}">{esc(label)}</a>'
        # ??(3) ?녿뒗 ?섏씠吏濡?留곹겕?섏? ?딄퀬 ?뚮┝?쇰줈 泥섎━
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
    }}
    *{{box-sizing:border-box}}
    html {{
      /* ???듭빱 ?대룞 ?꾩튂 蹂댁젙 */
      scroll-behavior:smooth;
      scroll-padding-top: 150px;
    }}
    body{{margin:0;background:var(--bg); color:var(--text);
         font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, \"Noto Sans KR\", Arial;}}
    .wrap{{max-width:1100px !important;margin:0 auto !important;padding:12px 14px 80px !important;touch-action:pan-y;overscroll-behavior-x:contain;}}
    .topbar{{position:sticky;top:0;background:rgba(255,255,255,0.94);backdrop-filter:saturate(180%) blur(10px);
            border-bottom:1px solid var(--line); z-index:10;}}
    .topin{{max-width:1100px;margin:0 auto;padding:12px 14px;display:grid;grid-template-columns:1fr;gap:10px;align-items:start}}
    h1{{margin:0;font-size:18px;letter-spacing:-0.2px}}
    .sub{{color:var(--muted);font-size:12.5px;margin-top:4px}}
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

    /* sticky chip bar */
    .chipbar{{border-top:1px solid var(--line);}}
    .chipwrap{{max-width:1100px;margin:0 auto;padding:8px 14px;}}
    .chips{{display:flex;gap:8px;flex-wrap:nowrap;overflow-x:auto; -webkit-overflow-scrolling:touch;}}
    .chips::-webkit-scrollbar{{height:8px}}
    .chip{{text-decoration:none;border:1px solid var(--line);padding:7px 10px;border-radius:999px;
          background:var(--chip);font-size:13px;color:#111827;display:inline-flex;gap:8px;align-items:center;min-width:0}}
    .chip:hover{{border-color:#cbd5e1}}
    .chipTitle{{font-weight:800;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
    .chipN{{min-width:28px;text-align:center;background:#111827;color:#fff;padding:2px 8px;border-radius:999px;font-size:12px}}

    .sec{{margin-top:14px !important;border:1px solid var(--line);border-radius:14px !important;overflow:hidden;background:var(--card);
          scroll-margin-top: 150px;
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
    @media (max-width: 840px){{
      .topbar{{background:rgba(255,255,255,0.98);backdrop-filter:none}}
      html{{scroll-padding-top: 170px;}}
      .sec{{scroll-margin-top: 170px;}}
    }}
    @media (max-width: 640px){{
      .topin{{gap:8px}}
      .navRow{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px}}
      .navRow > .navBtn:first-child{{grid-column:1}}
      .navRow > .navBtn:nth-child(2){{grid-column:2}}
      .navRow > .dateSelWrap{{grid-column:1; width:100%}}
      .navRow > .navBtn:last-child{{grid-column:2}}
      .dateSelWrap{{width:100%}}
      .dateSelWrap select{{width:100%;max-width:none}}
      /* mobile chips: 2 columns so counts are always visible */
      .chips{{display:grid;grid-template-columns:1fr 1fr;gap:10px;overflow:visible}}
      .chip{{width:100%;justify-content:space-between}}
      .chip{{padding:6px 10px;font-size:12.5px}}
      .chipN{{min-width:24px;padding:0 8px;background:#111827;color:#fff}}
    }}
  </style>
</head>
<body>
  <div class=\"topbar\">
    <div class=\"topin\">
      <div>
        <h1>{esc(page_title)}</h1>
        <div class=\"sub\">湲곌컙: {esc(period)} 쨌 湲곗궗 {total}嫄?/div>
      </div>
      <div class=\"navRow\">
        <a class=\"navBtn navArchive\" data-nav=\"archive\" href=\"{esc(home_href)}\" title=\"?좎쭨蹂??꾩뭅?대툕 紐⑸줉\">?꾩뭅?대툕</a>
        {nav_btn(prev_href, "? ?댁쟾", "?댁쟾 釉뚮━?묒씠 ?놁뒿?덈떎.", "prev")}
        <div class=\"dateSelWrap\">
          <select id=\"dateSelect\" aria-label=\"?좎쭨 ?좏깮\">
            {options_html}
          </select>
        </div>
        {nav_btn(next_href, "?ㅼ쓬 ??, "?ㅼ쓬 釉뚮━?묒씠 ?놁뒿?덈떎.", "next")}
      </div>
      <div id=\"swipeHint\" class=\"swipeHint\" aria-hidden=\"true\">
        <span class=\"arrow\">?</span>
        <span class=\"txt pill\">醫뚯슦 ?ㅼ??댄봽濡??좎쭨 ?대룞</span>
        <span class=\"arrow\">??/span>
      </div>
      <div id=\"navLoading\" class=\"navLoading\" aria-live=\"polite\" aria-atomic=\"true\">
        <span class=\"badge\">?좎쭨 ?대룞 以묅?/span>
      </div>
    </div>

    <div class=\"chipbar\">
      <div class=\"chipwrap\">
        <div class=\"chips\" data-swipe-ignore=\"1\">{chips_html}</div>
      </div>
    </div>
  </div>

  <div class=\"wrap\">
    {sections_html}
    <div class=\"footer\">* ?먮룞 ?섏쭛 寃곌낵?낅땲?? ?듭떖 ?뺤씤? ?쒖썝臾??닿린?앸줈 ?먮Ц???뺤씤?섏꽭??</div>
  </div>

  <script>
    (function() {{
      var sel = document.getElementById("dateSelect");
      if (sel) {{
        sel.setAttribute("data-swipe-ignore", "1");
        sel.addEventListener("change", function() {{
          var v = sel.value;
          if (v) {{
            var ld = document.getElementById("navLoading");
            if (ld) ld.classList.add("show");
            gotoUrlChecked(v, "?대떦 ?좎쭨??釉뚮━?묒씠 ?놁뒿?덈떎.");
          }}
        }});
      }}

      // ??(3) prev/next媛 ?놁쓣 ??404濡??대룞?섏? ?딅룄濡??뚮┝ 泥섎━
      var btns = document.querySelectorAll("button.navBtn[data-msg]");
      btns.forEach(function(b) {{
        b.setAttribute("data-swipe-ignore", "1");
        b.addEventListener("click", function() {{
          var msg = b.getAttribute("data-msg") || "?대룞???섏씠吏媛 ?놁뒿?덈떎.";
          alert(msg);
        }});
      }});

      // ??(4) 紐⑤컮??醫????ㅼ??댄봽濡??댁쟾/?ㅼ쓬 ?좎쭨 ?대룞 (湲곗궗 ?곸뿭 ?곗꽑 / topbar ?쒖뒪泥?李⑤떒)
      var navRow = document.querySelector(".navRow");
      var prevNav = navRow ? navRow.querySelector('[data-nav="prev"]') : null;
      var nextNav = navRow ? navRow.querySelector('[data-nav="next"]') : null;
      // fallback: old pages without data-nav
      if (navRow) {{
        if (!prevNav) {{
          Array.prototype.forEach.call(navRow.querySelectorAll(".navBtn,button.navBtn"), function(el) {{
            if (!prevNav && (el.textContent||"").indexOf("?댁쟾")>=0) prevNav = el;
          }});
        }}
        if (!nextNav) {{
          Array.prototype.forEach.call(navRow.querySelectorAll(".navBtn,button.navBtn"), function(el) {{
            if (!nextNav && (el.textContent||"").indexOf("?ㅼ쓬")>=0) nextNav = el;
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
      _bindNavClick(prevNav, +1, "?댁쟾 釉뚮━?묒씠 ?놁뒿?덈떎.");
      _bindNavClick(nextNav, -1, "?ㅼ쓬 釉뚮━?묒씠 ?놁뒿?덈떎.");

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
        var msg = fallbackMsg || "?대룞???섏씠吏媛 ?놁뒿?덈떎.";
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
        // ?곷떒(topbar: ?꾩뭅?대툕/?댁쟾/?좎쭨/?ㅼ쓬/?뱀뀡移??먯꽌???쒖뒪泥섎뒗 ?섏씠吏 ?ㅼ??댄봽 湲덉?
        if (target.closest(".topbar")) return true;
        if (target.closest("select,input,textarea,button,[contenteditable=\\"true\\"]")) return true;
        return false;
      }}

      function navigateBy(el) {{
        if (!el || isNavigating) return;
        if (el.tagName && el.tagName.toLowerCase() === "a") {{
          var href = el.getAttribute("href");
          if (href) {{
            isNavigating = true;
            showNavLoading();
            window.location.href = href;
            return;
          }}
        }}
        try {{
          el.click();
        }} catch (e) {{}}
      }}



// ??404 諛⑹?: ?ㅼ젣 議댁옱?섎뒗 ?꾩뭅?대툕 紐⑸줉?쇰줈 ?쒕∼?ㅼ슫/?댁쟾/?ㅼ쓬/?ㅼ??댄봽瑜??ъ젙?ы븳??
var __manifestDates = null;
var __rootPrefix = null;

function _getRootPrefix() {{
  if (__rootPrefix) return __rootPrefix;
  try {{
    var href = String(window.location.href || "");
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
  return _getRootPrefix() + "archive/" + d + ".html";
}}

function _extractDate(s) {{
  if (!s) return "";
  var str = String(s);
  var m = str.match(/(\d{{4}}-\d{{2}}-\d{{2}})\.html/);
  if (m && m[1]) return m[1];
  if (/^\d{{4}}-\d{{2}}-\d{{2}}$/.test(str)) return str;
  return "";
}}

function _currentDateIso() {{
  return _extractDate(window.location.pathname) || _extractDate(window.location.href);
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
    var url = _getRootPrefix() + "archive_manifest.json";
    var r = await fetch(url, {{ cache: "no-store" }});
    if (!r || !r.ok) return null;
    var obj = await r.json();
    var dates = (obj && obj.dates) ? obj.dates : null;
    if (!dates || !Array.isArray(dates)) return null;
    var clean = [];
    for (var i = 0; i < dates.length; i++) {{
      var d = dates[i];
      if (typeof d === "string" && /^\d{{4}}-\d{{2}}-\d{{2}}$/.test(d)) clean.push(d);
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
    showNoBrief(null, msg || "?대떦 ?좎쭨??釉뚮━?묒씠 ?놁뒿?덈떎.");
    return;
  }}

  var ok = await _urlExists(url);
  if (ok) {{
    isNavigating = true;
    showNavLoading();
    window.location.href = url;
    return;
  }}
  showNoBrief(null, msg || "?대떦 ?좎쭨??釉뚮━?묒씠 ?놁뒿?덈떎.");
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
  if (!dates || !dates.length) {{ showNoBrief(null, msg || "?대룞??釉뚮━?묒씠 ?놁뒿?덈떎."); return; }}
  var cur = _currentDateIso();
  var idx = dates.indexOf(cur);
  if (idx < 0) idx = 0;
  var step = (delta >= 0) ? 1 : -1;
  var j = idx + delta;
  while (j >= 0 && j < dates.length) {{
    var d = dates[j];
    var url = _dateToUrl(d);
    // Always verify existence (manifest can be stale; Pages deploy can lag)
    var ok = await _urlExists(url);
    if (ok) {{
      if (isNavigating) return;
      isNavigating = true;
      showNavLoading();
      window.location.href = url;
      return;
    }}
    j += step;
  }}
  showNoBrief(null, msg || (delta > 0 ? "?댁쟾 釉뚮━?묒씠 ?놁뒿?덈떎." : "?ㅼ쓬 釉뚮━?묒씠 ?놁뒿?덈떎."));
}}

// non-blocking: try to load manifest & prune date list
try {{ _ensureDates(); }} catch (e) {{}}

      function resetNavRowFeedback() {{
        if (!navRow) return;
        navRow.style.transform = "";
        navRow.style.opacity = "";
      }}

      var sx = 0, sy = 0, st = 0, blocked = false;
      var swipeArea = document.querySelector(".wrap") || document.documentElement || document.body || document;

      swipeArea.addEventListener("touchstart", function(e) {{
        if (!e.touches || e.touches.length !== 1) return;
        blocked = isBlockedTarget(e.target);
        var t = e.touches[0];
        sx = t.clientX;
        sy = t.clientY;
        st = Date.now();
      }}, {{ passive: true }});

      swipeArea.addEventListener("touchend", function(e) {{
        if (!e.changedTouches || e.changedTouches.length !== 1) return;
        if (blocked || isBlockedTarget(e.target)) return;
        var t = e.changedTouches[0];
        var dx = t.clientX - sx;
        var dy = t.clientY - sy;
        var dt = Date.now() - st;

        // accidental 諛⑹?: ??媛뺥븳 ?꾧퀎移?
        if (dt > 900 || Math.abs(dx) < 90 || Math.abs(dx) < Math.abs(dy) * 1.4) return;

        // ?ㅼ??댄봽 ?숈옉: ?쇱そ(?? dx<0)=?ㅼ쓬(?좉퇋) / ?ㅻⅨ履??? dx>0)=?댁쟾(怨쇨굅)
        if (dx < 0) {{
          gotoByOffset(-1, "?ㅼ쓬 釉뚮━?묒씠 ?놁뒿?덈떎.");
        }} else {{
          gotoByOffset(+1, "?댁쟾 釉뚮━?묒씠 ?놁뒿?덈떎.");
        }}
      }}, {{ passive: true }});

      document.addEventListener("keydown", function(e) {{
        if (!e) return;
        if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
        if (isBlockedTarget(e.target)) return;
        if (e.key === "ArrowLeft") {{
          if (hasHref(prevNav)) {{
            showNavLoading();
            navigateBy(prevNav);
          }} else {{
            showNoBrief(prevNav, "?댁쟾 釉뚮━?묒씠 ?놁뒿?덈떎.");
          }}
        }} else if (e.key === "ArrowRight") {{
          if (hasHref(nextNav)) {{
            showNavLoading();
            navigateBy(nextNav);
          }} else {{
            showNoBrief(nextNav, "?ㅼ쓬 釉뚮━?묒씠 ?놁뒿?덈떎.");
          }}
        }}
      }});

      window.addEventListener("pageshow", function() {{
        isNavigating = false;
        hideNavLoading();
        resetNavRowFeedback();
      }});

      // ?뚰듃??1踰덈쭔 ?좉퉸 ?몄텧(媛?낆꽦 ?좎?)
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


def render_index_page(manifest: dict, site_path: str) -> str:
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
            return f"{d.year}??{d.month}??{d.day}??
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
            <div class="meta">{esc(d)} 쨌 {esc(wd)}?붿씪</div>
          </a>
        """)

    cards_html = "\n".join(cards) if cards else '<div class="empty">?꾩뭅?대툕媛 ?꾩쭅 ?놁뒿?덈떎.</div>'

    latest_btn_html = (
        f'<a class="btn" href="{esc(latest_link)}">理쒖떊 釉뚮━???닿린</a>'
        if latest_link
        else '<button class="btn disabled" type="button" data-msg="理쒖떊 釉뚮━?묒씠 ?꾩쭅 ?놁뒿?덈떎.">理쒖떊 釉뚮━???닿린</button>'
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
  <title>?띿궛臾??댁뒪 釉뚮━??/title>
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
    <h1>?띿궛臾??댁뒪 釉뚮━??/h1>
    <div class="sub">理쒖떊 釉뚮━?묎낵 ?좎쭨蹂??꾩뭅?대툕瑜??쒓났?⑸땲?? (?ㅼ썙??寃??쨌 湲곌컙/?뱀뀡 ?꾪꽣 쨌 ?뺣젹 吏??</div>

    {latest_btn_html}

    <div class="panel">
      <div class="panelTitle">
        <span>?ㅼ썙??寃??/span>
        <span style="color:var(--muted);font-size:12px;font-weight:700">* 2湲???댁긽遺??寃곌낵 ?쒖떆</span>
      </div>

      <div class="searchRow">
        <input id="q" class="searchInput" type="search" placeholder="?? ?ш낵 媛寃? ?ㅼ씤癒몄뒪罹??섍툒, 蹂묓빐異?諛⑹젣" />
        <button id="clearBtn" class="btn" style="margin-top:0;padding:10px 12px;" type="button">珥덇린??/button>
      </div>

      <div class="filters">
        <select id="secSel" class="sel" title="?뱀뀡">
          <option value="">?꾩껜 ?뱀뀡</option>
        </select>

        <select id="sortSel" class="sel" title="?뺣젹">
          <option value="relevance">愿?⑤룄??/option>
          <option value="date">理쒖떊??/option>
          <option value="press">留ㅼ껜 以묒슂?꾩닚</option>
          <option value="score">?좎젙 ?먯닔??/option>
        </select>

        <span class="chip"><b>湲곌컙</b></span>
        <input id="fromDate" class="date" type="date" />
        <span style="color:var(--muted);font-size:12px;">~</span>
        <input id="toDate" class="date" type="date" />

        <button id="quick7" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">7??/button>
        <button id="quick30" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">30??/button>
        <button id="quick90" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">90??/button>
        <button id="quickAll" class="btn ghost" style="margin-top:0;padding:8px 10px;" type="button">?꾩껜</button>

        <label class="chip" style="cursor:pointer">
          <input id="groupToggle" type="checkbox" style="margin:0" />
          ?좎쭨蹂?洹몃９
        </label>
      </div>

      <div class="hint">寃????? ?쒕ぉ/?붿빟/?몃줎???뱀뀡/?좎쭨.  (?? "?ш낵 媛寃? 泥섎읆 ?꾩뼱?곌린瑜??섎㈃ 紐⑤뱺 ?⑥뼱媛 ?ы븿??湲곗궗留??쒖떆?⑸땲??)</div>

      <div class="metaLine">
        <div id="metaLeft" class="metaLeft"></div>
        <div id="metaRight" style="color:var(--muted)"></div>
      </div>

      <div id="results" class="results"></div>
      <div id="pager" class="pager" style="display:none"></div>
    </div>

    <div class="panel">
      <div class="panelTitle">?좎쭨蹂??꾩뭅?대툕</div>
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
          alert(b.getAttribute("data-msg") || "?대룞???섏씠吏媛 ?놁뒿?덈떎.");
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
        metaLeft.innerHTML += "<span class='chip'><b>寃??/b> " + escHtml(q) + "</span>";
        var secV = secSel.value || "";
        if (secV) metaLeft.innerHTML += "<span class='chip'><b>?뱀뀡</b> " + escHtml(secSel.options[secSel.selectedIndex].text) + "</span>";
        var fr = fromDate.value || "";
        var to = toDate.value || "";
        if (fr || to) metaLeft.innerHTML += "<span class='chip'><b>湲곌컙</b> " + escHtml(fr||"??) + " ~ " + escHtml(to||"??) + "</span>";
        metaLeft.innerHTML += "<span class='chip'><b>?뺣젹</b> " + escHtml(sortSel.options[sortSel.selectedIndex].text) + "</span>";

        metaRight.textContent = "珥?" + resCount + "嫄?쨌 " + showCount + "嫄??쒖떆";
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
          + "<div class='pinfo'>?섏씠吏 " + PAGE + " / " + totalPages + "</div>"
          + "<button class='pbtn' id='prevBtn' " + prevDis + ">?댁쟾</button>"
          + "<button class='pbtn' id='nextBtn' " + nextDis + ">?ㅼ쓬</button>";

        var prevBtn = document.getElementById("prevBtn");
        var nextBtn = document.getElementById("nextBtn");
        if (prevBtn) prevBtn.addEventListener("click", function(){{ if (PAGE>1) {{ PAGE--; runSearch(); }} }});
        if (nextBtn) nextBtn.addEventListener("click", function(){{ if (PAGE<totalPages) {{ PAGE++; runSearch(); }} }});
      }}

      function renderList(res, tokens) {{
        var start = (PAGE - 1) * PAGE_SIZE;
        var slice = res.slice(start, start + PAGE_SIZE);

        if (slice.length === 0) {{
          box.innerHTML = "<div class='empty'>寃??寃곌낵媛 ?놁뒿?덈떎.</div>";
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
          var tierLabel = tier>=4 ? "怨듭떇" : (tier>=3 ? "二쇱슂" : (tier>=2 ? "吏???꾨Ц" : "湲고?"));
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
               +    (aHref ? "<a href='" + aHref + "'>釉뚮━??蹂닿린</a>" : "")
               +    (uHref ? "<a href='" + uHref + "' target='_blank' rel='noopener'>?먮Ц ?닿린</a>" : "")
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
          box.innerHTML = "<div class='empty'>寃??寃곌낵媛 ?놁뒿?덈떎.</div>";
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
            var tierLabel = tier>=4 ? "怨듭떇" : (tier>=3 ? "二쇱슂" : (tier>=2 ? "吏???꾨Ц" : "湲고?"));

            html += "<div class='result'>"
                 +  "<div class='rTop'>"
                 +    "<span class='chip'>" + sec + "</span>"
                 +    (press ? "<span class='chip'>" + press + "</span>" : "")
                 +    "<span class='chip'><b>" + tierLabel + "</b></span>"
                 +  "</div>"
                 +  "<div class='rTitle'>" + title + "</div>"
                 +  (sum ? "<div class='rSum'>" + sum + "</div>" : "")
                 +  "<div class='rLinks'>"
                 +    (aHref ? "<a href='" + aHref + "'>釉뚮━??蹂닿린</a>" : "")
                 +    (uHref ? "<a href='" + uHref + "' target='_blank' rel='noopener'>?먮Ц ?닿린</a>" : "")
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
          metaLeft.innerHTML = "<span class='chip'><b>?덈궡</b> 寃???몃뜳?ㅻ? 遺덈윭?ㅻ뒗 以묒엯?덈떎...</span>";
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
        metaLeft.innerHTML = "<span class='chip'><b>?덈궡</b> 寃???몃뜳?ㅻ? 遺덈윭?ㅻ뒗 以?..</span>";
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

          metaLeft.innerHTML = "<span class='chip'><b>以鍮??꾨즺</b> ?ㅼ썙?쒕? ?낅젰?섏꽭??/span>";
          metaRight.textContent = "?몃뜳??" + items.length + "嫄?;
        }} catch(e) {{
          DATA = null;
          metaLeft.innerHTML = "<span class='chip'><b>?ㅻ쪟</b> 寃???몃뜳?ㅻ? 遺덈윭?ㅼ? 紐삵뻽?듬땲?? ?덈줈怨좎묠 ???ㅼ떆 ?쒕룄?섏꽭??</span>";
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

    # ???ъ슜??議곗쭅 ?ъ씠??owner.github.io)??repo path媛 遺숈? ?딆쓬
    if name.lower().endswith(".github.io"):
        default_url = f"https://{owner.lower()}.github.io"
    else:
        default_url = f"https://{owner.lower()}.github.io/{name}".rstrip("/")

    env_url = os.getenv("PAGES_BASE_URL", "").strip().rstrip("/")
    if not env_url:
        return default_url

    bad = ("gist.github.com", "raw.githubusercontent.com")
    if any(b in env_url for b in bad):
        log.warning("[WARN] PAGES_BASE_URL points to gist/raw. Ignoring and using default: %s", default_url)
        return default_url

    if not env_url.startswith("http://") and not env_url.startswith("https://"):
        log.warning("[WARN] PAGES_BASE_URL invalid (no http/https). Ignoring and using default: %s", default_url)
        return default_url

    return env_url

def ensure_not_gist(url: str, label: str):
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

def log_kakao_link(url: str):
    try:
        p = urlparse(url)
        log.info("[KAKAO LINK] %s (host=%s)", url, p.netloc)
    except Exception:
        log.info("[KAKAO LINK] %s", url)

# -----------------------------
# Kakao message (??1踰? 釉뚮━?묒쓽 '?듭떖2'? ?숈씪)
# -----------------------------
KAKAO_MESSAGE_SECTION_ORDER = ["supply", "policy", "dist", "pest"]

def _get_section_conf(key: str):
    for s in SECTIONS:
        if s["key"] == key:
            return s
    return None


def _kakao_pick_core2(lst: list[Article]) -> list[Article]:
    """移댄넚 硫붿떆吏?먮뒗 ?뱀뀡蹂?2瑗??留??몄텧.
    - core(?듭떖) 2媛쒓? ?덉쑝硫?洹멸쾬???곗꽑
    - core媛 ?놁쑝硫?'?듭? 梨꾩?'???쇳븯湲??꾪빐 ?쇱젙 ?먯닔 ?댁긽留??쒗븳?곸쑝濡??몄텧
    """
    if not lst:
        return []
    core = [a for a in lst if getattr(a, "is_core", False)]
    if core:
        return core[:2]

    # fallback: ?곷떒 湲곗궗 以묒뿉?쒕룄 理쒖냼 ?먯닔 湲곗????듦낵??寃껊쭔
    picked: list[Article] = []
    for a in lst:
        if a.score < 7.0:
            continue
        # supply ?뱀뀡?먯꽌???몄떇/?멸린異뺤젣(?뚮퉬 ?대깽??瑜섎? 移댄넚 '?듭떖2' ?泥??꾨낫?먯꽌 ?쒖쇅
        if (a.section or "") == "supply" and is_fruit_foodservice_event_context(((a.title or "") + " " + (a.description or "")).lower()):
            continue
        # ?덉쟾留? ?⑥뒪?명뫖??媛寃?湲곗궗???쒖쇅
        if is_fastfood_price_context(((a.title or "") + " " + (a.description or "")).lower()):
            continue
        picked.append(a)
        if len(picked) >= 2:
            break
    return picked


def build_kakao_message(report_date: str, by_section: dict[str, list["Article"]]) -> str:
    """移댁뭅?ㅽ넚 '?섏뿉寃?蹂대궡湲???1媛?硫붿떆吏 ?띿뒪???앹꽦.
    - 媛??뱀뀡蹂?'?듭떖 2媛?留??몄텧(釉뚮━???섏씠吏??core2? ?숈씪)
    - ??ぉ ?대? 以꾨컮轅덉? ?섏? ?딄퀬, ?뱀뀡 ?ъ씠留???以??꾩?(媛?낆꽦)
    """
    def _shorten(s: str, n: int = 78) -> str:
        s = (s or "").strip()
        s = re.sub(r"\s+", " ", s)
        if len(s) <= n:
            return s
        return s[: max(0, n-1)].rstrip() + "??

    order = list(KAKAO_MESSAGE_SECTION_ORDER) if isinstance(KAKAO_MESSAGE_SECTION_ORDER, list) else ["supply", "policy", "dist", "pest"]
    parts: list[str] = []
    parts.append(f"?띿궛臾??댁뒪 釉뚮━??({report_date})")

    for key in order:
        conf = _get_section_conf(key)
        sec_title = conf.get("title") if isinstance(conf, dict) else key
        parts.append(f"\n[{sec_title}]")

        lst = by_section.get(key, []) if isinstance(by_section, dict) else []
        picks = _kakao_pick_core2(lst)

        if not picks:
            parts.append("- (?대떦 ?놁쓬)")
            continue

        for i, a in enumerate(picks, start=1):
            press = (getattr(a, "press", "") or "").strip() or press_name_from_url(getattr(a, "originallink", "") or getattr(a, "link", ""))
            press = press or "誘몄긽"
            title = _shorten(getattr(a, "title", ""), 78)
            parts.append(f"{i}. ({press}) {title}")

    out = "\n".join(parts).strip()
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out


# -----------------------------
# Kakao API
# -----------------------------
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
        _log_http_error("[KAKAO TOKEN ERROR]", r)
        r.raise_for_status()
    j = r.json()
    return j["access_token"]

def kakao_send_to_me(text: str, web_url: str):
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
            "button_title": "釉뚮━???닿린",
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
            metric_inc("kakao.retry", reason="network")
            backoff = exponential_backoff(attempt, base=0.8, cap=15.0, jitter=0.4)
            log.warning("[KAKAO SEND] network error (attempt %d/%d): %s -> sleep %.1fs", attempt+1, max_try, exc, backoff)
            time.sleep(backoff)
            continue

        last_resp = r

        if r.ok:
            metric_inc("kakao.send.success")
            return r.json()

        if r.status_code in (401, 403):
            metric_inc("kakao.auth_refresh")
            _log_http_error("[KAKAO SEND AUTH ERROR]", r)
            access_token = kakao_refresh_access_token()
            continue

        if r.status_code == 429 or r.status_code in (500, 502, 503, 504):
            metric_inc("kakao.retry", reason="http", status=str(r.status_code))
            backoff = retry_after_or_backoff(r.headers, attempt, base=0.8, cap=15.0, jitter=0.4)
            log.warning("[KAKAO SEND] transient HTTP %s (attempt %d/%d) -> sleep %.1fs", r.status_code, attempt+1, max_try, backoff)
            time.sleep(backoff)
            continue

        _log_http_error("[KAKAO SEND ERROR]", r)
        r.raise_for_status()

    if last_resp is not None:
        _log_http_error("[KAKAO SEND ERROR]", last_resp)
        last_resp.raise_for_status()
    if last_exc is not None:
        raise last_exc
    metric_inc("kakao.send.failed")
    raise RuntimeError("Kakao send failed without response")

# -----------------------------
# Window calculation
# -----------------------------
def _parse_force_report_date(s: str):
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



def compute_end_kst():
    """End timestamp (KST) for collection window.
    ?댁쁺 湲곕낯? ??긽 KST 07:00 而룹삤?꾩뿉 ?ㅻ깄?쒕떎.
    FORCE_END_NOW???붾쾭洹??섎룞?ъ깮??= FORCE_REPORT_DATE 議댁옱)???뚮쭔 ?덉슜?쒕떎.
    """
    # FORCE_END_NOW ?덉쟾?μ튂:
    # ?ㅼ슫?곸뿉???ㅼ닔濡?true媛 ?⑥븘 ?덉뼱???덈룄?곌? '?ㅽ뻾?쒓컖'源뚯? ?섏뼱?섏? ?딅룄濡??쒗븳.
    if FORCE_END_NOW and FORCE_REPORT_DATE:
        return now_kst()
    elif FORCE_END_NOW and (not FORCE_REPORT_DATE):
        try:
            log.warning("[WARN] FORCE_END_NOW ignored (requires FORCE_REPORT_DATE for safe use)")
        except Exception:
            pass

    # ???뱀젙 ?좎쭨 ?ъ깮?? FORCE_REPORT_DATE媛 ?덉쑝硫??대떦 ?좎쭨??cutoff(07:00 KST)濡?end_kst瑜?怨좎젙
    #    (FORCE_END_NOW=true??寃쎌슦???덉쇅: ?붾쾭洹?紐⑹쟻)
    if FORCE_REPORT_DATE and (not FORCE_END_NOW):
        try:
            d = _parse_force_report_date(FORCE_REPORT_DATE)
            return dt_kst(d, REPORT_HOUR_KST)
        except Exception as e:
            try:
                log.warning("[WARN] Invalid FORCE_REPORT_DATE=%s (%s)", FORCE_REPORT_DATE, e)
            except Exception:
                pass

    n = now_kst()
    cutoff_today = n.replace(hour=REPORT_HOUR_KST, minute=0, second=0, microsecond=0)

    # workflow_dispatch(?섎룞 ?ㅽ뻾) + ?좎쭨 誘몄엯?? 臾댁“嫄??ㅻ뒛 07:00?쇰줈 怨좎젙
    try:
        if (os.getenv("GITHUB_EVENT_NAME", "").strip().lower() == "workflow_dispatch") and (not FORCE_REPORT_DATE):
            return cutoff_today
    except Exception:
        pass

    # ?쇰컲/?ㅼ?以??ㅽ뻾: 07:00 ?댁쟾?대㈃ 吏곸쟾 07:00, ?댄썑硫??ㅻ뒛 07:00
    if n < cutoff_today:
        return cutoff_today - timedelta(days=1)
    return cutoff_today

def compute_window(repo: str, token: str, end_kst: datetime):

    # ?덉쟾?μ튂: ?댁쁺 湲곕낯? end_kst瑜???긽 07:00 cutoff 寃쎄퀎濡??좎?
    # (?? ?몃? ?몄텧/?⑥튂 濡쒖쭅 以?now()媛 ?ㅼ뼱????덈룄???ㅼ뿼 諛⑹?)
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

    # ???섎룞/?뚯뒪???ъ깮??FORCE_REPORT_DATE)?먯꽌??state(last_end)???곹뼢諛쏆? ?딅룄濡?
    #    '吏곸쟾 ?곸뾽??07:00 ~ end_kst' 踰붿쐞濡?怨좎젙?쒕떎(?댁씪/二쇰쭚 ?고쑕 諛깊븘 ?ы븿).
    if FORCE_REPORT_DATE:
        start = prev_cutoff
        if start >= end_kst:
            start = end_kst - timedelta(hours=24)
        return start, end_kst

    state = load_state(repo, token)
    last_end_iso = state.get("last_end_iso")

    start = prev_cutoff
    if last_end_iso:
        try:
            st = datetime.fromisoformat(last_end_iso)
            if st.tzinfo is None:
                st = st.replace(tzinfo=KST)
            start = min(st.astimezone(KST), prev_cutoff)
        except Exception:
            start = prev_cutoff

    if start >= end_kst:
        start = end_kst - timedelta(hours=24)

    return start, end_kst


# -----------------------------
# Main
# -----------------------------


# -----------------------------
# Backfill archive navigation (fix: older pages missing "?ㅼ쓬 ?? when new day is added)
# - GitHub Pages???뺤쟻 HTML?대?濡? 湲곗〈 ?꾩뭅?대툕 ?섏씠吏(?? 02-22)???ㅼ쓬??02-23) ?앹꽦 ?꾩뿉???먮룞?쇰줈 ?낅뜲?댄듃?섏? ?딅뒗??
# - ?닿껐: 留??ㅽ뻾留덈떎 report_date??"?몄젒" ?꾩뭅?대툕(?꾨궇/?ㅼ쓬?? 1~2媛쒕? ?쎌뼱 navRow(?댁쟾/?ㅼ쓬 踰꾪듉 + ?좎쭨 ?쒕∼?ㅼ슫)留?媛깆떊?쒕떎.
# -----------------------------

_NAVROW_OPEN_RE = re.compile(r'<div[^>]*\bclass\s*=\s*["\']navRow["\'][^>]*>', re.I)

def _find_div_block(html_text: str, open_match_start: int) -> tuple[int, int] | None:
    """Given start index of a <div ...> opening tag, find the matching </div> end index (balanced by <div>/<\div>).
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
        f'  <a class="navBtn navArchive" data-nav="archive" href="{esc(home_href)}" title="?좎쭨蹂??꾩뭅?대툕 紐⑸줉">?꾩뭅?대툕</a>\n'
        f'  {nav_btn(prev_href, "? ?댁쟾", "?댁쟾 釉뚮━?묒씠 ?놁뒿?덈떎.", "prev")}\n'
        '  <div class="dateSelWrap">\n'
        '    <select id="dateSelect" aria-label="?좎쭨 ?좏깮">\n'
        f'      {options_html}\n'
        '    </select>\n'
        '  </div>\n'
        f'  {nav_btn(next_href, "?ㅼ쓬 ??, "?ㅼ쓬 釉뚮━?묒씠 ?놁뒿?덈떎.", "next")}\n'
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
    """Patch existing archive HTML to normalize UI/UX (nav label/style, swipe, chipbar) in-place."""
    try:
        path = f"{DOCS_ARCHIVE_DIR}/{iso_date}.html"
        raw, sha = github_get_file(repo, path, token, ref="main")
        if not raw or not sha:
            metric_inc("ux.patch.skipped", reason="missing_raw_or_sha")
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
            warn=lambda msg: log.warning(msg),
        )
        if not html_new:
            metric_inc("ux.patch.skipped", reason="no_change_or_invalid")
            return False

        github_put_file(repo, path, html_new, token, f"UX patch {iso_date}", sha=sha, branch="main")
        metric_inc("ux.patch.updated")
        return True
    except Exception as e:
        metric_inc("ux.patch.failed")
        log.warning("[WARN] ux patch failed for %s: %s", iso_date, e)
        return False


def backfill_neighbor_archive_nav(repo: str, token: str, report_date: str, archive_dates_desc: list[str], site_path: str, max_neighbors: int = 2):
    """Backfill navRow for report_date's neighbors so older pages can navigate forward to newly generated pages."""
    if not repo or not token or not report_date:
        return
    if not archive_dates_desc or report_date not in archive_dates_desc:
        return

    idx = archive_dates_desc.index(report_date)
    targets: list[str] = []
    # (1) ?꾨궇/??怨쇨굅 ?섏씠吏: "?ㅼ쓬 ??媛 report_date濡??곌껐?섎룄濡??대쾲 ?댁뒋???듭떖)
    if idx + 1 < len(archive_dates_desc):
        targets.append(archive_dates_desc[idx + 1])
    # (2) ?ㅼ쓬????理쒖떊 ?섏씠吏: out-of-order ?ъ깮????prev/next媛 瑗ъ씠吏 ?딅룄濡?諛⑹뼱
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
# Backfill rebuild recent archives (理쒓렐 N???꾩뭅?대툕 ?ъ깮??
# - ?꾪꽣/?ㅼ퐫???곗뼱 媛쒖꽑???앷꼈????怨쇨굅 N???섏씠吏?먮룄 ?먮룞 諛섏쁺
# - 湲곕낯: BACKFILL_REBUILD_DAYS=0 (OFF)
# - 二쇱쓽: N???щ㈃ Naver/OpenAI ?몄텧?됱씠 而ㅼ쭏 ???덉쓬
# -----------------------------

def _compute_window_for_report_date(report_date: str) -> tuple[datetime, datetime]:
    """FORCE_REPORT_DATE 紐⑤뱶? ?숈씪??諛⑹떇?쇰줈 ?덈룄?곕? 怨꾩궛?쒕떎.
    - end: report_date 07:00(KST)
    - start: 吏곸쟾 ?곸뾽??07:00(KST) (?고쑕/二쇰쭚?대㈃ ??湲몄뼱吏????덉쓬)
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
    summary_cache: dict,
    search_idx: dict,
) -> dict:
    """理쒓렐 BACKFILL_REBUILD_DAYS 留뚰겮??怨쇨굅 ?꾩뭅?대툕瑜??ъ깮?깊븯??而ㅻ컠?쒕떎.
    - daily html (docs/archive/YYYY-MM-DD.html) ?낅뜲?댄듃
    - docs/search_index.json ?뷀듃由щ룄 ?대떦 ?좎쭨濡??ъ깮??
    - 移댁뭅???꾩넚/manifest/state??嫄대뱶由ъ? ?딅뒗???ㅻ뒛?먯뿉?쒕쭔 泥섎━)
    """
    days = int(BACKFILL_REBUILD_DAYS or 0)
    use_range = bool((BACKFILL_START_DATE or "").strip() or (BACKFILL_END_DATE or "").strip())
    if use_range:
        log.info("[BACKFILL] range mode enabled: %s ~ %s (days_arg=%s create_missing=%s)", BACKFILL_START_DATE or "", BACKFILL_END_DATE or "", days, BACKFILL_REBUILD_CREATE_MISSING)
    if days <= 0 and not use_range:
        return search_idx
    # range 紐⑤뱶?먯꽌??backfill_days=0?댁뼱??BACKFILL_START_DATE~BACKFILL_END_DATE瑜?湲곗??쇰줈 ?ъ깮?깊븳??
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

    # rebuild targets: report_date ?쒖쇅, (1) BACKFILL_START_DATE~BACKFILL_END_DATE 踰붿쐞 ?먮뒗 (2) 怨쇨굅 N??
    create_missing = bool(BACKFILL_REBUILD_CREATE_MISSING)
    # start_date 吏????湲곌컙 ?ъ깮??紐⑤뱶) ?꾨씫 ?뚯씪 ?앹꽦??湲곕낯媛믪씠 ?섎룄濡?蹂댁젙
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


    # ??Prevent 404: exclude non-business days from navigation/date list by default
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

            # ???뺤콉: 二쇰쭚/怨듯쑕?쇱? 諛깊븘?먯꽌??湲곕낯 ?ㅽ궢 (?꾩슂 ??FORCE_RUN_ANYDAY=true濡??덉슜)
            try:
                if (not FORCE_RUN_ANYDAY) and (not is_business_day_kr(date.fromisoformat(d))):
                    log.info("[BACKFILL] skip non-business day: %s", d)
                    continue
            except Exception:
                pass

            bf_by_section = collect_all_sections(start_kst, end_kst)
            _emit_section_selection_metrics(bf_by_section, stage="backfill_collection")

            # ?붿빟? 鍮꾩슜/?덉씠?몃━諛뗭씠 嫄몃┫ ???덉뼱 ?듭뀡 ?쒓났(湲곕낯: ?섑뻾). skip_openai=True?щ룄 罹먯떆濡??붿빟??梨꾩슱 ???덇쾶 allow_openai濡??쒖뼱.
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


def _maybe_ux_patch(repo: str, token: str, base_iso: str, site_path: str):
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


def maintenance_rebuild_date(repo: str, token: str, report_date: str, site_path: str, allow_openai: bool = True):
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
    _emit_section_selection_metrics(by_section, stage="maintenance_collection")
    summary_cache = load_summary_cache(repo, token)
    by_section = fill_summaries(by_section, cache=summary_cache, allow_openai=allow_openai)

    # nav dates from actual archive listing
    avail = _list_archive_dates(repo, token)
    avail.add(report_date)
    archive_dates_desc = sorted(avail, reverse=True)

    # render
    daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, archive_dates_desc, site_path)
    daily_path = f"{DOCS_ARCHIVE_DIR}/{report_date}.html"
    raw_old, sha_old = github_get_file(repo, daily_path, token, ref="main")
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
            kakao_text = build_kakao_message(report_date, by_section)
            if KAKAO_INCLUDE_LINK_IN_TEXT:
                kakao_text = kakao_text + "\n" + daily_url
            daily_url = ensure_absolute_http_url(daily_url)
            log_kakao_link(daily_url)
            kakao_send_to_me(kakao_text, daily_url)
            log.info("[OK] Kakao message sent (maintenance rebuild_date). URL=%s", daily_url)
        except Exception as e:
            if KAKAO_FAIL_OPEN:
                metric_inc("kakao.fail_open")
                log_event("kakao.fail_open", error=str(e))
                log.error("[KAKAO] send failed but continue (fail-open): %s", e)
            else:
                raise

def maintenance_backfill_rebuild(repo: str, token: str, base_date_iso: str, site_path: str):
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







def main():
    log.info("[BUILD] %s", BUILD_TAG)
    if not DEFAULT_REPO:
        raise RuntimeError("GITHUB_REPO or GITHUB_REPOSITORY is not set (e.g., ORGNAME/agri-news-brief)")
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is not set")

    maintenance_task = (os.getenv("MAINTENANCE_TASK", "") or "").strip().lower()

    repo = DEFAULT_REPO
    end_kst = compute_end_kst()

    # -----------------------------
    # Maintenance-only tasks
    # -----------------------------
    if maintenance_task == "ux_patch":
        # 怨쇨굅 ?꾩뭅?대툕 UI/UX ?⑥튂留??섑뻾?섍퀬 醫낅즺(釉뚮━???앹꽦/移댄넚 諛쒖넚 ?놁쓬)
        try:
            site_path = get_site_path(repo)
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
            d2 = (base_d - timedelta(days=i)).isoformat()
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
            site_path = get_site_path(repo)
        except Exception:
            site_path = "/"

        if maintenance_task == "rebuild_date":
            if not FORCE_REPORT_DATE:
                raise RuntimeError("FORCE_REPORT_DATE(force_report_date) is required for task=rebuild_date")
            d_iso = _parse_force_report_date(FORCE_REPORT_DATE).isoformat()
            maintenance_rebuild_date(repo, GH_TOKEN, d_iso, site_path, allow_openai=True)
            return

        # maintenance_task == "backfill_rebuild"
        base_iso = ""
        try:
            base_iso = (_parse_force_report_date(FORCE_REPORT_DATE).isoformat() if FORCE_REPORT_DATE else end_kst.date().isoformat())
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
            site_path = get_site_path(repo)
        except Exception:
            site_path = "/"
        d_iso = ""
        try:
            d_iso = _parse_force_report_date(FORCE_REPORT_DATE).isoformat()
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
    # 72h ?щ씪?대뵫 ?덈룄??+ ?щ줈?ㅻ뜲??理쒓렐 N?? 以묐났 諛⑹? 珥덇린??
    # - FORCE_REPORT_DATE(?섎룞 ?ъ깮?? / maintenance?먯꽌??以묐났 諛⑹?瑜?湲곕낯 OFF(?ы쁽???묒뾽 ?몄쓽)
    # - ?뺤긽 daily run?먯꽌留?ON (?꾩슂 ??env CROSSDAY_DEDUPE_ENABLED濡??꾧린)
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
    log.info("[INFO] Report date: %s (override=%s) -> %s", report_date, bool(REPORT_DATE_OVERRIDE or force_iso), daily_url)

    ensure_not_gist(base_url, "base_url")
    ensure_not_gist(daily_url, "daily_url")

    # site path (??4踰? 404 諛⑹? 留곹겕??
    site_path = get_site_path(repo)

    # 理쒓렐 ?꾩뭅?대툕 UI/UX ?⑥튂 (?ㅼ??댄봽/?ㅽ떚??濡쒕뵫 諛곗?)
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

    # manifest load + sanitize (manifest???좎??섎릺, UI ?좎쭨 紐⑸줉? docs/archive ?ㅼ젣 ?뚯씪??湲곗??쇰줈 留뚮뱺??
    manifest, msha = load_archive_manifest(repo, GH_TOKEN)
    manifest = _normalize_manifest(manifest)

    # ??UI ?좎쭨 紐⑸줉: docs/archive ?붾젆?곕━ listing 湲곕컲(?좎쭨 ??됲듃/?댁쟾/?ㅼ쓬 ?쇨???蹂댁옣)
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
    # (鍮꾪솢?깊솕) 湲곌컙 踰붿쐞瑜?媛뺤젣濡??쒕∼?ㅼ슫???쒖떆?섏? ?딆뒿?덈떎.
    # ?ㅼ젣濡??앹꽦??docs/archive ?뚯씪 紐⑸줉(listing)留??쒕∼?ㅼ슫/?댁쟾/?ㅼ쓬??諛섏쁺?⑸땲??
    manifest["dates"] = sorted(set(sanitize_dates(list(avail_dates))))

    # collect + summarize
    by_section = collect_all_sections(start_kst, end_kst)
    _emit_section_selection_metrics(by_section, stage="collection")
    summary_cache = load_summary_cache(repo, GH_TOKEN)
    by_section = fill_summaries(by_section, cache=summary_cache)
    try:
        save_summary_cache(repo, GH_TOKEN, summary_cache)
    except Exception as e:
        log.warning("[WARN] save_summary_cache failed: %s", e)

    # render (??2踰? ?꾩껜 ?몄텧 / 以묒슂???뺣젹)
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

    # index??404 諛⑹?瑜??꾪빐 "寃利앸맂 ?좎쭨"留??몄텧
    index_manifest = {"dates": archive_dates_desc}
    index_html = render_index_page(index_manifest, site_path)

    # update keyword search index (docs/search_index.json)
    search_idx, ssha = load_search_index(repo, GH_TOKEN)
    search_idx = update_search_index(search_idx, report_date, by_section, site_path)
    # (?듭뀡) 諛깊븘 ?ъ깮?? 怨쇨굅 ?섏씠吏/寃???몃뜳?ㅺ퉴吏 理쒖떊 濡쒖쭅?쇰줈 ?ъ깮??
    try:
        search_idx = backfill_rebuild_recent_archives(repo, GH_TOKEN, report_date, archive_dates_desc, site_path, summary_cache, search_idx)
        # ??backfill ?? ?덈줈 ?앹꽦??docs/archive ?뚯씪??湲곗??쇰줈 ?좎쭨 紐⑸줉/?댁쟾/?ㅼ쓬/?쒕∼?ㅼ슫??利됱떆 媛깆떊
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
            # listing???쇱떆?곸쑝濡?鍮꾩뼱?? 湲곌컙 ?ъ깮??紐⑤뱶?쇰㈃ 踰붿쐞 湲곕컲 紐⑸줉?쇰줈 fallback
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
            # ?ㅻ뒛 ?섏씠吏??理쒖떊 ?좎쭨紐⑸줉?쇰줈 ?ㅼ떆 ?뚮뜑(? ?댁쟾 留곹겕/?ㅼ??댄봽/?쒕∼?ㅼ슫 ?듭씪)
            daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, archive_dates_desc, site_path)
        except Exception as e2:
            log.warning("[WARN] refresh archive dates after backfill failed: %s", e2)
    except Exception as e:
        log.warning("[WARN] backfill rebuild failed: %s", e)
    # ??backfill ???붿빟 罹먯떆 ???諛깊븘?먯꽌 ?덈줈 ?앹꽦???붿빟 諛섏쁺)
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

    
    # backfill neighbor archive nav (fix: older pages missing "?ㅼ쓬 ?? after new day is generated)
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
    # - ?숈씪 report_date ?ъ떎????state/report mismatch媛 ?꾩쟻?섏? ?딅룄濡?
    #   ?대떦 ?좎쭨 湲곕줉??"理쒖쥌 by_section 寃곌낵"濡?留ㅻ쾲 ?ъ깮?깊븳??
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

    # Kakao message (?듭떖2)
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
        log.info("[OK] Kakao message sent. URL=%s", daily_url)
    except Exception as e:
        if KAKAO_FAIL_OPEN:
            metric_inc("kakao.fail_open")
            log_event("kakao.fail_open", error=str(e))
            log.error("[KAKAO] send failed but continue (fail-open): %s", e)
        else:
            raise




_legacy_main = main


def _run_legacy_entry(*, maintenance_task: str | None = None, force_report_date: str | None = None) -> None:
    old_task = os.getenv("MAINTENANCE_TASK")
    old_force = os.getenv("FORCE_REPORT_DATE")
    old_force_const = FORCE_REPORT_DATE
    try:
        if maintenance_task is None:
            if old_task is None:
                os.environ.pop("MAINTENANCE_TASK", None)
            else:
                os.environ["MAINTENANCE_TASK"] = old_task
        else:
            os.environ["MAINTENANCE_TASK"] = str(maintenance_task)

        if force_report_date is None:
            if old_force is None:
                os.environ.pop("FORCE_REPORT_DATE", None)
            else:
                os.environ["FORCE_REPORT_DATE"] = old_force
            globals()["FORCE_REPORT_DATE"] = old_force_const
        else:
            force_value = str(force_report_date).strip()
            if force_value:
                os.environ["FORCE_REPORT_DATE"] = force_value
            else:
                os.environ.pop("FORCE_REPORT_DATE", None)
            globals()["FORCE_REPORT_DATE"] = force_value

        _legacy_main()
    finally:
        if old_task is None:
            os.environ.pop("MAINTENANCE_TASK", None)
        else:
            os.environ["MAINTENANCE_TASK"] = old_task

        if old_force is None:
            os.environ.pop("FORCE_REPORT_DATE", None)
        else:
            os.environ["FORCE_REPORT_DATE"] = old_force
        globals()["FORCE_REPORT_DATE"] = old_force_const

def main():
    if not DEFAULT_REPO:
        raise RuntimeError("GITHUB_REPO or GITHUB_REPOSITORY is not set (e.g., ORGNAME/agri-news-brief)")
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is not set")

    ctx = OrchestratorContext(
        repo=DEFAULT_REPO,
        end_kst=compute_end_kst(),
        maintenance_task=(os.getenv("MAINTENANCE_TASK", "") or "").strip().lower(),
        force_report_date=(os.getenv("FORCE_REPORT_DATE", "") or "").strip(),
        force_run_anyday=bool(FORCE_RUN_ANYDAY),
        naver_ready=bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET),
        kakao_ready=bool(KAKAO_REST_API_KEY and KAKAO_REFRESH_TOKEN),
    )

    log_event("orchestrator.start", maintenance_task=ctx.maintenance_task, force_report_date=ctx.force_report_date)

    handlers = OrchestratorHandlers(
        run_ux_patch=lambda _repo, _end: _run_legacy_entry(maintenance_task="ux_patch", force_report_date=""),
        run_maintenance_rebuild=lambda _repo, _end, task: _run_legacy_entry(maintenance_task=task),
        run_force_rebuild=lambda _repo, _end: _run_legacy_entry(maintenance_task="", force_report_date=ctx.force_report_date),
        run_daily=lambda _repo, _end, _task: _run_legacy_entry(maintenance_task="", force_report_date=""),
        is_business_day=lambda end_kst: is_business_day_kr(end_kst.date()),
        on_skip_non_business=lambda end_kst: log.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date().isoformat()),
    )

    try:
        execute_orchestration(ctx, handlers)
        log_event("orchestrator.done", maintenance_task=ctx.maintenance_task)
    finally:
        flush_metrics(clear=True)


if __name__ == "__main__":
    main()




