"""겨울철처럼 섹션 후보 풀이 말랐을 때 브리핑 발송이 통째로 막히지 않게 하는 규칙.

2026-01 pest 지면은 평균 0.3장이었는데 지금 게이트는 정상 4장·강제 복구 3장을 고정으로 요구해
그런 날은 어떤 자동 경로로도 발송되지 않는다. 반면 후보가 충분한데 파이프라인이 섹션을 비운 날
(2026-09-22 새벽: 유효 7건에 지면 1장)은 그대로 차단돼야 한다.

- 게이트 최소치 = min(고정 최소치, 유효 후보 수 achievable). 정상 통과(5장)도 같은 상한을 쓴다.
- 심판(report_eval)의 기대 카드 수도 achievable 로 상한을 걸어 불가능한 슬롯 감점을 없앤다.
- 선정: 섹션이 채움 하한(THIN_SECTION_TAIL_FILL_FLOOR, 기본 3)에 못 미치면 raw 크기와 무관하게
  약한 tail 차단을 유보하되, 그렇게 들어온 카드는 하한 위로는 채우지 않는다.
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main
import report_eval

KST = timezone(timedelta(hours=9))


def _mk(section, title, *, press="테스트신문", domain="example.com", score=10.0, fit=2.0, is_core=False):
    link = f"https://{domain}/{section}/{abs(hash(title)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description="가격 물량 정책 유통 병해충 현장 대응",
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 1, 15, 16, 0, tzinfo=KST),
        domain=domain,
        press=press,
        norm_key=main.make_norm_key(link, press, main.norm_title_key(title)),
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=score,
        is_core=is_core,
        selection_fit_score=fit,
    )


def _result(section_counts, achievable=None, *, score=90.0, hard_issues=0):
    result = {
        "operational_score": score,
        "overall_score": score,
        "reader_quality_score": score,
        "counts": {"briefing_by_section": dict(section_counts)},
        "metrics": {"reader_hard_issue_count": hard_issues, "summary_presence_rate": 1.0},
        "scores": {"commodity_board_quality": 95.0},
        "editorial": {"status": "skipped"},
    }
    if achievable is not None:
        result["counts"]["achievable_briefing_by_section"] = dict(achievable)
    return result


class TestAchievableCounts(unittest.TestCase):
    def test_counts_distinct_valid_candidates_and_excludes_cards_used_elsewhere(self):
        a = _mk("pest", "월동 병해충 방제 당부")
        b = _mk("pest", "과수 동계 전정 후 병해충 관리")
        broken = _mk("pest", "본문 깨진 기사")
        dup = _mk("pest", "월동 병해충 방제 당부")  # 같은 identity
        shared = _mk("pest", "정책 지면에 이미 실린 재해복구비 기사")
        raw = {"pest": [a, b, broken, dup], "supply": [], "policy": [], "dist": []}
        current = {"pest": [shared], "policy": [shared], "supply": [], "dist": []}

        def _reject(article, section, *, apply_selection_fit=True):
            return "pest_partial_mention" if article is broken else ""

        with patch.object(main, "_postbuild_article_reject_reason", side_effect=_reject):
            counts = main._section_achievable_counts(raw, current)
        self.assertEqual(counts["pest"], 2)
        self.assertEqual(counts["supply"], 0)


class TestGateMinimumsFollowThePool(unittest.TestCase):
    def test_minimum_is_capped_by_achievable(self):
        result = _result({"pest": 2, "supply": 5, "policy": 5, "dist": 5}, {"pest": 2, "supply": 40, "policy": 30, "dist": 20})
        minimums = main._prepublish_section_minimums(result, 4)
        self.assertEqual(minimums, {"supply": 4, "policy": 4, "dist": 4, "pest": 2})
        self.assertEqual(main._prepublish_thin_pool_sections(result, 4), {"pest": {"achievable": 2, "fixed_minimum": 4, "cards": 2}})
        # 옛 평가 JSON(achievable 없음)은 고정 최소치 그대로.
        self.assertEqual(main._prepublish_section_minimums(_result({"pest": 2}), 4)["pest"], 4)

    def test_thin_pool_section_does_not_block_sla_fallback(self):
        thin = _result({"pest": 2, "supply": 5, "policy": 5, "dist": 5}, {"pest": 2, "supply": 40, "policy": 30, "dist": 20})
        with patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", False):
            self.assertEqual(main._prepublish_sla_fallback_blockers(thin), [])
        empty = _result({"pest": 0, "supply": 5, "policy": 5, "dist": 5}, {"pest": 0, "supply": 40, "policy": 30, "dist": 20})
        with patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", False):
            self.assertEqual(main._prepublish_sla_fallback_blockers(empty), [])

    def test_wiped_section_with_healthy_pool_still_blocks(self):
        # 2026-09-22 새벽: 유효 후보 7건인데 지면은 1장 → 파이프라인 결함이므로 차단 유지.
        wiped = _result({"pest": 1, "supply": 5, "policy": 5, "dist": 5}, {"pest": 7, "supply": 40, "policy": 30, "dist": 20})
        with patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", False):
            self.assertEqual(main._prepublish_sla_fallback_blockers(wiped), ["section_underfill:pest=1/4"])
        with patch.object(main, "PREPUBLISH_FORCE_SLA_FALLBACK", True):
            self.assertEqual(main._prepublish_sla_fallback_blockers(wiped), ["section_underfill:pest=1/3"])

    def test_normal_pass_accepts_thin_pool_section(self):
        thin = _result({"pest": 2, "supply": 5, "policy": 5, "dist": 5}, {"pest": 2, "supply": 40, "policy": 30, "dist": 20}, score=96.0)
        self.assertTrue(main._operational_quality_publishable(thin))
        wiped = _result({"pest": 2, "supply": 5, "policy": 5, "dist": 5}, {"pest": 7, "supply": 40, "policy": 30, "dist": 20}, score=96.0)
        self.assertFalse(main._operational_quality_publishable(wiped))


class TestEvaluatorExpectedCountFollowsThePool(unittest.TestCase):
    def _surface(self, section, idx, is_core=False):
        return report_eval.SurfaceArticle(
            tag="li", surface=report_eval.BRIEFING_SURFACE, section=section, title=f"{section} 기사 {idx}",
            href=f"https://example.com/{section}/{idx}", article_id=f"{section}-{idx}", domain="example.com",
            summary="요약입니다. 가격과 물량 정보가 있습니다.", is_core=is_core, press_tier=2,
        )

    def test_expected_by_section_removes_impossible_slot_penalty(self):
        articles = []
        for section in ("supply", "policy", "dist"):
            articles.extend(self._surface(section, i, is_core=i < 2) for i in range(5))
        articles.extend(self._surface("pest", i, is_core=i < 1) for i in range(2))
        snapshot = {"report_date": "2026-01-15", "window": {}, "raw_by_section": {
            "supply": [{}] * 40, "policy": [{}] * 30, "dist": [{}] * 20, "pest": [{}] * 11,
        }}
        with patch.object(report_eval, "parse_report_html", return_value=articles):
            plain = report_eval.evaluate_report("2026-01-15", "<html></html>", snapshot)
            capped = report_eval.evaluate_report("2026-01-15", "<html></html>", snapshot, expected_by_section={"pest": 2})
        self.assertEqual(plain["counts"]["expected_briefing_by_section"]["pest"], 5)
        self.assertEqual(capped["counts"]["expected_briefing_by_section"]["pest"], 2)
        self.assertGreater(capped["scores"]["completeness"], plain["scores"]["completeness"])
        self.assertGreater(capped["overall_score"], plain["overall_score"])
        # 후보가 충분한 섹션의 기대치는 그대로다.
        self.assertEqual(capped["counts"]["expected_briefing_by_section"]["supply"], 5)


class TestThinSectionTailFill(unittest.TestCase):
    def _weak_notice(self):
        return _mk("pest", "OO시, 월동 병해충 방제 당부", press="인터넷신문", domain="t1.example.com")

    def test_weak_tail_allowed_below_floor_regardless_of_raw_size(self):
        article = self._weak_notice()
        with patch.object(main, "_is_weak_pest_tail", return_value=True), \
                patch.object(main, "_is_generic_pest_notice_tail", return_value=True):
            # raw 11행(중복 포함)이라 예전 규칙(raw<5)으로는 유보되지 않던 경우.
            self.assertEqual(main._preferred_tail_block_reason(article, "pest", current_count=1, raw_count=11), "")
            self.assertEqual(
                main._preferred_tail_block_reason(article, "pest", current_count=main.THIN_SECTION_TAIL_FILL_FLOOR, raw_count=11),
                "pest_weak_notice_tail",
            )

    def test_refill_uses_weak_tails_only_up_to_the_floor(self):
        strong = _mk("pest", "사과 탄저병 확산…농가 방제 비상", domain="t2.example.com", score=20.0)
        weak = [_mk("pest", f"OO군, 월동 병해충 방제 당부 {i}", domain="t2.example.com", score=5.0 + i) for i in range(4)]
        final = {"pest": [], "supply": [], "policy": [], "dist": []}
        raw = {"pest": [strong] + weak + [_mk("pest", f"중복 {i}") for i in range(6)], "supply": [], "policy": [], "dist": []}

        def _tail(article, section, *, current_count, raw_count):
            if article is strong:
                return ""
            thin = current_count < main.THIN_SECTION_TAIL_FILL_FLOOR
            return "" if thin else "pest_weak_notice_tail"

        pest_conf = next(s for s in main.SECTIONS if s.get("key") == "pest")
        with patch.object(main, "_preferred_tail_block_reason", side_effect=_tail), \
                patch.object(main, "_preferred_section_rank", side_effect=lambda sec, a, conf: (float(a.score),)), \
                patch.object(main, "_postbuild_article_reject_reason", return_value=""), \
                patch.object(main, "is_relevant", return_value=True), \
                patch.object(main, "_candidate_conflicts_with_final", return_value=False), \
                patch.object(main, "_pest_direct_gap_rank", return_value=None), \
                patch.object(main, "_is_pest_direct_gap_story", return_value=False), \
                patch.object(main, "is_pest_national_fire_blight_escalation_context", return_value=False):
            inserted = main._recover_preferred_section_counts_from_raw(final, raw, max_items=5)
        titles = [a.title for a in final["pest"]]
        self.assertEqual(inserted, main.THIN_SECTION_TAIL_FILL_FLOOR)
        self.assertEqual(titles[0], strong.title)
        self.assertEqual(len(titles), main.THIN_SECTION_TAIL_FILL_FLOOR)


if __name__ == "__main__":
    unittest.main()
