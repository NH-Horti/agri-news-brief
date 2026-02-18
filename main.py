# -*- coding: utf-8 -*-
"""
agri-news-brief main.py (production)

✅ Changes in this version (IMPORTANT):
1) "브리핑 열기"가 gist.github.com 으로 열리는 문제를 '철저히' 잡기 위한 진단/차단 강화
   - 코드에서 daily_url은 절대 gist로 만들지 않음
   - 발송 전: daily_url 도메인을 검사하여, 카카오 개발자 콘솔(플랫폼 > Web > 사이트 도메인)에
     등록해야 할 도메인 후보를 로그에 명시적으로 출력
   - 만약 카카오 도메인 미등록 때문에 링크가 강제로 gist로 열리는 경우:
     => 코드 수정만으로 해결 불가. "사이트 도메인"에 GitHub Pages 도메인을 추가해야 함.
        (예: hongtaehwa.github.io)

2) 카카오 메시지 포맷 개선(가독성):
   - 항목(블록) 간에만 빈 줄 1개
   - 항목 내부는 줄바꿈만 (불필요한 1칸씩 띄우기 제거)
   - (매체명) 기사제목 형태 고정

3) ( ) 안에는 링크가 아닌 '매체명'이 들어가도록 press 추출/표시 강화

기능:
- Naver News API 검색(섹션별 멀티 쿼리)
- 강한 관련도 필터링(연예/여행/주식/무관 기사 차단)
- 영업일 기준 윈도우(휴일/주말은 다음 영업일에 누적)
- OpenAI 요약(옵션): 실패/쿼터/키 없음이면 description 기반으로 자동 폴백
- GitHub Pages 출력:
  - docs/index.html (최신/아카이브)
  - docs/archive/YYYY-MM-DD.html (일자별 스냅샷)
- 카카오 "나에게 보내기" 단일 메시지 + "브리핑 열기" 버튼(해당 날짜 페이지로)

ENV REQUIRED:
- NAVER_CLIENT_ID
- NAVER_CLIENT_SECRET
- GITHUB_REPO               (e.g., HongTaeHwa/agri-news-brief) 또는 Actions 기본 GITHUB_REPOSITORY
- GH_TOKEN or GITHUB_TOKEN  (Actions built-in token OK if permissions: contents: write)
- KAKAO_REST_API_KEY
- KAKAO_REFRESH_TOKEN

OPTIONAL:
- OPENAI_API_KEY            (없거나/실패하면 폴백)
- OPENAI_MODEL              (default: gpt-5.2)
- KAKAO_CLIENT_SECRET
- PAGES_BASE_URL            (커스텀 도메인/조직 페이지 등)
- REPORT_HOUR_KST           (default: 7)
- MAX_PER_SECTION           (default: 10)
- MIN_PER_SECTION           (default: 5)
- EXTRA_HOLIDAYS            (comma dates, e.g., 2026-02-17,2026-02-18)
- EXCLUDE_HOLIDAYS          (comma dates to treat as business day)
- KAKAO_INCLUDE_LINK_IN_TEXT (true/false, default false)
- FORCE_REPORT_DATE         (YYYY-MM-DD) backfill test
- FORCE_RUN_ANYDAY          (true/false) 휴일/주말에도 강제 실행(테스트용)
- FORCE_END_NOW             (true/false) end를 "지금"으로(테스트용)
- STRICT_KAKAO_LINK_CHECK   (true/false, default false)  # true면 도메인 의심 시 발송 중단(테스트용)
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


# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agri-brief")


# -----------------------------
# Config
# -----------------------------
KST = timezone(timedelta(hours=9))

REPORT_HOUR_KST = int(os.getenv("REPORT_HOUR_KST", "7"))
MAX_PER_SECTION = int(os.getenv("MAX_PER_SECTION", "10"))
MIN_PER_SECTION = int(os.getenv("MIN_PER_SECTION", "5"))

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
# Domain blocks
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

# Strong agriculture context keywords (raise relevance)
AGRI_STRONG_TERMS = [
    "가락시장", "도매시장", "공판장", "경락", "경락가", "경매", "청과", "산지", "출하", "물량", "반입",
    "산지유통", "APC", "산지유통센터", "선별", "CA저장", "저장고", "저장량",
    "시세", "도매가격", "소매가격", "가격", "수급", "수급동향", "작황", "생산량", "재배", "수확", "면적",
    "농림축산식품부", "농식품부", "aT", "한국농수산식품유통공사", "농관원", "국립농산물품질관리원",
    "검역", "할당관세", "수입", "수출", "관세", "통관", "원산지", "부정유통", "온라인 도매시장",
    "비축미", "정부", "대책", "지원", "할인지원", "성수품",
    "병해충", "방제", "약제", "살포", "예찰", "과수화상병", "탄저병", "동해", "냉해", "월동",
]

# Very common off-topic hints (penalize)
OFFTOPIC_HINTS = [
    "배우", "아이돌", "드라마", "영화", "예능", "콘서트", "팬", "유튜브", "뮤직",
    "대통령", "국회", "총선", "검찰", "재판", "탄핵", "정당",
    "코스피", "코스닥", "주가", "급등", "급락", "비트코인", "환율",
    "여행", "관광", "호텔", "리조트", "레스토랑", "와인", "해변", "휴양", "파운드", "달러", "유로",
]

TRAVEL_MARKET_HINTS = [
    "현지", "전통시장", "노점", "파운드", "로제", "타파스", "리비에라", "프랑스", "두바이",
]

KOREA_CONTEXT_HINTS = [
    "국내", "한국", "우리나라", "농협", "지자체", "군", "시", "도", "농가", "산지", "가락시장",
    "농식품부", "aT", "농관원", "대한민국", "설", "명절",
]


# -----------------------------
# Section configuration
# -----------------------------
SECTIONS = [
    {
        "key": "supply",
        "title": "품목 및 수급 동향",
        "color": "#0f766e",
        "queries": [
            # 구조/기후/재배지 이동
            "기후변화 사과 재배지 북상 강원도",
            "과수 재배면적 변화 사과 배",
            # 사과/배/감/만감/기타
            "사과 가격", "사과 시세", "사과 도매시장", "사과 저장량", "사과 출하",
            "배(과일) 가격", "배(과일) 시세", "배(과일) 도매시장",
            "단감 시세", "단감 저장량",
            "떫은감 곶감 탄저병", "곶감 가격", "둥시 곶감",
            "감귤 가격", "한라봉 가격", "레드향 가격", "천혜향 가격", "만감류 출하",
            "참다래 시세", "키위 시세",
            "샤인머스캣 시세", "포도 가격",
            "풋고추 가격", "오이 가격", "시설채소 가격",
            "절화 가격", "졸업 입학 절화",
            "쌀 산지 가격", "비축미 방출",
        ],
        "must_terms": ["가격", "시세", "수급", "출하", "도매", "경락", "저장", "작황", "생산", "재배", "수확", "면적", "물량"],
    },
    {
        "key": "policy",
        "title": "주요 이슈 및 정책",
        "color": "#1d4ed8",
        "queries": [
            "농산물 온라인 도매시장 허위거래",
            "온라인 도매시장 이상거래 전수조사",
            "농축수산물 할인지원 연장",
            "할당관세 과일 검역 완화",
            "성수품 가격 안정 대책",
            "대한민국 정책브리핑 농축수산물",
            "korea.kr 농축수산물 할인",
            "농식품부 정책 할당관세 농축수산물",
        ],
        "must_terms": ["정책", "대책", "지원", "할인", "할당관세", "검역", "온라인 도매시장", "비축미", "성수품", "수급", "물가"],
    },
    {
        "key": "pest",
        "title": "병해충 및 방제",
        "color": "#b45309",
        "queries": [
            "과수화상병 약제 신청",
            "과수화상병 궤양 제거",
            "월동 해충 방제 기계유유제",
            "탄저병 예방 방제",
            "동해 냉해 과수 피해 대비",
        ],
        "must_terms": ["방제", "병해충", "약제", "살포", "예찰", "과수화상병", "탄저병", "냉해", "동해", "월동"],
    },
    {
        "key": "dist",
        "title": "유통 및 현장 (APC/수출)",
        "color": "#6d28d9",
        "queries": [
            "APC 스마트화 AI 선별기",
            "농협 APC 선별 저장",
            "CA저장 APC",
            "농식품 수출 실적 배 딸기",
            "가락시장 경매 재개 일정",
            "원산지 단속 농산물 부정유통",
        ],
        "must_terms": ["APC", "선별", "CA저장", "공판장", "도매시장", "가락시장", "수출", "원산지", "유통", "검역"],
    },
]

POLICY_DOMAINS = {
    "korea.kr", "www.korea.kr",
    "mafra.go.kr", "www.mafra.go.kr",
    "at.or.kr", "www.at.or.kr",
    "naqs.go.kr", "www.naqs.go.kr",
    "krei.re.kr", "www.krei.re.kr",
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
    t = re.sub(r"\[[^\]]+\]", " ", t)
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

def simplify_domain_for_press(dom: str) -> str:
    """
    도메인밖에 모르는 경우라도 (www 제거, 너무 지저분하지 않게) 표시용 press를 만든다.
    예: www.mbn.co.kr -> mbn
    예: news.mt.co.kr -> mt
    """
    d = (dom or "").lower()
    if not d:
        return "알수없음"
    d = d.replace("www.", "")
    parts = d.split(".")
    if len(parts) >= 2:
        return parts[-2].upper() if len(parts[-2]) <= 5 else parts[-2]
    return d


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
    r = requests.get(url, headers=github_api_headers(token), params={"ref": ref}, timeout=30)
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
    r = requests.put(url, headers=github_api_headers(token), json=payload, timeout=30)
    if not r.ok:
        log.error("[GitHub PUT ERROR] %s", r.text)
        r.raise_for_status()
    return r.json()


# -----------------------------
# State / archive manifest (legacy-safe)
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
def naver_news_search(query: str, display: int = 30, start: int = 1, sort: str = "date"):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set")
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query": query, "display": display, "start": start, "sort": sort}
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
    return has_any(text, must_terms)

def policy_domain_override(dom: str, text: str) -> bool:
    if dom in POLICY_DOMAINS:
        return has_any(text, AGRI_POLICY_KEYWORDS)
    return False

def is_relevant(article: Article, section_conf: dict) -> bool:
    dom = article.domain
    if is_blocked_domain(dom):
        return False

    text = (article.title + " " + article.description).lower()

    # must_terms gate (policy domains can override)
    if not section_must_terms_ok(text, [t.lower() for t in section_conf["must_terms"]]):
        if not policy_domain_override(dom, text):
            return False

    strength = agri_strength_score(text)
    offp = off_topic_penalty(text)
    trav = travel_penalty(text)
    korea = korea_context_score(text)

    if trav >= 1 and korea == 0 and strength < 3:
        return False
    if offp >= 1 and strength < 3:
        return False

    # disambiguation: "사과" apology
    if re.search(r"(공개\s*)?사과(했다|해야|하라|문|요구|요청|발표)", article.title) and strength < 4:
        return False

    # disambiguation: "배" ship
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

    if article.domain in POLICY_DOMAINS:
        score += 3.0

    age_hours = max(0.0, (datetime.now(tz=KST) - article.pub_dt_kst).total_seconds() / 3600.0)
    score += max(0.0, 24.0 - min(age_hours, 24.0)) * 0.05

    for t in section_conf["must_terms"]:
        if t.lower() in article.title.lower():
            score += 0.6

    return score


# -----------------------------
# Press mapping
# -----------------------------
PRESS_MAP = {
    # national
    "www.yna.co.kr": "연합뉴스", "yna.co.kr": "연합뉴스",
    "www.mk.co.kr": "매일경제", "mk.co.kr": "매일경제",
    "www.joongang.co.kr": "중앙일보", "joongang.co.kr": "중앙일보",
    "www.chosun.com": "조선일보", "chosun.com": "조선일보",
    "www.donga.com": "동아일보", "donga.com": "동아일보",
    "www.hani.co.kr": "한겨레", "hani.co.kr": "한겨레",
    "www.khan.co.kr": "경향신문", "khan.co.kr": "경향신문",
    "www.sedaily.com": "서울경제", "sedaily.com": "서울경제",
    "www.hankyung.com": "한국경제", "hankyung.com": "한국경제",
    "www.asiae.co.kr": "아시아경제", "asiae.co.kr": "아시아경제",
    "www.mt.co.kr": "머니투데이", "mt.co.kr": "머니투데이",
    "www.edaily.co.kr": "이데일리", "edaily.co.kr": "이데일리",
    "www.heraldcorp.com": "헤럴드경제", "heraldcorp.com": "헤럴드경제",
    "www.fnnews.com": "파이낸셜뉴스", "fnnews.com": "파이낸셜뉴스",
    "www.newsis.com": "뉴시스", "newsis.com": "뉴시스",
    "www.news1.kr": "뉴스1", "news1.kr": "뉴스1",

    # broadcast / mid-tier
    "www.mbn.co.kr": "MBN", "mbn.co.kr": "MBN",
    "news.sbs.co.kr": "SBS", "www.sbs.co.kr": "SBS", "sbs.co.kr": "SBS",
    "news.kbs.co.kr": "KBS", "www.kbs.co.kr": "KBS", "kbs.co.kr": "KBS",
    "imnews.imbc.com": "MBC", "www.imbc.com": "MBC", "imbc.com": "MBC",
    "www.ytn.co.kr": "YTN", "ytn.co.kr": "YTN",
    "news.jtbc.co.kr": "JTBC", "jtbc.co.kr": "JTBC", "www.jtbc.co.kr": "JTBC",

    # policy
    "www.korea.kr": "정책브리핑", "korea.kr": "정책브리핑",
    "www.mafra.go.kr": "농식품부", "mafra.go.kr": "농식품부",
    "www.at.or.kr": "aT", "at.or.kr": "aT",
    "www.naqs.go.kr": "농관원", "naqs.go.kr": "농관원",
}

CENTRAL_PRESS_NAMES = {
    "연합뉴스", "매일경제", "중앙일보", "조선일보", "동아일보", "한겨레", "경향신문",
    "서울경제", "한국경제", "아시아경제", "머니투데이", "헤럴드경제", "이데일리",
    "뉴시스", "뉴스1", "파이낸셜뉴스",
    "SBS", "KBS", "MBC", "YTN", "JTBC", "MBN",
    "정책브리핑", "농식품부", "aT", "농관원",
}

def press_tier(press: str, domain: str) -> str:
    """
    중앙/지방 집계용 (대략적인 분류)
    - 중앙: 중앙/방송/정책기관
    - 그 외는 지방으로 집계 (합계가 total과 맞도록)
    """
    p = (press or "").strip()
    d = (domain or "").lower()
    if p in CENTRAL_PRESS_NAMES:
        return "central"
    if d in POLICY_DOMAINS or d.endswith(".go.kr"):
        return "central"
    return "local"


# -----------------------------
# Collect articles
# -----------------------------
def collect_articles_for_section(section_conf: dict, start_kst: datetime, end_kst: datetime):
    items: list[Article] = []
    seen_keys = set()
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

                press = PRESS_MAP.get(dom)
                if not press:
                    press = simplify_domain_for_press(dom)

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

    items.sort(key=lambda a: (a.score, a.pub_dt_kst), reverse=True)
    return items[:MAX_PER_SECTION]

def collect_all_sections(start_kst: datetime, end_kst: datetime):
    by_section: dict[str, list[Article]] = {}
    for sec in SECTIONS:
        by_section[sec["key"]] = collect_articles_for_section(sec, start_kst, end_kst)

    # broad fill if too few
    for sec in SECTIONS:
        key = sec["key"]
        if len(by_section[key]) >= MIN_PER_SECTION:
            continue

        if key == "supply":
            broad_queries = ["농산물 가격", "과일 시세", "도매시장 시세", "산지 출하"]
        elif key == "policy":
            broad_queries = ["농축수산물 할인", "농산물 물가 대책", "할당관세 과일"]
        elif key == "pest":
            broad_queries = ["과수 방제 약제", "과수화상병 방제", "월동 해충 방제"]
        else:
            broad_queries = ["APC 선별", "농식품 수출 실적", "가락시장 경매"]

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
        "- 각 기사 요약은 2~3문장, 120~220자 내. 핵심 팩트 중심.\n"
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
        r = requests.post(
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
        s = mapping.get(a.norm_key, "").strip()
        if not s:
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

def render_daily_page(report_date: str, start_kst: datetime, end_kst: datetime, by_section: dict, base_url: str) -> str:
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
                  <div class="meta">
                    <span class="press">{esc(a.press)}</span>
                    <span class="dot">·</span>
                    <span class="time">{esc(fmt_dt(a.pub_dt_kst))}</span>
                  </div>
                  <div class="ttl">{esc(a.title)}</div>
                  <div class="sum">{summary_html}</div>
                  <div class="lnk"><a href="{esc(url)}" target="_blank" rel="noopener">원문 열기</a></div>
                </div>
                """
            )
        cards_html = '<div class="empty">특이사항 없음</div>' if not cards else "\n".join(cards)

        sections_html.append(
            f"""
            <section id="sec-{key}" class="sec">
              <div class="secHead" style="background:linear-gradient(90deg,{color},#111827);">
                <div class="secTitle">{esc(title)}</div>
                <div class="secCount">{len(lst)}건</div>
              </div>
              <div class="secBody">{cards_html}</div>
            </section>
            """
        )

    sections_html = "\n".join(sections_html)

    title = f"[{report_date} 농산물 뉴스 Brief]"
    period = f"{start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%Y-%m-%d %H:%M')}"
    index_url = f"{base_url}/"

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <style>
    :root {{
      --bg:#0b1220; --text:#e5e7eb; --muted:#94a3b8; --line:#1f2937;
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
          border-radius:14px;padding:12px;margin:10px 0}}
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

    <div class="chips">{chips_html}</div>

    {sections_html}

    <div class="footer">
      * 자동 수집 결과이며, 제목/요약은 원문 기반 정리입니다. (필요 시 원문 확인)
    </div>
  </div>
</body>
</html>
"""

def render_index_page(manifest: dict, base_url: str) -> str:
    manifest = _normalize_manifest(manifest)
    dates = sorted(manifest.get("dates", []), reverse=True)
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
      <ul>{ul}</ul>
    </div>
  </div>
</body>
</html>
"""


# -----------------------------
# Pages URL (anti-gist + safer)
# -----------------------------
def get_pages_base_url(repo: str) -> str:
    """
    base_url 결정 로직(안전 강화):
    - PAGES_BASE_URL이 없으면 기본 GitHub Pages로
    - PAGES_BASE_URL이 gist/raw 등 의심 도메인이면 무시하고 기본 URL로
    """
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
    """
    ✅ '브리핑 열기'가 gist로 열리는 대표 원인:
    - 카카오 개발자 콘솔 > 플랫폼 > Web > 사이트 도메인에
      GitHub Pages 도메인(예: hongtaehwa.github.io)이 등록되어 있지 않음
    이 경우 카카오가 링크를 정상 처리하지 못하고, 이미 등록된 다른 도메인(예: gist)로 열어버릴 수 있음.
    => 런 로그에 등록해야 할 도메인을 정확히 표시.
    """
    dom = domain_of(daily_url)
    if not dom:
        return
    # github pages / custom domain 모두에 대해 안내
    log.info("[KAKAO LINK CHECK] daily_url domain=%s", dom)
    log.info("[KAKAO LINK CHECK] If '브리핑 열기' opens wrong site, add this domain to Kakao Dev Console:")
    log.info("[KAKAO LINK CHECK] Kakao Developers > 내 애플리케이션 > 앱 설정 > 플랫폼 > Web > 사이트 도메인 : %s", dom)


def ensure_not_gist(url: str, label: str):
    if "gist.github.com" in url or "raw.githubusercontent.com" in url:
        raise RuntimeError(f"[FATAL] {label} points to gist/raw: {url}")


# -----------------------------
# Kakao message builder (compact, press in parentheses)
# -----------------------------
# 카톡 메시지 섹션 순서(요청 고정): 품목 → 정책 → 유통 → 방제
KAKAO_MESSAGE_SECTION_ORDER = ["supply", "policy", "dist", "pest"]

def _get_section_conf(key: str):
    for s in SECTIONS:
        if s["key"] == key:
            return s
    return None

def build_kakao_message(report_date: str, by_section: dict) -> str:
    """
    요구사항 반영:
    - 항목 간에만 빈 줄 1개
    - 항목 내부는 줄바꿈만
    - (매체명) 기사제목
    """
    total = 0
    central = 0
    local = 0
    per = {"supply": 0, "policy": 0, "pest": 0, "dist": 0}

    for key in per.keys():
        lst = by_section.get(key, [])
        per[key] = len(lst)
        total += len(lst)
        for a in lst:
            if press_tier(a.press, a.domain) == "central":
                central += 1
            else:
                local += 1

    lines = []
    lines.append(f"[{report_date} 농산물 뉴스 Brief]")
    lines.append("")  # 블록 간 1줄

    lines.append(f"기사 : 총 {total}건 (중앙 {central}건, 지방 {local}건)")
    lines.append(f"- 품목 {per['supply']} · 정책 {per['policy']} · 방제 {per['pest']} · 유통 {per['dist']}")
    lines.append("")  # 블록 간 1줄

    lines.append("오늘의 체크포인트")
    lines.append("")  # 블록 간 1줄

    section_num = 0
    for key in KAKAO_MESSAGE_SECTION_ORDER:
        conf = _get_section_conf(key)
        if not conf:
            continue
        section_num += 1

        lines.append(f"{section_num}) {conf['title']}")

        items = by_section.get(key, [])[:2]
        if not items:
            lines.append("   - (기사 없음)")
        else:
            for a in items:
                # (매체명) 기사제목
                press = (a.press or "").strip()
                if not press:
                    press = simplify_domain_for_press(a.domain)
                lines.append(f"   - ({press}) {a.title}")

        lines.append("")  # 섹션(항목) 간 1줄

    # 마지막 빈 줄 하나 제거(가독성)
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

    r = requests.post(url, data=data, timeout=30)
    if not r.ok:
        log.error("[KAKAO TOKEN ERROR] %s", r.text)
        r.raise_for_status()
    j = r.json()
    return j["access_token"]

def kakao_send_to_me(text: str, web_url: str):
    access_token = kakao_refresh_access_token()

    # ✅ 코드상 web_url은 gist가 될 수 없게 한다(치명 사고 방지)
    ensure_not_gist(web_url, "Kakao web_url")

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    # ✅ "text" 템플릿: 버튼(브리핑 열기) 및 말풍선 클릭 링크는 link 기준
    #    (본문에 URL이 들어가면 미리보기/자동 링크가 섞일 수 있으니 기본 false 권장)
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

    # 기본: 직전 영업일 컷오프부터
    start = prev_cutoff

    # 상태 파일(last_end)이 더 과거라면 더 과거부터(누락 방지) / 더 최근이면 prev_cutoff로
    if last_end_iso:
        try:
            st = datetime.fromisoformat(last_end_iso)
            if st.tzinfo is None:
                st = st.replace(tzinfo=KST)
            # 더 이른 쪽으로 설정(휴일 누적/누락 방지)
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

    # ✅ base_url / daily_url (gist 절대 불가)
    base_url = get_pages_base_url(repo).rstrip("/")
    daily_url = f"{base_url}/archive/{report_date}.html"

    ensure_not_gist(base_url, "base_url")
    ensure_not_gist(daily_url, "daily_url")

    # ✅ 철저 진단 로그: 카카오 링크 도메인 등록 필요 여부 확인용
    log_kakao_domain_requirement(daily_url)

    # Collect + summarize
    by_section = collect_all_sections(start_kst, end_kst)
    by_section = fill_summaries(by_section)

    # Render pages
    daily_html = render_daily_page(report_date, start_kst, end_kst, by_section, base_url)

    manifest, msha = load_archive_manifest(repo, GH_TOKEN)
    manifest = _normalize_manifest(manifest)
    dates = set(manifest.get("dates", []))
    dates.add(report_date)
    manifest["dates"] = sorted(list(dates))

    index_html = render_index_page(manifest, base_url)

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

    # Kakao message (compact & readable)
    kakao_text = build_kakao_message(report_date, by_section)

    # 본문에 URL 넣기 옵션(기본 false 권장: 미리보기/자동 링크가 섞일 수 있음)
    if KAKAO_INCLUDE_LINK_IN_TEXT:
        kakao_text = kakao_text + "\n" + daily_url

    # ✅ STRICT 모드: 링크 도메인 의심 시 발송 중단(테스트용)
    if STRICT_KAKAO_LINK_CHECK:
        # github.io / custom domain 모두 허용, 다만 gist/raw는 이미 차단
        parsed = urlparse(daily_url)
        if not parsed.scheme.startswith("http") or not parsed.netloc:
            raise RuntimeError(f"[FATAL] daily_url invalid: {daily_url}")

    kakao_send_to_me(kakao_text, daily_url)
    log.info("[OK] Kakao message sent. URL=%s", daily_url)


if __name__ == "__main__":
    main()
