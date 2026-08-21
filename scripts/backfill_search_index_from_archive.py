# -*- coding: utf-8 -*-
"""아카이브 HTML에서 검색 인덱스를 백필한다.

검색 인덱스(docs/search_index.json)는 2026-06-08 도입이라 그 이전 아카이브가
검색되지 않는다. 과거 날짜는 네이버 API 재수집(BACKFILL_*)로 재현할 수 없으므로,
발행 당시 확정본인 docs/archive/YYYY-MM-DD.html 카드에서 아이템을 복원한다.

- 인덱스에 없는 날짜만 추가한다(기존 아이템은 보존, 파이프라인이 쓴 원본 우선).
- 모든 아이템에 topics(원예 품목 태그)를 채운다. 분류기는 본문 파이프라인의
  _search_topics_for_text를 그대로 사용하고, 카드에 렌더된 topic 배지가 원예
  품목이면 합집합으로 반영한다(원문 전문 기준 분류라 절단 텍스트보다 정확).
- 카드 제목은 렌더 시 절단된 형태이므로 백필 아이템의 title도 절단본이다.

사용법: python scripts/backfill_search_index_from_archive.py
(로컬 파일만 수정한다. 커밋/발송/푸시 없음)
"""
import glob
import hashlib
import html as html_mod
import io
import json
import logging
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main  # noqa: E402

INDEX_PATH = "docs/search_index.json"
ARCHIVE_GLOB = "docs/archive/*.html"

_SEC_RE = re.compile(r'<section id="sec-(\w+)" class="sec".*?</section>', re.S)
_PRESS_RE = re.compile(r'<span class="press">(.*?)</span>', re.S)
_URL_RE = re.compile(r'class="btnOpen" href="([^"]+)"')
_TTL_RE = re.compile(r'<div class="ttl">(.*?)</div>', re.S)
_SUM_RE = re.compile(r'<div class="sum">(.*?)</div>', re.S)
_TOPIC_RE = re.compile(r'<span class="topic">(.*?)</span>', re.S)


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return html_mod.unescape(s).strip()


def _site_base(items: list) -> str:
    for it in items:
        arch = str((it or {}).get("archive") or "")
        if "/archive/" in arch:
            return arch.split("/archive/")[0] + "/"
    return "/agri-news-brief/"


def parse_archive_day(path: str, report_date: str, site_base: str, section_titles: dict) -> list:
    raw = io.open(path, encoding="utf-8").read()
    items = []
    for sec_m in _SEC_RE.finditer(raw):
        key = sec_m.group(1)
        body = sec_m.group(0)
        stitle = section_titles.get(key, key)
        archive_href = f"{site_base}archive/{report_date}.html#sec-{key}"
        chunks = re.split(r'<div class="card"', body)[1:]
        for rank, chunk in enumerate(chunks, start=1):
            url_m = _URL_RE.search(chunk)
            ttl_m = _TTL_RE.search(chunk)
            if not ttl_m:
                continue
            url = html_mod.unescape((url_m.group(1) if url_m else "").strip())
            title = _clean(ttl_m.group(1))
            press_m = _PRESS_RE.search(chunk)
            press = _clean(press_m.group(1)) if press_m else ""
            sum_m = _SUM_RE.search(chunk)
            summary = _clean(sum_m.group(1)) if sum_m else ""
            topic_m = _TOPIC_RE.search(chunk)
            card_topic = _clean(topic_m.group(1)) if topic_m else ""

            topics = set(main._search_topics_for_text(title, summary))
            if card_topic in main._HORTI_TOPICS_SET:
                topics.add(card_topic)

            dom = urlparse(url).netloc if url else ""
            tier = int(main.press_tier(press, dom))
            _id = hashlib.md5(f"{report_date}|{key}|{url}|{title}".encode("utf-8")).hexdigest()[:12]
            items.append({
                "id": _id,
                "date": report_date,
                "section": key,
                "section_title": stitle,
                "rank": rank,
                "title": title,
                "press": press,
                "summary": summary[:180],
                "url": url,
                "archive": archive_href,
                "score": 0.0,
                "press_tier": tier,
                "topics": sorted(topics),
            })
    return items


def run() -> None:
    with io.open(INDEX_PATH, encoding="utf-8") as f:
        idx = json.load(f)
    items = [x for x in idx.get("items", []) if isinstance(x, dict)]
    have_dates = {str(x.get("date")) for x in items}
    site_base = _site_base(items)
    section_titles = {s["key"]: s["title"] for s in main.SECTIONS}

    # 1) 기존 아이템 topics 보강 (없거나 비어있는 것만 채움)
    enriched = 0
    for it in items:
        if it.get("topics"):
            continue
        it["topics"] = main._search_topics_for_text(it.get("title") or "", it.get("summary") or "")
        enriched += 1

    # 2) 인덱스에 없는 아카이브 날짜 백필
    added_days = 0
    added_items = 0
    for path in sorted(glob.glob(ARCHIVE_GLOB)):
        d = os.path.basename(path)[:-5]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) or d in have_dates:
            continue
        day_items = parse_archive_day(path, d, site_base, section_titles)
        if not day_items:
            print(f"[warn] no cards parsed: {d}")
            continue
        items.extend(day_items)
        added_days += 1
        added_items += len(day_items)

    # 3) update_search_index와 동일한 정렬/보존 규칙 적용
    def _sort(x):
        d = x.get("date") or ""
        try:
            di = int(d.replace("-", ""))
        except Exception:
            di = 0
        return (di, int(x.get("press_tier") or 0), float(x.get("score") or 0.0), -int(x.get("rank") or 999))

    dates_desc = sorted({str(x.get("date")) for x in items}, reverse=True)
    keep = set(dates_desc[: main.MAX_SEARCH_DATES])
    items = [x for x in items if str(x.get("date")) in keep]
    items.sort(key=_sort, reverse=True)
    if len(items) > main.MAX_SEARCH_ITEMS:
        items = items[: main.MAX_SEARCH_ITEMS]

    idx["items"] = items
    idx["version"] = 1
    idx["topic_catalog"] = main._search_topic_catalog()
    idx["updated_at"] = datetime.now(tz=main.KST).isoformat()

    with io.open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(json.dumps(idx, ensure_ascii=False, indent=2))

    all_dates = sorted({str(x.get("date")) for x in items})
    print(f"enriched(topics): {enriched} | backfilled: {added_days} days / {added_items} items")
    print(f"index now: {len(items)} items, {len(all_dates)} days ({all_dates[0]} ~ {all_dates[-1]})")


if __name__ == "__main__":
    run()
