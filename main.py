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
import difflib
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
_SESSION_LOCAL = threading.local()

def http_session():
    """Thread-safe session accessor.
    - When NAVER_MAX_WORKERS>1, use per-thread Session to avoid cross-thread issues.
    """
    try:
        if int(os.getenv("NAVER_MAX_WORKERS", "1")) > 1:
            s = getattr(_SESSION_LOCAL, "session", None)
            if s is None:
                s = requests.Session()
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
MAX_PER_SECTION = int(os.getenv("MAX_PER_SECTION", os.getenv("MAX_ARTICLES_PER_SECTION", "5")))
MAX_PER_SECTION = max(1, min(MAX_PER_SECTION, int(os.getenv("MAX_PER_SECTION_CAP", "20"))))
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


STATE_FILE_PATH = ".agri_state.json"
ARCHIVE_MANIFEST_PATH = ".agri_archive.json"
DOCS_INDEX_PATH = "docs/index.html"
DOCS_ARCHIVE_DIR = "docs/archive"
DOCS_SEARCH_INDEX_PATH = "docs/search_index.json"
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
NAVER_MIN_INTERVAL_SEC = float(os.getenv("NAVER_MIN_INTERVAL_SEC", "0.35"))  # 최소 호출 간격(초)
NAVER_MAX_RETRIES = int(os.getenv("NAVER_MAX_RETRIES", "6"))
NAVER_BACKOFF_MAX_SEC = float(os.getenv("NAVER_BACKOFF_MAX_SEC", "20"))
NAVER_MAX_WORKERS = int(os.getenv("NAVER_MAX_WORKERS", "2"))  # 동시 요청 수(속도제한 회피용)

_NAVER_LOCK = threading.Lock()
_NAVER_LAST_CALL = 0.0

def _naver_throttle():
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
HORTI_CORE_MARKERS = [
    "원예", "과수", "화훼", "절화", "과일", "채소", "청과", "시설채소", "하우스", "비가림",
    "사과", "배", "감귤", "포도", "딸기", "고추", "오이", "토마토", "파프리카", "상추",
    "단감", "곶감", "참다래", "키위", "샤인머스캣", "만감", "한라봉", "레드향", "천혜향",
    "자조금", "원예자조금", "과수자조금", "화훼", "국화", "장미",
]


# 금융/산업 일반 기사(농협은행/NH투자/주가/실적 등) 오탐 차단용
FINANCE_STRICT_TERMS = [
    "농협은행", "nh투자", "nh 투자", "증권", "은행", "보험", "카드", "캐피탈",
    "주가", "배당", "배당금", "실적", "매출", "영업이익", "순이익", "주주", "상장",
    "ipo", "공모", "채권", "금리", "환율", "부동산", "코스피", "코스닥",
]
# 현재 관심도가 낮은 품목(정 없을 때만 하단에 남도록 강감점)
EXCLUDED_ITEMS = ["마늘", "양파"]
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
            "사과 수급",
            "사과 가격",
            "사과 작황",
            "사과 저장",
            "사과 출하",
            "배 과일 수급",
            "배 과일 가격",
            "배 과일 작황",
            "배 과일 저장",
            "배 과일 출하",
            "감귤 수급",
            "감귤 가격",
            "감귤 작황",
            "만감류 출하",
            "한라봉 출하",
            "레드향 출하",
            "천혜향 출하",
            "포도 수급",
            "포도 가격",
            "포도 작황",
            "샤인머스캣 수급",
            "샤인머스캣 가격",
            "샤인머스캣 작황",
            "단감 수급",
            "단감 가격",
            "단감 작황",
            "곶감 수급",
            "떫은감 작황",
            "키위 수급",
            "키위 가격",
            "유자 수급",
            "유자 가격",
            "알밤 수급",
            "알밤 가격",
            "자두 수급",
            "자두 가격",
            "복숭아 수급",
            "복숭아 가격",
            "매실 수급",
            "매실 가격",
            "딸기 수급",
            "딸기 가격",
            "딸기 작황",
            "파프리카 수급",
            "파프리카 가격",
            "파프리카 수출",
            "참외 수급",
            "참외 가격",
            "오이 수급",
            "오이 가격",
            "오이 작황",
            "풋고추 수급",
            "풋고추 가격",
            "토마토 수급",
            "토마토 가격",
            "토마토 작황",
            "방울토마토 가격",
            "대추방울토마토 가격",
            "수박 수급",
            "수박 도매가격",
            "수박 작황",
            "호박 가격",
            "애호박 수급",
            "애호박 가격",
            "단호박 가격",
            "쥬키니 가격",
            "피망 수급",
            "피망 가격",
            "멜론 출하",
            "멜론 도매가격",
            "멜론 작황",
            "멜론 재배",
            "머스크멜론 출하",
            "머스크멜론 도매가격",
            "고추 작황",
            "화훼 가격",
            "절화 가격",
            "꽃 소비",
            "화훼 수급",
            "화훼자조금",
            "꽃다발 선물",
            "꽃다발 선물 트렌드",
            "꽃다발 소비",
            "레고 꽃",
            "레고 꽃다발",
            "레고 보태니컬",
            "보태니컬 시리즈 꽃",
            "장난감 꽃다발 화훼",
            "화훼 소비 트렌드",
            "생화 꽃다발 소비",
            "꽃다발 선물 사라진 시대",
            "틈새 파고든 레고 꽃",
        ],
        "must_terms": [
            "원예",
            "과수",
            "과일",
            "화훼",
            "절화",
            "꽃다발",
            "생화",
            "부케",
            "플라워",
            "레고",
            "시설채소",
            "과채",
            "사과",
            "감귤",
            "만감",
            "한라봉",
            "레드향",
            "천혜향",
            "포도",
            "샤인머스캣",
            "단감",
            "떫은감",
            "곶감",
            "키위",
            "참다래",
            "유자",
            "알밤",
            "자두",
            "복숭아",
            "매실",
            "딸기",
            "파프리카",
            "참외",
            "오이",
            "풋고추",
            "고추",
            "토마토",
            "방울토마토",
            "대추방울토마토",
            "수박",
            "호박",
            "애호박",
            "단호박",
            "쥬키니",
            "피망",
            "멜론",
            "머스크멜론",
            "네트멜론",
            "얼스멜론",
            "하미과",
            "칸탈루프",
            "허니듀",
            "신고배",
            "나주배",
            "배 과일",
        ],
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
            "가락시장 청과 경락",
            "가락시장 경락가",
            "도매시장 청과 경락",
            "도매시장 반입량",
            "도매시장 수급",
            "공영도매시장 경매",
            "공판장 청과 경매",
            "시장도매인제 도매시장",
            "온라인 도매시장 청과",
            "산지유통센터 준공",
            "스마트 농산물 산지유통센터 준공",
            "스마트 APC 준공",
            "APC 산지유통센터 준공",
            "APC 저온저장",
            "CA저장 과일",
            "원산지 표시 단속 농산물",
            "부정유통 단속 농산물",
            "농산물 수출 검역",
            "과일 수출 검역",
            "통관 과일 검역",
            "화훼공판장 경매",
            "절화 경매",
            "화훼자조금",
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
            "준공",
            "저온저장",
            "ca저장",
            "저장고",
            "수출",
            "검역",
            "통관",
            "원산지",
            "부정유통",
            "단속",
            "화훼",
            "절화",
            "화훼공판장",
            "자조금",
        ],
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
    ("배", ["신고배", "나주배", "배 과일", "배(과일)"]),
    ("단감", ["단감"]),
    ("감/곶감", ["떫은감", "곶감"]),
    ("감귤/만감", ["감귤", "만감", "만감류", "한라봉", "레드향", "천혜향", "황금향"]),
    ("포도", ["포도", "샤인머스캣"]),
    ("키위", ["키위", "참다래"]),
    ("유자", ["유자"]),
    ("밤", ["알밤"]),
    ("자두", ["자두"]),
    ("복숭아", ["복숭아"]),
    ("매실", ["매실"]),
    ("딸기", ["딸기"]),
    ("토마토", ["토마토", "방울토마토", "대추방울토마토"]),
    ("수박", ["수박"]),
    ("호박", ["호박", "애호박", "단호박", "쥬키니", "주키니"]),
    ("피망", ["피망"]),
    ("멜론", ["머스크멜론", "네트멜론", "얼스멜론", "하미과", "칸탈루프", "허니듀", "멜론"]),
    ("파프리카", ["파프리카"]),
    ("참외", ["참외"]),
    ("오이", ["오이"]),
    ("고추", ["고추", "풋고추", "청양고추"]),
    ("화훼", ["화훼", "절화", "국화", "장미", "백합", "꽃다발", "생화", "부케", "플라워"]),
    ("도매시장", ["가락시장", "도매시장", "공영도매시장", "공판장", "청과", "경락", "경매", "반입", "중도매인", "시장도매인", "온라인 도매시장"]),
    ("APC/산지유통", ["apc", "산지유통", "산지유통센터", "선별", "저온", "저장", "ca저장", "물류"]),
    ("수출/검역", ["수출", "검역", "통관", "수입검역", "잔류농약"]),
    ("정책", ["대책", "지원", "보도자료", "브리핑", "할당관세", "할인지원", "원산지", "단속", "고시", "개정"]),
    ("병해충", ["병해충", "방제", "예찰", "약제", "살포", "과수화상병", "탄저병", "노균병", "냉해", "동해"]),
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
    "잔류농약", "방사능", "식품안전", "위해", "유통", "차단", "사전", "폐기",
)

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
    if (not desc.strip()) and getattr(a, "summary", ""):
        desc = str(getattr(a, "summary", "") or "")
    return (a.title or ""), desc

def _dist_story_signature(text: str) -> str | None:
    # ✅ 서울시-가락시장-부적합 농수산물(잔류농약/방사능/수거검사/불시검사) 같은 보도자료 다매체 중복을 강하게 제거
    if "서울시" in text and "가락시장" in text and ("농수산물" in text or "농산물" in text):
        if ("부적합" in text or "잔류농약" in text or "방사능" in text) and ("수거" in text or "검사" in text or "불시" in text):
            return "SIG:SEOUL_FOODSAFETY_GARAK"

    # ✅ 서울시-부적합 농수산물 유통 차단(가락시장 언급이 없어도) 보도자료 다매체 중복을 제거
    if "서울시" in text and ("부적합" in text or "잔류농약" in text or "방사능" in text) and ("농수산물" in text or "농산물" in text):
        if ("유통" in text or "반입" in text) and ("차단" in text or "검사" in text or "수거" in text or "점검" in text):
            return "SIG:SEOUL_FOODSAFETY"

    # 일반화: '원산지 단속', '부정유통 단속' 같은 보도자료도 다매체 중복이 잦아 시그니처로 묶는다
    if ("원산지" in text or "부정유통" in text) and ("단속" in text or "적발" in text) and ("농산물" in text or "농수산물" in text):
        if "서울시" in text:
            return "SIG:SEOUL_ORIGIN_ENFORCE"

    # ✅ 한국청과 출하비용 보전사업(가락시장 도매법인) 기사 다매체 중복 제거
    if ("한국청과" in text or "한국 청과" in text) and ("출하비용" in text or "출하 비용" in text):
        if ("보전" in text or "보전금" in text or "보전사업" in text or "기준가격" in text) and ("가락시장" in text or "도매법인" in text or "경락" in text or "출하농가" in text):
            return "SIG:KOREA_CHEONGGWA_SUPPORT"

    return None



def _event_key(a: "Article", section_key: str) -> str | None:
    """섹션별 '사실상 같은 이슈'를 더 강하게 묶기 위한 이벤트 키.
    - 제목이 다르더라도 같은 이벤트(APC 준공/개장 등)면 1건만 남겨 핵심을 보호한다.
    """
    try:
        text = ((a.title or "") + " " + (a.description or "")).lower()

        # 1) APC 준공/개장/가동/개소 등 이벤트(농협/지역 단위 묶음)
        if ("apc" in text or "산지유통센터" in text or "산지유통" in text) and any(k in text for k in ("준공", "준공식", "개장", "개소", "문 열", "가동", "준비", "스마트")):
            m = re.search(r"([가-힣]{2,12})\s*농협", (a.title or "") + " " + (a.description or ""))
            if m:
                org = f"{m.group(1)}농협"
                return f"EV:APC:{org}"
            regs = sorted(_region_set(text))
            loc = regs[0] if regs else ""
            return f"EV:APC:{loc}"

        # 2) 서울시 부적합 농수산물 유통 차단(보도자료 다매체 중복)
        if "서울시" in text and ("부적합" in text or "잔류농약" in text or "방사능" in text) and ("농수산물" in text or "농산물" in text):
            if ("유통" in text or "반입" in text) and ("차단" in text or "검사" in text or "수거" in text or "점검" in text):
                return "EV:SEOUL_FOODSAFETY"

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

        # dist에서 로컬 단신/공지형이면 중복 그룹에서 강하게 밀어냄
        if section_key == "dist" and is_local_brief_text(title, desc, "dist"):
            b -= 2.0

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

def _is_similar_story(a: "Article", b: "Article", section_key: str) -> bool:
    at, ad = _story_text(a)
    bt, bd = _story_text(b)
    a_txt = f"{at} {ad}"
    b_txt = f"{bt} {bd}"

    # 0) 제목/요약 기반 근접 중복(타매체 재전송/표기 차이) 보강
    try:
        if _near_duplicate_title(a, b, section_key):
            return True
    except Exception:
        pass


    # 1) dist는 '시그니처' 우선
    if section_key == "dist":
        sa = _dist_story_signature(a_txt)
        sb = _dist_story_signature(b_txt)
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
_SINGLE_TERM_CONTEXT_PATTERNS: dict[str, list[re.Pattern]] = {
    # 과일 '배' (배터리/배당/배달/배기/배포 등 오탐 방지)
    "배": [
        re.compile(r"(?:^|[\s\W])배(?:값|가격|시세|수급|출하|저장|작황|재배|농가)"),
        re.compile(r"(?:^|[\s\W])배\s+과일"),
        re.compile(r"신고배"),
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
        re.compile(r"꽃다발"),
        re.compile(r"부케"),
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

_HORTI_TOPICS_SET = {
    "화훼", "사과", "배", "감귤/만감", "단감", "감/곶감", "키위", "유자", "포도",
    "밤", "자두", "복숭아", "매실", "딸기", "파프리카", "참외", "오이", "고추",
    "토마토",
    "수박",
    "호박",
    "피망",
    "멜론",
}

def _topic_scores(title: str, desc: str) -> dict[str, float]:
    t = (title + " " + desc).lower()
    tl = (title or "").lower()
    scores: dict[str, float] = {}

    for topic, words in COMMODITY_TOPICS:
        sc = 0.0
        if topic == "멜론" and not is_edible_melon_context(t):
            # 멜론(음원 플랫폼) 오탐 방지
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
    """APC 오탐(UPS/전원장비 등)을 막기 위해, '농업/산지유통' 문맥일 때만 APC로 인정."""
    t = (text or "").lower()
    if "apc" not in t:
        return False
    agri_hints = (
        "산지유통", "산지유통센터", "선별", "선별장", "저온", "저장고", "ca저장", "저온저장",
        "가락시장", "도매시장", "공판장", "경락", "경매", "반입",
        "농협", "원예", "과수", "청과", "농산물"
    )
    return any(h.lower() in t for h in agri_hints)

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
    apology_markers = (
        "사과문", "사과했다", "사과합니다", "사과드립니다", "공식 사과", "유감", "사과 요구", "사과를 요구",
        "사과하", "사과하고", "사과할"
    )
    # 과일 맥락 마커
    fruit_markers = (
        "과일", "과수", "과원", "사과나무", "부사", "후지", "홍로", "감홍", "아오리", "시나노",
        "가락시장", "도매시장", "공판장", "청과", "경락", "경매", "산지", "농가", "재배", "수확",
        "출하", "작황", "수급", "시세", "가격", "저장", "재고", "선별", "apc", "산지유통"
    )
    if any(m in t for m in apology_markers) and not any(m in t for m in fruit_markers):
        return False

    # 4) 긍정 판단: 실무 마커가 1개 이상이면 True
    if any(m in t for m in fruit_markers):
        return True

    # 5) 보강 패턴: '사과값/사과 가격/사과 시세' 같은 표현
    if re.search(r"사과\s*(값|가격|시세|수급|출하|작황)", t):
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

_FLOWER_TREND_CORE_MARKERS = [
    "꽃다발", "부케", "생화", "절화", "화훼", "플라워",
]
_FLOWER_TREND_TREND_MARKERS = [
    "트렌드", "인기", "틈새", "선물", "소비", "소비액", "소비촉진", "클래스", "체험",
    "레고", "보태니컬", "블록", "장난감 꽃", "장난감 꽃다발",
]
_FLOWER_TREND_EXCLUDE_MARKERS = [
    # 관광/개화/축제류
    "벚꽃", "유채꽃", "개화", "만개", "꽃축제", "축제", "명소", "포토존", "관광", "여행",
    # 연예/화보/드라마
    "배우", "아이돌", "화보", "드라마", "공연",
    # 창업/상권/프랜차이즈
    "프랜차이즈", "가맹", "창업", "상권", "임대", "인테리어",
]
def is_flower_consumer_trend_context(text: str) -> bool:
    """화훼 '소비/선물 트렌드' 유형(예: 레고 꽃다발 논란/꽃다발 선물 트렌드)을 판정한다.
    - 품목 및 수급 동향(supply)에서 '화훼 이슈'로 비핵심(하단) 편입하는 용도.
    - 관광/축제/연예/창업성 노이즈는 제외.
    """
    t = (text or "").lower()
    if any(w.lower() in t for w in _FLOWER_TREND_EXCLUDE_MARKERS):
        return False
    core_hits = sum(1 for w in _FLOWER_TREND_CORE_MARKERS if w.lower() in t)
    trend_hits = sum(1 for w in _FLOWER_TREND_TREND_MARKERS if w.lower() in t)
    # 최소 조건: 꽃다발/화훼 계열 1개 이상 + 트렌드/선물/레고 등 1개 이상
    if core_hits >= 1 and trend_hits >= 1:
        return True
    # 레고+꽃다발 조합은 강하게 인정
    if ("레고" in t and ("꽃다발" in t or "보태니컬" in t)):
        return True
    return False

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
    if any(w in t for w in ("수출","수입","통관","검역","수입검역","수출길","수출길", "관세")) and any(k.lower() in t for k in _KOREA_STRONG_CONTEXT):
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
    'apc': 2.0, '선별': 1.8, '저온': 1.2, '저장': 1.2, '원산지': 2.0, '부정유통': 2.0,

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
        # pest: '협의회/간담회/회의/교육' 등 행정 일정성 기사 상단 배치 억제
        if section_key == "pest" and any(w in t for w in ("협의회", "간담회", "회의", "설명회", "교육", "워크숍", "세미나")):
            return 2.0
        return 1.2
    # 시찰/협의회/방문/기술트렌드만 있는 경우는 더 크게 감점
    return 2.8 + 0.6 * max(0, hits - 1) + 0.4 * tech

SUPPLY_TITLE_CORE_TERMS = ('수급','가격','시세','경락가','작황','출하','재고','저장','물량')
DIST_TITLE_CORE_TERMS = ('가락시장','도매시장','공판장','경락','경매','반입','중도매인','시장도매인','apc','원산지')
POLICY_TITLE_CORE_TERMS = ('대책','지원','할당관세','검역','단속','고시','개정','브리핑','보도자료')
PEST_TITLE_CORE_TERMS = ('병해충','방제','예찰','과수화상병','탄저병','냉해','동해','약제','농약')

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

    ttl = (title or "")
    txt = ((title or "") + " " + (desc or "")).lower()
    ttl_l = (title or "").lower()

    # 예외: 원예 자조금은 반드시 체크(지역기사라도 실무 핵심)
    if "자조금" in txt and count_any(txt, [t.lower() for t in ("원예","과수","화훼","과일","채소","청과","사과","배","감귤","딸기","고추","오이","포도")]) >= 1:
        return False

    # 제목에 지역 단위(시/군/구/읍/면) 표기가 없으면 로컬 단신으로 보지 않음
    # 단, '안산 시장'처럼 (지자체장) 표기는 있는데 '안산시'가 없는 케이스가 있어 보완한다.
    if (_LOCAL_REGION_IN_TITLE_RX.search(ttl) is None) and (_LOCAL_OFFICIAL_IN_TITLE_RX.search(ttl) is None):
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
    "gukjenews.com": "국제뉴스",

    
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
AGRI_TRADE_PRESS = {"한국농어민신문", "농수축산신문", "농업정보신문", "팜&마켓"}
AGRI_TRADE_HOSTS = {"agrinet.co.kr", "farmnmarket.com", "afnews.co.kr"}

# 중간: 농업 전문지/지방/중소/연구·지자체
MID_PRESS_HINTS = (
    '농업', '팜', '축산', '유통', '식품', '경남', '전북', '전남', '충북', '충남', '강원', '제주',
)

LOW_QUALITY_PRESS = {
    # 지나치게 가십/클릭 유도 성향이 강한 경우(필요 시 추가)
    # '포인트데일리',
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


def _sort_key_major_first(a: Article):
    # 점수(관련성/품질)를 1순위로, 매체 티어는 2순위로 반영
    return (a.score, press_priority(a.press, a.domain), a.pub_dt_kst)


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
    r = http_session().get(url, headers=github_api_headers(token), params={"ref": ref}, timeout=30)
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
    """GitHub Contents API로 파일 생성/업데이트.
    - 409(sha mismatch) 발생 시: 최신 sha를 다시 가져와 1회 재시도한다(동시 실행/중복 실행 대비).
    """
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    last_err = None
    for attempt in range(2):
        r = SESSION.put(url, headers=github_api_headers(token), json=payload, timeout=30)
        if r.ok:
            return r.json()

        # sha mismatch conflict → refetch sha and retry once
        if r.status_code == 409 and attempt == 0:
            try:
                _raw, latest_sha = github_get_file(repo, path, token, ref=branch)
            except Exception:
                latest_sha = None
            if latest_sha:
                payload["sha"] = latest_sha
                continue

        last_err = r
        break

    if last_err is not None:
        log.error("[GitHub PUT ERROR] %s", last_err.text)
        last_err.raise_for_status()
    raise RuntimeError("GitHub PUT failed without response")  # should not happen

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
            r = http_session().get(url, headers=headers, params=params, timeout=25)

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
def naver_web_search(query: str, display: int = 10, start: int = 1, sort: str = "date"):
    """Naver Web(웹문서) 검색: 기사에 언급된 보고서/자료(예: KREI 이슈+)를 보완 수집."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set")
    url = "https://openapi.naver.com/v1/search/webkr.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": query, "display": display, "start": start, "sort": sort}

    last_err = None
    for attempt in range(max(1, NAVER_MAX_RETRIES)):
        try:
            _naver_throttle()
            r = http_session().get(url, headers=headers, params=params, timeout=25)

            data = None
            try:
                data = r.json()
            except Exception:
                data = None

            is_rate = (r.status_code == 429) or (isinstance(data, dict) and str(data.get("errorCode", "")) == "012")
            if r.ok and not is_rate:
                return data if isinstance(data, dict) else {"items": []}

            if is_rate:
                ra = 0.0
                try:
                    ra = float(r.headers.get("Retry-After", "0") or 0)
                except Exception:
                    ra = 0.0
                backoff = ra if ra > 0 else min(NAVER_BACKOFF_MAX_SEC, (1.0 * (2 ** attempt)) + random.uniform(0.0, 0.4))
                time.sleep(backoff)
                continue

            last_err = RuntimeError(f"Naver web API error: status={r.status_code} body={r.text[:300]}")
            backoff = min(NAVER_BACKOFF_MAX_SEC, (0.8 * (2 ** attempt)) + random.uniform(0.0, 0.3))
            time.sleep(backoff)
        except Exception as e:
            last_err = e
            backoff = min(NAVER_BACKOFF_MAX_SEC, (0.8 * (2 ** attempt)) + random.uniform(0.0, 0.3))
            time.sleep(backoff)

    log.warning("[WARN] naver_web_search failed: %s", last_err)
    return {"items": []}


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
    "사과", "배", "감귤", "포도", "딸기", "복숭아", "고추", "오이", "쌀",
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
    "논", "이앙", "벼멸구", "멸구", "먹노린재", "멸강나방",
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
def is_relevant(title: str, desc: str, dom: str, url: str, section_conf: dict, press: str) -> bool:
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

    def _reject(reason: str) -> bool:
        # debug: collect why an item was filtered out
        dbg_add_filter_reject(key, reason, ttl, url, dom, press)
        return False

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

    # 오피니언/사설/칼럼은 브리핑 대상에서 제외
    ttl_l = ttl.lower()
    if any(w.lower() in ttl_l for w in OPINION_BAN_TERMS):
        return _reject("opinion_or_editorial")

    # ✅ 사건/역사/정치성(예: 제주4.3) 인터뷰/스토리는 원예 브리핑 핵심 목적과 무관하므로 전체 섹션에서 배제
    if any(t in ttl_l for t in ("제주4.3", "제주4·3", "4.3의", "4·3")):
        return _reject("hardblock_jeju43_any_section")


    # 공통 제외(광고/구인/부동산 등)
    if any(k in text for k in BAN_KWS):
        return _reject("ban_keywords")

    # ✅ 제외 품목(현재 관심 제외): 마늘/양파 등은 스크래핑 대상에서 제외
    if any(w in text for w in EXCLUDED_ITEMS):
        return _reject("excluded_items")
    # ✅ '멜론' 동음이의어(음원 플랫폼) 오탐 차단:
    # - '먹는 멜론' 맥락(재배/출하/작황/농가/도매시장 등)일 때만 통과
    if "멜론" in text and not is_edible_melon_context(text):
        return _reject("melon_non_edible_context")
    # ✅ '피망' 동음이의어(게임/브랜드) 오탐 차단:
    # - 채소/농업 맥락일 때만 통과
    if "피망" in text and not is_edible_pimang_context(text):
        return _reject("pimang_non_edible_context")
    # ✅ '사과' 동음이의어(사과대/사과문 등) 오탐 차단: 과일/시장 맥락일 때만 통과
    if "사과" in text and not is_edible_apple_context(text):
        return _reject("apple_non_edible_context")


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
    if livestock_core and (livestock_hits >= 1) and (horti_hits_pre == 0) and (horti_sc_pre < 1.2):
        return _reject("livestock_only")

    # ✅ 해외 원예/화훼 업계 '원격 해외' 기사(국내 맥락 없음)는 실무와 거리가 멀어 제외
    if key in ("supply", "dist") and is_remote_foreign_horti(text):
        return _reject("remote_foreign_horti")


    # (미리) 원예/도매 맥락 점검( must_terms 예외처리에 사용 )
    horti_sc = best_horti_score(ttl, desc)

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

    # (강제 컷) 전력/에너지/유틸리티 '도매시장/수급' 동음이의어 오탐 차단
    energy_hits = count_any(text, [t.lower() for t in ENERGY_CONTEXT_TERMS])
    # 전력/에너지 문맥이 강한데(>=2) 농업/원예 문맥이 전무하면, '도매시장/수급' 단어가 있어도 비농산물로 판단
    if energy_hits >= 2 and agri_ctx_hits == 0 and horti_core_hits == 0 and market_hits > 0 and horti_sc < 1.8:
        return _reject("energy_market_offtopic")

    # dist에서 '도매시장'은 전력/금융 등에서도 흔히 등장한다.
    # - 농산물 유통 디스앰비규에이터가 없고 원예 점수도 낮으면(dist 목적과 무관) 제외
    if key == "dist" and ("도매시장" in text):
        has_disambig = any(t in text for t in AGRI_WHOLESALE_DISAMBIGUATORS)
        if (not has_disambig) and (agri_ctx_hits == 0) and (horti_core_hits == 0) and (horti_sc < 2.0):
            return _reject("dist_wholesale_ambiguous_no_agri")

    # supply에서도 '전력 수급/에너지 가격' 류는 '수급/가격' 단어로 오탐되므로 컷
    if key == "supply" and energy_hits >= 2 and agri_ctx_hits == 0 and horti_core_hits == 0 and horti_sc < 1.8:
        return _reject("energy_supply_offtopic")
    if off_hits >= 2 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.6:
        return _reject("hard_offtopic_no_agri_context")

    # dist는 '선별/저온/유통' 같은 단어가 바이오/의과학 기사에도 등장해 누수가 잦다.
    # 오프토픽(바이오/의과학/플랫폼 등) 신호가 1개라도 있고 농업/시장 맥락이 없으면 강하게 컷한다.
    if key == "dist" and off_hits >= 1 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 2.2:
        return _reject("dist_offtopic_no_agri_context")

    # 금융/산업 기사(농협은행/증권/주가/실적 등) 오탐 차단
    fin_hits = count_any(text, [t.lower() for t in FINANCE_STRICT_TERMS])
    if fin_hits >= 1 and agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.8:
        return _reject("finance_strict_no_agri_context")

    # 서울경제(sedaily) 등 경제지 일반 기사 오탐 방지:
    # - 경제/정책 섹션 검색 시 '농협/가격' 등의 단어로 비관련 기사가 섞이는 경우가 있어,
    #   원예/도매/정책 강신호가 없는 경우는 컷한다.
    if normalize_host(dom).endswith("sedaily.com"):
        if agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 1.8:
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

        local_ok = (market_hits >= 2) or (has_wholesale and horti_core_hits >= 2) or (has_apc and has_infra and horti_sc >= 1.6)
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
            # policy는 도메인 override가 있음
            if not policy_domain_override(dom, text):
                return _reject("must_terms_fail_policy")
        else:
            # supply/dist에서 APC/산지유통/화훼 현장성이 강하면 must_terms 미통과라도 살린다
            dist_soft_ok = (market_hits >= 1) or has_apc_agri_context(text) or ("산지유통센터" in text) or ("원예농협" in text) or ("화훼" in text) or ("절화" in text) or ("자조금" in text)
            if not ((horti_sc >= 2.0) or (horti_core_hits >= 3) or dist_soft_ok):
                return _reject("must_terms_fail")

    # (핵심) 원예수급 관련성 게이트:
    # - 네이버 검색 쿼리의 동음이의어(배=배터리/배당, 밤=야간 등)로 인한 오탐을 강하게 차단
    if key == "supply":
        # 공급(supply) 섹션은 '범용 단어(가격/물량/재고)'만 있는 산업/IT 기사를 강하게 차단한다.
        # 통과 조건(택1):
        # - 품목/원예 점수(horti_sc)가 충분히 강함
        # - 도매/산지유통/시장 맥락(market_hits) 존재
        # - 농업/농산물 맥락(agri_ctx_hits) + 수급 신호(signal_hits) 동시 존재
        supply_ok = (horti_sc >= 1.3) or (market_hits >= 1) or (agri_ctx_hits >= 1 and signal_hits >= 1)
        if not supply_ok:
            return _reject("supply_context_gate")

        # URL이 IT/테크 섹션인데 농업/시장 맥락이 약하면 컷(범용 단어 오탐 방지)
        if any(p in _path for p in ("/it/", "/tech/", "/future/", "/science/", "/game/", "/culture/")):
            if agri_ctx_hits == 0 and market_hits == 0 and horti_sc < 2.2:
                return _reject("supply_tech_path_no_agri")

    # 정책(policy): 공식 도메인/정책브리핑이 아닌 경우 '농식품/농산물 맥락' 필수 + 경제/금융 정책 오탐 차단
    if key == "policy":
        is_official = policy_domain_override(dom, text) or (normalize_host(dom) in OFFICIAL_HOSTS) or any(normalize_host(dom).endswith("." + h) for h in OFFICIAL_HOSTS)

        if not is_official:
            policy_signal_terms = ["가격 안정", "성수품", "할인지원", "할당관세", "검역", "원산지", "수입", "수출", "관세", "도매시장", "온라인 도매시장", "유통", "수급"]
            agri_base = count_any(text, [t.lower() for t in ("농식품", "농산물", "농업")])
            sig = count_any(text, [t.lower() for t in policy_signal_terms])
            if not ((horti_sc >= 1.4) or (market_hits >= 1) or (agri_base >= 1 and sig >= 1)):
                return _reject("policy_context_gate")

        # 금융/산업 일반 정책 오탐 차단
        policy_off = ["금리", "주택", "부동산", "코스피", "코스닥", "주식", "채권", "가상자산", "원화", "환율", "반도체", "배터리"]
        if any(w in text for w in policy_off):
            if not ((horti_sc >= 1.8) or (market_hits >= 1) or ("농산물" in text and "가격" in text)):
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

        # 소프트/하드 신호 분리(일반어: 브랜드/통합/조화/꽃 등은 제거)
        dist_soft = ["산지유통", "산지유통센터", "원예농협", "과수농협", "판매농협", "작목반", "화훼", "절화", "자조금", "하나로마트", "온라인 도매시장"]
        dist_hard = ["가락시장", "도매시장", "공판장", "공영도매시장", "청과", "경락", "경락가", "경매", "반입",
                     "중도매인", "시장도매인",
                     "선별", "저온", "저온저장", "저장고", "ca저장", "물류",
                     "원산지", "부정유통", "단속",
                     "검역", "통관", "수출"]
        soft_hits = count_any(text, [t.lower() for t in dist_soft])
        hard_hits = count_any(text, [t.lower() for t in dist_hard])

        # APC는 농업 문맥일 때만 soft 신호로 카운트
        if has_apc_agri_context(text):
            soft_hits += 1

        if (soft_hits + hard_hits) < 1:
            return _reject("dist_context_gate")

        # ✅ 가장 중요한 원칙: '농산물/원예' 앵커가 없고(agri_anchor_hits==0),
        # 도매시장/산지유통/품목 점수도 약하면 일반 물류/경제 기사로 보고 컷
        if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 1.6:
            return _reject("dist_no_agri_anchor")

        # URL이 IT/테크 섹션인데 농업 맥락이 약하면 컷
        if any(p in _path for p in ("/it/", "/tech/", "/future/", "/science/", "/game/", "/culture/")):
            if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 2.2:
                return _reject("dist_tech_path_no_agri")

        # '산지유통/APC/농협/화훼' 같은 소프트 신호만 있을 땐,
        # 인프라/유통 강신호(준공/가동/선별/저온/저장/물류/원산지/검역/수출 등) + 농업 앵커/품목 신호가 함께 있어야 통과
        if hard_hits == 0:
            infra_terms = ("준공", "완공", "가동", "확충", "확대", "선별", "저온", "저온저장", "저장고", "ca저장", "물류", "원산지", "검역", "수출")
            has_infra = any(w in text for w in infra_terms)

            # soft-only는 (인프라 + (농업앵커 or 품목점수)) 또는 (품목점수 매우 강함 + soft 2개 이상)에서만 허용
            if not ((has_infra and (agri_anchor_hits >= 1 or horti_sc >= 1.9)) or (horti_sc >= 2.8 and soft_hits >= 2)):
                return _reject("dist_soft_without_infra")
# 병해충/방제(pest) 섹션 정교화: 농업 맥락 없는 방역/생활해충/벼 방제 오탐 제거 + 신호 강도 조건
    if key == "pest":
        agri_ctx_hits = count_any(text, [t.lower() for t in PEST_AGRI_CONTEXT_TERMS])
        if agri_ctx_hits < 1:
            return _reject("pest_no_agri_context")

        rice_hits = count_any(text, [t.lower() for t in PEST_RICE_TERMS])
        strict_hits = count_any(text, [t.lower() for t in PEST_STRICT_TERMS])
        weather_hits = count_any(text, [t.lower() for t in PEST_WEATHER_TERMS])

        # 벼 방제 단독은 제외(원예/과수와의 연관이 희박)
        if rice_hits >= 1 and strict_hits < 1 and weather_hits < 1:
            return _reject("pest_rice_only")

        # 방제/병해충 신호가 너무 약하면 제외
        if (strict_hits + weather_hits) < 1:
            return False

    return True

def compute_rank_score(title: str, desc: str, dom: str, pub_dt_kst: datetime, section_conf: dict, press: str) -> float:
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
    market_ctx_terms = ["가락시장", "도매시장", "공판장", "청과", "경락", "경락가", "반입", "온라인 도매시장", "산지유통", "산지유통센터"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    strength = agri_strength_score(text)
    korea = korea_context_score(text)
    offp = off_topic_penalty(text)

    # 기본: 강신호(원예수급/유통/정책/방제) 기반
    score = 0.0
    score += 0.55 * strength
    score += 0.25 * korea
    score -= 0.70 * offp

    # 섹션별 키워드 가중치
    key = section_conf["key"]
    if key == "supply":
        score += weighted_hits(text, SUPPLY_WEIGHT_MAP)
        score += count_any(title_l, [t.lower() for t in SUPPLY_TITLE_CORE_TERMS]) * 1.2
    elif key == "dist":
        score += weighted_hits(text, DIST_WEIGHT_MAP)
        score += count_any(title_l, [t.lower() for t in DIST_TITLE_CORE_TERMS]) * 1.2
        # ✅ 농업 전문/현장 매체의 '시장 현장/대목장' 리포트는 유통(현장) 실무 체크 가치가 높다.
        # - 도매시장/APC 키워드가 없어도 '현장/대목장/판매' 맥락이면 점수를 보강해 하단 고착을 방지한다.
        if press in AGRI_TRADE_PRESS or normalize_host(dom) in AGRI_TRADE_HOSTS:
            if has_any(title_l, ["대목장", "대목", "현장", "어땠나", "판매", "시장", "반응"]):
                score += 3.2

        # dist에서 '지자체 공지/지역 단신'으로 판정되면 점수 감점(후순위/빈칸메우기용)
        if is_local_brief_text(title, desc, "dist"):
            score -= 3.5

    elif key == "policy":
        score += weighted_hits(text, POLICY_WEIGHT_MAP)
        score += count_any(title_l, [t.lower() for t in POLICY_TITLE_CORE_TERMS]) * 1.2
        # 공식 정책 소스 추가 가점
        if normalize_host(dom) in OFFICIAL_HOSTS or press in ("농식품부", "정책브리핑"):
            score += 3.0
    elif key == "pest":
        score += weighted_hits(text, PEST_WEIGHT_MAP)
        score += count_any(title_l, [t.lower() for t in PEST_TITLE_CORE_TERMS]) * 1.1

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
            score -= 7.0

    # 언론/기관 가중치
    score += press_weight(press, dom)

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
    score -= eventy_penalty(text, title, key)

    # 행정/정치 인터뷰성(도지사/시장 등) 기사 상단 배치 억제
    score -= governance_interview_penalty(text, title, key, horti_sc, market_hits)

    # 지역 단위 농협 동정성 기사 패널티(특히 농민신문 지역농협 소식 과다 방지)
    score -= local_coop_penalty(text, press, dom, key)
    # ✅ 제외 품목(마늘/양파)은 점수 산정 이전 단계에서 이미 컷되도록 설계.
    # 혹시라도 남아 들어오면 최하단으로 밀어내기 위해 강한 패널티를 부여한다.
    if any(w.lower() in text for w in EXCLUDED_ITEMS):
        score -= 100.0

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
_PROVINCE_RX = re.compile("|".join(map(re.escape, _PROVINCE_NAMES)))

# 시/군/구/읍/면 단위는 오탐이 많아 '도'는 제외하고, 단어 경계에 가깝게만 매칭
_CITY_COUNTY_RX = re.compile(r"(?:(?<=\s)|^)([가-힣]{2,})(시|군|구|읍|면)(?=\s|$|[\]\[\)\(\.,·!\?\"'“”‘’:/-])")

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

_PEST_CORE_TOKENS = {
    "병해충","방제","예찰","과수화상병","탄저병","냉해","동해","월동","약제","농약","살포","방역"
}
_SUPPLY_CORE_TOKENS = {"수급","가격","시세","경락","경락가","작황","출하","재고","저장","물량","반입"}
_SUPPLY_COMMODITY_TOKENS = {
    "사과","배","감귤","만감","한라봉","레드향","천혜향","포도","샤인머스캣","오이","고추","풋고추","쌀","비축미","단감","곶감"
}
_DIST_CORE_TOKENS = {"가락시장","도매시장","공판장","경락","경매","반입","중도매인","시장도매인","apc","물류","유통","온라인도매시장"}
_POLICY_CORE_TOKENS = {"대책","지원","할인","할인지원","할당관세","검역","통관","단속","고시","개정","보도자료","브리핑","예산","확대","연장"}

def _pest_region_key(title: str) -> str:
    """pest 섹션 중복 억제를 위한 대표 지역 키.
    - 읍/면 등 하위 단위가 있어도 같은 군/시/구로 묶이도록 우선 군/시/구를 선택
    - 없으면 첫 지역 토큰(도 등) 사용
    """
    t = title or ""
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
    same_region = bool(ra & rb)

    if section_key == "pest":
        common_core = len((ta & tb) & _PEST_CORE_TOKENS)
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
    "인터뷰", "대담", "신간", "책", "추천", "여행", "맛집",
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
        # 유통 코어는 '도매시장/산지유통/단속/검역' 등 강신호가 2개 이상 + 농산물/품목/시장 앵커가 필요
        dist_terms = ["가락시장", "도매시장", "공판장", "공영도매시장", "청과", "경락", "경락가", "경매", "반입",
                      "중도매인", "시장도매인", "온라인 도매시장",
                      "선별", "저온", "저온저장", "저장고", "ca저장", "물류",
                      "수출", "검역", "통관", "원산지", "부정유통", "단속", "산지유통", "산지유통센터"]
        dist_hits = count_any(text, [t.lower() for t in dist_terms])
        if has_apc_agri_context(text):
            dist_hits += 1
        # ✅ 지역 단신/지자체 공지형 기사(dist)는 핵심2로 올리지 않는다.
        if is_local_brief_text(a.title or "", a.description or "", section_key):
            return False

        # dist_hits(도매/유통 강신호)가 부족하면 기본적으로 코어 불가
        # 단, 농업 전문/현장 매체의 '시장 현장/대목장' 리포트는(유통 실무 체크 가치) 예외로 코어 허용
        if dist_hits < 2:
            if ((a.press in AGRI_TRADE_PRESS or normalize_host(a.domain or "") in AGRI_TRADE_HOSTS)
                    and has_any(title, ["대목장", "대목", "현장", "어땠나", "판매", "시장"])
                    and (horti_title_sc >= 1.4 or horti_sc >= 2.0)):
                return True
            return False
        return (agri_anchor_hits >= 1) or (horti_sc >= 2.0) or (market_hits >= 1)

    if section_key == "pest":
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

    # 1) 칼럼/사설/기고/인물/부고/인사류는 코어가 아니어도 상단 노출을 막는다(거의 항상 노이즈)
    hard_stop = ("칼럼", "사설", "오피니언", "기고", "독자기고", "기자수첩",
    "일기", "농막일기", "수필", "에세이", "연재", "기행", 
                 "인터뷰", "대담", "인물", "동정", "부고", "결혼", "취임", "인사", "개업")
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

    # 3) 섹션별 최소 맥락 재확인(아주 느슨하게)
    horti_sc = best_horti_score(a.title or "", a.description or "")
    horti_title_sc = best_horti_score(a.title or "", "")
    market_ctx_terms = ["가락시장", "도매시장", "공판장", "청과", "경락", "경락가", "반입", "중도매인", "시장도매인", "온라인 도매시장", "산지유통", "산지유통센터"]
    market_hits = count_any(text, [t.lower() for t in market_ctx_terms])
    if has_apc_agri_context(text):
        market_hits += 1

    if section_key == "policy":
        # 공식 소스는 최대한 살림
        try:
            if _is_policy_official(a):
                return True
        except Exception:
            pass
        # 정책 섹션은 최소한 '정책 액션' + '농식품 맥락'이 있어야 함(완화 버전)
        action_terms = ("대책", "지원", "할인", "할당관세", "검역", "고시", "개정", "단속", "브리핑", "보도자료", "예산")
        ctx_terms = ("농산물", "농식품", "농업", "과일", "채소", "수급", "가격", "유통", "원산지", "도매시장", "온라인 도매시장")
        if (not any(t.lower() in text for t in action_terms)) and (horti_sc < 1.6) and (market_hits == 0):
            return False
        if not any(t.lower() in text for t in ctx_terms):
            return False
        return True

    if section_key == "supply":
        # supply는 '품목/농산물 앵커' + '수급 신호' 결합이 약한 기사(단순 언급)를 하단으로 밀기 위해 더 보수적으로 본다.
        agri_anchor_terms = ("농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화", "청과")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])
        signal_terms = ("가격", "시세", "수급", "작황", "출하", "반입", "물량", "재고", "경락", "경매")

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
        if sig_hits == 0 and market_hits == 0 and horti_sc < 2.4:
            return False

        return True

    if section_key == "dist":
        # dist는 is_relevant가 있어도 '일반 물류/유통' 누수가 있어, 완화 게이트에서도 농산물 앵커를 한번 더 본다.
        agri_anchor_terms = ("농산물", "농업", "농식품", "원예", "과수", "과일", "채소", "화훼", "절화", "청과")
        agri_anchor_hits = count_any(text, [t.lower() for t in agri_anchor_terms])
        dist_hard = ("가락시장", "도매시장", "공판장", "공영도매시장", "청과", "경락", "경매", "반입",
                     "중도매인", "시장도매인", "온라인 도매시장",
                     "선별", "저온", "저온저장", "저장고", "ca저장", "원산지", "부정유통", "단속", "검역", "통관", "수출", "물류",
                     "산지유통", "산지유통센터")
        hard_hits = count_any(text, [t.lower() for t in dist_hard])
        if has_apc_agri_context(text):
            hard_hits += 1

        # 농업 앵커도 없고 시장/품목도 약하면 제외
        if agri_anchor_hits == 0 and market_hits == 0 and horti_sc < 1.6:
            return False
        # 하드 신호가 거의 없고 soft(추상)만 있으면 제외(억지 채움 방지)
        if hard_hits == 0 and horti_sc < 2.2:
            return False
        return True

    # pest는 is_relevant에서 맥락을 확인하므로, 여기서는 제목 품질만 관리
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
def _dynamic_threshold(candidates_sorted: list["Article"], section_key: str) -> float:
    """상위 기사 분포에 맞춰 동적으로 임계치를 잡아 '약한 기사'를 컷한다.
    - 최상위(best)에서 일정 마진을 빼고, 섹션별 최소선(BASE_MIN_SCORE)보다 낮아지지 않게.
    """
    if not candidates_sorted:
        return BASE_MIN_SCORE.get(section_key, 6.0)
    best = float(getattr(candidates_sorted[0], "score", 0.0) or 0.0)
    margin = 8.0 if section_key in ("supply", "policy", "dist") else 7.0
    return max(BASE_MIN_SCORE.get(section_key, 6.0), best - margin)

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

    candidates_sorted = sorted(candidates, key=_sort_key_major_first, reverse=True)

    # 동적 임계치: 상위권 점수가 낮은 날은 더 엄격하게 컷하여 '억지 채움'을 막는다
    thr = _dynamic_threshold(candidates_sorted, section_key)

    # 임계치 이상 후보만 사용(없으면 빈 리스트)
    pool = [a for a in candidates_sorted if a.score >= thr]


    # dist: 동일 이슈(APC 준공/개장, 서울시 부적합 유통 차단 등)가 여러 매체로 반복되는 경우가 많아
    # '이벤트 키'로 먼저 1차 클러스터링하여 중복으로 핵심이 밀리는 문제를 완화한다.
    if section_key == "dist":
        pool = _dedupe_by_event_key(pool, section_key)

    if not pool:
        return []

    # '최대 max_n'은 상한(cap)이며, 뒤쪽 약한 기사로 억지 채우기 방지를 위해 tail-cut을 둔다
    best_score = float(getattr(pool[0], "score", 0.0) or 0.0)
    # 섹션별로 꼬리 허용폭을 다르게(유통/현장(dist)은 누수 방지를 위해 더 엄격)
    tail_margin_by_section = {
        "supply": 3.6,
        "policy": 3.8,
        "dist": 3.4,
        "pest": 3.6,
    }
    tail_margin = tail_margin_by_section.get(section_key, 3.6)
    tail_cut = max(thr, best_score - tail_margin)

    # 출처 캡(지방/인터넷 과다 방지)
    tier_count = {1: 0, 2: 0, 3: 0}
    wire_count = 0  # 통신/온라인 서비스 과대표집 방지
    # 더 보수적으로(사용자 피드백: 지방지/인터넷 비중 과다)
    tier1_cap = 1
    tier2_cap = 2 if section_key in ("supply", "policy") else 3

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
    core: list[Article] = []
    used_title_keys: set[str] = set()
    used_url_keys: set[str] = set()

    def _dup_key(a: Article) -> str:
        return a.norm_key or a.canon_url or a.title_key

    def _already_used(a: Article) -> bool:
        k = _dup_key(a)
        return (k in used_title_keys) or (a.canon_url and a.canon_url in used_url_keys)

    def _mark_used(a: Article) -> None:
        used_title_keys.add(_dup_key(a))
        if a.canon_url:
            used_url_keys.add(a.canon_url)

    # 1) 엄격 코어 2개
    for a in pool:
        if len(core) >= 2:
            break
        if a.score < core_min:
            continue
        if _already_used(a):
            continue
        # dist: 지역 단신/공지형은 core 후보에서 제외(진짜 이슈가 밀리는 것을 방지)
        if section_key == "dist" and is_local_brief_text(a.title or "", a.description or "", section_key):
            continue
        if section_key == "supply" and is_flower_consumer_trend_context((a.title + " " + a.description).lower()):
            continue
        if not _headline_gate(a, section_key):
            continue
        if any(_is_similar_title(a.title_key, b.title_key) for b in core):
            continue
        if any(_is_similar_story(a, b, section_key) for b in core):
            continue
        if not _source_ok_local(a):
            continue

        a.is_core = True
        core.append(a)
        _mark_used(a)
        _source_take(a)

    # 2) 코어 부족 시: 약간 완화(여전히 임계치 이상 + 중복 제거) — 하지만 억지 채움 금지
    if len(core) < 2:
        for a in pool:
            if len(core) >= 2:
                break
            if a.score < thr:
                continue
            if _already_used(a):
                continue
            # dist: 지역 단신/공지형은 core 후보에서 제외
            if section_key == "dist" and is_local_brief_text(a.title or "", a.description or "", section_key):
                continue
            if section_key == "supply" and is_flower_consumer_trend_context((a.title + " " + a.description).lower()):
                continue
            if not _headline_gate_relaxed(a, section_key):
                continue
            if any(_is_similar_title(a.title_key, b.title_key) for b in core):
                continue
            if not _source_ok_local(a):
                continue

            a.is_core = True
            core.append(a)
            _mark_used(a)
            _source_take(a)

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
            text = (a.title + " " + a.description).lower()
            has_anchor = any(t.lower() in text for t in anchor_terms) or has_apc_agri_context(text)
            if not has_anchor:
                continue
            # 추가 안전장치: 농산물/원예 앵커가 약하면 '일반 물류/경제'로 보고 제외
            agri_anchor_hits = count_any(text, [t.lower() for t in ("농산물","농업","농식품","원예","과수","과일","채소","화훼","절화","청과")])
            if agri_anchor_hits == 0 and best_horti_score(a.title, a.description) < 1.8 and count_any(text, [t.lower() for t in ("가락시장","도매시장","공판장","공영도매시장","경락","경매","반입","온라인 도매시장","산지유통","산지유통센터")]) == 0:
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

    # 4) 나머지(최대 max_n): 임계치 이상 + 출처 캡 + 중복 제거
    for a in pool:
        if len(final) >= max_n:
            break
        if a in final:
            continue
        # dist: 이미 2건 이상 확보된 상태에서는 지역 단신/공지형 기사는 추가하지 않음(빈칸 메우기용으로만 허용)
        if section_key == "dist" and len(final) >= 2 and is_local_brief_text(a.title or "", a.description or "", section_key):
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
            if a.score < relax_cut:
                continue
            if _already_used(a):
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
            final.append(a)
            _mark_used(a)
            _source_take(a)
            need -= 1
    # 4.5) supply 보강: 화훼 소비/선물 트렌드(예: 레고 꽃다발/꽃다발 선물 트렌드)는
    # - 품목 및 수급 동향에서만 "비핵심"으로 0~1건 하단 편입
    # - core(핵심2)에는 절대 포함하지 않음
    if section_key == "supply" and len(final) < max_n:
        added = 0
        for a in pool:
            if added >= 1 or len(final) >= max_n:
                break
            if a in final:
                continue
            if _already_used(a):
                continue
            # 너무 낮은 점수(임계치 크게 하회)는 제외하되, 트렌드형은 약간 완화
            if a.score < max(thr - 0.6, 0.0):
                continue
            txt2 = (a.title + " " + a.description).lower()
            if not is_flower_consumer_trend_context(txt2):
                continue
            # 유통 프로모션/관광/연예/창업성 노이즈는 함수에서 제외됨
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

    # 마지막 안전장치: 동일 URL 중복 제거
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
# Optional RSS ingestion (공식/신뢰 소스 보강)
# - WHITELIST_RSS_URLS 환경변수에 RSS URL을 넣으면 해당 소스에서 기사 후보를 추가한다.
# - 기본은 OFF(빈 값)이며, 기존 Naver OpenAPI 기반 파이프라인은 그대로 유지한다.
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
    # RSS pubDate는 형식이 다양해 보수적으로 처리(실패 시 None)
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
                # 날짜가 없으면 윈도우 밖일 수 있으므로 제외
                continue
            if pub < start_kst or pub >= end_kst:
                continue
            dom = domain_of(link)
            if not dom or is_blocked_domain(dom):
                continue
            press = press_name_from_url(link)
            if not is_relevant(title, desc, dom, link, section_conf, press):
                continue
            canon = canonicalize_url(link)
            title_key = norm_title_key(title)
            topic = extract_topic(title, desc)
            norm_key = make_norm_key(canon, press, title_key)
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

def collect_candidates_for_section(section_conf: dict, start_kst: datetime, end_kst: datetime) -> list[Article]:
    queries = section_conf["queries"]
    items: list[Article] = []
    _local_dedupe = DedupeIndex()  # 섹션 내부 dedupe (전역은 최종 선택 단계에서)

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
                if not is_relevant(title, desc, dom, (origin or link), section_conf, press):
                    continue

                canon = canonicalize_url(origin or link)
                title_key = norm_title_key(title)
                topic = extract_topic(title, desc)
                norm_key = make_norm_key(canon, press, title_key)

                if not _local_dedupe.add_and_check(canon, press, title_key, norm_key):
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
    # Optional RSS candidates (신뢰 소스 보강)
    try:
        items.extend(collect_rss_candidates(section_conf, start_kst, end_kst))
    except Exception:
        pass

    # 최종 안전장치: 수집 경로(RSS/추가소스)와 무관하게 윈도우 밖 기사는 제외
    items = [a for a in items if (a.pub_dt_kst is not None) and (start_kst <= a.pub_dt_kst < end_kst)]

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

def _pick_best_web_item(items: list[dict], issue_no: int) -> dict | None:
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

def _maybe_add_krei_issues_to_policy(raw_by_section: dict[str, list["Article"]], start_kst: datetime, end_kst: datetime):
    """기사에서 언급된 KREI 이슈+ 보고서를 찾아 policy 섹션에 추가."""
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
            )
            a.score = compute_rank_score(a.title, a.description, dom, ref_pub, policy_conf, press)

            raw_by_section.setdefault("policy", []).append(a)

        except Exception as e:
            log.warning("[WARN] add KREI issue report failed: issue=%s err=%s", issue_no, e)

def collect_all_sections(start_kst: datetime, end_kst: datetime):
    raw_by_section: dict[str, list[Article]] = {}

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
                if (d in POLICY_DOMAINS) or (p in ("정책브리핑", "농식품부")):
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
        r = http_session().post(
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
        data = {
            "generated_at_kst": DEBUG_DATA.get("generated_at_kst"),
            "build_tag": DEBUG_DATA.get("build_tag"),
            "filter_rejects": list(DEBUG_DATA.get("filter_rejects", [])),
            "sections": dict(DEBUG_DATA.get("sections", {})),
        }

    # 요약(사유 카운트)
    reason_count = {}
    for r in data["filter_rejects"]:
        reason = r.get("reason", "unknown")
        reason_count[reason] = reason_count.get(reason, 0) + 1
    reason_items = sorted(reason_count.items(), key=lambda x: x[1], reverse=True)[:12]

    # JSON 링크(작성 옵션이 켜져 있을 때만)
    json_href = ""
    if DEBUG_REPORT_WRITE_JSON:
        json_href = build_site_url(site_path, f"debug/{report_date}.json")

    def _kv(label: str, value: str) -> str:
        return f"<span class='dbgkv'><b>{esc(label)}:</b> {esc(value)}</span>"

    # 섹션 테이블
    sec_blocks = []
    for sec_key, payload in data["sections"].items():
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
            <span class="muted">candidates={payload.get('total_candidates','?')} selected={payload.get('total_selected','?')} thr={payload.get('threshold','?')} core_min={payload.get('core_min','?')}</span>
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
      .dbgTableWrap {{ overflow:auto; border:1px solid var(--line); border-radius:12px; margin-top:8px; }}
      table.dbgTable {{ width:100%; border-collapse:collapse; font-size:12px; min-width:980px; }}
      table.dbgTable th, table.dbgTable td {{ border-bottom:1px solid var(--line); padding:6px 8px; vertical-align:top; }}
      table.dbgTable th {{ position:sticky; top:0; background:#f9fafb; z-index:1; }}
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

    def add_tag(t: str):
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
            line = "병해충 예찰/방제 동향을 점검하세요."
            add_tag("병해충")
        # 주요 품목 태그
        for c in ("사과","배","감귤","포도","딸기","고추","오이","토마토","파프리카"):
            if c in txt:
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
        for c in ("사과","배","감귤","포도","딸기","고추","오이","단감","곶감","샤인머스캣","만감"):
            if c in txt:
                add_tag(c)
    elif section_key == "dist":
        line = "도매시장·공판장·유통현장 이슈를 점검하세요."
        for t in ("가락시장","도매시장","공판장","경락","반입","온라인도매시장","원산지","검역","통관"):
            if t.lower() in txt:
                add_tag(t)
    elif section_key == "policy":
        line = "대책/지원/검역/단속 등 정책 변동 여부를 확인하세요."
        for t in ("지원","할인지원","할당관세","검역","통관","단속","고시","개정","브리핑"):
            if t.lower() in txt:
                add_tag(t)
    else:
        line = ""
    return (line, tags)

def render_daily_page(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict,
                      archive_dates_desc: list[str], site_path: str) -> str:
    # 상단 칩 카운트 + 섹션별 중요도 정렬
    chips = []
    total = 0
    for sec in SECTIONS:
        lst = sorted(by_section.get(sec["key"], []), key=lambda a: ((1 if getattr(a, "is_core", False) else 0),) + _sort_key_major_first(a), reverse=True)
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
        insight_line, insight_tags = make_section_insight(key, lst)

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
            body_html = "\n".join([render_card(a, getattr(a, "is_core", False)) for a in lst])

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

    
    debug_html = render_debug_report_html(report_date, site_path) if DEBUG_REPORT else ""

    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
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
        <input id="q" class="searchInput" type="search" placeholder="예: 사과 가격, 샤인머스캣 수급, 병해충 방제" />
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
    parts.append(f"농산물 뉴스 브리핑 ({report_date})")

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

    r = http_session().post(url, headers=headers, data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=30)
    if not r.ok:
        log.error("[KAKAO SEND ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()


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
    if FORCE_REPORT_DATE:
        d = _parse_force_report_date(FORCE_REPORT_DATE)
        return dt_kst(d, REPORT_HOUR_KST)

    if FORCE_END_NOW:
        return now_kst()

    n = now_kst()
    candidate = n.replace(hour=REPORT_HOUR_KST, minute=0, second=0, microsecond=0)
    if n < candidate:
        candidate -= timedelta(days=1)
    return candidate

def compute_window(repo: str, token: str, end_kst: datetime):
    prev_bd = previous_business_day(end_kst.date())
    prev_cutoff = dt_kst(prev_bd, REPORT_HOUR_KST)

    # ✅ 수동/테스트 재생성(FORCE_REPORT_DATE)에서는 state(last_end)에 영향받지 않도록
    #    '직전 영업일 07:00 ~ end_kst' 범위로 고정한다(휴일/주말 연휴 백필 포함).
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

def main():
    log.info("[BUILD] %s", BUILD_TAG)
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

    report_date = REPORT_DATE_OVERRIDE or end_kst.date().isoformat()

    # Kakao absolute URL
    base_url = get_pages_base_url(repo).rstrip("/")
    daily_url = f"{base_url}/archive/{report_date}.html"
    log.info("[INFO] Report date: %s (override=%s) -> %s", report_date, bool(REPORT_DATE_OVERRIDE), daily_url)

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
    save_search_index(repo, GH_TOKEN, search_idx, ssha)


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
