import unittest
from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import patch

import main
import report_eval
from editorial_rules import export_ceremony_filler, policy_issue_key, remote_weather_feature
from scripts.evaluate_daily_report import apply_editorial_quality_gate
from scripts import review_weekly_briefings


def article(title, body="", section="policy", idx=1):
    url = f"https://www.yna.co.kr/view/{idx}"
    return main.Article(
        section=section, title=title, description=body, link=url, originallink=url,
        pub_dt_kst=datetime(2026, 8, 28, 6, tzinfo=main.KST), domain="yna.co.kr",
        press="연합뉴스", norm_key=url, title_key=main.norm_title_key(title),
        canon_url=url, topic="", score=20.0,
    )


class WeeklyEditorialGuardsTests(unittest.TestCase):
    def test_policy_theme_cap_handles_crop_free_headlines_and_refill(self):
        cards = [article(title, idx=i) for i, title in enumerate((
            "농식품부 CPTPP 가입 입장 발표", "여야 CPTPP 가입 논쟁", "CPTPP 가입 논의 착수",
        ))]
        final = {"policy": cards, "supply": [], "dist": [], "pest": []}
        main._final_global_story_dedupe(final)
        self.assertEqual(len(final["policy"]), 1)
        self.assertTrue(main._violates_section_theme_cap(cards[1], "policy", final))
        self.assertFalse(main._violates_section_theme_cap(article("농안법 시행, 가격 하락분 보전"), "policy", final))
        self.assertEqual(policy_issue_key("농안법 시행, 가격 하락분 보전"), "")
        self.assertEqual(policy_issue_key("역내포괄적경제동반자협정 관세 협의"), "rcep")

    def test_remote_weather_preserves_domestic_market_link(self):
        title = "벨기에 감자는 탁구공 크기, 프랑스선 악어 자연부화"
        body = "유럽 폭염에 감자 흉작. 연간 600만톤을 가공하고 90%를 수출한다."
        self.assertTrue(remote_weather_feature(title, body))
        self.assertFalse(remote_weather_feature(title, body + " 국내 냉동감자 수입 가격이 20% 상승했다."))
        card = article(title, body, "supply")
        self.assertEqual(main._postbuild_article_reject_reason(card, "supply"), "remote_weather_feature")
        surface = report_eval.SurfaceArticle(tag="div", surface="briefing_card", section="supply", title=title,
                                             href=card.link, article_id="1", domain=card.domain)
        self.assertEqual(report_eval._reader_hard_issue_reason(surface, body), "remote_weather_feature")

    def test_shipment_quantity_does_not_exempt_ceremony(self):
        title = "장성군, 샤인머스캣 4톤 대만 첫 수출"
        body = "상차식을 열었다. 4톤을 선적하고 판로 확대와 수출액 증가를 기대했다."
        self.assertTrue(export_ceremony_filler(title, body))
        self.assertFalse(export_ceremony_filler(title, body + " 전년보다 수출액이 30% 증가했다."))
        self.assertFalse(export_ceremony_filler(title, body + " 검역 요건 변경에 따른 통관 지연을 해결했다."))
        self.assertFalse(export_ceremony_filler("배 수출 20% 감소, 물류 차질", "수출 감소로 농가 피해"))
        self.assertEqual(main._postbuild_article_reject_reason(article(title, body, "dist"), "dist"),
                         "promotional_or_event_filler")
        # A standing supply channel or a large first shipment is market information, not filler.
        self.assertFalse(export_ceremony_filler("임실 풋고추, 일본 첫 수출 개시…매주 2톤 공급한다",
                                                "첫 수출 상차식을 열었다. 앞으로 매주 1.5~2톤을 공급한다."))
        self.assertFalse(export_ceremony_filler("올해산 아산배 미국 첫 수출…조생종 원황 47t",
                                                "첫 수출 선적식을 열고 47t을 선적했다."))
        self.assertTrue(export_ceremony_filler("남원시, 캠벨포도 10톤 베트남 첫 수출…브랜드 인지도 제고",
                                               "첫 수출 기념식을 열고 10톤을 선적했다."))

    def test_evaluator_counts_policy_theme_duplicates(self):
        titles = ("농식품부 CPTPP 입장", "여야 CPTPP 논쟁", "CPTPP 논의 착수")
        html = "".join(
            f'<div data-surface="briefing_card" data-section="policy" data-article-title="{title}" '
            f'data-href="https://example.com/{i}" data-article-id="{i}">'
            '<div class="sum">농업 분야 협상 쟁점과 대응 방침을 발표했다.</div></div>'
            for i, title in enumerate(titles)
        )
        result = report_eval.evaluate_report("2026-08-28", html, {"report_date": "2026-08-28", "raw_by_section": {}})
        self.assertEqual(result["metrics"]["policy_theme_duplicate_count"], 2)
        self.assertIn("policy_theme_duplicate", result["reader_quality_gate"]["reasons"])
        self.assertTrue(main._operational_quality_anomaly(result))

    def test_failed_acceptance_cannot_be_a_pass_despite_high_score(self):
        result = {"overall_score": 99.0, "operational_score": 99.0, "status": "pass"}
        apply_editorial_quality_gate(result, {
            "status": "success", "score": 94, "target_score": 88, "target_status": "target_met",
            "acceptance_gate": {"passed": False, "failure_reasons": ["no_major_issues"]},
            "issues": [{"severity": "major", "type": "duplicate_theme"}],
        })
        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["quality_gate"]["status"], "needs_iteration")

    def test_weekly_review_refuses_repeat_before_starting_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "manifest.json").write_text('{}', encoding="utf-8")
            argv = ["review", "--start", "2026-08-24", "--end", "2026-08-28",
                    "--output", directory, "--finalize"]
            with patch("sys.argv", argv), patch.object(review_weekly_briefings.subprocess, "run") as run:
                with self.assertRaises(SystemExit) as error:
                    review_weekly_briefings.main()
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()

    def test_weekly_review_requires_explicit_final_stage(self):
        with patch("sys.argv", ["review", "--output", "unused"]):
            with self.assertRaises(SystemExit) as error:
                review_weekly_briefings.main()
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
