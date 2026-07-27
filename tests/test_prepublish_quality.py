import unittest
from datetime import datetime
from unittest.mock import patch

import main


class PrepublishQualityGateTests(unittest.TestCase):
    def _stable_history_row(self, index: int) -> dict:
        return {
            "report_date": f"2026-07-{27 - index:02d}",
            "operational_score": 97.0,
            "editorial_score": 91.0,
            "editorial_acceptance_passed": True,
        }

    def test_stability_uses_last_twenty_full_evaluations_and_ignores_skips(self):
        reports = [
            {
                "report_date": "2026-07-27",
                "operational_score": 99.0,
                "editorial_score": None,
                "editorial_acceptance_passed": None,
            }
        ] + [self._stable_history_row(index) for index in range(main.PREPUBLISH_QUALITY_STABLE_DAYS)]

        self.assertTrue(main._quality_history_is_stable({"reports": reports}))

        reports[1]["editorial_score"] = 84.0
        self.assertFalse(main._quality_history_is_stable({"reports": reports}))

    def test_editorial_pass_also_requires_deterministic_quality(self):
        result = {
            "operational_score": 89.0,
            "counts": {"briefing_by_section": {section: 5 for section in main._section_keys()}},
            "metrics": {"reader_hard_issue_count": 0, "summary_presence_rate": 1.0},
            "scores": {"commodity_board_quality": 100.0},
            "editorial": {"status": "success", "acceptance_gate": {"passed": True}},
        }
        self.assertFalse(main._prepublish_evaluation_passed(result))

        result["operational_score"] = 94.0
        result["reader_quality_score"] = 94.0
        self.assertTrue(main._prepublish_evaluation_passed(result))

    def _raw_sections(self) -> dict[str, list[main.Article]]:
        raw: dict[str, list[main.Article]] = {}
        for section in main._section_keys():
            raw[section] = []
            for index in range(5):
                link = f"https://example.com/{section}/{index}"
                raw[section].append(
                    main.Article(
                        section=section,
                        title=f"{section} 농산물 기사 {index}",
                        description="가격 물량 정책 유통 병해충 현장 대응",
                        link=link,
                        originallink=link,
                        pub_dt_kst=datetime(2026, 7, 27, 6, 0, tzinfo=main.KST),
                        domain="example.com",
                        press="테스트신문",
                        norm_key=f"{section}-{index}",
                        title_key=f"{section}-title-{index}",
                        canon_url=link,
                        topic=f"{section}-topic-{index}",
                    )
                )
        return raw

    def test_repair_accepts_only_raw_pool_links_and_normalizes_core_count(self):
        raw = self._raw_sections()
        repair = {
            "sections": {
                section: [{"link": article.link, "is_core": False} for article in rows]
                for section, rows in raw.items()
            }
        }

        with patch.object(main, "_postbuild_article_reject_reason", return_value=""):
            repaired = main._apply_model_editorial_repair(repair, raw)

        self.assertIsNotNone(repaired)
        assert repaired is not None
        self.assertTrue(all(len(rows) == 5 for rows in repaired.values()))
        self.assertTrue(all(sum(1 for article in rows if article.is_core) == 2 for rows in repaired.values()))

        repair["sections"]["supply"][0]["link"] = "https://invented.invalid/not-in-pool"
        with patch.object(main, "_postbuild_article_reject_reason", return_value=""):
            self.assertIsNone(main._apply_model_editorial_repair(repair, raw))

    def test_bad_summary_issue_invalidates_only_matching_selected_cache_entry(self):
        selected = self._raw_sections()
        target = selected["supply"][0]
        untouched = selected["supply"][1]
        target.summary = "기존의 품질이 낮은 요약입니다. 다시 생성해야 하는 문장입니다."
        summary_cache: dict[str, main.SummaryCacheEntry | str] = {
            target.norm_key: {"s": target.summary, "t": "2026-07-27T06:00:00+09:00"},
            untouched.norm_key: {"s": "정상 요약입니다. 그대로 유지할 두 번째 문장입니다.", "t": "2026-07-27T06:00:00+09:00"},
        }
        editorial = {
            "issues": [
                {
                    "type": "bad_summary",
                    "section": "supply",
                    "title": target.title + "...",
                }
            ]
        }

        invalidated = main._invalidate_editorial_bad_summary_cache(
            editorial,
            selected,
            summary_cache,
        )

        self.assertEqual(invalidated, [target.norm_key])
        self.assertNotIn(target.norm_key, summary_cache)
        self.assertEqual(target.summary, "")
        self.assertIn(untouched.norm_key, summary_cache)


if __name__ == "__main__":
    unittest.main()
