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
            "operational_score": main.PREPUBLISH_QUALITY_MIN_OPERATIONAL_SCORE - 0.01,
            "counts": {"briefing_by_section": {section: 5 for section in main._section_keys()}},
            "metrics": {"reader_hard_issue_count": 0, "summary_presence_rate": 1.0},
            "scores": {"commodity_board_quality": 100.0},
            "editorial": {"status": "success", "acceptance_gate": {"passed": True}},
        }
        self.assertFalse(main._prepublish_evaluation_passed(result))

        result["operational_score"] = main.PREPUBLISH_QUALITY_MIN_OPERATIONAL_SCORE
        result["reader_quality_score"] = main.PREPUBLISH_QUALITY_MIN_OPERATIONAL_SCORE
        self.assertTrue(main._prepublish_evaluation_passed(result))

    def _sla_fallback_result(self) -> dict:
        return {
            "operational_score": main.PREPUBLISH_SLA_FALLBACK_MIN_SCORE,
            "reader_quality_score": main.PREPUBLISH_SLA_FALLBACK_MIN_SCORE,
            "counts": {
                "briefing_by_section": {
                    section: main.MAX_PER_SECTION for section in main._section_keys()
                }
            },
            "metrics": {"reader_hard_issue_count": 0, "summary_presence_rate": 1.0},
            "scores": {
                "commodity_board_quality": main.PREPUBLISH_SLA_FALLBACK_MIN_SCORE
            },
            "editorial": {
                "status": "success",
                "score": 70.0,
                "issues": [
                    {"type": "weak_core", "severity": "major", "section": "policy"}
                ],
                "acceptance_gate": {"passed": False},
            },
        }

    def test_sla_fallback_accepts_full_formal_briefing_with_only_soft_issues(self):
        result = self._sla_fallback_result()

        self.assertFalse(main._prepublish_evaluation_passed(result))
        self.assertTrue(main._prepublish_sla_fallback_publishable(result))

    def test_sla_fallback_rejects_hard_editorial_or_structural_issues(self):
        result = self._sla_fallback_result()
        result["editorial"]["issues"] = [
            {"type": "factual_error", "severity": "blocking", "section": "supply"}
        ]
        self.assertFalse(main._prepublish_sla_fallback_publishable(result))

        result = self._sla_fallback_result()
        result["counts"]["briefing_by_section"]["pest"] = main.MAX_PER_SECTION - 1
        self.assertFalse(main._prepublish_sla_fallback_publishable(result))

    def test_sla_fallback_rejects_score_below_floor(self):
        result = self._sla_fallback_result()
        result["operational_score"] = main.PREPUBLISH_SLA_FALLBACK_MIN_SCORE - 0.01

        self.assertFalse(main._prepublish_sla_fallback_publishable(result))

    def test_delivery_receipt_records_formal_page_and_normal_kakao_format(self):
        sections = self._raw_sections()
        with (
            patch.object(main, "github_get_file", return_value=(None, None)),
            patch.object(main, "github_put_file") as put_file,
        ):
            receipt = main._write_delivery_receipt(
                "owner/repo",
                "token",
                "2026-07-28",
                "https://example.com/archive/2026-07-28.html",
                "normal daily message",
                sections,
                publication_mode="sla_fallback",
            )

        self.assertTrue(main._delivery_receipt_succeeded(receipt, "2026-07-28"))
        self.assertEqual(receipt["page_format"], "full_formal_briefing")
        self.assertEqual(receipt["message_format"], "normal_daily_summary")
        self.assertEqual(receipt["section_counts"], {section: 5 for section in main._section_keys()})
        put_file.assert_called_once()

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

        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", return_value=3),
        ):
            repaired = main._apply_model_editorial_repair(repair, raw)

        self.assertIsNotNone(repaired)
        assert repaired is not None
        self.assertTrue(all(len(rows) == 5 for rows in repaired.values()))
        self.assertTrue(all(sum(1 for article in rows if article.is_core) == 2 for rows in repaired.values()))

        repair["sections"]["supply"][0]["link"] = "https://invented.invalid/not-in-pool"
        validation_errors: list[dict] = []
        with patch.object(main, "_postbuild_article_reject_reason", return_value=""):
            self.assertIsNone(
                main._apply_model_editorial_repair(
                    repair,
                    raw,
                    validation_errors=validation_errors,
                )
            )
        self.assertEqual(
            validation_errors,
            [
                {
                    "section": "supply",
                    "reason": "link_not_in_raw_pool",
                    "link": "https://invented.invalid/not-in-pool",
                    "title": "",
                }
            ],
        )

    def test_repair_rejects_excess_low_tier_sources_before_render(self):
        raw = self._raw_sections()
        repair = {
            "sections": {
                section: [{"link": article.link, "is_core": index < 2} for index, article in enumerate(rows)]
                for section, rows in raw.items()
            }
        }
        validation_errors: list[dict] = []

        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", return_value=1),
        ):
            repaired = main._apply_model_editorial_repair(
                repair,
                raw,
                validation_errors=validation_errors,
            )

        self.assertIsNone(repaired)
        self.assertEqual(validation_errors[0]["section"], "supply")
        self.assertEqual(validation_errors[0]["reason"], "low_tier_source_section_cap")

    def test_source_cap_validation_does_not_permanently_exclude_valid_candidate(self):
        self.assertFalse(
            main._repair_validation_error_excludes_candidate(
                {"reason": "low_tier_source_section_cap", "link": "https://example.com/keep"}
            )
        )
        self.assertFalse(
            main._repair_validation_error_excludes_candidate(
                {"reason": "low_tier_source_total_cap", "link": "https://example.com/keep"}
            )
        )
        self.assertTrue(
            main._repair_validation_error_excludes_candidate(
                {"reason": "pest_no_active_risk_core", "link": "https://example.com/drop"}
            )
        )

    def test_editorial_snapshot_is_enriched_with_source_tiers(self):
        raw = self._raw_sections()
        snapshot = {
            "raw_by_section": {
                section: [
                    {"title": article.title, "canon_url": article.canon_url}
                    for article in rows
                ]
                for section, rows in raw.items()
            }
        }

        with patch.object(main, "press_tier", return_value=3):
            enriched = main._enrich_editorial_snapshot_source_tiers(snapshot, raw)

        self.assertEqual(enriched, 20)
        self.assertTrue(
            all(
                row["press_tier"] == 3
                for rows in snapshot["raw_by_section"].values()
                for row in rows
            )
        )

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

    def test_factual_error_issue_invalidates_matching_summary_cache_entry(self):
        selected = self._raw_sections()
        target = selected["policy"][0]
        target.summary = "The wrong organization is attributed in this cached summary."
        summary_cache: dict[str, main.SummaryCacheEntry | str] = {
            target.norm_key: {"s": target.summary, "t": "2026-07-27T06:00:00+09:00"},
        }
        editorial = {
            "issues": [
                {
                    "type": "factual_error",
                    "section": "policy",
                    "title": target.title,
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

    def test_initial_repair_exclusions_hide_locally_invalid_candidates(self):
        raw = self._raw_sections()
        invalid = raw["supply"][0]

        def reject_reason(article, section):
            if article is invalid and section == "supply":
                return "supply_reader_role_misfit"
            return ""

        with patch.object(main, "_postbuild_article_reject_reason", side_effect=reject_reason):
            excluded = main._initial_editorial_repair_exclusions(raw)

        self.assertIn(invalid.link, excluded["supply"])
        self.assertNotIn(raw["supply"][1].link, excluded["supply"])


if __name__ == "__main__":
    unittest.main()
