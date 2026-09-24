"""P7·P8: 도매시세 리포트가 유통 지면에 남는지, 편집 평가가 주마다 최소 한 번은
같은 잣대로 돌아가는지 검증한다.

배경(2026-08 주간):
- 08-12 에 편집이 누락으로 지적한 '[한눈에 보는 시세] 여름사과 출하 마무리'는
  후보 풀에 있었지만 '수급 가격 기사'로 분류돼 유통에서 거부됐다. 편집 지침은
  유통 우선순위를 도매시세 → 정산 → 파업 → 물류 → 판매채널 순으로 둔다.
- 08-10(월)은 SLA 복구 모드가 주간 감사보다 먼저 걸려 편집 평가가 아예 돌지
  않았고, 08-13 은 교체안이 예산을 다 써 모델 재평가 없이 발행됐다.
"""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main  # noqa: E402


class DistWholesalePriceTests(unittest.TestCase):
    WHOLESALE = (
        (
            "[한눈에 보는 시세] 여름사과 출하 마무리…물량 줄면서 가격 회복세",
            "가락시장 여름사과 반입 물량이 줄면서 도매가격이 회복세를 보이고 있다.",
        ),
        (
            "가락시장 배추 경락가 20% 하락…반입 물량 증가",
            "가락시장 배추 반입 물량이 늘면서 경락가가 하락했다.",
        ),
    )
    NOT_WHOLESALE = (
        (
            "폭염에 채소값 급등…밥상물가 비상",
            "폭염으로 채소 소매가격이 올라 장바구니 부담이 커졌다.",
        ),
        (
            "배추 산지 폐기 확대…가격 폭락에 갈아엎는 농가",
            "배추 가격 폭락으로 산지 폐기가 늘고 있다.",
        ),
    )

    def test_wholesale_price_report_is_recognised(self) -> None:
        for title, desc in self.WHOLESALE:
            with self.subTest(title=title):
                self.assertTrue(main.is_dist_wholesale_price_report(title, desc))

    def test_wholesale_price_report_is_not_a_supply_squatter(self) -> None:
        for title, desc in self.WHOLESALE:
            with self.subTest(title=title):
                self.assertFalse(main.is_dist_primary_supply_price_story(title, desc))

    def test_retail_and_field_loss_stories_are_still_excluded(self) -> None:
        for title, desc in self.NOT_WHOLESALE:
            with self.subTest(title=title):
                self.assertFalse(main.is_dist_wholesale_price_report(title, desc))
        self.assertTrue(main.is_dist_primary_supply_price_story(*self.NOT_WHOLESALE[1]))


class EditorialCadenceTests(unittest.TestCase):
    def test_weekly_audit_day_is_monday(self) -> None:
        self.assertTrue(main._weekly_editorial_audit_due("2026-08-10"))  # 월
        self.assertFalse(main._weekly_editorial_audit_due("2026-08-14"))  # 금
        self.assertTrue(main._weekly_editorial_audit_due("not-a-date"))

    CLEAN_RESULT = {
        "operational_score": 96.0,
        "reader_quality_score": 95.0,
        "counts": {"briefing_by_section": {"supply": 5, "policy": 5, "dist": 5, "pest": 5}},
        "scores": {"commodity_board_quality": 98.0},
        "metrics": {
            "reader_hard_issue_count": 0,
            "summary_presence_rate": 1.0,
            "low_tier_source_excess_count": 0,
            "content_false_positive_rate": 0.0,
            "promotional_filler_rate": 0.0,
            "pest_theme_duplicate_rate": 0.0,
        },
    }

    def test_clean_day_is_not_treated_as_an_anomaly(self) -> None:
        self.assertFalse(main._operational_quality_anomaly(dict(self.CLEAN_RESULT)))

    def test_adaptive_decision_still_flags_the_audit_day(self) -> None:
        run, reason = main._should_run_full_editorial_eval(
            "repo", "token", "2026-08-10", dict(self.CLEAN_RESULT)
        )
        self.assertTrue(run)
        self.assertEqual(reason, "weekly_monday_audit")


class EditorialBudgetReservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = list(main.OPENAI_USAGE_EVENTS)
        main.OPENAI_USAGE_EVENTS.clear()

    def tearDown(self) -> None:
        main.OPENAI_USAGE_EVENTS.clear()
        main.OPENAI_USAGE_EVENTS.extend(self._saved)

    def test_fresh_run_can_fund_a_repair_and_its_verification(self) -> None:
        self.assertTrue(main._prepublish_editorial_budget_available(reserve_calls=1))

    def test_reservation_reports_when_a_verification_would_not_fit(self) -> None:
        spend = max(1, main.PREPUBLISH_EDITORIAL_TOKEN_BUDGET // 3 + 1)
        main.OPENAI_USAGE_EVENTS.append({"stage": "editorial_eval", "total_tokens": spend})
        # 교체안 자체는 아직 가능하지만, 그 뒤 재평가까지는 예산이 모자란다.
        self.assertTrue(main._prepublish_editorial_budget_available())
        self.assertFalse(main._prepublish_editorial_budget_available(reserve_calls=1))

    def test_call_ceiling_is_respected_by_the_reservation(self) -> None:
        for _ in range(main.PREPUBLISH_EDITORIAL_MAX_CALLS - 1):
            main.OPENAI_USAGE_EVENTS.append({"stage": "editorial_eval", "total_tokens": 1})
        self.assertTrue(main._prepublish_editorial_budget_available())
        self.assertFalse(main._prepublish_editorial_budget_available(reserve_calls=1))


if __name__ == "__main__":
    unittest.main()
