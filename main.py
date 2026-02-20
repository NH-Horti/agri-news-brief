#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py (GitHub Actions)
- 과수·화훼(원예) 브리핑 자동 수집/정리/배포 스크립트

✅ 반영 사항 (요청분)
1) "좋아요/별로에요(피드백)" 관련 코드: 완전 제거(없음)
2) 품목 키워드 점검/강화
   - 화훼 포함
   - 사과, 배, 단감, 감, 키위, 유자, 포도, 밤, 자두, 감귤, 만감, 복숭아, 매실 기본 포함
   - "기본 품목 키워드 + 신호 단어" 조합으로 동적 쿼리 생성 (스크래핑 효율↑)
3) 남은 3개 고도화까지 포함 완성
   - (A) 중복 제거 고도화: pest 섹션 '사건키(event key: 지역+병해/기상+기간)'로 묶기
   - (B) UX 필터: index.html에서 '매체 그룹' / '품목' 필터 제공 (search_index.json 기반)
   - (C) 전날 fallback: 섹션 기사 부족 시 전날 search_index.json에서 재활용(표시)

선택 옵션
- STRICT_HORTI_ONLY=true (기본) : 오이/고추/양곡/축산 등 원예(과수·화훼) 관련 없는 것 제외 강화
- ENABLE_EVENT_DEDUPE=true (기본) : 사건키 기반 중복 제거

필수 ENV (GitHub Actions secrets 권장)
- NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
- GITHUB_TOKEN (또는 GH_TOKEN)
- GITHUB_REPOSITORY (Actions 기본 제공) 또는 GITHUB_REPO/REPO_SLUG

선택 ENV
- KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN, KAKAO_REDIRECT_URI (카톡 전송 시)
- WHITELIST_RSS_URLS (콤마 구분)  # 비우면 기본 공식 RSS 사용
- MIN_PER_SECTION (기본 2)
- MAX_SECTION_QUERIES (기본 18)
- MAX_ITEMS_PER_QUERY (기본 50)
- REPORT_HOUR_KST (기본 7)
- FORCE_RUN=true (휴일/주말에도 강제 실행)
- DRY_RUN=true (GitHub 업로드/카톡 전송 없이 로컬 로그만)
"""

from __future__ import annotations

import os
import re
import json
import time
import math
import base64
import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, date
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import requests

# -----------------------------
# Timezone / Session
# -----------------------------
KST = timezone(timedelta(hours=9))
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "HortiBriefingBot/1.0 (+github actions)"})

def now_kst() -> datetime:
    return datetime.now(tz=KST)

# -----------------------------
# Config
# -----------------------------
REPO = (os.getenv("REPO_SLUG") or os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY") or "").strip()
GH_TOKEN = (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
BRANCH = (os.getenv("BRANCH") or os.getenv("GITHUB_REF_NAME") or "main").strip()

NAVER_CLIENT_ID = (os.getenv("NAVER_CLIENT_ID") or "").strip()
NAVER_CLIENT_SECRET = (os.getenv("NAVER_CLIENT_SECRET") or "").strip()

DOCS_DIR = "docs"
ARCHIVE_DIR = f"{DOCS_DIR}/archive"
SEARCH_INDEX_PATH = f"{DOCS_DIR}/search_index.json"
MANIFEST_PATH = f"{DOCS_DIR}/manifest.json"
INDEX_HTML_PATH = f"{DOCS_DIR}/index.html"

REPORT_HOUR_KST = int(os.getenv("REPORT_HOUR_KST", "7") or "7")

MAX_SECTION_QUERIES = max(5, int(os.getenv("MAX_SECTION_QUERIES", "18") or "18"))
MAX_ITEMS_PER_QUERY = max(10, int(os.getenv("MAX_ITEMS_PER_QUERY", "50") or "50"))
MIN_PER_SECTION = max(0, int(os.getenv("MIN_PER_SECTION", "2") or "2"))

DRY_RUN = (os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes"))
FORCE_RUN = (os.getenv("FORCE_RUN", "false").lower() in ("1", "true", "yes"))

STRICT_HORTI_ONLY = (os.getenv("STRICT_HORTI_ONLY", "true").lower() in ("1", "true", "yes"))
ENABLE_EVENT_DEDUPE = (os.getenv("ENABLE_EVENT_DEDUPE", "true").lower() in ("1", "true", "yes"))

# -----------------------------
# Default RSS (공식 소스 우선)
# - WHITELIST_RSS_URLS env가 비어 있으면 아래 기본값 사용
# -----------------------------
DEFAULT_RSS_URLS = [
    "https://www.korea.kr/rss/dept_mafra.xml",       # 정책브리핑(농식품부)
    "https://www.korea.kr/rss/dept_rda.xml",         # 정책브리핑(농촌진흥청)
    "https://www.korea.kr/rss/pressrelease.xml",     # 정책브리핑(보도자료 전체)
    "https://www.mafra.go.kr/bbs/home/792/rssList.do?row=50",  # 농식품부 보도자료 RSS
    "https://www.mafra.go.kr/bbs/home/793/rssList.do?row=50",  # 농식품부 설명자료 RSS
]
WHITELIST_RSS_URLS = [u.strip() for u in (os.getenv("WHITELIST_RSS_URLS", "") or "").split(",") if u.strip()] or DEFAULT_RSS_URLS

# -----------------------------
# Required commodity keywords (요청 기본 포함)
# -----------------------------
REQUIRED_ITEM_KEYWORDS = [
    "화훼",
    "사과", "배", "단감", "감", "키위", "유자", "포도", "밤", "자두", "감귤", "만감", "복숭아", "매실",
]

COMMODITY_SYNONYMS: dict[str, list[str]] = {
    "화훼": ["화훼", "절화", "꽃시장", "꽃 경매", "양재꽃시장", "화훼공판장", "화훼경매", "aT 화훼"],
    "사과": ["사과", "부사", "홍로", "후지"],
    "배": ["배", "신고", "원황"],
    "단감": ["단감", "부유", "태추"],
    "감": ["감", "떫은감", "대봉", "곶감"],
    "키위": ["키위", "참다래"],
    "유자": ["유자"],
    "포도": ["포도", "샤인머스캣", "거봉", "캠벨"],
    "밤": ["밤"],
    "자두": ["자두"],
    "감귤": ["감귤", "귤", "노지감귤"],
    "만감": ["만감", "만감류", "한라봉", "레드향", "천혜향", "카라향", "황금향"],
    "복숭아": ["복숭아", "백도", "황도"],
    "매실": ["매실"],
    # 확장(원예 과수) - 필요 시
    "딸기": ["딸기"],
}

# 원예 브리핑에서 배제할 가능성이 높은 품목(선택1)
NON_HORTI_ITEM_TERMS = [
    "오이", "고추", "풋고추", "파프리카", "토마토", "배추", "무", "양파", "마늘",
    "감자", "고구마", "콩", "팥", "쌀", "벼", "비축미", "밀", "보리",
    "한우", "돼지", "닭", "계란", "우유", "축산", "수산",
]

# -----------------------------
# Section definitions
# -----------------------------
SECTIONS = [
    {"key": "supply", "title": "수급·가격", "color": "#2563eb"},
    {"key": "policy", "title": "정책·지원", "color": "#16a34a"},
    {"key": "distribution", "title": "유통·도매시장", "color": "#f97316"},
    {"key": "pest", "title": "병해충·기상", "color": "#dc2626"},
]

SECTION_SIGNAL_TERMS = {
    "supply": ["수급", "가격", "작황", "저장", "출하"],
    "distribution": ["가락시장", "도매시장", "경락가", "반입", "공판장", "온라인도매시장"],
    "policy": ["지원", "할인지원", "수매", "비축", "할당관세", "검역", "원산지"],
    "pest": ["화상병", "탄저병", "냉해", "동해", "우박", "병해충", "방제", "예찰", "경보"],
}

CURATED_BASE_QUERIES = {
    "supply": [
        "사과 수급 가격", "배 수급 가격", "감귤 만감 수급 가격", "포도 샤인머스캣 수급 가격",
        "단감 곶감 수급 가격", "키위 참다래 수급 가격", "유자 수급 가격",
        "복숭아 자두 매실 수급 가격", "밤 수급 가격", "화훼 절화 경매 가격",
    ],
    "distribution": [
        "가락시장 청과 경락가", "도매시장 반입량 과일", "공판장 경매 청과",
        "APC 선별 과수", "CA저장 과수", "온라인도매시장 거래량", "농산물 수출 과일 검역",
    ],
    "policy": [
        "농식품부 보도자료 농산물", "정책브리핑 농축수산물 할인지원",
        "할당관세 수입 과일", "원산지 표시 단속 농산물", "온라인 도매시장 농식품부 aT",
        "검역본부 수출입 과일",
    ],
    "pest": [
        "과수화상병 예찰 방제", "탄저병 방제 과수", "냉해 동해 우박 과수 피해",
        "병해충 예찰 과수", "농업기술센터 과수 방제", "화훼 병해충 방제",
    ],
}

def build_section_queries(section_key: str) -> list[str]:
    """(기본 품목) + (신호 단어) 조합으로 쿼리를 만들되, 호출 수는 제한(MAX_SECTION_QUERIES)."""
    base = CURATED_BASE_QUERIES.get(section_key, []).copy()
    signals = SECTION_SIGNAL_TERMS.get(section_key, [])
    dyn = []

    # interleave: 신호 우선 → 품목 편향 완화
    commodities = REQUIRED_ITEM_KEYWORDS[:]
    if "감" in commodities and "단감" in commodities:
        commodities.remove("감")
        commodities.append("감")

    for sig in signals:
        for kw in commodities:
            dyn.append(f"{kw} {sig}")

    # merge unique in order
    seen = set()
    merged = []
    for q in base + dyn:
        qn = " ".join((q or "").split())
        if not qn:
            continue
        if qn in seen:
            continue
        seen.add(qn)
        merged.append(qn)

    return merged[:MAX_SECTION_QUERIES]

# -----------------------------
# Models
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
    canon_url: str
    norm_key: str
    title_key: str
    score: float = 0.0
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    commodities: list[str] = field(default_factory=list)
    press_group: str = ""
    urgent: bool = False
    reused: bool = False
    reused_from: str = ""

# -----------------------------
# Helpers: normalize / commodity / tags
# -----------------------------
def normalize_host(url_or_host: str) -> str:
    if not url_or_host:
        return ""
    if "://" in url_or_host:
        try:
            return (urlparse(url_or_host).netloc or "").lower()
        except Exception:
            return url_or_host.lower()
    return url_or_host.lower()

def canonicalize_url(url: str) -> str:
    """URL 정규화(utm 등 제거)."""
    if not url:
        return ""
    try:
        u = urlparse(url)
        q = parse_qs(u.query)
        # 흔한 트래킹 파라미터 제거
        for k in list(q.keys()):
            if k.lower().startswith("utm_") or k.lower() in ("fbclid", "gclid", "igshid"):
                q.pop(k, None)
        query = urlencode({k: v[0] for k, v in q.items()}, doseq=False)
        return urlunparse((u.scheme, u.netloc, u.path, "", query, ""))
    except Exception:
        return url

def norm_title_key(title: str) -> str:
    t = (title or "").lower()
    t = re.sub(r"\[[^\]]+\]", " ", t)
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"[^0-9a-z가-힣]+", "", t)
    return t[:90]

def make_norm_key(canon_url: str, press: str, title_key: str) -> str:
    if canon_url:
        h = hashlib.sha1(canon_url.encode("utf-8")).hexdigest()[:16]
        return f"url:{h}"
    base = f"{(press or '').strip()}|{title_key}"
    h = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    return f"t:{h}"

def detect_commodities(text: str) -> list[str]:
    t = (text or "").lower()
    found = []
    for canon, syns in COMMODITY_SYNONYMS.items():
        for s in syns:
            if s and s.lower() in t:
                found.append(canon)
                break
    order = {k: i for i, k in enumerate(REQUIRED_ITEM_KEYWORDS + sorted(COMMODITY_SYNONYMS.keys()))}
    return sorted(set(found), key=lambda x: order.get(x, 999))

_NUM_UNIT_RX = re.compile(r"(\d[\d,\.]*\s*(원|만원|천원|kg|㎏|g|톤|t|%))")
_DATE_HINT_RX = re.compile(r"(\d{1,2}월\s*\d{1,2}일|\d{4}년\s*\d{1,2}월|\d{1,2}월|이번\s*주|이\s*달|다음\s*주|내\s*달)")
URGENT_TERMS = ["과수화상병", "화상병", "탄저병", "냉해", "동해", "우박", "서리", "병해충 경보", "긴급", "주의보", "경보", "특보"]

def compute_press_group(press: str, domain: str) -> str:
    p = (press or "").strip()
    d = (domain or "").lower()
    if d.endswith(".go.kr") or "korea.kr" in d:
        return "공식"
    if any(k in p for k in ["농림축산식품부", "농식품부", "농촌진흥청", "검역", "정책브리핑", "aT", "정부"]):
        return "공식"
    if "농민신문" in p or "nongmin" in d:
        return "농민신문"
    # 대략적 분류
    major_kw = ["연합뉴스", "KBS", "MBC", "SBS", "YTN", "조선", "중앙", "동아", "한겨레", "경향", "한국경제", "매일경제"]
    if any(k in p for k in major_kw):
        return "주요"
    if any(k in p for k in ["일보", "신문", "방송", "뉴스"]):
        return "지역/기타"
    return "기타"

def analyze_signals(title: str, desc: str, section_key: str) -> tuple[list[str], list[str], bool]:
    text = f"{title} {desc}".strip()
    tags: set[str] = set()
    urgent = False

    if _NUM_UNIT_RX.search(text):
        tags.add("수치")
    if _DATE_HINT_RX.search(text):
        tags.add("기간")

    if any(k in text for k in ["가격", "시세", "경락", "경락가", "도매가", "소매가", "강세", "약세", "상승", "하락"]):
        tags.add("가격")
    if any(k in text for k in ["수급", "물량", "반입", "출하", "재고", "저장", "생산", "수확", "공급", "감소", "증가"]):
        tags.add("물량/수급")
    if any(k in text for k in ["지원", "할인지원", "수매", "비축", "할당관세", "관세", "대책", "보조", "예산", "정책", "조치"]):
        tags.add("정책")
    if any(k in text for k in ["병해충", "방제", "예찰", "경보", "발생", "확산", "약제", "살포", "검역"]):
        tags.add("병해/방제")

    if section_key == "distribution":
        tags.add("유통")
    if section_key == "pest":
        tags.add("병해/방제")
        if any(k in text for k in URGENT_TERMS):
            urgent = True
            tags.add("긴급")

    comms = detect_commodities(text)
    if comms:
        tags.add("품목")

    tag_order = ["긴급", "가격", "물량/수급", "정책", "유통", "병해/방제", "수치", "기간", "품목"]
    ordered = sorted(tags, key=lambda x: tag_order.index(x) if x in tag_order else 999)
    return ordered, comms, urgent

# -----------------------------
# Strict relevance filter (선택1 포함)
# -----------------------------
BAN_KWS = [
    "구인", "채용", "모집", "아르바이트", "알바", "대출", "카지노", "도박", "성인", "19금",
    "부동산", "분양", "오피스텔", "전세", "월세", "광고", "협찬", "체험단",
]

def is_relevant(section_key: str, title: str, desc: str, domain: str) -> bool:
    text = f"{title} {desc}".lower()
    if any(k in text for k in BAN_KWS):
        return False

    # ✅ 선택1: 원예 외 품목 강제 제외 (단, 원예 품목(과수/화훼)이 같이 있으면 허용)
    if STRICT_HORTI_ONLY:
        if any(t.lower() in text for t in NON_HORTI_ITEM_TERMS):
            if not detect_commodities(text):
                return False

    # section별 최소 맥락
    if section_key == "policy":
        # 정책은 공공/농업 맥락 없으면 제외
        agri_ctx = ["농식품", "농업", "농산물", "원예", "과수", "청과", "도매시장", "검역", "원산지", "할인지원", "성수품", "가격 안정", "aT", "농협"]
        if not any(k in text for k in agri_ctx) and not (domain.endswith(".go.kr") or "korea.kr" in domain):
            return False

    if section_key == "distribution":
        dist_ctx = ["가락시장", "도매시장", "공판장", "경락", "경락가", "반입", "APC", "선별", "온라인도매시장", "수출", "검역"]
        if not any(k.lower() in text for k in dist_ctx):
            return False

    if section_key == "pest":
        pest_ctx = ["병해충", "방제", "예찰", "화상병", "탄저병", "냉해", "동해", "우박", "서리", "경보", "약제", "살포"]
        if sum(1 for k in pest_ctx if k.lower() in text) < 2:
            return False

    # supply는 너무 광범위하므로 최소 원예/수급 맥락 보장
    if section_key == "supply":
        supply_ctx = ["수급", "가격", "작황", "출하", "저장", "물량", "반입", "경락", "도매"]
        if not any(k in text for k in supply_ctx) and not detect_commodities(text):
            return False

    return True

# -----------------------------
# Scoring (Decision signal 중심)
# -----------------------------
def score_article(section_key: str, title: str, desc: str, press: str, domain: str, pub_dt: datetime) -> float:
    text = f"{title} {desc}"
    score = 0.0

    tags, comms, urgent = analyze_signals(title, desc, section_key)

    # 신호 가중치
    if "가격" in tags: score += 4.0
    if "물량/수급" in tags: score += 3.5
    if "정책" in tags: score += 3.2
    if "유통" in tags: score += 2.6
    if "병해/방제" in tags: score += 3.0
    if "수치" in tags: score += 2.2
    if "기간" in tags: score += 0.8
    if urgent: score += 3.0

    # 품목 등장 가산
    if comms:
        score += min(2.0, 0.6 * len(comms))

    # 공식/농민신문/주요매체 가산
    pg = compute_press_group(press, domain)
    if pg == "공식": score += 3.0
    elif pg == "농민신문": score += 2.0
    elif pg == "주요": score += 1.6
    elif pg == "중견/전문": score += 1.0

    # 최신성
    try:
        age_h = (now_kst() - pub_dt).total_seconds() / 3600.0
        if age_h <= 8: score += 0.8
        elif age_h <= 24: score += 0.4
        elif age_h <= 48: score += 0.2
    except Exception:
        pass

    return round(score, 3)

# -----------------------------
# Dedup (URL/title) + pest 사건키
# -----------------------------
_REGION_RX = re.compile(r"[가-힣]{2,}(?:특별시|광역시|특별자치시|특별자치도|도|시|군|구|읍|면)")
_BARE_REGION_RX = re.compile(r"([가-힣]{2,6})(?=(?:\s*)?(?:농업기술센터|농기센터|군청|시청|구청|농업기술원|농업기술과))")

_PEST_DISEASE_TERMS = [
    "과수화상병", "화상병", "탄저병",
    "냉해", "동해", "우박", "서리", "한파", "폭설",
    "병해충", "방제", "예찰", "경보", "주의보", "특보",
]

def _pest_region_key(text: str) -> str:
    t = text or ""
    ms = list(_REGION_RX.finditer(t))
    if not ms:
        m2 = _BARE_REGION_RX.search(t)
        return (m2.group(1) if m2 else "") or ""
    for m in ms:
        r = m.group(0)
        if r.endswith(("군", "시", "구")):
            return r
    return ms[0].group(0)

def _pest_disease_key(text: str) -> str:
    for k in _PEST_DISEASE_TERMS:
        if k in (text or ""):
            return "화상병" if k in ("과수화상병", "화상병") else k
    return ""

def _pest_time_key(text: str) -> str:
    t = text or ""
    m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", t)
    if m:
        return f"{int(m.group(1)):02d}{int(m.group(2)):02d}"
    m = re.search(r"(\d{4})년\s*(\d{1,2})월", t)
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})월", t)
    if m:
        return f"{int(m.group(1)):02d}xx"
    if "이번주" in t or "이번 주" in t:
        return "thisweek"
    if "이달" in t or "이번달" in t or "이번 달" in t:
        return "thismonth"
    return ""

def pest_event_key(title: str, desc: str) -> str:
    blob = f"{title} {desc}".strip()
    region = _pest_region_key(blob)
    disease = _pest_disease_key(blob)
    tkey = _pest_time_key(blob)
    key = "|".join([k for k in (region, disease, tkey) if k])
    return key

def near_dup_title(a: Article, b: Article) -> bool:
    # 간단 토큰 유사도
    ta = set(re.findall(r"[0-9a-z가-힣]{2,}", (a.title or "").lower()))
    tb = set(re.findall(r"[0-9a-z가-힣]{2,}", (b.title or "").lower()))
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    union = len(ta | tb)
    j = inter / union if union else 0.0
    return j >= 0.78

# -----------------------------
# Naver Search
# -----------------------------
NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"

def naver_search(query: str, display: int = 50, start: int = 1) -> dict:
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "start": start, "sort": "date"}
    # 429 대응: 지수 백오프
    backoff = 1.0
    for _ in range(6):
        r = SESSION.get(NAVER_API_URL, headers=headers, params=params, timeout=15)
        if r.status_code == 429:
            time.sleep(backoff + random.random() * 0.2)
            backoff = min(30.0, backoff * 2)
            continue
        r.raise_for_status()
        return r.json()
    return {"items": []}

def clean_html(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&quot;", "\"").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_naver_item(it: dict) -> tuple[str, str, str, str, datetime]:
    title = clean_html(it.get("title", ""))
    desc = clean_html(it.get("description", ""))
    link = it.get("link", "") or ""
    origin = it.get("originallink", "") or link
    pub = it.get("pubDate", "")
    # naver pubDate RFC822
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        pub_kst = dt.astimezone(KST)
    except Exception:
        pub_kst = now_kst()
    return title, desc, link, origin, pub_kst

# -----------------------------
# RSS ingestion
# -----------------------------
def fetch_rss(url: str) -> list[dict]:
    try:
        r = SESSION.get(url, timeout=20)
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
            pub_kst = now_kst()
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                pub_kst = dt.astimezone(KST)
            except Exception:
                pass
            if title and link:
                items.append({"title": title, "description": clean_html(desc), "originallink": link, "link": link, "pub_dt_kst": pub_kst})
        return items
    except Exception:
        return []

# -----------------------------
# Press name guess
# -----------------------------
def press_from_domain(domain: str) -> str:
    d = (domain or "").lower()
    if "korea.kr" in d:
        return "정책브리핑"
    if d.endswith(".go.kr"):
        return "공공기관"
    if "mafra.go.kr" in d:
        return "농식품부"
    if "rda.go.kr" in d:
        return "농촌진흥청"
    if "nongmin.com" in d:
        return "농민신문"
    return domain

# -----------------------------
# Window computation (전일 07:00 ~ 금일 07:00 기본)
# -----------------------------
def scheduled_end_kst(now: datetime) -> datetime:
    d = now.date()
    end = datetime(d.year, d.month, d.day, REPORT_HOUR_KST, 0, 0, tzinfo=KST)
    if now >= end:
        return end
    return now

def compute_window() -> tuple[datetime, datetime, str]:
    end = scheduled_end_kst(now_kst())
    start = end - timedelta(days=1)
    report_date = end.date().isoformat()
    return start, end, report_date

# -----------------------------
# Selection / Fallback
# -----------------------------
def select_top(section_key: str, items: list[Article], max_n: int = 8) -> list[Article]:
    items = sorted(items, key=lambda a: (a.score, a.pub_dt_kst), reverse=True)

    # 1) URL/title dedupe
    out = []
    seen_url = set()
    for a in items:
        if a.canon_url and a.canon_url in seen_url:
            continue
        if any(near_dup_title(a, b) for b in out):
            continue
        seen_url.add(a.canon_url)
        out.append(a)

    # 2) pest 사건키 dedupe(선택2) + region 보조
    if section_key == "pest" and ENABLE_EVENT_DEDUPE:
        used_event = set()
        used_region = set()
        filtered = []
        for a in out:
            ek = pest_event_key(a.title, a.description)
            if ek and ek in used_event:
                continue
            if ek:
                used_event.add(ek)
            else:
                rk = _pest_region_key(a.title)
                if rk and rk in used_region:
                    continue
                if rk:
                    used_region.add(rk)
            filtered.append(a)
        out = filtered

    return out[:max_n]

def load_search_index_from_repo() -> dict:
    if not REPO or not GH_TOKEN:
        return {"version": 1, "updated_at": "", "items": []}
    raw = github_get_file(REPO, SEARCH_INDEX_PATH, GH_TOKEN, ref=BRANCH)
    if not raw:
        return {"version": 1, "updated_at": "", "items": []}
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            return {"version": 1, "updated_at": "", "items": obj}
        if isinstance(obj, dict):
            obj.setdefault("version", 1)
            obj.setdefault("items", [])
            return obj
    except Exception:
        pass
    return {"version": 1, "updated_at": "", "items": []}

def apply_prev_day_fallback(by_section: dict[str, list[Article]], report_date: str) -> None:
    if MIN_PER_SECTION <= 0:
        return
    if all(len(by_section.get(sec["key"], [])) >= MIN_PER_SECTION for sec in SECTIONS):
        return

    idx = load_search_index_from_repo()
    items = idx.get("items", []) if isinstance(idx, dict) else []
    if not items:
        return

    dates = sorted({it.get("date") for it in items if it.get("date")}, reverse=False)
    prev_dates = [d for d in dates if d < report_date]
    if not prev_dates:
        return
    prev_date = prev_dates[-1]

    # section별 후보
    prev_by_sec: dict[str, list[dict]] = {}
    for it in items:
        if it.get("date") != prev_date:
            continue
        sk = it.get("section")
        if not sk:
            continue
        prev_by_sec.setdefault(sk, []).append(it)

    # fallback
    for sec in SECTIONS:
        sk = sec["key"]
        cur = by_section.get(sk, [])
        need = max(0, MIN_PER_SECTION - len(cur))
        if need <= 0:
            continue
        cands = prev_by_sec.get(sk, [])
        if not cands:
            continue

        used_urls = {a.canon_url for a in cur if a.canon_url}
        used_titles = {a.title_key for a in cur if a.title_key}

        cands_sorted = sorted(cands, key=lambda x: float(x.get("score", 0.0)), reverse=True)
        added = 0
        for it in cands_sorted:
            if added >= need:
                break
            url = (it.get("url") or it.get("originallink") or "").strip()
            title = (it.get("title") or "").strip()
            if not url or not title:
                continue
            canon = canonicalize_url(url)
            tkey = norm_title_key(title)
            if canon in used_urls or tkey in used_titles:
                continue

            domain = normalize_host(url)
            press = (it.get("press") or press_from_domain(domain)).strip()
            desc = (it.get("snippet") or it.get("summary") or "").strip()
            pub_dt = datetime.fromisoformat(prev_date).replace(tzinfo=KST)

            tags = it.get("tags") or []
            comms = it.get("commodities") or detect_commodities(f"{title} {desc}")
            urgent = bool(it.get("urgent", False))
            pg = it.get("press_group") or compute_press_group(press, domain)

            a = Article(
                section=sk,
                title=title,
                description=desc,
                link=url,
                originallink=url,
                pub_dt_kst=pub_dt,
                domain=domain,
                press=press,
                canon_url=canon,
                title_key=tkey,
                norm_key=make_norm_key(canon, press, tkey),
                score=float(it.get("score", 0.0)),
                summary=(it.get("summary") or desc),
                tags=list(tags),
                commodities=list(comms),
                press_group=str(pg),
                urgent=urgent,
                reused=True,
                reused_from=prev_date,
            )
            cur.append(a)
            used_urls.add(canon)
            used_titles.add(tkey)
            added += 1

        by_section[sk] = sorted(cur, key=lambda x: (x.score, x.pub_dt_kst), reverse=True)

# -----------------------------
# Rendering: archive html + index html + search index json
# -----------------------------
def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def fmt_dt(dt: datetime) -> str:
    try:
        return dt.astimezone(KST).strftime("%m/%d %H:%M")
    except Exception:
        return ""

def render_archive(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict[str, list[Article]]) -> str:
    # chips
    chips = []
    for sec in SECTIONS:
        lst = by_section.get(sec["key"], [])
        chips.append((sec["key"], sec["title"], len(lst), sec["color"]))

    chips_html = "\n".join(
        f'<a class="chip" href="#sec-{k}" style="border-color:{c}"><span>{esc(t)}</span><b>{n}</b></a>'
        for k, t, n, c in chips
    )

    sections_html = []
    for sec in SECTIONS:
        key = sec["key"]
        title = sec["title"]
        color = sec["color"]
        lst = by_section.get(key, [])

        cards = []
        for i, a in enumerate(lst):
            url = a.originallink or a.link
            core_badge = '<span class="badge core">핵심</span>' if i < 2 else ""
            urgent_badge = '<span class="badge urgent">🚨긴급</span>' if a.urgent else ""
            reused_badge = f'<span class="badge reused">전날({esc(a.reused_from)})</span>' if a.reused else ""
            tags = " ".join(f'<span class="tag">{esc(t)}</span>' for t in a.tags[:6])
            comms = ", ".join(a.commodities[:5])

            cards.append(f"""
            <div class="card" style="border-left-color:{color}">
              <div class="top">
                {core_badge}{urgent_badge}{reused_badge}
                <span class="press">{esc(a.press)}</span>
                <span class="dot">·</span>
                <span class="time">{esc(fmt_dt(a.pub_dt_kst))}</span>
                <span class="dot">·</span>
                <span class="score">score {a.score:.1f}</span>
              </div>
              <a class="title" href="{esc(url)}" target="_blank" rel="noopener">{esc(a.title)}</a>
              <div class="meta">{tags}</div>
              <div class="summary">{esc((a.summary or a.description or "")[:220])}</div>
              <div class="bottom">
                <span class="comms">{esc(comms)}</span>
                <button class="copy" data-url="{esc(url)}">링크복사</button>
              </div>
            </div>
            """)

        sections_html.append(f"""
        <section id="sec-{key}">
          <h2 style="border-left:6px solid {color}; padding-left:10px;">{esc(title)}</h2>
          <div class="grid">
            {''.join(cards) if cards else '<div class="empty">해당 섹션 기사 없음</div>'}
          </div>
        </section>
        """)

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>원예(과수·화훼) 데일리 브리핑 - {esc(report_date)}</title>
<style>
  body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans KR,Apple SD Gothic Neo,sans-serif; margin:0; background:#0b1220; color:#e5e7eb}}
  a{{color:inherit; text-decoration:none}}
  .wrap{{max-width:980px; margin:0 auto; padding:18px}}
  .head{{display:flex; gap:10px; align-items:flex-end; justify-content:space-between; flex-wrap:wrap}}
  .title{{font-size:22px; font-weight:800}}
  .sub{{font-size:12px; color:#93c5fd}}
  .chips{{display:flex; gap:8px; flex-wrap:wrap; margin:12px 0 18px}}
  .chip{{display:inline-flex; gap:8px; align-items:center; border:1px solid #334155; padding:6px 10px; border-radius:999px; background:#0f172a}}
  .chip b{{background:#111827; padding:2px 8px; border-radius:999px}}
  section{{margin:18px 0 26px}}
  h2{{margin:0 0 12px}}
  .grid{{display:grid; grid-template-columns:1fr; gap:10px}}
  .card{{background:#0f172a; border:1px solid #1f2937; border-left:6px solid #334155; border-radius:12px; padding:12px}}
  .top{{display:flex; gap:8px; align-items:center; flex-wrap:wrap; font-size:12px; color:#cbd5e1}}
  .press{{font-weight:700}}
  .dot{{opacity:.6}}
  .title{{display:block; margin:8px 0 6px; font-size:16px; font-weight:800}}
  .summary{{font-size:13px; color:#e2e8f0; line-height:1.45}}
  .meta{{display:flex; gap:6px; flex-wrap:wrap; margin:8px 0 6px}}
  .tag{{font-size:11px; padding:2px 8px; background:#111827; border:1px solid #1f2937; border-radius:999px; color:#cbd5e1}}
  .badge{{font-size:11px; padding:2px 8px; border-radius:999px; font-weight:800; border:1px solid #334155}}
  .badge.core{{background:#1d4ed8; border-color:#1d4ed8}}
  .badge.urgent{{background:#b91c1c; border-color:#b91c1c}}
  .badge.reused{{background:#374151; border-color:#374151}}
  .bottom{{display:flex; justify-content:space-between; gap:10px; margin-top:10px; align-items:center; flex-wrap:wrap}}
  .copy{{cursor:pointer; border:1px solid #334155; background:#111827; color:#e5e7eb; padding:6px 10px; border-radius:10px}}
  .empty{{padding:14px; color:#94a3b8; background:#0f172a; border:1px dashed #334155; border-radius:12px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <div class="title">원예(과수·화훼) 데일리 브리핑</div>
      <div class="sub">{esc(report_date)} · 기간: {esc(start_kst.strftime("%Y-%m-%d %H:%M"))} ~ {esc(end_kst.strftime("%Y-%m-%d %H:%M"))}</div>
    </div>
    <div><a href="../index.html" style="opacity:.9; text-decoration:underline;">검색/필터로 보기</a></div>
  </div>

  <div class="chips">{chips_html}</div>

  {''.join(sections_html)}
</div>

<script>
document.addEventListener('click', (e) => {{
  const btn = e.target.closest('button.copy');
  if(!btn) return;
  const url = btn.getAttribute('data-url');
  if(!url) return;
  navigator.clipboard.writeText(url).then(()=>{{
    btn.textContent = '복사됨!';
    setTimeout(()=>btn.textContent='링크복사', 900);
  }});
}});
</script>
</body>
</html>
"""

def render_index_html(site_path: str) -> str:
    # search_index.json을 로딩하여 필터 제공
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>원예(과수·화훼) 브리핑 - 검색/필터</title>
<style>
  body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Noto Sans KR,Apple SD Gothic Neo,sans-serif; margin:0; background:#0b1220; color:#e5e7eb}}
  .wrap{{max-width:980px; margin:0 auto; padding:18px}}
  a{{color:inherit}}
  h1{{margin:0 0 10px; font-size:22px}}
  .bar{{display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:12px 0}}
  input,select{{background:#0f172a; color:#e5e7eb; border:1px solid #334155; border-radius:10px; padding:8px 10px}}
  input{{flex:1; min-width:220px}}
  .btn{{cursor:pointer; padding:8px 12px; border-radius:10px; border:1px solid #334155; background:#111827}}
  .meta{{font-size:12px; color:#94a3b8}}
  .list{{display:grid; grid-template-columns:1fr; gap:10px; margin-top:12px}}
  .item{{background:#0f172a; border:1px solid #1f2937; border-radius:12px; padding:12px}}
  .top{{display:flex; gap:8px; align-items:center; flex-wrap:wrap; font-size:12px; color:#cbd5e1}}
  .badge{{font-size:11px; padding:2px 8px; border-radius:999px; font-weight:800; border:1px solid #334155}}
  .badge.urgent{{background:#b91c1c; border-color:#b91c1c}}
  .badge.reused{{background:#374151; border-color:#374151}}
  .title{{display:block; margin:8px 0 6px; font-size:15px; font-weight:800; text-decoration:none}}
  .tags{{display:flex; gap:6px; flex-wrap:wrap; margin-top:6px}}
  .tag{{font-size:11px; padding:2px 8px; background:#111827; border:1px solid #1f2937; border-radius:999px; color:#cbd5e1}}
</style>
</head>
<body>
<div class="wrap">
  <h1>원예(과수·화훼) 브리핑 · 검색/필터</h1>
  <div class="meta">매체/품목 필터 · 사건키 중복제거(pest) · 전날 fallback 적용</div>

  <div class="bar">
    <input id="q" placeholder="키워드 검색 (예: 사과 10kg 6만원 / 화상병 / 가락시장)" />
    <select id="sec"></select>
    <select id="press"></select>
    <select id="comm"></select>
    <select id="date"></select>
    <button class="btn" id="reset">초기화</button>
  </div>

  <div class="meta" id="stat">loading...</div>
  <div class="list" id="list"></div>
</div>

<script>
const sitePath = {json.dumps(site_path)};
const secSel = document.getElementById('sec');
const pressSel = document.getElementById('press');
const commSel = document.getElementById('comm');
const dateSel = document.getElementById('date');
const qInput = document.getElementById('q');
const listEl = document.getElementById('list');
const statEl = document.getElementById('stat');

let DATA = [];

function uniq(arr) {{ return Array.from(new Set(arr.filter(Boolean))); }}
function opt(sel, value, label) {{
  const o = document.createElement('option');
  o.value = value; o.textContent = label;
  sel.appendChild(o);
}}
function fillSelects() {{
  secSel.innerHTML = ''; pressSel.innerHTML=''; commSel.innerHTML=''; dateSel.innerHTML='';
  opt(secSel, '', '전체 섹션');
  opt(pressSel, '', '전체 매체');
  opt(commSel, '', '전체 품목');
  opt(dateSel, '', '전체 날짜');

  const secs = uniq(DATA.map(x => x.section));
  const press = uniq(DATA.map(x => x.press_group));
  const comms = uniq(DATA.flatMap(x => (x.commodities||[])));
  const dates = uniq(DATA.map(x => x.date)).sort().reverse();

  secs.forEach(s => opt(secSel, s, s));
  press.forEach(p => opt(pressSel, p, p));
  comms.forEach(c => opt(commSel, c, c));
  dates.slice(0, 90).forEach(d => opt(dateSel, d, d));
}}

function matches(item) {{
  const q = (qInput.value||'').trim().toLowerCase();
  const sec = secSel.value;
  const pg = pressSel.value;
  const comm = commSel.value;
  const dt = dateSel.value;

  if (sec && item.section !== sec) return false;
  if (pg && item.press_group !== pg) return false;
  if (dt && item.date !== dt) return false;
  if (comm) {{
    const cs = item.commodities || [];
    if (!cs.includes(comm)) return false;
  }}
  if (!q) return true;

  const hay = (item.title + ' ' + (item.summary||'') + ' ' + (item.tags||[]).join(' ') + ' ' + (item.commodities||[]).join(' ')).toLowerCase();
  return hay.includes(q);
}}

function render() {{
  const filtered = DATA.filter(matches)
    .sort((a,b)=> (b.score||0) - (a.score||0));

  statEl.textContent = `총 ${DATA.length}건 · 필터 결과 ${filtered.length}건`;

  listEl.innerHTML = '';
  filtered.slice(0, 220).forEach(it => {{
    const url = it.url;
    const badges = [
      it.urgent ? '<span class="badge urgent">🚨긴급</span>' : '',
      it.reused ? `<span class="badge reused">전날</span>` : ''
    ].join('');
    const tags = (it.tags||[]).slice(0,6).map(t=>`<span class="tag">${{t}}</span>`).join('');
    const comms = (it.commodities||[]).slice(0,5).join(', ');
    const el = document.createElement('div');
    el.className = 'item';
    el.innerHTML = `
      <div class="top">
        ${{badges}}
        <span><b>${{it.section}}</b></span><span style="opacity:.6">·</span>
        <span>${{it.press}}</span><span style="opacity:.6">·</span>
        <span>${{it.date}}</span><span style="opacity:.6">·</span>
        <span>score ${{(it.score||0).toFixed(1)}}</span>
      </div>
      <a class="title" href="${{url}}" target="_blank" rel="noopener">${{it.title}}</a>
      <div class="meta">${{(it.summary||'').slice(0, 160)}}</div>
      <div class="tags">${{tags}}</div>
      <div class="meta" style="margin-top:8px">품목: ${{comms || '-'}}</div>
      <div class="meta" style="margin-top:6px"><a href="${{sitePath}}archive/${{it.date}}.html">해당 날짜 브리핑 보기</a></div>
    `;
    listEl.appendChild(el);
  }});
}}

async function init() {{
  const res = await fetch(sitePath + 'search_index.json', {{cache:'no-store'}});
  const obj = await res.json();
  DATA = (obj.items||[]);
  fillSelects();
  render();
}}

[qInput, secSel, pressSel, commSel, dateSel].forEach(el => el.addEventListener('input', render));
document.getElementById('reset').addEventListener('click', ()=> {{
  qInput.value=''; secSel.value=''; pressSel.value=''; commSel.value=''; dateSel.value='';
  render();
}});

init();
</script>
</body>
</html>
"""

def build_site_path(repo: str) -> str:
    # project pages: /REPO/
    if not repo or "/" not in repo:
        return "/"
    owner, name = repo.split("/", 1)
    if name.lower().endswith(".github.io"):
        return "/"
    return f"/{name}/"

# -----------------------------
# GitHub Content API (upload/download)
# -----------------------------
def gh_api_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

def github_get_file(repo: str, path: str, token: str, ref: str = "main") -> str:
    """Return decoded content string or ''"""
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        r = SESSION.get(url, headers=gh_api_headers(token), params={"ref": ref}, timeout=20)
        if r.status_code == 404:
            return ""
        r.raise_for_status()
        j = r.json()
        if isinstance(j, dict) and j.get("content"):
            raw = base64.b64decode(j["content"]).decode("utf-8", errors="replace")
            return raw
        return ""
    except Exception:
        return ""

def github_put_file(repo: str, path: str, token: str, content_text: str, message: str, branch: str = "main") -> None:
    """Create/update a file in repo via Contents API."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    # get sha if exists
    sha = None
    r0 = SESSION.get(url, headers=gh_api_headers(token), params={"ref": branch}, timeout=20)
    if r0.ok:
        try:
            sha = r0.json().get("sha")
        except Exception:
            sha = None
    payload = {
        "message": message,
        "content": base64.b64encode(content_text.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    r = SESSION.put(url, headers=gh_api_headers(token), json=payload, timeout=30)
    r.raise_for_status()

# -----------------------------
# Search index builder
# -----------------------------
def load_manifest() -> dict:
    if not REPO or not GH_TOKEN:
        return {"dates": []}
    raw = github_get_file(REPO, MANIFEST_PATH, GH_TOKEN, ref=BRANCH)
    if not raw:
        return {"dates": []}
    try:
        return json.loads(raw)
    except Exception:
        return {"dates": []}

def update_manifest(report_date: str) -> dict:
    mf = load_manifest()
    dates = mf.get("dates", [])
    if report_date not in dates:
        dates.append(report_date)
    dates = sorted(set(dates), reverse=True)
    mf["dates"] = dates
    mf["updated_at"] = now_kst().isoformat()
    return mf

def update_search_index(report_date: str, by_section: dict[str, list[Article]], site_path: str) -> dict:
    cur = load_search_index_from_repo()
    items = cur.get("items", []) if isinstance(cur, dict) else []
    # drop same date
    items = [it for it in items if it.get("date") != report_date]

    new_items = []
    for sec in SECTIONS:
        sk = sec["key"]
        for a in by_section.get(sk, []):
            url = a.originallink or a.link
            new_items.append({
                "date": report_date,
                "section": sk,
                "title": a.title,
                "url": url,
                "press": a.press,
                "domain": a.domain,
                "score": a.score,
                "summary": a.summary or a.description,
                "tags": a.tags,
                "commodities": a.commodities,
                "press_group": a.press_group,
                "urgent": a.urgent,
                "reused": a.reused,
            })

    out = {
        "version": 2,
        "updated_at": now_kst().isoformat(),
        "items": (items + new_items),
    }
    # keep recent only
    out["items"] = sorted(out["items"], key=lambda x: (x.get("date", ""), float(x.get("score", 0.0))), reverse=True)[:6000]
    return out

# -----------------------------
# Main collection
# -----------------------------
def collect_section(section_key: str, start_kst: datetime, end_kst: datetime) -> list[Article]:
    queries = build_section_queries(section_key)
    dedupe_url = set()
    dedupe_key = set()
    out: list[Article] = []

    # 1) Naver
    for q in queries:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            break
        js = naver_search(q, display=min(100, MAX_ITEMS_PER_QUERY), start=1)
        items = js.get("items", []) or []
        for it in items:
            title, desc, link, origin, pub = parse_naver_item(it)
            if not title:
                continue
            # window filter
            if pub < start_kst or pub > end_kst:
                continue
            dom = normalize_host(origin or link)
            if not is_relevant(section_key, title, desc, dom):
                continue

            canon = canonicalize_url(origin or link)
            tkey = norm_title_key(title)
            if canon in dedupe_url or tkey in dedupe_key:
                continue
            dedupe_url.add(canon)
            dedupe_key.add(tkey)

            press = press_from_domain(dom)
            tags, comms, urgent = analyze_signals(title, desc, section_key)
            pg = compute_press_group(press, dom)
            s = score_article(section_key, title, desc, press, dom, pub)

            out.append(Article(
                section=section_key,
                title=title,
                description=desc,
                link=link,
                originallink=origin or link,
                pub_dt_kst=pub,
                domain=dom,
                press=press,
                canon_url=canon,
                title_key=tkey,
                norm_key=make_norm_key(canon, press, tkey),
                score=s,
                summary="",  # later fill
                tags=tags,
                commodities=comms,
                press_group=pg,
                urgent=urgent,
            ))

    # 2) RSS (공식 소스 우선 보강)
    for rss_url in WHITELIST_RSS_URLS:
        rss_items = fetch_rss(rss_url)
        for it in rss_items:
            title = it.get("title", "")
            desc = it.get("description", "")
            origin = it.get("originallink", "")
            pub = it.get("pub_dt_kst") or now_kst()
            if not title or not origin:
                continue
            if pub < start_kst or pub > end_kst:
                continue
            dom = normalize_host(origin)
            if not is_relevant(section_key, title, desc, dom):
                continue
            canon = canonicalize_url(origin)
            tkey = norm_title_key(title)
            if canon in dedupe_url or tkey in dedupe_key:
                continue
            dedupe_url.add(canon)
            dedupe_key.add(tkey)

            press = press_from_domain(dom)
            tags, comms, urgent = analyze_signals(title, desc, section_key)
            pg = compute_press_group(press, dom)
            s = score_article(section_key, title, desc, press, dom, pub)

            out.append(Article(
                section=section_key,
                title=title,
                description=desc,
                link=origin,
                originallink=origin,
                pub_dt_kst=pub,
                domain=dom,
                press=press,
                canon_url=canon,
                title_key=tkey,
                norm_key=make_norm_key(canon, press, tkey),
                score=s,
                summary="",
                tags=tags,
                commodities=comms,
                press_group=pg,
                urgent=urgent,
            ))

    # 정렬
    out.sort(key=lambda a: (a.score, a.pub_dt_kst), reverse=True)
    return out

def fill_summaries(by_section: dict[str, list[Article]]) -> None:
    # 비용 없는 간단 요약(원문 설명 or 제목)
    for sec in SECTIONS:
        for a in by_section.get(sec["key"], []):
            if a.summary:
                continue
            a.summary = (a.description or a.title).strip()

# -----------------------------
# Kakao (optional)
# -----------------------------
KAKAO_REST_API_KEY = (os.getenv("KAKAO_REST_API_KEY") or "").strip()
KAKAO_REFRESH_TOKEN = (os.getenv("KAKAO_REFRESH_TOKEN") or "").strip()
KAKAO_REDIRECT_URI = (os.getenv("KAKAO_REDIRECT_URI") or "").strip()

def kakao_refresh_access_token() -> str:
    if not (KAKAO_REST_API_KEY and KAKAO_REFRESH_TOKEN):
        return ""
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN,
    }
    if KAKAO_REDIRECT_URI:
        data["redirect_uri"] = KAKAO_REDIRECT_URI
    r = SESSION.post(url, data=data, timeout=20)
    if not r.ok:
        return ""
    return (r.json().get("access_token") or "").strip()

def kakao_send_memo(text: str) -> bool:
    token = kakao_refresh_access_token()
    if not token:
        return False
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {token}"}
    template = {
        "object_type": "text",
        "text": text[:990],
        "link": {"web_url": "https://example.com", "mobile_web_url": "https://example.com"},
        "button_title": "브리핑 보기",
    }
    r = SESSION.post(url, headers=headers, data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=20)
    return r.ok

def build_kakao_text(report_date: str, site_url: str, by_section: dict[str, list[Article]]) -> str:
    lines = [f"📌 원예(과수·화훼) 데일리 브리핑 {report_date}", f"🔗 {site_url}", ""]
    for sec in SECTIONS:
        sk = sec["key"]
        lst = by_section.get(sk, [])
        if not lst:
            continue
        lines.append(f"■ {sec['title']} (상위 2)")
        for a in lst[:2]:
            u = a.originallink or a.link
            badge = "🚨" if a.urgent else ""
            why = ", ".join([t for t in a.tags if t in ("가격", "물량/수급", "정책", "유통", "병해/방제", "수치", "기간")][:3])
            why_txt = f" [{why}]" if why else ""
            lines.append(f"- {badge}{a.title}{why_txt}")
            lines.append(f"  · {a.press} · {u}")
        lines.append("")
    return "\n".join(lines).strip()

# -----------------------------
# Main
# -----------------------------
def main():
    if not REPO:
        print("[ERROR] REPO_SLUG/GITHUB_REPOSITORY not set.")
        return
    if not DRY_RUN and not GH_TOKEN:
        print("[ERROR] GITHUB_TOKEN/GH_TOKEN not set.")
        return

    start_kst, end_kst, report_date = compute_window()
    site_path = build_site_path(REPO)
    site_url = f"https://{REPO.split('/')[0]}.github.io{site_path}archive/{report_date}.html"

    print(f"[INFO] repo={REPO} branch={BRANCH}")
    print(f"[INFO] window={start_kst.isoformat()} ~ {end_kst.isoformat()} report_date={report_date}")
    print(f"[INFO] strict_horti={STRICT_HORTI_ONLY} event_dedupe={ENABLE_EVENT_DEDUPE} min_per_section={MIN_PER_SECTION}")

    # Collect
    by_section: dict[str, list[Article]] = {}
    for sec in SECTIONS:
        sk = sec["key"]
        cands = collect_section(sk, start_kst, end_kst)
        picked = select_top(sk, cands, max_n=8)
        by_section[sk] = picked
        print(f"[INFO] {sk}: candidates={len(cands)} selected={len(picked)}")

    # Fallback (전날)
    apply_prev_day_fallback(by_section, report_date)

    # Fill summaries
    fill_summaries(by_section)

    # Render archive + index + update manifest + search index
    archive_html = render_archive(report_date, start_kst, end_kst, by_section)
    index_html = render_index_html(site_path)

    manifest = update_manifest(report_date)
    search_index = update_search_index(report_date, by_section, site_path)

    if DRY_RUN:
        print("[DRY_RUN] skip GitHub upload & Kakao")
        print("[DRY_RUN] archive length:", len(archive_html))
        return

    # Upload files to GitHub
    github_put_file(REPO, f"{ARCHIVE_DIR}/{report_date}.html", GH_TOKEN, archive_html,
                    message=f"chore: update archive {report_date}", branch=BRANCH)
    github_put_file(REPO, INDEX_HTML_PATH, GH_TOKEN, index_html,
                    message="chore: update index.html", branch=BRANCH)
    github_put_file(REPO, MANIFEST_PATH, GH_TOKEN, json.dumps(manifest, ensure_ascii=False, indent=2),
                    message="chore: update manifest", branch=BRANCH)
    github_put_file(REPO, SEARCH_INDEX_PATH, GH_TOKEN, json.dumps(search_index, ensure_ascii=False),
                    message="chore: update search index", branch=BRANCH)

    print("[INFO] GitHub upload done.")

    # Optional Kakao
    if KAKAO_REST_API_KEY and KAKAO_REFRESH_TOKEN:
        msg = build_kakao_text(report_date, site_url, by_section)
        ok = kakao_send_memo(msg)
        print("[INFO] Kakao sent:", ok)
    else:
        print("[INFO] Kakao skipped (no keys).")

if __name__ == "__main__":
    main()
