# -*- coding: utf-8 -*-
"""
agri-news-brief main.py (production)

Features:
- Naver News API search (multi-query per section)
- Strong relevance filtering to prevent off-topic leakage
- Business-day window with KR holidays support (+ manual override)
- OpenAI summaries (batch) -> readable 2~3 lines per article
- GitHub Pages output:
  - docs/index.html (latest + archive list)
  - docs/archive/YYYY-MM-DD.html (daily snapshot)
- Kakao "나에게 보내기" one message with "브리핑 열기" button to the daily page

ENV REQUIRED:
- NAVER_CLIENT_ID
- NAVER_CLIENT_SECRET
- OPENAI_API_KEY          (optional but recommended for better summaries)
- OPENAI_MODEL            (default: gpt-5.2)
- GITHUB_REPO             (e.g., HongTaeHwa/agri-news-brief)
- GH_TOKEN or GITHUB_TOKEN (Actions built-in token OK if permissions: contents: write)
- KAKAO_REST_API_KEY
- KAKAO_REFRESH_TOKEN
OPTIONAL:
- KAKAO_CLIENT_SECRET
- PAGES_BASE_URL          (override github pages url / custom domain)
- REPORT_HOUR_KST         (default: 7)
- MAX_PER_SECTION         (default: 10)
- MIN_PER_SECTION         (default: 5)
- EXTRA_HOLIDAYS          (comma dates, e.g., 2026-02-17,2026-02-18)
- EXCLUDE_HOLIDAYS        (comma dates to treat as business day)
- KAKAO_INCLUDE_LINK_IN_TEXT (true/false, default false)
- FORCE_REPORT_DATE       (YYYY-MM-DD) for backfill tests
"""

import os
import re
import json
import base64
import html
import time
import logging
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import requests

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("agri-brief")

# -----------------------------
# Config (Easy-to-edit block)
# -----------------------------
KST = timezone(timedelta(hours=9))

REPORT_HOUR_KST = int(os.getenv("REPORT_HOUR_KST", "7"))
MAX_PER_SECTION = int(os.getenv("MAX_PER_SECTION", "10"))
MIN_PER_SECTION = int(os.getenv("MIN_PER_SECTION", "5"))

STATE_FILE_PATH = ".agri_state.json"
ARCHIVE_MANIFEST_PATH = ".agri_archive.json"

DOCS_INDEX_PATH = "docs/index.html"
DOCS_ARCHIVE_DIR = "docs/archive"

# If you use custom domain, set PAGES_BASE_URL like https://agri-brief.yourdomain.com
DEFAULT_REPO = os.getenv("GITHUB_REPO", "").strip()
GH_TOKEN = (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2").strip()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "").strip()
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "").strip()

KAKAO_INCLUDE_LINK_IN_TEXT = os.getenv("KAKAO_INCLUDE_LINK_IN_TEXT", "false").strip().lower() in ("1", "true", "yes")

FORCE_REPORT_DATE = os.getenv("FORCE_REPORT_DATE", "").strip()  # YYYY-MM-DD

EXTRA_HOLIDAYS = set([s.strip() for s in os.getenv("EXTRA_HOLIDAYS", "").split(",") if s.strip()])
EXCLUDE_HOLIDAYS = set([s.strip() for s in os.getenv("EXCLUDE_HOLIDAYS", "").split(",") if s.strip()])

# Hard blocks (low-value / lifestyle / spammy aggregators)
# Add more here if needed.
BLOCKED_DOMAINS = {
    "wikitree.co.kr",
    "theqoo.net",
    "instiz.net",
    "namu.wiki",
    "allurekorea.com",   # user reported false positive
    "vogue.co.kr",
    "marieclairekorea.com",
    "cosmopolitan.co.kr",
    "gqkorea.co.kr",
}

# Strong agriculture context keywords (raise relevance)
AGRI_STRONG_TERMS = [
    # markets / distribution
    "가락시장", "도매시장", "공판장", "경락", "경락가", "경매", "청과", "산지", "출하", "물량", "반입",
    "산지유통", "APC", "산지유통센터", "선별", "CA저장", "저장고", "저장량",
    # price/supply
    "시세", "도매가격", "소매가격", "가격", "수급", "수급동향", "작황", "생산량", "재배", "수확", "면적",
    # policy / institutions
    "농림축산식품부", "농식품부", "aT", "한국농수산식품유통공사", "농관원", "국립농산물품질관리원",
    "검역", "할당관세", "수입", "수출", "관세", "통관", "원산지", "부정유통", "온라인 도매시장",
    "비축미", "정부", "대책", "지원", "할인지원", "성수품",
    # pests
    "병해충", "방제", "약제", "살포", "예찰", "과수화상병", "탄저병", "동해", "냉해", "월동"
]

# Very common off-topic hints (penalize)
OFFTOPIC_HINTS = [
    # entertainment / celebrity
    "배우", "아이돌", "드라마", "영화", "예능", "콘서트", "팬", "유튜브", "뮤직",
    # politics / courts (often unrelated)
    "대통령", "국회", "총선", "검찰", "재판", "탄핵", "정당",
    # finance / stocks
    "코스피", "코스닥", "주가", "급등", "급락", "비트코인", "환율",
    # travel/lifestyle
    "여행", "관광", "호텔", "리조트", "레스토랑", "와인", "해변", "휴양", "파운드", "달러", "유로",
]

# Extra “travel-market” words that triggered false positives (like Allure)
TRAVEL_MARKET_HINTS = [
    "현지", "전통시장", "노점", "파운드", "로제", "타파스", "리비에라", "프랑스", "두바이",
]

# Korea-context hints (helps separate domestic agri from foreign travel markets)
KOREA_CONTEXT_HINTS = [
    "국내", "한국", "우리나라", "농협", "지자체", "군", "시", "도", "농가", "산지", "가락시장",
    "농식품부", "aT", "농관원", "대한민국", "설", "명절"
]

# Section configuration (order fixed as user requested)
SECTIONS = [
    {
        "key": "supply",
        "title": "품목 및 수급 동향",
        "color": "#0f766e",
        "queries": [
            # 구조/기후/재배지 이동
            "기후변화 사과 재배지 북상 강원도",
            "과수 재배면적 변화 사과 배",
            # 주요 과수: 사과/배 (ambiguous words handled by filter)
            "사과 도매시장 가격 시세",
            "사과 저장량 출하 수급",
            "배(과일) 도매시장 시세 신고",
            # 감/곶감
            "단감 시세 저장량",
            "떫은감 곶감 탄저병 생산량 가격",
            "둥시 곶감 물량 시세",
            # 만감류/제주
            "감귤 한라봉 레드향 천혜향 시세",
            "제주 만감류 출하 가격",
            "참다래 키위 시세",
            # 기타
            "샤인머스캣 포도 시세 출하",
            "절화 졸업 입학 시즌 가격",
            "풋고추 오이 시설채소 가격 일조량",
            "쌀 산지 가격 비축미 방출",
        ],
        # supply requires at least 1 supply-specific signal
        "must_terms": ["가격", "시세", "수급", "출하", "도매", "경락", "저장량", "작황", "생산량", "재배", "수확", "면적", "물량"],
    },
    {
        "key": "policy",
        "title": "주요 이슈 및 정책",
        "color": "#1d4ed8",
        "queries": [
            "농산물 온라인 도매시장 허위거래 전수조사",
            "농축수산물 할인지원 연장 3월",
            "할당관세 수입 과일 검역 완화",
            "성수품 가격 안정 대책 농축수산물",
            # policy briefing / government channels (to reduce false negatives)
            "대한민국 정책브리핑 농축수산물 할인 지원",
            "korea.kr 농축수산물 할인 지원",
            "농식품부 정책 농축수산물 할인 할당관세",
        ],
        "must_terms": ["정책", "대책", "지원", "할인", "할당관세", "검역", "온라인 도매시장", "비축미", "성수품", "수급"],
    },
    {
        "key": "pest",
        "title": "병해충 및 방제",
        "color": "#b45309",
        "queries": [
            "과수화상병 약제 신청 마감",
            "과수화상병 궤양 제거 골든타임",
            "월동 해충 방제 기계유유제 살포",
            "탄저병 예방 방제",
            "동해 냉해 과수 피해 대비",
        ],
        "must_terms": ["방제", "병해충", "약제", "살포", "예찰", "과수화상병", "탄저병", "냉해", "동해", "월동"],
    },
    {
        "key": "dist",
        "title": "유통 및 현장(APC/수출)",
        "color": "#6d28d9",
        "queries": [
            "APC 스마트화 AI 선별기 CA저장",
            "농협 APC 선별 저장",
            "농식품 수출 실적 배 딸기 포도",
            "가락시장 경매 재개 일정 휴무",
            "원산지 단속 농산물 부정유통",
        ],
        "must_terms": ["APC", "선별", "CA저장", "공판장", "도매시장", "가락시장", "수출", "검역", "원산지", "유통"],
    },
]

# policy/institution domains: allow slightly looser “work signals” if agri policy keywords exist
POLICY_DOMAINS = {
    "korea.kr",
    "www.korea.kr",
    "mafra.go.kr",
    "www.mafra.go.kr",
    "at.or.kr",
    "www.at.or.kr",
    "naqs.go.kr",
    "www.naqs.go.kr",
    "krei.re.kr",
    "www.krei.re.kr",
}

AGRI_POLICY_KEYWORDS = [
    "농축수산물", "농축산물", "성수품", "할인지원", "할당관세", "검역", "수급", "가격", "과일", "비축미", "원산지"
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
    # Naver returns RFC822-like date (e.g., "Mon, 17 Feb 2026 10:34:00 +0900")
    try:
        dt = parsedate_to_datetime(pubdate_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST)
    except Exception:
        return datetime.min.replace(tzinfo=KST)

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""

def strip_tracking_params(url: str) -> str:
    try:
        u = urlparse(url)
        q = [(k, v) for (k, v) in parse_qsl(u.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in ("gclid", "fbclid", "igshid", "ref")]
        new_q = urlencode(q, doseq=True)
        return urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))
    except Exception:
        return url

def norm_title_key(title: str) -> str:
    t = title.lower()
    t = re.sub(r"\[[^\]]+\]", " ", t)  # remove [..]
    t = re.sub(r"[^0-9a-z가-힣]+", "", t)
    return t[:80]

def make_norm_key(originallink: str, link: str, title: str) -> str:
    u = strip_tracking_params(originallink or link or "")
    if u:
        h = hashlib.sha1(u.encode("utf-8")).hexdigest()[:16]
        return f"url:{h}"
    return f"title:{norm_title_key(title)}"

def has_any(text: str, words) -> bool:
    return any(w in text for w in words)

def count_any(text: str, words) -> int:
    return sum(1 for w in words if w in text)


# -----------------------------
# KR business day / holidays
# -----------------------------
def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def is_korean_holiday(d: date) -> bool:
    s = d.isoformat()
    if s in EXCLUDE_HOLIDAYS:
        return False
    if s in EXTRA_HOLIDAYS:
        return True

    # Use python-holidays if available
    try:
        import holidays  # type: ignore
        kr = holidays.KR(years=[d.year], observed=True)
        return d in kr
    except Exception:
        # Fallback: weekend only (log once)
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
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "agri-news-brief-bot",
    }

def github_get_file(repo: str, path: str, token: str, ref: str = "main"):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    r = requests.get(url, headers=github_api_headers(token), params={"ref": ref}, timeout=30)
    if r.status_code == 404:
        return None, None
    if not r.ok:
        log.error("[GitHub GET ERROR] %s", r.text)
        r.raise_for_status()
    j = r.json()
    content_b64 = j.get("content", "")
    sha = j.get("sha")
    if content_b64:
        raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")
    else:
        raw = ""
    return raw, sha

def github_put_file(repo: str, path: str, content: str, token: str, message: str, sha: str = None, branch: str = "main"):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=github_api_headers(token), json=payload, timeout=30)
    if not r.ok:
        log.error("[GitHub PUT ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()


# -----------------------------
# State / archive manifest
# -----------------------------
def load_state(repo: str, token: str):
    raw, _sha = github_get_file(repo, STATE_FILE_PATH, token, ref="main")
    if not raw:
        return {"last_end_iso": None}
    try:
        return json.loads(raw)
    except Exception:
        return {"last_end_iso": None}

def save_state(repo: str, token: str, last_end: datetime):
    payload = {"last_end_iso": last_end.isoformat()}
    raw_old, sha = github_get_file(repo, STATE_FILE_PATH, token, ref="main")
    msg = f"Update state {last_end.date().isoformat()}"
    github_put_file(repo, STATE_FILE_PATH, json.dumps(payload, ensure_ascii=False, indent=2), token, msg, sha=sha, branch="main")

def load_archive_manifest(repo: str, token: str):
    raw, sha = github_get_file(repo, ARCHIVE_MANIFEST_PATH, token, ref="main")
    if not raw:
        return {"dates": []}, sha
    try:
        return json.loads(raw), sha
    except Exception:
        return {"dates": []}, sha

def save_archive_manifest(repo: str, token: str, manifest: dict, sha: str):
    msg = "Update archive manifest"
    github_put_file(repo, ARCHIVE_MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=2), token, msg, sha=sha, branch="main")


# -----------------------------
# Naver News search
# -----------------------------
def naver_news_search(query: str, display: int = 30, start: int = 1, sort: str = "date"):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set")

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort,
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if not r.ok:
        log.error("[NAVER ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()


# -----------------------------
# Relevance scoring / filtering
# -----------------------------
def is_blocked_domain(dom: str) -> bool:
    if not dom:
        return False
    dom = dom.lower()
    if dom in BLOCKED_DOMAINS:
        return True
    # also block subdomains of blocked domains
    for b in BLOCKED_DOMAINS:
        if dom.endswith("." + b):
            return True
    return False

def agri_strength_score(text: str) -> int:
    return count_any(text, AGRI_STRONG_TERMS)

def off_topic_penalty(text: str) -> int:
    return count_any(text, OFFTOPIC_HINTS)

def travel_penalty(text: str) -> int:
    return count_any(text, TRAVEL_MARKET_HINTS)

def korea_context_score(text: str) -> int:
    return count_any(text, KOREA_CONTEXT_HINTS)

def section_must_terms_ok(text: str, must_terms) -> bool:
    # must include at least one term from section's must_terms
    return has_any(text, must_terms)

def policy_domain_override(dom: str, text: str) -> bool:
    # if it's an official policy domain and has agri-policy keywords -> accept (avoid false negatives)
    if dom in POLICY_DOMAINS:
        return has_any(text, AGRI_POLICY_KEYWORDS)
    return False

def is_relevant(article: Article, section_conf: dict) -> bool:
    dom = article.domain
    if is_blocked_domain(dom):
        return False

    text = (article.title + " " + article.description).lower()

    # Section must_terms
    if not section_must_terms_ok(text, [t.lower() for t in section_conf["must_terms"]]):
        # Allow override for policy domains
        if not policy_domain_override(dom, text):
            return False

    # Core agriculture strength
    strength = agri_strength_score(text)
    offp = off_topic_penalty(text)
    trav = travel_penalty(text)
    korea = korea_context_score(text)

    # If it smells like travel/lifestyle market content, require explicit Korea context or strong agri strength
    if trav >= 1 and korea == 0 and strength < 3:
        return False

    # If off-topic hints exist, require stronger agri evidence
    if offp >= 1 and strength < 3:
        return False

    # Special disambiguation: "사과" apology pattern
    if re.search(r"(공개\s*)?사과(했다|해야|하라|문|요구|요청|발표)", article.title) and strength < 4:
        return False

    # Special disambiguation: "배" (ship) patterns
    if re.search(r"(선박|해군|항만|조선|함정|승선|항해)", text) and strength < 4:
        return False

    return True

def compute_rank_score(article: Article, section_conf: dict) -> float:
    text = (article.title + " " + article.description).lower()
    strength = agri_strength_score(text)
    korea = korea_context_score(text)
    offp = off_topic_penalty(text)
    trav = travel_penalty(text)

    score = 0.0
    score += strength * 2.0
    score += korea * 0.8
    score -= offp * 2.5
    score -= trav * 2.0

    # Prefer official policy sources a bit
    if article.domain in POLICY_DOMAINS:
        score += 3.0

    # Freshness (within the window, newer gets small boost)
    # (Not absolute time, but helps ordering)
    age_hours = max(0.0, (datetime.now(tz=KST) - article.pub_dt_kst).total_seconds() / 3600.0)
    score += max(0.0, 24.0 - min(age_hours, 24.0)) * 0.05

    # If title contains key must terms, boost
    for t in section_conf["must_terms"]:
        if t.lower() in article.title.lower():
            score += 0.6

    return score


# -----------------------------
# Collect articles for a window
# -----------------------------
def collect_articles_for_section(section_conf: dict, start_kst: datetime, end_kst: datetime):
    items = []
    seen_keys = set()

    # pull more per query to avoid “too few articles”
    display = 40

    for q in section_conf["queries"]:
        try:
            data = naver_news_search(q, display=display, start=1, sort="date")
            for it in data.get("items", []):
                title = clean_text(it.get("title", ""))
                desc = clean_text(it.get("description", ""))
                link = strip_tracking_params(it.get("link", "") or "")
                origin = strip_tracking_params(it.get("originallink", "") or link)
                pub = parse_pubdate_to_kst(it.get("pubDate", ""))

                if pub < start_kst or pub >= end_kst:
                    continue

                dom = domain_of(origin) or domain_of(link)
                if is_blocked_domain(dom):
                    continue

                press = dom
                # simple domain->press mapping (extend as you want)
                PRESS_MAP = {
                    "www.yna.co.kr": "연합뉴스",
                    "yna.co.kr": "연합뉴스",
                    "www.mk.co.kr": "매일경제",
                    "mk.co.kr": "매일경제",
                    "www.joongang.co.kr": "중앙일보",
                    "joongang.co.kr": "중앙일보",
                    "www.chosun.com": "조선일보",
                    "chosun.com": "조선일보",
                    "www.donga.com": "동아일보",
                    "donga.com": "동아일보",
                    "www.hani.co.kr": "한겨레",
                    "hani.co.kr": "한겨레",
                    "www.khan.co.kr": "경향신문",
                    "khan.co.kr": "경향신문",
                    "www.sedaily.com": "서울경제",
                    "sedaily.com": "서울경제",
                    "www.newsis.com": "뉴시스",
                    "newsis.com": "뉴시스",
                    "www.news1.kr": "뉴스1",
                    "news1.kr": "뉴스1",
                    "www.fnnews.com": "파이낸셜뉴스",
                    "fnnews.com": "파이낸셜뉴스",
                    "www.korea.kr": "정책브리핑",
                    "korea.kr": "정책브리핑",
                }
                if dom in PRESS_MAP:
                    press = PRESS_MAP[dom]

                norm_key = make_norm_key(origin, link, title)
                if norm_key in seen_keys:
                    continue

                art = Article(
                    section=section_conf["key"],
                    title=title,
                    description=desc,
                    link=link,
                    originallink=origin,
                    pub_dt_kst=pub,
                    domain=dom,
                    press=press,
                    norm_key=norm_key,
                )

                if not is_relevant(art, section_conf):
                    continue

                art.score = compute_rank_score(art, section_conf)
                seen_keys.add(norm_key)
                items.append(art)
        except Exception as e:
            log.warning("[WARN] query failed: %s (%s)", q, e)

    # Sort by score desc then pubdate desc
    items.sort(key=lambda a: (a.score, a.pub_dt_kst), reverse=True)

    # Cap
    return items[:MAX_PER_SECTION]


def collect_all_sections(start_kst: datetime, end_kst: datetime):
    by_section = {}
    for sec in SECTIONS:
        lst = collect_articles_for_section(sec, start_kst, end_kst)
        by_section[sec["key"]] = lst

    # If any section has too few, do a light “broad fill” but still filtered by relevance
    for sec in SECTIONS:
        key = sec["key"]
        if len(by_section[key]) >= MIN_PER_SECTION:
            continue

        broad_queries = []
        if key == "supply":
            broad_queries = ["농산물 가격", "과일 도매시장 시세", "청과 경락가", "산지 출하 물량"]
        elif key == "policy":
            broad_queries = ["농축수산물 할인 지원", "할당관세 과일", "농산물 물가 대책"]
        elif key == "pest":
            broad_queries = ["과수 병해충 방제 약제", "과수화상병 방제", "월동 해충 방제"]
        elif key == "dist":
            broad_queries = ["APC 선별 저장", "농식품 수출 실적", "가락시장 경매 일정"]

        # temporarily append and fetch extra
        tmp = dict(sec)
        tmp["queries"] = broad_queries

        extra = collect_articles_for_section(tmp, start_kst, end_kst)
        merged = {a.norm_key: a for a in by_section[key]}
        for a in extra:
            merged.setdefault(a.norm_key, a)

        merged_list = list(merged.values())
        merged_list.sort(key=lambda a: (a.score, a.pub_dt_kst), reverse=True)
        by_section[key] = merged_list[:MAX_PER_SECTION]

    return by_section


# -----------------------------
# OpenAI summaries (batch)
# -----------------------------
def openai_extract_text(resp_json: dict) -> str:
    # Robust extraction for Responses API
    try:
        out = resp_json.get("output", [])
        if not out:
            return ""
        # find first text chunk
        for block in out:
            for c in block.get("content", []):
                if c.get("type") == "output_text" and "text" in c:
                    return c["text"]
                if c.get("type") == "text" and "text" in c:
                    return c["text"]
        # fallback
        return json.dumps(resp_json, ensure_ascii=False)
    except Exception:
        return ""

def openai_summarize_batch(articles: list[Article]) -> dict:
    """
    Returns dict: norm_key -> summary text (2~3 lines).
    """
    if not OPENAI_API_KEY or not articles:
        return {}

    # Keep input compact
    rows = []
    for a in articles:
        rows.append({
            "id": a.norm_key,
            "press": a.press,
            "title": a.title[:180],
            "desc": a.description[:240],
            "section": a.section,
            "url": a.originallink or a.link,
        })

    system = (
        "너는 농협 경제지주 원예수급부(과수화훼) 실무자를 위한 '농산물 뉴스 요약가'다.\n"
        "- 절대 상상/추정으로 사실을 만들지 마라.\n"
        "- 각 기사 요약은 '업무적으로 쓸모 있는 팩트' 위주로 2~3문장(줄바꿈 포함 가능), 120~220자 내.\n"
        "- 가격/수급/정책/방제/유통 포인트를 한 번에 파악되게 써라.\n"
        "- 연예/정치(사과=apology) 등 비농업이면 요약하지 말고 빈칸으로 두지 말고 '제외(무관)'라고 써라.\n"
        "출력 형식(반드시): 각 줄에 'id\\t요약' 형태로만 출력."
    )

    user = "기사 목록(JSON):\n" + json.dumps(rows, ensure_ascii=False)

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if not r.ok:
            log.error("[OpenAI ERROR BODY] %s", r.text)
            r.raise_for_status()

        text = openai_extract_text(r.json()).strip()
        out = {}
        for line in text.splitlines():
            if "\t" not in line:
                continue
            k, v = line.split("\t", 1)
            k = k.strip()
            v = v.strip()
            if not k:
                continue
            out[k] = v
        return out
    except Exception as e:
        log.warning("[OpenAI] summarize failed: %s", e)
        return {}


def fill_summaries(by_section: dict):
    # Batch all for one call (cheaper, consistent)
    all_articles = []
    for sec in SECTIONS:
        all_articles.extend(by_section.get(sec["key"], []))

    mapping = openai_summarize_batch(all_articles)

    for a in all_articles:
        s = mapping.get(a.norm_key, "").strip()
        if not s:
            # fallback to description snippet
            s = a.description.strip() or a.title.strip()
        # If model says excluded, keep fallback desc (we already filtered hard, but just in case)
        if "제외(무관)" in s:
            s = a.description.strip() or a.title.strip()
        a.summary = s

    return by_section


# -----------------------------
# Rendering (HTML)
# -----------------------------
def esc(s: str) -> str:
    return html.escape(s or "")

def fmt_dt(dt_: datetime) -> str:
    return dt_.strftime("%m/%d %H:%M")

def section_conf(key: str) -> dict:
    for s in SECTIONS:
        if s["key"] == key:
            return s
    return None

def render_daily_page(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict, base_url: str) -> str:
    # summary chips
    chips = []
    total = 0
    for sec in SECTIONS:
        n = len(by_section.get(sec["key"], []))
        total += n
        chips.append((sec["key"], sec["title"], n, sec["color"]))

    def chip_html(k, title, n, color):
        return (
            f'<a class="chip" style="border-color:{color};color:{color}" href="#sec-{k}">'
            f'{esc(title)} <span class="chipN">{n}</span></a>'
        )

    chips_html = "\n".join([chip_html(*c) for c in chips])

    # sections
    sections_html = []
    for sec in SECTIONS:
        key = sec["key"]
        title = sec["title"]
        color = sec["color"]
        lst = by_section.get(key, [])
        cards = []
        for a in lst:
            url = a.originallink or a.link
            cards.append(
                f"""
                <div class="card" style="border-left-color:{color}">
                  <div class="meta">
                    <span class="press">{esc(a.press)}</span>
                    <span class="dot">·</span>
                    <span class="time">{esc(fmt_dt(a.pub_dt_kst))}</span>
                  </div>
                  <div class="ttl">{esc(a.title)}</div>
                  <div class="sum">{esc(a.summary).replace('\\n','<br>')}</div>
                  <div class="lnk"><a href="{esc(url)}" target="_blank" rel="noopener">원문 열기</a></div>
                </div>
                """
            )
        if not cards:
            cards_html = '<div class="empty">특이사항 없음</div>'
        else:
            cards_html = "\n".join(cards)

        sections_html.append(
            f"""
            <section id="sec-{key}" class="sec">
              <div class="secHead" style="background:linear-gradient(90deg,{color},#111827);">
                <div class="secTitle">{esc(title)}</div>
                <div class="secCount">{len(lst)}건</div>
              </div>
              <div class="secBody">
                {cards_html}
              </div>
            </section>
            """
        )

    sections_html = "\n".join(sections_html)

    title = f"[{report_date} 농산물 뉴스 Brief]"
    period = f"{start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}"

    # Simple archive nav
    index_url = f"{base_url}/"
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <style>
    :root {{
      --bg:#0b1220; --panel:#0f172a; --card:#0b1220;
      --text:#e5e7eb; --muted:#94a3b8; --line:#1f2937;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;background:radial-gradient(1200px 600px at 20% 10%, #111827, var(--bg)); color:var(--text);
         font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Noto Sans KR", Arial;}}
    .wrap{{max-width:1100px;margin:0 auto;padding:22px 16px 80px;}}
    .topbar{{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}}
    h1{{margin:0;font-size:20px;letter-spacing:-0.2px}}
    .sub{{color:var(--muted);font-size:13px;margin-top:6px}}
    .nav a{{color:#cbd5e1;text-decoration:none;font-size:13px;border:1px solid var(--line);padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.02)}}
    .chips{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}
    .chip{{text-decoration:none;border:1px solid var(--line);padding:8px 10px;border-radius:999px;
          background:rgba(255,255,255,0.02);font-size:13px}}
    .chipN{{margin-left:6px;background:rgba(255,255,255,0.08);padding:2px 8px;border-radius:999px;color:var(--text)}}
    .sec{{margin-top:18px;border:1px solid var(--line);border-radius:16px;overflow:hidden;background:rgba(255,255,255,0.02)}}
    .secHead{{display:flex;align-items:center;justify-content:space-between;padding:12px 14px}}
    .secTitle{{font-size:15px;font-weight:700}}
    .secCount{{font-size:13px;color:#e2e8f0;background:rgba(0,0,0,0.25);padding:4px 10px;border-radius:999px}}
    .secBody{{padding:12px 12px 14px}}
    .card{{background:rgba(15,23,42,0.55);border:1px solid var(--line);border-left:4px solid #334155;
          border-radius:14px;padding:12px 12px 12px;margin:10px 0}}
    .meta{{color:var(--muted);font-size:12px;display:flex;align-items:center;gap:6px}}
    .press{{color:#e2e8f0}}
    .dot{{opacity:.6}}
    .ttl{{margin-top:6px;font-size:15px;line-height:1.35}}
    .sum{{margin-top:8px;color:#cbd5e1;font-size:13px;line-height:1.55}}
    .lnk{{margin-top:10px}}
    .lnk a{{display:inline-block;color:#e5e7eb;text-decoration:none;border:1px solid var(--line);
           padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.03)}}
    .empty{{color:var(--muted);font-size:13px;padding:10px 2px}}
    .footer{{margin-top:22px;color:var(--muted);font-size:12px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div>
        <h1>{esc(title)}</h1>
        <div class="sub">기간: {esc(period)} · 기사 {total}건</div>
      </div>
      <div class="nav">
        <a href="{esc(index_url)}">최신/아카이브</a>
      </div>
    </div>

    <div class="chips">
      {chips_html}
    </div>

    {sections_html}

    <div class="footer">
      * 자동 수집 결과이며, 제목/요약은 원문을 기반으로 정리됩니다. (필요 시 원문 확인)
    </div>
  </div>
</body>
</html>
"""


def render_index_page(manifest: dict, base_url: str) -> str:
    dates = manifest.get("dates", [])
    dates = sorted(dates, reverse=True)
    latest = dates[0] if dates else None

    items_html = []
    for d in dates[:30]:
        url = f"{base_url}/archive/{d}.html"
        items_html.append(f'<li><a href="{esc(url)}">{esc(d)}</a></li>')
    ul = "\n".join(items_html) if items_html else "<li>아카이브가 아직 없습니다.</li>"

    latest_link = f"{base_url}/archive/{latest}.html" if latest else base_url

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>농산물 뉴스 브리핑</title>
  <style>
    body{{margin:0;background:#0b1220;color:#e5e7eb;font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Noto Sans KR", Arial;}}
    .wrap{{max-width:900px;margin:0 auto;padding:24px 16px 60px}}
    h1{{margin:0;font-size:22px}}
    .sub{{color:#94a3b8;margin-top:8px;font-size:13px}}
    .btn{{display:inline-block;margin-top:14px;text-decoration:none;color:#e5e7eb;border:1px solid #1f2937;
         padding:10px 12px;border-radius:12px;background:rgba(255,255,255,0.03)}}
    .panel{{margin-top:18px;border:1px solid #1f2937;border-radius:16px;background:rgba(255,255,255,0.02);padding:14px}}
    ul{{margin:10px 0 0 18px}}
    a{{color:#cbd5e1}}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>농산물 뉴스 브리핑</h1>
    <div class="sub">최신 브리핑과 날짜별 아카이브를 제공합니다.</div>

    <a class="btn" href="{esc(latest_link)}">최신 브리핑 열기</a>

    <div class="panel">
      <div style="font-weight:700;margin-bottom:6px;">날짜별 아카이브</div>
      <ul>
        {ul}
      </ul>
    </div>
  </div>
</body>
</html>
"""


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

    r = requests.post(url, data=data, timeout=30)
    if not r.ok:
        log.error("[KAKAO TOKEN ERROR] %s", r.text)
        r.raise_for_status()
    j = r.json()
    return j["access_token"]

def kakao_send_to_me(text: str, web_url: str):
    access_token = kakao_refresh_access_token()

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    # Kakao default template
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": web_url, "mobile_web_url": web_url},
        "button_title": "브리핑 열기",
    }

    r = requests.post(url, headers=headers, data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=30)
    if not r.ok:
        log.error("[KAKAO SEND ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()

def pick_kakao_highlights(by_section: dict, k: int = 3):
    # pick best one per section first, then top-k overall
    picks = []
    for sec in SECTIONS:
        lst = by_section.get(sec["key"], [])
        if lst:
            picks.append(lst[0])
    # sort by score desc
    picks.sort(key=lambda a: a.score, reverse=True)
    return picks[:k]


# -----------------------------
# Window calculation
# -----------------------------
def compute_end_kst():
    if FORCE_REPORT_DATE:
        d = datetime.strptime(FORCE_REPORT_DATE, "%Y-%m-%d").date()
        return dt_kst(d, REPORT_HOUR_KST)

    n = now_kst()
    candidate = n.replace(hour=REPORT_HOUR_KST, minute=0, second=0, microsecond=0)
    # If running before today's report hour, use yesterday's cutoff
    if n < candidate:
        candidate -= timedelta(days=1)
    return candidate

def compute_window(repo: str, token: str, end_kst: datetime):
    state = load_state(repo, token)
    last_end_iso = state.get("last_end_iso")

    prev_bd = previous_business_day(end_kst.date())
    prev_cutoff = dt_kst(prev_bd, REPORT_HOUR_KST)

    start = prev_cutoff
    if last_end_iso:
        try:
            st = datetime.fromisoformat(last_end_iso)
            if st.tzinfo is None:
                st = st.replace(tzinfo=KST)
            # choose earlier to avoid missing (also fixes “holiday mis-detected and state moved forward”)
            start = min(st.astimezone(KST), prev_cutoff)
        except Exception:
            start = prev_cutoff

    # safety
    if start >= end_kst:
        start = end_kst - timedelta(hours=24)

    return start, end_kst


# -----------------------------
# Main
# -----------------------------
def main():
    if not DEFAULT_REPO:
        raise RuntimeError("GITHUB_REPO is not set (e.g., HongTaeHwa/agri-news-brief)")
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is not set")
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        raise RuntimeError("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN is not set")

    repo = DEFAULT_REPO

    end_kst = compute_end_kst()

    # Skip if not business day in KR
    if not is_business_day_kr(end_kst.date()):
        log.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date().isoformat())
        return

    start_kst, end_kst = compute_window(repo, GH_TOKEN, end_kst)
    log.info("[INFO] Window KST: %s ~ %s", start_kst.isoformat(), end_kst.isoformat())

    report_date = end_kst.date().isoformat()

    # PAGES_BASE_URL
    base_url = os.getenv("PAGES_BASE_URL", "").strip()
    if not base_url:
        owner, name = repo.split("/", 1)
        base_url = f"https://{owner.lower()}.github.io/{name}"
    base_url = base_url.rstrip("/")

    daily_url = f"{base_url}/archive/{report_date}.html"

    # Collect
    by_section = collect_all_sections(start_kst, end_kst)
    by_section = fill_summaries(by_section)

    # Render daily page + index
    daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, base_url)
    manifest, msha = load_archive_manifest(repo, GH_TOKEN)
    dates = set(manifest.get("dates", []))
    dates.add(report_date)
    manifest["dates"] = sorted(list(dates))

    index_html = render_index_page(manifest, base_url)

    # Write to GitHub (docs/)
    # daily
    daily_path = f"{DOCS_ARCHIVE_DIR}/{report_date}.html"
    raw_old, sha_old = github_get_file(repo, daily_path, GH_TOKEN, ref="main")
    github_put_file(repo, daily_path, daily_html, GH_TOKEN, f"Add daily brief {report_date}", sha=sha_old, branch="main")

    # index
    raw_old2, sha_old2 = github_get_file(repo, DOCS_INDEX_PATH, GH_TOKEN, ref="main")
    github_put_file(repo, DOCS_INDEX_PATH, index_html, GH_TOKEN, f"Update index {report_date}", sha=sha_old2, branch="main")

    # archive manifest + state
    save_archive_manifest(repo, GH_TOKEN, manifest, msha)
    save_state(repo, GH_TOKEN, end_kst)

    # Compose Kakao message
    counts = []
    total = 0
    for sec in SECTIONS:
        n = len(by_section.get(sec["key"], []))
        total += n
        counts.append((sec["key"], n))

    # supply, policy, pest, dist order fixed
    c_map = {k: n for k, n in counts}
    line_counts = f"- 기사(총 {total}건) : 품목 {c_map.get('supply',0)} · 정책 {c_map.get('policy',0)} · 방제 {c_map.get('pest',0)} · 유통 {c_map.get('dist',0)}"

    highlights = pick_kakao_highlights(by_section, k=3)
    hl_lines = []
    for i, a in enumerate(highlights, 1):
        sec_title = section_conf(a.section)["title"]
        one = a.summary.splitlines()[0].strip()
        if len(one) > 70:
            one = one[:70].rstrip() + "…"
        hl_lines.append(f"{i}) ({sec_title}) {a.press} | {a.title}")
        hl_lines.append(f"   - {one}")

    title = f"[{report_date} 농산물 뉴스 Brief]"
    body = [title, "", line_counts, ""]
    if hl_lines:
        body.append("오늘의 체크포인트")
        body.extend(hl_lines)
        body.append("")
    body.append("👉 '브리핑 열기'에서 섹션별 요약/원문을 확인하세요.")

    if KAKAO_INCLUDE_LINK_IN_TEXT:
        body.append(daily_url)

    kakao_text = "\n".join(body)

    kakao_send_to_me(kakao_text, daily_url)
    log.info("[OK] Kakao message sent. URL=%s", daily_url)


if __name__ == "__main__":
    main()
