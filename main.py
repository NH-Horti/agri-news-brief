# main.py
# -*- coding: utf-8 -*-
"""
농산물 뉴스 브리핑 자동화 (GitHub Actions 운영용)

요구사항 반영 사항
1) 카톡 메시지에서 '브리핑 열기 -> gist' 구조 제거: 브리핑 내용을 카톡 대화창에 직접 발송(여러 메시지로 분할)
2) 각 기사 요약을 최소 2줄(핵심 요약 + 시사점/체크포인트)로 강화
3) 저품질/비주류 매체 배제(화이트리스트 우선, 부족하면 블랙리스트 완화)
4) 기사 있는 섹션을 앞으로 배치, 없는 섹션은 뒤로 배치 + '특이사항 없음' 명확 구분
5) 주말/공휴일에는 발송하지 않음. 다음 영업일에 직전 영업일~현재까지(휴일 포함) 범위로 확장 스크랩

필요 Secrets/ENV (GitHub Actions)
- OPENAI_API_KEY
- OPENAI_MODEL (옵션, 기본: gpt-5.2)
- NAVER_CLIENT_ID
- NAVER_CLIENT_SECRET
- KAKAO_REST_API_KEY (client_id)
- KAKAO_CLIENT_SECRET
- KAKAO_REFRESH_TOKEN
- GIST_ID (상태 저장용. 선택이지만 운영 권장)
- GH_GIST_TOKEN (gist scope 포함 토큰. 선택이지만 운영 권장)

주의/운영 팁
- 카카오 "기본 템플릿(text)" 본문 200자 제한 때문에, 브리핑은 여러 메시지로 나뉘어 도착합니다.
- 카카오 메시지 카드(버튼) 클릭 링크는 앱 설정의 "제품 링크"에 등록된 도메인만 허용될 수 있어,
  본문에는 원문 URL을 그대로 두되, 카드 링크는 안전하게 네이버 뉴스 검색(도메인 1개)로 통일합니다.
"""

from __future__ import annotations

import os
import re
import json
import time
import html
import math
import hashlib
import logging
import urllib.parse
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, date
from email.utils import parsedate_to_datetime

import requests

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------------------------
# Constants
# ---------------------------
KST = ZoneInfo("Asia/Seoul") if ZoneInfo else None
USER_AGENT = "agri-news-brief/1.0 (+github-actions)"

NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"
OPENAI_RESPONSES_API = "https://api.openai.com/v1/responses"
KAKAO_TOKEN_API = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_SEND_API = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

GITHUB_GIST_API = "https://api.github.com/gists"

# 카카오 카드(버튼) 클릭 시 이동 링크: 도메인 1개만 관리하기 위해 네이버 뉴스 검색으로 통일
KAKAO_CARD_FALLBACK_URL = "https://search.naver.com/search.naver?where=news&query=" + urllib.parse.quote("농산물 수급 가격")

# 카카오 text 본문 제한(문서상 200자)
KAKAO_TEXT_LIMIT = 200
# 실제 운영 안전 마진(번호/공백/개행 고려)
KAKAO_TEXT_SAFE = 190

# OpenAI 비용/속도 균형
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")  # low/medium/high
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "1200"))

# Naver API 호출 제한 대비
NAVER_DISPLAY_PER_QUERY = int(os.getenv("NAVER_DISPLAY_PER_QUERY", "50"))  # 1~100
NAVER_MAX_QUERIES_PER_SECTION = int(os.getenv("NAVER_MAX_QUERIES_PER_SECTION", "8"))
MAX_FETCH_ARTICLE_BODY = int(os.getenv("MAX_FETCH_ARTICLE_BODY", "18"))  # 본문 크롤 최대 수(속도/리밋 방지)

# 섹션별 최종 선정 기사 수(카톡 메시지 양 조절)
PICK_PER_SECTION = {
    "1. 품목 및 수급 동향": int(os.getenv("PICK_ITEMS_SUPPLY", "4")),
    "2. 주요 이슈 및 정책": int(os.getenv("PICK_ITEMS_POLICY", "3")),
    "3. 병해충 및 방제": int(os.getenv("PICK_ITEMS_PEST", "2")),
    "4. 유통 및 현장(APC/수출)": int(os.getenv("PICK_ITEMS_FIELD", "3")),
}

SECTION_ORDER = [
    "1. 품목 및 수급 동향",
    "2. 주요 이슈 및 정책",
    "3. 병해충 및 방제",
    "4. 유통 및 현장(APC/수출)",
]

# ---------------------------
# Source quality filtering
# ---------------------------
# 1) 우선 허용(화이트리스트). 너무 적으면 완화 모드로 블랙리스트만 적용.
ALLOWED_DOMAINS = {
    # 통신/방송/주요 종합지/경제지
    "yna.co.kr", "newsis.com", "kbs.co.kr", "imnews.imbc.com", "sbs.co.kr", "ytn.co.kr",
    "joongang.co.kr", "chosun.com", "donga.com", "hani.co.kr", "khan.co.kr",
    "mk.co.kr", "hankyung.com", "sedaily.com", "fnnews.com", "etnews.com",

    # 정부/유관
    "mafra.go.kr", "korea.kr", "policy.go.kr", "at.or.kr", "krei.re.kr", "naqs.go.kr",

    # 주요 지역지(대표급 일부)
    "ksilbo.co.kr", "busan.com", "kookje.co.kr", "kwnews.co.kr", "gnnews.co.kr",
    "jbnews.com", "jjan.kr", "idomin.com", "jjilbo.com",
}

# 제외(블랙리스트) - 사용자 언급 및 흔한 저품질/어그로성
BLOCKED_DOMAINS = {
    "wikitree.co.kr",
    "thetravelnews.co.kr",
    "donghaengmedia.net",
    "sidae.com",
    "topstarnews.net",
    "insight.co.kr",
}
# 제목/요약에 특정 매체명이 박혀오는 경우 보조 차단
BLOCKED_PATTERNS = [
    r"위키트리", r"동행미디어", r"\b시대\b", r"인사이트",
]

# ---------------------------
# Relevance / Season filtering
# ---------------------------
# 너무 "원예수급부 관점"과 거리가 먼(지자체 환급/행사/축제/홍보) 기사 억제
LOW_RELEVANCE_HINTS = [
    "온누리상품권", "환급", "축제", "행사", "기부", "나눔", "홍보", "공모전", "체험", "박람회",
    "맛집", "레시피", "관광", "지역화폐", "상품권",
]
# 반대로 수급/정책/시장 관련 핵심 단서 (이게 하나도 없으면 걸러냄)
HIGH_RELEVANCE_HINTS = [
    "가격", "시세", "도매", "경락", "물량", "수급", "출하", "저장", "재고", "작황", "생산량",
    "수입", "할당관세", "검역", "물가", "할인", "도매시장", "가락시장", "공판장",
    "APC", "선별", "CA저장", "수출", "방제", "병해충", "화상병", "탄저", "동해", "냉해",
]

# 철 지난(수확기 회고 등) 억제: 최근 기사라도 내용이 “10월 수확기” 중심이면 제외
OUT_OF_SEASON_HINTS = [
    "10월", "11월", "추석", "가을 수확", "수확기", "햇과일", "햇사과", "햇배",
]

# ---------------------------
# Keyword maps for section routing
# ---------------------------
SECTION_KEYWORDS = {
    "1. 품목 및 수급 동향": [
        "사과", "배", "단감", "떫은감", "곶감", "둥시",
        "감귤", "한라봉", "레드향", "천혜향", "만감류",
        "참다래", "키위", "포도", "샤인머스캣", "복숭아", "자두", "매실", "유자", "밤",
        "풋고추", "오이", "애호박",
        "쌀", "절화", "화훼",
        "저장", "저장량", "재고", "도매가격", "경락가", "시세", "작황", "생산량", "출하",
        "기후변화", "재배지", "북상", "강원도",
    ],
    "2. 주요 이슈 및 정책": [
        "온라인 도매시장", "도매시장", "허위거래", "이상거래", "전수조사",
        "할인", "할인지원", "물가", "물가안정", "비축미", "방출", "수입", "할당관세", "검역", "시장개방",
        "가락시장", "휴무", "경매", "재개",
        "기후변화", "재배적지", "대체작물", "아열대",
    ],
    "3. 병해충 및 방제": [
        "과수화상병", "화상병", "약제", "신청", "마감", "궤양", "골든타임",
        "기계유유제", "월동", "해충", "탄저병", "방제", "냉해", "동해",
    ],
    "4. 유통 및 현장(APC/수출)": [
        "농협", "APC", "스마트", "AI 선별", "선별기", "CA저장", "저장시설", "공판장",
        "도매시장", "가락시장", "유통", "물류",
        "수출", "수출실적", "농식품", "해외", "검역",
    ],
}

# Search queries per section (짧게 여러 번 -> 기사 수 확보)
SEARCH_QUERIES = {
    "1. 품목 및 수급 동향": [
        "사과 저장량 가격", "배 저장량 도매가격", "단감 시세 저장", "곶감 가격 생산량", "떫은감 탄저병 곶감",
        "감귤 한라봉 레드향 천혜향 시세", "참다래 키위 가격", "샤인머스캣 가격", "풋고추 오이 애호박 가격",
        "쌀 산지 가격 비축미", "절화 졸업 입학 가격",
        "기후변화 사과 재배지 북상 강원도",
    ],
    "2. 주요 이슈 및 정책": [
        "농산물 온라인 도매시장 허위거래", "온라인 도매시장 이상거래 전수조사",
        "농산물 할인지원 연장 3월", "할당관세 수입 과일", "검역 완화 수입 과일",
        "가락시장 설 휴무 경매 재개",
        "농산물 물가 안정 대책",
    ],
    "3. 병해충 및 방제": [
        "과수화상병 약제 신청 마감", "과수화상병 궤양 제거 골든타임",
        "기계유유제 월동 해충 방제", "탄저병 예방 방제", "동해 냉해 대비 과수",
    ],
    "4. 유통 및 현장(APC/수출)": [
        "농협 APC 스마트 선별기", "CA 저장 APC", "공판장 도매시장 동향",
        "가락시장 휴무 일정 경매 재개", "농식품 수출 실적 1월", "배 수출 딸기 수출 실적",
    ],
}


# ---------------------------
# Data structures
# ---------------------------
@dataclass
class Article:
    uid: str
    section: str
    title: str
    description: str
    pub_dt_kst: datetime
    naver_link: str
    origin_link: str
    domain: str
    body_text: str = ""


# ---------------------------
# Utils
# ---------------------------
def now_kst() -> datetime:
    if KST:
        return datetime.now(tz=KST)
    # fallback
    return datetime.now()

def to_kst(dt: datetime) -> datetime:
    if KST and dt.tzinfo is not None:
        return dt.astimezone(KST)
    return dt

def clean_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""

def sha1_short(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def is_korean_holiday(d: date) -> bool:
    """
    공휴일 판단: holidays 패키지 사용 가능하면 KR 공휴일 적용, 없으면 주말만.
    """
    try:
        import holidays  # type: ignore
        kr = holidays.KR()
        return d in kr
    except Exception:
        return False

def is_business_day(d: date) -> bool:
    # 주말 + 공휴일 제외
    if is_weekend(d):
        return False
    if is_korean_holiday(d):
        return False
    return True

def clamp_text(s: str, limit: int) -> str:
    s = (s or "").rstrip()
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 1)] + "…"

def looks_low_relevance(text: str) -> bool:
    t = text or ""
    low = any(k in t for k in LOW_RELEVANCE_HINTS)
    high = any(k in t for k in HIGH_RELEVANCE_HINTS)
    # low가 강하고 high가 전혀 없으면 제외
    return low and (not high)

def looks_out_of_season(text: str) -> bool:
    t = text or ""
    # "10월/11월/추석/수확기" 중심이면 제외, 단 '저장/전정/설 이후' 등 현재 키워드가 같이 있으면 통과
    out = any(k in t for k in OUT_OF_SEASON_HINTS)
    current_ok = any(k in t for k in ["저장", "전정", "설", "저장량", "재고", "현재", "최근"])
    return out and (not current_ok)

def match_section(title_desc: str) -> Optional[str]:
    """
    키워드 기반 섹션 매칭(최다 점수).
    """
    text = title_desc
    scores = {sec: 0 for sec in SECTION_ORDER}
    for sec in SECTION_ORDER:
        for kw in SECTION_KEYWORDS.get(sec, []):
            if kw and kw in text:
                scores[sec] += 1
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] == 0:
        return None
    return best[0]

def source_score(domain: str) -> int:
    """
    간단 신뢰도 점수(중복 시 선택용)
    """
    d = domain
    if d == "yna.co.kr":
        return 100
    if d in {"kbs.co.kr", "imnews.imbc.com", "sbs.co.kr", "ytn.co.kr"}:
        return 90
    if d in {"joongang.co.kr", "chosun.com", "donga.com", "hani.co.kr", "khan.co.kr"}:
        return 85
    if d in {"mk.co.kr", "hankyung.com", "sedaily.com", "fnnews.com", "etnews.com"}:
        return 80
    if d in {"mafra.go.kr", "korea.kr", "policy.go.kr", "at.or.kr", "krei.re.kr", "naqs.go.kr"}:
        return 95
    if d in ALLOWED_DOMAINS:
        return 70
    return 50

def title_similarity(a: str, b: str) -> float:
    """
    아주 단순한 중복 이슈 감지(공백 토큰 자카드).
    """
    ta = set(re.findall(r"[0-9가-힣A-Za-z]+", a))
    tb = set(re.findall(r"[0-9가-힣A-Za-z]+", b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


# ---------------------------
# Gist state (optional but recommended)
# ---------------------------
def gist_get_state(gist_id: str, token: str) -> Dict:
    url = f"{GITHUB_GIST_API}/{gist_id}"
    r = requests.get(url, headers={"Authorization": f"token {token}", "User-Agent": USER_AGENT}, timeout=20)
    r.raise_for_status()
    data = r.json()
    files = data.get("files", {})
    if "state.json" in files and files["state.json"].get("content"):
        try:
            return json.loads(files["state.json"]["content"])
        except Exception:
            return {}
    return {}

def gist_put_state(gist_id: str, token: str, state: Dict, archive_text: Optional[str] = None) -> None:
    url = f"{GITHUB_GIST_API}/{gist_id}"
    files_payload = {
        "state.json": {"content": json.dumps(state, ensure_ascii=False, indent=2)}
    }
    # 운영상 디버깅/기록용: 최신 브리핑을 gist에 저장(사용자 클릭용으로 쓰지 않음)
    if archive_text is not None:
        files_payload["latest_brief.txt"] = {"content": archive_text}
    payload = {"files": files_payload}
    r = requests.patch(
        url,
        headers={"Authorization": f"token {token}", "User-Agent": USER_AGENT},
        json=payload,
        timeout=20,
    )
    r.raise_for_status()


# ---------------------------
# Kakao token + send
# ---------------------------
def kakao_refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    # client_secret이 설정되어 있다면 포함
    if client_secret:
        data["client_secret"] = client_secret

    r = requests.post(
        KAKAO_TOKEN_API,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        data=data,
        timeout=20,
    )
    r.raise_for_status()
    j = r.json()
    access_token = j.get("access_token")
    if not access_token:
        raise RuntimeError(f"Kakao token refresh failed: {j}")
    return access_token

def kakao_send_text(access_token: str, text: str) -> None:
    """
    카카오 기본 템플릿(text)로 '나에게 보내기' 발송.
    text는 최대 200자 제한이 있으므로 호출 전에 분할/절삭 필요.
    """
    template_object = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": KAKAO_CARD_FALLBACK_URL,
            "mobile_web_url": KAKAO_CARD_FALLBACK_URL
        },
        "button_title": "뉴스 검색"
    }

    r = requests.post(
        KAKAO_MEMO_SEND_API,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template_object, ensure_ascii=False)},
        timeout=20,
    )
    r.raise_for_status()

def split_for_kakao(text: str, safe_limit: int = KAKAO_TEXT_SAFE) -> List[str]:
    """
    200자 제한을 넘지 않도록, 줄 단위로 최대한 자연스럽게 분할.
    """
    text = (text or "").strip()
    if len(text) <= safe_limit:
        return [text]

    lines = text.splitlines()
    chunks: List[str] = []
    cur = ""
    for ln in lines:
        if not ln:
            # 빈 줄은 가급적 유지
            candidate = (cur + "\n").strip("\n") if cur else ""
            if len(candidate) <= safe_limit:
                cur = candidate
            continue

        if not cur:
            cur = ln
            continue

        candidate = cur + "\n" + ln
        if len(candidate) <= safe_limit:
            cur = candidate
        else:
            if cur:
                chunks.append(cur)
            # ln 자체가 너무 길면 강제 절삭
            if len(ln) > safe_limit:
                chunks.append(clamp_text(ln, safe_limit))
                cur = ""
            else:
                cur = ln

    if cur:
        chunks.append(cur)

    # 그래도 혹시 넘는 경우 2차 절삭
    final = [clamp_text(c, safe_limit) for c in chunks if c.strip()]
    return final


# ---------------------------
# Naver News Search API
# ---------------------------
def naver_search_news(client_id: str, client_secret: str, query: str, display: int, start: int = 1) -> List[Dict]:
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": "date",
    }
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "User-Agent": USER_AGENT,
    }
    r = requests.get(NAVER_NEWS_API, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("items", [])

def parse_pubdate_to_kst(pub_date_str: str) -> Optional[datetime]:
    try:
        dt = parsedate_to_datetime(pub_date_str)
        if dt.tzinfo is None:
            return None
        return to_kst(dt)
    except Exception:
        return None

def fetch_naver_article_body(naver_link: str, timeout: int = 15) -> str:
    """
    Naver 뉴스 링크(news.naver.com)면 비교적 일관된 구조로 본문 추출 가능.
    다른 링크면 빈 문자열 반환.
    """
    if "news.naver.com" not in (naver_link or ""):
        return ""
    try:
        r = requests.get(naver_link, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        r.raise_for_status()
        html_text = r.text

        # BeautifulSoup 있으면 우선 사용
        try:
            from bs4 import BeautifulSoup  # type: ignore
            soup = BeautifulSoup(html_text, "html.parser")

            # 구형/신형 레이아웃 대응
            candidates = [
                soup.select_one("#dic_area"),
                soup.select_one("#articleBodyContents"),
                soup.select_one("article#dic_area"),
            ]
            for c in candidates:
                if c and c.get_text(strip=True):
                    t = c.get_text(" ", strip=True)
                    t = re.sub(r"\s+", " ", t).strip()
                    return t
        except Exception:
            pass

        # fallback: 정규식(최후)
        m = re.search(r'id="dic_area".*?>(.*?)</div>', html_text, re.DOTALL)
        if m:
            txt = re.sub(r"<[^>]+>", " ", m.group(1))
            txt = re.sub(r"\s+", " ", txt).strip()
            return txt

        return ""
    except Exception:
        return ""


# ---------------------------
# Article collection + filtering
# ---------------------------
def collect_articles(start_kst: datetime, end_kst: datetime) -> List[Article]:
    naver_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    naver_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    if not (naver_id and naver_secret):
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 이(가) 필요합니다.")

    raw_items: List[Dict] = []
    # 섹션별 여러 쿼리 실행
    for sec in SECTION_ORDER:
        queries = SEARCH_QUERIES.get(sec, [])[:NAVER_MAX_QUERIES_PER_SECTION]
        for q in queries:
            try:
                items = naver_search_news(
                    naver_id, naver_secret,
                    query=q,
                    display=NAVER_DISPLAY_PER_QUERY,
                    start=1
                )
                raw_items.extend(items)
                time.sleep(0.15)  # 소폭 rate-limit 완화
            except Exception as e:
                logging.warning(f"Naver query failed [{sec}] q='{q}': {e}")

    # 정리/필터링
    candidates: List[Article] = []
    for it in raw_items:
        title = clean_html(it.get("title", ""))
        desc = clean_html(it.get("description", ""))
        pub_dt = parse_pubdate_to_kst(it.get("pubDate", ""))
        if not pub_dt:
            continue
        if not (start_kst <= pub_dt < end_kst):
            continue

        naver_link = it.get("link", "") or ""
        origin_link = it.get("originallink", "") or naver_link
        dom = domain_of(origin_link)

        # 매체/패턴 차단
        if dom in BLOCKED_DOMAINS:
            continue
        if any(re.search(p, title) for p in BLOCKED_PATTERNS):
            continue

        # 시즈널/관련성 필터
        combined = f"{title} {desc}"
        if looks_low_relevance(combined):
            continue
        if looks_out_of_season(combined):
            continue

        # 섹션 추정
        sec = match_section(combined) or "2. 주요 이슈 및 정책"  # 미매칭은 정책/이슈로 우선(너무 품목 편중 방지)
        uid = sha1_short((origin_link or "") + "|" + title)

        candidates.append(Article(
            uid=uid,
            section=sec,
            title=title,
            description=desc,
            pub_dt_kst=pub_dt,
            naver_link=naver_link,
            origin_link=origin_link,
            domain=dom,
        ))

    # 1차 중복 제거(링크/제목 유사)
    candidates = dedupe_articles(candidates)

    # 매체 품질 필터(화이트리스트 우선)
    strict = [a for a in candidates if a.domain in ALLOWED_DOMAINS]
    # 너무 적으면 완화: 블랙리스트만 유지
    if len(strict) >= 8:
        candidates = strict
        logging.info(f"[FILTER] strict allowlist applied: {len(candidates)} articles")
    else:
        logging.info(f"[FILTER] strict allowlist too few ({len(strict)}). fallback to blocklist-only: {len(candidates)} articles")

    # Naver 기사 본문 확보(가능한 것만, 상위 몇 개)
    candidates = sorted(candidates, key=lambda x: x.pub_dt_kst, reverse=True)
    for a in candidates[:MAX_FETCH_ARTICLE_BODY]:
        if a.naver_link and "news.naver.com" in a.naver_link:
            a.body_text = fetch_naver_article_body(a.naver_link)

    return candidates

def dedupe_articles(arts: List[Article]) -> List[Article]:
    # 링크 기준 1차
    by_url: Dict[str, Article] = {}
    for a in arts:
        key = (a.origin_link or a.naver_link or "")[:300]
        if not key:
            key = a.uid
        if key in by_url:
            # 같은 링크면 더 신뢰도 높은 쪽/더 최신을 남김
            prev = by_url[key]
            if (source_score(a.domain), a.pub_dt_kst) > (source_score(prev.domain), prev.pub_dt_kst):
                by_url[key] = a
        else:
            by_url[key] = a
    unique = list(by_url.values())

    # 제목 유사도 기반 2차(같은 이슈 여러 매체)
    unique_sorted = sorted(unique, key=lambda x: (x.section, x.pub_dt_kst), reverse=True)
    kept: List[Article] = []
    for a in unique_sorted:
        dup = False
        for b in kept:
            if a.section == b.section and title_similarity(a.title, b.title) >= 0.75:
                # 같은 섹션 내 유사 제목 -> 더 신뢰도 높은 것만
                if source_score(a.domain) > source_score(b.domain):
                    kept.remove(b)
                    kept.append(a)
                dup = True
                break
        if not dup:
            kept.append(a)
    return kept


# ---------------------------
# OpenAI summarization
# ---------------------------
def openai_summarize(selected: List[Article], start_kst: datetime, end_kst: datetime) -> Dict[str, List[Dict]]:
    """
    selected 기사들에 대해:
    - 2줄 요약(line1, line2)
    - 링크(origin_link)
    를 생성. 출력은 섹션별 리스트로 반환.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 이(가) 필요합니다.")

    # 입력 구성(기사 본문이 있으면 일부 포함)
    items = []
    for a in selected:
        body = (a.body_text or "").strip()
        if body:
            body = body[:1200]
        items.append({
            "id": a.uid,
            "section": a.section,
            "title": a.title,
            "desc": a.description,
            "published_kst": a.pub_dt_kst.strftime("%Y-%m-%d %H:%M"),
            "source_domain": a.domain,
            "body": body,
            "url": a.origin_link or a.naver_link,
        })

    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "section": {"type": "string"},
                        "line1": {"type": "string"},
                        "line2": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["id", "section", "line1", "line2", "url"],
                    "additionalProperties": False,
                }
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }

    sys = (
        "당신은 농협중앙회 원예수급부 팀장 결재용 '농산물 뉴스 브리핑' 작성자입니다.\n"
        "목표: 각 기사마다 카카오톡 메시지 1건(짧게)으로 전달 가능한 2줄 요약을 생성합니다.\n"
        "규칙:\n"
        "- line1: 1문장, 핵심 사실/이슈를 압축(너무 포괄 금지)\n"
        "- line2: 1문장, 원예수급/유통 관점의 시사점 또는 체크포인트(숫자/시장 반응/현장 대응 중심)\n"
        "- 두 줄 모두 과장 없이 팩트 기반. '추정/가능성'이면 그렇게 명시.\n"
        "- 각 line은 65자 내외로 최대한 짧게.\n"
        "- 저품질/홍보성/축제성 내용은 강조하지 말고, 있더라도 요약은 중립적으로.\n"
        "- 출력은 반드시 JSON.\n"
    )

    user = (
        f"기간(KST): {start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}\n"
        f"아래 기사 목록을 섹션을 유지한 채로 2줄 요약으로 변환하세요.\n\n"
        f"{json.dumps(items, ensure_ascii=False)}"
    )

    payload = {
        "model": DEFAULT_OPENAI_MODEL,
        "input": [
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "agri_brief_items",
                "strict": True,
                "schema": schema,
            }
        },
        "reasoning_effort": OPENAI_REASONING_EFFORT,
        "verbosity": "low",
        "max_output_tokens": OPENAI_MAX_OUTPUT_TOKENS,
        "store": False,
    }

    r = requests.post(
        OPENAI_RESPONSES_API,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if r.status_code >= 400:
        try:
            logging.error("[OpenAI ERROR BODY] %s", json.dumps(r.json(), ensure_ascii=False, indent=2))
        except Exception:
            logging.error("[OpenAI ERROR TEXT] %s", r.text)
        r.raise_for_status()

    resp = r.json()
    out_text = extract_responses_output_text(resp)
    data = json.loads(out_text)

    # 섹션별로 묶기
    by_sec: Dict[str, List[Dict]] = {s: [] for s in SECTION_ORDER}
    for it in data.get("items", []):
        sec = it.get("section") or ""
        if sec not in by_sec:
            sec = "2. 주요 이슈 및 정책"
        by_sec[sec].append(it)

    return by_sec

def extract_responses_output_text(resp_json: Dict) -> str:
    """
    Responses API 응답에서 output_text를 합쳐 반환
    """
    outs = resp_json.get("output", [])
    texts = []
    for item in outs:
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    texts.append(c.get("text", ""))
    return "".join(texts).strip()


# ---------------------------
# Build briefing & send
# ---------------------------
def pick_articles_by_section(arts: List[Article]) -> List[Article]:
    """
    섹션별 상위 N개 선정.
    - 점수: (섹션키워드 매칭 수) + (source_score 가중) + (최근성)
    """
    by_sec: Dict[str, List[Article]] = {s: [] for s in SECTION_ORDER}
    for a in arts:
        by_sec[a.section].append(a)

    picked: List[Article] = []
    for sec in SECTION_ORDER:
        lst = by_sec.get(sec, [])
        if not lst:
            continue

        def score(a: Article) -> float:
            text = f"{a.title} {a.description}"
            kw_hits = sum(1 for kw in SECTION_KEYWORDS.get(sec, []) if kw in text)
            recency = a.pub_dt_kst.timestamp()
            return kw_hits * 10 + source_score(a.domain) + (recency / 1e10)

        lst_sorted = sorted(lst, key=score, reverse=True)
        picked.extend(lst_sorted[:PICK_PER_SECTION.get(sec, 2)])

    # 전체 중복 재확인
    picked = dedupe_articles(picked)

    # 너무 품목 편중 완화: 품목이 과도하면 정책/현장 쪽을 추가로 보정
    # (단, 실제로 기사가 없으면 강제하지 않음)
    sec_counts = {s: 0 for s in SECTION_ORDER}
    for a in picked:
        sec_counts[a.section] += 1

    supply = sec_counts["1. 품목 및 수급 동향"]
    others = len(picked) - supply
    if supply >= 6 and others <= 2:
        # 정책/현장에서 추가로 1~2개 더(있으면)
        for sec in ["2. 주요 이슈 및 정책", "4. 유통 및 현장(APC/수출)", "3. 병해충 및 방제"]:
            if sec_counts[sec] >= PICK_PER_SECTION.get(sec, 2):
                continue
            pool = [a for a in arts if a.section == sec and a not in picked]
            pool = sorted(pool, key=lambda x: (source_score(x.domain), x.pub_dt_kst), reverse=True)
            for a in pool[:2]:
                picked.append(a)
                sec_counts[sec] += 1
            if len(picked) >= 12:
                break

    return picked

def build_messages(
    summarized: Dict[str, List[Dict]],
    articles_index: Dict[str, Article],
    start_kst: datetime,
    end_kst: datetime
) -> List[str]:
    """
    카카오로 보낼 '짧은 메시지' 리스트 생성.
    - 섹션 중 기사 있는 섹션을 먼저 배치
    - 각 기사: 2줄 요약 + 링크(원문)
    - 섹션 구분/특이사항 없음 표시
    """
    msgs: List[str] = []

    header = (
        f"[농산물 뉴스 Brief]\n"
        f"{start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} (KST)\n"
        f"※ 주말/공휴일 미발송 시 기간이 자동 확장됩니다."
    )
    msgs.append(header)

    # 섹션 순서 재배치: 기사 있는 섹션 -> 없는 섹션
    non_empty = [s for s in SECTION_ORDER if summarized.get(s)]
    empty = [s for s in SECTION_ORDER if not summarized.get(s)]
    ordered_sections = non_empty + empty

    for sec in ordered_sections:
        msgs.append(f"== {sec} ==")

        items = summarized.get(sec, [])
        if not items:
            # 구분을 위해 빈 줄 한 번
            msgs.append("특이사항 없음")
            continue

        for it in items:
            uid = it.get("id", "")
            line1 = clean_html(it.get("line1", ""))
            line2 = clean_html(it.get("line2", ""))
            url = (it.get("url") or "").strip()

            # 링크가 너무 길면(드물지만) naver_link로 대체
            if uid in articles_index:
                a = articles_index[uid]
                if not url:
                    url = (a.origin_link or a.naver_link).strip()

            block = f"- {line1}\n- {line2}\n{url}".strip()
            # 카카오 200자 제한 대응: 줄 단위 축약
            if len(block) > KAKAO_TEXT_SAFE:
                # 1) line2를 우선 축약
                line2 = clamp_text(line2, 55)
                block = f"- {line1}\n- {line2}\n{url}".strip()
            if len(block) > KAKAO_TEXT_SAFE:
                # 2) line1 축약
                line1 = clamp_text(line1, 55)
                block = f"- {line1}\n- {line2}\n{url}".strip()
            if len(block) > KAKAO_TEXT_SAFE:
                # 3) 그래도 길면 line2 제거(최후)
                block = f"- {line1}\n{url}".strip()
                block = clamp_text(block, KAKAO_TEXT_SAFE)

            msgs.append(block)

    return msgs

def send_brief_to_kakao(msgs: List[str]) -> None:
    client_id = os.getenv("KAKAO_REST_API_KEY", "").strip()
    client_secret = os.getenv("KAKAO_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not (client_id and refresh_token):
        raise RuntimeError("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN 이(가) 필요합니다.")

    access_token = kakao_refresh_access_token(client_id, client_secret, refresh_token)

    # 각 메시지를 200자 제한에 맞춰 쪼개서 발송
    sent = 0
    for m in msgs:
        parts = split_for_kakao(m, KAKAO_TEXT_SAFE)
        for p in parts:
            if not p.strip():
                continue
            kakao_send_text(access_token, p)
            sent += 1
            time.sleep(0.2)
    logging.info(f"[KAKAO] sent {sent} message(s)")

# ---------------------------
# Main
# ---------------------------
def compute_window(now: datetime, run_hour_kst: int = 7) -> Tuple[datetime, datetime]:
    """
    end_kst: 오늘 run_hour_kst 시각(분/초 0)으로 고정.
    GitHub Actions가 약간 일찍(06:59) 돌면 전일 07:00을 end로 잡음.
    """
    end = now.replace(hour=run_hour_kst, minute=0, second=0, microsecond=0)
    if now < end:
        end = end - timedelta(days=1)
    return (end - timedelta(hours=24), end)

def main():
    run_hour = int(os.getenv("RUN_HOUR_KST", "7"))
    now = now_kst()
    default_start, end_kst = compute_window(now, run_hour_kst=run_hour)

    # 영업일이 아니면 발송 생략(상태도 업데이트하지 않음 -> 다음 영업일에 기간 자동 확장)
    if not is_business_day(end_kst.date()):
        logging.info(f"[SKIP] Not a business day in KR: {end_kst.date()} (weekend/holiday)")
        return

    # 상태 로드(가능하면 gist)
    gist_id = os.getenv("GIST_ID", "").strip()
    gist_token = os.getenv("GH_GIST_TOKEN", "").strip()
    state = {}
    if gist_id and gist_token:
        try:
            state = gist_get_state(gist_id, gist_token)
        except Exception as e:
            logging.warning(f"[GIST] read failed, fallback to default window: {e}")
            state = {}

    last_end_str = state.get("last_end_kst")
    if last_end_str:
        try:
            start_kst = datetime.fromisoformat(last_end_str)
            if start_kst.tzinfo is None and KST:
                start_kst = start_kst.replace(tzinfo=KST)
        except Exception:
            start_kst = default_start
    else:
        start_kst = default_start

    # 안전: start >= end면 종료
    if start_kst >= end_kst:
        logging.info(f"[EXIT] start_kst >= end_kst: {start_kst} >= {end_kst}")
        return

    logging.info(f"[INFO] Window KST: {start_kst} ~ {end_kst}")

    # 기사 수집
    articles = collect_articles(start_kst, end_kst)
    if not articles:
        # 그래도 카톡으로 "기사 없음" 안내는 보냄(운영 확인용)
        msgs = [
            f"[농산물 뉴스 Brief]\n{start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} (KST)",
            "수집된 기사가 없습니다(필터/키워드/기간을 확인하세요)."
        ]
        send_brief_to_kakao(msgs)
        # 상태 업데이트는 하되(중복 발송 방지), gist 실패해도 크래시 금지
        state_out = {"last_end_kst": end_kst.isoformat()}
        if gist_id and gist_token:
            try:
                gist_put_state(gist_id, gist_token, state_out, archive_text="\n\n".join(msgs))
            except Exception as e:
                logging.warning(f"[GIST] write failed: {e}")
        return

    # 섹션별 픽
    picked = pick_articles_by_section(articles)

    # OpenAI 요약(2줄)
    summarized_by_section = openai_summarize(picked, start_kst, end_kst)

    # uid -> Article index
    idx = {a.uid: a for a in picked}

    # 메시지 구성(기사 있는 섹션 먼저)
    msgs = build_messages(summarized_by_section, idx, start_kst, end_kst)

    # 발송
    send_brief_to_kakao(msgs)

    # 상태 저장(다음 실행에서 기간 확장/중복 방지)
    state_out = {"last_end_kst": end_kst.isoformat()}
    if gist_id and gist_token:
        try:
            gist_put_state(gist_id, gist_token, state_out, archive_text="\n\n".join(msgs))
        except Exception as e:
            # gist 실패해도 발송은 성공했을 수 있으니 크래시 금지
            logging.warning(f"[GIST] write failed (non-fatal): {e}")

if __name__ == "__main__":
    main()
