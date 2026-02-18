# -*- coding: utf-8 -*-
"""
agri-news-brief main.py (production)

✅ 이번 수정 반영 (요청 1~10)

1) 일부 매체 영문 표기 개선
   - PRESS_HOST_MAP 확장: 팜&마켓(farmnmarket.com), 미디어제주(mediajeju.com),
     포인트데일리(pointdaily.co.kr), 메트로신문(metroseoul.co.kr) 등 추가
   - host exact + suffix 매칭, 2단계 TLD(co.kr 등) 브랜드 추출 개선 유지

2) 카톡 메시지에 중앙지 우선
   - 기사 점수에 “매체 우선순위(중앙/주요방송/농민신문/정책기관)” 가중치 강화
   - 카톡용 TOP2는 섹션 리스트에서 다시 “중앙/주요매체 우선 정렬” 후 선택

3) 브리핑 페이지 ‘다음’이 없는 경우 클릭해도 에러페이지 안 뜨게
   - next/prev가 없으면 <button disabled> 로 렌더링(링크 자체를 없앰)
   - select 이동도 항상 존재하는 날짜만 생성

4) 도매시장 이슈는 유통으로, 품목/수급은 품목 중심으로
   - supply 섹션에서 ‘가락시장/도매시장/경락/경매/반입’ 키워드가 나오면 제외(유통으로만)
   - dist 섹션에 도매시장/가락시장 관련 쿼리/필수키워드 집중 배치

5) ‘주요 이슈 및 정책’에서 농식품부(마프라) 기사가 항상 1번
   - policy 섹션 선택 로직: mafra.go.kr 최우선 고정(있으면 무조건 1번)

6) 섹션당 기사수는 꼭 5개가 아님
   - 최대(MAX_PER_SECTION)까지지만, 품질 기준 미달이면 과감히 제외
   - 정말 관련 없으면 “해당사항 없음” 표시

7) 최신/아카이브 페이지 에러 개선
   - HTML 내부 링크를 base_url 절대경로가 아닌 “상대경로”로 변경(환경/도메인 설정과 무관하게 동작)
     · index: ./archive/YYYY-MM-DD.html
     · daily: ../ (index로), ./YYYY-MM-DD.html(같은 archive 내부 이동)

8) ‘미 전역 Target 매장 시위’ 같은 비관련 뉴스 유입 차단
   - 글로벌 리테일/소매 시위/보이콧류 키워드 + 농업 강도 낮으면 강제 제외
   - dist 섹션의 필수키워드에서 너무 일반적인 “유통” 제거(오탐 감소)

9) 중앙지/농민신문/MBC 등 주요 매체 우선 기준 철저
   - MAJOR_PRESS_SET 확장(농민신문 포함)
   - 점수/정렬/카톡선정 모두 동일 기준 적용

10) 날짜 셀렉 길이(레이아웃) 조정
   - 옵션 표시는 YY-MM-DD로 축약, select 폭 제한 + 줄바꿈/정렬 개선
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


# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agri-brief")


# -----------------------------
# HTTP session (keep-alive)
# -----------------------------
SESSION = requests.Session()


# -----------------------------
# Config
# -----------------------------
KST = timezone(timedelta(hours=9))

REPORT_HOUR_KST = int(os.getenv("REPORT_HOUR_KST", "7"))

# 최대치(상한)만 5 정도로 두되, 실제는 품질에 따라 더 적을 수 있음
MAX_PER_SECTION = int(os.getenv("MAX_PER_SECTION", "5"))

STATE_FILE_PATH = ".agri_state.json"
ARCHIVE_MANIFEST_PATH = ".agri_archive.json"

DOCS_INDEX_PATH = "docs/index.html"
DOCS_ARCHIVE_DIR = "docs/archive"

DEFAULT_REPO = (os.getenv("GITHUB_REPO") or os.getenv("GITHUB_REPOSITORY") or "").strip()
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
FORCE_RUN_ANYDAY = os.getenv("FORCE_RUN_ANYDAY", "false").strip().lower() in ("1", "true", "yes")
FORCE_END_NOW = os.getenv("FORCE_END_NOW", "false").strip().lower() in ("1", "true", "yes")
STRICT_KAKAO_LINK_CHECK = os.getenv("STRICT_KAKAO_LINK_CHECK", "false").strip().lower() in ("1", "true", "yes")

EXTRA_HOLIDAYS = set([s.strip() for s in os.getenv("EXTRA_HOLIDAYS", "").split(",") if s.strip()])
EXCLUDE_HOLIDAYS = set([s.strip() for s in os.getenv("EXCLUDE_HOLIDAYS", "").split(",") if s.strip()])


# -----------------------------
# Domain blocks (noise)
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

# 농업 맥락 강한 키워드
AGRI_STRONG_TERMS = [
    "가락시장", "도매시장", "공판장", "경락", "경락가", "경매", "청과", "산지", "출하", "물량", "반입",
    "산지유통", "APC", "산지유통센터", "선별", "CA저장", "저장고", "저장량",
    "시세", "도매가격", "소매가격", "가격", "수급", "수급동향", "작황", "생산량", "재배", "수확", "면적",
    "농림축산식품부", "농식품부", "aT", "한국농수산식품유통공사", "농관원", "국립농산물품질관리원",
    "검역", "할당관세", "수입", "수출", "관세", "통관", "원산지", "부정유통", "온라인 도매시장",
    "비축미", "정부", "대책", "지원", "할인지원", "성수품",
    "병해충", "방제", "약제", "살포", "예찰", "과수화상병", "탄저병", "동해", "냉해", "월동",
]

# 오프토픽(감점)
OFFTOPIC_HINTS = [
    "배우", "아이돌", "드라마", "영화", "예능", "콘서트", "팬", "뮤직",
    "국회", "총선", "검찰", "재판", "탄핵", "정당",
    "코스피", "코스닥", "주가", "급등", "급락", "비트코인", "환율",
    "여행", "관광", "호텔", "리조트", "레스토랑", "와인", "해변", "휴양",
]

# ✅ 8번: 글로벌 리테일 시위/보이콧류 차단(농업 강도 낮으면 제외)
GLOBAL_RETAIL_PROTEST_HINTS = [
    "target", "타깃", "walmart", "월마트", "costco", "코스트코",
    "starbucks", "스타벅스", "boycott", "보이콧", "시위", "protest",
    "매장", "retail", "소매", "전역",
]

KOREA_CONTEXT_HINTS = [
    "국내", "한국", "우리나라", "농협", "지자체", "군", "시", "도", "농가", "산지", "가락시장",
    "농식품부", "aT", "농관원", "대한민국", "설", "명절",
]

# ✅ 4번: supply에서 제외할 도매시장/유통 키워드(유통 섹션으로만)
WHOLESALE_MARKET_TERMS = ["가락시장", "도매시장", "공판장", "경락", "경매", "반입", "중도매"]


# -----------------------------
# Policy domains (정책기관은 policy 섹션으로만)
# -----------------------------
POLICY_DOMAINS = {
    "korea.kr",
    "mafra.go.kr",
    "at.or.kr",
    "naqs.go.kr",
    "krei.re.kr",
}

AGRI_POLICY_KEYWORDS = [
    "농축수산물", "농축산물", "성수품", "할인지원", "할당관세", "검역",
    "수급", "가격", "과일", "비축미", "원산지", "정책", "대책", "브리핑", "보도자료"
]


# -----------------------------
# Sections (4번 반영: supply 품목 중심 / dist 도매시장 중심)
# -----------------------------
SECTIONS = [
    {
        "key": "supply",
        "title": "품목 및 수급 동향",
        "color": "#0f766e",
        "queries": [
            # ✅ 품목 중심(도매시장/가락시장 쿼리 제거)
            "사과 작황", "사과 생산량", "사과 저장", "사과 수급", "사과 가격",
            "배 작황", "배 생산량", "배 저장", "배 수급", "배 가격",
            "감귤 작황", "감귤 수급", "만감류 출하", "한라봉 출하", "레드향 출하", "천혜향 출하",
            "샤인머스캣 작황", "샤인머스캣 수급", "포도 작황", "포도 수급",
            "오이 작황", "오이 수급", "풋고추 작황", "풋고추 수급",
            "쌀 산지 가격", "비축미 동향",
        ],
        # ✅ 품목/생산/작황/저장 중심
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
            # ✅ 도매시장/가락시장 이슈를 여기로 집중
            "가락시장 청과 경락", "도매시장 경락가", "도매시장 반입량", "도매시장 수급",
            "공판장 경매", "경락가 상승", "경락가 하락",
            "APC 선별", "CA저장 APC", "산지유통센터 APC",
            "농산물 수출 실적", "과일 수출 실적", "검역 수출 농산물",
            "부정유통 단속 농산물", "원산지 표시 단속",
        ],
        # ✅ 너무 일반적인 '유통' 제거 (8번 오탐 감소)
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
# Topic diversity (품목 도배 방지)
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
        frag = ""  # fragment 제거
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

def off_topic_penalty(text: str) -> int:
    return count_any(text, OFFTOPIC_HINTS)

def korea_context_score(text: str) -> int:
    return count_any(text, KOREA_CONTEXT_HINTS)

def global_retail_protest_penalty(text: str) -> int:
    t = text.lower()
    return count_any(t, GLOBAL_RETAIL_PROTEST_HINTS)


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
# Press mapping (1번 강화)
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

    # ✅ 농업/전문지(우선순위 높게)
    "nongmin.com": "농민신문",
    "farmnmarket.com": "팜&마켓",

    # ✅ 스포츠/중견
    "sportsseoul.com": "스포츠서울",
    "sportschosun.com": "스포츠조선",
    "osen.co.kr": "오센",
    "mydaily.co.kr": "마이데일리",
    "stoo.com": "스포츠투데이",
    "sportsworldi.com": "스포츠월드",
    "isplus.com": "일간스포츠",
    "spotvnews.co.kr": "SPOTVNEWS",
    "xportsnews.com": "엑스포츠뉴스",

    # ✅ 요청 매체(영문→한글)
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
    "osen": "오센",
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
# Press priority (2,9번 핵심)
# -----------------------------
MAFRA_HOSTS = {"mafra.go.kr"}
POLICY_HOSTS = set(POLICY_DOMAINS)

MAJOR_PRESS_SET = {
    "연합뉴스", "중앙일보", "동아일보", "조선일보", "한겨레", "경향신문", "국민일보", "서울신문",
    "매일경제", "머니투데이", "서울경제", "한국경제", "파이낸셜뉴스", "이데일리", "아시아경제", "헤럴드경제",
    "KBS", "MBC", "SBS", "YTN", "JTBC", "MBN",
    "농민신문",
    "정책브리핑", "농식품부", "aT", "농관원", "KREI",
    "팜&마켓",
}

def press_priority(press: str, domain: str) -> int:
    """
    3: 농식품부(최우선)
    2: 주요 중앙지/방송/농민신문/정책기관/전문 핵심
    1: 기타(지방지/인터넷)
    """
    p = (press or "").strip()
    d = (domain or "").lower()

    if d in MAFRA_HOSTS or d.endswith(".mafra.go.kr") or p == "농식품부":
        return 3
    if p in MAJOR_PRESS_SET:
        return 2
    if d in POLICY_HOSTS or d.endswith(".go.kr") or d.endswith(".re.kr"):
        return 2
    return 1


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
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set")
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": query, "display": display, "start": start, "sort": sort}
    r = SESSION.get(url, headers=headers, params=params, timeout=25)
    if not r.ok:
        log.error("[NAVER ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()


# -----------------------------
# Relevance / scoring
# -----------------------------
def section_must_terms_ok(text: str, must_terms) -> bool:
    return has_any(text, must_terms)

def policy_domain_override(dom: str, text: str) -> bool:
    if dom in POLICY_DOMAINS or dom.endswith(".go.kr"):
        return has_any(text, [k.lower() for k in AGRI_POLICY_KEYWORDS])
    return False

def is_relevant(title: str, desc: str, dom: str, section_conf: dict) -> bool:
    if is_blocked_domain(dom):
        return False

    text = (title + " " + desc).lower()

    # 정책기관 도메인은 policy 섹션 외에서는 제외
    if (dom in POLICY_DOMAINS or dom.endswith(".go.kr") or dom.endswith(".re.kr")) and section_conf["key"] != "policy":
        return False

    # ✅ 4번: supply는 도매시장/가락시장 이슈 제외(유통으로만)
    if section_conf["key"] == "supply":
        if has_any(text, [w.lower() for w in WHOLESALE_MARKET_TERMS]):
            return False

    # ✅ 8번: 글로벌 리테일 시위/보이콧 오탐 제거(농업 강도 낮으면 컷)
    strength = agri_strength_score(text)
    retail_pen = global_retail_protest_penalty(text)
    if retail_pen >= 2 and strength < 4:
        return False

    # must_terms gate (policy domains can override)
    if not section_must_terms_ok(text, [t.lower() for t in section_conf["must_terms"]]):
        if not policy_domain_override(dom, text):
            return False

    offp = off_topic_penalty(text)
    korea = korea_context_score(text)

    # 오프토픽인데 농업 강도 낮으면 제외
    if offp >= 1 and strength < 4:
        return False

    # “사과(사과문)” 오탐 방지
    if re.search(r"(공개\s*)?사과(했다|해야|하라|문|요구|요청|발표)", title) and strength < 5:
        return False

    # “배(선박)” 오탐 방지
    if re.search(r"(선박|해군|항만|조선|함정|승선|항해)", text) and strength < 5:
        return False

    # dist 섹션은 “유통 일반” 오탐을 막기 위해 농업 강도 최소치 요구
    if section_conf["key"] == "dist" and strength < 4:
        return False

    # supply 섹션도 최소 농업 강도 요구(품목 중심)
    if section_conf["key"] == "supply" and strength < 3:
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

    # ✅ 2,9번: 매체 우선순위 강하게 반영
    pr = press_priority(press, dom)
    if pr == 3:
        score += 10.0  # 농식품부 최우선
    elif pr == 2:
        score += 4.5   # 중앙지/방송/농민신문/정책기관
    else:
        score += 0.0

    # 최신 가산
    age_hours = max(0.0, (datetime.now(tz=KST) - pub_dt_kst).total_seconds() / 3600.0)
    score += max(0.0, 24.0 - min(age_hours, 24.0)) * 0.06

    # 제목에 must term 포함 가산
    for t in section_conf["must_terms"]:
        if t.lower() in title.lower():
            score += 0.7

    # policy 섹션에서 농식품부/정책브리핑 가산
    if section_conf["key"] == "policy":
        if "농식품부" in title or "정책브리핑" in title or dom in ("mafra.go.kr", "korea.kr"):
            score += 2.0

    return score


# -----------------------------
# Selection (5,6,9번 반영)
# -----------------------------
BASE_MIN_SCORE = {
    "supply": 7.0,
    "policy": 6.5,
    "dist": 7.0,
    "pest": 6.0,
}

def _dynamic_threshold(candidates: list[Article], section_key: str) -> float:
    if not candidates:
        return 10**9
    best = max(a.score for a in candidates)
    # best 대비 너무 멀리 떨어진 기사들은 버림 + 섹션별 바닥 기준
    return max(BASE_MIN_SCORE.get(section_key, 6.5), best - 8.0)

def _sort_key_major_first(a: Article):
    # 중앙/주요매체 우선 -> 점수 -> 최신
    return (press_priority(a.press, a.domain), a.score, a.pub_dt_kst)

def select_top_articles(candidates: list[Article], section_key: str, max_n: int) -> list[Article]:
    if not candidates:
        return []

    # 우선순위 정렬
    candidates = sorted(candidates, key=_sort_key_major_first, reverse=True)

    # ✅ 6번: 품질 기준 미달은 과감히 제거
    thr = _dynamic_threshold(candidates, section_key)
    filtered = [a for a in candidates if a.score >= thr]

    # policy는 “농식품부 1번”을 최우선 보장 (5번)
    selected: list[Article] = []

    def add_one(pred):
        for a in filtered:
            if a in selected:
                continue
            if pred(a):
                selected.append(a)
                return True
        return False

    if section_key == "policy":
        # 1) mafra.go.kr 최우선(있으면 무조건 1번)
        if not add_one(lambda a: normalize_host(a.domain) == "mafra.go.kr" or a.press == "농식품부"):
            # 2) 다음은 정책브리핑
            add_one(lambda a: normalize_host(a.domain) == "korea.kr" or a.press == "정책브리핑")

    # 다양성(같은 토픽 도배 완화)
    used_topic = {}
    def can_take(a: Article, cap: int) -> bool:
        return used_topic.get(a.topic, 0) < cap

    # 먼저 cap=1로 채우기
    for a in filtered:
        if len(selected) >= max_n:
            break
        if a in selected:
            continue
        if not can_take(a, 1):
            continue
        selected.append(a)
        used_topic[a.topic] = used_topic.get(a.topic, 0) + 1

    # 부족하면 cap=2로 완화
    if len(selected) < max_n:
        for a in filtered:
            if len(selected) >= max_n:
                break
            if a in selected:
                continue
            if not can_take(a, 2):
                continue
            selected.append(a)
            used_topic[a.topic] = used_topic.get(a.topic, 0) + 1

    # 그래도 부족하면 그냥 점수순으로
    if len(selected) < max_n:
        for a in filtered:
            if len(selected) >= max_n:
                break
            if a in selected:
                continue
            selected.append(a)

    selected = sorted(selected, key=_sort_key_major_first, reverse=True)[:max_n]

    # ✅ 5번: policy는 “농식품부 1번” 고정
    if section_key == "policy":
        mafra = None
        for a in selected:
            if normalize_host(a.domain) == "mafra.go.kr" or a.press == "농식품부":
                mafra = a
                break
        if mafra:
            selected = [mafra] + [x for x in selected if x is not mafra]

    return selected


# -----------------------------
# Collect articles (병렬 수집 + dedupe)
# -----------------------------
def collect_candidates_for_section(section_conf: dict, start_kst: datetime, end_kst: datetime, dedupe: DedupeIndex) -> list[Article]:
    queries = section_conf["queries"]
    items: list[Article] = []

    def fetch(q: str):
        return q, naver_news_search(q, display=50, start=1, sort="date")

    max_workers = min(6, max(1, len(queries)))
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

                if not is_relevant(title, desc, dom, section_conf):
                    continue

                press = press_name_from_url(origin or link)
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

    # policy 먼저 수집
    ordered = sorted(SECTIONS, key=lambda s: 0 if s["key"] == "policy" else 1)
    for sec in ordered:
        raw_by_section[sec["key"]] = collect_candidates_for_section(sec, start_kst, end_kst, dedupe)

    # ✅ “억지로 채우지 않음” (6번)
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
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text}
            msg = (body.get("error") or {}).get("message") or r.text
            code = (body.get("error") or {}).get("code") or str(r.status_code)
            log.warning("[OpenAI] summarize skipped (%s): %s", code, msg)
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
# Rendering (HTML)  ✅ 3,7,10번 핵심
# - 내부 링크는 상대경로로만 구성 (base_url 영향 제거)
# -----------------------------
def esc(s: str) -> str:
    return html.escape(s or "")

def fmt_dt(dt_: datetime) -> str:
    return dt_.strftime("%m/%d %H:%M")

def short_date_label(iso_date: str) -> str:
    # ✅ 10번: 날짜 셀렉 표시 길이 축소 (YY-MM-DD)
    return iso_date[2:] if len(iso_date) == 10 else iso_date

def compute_prev_next_dates(archive_dates_desc: list[str], current_date: str):
    prev_date = None  # 더 과거
    next_date = None  # 더 최신
    if current_date in archive_dates_desc:
        idx = archive_dates_desc.index(current_date)
        if idx + 1 < len(archive_dates_desc):
            prev_date = archive_dates_desc[idx + 1]
        if idx - 1 >= 0:
            next_date = archive_dates_desc[idx - 1]
    return prev_date, next_date

def render_daily_page(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict,
                      archive_dates_desc: list[str]) -> str:
    chips = []
    total = 0
    for sec in SECTIONS:
        n = len(by_section.get(sec["key"], []))
        total += n
        chips.append((sec["key"], sec["title"], n, sec["color"]))

    prev_date, next_date = compute_prev_next_dates(archive_dates_desc, report_date)

    # ✅ 3번: next/prev 없으면 disabled button(링크 없음)
    # archive 폴더 내 이동은 같은 폴더이므로 ./YYYY-MM-DD.html
    prev_href = f"./{prev_date}.html" if prev_date else None
    next_href = f"./{next_date}.html" if next_date else None

    # dropdown (최근 60개만)
    options = []
    for d in archive_dates_desc[:60]:
        sel = " selected" if d == report_date else ""
        options.append(f'<option value="./{esc(d)}.html"{sel}>{esc(short_date_label(d))}</option>')
    options_html = "\n".join(options) if options else f'<option value="./{esc(report_date)}.html" selected>{esc(short_date_label(report_date))}</option>'

    def chip_html(k, title, n, color):
        return (
            f'<a class="chip" style="border-color:{color};" href="#sec-{k}">'
            f'<span class="chipTitle">{esc(title)}</span><span class="chipN">{n}</span></a>'
        )

    chips_html = "\n".join([chip_html(*c) for c in chips])

    sections_html = []
    for sec in SECTIONS:
        key = sec["key"]
        title = sec["title"]
        color = sec["color"]
        lst = by_section.get(key, [])

        cards = []
        for a in lst:
            url = a.originallink or a.link
            summary_html = "<br>".join(esc(a.summary).splitlines())
            cards.append(
                f"""
                <div class="card" style="border-left-color:{color}">
                  <div class="cardTop">
                    <div class="meta">
                      <span class="press">{esc(a.press)}</span>
                      <span class="dot">·</span>
                      <span class="time">{esc(fmt_dt(a.pub_dt_kst))}</span>
                      <span class="dot">·</span>
                      <span class="topic">{esc(a.topic)}</span>
                    </div>
                    <a class="btnOpen" href="{esc(url)}" target="_blank" rel="noopener">원문 열기</a>
                  </div>
                  <div class="ttl">{esc(a.title)}</div>
                  <div class="sum">{summary_html}</div>
                </div>
                """
            )

        cards_html = '<div class="empty">해당사항 없음</div>' if not cards else "\n".join(cards)

        sections_html.append(
            f"""
            <section id="sec-{key}" class="sec">
              <div class="secHead">
                <div class="secTitle">
                  <span class="dotColor" style="background:{color}"></span>
                  {esc(title)}
                </div>
                <div class="secCount">{len(lst)}건</div>
              </div>
              <div class="secBody">{cards_html}</div>
            </section>
            """
        )

    sections_html = "\n".join(sections_html)

    title = f"[{report_date} 농산물 뉴스 Brief]"
    period = f"{start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}"

    def nav_btn(href: str | None, label: str):
        if href:
            return f'<a class="navBtn" href="{esc(href)}">{esc(label)}</a>'
        return f'<button class="navBtn disabled" disabled>{esc(label)}</button>'

    # ✅ 7번: index로 가는 링크도 상대경로(archive에서 상위로)
    index_href = "../"

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
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
    body{{margin:0;background:var(--bg); color:var(--text);
         font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Noto Sans KR", Arial;}}
    .wrap{{max-width:1100px;margin:0 auto;padding:18px 14px 80px;}}
    .topbar{{position:sticky;top:0;background:rgba(255,255,255,0.92);backdrop-filter:saturate(180%) blur(10px);
            border-bottom:1px solid var(--line); z-index:10;}}
    .topin{{max-width:1100px;margin:0 auto;padding:12px 14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;justify-content:space-between}}
    h1{{margin:0;font-size:18px;letter-spacing:-0.2px}}
    .sub{{color:var(--muted);font-size:12.5px;margin-top:4px}}
    .navRow{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
    .navBtn{{display:inline-flex;align-items:center;justify-content:center;
            height:36px;padding:0 12px;border:1px solid var(--line);border-radius:10px;
            background:#fff;color:#111827;text-decoration:none;font-size:13px; cursor:pointer;}}
    .navBtn:hover{{border-color:#cbd5e1}}
    .navBtn.disabled{{opacity:.45;cursor:not-allowed}}
    /* ✅ 10번: 셀렉트 길이/레이아웃 조정 */
    .dateSelWrap{{display:inline-flex;align-items:center;gap:6px}}
    select{{height:36px;border:1px solid var(--line);border-radius:10px;padding:0 10px;background:#fff;font-size:13px;
            width:140px; max-width:140px;}}
    @media (max-width: 520px) {{
      select{{width:120px; max-width:120px;}}
    }}
    .chips{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}
    .chip{{text-decoration:none;border:1px solid var(--line);padding:8px 10px;border-radius:999px;
          background:var(--chip);font-size:13px;color:#111827;display:inline-flex;gap:8px;align-items:center}}
    .chip:hover{{border-color:#cbd5e1}}
    .chipTitle{{font-weight:600}}
    .chipN{{min-width:28px;text-align:center;background:#111827;color:#fff;padding:2px 8px;border-radius:999px;font-size:12px}}
    .sec{{margin-top:16px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--card)}}
    .secHead{{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:#fafafa;border-bottom:1px solid var(--line)}}
    .secTitle{{font-size:15px;font-weight:800;display:flex;align-items:center;gap:10px}}
    .dotColor{{width:10px;height:10px;border-radius:999px}}
    .secCount{{font-size:12px;color:var(--muted);background:#fff;border:1px solid var(--line);padding:4px 10px;border-radius:999px}}
    .secBody{{padding:12px 12px 14px}}
    .card{{border:1px solid var(--line);border-left:5px solid #334155;border-radius:14px;padding:12px;margin:10px 0;background:#fff}}
    .cardTop{{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}}
    .meta{{color:var(--muted);font-size:12px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
    .press{{color:#111827;font-weight:700}}
    .dot{{opacity:.5}}
    .topic{{background:#f3f4f6;border:1px solid var(--line);padding:2px 8px;border-radius:999px;font-size:11.5px;color:#111827}}
    .ttl{{margin-top:8px;font-size:15px;line-height:1.35;font-weight:700}}
    .sum{{margin-top:8px;color:#374151;font-size:13px;line-height:1.55}}
    .btnOpen{{display:inline-flex;align-items:center;justify-content:center;
             height:38px;padding:0 16px;border-radius:12px;border:1px solid var(--btn);
             background:var(--btn);color:#fff;text-decoration:none;font-size:13px;font-weight:800}}
    .btnOpen:hover{{background:var(--btnHover);border-color:var(--btnHover)}}
    .empty{{color:var(--muted);font-size:13px;padding:10px 2px}}
    .footer{{margin-top:18px;color:var(--muted);font-size:12px}}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="topin">
      <div>
        <h1>{esc(title)}</h1>
        <div class="sub">기간: {esc(period)} · 기사 {total}건 (상한 {MAX_PER_SECTION}개/섹션, 품질 미달은 제외)</div>
      </div>
      <div class="navRow">
        <a class="navBtn" href="{esc(index_href)}">최신/아카이브</a>
        {nav_btn(prev_href, "◀ 이전")}
        <div class="dateSelWrap">
          <select id="dateSelect" aria-label="날짜 선택">
            {options_html}
          </select>
        </div>
        {nav_btn(next_href, "다음 ▶")}
      </div>
    </div>
  </div>

  <div class="wrap">
    <div class="chips">{chips_html}</div>
    {sections_html}
    <div class="footer">* 자동 수집 결과입니다. 핵심 확인은 “원문 열기”로 원문을 확인하세요.</div>
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
    }})();
  </script>
</body>
</html>
"""

def render_index_page(manifest: dict) -> str:
    manifest = _normalize_manifest(manifest)
    dates = sorted(manifest.get("dates", []), reverse=True)
    latest = dates[0] if dates else None

    items_html = []
    for d in dates[:60]:
        url = f'./archive/{esc(d)}.html'
        items_html.append(f'<li><a href="{url}">{esc(d)}</a></li>')
    ul = "\n".join(items_html) if items_html else "<li>아카이브가 아직 없습니다.</li>"

    latest_link = f'./archive/{esc(latest)}.html' if latest else "./archive/"

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>농산물 뉴스 브리핑</title>
  <style>
    body{{margin:0;background:#ffffff;color:#111827;font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Noto Sans KR", Arial;}}
    .wrap{{max-width:900px;margin:0 auto;padding:24px 16px 60px}}
    h1{{margin:0;font-size:22px}}
    .sub{{color:#6b7280;margin-top:8px;font-size:13px}}
    .btn{{display:inline-block;margin-top:14px;text-decoration:none;color:#fff;border:1px solid #1d4ed8;
         padding:10px 14px;border-radius:12px;background:#1d4ed8;font-weight:900}}
    .btn:hover{{background:#1e40af;border-color:#1e40af}}
    .panel{{margin-top:18px;border:1px solid #e5e7eb;border-radius:16px;background:#fff;padding:14px}}
    ul{{margin:10px 0 0 18px}}
    a{{color:#1d4ed8}}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>농산물 뉴스 브리핑</h1>
    <div class="sub">최신 브리핑과 날짜별 아카이브를 제공합니다.</div>

    <a class="btn" href="{latest_link}">최신 브리핑 열기</a>

    <div class="panel">
      <div style="font-weight:900;margin-bottom:6px;">날짜별 아카이브</div>
      <ul>{ul}</ul>
    </div>
  </div>
</body>
</html>
"""


# -----------------------------
# Pages URL (anti-gist) - Kakao용 절대 URL 생성만 사용
# -----------------------------
def get_pages_base_url(repo: str) -> str:
    owner, name = repo.split("/", 1)
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

def log_kakao_domain_requirement(daily_url: str):
    dom = domain_of(daily_url)
    if not dom:
        return
    log.info("[KAKAO LINK CHECK] daily_url domain=%s", dom)
    log.info("[KAKAO LINK CHECK] If '브리핑 열기' opens wrong site, add this domain to Kakao Dev Console:")
    log.info("[KAKAO LINK CHECK] Kakao Developers > 앱 설정 > 플랫폼 > Web > 사이트 도메인 : %s", dom)

def ensure_not_gist(url: str, label: str):
    if "gist.github.com" in url or "raw.githubusercontent.com" in url:
        raise RuntimeError(f"[FATAL] {label} points to gist/raw: {url}")


# -----------------------------
# Kakao web_url safety (hard block)
# -----------------------------
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
# Kakao message builder (2,9번 반영: 중앙/주요매체 우선)
# -----------------------------
KAKAO_MESSAGE_SECTION_ORDER = ["supply", "policy", "dist", "pest"]

def _get_section_conf(key: str):
    for s in SECTIONS:
        if s["key"] == key:
            return s
    return None

def _kakao_pick_top2(lst: list[Article]) -> list[Article]:
    # 중앙/주요매체 우선 정렬 후 2개
    if not lst:
        return []
    return sorted(lst, key=_sort_key_major_first, reverse=True)[:2]

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
    lines.append("오늘의 체크포인트")
    lines.append("")

    section_num = 0
    for key in KAKAO_MESSAGE_SECTION_ORDER:
        conf = _get_section_conf(key)
        if not conf:
            continue
        section_num += 1

        lines.append(f"{section_num}) {conf['title']}")

        items = _kakao_pick_top2(by_section.get(key, []))
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
    lines.append("👉 '브리핑 열기'에서 섹션별 기사를 확인하세요.")
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
    if FORCE_RUN_ANYDAY and (not is_bd):
        log.info("[FORCE] Non-business day but proceeding for test: %s", end_kst.date().isoformat())

    start_kst, end_kst = compute_window(repo, GH_TOKEN, end_kst)
    log.info("[INFO] Window KST: %s ~ %s", start_kst.isoformat(), end_kst.isoformat())

    report_date = end_kst.date().isoformat()

    # Kakao는 절대 URL이 필요하므로 base_url 유지
    base_url = get_pages_base_url(repo).rstrip("/")
    daily_url = f"{base_url}/archive/{report_date}.html"

    ensure_not_gist(base_url, "base_url")
    ensure_not_gist(daily_url, "daily_url")
    log_kakao_domain_requirement(daily_url)

    # 아카이브 목록 로드
    manifest, msha = load_archive_manifest(repo, GH_TOKEN)
    manifest = _normalize_manifest(manifest)
    dates_set = set(manifest.get("dates", []))
    dates_set.add(report_date)
    manifest["dates"] = sorted(list(dates_set))  # 저장은 오름차순
    archive_dates_desc = sorted(manifest["dates"], reverse=True)  # 화면용은 내림차순

    # Collect + summarize
    by_section = collect_all_sections(start_kst, end_kst)
    by_section = fill_summaries(by_section)

    # Render pages (상대경로 기반)
    daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, archive_dates_desc)
    index_html = render_index_page(manifest)

    # Write daily page
    daily_path = f"{DOCS_ARCHIVE_DIR}/{report_date}.html"
    _raw_old, sha_old = github_get_file(repo, daily_path, GH_TOKEN, ref="main")
    github_put_file(repo, daily_path, daily_html, GH_TOKEN, f"Add daily brief {report_date}", sha=sha_old, branch="main")

    # Write index
    _raw_old2, sha_old2 = github_get_file(repo, DOCS_INDEX_PATH, GH_TOKEN, ref="main")
    github_put_file(repo, DOCS_INDEX_PATH, index_html, GH_TOKEN, f"Update index {report_date}", sha=sha_old2, branch="main")

    # Save manifest/state
    save_archive_manifest(repo, GH_TOKEN, manifest, msha)
    save_state(repo, GH_TOKEN, end_kst)

    # Kakao message
    kakao_text = build_kakao_message(report_date, by_section)
    if KAKAO_INCLUDE_LINK_IN_TEXT:
        kakao_text = kakao_text + "\n" + daily_url

    if STRICT_KAKAO_LINK_CHECK:
        parsed = urlparse(daily_url)
        if not parsed.scheme.startswith("http") or not parsed.netloc:
            raise RuntimeError(f"[FATAL] daily_url invalid: {daily_url}")

    # anti-gist hard block
    daily_url = ensure_absolute_http_url(daily_url)
    log_kakao_link(daily_url)
    kakao_send_to_me(kakao_text, daily_url)
    log.info("[OK] Kakao message sent. URL=%s", daily_url)


if __name__ == "__main__":
    main()
