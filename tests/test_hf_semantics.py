from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hf_semantics
import main


class _FakeResponse:
    def __init__(self, payload, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 400
        self.text = ""

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def post(self, url, *, headers, json, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return _FakeResponse(self.payload)


class TestHFSemanticsModule(unittest.TestCase):
    def test_score_section_candidates_parses_token_embeddings_batch(self):
        cfg = hf_semantics.HFSemanticConfig(
            api_token="hf_test_token",
            model="intfloat/multilingual-e5-large",
            max_candidates=4,
            max_boost=0.9,
        )
        session = _FakeSession(
            [
                [[1.0, 0.0], [1.0, 0.0]],
                [[0.9, 0.1], [0.9, 0.1]],
                [[0.1, 0.9], [0.1, 0.9]],
            ]
        )
        section_conf = {
            "key": "pest",
            "title": "생육 리스크 및 방제",
            "queries": ["과수화상병 방제", "토마토뿔나방 예찰"],
            "must_terms": ["방제", "병해충", "예찰"],
        }
        articles = [
            SimpleNamespace(
                title="과수화상병 확산 차단 위해 과원 예찰 강화",
                description="사과 과원 농가에 약제를 공급하고 예찰을 강화한다.",
                press="뉴스1",
                source_query="과수화상병 방제",
            ),
            SimpleNamespace(
                title="토마토뿔나방 대응 위해 시설채소 농가 조사",
                description="시설채소 농가에 대한 예찰과 방제 지원을 실시한다.",
                press="뉴시스",
                source_query="토마토뿔나방 예찰",
            ),
        ]

        adjustments = hf_semantics.score_section_candidates(
            section_conf,
            articles,
            cfg=cfg,
            session_factory=lambda: session,
        )

        self.assertEqual(len(adjustments), 2)
        self.assertGreater(adjustments[0].similarity, adjustments[1].similarity)
        self.assertGreater(adjustments[0].boost, adjustments[1].boost)
        self.assertEqual(session.calls[0]["url"], cfg.endpoint_url())
        self.assertEqual(session.calls[0]["headers"]["Authorization"], "Bearer hf_test_token")

    def test_score_profile_passages_with_noise_penalizes_noise_like_passage(self):
        cfg = hf_semantics.HFSemanticConfig(
            api_token="hf_test_token",
            model="intfloat/multilingual-e5-large",
            max_candidates=4,
            max_boost=0.9,
        )
        session = _FakeSession(
            [
                [[1.0, 0.0], [1.0, 0.0]],
                [[0.0, 1.0], [0.0, 1.0]],
                [[0.98, 0.02], [0.98, 0.02]],
                [[0.28, 0.72], [0.28, 0.72]],
            ]
        )

        adjustments = hf_semantics.score_profile_passages_with_noise(
            "query: 샤인머스캣 수급과 가격 기사",
            ["오피니언 칼럼과 수필, 개인 서사 중심 기사"],
            [
                "passage: 샤인머스캣 가격 하락과 폐원 논의가 이어지고 출하 조절 대책이 거론된다.",
                "passage: 샤인머스캣을 떠올리며 농가의 시간을 회상하는 수필 형식의 글이다.",
            ],
            cfg=cfg,
            session_factory=lambda: session,
        )

        self.assertEqual(len(adjustments), 2)
        self.assertLess(adjustments[0].negative_similarity, adjustments[1].negative_similarity)
        self.assertGreater(adjustments[0].margin, adjustments[1].margin)
        self.assertGreater(adjustments[0].boost, adjustments[1].boost)


class TestHFSemanticsSelectionIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conf = {s["key"]: s for s in main.SECTIONS}
        cls.now = datetime.now(main.KST)

    def _make_article(self, section: str, title: str, desc: str, url: str, *, score: float) -> main.Article:
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        canon = main.canonicalize_url(url)
        title_key = main.norm_title_key(title)
        return main.Article(
            section=section,
            title=title,
            description=desc,
            link=url,
            originallink=url,
            origin_section=section,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            norm_key=main.make_norm_key(canon, press, title_key),
            title_key=title_key,
            canon_url=canon,
            topic=main.extract_topic(title, desc),
            score=score,
        )

    def test_select_top_articles_can_flip_close_ranking_with_semantic_boost(self):
        fire_blight = self._make_article(
            "pest",
            "진주시, 과수화상병 예찰 강화… 방제 약제 3회 무상 공급",
            "과수화상병 확산 차단을 위해 사과 과원 예찰과 약제 방제를 강화한다.",
            "https://www.newsis.com/view/NISX20260228_0003530198",
            score=9.7,
        )
        tomato_moth = self._make_article(
            "pest",
            "경기도, 토마토뿔나방 예찰 확대… 시설채소 농가 방제 지원",
            "토마토뿔나방 확산 대응을 위해 시설채소 농가 전수조사와 방제 지원을 실시한다.",
            "https://www.kyeonggi.com/article/20260327580123",
            score=9.5,
        )

        with mock.patch.object(
            main,
            "_hf_semantic_selection_adjustments",
            return_value={
                main._article_selection_key(fire_blight): hf_semantics.SemanticAdjustment(
                    similarity=0.71,
                    boost=-0.2,
                    model="test-model",
                ),
                main._article_selection_key(tomato_moth): hf_semantics.SemanticAdjustment(
                    similarity=0.92,
                    boost=0.8,
                    model="test-model",
                ),
            },
        ):
            picked = main.select_top_articles([fire_blight, tomato_moth], "pest", 1)

        self.assertEqual(len(picked), 1)
        self.assertEqual(picked[0].title, tomato_moth.title)
        self.assertGreater(float(getattr(picked[0], "semantic_boost", 0.0) or 0.0), 0.0)

    def test_select_top_articles_can_drop_noise_story_with_semantic_margin(self):
        essay_story = self._make_article(
            "supply",
            "샤인머스캣 속사정",
            "샤인머스캣 가격 하락과 재배 면적 확대를 돌아보는 글로 농가의 회한과 감상을 담았다.",
            "https://example.com/shine-muscat-essay",
            score=22.1,
        )
        issue_story = self._make_article(
            "supply",
            "샤인머스캣 가격 하락에 폐원 논의…농가 대책 촉구",
            "샤인머스캣 가격 약세와 재배 면적 조정, 폐원 지원 요구가 이어지고 있다.",
            "https://example.com/shine-muscat-issue",
            score=21.7,
        )
        onion_story = self._make_article(
            "supply",
            "양파 출하 조절 총력…산지 가격 반등 모색",
            "양파 산지에서 출하 조절과 저장 관리로 가격 반등을 모색하고 있다.",
            "https://example.com/onion-issue",
            score=21.1,
        )

        with mock.patch.object(
            main,
            "_hf_semantic_selection_adjustments",
            return_value={
                main._article_selection_key(essay_story): hf_semantics.SemanticAdjustment(
                    similarity=0.81,
                    boost=-0.9,
                    model="test-model",
                    negative_similarity=0.93,
                    margin=-0.12,
                ),
                main._article_selection_key(issue_story): hf_semantics.SemanticAdjustment(
                    similarity=0.89,
                    boost=0.42,
                    model="test-model",
                    negative_similarity=0.38,
                    margin=0.51,
                ),
                main._article_selection_key(onion_story): hf_semantics.SemanticAdjustment(
                    similarity=0.86,
                    boost=0.18,
                    model="test-model",
                    negative_similarity=0.33,
                    margin=0.53,
                ),
            },
        ):
            picked = main.select_top_articles([essay_story, issue_story, onion_story], "supply", 2)

        picked_titles = {article.title for article in picked}
        self.assertIn(issue_story.title, picked_titles)
        self.assertIn(onion_story.title, picked_titles)
        self.assertNotIn(essay_story.title, picked_titles)

    def test_select_top_articles_skips_obvious_column_marker_story(self):
        column_story = self._make_article(
            "supply",
            "[길섶에서] 샤인머스캣 속사정",
            "샤인머스캣 가격 하락을 되짚는 칼럼 형식의 글이다.",
            "https://example.com/shine-muscat-column",
            score=22.1,
        )
        issue_story = self._make_article(
            "supply",
            "샤인머스캣 가격 하락에 폐원 논의…농가 대책 촉구",
            "샤인머스캣 가격 약세와 재배 면적 조정, 폐원 지원 요구가 이어지고 있다.",
            "https://example.com/shine-muscat-issue-core",
            score=21.5,
        )
        tomato_story = self._make_article(
            "supply",
            "토마토 작황 부진에 출하량 감소…도매가격 강세",
            "시설 토마토 작황 부진으로 출하량이 줄며 도매가격이 강세를 보이고 있다.",
            "https://example.com/tomato-supply-core",
            score=21.2,
        )

        picked = main.select_top_articles([column_story, issue_story, tomato_story], "supply", 2)
        picked_titles = {article.title for article in picked}

        self.assertIn(issue_story.title, picked_titles)
        self.assertIn(tomato_story.title, picked_titles)
        self.assertNotIn(column_story.title, picked_titles)


if __name__ == "__main__":
    unittest.main()
