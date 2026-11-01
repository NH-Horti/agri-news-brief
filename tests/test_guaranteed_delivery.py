"""발행 보장·최선 상태 복원·교체안 빈칸 재충원 (2026-10-01).

9/22·10/1 은 본 런과 워치독 복구가 모두 막혀 수동 복구로 07:36·08:17 에 나갔고, 9월 교체안 58건 중
49건은 마무리 가드가 한두 장을 뺐다는 이유로 통째로 기각됐다.
"""
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main

KST = timezone(timedelta(hours=9))


def _mk(title, section="policy", is_core=False, score=10.0):
    link = f"https://news.example.com/{abs(hash(title)) % 10**8}"
    article = main.Article(
        section=section,
        title=title,
        description="",
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 9, 30, 18, 0, tzinfo=KST),
        domain="news.example.com",
        press="언론사",
        norm_key=main.make_norm_key(link, "언론사", main.norm_title_key(title)),
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=score,
        is_core=is_core,
        selection_fit_score=2.0,
    )
    article.summary = f"{title} 요약"
    return article


def _sections():
    return {
        "supply": [_mk(f"공급 기사 {i}", "supply", is_core=i < 2) for i in range(5)],
        "policy": [
            _mk("농식품부, 추석 성수품 109.1% 공급", "policy", is_core=True),
            _mk("추석 계란값 잡는다…농협 공급 2.4배로 확대", "policy", is_core=True),
            _mk("농업소득 짓누르는 경영비…농가 경영안전망 실효성 시험대", "policy"),
            _mk("김선기 KTL 원장 취임…첨단 산업 시험인증 지원 강화", "policy"),
            _mk("청주 내수농협, 계약 재배 농가에 영농자재 지원", "policy"),
        ],
        "dist": [_mk(f"유통 기사 {i}", "dist", is_core=i < 2) for i in range(5)],
        "pest": [_mk(f"병해충 기사 {i}", "pest", is_core=i < 2) for i in range(5)],
    }


def _editorial(issues, score=70.0):
    return {
        "status": "success",
        "score": score,
        "target_score": 82.0,
        "issues": issues,
        "acceptance_gate": {"passed": False, "status": "needs_major_iteration"},
        "scores": {"article_selection": 66, "section_fit": 72, "core": 66, "summary": 90, "missed": 58, "noise": 58},
    }


def _result(editorial, *, overall=88.0, counts=None, reader_samples=None):
    return {
        "overall_score": overall,
        "operational_score": 93.0,
        "reader_quality_score": overall,
        "scores": {"commodity_board_quality": 88.0},
        "counts": {"briefing_by_section": counts or {s: 5 for s in main._section_keys()}},
        "metrics": {"reader_hard_issue_count": len(reader_samples or []), "summary_presence_rate": 1.0},
        "reader_hard_issue_samples": reader_samples or [],
        "editorial": editorial,
    }


BLOCKING = {"type": "off_topic", "severity": "blocking", "section": "policy",
            "title": "김선기 KTL 원장 취임…첨단 산업 시험인증 지원 강화", "reason": "비농업 기관장 취임"}


class _GateHarness(unittest.TestCase):
    def setUp(self):
        main._GATE_EXCISED_LINK_KEYS.clear()
        main._GATE_EXCISED_ARTICLES.clear()
        main._GATE_EXCISION_KEEP_LINK_KEYS.clear()
        main._GATE_RELOCATED_OUT.clear()
        main.OPENAI_USAGE_EVENTS.clear()

    def _run(self, evaluations, *, fake_excise, guarantee=True, extra_patches=(), sections=None):
        calls = []

        def fake_compose(report_date, html_text, snapshot_payload, *, run_editorial, adaptive_reason, achievable_by_section=None):
            calls.append((run_editorial, adaptive_reason))
            return evaluations.pop(0)

        sections = sections or _sections()
        patches = [
            patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", False),
            patch.object(main, "PREPUBLISH_SLA_FALLBACK_ENABLED", True),
            patch.object(main, "PREPUBLISH_QUALITY_FAIL_CLOSED", False),
            patch.object(main, "PREPUBLISH_GUARANTEED_DELIVERY", True),
            patch.object(main, "GUARANTEED_DELIVERY_MIN_TOTAL_CARDS", 8),
            patch.object(main, "PREPUBLISH_MAX_HARD_ISSUE_EXCISIONS", 2),
            patch.object(main, "_OPENAI_QUOTA_EXHAUSTED", False),
            patch.object(main, "_prepublish_deadline_reached", return_value=False),
            patch.object(main, "_should_run_full_editorial_eval", return_value=(True, "deterministic_anomaly")),
            patch.object(main, "_compose_prepublish_evaluation", side_effect=fake_compose),
            patch.object(main, "_excise_flagged_cards_and_refill", side_effect=fake_excise),
            patch.object(main, "_top_up_sections_after_guard", side_effect=lambda s, *a, **k: s),
            patch.object(main, "render_daily_page", return_value="<html>"),
            patch.object(main, "_enrich_editorial_snapshot_source_tiers", return_value=0),
            patch.object(main, "_section_achievable_counts", return_value={s: 20 for s in main._section_keys()}),
            patch.object(main, "_initial_editorial_repair_exclusions", return_value={s: set() for s in main._section_keys()}),
            patch.object(main, "_prepublish_editorial_budget_available", return_value=False),
            patch.object(main, "_prepublish_verification_call_allowed", return_value=True),
            patch.object(main, "_write_prepublish_evaluation_artifacts"),
            patch.object(main, "_notify_quality_hold"),
            patch("report_eval.load_snapshot_payload", return_value={}),
            patch("editorial_eval.propose_editorial_repair", side_effect=AssertionError("repair must not run")),
            *extra_patches,
        ]
        with ExitStack() as stack:
            for cm in patches:
                stack.enter_context(cm)
            out_sections, _html, result = main._run_prepublish_quality_gate(
                "repo", "token", "2026-10-01", datetime(2026, 9, 30, 6, tzinfo=KST), datetime(2026, 10, 1, 6, tzinfo=KST),
                "https://example.test/", ["2026-10-01"], "docs", {}, sections, {}, Path("snapshot.json"),
                guarantee_delivery=guarantee,
            )
        return out_sections, result, calls


class GuaranteedDeliveryTests(_GateHarness):
    def test_remaining_hard_issue_is_removed_and_the_briefing_is_published(self):
        """절제 재충원이 하한에 막혀 hard issue 가 남아도, 보장 발행이 그 카드를 빼고 발행한다(10/1 07:35 재현)."""
        sections = _sections()
        victim = sections["policy"][3]

        def fake_excise(current, raw, targets, cache, *, allow_openai_summaries=True, achievable_by_section=None, enforce_floor=True):
            if enforce_floor:
                return None  # rejected_refill_floor
            ids = {id(t["article"]) for t in targets}
            return {k: [a for a in v if id(a) not in ids] for k, v in current.items()}

        evaluations = [
            _result({"status": "skipped"}),                 # policy probe
            _result(_editorial([BLOCKING]), overall=70.0),   # first editorial
            _result({"status": "skipped"}, counts={"supply": 5, "policy": 4, "dist": 5, "pest": 5}),  # salvage round
            _result({"status": "skipped"}, counts={"supply": 5, "policy": 4, "dist": 5, "pest": 5}),  # salvage final
        ]
        out, result, _calls = self._run(evaluations, fake_excise=fake_excise, sections=sections)
        gate = result["prepublish_quality_gate"]
        self.assertTrue(gate["publishable"])
        self.assertEqual(gate["publication_mode"], "guaranteed_minimum")
        self.assertEqual(gate["status"], "guaranteed_delivery_passed")
        self.assertNotIn(victim, out["policy"])
        self.assertEqual(len(out["policy"]), 4)
        self.assertEqual(gate["hard_editorial_issue_count"], 0)
        self.assertIn("editorial_hard_issues:1", gate["guaranteed_delivery"]["blockers_before"])
        self.assertNotIn("editorial_hard_issues:1", gate["guaranteed_delivery"]["blockers_after"])
        self.assertEqual([r["title"] for r in gate["guaranteed_delivery"]["removed"]], [victim.title])

    def test_thin_section_does_not_block_delivery(self):
        """후보가 있는데 섹션이 얇게 끝나도(9/29 정책 3/4) 발행은 막지 않는다."""
        sections = _sections()
        sections["policy"] = sections["policy"][:3]
        thin = {"supply": 5, "policy": 3, "dist": 5, "pest": 5}
        evaluations = [
            _result({"status": "skipped"}, counts=thin),
            _result(_editorial([], score=74.0), overall=84.0, counts=thin),
            _result({"status": "skipped"}, counts=thin),     # salvage final (no unsafe cards)
        ]
        out, result, _calls = self._run(
            evaluations, fake_excise=lambda *a, **k: None, sections=sections,
        )
        gate = result["prepublish_quality_gate"]
        self.assertEqual(gate["guaranteed_delivery"]["blockers_before"], ["section_underfill:policy=3/4"])
        self.assertEqual(gate["publication_mode"], "guaranteed_minimum")
        self.assertEqual(len(out["policy"]), 3)

    def test_unsafe_reader_issue_card_is_removed(self):
        sections = _sections()
        bad = sections["dist"][4]
        sample = [{"title": bad.title, "section": "dist", "reason": "off_scope_content"}]

        def fake_excise(current, raw, targets, cache, *, allow_openai_summaries=True, achievable_by_section=None, enforce_floor=True):
            if enforce_floor:
                return None
            ids = {id(t["article"]) for t in targets}
            return {k: [a for a in v if id(a) not in ids] for k, v in current.items()}

        evaluations = [
            _result({"status": "skipped"}, reader_samples=sample),
            _result(_editorial([], score=74.0), overall=80.0, reader_samples=sample),
            _result({"status": "skipped"}, counts={"supply": 5, "policy": 5, "dist": 4, "pest": 5}),
            _result({"status": "skipped"}, counts={"supply": 5, "policy": 5, "dist": 4, "pest": 5}),
        ]
        out, result, _calls = self._run(evaluations, fake_excise=fake_excise, sections=sections)
        self.assertEqual(result["prepublish_quality_gate"]["publication_mode"], "guaranteed_minimum")
        self.assertNotIn(bad, out["dist"])

    def test_collection_outage_is_not_published(self):
        sections = {s: [_mk(f"{s} 기사 {i}", s) for i in range(1)] for s in main._section_keys()}
        tiny = {s: 1 for s in main._section_keys()}
        evaluations = [
            _result({"status": "skipped"}, counts=tiny),
            _result(_editorial([], score=60.0), overall=40.0, counts=tiny),
            _result({"status": "skipped"}, counts=tiny),
        ]
        _out, result, _calls = self._run(evaluations, fake_excise=lambda *a, **k: None, sections=sections)
        gate = result["prepublish_quality_gate"]
        self.assertFalse(gate["publishable"])
        self.assertEqual(gate["publication_mode"], "blocked")
        self.assertEqual(gate["guaranteed_delivery"]["total_cards"], 4)

    def test_rebuild_paths_without_the_guarantee_still_block(self):
        evaluations = [
            _result({"status": "skipped"}),
            _result(_editorial([BLOCKING]), overall=70.0),
        ]
        _out, result, _calls = self._run(evaluations, fake_excise=lambda *a, **k: None, guarantee=False)
        gate = result["prepublish_quality_gate"]
        self.assertFalse(gate["publishable"])
        self.assertEqual(gate["guaranteed_delivery"], {})


class BestStateRestoreTests(_GateHarness):
    def test_excision_that_surfaces_a_new_blocker_is_rolled_back(self):
        """절제 재평가가 새 blocking 을 내고 더 고칠 수 없으면, 발행 가능했던 앞 상태를 낸다."""
        sections = _sections()
        dup = sections["dist"][4]
        refill = _mk("성주농협, 조합원 대학생 자녀 장학금 전달", "dist")
        major_dup = {"type": "duplicate_story", "severity": "major", "section": "dist", "title": dup.title, "reason": "중복"}
        new_blocking = {"type": "off_topic", "severity": "blocking", "section": "dist", "title": refill.title, "reason": "장학금"}
        rounds = []

        def fake_excise(current, raw, targets, cache, *, allow_openai_summaries=True, achievable_by_section=None, enforce_floor=True):
            rounds.append([t["title"] for t in targets])
            if len(rounds) > 1:
                return None
            out = {k: list(v) for k, v in current.items()}
            out["dist"] = [a for a in out["dist"] if a is not dup] + [refill]
            return out

        evaluations = [
            _result({"status": "skipped"}),
            _result(_editorial([major_dup], score=72.0), overall=85.0),       # SLA 발행 가능(hard 0)
            _result(_editorial([new_blocking], score=66.0), overall=66.0),    # 절제 후 새 blocking
        ]
        out, result, _calls = self._run(evaluations, fake_excise=fake_excise, guarantee=False, sections=sections)
        gate = result["prepublish_quality_gate"]
        self.assertEqual(gate["restored_best_state"], "initial")
        self.assertTrue(gate["publishable"])
        self.assertEqual(gate["publication_mode"], "sla_fallback")
        self.assertIn(dup, out["dist"])
        self.assertNotIn(refill, out["dist"])
        self.assertEqual(result["overall_score"], 85.0)
        # 되돌린 지면 카드는 뒤 라운드에서 절제됐어도 발행 후 패스가 빼지 않는다.
        self.assertNotEqual(main._postbuild_article_reject_reason(dup, "dist"), "editorial_issue_excised")


class RestoreSafetyTests(_GateHarness):
    def test_restored_state_never_republishes_a_card_a_later_review_called_off_topic(self):
        """편집 판정은 비결정적이다: 앞 평가가 놓친 off_topic 카드를 뒤 평가가 잡았다면, 앞 상태로 되돌려도 뺀다."""
        sections = _sections()
        dup = sections["dist"][4]
        offtopic = sections["supply"][4]
        refill = _mk("성주농협, 조합원 대학생 자녀 장학금 전달", "dist")
        major_dup = {"type": "duplicate_story", "severity": "major", "section": "dist", "title": dup.title, "reason": "중복"}
        late_blocking = [
            {"type": "off_topic", "severity": "blocking", "section": "supply", "title": offtopic.title, "reason": "비농업"},
            {"type": "off_topic", "severity": "blocking", "section": "dist", "title": refill.title, "reason": "장학금"},
        ]
        rounds = []

        def fake_excise(current, raw, targets, cache, *, allow_openai_summaries=True, achievable_by_section=None, enforce_floor=True):
            rounds.append([t["title"] for t in targets])
            if len(rounds) == 1:
                out = {k: list(v) for k, v in current.items()}
                out["dist"] = [a for a in out["dist"] if a is not dup] + [refill]
                return out
            for target in targets:  # 두 번째 라운드: hard 로 지목된 카드를 기록만 하고 하한 때문에 기각
                main._GATE_HARD_FLAGGED_LINK_KEYS.update(main._repair_article_link_keys(target["article"]))
            return None

        evaluations = [
            _result({"status": "skipped"}),
            _result(_editorial([major_dup], score=72.0), overall=85.0),
            _result(_editorial(late_blocking, score=60.0), overall=60.0),
            _result({"status": "skipped"}, counts={"supply": 4, "policy": 5, "dist": 5, "pest": 5}),  # sanitized re-measure
        ]
        main._GATE_HARD_FLAGGED_LINK_KEYS.clear()
        out, result, _calls = self._run(evaluations, fake_excise=fake_excise, guarantee=False, sections=sections)
        gate = result["prepublish_quality_gate"]
        self.assertEqual(gate["restored_best_state"], "initial")
        self.assertNotIn(offtopic, out["supply"])
        self.assertIn(dup, out["dist"])
        main._GATE_HARD_FLAGGED_LINK_KEYS.clear()


class PriceBasisNoteTests(unittest.TestCase):
    def test_mixed_direction_weekly_bulletin_gets_no_basis_note(self):
        bulletin = _mk("[2026년 9월 4주] 주요 농산물 경락가 상승·하락 품목 - 양배추·참외", "supply")
        bulletin.summary = "양배추가 한 주간 115.6% 올랐다."
        other = _mk("양배추 도매가 급락…산지 출하 늘어", "supply")
        other.summary = "양배추 도매가가 내렸다."
        with patch.object(main, "managed_commodity_board_keys_for_article", return_value=["cabbage"]):
            main._clarify_conflicting_price_basis_summaries({"supply": [bulletin, other], "policy": []})
        self.assertNotIn("비교 기준이 다르다", bulletin.summary)


class RepairTopUpTests(_GateHarness):
    def test_repair_is_kept_when_the_final_guard_drops_one_card(self):
        sections = _sections()
        weak = sections["policy"][4]
        missed = _mk("농안법 개정안 시행…마늘·양파 단체 가격 안전망 요구", "policy")
        variant = _mk("농안법 시행 첫날…생산자 단체 가격 안전망 촉구", "policy")
        filler = _mk("정부, 추석 농축산물 할인 지원 900억 추가", "policy")
        repaired = {k: list(v) for k, v in sections.items()}
        repaired["policy"] = [a for a in repaired["policy"] if a is not weak][:3] + [missed, variant]
        major = {"type": "missed_candidate", "severity": "major", "section": "policy", "title": missed.title, "reason": "누락"}
        clean = _editorial([], score=80.0)
        top_up_calls = []

        def fake_finalize(by_section):
            # 같은 사건 매체판 한 장을 빼는 마무리 가드
            if variant in by_section.get("policy", []):
                by_section["policy"] = [a for a in by_section["policy"] if a is not variant]
                return 1
            return 0

        def fake_top_up(sections_in, raw, cache, *, allow_openai_summaries=True, skip_link_keys=None, rounds=2,
                        section_floors=None, prefer_pool=None):
            top_up_calls.append((set(skip_link_keys or set()), dict(section_floors or {}), prefer_pool))
            sections_in["policy"] = list(sections_in["policy"]) + [filler]
            return sections_in

        evaluations = [
            _result({"status": "skipped"}),
            _result(_editorial([major], score=72.0), overall=84.0),
            _result(clean, overall=89.0),
        ]
        extra = (
            patch.object(main, "PREPUBLISH_QUALITY_MAX_REPAIRS", 1),
            patch.object(main, "PREPUBLISH_QUALITY_MAX_PROPOSALS", 2),
            patch.object(main, "_editorial_repair_section_targets", return_value={s: 5 for s in main._section_keys()}),
            patch.object(main, "_prepublish_editorial_budget_available", side_effect=lambda *, reserve_calls=0: True),
            patch.object(main, "_apply_model_editorial_repair", return_value=repaired),
            patch.object(main, "_invalidate_editorial_bad_summary_cache", return_value=[]),
            patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
            patch.object(main, "_finalize_sections_for_render", side_effect=fake_finalize),
            patch.object(main, "_top_up_sections_after_guard", side_effect=fake_top_up),
            patch("editorial_eval.propose_editorial_repair", return_value={"status": "success", "sections": {}, "usage": {}}),
        )
        out, result, _calls = self._run(evaluations, fake_excise=lambda *a, **k: None, guarantee=False,
                                         extra_patches=extra, sections=sections)
        gate = result["prepublish_quality_gate"]
        self.assertEqual(gate["applied_repair_count"], 1)
        self.assertEqual(gate["repair_attempts"][0]["post_finalize_top_up"], {"policy": 1})
        self.assertIn(missed, out["policy"])
        self.assertIn(filler, out["policy"])
        self.assertEqual(len(out["policy"]), 5)
        # 교체안이 뺀 지면 카드는 raw 재충원에서 제외되고, 대신 '직전 지면' 풀로 먼저 넘어간다.
        skip_keys, floors, prefer_pool = top_up_calls[0]
        self.assertTrue(main._repair_article_link_keys(weak) <= skip_keys)
        self.assertEqual(floors["policy"], 5)
        self.assertIn(weak, prefer_pool["policy"])


class RepairVerificationRoomTests(_GateHarness):
    def test_repair_is_not_started_when_its_verification_would_exceed_the_call_cap(self):
        """2026-10-01 하네스: 마지막 호출로 제안한 교체안이 미검증으로 발행됐다 — 검증 자리가 없으면 시작하지 않는다."""
        major = {"type": "missed_candidate", "severity": "major", "section": "policy", "title": "농안법 시행", "reason": "누락"}
        evaluations = [
            _result({"status": "skipped"}),
            _result(_editorial([major], score=72.0), overall=86.0),
        ]
        main.OPENAI_USAGE_EVENTS.extend(
            [{"stage": "editorial_eval", "total_tokens": 10} for _ in range(4)]
        )
        extra = (
            patch.object(main, "PREPUBLISH_EDITORIAL_MAX_CALLS", 5),
            patch.object(main, "PREPUBLISH_QUALITY_MAX_REPAIRS", 2),
            patch.object(main, "PREPUBLISH_QUALITY_MAX_PROPOSALS", 3),
            patch.object(main, "_prepublish_editorial_budget_available", side_effect=lambda *, reserve_calls=0: True),
            patch("editorial_eval.propose_editorial_repair", side_effect=AssertionError("must not propose")),
        )
        _out, result, _calls = self._run(evaluations, fake_excise=lambda *a, **k: None, guarantee=False, extra_patches=extra)
        gate = result["prepublish_quality_gate"]
        self.assertEqual(gate["repair_count"], 0)
        self.assertEqual(gate["publication_mode"], "sla_fallback")


class SummaryFactualErrorTests(unittest.TestCase):
    def setUp(self):
        main._GATE_SUMMARY_FIXED_LINK_KEYS.clear()

    def test_first_factual_error_swaps_in_the_source_lead_then_second_one_is_excisable(self):
        """9/29 주간 경락가 동향: 요약이 시작가를 평균가로 썼다 — 카드를 빼지 말고 요약을 원문 리드로 바꾼다."""
        sections = _sections()
        bulletin = _mk("[2026년 9월 5주] 주요 농산물 경락가 상승·하락 품목 - 쌈배추·단감", "supply", is_core=True)
        bulletin.description = "가락시장 주간 경락가를 보면 쌈배추가 3503원에서 8611원으로 145.8% 올랐고 단감·송이는 내렸다."
        bulletin.summary = "쌈배추 평균가 3503원으로 전년 대비 산지가격이 올랐다."
        sections["supply"][0] = bulletin
        issue = {"type": "factual_error", "severity": "blocking", "section": "supply",
                 "title": "[2026년 9월 5주] 주요 농산물 경락가 상승·하락 품목 - 쌈배추·...", "reason": "시작가를 평균가로 씀"}
        cache = {bulletin.norm_key: {"s": bulletin.summary, "t": "x"}}
        fixes = main._replace_flagged_summaries_with_source_text({"issues": [issue]}, sections, cache)
        self.assertEqual([f["article"] for f in fixes], [bulletin])
        self.assertIn("8611원", bulletin.summary)
        self.assertEqual(cache[bulletin.norm_key]["s"], bulletin.summary)
        # 같은 카드가 다시 지적되면 고치지 않는다(그때는 절제 대상)
        self.assertEqual(main._replace_flagged_summaries_with_source_text({"issues": [issue]}, sections, cache), [])
        targets = main._editorial_excision_targets({"issues": [issue]}, sections)
        self.assertEqual([t["article"] for t in targets], [bulletin])


class TopUpHelperTests(unittest.TestCase):
    def test_top_up_refills_until_no_progress_and_skips_dropped_cards(self):
        sections = _sections()
        sections["policy"] = sections["policy"][:3]
        dropped = _mk("교체안이 뺀 카드", "policy")
        seen_skip = []

        def fake_recover(final, raw, *, max_items=None):
            seen_skip.append(set(main._GATE_REFILL_SKIP_LINK_KEYS))
            reason = main._postbuild_article_reject_reason(dropped, "policy")
            self.assertEqual(reason, "editorial_repair_dropped")
            if len(final["policy"]) < 5:
                final["policy"] = list(final["policy"]) + [_mk(f"보충 {len(final['policy'])}", "policy")]
            return 1

        with ExitStack() as stack:
            for cm in (
                patch.object(main, "_recover_preferred_section_counts_from_raw", side_effect=fake_recover),
                patch.object(main, "_final_global_story_dedupe", return_value=(0, 0)),
                patch.object(main, "_cap_final_low_tier_sources", return_value=0),
                patch.object(main, "_ensure_final_selection_fit", return_value=0),
                patch.object(main, "_demote_soft_news_final_cores", return_value=0),
                patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
                patch.object(main, "_finalize_sections_for_render", return_value=0),
            ):
                stack.enter_context(cm)
            out = main._top_up_sections_after_guard(
                sections, {}, {}, skip_link_keys=main._repair_article_link_keys(dropped), rounds=3
            )
        self.assertEqual(len(out["policy"]), 5)
        self.assertEqual(len(seen_skip), 2)  # 3장→4장→5장, 꽉 차면 멈춤
        self.assertEqual(main._GATE_REFILL_SKIP_LINK_KEYS, set())  # 재충원이 끝나면 비운다
        self.assertEqual(main._postbuild_article_reject_reason(dropped, "policy") == "editorial_repair_dropped", False)

    def test_top_up_only_fills_sections_below_their_floor_and_prefers_vetted_cards(self):
        sections = _sections()
        sections["policy"] = sections["policy"][:4]
        sections["pest"] = sections["pest"][:3]
        vetted = _mk("직전 지면 정책 카드", "policy")
        page_twin = _mk("농식품부, 추석 성수품 109.1% 공급", "policy")  # 지면 카드와 같은 기사
        recover_calls = []

        def fake_recover(final, raw, *, max_items=None):
            recover_calls.append(1)
            for key in final:
                final[key] = list(final[key]) + [_mk(f"raw {key} {len(final[key])}", key)]
            return 4

        with ExitStack() as stack:
            for cm in (
                patch.object(main, "_recover_preferred_section_counts_from_raw", side_effect=fake_recover),
                patch.object(main, "_final_global_story_dedupe", return_value=(0, 0)),
                patch.object(main, "_cap_final_low_tier_sources", return_value=0),
                patch.object(main, "_ensure_final_selection_fit", return_value=0),
                patch.object(main, "_demote_soft_news_final_cores", return_value=0),
                patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
                patch.object(main, "_finalize_sections_for_render", return_value=0),
            ):
                stack.enter_context(cm)
            out = main._top_up_sections_after_guard(
                sections, {}, {},
                section_floors={"supply": 5, "policy": 5, "dist": 5, "pest": 3},
                prefer_pool={"policy": [page_twin, vetted]},
            )
        # 정책은 직전 지면 카드로 채워져 raw 체인이 돌지 않고, 하한을 이미 채운 pest(3)는 늘리지 않는다.
        self.assertEqual(recover_calls, [])
        self.assertIn(vetted, out["policy"])
        self.assertNotIn(page_twin, out["policy"][4:])
        self.assertEqual(len(out["policy"]), 5)
        self.assertEqual(len(out["pest"]), 3)


if __name__ == "__main__":
    unittest.main()
