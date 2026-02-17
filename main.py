# main.py
# -*- coding: utf-8 -*-
"""
Agri News Brief (KST 07:00) -> Kakao "나에게 보내기"

이번 버전 반영사항
1) [SKIP] 주말/공휴일에는 발송하지 않되(영업일만 발송), 다음 영업일에 누락 구간을 자동 포함
2) 공휴일 판정 오버라이드(특정 날짜를 강제로 영업일/공휴일로)
3) FORCE_SEND=1 이면 주말/공휴일이라도 강제 발송 (테스트/긴급용)
4) 카톡 메시지를 "여러 번" 대신 "한 번"으로 줄이기 옵션:
   - KAKAO_SEND_MODE=multi_text  : (기본) 긴 브리핑을 여러 메시지로 분할 전송
   - KAKAO_SEND_MODE=single_text : 1개 메시지(핵심 2~3줄 + 상세보기 링크 1개)
   - KAKAO_SEND_MODE=single_list : 1개 메시지(리스트 템플릿 2~3개 카드 + 헤더 링크)
5) gist로 넘어가지 않게:
   - (권장) PUBLISH_MODE=github_pages 로 HTML 뷰어를 repo에 올리고 Pages 링크로 읽기
   - 카톡엔 BRIEF_VIEW_URL(= Pages URL)을 넣어 1번 클릭으로 보기

필수 환경변수 (Secrets)
- OPENAI_API_KEY
- KAKAO_REST_API_KEY         (카카오 앱 REST API 키)
- KAKAO_CLIENT_SECRET        (카카오 앱 Client Secret)
- KAKAO_REFRESH_TOKEN        (카카오 OAuth refresh_token)

선택 환경변수
- FORCE_SEND=1                      (테스트용)
- KAKAO_SEND_MODE=multi_text|single_text|single_list
- MAX_ARTICLES_PER_SECTION=3
- PUBLISH_MODE=none|github_pages
- BRIEF_VIEW_URL=https://...        (single_text/single_list 에서 상세보기 링크로 사용)
- PAGES_FILE_PATH=docs/brief.html   (repo에 업로드할 파일 경로)
- PAGES_BRANCH=main                 (업로드 대상 브랜치)
- STATE_BACKEND=gist|repo
- (STATE_BACKEND=gist일 때)
  - GIST_ID
  - GH_GIST_TOKEN
- (STATE_BACKEND=repo일 때)
  - STATE_FILE_PATH=.agri_state.json
  - (GitHub Actions 기본 제공 GITHUB_TOKEN 사용, workflow permissions: contents: write 필요)

매체 필터
- 기본: 메이저/공식 위주 "허용 리스트" 기반
- 필요시 아래 DEFAULT_ALLOWED_PRESS에 추가/삭제
"""

import os
import re
import json
import base64
import html
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlparse

import requests

KST = ZoneInfo("Asia/Seoul")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -----------------------------
# Kakao API endpoints
# -----------------------------
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_SEND_API = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

# -----------------------------
# OpenAI API endpoints
# -----------------------------
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")  # 사용자가 원한 gpt-5.2 기본
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "minimal")  # none/minimal/low/...
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "1200"))

# -----------------------------
# Behavior / Modes
# -----------------------------
FORCE_SEND = (os.getenv("FORCE_SEND", "0") == "1")
KAKAO_SEND_MODE = os.getenv("KAKAO_SEND_MODE", "multi_text")  # multi_text | single_text | single_list
MAX_ARTICLES_PER_SECTION = int(os.getenv("MAX_ARTICLES_PER_SECTION", "3"))

PUBLISH_MODE = os.getenv("PUBLISH_MODE", "none")  # none | github_pages
BRIEF_VIEW_URL = os.getenv("BRIEF_VIEW_URL", "").strip()  # single_* 모드에서 권장

PAGES_FILE_PATH = os.getenv("PAGES_FILE_PATH", "docs/brief.html")
PAGES_BRANCH = os.getenv("PAGES_BRANCH", "main")

STATE_BACKEND = os.getenv("STATE_BACKEND", "gist")  # gist | repo
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", ".agri_state.json")  # repo backend용

# Kakao default 텍스트 템플릿 표시 200자 가이드에 맞춰 안전 마진
KAKAO_TEXT_SOFT_LIMIT = int(os.getenv("KAKAO_TEXT_SOFT_LIMIT", "180"))

# -----------------------------
# Naver News search
# -----------------------------
NAVER_NEWS_SEARCH_URL = "https://search.naver.com/search.naver?where=news&sm=tab_opt&sort=1&photo=0&field=0&pd=3&ds=&de=&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so:dd,p:1d&query="

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

# -----------------------------
# Press filtering (tunable)
# -----------------------------
DEFAULT_ALLOWED_PRESS = [
    # 통신/방송
    "연합뉴스", "뉴시스", "KBS", "MBC", "SBS", "JTBC", "YTN", "연합뉴스TV",
    # 중앙지
    "조선일보", "중앙일보", "동아일보", "한겨레", "경향신문", "국민일보", "한국일보",
    "매일경제", "한국경제", "서울경제", "세계일보",
    "이데일리", "아시아경제", "헤럴드경제",
    # 농업/정책/공공
    "농민신문", "농수축산신문", "한국농어민신문",
    "정책브리핑", "농림축산식품부", "농식품부", "aT", "한국농수산식품유통공사",
]
DEFAULT_BLOCKED_PRESS = [
    "위키트리", "동행미디어", "시대", "인사이트", "톱스타뉴스"
]

ALLOWED_PRESS = [p.strip() for p in os.getenv("ALLOWED_PRESS", ",".join(DEFAULT_ALLOWED_PRESS)).split(",") if p.strip()]
BLOCKED_PRESS = [p.strip() for p in os.getenv("BLOCKED_PRESS", ",".join(DEFAULT_BLOCKED_PRESS)).split(",") if p.strip()]

# 도메인 기반(공식/직접 도메인)
DEFAULT_ALLOWED_DOMAINS = [
    "yna.co.kr", "news.kbs.co.kr", "imnews.imbc.com", "news.sbs.co.kr",
    "news.jtbc.co.kr", "www.chosun.com", "www.joongang.co.kr", "www.donga.com",
    "www.hani.co.kr", "www.khan.co.kr", "www.kmib.co.kr", "www.hankookilbo.com",
    "www.mk.co.kr", "www.hankyung.com", "www.sedaily.com",
    "www.edaily.co.kr", "www.asiae.co.kr", "biz.heraldcorp.com",
    # 정책/공공
    "www.korea.kr", "www.mafra.go.kr", "www.at.or.kr",
    # 네이버 호스팅(press 판별이 필요)
    "n.news.naver.com", "news.naver.com",
]
ALLOWED_DOMAINS = [d.strip() for d in os.getenv("ALLOWED_DOMAINS", ",".join(DEFAULT_ALLOWED_DOMAINS)).split(",") if d.strip()]


# -----------------------------
# Sections / Queries
# -----------------------------
SECTIONS = [
    ("품목 및 수급 동향", [
        "기후변화 사과 재배지 북상 강원도",
        "사과 저장량 도매가격",
        "배 저장량 도매가격",
        "단감 저장량 시세",
        "떫은감 탄저병 곶감 생산량 가격 둥시",
        "감귤 한라봉 레드향 천혜향 가격",
        "참다래 키위 가격",
        "샤인머스캣 포도 가격",
        "매실 개화 전망 냉해",
        "유자 가격",
        "밤 가격",
        "풋고추 오이 애호박 시설채소 가격 일조량 부족",
        "쌀 산지쌀값 비축미 방출",
        "절화 졸업 입학 시즌 꽃값",
    ]),
    ("주요 이슈 및 정책", [
        "농산물 온라인 도매시장 허위거래 이상거래 전수조사",
        "농산물 물가 할인 지원 연장",
        "할당관세 수입과일 검역 완화",
        "가락시장 휴무 경매 재개 일정",
    ]),
    ("병해충 및 방제", [
        "과수화상병 약제 신청 마감",
        "과수화상병 궤양 제거 골든타임",
        "기계유유제 살포 월동해충 방제",
        "탄저병 예방",
        "동해 냉해 대비 과수",
    ]),
    ("유통 및 현장(APC/수출)", [
        "농협 APC 스마트화 AI 선별기 CA 저장",
        "공판장 도매시장 산지유통 동향",
        "농식품 수출 실적 배 딸기 라면",
    ]),
]


# -----------------------------
# Holiday / Business day logic (with override)
# -----------------------------
def is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # 5=Sat, 6=Sun


def is_korean_holiday(d: date) -> bool:
    """
    한국 공휴일 판정.
    - holidays.KR() 사용 (설치/동작 문제시 주말만 스킵하도록 fallback)
    - 오판정 발생 시 OVERRIDE로 즉시 수정 가능
    """
    # 강제 오버라이드(필요 시 날짜 문자열 추가)
    OVERRIDE_FORCE_WORKDAY = {
        # "2026-02-17",  # 예: 이 날짜를 영업일로 강제
    }
    OVERRIDE_FORCE_HOLIDAY = {
        # "2026-xx-yy",
    }

    ds = d.isoformat()
    if ds in OVERRIDE_FORCE_WORKDAY:
        return False
    if ds in OVERRIDE_FORCE_HOLIDAY:
        return True

    try:
        import holidays  # type: ignore
        kr = holidays.KR()
        return d in kr
    except Exception:
        # holidays 라이브러리 없거나 오류 시: 공휴일 아님(주말만 스킵)
        return False


def is_business_day(d: date) -> bool:
    if is_weekend(d):
        return False
    if is_korean_holiday(d):
        return False
    return True


# -----------------------------
# State storage (gist or repo)
# -----------------------------
@dataclass
class State:
    last_end_kst_iso: str  # ISO datetime with tz


def gist_get_file(gist_id: str, token: str, filename: str) -> Optional[str]:
    url = f"https://api.github.com/gists/{gist_id}"
    r = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=20)
    if not r.ok:
        logging.error("[Gist GET ERROR] %s", r.text)
        r.raise_for_status()
    data = r.json()
    files = data.get("files", {})
    if filename in files:
        return files[filename].get("content")
    return None


def gist_update_files(gist_id: str, token: str, files_map: Dict[str, str]) -> None:
    url = f"https://api.github.com/gists/{gist_id}"
    payload = {"files": {fn: {"content": content} for fn, content in files_map.items()}}
    r = requests.patch(url, headers={"Authorization": f"token {token}"}, json=payload, timeout=20)
    if not r.ok:
        logging.error("[Gist PATCH ERROR] %s", r.text)
        r.raise_for_status()


def github_get_file(repo: str, path: str, token: str, ref: str = "main") -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (content_text, sha) or (None, None) if not found.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if r.status_code == 404:
        return None, None
    if not r.ok:
        logging.error("[GitHub GET ERROR] %s", r.text)
        r.raise_for_status()
    j = r.json()
    sha = j.get("sha")
    b64 = j.get("content", "")
    if j.get("encoding") == "base64" and b64:
        raw = base64.b64decode(b64).decode("utf-8", errors="replace")
        return raw, sha
    return None, sha


def github_put_file(repo: str, path: str, token: str, content_text: str, branch: str = "main", sha: Optional[str] = None, message: str = "Update file") -> None:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    b64 = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
    payload = {
        "message": message,
        "content": b64,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=20)
    if not r.ok:
        logging.error("[GitHub PUT ERROR] %s", r.text)
        r.raise_for_status()


def load_state(now_kst: datetime) -> State:
    default_last = (now_kst - timedelta(hours=24)).isoformat()

    if STATE_BACKEND == "repo":
        repo = os.getenv("GITHUB_REPOSITORY", "")
        token = os.getenv("GITHUB_TOKEN", "")
        if not repo or not token:
            logging.warning("[STATE repo] missing GITHUB_REPOSITORY/GITHUB_TOKEN -> fallback to default window")
            return State(last_end_kst_iso=default_last)
        raw, _sha = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
        if not raw:
            return State(last_end_kst_iso=default_last)
        try:
            j = json.loads(raw)
            return State(last_end_kst_iso=j.get("last_end_kst_iso", default_last))
        except Exception:
            return State(last_end_kst_iso=default_last)

    # gist backend
    gist_id = os.getenv("GIST_ID", "")
    token = os.getenv("GH_GIST_TOKEN", "")
    if not gist_id or not token:
        logging.warning("[STATE gist] missing GIST_ID/GH_GIST_TOKEN -> fallback to default window")
        return State(last_end_kst_iso=default_last)

    raw = gist_get_file(gist_id, token, "state.json")
    if not raw:
        return State(last_end_kst_iso=default_last)
    try:
        j = json.loads(raw)
        return State(last_end_kst_iso=j.get("last_end_kst_iso", default_last))
    except Exception:
        return State(last_end_kst_iso=default_last)


def save_state(state: State) -> None:
    if STATE_BACKEND == "repo":
        repo = os.getenv("GITHUB_REPOSITORY", "")
        token = os.getenv("GITHUB_TOKEN", "")
        if not repo or not token:
            logging.warning("[STATE repo] missing GITHUB_REPOSITORY/GITHUB_TOKEN -> cannot save")
            return
        current, sha = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
        _ = current  # unused
        content = json.dumps({"last_end_kst_iso": state.last_end_kst_iso}, ensure_ascii=False, indent=2)
        github_put_file(repo, STATE_FILE_PATH, token, content, branch=PAGES_BRANCH, sha=sha, message="Update agri-news state")
        return

    gist_id = os.getenv("GIST_ID", "")
    token = os.getenv("GH_GIST_TOKEN", "")
    if not gist_id or not token:
        logging.warning("[STATE gist] missing GIST_ID/GH_GIST_TOKEN -> cannot save")
        return
    content = json.dumps({"last_end_kst_iso": state.last_end_kst_iso}, ensure_ascii=False, indent=2)
    gist_update_files(gist_id, token, {"state.json": content})


# -----------------------------
# Kakao OAuth / Send
# -----------------------------
def kakao_refresh_access_token(refresh_token: str) -> str:
    rest_api_key = os.getenv("KAKAO_REST_API_KEY", "")
    client_secret = os.getenv("KAKAO_CLIENT_SECRET", "")
    if not rest_api_key or not client_secret:
        raise RuntimeError("Missing KAKAO_REST_API_KEY / KAKAO_CLIENT_SECRET")

    data = {
        "grant_type": "refresh_token",
        "client_id": rest_api_key,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    r = requests.post(KAKAO_TOKEN_URL, data=data, timeout=20)
    if not r.ok:
        logging.error("[Kakao token ERROR BODY] %s", r.text)
        r.raise_for_status()
    j = r.json()
    access = j.get("access_token")
    if not access:
        raise RuntimeError(f"Kakao token refresh failed: {j}")
    return access


def kakao_send_template(access_token: str, template_object: dict) -> None:
    r = requests.post(
        KAKAO_MEMO_SEND_API,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template_object, ensure_ascii=False)},
        timeout=20,
    )
    if not r.ok:
        logging.error("[Kakao send ERROR BODY] %s", r.text)
    else:
        logging.info("[Kakao send OK] %s", r.text)
    r.raise_for_status()


def kakao_send_text(access_token: str, text: str, fallback_url: str) -> None:
    template_object = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": fallback_url,
            "mobile_web_url": fallback_url,
        },
        "button_title": "바로 확인",
    }
    kakao_send_template(access_token, template_object)


def kakao_send_list(access_token: str, header_title: str, header_url: str, items: List[dict], button_title: str = "상세보기") -> None:
    """
    Default template 'list' : contents 2~3개 제한이 있어 top 3만 넣는 용도로 사용 권장.
    """
    template_object = {
        "object_type": "list",
        "header_title": header_title[:200],
        "header_link": {"web_url": header_url, "mobile_web_url": header_url},
        "contents": items[:3],  # 안전
        "button_title": button_title[:20],
    }
    kakao_send_template(access_token, template_object)


# -----------------------------
# Naver parsing helpers
# -----------------------------
def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_allowed_article(url: str, press_name: str) -> bool:
    """
    도메인 허용 or (네이버 호스팅일 경우 press_name 허용)
    """
    h = host_of(url)
    if any(h == d or h.endswith("." + d) for d in ALLOWED_DOMAINS):
        # 네이버 호스팅이면 press_name 체크 강화
        if h.endswith("naver.com"):
            if press_name and any(p in press_name for p in BLOCKED_PRESS):
                return False
            if press_name and any(p in press_name for p in ALLOWED_PRESS):
                return True
            # press_name을 못 뽑았으면 보수적으로 제외
            return False
        return True

    # 도메인이 허용 리스트 밖이면 press 기반으로 한 번 더 허용
    if press_name and any(p in press_name for p in BLOCKED_PRESS):
        return False
    if press_name and any(p in press_name for p in ALLOWED_PRESS):
        return True
    return False


def parse_naver_time_str(s: str, now_kst: datetime) -> Optional[datetime]:
    """
    Naver 뉴스 결과 시간 문자열 파싱:
    - '3시간 전', '15분 전'
    - '2026.02.17.'
    - '2026.02.17. 09:30'
    """
    s = normalize_space(s)
    if not s:
        return None

    m = re.search(r"(\d+)\s*분\s*전", s)
    if m:
        return now_kst - timedelta(minutes=int(m.group(1)))

    m = re.search(r"(\d+)\s*시간\s*전", s)
    if m:
        return now_kst - timedelta(hours=int(m.group(1)))

    m = re.search(r"(\d+)\s*일\s*전", s)
    if m:
        return now_kst - timedelta(days=int(m.group(1)))

    # 2026.02.17. 09:30
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\.\s*(\d{2}):(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), tzinfo=KST)

    # 2026.02.17.
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\.", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, tzinfo=KST)

    return None


def fetch_naver_news(query: str, start_kst: datetime, end_kst: datetime, max_items: int = 10) -> List[dict]:
    """
    Naver 뉴스 검색 결과에서 기사 후보를 추출하고, 시간/매체 필터 후 반환.
    """
    now_kst = end_kst
    url = NAVER_NEWS_SEARCH_URL + quote_plus(query)
    r = requests.get(url, headers=HEADERS, timeout=20)
    if not r.ok:
        logging.warning("[Naver search fail] %s %s", r.status_code, r.text[:200])
        return []

    html_text = r.text

    # bs4 있으면 정확도 상승
    try:
        from bs4 import BeautifulSoup  # type: ignore
        soup = BeautifulSoup(html_text, "html.parser")
        items = soup.select("div.news_area")
        results = []
        for it in items:
            a = it.select_one("a.news_tit")
            if not a:
                continue
            link = a.get("href", "").strip()
            title = normalize_space(a.get("title") or a.get_text(" ", strip=True))

            # press
            press = ""
            press_el = it.select_one("a.info.press") or it.select_one("span.info.press")
            if press_el:
                press = normalize_space(press_el.get_text(" ", strip=True))

            # time
            time_str = ""
            info = it.select("span.info")
            # 보통 span.info 중에 날짜/시간이 섞여 있음
            for sp in info:
                t = normalize_space(sp.get_text(" ", strip=True))
                if "전" in t or re.search(r"\d{4}\.\d{2}\.\d{2}\.", t):
                    time_str = t
                    break
            dt = parse_naver_time_str(time_str, now_kst)
            if not dt:
                continue

            if not (start_kst <= dt < end_kst):
                continue

            if not is_allowed_article(link, press):
                continue

            results.append({
                "query": query,
                "title": title,
                "url": link,
                "press": press,
                "published_kst": dt.isoformat(),
            })
            if len(results) >= max_items:
                break
        return results
    except Exception:
        # fallback: 매우 단순 추출(정확도 낮음) -> 운영에선 bs4 설치 권장
        results = []
        # title+url
        for m in re.finditer(r'<a[^>]+class="news_tit"[^>]+href="([^"]+)"[^>]*title="([^"]+)"', html_text):
            link, title = m.group(1), html.unescape(m.group(2))
            results.append({"query": query, "title": normalize_space(title), "url": link, "press": "", "published_kst": ""})
            if len(results) >= max_items:
                break
        return results


# -----------------------------
# Dedupe / Group
# -----------------------------
def dedupe_articles(articles: List[dict]) -> List[dict]:
    """
    - 동일 URL 제거
    - (제목 유사) 간단 중복 제거
    """
    seen_url = set()
    out = []
    seen_title_key = set()
    for a in articles:
        u = a.get("url", "")
        t = normalize_space(a.get("title", ""))
        if not u or not t:
            continue
        if u in seen_url:
            continue
        seen_url.add(u)

        key = re.sub(r"[^0-9a-zA-Z가-힣]+", "", t.lower())[:60]
        if key in seen_title_key:
            continue
        seen_title_key.add(key)

        out.append(a)
    return out


def collect_articles_by_section(start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    by_section: Dict[str, List[dict]] = {sec: [] for sec, _ in SECTIONS}

    for sec, queries in SECTIONS:
        collected: List[dict] = []
        for q in queries:
            items = fetch_naver_news(q, start_kst, end_kst, max_items=8)
            collected.extend(items)
        collected = dedupe_articles(collected)

        # 섹션당 상한
        by_section[sec] = collected[:MAX_ARTICLES_PER_SECTION]
        logging.info("[Collect] %s: %d", sec, len(by_section[sec]))

    return by_section


# -----------------------------
# OpenAI summarization (robust fallback)
# -----------------------------
def openai_summarize(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    """
    각 기사에 대해 2~3문장 요약 + 실무포인트 1줄을 생성.
    실패 시 press/title 기반 간이 요약으로 fallback.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logging.warning("[OpenAI] Missing OPENAI_API_KEY -> fallback summaries")
        return fallback_summaries(articles_by_section)

    # 입력 payload 최소화(비용 절감)
    compact = []
    for sec, arts in articles_by_section.items():
        for a in arts:
            compact.append({
                "section": sec,
                "title": a.get("title", ""),
                "press": a.get("press", ""),
                "url": a.get("url", ""),
                "published_kst": a.get("published_kst", ""),
            })

    prompt = f"""
너는 농협중앙회 원예수급부 실무자를 위한 '농산물 뉴스 브리핑 편집자'다.
아래 기사 목록(제목/매체/URL/발행시각)만 보고, 각 기사에 대해:
- summary: 2~3문장(정책/수급/현장에 직접 연결되게, 군더더기 없이)
- point: 실무자 관점 한 줄(예: "가격 급등 가능성", "현장 방제 선제 필요", "도매시장 일정 확인 필요")
를 작성해라.

중요:
- 추측/과장 금지. 제목으로 판단이 어려우면 '제목상' 표현으로 보수적으로.
- 동일 이슈 중복 느낌이면 point에서 "중복 이슈" 언급 말고, 그냥 핵심만.
- 출력은 JSON만.

기간(KST): {start_kst.isoformat()} ~ {end_kst.isoformat()}
기사 목록 JSON:
{json.dumps(compact, ensure_ascii=False)}
"""

    schema = {
        "name": "agri_brief_summaries",
        "schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "summary": {"type": "string"},
                            "point": {"type": "string"}
                        },
                        "required": ["url", "summary", "point"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["items"],
            "additionalProperties": False
        },
        "strict": True
    }

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "user", "content": prompt}
        ],
        "reasoning_effort": OPENAI_REASONING_EFFORT,
        "max_output_tokens": OPENAI_MAX_OUTPUT_TOKENS,
        "text": {
            "format": {
                "type": "json_schema",
                "json_schema": schema
            }
        },
    }

    try:
        r = requests.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if not r.ok:
            logging.error("[OpenAI ERROR BODY] %s", r.text)
            r.raise_for_status()

        data = r.json()

        # Responses API: output_text는 SDK에서만 편의 제공인 경우가 있어 output에서 파싱
        out_text = ""
        if isinstance(data, dict):
            if "output_text" in data and isinstance(data["output_text"], str):
                out_text = data["output_text"]
            else:
                # output -> message -> output_text
                for item in data.get("output", []) or []:
                    if item.get("type") == "message":
                        for c in item.get("content", []) or []:
                            if c.get("type") == "output_text":
                                out_text += c.get("text", "")

        out_text = out_text.strip()
        if not out_text:
            logging.warning("[OpenAI] empty output -> fallback")
            return fallback_summaries(articles_by_section)

        j = json.loads(out_text)
        mapping = {it["url"]: {"summary": it["summary"], "point": it["point"]} for it in j.get("items", [])}

        # merge back
        merged: Dict[str, List[dict]] = {}
        for sec, arts in articles_by_section.items():
            merged[sec] = []
            for a in arts:
                u = a.get("url", "")
                extra = mapping.get(u, {})
                aa = dict(a)
                aa["summary"] = normalize_space(extra.get("summary", "")) or fallback_one_summary(a)
                aa["point"] = normalize_space(extra.get("point", "")) or ""
                merged[sec].append(aa)
        return merged

    except Exception as e:
        logging.warning("[OpenAI summarize fail] %s -> fallback", str(e))
        return fallback_summaries(articles_by_section)


def fallback_one_summary(a: dict) -> str:
    press = a.get("press", "").strip()
    title = a.get("title", "").strip()
    if press:
        return f"{press} 보도: {title}"
    return title


def fallback_summaries(articles_by_section: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    merged: Dict[str, List[dict]] = {}
    for sec, arts in articles_by_section.items():
        merged[sec] = []
        for a in arts:
            aa = dict(a)
            aa["summary"] = fallback_one_summary(a)
            aa["point"] = ""
            merged[sec].append(aa)
    return merged


# -----------------------------
# Render brief
# -----------------------------
def render_full_brief_text(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> str:
    """
    '카톡 복붙용' 전체 브리핑 텍스트(Plain text).
    - 기사 없는 섹션은 뒤로 밀고, 아예 비표시(요청사항 반영)
    """
    # 섹션 정렬: 기사 있는 섹션 먼저
    nonempty = [(sec, arts) for sec, arts in articles_by_section.items() if arts]
    empty = [(sec, arts) for sec, arts in articles_by_section.items() if not arts]
    ordered = nonempty + empty

    lines = []
    lines.append(f"[농산물 뉴스 Brief] ({start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} KST)")
    lines.append("")

    for sec, arts in ordered:
        if not arts:
            # 요청: 없는 기사는 안 보여줘도 됨 -> 섹션 자체도 생략
            continue

        lines.append(f"■ {sec}")
        for a in arts:
            title = normalize_space(a.get("title", ""))
            press = normalize_space(a.get("press", ""))
            summary = normalize_space(a.get("summary", ""))
            point = normalize_space(a.get("point", ""))

            # 2~3문장 요약(한 줄로 너무 길어지면 줄바꿈)
            body = summary
            if point:
                body = f"{summary} / 포인트: {point}"

            # 카톡에서 보기 좋게 2줄 정도로 분리
            lines.append(f"- {press} | {title}")
            lines.append(f"  {body}")
            lines.append(f"  {a.get('url','')}")
            lines.append("")
        lines.append("")  # 섹션 구분

    return "\n".join(lines).strip() + "\n"


def build_single_highlight_message(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime, view_url: str) -> str:
    """
    single_text 모드: 200자 내외로 핵심+링크 1개
    """
    # 상위 3개 기사만 뽑아 한 줄 키포인트로
    tops = []
    for sec, arts in articles_by_section.items():
        for a in arts:
            tops.append((sec, a))
    tops = tops[:3]

    # 최대한 짧게 구성
    head = f"[농산물 브리핑] {end_kst.strftime('%m/%d')} 07시"
    pts = []
    for sec, a in tops:
        t = normalize_space(a.get("title", ""))
        # 너무 길면 자름
        t = (t[:28] + "…") if len(t) > 29 else t
        pts.append(f"- {t}")

    msg = head
    if pts:
        msg += "\n" + "\n".join(pts)

    if view_url:
        msg += f"\n상세: {view_url}"

    # 200자 가이드에 맞춰 과하면 절단(링크는 살리기)
    if len(msg) > 240:  # 줄바꿈/표시차 감안해 넉넉히
        if view_url:
            base = head + "\n" + "\n".join(pts[:2])
            base = (base[:160] + "…") if len(base) > 170 else base
            msg = base + f"\n상세: {view_url}"
        else:
            msg = msg[:220] + "…"
    return msg


def split_text_for_kakao(full_text: str, soft_limit: int = 180) -> List[str]:
    """
    multi_text 모드: 텍스트를 여러 메시지로 분할.
    - 기사 단위 블록을 최대한 유지
    """
    blocks = full_text.strip().split("\n\n")
    chunks = []
    current = ""
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        candidate = (current + "\n\n" + b).strip() if current else b
        if len(candidate) <= soft_limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # 단일 블록이 너무 길면 하드 컷
            if len(b) > soft_limit:
                # 링크가 있는 마지막 줄을 유지하려고 노력
                lines = b.splitlines()
                url_line = ""
                for ln in reversed(lines):
                    if ln.strip().startswith("http"):
                        url_line = ln.strip()
                        break
                trimmed = b[: max(0, soft_limit - (len(url_line) + 8))].rstrip()
                if url_line:
                    trimmed = trimmed + "\n" + url_line
                chunks.append(trimmed)
                current = ""
            else:
                current = b
    if current:
        chunks.append(current)
    return chunks


# -----------------------------
# Publish viewer (GitHub Pages)
# -----------------------------
def linkify(text: str) -> str:
    def repl(m):
        u = m.group(1)
        return f'<a href="{u}" target="_blank" rel="noopener noreferrer">{u}</a>'
    return re.sub(r"(https?://[^\s<]+)", repl, text)


def make_brief_html(full_text: str, title: str) -> str:
    escaped = html.escape(full_text)
    escaped = linkify(escaped).replace("\n", "<br>\n")
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
  body{{font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; margin: 18px; line-height: 1.45;}}
  .wrap{{max-width: 860px; margin:0 auto;}}
  .card{{border:1px solid #e5e7eb; border-radius:12px; padding:16px; background:#fff; box-shadow: 0 2px 10px rgba(0,0,0,.04);}}
  .meta{{color:#6b7280; font-size:14px; margin-bottom:12px;}}
  a{{word-break:break-all;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="meta">{html.escape(title)}</div>
    <div>{escaped}</div>
  </div>
</div>
</body>
</html>
"""


def publish_to_github_pages(html_text: str, commit_title: str) -> None:
    """
    repo의 PAGES_FILE_PATH 에 HTML을 업로드(또는 갱신).
    - GitHub Pages는 별도 설정 필요 (repo Settings > Pages)
    - workflow permissions 에 contents: write 필요
    """
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[Pages publish] missing GITHUB_REPOSITORY/GITHUB_TOKEN -> skip")
        return

    raw, sha = github_get_file(repo, PAGES_FILE_PATH, token, ref=PAGES_BRANCH)
    _ = raw
    github_put_file(
        repo=repo,
        path=PAGES_FILE_PATH,
        token=token,
        content_text=html_text,
        branch=PAGES_BRANCH,
        sha=sha,
        message=f"Publish brief viewer: {commit_title}"
    )
    logging.info("[Pages publish] updated %s on %s", PAGES_FILE_PATH, PAGES_BRANCH)


# -----------------------------
# Main
# -----------------------------
def main():
    now_kst = datetime.now(tz=KST)

    # end_kst = 현재시각(보통 Actions가 07:00에 실행)
    end_kst = now_kst

    state = load_state(end_kst)
    try:
        last_end = datetime.fromisoformat(state.last_end_kst_iso)
        if last_end.tzinfo is None:
            last_end = last_end.replace(tzinfo=KST)
    except Exception:
        last_end = end_kst - timedelta(hours=24)

    start_kst = last_end

    # window sanity
    if start_kst >= end_kst:
        start_kst = end_kst - timedelta(hours=24)

    logging.info("[INFO] Window KST: %s ~ %s", start_kst, end_kst)

    # 영업일 스킵 (FORCE_SEND 예외)
    if FORCE_SEND:
        logging.info("[FORCE_SEND] enabled: will send even on weekend/holiday")

    if (not FORCE_SEND) and (not is_business_day(end_kst.date())):
        logging.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date())
        # 스킵이면 state 저장하지 않음(다음 영업일에 누락구간 포함하기 위함)
        return

    # 1) Collect
    raw_by_section = collect_articles_by_section(start_kst, end_kst)

    # 2) Summarize
    enriched_by_section = openai_summarize(raw_by_section, start_kst, end_kst)

    # 3) Render
    full_text = render_full_brief_text(enriched_by_section, start_kst, end_kst)

    # 4) Publish viewer (optional)
    view_url = BRIEF_VIEW_URL
    if PUBLISH_MODE == "github_pages":
        title = f"농산물 뉴스 Brief ({start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} KST)"
        html_page = make_brief_html(full_text, title)
        publish_to_github_pages(html_page, commit_title=end_kst.strftime("%Y-%m-%d"))
        # view_url은 사용자가 환경변수로 넣어줘야 가장 확실 (Pages URL은 계정/설정 따라 다름)
        if not view_url:
            logging.warning("[Pages publish] BRIEF_VIEW_URL is empty. Set it to your GitHub Pages URL for single_* mode.")

    # 5) Kakao send
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "")
    if not refresh_token:
        raise RuntimeError("Missing KAKAO_REFRESH_TOKEN")

    access = kakao_refresh_access_token(refresh_token)

    fallback_url = "https://search.naver.com/search.naver?where=news&query=" + quote_plus("농산물 뉴스 브리핑")

    if KAKAO_SEND_MODE == "single_list":
        # top 3 카드 + 헤더 링크(view_url 우선)
        header_url = view_url or fallback_url
        items = []
        # 섹션 순서대로 3개만
        for sec, arts in enriched_by_section.items():
            for a in arts:
                title = normalize_space(a.get("title", ""))
                desc = normalize_space(a.get("summary", ""))[:60]
                u = a.get("url", "")
                items.append({
                    "title": (title[:40] + "…") if len(title) > 41 else title,
                    "description": (desc[:57] + "…") if len(desc) > 58 else desc,
                    "link": {"web_url": u, "mobile_web_url": u},
                })
                if len(items) >= 3:
                    break
            if len(items) >= 3:
                break
        # list 템플릿은 contents 최소 2개 필요인 경우가 있어, 부족하면 single_text로 fallback :contentReference[oaicite:2]{index=2}
        if len(items) >= 2:
            kakao_send_list(
                access_token=access,
                header_title=f"농산물 뉴스 브리핑 {end_kst.strftime('%m/%d')} 07시",
                header_url=header_url,
                items=items,
                button_title="상세보기",
            )
        else:
            msg = build_single_highlight_message(enriched_by_section, start_kst, end_kst, view_url or fallback_url)
            kakao_send_text(access, msg, view_url or fallback_url)

    elif KAKAO_SEND_MODE == "single_text":
        msg = build_single_highlight_message(enriched_by_section, start_kst, end_kst, view_url or fallback_url)
        kakao_send_text(access, msg, view_url or fallback_url)

    else:
        # multi_text
        chunks = split_text_for_kakao(full_text, soft_limit=KAKAO_TEXT_SOFT_LIMIT)
        # 최소 1개는 보내기
        if not chunks:
            chunks = [f"[농산물 뉴스 Brief] ({start_kst.strftime('%m/%d %H:%M')}~{end_kst.strftime('%m/%d %H:%M')} KST)\n특이사항 없음\n{fallback_url}"]

        for i, ch in enumerate(chunks, start=1):
            # 너무 길면 하드 컷
            txt = ch
            if len(txt) > 250:
                txt = txt[:240] + "…"
            kakao_send_text(access, txt, view_url or fallback_url)

    # 6) Save state (성공적으로 발송한 경우에만 저장)
    save_state(State(last_end_kst_iso=end_kst.isoformat()))
    logging.info("[DONE] sent and state updated: %s", end_kst.isoformat())


if __name__ == "__main__":
    main()
