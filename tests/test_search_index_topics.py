# -*- coding: utf-8 -*-
"""검색 인덱스 품목 태깅과 아카이브 백필 파서 테스트.

'배' 같은 한 글자 품목 검색이 부분문자열 오탐(배추/재배/배송)에 묻히는 문제를
품목 태그 + 별칭 카탈로그로 해결한다. 인덱스 스키마 하위호환과 카탈로그 구성,
index.html JS 배선, 백필 파서의 필드 복원을 검증한다.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


def _load_backfill_module():
    path = ROOT / "scripts" / "backfill_search_index_from_archive.py"
    spec = importlib.util.spec_from_file_location("backfill_search_index", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSearchTopicsForText(unittest.TestCase):
    def test_pear_context_is_tagged(self):
        topics = main._search_topics_for_text('나주배 수출 성장세…"세계 최고의 배"', "")
        self.assertIn("배", topics)

    def test_napa_cabbage_does_not_leak_pear(self):
        topics = main._search_topics_for_text("배추 저장량 5.2% 감소", "저장 배추 수급 점검")
        self.assertIn("배추", topics)
        self.assertNotIn("배", topics)

    def test_delivery_noise_gets_no_horti_tag(self):
        self.assertEqual(main._search_topics_for_text("쿠팡 배송 지연 대란", ""), [])

    def test_apology_is_not_apple(self):
        self.assertNotIn("사과", main._search_topics_for_text("사과문 발표한 유통업체", ""))

    def test_apple_price_is_apple(self):
        self.assertIn("사과", main._search_topics_for_text("올 추석 金사과 걱정 줄었다", "사과 가격 하락"))

    def test_enumeration_headline_supplements_pear(self):
        # 나열형("사과·배")은 bigram 문맥 게이트가 놓치는 계열 — 검색 태깅에서 보강
        topics = main._search_topics_for_text(
            '농식품부 "폭염에도 사과·배 작황 양호… 수급 안정적"',
            "전국 사과·배는 폭염과 가뭄에도 작황이 양호해 수급이 안정적일 것으로 전망됐다.",
        )
        self.assertIn("배", topics)

    def test_fire_blight_summary_supplements_pear(self):
        topics = main._search_topics_for_text(
            "공주시 '과수화상병·돌발해충 방제 약제' 무상 지원",
            "충남 공주시가 사과·배 과수화상병과 돌발해충 방제 약제를 지원한다.",
        )
        self.assertIn("배", topics)

    def test_numeric_multiplier_is_not_pear(self):
        self.assertNotIn("배", main._search_topics_for_text(
            "폭염에 시금치 2배, 오이·깻잎도 60%대 급등", "가격이 2배로 뛰었다."))
        self.assertNotIn("배", main._search_topics_for_text(
            "예산 밤나무 43.49㏊(축구장 61배 크기) 드론 방제", "밤나무 재배지 방제를 실시한다."))

    def test_cultivation_compound_is_not_pear(self):
        self.assertNotIn("배", main._search_topics_for_text(
            "스마트팜 계약재배 확대 추진", "계약재배 물량이 늘었다."))

    def test_napa_radish_enumeration_supplements_radish_not_pear(self):
        topics = main._search_topics_for_text(
            "폭염에 추석 채솟값 뛸라…정부, 배추·무 비축 물량 푼다",
            "정부가 배추·무 비축물량을 공급한다.",
        )
        self.assertIn("무", topics)
        self.assertIn("배추", topics)
        self.assertNotIn("배", topics)

    def test_chestnut_tree_supplements_chestnut(self):
        self.assertIn("밤", main._search_topics_for_text(
            "예산군, 드론 활용 밤나무 병해충 방제 추진", ""))
        self.assertNotIn("밤", main._search_topics_for_text(
            "밤사이 폭우로 농경지 침수 피해", "간밤에 내린 비로 침수됐다."))


class TestSearchTopicCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = main._search_topic_catalog()
        self.by_topic = {c["topic"]: c["aliases"] for c in self.catalog}
        self.by_entry = {c["topic"]: c for c in self.catalog}

    def test_covers_all_horti_topics(self):
        self.assertEqual(set(self.by_topic), set(main._HORTI_TOPICS_SET))

    def test_pear_aliases(self):
        self.assertIn("배", self.by_topic["배"])
        self.assertIn("나주배", self.by_topic["배"])

    def test_single_char_shortcuts_map_to_topics(self):
        self.assertIn("감", self.by_topic["단감"])
        self.assertIn("감", self.by_topic["감/곶감"])
        self.assertIn("귤", self.by_topic["감귤/만감"])
        self.assertIn("꽃", self.by_topic["화훼"])
        self.assertIn("파", self.by_topic["대파"])

    def test_aliases_are_lowercase_and_tokenizable(self):
        for c in self.catalog:
            for a in c["aliases"]:
                self.assertEqual(a, a.lower())
                self.assertNotIn(" ", a)

    def test_nested_commodity_excludes(self):
        # "배추"⊂"양배추", "오이"⊂"오이고추" — 부분문자열 경로의 교차 오염 방지
        self.assertIn("양배추", self.by_entry["배추"].get("exclude_substr", []))
        self.assertIn("오이고추", self.by_entry["오이"].get("exclude_substr", []))
        self.assertIn("오이맛고추", self.by_entry["오이"].get("exclude_substr", []))
        self.assertIn("사과대추", self.by_entry["사과"].get("exclude_substr", []))
        self.assertIn("뉴스토마토", self.by_entry["토마토"].get("exclude_substr", []))
        self.assertNotIn("exclude_substr", self.by_entry["양배추"])

    def test_homonym_dominant_alias_is_tag_only(self):
        # "가지"는 여러 가지/나뭇가지/가지검은마름병 오탐이 94% — 태그 전용
        self.assertTrue(self.by_entry["가지"].get("tag_only"))
        self.assertNotIn("tag_only", self.by_entry["오이"])

    def test_specific_pepper_aliases_owned_by_specific_topic(self):
        # 우산 토픽(고추/호박)이 하위 품목명을 겸유하면 "풋고추" 검색이 고추 전체를 부른다
        self.assertNotIn("풋고추", self.by_topic["고추"])
        self.assertNotIn("청양고추", self.by_topic["고추"])
        self.assertIn("풋고추", self.by_topic["풋고추"])
        self.assertIn("청양고추", self.by_topic["풋고추"])
        self.assertIn("고추", self.by_topic["고추"])  # 우산어는 유지
        self.assertNotIn("애호박", self.by_topic["호박"])
        self.assertIn("애호박", self.by_topic["애호박(쥬키니)"])
        self.assertIn("호박", self.by_topic["호박"])

    def test_cabbage_article_not_tagged_napa(self):
        topics = main._search_topics_for_text("양배추 가격 급등에 소비자 부담", "양배추 출하량이 줄었다.")
        self.assertIn("양배추", topics)
        self.assertNotIn("배추", topics)


class TestSearchItemSchema(unittest.TestCase):
    def test_items_carry_topics_and_legacy_keys(self):
        by_section = {
            "supply": [{
                "title": "신고배 출하 앞두고 가뭄 피해 우려",
                "link": "https://news.example.com/pear-1",
                "press": "농민신문",
                "summary": "배 주산지 가뭄으로 출하량 감소가 우려된다.",
                "score": 12.5,
            }],
        }
        items = main._make_search_items_for_day("2026-08-21", by_section, "/agri-news-brief/")
        self.assertEqual(len(items), 1)
        it = items[0]
        for key in ("id", "date", "section", "section_title", "rank", "title",
                    "press", "summary", "url", "archive", "score", "press_tier", "topics"):
            self.assertIn(key, it)
        self.assertIn("배", it["topics"])

    def test_update_search_index_preserves_other_dates_and_sets_catalog(self):
        existing = {
            "version": 1,
            "updated_at": "",
            "items": [{
                "id": "old123", "date": "2026-01-05", "section": "supply",
                "section_title": "품목 및 수급 동향", "rank": 1,
                "title": "월동무 출하", "press": "언론사", "summary": "",
                "url": "https://news.example.com/old", "archive": "/agri-news-brief/archive/2026-01-05.html#sec-supply",
                "score": 1.0, "press_tier": 2, "topics": ["무"],
            }],
        }
        by_section = {"supply": [{
            "title": "사과 도매가격 강세", "link": "https://news.example.com/apple",
            "press": "언론사", "summary": "사과 가격이 강세다.", "score": 5.0,
        }]}
        idx = main.update_search_index(existing, "2026-08-21", by_section, "/agri-news-brief/")
        dates = {x["date"] for x in idx["items"]}
        self.assertIn("2026-01-05", dates)
        self.assertIn("2026-08-21", dates)
        self.assertTrue(idx.get("topic_catalog"))
        aliases = {a for c in idx["topic_catalog"] for a in c["aliases"]}
        self.assertIn("배", aliases)


class TestIndexPageWiring(unittest.TestCase):
    def test_render_index_page_wires_commodity_search(self):
        html = main.render_index_page({"dates": ["2026-08-21"]}, "/agri-news-brief/")
        for needle in ("ALIAS2TOPICS", "ALIAS2EXCLUDES", "ALIAS2TAGONLY",
                       "exclude_substr", "classifyTokens", "topic_catalog",
                       "topicChip", "tokenHit", "검색 가능:"):
            self.assertIn(needle, html)
        # 한 글자 일반어 안내 + 기본 기간 전체(로드시 30일 자동 축소 제거)
        self.assertIn("한 글자", html)
        self.assertIn("default date: 전체 기간", html)


class TestBackfillParser(unittest.TestCase):
    SAMPLE = """
    <section id="sec-supply" class="sec">
      <div class="secBody">
        <div class="card" style="border-left-color:#0f766e">
          <div class="cardTop">
            <div class="meta">
              <span class="press">서울신문</span>
              <span class="time">03/09 18:04</span>
              <span class="topic">배</span>
            </div>
            <a class="btnOpen" href="https://news.example.com/pear?a=1&amp;b=2" target="_blank" rel="noopener">원문 열기</a>
          </div>
          <div class="ttl">&quot;신고배&quot; 출하 앞두고 저장량 점검...</div>
          <div class="sum">배 주산지 저장량이 감소했다.</div>
        </div>
        <div class="card" style="border-left-color:#0f766e">
          <div class="cardTop">
            <div class="meta"><span class="press">농수축산신문</span></div>
            <a class="btnOpen" href="https://news.example.com/cabbage" target="_blank" rel="noopener">원문 열기</a>
          </div>
          <div class="ttl">배추 저장량 5.2% 감소</div>
          <div class="sum">저장 배추 수급을 점검한다.</div>
        </div>
      </div>
    </section>
    """

    def test_parse_archive_day_restores_fields(self):
        mod = _load_backfill_module()
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "2026-03-10.html"
            p.write_text(self.SAMPLE, encoding="utf-8")
            items = mod.parse_archive_day(
                str(p), "2026-03-10", "/agri-news-brief/",
                {s["key"]: s["title"] for s in main.SECTIONS},
            )

        self.assertEqual(len(items), 2)
        pear, cabbage = items
        self.assertEqual(pear["date"], "2026-03-10")
        self.assertEqual(pear["section"], "supply")
        self.assertEqual(pear["press"], "서울신문")
        self.assertEqual(pear["url"], "https://news.example.com/pear?a=1&b=2")
        self.assertEqual(pear["title"], '"신고배" 출하 앞두고 저장량 점검...')
        self.assertIn("배", pear["topics"])  # 카드 topic 배지 반영
        self.assertEqual(pear["rank"], 1)
        self.assertTrue(pear["archive"].endswith("archive/2026-03-10.html#sec-supply"))

        self.assertEqual(cabbage["rank"], 2)
        self.assertIn("배추", cabbage["topics"])
        self.assertNotIn("배", cabbage["topics"])

    HOMONYM_SAMPLE = """
    <section id="sec-pest" class="sec">
      <div class="secBody">
        <div class="card">
          <div class="cardTop">
            <div class="meta"><span class="press">언론사</span><span class="topic">가지</span></div>
            <a class="btnOpen" href="https://news.example.com/blight" target="_blank">원문 열기</a>
          </div>
          <div class="ttl">과수화상병 예방 철저 당부</div>
          <div class="sum">배 재배 농가 대상 예방 교육을 실시한다.</div>
        </div>
        <div class="card">
          <div class="cardTop">
            <div class="meta"><span class="press">언론사</span><span class="topic">가지</span></div>
            <a class="btnOpen" href="https://news.example.com/eggplant" target="_blank">원문 열기</a>
          </div>
          <div class="ttl">가지 출하량 증가로 가격 하락</div>
          <div class="sum">여름 가지 출하가 늘었다.</div>
        </div>
      </div>
    </section>
    """

    def test_homonym_badge_trusted_only_with_text_evidence(self):
        # 과거 배지 오분류('가지'=나뭇가지 문맥) 유입 차단 — 텍스트에 품목명이 있을 때만 신뢰
        mod = _load_backfill_module()
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "2026-03-18.html"
            p.write_text(self.HOMONYM_SAMPLE, encoding="utf-8")
            items = mod.parse_archive_day(
                str(p), "2026-03-18", "/agri-news-brief/",
                {s["key"]: s["title"] for s in main.SECTIONS},
            )
        blight, eggplant = items
        self.assertNotIn("가지", blight["topics"])
        self.assertIn("가지", eggplant["topics"])


if __name__ == "__main__":
    unittest.main()
