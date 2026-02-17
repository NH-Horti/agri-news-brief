# main.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
import json
import time
import base64
import html
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, quote_plus

import requests
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# =========================
# 운영 파라미터
# =========================
RUN_HOUR_KST = int(os.getenv("RUN_HOUR_KST", "7"))  # 항상 07:00 기준으로 기간 고정
FORCE_SEND = (os.getenv("FORCE_SEND", "0") == "1")  # 테스트용(휴일/주말에도 강제 발송)

MAX_ARTICLES_PER_SECTION = int(os.getenv("MAX_ARTICLES_PER_SECTION", "7"))  # 기사량 늘림(기본 7)
MIN_ARTICLES_PER_SECTION = int(os.getenv("MIN_ARTICLES_PER_SECTION", "4"))  # 섹션당 최소 목표(모자라면 필터 완화)

PUBLISH_MODE = os.getenv("PUBLISH_MODE", "github_pages")  # github_pages 권장
PAGES_BRANCH = os.getenv("PAGES_BRANCH", "main")
PAGES_FILE_PATH = os.getenv("PAGES_FILE_PATH", "docs/index.html")

STATE_BACKEND = os.getenv("STATE_BACKEND", "repo")  # repo 권장
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", ".agri_state.json")

# Pages 링크(없으면 자동 추정)
BRIEF_VIEW_URL = os.getenv("BRIEF_VIEW_URL", "").strip()

# 카톡 메시지(1개) 최적 길이(표시 제한/잘림 방지용 보수치)
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
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "1400"))


# =========================
# 섹션 / 쿼리 (순서 고정)
# =========================
SECTION_ORDER: List[Tuple[str, List[str]]] = [
    ("품목 및 수급 동향", [
        "사과 저장량 도매가격",
        "배 저장량 도매가격",
        "기후변화 사과 재배지 북상 강원도",
        "단감 저장량 시세",
        "떫은감 탄저병 곶감 생산량 가격 둥시",
        "감귤 한라봉 레드향 천혜향 가격",
        "참다래 키위 가격",
        "샤인머스캣 포도 가격",
        "매실 개화 전망 냉해",
        "풋고추 오이 애호박 시설채소 가격",
        "쌀 산지쌀값 비축미 방출",
        "절화 졸업 입학 시즌 꽃값",
    ]),
    ("주요 이슈 및 정책", [
        "농산물 온라인 도매시장 허위거래 이상거래 전수조사",
        "농산물 물가 할인 지원 연장",
        "할당관세 수입과일 검역 완화",
        "가락시장 휴무 경매 재개 일정",
        "농식품부 물가 안정 대책 농산물",
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
        "산지유통센터 APC 선별 저장",
    ]),
]


# =========================
# 품질 필터(운영형)
# =========================
LOW_RELEVANCE_HINTS = [
    "온누리상품권", "환급", "지역화폐", "상품권", "축제", "행사", "홍보", "체험", "관광", "맛집", "레시피",
]
OUT_OF_SEASON_HINTS = [
    "10월", "11월", "추석", "가을 수확", "수확기", "햇사과", "햇배",
]
HIGH_RELEVANCE_HINTS = [
    "가격", "시세", "도매", "경락", "물량", "수급", "출하", "저장", "재고", "작황", "생산량",
    "수입", "할당관세", "검역", "물가", "할인", "도매시장", "가락시장", "공판장",
    "APC", "선별", "CA", "저장", "수출", "방제", "병해충", "화상병", "탄저", "동해", "냉해",
]

# “주요 매체” 도메인(기본은 엄격, 부족하면 완화)
ALLOWED_DOMAINS = {
    # 통신/방송/포털 정책
    "yna.co.kr", "newsis.com", "korea.kr",
    # 중앙/경제지
    "mk.co.kr", "joongang.co.kr", "donga.com", "hani.co.kr", "khan.co.kr", "chosun.com",
    "hankyung.com", "sedaily.com", "edaily.co.kr", "asiae.co.kr", "heraldcorp.com",
    # 경제/종합(운영에서 자주 쓰는 수준)
    "mt.co.kr",  # 머니투데이
    # 농업/전문/공공
    "nongmin.com", "aflnews.co.kr", "ikpnews.net",
    "mafra.go.kr", "at.or.kr", "krei.re.kr", "naqs.go.kr",
}

BLOCKED_DOMAINS = {
    "wikitree.co.kr",
    "donghaengmedia.net",
    "sidae.com",
}

# 도메인 -> 언론명 표시(상세페이지에서 “언론명”이 핵심이라 매핑 강화)
PRESS_MAP = {
    "yna.co.kr": "연합뉴스",
    "newsis.com": "뉴시스",
    "korea.kr": "정책브리핑",
    "mk.co.kr": "매일경제",
    "mt.co.kr": "머니투데이",
    "joongang.co.kr": "중앙일보",
    "donga.com": "동아일보",
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "chosun.com": "조선일보",
    "hankyung.com": "한국경제",
    "sedaily.com": "서울경제",
    "edaily.co.kr": "이데일리",
    "asiae.co.kr": "아시아경제",
    "heraldcorp.com": "헤럴드경제",
    "nongmin.com": "농민신문",
    "aflnews.co.kr": "농수축산신문",
    "ikpnews.net": "한국농어민신문",
    "mafra.go.kr": "농림축산식품부",
    "at.or.kr": "aT",
    "krei.re.kr": "KREI",
    "naqs.go.kr": "농관원",
}


# =========================
# 공휴일 / 영업일 판단 + 오버라이드
# =========================
def is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def is_korean_holiday(d: date) -> bool:
    OVERRIDE_FORCE_WORKDAY = {
        # "2026-02-17",
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
        return False

def is_business_day(d: date) -> bool:
    return (not is_weekend(d)) and (not is_korean_holiday(d))


# =========================
# 시간 창(항상 07:00 기준)
# =========================
def compute_fixed_end_kst(now_kst: datetime, run_hour: int) -> datetime:
    end = now_kst.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    if now_kst < end:
        end -= timedelta(days=1)
    return end


# =========================
# GitHub repo 파일 read/write (state + pages)
# =========================
def github_get_file(repo: str, path: str, token: str, ref: str = "main") -> Tuple[Optional[str], Optional[str]]:
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if r.status_code == 404:
        return None, None
    if not r.ok:
        logging.error("[GitHub GET ERROR] %s", r.text)
        return None, None  # 401이어도 전체 중단하지 않게(운영 안정성)
    j = r.json()
    sha = j.get("sha")
    b64 = j.get("content", "")
    if j.get("encoding") == "base64" and b64:
        raw = base64.b64decode(b64).decode("utf-8", errors="replace")
        return raw, sha
    return None, sha

def github_put_file(repo: str, path: str, token: str, content_text: str, branch: str = "main",
                    sha: Optional[str] = None, message: str = "Update file") -> bool:
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
    # 기본: 24시간 전
    fallback = State(last_end_kst_iso=(default_last_end - timedelta(hours=24)).isoformat())

    if STATE_BACKEND != "repo":
        return fallback

    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[STATE] missing repo/token -> fallback")
        return fallback

    raw, _sha = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
    if not raw:
        return fallback

    try:
        j = json.loads(raw)
        v = j.get("last_end_kst_iso")
        if v:
            return State(last_end_kst_iso=v)
    except Exception:
        pass
    return fallback

def save_state(end_kst: datetime) -> None:
    if STATE_BACKEND != "repo":
        return
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[STATE] missing repo/token -> cannot save")
        return
    _raw, sha = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
    content = json.dumps({"last_end_kst_iso": end_kst.isoformat()}, ensure_ascii=False, indent=2)
    github_put_file(repo, STATE_FILE_PATH, token, content, branch=PAGES_BRANCH, sha=sha, message="Update agri-news state")


# =========================
# Kakao send (1 message)
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
        logging.error("[Kakao token ERROR BODY] %s", r.text)
        r.raise_for_status()
    j = r.json()
    access = j.get("access_token")
    if not access:
        raise RuntimeError(f"Kakao token refresh failed: {j}")
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
        logging.error("[Kakao send ERROR BODY] %s", r.text)
    else:
        logging.info("[Kakao send OK] %s", r.text)
    r.raise_for_status()


# =========================
# Naver OpenAPI 수집
# =========================
def clean_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def domain_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""

def press_name_from_domain(dom: str) -> str:
    if not dom:
        return "미상"
    if dom in PRESS_MAP:
        return PRESS_MAP[dom]
    # 하위도메인 처리(예: www.mk.co.kr)
    for k, v in PRESS_MAP.items():
        if dom == k or dom.endswith("." + k):
            return v
    return dom

def has_any(text: str, keys: List[str]) -> bool:
    return any(k in text for k in keys)

def looks_low_relevance(text: str) -> bool:
    t = text or ""
    # 낮은 키워드가 있고, 높은 키워드가 없으면 제외
    return has_any(t, LOW_RELEVANCE_HINTS) and (not has_any(t, HIGH_RELEVANCE_HINTS))

def looks_out_of_season(text: str) -> bool:
    t = text or ""
    out = has_any(t, OUT_OF_SEASON_HINTS)
    # '저장/전정/현재/설 이후' 같이 시기 보정 단서가 있으면 살림
    current_ok = has_any(t, ["저장", "저장량", "재고", "전정", "설", "설 이후", "최근", "현재"])
    return out and (not current_ok)

def is_major_domain(dom: str) -> bool:
    if not dom:
        return False
    if dom in BLOCKED_DOMAINS:
        return False
    if dom in ALLOWED_DOMAINS:
        return True
    for d in ALLOWED_DOMAINS:
        if dom.endswith("." + d):
            return True
    return False

def naver_api_search(query: str, display: int = 100, start: int = 1) -> List[dict]:
    cid = os.getenv("NAVER_CLIENT_ID", "").strip()
    csec = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        raise RuntimeError("Missing NAVER_CLIENT_ID / NAVER_CLIENT_SECRET")

    headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec}
    params = {"query": query, "display": display, "start": start, "sort": "date"}
    r = requests.get(NAVER_NEWS_API, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("items", [])

def naver_api_search_window(query: str, start_kst: datetime, end_kst: datetime, max_pages: int = 3) -> List[dict]:
    """
    최신순(date)으로 가져오며, pubDate가 start_kst 이전으로 내려가면 조기 종료.
    """
    collected: List[dict] = []
    display = 100
    start_idx = 1

    for _ in range(max_pages):
        items = naver_api_search(query, display=display, start=start_idx)
        if not items:
            break

        stop_early = False
        for it in items:
            pub = it.get("pubDate", "")
            try:
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    continue
                dt_kst = dt.astimezone(KST)
            except Exception:
                continue

            if dt_kst < start_kst:
                stop_early = True
                continue

            if not (start_kst <= dt_kst < end_kst):
                continue

            title = clean_html(it.get("title", ""))
            desc = clean_html(it.get("description", ""))
            origin = (it.get("originallink") or "").strip()
            naver_link = (it.get("link") or "").strip()
            url = origin or naver_link
            dom = domain_of(url)

            text = f"{title} {desc}"
            if dom in BLOCKED_DOMAINS:
                continue
            if looks_low_relevance(text):
                continue
            if looks_out_of_season(text):
                continue

            collected.append({
                "title": title,
                "description": desc,
                "published_kst": dt_kst.isoformat(),
                "domain": dom,
                "press": press_name_from_domain(dom),
                "url": url,
                "naver_link": naver_link,
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
        t = (it.get("title") or "").strip()
        if not u or not t:
            continue
        key = (u[:300] + "|" + re.sub(r"\s+", " ", t.lower())[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def quality_score(it: dict) -> int:
    """
    기사 품질 점수: 메이저 도메인 + 핵심 키워드 포함 우선.
    """
    s = 0
    dom = it.get("domain", "")
    text = f"{it.get('title','')} {it.get('description','')}"
    if is_major_domain(dom):
        s += 3
    if has_any(text, HIGH_RELEVANCE_HINTS):
        s += 2
    # 정책브리핑/농식품부/aT는 실무 가치 높게
    if dom in {"korea.kr", "mafra.go.kr", "at.or.kr"}:
        s += 2
    return s

def collect_articles_by_section(start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    """
    - 섹션 순서 고정
    - 섹션당 목표수량을 채우도록 수집
    - 중복 URL은 “먼저 등장한 섹션”에만 배치(중복 이슈 배제)
    """
    by_section: Dict[str, List[dict]] = {sec: [] for sec, _ in SECTION_ORDER}
    global_seen_urls: set[str] = set()

    total_window = 0

    for sec, queries in SECTION_ORDER:
        bucket: List[dict] = []
        for q in queries:
            try:
                items = naver_api_search_window(q, start_kst, end_kst, max_pages=3)
            except Exception as e:
                logging.warning("[NAVER API] query fail '%s': %s", q, e)
                continue

            for it in items:
                total_window += 1
                url = (it.get("url") or "").strip()
                if not url or url in global_seen_urls:
                    continue
                bucket.append(it)

            # 빠르게 목표치 근접하면 다음 쿼리로 넘어가며 누적
            if len(bucket) >= MAX_ARTICLES_PER_SECTION * 2:
                break

        bucket = dedupe(bucket)
        # 품질/최신 우선 정렬
        bucket.sort(key=lambda x: (quality_score(x), x.get("published_kst", "")), reverse=True)

        # 1차: 메이저 우선
        majors = [b for b in bucket if is_major_domain(b.get("domain", ""))]
        picked: List[dict] = []

        # 메이저가 충분하면 메이저로 채우기
        if len(majors) >= MIN_ARTICLES_PER_SECTION:
            picked = majors[:MAX_ARTICLES_PER_SECTION]
        else:
            # 메이저가 적으면: 메이저를 먼저 깔고, 부족분은 (차단 도메인 제외된) 나머지에서 핵심 키워드 포함 위주로 보충
            picked = majors[:MAX_ARTICLES_PER_SECTION]
            if len(picked) < MIN_ARTICLES_PER_SECTION:
                rest = [b for b in bucket if b not in picked]
                rest.sort(key=lambda x: (quality_score(x), x.get("published_kst", "")), reverse=True)
                need = min(MAX_ARTICLES_PER_SECTION - len(picked), MIN_ARTICLES_PER_SECTION - len(picked))
                picked.extend(rest[:max(0, need)])

            # 그래도 부족하면 그냥 최신+점수 순으로 MAX까지 채움(단, blocked는 이미 제거됨)
            if len(picked) < MIN_ARTICLES_PER_SECTION:
                rest2 = [b for b in bucket if b not in picked]
                rest2.sort(key=lambda x: (quality_score(x), x.get("published_kst", "")), reverse=True)
                picked.extend(rest2[: max(0, MAX_ARTICLES_PER_SECTION - len(picked))])

        picked = picked[:MAX_ARTICLES_PER_SECTION]
        by_section[sec] = picked

        for it in picked:
            u = (it.get("url") or "").strip()
            if u:
                global_seen_urls.add(u)

        logging.info("[Collect] %s: %d", sec, len(by_section[sec]))

    logging.info("[Collect Summary] total_candidates_in_window=%d", total_window)
    return by_section


# =========================
# OpenAI 요약(2~3문장 + 체크포인트 1줄)
# =========================
def openai_summarize(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    # 기사 0건이면 스킵
    total = sum(len(v) for v in articles_by_section.values())
    if total == 0 or not api_key:
        for sec, arts in articles_by_section.items():
            for a in arts:
                # 최소한 description을 1줄이라도 보여주기
                desc = (a.get("description") or "").strip()
                a["summary"] = desc if desc else a.get("title", "")
                a["point"] = ""
        return articles_by_section

    compact = []
    for sec, _ in SECTION_ORDER:
        for a in articles_by_section.get(sec, []):
            compact.append({
                "section": sec,
                "press": a.get("press", ""),
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "published_kst": a.get("published_kst", ""),
                "url": a.get("url", ""),
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
                    "required": ["url", "summary", "point"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }

    system = (
        "너는 농협중앙회 원예수급부 결재/공유용 '농산물 뉴스 브리핑' 작성자다.\n"
        "각 기사마다:\n"
        "- summary: 2~3문장(핵심 사실/동향 위주, 실무에 바로 연결되게)\n"
        "- point: 체크포인트 1문장(수급/가격/유통/방제/정책 대응 관점)\n"
        "주의: 과장/추측 금지. 제목/설명만으로 애매하면 '제목상'으로 보수적으로.\n"
        "형식: 문장형, 간결, 중복표현 최소화.\n"
    )
    user = (
        f"기간(KST): {start_kst.isoformat()} ~ {end_kst.isoformat()}\n"
        f"기사 목록 JSON:\n{json.dumps(compact, ensure_ascii=False)}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "reasoning_effort": OPENAI_REASONING_EFFORT,
        "max_output_tokens": OPENAI_MAX_OUTPUT_TOKENS,
        "text": {"format": {"type": "json_schema", "name": "agri_summaries", "strict": True, "schema": schema}},
        "store": False,
    }

    r = requests.post(
        OPENAI_RESPONSES_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=75,
    )
    if not r.ok:
        logging.error("[OpenAI ERROR BODY] %s", r.text)
        # fallback
        for sec, arts in articles_by_section.items():
            for a in arts:
                desc = (a.get("description") or "").strip()
                a["summary"] = desc if desc else a.get("title", "")
                a["point"] = ""
        return articles_by_section

    data = r.json()
    out_text = ""
    for item in data.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    out_text += c.get("text", "")
    out_text = out_text.strip()
    if not out_text:
        return articles_by_section

    j = json.loads(out_text)
    mapping = {it["url"]: it for it in j.get("items", [])}

    # merge + 중복/빈 요약 보정
    for sec, _ in SECTION_ORDER:
        for a in articles_by_section.get(sec, []):
            u = a.get("url", "")
            m = mapping.get(u, {})
            summary = (m.get("summary") or "").strip()
            point = (m.get("point") or "").strip()

            if not summary:
                desc = (a.get("description") or "").strip()
                summary = desc if desc else a.get("title", "")

            # summary가 제목과 동일하면(너무 빈약) description으로 보강
            if summary.strip() == (a.get("title", "").strip()) and (a.get("description") or "").strip():
                summary = (a.get("description") or "").strip()

            a["summary"] = summary
            a["point"] = point

    return articles_by_section


# =========================
# 상세 텍스트 / HTML (섹션 순서 고정 + 특이사항 없음 유지)
# =========================
def render_full_brief_text(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> str:
    span_days = (end_kst.date() - start_kst.date()).days
    span_note = ""
    if span_days >= 2:
        span_note = f" (휴일/주말 누적 포함: {span_days}일)"

    lines = []
    lines.append(f"[농산물 뉴스 Brief] ({start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} KST){span_note}")
    lines.append("")

    total = sum(len(v) for v in articles_by_section.values())
    lines.append(f"총 {total}건 (섹션별: " + ", ".join([f"{sec} {len(articles_by_section.get(sec, []))}건" for sec, _ in SECTION_ORDER]) + ")")
    lines.append("")

    for sec, _ in SECTION_ORDER:
        arts = articles_by_section.get(sec, [])
        lines.append(f"■ {sec}")
        if not arts:
            lines.append("- 특이사항 없음")
            lines.append("")
            continue

        for a in arts:
            press = a.get("press", "미상")
            title = a.get("title", "")
            summary = (a.get("summary") or "").strip()
            point = (a.get("point") or "").strip()
            url = a.get("url", "")

            lines.append(f"- {press} | {title}")
            if summary:
                lines.append(f"  {summary}")
            if point:
                lines.append(f"  체크포인트: {point}")
            lines.append(f"  {url}")
            lines.append("")

        lines.append("")

    return "\n".join(lines).strip() + "\n"

def linkify_escaped(s: str) -> str:
    return re.sub(
        r"(https?://[^\s<]+)",
        lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        s,
    )

def make_brief_html(full_text: str, title: str) -> str:
    esc = html.escape(full_text)
    esc = linkify_escaped(esc)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;margin:18px;line-height:1.45;background:#f7f7f8;}}
.wrap{{max-width:900px;margin:0 auto;}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px;box-shadow:0 2px 10px rgba(0,0,0,.05);}}
pre{{white-space:pre-wrap;word-break:break-word;margin:0;font-size:15px;}}
a{{word-break:break-all;}}
.small{{color:#6b7280;font-size:13px;margin-bottom:10px;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="small">{html.escape(title)}</div>
    <pre>{esc}</pre>
  </div>
</div>
</body>
</html>
"""

def publish_to_github_pages(html_text: str, commit_title: str) -> None:
    if PUBLISH_MODE != "github_pages":
        return
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[Pages publish] missing repo/token -> skip")
        return
    _raw, sha = github_get_file(repo, PAGES_FILE_PATH, token, ref=PAGES_BRANCH)
    ok = github_put_file(
        repo=repo,
        path=PAGES_FILE_PATH,
        token=token,
        content_text=html_text,
        branch=PAGES_BRANCH,
        sha=sha,
        message=f"Publish brief viewer: {commit_title}",
    )
    if ok:
        logging.info("[Pages publish] updated %s", PAGES_FILE_PATH)


# =========================
# 카톡 1메시지(“매력적” 유도문)
# =========================
def auto_pages_url() -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}/"

def clamp(s: str, n: int) -> str:
    return s if len(s) <= n else (s[: max(0, n - 1)] + "…")

def build_kakao_message(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime, view_url: str) -> str:
    # 섹션 순서대로 요약
    total = sum(len(v) for v in articles_by_section.values())
    span_days = (end_kst.date() - start_kst.date()).days
    span_hint = ""
    if span_days >= 2:
        span_hint = f" / 휴일누적 {span_days}일"

    # 섹션별 건수
    sec_counts = " · ".join([f"{sec.split()[0]} {len(articles_by_section.get(sec, []))}" for sec, _ in SECTION_ORDER])

    head = f"[농산물 브리핑] {end_kst.strftime('%m/%d')} {RUN_HOUR_KST:02d}시 | {total}건{span_hint}"
    sub = f"섹션: {sec_counts}"

    # 오늘 핵심 3줄: 섹션 우선순위대로 기사 1개씩 뽑아 구성
    highlights: List[str] = []
    for sec, _ in SECTION_ORDER:
        if not articles_by_section.get(sec):
            continue
        a = articles_by_section[sec][0]
        press = a.get("press", "")
        title = a.get("title", "")
        # 너무 길면 잘라서 “궁금증”만 남기기
        line = f"- {press}: {clamp(title, 28)}"
        highlights.append(line)
        if len(highlights) >= 3:
            break

    if not highlights:
        highlights = ["- 수집된 핵심 기사가 적습니다(기간/필터 점검 필요)."]

    cta = "▶ 브리핑 열기(상세/요약/링크)"
    msg = "\n".join([head, sub, "오늘 포인트:", *highlights, cta, f"상세: {view_url}"])

    return clamp(msg, KAKAO_MESSAGE_SOFT_LIMIT)


# =========================
# Main
# =========================
def main():
    now_kst = datetime.now(tz=KST)
    end_kst = compute_fixed_end_kst(now_kst, RUN_HOUR_KST)

    if FORCE_SEND:
        logging.info("[FORCE_SEND] enabled: will send even on weekend/holiday")

    if (not FORCE_SEND) and (not is_business_day(end_kst.date())):
        logging.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date())
        # 휴일/주말엔 state 저장하지 않음 -> 다음 영업일에 누락 구간 포함
        return

    # start_kst: 마지막 발송 시각(state) 기준
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

    # Pages URL
    view_url = BRIEF_VIEW_URL or auto_pages_url() or ("https://search.naver.com/search.naver?where=news&query=" + quote_plus("농산물 뉴스 브리핑"))

    # 1) collect
    articles_by_section = collect_articles_by_section(start_kst, end_kst)

    # 2) summarize
    articles_by_section = openai_summarize(articles_by_section, start_kst, end_kst)

    # 3) render + publish
    full_text = render_full_brief_text(articles_by_section, start_kst, end_kst)
    title = f"농산물 뉴스 Brief ({start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} KST)"
    html_page = make_brief_html(full_text, title)
    publish_to_github_pages(html_page, commit_title=end_kst.strftime("%Y-%m-%d"))

    # 4) kakao send (1 message)
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not refresh_token:
        raise RuntimeError("Missing KAKAO_REFRESH_TOKEN")

    access = kakao_refresh_access_token(refresh_token)
    msg = build_kakao_message(articles_by_section, start_kst, end_kst, view_url)
    kakao_send_text(access, msg, view_url)

    # 5) save state only after send
    save_state(end_kst)
    logging.info("[DONE] sent and state updated: %s", end_kst.isoformat())

if __name__ == "__main__":
    main()
