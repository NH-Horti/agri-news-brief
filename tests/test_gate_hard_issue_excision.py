"""발행 전 게이트의 결정적 절제(excision)와 강제 SLA 복구의 편집 평가 실행 (2026-09-16 재발 방지)."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main

KST = timezone(timedelta(hours=9))


def _mk(title, section="policy", desc="", domain="news.example.com", is_core=False, score=10.0):
    link = f"https://{domain}/{abs(hash(title)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description=desc,
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 9, 15, 18, 0, tzinfo=KST),
        domain=domain,
        press="언론사",
        norm_key=main.make_norm_key(link, "언론사", main.norm_title_key(title)),
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=score,
        is_core=is_core,
        selection_fit_score=2.0,
    )


def _sections():
    return {
        "supply": [_mk(f"공급 기사 {i}", "supply", is_core=i < 2) for i in range(5)],
        "policy": [
            _mk("농식품부, 추석 성수품 109.1% 공급", "policy", is_core=True),
            _mk("추석 계란값 잡는다…농협 공급 2.4배로 확대", "policy", is_core=True),
            _mk("농업소득 짓누르는 경영비…농가 경영안전망 실효성 시험대", "policy"),
            _mk("대구 동구, 추석맞이 종합 대책 추진", "policy"),
            _mk("청주 내수농협, 계약 재배 농가에 영농자재 지원", "policy"),
        ],
        "dist": [_mk(f"유통 기사 {i}", "dist", is_core=i < 2) for i in range(5)],
        "pest": [_mk(f"병해충 기사 {i}", "pest", is_core=i < 2) for i in range(5)],
    }


def _editorial(issues, score=68.5, status="success"):
    return {
        "status": status,
        "score": score,
        "issues": issues,
        "acceptance_gate": {"passed": False, "status": "needs_major_iteration"},
        "scores": {"article_selection": 66, "section_fit": 72, "core": 66, "summary": 90, "missed": 58, "noise": 58},
    }


def _result(editorial, operational=93.0):
    return {
        "overall_score": operational,
        "operational_score": operational,
        "reader_quality_score": 85.0,
        "scores": {"commodity_board_quality": 100.0},
        "counts": {"briefing_by_section": {s: 5 for s in main._section_keys()}},
        "metrics": {"reader_hard_issue_count": 0, "summary_presence_rate": 1.0},
        "editorial": editorial,
    }


class ExcisionTargetTests(unittest.TestCase):
    def setUp(self):
        main._GATE_EXCISED_LINK_KEYS.clear()
        main._GATE_EXCISED_ARTICLES.clear()
        main._GATE_EXCISION_KEEP_LINK_KEYS.clear()

    def test_targets_match_truncated_titles_and_ambiguous_sections(self):
        sections = _sections()
        issues = [
            {"type": "off_topic", "severity": "blocking", "section": "policy",
             "title": "대구 동구, 추석맞이 종합 대책 추진", "reason": "비농업"},
            {"type": "duplicate_story", "severity": "major", "section": "supply/dist",
             "title": "유통 기사 3", "reason": "중복"},
            {"type": "weak_core", "severity": "moderate", "section": "policy",
             "title": "농식품부, 추석 성수품 109.1% 공급", "reason": "약함"},
            {"type": "wrong_section", "severity": "moderate", "section": "supply",
             "title": "공급 기사 1", "reason": "정책 기사"},
        ]
        targets = main._editorial_excision_targets(_editorial(issues), sections)
        self.assertEqual(
            [(t["section"], t["title"]) for t in targets],
            [("policy", "대구 동구, 추석맞이 종합 대책 추진"), ("dist", "유통 기사 3")],
        )
        # blocking 이 major 보다 앞서고, moderate 는 절제 대상이 아니다
        self.assertEqual(targets[0]["severity"], "blocking")

    def test_excised_cards_are_blocked_at_the_chokepoint(self):
        sections = _sections()
        victim = sections["policy"][3]
        targets = [{"section": "policy", "article": victim, "title": victim.title, "link": victim.link}]
        refilled = _mk("정부, 추석 농축산물 할인 지원 900억 추가", "policy")

        def fake_recover(final, raw, *, max_items=None):
            final["policy"].append(refilled)
            return 1

        with (
            patch.object(main, "_recover_preferred_section_counts_from_raw", side_effect=fake_recover),
            patch.object(main, "_final_global_story_dedupe", return_value=(0, 0)),
            patch.object(main, "_cap_final_low_tier_sources", return_value=0),
            patch.object(main, "_ensure_final_selection_fit", return_value=0),
            patch.object(main, "_demote_soft_news_final_cores", return_value=0),
            patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
            patch.object(main, "_finalize_sections_for_render", return_value=0),
        ):
            excised = main._excise_flagged_cards_and_refill(sections, {}, targets, {})
        self.assertIsNotNone(excised)
        assert excised is not None
        self.assertNotIn(victim, excised["policy"])
        self.assertIn(refilled, excised["policy"])
        self.assertEqual(len(excised["policy"]), 5)
        self.assertEqual(main._postbuild_article_reject_reason(victim, "policy"), "editorial_issue_excised")
        # 원본 선정은 건드리지 않는다
        self.assertIn(victim, sections["policy"])

    def test_duplicates_of_excised_cards_are_blocked_from_refill(self):
        main._GATE_EXCISED_ARTICLES.clear()
        sections = _sections()
        victim = _mk("봄동·당근 파렛트 출하 의무화", "supply", domain="agrinet.co.kr")
        sections["supply"][4] = victim
        variant = _mk("느타리·봄동·제주당근까지…가락시장 파렛트 의무출하 가속", "supply", domain="aflnews.co.kr")
        targets = [{"section": "supply", "article": victim, "title": victim.title, "link": victim.link}]
        with (
            patch.object(main, "_recover_preferred_section_counts_from_raw", return_value=0),
            patch.object(main, "_final_global_story_dedupe", return_value=(0, 0)),
            patch.object(main, "_cap_final_low_tier_sources", return_value=0),
            patch.object(main, "_ensure_final_selection_fit", return_value=0),
            patch.object(main, "_demote_soft_news_final_cores", return_value=0),
            patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
            patch.object(main, "_finalize_sections_for_render", return_value=0),
        ):
            excised = main._excise_flagged_cards_and_refill(sections, {}, targets, {})
        self.assertIsNotNone(excised)
        self.assertEqual(main._postbuild_article_reject_reason(variant, "supply"), "editorial_issue_excised_duplicate")
        unrelated = _mk("사과 도매가 3주째 하락…추석 수요 둔화", "supply")
        self.assertNotIn("excised", main._postbuild_article_reject_reason(unrelated, "supply"))
        # 중복의 남는 쪽(지면에 남은 카드)은 절제 카드와 중복이어도 잘리지 않는다
        kept_twin = _mk("가락시장, 파렛트 중심 물류체계 전환 가속화", "dist", domain="wonyesanup.co.kr")
        sections["dist"][4] = kept_twin
        main._GATE_EXCISION_KEEP_LINK_KEYS.update(main._repair_article_link_keys(kept_twin))
        self.assertNotEqual(main._postbuild_article_reject_reason(kept_twin, "dist"), "editorial_issue_excised_duplicate")
        main._GATE_EXCISED_ARTICLES.clear()
        main._GATE_EXCISION_KEEP_LINK_KEYS.clear()

    def test_refill_below_floor_keeps_previous_selection(self):
        sections = _sections()
        victims = sections["policy"][:3]
        targets = [{"section": "policy", "article": v, "title": v.title, "link": v.link} for v in victims]
        with (
            patch.object(main, "_recover_preferred_section_counts_from_raw", return_value=0),
            patch.object(main, "_final_global_story_dedupe", return_value=(0, 0)),
            patch.object(main, "_cap_final_low_tier_sources", return_value=0),
            patch.object(main, "_ensure_final_selection_fit", return_value=0),
            patch.object(main, "_demote_soft_news_final_cores", return_value=0),
            patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
            patch.object(main, "_finalize_sections_for_render", return_value=0),
        ):
            self.assertIsNone(main._excise_flagged_cards_and_refill(sections, {}, targets, {}))

    def test_carried_forward_editorial_drops_only_excised_issues(self):
        issues = [
            {"type": "off_topic", "severity": "blocking", "section": "policy", "title": "대구 동구, 추석맞이 종합 대책 추진"},
            {"type": "promotional_filler", "severity": "moderate", "section": "dist", "title": "유통 기사 2"},
        ]
        targets = [{"section": "policy", "title": "대구 동구, 추석맞이 종합 대책 추진"}]
        carried = main._editorial_result_without_excised(_editorial(issues), targets, _result({}))
        self.assertEqual([i["title"] for i in carried["issues"]], ["유통 기사 2"])
        self.assertTrue(carried["carried_forward_after_excision"])
        self.assertEqual(carried["excised_issue_count"], 1)
        self.assertEqual(carried["acceptance_gate"]["blocking_issue_count"], 0)
        result = _result(carried)
        self.assertEqual(main._prepublish_hard_editorial_issues(result), [])
        self.assertNotIn("editorial_hard_issues:1", main._prepublish_sla_fallback_blockers(result))


class GateFlowTests(unittest.TestCase):
    def setUp(self):
        main._GATE_EXCISED_LINK_KEYS.clear()
        main._GATE_EXCISED_ARTICLES.clear()
        main._GATE_EXCISION_KEEP_LINK_KEYS.clear()
        main.OPENAI_USAGE_EVENTS.clear()

    def _run_gate(self, evaluations, *, forced=False):
        calls = []

        def fake_compose(report_date, html_text, snapshot_payload, *, run_editorial, adaptive_reason):
            calls.append((run_editorial, adaptive_reason))
            return evaluations.pop(0)

        sections = _sections()
        victim = sections["policy"][3]
        refilled = _mk("정부, 추석 농축산물 할인 지원 900억 추가", "policy")

        def fake_excise(current, raw, targets, cache, *, allow_openai_summaries=True):
            self.assertEqual([t["title"] for t in targets], [victim.title])
            out = {k: list(v) for k, v in current.items()}
            out["policy"] = [a for a in out["policy"] if a is not victim] + [refilled]
            return out

        with (
            patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", forced),
            patch.object(main, "PREPUBLISH_SLA_FALLBACK_ENABLED", True),
            patch.object(main, "PREPUBLISH_QUALITY_FAIL_CLOSED", False),
            patch.object(main, "PREPUBLISH_MAX_HARD_ISSUE_EXCISIONS", 2),
            patch.object(main, "_OPENAI_QUOTA_EXHAUSTED", False),
            patch.object(main, "_prepublish_deadline_reached", return_value=False),
            patch.object(main, "_should_run_full_editorial_eval", return_value=(True, "deterministic_anomaly")),
            patch.object(main, "_compose_prepublish_evaluation", side_effect=fake_compose),
            patch.object(main, "_excise_flagged_cards_and_refill", side_effect=fake_excise),
            patch.object(main, "render_daily_page", return_value="<html>"),
            patch.object(main, "_enrich_editorial_snapshot_source_tiers", return_value=0),
            patch.object(main, "_initial_editorial_repair_exclusions", return_value={s: set() for s in main._section_keys()}),
            patch.object(main, "_prepublish_editorial_budget_available", return_value=False),
            patch.object(main, "_write_prepublish_evaluation_artifacts"),
            patch.object(main, "_notify_quality_hold"),
            patch("report_eval.load_snapshot_payload", return_value={}),
            patch("editorial_eval.propose_editorial_repair", side_effect=AssertionError("repair must not run")),
        ):
            out_sections, _html, result = main._run_prepublish_quality_gate(
                "repo", "token", "2026-09-16", datetime(2026, 9, 15, 6, tzinfo=KST), datetime(2026, 9, 16, 6, tzinfo=KST),
                "https://example.test/", ["2026-09-16"], "docs", {}, sections, {}, Path("snapshot.json"),
            )
        return out_sections, result, calls, victim, refilled

    def test_blocking_issue_is_excised_and_published_via_sla_fallback(self):
        blocking = {"type": "off_topic", "severity": "blocking", "section": "policy",
                    "title": "대구 동구, 추석맞이 종합 대책 추진", "reason": "비농업"}
        evaluations = [
            _result({"status": "skipped"}),                       # policy probe
            _result(_editorial([blocking])),                      # first editorial eval
            _result({"status": "skipped", "reason": "x"}),        # deterministic re-eval after excision (budget gone)
        ]
        out_sections, result, calls, victim, refilled = self._run_gate(evaluations)
        gate = result["prepublish_quality_gate"]
        self.assertTrue(gate["publishable"])
        self.assertEqual(gate["publication_mode"], "sla_fallback")
        self.assertEqual(gate["hard_editorial_issue_count"], 0)
        self.assertEqual(len(gate["hard_issue_excisions"]), 1)
        self.assertEqual(gate["hard_issue_excisions"][0]["verification"], "deterministic_carry_forward")
        self.assertNotIn(victim, out_sections["policy"])
        self.assertIn(refilled, out_sections["policy"])
        self.assertTrue(result["editorial"]["carried_forward_after_excision"])

    def test_forced_recovery_runs_editorial_review_instead_of_skipping(self):
        blocking = {"type": "off_topic", "severity": "blocking", "section": "policy",
                    "title": "대구 동구, 추석맞이 종합 대책 추진", "reason": "비농업"}
        evaluations = [
            _result({"status": "skipped"}),
            _result(_editorial([blocking])),
            _result({"status": "skipped", "reason": "x"}),
        ]
        out_sections, result, calls, victim, _refilled = self._run_gate(evaluations, forced=True)
        self.assertIn((True, "forced_sla_recovery_review"), calls)
        gate = result["prepublish_quality_gate"]
        self.assertEqual(gate["publication_mode"], "forced_sla_recovery")
        self.assertEqual(gate["hard_editorial_issue_count"], 0)
        self.assertNotIn(victim, out_sections["policy"])

    def test_forced_recovery_summaries_follow_the_deadline(self):
        with patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", True):
            with patch.object(main, "_prepublish_deadline_reached", return_value=False):
                self.assertTrue(main._daily_summary_allow_openai("2026-09-16"))
            with patch.object(main, "_prepublish_deadline_reached", return_value=True):
                self.assertFalse(main._daily_summary_allow_openai("2026-09-16"))
            self.assertFalse(main._daily_summary_allow_openai())
        with patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", False):
            self.assertTrue(main._daily_summary_allow_openai("2026-09-16"))


class FillerRuleTests(unittest.TestCase):
    def test_person_profile_and_delegation_tour_are_rejected(self):
        profile = _mk("박노봉(익산원예농협 멜론 공선회장) - 농사경력 40년 베테랑, 배움엔 끝이 없다", "supply",
                      "익산원예농협 멜론 공선회장 박노봉 씨는 40년째 멜론 농가를 이끌고 있다.")
        self.assertEqual(main._postbuild_article_reject_reason(profile, "supply"), "person_profile_feature")
        tour = _mk("영등포농협, 일본 동경농업대 방문단에 우리 농산물 유통 현장 소개", "dist",
                   "영등포농협은 방문단에게 하나로마트 농산물 유통 현장을 소개했다.")
        self.assertEqual(main._postbuild_article_reject_reason(tour, "dist"), "visiting_delegation_tour")

    def test_policy_interviews_and_trade_visits_are_kept(self):
        self.assertFalse(main.is_person_profile_feature_context(
            "[인터뷰] 송미령 장관 \"농지조사, 위반 확인 시 곧바로 처분 아냐\"", "농식품부 장관은 농지 조사 결과를 설명했다."))
        self.assertTrue(main.is_person_profile_feature_context(
            "[인터뷰] 공영민 고흥군수 \"2030년 인구 10만, 반드시 실현하겠다\"", ""))
        self.assertFalse(main.is_visiting_delegation_tour_context(
            "베트남 바이어 방문단, 샤인머스캣 20t 수출 계약 체결", "방문단은 산지에서 계약을 체결했다."))


if __name__ == "__main__":
    unittest.main()
