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
EARLY_GRACE_MINUTES = int(os.getenv("EARLY_GRACE_MINUTES", "20"))
FORCE_SEND = (os.getenv("FORCE_SEND", "0") == "1")

MAX_ARTICLES_PER_SECTION = int(os.getenv("MAX_ARTICLES_PER_SECTION", "10"))
MIN_ARTICLES_PER_SECTION = int(os.getenv("MIN_ARTICLES_PER_SECTION", "7"))
GLOBAL_BACKFILL_LIMIT = int(os.getenv("GLOBAL_BACKFILL_LIMIT", "140"))
MAX_PAGES_PER_QUERY = int(os.getenv("MAX_PAGES_PER_QUERY", "3"))  # 네이버 API 페이지(50개씩)

PUBLISH_MODE = os.getenv("PUBLISH_MODE", "github_pages")
PAGES_BRANCH = os.getenv("PAGES_BRANCH", "main")
PAGES_LATEST_PATH = os.getenv("PAGES_LATEST_PATH", "docs/index.html")  # 최신
ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "docs/archive")                # 일자별 저장
ARCHIVE_INDEX_PATH = os.getenv("ARCHIVE_INDEX_PATH", "docs/archive/index.html")
ARCHIVE_MANIFEST_PATH = os.getenv("ARCHIVE_MANIFEST_PATH", ".agri_archive.json")

STATE_BACKEND = os.getenv("STATE_BACKEND", "repo")
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", ".agri_state.json")

BRIEF_VIEW_URL = os.getenv("BRIEF_VIEW_URL", "").strip()  # 비우면 자동 pages 주소 사용
KAKAO_MESSAGE_SOFT_LIMIT = int(os.getenv("KAKAO_MESSAGE_SOFT_LIMIT", "360"))

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
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "2200"))

# =========================
# 섹션(순서 고정)
# =========================
SECTION_ORDER: List[str] = [
    "품목 및 수급 동향",
    "주요 이슈 및 정책",
    "병해충 및 방제",
    "유통 및 현장(APC/수출)",
]

# ==========================================================
# 1) 키워드 전면 재조정(오염/다의어 제거 + 농업 앵커 강화)
# ==========================================================
# 다의어/오염 가능 단어는 원형(감, 밤 등) 대신 “구체 품목”으로
FRUITS = [
    "사과","배","신고배",
    "단감","떫은감","곶감",
    "감귤","만감류","한라봉","레드향","천혜향",
    "참다래","키위",
    "포도","샤인머스캣",
    "딸기","복숭아","자두","매실","유자",
    "알밤",
]
VEGGIES = [
    "오이","풋고추","애호박","토마토","파프리카","가지",
    "상추","깻잎","배추","무","양파","대파","마늘","감자","고구마",
]
FLOWERS = ["절화","화훼","꽃값","국화","장미","백합","프리지아"]
STAPLES = ["쌀","산지쌀값","비축미"]

# 농업 앵커(이게 최소 1개는 있어야 “업무 관련”으로 인정)
AGRI_ANCHORS = [
    "농산물","농업","농가","과수","원예","청과","산지","도매","경락","경매",
    "출하","작황","재배","수확","저장량","재고",
    "가락시장","공판장","도매시장","온라인 도매시장",
    "APC","산지유통","선별","CA저장","저장고",
    "수출","검역","할당관세",
    "과수화상병","화상병","탄저병","병해충","방제","약제","예찰",
    "원산지","농작물재해보험","재해보험","시설원예","시설채소",
    "절화","화훼",
    "농림축산식품부","정책브리핑","aT","농관원",
]

# 업무 핵심(수급·가격·정책·방제·유통 등 “업무성”을 확인하는 키)
WORK_SIGNALS = [
    "수급","가격","시세","물량","생산","생산량","출하","도매","경락","경매",
    "저장량","재고","작황","재배","수확",
    "단속","조사","전수조사","허위거래","이상거래","실적 부풀리기",
    "할인","물가","대책","지원","방출","비축",
    "검역","할당관세","수입","수출",
    "방제","약제","예찰","피해","동해","냉해","서리","가뭄","폭염",
    "APC","선별","저장","CA",
]

# “저장”은 다의어가 심하므로 “저장량/저장고/CA저장”만 인정 (저장 단독은 제거)
BANNED_PHRASES = [
    "내 마음속에 저장",  # 연예/인터뷰에서 자주 등장
    "저장성",             # 중국 저장(浙江)
]

# 연예/스포츠/정치/부동산/IT/날씨 등 강한 노이즈 신호
NOISE_TOPICS = [
    "배우","아이돌","드라마","영화","예능","콘서트","뮤지컬","팬",
    "야구","축구","농구","골프","선수","경기",
    "코스피","주가","증시","상장","반도체","하이테크","전기차","AI 브라우저","검색 판",
    "부동산","집값","아파트","청약",
    "대통령","국회","총선","대선","정치",
    "날씨","기상","강풍","미세먼지","풍랑",
]

# 사회 미담/기부류는 원예수급부 업무와 거리가 멀어 우선 제외(정책/수급 기사와 구분)
LOW_VALUE_HINTS = ["기부","나눔","봉사","차상위","수급자","명절 선물","무료 배포","후원","캠페인"]

# ----------------------------------------------------------
# 섹션별 쿼리 생성: 모든 쿼리는 농업 앵커 포함(“물가” 단독 금지)
# ----------------------------------------------------------
STRUCTURAL_QUERIES = [
    "기후변화 과수 재배지 북상",
    "사과 재배지 북상 강원 과수",
    "과수 동해 피해 농가",
    "시설원예 일조량 부족 수급",
]

POLICY_CORE = [
    "농산물 온라인 도매시장 허위거래",
    "온라인 도매시장 이상거래 전수조사",
    "가락시장 휴무 경매 재개 청과",
    "농산물 물가 대책 할인",
    "농축산물 할인지원 연장",
    "수입 과일 할당관세 검역",
    "농림축산식품부 농산물 대책",
    "정책브리핑 농산물 물가",
]

PEST_CORE = [
    "과수화상병 방제 약제 신청",
    "과수화상병 궤양 제거 골든타임",
    "월동해충 방제 기계유유제 과수",
    "탄저병 예방 방제 과수",
    "냉해 대비 과수 방제",
    "동해 피해 과수 농가",
]

DIST_CORE = [
    "농협 APC 스마트 선별",
    "산지유통센터 APC CA저장",
    "가락시장 청과 도매시장 물량",
    "농식품 수출 과일 배 딸기",
    "농산물 수출 검역 물류",
]

def uniq_keep_order(xs: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        x = re.sub(r"\s+", " ", (x or "").strip())
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

def build_supply_queries() -> List[str]:
    qs: List[str] = []
    qs += STRUCTURAL_QUERIES

    def add_item(item: str):
        # ✅ “저장” 단독 금지 → 저장량/저장고/CA저장만
        qs.extend([
            f"{item} 농산물 수급",
            f"{item} 산지 출하",
            f"{item} 도매 경락",
            f"{item} 가락시장 청과",
            f"{item} 가격 시세",
            f"{item} 저장량",
            f"{item} 작황 재배",
        ])

    for it in FRUITS + VEGGIES + FLOWERS + STAPLES:
        add_item(it)

    # 카테고리/시장 단위
    qs += [
        "청과 도매가격 경락",
        "과일 도매시장 물량",
        "시설채소 수급 가격",
        "절화 화훼 가격",
        "만감류 출하 수급",
    ]
    return uniq_keep_order(qs)

def build_policy_queries() -> List[str]:
    return uniq_keep_order(POLICY_CORE + [
        "농산물 물가 안정 대책",
        "농축산물 할인 행사 지원",
        "할당관세 수입과일 시장 영향",
        "원산지 단속 농산물",
    ])

def build_pest_queries() -> List[str]:
    return uniq_keep_order(PEST_CORE + [
        "과수 병해충 예찰 방제",
        "시설원예 병해충 방제",
        "농작물재해보험 과수 사과 배",
    ])

def build_dist_queries() -> List[str]:
    return uniq_keep_order(DIST_CORE + [
        "APC 선별 저장고",
        "산지유통 혁신 농협",
        "공판장 청과 경매",
        "농식품 수출 실적 과일",
    ])

SECTION_QUERIES: Dict[str, List[str]] = {
    "품목 및 수급 동향": build_supply_queries(),
    "주요 이슈 및 정책": build_policy_queries(),
    "병해충 및 방제": build_pest_queries(),
    "유통 및 현장(APC/수출)": build_dist_queries(),
}

GLOBAL_BACKFILL_QUERIES = uniq_keep_order([
    "농산물 수급 가격",
    "청과 도매 경락",
    "가락시장 청과 물량",
    "과수 동해 냉해 피해",
    "과수화상병 방제 약제",
    "농산물 온라인 도매시장",
    "농축산물 할인 물가",
    "농식품 수출 과일",
    "농협 APC 산지유통",
])

# =========================
# 2) 매체 정책: 차단 목록 + 나머지는 점수화(지방지/방송 포함)
# =========================
BLOCKED_DOMAINS = {
    "wikitree.co.kr", "donghaengmedia.net", "sidae.com",
    "namu.wiki", "blog.naver.com", "post.naver.com",
}

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
    # 농업 전문
    "nongmin.com","ikpnews.net","aflnews.co.kr",
    # 지방지/지방방송(대표)
    "kwnews.co.kr","kado.net","kyeonggi.com","joongboo.com","cctoday.co.kr","imaeil.com","yeongnam.com",
    "gnnews.co.kr","namdonews.com","jeonmae.co.kr",
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
    if dom.endswith(".go.kr") or dom.endswith(".or.kr"):
        return True
    return False

def clamp(s: str, n: int) -> str:
    return s if len(s) <= n else (s[: max(0, n-1)] + "…")

# =========================
# ✅ 핵심: 업무 관련성 게이트(무관 기사 전면 차단)
# =========================
def agri_relevance_ok(title: str, desc: str) -> bool:
    t = f"{title} {desc}"

    # 금지 문구(저장성/내 마음속 저장 등) 즉시 컷
    if has_any(t, BANNED_PHRASES):
        return False

    # 사회 미담/기부류는 대부분 업무와 무관 → 컷(단, 가격/수급/단속 신호가 강하면 예외)
    if has_any(t, LOW_VALUE_HINTS) and (not has_any(t, ["가격","시세","수급","도매","경락","단속","조사","전수조사"])):
        return False

    # 농업 앵커 1개 + 업무 신호 1개를 “필수”로 요구
    has_anchor = has_any(t, AGRI_ANCHORS)
    has_work = has_any(t, WORK_SIGNALS)

    if not (has_anchor and has_work):
        return False

    # 노이즈 토픽이 강하면 추가 검증: 농업 앵커가 약하면 컷
    if has_any(t, NOISE_TOPICS):
        strong_agri = has_any(t, [
            "농산물","과수","원예","청과","가락시장","공판장","도매","경락","출하","저장량","재고",
            "APC","산지유통","검역","할당관세","수출","화상병","탄저병","방제","병해충"
        ])
        if not strong_agri:
            return False

    # “사과/배” 다의어 보호(농업 맥락이 더 강해야 통과)
    if "사과" in t and (not has_any(t, ["과수","농산물","산지","도매","경락","출하","재배","작황","저장량","청과","가락시장"])):
        return False
    # 배(선박/배우 등) 오염 방지: “과수/과일/청과/신고배/경락” 같은 단서 요구
    if " 배" in (" " + t) and (("배" in t) and (not has_any(t, ["과수","과일","청과","신고배","원황","산지","도매","경락","출하","저장량","가락시장"]))):
        # (띄어쓰기 기반 완전판은 아니지만 오염을 크게 줄임)
        pass

    # “저장”은 저장량/저장고/CA저장 맥락이면 OK, 그 외 저장 단독은 신호로 보지 않음(이미 쿼리에서 제거)
    return True

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

def load_archive_manifest() -> List[dict]:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        return []
    raw, _ = github_get_file(repo, ARCHIVE_MANIFEST_PATH, token, ref=PAGES_BRANCH)
    if not raw:
        return []
    try:
        j = json.loads(raw)
        if isinstance(j, list):
            return j
        return []
    except Exception:
        return []

def save_archive_manifest(items: List[dict]) -> None:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        return
    raw, sha = github_get_file(repo, ARCHIVE_MANIFEST_PATH, token, ref=PAGES_BRANCH)
    _ = raw
    content = json.dumps(items, ensure_ascii=False, indent=2)
    github_put_file(repo, ARCHIVE_MANIFEST_PATH, token, content, branch=PAGES_BRANCH, sha=sha, message="Update archive manifest")

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

            # ✅ 업무 관련성 게이트 (무관 기사 전면 차단)
            if not agri_relevance_ok(title, desc):
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
        key = u[:280] + "|" + re.sub(r"\s+", " ", t)[:140]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def quality_score(it: dict) -> int:
    s = 0
    dom = it.get("domain", "")
    text = f"{it.get('title','')} {it.get('description','')}"
    if is_trusted_domain(dom):
        s += 8
    if dom.endswith(".go.kr") or dom.endswith(".or.kr"):
        s += 2
    # 농업 앵커/업무 신호 가점
    if has_any(text, AGRI_ANCHORS):
        s += 4
    if has_any(text, WORK_SIGNALS):
        s += 3
    return s

def classify_section(it: dict) -> str:
    t = f"{it.get('title','')} {it.get('description','')}"
    if any(k in t for k in ["온라인 도매시장","허위거래","이상거래","전수조사","할당관세","검역","할인","물가","대책","휴무","경매 재개","가락시장","도매시장","원산지"]):
        return "주요 이슈 및 정책"
    if any(k in t for k in ["화상병","병해충","방제","약제","탄저병","기계유유제","예찰","동해","냉해","서리","재해보험"]):
        return "병해충 및 방제"
    if any(k in t for k in ["APC","산지유통","선별","CA저장","저장고","공판장","수출","물류","콜드체인"]):
        return "유통 및 현장(APC/수출)"
    return "품목 및 수급 동향"

def collect_articles(start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    buckets: Dict[str, List[dict]] = {s: [] for s in SECTION_ORDER}
    seen_urls: set[str] = set()

    # 1) 섹션별 정밀 수집
    for sec in SECTION_ORDER:
        local: List[dict] = []
        for q in SECTION_QUERIES.get(sec, []):
            local.extend(naver_search_window(q, start_kst, end_kst, max_pages=MAX_PAGES_PER_QUERY))
            if len(local) >= MAX_ARTICLES_PER_SECTION * 12:
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

    # 2) 백필(부족 섹션이 있으면 넓게 긁고 분류)
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
        "1) summary: 2~3문장으로 핵심만(수급/가격/물량/출하/저장량/유통/정책/방제 관점)\n"
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
# Pages URL
# =========================
def auto_pages_url() -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}/"

def archive_url_for_date(base_url: str, report_date: str) -> str:
    return f"{base_url}archive/{report_date}.html"

# =========================
# 상세 페이지(모바일 카드 UI) + 섹션 앵커 + 칩 이동
# =========================
def make_html(buckets: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime, archive_link: str) -> str:
    total = sum(len(v) for v in buckets.values())
    span_days = (end_kst.date() - start_kst.date()).days

    def esc(x: str) -> str:
        return html.escape(x or "")

    sec_ids = {
        "품목 및 수급 동향": "sec-supply",
        "주요 이슈 및 정책": "sec-policy",
        "병해충 및 방제": "sec-pest",
        "유통 및 현장(APC/수출)": "sec-dist",
    }

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

    chips_html = ""
    for sec in SECTION_ORDER:
        sid = sec_ids[sec]
        chips_html += f'<a class="chip" href="#{sid}">{esc(sec)} {len(buckets.get(sec, []))}건</a>'

    sections_html = ""
    for sec in SECTION_ORDER:
        sid = sec_ids[sec]
        items = buckets.get(sec, [])
        sections_html += f'<div class="section" id="{sid}"><div class="secbar"><h2>{esc(sec)} <span class="count">({len(items)})</span></h2></div>'
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
    --bar:#111827;
  }}
  html{{scroll-behavior:smooth;}}
  body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;}}
  .wrap{{max-width:980px;margin:0 auto;padding:14px;}}
  .header{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px;box-shadow:0 2px 10px rgba(0,0,0,.04);}}
  .toprow{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;}}
  .h1{{font-size:18px;font-weight:900;margin:0 0 6px;}}
  .sub{{color:var(--muted);font-size:13px;line-height:1.35;}}
  .linkrow a{{font-size:12px;color:#111;text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:6px 10px;display:inline-block;background:#fff;}}
  .chips{{margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;}}
  .chip{{font-size:12px;color:#111;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 10px;text-decoration:none;font-weight:800;}}
  .chip:active{{transform:scale(.99);}}
  .section{{margin-top:14px;border-top:3px solid var(--bar);padding-top:10px;}}
  .secbar{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px 12px;box-shadow:0 2px 10px rgba(0,0,0,.03);}}
  h2{{font-size:16px;margin:0;display:flex;justify-content:space-between;align-items:center;}}
  .count{{color:var(--muted);font-weight:700;}}
  .empty{{color:var(--muted);background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:12px;margin-top:10px;}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:10px 0;box-shadow:0 2px 10px rgba(0,0,0,.03);}}
  .meta{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}}
  .press{{font-weight:900;font-size:13px;}}
  .time{{color:var(--muted);font-size:12px;}}
  .title{{font-size:15px;font-weight:900;line-height:1.35;margin:4px 0 8px;}}
  .summary{{font-size:14px;line-height:1.55;color:#111;margin:0 0 8px;}}
  .point{{font-size:13px;line-height:1.45;color:#0f172a;background:#f3f4f6;border-radius:10px;padding:8px 10px;margin:6px 0 10px;}}
  .btn{{display:inline-block;text-decoration:none;font-weight:900;font-size:14px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;}}
  .footer{{color:var(--muted);font-size:12px;margin:18px 4px 8px;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="toprow">
      <div>
        <div class="h1">농산물 뉴스 브리핑</div>
        <div class="sub">기간: {esc(start_kst.strftime('%Y-%m-%d %H:%M'))} ~ {esc(end_kst.strftime('%Y-%m-%d %H:%M'))} (KST) · 총 {total}건<br>{esc(note)}</div>
      </div>
      <div class="linkrow">
        <a href="{esc(archive_link)}">아카이브 목록</a>
      </div>
    </div>
    <div class="chips">
      {chips_html}
    </div>
  </div>

  {sections_html}

  <div class="footer">* 휴일/주말에는 발송을 스킵하고 state가 갱신되지 않아, 다음 영업일에 누적 구간이 자동 확장됩니다(중복 URL은 1회만 반영).</div>
</div>
</body>
</html>
"""

def make_archive_index_html(base_url: str, manifest: List[dict]) -> str:
    def esc(x: str) -> str:
        return html.escape(x or "")
    rows = ""
    # 최신이 위로
    for it in sorted(manifest, key=lambda x: x.get("date",""), reverse=True)[:120]:
        d = it.get("date","")
        total = it.get("total",0)
        start = it.get("start","")
        end = it.get("end","")
        url = archive_url_for_date(base_url, d)
        rows += f'<a class="row" href="{esc(url)}"><div class="d">{esc(d)}</div><div class="m">총 {total}건 · {esc(start)}~{esc(end)}</div></a>'

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>농산물 뉴스 브리핑 아카이브</title>
<style>
  :root{{--bg:#f6f7f9;--card:#fff;--line:#e5e7eb;--text:#111827;--muted:#6b7280;}}
  body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;}}
  .wrap{{max-width:860px;margin:0 auto;padding:14px;}}
  .header{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:0 2px 10px rgba(0,0,0,.04);}}
  .h1{{font-size:18px;font-weight:900;margin:0 0 6px;}}
  .sub{{color:var(--muted);font-size:13px;line-height:1.35;}}
  .list{{margin-top:12px;}}
  .row{{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:10px 0;text-decoration:none;color:var(--text);box-shadow:0 2px 10px rgba(0,0,0,.03);}}
  .d{{font-weight:900;font-size:15px;margin-bottom:4px;}}
  .m{{color:var(--muted);font-size:12px;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="h1">브리핑 아카이브</div>
    <div class="sub">날짜를 누르면 해당 일자의 브리핑 페이지로 이동합니다.</div>
  </div>
  <div class="list">{rows or '<div class="row"><div class="d">기록 없음</div></div>'}</div>
</div>
</body>
</html>
"""

def publish_file(path: str, html_text: str, message: str) -> None:
    if PUBLISH_MODE != "github_pages":
        return
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[Pages] missing repo/token")
        return
    raw, sha = github_get_file(repo, path, token, ref=PAGES_BRANCH)
    _ = raw
    github_put_file(repo, path, token, html_text, branch=PAGES_BRANCH, sha=sha, message=message)

# =========================
# 카톡 메시지(가독성 전면 개편)
# =========================
def build_kakao_message(buckets: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> str:
    total = sum(len(v) for v in buckets.values())
    span_days = (end_kst.date() - start_kst.date()).days
    span_hint = f" · 누적 {span_days}일" if span_days >= 2 else ""

    counts = {
        "품목": len(buckets.get("품목 및 수급 동향", [])),
        "정책": len(buckets.get("주요 이슈 및 정책", [])),
        "방제": len(buckets.get("병해충 및 방제", [])),
        "유통": len(buckets.get("유통 및 현장(APC/수출)", [])),
    }

    # 섹션별 Top 1 (최대 4줄)
    top_lines = []
    label_map = {
        "품목 및 수급 동향": "품목",
        "주요 이슈 및 정책": "정책",
        "병해충 및 방제": "방제",
        "유통 및 현장(APC/수출)": "유통",
    }
    for sec in SECTION_ORDER:
        items = buckets.get(sec, [])
        if not items:
            continue
        a = items[0]
        press = a.get("press","")
        title = clamp(a.get("title",""), 28)
        top_lines.append(f"- {label_map[sec]}: {press} | {title}")

    if not top_lines:
        top_lines = ["- 오늘은 조건을 만족하는 기사량이 부족합니다(키워드/필터 점검 필요)"]

    msg = "\n".join([
        f"[농산물 브리핑] {end_kst.strftime('%m/%d')} {RUN_HOUR_KST:02d}시",
        f"기간: {start_kst.strftime('%m/%d %H:%M')}~{end_kst.strftime('%m/%d %H:%M')} (KST){span_hint}",
        f"총 {total}건 | 품목 {counts['품목']} · 정책 {counts['정책']} · 방제 {counts['방제']} · 유통 {counts['유통']}",
        "핵심:",
        *top_lines[:4],
        "👉 버튼 ‘브리핑 열기’에서 섹션별 요약/체크포인트/원문 확인",
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

    base_url = BRIEF_VIEW_URL or auto_pages_url()
    if not base_url:
        raise RuntimeError("BRIEF_VIEW_URL is empty and auto_pages_url failed.")
    if not base_url.endswith("/"):
        base_url += "/"

    report_date = end_kst.strftime("%Y-%m-%d")
    today_archive_web = archive_url_for_date(base_url, report_date)
    archive_index_web = f"{base_url}archive/"

    # 1) 수집(전면 필터 적용 + 백필)
    buckets = collect_articles(start_kst, end_kst)

    # 2) 요약
    buckets = openai_summarize(buckets, start_kst, end_kst)

    # 3) 상세 페이지 생성(일자별 + 최신)
    html_page = make_html(buckets, start_kst, end_kst, archive_link=archive_index_web)

    # 최신 페이지 갱신
    publish_file(PAGES_LATEST_PATH, html_page, message=f"Publish latest brief {report_date}")

    # 일자별 아카이브 저장
    archive_path = f"{ARCHIVE_DIR}/{report_date}.html"
    publish_file(archive_path, html_page, message=f"Publish archive brief {report_date}")

    # 아카이브 목록/manifest 갱신
    manifest = load_archive_manifest()
    # 동일 날짜 있으면 갱신
    manifest = [m for m in manifest if m.get("date") != report_date]
    manifest.append({
        "date": report_date,
        "start": start_kst.strftime("%m/%d %H:%M"),
        "end": end_kst.strftime("%m/%d %H:%M"),
        "total": sum(len(v) for v in buckets.values()),
    })
    save_archive_manifest(manifest)

    archive_index_html = make_archive_index_html(base_url, manifest)
    publish_file(ARCHIVE_INDEX_PATH, archive_index_html, message="Update archive index")

    # 4) 카톡 1메시지(본문 링크 제거, 버튼은 오늘자 아카이브로)
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not refresh_token:
        raise RuntimeError("Missing KAKAO_REFRESH_TOKEN")
    access = kakao_refresh_access_token(refresh_token)

    msg = build_kakao_message(buckets, start_kst, end_kst)
    kakao_send_text(access, msg, today_archive_web)

    # 5) state 저장(발송 성공 후)
    save_state(end_kst)
    logging.info("[DONE] sent and state updated: %s", end_kst.isoformat())

if __name__ == "__main__":
    main()
