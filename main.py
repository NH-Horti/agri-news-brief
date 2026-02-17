import os
import json
import re
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime

import requests
import holidays

# =========================
# 운영 설정 (보통 기준)
# =========================
KST = ZoneInfo("Asia/Seoul")
KR_HOLIDAYS = holidays.KR()

ANCHOR_HOUR = 7  # 매일 07:00 KST를 기준으로 윈도우 종료 시각 고정
MAX_PER_QUERY = 100  # 네이버 뉴스 검색 API display 최대 100

# "보통" 기준: OpenAI에 넘기는 기사 수/출력 상한
MAX_ITEMS_PER_SECTION_FOR_OPENAI = 6
OPENAI_MAX_OUTPUT_TOKENS = 2000
OPENAI_REASONING_EFFORT = "medium"  # none/low/medium/high

KAKAO_BUTTON_TITLE = "브리핑 열기"

SECTION_QUERIES = {
    "1) 품목 및 수급 동향": [
        "사과 저장량 가격", "배 도매가격", "단감 시세", "곶감 떫은감 탄저병",
        "한라봉 레드향 시세", "감귤 가격", "참다래 키위 가격",
        "샤인머스캣 가격", "풋고추 오이 시설채소 가격 일조량",
        "절화 졸업 입학 시즌 가격", "쌀 산지 가격 비축미 방출",
        "APC 물량 가격 10kg 사과", "가락시장 사과 경락가"
    ],
    "2) 주요 이슈 및 정책": [
        "농산물 온라인 도매시장 허위거래 이상거래",
        "농산물 할인 지원 연장",
        "할당관세 수입 과일 검역 완화",
        "가락시장 휴무 경매 재개"
    ],
    "3) 병해충 및 방제": [
        "과수화상병 약제 신청",
        "과수화상병 궤양 제거",
        "기계유유제 월동 해충 방제",
        "탄저병 예방",
        "과수 동해 냉해 대비"
    ],
    "4) 유통 및 현장(APC/수출 등)": [
        "농협 APC 스마트 AI 선별기 CA 저장",
        "공판장 도매시장 물량 동향",
        "농식품 수출 실적 배 딸기",
        "가락시장 경매 물량 동향"
    ]
}

IRRELEVANT_PATTERNS = [
    r"온누리상품권", r"환급", r"지역축제", r"바자회", r"기부", r"나눔행사",
    r"복지", r"장학금", r"봉사", r"기념식", r"캠페인"
]


# =========================
# 공통 유틸
# =========================
def kst_now() -> datetime:
    return datetime.now(tz=KST)


def anchor_end_time(now: datetime) -> datetime:
    return datetime.combine(now.date(), time(ANCHOR_HOUR, 0), tzinfo=KST)


def is_business_day(d: datetime) -> bool:
    if d.weekday() >= 5:
        return False
    return d.date() not in KR_HOLIDAYS


def strip_html(s: str) -> str:
    s = re.sub(r"<.*?>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_title(t: str) -> str:
    t = strip_html(t)
    t = re.sub(r"[^\w\s가-힣]", "", t)
    return t.lower()


def looks_irrelevant(title: str) -> bool:
    for p in IRRELEVANT_PATTERNS:
        if re.search(p, title):
            return True
    return False


def shorten(s: str, n: int = 80) -> str:
    s = strip_html(s)
    return s if len(s) <= n else (s[: n - 1] + "…")


# =========================
# GitHub Gist (state + latest.md)
# =========================
def gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "agri-news-brief-bot"
    }


def gist_get(gist_id: str, token: str) -> dict:
    r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=gh_headers(token), timeout=30)
    if not r.ok:
        print("[Gist GET ERROR BODY]", r.text)
    r.raise_for_status()
    return r.json()


def gist_update_files(gist_id: str, token: str, files_payload: dict) -> dict:
    r = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers=gh_headers(token),
        json={"files": files_payload},
        timeout=30
    )
    if not r.ok:
        print("[Gist PATCH ERROR BODY]", r.text)
    r.raise_for_status()
    return r.json()


def load_state_from_gist(gist_json: dict) -> dict:
    files = gist_json.get("files", {})
    if "state.json" in files and "content" in files["state.json"]:
        try:
            return json.loads(files["state.json"]["content"] or "{}")
        except Exception:
            pass
    return {"last_end_kst": None}


# =========================
# Naver News Search API 수집
# =========================
def naver_news_search(query: str, client_id: str, client_secret: str, display: int = 100) -> list[dict]:
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": query, "display": min(display, 100), "start": 1, "sort": "date"}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("items", [])


def parse_pubdate_to_kst(pub: str) -> datetime | None:
    try:
        dt = parsedate_to_datetime(pub)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(KST)
    except Exception:
        return None


def collect_articles(start_kst: datetime, end_kst: datetime) -> dict[str, list[dict]]:
    nav_id = os.environ["NAVER_CLIENT_ID"]
    nav_secret = os.environ["NAVER_CLIENT_SECRET"]

    out: dict[str, list[dict]] = {k: [] for k in SECTION_QUERIES.keys()}
    seen_links = set()
    seen_titles = set()

    for section, queries in SECTION_QUERIES.items():
        for q in queries:
            items = naver_news_search(q, nav_id, nav_secret, display=MAX_PER_QUERY)
            for it in items:
                pub_kst = parse_pubdate_to_kst(it.get("pubDate", ""))
                if not pub_kst:
                    continue
                if not (start_kst <= pub_kst < end_kst):
                    continue

                title = strip_html(it.get("title", ""))
                if not title:
                    continue
                if looks_irrelevant(title):
                    continue

                link = it.get("originallink") or it.get("link") or ""
                if not link:
                    continue

                nt = norm_title(title)
                if link in seen_links or nt in seen_titles:
                    continue

                seen_links.add(link)
                seen_titles.add(nt)

                out[section].append({
                    "title": title,
                    "link": link,
                    "pub_kst_dt": pub_kst,
                    "pub_kst": pub_kst.strftime("%Y-%m-%d %H:%M"),
                    "query": q
                })

    for section in out:
        out[section].sort(key=lambda x: x["pub_kst_dt"], reverse=True)

    return out


# =========================
# OpenAI Responses API 요약 (gpt-5.2, 보통 기준)
# =========================
def extract_response_text(data: dict) -> str:
    ot = data.get("output_text")
    if isinstance(ot, str) and ot.strip():
        return ot.strip()

    text_parts = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                t = c.get("text", "")
                if t:
                    text_parts.append(t)
    return "".join(text_parts).strip()


def simple_compose_md(articles_by_section: dict[str, list[dict]], start_kst: datetime, end_kst: datetime, note: str = "") -> str:
    out = []
    out.append(f"[농산물 뉴스 Brief] {start_kst:%Y-%m-%d %H:%M}~{end_kst:%Y-%m-%d %H:%M} KST {note}".strip())
    for sec, items in articles_by_section.items():
        out.append(f"\n{sec}")
        if not items:
            out.append("특이사항 없음")
            continue
        for it in items:
            out.append(f"- {it['title']} ({it['pub_kst']})")
            out.append(it["link"])
    return "\n".join(out)


def openai_summarize(articles_by_section: dict[str, list[dict]], start_kst: datetime, end_kst: datetime) -> str:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return simple_compose_md(articles_by_section, start_kst, end_kst, note="(OPENAI_API_KEY 없음: 제목 기반 나열)")

    model = (os.getenv("OPENAI_MODEL") or "gpt-5.2").strip()

    lines = []
    lines.append(f"기간(KST): {start_kst:%Y-%m-%d %H:%M} ~ {end_kst:%Y-%m-%d %H:%M}")
    lines.append("아래는 섹션별 기사 목록(최신순). 중복 이슈는 통합해 요약하되 링크는 남길 것.\n")

    for sec, items in articles_by_section.items():
        lines.append(f"[{sec}]")
        if not items:
            lines.append("- (해당 없음)\n")
            continue

        for it in items[:MAX_ITEMS_PER_SECTION_FOR_OPENAI]:
            lines.append(f"- {it['pub_kst']} | {it['title']}")
            lines.append(f"  {it['link']}")
        lines.append("")

    instructions = (
        "너는 농협중앙회 원예수급부(과수화훼) 팀장 결재용 '농산물 뉴스 브리핑' 작성자다.\n"
        "출력 규칙(엄수):\n"
        "1) 한국어, plain text(볼드/마크다운 강조/이모지 과다 금지).\n"
        "2) 섹션 순서 유지(1→4).\n"
        "3) 각 섹션에서 이슈 단위로 2~5개 항목만 선정.\n"
        "4) 각 항목: 요약 1줄(20~45자) + 다음 줄에 링크(URL만) 1개 이상.\n"
        "5) 섹션에 기사 없으면: '특이사항 없음' 한 줄.\n"
        "6) 정책/제도/가격/저장/병해충/유통(APC/가락시장) 관점 우선.\n"
    )

    payload = {
        "model": model,
        "instructions": instructions,
        "input": "\n".join(lines),
        "max_output_tokens": OPENAI_MAX_OUTPUT_TOKENS,
        "truncation": "auto",
        "reasoning": {"effort": OPENAI_REASONING_EFFORT},
    }

    # gpt-5.2는 reasoning.effort가 none일 때만 temperature/top_p 등이 지원됨
    # (effort가 medium/high면 넣으면 400 발생)  ← 지금 이 케이스
    if OPENAI_REASONING_EFFORT == "none":
        payload["temperature"] = 0.2

    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=90
        )
        if not r.ok:
            print("[OpenAI ERROR BODY]", r.text)
        r.raise_for_status()
        data = r.json()

        usage = data.get("usage", {})
        if usage:
            print("[OpenAI USAGE]", json.dumps(usage, ensure_ascii=False))

        text = extract_response_text(data)
        return text if text else simple_compose_md(articles_by_section, start_kst, end_kst, note="(OpenAI 응답 텍스트 없음: 제목 기반 나열)")

    except requests.exceptions.RequestException as e:
        print("[OpenAI REQUEST FAILED]", str(e))
        return simple_compose_md(articles_by_section, start_kst, end_kst, note="(OpenAI 실패: 제목 기반 나열)")


# =========================
# 카카오: refresh_token → access_token 갱신 → 나에게 보내기
# =========================
def kakao_refresh_access_token() -> str:
    refresh_token = os.environ["KAKAO_REFRESH_TOKEN"].strip()
    client_id = os.environ["KAKAO_REST_API_KEY"].strip()
    client_secret = (os.getenv("KAKAO_CLIENT_SECRET") or "").strip()

    data = {"grant_type": "refresh_token", "client_id": client_id, "refresh_token": refresh_token}
    if client_secret:
        data["client_secret"] = client_secret

    r = requests.post(
        "https://kauth.kakao.com/oauth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        data=data,
        timeout=30
    )
    if not r.ok:
        print("[Kakao token ERROR BODY]", r.text)
    r.raise_for_status()

    return r.json()["access_token"]


def kakao_send_to_me(access_token: str, text: str, link_url: str):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    template_object = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": link_url, "mobile_web_url": link_url},
        "button_title": KAKAO_BUTTON_TITLE
    }

    data = {"template_object": json.dumps(template_object, ensure_ascii=False)}
    r = requests.post(url, headers=headers, data=data, timeout=30)
    if not r.ok:
        print("[Kakao send ERROR BODY]", r.text)
    r.raise_for_status()
    return r.json()


# =========================
# main
# =========================
def main():
    required = [
        "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET",
        "KAKAO_REST_API_KEY", "KAKAO_REFRESH_TOKEN",
        "GIST_ID", "GH_GIST_TOKEN"
    ]
    missing = [k for k in required if not (os.getenv(k) or "").strip()]
    if missing:
        raise RuntimeError(f"Missing env: {missing}")

    now = kst_now()
    end_kst = anchor_end_time(now)

    force = (os.getenv("FORCE_SEND") or "0") == "1"
    if (not force) and (not is_business_day(end_kst)):
        print(f"[SKIP] Not a business day (end_kst={end_kst:%Y-%m-%d}). No send, state not updated.")
        return

    gist_id = os.environ["GIST_ID"].strip()
    gh_token = os.environ["GH_GIST_TOKEN"].strip()

    gist_json = gist_get(gist_id, gh_token)
    state = load_state_from_gist(gist_json)

    last_end_str = state.get("last_end_kst")
    if last_end_str:
        last_end_kst = datetime.fromisoformat(last_end_str).astimezone(KST)
    else:
        last_end_kst = end_kst - timedelta(hours=24)

    start_kst = last_end_kst
    print(f"[INFO] Window KST: {start_kst} ~ {end_kst}")

    articles_by_section = collect_articles(start_kst, end_kst)
    brief_text = openai_summarize(articles_by_section, start_kst, end_kst)

    updated = gist_update_files(gist_id, gh_token, {"latest.md": {"content": brief_text}})
    gist_url = updated.get("html_url") or gist_json.get("html_url") or f"https://gist.github.com/{gist_id}"

    highlights = []
    for sec, items in articles_by_section.items():
        if items:
            highlights.append(f"- {sec}: {shorten(items[0]['title'], 70)}")
    if not highlights:
        highlights.append("- 주요 기사: 없음(기간 내 검색 결과 기준)")

    kakao_text = (
        "농산물 뉴스 브리핑\n"
        f"{start_kst:%m/%d %H:%M}~{end_kst:%m/%d %H:%M} KST\n"
        + "\n".join(highlights[:4]) +
        "\n(전문은 버튼 클릭)"
    )

    access_token = kakao_refresh_access_token()
    kakao_send_to_me(access_token, kakao_text, gist_url)

    new_state = {"last_end_kst": end_kst.isoformat()}
    gist_update_files(gist_id, gh_token, {"state.json": {"content": json.dumps(new_state, ensure_ascii=False)}})

    print("[OK] Sent to Kakao + Updated gist/state.")


if __name__ == "__main__":
    main()
