# -*- coding: utf-8 -*-
"""
agri-news-brief main.py (production)

✅ 이번 수정 반영 (요청 1~6)

1) 브리핑에서도 "핵심 뉴스 2개"가 명확히 보이도록 설계
   - 각 섹션: 상단 2개를 '핵심' 배지로 강조 (접어두지 않고 전부 노출)
   - 카톡 메시지도 동일 로직(섹션 상단 2개) 사용 -> "브리핑 핵심 2"와 일치

2) 아주뉴스, 스포츠서울 등 매체명이 영문으로 표기되는 문제 개선
   - PRESS_HOST_MAP에 ajunews.com/ajunews.co.kr 등, sportsseoul.co.kr 추가
   - suffix 매칭 + 2단계 TLD 처리 유지

3) 상단 섹션 클릭 시 위치가 중간으로 가는 문제 개선
   - html { scroll-padding-top } + .sec { scroll-margin-top } 적용

4) "최신/아카이브"에서 최신 브리핑/날짜별 아카이브 클릭 시 404 문제 해결 + 가독성 개선
   - GitHub Pages 프로젝트 사이트 경로(/REPO/)를 고려한 '절대 경로' 링크 생성
   - 아카이브는 카드형(날짜 + 요일) 리스트로 표시

기존 반영 유지:
- Kakao web_url 안전장치(빈값/상대경로/비 http(s)/gist 차단) + 로그
- (CO) 언론사명 추출 버그 수정
- 중앙/주요매체 우선 점수/정렬
- supply(품목) vs dist(도매시장) 분리
- 글로벌 리테일 시위/보이콧 오탐 차단
"""

import os
import re
import json
import base64
import html
import logging
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, date, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
import threading


# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agri-brief")

# -----------------------------
# HTTP session
# -----------------------------
SESSION = requests.Session()

# -----------------------------
# Config
# -----------------------------
KST = timezone(timedelta(hours=9))
REPORT_HOUR_KST = int(os.getenv("REPORT_HOUR_KST", os.getenv("RUN_HOUR_KST", "7")))
MAX_PER_SECTION = int(os.getenv("MAX_PER_SECTION", os.getenv("MAX_ARTICLES_PER_SECTION", "5")))

STATE_FILE_PATH = ".agri_state.json"
ARCHIVE_MANIFEST_PATH = ".agri_archive.json"
DOCS_INDEX_PATH = "docs/index.html"
DOCS_ARCHIVE_DIR = "docs/archive"

DEFAULT_REPO = (os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY") or "").strip()
GH_TOKEN = (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()

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

def _naver_throttle():
    """전역 최소 간격을 보장(멀티스레드 안전)."""
    global _NAVER_LAST_CALL
    with _NAVER_LOCK:
        now = time.monotonic()
        wait = NAVER_MIN_INTERVAL_SEC - (now - _NAVER_LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        _NAVER_LAST_CALL = time.monotonic()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2").strip()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "").strip()
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "").strip()
KAKAO_INCLUDE_LINK_IN_TEXT = os.getenv("KAKAO_INCLUDE_LINK_IN_TEXT", "false").strip().lower() in ("1", "true", "yes")

FORCE_REPORT_DATE = os.getenv("FORCE_REPORT_DATE", "").strip()  # YYYY-MM-DD
FORCE_RUN_ANYDAY = os.getenv("FORCE_RUN_ANYDAY", "false").strip().lower() in ("1", "true", "yes")
FORCE_END_NOW = os.getenv("FORCE_END_NOW", "false").strip().lower() in ("1", "true", "yes")
STRICT_KAKAO_LINK_CHECK = os.getenv("STRICT_KAKAO_LINK_CHECK", "false").strip().lower() in ("1", "true", "yes")

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


# -----------------------------
# Sections
# -----------------------------
SECTIONS = [
    {
        "key": "supply",
        "title": "품목 및 수급 동향",
        "color": "#0f766e",
        "queries": [
            "사과 작황", "사과 생산량", "사과 저장", "사과 수급", "사과 가격",
            "배 작황", "배 생산량", "배 저장", "배 수급", "배 가격",
            "감귤 작황", "감귤 수급", "만감류 출하", "한라봉 출하", "레드향 출하", "천혜향 출하",
            "샤인머스캣 작황", "샤인머스캣 수급", "포도 작황", "포도 수급",
            "오이 작황", "오이 수급", "풋고추 작황", "풋고추 수급",
            "쌀 산지 가격", "비축미 동향",
        ],
        "must_terms": ["작황", "생산", "재배", "수확", "면적", "저장", "출하", "수급", "가격", "시세"],
    },
    {
        "key": "policy",
        "title": "주요 이슈 및 정책",
        "color": "#1d4ed8",
        "queries": [
            "농식품부 정책브리핑", "농식품부 보도자료 농산물", "정책브리핑 농축수산물",
            "농축수산물 할인지원", "성수품 가격 안정 대책", "할당관세 과일 검역",
            "원산지 단속 농산물", "온라인 도매시장 농식품부",
        ],
        "must_terms": ["정책", "대책", "지원", "할인", "할당관세", "검역", "보도자료", "브리핑", "온라인 도매시장", "원산지"],
    },
    {
        "key": "dist",
        "title": "유통 및 현장 (도매시장/APC/수출)",
        "color": "#6d28d9",
        "queries": [
            "가락시장 청과 경락", "도매시장 경락가", "도매시장 반입량", "도매시장 수급",
            "공판장 경매", "경락가 상승", "경락가 하락",
            "APC 선별", "CA저장 APC", "산지유통센터 APC",
            "농산물 수출 실적", "과일 수출 실적", "검역 수출 농산물",
            "부정유통 단속 농산물", "원산지 표시 단속",
        ],
        "must_terms": ["가락시장", "도매시장", "공판장", "경락", "경매", "반입", "APC", "선별", "CA저장", "수출", "검역", "원산지", "부정유통"],
    },
    {
        "key": "pest",
        "title": "병해충 및 방제",
        "color": "#b45309",
        "queries": [
            "과수화상병 방제", "탄저병 방제", "월동 해충 방제",
            "냉해 동해 과수 피해", "병해충 예찰 방제",
        ],
        "must_terms": ["방제", "병해충", "약제", "살포", "예찰", "과수화상병", "탄저병", "냉해", "동해", "월동"],
    },
]


# -----------------------------
# Topic diversity
# -----------------------------
COMMODITY_TOPICS = [
    ("사과", ["사과"]),
    ("배", ["배 ", "배(과일)", "배 가격", "배 시세"]),
    ("감귤/만감", ["감귤", "만감", "한라봉", "레드향", "천혜향"]),
    ("감/곶감", ["단감", "떫은감", "곶감", "감 "]),
    ("포도", ["포도", "샤인머스캣"]),
    ("오이", ["오이"]),
    ("고추", ["고추", "풋고추", "청양"]),
    ("쌀", ["쌀", "비축미"]),
    ("도매시장", ["가락시장", "도매시장", "공판장", "경락", "경매", "반입"]),
    ("수출", ["수출", "검역", "통관"]),
    ("정책", ["정책", "대책", "브리핑", "보도자료", "할당관세", "할인지원", "원산지"]),
    ("병해충", ["병해충", "방제", "약제", "예찰", "과수화상병", "탄저병", "냉해", "동해"]),
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

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url: str) -> str:
    try:
        u = urlparse(url)
        return (u.hostname or "").lower()
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

def extract_topic(title: str, desc: str) -> str:
    text = (title + " " + desc).lower()
    for topic, words in COMMODITY_TOPICS:
        for w in words:
            if w.lower() in text:
                return topic
    return "기타"

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


def keyword_strength(text: str, section_conf: dict) -> int:
    """섹션 관련 키워드 강도(정수).
    - 섹션 must_terms 포함 여부(1차) + 농산물 강키워드(AGRI_STRONG_TERMS) 기반 점수
    - dist/pest에서 낚시성 기사 제거에 사용
    """
    if not section_conf:
        return agri_strength_score(text)
    must = [t.lower() for t in section_conf.get("must_terms", [])]
    return count_any(text, must) + agri_strength_score(text)

def off_topic_penalty(text: str) -> int:
    return count_any(text, OFFTOPIC_HINTS)

def korea_context_score(text: str) -> int:
    return count_any(text, KOREA_CONTEXT_HINTS)

def global_retail_protest_penalty(text: str) -> int:
    return count_any(text.lower(), GLOBAL_RETAIL_PROTEST_HINTS)


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

    # ✅ (추가) 아주뉴스/아주경제
    "ajunews.com": "아주경제",
    "ajunews.co.kr": "아주경제",
    "ajunews.kr": "아주경제",

    # ✅ (추가) 스포츠서울 (co.kr 케이스 포함)
    "sportsseoul.com": "스포츠서울",
    "sportsseoul.co.kr": "스포츠서울",

    # 요청 매체(영문→한글)
    "mediajeju.com": "미디어제주",
    "pointdaily.co.kr": "포인트데일리",
    "metroseoul.co.kr": "메트로신문",

    # 정책기관/연구기관
    "korea.kr": "정책브리핑",
    "mafra.go.kr": "농식품부",
    "at.or.kr": "aT",
    "naqs.go.kr": "농관원",
    "krei.re.kr": "KREI",
}

ABBR_MAP = {
    "mk": "매일경제",
    "mt": "머니투데이",
    "mbn": "MBN",
    "ytn": "YTN",
    "jtbc": "JTBC",
    "kbs": "KBS",
    "mbc": "MBC",
    "sbs": "SBS",
    "ajunews": "아주경제",
    "sportsseoul": "스포츠서울",
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
    return brand.upper() if len(brand) <= 6 else brand


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
    if p and (re.search(r"(일보|신문)$", p) or ("방송" in p and p not in TOP_TIER_PRESS)):
        return 2

    # UGC/커뮤니티성
    if any(h in d for h in _UGC_HOST_HINTS):
        return 1

    return 1
def _sort_key_major_first(a: Article):
    return (press_priority(a.press, a.domain), a.score, a.pub_dt_kst)


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
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "agri-news-brief-bot",
    }

def github_get_file(repo: str, path: str, token: str, ref: str = "main"):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    r = SESSION.get(url, headers=github_api_headers(token), params={"ref": ref}, timeout=30)
    if r.status_code == 404:
        return None, None
    if not r.ok:
        log.error("[GitHub GET ERROR] %s", r.text)
        r.raise_for_status()
    j = r.json()
    content_b64 = j.get("content", "")
    sha = j.get("sha")
    raw = base64.b64decode(content_b64).decode("utf-8", errors="replace") if content_b64 else ""
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
    r = SESSION.put(url, headers=github_api_headers(token), json=payload, timeout=30)
    if not r.ok:
        log.error("[GitHub PUT ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()

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
    - report_date는 이번 실행에서 생성/업로드하므로 존재한다고 간주.
    """
    from concurrent.futures import ThreadPoolExecutor

    head = dates_desc[:verify_n]
    to_check = [d for d in head if d != report_date]

    exists: dict[str, bool] = {}

    def _check(d: str) -> bool:
        try:
            return archive_page_exists(repo, token, d)
        except Exception as e:
            log.warning("[WARN] archive exists check failed for %s: %s", d, e)
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

def save_state(repo: str, token: str, last_end: datetime):
    payload = {"last_end_iso": last_end.isoformat()}
    _raw_old, sha = github_get_file(repo, STATE_FILE_PATH, token, ref="main")
    github_put_file(repo, STATE_FILE_PATH, json.dumps(payload, ensure_ascii=False, indent=2), token,
                    f"Update state {last_end.date().isoformat()}", sha=sha, branch="main")

def _normalize_manifest(obj):
    if obj is None:
        return {"dates": []}
    if isinstance(obj, list):
        return {"dates": [str(x) for x in obj if str(x).strip()]}
    if isinstance(obj, dict):
        dates = obj.get("dates", [])
        if isinstance(dates, list):
            return {"dates": [str(x) for x in dates if str(x).strip()]}
        if isinstance(dates, str) and dates.strip():
            return {"dates": [dates.strip()]}
        return {"dates": []}
    return {"dates": []}

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
    github_put_file(repo, ARCHIVE_MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=2), token,
                    "Update archive manifest", sha=sha, branch="main")


# -----------------------------
# Naver News search
# -----------------------------
def naver_news_search(query: str, display: int = 40, start: int = 1, sort: str = "date"):
    """Naver News 검색 (429 속도제한 대응: throttle + retry + backoff).
    - 429/에러코드 012는 일정 시간 대기 후 재시도
    - 계속 실패하면 빈 결과(items=[])로 반환해 전체 파이프라인이 죽지 않게 함
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set")
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": query, "display": display, "start": start, "sort": sort}

    last_err = None
    for attempt in range(max(1, NAVER_MAX_RETRIES)):
        try:
            _naver_throttle()
            r = SESSION.get(url, headers=headers, params=params, timeout=25)

            # JSON 파싱 시도 (에러 본문에 errorCode가 오는 경우 대응)
            data = None
            try:
                data = r.json()
            except Exception:
                data = None

            # 속도 제한(429) 또는 Naver 에러코드 012
            is_rate = (r.status_code == 429) or (isinstance(data, dict) and str(data.get("errorCode", "")) == "012")

            if r.ok and not is_rate:
                return data if isinstance(data, dict) else {"items": []}

            if is_rate:
                # Retry-After 헤더가 있으면 우선 사용
                ra = 0.0
                try:
                    ra = float(r.headers.get("Retry-After", "0") or 0)
                except Exception:
                    ra = 0.0
                backoff = ra if ra > 0 else min(NAVER_BACKOFF_MAX_SEC, (1.0 * (2 ** attempt)) + random.uniform(0.0, 0.4))
                msg = None
                if isinstance(data, dict):
                    msg = data.get("errorMessage") or data.get("message")
                log.warning("[NAVER] rate-limited (attempt %d/%d). sleep %.1fs. %s", attempt+1, NAVER_MAX_RETRIES, backoff, (msg or ""))
                time.sleep(backoff)
                continue

            # 그 외 오류는 즉시 raise (호출부에서 처리)
            if not r.ok:
                log.error("[NAVER ERROR] %s", r.text)
                r.raise_for_status()

            # r.ok인데도 error 구조가 이상한 경우
            return {"items": []}

        except Exception as e:
            last_err = e
            # 네트워크/일시오류는 backoff 후 재시도
            backoff = min(NAVER_BACKOFF_MAX_SEC, (1.0 * (2 ** attempt)) + random.uniform(0.0, 0.4))
            log.warning("[NAVER] transient error (attempt %d/%d): %s -> sleep %.1fs", attempt+1, NAVER_MAX_RETRIES, e, backoff)
            time.sleep(backoff)

    # 모두 실패: 빈 결과로 반환 (파이프라인 유지)
    log.error("[NAVER] giving up after retries: query=%s (last=%s)", query, last_err)
    return {"items": []}


# -----------------------------
# Relevance / scoring
# -----------------------------
def section_must_terms_ok(text: str, must_terms) -> bool:
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
    "사과", "배", "감귤", "포도", "딸기", "복숭아", "감자", "고추", "오이", "양파", "마늘", "벼", "쌀",
]
PEST_OFFTOPIC_TERMS = [
    # 사람/도시 방역성 기사(농업과 무관한 경우 차단)
    "코로나", "독감", "감염병", "방역", "방역당국", "모기", "진드기", "말라리아", "뎅기",
    # 생활 해충/건물 해충
    "바퀴", "흰개미", "개미",
]
def is_relevant(title: str, desc: str, dom: str, section_conf: dict, press: str) -> bool:
    """섹션별 1차 필터(관련도/노이즈 컷)."""
    text = (title + " " + desc).lower()
    dom = (dom or "").lower().strip()

    # 공통 제외(광고/구인/부동산 등)
    if any(k in text for k in BAN_KWS):
        return False

    # 정책 섹션만 정책기관/공공 도메인 허용(단, 방제(pest)는 지방 이슈가 많아 예외 허용)
    # ✅ (5) pest 섹션은 지자체/연구기관(.go.kr/.re.kr) 기사도 허용
    if (
        dom in POLICY_DOMAINS
        or dom in ALLOWED_GO_KR
        or dom.endswith(".re.kr")
        or dom.endswith(".go.kr")
    ) and section_conf["key"] not in ("policy", "pest"):
        return False

    # 섹션 must-term 통과 여부
    if not section_must_terms_ok(text, section_conf["must_terms"]):
        # policy는 도메인 override가 있음
        if not policy_domain_override(dom, text):
            return False

    # 정책 섹션: 지방 행사성/지역 단신을 강하게 배제(주요 매체는 일부 허용)
    if section_conf["key"] == "policy":
        is_major = press_priority(press, dom) >= 2
        if (not is_major) and _LOCAL_GEO_PATTERN.search(title):
            return False

    # 병해충/방제 섹션 정교화: 농업 맥락 없는 "방역/생활해충" 오탐을 강하게 제거
    if section_conf["key"] == "pest":
        # (A) 농업 맥락 단어가 최소 1개는 있어야 함
        if not has_any(text, [t.lower() for t in PEST_AGRI_CONTEXT_TERMS]):
            return False
        # (B) 병해충/방제 핵심 단어(또는 냉해/동해 등 과수 피해) 중 하나는 있어야 함
        strict_hit = has_any(text, [t.lower() for t in PEST_STRICT_TERMS])
        weather_hit = has_any(text, [t.lower() for t in PEST_WEATHER_TERMS])
        if not strict_hit and not weather_hit:
            return False
        # (C) 사람/도시 방역성 기사 차단(단, 농작물 맥락이 강하면 일부 허용)
        if has_any(text, [t.lower() for t in PEST_OFFTOPIC_TERMS]) and count_any(text, [t.lower() for t in ["농작물","과수","과원","재배","농가"]]) == 0:
            return False

    # 섹션별 키워드 강도(낚시성/약한 기사 컷)
    strength = keyword_strength(text, section_conf)
    if section_conf["key"] == "pest" and strength < 3:
        return False

    # 유통 섹션은 MUST/강도 기준을 좀 더 엄격하게 (낚시성/인물기사 방지)
    if section_conf["key"] == "dist" and strength < 4:
        return False

    return True


def compute_rank_score(title: str, desc: str, dom: str, pub_dt_kst: datetime, section_conf: dict, press: str) -> float:
    text = (title + " " + desc).lower()
    strength = agri_strength_score(text)
    korea = korea_context_score(text)
    offp = off_topic_penalty(text)
    retail_pen = global_retail_protest_penalty(text)

    score = 0.0
    score += strength * 2.2
    score += korea * 0.9
    score -= offp * 2.8
    score -= retail_pen * 2.0

    pr = press_priority(press, dom)
    if pr == 3:
        score += 10.0
    elif pr == 2:
        score += 4.5

    # 정책 섹션: 지방 단신 감점
    if section_conf["key"] == "policy" and _LOCAL_GEO_PATTERN.search(title) and pr < 2:
        score -= 5.0

    # ✅ (6) 유통(dist): '현장/유통'과 무관한 인물·역사·문화성 기사(예: 제주 4.3 등) 상단 배치 방지
    if section_conf["key"] == "dist":
        dist_strong_terms = [
            "가락시장", "도매시장", "공판장", "경락", "경락가", "경매", "반입", "반출",
            "중도매인", "시장도매인", "유통센터", "물류", "창고",
            "apc", "선별", "ca저장", "저장", "저온",
            "원산지", "부정유통", "단속", "검역", "통관",
        ] + [t.lower() for t in WHOLESALE_MARKET_TERMS]

        dist_noise_terms = [
            "4.3", "제주4.3", "추모", "희생", "유족", "영령", "기념", "기념식", "기념관",
            "문화", "공연", "전시", "축제", "문학", "소설", "시집", "시인", "작가",
            "영화", "드라마", "다큐", "연극",
        ]

        strong_hits = sum(1 for t in dist_strong_terms if t in text)
        noise_hits = sum(1 for t in dist_noise_terms if t in text)

        # 핵심 유통 인프라/현장 단어가 없으면 상단 노출을 억제
        if strong_hits >= 2:
            score += 2.5
        elif strong_hits == 1:
            score += 0.8
        else:
            score -= 2.5

        # 문화/역사성 단어가 섞이고(노이즈), 유통 핵심 단어가 없으면 추가 감점
        if noise_hits and strong_hits == 0:
            score -= 6.0 + (noise_hits * 1.5)

    # 최신성(24시간 내 가산)
    age_hours = max(0.0, (datetime.now(tz=KST) - pub_dt_kst).total_seconds() / 3600.0)
    score += max(0.0, 24.0 - min(age_hours, 24.0)) * 0.06

    # 섹션 must-term이 제목에 직접 들어가면 약간 가산
    for t in section_conf["must_terms"]:
        if t.lower() in title.lower():
            score += 0.7

    # 정책 섹션: 농식품부/정책브리핑 가산
    if section_conf["key"] == "policy":
        if "농식품부" in title or dom == "mafra.go.kr":
            score += 3.0
        if "정책브리핑" in title or dom == "korea.kr":
            score += 1.5

    return score


# -----------------------------
# Selection thresholds (섹션별 최소 점수)
# - 동적 threshold(best-8)와 함께 사용
# - 값이 높을수록 '정말 핵심'만 남김
# -----------------------------
BASE_MIN_SCORE = {
    # 품목/수급
        "supply": 7.5,
    # 정책/제도(공식기관 우선)
        "policy": 7.5,
    # 유통/현장(시장·유통 인프라 중심)
    "dist": 7.0,
    # 병해충/방제(지방 이슈가 많아 상대적으로 완화)
    "pest": 6.0,
}

def _dynamic_threshold(candidates: list[Article], section_key: str) -> float:
    if not candidates:
        return 10**9
    best = max(a.score for a in candidates)
    return max(BASE_MIN_SCORE.get(section_key, 6.5), best - 8.0)



# -----------------------------
# Headline(core2) gate: "섹션 타이틀" 급 기사만 코어로 올리기
# -----------------------------
_HEADLINE_STOPWORDS = [
    "칼럼", "기고", "사설", "인터뷰", "포토", "사진", "영상", "만평", "연재",
    "기획", "탐방", "인물", "추모", "기념", "축제", "전시", "공연", "문학", "소설", "시",
]

def _token_set(s: str) -> set[str]:
    s = (s or "").lower()
    toks = re.findall(r"[0-9a-z가-힣]{2,}", s)
    return {t for t in toks if t not in ("기사", "뉴스", "농산물", "농업", "정부", "지자체")}

def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def _is_policy_official(a: "Article") -> bool:
    dom = normalize_host(a.domain)
    p = (a.press or "").strip()
    return (dom in ("mafra.go.kr", "korea.kr") or p in ("농식품부", "정책브리핑"))

def _headline_gate(a: "Article", section_key: str) -> bool:
    """코어(핵심2)로 올릴 자격이 있는지(섹션별)."""
    title = (a.title or "").lower()
    text = (a.title + " " + a.description).lower()

    # 공통: 칼럼/기고/인물/행사성은 코어에서 제외
    if has_any(title, [w.lower() for w in _HEADLINE_STOPWORDS]):
        return False

    if section_key == "supply":
        core_terms = ["가격", "시세", "수급", "작황", "생산", "출하", "물량", "재고", "저장"]
        crop_terms = ["사과", "배", "감귤", "한라봉", "레드향", "천혜향", "포도", "샤인머스캣", "오이", "고추", "쌀", "비축미"]
        return has_any(text, core_terms) and has_any(text, crop_terms)

    if section_key == "policy":
        if _is_policy_official(a):
            return True
        action_terms = ["대책", "지원", "할인", "할당관세", "검역", "고시", "개정", "발표", "추진", "확대", "연장", "단속", "브리핑", "보도자료", "예산"]
        ctx_terms = ["농산물", "농업", "농식품", "과일", "채소", "수급", "가격", "유통", "원산지", "도매시장", "수출", "검역"]
        return has_any(text, action_terms) and has_any(text, ctx_terms)

    if section_key == "dist":
        dist_terms = ["가락시장", "도매시장", "공판장", "경락", "경락가", "경매", "반입", "중도매인", "시장도매인", "apc", "선별", "ca저장", "물류", "수출", "검역", "통관", "원산지"]
        return count_any(text, dist_terms) >= 2

    if section_key == "pest":
        # 농업 맥락 + 병해충/방제(또는 냉해/동해 피해) 가시적이어야 코어
        if not has_any(text, [t.lower() for t in PEST_AGRI_CONTEXT_TERMS]):
            return False
        strict_hits = count_any(text, [t.lower() for t in PEST_STRICT_TERMS])
        weather_hits = count_any(text, [t.lower() for t in PEST_WEATHER_TERMS])
        return (strict_hits >= 2) or (strict_hits >= 1 and weather_hits >= 1) or (weather_hits >= 2)

    return True
def select_top_articles(candidates: list[Article], section_key: str, max_n: int) -> list[Article]:
    """섹션별 기사 선정.
    ✅ (1) 카톡/브리핑 상단 '핵심 2'는 "진짜 상위 2"가 되도록(다양성 캡에 의해 밀려나지 않게) 고정.
    ✅ 나머지는 topic 다양성을 약하게 반영해 채움.
    """
    if not candidates:
        return []

    candidates_sorted = sorted(candidates, key=_sort_key_major_first, reverse=True)

    # --- 핵심 2: 상위 중요도 2개를 우선 확보(너무 저품질은 컷) ---
    CORE_MIN_SCORE = {
        "supply": 7.5,
        "policy": 7.5,
        "dist": 8.0,
        "pest": 6.8,
    }
    core_min = CORE_MIN_SCORE.get(section_key, 6.5)

    used_keys: set[str] = set()

    def akey(a: Article) -> str:
        return a.norm_key or a.canon_url or a.link or a.title_key

    core2: list[Article] = []

    def try_add_core(a: Article) -> bool:
        k = akey(a)
        if k in used_keys:
            return False
        core2.append(a)
        used_keys.add(k)
        return True


    def _too_similar(a1: Article, a2: Article) -> bool:
        return _jaccard(_token_set(a1.title), _token_set(a2.title)) >= 0.72

    # ✅ (5) 코어(핵심 2)는 "정말 핵심"만: 섹션별 게이트(_headline_gate) 통과 우선
    if section_key == "policy":
        # (최우선) 농식품부/정책브리핑 등 공식 소스
        for a in candidates_sorted:
            if len(core2) >= 2:
                break
            if a.score < core_min:
                continue
            if not _is_policy_official(a):
                continue
            if not _headline_gate(a, section_key):
                continue
            if core2 and _too_similar(core2[0], a):
                continue
            try_add_core(a)

        # (차순) 정책 액션/제도성(대책/지원/할당관세 등) 기사
        for a in candidates_sorted:
            if len(core2) >= 2:
                break
            if a.score < core_min:
                continue
            if not _headline_gate(a, section_key):
                continue
            if core2 and _too_similar(core2[0], a):
                continue
            try_add_core(a)

    else:
        for a in candidates_sorted:
            if len(core2) >= 2:
                break
            if a.score < core_min:
                continue
            if not _headline_gate(a, section_key):
                continue
            if core2 and _too_similar(core2[0], a):
                continue
            try_add_core(a)

    # 게이트 통과가 부족하면, 최소 점수(core_min) 이상 상위 기사로 보완(코어 2 확보)
    for a in candidates_sorted:
        if len(core2) >= 2:
            break
        if a.score < core_min:
            continue
        if core2 and _too_similar(core2[0], a):
            continue
        try_add_core(a)

    # 그래도 부족하면 최상위에서 채움(단, 유사 제목은 회피)
    for a in candidates_sorted:
        if len(core2) >= 2:
            break
        if core2 and _too_similar(core2[0], a):
            continue
        try_add_core(a)
    # --- 나머지: 동적 임계치로 너무 약한 기사 컷 + topic 다양성 약하게 반영 ---
    thr = _dynamic_threshold(candidates_sorted, section_key)
    pool = [a for a in candidates_sorted if a.score >= thr]
    if not pool:
        pool = candidates_sorted

    used_topic: dict[str, int] = {}
    for a in core2:
        used_topic[a.topic] = used_topic.get(a.topic, 0) + 1

    rest: list[Article] = []
    target_rest = max(0, max_n - len(core2))

    def can_take(a: Article, cap: int) -> bool:
        return used_topic.get(a.topic, 0) < cap

    for cap in (1, 2, 99):
        for a in pool:
            if len(rest) >= target_rest:
                break
            k = akey(a)
            if k in used_keys:
                continue
            if not can_take(a, cap):
                continue
            rest.append(a)
            used_keys.add(k)
            used_topic[a.topic] = used_topic.get(a.topic, 0) + 1
        if len(rest) >= target_rest:
            break

    rest = sorted(rest, key=_sort_key_major_first, reverse=True)

    selected = core2[:2] + rest
    return selected[:max_n]

def collect_candidates_for_section(section_conf: dict, start_kst: datetime, end_kst: datetime, dedupe: DedupeIndex) -> list[Article]:
    queries = section_conf["queries"]
    items: list[Article] = []

    def fetch(q: str):
        return q, naver_news_search(q, display=50, start=1, sort="date")

    max_workers = min(NAVER_MAX_WORKERS, max(1, len(queries)))
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for q in queries:
            futures.append(ex.submit(fetch, q))

        for fut in as_completed(futures):
            try:
                _q, data = fut.result()
            except Exception as e:
                log.warning("[WARN] query failed: %s", e)
                continue

            for it in data.get("items", []):
                title = clean_text(it.get("title", ""))
                desc = clean_text(it.get("description", ""))
                link = strip_tracking_params(it.get("link", "") or "")
                origin = strip_tracking_params(it.get("originallink", "") or link)
                pub = parse_pubdate_to_kst(it.get("pubDate", ""))

                if pub < start_kst or pub >= end_kst:
                    continue

                dom = domain_of(origin) or domain_of(link)
                if not dom or is_blocked_domain(dom):
                    continue

                press = press_name_from_url(origin or link)
                if not is_relevant(title, desc, dom, section_conf, press):
                    continue

                canon = canonicalize_url(origin or link)
                title_key = norm_title_key(title)
                topic = extract_topic(title, desc)
                norm_key = make_norm_key(canon, press, title_key)

                if not dedupe.add_and_check(canon, press, title_key, norm_key):
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
                    title_key=title_key,
                    canon_url=canon,
                    topic=topic,
                )
                art.score = compute_rank_score(title, desc, dom, pub, section_conf, press)
                items.append(art)

    items.sort(key=_sort_key_major_first, reverse=True)
    return items

def collect_all_sections(start_kst: datetime, end_kst: datetime):
    dedupe = DedupeIndex()
    raw_by_section: dict[str, list[Article]] = {}

    ordered = sorted(SECTIONS, key=lambda s: 0 if s["key"] == "policy" else 1)
    for sec in ordered:
        raw_by_section[sec["key"]] = collect_candidates_for_section(sec, start_kst, end_kst, dedupe)

    final_by_section: dict[str, list[Article]] = {}
    for sec in SECTIONS:
        key = sec["key"]
        candidates = raw_by_section.get(key, [])
        final_by_section[key] = select_top_articles(candidates, key, MAX_PER_SECTION)

    return final_by_section


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

def openai_summarize_batch(articles: list[Article]) -> dict:
    if not OPENAI_API_KEY or not articles:
        return {}

    rows = []
    for a in articles:
        rows.append({
            "id": a.norm_key,
            "press": a.press,
            "title": a.title[:180],
            "desc": a.description[:260],
            "section": a.section,
            "url": a.originallink or a.link,
        })

    system = (
        "너는 농협 경제지주 원예수급부(과수화훼) 실무자를 위한 '농산물 뉴스 요약가'다.\n"
        "- 절대 상상/추정으로 사실을 만들지 마라.\n"
        "- 각 기사 요약은 2문장 내, 110~200자 내. 핵심 팩트 중심.\n"
        "출력 형식: 각 줄 'id\\t요약' 형태로만 출력."
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
        r = SESSION.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if not r.ok:
            log.warning("[OpenAI] summarize skipped: %s", r.text)
            return {}

        text = openai_extract_text(r.json()).strip()
        out = {}
        for line in text.splitlines():
            if "\t" not in line:
                continue
            k, v = line.split("\t", 1)
            k = k.strip()
            v = v.strip()
            if k:
                out[k] = v
        return out

    except Exception as e:
        log.warning("[OpenAI] summarize failed, fallback: %s", e)
        return {}

def fill_summaries(by_section: dict):
    all_articles: list[Article] = []
    for sec in SECTIONS:
        all_articles.extend(by_section.get(sec["key"], []))

    mapping = openai_summarize_batch(all_articles)

    for a in all_articles:
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


# -----------------------------
# Rendering (HTML)
# -----------------------------
def esc(s: str) -> str:
    return html.escape(s or "")

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


def render_daily_page(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict,
                      archive_dates_desc: list[str], site_path: str) -> str:
    # 상단 칩 카운트 + 섹션별 중요도 정렬
    chips = []
    total = 0
    for sec in SECTIONS:
        lst = sorted(by_section.get(sec["key"], []), key=_sort_key_major_first, reverse=True)
        by_section[sec["key"]] = lst
        n = len(lst)
        total += n
        chips.append((sec["key"], sec["title"], n, sec["color"]))

    # prev/next: 검증된 날짜 리스트 기준 (없을 때는 '알림 버튼'으로 404 방지)
    prev_href = None
    next_href = None
    if report_date in archive_dates_desc:
        idx = archive_dates_desc.index(report_date)
        # prev(더 과거) = idx+1
        if idx + 1 < len(archive_dates_desc):
            prev_href = build_site_url(site_path, f"archive/{archive_dates_desc[idx+1]}.html")
        # next(더 최신) = idx-1
        if idx - 1 >= 0:
            next_href = build_site_url(site_path, f"archive/{archive_dates_desc[idx-1]}.html")

    # 날짜 select (value도 절대경로)
    options = []
    for d in archive_dates_desc[:60]:
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
            f'<span class="chipTitle">{esc(title)}</span><span class="chipN">{n}</span></a>'
        )

    chips_html = "\n".join([chip_html(*c) for c in chips])

    # ✅ (2) 섹션 렌더: 더 이상 숨김(<details>) 사용하지 않고 '전부' 노출
    # ✅ (2) 섹션 내 기사는 중요도 순(이미 정렬됨)
    sections_html = []
    for sec in SECTIONS:
        key = sec["key"]
        title = sec["title"]
        color = sec["color"]
        lst = by_section.get(key, [])

        def render_card(a: Article, is_core: bool):
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
                <a class=\"btnOpen\" href=\"{esc(url)}\" target=\"_blank\" rel=\"noopener\">원문 열기</a>
              </div>
              <div class=\"ttl\">{esc(a.title)}</div>
              <div class=\"sum\">{summary_html}</div>
            </div>
            """

        if not lst:
            body_html = '<div class="empty">해당사항 없음</div>'
        else:
            body_html = "\n".join([render_card(a, i < 2) for i, a in enumerate(lst)])

        sections_html.append(
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

    sections_html = "\n".join(sections_html)

    page_title = f"[{report_date} 농산물 뉴스 Brief]"
    period = f"{start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}"
    home_href = site_path

    def nav_btn(href: str | None, label: str, empty_msg: str):
        if href:
            return f'<a class="navBtn" href="{esc(href)}">{esc(label)}</a>'
        # ✅ (3) 없는 페이지로 링크하지 않고 알림으로 처리
        return f'<button class="navBtn disabled" type="button" data-msg="{esc(empty_msg)}">{esc(label)}</button>'

    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
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
    }}
    *{{box-sizing:border-box}}
    html {{
      /* ✅ 앵커 이동 위치 보정 */
      scroll-behavior:smooth;
      scroll-padding-top: 150px;
    }}
    body{{margin:0;background:var(--bg); color:var(--text);
         font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, \"Noto Sans KR\", Arial;}}
    .wrap{{max-width:1100px;margin:0 auto;padding:12px 14px 80px;}}
    .topbar{{position:sticky;top:0;background:rgba(255,255,255,0.94);backdrop-filter:saturate(180%) blur(10px);
            border-bottom:1px solid var(--line); z-index:10;}}
    .topin{{max-width:1100px;margin:0 auto;padding:12px 14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;justify-content:space-between}}
    h1{{margin:0;font-size:18px;letter-spacing:-0.2px}}
    .sub{{color:var(--muted);font-size:12.5px;margin-top:4px}}
    .navRow{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
    .navBtn{{display:inline-flex;align-items:center;justify-content:center;
            height:36px;padding:0 12px;border:1px solid var(--line);border-radius:10px;
            background:#fff;color:#111827;text-decoration:none;font-size:13px; cursor:pointer;}}
    .navBtn:hover{{border-color:#cbd5e1}}
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
    .chip{{white-space:nowrap;text-decoration:none;border:1px solid var(--line);padding:7px 10px;border-radius:999px;
          background:var(--chip);font-size:13px;color:#111827;display:inline-flex;gap:8px;align-items:center}}
    .chip:hover{{border-color:#cbd5e1}}
    .chipTitle{{font-weight:800}}
    .chipN{{min-width:28px;text-align:center;background:#111827;color:#fff;padding:2px 8px;border-radius:999px;font-size:12px}}

    .sec{{margin-top:14px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--card);
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
  </style>
</head>
<body>
  <div class=\"topbar\">
    <div class=\"topin\">
      <div>
        <h1>{esc(page_title)}</h1>
        <div class=\"sub\">기간: {esc(period)} · 기사 {total}건</div>
      </div>
      <div class=\"navRow\">
        <a class=\"navBtn\" href=\"{esc(home_href)}\">최신/아카이브</a>
        {nav_btn(prev_href, "◀ 이전", "이전 브리핑이 없습니다.")}
        <div class=\"dateSelWrap\">
          <select id=\"dateSelect\" aria-label=\"날짜 선택\">
            {options_html}
          </select>
        </div>
        {nav_btn(next_href, "다음 ▶", "다음 브리핑이 없습니다.")}
      </div>
    </div>

    <div class=\"chipbar\">
      <div class=\"chipwrap\">
        <div class=\"chips\">{chips_html}</div>
      </div>
    </div>
  </div>

  <div class=\"wrap\">
    {sections_html}
    <div class=\"footer\">* 자동 수집 결과입니다. 핵심 확인은 “원문 열기”로 원문을 확인하세요.</div>
  </div>

  <script>
    (function() {{
      var sel = document.getElementById("dateSelect");
      if (sel) {{
        sel.addEventListener("change", function() {{
          var v = sel.value;
          if (v) window.location.href = v;
        }});
      }}

      // ✅ (3) prev/next가 없을 때 404로 이동하지 않도록 알림 처리
      var btns = document.querySelectorAll("button.navBtn[data-msg]");
      btns.forEach(function(b) {{
        b.addEventListener("click", function() {{
          var msg = b.getAttribute("data-msg") || "이동할 페이지가 없습니다.";
          alert(msg);
        }});
      }});
    }})();
  </script>
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
          <a class=\"card\" href=\"{esc(href)}\">
            <div class=\"dt\">{esc(pretty_date_kr(d))}</div>
            <div class=\"meta\">{esc(d)} · {esc(wd)}요일</div>
          </a>
        """)

    cards_html = "\n".join(cards) if cards else '<div class="empty">아카이브가 아직 없습니다.</div>'

    latest_btn_html = (
        f'<a class="btn" href="{esc(latest_link)}">최신 브리핑 열기</a>'
        if latest_link
        else '<button class="btn disabled" type="button" data-msg="최신 브리핑이 아직 없습니다.">최신 브리핑 열기</button>'
    )

    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>농산물 뉴스 브리핑</title>
  <style>
    :root {{
      --bg:#ffffff;
      --text:#111827;
      --muted:#6b7280;
      --line:#e5e7eb;
      --btn:#1d4ed8;
      --btnHover:#1e40af;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;background:var(--bg);color:var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, \"Noto Sans KR\", Arial;}}
    .wrap{{max-width:980px;margin:0 auto;padding:26px 16px 70px}}
    h1{{margin:0;font-size:22px;letter-spacing:-0.2px}}
    .sub{{color:var(--muted);margin-top:8px;font-size:13px;line-height:1.5}}
    .btn{{display:inline-flex;align-items:center;justify-content:center;margin-top:14px;text-decoration:none;color:#fff;
         border:1px solid var(--btn);padding:10px 14px;border-radius:12px;background:var(--btn);font-weight:900; cursor:pointer}}
    .btn:hover{{background:var(--btnHover);border-color:var(--btnHover)}}
    .btn.disabled{{opacity:.5; cursor:pointer}}

    .panel{{margin-top:18px;border:1px solid var(--line);border-radius:16px;background:#fff;padding:14px}}
    .panelTitle{{font-weight:900;margin-bottom:10px}}
    .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
    @media (max-width: 820px) {{ .grid{{grid-template-columns:repeat(2,1fr);}} }}
    @media (max-width: 520px) {{ .grid{{grid-template-columns:1fr;}} }}

    .card{{display:block;text-decoration:none;border:1px solid var(--line);border-radius:14px;padding:12px;
          background:#ffffff;color:var(--text)}}
    .card:hover{{border-color:#cbd5e1}}
    .dt{{font-size:15px;font-weight:900}}
    .meta{{margin-top:6px;color:var(--muted);font-size:12px}}
    .empty{{color:var(--muted);font-size:13px}}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>농산물 뉴스 브리핑</h1>
    <div class=\"sub\">최신 브리핑과 날짜별 아카이브를 제공합니다.</div>

    {latest_btn_html}

    <div class=\"panel\">
      <div class=\"panelTitle\">날짜별 아카이브</div>
      <div class=\"grid\">
        {cards_html}
      </div>
    </div>
  </div>

  <script>
    (function() {{
      var b = document.querySelector("button.btn.disabled[data-msg]");
      if (b) {{
        b.addEventListener("click", function() {{
          alert(b.getAttribute("data-msg") || "이동할 페이지가 없습니다.");
        }});
      }}
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
        print(f"[KAKAO LINK] {url}  (host={p.netloc})")
    except Exception:
        print(f"[KAKAO LINK] {url}")


# -----------------------------
# Kakao message (✅ 1번: 브리핑의 '핵심2'와 동일)
# -----------------------------
KAKAO_MESSAGE_SECTION_ORDER = ["supply", "policy", "dist", "pest"]

def _get_section_conf(key: str):
    for s in SECTIONS:
        if s["key"] == key:
            return s
    return None


def _kakao_pick_core2(lst: list[Article]) -> list[Article]:
    # ✅ (1) 카톡 메시지는 브리핑 상단 '핵심 2'와 동일(선정 단계에서 이미 core2를 상단에 고정)
    return lst[:2] if lst else []

def build_kakao_message(report_date: str, by_section: dict) -> str:
    total = 0
    major_cnt = 0
    other_cnt = 0
    per = {"supply": 0, "policy": 0, "pest": 0, "dist": 0}

    for key in per.keys():
        lst = by_section.get(key, [])
        per[key] = len(lst)
        total += len(lst)
        for a in lst:
            if press_priority(a.press, a.domain) >= 2:
                major_cnt += 1
            else:
                other_cnt += 1

    lines = []
    lines.append(f"[{report_date} 농산물 뉴스 Brief]")
    lines.append("")
    lines.append(f"기사 : 총 {total}건 (주요매체 {major_cnt}건, 기타 {other_cnt}건)")
    lines.append(f"- 품목 {per['supply']} · 정책 {per['policy']} · 유통 {per['dist']} · 방제 {per['pest']}")
    lines.append("")

    section_num = 0
    for key in KAKAO_MESSAGE_SECTION_ORDER:
        conf = _get_section_conf(key)
        if not conf:
            continue
        section_num += 1
        lines.append(f"{section_num}) {conf['title']}")

        items = _kakao_pick_core2(by_section.get(key, []))
        if not items:
            lines.append("   - (해당사항 없음)")
        else:
            for a in items:
                press = (a.press or "").strip() or "미상"
                lines.append(f"   - ({press}) {a.title}")
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    lines.append("")
    lines.append("👉 브리핑 열기에서 오늘의 뉴스를 확인하세요.")
    return "\n".join(lines)


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

    r = SESSION.post(url, data=data, timeout=30)
    if not r.ok:
        log.error("[KAKAO TOKEN ERROR] %s", r.text)
        r.raise_for_status()
    j = r.json()
    return j["access_token"]

def kakao_send_to_me(text: str, web_url: str):
    web_url = ensure_absolute_http_url(web_url)
    log_kakao_link(web_url)
    ensure_not_gist(web_url, "Kakao web_url")

    access_token = kakao_refresh_access_token()

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": web_url, "mobile_web_url": web_url},
        "button_title": "브리핑 열기",
    }

    r = SESSION.post(url, headers=headers, data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=30)
    if not r.ok:
        log.error("[KAKAO SEND ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()


# -----------------------------
# Window calculation
# -----------------------------
def compute_end_kst():
    if FORCE_REPORT_DATE:
        d = datetime.strptime(FORCE_REPORT_DATE, "%Y-%m-%d").date()
        return dt_kst(d, REPORT_HOUR_KST)

    if FORCE_END_NOW:
        return now_kst()

    n = now_kst()
    candidate = n.replace(hour=REPORT_HOUR_KST, minute=0, second=0, microsecond=0)
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
            start = min(st.astimezone(KST), prev_cutoff)
        except Exception:
            start = prev_cutoff

    if start >= end_kst:
        start = end_kst - timedelta(hours=24)

    return start, end_kst


# -----------------------------
# Main
# -----------------------------

def main():
    if not DEFAULT_REPO:
        raise RuntimeError("GITHUB_REPO or GITHUB_REPOSITORY is not set (e.g., ORGNAME/agri-news-brief)")
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is not set")
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is not set")
    if not KAKAO_REST_API_KEY or not KAKAO_REFRESH_TOKEN:
        raise RuntimeError("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN is not set")

    repo = DEFAULT_REPO
    end_kst = compute_end_kst()

    is_bd = is_business_day_kr(end_kst.date())
    if (not FORCE_RUN_ANYDAY) and (not is_bd):
        log.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date().isoformat())
        return

    start_kst, end_kst = compute_window(repo, GH_TOKEN, end_kst)
    log.info("[INFO] Window KST: %s ~ %s", start_kst.isoformat(), end_kst.isoformat())

    report_date = end_kst.date().isoformat()

    # Kakao absolute URL
    base_url = get_pages_base_url(repo).rstrip("/")
    daily_url = f"{base_url}/archive/{report_date}.html"

    ensure_not_gist(base_url, "base_url")
    ensure_not_gist(daily_url, "daily_url")

    # site path (✅ 4번: 404 방지 링크용)
    site_path = get_site_path(repo)

    # manifest load + sanitize (✅ 4번: 이상한 엔트리 제거)
    manifest, msha = load_archive_manifest(repo, GH_TOKEN)
    manifest = _normalize_manifest(manifest)

    clean_dates = sanitize_dates(manifest.get("dates", []))
    clean_dates.append(report_date)
    clean_dates = sorted(set(clean_dates))
    dates_desc = sorted(clean_dates, reverse=True)

    # ✅ (3,4) 최근 N개는 실제 파일 존재 여부를 확인해 UI 링크 404 제거
    verified_desc = verify_recent_archive_dates(repo, GH_TOKEN, dates_desc, report_date, verify_n=120)

    # manifest에는 "검증된 최근" + "오래된 tail"(검증 생략)만 유지
    tail = [d for d in dates_desc[120:] if d not in verified_desc]
    manifest["dates"] = sorted(set(verified_desc + tail))

    archive_dates_desc = verified_desc  # UI용(이전/다음/셀렉트/인덱스에 사용)

    # collect + summarize
    by_section = collect_all_sections(start_kst, end_kst)
    by_section = fill_summaries(by_section)

    # render (✅ 2번: 전체 노출 / 중요도 정렬)
    daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, archive_dates_desc, site_path)

    # index는 404 방지를 위해 "검증된 날짜"만 노출
    index_manifest = {"dates": archive_dates_desc}
    index_html = render_index_page(index_manifest, site_path)

    # write daily
    daily_path = f"{DOCS_ARCHIVE_DIR}/{report_date}.html"
    _raw_old, sha_old = github_get_file(repo, daily_path, GH_TOKEN, ref="main")
    github_put_file(repo, daily_path, daily_html, GH_TOKEN, f"Add daily brief {report_date}", sha=sha_old, branch="main")

    # write index
    _raw_old2, sha_old2 = github_get_file(repo, DOCS_INDEX_PATH, GH_TOKEN, ref="main")
    github_put_file(repo, DOCS_INDEX_PATH, index_html, GH_TOKEN, f"Update index {report_date}", sha=sha_old2, branch="main")

    # save manifest/state (manifest는 clean 유지)
    save_archive_manifest(repo, GH_TOKEN, manifest, msha)
    save_state(repo, GH_TOKEN, end_kst)

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
    kakao_send_to_me(kakao_text, daily_url)
    log.info("[OK] Kakao message sent. URL=%s", daily_url)


if __name__ == "__main__":
    main()
