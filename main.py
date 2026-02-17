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

# -----------------------------
# Modes / Settings
# -----------------------------
RUN_HOUR_KST = int(os.getenv("RUN_HOUR_KST", "7"))               # 항상 07:00 기준으로 윈도우 고정
FORCE_SEND = (os.getenv("FORCE_SEND", "0") == "1")              # 테스트용(휴일/주말에도 발송)
KAKAO_SEND_MODE = os.getenv("KAKAO_SEND_MODE", "single_text")   # single_text 권장
PUBLISH_MODE = os.getenv("PUBLISH_MODE", "github_pages")        # github_pages 권장
PAGES_BRANCH = os.getenv("PAGES_BRANCH", "main")
PAGES_FILE_PATH = os.getenv("PAGES_FILE_PATH", "docs/index.html")

STATE_BACKEND = os.getenv("STATE_BACKEND", "repo")              # repo 권장(gist 불필요)
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", ".agri_state.json")

# Pages 링크(없으면 자동 추정)
BRIEF_VIEW_URL = os.getenv("BRIEF_VIEW_URL", "").strip()

# 기사 수(페이지에 너무 길어지는 것 방지)
MAX_ARTICLES_PER_SECTION = int(os.getenv("MAX_ARTICLES_PER_SECTION", "4"))

# -----------------------------
# Kakao
# -----------------------------
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MEMO_SEND_API = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

# -----------------------------
# Naver OpenAPI
# -----------------------------
NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"

# -----------------------------
# OpenAI
# -----------------------------
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "minimal")
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "1200"))

# -----------------------------
# Source filtering (메이저 위주)
# -----------------------------
ALLOWED_DOMAINS = {
    # 통신/방송
    "yna.co.kr", "newsis.com", "kbs.co.kr", "imnews.imbc.com", "sbs.co.kr", "ytn.co.kr", "jtbc.co.kr",
    # 중앙/경제지
    "chosun.com", "joongang.co.kr", "donga.com", "hani.co.kr", "khan.co.kr", "kmib.co.kr", "hankookilbo.com",
    "mk.co.kr", "hankyung.com", "sedaily.com", "edaily.co.kr", "asiae.co.kr", "heraldcorp.com",
    # 농업/전문/공공
    "nongmin.com", "aflnews.co.kr", "ikpnews.net",
    "mafra.go.kr", "korea.kr", "policy.go.kr", "at.or.kr", "krei.re.kr", "naqs.go.kr",
}

BLOCKED_DOMAINS = {
    "wikitree.co.kr",
    "donghaengmedia.net",
    "sidae.com",
}

LOW_RELEVANCE_HINTS = [
    "온누리상품권", "환급", "축제", "행사", "홍보", "체험", "박람회", "맛집", "레시피", "관광", "지역화폐", "상품권",
]
HIGH_RELEVANCE_HINTS = [
    "가격", "시세", "도매", "경락", "물량", "수급", "출하", "저장", "재고", "작황", "생산량",
    "수입", "할당관세", "검역", "물가", "할인", "도매시장", "가락시장", "공판장",
    "APC", "선별", "CA저장", "수출", "방제", "병해충", "화상병", "탄저", "동해", "냉해",
]
OUT_OF_SEASON_HINTS = ["10월", "11월", "추석", "가을 수확", "수확기", "햇사과", "햇배"]

SECTIONS: List[Tuple[str, List[str]]] = [
    ("품목 및 수급 동향", [
        "기후변화 사과 재배지 북상 강원도",
        "사과 저장량 도매가격", "배 저장량 도매가격",
        "단감 저장량 시세", "떫은감 탄저병 곶감 생산량 가격 둥시",
        "감귤 한라봉 레드향 천혜향 가격", "참다래 키위 가격",
        "샤인머스캣 포도 가격", "매실 개화 전망 냉해",
        "풋고추 오이 애호박 시설채소 가격", "쌀 산지쌀값 비축미 방출",
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
        "탄저병 예방", "동해 냉해 대비 과수",
    ]),
    ("유통 및 현장(APC/수출)", [
        "농협 APC 스마트화 AI 선별기 CA 저장",
        "공판장 도매시장 산지유통 동향",
        "농식품 수출 실적 배 딸기 라면",
    ]),
]

# -----------------------------
# Holiday logic + override
# -----------------------------
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
    if is_weekend(d):
        return False
    if is_korean_holiday(d):
        return False
    return True

# -----------------------------
# Time window (항상 07:00 기준)
# -----------------------------
def compute_fixed_end_kst(now_kst: datetime, run_hour: int) -> datetime:
    end = now_kst.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    if now_kst < end:
        end = end - timedelta(days=1)
    return end

# -----------------------------
# GitHub repo file read/write (state + pages)
# -----------------------------
def github_get_file(repo: str, path: str, token: str, ref: str = "main") -> Tuple[Optional[str], Optional[str]]:
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if r.status_code == 404:
        return None, None
    if not r.ok:
        logging.error("[GitHub GET ERROR] %s", r.text)
        return None, None  # ✅ 401이어도 전체 중단하지 않게
    j = r.json()
    sha = j.get("sha")
    b64 = j.get("content", "")
    if j.get("encoding") == "base64" and b64:
        raw = base64.b64decode(b64).decode("utf-8", errors="replace")
        return raw, sha
    return None, sha

def github_put_file(repo: str, path: str, token: str, content_text: str, branch: str = "main", sha: Optional[str] = None, message: str = "Update file") -> bool:
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
    if STATE_BACKEND != "repo":
        return State(last_end_kst_iso=(default_last_end - timedelta(hours=24)).isoformat())

    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[STATE] missing GITHUB_REPOSITORY/GITHUB_TOKEN -> fallback")
        return State(last_end_kst_iso=(default_last_end - timedelta(hours=24)).isoformat())

    raw, _sha = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
    if not raw:
        return State(last_end_kst_iso=(default_last_end - timedelta(hours=24)).isoformat())

    try:
        j = json.loads(raw)
        v = j.get("last_end_kst_iso")
        if v:
            return State(last_end_kst_iso=v)
    except Exception:
        pass
    return State(last_end_kst_iso=(default_last_end - timedelta(hours=24)).isoformat())

def save_state(end_kst: datetime) -> None:
    if STATE_BACKEND != "repo":
        return
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    if not repo or not token:
        logging.warning("[STATE] missing GITHUB_REPOSITORY/GITHUB_TOKEN -> cannot save")
        return
    raw, sha = github_get_file(repo, STATE_FILE_PATH, token, ref=PAGES_BRANCH)
    _ = raw
    content = json.dumps({"last_end_kst_iso": end_kst.isoformat()}, ensure_ascii=False, indent=2)
    github_put_file(repo, STATE_FILE_PATH, token, content, branch=PAGES_BRANCH, sha=sha, message="Update agri-news state")

# -----------------------------
# Kakao send (single message)
# -----------------------------
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
        "button_title": "상세보기",
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

# -----------------------------
# Naver OpenAPI collection
# -----------------------------
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

def looks_low_relevance(text: str) -> bool:
    t = text or ""
    low = any(k in t for k in LOW_RELEVANCE_HINTS)
    high = any(k in t for k in HIGH_RELEVANCE_HINTS)
    return low and (not high)

def looks_out_of_season(text: str) -> bool:
    t = text or ""
    out = any(k in t for k in OUT_OF_SEASON_HINTS)
    current_ok = any(k in t for k in ["저장", "전정", "설", "저장량", "재고", "현재", "최근"])
    return out and (not current_ok)

def naver_api_search(query: str, display: int = 100, start: int = 1) -> List[dict]:
    cid = os.getenv("NAVER_CLIENT_ID", "").strip()
    csec = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        raise RuntimeError("Missing NAVER_CLIENT_ID / NAVER_CLIENT_SECRET")

    headers = {
        "X-Naver-Client-Id": cid,
        "X-Naver-Client-Secret": csec,
    }
    params = {"query": query, "display": display, "start": start, "sort": "date"}
    r = requests.get(NAVER_NEWS_API, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("items", [])

def is_major_domain(dom: str) -> bool:
    if not dom:
        return False
    if dom in BLOCKED_DOMAINS:
        return False
    # 허용 도메인 목록에 포함/하위도메인 포함 허용
    for d in ALLOWED_DOMAINS:
        if dom == d or dom.endswith("." + d):
            return True
    return False

def dedupe_by_url_title(items: List[dict]) -> List[dict]:
    seen = set()
    out = []
    for it in items:
        u = (it.get("url") or "")[:300]
        t = (it.get("title") or "")[:120]
        key = u + "|" + t
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def collect_articles_by_section(start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    by_section: Dict[str, List[dict]] = {sec: [] for sec, _ in SECTIONS}

    all_count = 0
    major_count = 0

    for sec, queries in SECTIONS:
        bucket: List[dict] = []
        for q in queries:
            try:
                items = naver_api_search(q, display=100, start=1)
            except Exception as e:
                logging.warning("[NAVER API] query fail '%s': %s", q, e)
                continue

            for it in items:
                title = clean_html(it.get("title", ""))
                desc = clean_html(it.get("description", ""))
                pub = it.get("pubDate", "")

                try:
                    dt = parsedate_to_datetime(pub)
                    if dt.tzinfo is None:
                        continue
                    dt_kst = dt.astimezone(KST)
                except Exception:
                    continue

                if not (start_kst <= dt_kst < end_kst):
                    continue

                origin = (it.get("originallink") or "").strip()
                naver_link = (it.get("link") or "").strip()
                url = origin or naver_link
                dom = domain_of(url)

                all_count += 1

                text = f"{title} {desc}"
                if looks_low_relevance(text) or looks_out_of_season(text):
                    continue

                if dom in BLOCKED_DOMAINS:
                    continue

                major = is_major_domain(dom)
                if major:
                    major_count += 1

                bucket.append({
                    "section": sec,
                    "title": title,
                    "description": desc,
                    "published_kst": dt_kst.isoformat(),
                    "domain": dom,
                    "url": url,
                    "naver_link": naver_link,
                })

            time.sleep(0.05)

        bucket = dedupe_by_url_title(bucket)

        # 메이저 도메인 우선 적용. 너무 적으면(=전체 0에 가깝거나) 완화.
        majors = [b for b in bucket if is_major_domain(b.get("domain", ""))]
        if len(majors) >= 2:
            bucket = majors

        # 최신순 정렬 + 상한
        bucket.sort(key=lambda x: x.get("published_kst", ""), reverse=True)
        by_section[sec] = bucket[:MAX_ARTICLES_PER_SECTION]
        logging.info("[Collect] %s: %d", sec, len(by_section[sec]))

    logging.info("[Collect Summary] total_window_items=%d, major_window_items=%d", all_count, major_count)
    return by_section

# -----------------------------
# OpenAI summarization (2~3문장 + point)
# -----------------------------
def openai_summarize(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> Dict[str, List[dict]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logging.warning("[OpenAI] missing key -> title fallback")
        for sec, arts in articles_by_section.items():
            for a in arts:
                a["summary"] = a["title"]
                a["point"] = ""
        return articles_by_section

    compact = []
    for sec, arts in articles_by_section.items():
        for a in arts:
            compact.append({
                "section": sec,
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "domain": a.get("domain", ""),
                "published_kst": a.get("published_kst", ""),
                "url": a.get("url", ""),
            })

    # 기사 0건이면 굳이 OpenAI 호출 X
    if not compact:
        return articles_by_section

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

    sys = (
        "너는 농협중앙회 원예수급부 결재/공유용 뉴스 브리핑 편집자다.\n"
        "각 기사마다:\n"
        "- summary: 2~3문장(핵심 사실/동향 위주)\n"
        "- point: 실무자 체크포인트 1문장(수급/가격/유통/방제/정책 대응)\n"
        "과장/추측 금지. 제목만으로 애매하면 '제목상'이라고 보수적으로.\n"
    )
    user = (
        f"기간(KST): {start_kst.isoformat()} ~ {end_kst.isoformat()}\n"
        f"기사 목록 JSON:\n{json.dumps(compact, ensure_ascii=False)}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {"role": "system", "content": sys},
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
        timeout=60,
    )
    if not r.ok:
        logging.error("[OpenAI ERROR BODY] %s", r.text)
        # fallback
        for sec, arts in articles_by_section.items():
            for a in arts:
                a["summary"] = a["title"]
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

    for sec, arts in articles_by_section.items():
        for a in arts:
            m = mapping.get(a.get("url", ""), {})
            a["summary"] = (m.get("summary") or a["title"]).strip()
            a["point"] = (m.get("point") or "").strip()

    return articles_by_section

# -----------------------------
# Render text + HTML (빈페이지 방지)
# -----------------------------
def render_full_brief_text(articles_by_section: Dict[str, List[dict]], start_kst: datetime, end_kst: datetime) -> str:
    lines = []
    lines.append(f"[농산물 뉴스 Brief] ({start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} KST)")
    lines.append("")

    total = sum(len(v) for v in articles_by_section.values())
    if total == 0:
        lines.append("수집된 기사가 없습니다.")
        lines.append("- 원인 후보: (1) 기간/휴일 스킵, (2) 필터가 너무 엄격, (3) 네이버 API 키 미설정")
        lines.append("- 빠른 점검: NAVER_CLIENT_ID/NAVER_CLIENT_SECRET, 시간창(07:00 고정), 허용 도메인 목록")
        lines.append("")
        lines.append("참고(직접 검색):")
        for sec, queries in SECTIONS:
            q = queries[0] if queries else "농산물"
            lines.append(f"- {sec}: https://search.naver.com/search.naver?where=news&query={quote_plus(q)}")
        lines.append("")
        return "\n".join(lines)

    # 기사 있는 섹션 먼저
    ordered = sorted(articles_by_section.items(), key=lambda kv: (0 if kv[1] else 1, kv[0]))

    for sec, arts in ordered:
        if not arts:
            continue
        lines.append(f"■ {sec}")
        for a in arts:
            title = a.get("title", "")
            dom = a.get("domain", "")
            summary = (a.get("summary") or "").strip()
            point = (a.get("point") or "").strip()
            url = a.get("url", "")

            lines.append(f"- ({dom}) {title}")
            if summary:
                lines.append(f"  {summary}")
            if point:
                lines.append(f"  포인트: {point}")
            lines.append(f"  {url}")
            lines.append("")
        lines.append("")
    return "\n".join(lines).strip() + "\n"

def linkify_escaped(s: str) -> str:
    # escaped text 안의 URL을 링크로 변환
    return re.sub(
        r"(https?://[^\s<]+)",
        lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        s,
    )

def make_brief_html(full_text: str, title: str) -> str:
    esc = html.escape(full_text)
    esc = linkify_escaped(esc)
    # pre-wrap로 줄바꿈 보존
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

# -----------------------------
# Kakao single message
# -----------------------------
def clamp(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"

def auto_pages_url() -> str:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}/"

def build_single_message(articles_by_section: Dict[str, List[dict]], end_kst: datetime, view_url: str) -> str:
    total = sum(len(v) for v in articles_by_section.values())
    head = f"[농산물 브리핑] {end_kst.strftime('%m/%d')} {RUN_HOUR_KST:02d}시 (기사 {total}건)"
    if total == 0:
        return clamp(head + f"\n상세: {view_url}", 180)

    # 상위 3개만 하이라이트
    tops: List[str] = []
    for sec, arts in articles_by_section.items():
        for a in arts:
            t = a.get("title", "").strip()
            if t:
                tops.append(clamp(t, 34))
        if len(tops) >= 3:
            break
    body = "\n".join([f"- {t}" for t in tops[:3]])
    msg = f"{head}\n{body}\n상세: {view_url}"
    return clamp(msg, 180)

# -----------------------------
# Main
# -----------------------------
def main():
    now_kst = datetime.now(tz=KST)
    end_kst = compute_fixed_end_kst(now_kst, RUN_HOUR_KST)

    if FORCE_SEND:
        logging.info("[FORCE_SEND] enabled: will send even on weekend/holiday")

    if (not FORCE_SEND) and (not is_business_day(end_kst.date())):
        logging.info("[SKIP] Not a business day in KR: %s (weekend/holiday)", end_kst.date())
        # 스킵 시 state 저장하지 않음 -> 다음 영업일에 기간 자동 확장
        return

    # state 기반 start 결정(휴일/주말 누락분 포함)
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

    # collect
    articles_by_section = collect_articles_by_section(start_kst, end_kst)

    # summarize
    articles_by_section = openai_summarize(articles_by_section, start_kst, end_kst)

    # render
    full_text = render_full_brief_text(articles_by_section, start_kst, end_kst)
    title = f"농산물 뉴스 Brief ({start_kst.strftime('%Y-%m-%d %H:%M')}~{end_kst.strftime('%Y-%m-%d %H:%M')} KST)"
    html_page = make_brief_html(full_text, title)
    publish_to_github_pages(html_page, commit_title=end_kst.strftime("%Y-%m-%d"))

    # kakao send (single)
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not refresh_token:
        raise RuntimeError("Missing KAKAO_REFRESH_TOKEN")

    access = kakao_refresh_access_token(refresh_token)
    msg = build_single_message(articles_by_section, end_kst, view_url)
    kakao_send_text(access, msg, view_url)

    # save state only after send
    save_state(end_kst)
    logging.info("[DONE] sent and state updated: %s", end_kst.isoformat())

if __name__ == "__main__":
    main()
