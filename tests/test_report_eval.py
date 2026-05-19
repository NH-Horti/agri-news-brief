import unittest
from html import escape
from pathlib import Path

import report_eval


ROOT = Path(__file__).resolve().parents[1]


class ReportEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report_date = "2026-04-10"
        cls.html_text = (ROOT / "docs" / "archive" / f"{cls.report_date}.html").read_text(encoding="utf-8")
        cls.snapshot_payload = report_eval.load_snapshot_payload(
            ROOT / "docs" / "replay" / f"{cls.report_date}.snapshot.json"
        )

    def test_parse_report_html_extracts_briefing_cards_and_summaries(self) -> None:
        articles = report_eval.parse_report_html(self.html_text)
        briefing = [article for article in articles if article.surface == report_eval.BRIEFING_SURFACE]
        commodity = [article for article in articles if article.surface in report_eval.COMMODITY_SURFACES]

        self.assertEqual(len(briefing), 15)
        self.assertGreater(len(commodity), 20)
        self.assertTrue(any(article.is_core for article in briefing))
        self.assertTrue(all(article.summary.strip() for article in briefing))

    def test_parse_report_html_extracts_commodity_primary_metadata(self) -> None:
        html = """
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="양파 가격 폭락 우려"
          data-article-id="abc123"
          data-target-domain="example.com"
          data-item-key="onion"
          data-item-label="양파"
          data-representative-rank="4"
          data-representative-score="123.4"
          data-board-score="88.2"
          data-selection-fit="1.55"
          data-selection-stage="core_final"
          data-is-core="1"
          href="https://example.com/onion-core"
        >link</a>
        """

        articles = report_eval.parse_report_html(html)
        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article.item_key, "onion")
        self.assertEqual(article.item_label, "양파")
        self.assertEqual(article.representative_rank, 4)
        self.assertAlmostEqual(article.selection_fit_score, 1.55)
        self.assertEqual(article.selection_stage, "core_final")
        self.assertTrue(article.is_core)

    def test_parse_report_html_extracts_briefing_selection_metadata(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="양파 가격 폭락 우려"
          data-href="https://example.com/onion-core"
          data-article-id="brief123"
          data-target-domain="example.com"
          data-selection-fit="1.72"
          data-selection-stage="core_final"
          data-is-core="1"
        >
          <span class="badgeCore">핵심</span>
          <div class="sum">양파 가격과 산지 출하 조절을 다룬 기사다.</div>
        </div>
        """

        article = report_eval.parse_report_html(html)[0]

        self.assertTrue(article.is_core)
        self.assertAlmostEqual(article.selection_fit_score, 1.72)
        self.assertEqual(article.selection_stage, "core_final")

    def test_evaluate_report_returns_scores_and_feedback(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)

        self.assertEqual(result["counts"]["briefing_total"], 15)
        self.assertIn(result["status"], {"pass", "warn", "fail"})
        self.assertGreaterEqual(result["overall_score"], 0.0)
        self.assertLessEqual(result["overall_score"], 100.0)
        self.assertTrue(result["improvement_hints"])
        self.assertTrue(result["summary_prompt_feedback"])
        self.assertIn("selection_guardrails", result)
        self.assertIn("summary_quality", result["scores"])
        self.assertIn("section_alignment", result["scores"])
        self.assertIn("core_quality", result["scores"])
        self.assertIn("commodity_board_quality", result["scores"])

    def test_evaluate_report_tunes_foreign_scope_and_story_duplicate_guardrails(self) -> None:
        items = [
            (
                "supply",
                "평창군, 908개 농가에 농산물 가격안정 기금 21억 지원",
                "평창군은 농산물 가격안정 기금 21억을 908개 농가에 지급해 산지 수급 불안을 완화한다. 농가 경영비 부담과 출하 조절 여건을 함께 짚었다.",
                "https://source0.example.com/supply-pyeongchang",
            ),
            (
                "policy",
                "평창군, 농축산물 가격 안정 기금 21억 지원 908농가 숨통",
                "평창군은 농축산물 가격 안정 기금 21억을 908개 농가에 지급해 농가 경영 부담을 낮춘다. 산지 수급과 가격 안정 효과를 같은 사건으로 다뤘다.",
                "https://source1.example.com/policy-pyeongchang",
            ),
            (
                "policy",
                "한국향 두리안 수출 262% 급증에도 베트남 농가 울상",
                "베트남 현지 두리안 농가가 수출 가격 하락과 재고 부담을 호소했다. 한국향 물량 증가에도 현지 산지 수익성이 악화됐다는 내용이다.",
                "https://source2.example.com/vietnam-durian",
            ),
        ]
        section_counts = {"supply": 6, "policy": 4, "dist": 3, "pest": 2}
        filler_templates = {
            "supply": [
                ("사과 산지 출하 조절로 도매시장 가격 안정 기대", "사과 산지 출하량과 저장 물량 조절이 수급 안정에 영향을 준다. 도매시장 반입 흐름과 농가 출하 전략을 수치와 함께 설명했다."),
                ("양파 재배면적 감소 전망에 산지 수급 점검", "양파 재배면적 감소 전망이 나오자 산지 수급과 저장 물량 점검이 이어졌다. 농가 출하 시점과 가격 변동 가능성을 다뤘다."),
                ("배추 봄작형 작황 회복으로 출하량 증가 예상", "배추 봄작형 작황이 회복되며 출하량 증가가 예상된다. 산지 기상 변수와 도매시장 가격 안정 흐름을 함께 정리했다."),
                ("토마토 시설농가 난방비 부담에 출하 조절 검토", "토마토 시설농가가 난방비 부담으로 출하 조절을 검토한다. 농가 비용과 시장 공급량 변화가 가격에 미칠 영향을 짚었다."),
                ("마늘 산지 저장 물량 감소로 수급 관리 강화", "마늘 산지 저장 물량이 줄어 수급 관리 필요성이 커졌다. 농협과 지자체의 출하 조절 논의가 가격 안정 변수로 제시됐다."),
            ],
            "policy": [
                ("농식품부, 채소류 가격 안정 대책 점검", "농식품부가 채소류 가격 안정과 산지 출하 상황을 점검했다. 농가 지원과 도매시장 반입 관리가 정책 대응의 핵심으로 제시됐다."),
                ("지자체 농산물 수급 협의회 열고 출하 계획 조율", "지자체가 농산물 수급 협의회를 열고 출하 계획을 조율했다. 농가와 유통 주체가 가격 안정 방안을 함께 논의했다."),
            ],
            "dist": [
                ("가락시장 배추 반입 증가로 경락가 안정세", "가락시장 배추 반입량이 늘며 경락가 변동 폭이 줄었다. 도매시장 거래 물량과 유통 흐름을 중심으로 가격 안정세를 설명했다."),
                ("도매시장 사과 거래량 회복에 유통업계 주목", "도매시장 사과 거래량이 회복되며 유통업계가 가격 흐름을 주시한다. 산지 출하와 소매 수요 변화가 함께 언급됐다."),
                ("청과 유통업체, 딸기 물량 분산 출하 확대", "청과 유통업체가 딸기 물량을 분산 출하하며 가격 변동을 줄이려 한다. 산지 물류와 소비지 반입 일정을 함께 조정했다."),
            ],
            "pest": [
                ("과수화상병 예찰 강화로 농가 방제 당부", "지자체가 과수화상병 예찰과 농가 방제 수칙 준수를 당부했다. 과수 농가 피해 예방과 조기 신고 체계가 핵심 내용이다."),
                ("고추 탄저병 확산 우려에 병해충 방제 지도", "고추 탄저병 확산 우려가 커지며 병해충 방제 지도가 강화됐다. 농가 재배 관리와 약제 살포 시점이 함께 안내됐다."),
            ],
        }
        for section, target in section_counts.items():
            current = sum(1 for item in items if item[0] == section)
            fillers = filler_templates[section]
            for idx in range(current, target):
                base_title, base_desc = fillers[idx - current]
                items.append(
                    (
                        section,
                        base_title,
                        base_desc,
                        f"https://source{len(items)}.example.com/{section}-{idx}",
                    )
                )

        html = "\n".join(
            f"""
            <div
              data-surface="briefing_card"
              data-section="{section}"
              data-article-title="{escape(title)}"
              data-href="{href}"
              data-article-id="brief-{idx}"
              data-target-domain="example.com"
              data-selection-fit="1.65"
              data-selection-stage="core_final"
              data-is-core="{1 if idx < 4 else 0}"
            >
              <div class="sum">{escape(desc)}</div>
            </div>
            """
            for idx, (section, title, desc, href) in enumerate(items)
        )
        raw_by_section: dict[str, list[dict[str, object]]] = {section: [] for section in report_eval.SECTION_KEYS}
        for idx, (section, title, desc, href) in enumerate(items):
            raw_by_section[section].append(
                {
                    "section": section,
                    "title": title,
                    "link": href,
                    "description": desc,
                    "selection_fit_score": 1.65,
                    "selection_stage": "core_final",
                    "score": 90.0 - idx * 0.1,
                    "pub_dt_kst": "2026-05-19T05:00:00+09:00",
                }
            )
        snapshot_payload = {
            "window": {"end_kst": "2026-05-19T06:00:00+09:00"},
            "raw_by_section": raw_by_section,
        }

        result = report_eval.evaluate_report("2026-05-19", html, snapshot_payload)
        feedback = report_eval.build_selection_feedback_payload(result)
        guardrails = feedback["selection_guardrails"]

        self.assertGreater(result["metrics"]["off_scope_foreign_rate"], 0.0)
        self.assertGreater(result["metrics"]["story_duplicate_rate"], 0.0)
        self.assertGreater(result["metrics"]["cross_section_duplicate_rate"], 0.0)
        self.assertLess(result["overall_score"], 95.0)
        self.assertGreater(result["metrics"]["quality_signal_penalty"], 0.0)
        self.assertIn("foreign_scope_noise", guardrails["driver_tags"])
        self.assertIn("story_duplicate", guardrails["driver_tags"])
        self.assertIn("cross_section_duplicate", guardrails["driver_tags"])
        self.assertIn("두리안", guardrails["exclude_title_terms"])
        self.assertGreater(guardrails["story_duplicate_similarity_min"], 0.0)
        self.assertTrue(feedback["quality_samples"]["off_scope"])
        self.assertTrue(feedback["quality_samples"]["story_duplicates"])

    def test_evaluate_report_flags_section_core_and_commodity_risks(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐"
          data-href="https://example.com/onion-training"
          data-article-id="brief-1"
          data-target-domain="example.com"
        >
          <span class="badgeCore">핵심</span>
          <div class="sum">양파 농가 교육과 총회 소식을 전한 행사성 기사다.</div>
        </div>
        <div
          data-surface="briefing_card"
          data-section="dist"
          data-article-title="가락시장 사과 반입 감소…경락가 상승"
          data-href="https://example.com/apple-market"
          data-article-id="brief-2"
          data-target-domain="example.com"
        >
          <div class="sum">사과 반입 감소와 경락가 상승 흐름을 정리했다.</div>
        </div>
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐"
          data-article-id="commodity-1"
          data-target-domain="example.com"
          data-item-key="onion"
          data-item-label="양파"
          data-representative-rank="0"
          data-representative-score="58.2"
          data-board-score="46.0"
          data-selection-fit="0.45"
          data-selection-stage="tail"
          href="https://example.com/onion-training"
        >대표</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-04-10T08:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐",
                        "link": "https://example.com/onion-training",
                        "description": "양파 재배 농가 교육과 총회를 진행한 행사 기사다.",
                        "selection_fit_score": 0.45,
                        "selection_stage": "tail",
                        "score": 32.0,
                        "pub_dt_kst": "2026-04-10T06:00:00+09:00",
                    },
                    {
                        "section": "supply",
                        "title": "양파 가격 폭락 우려…산지 출하 조절·수급 대책 촉구",
                        "link": "https://example.com/onion-issue",
                        "description": "양파 가격 급락과 산지 출하 조절, 수급 대책 요구를 다룬 기사다.",
                        "selection_fit_score": 1.72,
                        "selection_stage": "core_final",
                        "score": 91.0,
                        "pub_dt_kst": "2026-04-10T05:00:00+09:00",
                    },
                ],
                "policy": [],
                "dist": [
                    {
                        "section": "dist",
                        "title": "화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐",
                        "link": "https://example.com/onion-training-dist",
                        "description": "도매시장 반입과 가격 대응 문맥에서는 더 적합한 제목으로 재분류될 수 있다.",
                        "selection_fit_score": 1.6,
                        "selection_stage": "cross_section_dist_backfill",
                        "score": 83.0,
                        "pub_dt_kst": "2026-04-10T06:30:00+09:00",
                    },
                    {
                        "section": "dist",
                        "title": "가락시장 사과 반입 감소…경락가 상승",
                        "link": "https://example.com/apple-market",
                        "description": "가락시장 사과 반입 감소와 경락가 상승 흐름을 다뤘다.",
                        "selection_fit_score": 1.42,
                        "selection_stage": "core_final",
                        "score": 88.0,
                        "pub_dt_kst": "2026-04-10T04:00:00+09:00",
                    },
                ],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-04-10", html, snapshot_payload)

        self.assertLess(result["scores"]["section_alignment"], 75.0)
        self.assertLess(result["scores"]["core_quality"], 70.0)
        self.assertLess(result["scores"]["commodity_board_quality"], 65.0)
        selection_feedback = report_eval.build_selection_feedback_payload(result)
        self.assertEqual(selection_feedback["selection_guardrails"]["commodity_active_min_rank"], 2)
        self.assertTrue(selection_feedback["selection_guardrails"]["commodity_require_issue_signal"])
        self.assertTrue(selection_feedback["selection_guardrails"]["commodity_require_direct_item_focus"])
        self.assertTrue(any("섹션 오배치" in hint for hint in result["improvement_hints"]))
        self.assertTrue(any("핵심기사 품질" in hint for hint in result["improvement_hints"]))
        self.assertTrue(any("품목 보드 대표기사" in hint for hint in result["improvement_hints"]))

    def test_evaluate_report_flags_semantic_false_positive_news(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="오이 솔루션, 장중 상한가 직행 후 이탈…광통신 기대감에"
          data-href="https://www.cbci.co.kr/news/articleView.html?idxno=572803"
          data-article-id="cbci-stock"
          data-target-domain="cbci.co.kr"
        >
          <div class="sum">오이솔루션 주가와 광통신 기대감을 다룬 증권 기사다.</div>
        </div>
        <div
          data-surface="briefing_card"
          data-section="dist"
          data-article-title="영등포 지도가 바뀐다... 김종길 의원, ‘영등포구청역~ 청과 시장 ’ 1호..."
          data-href="https://www.dnews.co.kr/uhtml/view.jsp?idxno=202605071103059370818"
          data-article-id="dnews-pledge"
          data-target-domain="dnews.co.kr"
        >
          <div class="sum">청과시장 일대 개발 공약을 발표한 정치 기사다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-05-08T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "오이 솔루션, 장중 상한가 직행 후 이탈…광통신 기대감에",
                        "link": "https://www.cbci.co.kr/news/articleView.html?idxno=572803",
                        "description": "오이솔루션 주가와 광통신 장비 기대감을 다룬 증권 기사다. 페이지 하단에 가락시장 종사자와 농산물 기사 목록이 섞였다.",
                        "selection_fit_score": 1.9,
                        "selection_stage": "supply_board_bridge",
                        "score": 11.68,
                        "pub_dt_kst": "2026-05-07T12:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [
                    {
                        "section": "dist",
                        "title": "영등포 지도가 바뀐다... 김종길 의원, ‘영등포구청역~ 청과 시장 ’ 1호...",
                        "link": "https://www.dnews.co.kr/uhtml/view.jsp?idxno=202605071103059370818",
                        "description": "국민의힘 김종길 의원이 재선 도전을 앞두고 제1호 공약으로 영등포청과시장 일대 용적률 1000% 개발과 대단지 조성을 발표했다.",
                        "selection_fit_score": 1.14,
                        "selection_stage": "underfill",
                        "score": 17.76,
                        "pub_dt_kst": "2026-05-07T11:03:00+09:00",
                    }
                ],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-05-08", html, snapshot_payload)

        self.assertEqual(result["metrics"]["content_false_positive_rate"], 1.0)
        reasons = {sample["reason"] for sample in result["content_false_positive_samples"]}
        self.assertIn("finance_company_noise", reasons)
        self.assertIn("political_market_pledge_noise", reasons)
        self.assertLess(result["overall_score"], 85.0)
        self.assertIn("semantic_false_positive", result["selection_guardrails"]["driver_tags"])
        self.assertTrue(any("금융·정치성 오탐" in hint for hint in result["improvement_hints"]))

    def test_evaluate_report_does_not_flag_broadcast_report_as_finance_noise(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="[D리포트] 중국산 사과 묘목 밀수 일당 16명 적발…63만 주 압수"
          data-href="https://news.sbs.co.kr/news/endPage.do?news_id=N1008539140"
          data-article-id="sbs-seedling"
          data-target-domain="news.sbs.co.kr"
          data-selection-fit="2.2"
          data-selection-stage="core"
          data-is-core="1"
        >
          <span class="badgeCore">핵심</span>
          <div class="sum">사과 묘목 밀수와 과수화상병 검역 위험을 전했다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-04-30T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "[D리포트] 중국산 사과 묘목 밀수 일당 16명 적발…63만 주 압수",
                        "link": "https://news.sbs.co.kr/news/endPage.do?news_id=N1008539140",
                        "description": "중국산 사과 묘목과 복숭아 묘목을 밀수한 일당이 적발됐고 검역본부가 과수화상병 유입 위험을 설명했다.",
                        "selection_fit_score": 0.0,
                        "selection_stage": "",
                        "score": 88.0,
                        "pub_dt_kst": "2026-04-30T05:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-04-30", html, snapshot_payload)

        self.assertEqual(result["metrics"]["content_false_positive_rate"], 0.0)
        self.assertEqual(result["content_false_positive_samples"], [])
        self.assertGreater(result["scores"]["core_quality"], 80.0)

    def test_commodity_item_focus_uses_snapshot_body_context(self) -> None:
        html = """
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="도매시장 반입 줄어 가격 상승"
          data-article-id="commodity-apple"
          data-target-domain="example.com"
          data-item-key="apple"
          data-item-label="사과"
          data-representative-rank="3"
          data-selection-fit="1.4"
          data-selection-stage="core_final"
          href="https://example.com/apple-market"
        >대표기사</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-04-24T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "도매시장 반입 줄어 가격 상승",
                        "link": "https://example.com/apple-market",
                        "description": "사과 산지 출하가 줄고 도매시장 반입량이 감소하면서 경락가 상승세가 이어졌다.",
                        "selection_fit_score": 1.4,
                        "selection_stage": "core_final",
                        "score": 88.0,
                        "pub_dt_kst": "2026-04-24T05:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-04-24", html, snapshot_payload)

        self.assertEqual(result["metrics"]["commodity_primary_item_focus_rate"], 1.0)

    def test_monday_freshness_weights_weekend_collection_span(self) -> None:
        summary = "사과 산지 출하량과 도매시장 반입 흐름을 점검하고 가격 변동 가능성을 설명했다. 농가와 유통 주체의 대응 방향도 함께 전했다."
        html = "\n".join(
            f"""
            <div
              data-surface="briefing_card"
              data-section="supply"
              data-article-title="사과 주말 출하 점검 {idx}"
              data-href="https://example.com/apple-{idx}"
              data-article-id="brief-{idx}"
              data-target-domain="example.com"
            >
              <div class="sum">{summary}</div>
            </div>
            """
            for idx in range(4)
        )
        raw_items = [
            {
                "section": "supply",
                "title": f"사과 주말 출하 점검 {idx}",
                "link": f"https://example.com/apple-{idx}",
                "description": "사과 산지 출하량과 도매시장 반입 흐름을 점검했다.",
                "selection_fit_score": 1.4,
                "selection_stage": "core_final",
                "score": 85.0,
                "pub_dt_kst": f"2026-04-17T{idx + 8:02d}:00:00+09:00",
            }
            for idx in range(4)
        ]
        snapshot_payload = {
            "window": {
                "start_kst": "2026-04-17T06:00:00+09:00",
                "end_kst": "2026-04-20T06:00:00+09:00",
            },
            "raw_by_section": {"supply": raw_items, "policy": [], "dist": [], "pest": []},
        }

        monday = report_eval.evaluate_report("2026-04-20", html, snapshot_payload)
        regular = report_eval.evaluate_report("2026-04-21", html, {**snapshot_payload, "window": {"end_kst": "2026-04-21T06:00:00+09:00"}})

        self.assertEqual(monday["metrics"]["freshness_window_mode"], "weekend_span")
        self.assertGreater(monday["scores"]["freshness"], regular["scores"]["freshness"])
        self.assertGreaterEqual(monday["scores"]["freshness"], 85.0)

    def test_markdown_and_history_renderers_have_expected_shape(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)
        result["operational_score"] = result["overall_score"]
        result["editorial_score"] = 91.0
        result["editorial"] = {
            "status": "success",
            "score": 91.0,
            "target_score": 95.0,
            "target_status": "needs_minor_iteration",
            "scores": {
                "article_selection": 91.0,
                "section_fit": 92.0,
                "core_pick_quality": 90.0,
                "summary_usefulness": 93.0,
                "missed_opportunity": 88.0,
                "noise_control": 94.0,
            },
            "summary": "Good but not perfect.",
            "issues": [
                {"type": "missed_better_candidate", "severity": "medium", "title": "issue-1", "reason": "better option visible"},
                {"type": "duplicate", "severity": "high", "title": "issue-2", "reason": "same event repeated"},
                {"type": "noise", "severity": "medium", "title": "issue-3", "reason": "selection noise"},
                {"type": "noise", "severity": "medium", "title": "issue-4", "reason": "selection noise"},
                {"type": "noise", "severity": "medium", "title": "issue-5", "reason": "selection noise"},
                {"type": "noise", "severity": "medium", "title": "issue-6", "reason": "selection noise"},
                {"type": "noise", "severity": "medium", "title": "issue-7", "reason": "selection noise"},
                {"type": "noise", "severity": "medium", "title": "issue-8", "reason": "selection noise"},
            ],
        }
        markdown = report_eval.render_evaluation_markdown(result)
        history_entry = report_eval.result_to_history_entry(result)
        selection_feedback = report_eval.build_selection_feedback_payload(result)

        self.assertIn("## Daily Eval", markdown)
        self.assertIn(self.report_date, markdown)
        self.assertIn("section_fit=", markdown)
        self.assertIn("Editorial Shadow Eval", markdown)
        self.assertIn("issue-8", markdown)
        self.assertEqual(history_entry["report_date"], self.report_date)
        self.assertIn("overall_score", history_entry)
        self.assertEqual(history_entry["editorial_score"], 91.0)
        self.assertIn("editorial_duplicate_topic", selection_feedback["selection_guardrails"]["driver_tags"])


if __name__ == "__main__":
    unittest.main()
