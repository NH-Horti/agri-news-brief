# main.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os, re, json, time, base64, html, logging
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# =========================
# 운영 파라미터
# =========================
RUN_HOUR_KST = int(os.getenv("RUN_HOUR_KST", "7"))
EARLY_GRACE_MINUTES = int(os.getenv("EARLY_GRACE_MINUTES", "20"))  # 07:00 직전 실행 보정
FORCE_SEND = (os.getenv("FORCE_SEND", "0") == "1")

MAX_ARTICLES_PER_SECTION = int(os.getenv("MAX_ARTICLES_PER_SECTION", "10"))
MIN_ARTICLES_PER_SECTION = int(os.getenv("MIN_ARTICLES_PER_SECTION", "7"))
GLOBAL_BACKFILL_LIMIT = int(os.getenv("GLOBAL_BACKFILL_LIMIT", "120"))
MAX_PAGES_PER_QUERY = int(os.getenv("MAX_PAGES_PER_QUERY", "3"))  # 네이버 API 페이지(50개씩)

PUBLISH_MODE = os.getenv("PUBLISH_MODE", "github_pages")
PAGES_BRANCH = os.getenv("PAGES_BRANCH", "main")
PAGES_FILE_PATH = os.getenv("PAGES_FILE_PATH", "docs/index.html")

STATE_BACKEND = os.getenv("STATE_BACKEND", "repo")
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", ".agri_state.json")

BRIEF_VIEW_URL = os.getenv("BRIEF_VIEW_URL", "").strip()
KAKAO_MESSAGE_SOFT_LIMIT = int(os.getenv("KAKAO_MESSAGE_SOFT_LIMIT", "260"))

# =========================
# Kakao
# =========================
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_SEND_API = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

# =========================
# Naver OpenAPI
# =========================
NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"

# =========================
# OpenAI
# =========================
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "minimal")
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "2000"))

# =========================
# 섹션(순서 고정)
# =========================
SECTION_ORDER: List[str] = [
    "품목 및 수급 동향",
    "주요 이슈 및 정책",
    "병해충 및 방제",
    "유통 및 현장(APC/수출)",
]

# =========================
# 1) 키워드 전면 재조정 (원예수급부/과수화훼팀 관점)
# =========================
FRUITS = [
    "사과","배","감귤","만감류","한라봉","레드향","천혜향","참다래","키위",
    "포도","샤인머스캣","복숭아","자두","매실","유자","밤",
    "단감","떫은감","곶감","감",
]
VEGGIES = [
    "딸기","오이","풋고추","애호박","토마토","파프리카","가지","상추","깻잎",
    "배추","무","양파","대파","마늘","감자","고구마",
]
FLOWERS = ["절화","화훼","꽃값","국화","장미","백합","프리지아"]
STAPLES = ["쌀","산지쌀값","비축미"]

# 원예수급부에서 “기사 빠짐”이 덜 나오는 맥락 단어(품목 단독검색의 노이즈를 줄이기)
AGRI_CONTEXT = ["농산물","원예","과수","과일","청과","산지","농가","도매","경매","출하","저장","수급","작황"]

# 모디파이어(=가격만 붙이면 빠짐 -> 가격/시세는 “보조”로)
SUPPLY_MODS = ["수급","출하","저장","재고","작황","생산","물량","도매","경매","경락","시세","가격"]

# 구조/기후/산지이동(과수화훼팀 관점 중요)
STRUCTURAL_QUERIES = [
    "기후변화 과수 재배지 북상",
    "사과 재배지 북상 강원",
    "과수 동해 냉해 피해",
    "일조량 부족 시설원예",
    "고온 가뭄 과수 작황",
]

POLICY_CORE = [
    "농산물 온라인 도매시장", "온라인 도매시장", "도매시장 제도",
    "가락시장 휴무", "가락시장 경매 재개", "공영도매시장",
    "농산물 물가 대책", "농축산물 할인", "할인지원",
    "할당관세", "수입 과일", "검역 완화", "시장개방",
    "농림축산식품부 농산물", "정책브리핑 농산물",
]

Pest_CORE = [
    "과수화상병", "화상병 약제", "화상병 방제", "궤양 제거",
    "월동해충 방제", "기계유유제", "탄저병", "병해충 예찰",
    "동해 대비", "냉해 대비", "서리 피해",
]

DIST_CORE = [
    "APC", "산지유통센터", "스마트 APC", "AI 선별", "선별기", "CA 저장", "저장시설",
    "공판장", "도매시장 유통", "산지유통", "콜드체인",
    "농식품 수출", "농산물 수출", "딸기 수출", "배 수출",
    "K-Food 수출", "aT 수출",
]

def uniq_keep_order(xs: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        x = re.sub(r"\s+", " ", (x or "").strip())
        if not x:
            continue
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

def build_supply_queries() -> List[str]:
    """
    ✅ 핵심: '사과 가격' 같은 AND 조합만 쓰지 말고,
    (1) 품목 + 농업맥락(농산물/과수/산지/도매/출하/저장)부터 폭넓게 수집
    (2) 그 다음 가격/시세/경락 등 보조 키워드 조합
    """
    qs: List[str] = []

    # 0) 구조/기후 이슈는 선행 수집(과수화훼팀 핵심)
    qs += STRUCTURAL_QUERIES

    # 1) 품목(과수/채소/화훼/쌀) + 농업맥락
    def add_item(item: str):
        # 노이즈를 줄이기 위해 "품목 단독" 대신 맥락 포함 쿼리 우선
        # (특히 사과=Apple, 배=ship 같은 오염 방지)
        qs.append(f"{item} 농산물")
        qs.append(f"{item} 산지")
        qs.append(f"{item} 도매")
        qs.append(f"{item} 출하")
        qs.append(f"{item} 저장")
        qs.append(f"{item} 수급")
        qs.append(f"{item} 작황")

        # 가격/시세는 보조(그래도 중요해서 포함)
        qs.append(f"{item} 시세")
        qs.append(f"{item} 가격")
        qs.append(f"{item} 경락")

    for it in FRUITS + VEGGIES + FLOWERS:
        add_item(it)

    # 2) 카테고리 기반(품목명이 기사에 없을 때 대비)
    qs += [
        "과일 도매가격", "청과 도매가격", "가락시장 과일", "가락시장 청과",
        "시설채소 수급", "시설원예 수급", "시설채소 가격",
        "만감류 수급", "만감류 출하", "감귤 수급",
        "화훼 절화 가격", "꽃값 동향",
        "산지 출하 동향 과일", "저장 과수 재고",
    ]

    # 3) 쌀(원예수급부와 직접은 약하지만 팀 보고에 자주 포함)
    qs += [
        "쌀값", "산지쌀값", "비축미 방출", "쌀 수급",
    ]

    return uniq_keep_order(qs)

def build_policy_queries() -> List[str]:
    qs: List[str] = []
    qs += POLICY_CORE
    # 정책/물가 관련은 표현이 다양하므로 확장
    qs += [
        "농산물 할인 행사", "농축산물 할인 지원", "물가 안정 농산물",
        "도매시장 유통 개선", "농산물 유통 구조 개선",
        "수입과일 물량", "수입과일 가격", "과일 수입",
    ]
    return uniq_keep_order(qs)

def build_pest_queries() -> List[str]:
    qs: List[str] = []
    qs += Pest_CORE
    qs += [
        "과수 병해충", "과수 방제", "과수 약제 살포",
        "시설원예 병해충", "진딧물 방제", "응애 방제",
        "냉해 피해 과수", "동해 피해 과수",
    ]
    return uniq_keep_order(qs)

def build_dist_queries() -> List[str]:
    qs: List[str] = []
    qs += DIST_CORE
    qs += [
        "농협 산지유통", "농협 APC", "산지유통 혁신", "스마트팜 유통",
        "공판장 경매", "도매시장 경매", "도매시장 물량",
        "수출 검역", "수출 물류",
    ]
    return uniq_keep_order(qs)

SECTION_QUERIES: Dict[str, List[str]] = {
    "품목 및 수급 동향": build_supply_queries(),
    "주요 이슈 및 정책": build_policy_queries(),
    "병해충 및 방제": build_pest_queries(),
    "유통 및 현장(APC/수출)": build_dist_queries(),
}

# 섹션 부족 시 백필(넓게 긁고 분류)
GLOBAL_BACKFILL_QUERIES = uniq_keep_order(
    ["농산물", "원예", "과수", "화훼", "청과", "도매시장", "가락시장", "공판장", "수급", "출하", "저장", "재고"]
    + ["과일", "채소", "절화", "꽃값", "만감류", "감귤", "사과", "배", "딸기", "포도"]
    + ["물가", "할인", "할당관세", "검역", "수입과일"]
    + ["APC", "산지유통", "선별", "CA 저장", "수출"]
    + ["과수화상병", "병해충", "방제", "냉해", "동해"]
)

# =========================
# 2) 매체 정책: 지방지/지방방송 포함 + 군소차단
# =========================
# 확실히 필요 없는 군소/낚시/이상 도메인(필요시 계속 추가)
BLOCKED_DOMAINS = {
    "wikitree.co.kr", "donghaengmedia.net", "sidae.com",
    "namu.wiki", "blog.naver.com", "post.naver.com",
}

# 신뢰/가점 도메인(메이저+중견+전문+공공+지방지/지방방송 일부)
# ✅ 여기 없는 지방지는 “차단만 아니면” 수집될 수 있음(점수만 낮음)
TRUSTED_DOMAINS = {
    # 통신/정책/공공
    "yna.co.kr", "newsis.com", "korea.kr", "mafra.go.kr", "at.or.kr", "krei.re.kr", "naqs.go.kr",
    # 중앙/경제/종합
    "mk.co.kr", "mt.co.kr", "hankyung.com", "sedaily.com", "edaily.co.kr", "asiae.co.kr", "heraldcorp.com",
    "joongang.co.kr", "donga.com", "hani.co.kr", "khan.co.kr", "chosun.com",
    # 중견
    "fnnews.com", "kmib.co.kr", "munhwa.com", "segye.com", "dt.co.kr", "nocutnews.co.kr", "news1.kr",
    # 방송(전국)
    "kbs.co.kr","imbc.com","sbs.co.kr","jtbc.co.kr","ytn.co.kr","mbn.co.kr","yonhapnewstv.co.kr",
    # 전문/농업
    "nongmin.com","ikpnews.net","aflnews.co.kr",
    # 지방지/지방방송(대표적인 것 일부)
    "kwnews.co.kr","kado.net","kyeonggi.com","joongboo.com","cctoday.co.kr","imaeil.com","yeongnam.com",
    "gnnews.co.kr","namdonews.com","jeonmae.co.kr","newsis.com",
    "g1tv.co.kr","cjb.co.kr","tjb.co.kr","kbc.co.kr","jibs.co.kr","obn.co.kr",
}

PRESS_MAP = {
    "yna.co.kr": "연합뉴스",
    "newsis.com": "뉴시스",
    "korea.kr": "정책브리핑",
    "mafra.go.kr": "농림축산식품부",
    "at.or.kr": "aT",
    "krei.re.kr": "KREI",
    "naqs.go.kr": "농관원",

    "mk.co.kr": "매일경제",
    "mt.co.kr": "머니투데이",
    "hankyung.com": "한국경제",
    "sedaily.com": "서울경제",
    "edaily.co.kr": "이데일리",
    "asiae.co.kr": "아시아경제",
    "heraldcorp.com": "헤럴드경제",
    "joongang.co.kr": "중앙일보",
    "donga.com": "동아일보",
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "chosun.com": "조선일보",

    "fnnews.com": "파이낸셜뉴스",
    "kmib.co.kr": "국민일보",
    "munhwa.com": "문화일보",
    "segye.com": "세계일보",
    "dt.co.kr": "디지털타임스",
    "nocutnews.co.kr": "노컷뉴스",
    "news1.kr": "뉴스1",
    "yonhapnewstv.co.kr": "연합뉴스TV",

    "kbs.co.kr": "KBS",
    "imbc.com": "MBC",
    "sbs.co.kr": "SBS",
    "jtbc.co.kr": "JTBC",
    "ytn.co.kr": "YTN",
    "mbn.co.kr": "MBN",

    "nongmin.com": "농민신문",
    "aflnews.co.kr": "농수축산신문",
    "ikpnews.net": "한국농어민신문",

    "kwnews.co.kr": "강원일보",
    "kado.net": "강원도민일보",
    "kyeonggi.com": "경기일보",
    "joongboo.com": "중부일보",
    "cctoday.co.kr": "충청투데이",
    "imaeil.com": "매일신문",
    "yeongnam.com": "영남일보",
    "gnnews.co.kr": "경남신문",
    "namdonews.com": "남도일보",
    "jeonmae.co.kr": "전국매일신문",

    "g1tv.co.kr": "G1",
    "cjb.co.kr": "CJB",
    "tjb.co.kr": "TJB",
    "kbc.co.kr": "kbc",
    "jibs.co.kr": "JIBS",
    "obn.co.kr": "OBN",
}

LOW_RELEVANCE_HINTS = ["온누리상품권", "환급", "지역화폐", "축제", "행사", "관광", "맛집", "레시피", "홍보", "체험"]
OUT_OF_SEASON_HINTS = ["10월", "11월", "추석", "수확기", "가을 수확", "햇사과", "햇배"]
HIGH_RELEVANCE_HINTS = [
    "가격","시세","도매","경락","수급","물량","출하","저장","재고","작황","생산량",
    "물가","할인","할당관세","검역","수입","도매시장","가락시장","공판장",
    "APC","선별","CA","저장","수출","방제","병해충","화상병","탄저","동해","냉해"
]

# =========================
# 휴일/영업일 유틸
# =========================
def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def is_korean_holiday(d: date) -> bool:
    try:
        import holidays  # type: ignore
        return d in holidays.KR()
    except Exception:
        return False

def is_business_day(d: date) -> bool:
    return (not is_weekend(d)) and (not is_korean_holiday(d))

def compute_fixed_end_kst(now_kst: datetime, run_hour: int, early_grace_minutes: int) -> datetime:
    today_end = now_kst.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    if now_kst >= today_end:
        return today_end
    if (today_end - now_kst) <= timedelta(minutes=early_grace_minutes):
        return today_end
    return today_end - timedelta(days=1)

def clean_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""

def press_name(dom: str) -> str:
    if not dom:
        return "미상"
    if dom in PRESS_MAP:
        return PRESS_MAP[dom]
    for k, v in PRESS_MAP.items():
        if dom.endswith("." + k):
            return v
    return dom

def has_any(text: str, keys: List[str]) -> bool:
    return any(k in text for k in keys)

def looks_low_relevance(text: str) -> bool:
    return has_any(text, LOW_RELEVANCE_HINTS) and (not has_any(text, HIGH_RELEVANCE_HINTS))

def looks_out_of_season(text: str) -> bool:
    out = has_any(text, OUT_OF_SEASON_HINTS)
    current_ok = has_any(text, ["저장", "저장량", "재고", "전정", "설", "설 이후", "최근", "현재"])
    return out and (not current_ok)

def is_blocked_domain(dom: str) -> bool:
    if not dom:
        return True
    if dom in BLOCKED_DOMAINS:
        return True
    return False

def is_trusted_domain(dom: str) -> bool:
    if not dom:
        return False
    if dom in TRUSTED_DOMAINS:
        return True
    # 공공/기관 도메인 가점
    if dom.endswith(".go.kr") or dom.endswith(".or.kr"):
        return True
    return False

def clamp(s: str, n: int) -> str:
    return s if len(s) <= n else (s[: max(0, n-1)] + "…")

# =========================
# GitHub repo 파일 read/write
# =========================
def github_get_file(repo: str, path: str, token: str, ref: str = "main") -> Tuple[Optional[str], Optional[str]]:
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if r.status_code == 404:
        return None, None
    if not r.ok:
        logging.error("[GitHub GET ERROR] %s", r.text)
        return None, None
    j = r.json()
    sha = j.get("sha")
    b64 = j.get("content", "")
    if j.get("encoding") == "base64" and b64:
        raw = base64.b64decode(b64).decode("utf-8", errors="replace")
        return raw, sha
    return None, sha

def github_put_file(repo: str, path: str, token: str, content_text: str,
                    branch: str = "main", sha: Optional[str] = None, message: str = "Update file") -> bool:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    b64 = base64.b64encode(content_text.encode("utf-8")).decode("ascii")
    payload = {"message": message, "content": b64, "branch": branch}
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=20)
    if not r.ok:
        logging.error("[GitHub PUT ERROR] %s", r.text)
        return False
    return True

@dataclass
class State:
    last_end_kst_iso: str

def load_state(default_last_end: datetime) -> State:
    fallback = State(last_end_kst_iso=(default_last_end - timedelta(hours=24)).isoformat())
    if STATE_BACKEND != "repo":
        return fallback
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        return fallback
    raw, _ = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
    if not raw:
        return fallback
    try:
        j = json.loads(raw)
        v = j.get("last_end_kst_iso")
        return State(last_end_kst_iso=v) if v else fallback
    except Exception:
        return fallback

def save_state(end_kst: datetime) -> None:
    if STATE_BACKEND != "repo":
        return
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        return
    raw, sha = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
    _ = raw
    content = json.dumps({"last_end_kst_iso": end_kst.isoformat()}, ensure_ascii=False, indent=2)
    github_put_file(repo, STATE_FILE_PATH, token, content, branch=PAGES_BRANCH, sha=sha, message="Update agri-news state")

# =========================
# Kakao
# =========================
def kakao_refresh_access_token(refresh_token: str) -> str:
    rest_api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    client_secret = os.getenv("KAKAO_CLIENT_SECRET", "").strip()
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
        logging.error("[Kakao token ERROR] %s", r.text)
        r.raise_for_status()
    access = r.json().get("access_token")
    if not access:
        raise RuntimeError("Kakao access_token missing")
    return access

def kakao_send_text(access_token: str, text: str, link_url: str) -> None:
    template_object = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": link_url, "mobile_web_url": link_url},
        "button_title": "브리핑 열기",
    }
    r = requests.post(
        KAKAO_MEMO_SEND_API,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template_object, ensure_ascii=False)},
        timeout=20,
    )
    if not r.ok:
        logging.error("[Kakao send ERROR] %s", r.text)
    r.raise_for_status()

# =========================
# Naver OpenAPI
# =========================
def naver_api_search(query: str, display: int = 50, start: int = 1) -> List[dict]:
    cid = os.getenv("NAVER_CLIENT_ID", "").strip()
    csec = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        raise RuntimeError("Missing NAVER_CLIENT_ID / NAVER_CLIENT_SECRET")
    headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec}
    params = {"query": query, "display": display, "start": start, "sort": "date"}
    r = requests.get(NAVER_NEWS_API, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("items", [])

def naver_search_window(query: str, start_kst: datetime, end_kst: datetime, max_pages: int) -> List[dict]:
    collected: List[dict] = []
    display = 50
    start_idx = 1

    for _ in range(max_pages):
        items = naver_api_search(query, display=display, start=start_idx)
        if not items:
            break

        stop_early = False
        for it in items:
            pub = it.get("pubDate", "")
            try:
                dt = parsedate_to_datetime(pub).astimezone(KST)
            except Exception:
                continue

            if dt < start_kst:
                stop_early = True
                continue
            if not (start_kst <= dt < end_kst):
                continue

            title = clean_html(it.get("title", ""))
            desc = clean_html(it.get("description", ""))
            origin = (it.get("originallink") or "").strip()
            nlink = (it.get("link") or "").strip()
            url = origin or nlink
            dom = domain_of(url)

            if (not url) or is_blocked_domain(dom):
                continue

            text = f"{title} {desc}"
            if looks_low_relevance(text) or looks_out_of_season(text):
                continue

            collected.append({
                "title": title,
                "description": desc,
                "published_kst": dt.isoformat(),
                "published_hm": dt.strftime("%m/%d %H:%M"),
                "domain": dom,
                "press": press_name(dom),
                "url": url,
                "query": query,
            })

        if stop_early:
            break

        start_idx += display
        time.sleep(0.05)

    return collected

def dedupe(items: List[dict]) -> List[dict]:
    seen = set()
    out = []
    for it in items:
        u = (it.get("url") or "").strip()
        t = (it.get("title") or "").strip().lower()
        if not u or not t:
            continue
        # URL 우선 + 제목 정규화로 중복 제거
        key = u[:280] + "|" + re.sub(r"\s+", " ", t)[:140]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def quality_score(it: dict) -> int:
    """
    점수로 메이저/중견/지방지/지방방송/공공을 “살리되”
    군소는 차단 또는 낮은 점수로 뒤로.
    """
    s = 0
    dom = it.get("domain", "")
    text = f"{it.get('title','')} {it.get('description','')}"

    if is_trusted_domain(dom):
        s += 6
    # 공공/기관은 추가 가점
    if dom.endswith(".go.kr") or dom.endswith(".or.kr"):
        s += 2
    if has_any(text, HIGH_RELEVANCE_HINTS):
        s += 3
    # 쿼리 자체가 섹션 핵심이면 약간 가점(실무 적합)
    q = it.get("query","")
    if any(k in q for k in ["수급","출하","저장","도매","경매","방제","화상병","APC","온라인 도매시장","할당관세"]):
        s += 1
    return s

def classify_section(it: dict) -> str:
    t = f"{it.get('title','')} {it.get('description','')}"
    if any(k in t for k in ["온라인 도매시장", "허위거래", "이상거래", "전수조사", "할당관세", "검역", "할인", "물가", "대책", "휴무", "경매 재개", "가락시장", "도매시장"]):
        return "주요 이슈 및 정책"
    if any(k in t for k in ["화상병", "병해충", "방제", "약제", "탄저", "기계유", "동해", "냉해", "월동해충", "서리"]):
        return "병해충 및 방제"
    if any(k in t for k in ["APC", "산지유통", "선별", "CA", "저장시설", "공판장", "수출", "물류", "콜드체인"]):
        return "유통 및 현장(APC/수출)"
    return "품목 및 수급 동향"

def collect_articles(start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    buckets: Dict[str, List[dict]] = {s: [] for s in SECTION_ORDER}
    seen_urls: set[str] = set()

    # 1) 섹션별 정밀 수집(키워드가 넓어졌으므로 “필요량 채우면 중단”)
    for sec in SECTION_ORDER:
        local: List[dict] = []
        for q in SECTION_QUERIES.get(sec, []):
            local.extend(naver_search_window(q, start_kst, end_kst, max_pages=MAX_PAGES_PER_QUERY))

            # 충분히 모이면 중단(속도/쿼터 절약)
            if len(local) >= MAX_ARTICLES_PER_SECTION * 10:
                break

        local = dedupe(local)
        local.sort(key=lambda x: (quality_score(x), x.get("published_kst","")), reverse=True)

        picked: List[dict] = []
        for it in local:
            u = it["url"]
            if u in seen_urls:
                continue
            picked.append(it)
            seen_urls.add(u)
            if len(picked) >= MAX_ARTICLES_PER_SECTION:
                break

        buckets[sec] = picked
        logging.info("[Collect] %s: %d", sec, len(buckets[sec]))

    # 2) 백필: 부족 섹션이 있으면 넓게 긁고 자동 분류하여 채움
    if any(len(buckets[s]) < MIN_ARTICLES_PER_SECTION for s in SECTION_ORDER):
        pool: List[dict] = []
        for q in GLOBAL_BACKFILL_QUERIES:
            pool.extend(naver_search_window(q, start_kst, end_kst, max_pages=MAX_PAGES_PER_QUERY))

        pool = dedupe(pool)
        pool.sort(key=lambda x: (quality_score(x), x.get("published_kst","")), reverse=True)
        pool = pool[:GLOBAL_BACKFILL_LIMIT]

        for it in pool:
            u = it["url"]
            if u in seen_urls:
                continue
            sec = classify_section(it)
            if len(buckets[sec]) >= MAX_ARTICLES_PER_SECTION:
                continue
            buckets[sec].append(it)
            seen_urls.add(u)

        for sec in SECTION_ORDER:
            logging.info("[Backfill] %s: %d", sec, len(buckets[sec]))

    return buckets

# =========================
# OpenAI 요약(2~3문장 + 체크포인트)
# =========================
def openai_summarize(buckets: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    total = sum(len(v) for v in buckets.values())
    if total == 0:
        return buckets

    if not api_key:
        for sec in SECTION_ORDER:
            for a in buckets[sec]:
                a["summary"] = a.get("description","") or a.get("title","")
                a["point"] = ""
        return buckets

    compact = []
    for sec in SECTION_ORDER:
        for a in buckets[sec]:
            compact.append({
                "section": sec,
                "press": a.get("press",""),
                "title": a.get("title",""),
                "description": a.get("description",""),
                "url": a.get("url",""),
            })

    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "summary": {"type": "string"},
                        "point": {"type": "string"},
                    },
                    "required": ["url","summary","point"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }

    system = (
        "너는 농협 경제지주 원예수급부(과수화훼팀 중심) 내부 공유용 뉴스 브리핑 작성자다.\n"
        "각 기사마다 아래 순서를 반드시 지켜라:\n"
        "1) summary: 2~3문장으로 핵심만(수급/가격/물량/출하/저장/유통/정책/방제 관점)\n"
        "2) point: 체크포인트 1문장(팀이 무엇을 확인/대응해야 하는지)\n"
        "과장/추측 금지. 애매하면 보수적으로.\n"
        "문장 짧고 가독성 좋게.\n"
    )
    user = f"기간(KST): {start_kst.isoformat()} ~ {end_kst.isoformat()}\n{json.dumps(compact, ensure_ascii=False)}"

    payload = {
        "model": OPENAI_MODEL,
        "input": [{"role":"system","content":system},{"role":"user","content":user}],
        "reasoning_effort": OPENAI_REASONING_EFFORT,
        "max_output_tokens": OPENAI_MAX_OUTPUT_TOKENS,
        "text": {"format": {"type":"json_schema","name":"agri_summaries","strict":True,"schema":schema}},
        "store": False,
    }

    r = requests.post(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type":"application/json"},
        json=payload,
        timeout=90,
    )
    if not r.ok:
        logging.error("[OpenAI ERROR] %s", r.text)
        for sec in SECTION_ORDER:
            for a in buckets[sec]:
                a["summary"] = a.get("description","") or a.get("title","")
                a["point"] = ""
        return buckets

    data = r.json()
    out_text = ""
    for item in data.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    out_text += c.get("text","")
    out_text = out_text.strip()
    if not out_text:
        return buckets

    j = json.loads(out_text)
    mp = {it["url"]: it for it in j.get("items", [])}

    for sec in SECTION_ORDER:
        for a in buckets[sec]:
            u = a.get("url","")
            m = mp.get(u, {})
            summary = (m.get("summary") or "").strip()
            point = (m.get("point") or "").strip()
            if not summary:
                summary = a.get("description","") or a.get("title","")
            a["summary"] = summary
            a["point"] = point

    return buckets

# =========================
# 상세 페이지(모바일 카드 UI)
# =========================
def make_html(buckets: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> str:
    total = sum(len(v) for v in buckets.values())
    span_days = (end_kst.date() - start_kst.date()).days

    def esc(x: str) -> str:
        return html.escape(x or "")

    def card(a: dict) -> str:
        press = esc(a.get("press","미상"))
        hm = esc(a.get("published_hm",""))
        title = esc(a.get("title",""))
        summary = esc((a.get("summary") or "").strip())
        point = esc((a.get("point") or "").strip())
        url = a.get("url","")

        point_html = f'<div class="point">체크포인트: {point}</div>' if point else ""
        return f"""
        <div class="card">
          <div class="meta"><span class="press">{press}</span><span class="time">{hm}</span></div>
          <div class="title">{title}</div>
          <div class="summary">{summary}</div>
          {point_html}
          <a class="btn" href="{esc(url)}" target="_blank" rel="noopener noreferrer">원문 열기</a>
        </div>
        """

    sections_html = ""
    for sec in SECTION_ORDER:
        items = buckets.get(sec, [])
        sections_html += f'<div class="section"><h2>{esc(sec)} <span class="count">({len(items)})</span></h2>'
        if not items:
            sections_html += '<div class="empty">특이사항 없음</div></div>'
            continue
        for a in items:
            sections_html += card(a)
        sections_html += "</div>"

    note = ""
    if span_days >= 2:
        note = f"휴일/주말 누적 포함: {span_days}일"

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>농산물 뉴스 브리핑</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#fff; --line:#e5e7eb; --text:#111827; --muted:#6b7280;
  }}
  body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;}}
  .wrap{{max-width:900px;margin:0 auto;padding:14px;}}
  .header{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px;box-shadow:0 2px 10px rgba(0,0,0,.04);}}
  .h1{{font-size:18px;font-weight:800;margin:0 0 6px;}}
  .sub{{color:var(--muted);font-size:13px;line-height:1.35;}}
  .chips{{margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;}}
  .chip{{font-size:12px;color:#111;border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 10px;}}
  .section{{margin-top:12px;}}
  h2{{font-size:16px;margin:14px 2px 10px;}}
  .count{{color:var(--muted);font-weight:600;}}
  .empty{{color:var(--muted);background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:12px;}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:10px 0;box-shadow:0 2px 10px rgba(0,0,0,.03);}}
  .meta{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}}
  .press{{font-weight:800;font-size:13px;}}
  .time{{color:var(--muted);font-size:12px;}}
  .title{{font-size:15px;font-weight:800;line-height:1.35;margin:4px 0 8px;}}
  .summary{{font-size:14px;line-height:1.5;color:#111;margin:0 0 8px;}}
  .point{{font-size:13px;line-height:1.4;color:#0f172a;background:#f3f4f6;border-radius:10px;padding:8px 10px;margin:6px 0 10px;}}
  .btn{{display:inline-block;text-decoration:none;font-weight:800;font-size:14px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;}}
  .footer{{color:var(--muted);font-size:12px;margin:18px 4px 8px;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="h1">농산물 뉴스 브리핑</div>
    <div class="sub">기간: {esc(start_kst.strftime('%Y-%m-%d %H:%M'))} ~ {esc(end_kst.strftime('%Y-%m-%d %H:%M'))} (KST) · 총 {total}건<br>{esc(note)}</div>
    <div class="chips">
      {''.join([f'<div class="chip">{html.escape(sec)} {len(buckets.get(sec, []))}건</div>' for sec in SECTION_ORDER])}
    </div>
  </div>

  {sections_html}

  <div class="footer">* 휴일/주말에는 발송을 스킵하고 state가 갱신되지 않아, 다음 영업일에 자동으로 누적 구간이 확장됩니다(중복 URL은 1회만 반영).</div>
</div>
</body>
</html>
"""

def publish_to_pages(html_text: str, end_kst: datetime) -> None:
    if PUBLISH_MODE != "github_pages":
        return
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[Pages] missing repo/token")
        return
    raw, sha = github_get_file(repo, PAGES_FILE_PATH, token, ref=PAGES_BRANCH)
    _ = raw
    github_put_file(
        repo, PAGES_FILE_PATH, token, html_text,
        branch=PAGES_BRANCH, sha=sha,
        message=f"Publish brief {end_kst.strftime('%Y-%m-%d')}",
    )

# =========================
# 카톡 메시지(본문 URL 제거)
# =========================
def auto_pages_url() -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}/"

def build_kakao_message(buckets: Dict[str, List[dict]], end_kst: datetime, span_days: int) -> str:
    total = sum(len(v) for v in buckets.values())
    span_hint = f" (누적 {span_days}일)" if span_days >= 2 else ""
    counts = " / ".join([
        f"품목 {len(buckets.get('품목 및 수급 동향', []))}",
        f"정책 {len(buckets.get('주요 이슈 및 정책', []))}",
        f"방제 {len(buckets.get('병해충 및 방제', []))}",
        f"유통 {len(buckets.get('유통 및 현장(APC/수출)', []))}",
    ])

    highlights = []
    for sec in SECTION_ORDER:
        if not buckets.get(sec):
            continue
        a = buckets[sec][0]
        highlights.append(f"- {a.get('press','')}: {clamp(a.get('title',''), 26)}")
        if len(highlights) >= 3:
            break
    if not highlights:
        highlights = ["- 핵심 기사가 부족합니다(기간/필터/키워드 점검 필요)"]

    msg = "\n".join([
        f"[농산물 브리핑] {end_kst.strftime('%m/%d')} {RUN_HOUR_KST:02d}시 · {total}건{span_hint}",
        f"섹션: {counts}",
        "오늘 핵심 3줄:",
        *highlights,
        "👇 버튼 ‘브리핑 열기’에서 요약/체크포인트/원문 확인",
    ])
    return clamp(msg, KAKAO_MESSAGE_SOFT_LIMIT)

# =========================
# Main
# =========================
def main():
    now_kst = datetime.now(tz=KST)
    end_kst = compute_fixed_end_kst(now_kst, RUN_HOUR_KST, EARLY_GRACE_MINUTES)

    # 영업일만 발송(휴일/주말은 스킵 -> state 미갱신 -> 다음 영업일 누적)
    if (not FORCE_SEND) and (not is_business_day(end_kst.date())):
        logging.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date())
        return

    state = load_state(end_kst)
    try:
        start_kst = datetime.fromisoformat(state.last_end_kst_iso)
        if start_kst.tzinfo is None:
            start_kst = start_kst.replace(tzinfo=KST)
    except Exception:
        start_kst = end_kst - timedelta(hours=24)

    if start_kst >= end_kst:
        start_kst = end_kst - timedelta(hours=24)

    logging.info("[INFO] Window KST: %s ~ %s", start_kst, end_kst)

    view_url = BRIEF_VIEW_URL or auto_pages_url()
    if not view_url:
        raise RuntimeError("BRIEF_VIEW_URL is empty and auto_pages_url failed.")

    # 1) 수집(키워드 전면 재조정 + 백필)
    buckets = collect_articles(start_kst, end_kst)

    # 2) 요약
    buckets = openai_summarize(buckets, start_kst, end_kst)

    # 3) 상세 페이지 발행
    html_page = make_html(buckets, start_kst, end_kst)
    publish_to_pages(html_page, end_kst)

    # 4) 카톡 1메시지(본문 URL 제거)
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not refresh_token:
        raise RuntimeError("Missing KAKAO_REFRESH_TOKEN")
    access = kakao_refresh_access_token(refresh_token)

    span_days = (end_kst.date() - start_kst.date()).days
    msg = build_kakao_message(buckets, end_kst, span_days)
    kakao_send_text(access, msg, view_url)

    # 5) state 저장(발송 성공 후)
    save_state(end_kst)
    logging.info("[DONE] sent and state updated: %s", end_kst.isoformat())

if __name__ == "__main__":
    main()
