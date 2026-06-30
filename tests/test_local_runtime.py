import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import main
import replay


class LocalRuntimeTests(TestCase):
    def _make_article(
        self,
        section: str = "supply",
        title: str = "사과 가격 상승... 출하 물량 감소에 수급 비상",
        description: str = "사과 출하 물량 감소로 도매가격 상승세가 이어지고 있다.",
        link: str = "https://www.news1.kr/economy/food/999001",
        press: str = "뉴스1",
        topic: str = "사과",
    ) -> main.Article:
        canon = main.canonicalize_url(link)
        title_key = main.norm_title_key(title)
        return main.Article(
            section=section,
            title=title,
            description=description,
            link=link,
            originallink=link,
            pub_dt_kst=datetime(2026, 3, 20, 7, 0, tzinfo=main.KST),
            domain=main.domain_of(link),
            press=press,
            norm_key=main.make_norm_key(canon, press, title_key),
            title_key=title_key,
            canon_url=canon,
            topic=topic,
            score=11.0,
            source_query="사과 수급",
            source_channel="naver_news",
        )

    def test_load_env_file_preserves_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / ".env.local"
            env_path.write_text(
                "\n".join(
                    [
                        "NAVER_CLIENT_ID=from_file",
                        'QUOTED_VALUE="alpha beta"',
                        "INLINE_COMMENT=value # ignored",
                        "export EXTRA_VALUE=' spaced value '",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"NAVER_CLIENT_ID": "keep_me"}, clear=False):
                loaded = main._load_env_file(env_path)
                self.assertEqual(os.environ["NAVER_CLIENT_ID"], "keep_me")
                self.assertEqual(os.environ["QUOTED_VALUE"], "alpha beta")
                self.assertEqual(os.environ["INLINE_COMMENT"], "value")
                self.assertEqual(os.environ["EXTRA_VALUE"], " spaced value ")
                self.assertEqual(loaded["NAVER_CLIENT_ID"], "from_file")

    def test_local_dry_run_github_wrappers_use_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            with patch.dict(
                os.environ,
                {
                    "LOCAL_DRY_RUN": "true",
                    "LOCAL_OUTPUT_DIR": str(out_dir),
                },
                clear=False,
            ):
                main.github_put_file(
                    "NH-Horti/agri-news-brief",
                    "docs/dev/index.html",
                    "<html>preview</html>",
                    token="",
                    message="local write",
                    branch="codex/dev-preview",
                )
                target = out_dir / "codex" / "dev-preview" / "docs" / "dev" / "index.html"
                self.assertTrue(target.is_file())

                raw, sha = main.github_get_file(
                    "NH-Horti/agri-news-brief",
                    "docs/dev/index.html",
                    token="",
                    ref="codex/dev-preview",
                )
                self.assertEqual(raw, "<html>preview</html>")
                self.assertTrue(sha)

                items = main.github_list_dir(
                    "NH-Horti/agri-news-brief",
                    "docs/dev",
                    token="",
                    ref="codex/dev-preview",
                )
                self.assertTrue(any(item["name"] == "index.html" for item in items))

    def test_article_snapshot_roundtrip_preserves_fields(self) -> None:
        article = self._make_article()
        article.summary = "사과 수급과 가격 흐름을 다룬 핵심 기사다."
        article.selection_stage = "supply_core"
        article.selection_note = "program_core"
        article.selection_fit_score = 3.4
        article.reassigned_from = "dist"

        payload = replay.article_to_snapshot_dict(article)
        restored = main.Article(**replay.article_dict_to_kwargs(payload))

        self.assertEqual(restored.title, article.title)
        self.assertEqual(restored.summary, article.summary)
        self.assertEqual(restored.selection_stage, article.selection_stage)
        self.assertEqual(restored.reassigned_from, article.reassigned_from)
        self.assertEqual(restored.pub_dt_kst, article.pub_dt_kst)

    def test_save_and_load_replay_snapshot_roundtrip(self) -> None:
        article = self._make_article()
        summary_cache = {
            article.norm_key: {
                "s": "사과 가격 상승과 출하 감소를 다룬 요약",
                "t": "2026-03-20T07:10:00+09:00",
            }
        }
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            with patch.dict(
                os.environ,
                {
                    "LOCAL_DRY_RUN": "true",
                    "LOCAL_OUTPUT_DIR": str(out_dir),
                },
                clear=False,
            ):
                saved = main.save_replay_snapshot(
                    "2026-03-20",
                    datetime(2026, 3, 19, 7, 0, tzinfo=main.KST),
                    datetime(2026, 3, 20, 7, 0, tzinfo=main.KST),
                    {"supply": [article]},
                    summary_cache=summary_cache,
                    debug_payload={"collections": {"supply": {"items_total": 1}}},
                )
                self.assertTrue(saved.is_file())

                raw_by_section, start_kst, end_kst, loaded_cache, debug_payload, loaded_path = main.load_replay_snapshot("2026-03-20")
                self.assertEqual(loaded_path, saved)
                self.assertEqual(start_kst.isoformat(), "2026-03-19T07:00:00+09:00")
                self.assertEqual(end_kst.isoformat(), "2026-03-20T07:00:00+09:00")
                self.assertEqual(raw_by_section["supply"][0].title, article.title)
                self.assertEqual(loaded_cache[article.norm_key]["s"], summary_cache[article.norm_key]["s"])
                self.assertEqual(debug_payload["collections"]["supply"]["items_total"], 1)

    def test_build_sections_for_report_replay_uses_snapshot_summary_cache(self) -> None:
        article = self._make_article()
        snapshot_path: Path
        with tempfile.TemporaryDirectory() as td:
            snapshot_path = Path(td) / "2026-03-20.snapshot.json"
            with patch.dict(
                os.environ,
                {
                    "REPLAY_SNAPSHOT_PATH": str(snapshot_path),
                    "REPLAY_WRITE_SNAPSHOT": "false",
                },
                clear=False,
            ):
                main.save_replay_snapshot(
                    "2026-03-20",
                    datetime(2026, 3, 19, 7, 0, tzinfo=main.KST),
                    datetime(2026, 3, 20, 7, 0, tzinfo=main.KST),
                    {"supply": [article]},
                    summary_cache={
                        article.norm_key: {
                            "s": "리플레이 스냅샷에서 가져온 요약",
                            "t": "2026-03-20T07:15:00+09:00",
                        }
                    },
                )

                with patch.object(main, "load_summary_cache", return_value={}):
                    by_section, summary_cache, start_kst, end_kst = main._build_sections_for_report(
                        "NH-Horti/agri-news-brief",
                        "",
                        "2026-03-20",
                        datetime.min.replace(tzinfo=main.KST),
                        datetime.min.replace(tzinfo=main.KST),
                        allow_openai=False,
                        replay_snapshot=True,
                    )

                self.assertEqual(start_kst.isoformat(), "2026-03-19T07:00:00+09:00")
                self.assertEqual(end_kst.isoformat(), "2026-03-20T07:00:00+09:00")
                self.assertTrue(by_section["supply"])
                self.assertEqual(by_section["supply"][0].summary, "리플레이 스냅샷에서 가져온 요약")
                self.assertEqual(summary_cache[article.norm_key]["s"], "리플레이 스냅샷에서 가져온 요약")

    def test_load_openai_summary_feedback_reads_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            feedback_path = Path(td) / "latest-feedback.txt"
            feedback_path.write_text("- keep the first sentence concrete\n- retain one number\n", encoding="utf-8")
            with patch.object(main, "OPENAI_SUMMARY_FEEDBACK_PATH", str(feedback_path)):
                with patch.object(main, "OPENAI_SUMMARY_FEEDBACK_MAX_CHARS", 80):
                    feedback = main._load_openai_summary_feedback()
            self.assertIn("first sentence", feedback)
            self.assertIn("retain one number", feedback)

    def test_load_selection_feedback_guardrails_reads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            feedback_path = Path(td) / "latest-selection-feedback.json"
            feedback_path.write_text(
                json.dumps(
                    {
                        "selection_guardrails": {
                            "commodity_active_min_rank": 2,
                            "commodity_require_issue_signal": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with patch.object(main, "SELECTION_FEEDBACK_PATH", str(feedback_path)):
                guardrails = main._load_selection_feedback_guardrails()
            self.assertEqual(int(guardrails["commodity_active_min_rank"]), 2)
            self.assertTrue(bool(guardrails["commodity_require_issue_signal"]))

    def test_selection_feedback_url_exclusion_blocks_known_articles(self) -> None:
        article = self._make_article(
            section="policy",
            title="한국향 두리안 수출 262% 급증에도...울상짓는 베트남 농가?",
            link="https://www.ajunews.com/view/20260518142237838",
        )
        with patch.dict(
            main.SELECTION_FEEDBACK_GUARDRAILS,
            {"exclude_url_fragments": ["ajunews.com/view/20260518142237838"]},
            clear=True,
        ):
            self.assertEqual(main._selection_feedback_block_reason(article, "policy"), "feedback_url_exclusion")

    def test_editorial_safe_demotes_price_report_without_policy_action(self) -> None:
        article = self._make_article(
            section="policy",
            title="5월 입하 이후, 품종 교체 및 주산지 변동으로 일부 농산물 가격 오름세",
            description="도매시장 입하와 품종 교체 영향으로 일부 농산물 가격 오름세가 나타났다.",
        )

        self.assertEqual(
            main._editorial_safe_core_demote_reason(article, "policy"),
            "policy_price_report_without_policy_action",
        )
        self.assertGreater(main._editorial_safe_soft_penalty(article, "policy"), 0.0)

    def test_editorial_safe_keeps_policy_action_article(self) -> None:
        article = self._make_article(
            section="policy",
            title="계란 224만개 추가 수입, 가공용 돼지ㆍ닭고기 할당관세 추가 적용",
            description="정부가 수급 안정을 위해 추가 수입과 할당관세 적용 대책을 발표했다.",
        )

        self.assertEqual(main._editorial_safe_core_demote_reason(article, "policy"), "")

    def test_editorial_safe_demotes_promotional_and_weak_dist_items(self) -> None:
        supply_article = self._make_article(
            section="supply",
            title="NH농협 창녕군지부, 마늘 망 지원… 농업인 영농비 절감 기대",
            description="지역 농업인을 대상으로 마늘 망 지원 행사를 열었다.",
        )
        dist_article = self._make_article(
            section="dist",
            title="강원 농협 연합판매사업 협의회, 2026 산지 유통 현장투어 개최",
            description="협의회가 산지 유통 현장투어를 개최했다.",
        )

        mou_article = self._make_article(
            section="dist",
            title="강릉도매시장-미스터아빠, 미래형 북상 사과 SCM 혁신 프로젝트 업무협약",
            description="양측이 사과 유통 혁신 프로젝트 추진을 위한 업무협약을 맺었다.",
        )
        raw_like_mou_article = self._make_article(
            section="dist",
            title="강릉도매시장-미스터아빠, 미래형 북상 사과 SCM 혁신 프로젝트 업무협약",
            description=(
                "지난 19일 업무협약을 체결했다. 온라인도매시장 플랫폼을 기반으로 AI 물류 "
                "프로세싱 기술을 결합하고 사과 전문 선별 출하 거점센터를 구축한다."
            ),
        )
        dist_ops_article = self._make_article(
            section="dist",
            title="가락시장 근교산 채소류 파렛트 운송지원 확대 추진",
            description="가락시장 채소 반입과 물류비 절감을 위해 파렛트 운송지원 물량을 확대한다.",
        )
        field_policy_article = self._make_article(
            section="policy",
            title='무안 양파 값 폭락…"캘수록 손해, 갈아엎어도 소용없다"',
            description="양파 생산량 증가로 가격이 폭락해 농가가 밭을 갈아엎고 정부 대응을 요구했다.",
        )

        self.assertEqual(main._editorial_safe_core_demote_reason(supply_article, "supply"), "promotional_or_event_filler")
        self.assertIn(
            main._editorial_safe_core_demote_reason(dist_article, "dist"),
            {"promotional_or_event_filler", "dist_event_or_development_without_ops"},
        )
        self.assertEqual(
            main._editorial_safe_core_demote_reason(mou_article, "dist"),
            "dist_event_or_development_without_ops",
        )
        self.assertEqual(
            main._editorial_safe_core_demote_reason(raw_like_mou_article, "dist"),
            "dist_event_or_development_without_ops",
        )
        self.assertEqual(main._editorial_safe_core_demote_reason(dist_ops_article, "dist"), "")
        self.assertEqual(
            main._editorial_safe_core_demote_reason(field_policy_article, "policy"),
            "policy_field_price_collapse_without_policy_lead",
        )

    def test_editorial_safe_demotes_nonfood_supply_and_training_dist_core(self) -> None:
        citrus_cosmetic = self._make_article(
            section="supply",
            title="국산 감귤, 기능성 화장품으로 대변신",
            description="감귤 추출물을 활용해 스킨케어 제품을 개발했다는 소개 기사다.",
        )
        dist_training = self._make_article(
            section="dist",
            title='[동화청과 유통교육] "맛· 품질 은 기본…소비자 선택 기준까지 설계 필요"',
            description=(
                "미래농업인을 대상으로 소비자 선택 기준과 상품 기획 교육을 진행했다. "
                "강연에서는 AI 선별, 포장, 물류, 산지 거래 전략도 소개됐다."
            ),
        )
        dist_ops_article = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 반입 물류 효율화를 위해 파렛트 운송지원 물량을 확대한다.",
        )

        self.assertEqual(
            main._editorial_safe_core_demote_reason(citrus_cosmetic, "supply"),
            "supply_nonfood_promo_without_market_signal",
        )
        self.assertEqual(
            main._editorial_safe_core_demote_reason(dist_training, "dist"),
            "dist_education_or_training_without_ops",
        )
        self.assertEqual(
            main._editorial_safe_core_demote_reason(dist_ops_article, "dist"),
            "promotional_or_event_filler",
        )

    def test_editorial_safe_keeps_metric_dist_logistics_article(self) -> None:
        metric_ops_article = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description=(
                "가락시장 농산물 물류체계 개선을 위해 근교산 채소류와 햇감자 파렛트 운송지원 사업을 확대한다. "
                "청과부류 전체 파렛트 출하율은 88%로 전년보다 5.3%포인트 올랐고, "
                "운송비 지원금은 파렛트 1장당 평균 5500원으로 확대된다."
            ),
            link="http://www.amnews.co.kr/news/articleView.html?idxno=72651",
            press="농축유통신문",
        )

        self.assertTrue(main.is_dist_hard_logistics_metric_context(metric_ops_article.title, metric_ops_article.description))
        self.assertEqual(main._editorial_safe_core_demote_reason(metric_ops_article, "dist"), "")

    def test_dist_national_export_logistics_is_kept_and_promoted(self) -> None:
        kfood = self._make_article(
            section="dist",
            title='K-푸드는 "전쟁 영향? 글쎄요"…중동 물류난에도 GCC 수출 37.6%↑',
            description=(
                "중동전쟁에 따른 해상 물류 차질과 운임 급등에도 올해 K-푸드 수출이 증가세를 이어갔다. "
                "정부는 물류비 지원 등을 담은 72억원 규모 수출바우처 추경 사업으로 수출기업 부담을 완화한다."
            ),
            link="https://newsis.com/view/NISX20260521_0003638627",
            press="뉴시스",
            topic="농식품",
        )
        local_tail = self._make_article(
            section="dist",
            title="무안군, 양파 100톤 수도권 직거래로 판로 뚫었다",
            description="전남 무안군이 양파 소비촉진 캠페인과 온라인 할인행사를 추진했다.",
            link="https://example.com/muan-onion",
        )
        pallet_core = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 농산물 물류체계 개선을 위해 파렛트 운송지원 사업을 확대한다.",
            link="https://example.com/pallet",
            press="농축유통신문",
        )
        pallet_core.is_core = True
        final_by_section = {"dist": [pallet_core, local_tail]}

        dist_conf = next((s for s in main.SECTIONS if s.get("key") == "dist"), {})
        self.assertTrue(main.is_dist_national_export_logistics_context(kfood.title, kfood.description, kfood.domain, kfood.press))
        self.assertFalse(main.is_dist_macro_export_noise_context(kfood.title, kfood.description, kfood.domain, kfood.press))
        self.assertTrue(main.is_relevant(kfood.title, kfood.description, kfood.domain, kfood.link, dist_conf, kfood.press))
        self.assertEqual(main._promote_dist_national_export_logistics_core(final_by_section, {"dist": [kfood]}), 1)

        dist_titles = {article.title: article for article in final_by_section["dist"]}
        self.assertTrue(dist_titles[kfood.title].is_core)
        self.assertFalse(pallet_core.is_core)
        self.assertNotIn(local_tail.link, {article.link for article in final_by_section["dist"]})

    def test_dist_national_export_logistics_core_skips_opinion_column(self) -> None:
        column = self._make_article(
            section="dist",
            title="[천자칼럼] K-푸드 수출 물류비 지원의 명암",
            description="K-푸드 수출 기업의 물류비 지원과 수출바우처 72억원, 중동 물류 차질 37.6%를 다룬 칼럼.",
            link="https://www.hankyung.com/article/2026062200011",
            press="한국경제",
        )
        kfood = self._make_article(
            section="dist",
            title="K-푸드 수출기업, 중동 물류 차질에 물류비 지원 72억원",
            description="정부가 수출바우처와 물류비 지원으로 농식품 수출기업 부담을 낮춘다. GCC 수출은 37.6% 늘었다.",
            link="https://www.yna.co.kr/view/AKR20260622000000000",
            press="연합뉴스",
        )
        local_tail = self._make_article(
            section="dist",
            title="무안군 양파 직거래 행사로 소비 촉진",
            description="지역 농산물 소비촉진 캠페인과 할인 행사를 추진한다.",
            link="https://example.com/muan-onion-column",
        )
        column.is_core = True
        final_by_section = {"dist": [column, local_tail]}

        self.assertTrue(main._is_dist_national_export_core_opinion_noise(column))
        self.assertTrue(main.is_dist_national_export_logistics_context(column.title, column.description, column.domain, column.press))
        self.assertTrue(main.is_dist_national_export_logistics_context(kfood.title, kfood.description, kfood.domain, kfood.press))
        self.assertEqual(main._promote_dist_national_export_logistics_core(final_by_section, {"dist": [kfood]}), 1)

        links = {article.link: article for article in final_by_section["dist"]}
        self.assertTrue(links[kfood.link].is_core)
        self.assertFalse(column.is_core)
        self.assertIn(column.link, links)
        self.assertNotIn(local_tail.link, links)

    def test_dist_national_export_logistics_does_not_match_at_inside_words(self) -> None:
        foreign_macro = self._make_article(
            section="dist",
            title="이게 다 얼마야? 미국인들 망했다 말 나온 이유",
            description=(
                "미국과 이란 전쟁으로 에너지·원자재 가격이 오르고 물류비 부담이 커졌다는 외신 분석이다. "
                "식품 가격과 비료 가격에도 1320억 달러 충격이 발생한다는 전망을 전했다."
            ),
            link="https://www.seoul.co.kr/news/international/2026/06/20/20260620500009",
            press="서울신문",
        )
        at_export = self._make_article(
            section="dist",
            title="aT, K-푸드 중동 수출 물류비 지원 72억원 확대",
            description="aT가 수출바우처와 물류비 지원으로 농식품 수출기업의 GCC 물류 차질 대응을 돕는다.",
            link="https://example.com/at-kfood-logistics",
            press="aT",
        )

        self.assertFalse(main.is_dist_national_export_logistics_context(
            foreign_macro.title,
            foreign_macro.description,
            foreign_macro.domain,
            foreign_macro.press,
        ))
        self.assertTrue(main.is_dist_national_export_logistics_context(
            at_export.title,
            at_export.description,
            at_export.domain,
            at_export.press,
        ))

    def test_editorial_shadow_restores_fruit_tariff_and_reference_price_policy(self) -> None:
        reserve = self._make_article(
            section="policy",
            title="농식품부, 여름철 폭염·호우 대비 농산물 비축물량 확대",
            description="정부가 폭염과 호우에 대비해 농산물 수급 안정 대책을 추진한다.",
            link="https://example.com/reserve",
            press="농식품부",
        )
        labor = self._make_article(
            section="policy",
            title="농식품부·법무부, 계절노동자 현장간담회 개최",
            description="농업 인력난 대응을 위한 제도 개선 논의를 진행했다.",
            link="https://example.com/labor",
            press="농식품부",
        )
        fertilizer = self._make_article(
            section="policy",
            title="비료 가격 상승에도 지원 예산은 감소...농가 부담 가중",
            description="비료 가격 상승과 지원 예산 감소로 농가 생산비 부담이 커지고 있다.",
            link="https://example.com/fertilizer",
        )
        president_a = self._make_article(
            section="policy",
            title='李대통령 "첫째도 둘째도 물가…채소·육류 가격 안정 특단 방안"',
            description="대통령이 민생 물가 안정과 채소·육류 가격 안정 방안을 지시했다.",
            link="https://example.com/president-a",
        )
        president_b = self._make_article(
            section="policy",
            title='이 대통령 "중동전쟁 종전 문턱…민생·물가 대응, 이제 시작"',
            description="대통령이 중동전쟁 이후 민생과 물가 대응을 주문했다.",
            link="https://example.com/president-b",
        )
        tariff = self._make_article(
            section="policy",
            title="국산 과일 한창때 ‘할당관세’ 재 뿌리나",
            description="바나나·파인애플·망고 할당관세 적용기간 연장으로 국산 여름과일 가격 하락 우려가 커졌다.",
            link="https://www.nongmin.com/article/20260619500576",
            press="농민신문",
        )
        reference_price = self._make_article(
            section="policy",
            title="농산물가격안정제, 핵심은 ‘기준가격’…“비용 보전 넘어 경영안정에 방점을”",
            description="새 농안법 시행을 앞두고 기준가격, 경영비, 차액 지원 기준을 두고 전문가 제언이 나왔다.",
            link="https://www.nongmin.com/article/20260619500594",
            press="농민신문",
        )
        reserve.is_core = True
        labor.is_core = True
        final_by_section = {"policy": [reserve, labor, fertilizer, president_a, president_b]}

        changed = main._repair_editorial_shadow_issues_from_raw(
            final_by_section,
            {"policy": [tariff, reference_price]},
        )

        titles = [article.title for article in final_by_section["policy"]]
        self.assertGreaterEqual(changed, 2)
        self.assertIn(tariff.title, titles)
        self.assertIn(reference_price.title, titles)
        self.assertNotIn(fertilizer.title, titles)
        self.assertLessEqual(sum(1 for title in titles if "대통령" in title or "대통령" in title), 1)

    def test_dist_response_logistics_and_market_education_replace_local_promo_tail(self) -> None:
        response = self._make_article(
            section="policy",
            title="중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력",
            description=(
                "중동 전쟁 장기화 여파로 K-푸드 수출 물류 부담이 커지자 정부가 수출바우처와 물류비 지원을 확대한다. "
                "농식품 수출기업 지원 예산은 72억원 규모로 편성됐다."
            ),
            link="https://example.com/kfood-response",
            press="전자신문",
        )
        education = self._make_article(
            section="dist",
            title='[동화청과 유통교육] "맛·품질은 기본…소비자 선택 기준까지 설계 필요"',
            description="동화청과가 청년농에게 도매시장 유통 구조와 대형 유통업체 구매·판매 전략, 출하 전략을 교육했다.",
            link="https://example.com/education",
            press="한국농업신문",
        )
        local_tail = self._make_article(
            section="dist",
            title="무안군, 양파 100톤 수도권 직거래로 판로 뚫었다",
            description="전남 무안군이 양파 소비촉진 캠페인과 온라인 할인행사를 추진했다.",
            link="https://example.com/muan-onion",
        )
        pallet = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 농산물 물류체계 개선을 위해 파렛트 운송지원 사업을 확대한다.",
            link="https://example.com/pallet",
            press="농축유통신문",
        )
        pallet.is_core = True
        response.section = "dist"
        response.is_core = True
        final_by_section = {"dist": [response, pallet, local_tail]}

        self.assertTrue(main.is_dist_national_export_logistics_context(response.title, response.description, response.domain, response.press))
        self.assertTrue(main.is_dist_market_education_tail_context(education.title, education.description))
        self.assertTrue(main._is_optional_dist_editorial_tail(local_tail))
        self.assertEqual(main._replace_optional_dist_tail_from_raw(final_by_section, {"dist": [education]}), 1)

        links = {article.link for article in final_by_section["dist"]}
        self.assertIn(response.link, links)
        self.assertIn(education.link, links)
        self.assertNotIn(local_tail.link, links)

    def test_dist_hard_logistics_core_is_not_displaced_by_export_logistics(self) -> None:
        pallet_core = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description=(
                "가락시장 농산물 물류체계 개선을 위해 근교산 채소류와 햇감자 파렛트 운송지원 사업을 확대한다. "
                "청과부류 전체 파렛트 출하율은 88%로 전년보다 5.3%포인트 올랐고, "
                "운송비 지원금은 파렛트 1장당 평균 5500원으로 확대된다."
            ),
            link="https://example.com/pallet-core",
            press="농축유통신문",
        )
        kfood = self._make_article(
            section="policy",
            title="중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력",
            description=(
                "중동 전쟁 장기화 여파로 K-푸드 수출 물류 부담이 커지자 정부가 수출바우처와 물류비 지원을 확대한다. "
                "농식품 수출기업 지원 예산은 72억원 규모로 편성됐다."
            ),
            link="https://example.com/kfood-response-core-check",
            press="전자신문",
        )
        local_tail = self._make_article(
            section="dist",
            title="무안군, 양파 100톤 수도권 직거래로 판로 뚫었다",
            description="전남 무안군이 양파 소비촉진 캠페인과 온라인 할인행사를 추진했다.",
            link="https://example.com/muan-onion-hard-core",
        )
        pallet_core.is_core = True
        final_by_section = {"dist": [pallet_core, local_tail]}

        self.assertTrue(main.is_dist_hard_logistics_metric_context(pallet_core.title, pallet_core.description))
        self.assertEqual(main._promote_dist_national_export_logistics_core(final_by_section, {"policy": [kfood]}), 1)

        titles = {article.title: article for article in final_by_section["dist"]}
        self.assertTrue(titles[pallet_core.title].is_core)
        self.assertFalse(titles[kfood.title].is_core)
        self.assertNotIn(local_tail.link, {article.link for article in final_by_section["dist"]})

    def test_dist_specific_export_logistics_tail_prefers_concrete_wire_story(self) -> None:
        response = self._make_article(
            section="dist",
            title="중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력",
            description=(
                "중동 전쟁 장기화 여파로 K-푸드 수출 물류 부담이 커지자 정부가 수출바우처와 물류비 지원을 확대한다. "
                "농식품 수출기업 지원 예산은 72억원 규모로 편성됐다."
            ),
            link="https://example.com/kfood-response",
            press="전자신문",
        )
        vague_specific = self._make_article(
            section="dist",
            title="K-푸드 수출, 중동 물류난 속 37.6% 성장 기록",
            description="중동 수출 물류난에도 K-푸드 수출이 성장했다는 업계 동향을 전했다.",
            link="https://www.cooknchefnews.com/news/view/1065599999999999",
            press="Cook&Chef",
        )
        concrete_wire = self._make_article(
            section="dist",
            title='K-푸드는 "전쟁 영향? 글쎄요"…중동 물류난에도 GCC 수출 37.6%↑',
            description=(
                "중동전쟁에 따른 해상 물류 차질과 운임 급등에도 K-푸드 수출이 증가세를 보였다. "
                "정부는 딸기 등 농식품 수출기업에 수출바우처와 물류비 지원을 확대한다."
            ),
            link="https://newsis.com/view/NISX20260521_0003638627",
            press="뉴시스",
        )
        pallet = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 농산물 물류체계 개선을 위해 파렛트 운송지원 사업을 확대한다.",
            link="https://example.com/pallet",
            press="농축유통신문",
        )
        response.is_core = True
        final_by_section = {"dist": [response, vague_specific, pallet]}

        self.assertTrue(main.is_dist_specific_kfood_export_logistics_context(vague_specific.title, vague_specific.description))
        self.assertTrue(main.is_dist_specific_kfood_export_logistics_context(concrete_wire.title, concrete_wire.description))
        self.assertEqual(main._ensure_dist_specific_export_logistics_tail(final_by_section, {"dist": [concrete_wire]}), 1)

        links = {article.link for article in final_by_section["dist"]}
        self.assertIn(concrete_wire.link, links)
        self.assertNotIn(vague_specific.link, links)

    def test_editorial_safe_demotes_dist_production_policy_tail(self) -> None:
        smartfarm_policy = self._make_article(
            section="dist",
            title="스마트팜·신품종 보급…품목맞춤형 접근 필요",
            description=(
                "기후변화 대응을 위해 시설원예 스마트팜과 복합형질 품종 보급, "
                "품목맞춤형 지원체계가 필요하다는 연구 분석이다."
            ),
        )
        self.assertEqual(
            main._editorial_safe_core_demote_reason(smartfarm_policy, "dist"),
            "dist_production_policy_without_ops",
        )

    def test_editorial_safe_keeps_dist_distribution_cooperation_tail(self) -> None:
        cooperation = self._make_article(
            section="dist",
            title='"대구·경북 농산물 유통협력 강화"',
            description=(
                "대구농수산물유통관리공사와 경상북도가 농산물 유통 효율화와 상생 협력을 논의했다. "
                "도매시장 물류시설과 경매 현장을 둘러보고 온라인도매시장 활용과 산지-소비지 연계 모델을 협의했다."
            ),
            link="https://example.com/dist-cooperation",
        )

        self.assertEqual(main._editorial_safe_core_demote_reason(cooperation, "dist"), "")

    def test_optional_supply_nonfood_tail_drops_only_above_minimum(self) -> None:
        onion_core = self._make_article(title="양파 가격 급락…산지폐기 확대 요구")
        cabbage = self._make_article(title="양배추 반입량 증가에 도매가격 약세", link="https://example.com/cabbage")
        garlic = self._make_article(title="마늘 저장 물량 감소로 시세 강세", link="https://example.com/garlic")
        citrus_cosmetic = self._make_article(
            title="국산 감귤, 기능성 화장품으로 대변신",
            description="감귤 추출물을 활용해 스킨케어 제품을 개발했다는 소개 기사다.",
            link="https://example.com/citrus-cosmetic",
        )
        onion_core.is_core = True
        final_by_section = {"supply": [onion_core, cabbage, garlic, citrus_cosmetic]}

        self.assertEqual(main._drop_optional_supply_nonfood_tail(final_by_section, min_items=3), 1)
        self.assertEqual(len(final_by_section["supply"]), 3)
        self.assertNotIn(citrus_cosmetic, final_by_section["supply"])

        final_by_section = {"supply": [onion_core, cabbage, citrus_cosmetic]}
        self.assertEqual(main._drop_optional_supply_nonfood_tail(final_by_section, min_items=3), 0)
        self.assertIn(citrus_cosmetic, final_by_section["supply"])

    def test_optional_dist_training_tail_drops_only_above_minimum(self) -> None:
        dist_core = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 반입 물류 효율화를 위해 파렛트 운송지원 물량을 확대한다.",
            link="https://example.com/dist-core",
        )
        dist_training = self._make_article(
            section="dist",
            title='[동화청과 유통교육] "맛·품질은 기본…소비자 선택 기준까지 설계 필요"',
            description="청년농 유통 교육에서 상품 기획과 선별, 포장, 물류 전략을 공유했다.",
            link="https://example.com/dist-training",
        )
        dist_tail_a = self._make_article(section="dist", title="농산물 직거래로 양파 100톤 판로 확보", link="https://example.com/dist-a")
        dist_tail_b = self._make_article(section="dist", title="스마트 APC 운영 개선 필요", link="https://example.com/dist-b")
        dist_core.is_core = True
        final_by_section = {"dist": [dist_core, dist_training, dist_tail_a, dist_tail_b]}

        self.assertEqual(main._drop_optional_dist_editorial_tail(final_by_section, min_items=3), 1)
        self.assertEqual(len(final_by_section["dist"]), 3)
        self.assertNotIn(dist_training, final_by_section["dist"])

        final_by_section = {"dist": [dist_core, dist_training, dist_tail_a]}
        self.assertEqual(main._drop_optional_dist_editorial_tail(final_by_section, min_items=3), 0)
        self.assertIn(dist_training, final_by_section["dist"])

    def test_priority_policy_price_system_promotes_to_core_without_growing_core_count(self) -> None:
        governance_core = self._make_article(
            section="policy",
            title="농협, 조합원 직선제 수용 등 개혁안 발표",
            description="농협중앙회가 조합원 직선제 수용과 내부 지배구조 개선 방안을 발표했다.",
            link="https://example.com/nh-governance",
        )
        macro_core = self._make_article(
            section="policy",
            title="슈퍼 엘리뇨·이란전쟁 장기화…애그플레이션 우려",
            description="기후와 원자재 가격 상승으로 농산물 물가 부담이 커질 수 있다는 분석이다.",
            link="https://example.com/agflation",
        )
        price_system = self._make_article(
            section="policy",
            title="농산물가격안정제도 8월 시행…평균가격, 경영비 밑돌땐 차액 지원",
            description="농식품부가 농안법 시행령 개정안을 입법예고하고 기준가격과 차액 지원 방식을 정했다.",
            link="https://example.com/price-system",
        )
        governance_core.is_core = True
        macro_core.is_core = True
        final_by_section = {"policy": [governance_core, macro_core, price_system]}

        self.assertEqual(main._promote_priority_policy_core(final_by_section, max_core=2), 1)

        core_titles = {article.title for article in final_by_section["policy"] if article.is_core}
        self.assertIn(price_system.title, core_titles)
        self.assertEqual(len(core_titles), 2)
        self.assertFalse(macro_core.is_core)

    def test_legislative_policy_recovery_replaces_weak_macro_core(self) -> None:
        price_system = self._make_article(
            section="policy",
            title="농산물가격안정제도 8월 시행…평균가격, 경영비 밑돌땐 차액 지원",
            description="농식품부가 농안법 시행령 개정안을 입법예고하고 기준가격과 차액 지원 방식을 정했다.",
            link="https://example.com/price-system",
        )
        macro_core = self._make_article(
            section="policy",
            title="슈퍼 엘리뇨·이란전쟁 장기화…애그플레이션 우려",
            description="기후와 원자재 가격 상승으로 농산물 물가 부담이 커질 수 있다는 분석이다.",
            link="https://example.com/agflation",
        )
        producer_price = self._make_article(
            section="policy",
            title="4월 생산자물가 2.5%↑…석탄·석유 가격이 끌어올려",
            description="생산자물가 상승률이 높아졌고 일부 농식품 가격 부담이 이어졌다.",
            link="https://example.com/ppi",
        )
        legislative = self._make_article(
            section="policy",
            title="‘농업민생’ 입법에 여야 합심…농협법·농지법 개정 난제 산적",
            description="국회가 농업 민생 입법으로 농협법과 농지법 개정을 논의하고 농정 제도 개선 쟁점을 다룬다.",
            link="https://example.com/legislative",
            press="농민신문",
        )
        price_system.is_core = True
        macro_core.is_core = True
        final_by_section = {"policy": [price_system, macro_core, producer_price]}

        self.assertTrue(main.is_policy_legislative_reform_context(legislative.title, legislative.description))
        self.assertEqual(
            main._recover_legislative_policy_from_raw(final_by_section, {"policy": [legislative]}, max_items=3),
            1,
        )

        titles = {article.title for article in final_by_section["policy"]}
        core_titles = {article.title for article in final_by_section["policy"] if article.is_core}
        self.assertIn(legislative.title, titles)
        self.assertNotIn(macro_core.title, titles)
        self.assertIn(price_system.title, core_titles)
        self.assertIn(legislative.title, core_titles)
        self.assertEqual(len(core_titles), 2)

    def test_optional_policy_macro_tail_drops_only_above_minimum(self) -> None:
        price_system = self._make_article(
            section="policy",
            title="농산물가격안정제도 8월 시행…평균가격, 경영비 밑돌땐 차액 지원",
            description="농식품부가 농안법 시행령 개정안을 입법예고하고 기준가격과 차액 지원 방식을 정했다.",
            link="https://example.com/price-system",
        )
        legislative = self._make_article(
            section="policy",
            title="‘농업민생’ 입법에 여야 합심…농협법·농지법 개정 난제 산적",
            description="국회가 농업 민생 입법으로 농협법과 농지법 개정을 논의하고 농정 제도 개선 쟁점을 다룬다.",
            link="https://example.com/legislative",
            press="농민신문",
        )
        macro_tail = self._make_article(
            section="policy",
            title="슈퍼 엘리뇨·이란전쟁 장기화…애그플레이션 우려",
            description="기후와 원자재 가격 상승으로 농산물 물가 부담이 커질 수 있다는 분석이다.",
            link="https://example.com/agflation",
        )
        producer_price = self._make_article(
            section="policy",
            title="4월 생산자물가 2.5%↑…석탄·석유 가격이 끌어올려",
            description="생산자물가 상승률이 높아졌고 일부 농식품 가격 부담이 이어졌다.",
            link="https://example.com/ppi",
        )
        price_system.is_core = True
        legislative.is_core = True
        final_by_section = {"policy": [price_system, legislative, macro_tail, producer_price]}

        self.assertEqual(main._drop_optional_policy_macro_tail(final_by_section, min_items=3), 1)
        self.assertNotIn(macro_tail, final_by_section["policy"])
        self.assertEqual(len(final_by_section["policy"]), 3)

        final_by_section = {"policy": [price_system, legislative, macro_tail]}
        self.assertEqual(main._drop_optional_policy_macro_tail(final_by_section, min_items=3), 0)
        self.assertIn(macro_tail, final_by_section["policy"])

    def test_supply_board_price_tail_replaced_by_response_story_without_underfill(self) -> None:
        onion_core = self._make_article(
            section="supply",
            title='"㎏당 500원도 안해… 양파 농사 포기하고 싶다"',
            description="양파 산지 가격 급락으로 농가 손실이 커지고 있다.",
            link="https://example.com/onion-core",
        )
        storage_core = self._make_article(
            section="supply",
            title="햇 양파 보관 어쩌라고...지난해산 비축분 폐기 ‘세월아 네월아’",
            description="지난해산 양파 비축분 폐기가 지연되며 햇양파 보관 공간 부족이 우려된다.",
            link="https://example.com/onion-storage",
            press="농민신문",
        )
        board_tail = self._make_article(
            section="supply",
            title="[한눈에 보는 시세] 양배추, 반입량 많고 소비는 침체…‘약세늪’서 허덕",
            description="양배추 반입량과 소비 부진으로 도매가격이 약세를 보였다.",
            link="https://example.com/cabbage-board",
            press="농민신문",
        )
        response = self._make_article(
            section="supply",
            title="고흥군, 양파 400톤 시장격리…수급 안정 대책 본격화",
            description="양파 공급과잉과 가격 급락에 대응해 400톤 시장격리와 수급 안정 대책을 추진한다.",
            link="https://example.com/onion-market-isolation",
            press="아시아투데이",
        )
        onion_core.is_core = True
        storage_core.is_core = True
        final_by_section = {"supply": [onion_core, storage_core, board_tail]}

        self.assertEqual(main._replace_supply_board_price_tail_from_raw(final_by_section, {"supply": [response]}), 1)

        links = {article.link for article in final_by_section["supply"]}
        self.assertEqual(len(final_by_section["supply"]), 3)
        self.assertIn(response.link, links)
        self.assertNotIn(board_tail.link, links)

    def test_dist_tail_replacement_preserves_count_when_better_raw_candidate_exists(self) -> None:
        dist_core = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 반입 물류 효율화를 위해 파렛트 운송지원 물량을 확대한다.",
            link="https://example.com/dist-core",
        )
        weak_tail = self._make_article(
            section="dist",
            title="스마트팜·신품종 보급…품목맞춤형 접근 필요",
            description="기후변화 대응을 위해 시설원예 스마트팜과 신품종 보급 지원체계를 제안했다.",
            link="https://example.com/dist-weak",
        )
        replacement = self._make_article(
            section="dist",
            title="가락시장 채소류 반입 물류비 정산 개선",
            description="가락시장 채소 반입과 하역, 물류비 정산 절차를 개선해 도매시장 운영 효율을 높인다.",
            link="https://example.com/dist-replacement",
        )
        dist_core.is_core = True
        final_by_section = {"dist": [dist_core, weak_tail]}

        self.assertEqual(
            main._replace_optional_dist_tail_from_raw(final_by_section, {"dist": [replacement]}),
            1,
        )
        self.assertEqual(len(final_by_section["dist"]), 2)
        self.assertIn(replacement.link, {article.link for article in final_by_section["dist"]})
        self.assertNotIn(weak_tail.link, {article.link for article in final_by_section["dist"]})

    def test_dist_reservation_tail_replacement_preserves_count(self) -> None:
        dist_core = self._make_article(
            section="dist",
            title="가락시장 하역노동자, 주5일 일할 수 있을까?",
            description="가락시장 도매시장 반입과 하역 운영 체계 개편을 둘러싼 현장 쟁점을 다뤘다.",
            link="https://example.com/dist-core-ops",
        )
        reservation_tail = self._make_article(
            section="dist",
            title="농협 유통 하나로마트, '매실' 본격출하!..사전 예약 중",
            description="하나로마트가 햇매실 사전 예약 판매를 진행하며 행사 가격을 안내한다는 기사다.",
            link="https://example.com/reservation",
        )
        replacement = self._make_article(
            section="dist",
            title="가락시장 채소류 반입 물류비 정산 개선",
            description="가락시장 채소 반입과 하역, 물류비 정산 절차를 개선해 도매시장 운영 효율을 높인다.",
            link="https://example.com/dist-replacement-ops",
        )
        dist_core.is_core = True
        final_by_section = {"dist": [dist_core, reservation_tail]}

        self.assertTrue(main._is_optional_dist_editorial_tail(reservation_tail))
        self.assertEqual(
            main._replace_optional_dist_tail_from_raw(final_by_section, {"dist": [replacement]}),
            1,
        )
        self.assertEqual(len(final_by_section["dist"]), 2)
        self.assertIn(replacement.link, {article.link for article in final_by_section["dist"]})
        self.assertNotIn(reservation_tail.link, {article.link for article in final_by_section["dist"]})

    def test_dist_replacement_allows_distinct_structural_market_story(self) -> None:
        pallet_core = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 파렛트 운송지원 사업으로 출하율 88%와 운송비 지원금 확대가 제시됐다.",
            link="https://example.com/pallet",
        )
        weak_training = self._make_article(
            section="dist",
            title='[동화청과 유통교육] "맛·품질은 기본…소비자 선택 기준까지 설계 필요"',
            description="청년농 교육에서 소비자 선택 기준과 상품 기획 강연이 진행됐다.",
            link="https://example.com/training",
        )
        cooperation = self._make_article(
            section="dist",
            title='"대구·경북 농산물 유통협력 강화"',
            description=(
                "대구농수산물유통관리공사와 경상북도가 농산물 유통 효율화와 상생형 유통체계 구축을 논의했다. "
                "도매시장 거래 활성화, 출하 집중 시 물량 분산과 가격 안정, 온라인도매시장 활용 및 "
                "산지-소비지 연계 유통모델 구축 방안을 협의했다."
            ),
            link="https://example.com/cooperation",
            press="농축유통신문",
        )
        pallet_core.is_core = True
        cooperation.score = 27.21
        final_by_section = {"dist": [pallet_core, weak_training]}

        self.assertEqual(main._replace_optional_dist_tail_from_raw(final_by_section, {"dist": [cooperation]}), 1)
        self.assertIn(cooperation.link, {article.link for article in final_by_section["dist"]})
        self.assertNotIn(weak_training.link, {article.link for article in final_by_section["dist"]})

    def test_hard_metric_dist_logistics_promotes_over_labor_core(self) -> None:
        labor_core = self._make_article(
            section="dist",
            title="가락시장 하역노동자, 주5일 일할 수 있을까?",
            description="가락시장 하역노동자의 주5일 근무 전환을 둘러싼 노동 현안을 다뤘다.",
            link="https://www.laborplus.co.kr/news/articleView.html?idxno=40833",
            press="참여와혁신",
        )
        weak_tail = self._make_article(
            section="dist",
            title="스마트팜·신품종 보급…품목맞춤형 접근 필요",
            description="기후변화 대응을 위해 시설원예 스마트팜과 신품종 보급 지원체계를 제안했다.",
            link="https://example.com/dist-weak-smartfarm",
        )
        market_tail = self._make_article(
            section="dist",
            title="무안군, 양파 100톤 수도권 직거래로 판로 확보",
            description="양파 농가 판로 확보를 위해 수도권 직거래 판매를 추진했다.",
            link="https://example.com/dist-market-tail",
        )
        metric_ops = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description=(
                "가락시장 농산물 물류체계 개선을 위해 근교산 채소류와 햇감자 파렛트 운송지원 사업을 확대한다. "
                "청과부류 전체 파렛트 출하율은 88%로 전년보다 5.3%포인트 증가했고 "
                "운송비 지원금은 파렛트 1장당 평균 5500원으로 확대된다."
            ),
            link="http://www.amnews.co.kr/news/articleView.html?idxno=72651",
            press="농축유통신문",
        )
        metric_ops.score = 34.31
        labor_core.is_core = True
        final_by_section = {"dist": [labor_core, market_tail, weak_tail]}

        self.assertTrue(main.is_dist_hard_logistics_metric_context(metric_ops.title, metric_ops.description))
        self.assertEqual(main._editorial_safe_core_demote_reason(metric_ops, "dist"), "")
        self.assertEqual(main._postbuild_article_reject_reason(metric_ops, "dist"), "")
        dist_conf = next((s for s in main.SECTIONS if s.get("key") == "dist"), {})
        self.assertGreaterEqual(
            main.section_fit_score(metric_ops.title, metric_ops.description, dist_conf, metric_ops.domain, metric_ops.press),
            1.0,
        )
        self.assertEqual(main._promote_dist_hard_logistics_core(final_by_section, {"dist": [metric_ops]}), 1)

        dist_titles = {article.title: article for article in final_by_section["dist"]}
        self.assertTrue(dist_titles[metric_ops.title].is_core)
        self.assertFalse(labor_core.is_core)
        self.assertNotIn(weak_tail.link, {article.link for article in final_by_section["dist"]})

    def test_pest_tail_replacement_prefers_real_fire_blight_candidate(self) -> None:
        pest_core = self._make_article(
            section="pest",
            title="화성서 올해 첫 경기도 과수화상병 발생…확산 차단 총력",
            description="사과 과원에서 과수화상병이 발생해 방역당국이 매몰과 예찰을 강화했다.",
            link="https://example.com/pest-core",
        )
        weak_tail = self._make_article(
            section="pest",
            title="시설하우스 자두 출격",
            description="시설하우스 자두 출하가 시작됐다는 산지 소식이다.",
            link="https://example.com/plum-tail",
        )
        replacement = self._make_article(
            section="pest",
            title="농진청, 과수화상병 확산 차단…세종서 첫 과수화상병 확진",
            description="농촌진흥청이 위기단계를 높이고 세종 첫 확진 농가 주변 예찰과 방제를 강화했다.",
            link="https://example.com/fire-blight-replacement",
        )
        pest_core.is_core = True
        final_by_section = {"pest": [pest_core, weak_tail]}

        self.assertEqual(
            main._replace_weak_pest_tail_from_raw(final_by_section, {"pest": [replacement]}),
            1,
        )
        self.assertIn(replacement.link, {article.link for article in final_by_section["pest"]})
        self.assertNotIn(weak_tail.link, {article.link for article in final_by_section["pest"]})

    def test_khan_style_fire_blight_field_report_is_recalled_as_pest_risk(self) -> None:
        title = "‘치료제 없어 걸리면 답도 없다’···사과 과수원 덮친 ‘붉은 죽음’에 충북 농가 시름"
        desc = "청주 사과 과수원에서 과수화상병 확진 뒤 매몰 처분이 진행됐고 충북 전역으로 확산하고 있다."

        self.assertTrue(main.is_pest_fire_blight_farmer_risk_context(title, ""))
        self.assertTrue(main.is_pest_fire_blight_farmer_risk_context(title, desc))
        self.assertTrue(main.is_pest_fire_blight_field_report_context(title, desc))
        self.assertIn("사과 과수원 붉은 죽음", main.PEST_ALWAYS_ON_RECALL_QUERIES[:4])
        self.assertIn('"붉은 죽음" 과수화상병 농가', main.PEST_GOOGLE_NEWS_PRECISION_RECALL_QUERIES)
        self.assertIn('site:khan.co.kr "붉은 죽음" 과수화상병', main.PEST_GOOGLE_NEWS_PRECISION_RECALL_QUERIES)
        self.assertGreaterEqual(main.PEST_GOOGLE_NEWS_RECALL_QUERY_CAP, 6)
        self.assertIn("붉은 죽음", main.PEST_KHAN_SEARCH_RECALL_QUERIES)
        self.assertIn("khan.co.kr/search", main.build_khan_search_url("과수화상병"))
        recall_path = Path(main.EDITORIAL_RECALL_URLS_PATH)
        self.assertTrue(recall_path.exists())
        recall_data = json.loads(recall_path.read_text(encoding="utf-8"))
        self.assertIn(
            "https://www.khan.co.kr/article/202605280600001",
            {row.get("url") for row in recall_data.get("items", [])},
        )
        recall_start = datetime(2026, 5, 27, 6, 0, tzinfo=main.KST)
        recall_end = datetime(2026, 5, 28, 6, 0, tzinfo=main.KST)
        boundary_pub = datetime(2026, 5, 28, 6, 0, tzinfo=main.KST)
        self.assertLess(
            main._editorial_recall_window_pubdate(boundary_pub, recall_start, recall_end),
            recall_end,
        )

        article = self._make_article(
            section="pest",
            title=title,
            description=desc,
            link="https://www.khan.co.kr/article/202605280600001",
            press="경향신문",
        )
        pest_conf = next((s for s in main.SECTIONS if s.get("key") == "pest"), {})
        self.assertFalse(main._is_weak_pest_tail(article))
        self.assertIsNotNone(main._pest_replacement_candidate_rank(article, pest_conf))
        self.assertGreaterEqual(
            main.compute_rank_score(article.title, article.description, article.domain, article.pub_dt_kst, pest_conf, article.press),
            35.0,
        )

    def test_pest_field_report_replaces_weak_tail_even_when_fire_theme_exists(self) -> None:
        fire_core = self._make_article(
            section="pest",
            title="아산시, 과수화상병 차단 총력… 생육기 방제약제 전 농가 무상 지원",
            description="배·사과 농가에 과수화상병 방제 약제를 지원하고 예찰을 강화한다.",
            link="https://example.com/fire-core",
        )
        fire_core.is_core = True
        fire_tail = self._make_article(
            section="pest",
            title="수요일마다 과수화상병 예찰하세요",
            description="농진청이 과수화상병 예찰의 날을 지정하고 농가 신고를 당부했다.",
            link="https://example.com/fire-tail",
        )
        non_fire = self._make_article(
            section="pest",
            title="창원특례시, 단감 미국선녀벌레 방제 약제 지원",
            description="단감 과원 미국선녀벌레 방제 약제를 지원한다.",
            link="https://example.com/persimmon-pest",
            topic="단감",
        )
        weak_tail = self._make_article(
            section="pest",
            title="제놀루션, 차세대 친환경 RNA 작물보호제 특허 출원",
            description="작물보호제 특허 출원 소식이다.",
            link="https://example.com/weak-pest-tail",
            topic="풋고추",
        )
        weak_tail.score = 12.0
        field_report = self._make_article(
            section="pest",
            title="‘치료제 없어 걸리면 답도 없다’···사과 과수원 덮친 ‘붉은 죽음’에 충북 농가 시름",
            description="청주 사과 과수원에서 과수화상병 확진 뒤 매몰 처분이 진행됐고 충북 전역으로 확산하고 있다.",
            link="https://www.khan.co.kr/article/202605280600001",
            press="경향신문",
        )
        field_report.source_channel = "editorial_recall"
        field_report.score = 38.0
        final_by_section = {"pest": [fire_core, fire_tail, non_fire, weak_tail]}

        self.assertTrue(
            main.is_pest_fire_blight_high_impact_field_report_context(
                field_report.title, field_report.description, field_report.source_channel,
            )
        )
        self.assertTrue(main._is_weak_pest_tail(weak_tail))
        self.assertEqual(
            main._promote_pest_fire_blight_field_report_from_raw(final_by_section, {"pest": [field_report]}),
            1,
        )
        self.assertIn(field_report.link, {article.link for article in final_by_section["pest"]})
        self.assertNotIn(weak_tail.link, {article.link for article in final_by_section["pest"]})

        final_by_section["pest"] = [
            article for article in final_by_section["pest"] if article.link != field_report.link
        ] + [weak_tail]
        self.assertEqual(
            main._promote_pest_fire_blight_field_report_from_raw(final_by_section, {"pest": [field_report]}),
            1,
        )
        self.assertIn(field_report.link, {article.link for article in final_by_section["pest"]})

    def test_priority_fire_blight_promotes_national_escalation_to_core(self) -> None:
        local_core = self._make_article(
            section="pest",
            title="원주시 “과수화상병 농가, 예방 약제 미살포”",
            description="원주 과수 농가에서 과수화상병이 확인돼 예방 약제 미살포 행정 처분을 검토한다.",
            link="https://example.com/wonju-fire",
            press="KBS",
        )
        hwaseong_core = self._make_article(
            section="pest",
            title="화성서 올해 첫 경기도 과수화상병 발생…도농기원 확산 차단 총력",
            description="경기도 사과 과원에서 과수화상병이 발생해 매몰과 주변 예찰을 강화했다.",
            link="https://example.com/hwaseong-fire",
            press="경기일보",
        )
        national = self._make_article(
            section="pest",
            title="농진청, 과수화상병 확산 차단... 세종서 첫 과수화상병 확진…위기단계 상향",
            description="농촌진흥청은 세종 첫 확진에 따라 위기단계를 경계로 높이고 반경 2km 농가 정밀 예찰에 나섰다.",
            link="https://example.com/national-fire",
            press="농축유통신문",
        )
        pepper_tail = self._make_article(
            section="pest",
            title="고추 총채벌레 확산 우려…적기 방제 당부",
            description="고추 시설하우스에서 총채벌레와 바이러스 확산 우려가 커지고 있다.",
            link="https://example.com/pepper",
        )
        local_core.is_core = True
        hwaseong_core.is_core = True
        final_by_section = {"pest": [local_core, hwaseong_core, pepper_tail]}

        self.assertTrue(main.is_pest_national_fire_blight_escalation_context(national.title, national.description))
        self.assertEqual(main._promote_pest_priority_fire_blight_from_raw(final_by_section, {"pest": [national]}), 1)

        core_titles = {article.title for article in final_by_section["pest"] if article.is_core}
        self.assertIn(national.title, core_titles)
        self.assertLessEqual(len(core_titles), 2)

    def test_priority_fire_blight_prefers_national_alert_over_first_case_only(self) -> None:
        hwaseong_core = self._make_article(
            section="pest",
            title="화성서 올해 첫 경기도 과수화상병 발생…도농기원 확산 차단 총력",
            description="경기도 사과 과원에서 과수화상병이 발생해 매몰과 주변 예찰을 강화했다.",
            link="https://example.com/hwaseong-fire-alert",
            press="경기일보",
        )
        first_case_national = self._make_article(
            section="pest",
            title="농진청, 과수화상병 확산 차단... 세종서 첫 과수화상병 확진…위기단계 상향",
            description="농촌진흥청은 세종 첫 확진에 따라 위기단계를 경계로 높이고 정밀 예찰에 나섰다.",
            link="https://example.com/national-fire-first-case",
            press="농축유통신문",
        )
        national_alert = self._make_article(
            section="pest",
            title="과수화상병 확산 우려…위기 단계 ‘주의’에서 ‘경계’로",
            description="농촌진흥청이 과수화상병 위기 경보를 경계로 상향했고 전국 7개 농가 2.5헥타르에서 발생했다.",
            link="https://example.com/national-fire-alert",
            press="KBS",
        )
        pepper_tail = self._make_article(
            section="pest",
            title="고추 총채벌레 확산 우려…적기 방제 당부",
            description="고추 시설하우스에서 총채벌레와 바이러스 확산 우려가 커지고 있다.",
            link="https://example.com/pepper-alert",
        )
        hwaseong_core.is_core = True
        first_case_national.is_core = True
        final_by_section = {"pest": [hwaseong_core, first_case_national, pepper_tail]}

        self.assertTrue(main.is_pest_national_fire_blight_escalation_context(national_alert.title, national_alert.description))
        self.assertEqual(main._promote_pest_priority_fire_blight_from_raw(final_by_section, {"pest": [national_alert]}), 1)

        core_titles = {article.title for article in final_by_section["pest"] if article.is_core}
        self.assertIn(national_alert.title, core_titles)
        self.assertNotIn(first_case_national.title, {article.title for article in final_by_section["pest"]})

    def test_regional_fire_blight_response_replaces_generic_pest_tail(self) -> None:
        national_core = self._make_article(
            section="pest",
            title="농진청, 과수화상병 확산 차단... 세종서 첫 과수화상병 확진…위기단계 상향",
            description="농촌진흥청은 세종 첫 확진에 따라 위기단계를 경계로 높이고 정밀 예찰에 나섰다.",
            link="https://example.com/national-fire",
            press="농축유통신문",
        )
        generic_tail = self._make_article(
            section="pest",
            title="초기 방제 실패하면 콩 농사 끝",
            description="콩 생육 초기에 병해충 예찰과 적기 방제가 중요하다고 농촌진흥청이 밝혔다.",
            link="https://example.com/soy-pest",
        )
        pepper_tail = self._make_article(
            section="pest",
            title="고추 총채벌레 확산 우려…적기 방제 당부",
            description="고추 시설하우스에서 총채벌레와 바이러스 확산 우려가 커지고 있다.",
            link="https://example.com/pepper-tail",
        )
        regional = self._make_article(
            section="pest",
            title="충북농기원, 과수화상병 차단 총력",
            description="충북농업기술원은 과수화상병 현장진단실을 긴급 운영하고 신속 진단과 초동 방제 체계를 가동했다.",
            link="https://example.com/chungbuk-fire",
            press="농축유통신문",
        )
        national_core.is_core = True
        final_by_section = {"pest": [national_core, generic_tail, pepper_tail]}

        self.assertTrue(main.is_pest_regional_fire_blight_response_context(regional.title, regional.description))
        self.assertTrue(main.is_pest_fire_blight_diagnostics_response_context(regional.title, regional.description))
        self.assertEqual(
            main._promote_pest_regional_fire_blight_response_from_raw(final_by_section, {"pest": [regional]}),
            1,
        )
        links = {article.link for article in final_by_section["pest"]}
        self.assertIn(regional.link, links)
        self.assertNotIn(generic_tail.link, links)

    def test_generic_pest_notice_replacement_preserves_section_count(self) -> None:
        hwaseong = self._make_article(
            section="pest",
            title="화성서 올해 첫 경기도 과수화상병 발생…도농기원 확산 차단 총력",
            description="경기도 사과 과원에서 과수화상병이 발생해 매몰과 주변 예찰을 강화했다.",
            link="https://example.com/hwaseong-fire",
        )
        national = self._make_article(
            section="pest",
            title="농진청, 과수화상병 확산 차단... 세종서 첫 과수화상병 확진…위기단계 상향",
            description="농촌진흥청은 세종 첫 확진에 따라 위기단계를 경계로 높이고 정밀 예찰에 나섰다.",
            link="https://example.com/national-fire",
            press="농축유통신문",
        )
        generic_notice = self._make_article(
            section="pest",
            title="서천군 농업기술센터, 밭작물 병해충 예찰 강화",
            description="농업기술센터가 밭작물 병해충 예찰을 강화하고 농가 관리를 당부했다.",
            link="https://example.com/generic-notice",
            press="전국매일신문",
        )
        anthracnose = self._make_article(
            section="pest",
            title="딸기 육묘장 '탄저병' 주의…선제적 방제가 핵심",
            description="딸기 육묘 포장에서 탄저병 감염주 제거와 예방 약제 살포 등 초기 방제 요령을 안내했다.",
            link="https://example.com/strawberry-anthracnose",
            press="충청일보",
        )
        hwaseong.is_core = True
        national.is_core = True
        final_by_section = {"pest": [hwaseong, national, generic_notice]}

        self.assertTrue(main._is_generic_pest_notice_tail(generic_notice))
        self.assertFalse(main._is_generic_pest_notice_tail(anthracnose))
        self.assertEqual(main._replace_generic_pest_notice_tail_from_raw(final_by_section, {"pest": [anthracnose]}), 1)

        links = {article.link for article in final_by_section["pest"]}
        self.assertEqual(len(final_by_section["pest"]), 3)
        self.assertIn(anthracnose.link, links)
        self.assertNotIn(generic_notice.link, links)

    def test_preferred_count_recovery_fills_section_to_five_when_safe_raw_exists(self) -> None:
        final_articles = [
            self._make_article(
                section="supply",
                title="사과 산지 출하 물량 감소에 도매가격 상승",
                description="사과 출하 물량 감소와 도매가격 상승 흐름을 다뤘다.",
                link="https://example.com/supply-apple",
                topic="사과",
            ),
            self._make_article(
                section="supply",
                title="양파 저장 물량 줄며 산지 가격 강세",
                description="양파 저장 물량과 산지 가격 강세 흐름을 정리했다.",
                link="https://example.com/supply-onion",
                topic="양파",
            ),
            self._make_article(
                section="supply",
                title="배추 출하 조절 논의에 수급 안정 기대",
                description="배추 출하 조절과 수급 안정 대책을 다뤘다.",
                link="https://example.com/supply-cabbage",
                topic="배추",
            ),
        ]
        raw_articles = final_articles + [
            self._make_article(
                section="supply",
                title="마늘 작황 부진에 생산량 감소 우려",
                description="마늘 작황 부진과 생산량 감소 가능성을 전했다.",
                link="https://example.com/supply-garlic",
                topic="마늘",
            ),
            self._make_article(
                section="supply",
                title="감귤 출하 확대에도 품질별 가격 차 뚜렷",
                description="감귤 출하 확대와 품질별 가격 차이를 설명했다.",
                link="https://example.com/supply-citrus",
                topic="감귤",
            ),
        ]
        final_by_section = {"supply": list(final_articles)}

        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "_preferred_section_rank", side_effect=lambda section, article, conf: (article.score,) if section == "supply" else None),
        ):
            inserted = main._recover_preferred_section_counts_from_raw(final_by_section, {"supply": raw_articles})

        self.assertEqual(inserted, 2)
        self.assertEqual(len(final_by_section["supply"]), 5)
        self.assertTrue(
            all(
                article.selection_stage == "supply_preferred_count_recovery"
                for article in final_by_section["supply"]
                if article.link in {"https://example.com/supply-garlic", "https://example.com/supply-citrus"}
            )
        )

    def test_preferred_count_recovery_crossfills_foodservice_supply_chain_story(self) -> None:
        final_articles = [
            self._make_article(
                section="supply",
                title=f"{item} 산지 출하 물량 감소에 도매가격 상승",
                description=f"{item} 출하 물량 감소와 도매가격 상승 흐름을 다뤘다.",
                link=f"https://example.com/supply-{idx}",
                topic=item,
            )
            for idx, item in enumerate(("사과", "양파", "대파", "수박"), start=1)
        ]
        policy_article = self._make_article(
            section="policy",
            title='[빨라진 폭염 시계] "금(金)추 되기 전에..." 식품·식자재 업계, 벌써 비축',
            description=(
                "폭염과 폭우가 예고되자 식품업계와 식자재 업계가 배추, 무, 양파 비축을 늘리고 "
                "계약재배와 스마트팜 조달로 공급망과 수급 안정에 나섰다. 정부도 수매 비축 물량을 "
                "앞당겨 도매시장과 김치업체에 공급할 계획이다."
            ),
            link="https://www.ajunews.com/view/20260527153455412",
            press="아주경제",
            topic="정책",
        )
        policy_article.score = 43.43
        final_by_section = {"supply": list(final_articles), "policy": []}
        raw_by_section = {"supply": list(final_articles), "policy": [policy_article]}

        inserted = main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section)

        self.assertEqual(inserted, 1)
        self.assertEqual(len(final_by_section["supply"]), 5)
        picked = next(article for article in final_by_section["supply"] if article.link == policy_article.link)
        self.assertEqual(picked.section, "supply")
        self.assertEqual(picked.reassigned_from, "policy")
        self.assertEqual(picked.selection_stage, "supply_preferred_count_recovery")

    def test_napa_cabbage_board_recognizes_geumchu_supply_chain_story(self) -> None:
        article = self._make_article(
            section="policy",
            title='[빨라진 폭염 시계] "금(金)추 되기 전에..." 식품·식자재 업계, 벌써 비축',
            description=(
                "폭염과 폭우 예고로 식품업계가 배추와 무 비축을 늘리고 포장김치 업체와 "
                "식자재 업체가 계약재배, 스마트팜 조달, 공급망 관리와 도매시장 공급을 확대한다."
            ),
            link="https://www.ajunews.com/view/20260527153455412",
            press="아주경제",
            topic="정책",
        )
        article.score = 43.43
        article.selection_fit_score = 2.05
        item = next(item for item in main.MANAGED_COMMODITY_CATALOG if item.get("key") == "napa_cabbage")

        metrics = main._commodity_board_item_article_representative_metrics(item, article, include_semantic=False)

        self.assertTrue(metrics["board_eligible"])
        self.assertGreaterEqual(metrics["representative_rank"], 1)
        self.assertTrue(main._commodity_board_article_is_active_candidate(item, article, metrics))

    def test_preferred_tail_block_rejects_nonmarket_and_nonhorti_tail_noise(self) -> None:
        cosmetic = self._make_article(
            section="supply",
            title="국산 감귤, 기능성 화장품으로 대변신",
            description="감귤 추출물을 활용한 피부장벽 개선 화장품 인증 소식이다.",
            link="https://example.com/citrus-cosmetic",
            topic="감귤",
        )
        livestock = self._make_article(
            section="policy",
            title='"소양호 오염 축산 탓?" 축산농가 반발',
            description="축산농가가 환경부 발언에 반발했다.",
            link="https://example.com/livestock-policy",
            topic="축산",
        )
        smartfarm = self._make_article(
            section="dist",
            title="스마트팜·신품종 보급…품목맞춤형 접근 필요",
            description="기후변화 대응을 위해 스마트팜과 신품종 보급을 확대해야 한다는 분석이다.",
            link="https://example.com/smartfarm-variety",
            topic="스마트팜",
        )
        health = self._make_article(
            section="supply",
            title="라면, 밥과 함께 양파 꼭 먹었더니…혈당·염증에 큰 변화",
            description="양파의 건강 효능을 소개하는 소비자 생활 기사다.",
            link="https://example.com/onion-health",
            topic="양파",
        )
        livestock_lead = self._make_article(
            section="policy",
            title='"근거 없는 발언으로 축산농가 낙인"',
            description="축산농가 단체가 환경부 발언에 반발했다.",
            link="https://example.com/livestock-lead",
            topic="축산",
        )
        brand = self._make_article(
            section="supply",
            title="첨단 기술과 행정의 만남…청송사과 브랜드 혁신 이끈다",
            description="청송사과 브랜드 홍보와 행정 혁신을 소개했다.",
            link="https://example.com/apple-brand",
            topic="사과",
        )
        retail_finance = self._make_article(
            section="policy",
            title="홈플러스 청산 수순…메리츠 외면에 회생 먹구름",
            description="대형마트 회생 절차와 채권단 논의를 다뤘다.",
            link="https://example.com/homeplus",
            topic="홈플러스",
        )
        fertilizer = self._make_article(
            section="supply",
            title="작물의 밥, 비료도 알맞게 사용해야 한다",
            description="비료 사용 요령을 설명하는 일반 영농 기사다.",
            link="https://example.com/fertilizer",
            topic="비료",
        )
        local_launch = self._make_article(
            section="supply",
            title="경산 와촌 자두 출하 본격화…명품 과일 전국 공략",
            description="경산 와촌 특산품 자두 출하 소식이다.",
            link="https://example.com/local-launch-tail",
            topic="자두",
        )
        insect_feed = self._make_article(
            section="supply",
            title="비상품화 참외 등으로 곤충사료 개발",
            description="비상품화 참외를 활용한 사료 개발 기술을 소개했다.",
            link="https://example.com/insect-feed-tail",
            topic="참외",
        )
        restaurant_price = self._make_article(
            section="supply",
            title="롯데리아도 가격 오른다…고환율·채소값 부담에 외식업계 한숨",
            description="외식 프랜차이즈 가격 인상 소식이다.",
            link="https://example.com/restaurant-price",
            topic="외식",
        )
        patrol = self._make_article(
            section="policy",
            title="[패트롤] 경산시-경주시-신용보증기금",
            description="지역 기관 소식을 묶어 소개했다.",
            link="https://example.com/patrol",
            topic="지역",
        )
        expo_promo = self._make_article(
            section="policy",
            title="농업회사법인코파, SIAL 상하이서 K-파프리카 알려",
            description="중국 식품박람회에서 파프리카 브랜드 홍보를 진행했다.",
            link="https://example.com/expo-promo",
            topic="파프리카",
        )
        cosmetic_policy = self._make_article(
            section="policy",
            title="감귤로 피부장벽 기능성 화장품 개발",
            description="농진청이 감귤 추출물 화장품의 식약처 인증 확보를 알렸다.",
            link="https://example.com/citrus-cosmetic-policy",
            topic="감귤",
        )

        self.assertIn(
            main._preferred_tail_block_reason(cosmetic, "supply", current_count=4, raw_count=20),
            {"supply_nonmarket_tail", "supply_nonfood_promo_without_market_signal"},
        )
        self.assertIn(
            main._preferred_tail_block_reason(livestock, "policy", current_count=4, raw_count=20),
            {"policy_livestock_non_horti_tail", "policy_field_price_collapse_without_policy_lead"},
        )
        self.assertTrue(main._is_optional_dist_editorial_tail(smartfarm))
        self.assertEqual(
            main._preferred_tail_block_reason(health, "supply", current_count=4, raw_count=20),
            "supply_consumer_health_tail",
        )
        self.assertIn(
            main._preferred_tail_block_reason(livestock_lead, "policy", current_count=4, raw_count=20),
            {"policy_livestock_non_horti_tail", "policy_field_price_collapse_without_policy_lead"},
        )
        self.assertIn(
            main._preferred_tail_block_reason(brand, "supply", current_count=4, raw_count=20),
            {"supply_brand_promo_tail", "promotional_or_event_filler"},
        )
        self.assertEqual(
            main._preferred_tail_block_reason(retail_finance, "policy", current_count=4, raw_count=20),
            "policy_retail_finance_tail",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(fertilizer, "supply", current_count=4, raw_count=20),
            "supply_input_advice_tail",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(local_launch, "supply", current_count=3, raw_count=20),
            "",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(local_launch, "supply", current_count=4, raw_count=20),
            "supply_local_launch_preferred_tail",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(insect_feed, "supply", current_count=4, raw_count=20),
            "supply_weak_preferred_tail",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(restaurant_price, "supply", current_count=4, raw_count=20),
            "supply_restaurant_price_tail",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(patrol, "policy", current_count=4, raw_count=20),
            "policy_digest_tail",
        )
        self.assertIn(
            main._preferred_tail_block_reason(expo_promo, "policy", current_count=3, raw_count=20),
            {"policy_anchorless_preferred_tail", "policy_non_policy_product_tail", "promotional_or_event_filler"},
        )
        self.assertIn(
            main._preferred_tail_block_reason(cosmetic_policy, "policy", current_count=3, raw_count=20),
            {"policy_non_policy_product_tail", "promotional_or_event_filler"},
        )

    def test_policy_soft_fallback_allows_agflation_issue_as_fourth_card(self) -> None:
        agflation = self._make_article(
            section="policy",
            title="슈퍼 엘리뇨·이란전쟁 장기화...'애그플레이션' 시대 오나",
            description="농산물 물가와 원자재 가격 상승이 수급 대책 압력으로 이어질 수 있다는 분석이다.",
            link="https://example.com/agflation-tail",
            topic="농산물 물가",
        )

        self.assertEqual(
            main._preferred_tail_block_reason(agflation, "policy", current_count=3, raw_count=20),
            "",
        )
        self.assertTrue(main._is_soft_fallback_policy_issue_tail(agflation))
        self.assertEqual(
            main._preferred_tail_block_reason(agflation, "policy", current_count=4, raw_count=20),
            "policy_anchorless_preferred_tail",
        )

    def test_policy_macro_cleanup_keeps_national_agflation_over_local_field_support(self) -> None:
        price_system = self._make_article(
            section="policy",
            title="농산물 가격 안정제도 8월 시행…평균가격, 경영비 밑돌땐 차액 지원",
            description="농식품부가 가격안정제도 시행과 차액 지원 기준을 밝혔다.",
            link="https://example.com/policy-price-system-cleanup",
        )
        legislative = self._make_article(
            section="policy",
            title="‘농업민생’ 입법에 여야 합심…농협법·농지법 개정 난제 산적",
            description="국회가 농업 민생 입법과 농협법 개정 쟁점을 논의했다.",
            link="https://example.com/policy-legislative-cleanup",
        )
        agflation = self._make_article(
            section="policy",
            title="슈퍼 엘리뇨·이란전쟁 장기화...'애그플레이션' 시대 오나",
            description="농식품부가 국제 곡물 가격과 농산물 물가, 수급 대책을 점검했다.",
            link="https://example.com/policy-agflation-cleanup",
        )
        field_support = self._make_article(
            section="policy",
            title="생산비 폭등에 농민은 빚더미…장진영 의원, 필수 농자재 직접지원 추진",
            description="지역 의원이 필수 농자재 직접지원 조례를 추진했다.",
            link="https://example.com/policy-field-support-cleanup",
        )
        price_system.is_core = True
        legislative.is_core = True
        final_by_section = {"policy": [price_system, legislative, agflation, field_support]}

        self.assertFalse(main._is_weaker_policy_macro_story(agflation))
        self.assertEqual(main._drop_optional_policy_macro_tail(final_by_section, min_items=3), 1)

        links = {article.link for article in final_by_section["policy"]}
        self.assertIn(agflation.link, links)
        self.assertNotIn(field_support.link, links)

    def test_policy_soft_fallback_allows_field_support_issue_tail(self) -> None:
        field_support = self._make_article(
            section="policy",
            title="장진영 경남도의원, 필수 농자재 직접지원 추진",
            description="생산비 부담 완화를 위해 필수 농자재 직접지원 조례와 경영비 지원 방안을 추진한다.",
            link="https://example.com/field-support-policy",
            topic="농자재",
        )
        existing = [
            self._make_article(
                section="policy",
                title=f"농업 정책 핵심 기사 {idx}",
                description="농업 정책과 제도 개선을 다뤘다.",
                link=f"https://example.com/policy-existing-{idx}",
            )
            for idx in range(3)
        ]
        final_by_section = {"policy": existing}
        raw_by_section = {
            "policy": [
                field_support,
                *[
                    self._make_article(
                        section="policy",
                        title=f"지역 정책 단신 후보 {idx}",
                        description="지역 정책 단신이다.",
                        link=f"https://example.com/policy-raw-filler-{idx}",
                    )
                    for idx in range(3)
                ],
            ]
        }

        self.assertTrue(main._is_soft_fallback_policy_issue_tail(field_support))
        recovered = main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section)

        self.assertEqual(recovered, 1)
        self.assertIn(field_support, final_by_section["policy"])

    def test_dist_hard_logistics_promotion_does_not_move_primary_supply_price_story(self) -> None:
        price_story = self._make_article(
            section="supply",
            title="[한눈에 보는 시세] 양배추, 반입량 많고 소비는 침체…약세늪",
            description="가락시장 도매시장 양배추 반입량 1000톤, 경매가 하락과 물류 처리물량 증가를 다뤘다.",
            link="https://example.com/cabbage-price-logistics",
            topic="양배추",
        )
        dist_tail = self._make_article(
            section="dist",
            title="K-푸드는 중동 물류난에도 GCC 수출 증가",
            description="중동 물류난 속 K-푸드 수출 흐름을 다뤘다.",
            link="https://example.com/dist-export-existing",
        )
        final_by_section = {"dist": [dist_tail], "supply": [price_story]}
        raw_by_section = {"dist": [], "supply": [price_story]}

        self.assertTrue(main.is_dist_hard_logistics_metric_context(price_story.title, price_story.description))
        self.assertTrue(main.is_dist_primary_supply_price_story(price_story.title, price_story.description))
        promoted = main._promote_dist_hard_logistics_core(final_by_section, raw_by_section)

        self.assertEqual(promoted, 0)
        self.assertEqual(price_story.section, "supply")
        self.assertNotIn(price_story, final_by_section["dist"])

    def test_dist_tail_replacement_removes_primary_supply_price_story(self) -> None:
        pallet_core = self._make_article(
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            description="가락시장 농산물 물류체계 개선을 위해 파렛트 운송지원 사업을 확대한다.",
            link="https://example.com/pallet-primary-price",
            press="농축유통신문",
        )
        price_tail = self._make_article(
            section="dist",
            title="[한눈에 보는 시세] 양배추, 반입량 많고 소비는 침체…약세늪",
            description="양배추 반입량 증가와 소비 침체로 도매가격이 약세를 보인 시세 기사다.",
            link="https://example.com/cabbage-primary-price",
            topic="양배추",
            press="농민신문",
        )
        education = self._make_article(
            section="dist",
            title='[동화청과 유통교육] "맛·품질은 기본…소비자 선택 기준까지 설계 필요"',
            description="도매시장 유통 교육에서 선별, 포장, 물류 전략과 출하 기준을 공유했다.",
            link="https://example.com/dist-education-replacement",
            press="한국농업신문",
        )
        pallet_core.is_core = True
        final_by_section = {"dist": [pallet_core, price_tail]}

        self.assertTrue(main.is_dist_primary_supply_price_story(price_tail.title, price_tail.description))
        self.assertTrue(main._is_optional_dist_editorial_tail(price_tail))
        self.assertEqual(
            main._replace_optional_dist_tail_from_raw(final_by_section, {"dist": [education]}),
            1,
        )

        links = {article.link for article in final_by_section["dist"]}
        self.assertIn(education.link, links)
        self.assertNotIn(price_tail.link, links)

    def test_supply_recovery_prefers_price_crisis_response_over_local_launch(self) -> None:
        existing = [
            self._make_article(
                section="supply",
                title=f"양파 수급 핵심 기사 {idx}",
                description="양파 가격 급락과 수급 대응을 다뤘다.",
                link=f"https://example.com/onion-existing-{idx}",
            )
            for idx in range(3)
        ]
        crisis_response = self._make_article(
            section="supply",
            title="햇 양파 공급과잉에 가격 급락…정부, 수출 확대로 돌파구 모색",
            description="햇양파 공급과잉과 가격 급락에 대응해 정부가 수출 확대와 수급 안정 대책을 추진한다.",
            link="https://example.com/onion-crisis-response",
            press="미디어펜",
        )
        local_launch = self._make_article(
            section="supply",
            title="경산 와촌 시설재배 자두 본격 출하",
            description="경산 와촌 자두 출하가 시작됐다.",
            link="https://example.com/jadu-local-launch",
            topic="자두",
            press="경북매일",
        )
        final_by_section = {"supply": existing}

        recovered = main._recover_supply_underfill_from_raw(
            final_by_section,
            {"supply": [local_launch, crisis_response]},
            max_items=4,
        )

        self.assertEqual(recovered, 1)
        links = {article.link for article in final_by_section["supply"]}
        self.assertIn(crisis_response.link, links)
        self.assertNotIn(local_launch.link, links)

    def test_policy_macro_issue_with_ai_text_is_not_livestock_dominant(self) -> None:
        macro_issue = self._make_article(
            section="policy",
            title="슈퍼 엘리뇨·이란전쟁 장기화...'애그플레이션' 시대 오나",
            description=(
                "농림축산식품부가 국제 곡물 가격과 농산물 물가를 점검했고, "
                "AI 기반 수급 예측 필요성도 함께 다룬 전국 정책 이슈다."
            ),
            link="https://example.com/agflation-ai",
        )

        self.assertFalse(
            main.is_policy_livestock_dominant_context(
                macro_issue.title,
                macro_issue.description,
                macro_issue.domain,
                macro_issue.press,
            )
        )
        self.assertNotEqual(
            main._preferred_tail_block_reason(
                macro_issue,
                "policy",
                current_count=3,
                raw_count=20,
            ),
            "policy_livestock_non_horti_tail",
        )

    def test_commodity_board_drops_rank_one_non_issue_representatives(self) -> None:
        grape_item = next(item for item in main.MANAGED_COMMODITY_CATALOG if item.get("key") == "grape")
        lifestyle = self._make_article(
            section="supply",
            title="[류재국의 고전, 오늘을 말하다] 『분노의 포도』-괴물은 규칙을 따른다",
            description="문학 작품을 소개하는 칼럼으로 포도 수급이나 가격 이슈는 없다.",
            link="https://example.com/grape-literary-column",
            topic="포도",
        )

        metrics = main._commodity_board_item_article_representative_metrics(grape_item, lifestyle)

        self.assertEqual(metrics["representative_rank"], 1)
        self.assertFalse(main._commodity_board_has_operational_issue_signal(metrics))
        self.assertFalse(main._commodity_board_article_is_active_candidate(grape_item, lifestyle, metrics))

    def test_commodity_board_requires_title_item_focus_for_active_primary(self) -> None:
        tomato_item = next(item for item in main.MANAGED_COMMODITY_CATALOG if item.get("key") == "tomato")
        body_only = self._make_article(
            section="policy",
            title="통합 대한항공, 출범 앞두고 기내 생수 수급 변수",
            description="기내식 공급 설명 중 토마토와 채소가 본문에 언급되지만 제목은 항공 생수 수급 이슈다.",
            link="https://example.com/korean-air-water",
            topic="토마토",
        )
        body_only.selection_fit_score = 1.2
        body_only.selection_stage = "policy_preferred_count_recovery"

        metrics = main._commodity_board_item_article_representative_metrics(tomato_item, body_only)

        self.assertEqual(metrics["title_primary_hits"], 0)
        self.assertFalse(main._commodity_board_article_is_active_candidate(tomato_item, body_only, metrics))

    def test_supply_demotes_distribution_market_education_story(self) -> None:
        education = self._make_article(
            section="supply",
            title='[동화청과 유통교육] "맛·품질은 기본…소비자 선택 기준까지 설계 필요"',
            description="도매시장 유통교육에서 출하 전략, 품질 설계와 소비자 선택 기준을 설명했다.",
            link="https://example.com/dist-education-in-supply",
        )

        self.assertTrue(main.is_dist_market_education_tail_context(education.title, education.description))
        self.assertEqual(
            main._editorial_safe_core_demote_reason(education, "supply"),
            "supply_dist_market_education_tail",
        )

    def test_preferred_count_recovery_avoids_duplicate_nh_direct_election_policy(self) -> None:
        existing = self._make_article(
            section="policy",
            title='“농협, 직선제 받겠다”…강호동 회장 개혁안 발표',
            description="농협중앙회장 직선제 수용과 농협법 개정 논의를 다뤘다.",
            link="https://example.com/nh-direct-1",
            topic="농협",
        )
        duplicate = self._make_article(
            section="policy",
            title='강호동 농협회장 "직선제 수용"',
            description="농협중앙회가 회장 직선제를 수용하겠다고 밝혔다.",
            link="https://example.com/nh-direct-2",
            topic="농협",
        )

        self.assertTrue(
            main._candidate_conflicts_with_final(duplicate, {"policy": [existing]}, "policy")
        )

    def test_preferred_count_recovery_avoids_duplicate_ag_tax_policy_statement(self) -> None:
        existing = self._make_article(
            section="policy",
            title="농민의길 “농특세, 농산물 가격 안정에 우선 써야”",
            description="농산물 가격안정 재원으로 농특세를 우선 써야 한다고 성명을 냈다.",
            link="https://example.com/ag-tax-1",
            topic="농산물",
        )
        duplicate = self._make_article(
            section="policy",
            title='"농어촌특별세, 농산물 가격안정에 사용해야"',
            description="농어촌특별세를 농산물 가격 안정에 사용해야 한다는 같은 성명이 발표됐다.",
            link="https://example.com/ag-tax-2",
            topic="농산물",
        )

        self.assertTrue(
            main._candidate_conflicts_with_final(duplicate, {"policy": [existing]}, "policy")
        )

    def test_policy_gap_still_blocks_duplicate_ag_tax_policy_statement(self) -> None:
        existing = self._make_article(
            section="policy",
            title="농민의길 “농특세, 농산물 가격 안정에 우선 써야”",
            description="농산물 가격안정 재원으로 농특세를 우선 써야 한다고 성명을 냈다.",
            link="https://example.com/ag-tax-gap-1",
            topic="농산물",
        )
        duplicate = self._make_article(
            section="policy",
            title='"농어촌특별세, 농산물 가격안정에 사용해야"',
            description="농어촌특별세를 농산물 가격 안정에 사용해야 한다는 같은 성명이 발표됐다.",
            link="https://example.com/ag-tax-gap-2",
            topic="농산물",
        )

        self.assertTrue(
            main._candidate_conflicts_with_final(
                duplicate,
                {"policy": [existing]},
                "policy",
                allow_policy_preferred_gap=True,
            )
        )

    def test_preferred_count_recovery_uses_story_signature_for_same_section_duplicates(self) -> None:
        existing = self._make_article(
            section="supply",
            title="경산 와촌 시설재배 자두 본격 출하",
            description="경산 와촌 자두 출하가 시작됐다.",
            link="https://example.com/jadu-signature-a",
        )
        duplicate = self._make_article(
            section="supply",
            title="경산 와촌 자두 출하 본격화…명품 과일 전국 공략",
            description="경산 와촌 시설재배 자두 출하가 본격화했다.",
            link="https://example.com/jadu-signature-b",
        )

        self.assertTrue(
            main._candidate_conflicts_with_final(duplicate, {"supply": [existing]}, "supply")
        )

    def test_preferred_count_recovery_caps_pest_fire_blight_theme(self) -> None:
        existing = [
            self._make_article(
                section="pest",
                title=title,
                description="과수화상병 확산과 방제 대응을 다뤘다.",
                link=f"https://example.com/fire-{idx}",
            )
            for idx, title in enumerate(
                (
                    "과수화상병 확산 우려…위기 단계 경계",
                    "화성서 올해 첫 경기도 과수화상병 발생",
                    "충북농기원, 과수화상병 차단 총력",
                ),
                start=1,
            )
        ]
        candidate = self._make_article(
            section="pest",
            title="농진청, 세종서 첫 과수화상병 확진",
            description="과수화상병 위기단계 상향과 예찰을 다뤘다.",
            link="https://example.com/fire-4",
        )

        self.assertTrue(
            main._candidate_conflicts_with_final(candidate, {"pest": existing}, "pest")
        )

    def test_preferred_count_recovery_allows_national_fire_blight_fifth_slot(self) -> None:
        existing = [
            self._make_article(
                section="pest",
                title="아산시, 과수화상병 차단 총력…생육기 방제약제 전 농가 지원",
                description="과수화상병 확산 차단과 생육기 방제 지원을 다뤘다.",
                link="https://example.com/pest-asan",
            ),
            self._make_article(
                section="pest",
                title="수요일마다 과수화상병 예찰하세요",
                description="과수화상병 예찰과 신고 요령을 안내했다.",
                link="https://example.com/pest-wed",
            ),
            self._make_article(
                section="pest",
                title="상주시, 과수화상병 5~6월 집중 예찰·적기 방제",
                description="과수화상병 예찰과 방제 대응을 강화한다.",
                link="https://example.com/pest-sangju",
            ),
            self._make_article(
                section="pest",
                title="창원특례시, 단감 미국선녀벌레 방제 약제 지원",
                description="단감 재배 농가에 미국선녀벌레 방제 약제를 지원한다.",
                link="https://example.com/pest-persimmon",
            ),
        ]
        national = self._make_article(
            section="pest",
            title="충남 공주서 과수화상병 신규 확인…농진청, 위기 단계 '주의'→'경계' 격상",
            description="농촌진흥청이 전국 7개 농가에서 과수화상병을 확인하고 위기단계를 경계로 상향했다.",
            link="https://example.com/pest-national-alert",
            press="뉴스1",
        )
        final_by_section = {"pest": list(existing)}
        raw_by_section = {"pest": [*existing, national]}

        self.assertTrue(main.is_pest_national_fire_blight_escalation_context(national.title, national.description))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertEqual(len(final_by_section["pest"]), 5)
        self.assertIn(national.link, {article.link for article in final_by_section["pest"]})

    def test_preferred_count_recovery_allows_structural_policy_fifth_slot(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title="계란값 부담에 할인 더 키운다…한 판 1500원 지원",
                description="정부가 계란 수급 안정을 위해 할인 지원과 공급 대책을 확대한다.",
                link="https://example.com/policy-egg",
            ),
            self._make_article(
                section="policy",
                title="KREI, 농산물가격안정제 도입 앞두고 정책토론회 개최",
                description="한국농촌경제연구원이 농산물가격안정제 도입 방향과 제도 설계를 논의했다.",
                link="https://example.com/policy-krei",
                press="한국농업신문",
            ),
            self._make_article(
                section="policy",
                title="[사실은 이렇습니다] 큰 일교차로 일부 노지채소 도매가격 일시 상승",
                description="농식품부가 노지채소 도매가격 상승과 수급 안정 대책을 설명했다.",
                link="https://example.com/policy-fact",
                press="정책브리핑",
            ),
            self._make_article(
                section="policy",
                title="양파값 급락·계란값 고공행진…정부, 수급 안정·할인지원 총력",
                description="정부가 농산물 수급 안정과 할인 지원 대책을 추진한다.",
                link="https://example.com/policy-onion",
            ),
        ]
        structural = self._make_article(
            section="policy",
            title="[단독] 정부, 농산물 과잉생산 막는다…차액 보전 요건·생산량 조절 대책",
            description="정부가 농산물가격안정제 도입을 앞두고 과잉생산을 막기 위해 차액 보전 요건과 생산량 조절 장치를 마련한다.",
            link="https://example.com/policy-structural",
            press="조선비즈",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, structural]}

        self.assertTrue(main._is_policy_preferred_gap_story(structural))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertEqual(len(final_by_section["policy"]), 5)
        self.assertIn(structural.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_crossfills_policy_supply_response_gap(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격안정제 정책 점검 {idx}",
                description="정부가 농산물 가격안정제와 수급 안정 대책을 점검했다.",
                link=f"https://example.com/policy-existing-{idx}",
                press="농업신문",
                topic="농산물",
            )
            for idx in range(4)
        ]
        supply_response = self._make_article(
            section="supply",
            title='과잉 양파 "수매"·부족 계란 "수입"…정부 "6~7월 물가 안정 총력"',
            description=(
                "농식품부가 양파 정부 수매와 수출 지원, 대파·수박 수급 점검, "
                "농축산물 공급 확대와 할인지원으로 물가 안정에 총력 대응한다고 밝혔다."
            ),
            link="https://example.com/policy-supply-response",
            press="뉴스핌",
            topic="양파",
        )
        supply_response.score = 61.0
        final_by_section = {"policy": list(existing), "supply": []}
        raw_by_section = {"policy": list(existing), "supply": [supply_response]}

        self.assertTrue(main._is_policy_supply_response_gap_story(supply_response))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertEqual(len(final_by_section["policy"]), 5)
        picked = next(article for article in final_by_section["policy"] if article.link == supply_response.link)
        self.assertEqual(picked.section, "policy")
        self.assertEqual(picked.reassigned_from, "supply")

    def test_policy_supply_response_gap_keeps_official_discount_support_even_with_promo_terms(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격안정제 정책 점검 {idx}",
                description="정부가 농산물 가격안정제와 수급 안정 대책을 점검했다.",
                link=f"https://example.com/policy-official-discount-existing-{idx}",
                press="농업신문",
                topic="농산물",
            )
            for idx in range(4)
        ]
        official_response = self._make_article(
            section="policy",
            title="농식품부, 여름철 농축산물 수급 불안 대비 공급 확대·할인지원",
            description=(
                "농식품부가 여름철 농축산물 수급 불안에 대비해 공급 확대와 할인지원을 추진하고 "
                "소비자 체감 물가 안정을 위해 대형마트 기획전도 병행한다고 밝혔다."
            ),
            link="https://example.com/policy-official-discount-support",
            press="경남일보",
            topic="농축산물",
        )
        official_response.score = 79.0
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, official_response]}

        self.assertFalse(main.is_low_value_local_promo_context(official_response.title, official_response.description))
        self.assertTrue(main._is_policy_supply_response_gap_story(official_response))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(official_response.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_keeps_policy_e_invoice_price_response(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격 안정 정책 점검 {idx}",
                description="정부가 농산물 가격 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-einvoice-existing-{idx}",
                topic="정책",
            )
            for idx in range(4)
        ]
        e_invoice = self._make_article(
            section="policy",
            title="정부, 널뛰는 농산물 가격에 전자송품장·출하비용 보전 추진",
            description="정부가 농산물 가격 변동을 줄이기 위해 전자송품장과 출하비용 보전 제도를 추진한다.",
            link="https://example.com/policy-einvoice-price-response",
            press="중앙일보",
            topic="정책",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, e_invoice]}

        self.assertTrue(main._is_policy_supply_response_gap_story(e_invoice))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertEqual(len(final_by_section["policy"]), 5)
        self.assertIn(e_invoice.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_keeps_supply_procurement_gap_story(self) -> None:
        existing = [
            self._make_article(
                section="supply",
                title=f"{item} 산지 출하 물량 감소에 도매가격 상승",
                description=f"{item} 출하 물량 감소와 도매가격 상승 흐름을 다뤘다.",
                link=f"https://example.com/supply-proc-existing-{idx}",
                topic=item,
            )
            for idx, item in enumerate(("사과", "양파", "배추", "수박"), start=1)
        ]
        procurement = self._make_article(
            section="supply",
            title="진주문산농협, 못난이 매실 가공용 수매 지원 나선다",
            description="농협이 규격외 매실을 가공용으로 수매해 농가 판로와 가격 지지를 돕는다.",
            link="https://example.com/supply-maesil-procurement",
            press="농민신문",
            topic="매실",
        )
        final_by_section = {"supply": list(existing)}
        raw_by_section = {"supply": [*existing, procurement]}

        self.assertTrue(main._is_supply_field_support_gap_story(procurement))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertEqual(len(final_by_section["supply"]), 5)
        self.assertIn(procurement.link, {article.link for article in final_by_section["supply"]})

    def test_supply_underfill_recovery_keeps_direct_procurement_gap_despite_broad_supply_similarity(self) -> None:
        existing = [
            self._make_article(
                section="supply",
                title="기온 상승에 채소·축산물 '들썩'…여름철 수급 안정 '가동'",
                description="정부가 여름철 채소와 축산물 수급 안정을 위해 공급 물량과 가격 동향을 점검했다.",
                link="https://example.com/supply-broad-stabilization",
                topic="채소",
            ),
            self._make_article(
                section="supply",
                title='농식품부 "대파·수박 가격 하락…계란은 7월 이후 수급 안정"',
                description="농식품부가 대파와 수박 가격 하락, 계란 수급 안정 전망을 발표했다.",
                link="https://example.com/supply-ministry-price",
                topic="수박",
            ),
            self._make_article(
                section="supply",
                title="때이른 더위에 수박 소비 늘며 가격 부담",
                description="수박 소비와 가격 부담을 다룬 산지·소비 현장 기사다.",
                link="https://example.com/supply-watermelon",
                topic="수박",
            ),
        ]
        onion_procurement = self._make_article(
            section="supply",
            title="'공급과잉' 양파 가격 뚝…수매비축 늘리고 수출 돕는다",
            description="정부가 공급과잉으로 떨어진 양파 가격 지지를 위해 수매·매입을 늘리고 소비촉진과 수출 지원에 나선다.",
            link="https://example.com/supply-onion-procurement",
            press="아시아투데이",
            topic="양파",
        )
        onion_procurement.score = 26.5
        final_by_section = {"supply": list(existing)}
        raw_by_section = {"supply": [*existing, onion_procurement]}

        self.assertTrue(main._is_supply_field_support_gap_story(onion_procurement))
        self.assertEqual(main._recover_supply_underfill_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(onion_procurement.link, {article.link for article in final_by_section["supply"]})

    def test_preferred_count_recovery_keeps_policy_fertilizer_support_gap_story(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 수급 안정 정책 점검 {idx}",
                description="정부가 농산물 수급 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-fert-existing-{idx}",
                press="농업신문",
                topic="농산물",
            )
            for idx in range(4)
        ]
        fertilizer = self._make_article(
            section="policy",
            title="정부, 무기질비료 보조금 115억 긴급 투입",
            description="농식품부가 농가 부담 완화를 위해 무기질비료 구입 보조금을 긴급 지원한다.",
            link="https://example.com/policy-fertilizer-support",
            press="농식품부",
            topic="비료",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, fertilizer]}

        self.assertTrue(main._is_policy_fertilizer_support_gap_story(fertilizer))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertEqual(len(final_by_section["policy"]), 5)
        self.assertIn(fertilizer.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_allows_central_and_local_fertilizer_support(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격 안정 정책 점검 {idx}",
                description="정부가 농산물 가격 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-fert-pair-existing-{idx}",
                topic="농산물",
            )
            for idx in range(3)
        ]
        central = self._make_article(
            section="policy",
            title="정부, 무기질비료 보조금 115억 긴급 투입",
            description="농식품부가 농가 부담 완화를 위해 무기질비료 구입 보조금을 긴급 지원한다.",
            link="https://example.com/policy-fertilizer-central",
            press="농식품부",
            topic="비료",
        )
        local = self._make_article(
            section="policy",
            title="횡성군, 2027년 유기질 비료 지원사업 접수 시작",
            description="횡성군이 농가 경영비 부담 완화를 위해 유기질 비료 지원사업 신청을 받는다.",
            link="https://example.com/policy-fertilizer-local",
            press="강원도민일보",
            topic="비료",
        )
        dist_context = self._make_article(
            section="dist",
            title="고당도 ‘다올찬수박’ 본격 출하",
            description="음성 지역 수박 공선회가 본격 출하에 들어가 전국 시장 공급을 시작했다.",
            link="https://example.com/dist-watermelon-context",
            topic="수박",
        )
        final_by_section = {"policy": list(existing), "dist": [dist_context]}
        raw_by_section = {"policy": [*existing, central, local], "dist": [dist_context]}

        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 2)
        links = {article.link for article in final_by_section["policy"]}
        self.assertIn(central.link, links)
        self.assertIn(local.link, links)

    def test_preferred_count_recovery_keeps_policy_climate_adaptation_gap_story(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 수급 안정 정책 점검 {idx}",
                description="정부가 농산물 수급 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-climate-existing-{idx}",
                topic="농산물",
            )
            for idx in range(4)
        ]
        climate = self._make_article(
            section="policy",
            title="시설하우스 ‘천장 환기창’ 달아 폭염 극복",
            description="농업기술원이 시범사업으로 시설하우스 농가에 천장 환기창 기술과 시설 개선을 지원해 작물 고온 피해를 줄인다.",
            link="https://example.com/policy-greenhouse-heat",
            press="농민신문",
            topic="시설하우스",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, climate]}

        self.assertTrue(main._is_policy_climate_adaptation_gap_story(climate))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(climate.link, {article.link for article in final_by_section["policy"]})

    def test_policy_climate_adaptation_gap_allows_coop_local_program(self) -> None:
        climate = self._make_article(
            section="policy",
            title="시설하우스 ‘천장 환기창’ 달아 폭염 극복",
            description="대호지농협이 시설하우스 농가에 천장 환기창 27동 설치 지원을 지자체 협력사업으로 추진해 작물 고온 피해를 줄인다.",
            link="https://example.com/policy-greenhouse-coop",
            press="농민신문",
            topic="시설하우스",
        )
        shipment = self._make_article(
            section="policy",
            title="시설하우스 자두 출격",
            description="시설하우스 자두 출하가 시작됐다는 산지 소식이다.",
            link="https://example.com/greenhouse-shipment",
            press="지역신문",
            topic="자두",
        )

        self.assertTrue(main._is_policy_climate_adaptation_gap_story(climate))
        self.assertFalse(main._is_policy_climate_adaptation_gap_story(shipment))

    def test_preferred_count_recovery_keeps_policy_agri_finance_support_gap_story(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격 안정 정책 점검 {idx}",
                description="정부가 농산물 가격 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-finance-existing-{idx}",
                topic="농산물",
            )
            for idx in range(4)
        ]
        finance = self._make_article(
            section="policy",
            title="도시 농축협, 무이자자금 3771억원 지원",
            description="농협중앙회 상생협력위원회가 농촌지역 농축협의 경제사업 활성화를 위해 도농상생기금 3771억원을 지원한다.",
            link="https://example.com/policy-finance-support",
            press="농축유통신문",
            topic="농협",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, finance]}

        self.assertTrue(main._is_policy_agri_finance_support_gap_story(finance))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(finance.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_rejects_broad_agri_finance_fund_tail(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격 안정 정책 점검 {idx}",
                description="정부가 농산물 가격 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-broad-finance-existing-{idx}",
                topic="농산물",
            )
            for idx in range(4)
        ]
        broad_fund = self._make_article(
            section="policy",
            title="농협 상생협력위원회, '도농상생기금' 3771억원 지원",
            description="농협중앙회 상생협력위원회가 농촌지역 농축협의 경제사업 활성화를 위해 도농상생기금 3771억원을 지원한다.",
            link="https://example.com/policy-broad-finance-fund",
            press="농축유통신문",
            topic="농협",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, broad_fund]}

        self.assertFalse(main._is_policy_agri_finance_support_gap_story(broad_fund))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 0)
        self.assertNotIn(broad_fund.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_keeps_policy_farm_cost_support_gap_story(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격 안정 정책 점검 {idx}",
                description="정부가 농산물 가격 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-cost-existing-{idx}",
                topic="농산물",
            )
            for idx in range(4)
        ]
        farm_cost = self._make_article(
            section="policy",
            title="농협, 민생 지원에 1142억 투입…장바구니 덜고 영농비도 낮췄다",
            description="농협이 농가 영농비 부담 완화와 농축산물 물가 안정을 위해 1142억원 규모 지원 대책을 추진한다.",
            link="https://example.com/policy-farm-cost-support",
            press="한국일보",
            topic="농협",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, farm_cost]}

        self.assertTrue(main._is_policy_agri_finance_support_gap_story(farm_cost))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(farm_cost.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_keeps_policy_supplier_payment_gap_story(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격 안정 정책 점검 {idx}",
                description="정부가 농산물 가격 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-payment-existing-{idx}",
                topic="농산물",
            )
            for idx in range(4)
        ]
        payment_gap = self._make_article(
            section="policy",
            title="홈플러스 미정산 2000억 추산…농산물 납품업체·농가 생존 위기",
            description=(
                "홈플러스 회생 이후 납품대금 정산 지연이 커지며 농산물 협력업체와 "
                "산지 농가 피해 부담이 확대돼 대책을 호소하고 있다."
            ),
            link="https://example.com/policy-supplier-payment-gap",
            press="경북일보",
            topic="농산물",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": [*existing, payment_gap]}

        self.assertFalse(main.is_low_value_local_political_context(payment_gap.title, payment_gap.description))
        self.assertEqual(main._postbuild_article_reject_reason(payment_gap, "policy", apply_selection_fit=False), "")
        self.assertTrue(main._is_policy_agri_supplier_payment_gap_story(payment_gap))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(payment_gap.link, {article.link for article in final_by_section["policy"]})

    def test_preferred_count_recovery_crossfills_supplier_payment_gap_from_supply_raw(self) -> None:
        existing = [
            self._make_article(
                section="policy",
                title=f"농산물 가격 안정 정책 점검 {idx}",
                description="정부가 농산물 가격 안정과 농가 지원 대책을 점검했다.",
                link=f"https://example.com/policy-payment-cross-existing-{idx}",
                topic="농산물",
            )
            for idx in range(4)
        ]
        payment_gap = self._make_article(
            section="supply",
            title="홈플러스 회생 이후 납품대금 정산 지연…농산물 협력업체 부담 확대",
            description=(
                "홈플러스 납품대금 정산 지연으로 농산물 협력업체와 산지 농가 피해 부담이 커져 "
                "정부와 국회에 대책을 호소하고 있다."
            ),
            link="https://example.com/supply-origin-policy-payment-gap",
            press="중도일보",
            topic="농산물",
        )
        final_by_section = {"policy": list(existing)}
        raw_by_section = {"policy": list(existing), "supply": [payment_gap]}

        self.assertTrue(main._is_policy_agri_supplier_payment_gap_story(payment_gap))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(payment_gap.link, {article.link for article in final_by_section["policy"]})
        self.assertEqual(final_by_section["policy"][-1].section, "policy")

    def test_policy_editorial_guard_marks_broad_national_task_tail_weak(self) -> None:
        broad_tail = self._make_article(
            section="policy",
            title="친환경 유기농업 2배 확대, 국정과제 이행 '역량 집중'",
            description="정부 국정과제 이행 계획과 친환경농업 확대 방향을 소개하는 행사성 브리핑이다.",
            link="https://example.com/policy-organic-task",
            press="한국농어민신문",
            topic="농업",
        )

        self.assertTrue(main._is_policy_editorial_weak_tail(broad_tail))
        self.assertFalse(main._is_policy_broad_editorial_replacement(broad_tail))

    def test_policy_editorial_guard_rejects_event_campaign_tail(self) -> None:
        campaign_tail = self._make_article(
            section="policy",
            title="양파 1망 사면 100원 기부…농협, 1150개 매장서 상생 캠페인",
            description="농협이 양파 소비 촉진을 위해 상생 캠페인과 기부 행사를 진행한다고 밝혔다.",
            link="https://example.com/policy-onion-campaign-tail",
            press="농민신문",
            topic="양파",
        )
        organic_event = self._make_article(
            section="policy",
            title="농식품부, '2026 유기농데이 기념행사' 개최…친환경 소비 촉진 나선다",
            description="농식품부가 유기농데이 기념행사를 열고 친환경 농산물 소비 촉진을 홍보한다.",
            link="https://example.com/policy-organic-event-tail",
            press="농축유통신문",
            topic="농산물",
        )

        for article in (campaign_tail, organic_event):
            self.assertTrue(main.is_low_value_local_promo_context(article.title, article.description))
            self.assertEqual(main._postbuild_article_reject_reason(article, "policy"), "low_value_local_promo")
            self.assertTrue(main._is_policy_editorial_weak_tail(article))
            self.assertFalse(main._is_policy_broad_editorial_replacement(article))

    def test_local_political_filter_keeps_direct_field_supply_harvest_story(self) -> None:
        harvest_story = self._make_article(
            section="supply",
            title="소비 부진에 '스펀지 마늘'까지…'한숨' 속 수확철",
            description="마늘 수확철 산지에서 소비 부진과 품질 저하가 겹쳐 농가 가격 부담이 커지고 있다.",
            link="https://example.com/supply-garlic-harvest-slump",
            press="지역방송",
            topic="마늘",
        )

        self.assertFalse(main.is_low_value_local_political_context(harvest_story.title, harvest_story.description))
        self.assertEqual(main._postbuild_article_reject_reason(harvest_story, "supply", apply_selection_fit=False), "")

    def test_preferred_count_recovery_allows_dist_online_wholesale_fifth_slot(self) -> None:
        existing = [
            self._make_article(
                section="dist",
                title=title,
                description=desc,
                link=f"https://example.com/dist-existing-{idx}",
                press="농민신문",
                topic=topic,
            )
            for idx, (title, desc, topic) in enumerate(
                (
                    ("논산 수박 판촉전 전량 매진", "수도권 하나로마트에서 수박 판촉전과 직거래 판매가 진행됐다.", "수박"),
                    ("완주 흑피수박 본격 출하", "산지 농협이 흑피수박 출하식을 열고 시장 공급을 시작했다.", "수박"),
                    ("친환경농산물 급식 물류센터 시범 운영", "친환경농산물 물류센터가 학교급식 납품 정보를 제공한다.", "친환경농산물"),
                    ("성주참외 일본 판촉행사 호평", "성주참외 수출 확대를 위한 일본 소비자 판촉행사가 열렸다.", "참외"),
                ),
                start=1,
            )
        ]
        online_market = self._make_article(
            section="dist",
            title="강원농협·농협공판장, 온라인 도매시장 활성화 앞장",
            description=(
                "강원농협과 농협공판장이 온라인 도매시장 출하 업무협약을 맺고 "
                "강원지역 우수 농산물의 온라인 도매시장 취급 확대와 유통 구조 개선에 나섰다."
            ),
            link="https://example.com/dist-online-wholesale",
            press="강원일보",
            topic="농산물",
        )
        online_market.score = 70.0
        final_by_section = {"dist": list(existing)}
        raw_by_section = {"dist": [*existing, online_market]}

        self.assertTrue(main._is_dist_preferred_gap_story(online_market))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertEqual(len(final_by_section["dist"]), 5)
        self.assertIn(online_market.link, {article.link for article in final_by_section["dist"]})

    def test_dist_editorial_guard_marks_entry_briefing_tail_optional(self) -> None:
        entry_briefing = self._make_article(
            section="dist",
            title="[전남농협 소식] 유통센터 담당자 대상 '싱씽몰' 입점 설명회",
            description=(
                "전남 권역 APC 산지유통센터 운영 농협 담당자를 대상으로 농협몰 입점 설명회를 열고 "
                "온라인 판로 확대 방안을 안내했다."
            ),
            link="https://example.com/dist-entry-briefing",
            press="SIDAE",
            topic="농산물",
        )

        self.assertEqual(
            main._editorial_safe_core_demote_reason(entry_briefing, "dist"),
            "promotional_or_event_filler",
        )
        self.assertTrue(main._is_optional_dist_editorial_tail(entry_briefing))

    def test_dist_replacement_rejects_bank_president_lecture_news_tail(self) -> None:
        lecture_tail = self._make_article(
            section="dist",
            title="[경남농협 소식] 강태영 농협은행장 경상국립대서 특강",
            description="농협은행장이 경상국립대에서 청년과 농업의 미래를 주제로 특강을 진행하고 지역 농협 소식을 전했다.",
            link="https://example.com/dist-bank-president-lecture",
            press="뉴스1",
            topic="농협",
        )

        self.assertIsNone(main._dist_replacement_candidate_rank(lecture_tail, next(s for s in main.SECTIONS if s.get("key") == "dist")))
        self.assertFalse(main._is_dist_preferred_gap_story(lecture_tail))

    def test_dist_preferred_gap_rejects_anchorless_lowprice_legal_case(self) -> None:
        legal_case = self._make_article(
            section="dist",
            title="[예규·판례] “못난이라 반값?”…中 건조고추 ‘저가 신고’ 전말",
            description="수입 건조고추 저가 신고와 관세 판례를 다룬 법률성 해설 기사다.",
            link="https://example.com/dist-lowprice-legal-case",
            press="세정일보",
            topic="고추",
        )

        self.assertFalse(main._is_dist_preferred_gap_story(legal_case))
        self.assertIsNone(main._dist_replacement_candidate_rank(legal_case, next(s for s in main.SECTIONS if s.get("key") == "dist")))

    def test_dist_preferred_gap_accepts_direct_export_shipment_story(self) -> None:
        export_story = self._make_article(
            section="dist",
            title="대전산 씨 없는 포도, 대만에 320kg 수출",
            description=(
                "대전 산내농협 공동선별·출하를 통해 생산된 델라웨어 포도 320kg이 "
                "대만으로 선적됐고 잔류농약 검정을 통과했다."
            ),
            link="https://example.com/dist-grape-export",
            press="연합뉴스TV",
            topic="포도",
        )

        self.assertTrue(main._is_dist_preferred_gap_story(export_story))
        self.assertIsNotNone(main._dist_preferred_gap_rank(export_story, next(s for s in main.SECTIONS if s.get("key") == "dist")))
        self.assertEqual(main._postbuild_article_reject_reason(export_story, "dist"), "")

    def test_preferred_count_recovery_crossfills_dist_export_gap_from_supply_raw(self) -> None:
        existing = [
            self._make_article(
                section="dist",
                title=title,
                description=desc,
                link=f"https://example.com/dist-export-cross-existing-{idx}",
                press="농민신문",
                topic=topic,
            )
            for idx, (title, desc, topic) in enumerate(
                (
                    ("청도 농산물 공판장 일제 개장", "청도 농산물 공판장이 경매와 출하를 시작했다.", "농산물"),
                    ("광주농협, 농산물 판로 지원 총력", "농협이 산지 농산물 판로 확대와 유통 지원을 추진했다.", "농산물"),
                    ("제주 항만 검역 탐지견 운영 확대", "제주 항만에서 농산물 검역 현장 대응 역량을 강화했다.", "농산물"),
                    ("함양 양파 수급 안정 직거래 추진", "함양군과 농협이 양파 수급 안정과 소비지 판로 확보에 나섰다.", "양파"),
                ),
                start=1,
            )
        ]
        export_story = self._make_article(
            section="supply",
            title="대전산 씨 없는 포도, 대만에 320kg 수출",
            description=(
                "대전산내농협 공동선별·출하를 통해 생산된 델라웨어 포도 320kg이 "
                "대만으로 선적됐고 잔류농약 검정을 통과했다."
            ),
            link="https://example.com/supply-origin-dist-grape-export",
            press="연합뉴스TV",
            topic="포도",
        )
        final_by_section = {"dist": list(existing)}
        raw_by_section = {"dist": list(existing), "supply": [export_story]}

        self.assertTrue(main._is_dist_preferred_gap_story(export_story))
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(export_story.link, {article.link for article in final_by_section["dist"]})

    def test_preferred_count_recovery_keeps_structural_apc_gap_despite_dist_similarity(self) -> None:
        existing = [
            self._make_article(
                section="dist",
                title=title,
                description=desc,
                link=f"https://example.com/dist-apc-existing-{idx}",
                press="농민신문",
                topic="농산물",
            )
            for idx, (title, desc) in enumerate(
                (
                    (
                        "고품질 농산물 유통 새로운 표준 세운다",
                        "산지유통센터와 스마트 APC 운영 준비를 통해 AI 기반 산지 유통 데이터 공유를 추진한다.",
                    ),
                    ("농협, 양파 해외 수출로 돌파구 마련", "함양 양파 대만 수출 선적식을 열고 수출 판로를 확대했다."),
                    ("순천 매실 본격 출하", "순천 매실이 산지에서 본격 출하돼 전국 소비지로 공급된다."),
                    ("CA 수출 품질 관리 프로그램 공개", "원예작물 수출 전후 품질 관리 정보를 제공한다."),
                ),
                start=1,
            )
        ]
        structural_gap = self._make_article(
            section="dist",
            title="스마트 APC 성패여부, AI 기반 산지 유통 데이터 공유에 달렸다",
            description="농산물 산지 유통 경쟁력 강화를 위해 APC 운영 데이터 공유와 유통 구조 개선이 핵심 과제로 제시됐다.",
            link="https://example.com/dist-smart-apc-data-share",
            press="원예산업신문",
            topic="농산물",
        )
        final_by_section = {"dist": list(existing)}
        raw_by_section = {"dist": [*existing, structural_gap]}

        self.assertTrue(main._is_dist_structural_ops_gap_story(structural_gap))
        self.assertTrue(
            any(main._is_similar_story(structural_gap, article, "dist") for article in existing)
        )
        self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(structural_gap.link, {article.link for article in final_by_section["dist"]})

    def test_preferred_count_recovery_keeps_regional_dist_shipment_despite_cross_section_similarity(self) -> None:
        existing = [
            self._make_article(
                section="dist",
                title=title,
                description=desc,
                link=f"https://example.com/dist-regional-existing-{idx}",
                topic=topic,
            )
            for idx, (title, desc, topic) in enumerate(
                (
                    ("고당도 ‘다올찬수박’ 본격 출하", "음성 수박 공선회가 본격 출하에 들어갔다.", "수박"),
                    ("청도 농협공판장 일제 개장", "청도 농산물 공판장이 경매와 출하를 시작했다.", "농산물"),
                    ("제주 농산물 산지 유통 경쟁력 강화", "제주 농산물 저온유통체계 구축을 추진한다.", "농산물"),
                    ("온라인 도매시장 출하 업무협약", "농협공판장이 온라인 도매시장 출하 업무협약을 맺었다.", "농산물"),
                ),
                start=1,
            )
        ]
        policy_context = self._make_article(
            section="policy",
            title="정부, 무기질비료 보조금 115억 긴급 투입",
            description="농식품부가 농가 부담 완화를 위해 무기질비료 구입 보조금을 긴급 지원한다.",
            link="https://example.com/policy-fert-dist-context",
            press="농식품부",
            topic="비료",
        )
        regional = self._make_article(
            section="dist",
            title="여름 과일 고창 수박, 도매시장 본격 출하…공선회 중심 51만 덩이 공급",
            description="고창 수박 공선회가 산지유통센터를 통해 농산물 도매시장 출하 물량을 전국 시장에 공급한다.",
            link="https://example.com/dist-gochang-watermelon",
            press="전북일보",
            topic="수박",
        )
        dist_conf = next(s for s in main.SECTIONS if s.get("key") == "dist")
        final_by_section = {"dist": list(existing), "policy": [policy_context]}
        raw_by_section = {"dist": [*existing, regional], "policy": [policy_context]}

        original_reject = main._postbuild_article_reject_reason

        def _rank(article: main.Article, _conf: main.JsonDict) -> tuple[int, ...] | None:
            return (1,) if article.link == regional.link else None

        def _reject(article: main.Article, section_key: str, *args: object, **kwargs: object) -> str:
            if article.link == regional.link and section_key == "dist":
                return ""
            return original_reject(article, section_key, *args, **kwargs)

        with (
            patch.object(main, "_dist_replacement_candidate_rank", side_effect=_rank),
            patch.object(main, "_postbuild_article_reject_reason", side_effect=_reject),
        ):
            self.assertEqual(main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section), 1)
        self.assertIn(regional.link, {article.link for article in final_by_section["dist"]})

    def test_postbuild_rejects_foreign_unmanaged_commodity_context(self) -> None:
        ai_market = self._make_article(
            section="dist",
            title="해외 열대과일 가격은 왜 천천히 떨어지나",
            description="중국 현지 두리안과 망고 가격, 해외 바나나 유통 사례를 중심으로 소비자물가 흐름을 분석했다.",
            link="https://example.com/dist-foreign-unmanaged",
            press="뉴스핌",
            topic="농산물",
        )

        self.assertTrue(main.is_foreign_unmanaged_commodity_context(ai_market.title, ai_market.description))
        self.assertEqual(main._postbuild_article_reject_reason(ai_market, "dist"), "foreign_unmanaged_commodity")

    def test_postbuild_rejects_garbled_article_text(self) -> None:
        garbled = self._make_article(
            section="supply",
            title="국산 양파값, 수입산보다 싸진 이유는",
            description=(
                "±¹»ê ¾çÆÄ °¡°ÝÀÌ ¼öÀÔ»êº¸´Ù ³·¾ÆÁö´Â ÀÌ·ÊÀûÀÎ Çö»óÀÌ "
                "Àå±â°£ ÀÌ¾îÁö¸é¼­ ±¹³» ¾çÆÄ »ê¾÷ÀÇ ¼ö±Þ ºÒ¾ÈÁ¤¿¡ ´ëÇÑ "
                "¿ì·Á°¡ Ä¿Áö°í ÀÖ´Ù."
            ),
            link="https://example.com/garbled-onion",
            topic="양파",
        )
        clean = self._make_article(
            section="supply",
            title="국산 양파값, 수입산보다 싸진 이유는",
            description="국산 양파 가격 하락과 수입산 역전 현상을 두고 산지 수급 대책 논의가 이어졌다.",
            link="https://example.com/clean-onion",
            topic="양파",
        )

        self.assertTrue(main.is_garbled_article_text(garbled.title, garbled.description))
        self.assertEqual(main._postbuild_article_reject_reason(garbled, "supply"), "garbled_article_text")
        self.assertFalse(main.is_garbled_article_text(clean.title, clean.description))

    def test_postbuild_rejects_ai_economic_explainer_tail(self) -> None:
        explainer = self._make_article(
            section="dist",
            title="[AI로 읽는 경제] ② 농산물값은 올라갈 땐 바로 뛰는데, 왜 내릴 땐 한참 뒤에야 떨어지나",
            description="AI 핵심 요약과 산지와 식탁 사이 기획시리즈로 유통단계 시차를 설명했다.",
            link="https://example.com/dist-ai-explainer",
            press="뉴스핌",
            topic="농산물",
        )

        self.assertTrue(main.is_ai_economic_explainer_tail(explainer.title, explainer.description))
        self.assertEqual(main._postbuild_article_reject_reason(explainer, "dist"), "dist_ai_explainer_tail")

    def test_postbuild_rejects_housing_market_policy_noise(self) -> None:
        housing = self._make_article(
            section="policy",
            title="[장용동의 우리들의 주거복지] 주택시장을 보는 대통령과 시장 간의 괴리",
            description="아파트 매매와 주택시장 규제 완화 기대를 다룬 부동산 정책 칼럼이다.",
            link="https://example.com/policy-housing-market-noise",
            press="부동산뉴스",
            topic="주택시장",
        )
        final_by_section = {
            "policy": [
                self._make_article(
                    section="policy",
                    title=f"농산물 가격 안정 정책 점검 {idx}",
                    description="정부가 농산물 수급과 농가 지원 대책을 점검했다.",
                    link=f"https://example.com/policy-housing-existing-{idx}",
                    topic="농산물",
                )
                for idx in range(4)
            ] + [housing],
        }

        self.assertTrue(main.is_housing_market_policy_noise_context(housing.title, housing.description))
        self.assertEqual(main._postbuild_article_reject_reason(housing, "policy"), "housing_market_noise")
        self.assertEqual(main._preferred_tail_block_reason(housing, "policy", current_count=4, raw_count=20), "housing_market_noise")
        self.assertEqual(main._drop_hard_postbuild_rejected_final_items(final_by_section, min_items=4), 1)
        self.assertNotIn(housing, final_by_section["policy"])

    def test_postbuild_rejects_non_agri_stock_auto_and_road_policy_noise(self) -> None:
        stock = self._make_article(
            section="supply",
            title="[특징주] TS인베스트먼트, 액면병합 마치고 30일 거래 재개…기준가 2635원",
            description="코스닥 변경상장일 보통주 기준가격과 거래 재개 일정을 전한 증권 기사다.",
            link="https://example.com/stock-noise",
            press="토큰포스트",
            topic="증권",
        )
        auto = self._make_article(
            section="supply",
            title="3000만원대 중 친환경차 ‘공습’…현대차 포위전략 ‘반격’",
            description="BYD 전기차와 PHEV 출시, 현대차 HEV 라인업 확대 등 자동차 시장 수급 전략을 다뤘다.",
            link="https://example.com/auto-noise",
            press="뉴스토마토",
            topic="자동차",
        )
        road = self._make_article(
            section="policy",
            title="[민생브리핑]'성남~서초 고속도로' 추진 양재나들목 정체 줄인다",
            description="국토교통부가 10.7㎞ 왕복 4차로 민간투자사업 우선협상대상자를 선정했다.",
            link="https://example.com/road-policy-noise",
            press="정책브리핑",
            topic="교통",
        )
        final_by_section = {
            "supply": [
                self._make_article(
                    section="supply",
                    title=f"사과 가격 상승…출하량 감소 {idx}",
                    description="사과 출하량 감소와 도매가격 상승을 다뤘다.",
                    link=f"https://example.com/supply-clean-{idx}",
                    topic="사과",
                )
                for idx in range(3)
            ] + [stock, auto],
            "policy": [
                self._make_article(
                    section="policy",
                    title=f"정부 농산물 수급 안정 대책 {idx}",
                    description="정부가 농산물 수급과 가격 안정 대책을 추진한다.",
                    link=f"https://example.com/policy-clean-{idx}",
                    topic="농산물",
                )
                for idx in range(4)
            ] + [road],
        }

        self.assertTrue(main.is_commodity_corporate_stock_context(stock.title, stock.description))
        self.assertTrue(main.is_non_agri_auto_market_context(auto.title, auto.description))
        self.assertTrue(main.is_non_agri_transport_policy_context(road.title, road.description))
        self.assertEqual(main._postbuild_article_reject_reason(stock, "supply"), "commodity_corporate_stock_context")
        self.assertEqual(main._postbuild_article_reject_reason(auto, "supply"), "non_agri_auto_market_noise")
        self.assertEqual(main._postbuild_article_reject_reason(road, "policy"), "non_agri_transport_policy_noise")
        self.assertTrue(main._is_supply_publish_wrong_section_noise(stock))
        self.assertTrue(main._is_supply_publish_wrong_section_noise(auto))
        self.assertTrue(main._is_publish_policy_editorial_weak(road))
        self.assertEqual(main._drop_hard_postbuild_rejected_final_items(final_by_section, min_items=3), 3)
        self.assertNotIn(stock, final_by_section["supply"])
        self.assertNotIn(auto, final_by_section["supply"])
        self.assertNotIn(road, final_by_section["policy"])

    def test_postbuild_rejects_ai_robot_and_unmanaged_price_roundup_noise(self) -> None:
        robot = self._make_article(
            section="policy",
            title="[아이온의 AI:온] 걷고 들고 나르고…로봇이 바꾸는 산업 현장",
            description="휴머노이드와 입는 로봇, 자동차 정비사 로봇 등 일반 AI 로봇 산업 동향을 소개했다.",
            link="https://example.com/robot-industry-noise",
            press="TV조선",
            topic="AI",
        )
        roundup = self._make_article(
            section="supply",
            title="늦어지는 '장마'·무더위에 농산물값, 체리·파프리카↓ 다다기오이↑",
            description="YTN 라디오 방송에서 체리와 파프리카, 다다기오이 가격을 생활정보로 소개했다.",
            link="https://example.com/ytn-price-roundup",
            press="YTN",
            topic="농산물",
        )

        self.assertTrue(main.is_non_agri_ai_robot_industry_context(robot.title, robot.description))
        self.assertTrue(main.is_supply_unmanaged_broad_price_roundup_context(roundup.title, roundup.description))
        self.assertEqual(main._postbuild_article_reject_reason(robot, "policy"), "non_agri_ai_robot_industry_noise")
        self.assertEqual(main._postbuild_article_reject_reason(roundup, "supply"), "supply_unmanaged_broad_price_roundup")
        self.assertEqual(main._postbuild_article_reject_reason(roundup, "policy"), "supply_unmanaged_broad_price_roundup")
        self.assertTrue(main._is_publish_policy_editorial_weak(robot))
        self.assertTrue(main._is_publish_policy_editorial_weak(roundup))
        self.assertTrue(main._is_supply_publish_wrong_section_noise(roundup))

    def test_postbuild_rejects_consumer_storage_tip_from_supply(self) -> None:
        storage_tip = self._make_article(
            section="supply",
            title="감자만 따로 보관하면 손해… 사과와 함께 두니 저장 기간 길어진 이유",
            description="감자는 실온 보관 시 싹이 트기 쉽고 솔라닌 독성 위험이 있어 햇빛과 수분 노출을 피해야 한다는 생활정보 기사다.",
            link="https://example.com/potato-storage-tip",
            topic="감자",
        )

        self.assertTrue(main.is_commodity_consumer_storage_tip_context(storage_tip.title, storage_tip.description))
        self.assertEqual(
            main._postbuild_article_reject_reason(storage_tip, "supply"),
            "commodity_consumer_storage_tip",
        )

    def test_postbuild_rejects_supply_crime_incident_tail(self) -> None:
        incident = self._make_article(
            section="supply",
            title="사라진 하우스 개폐기…한라봉 농사 망쳐",
            description="제주 서귀포 하우스에서 자동개폐기 도난으로 한라봉 묘목이 고사했고 경찰 수사가 진행 중이다.",
            link="https://example.com/citrus-theft",
            topic="한라봉",
        )

        self.assertTrue(main.is_supply_crime_incident_context(incident.title, incident.description))
        self.assertEqual(
            main._postbuild_article_reject_reason(incident, "supply"),
            "agri_crime_incident_tail",
        )

    def test_postbuild_rejects_no_damage_crop_price_story_from_pest(self) -> None:
        no_damage = self._make_article(
            section="pest",
            title="광양 매실 냉해 없어 '풍작'.. 가격은 걱정",
            description="올해 냉해 피해가 없어 매실 작황이 좋지만 생산량 증가에 따른 가격 하락이 우려된다.",
            link="https://example.com/maesil-no-damage",
            topic="매실",
        )

        self.assertTrue(main.is_pest_no_damage_crop_price_context(no_damage.title, no_damage.description))
        self.assertEqual(
            main._postbuild_article_reject_reason(no_damage, "pest"),
            "pest_no_damage_crop_price",
        )

    def test_postbuild_rejects_non_agri_industrial_material_market_noise(self) -> None:
        industrial = self._make_article(
            section="supply",
            title="분리막·동박 가격반등…K배터리 소재 온기 확산",
            description="배터리 소재 업황과 동박 가격 반등으로 관련 기업 실적 개선 기대가 커지고 있다.",
            link="https://example.com/battery-material-price",
            topic="배터리",
        )

        self.assertTrue(main.is_non_agri_industrial_material_market_context(industrial.title, industrial.description))
        self.assertEqual(
            main._postbuild_article_reject_reason(industrial, "supply"),
            "industrial_material_market_noise",
        )
        scraped_press_text = self._make_article(
            section="supply",
            title="분리막·동박 가격반등…K배터리 소재 ‘온기 확산’",
            description="뉴스토마토 기사 본문에 토마토 문자열이 포함됐지만 내용은 전기차 배터리 소재 업황이다.",
            link="https://example.com/battery-material-tomato-press",
            topic="배터리",
        )

        self.assertTrue(
            main.is_non_agri_industrial_material_market_context(
                scraped_press_text.title,
                scraped_press_text.description,
            )
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(scraped_press_text, "supply"),
            "industrial_material_market_noise",
        )

    def test_postbuild_rejects_non_agri_policy_transport_and_export_promo(self) -> None:
        transport = self._make_article(
            section="policy",
            title="조타실 CCTV 의무화·AI 도입…여객선 안전 대전환",
            description="여객선 안전관리와 해양사고 예방을 위한 제도 개편을 다뤘다.",
            link="https://example.com/passenger-ship-policy",
            topic="해양안전",
        )
        consumer_export = self._make_article(
            section="policy",
            title="베트남 등 동남아 소비재 전서...전남도 수출길 청신호",
            description="소비재 박람회에서 해외 바이어 상담과 판로 확대 성과를 소개했다.",
            link="https://example.com/consumer-export-promo",
            topic="수출홍보",
        )

        self.assertEqual(
            main._postbuild_article_reject_reason(transport, "policy"),
            "non_agri_transport_policy_noise",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(transport, "policy", current_count=3, raw_count=20),
            "non_agri_transport_policy_noise",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(consumer_export, "policy"),
            "non_agri_export_promo_noise",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(consumer_export, "policy", current_count=3, raw_count=20),
            "non_agri_export_promo_noise",
        )
        education_opinion = self._make_article(
            section="policy",
            title="[기고] 대학이 부산의 ‘앵커’ 되어야",
            description="지역 대학과 도시 혁신 거점 역할을 다룬 오피니언이다.",
            link="https://example.com/local-university-opinion",
            topic="대학",
        )

        self.assertEqual(
            main._postbuild_article_reject_reason(education_opinion, "policy"),
            "non_agri_education_opinion_noise",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(education_opinion, "policy", current_count=3, raw_count=20),
            "non_agri_education_opinion_noise",
        )

    def test_postbuild_rejects_pest_diplomacy_story(self) -> None:
        diplomacy = self._make_article(
            section="pest",
            title="제주 한라봉 묘목 北으로…‘비타민C 외교’ 재개될까",
            description="한라봉 묘목 지원과 남북 교류 재개 가능성을 다룬 외교 기사다.",
            link="https://example.com/citrus-diplomacy",
            topic="한라봉",
        )

        self.assertTrue(main.is_pest_diplomacy_not_pest_context(diplomacy.title, diplomacy.description))
        self.assertEqual(
            main._postbuild_article_reject_reason(diplomacy, "pest"),
            "pest_diplomacy_not_pest",
        )

        final_by_section = {
            "pest": [
                self._make_article(section="pest", title="과수화상병 확산 비상 현장 점검", topic="사과"),
                self._make_article(section="pest", title="사과 과원 병해충 예찰 강화", topic="사과"),
                self._make_article(section="pest", title="여름철 탄저병 방제 지도", topic="복숭아"),
                diplomacy,
            ],
        }
        dropped = main._drop_hard_postbuild_rejected_final_items(final_by_section, min_items=3)

        self.assertEqual(dropped, 1)
        self.assertNotIn(diplomacy, final_by_section["pest"])

    def test_postbuild_rejects_commodity_origin_history_tail(self) -> None:
        origin_story = self._make_article(
            section="supply",
            title="일본서 들여온 참외, ‘코리안 멜론’ 된 사연",
            description="참외가 국내 대표 과일로 자리 잡기까지 품종 유래와 역사 이야기를 소개했다.",
            link="https://example.com/melon-origin-story",
            topic="참외",
        )

        self.assertTrue(main.is_commodity_origin_history_tail_context(origin_story.title, origin_story.description))
        self.assertEqual(
            main._postbuild_article_reject_reason(origin_story, "supply"),
            "commodity_origin_history_tail",
        )

    def test_dist_preferred_gap_accepts_cold_chain_system_story(self) -> None:
        cold_chain = self._make_article(
            section="dist",
            title="제주 농산물, 산지 저온유통체계 구축…신선도 잡는다",
            description="제주 농산물 산지 유통 경쟁력 강화를 위해 저온유통체계 구축을 추진한다.",
            link="https://example.com/jeju-cold-chain",
            topic="농산물",
        )

        self.assertTrue(main._is_dist_preferred_gap_story(cold_chain))
        dist_conf = next(section for section in main.SECTIONS if section.get("key") == "dist")
        self.assertIsNotNone(main._dist_preferred_gap_rank(cold_chain, dist_conf))

    def test_dist_soft_fallback_allows_direct_distribution_tail_only_for_short_section(self) -> None:
        dist_tail = self._make_article(
            section="dist",
            title="무안군, 양파 100톤 수도권 직거래로 판로 뚫었다",
            description="양파 직거래와 수도권 판로 확대를 다뤘다.",
            link="https://example.com/dist-soft-tail",
        )

        self.assertTrue(main._is_soft_fallback_dist_ops_tail(dist_tail))
        self.assertEqual(
            main._preferred_tail_block_reason(dist_tail, "dist", current_count=3, raw_count=20),
            "",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(dist_tail, "dist", current_count=4, raw_count=20),
            "dist_optional_weak_tail",
        )

    def test_preferred_count_recovery_crossfills_dist_from_supply_for_direct_channel_tail(self) -> None:
        core = self._make_article(
            section="dist",
            title="가락시장 물류 선진화 속도…파렛트 운송지원 확대",
            description="가락시장 파렛트 운송지원과 물류 개선을 다뤘다.",
            link="https://example.com/dist-core-logistics",
        )
        export_a = self._make_article(
            section="dist",
            title="K-푸드는 중동 물류난에도 GCC 수출 증가",
            description="중동 물류난 속 K-푸드 수출 흐름을 다뤘다.",
            link="https://example.com/dist-export-a",
        )
        export_b = self._make_article(
            section="dist",
            title="중동발 충격 확산…정부, K-푸드 물류 대응 총력",
            description="정부의 K-푸드 물류 대응과 수출 지원을 다뤘다.",
            link="https://example.com/dist-export-b",
        )
        direct_channel = self._make_article(
            section="supply",
            title="무안군, 양파 100톤 수도권 직거래로 판로 뚫었다",
            description="무안군이 양파 100톤을 수도권 직거래로 공급하며 판로 확대에 나섰다.",
            link="https://example.com/supply-direct-channel",
        )
        core.is_core = True
        final_by_section = {"dist": [core, export_a, export_b]}
        raw_by_section = {"dist": [], "supply": [direct_channel]}

        recovered = main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section)

        self.assertEqual(recovered, 1)
        self.assertEqual(len(final_by_section["dist"]), 4)
        self.assertIn(direct_channel, final_by_section["dist"])

    def test_preferred_count_recovery_does_not_crossfill_dist_political_visit_tail(self) -> None:
        core = self._make_article(
            section="dist",
            title="가락시장 물류 선진화 속도…파렛트 운송지원 확대",
            description="가락시장 파렛트 운송지원과 물류 개선을 다뤘다.",
            link="https://example.com/dist-core-logistics",
        )
        export_a = self._make_article(
            section="dist",
            title="K-푸드는 중동 물류난에도 GCC 수출 증가",
            description="중동 물류난 속 K-푸드 수출 흐름을 다뤘다.",
            link="https://example.com/dist-export-a",
        )
        export_b = self._make_article(
            section="dist",
            title="중동발 충격 확산…정부, K-푸드 물류 대응 총력",
            description="정부의 K-푸드 물류 대응과 수출 지원을 다뤘다.",
            link="https://example.com/dist-export-b",
        )
        political_visit = self._make_article(
            section="supply",
            title="가락시장부터 청계광장까지 '회오리 유세'...오세훈 후보 총력전",
            description="오세훈 후보가 가락시장과 청계광장을 돌며 선거 유세에 나섰다.",
            link="https://example.com/dist-political-visit",
        )
        core.is_core = True
        final_by_section = {"dist": [core, export_a, export_b]}
        raw_by_section = {"dist": [], "supply": [political_visit]}

        recovered = main._recover_preferred_section_counts_from_raw(final_by_section, raw_by_section)

        self.assertEqual(recovered, 0)
        self.assertEqual(len(final_by_section["dist"]), 3)
        self.assertNotIn(political_visit, final_by_section["dist"])

    def test_final_preferred_tail_cleanup_removes_weak_noncore_without_cutting_below_minimum(self) -> None:
        core_a = self._make_article(
            section="supply",
            title="양파 가격 폭락에 산지 폐기 검토",
            description="양파 가격 폭락과 산지 폐기 대응을 다뤘다.",
            link="https://example.com/onion-core-a",
        )
        core_b = self._make_article(
            section="supply",
            title="배추 출하 감소로 도매가격 상승",
            description="배추 출하 감소와 도매가격 상승 흐름이다.",
            link="https://example.com/cabbage-core-b",
        )
        good_tail = self._make_article(
            section="supply",
            title="고흥군, 양파 400톤 시장격리…수급 안정 대책",
            description="양파 시장격리와 수급 안정 대책을 다뤘다.",
            link="https://example.com/onion-good-tail",
        )
        weak_tail = self._make_article(
            section="supply",
            title="작물의 밥, 비료도 알맞게 사용해야 한다",
            description="비료 사용 요령을 설명하는 일반 영농 기사다.",
            link="https://example.com/fertilizer-tail",
        )
        core_a.is_core = True
        core_b.is_core = True
        final_by_section = {"supply": [core_a, core_b, good_tail, weak_tail]}

        dropped = main._drop_preferred_tail_blocked_items(final_by_section, min_items=3)

        self.assertEqual(dropped, 1)
        self.assertEqual(len(final_by_section["supply"]), 3)
        self.assertNotIn(weak_tail, final_by_section["supply"])

    def test_final_preferred_tail_cleanup_keeps_direct_pest_gap_story(self) -> None:
        existing = [
            self._make_article(
                section="pest",
                title=f"과수화상병 예찰·방제 대응 {idx}",
                description="과수화상병 확산 차단과 예찰 대응을 다뤘다.",
                link=f"https://example.com/pest-cleanup-existing-{idx}",
                topic="과수화상병",
            )
            for idx in range(3)
        ]
        direct = self._make_article(
            section="pest",
            title="정읍시, 농작물 돌발해충 피해 예방 '공동 방제' 총력",
            description="농작물 돌발해충 피해 예방을 위해 공동 방제와 예찰을 강화한다.",
            link="https://example.com/pest-direct-gap-cleanup",
            press="전북일보",
            topic="돌발해충",
        )
        final_by_section = {"pest": [*existing, direct]}

        self.assertTrue(main._is_pest_direct_gap_story(direct))
        self.assertEqual(main._preferred_tail_block_reason(direct, "pest", current_count=4, raw_count=20), "pest_weak_notice_tail")
        self.assertEqual(main._drop_preferred_tail_blocked_items(final_by_section, min_items=3), 0)
        self.assertIn(direct, final_by_section["pest"])

    def test_final_story_duplicate_cleanup_removes_same_region_commodity_tail(self) -> None:
        core = self._make_article(
            section="supply",
            title="양파 가격 폭락에 산지 폐기 검토",
            description="양파 가격 폭락과 산지 폐기 대응을 다뤘다.",
            link="https://example.com/onion-core-dup",
        )
        core.is_core = True
        kept = self._make_article(
            section="supply",
            title="경산 와촌 시설재배 자두 본격 출하",
            description="경산 와촌 자두 출하가 시작됐다.",
            link="https://example.com/jadu-a",
            press="연합뉴스",
        )
        duplicate = self._make_article(
            section="supply",
            title="경산 와촌 자두 출하 본격화…명품 과일 전국 공략",
            description="경산 와촌 시설재배 자두 출하가 본격화했다.",
            link="https://example.com/jadu-b",
            press="지역신문",
        )
        other = self._make_article(
            section="supply",
            title="고흥군, 양파 400톤 시장격리…수급 안정 대책",
            description="양파 시장격리와 수급 안정 대책이다.",
            link="https://example.com/onion-other",
        )
        final_by_section = {"supply": [core, kept, duplicate, other]}

        dropped = main._drop_final_story_duplicates(final_by_section, min_items=3)

        self.assertEqual(dropped, 1)
        self.assertEqual(len(final_by_section["supply"]), 3)
        self.assertIn(kept, final_by_section["supply"])
        self.assertNotIn(duplicate, final_by_section["supply"])

    def test_fire_blight_alert_keeps_incident_pair_instead_of_two_national_firsts(self) -> None:
        first_case_national = self._make_article(
            section="pest",
            title="농진청, 과수화상병 확산 차단... 세종서 첫 과수화상병 확진…위기단계 상향",
            description="농촌진흥청은 세종 첫 확진에 따라 위기단계를 경계로 높이고 정밀 예찰에 나섰다.",
            link="https://example.com/national-fire-first-balance",
            press="농축유통신문",
        )
        national_alert = self._make_article(
            section="pest",
            title="과수화상병 확산 우려…위기 단계 ‘주의’에서 ‘경계’로",
            description="농촌진흥청이 과수화상병 위기 경보를 경계로 상향했고 전국 7개 농가 2.5헥타르에서 발생했다.",
            link="https://example.com/national-fire-alert-balance",
            press="KBS",
        )
        incident = self._make_article(
            section="pest",
            title="화성서 올해 첫 경기도 과수화상병 발생…도농기원 확산 차단 총력",
            description="경기도 사과 과원에서 과수화상병이 발생해 매몰과 주변 예찰을 강화했다.",
            link="https://example.com/hwaseong-fire-balance",
            press="경기일보",
        )
        incident_only = self._make_article(
            section="pest",
            title="원주시 “과수화상병 농가, 예방 약제 미살포”",
            description="원주 과수 농가에서 과수화상병이 확인돼 예방 약제 미살포 행정 처분을 검토한다.",
            link="https://example.com/wonju-fire-balance",
            press="KBS",
        )
        pepper_tail = self._make_article(
            section="pest",
            title="고추 총채벌레 확산 우려…적기 방제 당부",
            description="고추 시설하우스에서 총채벌레와 바이러스 확산 우려가 커지고 있다.",
            link="https://example.com/pepper-balance",
        )
        first_case_national.is_core = True
        national_alert.is_core = True
        final_by_section = {"pest": [first_case_national, national_alert, pepper_tail]}

        self.assertEqual(
            main._ensure_pest_fire_blight_alert_incident_balance(final_by_section, {"pest": [incident_only, incident]}),
            1,
        )

        links = {article.link for article in final_by_section["pest"]}
        self.assertIn(national_alert.link, links)
        self.assertIn(incident.link, links)
        self.assertNotIn(incident_only.link, links)
        self.assertNotIn(first_case_national.link, links)

    def test_duplicate_pest_theme_tail_replacement_prefers_non_fire_horti_candidate(self) -> None:
        fire_core_a = self._make_article(
            section="pest",
            title="화성서 올해 첫 경기도 과수화상병 발생…확산 차단 총력",
            description="사과 과원에서 과수화상병이 발생해 방역당국이 매몰과 예찰을 강화했다.",
            link="https://example.com/fire-a",
        )
        fire_core_b = self._make_article(
            section="pest",
            title="원주시 “과수화상병 농가, 예방 약제 미살포”",
            description="원주 과수 농가에서 과수화상병이 확인돼 예방 약제 살포와 방제 중요성이 제기됐다.",
            link="https://example.com/fire-b",
        )
        fire_tail_a = self._make_article(
            section="pest",
            title="농진청, 과수화상병 확산 차단…세종서 첫 과수화상병 확진",
            description="농촌진흥청이 세종 첫 확진 농가 주변 예찰과 방제를 강화했다.",
            link="https://example.com/fire-c",
        )
        fire_tail_b = self._make_article(
            section="pest",
            title="홍천군, 영농현장 기술보급확산지원단 가동…과수화상병 예찰 강화",
            description="홍천군이 이상기후와 과수화상병 예찰 대응을 강화하기 위해 현장 지원단을 운영한다.",
            link="https://example.com/fire-d",
        )
        strawberry = self._make_article(
            section="pest",
            title="딸기 육묘장 '탄저병 비상'…5월 어미묘 관리가 수확 좌우",
            description="딸기 육묘장의 탄저병 확산을 막기 위해 예찰과 방제, 묘 관리가 중요하다는 현장 기사다.",
            link="https://example.com/strawberry",
        )
        pepper = self._make_article(
            section="pest",
            title="안동시, 고추 진딧물·총채벌레 급증 우려…적기 방제 당부",
            description="고추 재배지에서 진딧물과 총채벌레 발생 우려가 커져 적기 방제가 요구된다.",
            link="https://example.com/pepper",
        )
        fire_core_a.is_core = True
        fire_core_b.is_core = True
        final_by_section = {"pest": [fire_core_a, fire_core_b, fire_tail_a, fire_tail_b]}

        self.assertEqual(
            main._replace_duplicate_pest_theme_tail_from_raw(
                final_by_section,
                {"pest": [strawberry, pepper]},
            ),
            2,
        )
        themes = [main._pest_editorial_theme_key(article) for article in final_by_section["pest"]]
        self.assertLessEqual(themes.count("fire_blight"), 2)
        self.assertIn(strawberry.link, {article.link for article in final_by_section["pest"]})

    def test_duplicate_pest_theme_tail_cleanup_drops_extra_fire_blight_direct_tail(self) -> None:
        fire_core = self._make_article(
            section="pest",
            title='"과수화상병 확산 비상"… 이승돈 청장, 공주 사과농가 긴급 점검',
            description="과수화상병 확산 차단을 위해 농진청이 공주 사과농가를 점검하고 예찰과 방제를 강화했다.",
            link="https://example.com/fire-core",
        )
        fire_field = self._make_article(
            section="pest",
            title="‘붉은 죽음’ 전국 퍼진다…초토화된 사과 과수원",
            description="과수화상병 확산으로 사과 과원이 매몰되고 농가 피해가 커지고 있다.",
            link="https://example.com/fire-field",
        )
        fire_photo = self._make_article(
            section="pest",
            title="과수화상병 예찰 현장 점검하는 이승돈 농진청장",
            description="충남 공주 사과농가에서 과수화상병 정밀 예찰과 현장 대응 상황을 점검했다.",
            link="https://example.com/fire-photo",
        )
        mite = self._make_article(
            section="pest",
            title="충남도 농기원, 맥문동 정식 후 예찰·방제 필수",
            description="맥문동 재배지에서 뿌리응애 발생이 늘어 예찰과 방제 관리가 필수다.",
            link="https://example.com/mite",
        )
        fire_core.is_core = True
        fire_field.is_core = True
        final_by_section = {"pest": [fire_core, fire_field, fire_photo, mite]}

        self.assertTrue(main._is_pest_direct_gap_story(fire_photo))
        self.assertEqual(main._drop_duplicate_pest_theme_tail(final_by_section, max_theme_cards=2, min_items=3), 1)
        links = {article.link for article in final_by_section["pest"]}
        self.assertNotIn(fire_photo.link, links)
        self.assertIn(mite.link, links)

    def test_weak_pest_tail_replacement_prefers_named_non_fire_pest_when_fire_full(self) -> None:
        fire_core = self._make_article(
            section="pest",
            title='"과수화상병 확산 비상"… 이승돈 청장, 공주 사과농가 긴급 점검',
            description="과수화상병 확산 차단을 위해 농진청이 공주 사과농가를 점검하고 예찰과 방제를 강화했다.",
            link="https://example.com/fire-core-repl",
        )
        fire_field = self._make_article(
            section="pest",
            title="‘붉은 죽음’ 전국 퍼진다…초토화된 사과 과수원",
            description="과수화상병 확산으로 사과 과원이 매몰되고 농가 피해가 커지고 있다.",
            link="https://example.com/fire-field-repl",
        )
        weather_tail = self._make_article(
            section="pest",
            title="여름철 태풍·집중호우 '선제적 차단'",
            description="충북도는 여름철 태풍·집중호우에 대비해 농업재해대책 추진계획을 수립했다.",
            link="https://example.com/weather-tail",
        )
        fire_photo = self._make_article(
            section="pest",
            title="과수화상병 예찰 현장 점검하는 이승돈 농진청장",
            description="충남 공주 사과농가에서 과수화상병 정밀 예찰과 현장 대응 상황을 점검했다.",
            link="https://example.com/fire-photo-repl",
        )
        mite = self._make_article(
            section="pest",
            title="노랗게 마르는 맥문동, '뿌리응애'부터 살펴야",
            description="맥문동 재배지에서 뿌리응애 발생이 늘어 예찰과 등록 약제 방제가 필요하다.",
            link="https://example.com/root-mite",
        )
        fire_core.is_core = True
        fire_field.is_core = True
        final_by_section = {"pest": [fire_core, fire_field, weather_tail]}

        self.assertTrue(main._is_weak_pest_tail(weather_tail))
        self.assertEqual(main._replace_weak_pest_tail_from_raw(final_by_section, {"pest": [fire_photo, mite]}), 1)
        links = {article.link for article in final_by_section["pest"]}
        self.assertIn(mite.link, links)
        self.assertNotIn(fire_photo.link, links)

    def test_pest_weather_disaster_noise_blocks_generic_weather_tail(self) -> None:
        weather_tail = self._make_article(
            section="pest",
            title="함평군, 장마철 농작물 피해 예방 강화",
            description="장마철 집중호우·태풍에 대비해 농작물과 시설물 피해 예방을 강화하고 시설채소 현장 기술지원단을 가동했다. 후반에는 습해 뒤 탄저병 방제 요령도 안내했다.",
            link="https://example.com/hampyeong-weather",
        )
        direct = self._make_article(
            section="pest",
            title="정읍시, 농작물 돌발해충 피해 예방 '공동 방제' 총력",
            description="농작물 돌발해충 피해 예방을 위해 공동 방제와 예찰을 강화한다.",
            link="https://example.com/jeongeup-pest",
        )

        self.assertTrue(main._is_pest_weather_disaster_noise(weather_tail))
        self.assertTrue(main._is_generic_pest_notice_tail(weather_tail))
        self.assertTrue(main._is_weak_pest_tail(weather_tail))
        self.assertFalse(main._is_pest_direct_gap_story(weather_tail))
        self.assertFalse(main._is_pest_weather_disaster_noise(direct))
        self.assertTrue(main._is_pest_direct_gap_story(direct))

    def test_final_pest_direct_gap_refill_replaces_weather_and_fills_to_preferred(self) -> None:
        fire_core = self._make_article(
            section="pest",
            title='"과수화상병 확산 비상"… 이승돈 청장, 공주 사과농가 긴급 점검',
            description="과수화상병 확산 차단을 위해 농진청이 공주 사과농가를 점검하고 예찰과 방제를 강화했다.",
            link="https://example.com/refill-fire-core",
        )
        fire_field = self._make_article(
            section="pest",
            title="‘붉은 죽음’ 전국 퍼진다…초토화된 사과 과수원",
            description="과수화상병 확산으로 사과 과원이 매몰되고 농가 피해가 커지고 있다.",
            link="https://example.com/refill-fire-field",
        )
        weather_tail = self._make_article(
            section="pest",
            title="함평군, 장마철 농작물 피해 예방 강화",
            description="장마철 집중호우·태풍에 대비해 농작물과 시설물 피해 예방을 강화하고 현장 기술지원을 확대했다.",
            link="https://example.com/refill-weather",
        )
        mite = self._make_article(
            section="pest",
            title="충남도 농기원, 맥문동 정식 후 예찰·방제 필수",
            description="맥문동 재배지에서 뿌리응애 발생이 늘어 예찰과 방제 관리가 필수다.",
            link="https://example.com/refill-mite",
        )
        jeongeup = self._make_article(
            section="pest",
            title="정읍시, 농작물 돌발해충 피해 예방 '공동 방제' 총력",
            description="농작물 돌발해충 피해 예방을 위해 공동 방제와 예찰을 강화한다.",
            link="https://example.com/refill-jeongeup",
        )
        stinkbug = self._make_article(
            section="pest",
            title="과수 노린재 피해 증가, 친환경 관리 관심 확대",
            description="사과·배 과수원에서 노린재 피해가 증가해 친환경 관리와 방제가 필요하다.",
            link="https://example.com/refill-stinkbug",
        )
        fire_photo = self._make_article(
            section="pest",
            title="과수화상병 예찰 현장 점검하는 이승돈 농진청장",
            description="충남 공주 사과농가에서 과수화상병 정밀 예찰과 현장 대응 상황을 점검했다.",
            link="https://example.com/refill-fire-photo",
        )
        fire_core.is_core = True
        fire_field.is_core = True
        final_by_section = {"pest": [fire_core, fire_field, weather_tail, mite]}

        changed = main._refill_pest_direct_gap_from_raw(
            final_by_section,
            {"pest": [fire_photo, jeongeup, stinkbug]},
            target=5,
        )

        links = {article.link for article in final_by_section["pest"]}
        self.assertEqual(changed, 2)
        self.assertEqual(len(final_by_section["pest"]), 5)
        self.assertNotIn(weather_tail.link, links)
        self.assertNotIn(fire_photo.link, links)
        self.assertIn(jeongeup.link, links)
        self.assertIn(stinkbug.link, links)

    def test_supply_editorial_guard_replaces_machine_demo_tail(self) -> None:
        core = self._make_article(
            section="supply",
            title="“캘수록 손해” 창녕 양파 수확농가의 눈물",
            description="양파 산지 가격 하락과 인건비 상승으로 수확 농가 손실이 커지고 있다.",
            link="https://example.com/supply-core-onion",
        )
        weak = self._make_article(
            section="supply",
            title="창녕서 마늘 전 과정 기계화 기술 공개…농촌 인력난 해법 제시",
            description="마늘 파종부터 수확까지 기계화 기술을 공개하는 행사성 기사다.",
            link="https://example.com/supply-machine",
        )
        better = self._make_article(
            section="supply",
            title="광양매실 생산량 급증...가격은 전년보다 하락 조짐",
            description="매실 생산량 급증과 소비 부진으로 산지 가격 하락 우려가 커지고 있다.",
            link="https://example.com/supply-maesil-buy",
        )
        better.selection_fit_score = 1.8
        core.is_core = True
        final_by_section = {"supply": [core, weak]}

        self.assertEqual(main._replace_supply_editorial_weak_tail_from_raw(final_by_section, {"supply": [better]}), 1)
        links = {article.link for article in final_by_section["supply"]}
        self.assertNotIn(weak.link, links)
        self.assertIn(better.link, links)

    def test_supply_editorial_guard_skips_policy_duplicate_and_market_event(self) -> None:
        weak = self._make_article(
            section="supply",
            title="광양시, 매실 상생마케팅 후원금 지원…소비촉진·제값받기",
            description="지역 후원금과 판촉 지원을 소개하는 행사성 기사다.",
            link="https://example.com/supply-weak-maesil",
        )
        policy_core = self._make_article(
            section="policy",
            title="농민의길 “농특세, 농산물 가격 안정에 우선 써야”",
            description="농특세를 농산물 가격 안정에 써야 한다는 정책 주장이다.",
            link="https://example.com/policy-ag-tax",
        )
        policy_duplicate = self._make_article(
            section="supply",
            title="농민의길 “농특세, 농산물 가격 안정에 우선 써야”",
            description="농특세를 농산물 가격 안정에 써야 한다는 정책 주장이다.",
            link="https://example.com/policy-ag-tax",
        )
        direct_market = self._make_article(
            section="supply",
            title="햇마늘·햇 양파 직거래장터 오세요",
            description="농협 주차장에서 마늘과 양파 직거래장터를 연다는 안내 기사다.",
            link="https://example.com/supply-direct-market",
        )
        better = self._make_article(
            section="supply",
            title="광양매실 생산량 급증...가격은 전년보다 하락 조짐",
            description="매실 생산량 급증과 소비 부진으로 산지 가격 하락 우려가 커지고 있다.",
            link="https://example.com/supply-maesil-price",
        )
        better.selection_fit_score = 1.8
        final_by_section = {"supply": [weak], "policy": [policy_core]}

        self.assertEqual(
            main._replace_supply_editorial_weak_tail_from_raw(
                final_by_section,
                {"supply": [policy_duplicate, direct_market, better]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["supply"]}
        self.assertNotIn(weak.link, links)
        self.assertNotIn(policy_duplicate.link, links)
        self.assertNotIn(direct_market.link, links)
        self.assertIn(better.link, links)

    def test_supply_editorial_guard_replaces_support_core_with_market_story(self) -> None:
        weak_core = self._make_article(
            section="supply",
            title="“여름채소 생산기반 지키자”…대아청과, 물류기자재 4천만원 지원",
            description="대아청과가 고랭지 여름채소 농가에 물류기자재와 후원금을 지원하는 상생 활동을 진행했다.",
            link="https://example.com/supply-support-core",
        )
        better = self._make_article(
            section="supply",
            title="외식업 불황에 김치 소비 부진…‘배추값’ 넉달째 약세",
            description="김치 소비 부진과 출하 물량 영향으로 배추 가격 약세가 이어지고 있다.",
            link="https://example.com/supply-cabbage-price",
            topic="배추",
        )
        weak_core.is_core = True
        final_by_section = {"supply": [weak_core]}

        self.assertEqual(main._replace_supply_editorial_weak_tail_from_raw(final_by_section, {"supply": [better]}), 1)
        self.assertEqual(final_by_section["supply"][0].link, better.link)
        self.assertTrue(final_by_section["supply"][0].is_core)

    def test_policy_energy_tariff_duplicates_are_grouped(self) -> None:
        first = self._make_article(
            section="policy",
            title="정부, LNG·LPG 관세 0%로 낮춘다…하반기 물가 안정 총력",
            description="정부가 발전용 LNG와 LPG 할당관세를 연말까지 0%로 낮춰 물가 부담 완화를 추진한다.",
            link="https://example.com/policy-lng-a",
        )
        second = self._make_article(
            section="policy",
            title="하반기에도 LNG·LPG 할당관세율 0%…발전용LNG 개소세 감면",
            description="LNG·LPG 할당 관세를 0%로 유지하고 에너지 비용 부담을 낮추는 정책이다.",
            link="https://example.com/policy-lng-b",
        )
        final_by_section = {"policy": [first, second]}

        self.assertEqual(main._drop_final_story_duplicates(final_by_section, min_items=1), 1)
        self.assertEqual(len(final_by_section["policy"]), 1)

    def test_supply_core_pest_care_story_is_replaced_by_market_story(self) -> None:
        weak_core = self._make_article(
            section="supply",
            title="장마철 사과 과원 관리 비상…철저한 배수·병해 예방 필요",
            description="장마철 배수 관리와 병해 예방을 안내하는 기술 기사다.",
            link="https://example.com/supply-pest-care-core",
        )
        market = self._make_article(
            section="supply",
            title="풍년에 가격 폭락…양파 농가 시름",
            description="양파 생산량 증가와 가격 폭락으로 산지 농가의 수급 부담이 커지고 있다.",
            link="https://example.com/supply-onion-price",
            topic="양파",
        )
        weak_core.is_core = True
        final_by_section = {"supply": [weak_core]}

        self.assertEqual(main._replace_supply_editorial_weak_tail_from_raw(final_by_section, {"supply": [market]}), 1)
        self.assertEqual(final_by_section["supply"][0].link, market.link)

    def test_policy_fertilizer_campaign_tail_is_rejected(self) -> None:
        campaign = self._make_article(
            section="policy",
            title="‘비료 사용 처방 적정 시비 실천 캠페인’ 추진",
            description="비료 사용 처방과 적정 시비 실천을 홍보하는 캠페인 기사다.",
            link="https://example.com/policy-fertilizer-campaign",
        )

        self.assertEqual(main._postbuild_article_reject_reason(campaign, "policy", apply_selection_fit=False), "policy_private_support_promo")
        self.assertTrue(main._is_policy_editorial_weak_tail(campaign))

    def test_policy_rejects_local_field_trial_supply_story(self) -> None:
        trial = self._make_article(
            section="policy",
            title="준고랭지 여름 배추 시범사업으로 수급 안정 뒷받침",
            description="지역 재배 시범사업으로 여름 배추 수급 안정을 뒷받침한다는 산지 기사다.",
            link="https://example.com/policy-local-field-trial",
            topic="배추",
        )

        self.assertEqual(main._postbuild_article_reject_reason(trial, "policy", apply_selection_fit=False), "policy_local_field_trial_not_policy")

    def test_postbuild_rejects_section_misfits_from_june_quality_gate(self) -> None:
        potato_ship = self._make_article(
            section="policy",
            title="오창농협, 청원생명 ‘꺼리’ 햇 감자 출하",
            description="지역 농협이 햇감자 출하를 시작했다는 산지 출하 소식이다.",
            link="https://example.com/policy-potato-ship",
        )
        tourism = self._make_article(
            section="dist",
            title="관광기념품 지역 제한 완화…지자체 조례 등 233건 개선",
            description="관광기념품 공모 지역 제한 완화와 조례 개선을 다룬 행정 기사다.",
            link="https://example.com/dist-tourism-policy",
        )
        labor = self._make_article(
            section="pest",
            title="대전 유성농협·고향주부모임, 배농가 찾아 봉지 씌우기 도와",
            description="농협과 단체가 배 농가를 찾아 봉지 씌우기 일손돕기 활동을 했다.",
            link="https://example.com/pest-labor-help",
        )

        self.assertEqual(main._postbuild_article_reject_reason(potato_ship, "policy", apply_selection_fit=False), "policy_shipping_story_not_policy")
        self.assertEqual(main._postbuild_article_reject_reason(tourism, "dist", apply_selection_fit=False), "dist_non_agri_tourism_policy")
        self.assertEqual(main._postbuild_article_reject_reason(labor, "pest", apply_selection_fit=False), "pest_labor_help_not_pest")

    def test_dist_editorial_guard_replaces_support_promo_with_market_ops(self) -> None:
        promo = self._make_article(
            section="dist",
            title="대아청과, 고랭지 여름채소 생산 안정에 4천만원 지원",
            description="농가 물류기자재 지원과 생산 안정 후원금을 전달했다는 홍보성 기사다.",
            link="https://example.com/dist-support-promo",
        )
        ops = self._make_article(
            section="dist",
            title="“고온에 농산물 쉽게 상해”…구리시장 7월15일 시범휴업 안한다",
            description="구리 농수산물도매시장이 경매와 시장 운영 상황을 고려해 시범휴업을 하지 않기로 했다.",
            link="https://example.com/dist-guri-market",
        )
        final_by_section = {"dist": [promo]}

        self.assertEqual(main._replace_dist_editorial_promo_tail_from_raw(final_by_section, {"dist": [ops]}), 1)
        self.assertEqual(final_by_section["dist"][0].link, ops.link)

    def test_dist_apc_channel_expansion_is_operational_replacement(self) -> None:
        article = self._make_article(
            section="dist",
            title="서북부경남 과수 거점 APC, 농산물 유통 역량 강화",
            description=(
                "과수거점산지유통센터(APC)는 기존 홈쇼핑 중심 판매에서 라이브커머스 채널과 "
                "신규 판로를 확대한다. 지난해 매출 191억원과 방송 수수료 부담을 토대로 "
                "판매 채널 다변화와 수익성 개선을 추진한다."
            ),
            link="https://example.com/dist-apc-channel-expansion",
        )

        self.assertTrue(main._is_dist_apc_channel_expansion_story(article))
        self.assertTrue(main._is_dist_editorial_ops_replacement(article))
        self.assertTrue(main._is_dist_operational_upgrade_candidate(article))
        self.assertTrue(main._is_publish_editorial_candidate("dist", article))

    def test_dist_direct_platform_launch_is_operational_replacement(self) -> None:
        article = self._make_article(
            section="dist",
            title="제주 농특산물 직거래 플랫폼 '탐나는장터' 7월 10일 공식 오픈",
            description=(
                "생산자는 온라인 마케팅 비용과 판매 수수료 부담을 줄이고 새로운 판로를 확보하며, "
                "소비자는 제주 농특산물을 직접 구매한다. 시범 운영 뒤 공식 오픈한다."
            ),
            link="https://example.com/dist-direct-platform",
        )

        self.assertTrue(main._is_dist_direct_platform_launch_story(article))
        self.assertTrue(main._is_dist_editorial_ops_replacement(article))
        self.assertTrue(main._is_dist_operational_upgrade_candidate(article))
        self.assertTrue(main._is_publish_editorial_candidate("dist", article))

    def test_dist_measured_export_growth_can_crossfill_from_supply(self) -> None:
        article = self._make_article(
            section="supply",
            title="K-참외 매력에 ‘흠뻑’…국산 참외 일본 수출 ‘쑥쑥’",
            description="국산 참외의 일본 수출량이 1.2톤에서 2.4톤으로 늘고 현지 판매량도 해마다 증가했다.",
            link="https://example.com/dist-measured-export-growth",
        )

        self.assertTrue(main._is_dist_export_growth_context(article.title, article.description))
        self.assertTrue(main._is_dist_operational_upgrade_candidate(article))
        self.assertTrue(main._is_publish_editorial_candidate("dist", article))

    def test_dist_editorial_guard_can_limit_followup_replacements(self) -> None:
        promos = [
            self._make_article(
                section="dist",
                title=f"도매법인 {idx}, 산지에 물류·영농기자재 지원",
                description="농가에 물류기자재 지원금을 전달했다는 홍보성 기사다.",
                link=f"https://example.com/dist-promo-{idx}",
            )
            for idx in range(2)
        ]
        replacements = [
            self._make_article(
                section="dist",
                title=f"농산물 도매시장 {idx}, 경매시간 운영 변경",
                description="도매시장이 출하정보와 반입량을 토대로 경매시간과 시장 운영을 변경한다.",
                link=f"https://example.com/dist-ops-{idx}",
            )
            for idx in range(2)
        ]
        final_by_section = {"dist": promos}

        self.assertEqual(
            main._replace_dist_editorial_promo_tail_from_raw(
                final_by_section,
                {"dist": replacements},
                max_changes=1,
            ),
            1,
        )
        self.assertEqual(sum(article.link in {item.link for item in replacements} for article in final_by_section["dist"]), 1)

    def test_dist_followup_replaces_only_duplicate_support_handoff_with_apc_shift(self) -> None:
        support_items = [
            self._make_article(
                section="dist",
                title=f"도매법인 {idx}, 산지에 물류·영농기자재 전달",
                description="산지 출하조직에 물류기자재 지원금을 전달했다.",
                link=f"https://example.com/dist-support-handoff-{idx}",
            )
            for idx in range(2)
        ]
        fixed_items = [
            self._make_article(
                section="dist",
                title=f"농산물 도매시장 운영 개선 {idx}",
                description="도매시장 경매와 반입량 운영을 개선한다.",
                link=f"https://example.com/dist-fixed-{idx}",
            )
            for idx in range(3)
        ]
        apc = self._make_article(
            section="dist",
            title="서북부경남 과수 거점 APC, 농산물 유통 역량 강화",
            description=(
                "과수거점산지유통센터(APC)가 매출 191억원과 홈쇼핑 수수료 부담을 토대로 "
                "라이브커머스 판매 채널과 신규 판로를 확대한다."
            ),
            link="https://example.com/dist-apc-measured-shift",
        )
        final_by_section = {"dist": fixed_items + support_items}

        self.assertEqual(
            main._replace_publish_dist_support_promo_with_apc_channel_expansion(
                final_by_section,
                {"dist": [apc]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["dist"]}
        self.assertIn(apc.link, links)
        self.assertEqual(sum(article.link in links for article in support_items), 1)

    def test_dist_followup_replaces_single_support_handoff_with_apc_shift(self) -> None:
        support = self._make_article(
            section="dist",
            title="중앙청과, 서창농협에 물류·영농기자재 지원",
            description="산지 출하조직에 물류기자재 지원금을 전달했다.",
            link="https://example.com/dist-single-support-handoff",
        )
        fixed_items = [
            self._make_article(
                section="dist",
                title=f"농산물 도매시장 운영 개선 {idx}",
                description="도매시장 경매와 반입량 운영을 개선한다.",
                link=f"https://example.com/dist-single-fixed-{idx}",
            )
            for idx in range(4)
        ]
        apc = self._make_article(
            section="dist",
            title="서북부경남 과수 거점 APC, 농산물 유통 역량 강화",
            description=(
                "과수거점산지유통센터(APC)가 매출 191억원과 홈쇼핑 수수료 부담을 토대로 "
                "라이브커머스 판매 채널과 신규 판로를 확대한다."
            ),
            link="https://example.com/dist-single-apc-shift",
        )
        final_by_section = {"dist": fixed_items + [support]}

        self.assertEqual(
            main._replace_publish_dist_support_promo_with_apc_channel_expansion(
                final_by_section,
                {"dist": [apc]},
            ),
            1,
        )
        self.assertIn(apc.link, {article.link for article in final_by_section["dist"]})
        self.assertNotIn(support.link, {article.link for article in final_by_section["dist"]})

    def test_measured_climate_output_story_is_valid_supply_candidate(self) -> None:
        article = self._make_article(
            section="supply",
            title='"폭염에도 상추 수확 40%↑"…농진청, 양액 냉각기 점검',
            description=(
                "여름철 채소 수급 불안 우려 속에 양액 냉각 기술을 적용한 상추 생산량이 "
                "최대 2배 증가했다."
            ),
            link="https://example.com/supply-measured-lettuce-output",
            topic="상추",
        )
        conf = next(section for section in main.SECTIONS if section.get("key") == "supply")

        self.assertTrue(main._is_supply_climate_output_context(article.title, article.description))
        self.assertFalse(main._is_publish_supply_editorial_weak(article))
        self.assertEqual(main._postbuild_article_reject_reason(article, "supply"), "")
        self.assertGreater(main.section_fit_score(article.title, article.description, conf), 1.2)

    def test_supply_followup_replaces_regional_duplicate_with_climate_output(self) -> None:
        onion_a = self._make_article(
            section="supply",
            title="경북, 양파 가격 폭락에 소비촉진 행사 개최",
            description="경북이 양파 가격 하락에 대응해 소비촉진 행사를 열었다.",
            link="https://example.com/supply-onion-duplicate-a",
            topic="양파",
        )
        onion_b = self._make_article(
            section="supply",
            title="경상북도, 양파 가격하락 농가 피해 줄이기 위해 수급 안정 대책",
            description="경북이 양파 가격 하락과 농가 피해에 대응해 수급 안정 대책을 추진한다.",
            link="https://example.com/supply-onion-duplicate-b",
            topic="양파",
        )
        fixed = [
            self._make_article(
                section="supply",
                title=f"채소 가격·출하 동향 {idx}",
                description="채소 출하량과 가격 변화를 다룬다.",
                link=f"https://example.com/supply-fixed-{idx}",
            )
            for idx in range(3)
        ]
        climate = self._make_article(
            section="supply",
            title='"폭염에도 상추 수확 40%↑"…농진청, 양액 냉각기 점검',
            description="여름철 채소 수급 불안 속에 상추 생산량이 최대 2배 증가했다.",
            link="https://example.com/supply-climate-replacement",
            topic="상추",
        )
        final_by_section = {"supply": [onion_a, onion_b] + fixed}

        self.assertEqual(
            main._replace_publish_supply_duplicate_with_climate_output(
                final_by_section,
                {"supply": [climate]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["supply"]}
        self.assertIn(climate.link, links)
        self.assertEqual(sum(article.link in links for article in (onion_a, onion_b)), 1)

    def test_supply_followup_replaces_climate_technology_with_authoritative_multi_price(self) -> None:
        climate = self._make_article(
            section="supply",
            title='"폭염에도 상추 수확 40%↑"…농진청, 양액 냉각기 점검',
            description="여름철 채소 수급 불안 속에 상추 생산량이 최대 2배 증가했다.",
            link="https://example.com/supply-climate-tail",
            topic="상추",
        )
        fixed = [
            self._make_article(
                section="supply",
                title=f"채소 가격·출하 동향 {idx}",
                description="채소 출하량과 가격 변화를 다룬다.",
                link=f"https://example.com/supply-multi-price-fixed-{idx}",
            )
            for idx in range(4)
        ]
        multi_price = self._make_article(
            section="supply",
            title="늦어지는 '장마'·무더위에 농산물값, 체리·파프리카↓, 다다기오이↑",
            description=(
                "한국농수산식품유통공사는 파프리카 가격이 전주 대비 17.1% 하락하고 "
                "감자 생산량 증가로 가격이 13.4% 내렸다고 밝혔다. 다다기오이는 "
                "산지 흐린 날씨로 반입량이 감소해 3.2% 상승했고 참외 출하량도 늘었다."
            ),
            link="https://example.com/supply-authoritative-multi-price",
            topic="파프리카",
        )
        final_by_section = {"supply": fixed + [climate]}

        self.assertTrue(main._is_supply_authoritative_multi_price_context(
            multi_price.title,
            multi_price.description,
        ))
        self.assertFalse(main.is_supply_unmanaged_broad_price_roundup_context(
            multi_price.title,
            multi_price.description,
        ))
        self.assertTrue(main._is_publish_editorial_candidate("supply", multi_price))
        self.assertEqual(
            main._replace_publish_supply_climate_output_with_multi_price(
                final_by_section,
                {"supply": [multi_price]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["supply"]}
        self.assertEqual(len(final_by_section["supply"]), 5)
        self.assertIn(multi_price.link, links)
        self.assertNotIn(climate.link, links)

    def test_measured_export_growth_and_operating_apc_automation_fit_dist(self) -> None:
        export = self._make_article(
            section="dist",
            title="K-참외 매력에 흠뻑…국산 참외 일본 수출 쑥쑥",
            description="참외 수출량이 4년 전 61톤에서 지난해 271톤으로 4배 이상 증가했다.",
            link="https://example.com/dist-melon-export-growth",
            topic="참외",
        )
        automation = self._make_article(
            section="dist",
            title="토마토 선별·포장, 로봇이 다 해줍니다",
            description=(
                "전국 최초로 로봇 기반 자동화 시스템을 갖춘 스마트 농산물산지유통센터(APC)가 "
                "토마토를 선별·포장한다."
            ),
            link="https://example.com/dist-tomato-apc-automation",
            topic="토마토",
        )
        conf = next(section for section in main.SECTIONS if section.get("key") == "dist")

        self.assertTrue(main._is_dist_export_growth_context(export.title, export.description))
        self.assertTrue(main._is_dist_apc_automation_context(automation.title, automation.description))
        self.assertFalse(main._is_publish_dist_editorial_weak(export))
        self.assertFalse(main._is_publish_dist_editorial_weak(automation))
        self.assertGreater(main.section_fit_score(export.title, export.description, conf), 1.2)
        self.assertGreater(main.section_fit_score(automation.title, automation.description, conf), 1.2)

    def test_dist_structural_followup_replaces_two_event_tails(self) -> None:
        fixed = [
            self._make_article(
                section="dist",
                title=f"농산물 도매시장 운영 기사 {idx}",
                description="도매시장 반입량과 경매 운영을 다룬다.",
                link=f"https://example.com/dist-fixed-structural-{idx}",
            )
            for idx in range(3)
        ]
        meeting = self._make_article(
            section="dist",
            title="영동농협, 경매사 초청 간담회",
            description="경매사를 초청해 판로 확대 의견을 나눴다.",
            link="https://example.com/dist-meeting-tail",
        )
        support = self._make_article(
            section="dist",
            title="중앙청과, 서창농협에 물류·영농기자재 지원",
            description="물류기자재 지원금 전달식을 열었다.",
            link="https://example.com/dist-support-tail-structural",
        )
        export = self._make_article(
            section="dist",
            title="K-참외 매력에 흠뻑…국산 참외 일본 수출 쑥쑥",
            description="수출량이 61톤에서 271톤으로 4배 이상 증가했다.",
            link="https://example.com/dist-export-replacement",
            topic="참외",
        )
        automation = self._make_article(
            section="dist",
            title="토마토 선별·포장, 로봇이 다 해줍니다",
            description="전국 최초 자동화 시스템을 갖춘 스마트 APC가 토마토를 선별·포장한다.",
            link="https://example.com/dist-automation-replacement",
            topic="토마토",
        )
        final_by_section = {"dist": fixed + [meeting, support]}

        self.assertEqual(
            main._replace_publish_dist_weak_tails_with_structural_ops(
                final_by_section,
                {"dist": [export, automation]},
            ),
            2,
        )
        links = {article.link for article in final_by_section["dist"]}
        self.assertIn(export.link, links)
        self.assertIn(automation.link, links)

    def test_dist_core_rebalance_prefers_operational_anchors_over_structural_tails(self) -> None:
        onion_export = self._make_article(
            section="dist",
            title="전주시, 양파 대만 수출 확대…농가 판로 다변화",
            description="전주산 양파를 대만에 선적해 수출 판로를 넓힌다.",
            link="https://example.com/dist-onion-export-anchor",
            topic="양파",
        )
        garak = self._make_article(
            section="dist",
            title="[Issue+] 가락시장 시범휴업 추진 상황과 과제는",
            description="가락시장 시범휴업의 운영 일정과 출하자 대응 과제를 점검한다.",
            link="https://example.com/dist-garak-suspension-anchor",
        )
        automation = self._make_article(
            section="dist",
            title="토마토 선별·포장, 로봇이 다 해줍니다",
            description="스마트 APC가 토마토 선별과 포장을 자동화한다.",
            link="https://example.com/dist-automation-tail",
            topic="토마토",
        )
        export_growth = self._make_article(
            section="dist",
            title="K-참외 매력에 흠뻑…국산 참외 일본 수출 쑥쑥",
            description="참외 수출량이 61톤에서 271톤으로 4배 이상 증가했다.",
            link="https://example.com/dist-export-growth-tail",
            topic="참외",
        )
        support = self._make_article(
            section="dist",
            title="중앙청과, 서창농협에 물류·영농기자재 지원",
            description="물류기자재 지원금을 전달했다.",
            link="https://example.com/dist-support-tail",
        )
        for article in (automation, export_growth):
            article.is_core = True
        final_by_section = {
            "dist": [automation, export_growth, support, onion_export, garak],
        }

        main._rebalance_publish_core_badges_for_editorial_target(final_by_section)

        self.assertEqual(len(final_by_section["dist"]), 5)
        self.assertEqual(
            {article.link for article in final_by_section["dist"] if article.is_core},
            {onion_export.link, garak.link},
        )

    def test_pest_followup_prefers_named_weather_warning_over_generic_consultation(self) -> None:
        generic = self._make_article(
            section="pest",
            title="논산시, 7월 한 달 농가 찾아간다…폭염·병해충 영농상담 강화",
            description="농가를 찾아 일반 영농상담과 병해충 예찰을 안내한다.",
            link="https://example.com/pest-generic-consultation",
        )
        fixed = [
            self._make_article(
                section="pest",
                title=f"고추 병해충 현장 기사 {idx}",
                description="고추 재배지 병해충 발생과 방제 대응을 다룬다.",
                link=f"https://example.com/pest-fixed-{idx}",
            )
            for idx in range(4)
        ]
        warning = self._make_article(
            section="pest",
            title="해남군 '고온다습 장마철' 고추 병해충 예방 당부",
            description="고추 탄저병과 담배나방 발생 위험에 대비해 장마철 예방을 당부했다.",
            link="https://example.com/pest-haenam-warning",
        )
        final_by_section = {"pest": fixed + [generic]}

        self.assertEqual(
            main._replace_publish_pest_generic_tail_with_direct_warning(
                final_by_section,
                {"pest": [warning]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["pest"]}
        self.assertIn(warning.link, links)
        self.assertNotIn(generic.link, links)

    def test_pest_followup_replaces_feature_with_weekly_guidance(self) -> None:
        investigation = self._make_article(
            section="pest",
            title="사과 나무 무더기로 죽었는데 원인 불명?…경찰 수사까지",
            description="당국은 과수화상병 가능성이 낮다고 보고 원인을 조사하고 있다.",
            link="https://example.com/pest-unknown-apple",
            topic="사과",
        )
        feature = self._make_article(
            section="pest",
            title="농약 치기 쉬운 만감류 나무, 제주 농가에 보급될까",
            description="방제 작업이 쉬운 만감류 수형 연구를 소개한다.",
            link="https://example.com/pest-citrus-feature",
        )
        fixed = [
            self._make_article(
                section="pest",
                title=f"고추 병해충 발생 경보 {idx}",
                description="장마철 고추 병해충 발생과 방제 대응을 다룬다.",
                link=f"https://example.com/pest-guidance-fixed-{idx}",
            )
            for idx in range(3)
        ]
        weekly = self._make_article(
            section="pest",
            title="[주간농사메모] 병해충 발생 여부 수시 예찰",
            description="병해충을 수시 예찰하고 발생 시 즉시 적용약제로 방제하도록 안내한다.",
            link="https://example.com/pest-weekly-guidance",
        )
        final_by_section = {"pest": fixed + [investigation, feature]}

        self.assertEqual(
            main._replace_publish_pest_feature_tail_with_weekly_advisory(
                final_by_section,
                {"pest": [weekly]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["pest"]}
        self.assertEqual(len(final_by_section["pest"]), 5)
        self.assertIn(weekly.link, links)
        self.assertIn(investigation.link, links)
        self.assertNotIn(feature.link, links)

    def test_dist_support_grant_is_not_hard_logistics_core(self) -> None:
        grant = self._make_article(
            section="dist",
            title="“여름채소 생산기반 지키자”…대아청과·농어촌희망재단, 물류기자재 지원금 전달",
            description="가락시장 대아청과가 고랭지 채소 산지를 대상으로 물류기자재 지원금을 전달했다.",
            link="https://example.com/dist-material-grant",
        )

        self.assertFalse(main.is_dist_hard_logistics_metric_context(grant.title, grant.description))
        self.assertTrue(main._is_dist_editorial_promo_tail(grant))
        self.assertEqual(
            main._postbuild_article_reject_reason(grant, "dist", apply_selection_fit=False),
            "dist_support_promo_without_ops",
        )

    def test_followup_quality_gate_rejects_event_and_section_misfits(self) -> None:
        market_ops_in_supply = self._make_article(
            section="supply",
            title="7월부터 두달간 가락시장 배추 경매 오후 10시에 시작",
            description="서울시공사가 하절기 가락시장 배추 경매개시 시각을 조정한다.",
            link="https://example.com/supply-garak-market",
        )
        machine_demo = self._make_article(
            section="supply",
            title="'마늘' 파종부터 수확까지 기계가 척척",
            description="마늘 종자 준비부터 파종, 수확, 저장까지 전 과정 기계화 기술을 공개했다.",
            link="https://example.com/supply-garlic-machine",
        )
        donation_event = self._make_article(
            section="policy",
            title="함양군, 양파 가격 하락에 고향사랑기부 연계 이벤트 실시",
            description="양파 가격 하락 농가를 지원한다며 고향사랑기부제와 연계한 상생 이벤트를 추진한다.",
            link="https://example.com/policy-donation-event",
        )
        expo = self._make_article(
            section="dist",
            title="'제2회 한국 마늘 산업 박람회' 해남서 7월 9일 개막",
            description="마늘 산업의 현재와 스마트 첨단 미래 기술을 볼 수 있는 박람회가 열린다.",
            link="https://example.com/dist-garlic-expo",
        )
        live_sale = self._make_article(
            section="dist",
            title="익산 '탑마루' 블루베리, 오는 20일 온라인 생중계 판매",
            description="클릭 한 번으로 구매할 수 있는 온라인 생중계 판매를 진행한다.",
            link="https://example.com/dist-live-sale",
        )
        e_invoice_dist = self._make_article(
            section="dist",
            title="정부, 널뛰는 농산물 가격에 전자송품장·출하비용 보전 추진",
            description="정부가 농산물 가격 변동을 줄이기 위해 전자송품장과 출하비용 보전 제도를 추진한다.",
            link="https://example.com/dist-einvoice-price-response",
        )

        self.assertEqual(
            main._postbuild_article_reject_reason(market_ops_in_supply, "supply", apply_selection_fit=False),
            "supply_market_ops_not_supply",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(machine_demo, "supply", apply_selection_fit=False),
            "supply_editorial_weak_tail",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(donation_event, "policy", apply_selection_fit=False),
            "policy_private_support_promo",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(expo, "dist", apply_selection_fit=False),
            "dist_event_sales_promo",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(e_invoice_dist, "dist", apply_selection_fit=False),
            "dist_policy_price_response_not_dist",
        )
        self.assertTrue(main._is_dist_editorial_promo_tail(live_sale))

    def test_pest_refill_allows_third_fire_blight_when_section_is_underfilled(self) -> None:
        fire_a = self._make_article(
            section="pest",
            title="곡성군, 과수화상병 선제 대응",
            description="과수화상병 확산 차단을 위해 사과·배 농가 예찰과 방제를 강화한다.",
            link="https://example.com/pest-fire-a",
        )
        fire_b = self._make_article(
            section="pest",
            title="무주 사과농가 과수화상병 비상…올해 벌써 8곳 매몰",
            description="사과 농가 과수화상병 피해가 커져 매몰과 긴급 방제가 이어지고 있다.",
            link="https://example.com/pest-fire-b",
        )
        fire_c = self._make_article(
            section="pest",
            title="담양군, 사과·배 농가 방제 총력…과수화상병 유입 차단",
            description="담양군이 사과와 배 농가에 약제비를 지원하고 과수화상병 유입 차단 방제를 추진한다.",
            link="https://example.com/pest-fire-c",
        )
        fire_a.is_core = True
        fire_b.is_core = True
        final_by_section = {"pest": [fire_a, fire_b]}

        changed = main._refill_pest_direct_gap_from_raw(final_by_section, {"pest": [fire_c]}, target=3)

        links = {article.link for article in final_by_section["pest"]}
        self.assertEqual(changed, 1)
        self.assertIn(fire_c.link, links)

    def test_duplicate_pest_theme_cleanup_preserves_target_direct_fire_blight(self) -> None:
        fire_a = self._make_article(
            section="pest",
            title="치료제 없는 과수화상병…전국 과일 농가 초비상",
            description="과수화상병 확산으로 사과와 배 농가 피해와 매몰 대응이 이어지고 있다.",
            link="https://example.com/pest-fire-core-a",
        )
        fire_b = self._make_article(
            section="pest",
            title="과수화상병 즉시 신고를…이중진단키트 활용 예찰 강화",
            description="과수화상병 예찰과 즉시 신고, 방제 대응을 강화한다.",
            link="https://example.com/pest-fire-core-b",
        )
        fire_direct = self._make_article(
            section="pest",
            title="담양군, 사과·배 농가 방제 총력…과수화상병 유입 차단",
            description="사과와 배 농가에 약제비를 지원하고 과수화상병 유입 차단 방제를 추진한다.",
            link="https://example.com/pest-fire-direct",
        )
        pepper = self._make_article(
            section="pest",
            title="안동시, 고추 진딧물·총채벌레 급증 우려…적기 방제 당부",
            description="고추 진딧물과 총채벌레 피해 예방을 위해 예찰과 방제가 필요하다.",
            link="https://example.com/pest-pepper",
        )
        tomato = self._make_article(
            section="pest",
            title="토마토뿔나방 확산 우려…시설하우스 예찰 강화",
            description="토마토뿔나방 피해 예방을 위해 시설하우스 예찰과 방제를 강화한다.",
            link="https://example.com/pest-tomato",
        )
        fire_a.is_core = True
        fire_b.is_core = True
        final_by_section = {"pest": [fire_a, fire_b, fire_direct, pepper, tomato]}

        self.assertEqual(main._drop_duplicate_pest_theme_tail(final_by_section, min_items=4), 0)
        self.assertEqual(len(final_by_section["pest"]), 5)
        self.assertIn(fire_direct, final_by_section["pest"])

    def test_render_cleanup_preserves_preferred_pest_count(self) -> None:
        fire_a = self._make_article(
            section="pest",
            title="치료제 없는 과수화상병…전국 과일 농가 초비상",
            description="과수화상병 확산으로 사과와 배 농가 피해와 매몰 대응이 이어지고 있다.",
            link="https://example.com/render-pest-fire-a",
        )
        fire_b = self._make_article(
            section="pest",
            title="과수화상병 즉시 신고를…이중진단키트 활용 예찰 강화",
            description="과수화상병 예찰과 즉시 신고, 방제 대응을 강화한다.",
            link="https://example.com/render-pest-fire-b",
        )
        fire_direct = self._make_article(
            section="pest",
            title="담양군, 사과·배 농가 방제 총력…과수화상병 유입 차단",
            description="사과와 배 농가에 약제비를 지원하고 과수화상병 유입 차단 방제를 추진한다.",
            link="https://example.com/render-pest-fire-direct",
        )
        pepper = self._make_article(
            section="pest",
            title="[요즘 이기술] 장마철 고추 병해 예방하려면…땅 적정 산성도 유지",
            description="장마철 고추 병해 예방을 위해 토양 산성도와 배수 관리, 예찰이 필요하다.",
            link="https://example.com/render-pest-pepper",
        )
        tomato = self._make_article(
            section="pest",
            title="토마토뿔나방 확산 우려…시설하우스 예찰 강화",
            description="토마토뿔나방 피해 예방을 위해 시설하우스 예찰과 방제를 강화한다.",
            link="https://example.com/render-pest-tomato",
        )
        fire_a.is_core = True
        fire_b.is_core = True
        by_section = {"supply": [], "policy": [], "dist": [], "pest": [fire_a, fire_b, fire_direct, pepper, tomato]}

        html = main.render_daily_page(
            "2026-06-19",
            datetime(2026, 6, 18, 6, 0, tzinfo=main.KST),
            datetime(2026, 6, 19, 6, 0, tzinfo=main.KST),
            by_section,
            ["2026-06-19"],
            "/agri-news-brief/",
        )

        self.assertEqual(len(by_section["pest"]), 5)
        self.assertIn("render-pest-fire-direct", html)
        self.assertIn("render-pest-tomato", html)

    def test_render_guard_never_reduces_dist_below_five(self) -> None:
        articles = [
            self._make_article(
                section="dist",
                title=f"농산물 도매시장 운영 개선 {idx}",
                description="도매시장 경매와 산지 출하 운영을 개선한다.",
                link=f"https://example.com/render-dist-safe-{idx}",
            )
            for idx in range(4)
        ]
        weak_first_shipment = self._make_article(
            section="dist",
            title="햇사레 복숭아 본격 출하",
            description="첫 출하 기념식과 브랜드 홍보, 판매 활성화 계획을 소개했다.",
            link="https://example.com/render-dist-first-shipment",
            topic="복숭아",
        )
        by_section = {
            "supply": [],
            "policy": [],
            "dist": articles + [weak_first_shipment],
            "pest": [],
        }

        main.render_daily_page(
            "2026-06-29",
            datetime(2026, 6, 26, 6, 0, tzinfo=main.KST),
            datetime(2026, 6, 29, 6, 0, tzinfo=main.KST),
            by_section,
            ["2026-06-29"],
            "/agri-news-brief/",
        )

        self.assertEqual(len(by_section["dist"]), 5)

    def test_pest_diversity_replacement_accepts_pepper_disease_prevention(self) -> None:
        fire_core_a = self._make_article(
            section="pest",
            title="치료제 없는 과수화상병…전국 과일 농가 초비상",
            description="과수화상병 확산으로 사과와 배 농가 피해와 매몰 대응이 이어지고 있다.",
            link="https://example.com/pest-diversity-fire-a",
        )
        fire_core_b = self._make_article(
            section="pest",
            title="과수화상병 즉시 신고를…이중진단키트 활용 예찰 강화",
            description="과수화상병 예찰과 즉시 신고, 방제 대응을 강화한다.",
            link="https://example.com/pest-diversity-fire-b",
        )
        fire_tail = self._make_article(
            section="pest",
            title="담양군, 사과·배 농가 방제 총력…과수화상병 유입 차단",
            description="사과와 배 농가에 약제비를 지원하고 과수화상병 유입 차단 방제를 추진한다.",
            link="https://example.com/pest-diversity-fire-tail",
        )
        input_tail = self._make_article(
            section="pest",
            title="신젠타 인시피오Ⓡ, 미국·대만·일본에 등록 완료",
            description="나방, 노린재, 응애, 총채벌레 등을 두루 방제하는 약제가 해외 등록을 마쳤다.",
            link="https://example.com/pest-diversity-input",
        )
        pepper = self._make_article(
            section="pest",
            title="[요즘 이기술] 장마철 고추 병해 예방하려면…땅 적정 산성도 유지",
            description="장마철 고추 병해 예방을 위해 토양 산성도와 배수 관리, 예찰이 필요하다.",
            link="https://example.com/pest-diversity-pepper",
            topic="고추",
        )
        fire_core_a.is_core = True
        fire_core_b.is_core = True
        final_by_section = {"pest": [fire_core_a, fire_core_b, fire_tail, input_tail]}

        self.assertTrue(main._is_pest_direct_gap_story(pepper))
        self.assertFalse(main._is_pest_weather_disaster_noise(pepper))
        self.assertFalse(main._is_generic_pest_notice_tail(pepper))
        self.assertEqual(main._replace_duplicate_pest_theme_tail_from_raw(final_by_section, {"pest": [pepper]}), 1)
        themes = [main._pest_editorial_theme_key(article) for article in final_by_section["pest"]]
        self.assertLessEqual(themes.count("fire_blight"), 2)
        self.assertIn(pepper.link, {article.link for article in final_by_section["pest"]})

    def test_pest_diversity_gap_refill_uses_input_and_climate_tails(self) -> None:
        fire_core_a = self._make_article(
            section="pest",
            title="치료제 없는 과수화상병…전국 과일 농가 초비상",
            description="과수화상병 확산으로 사과와 배 농가 피해와 매몰 대응이 이어지고 있다.",
            link="https://example.com/pest-gap-fire-a",
        )
        fire_core_b = self._make_article(
            section="pest",
            title="과수화상병 즉시 신고를…이중진단키트 활용 예찰 강화",
            description="과수화상병 예찰과 즉시 신고, 방제 대응을 강화한다.",
            link="https://example.com/pest-gap-fire-b",
        )
        fire_tail = self._make_article(
            section="pest",
            title="담양군, 사과·배 농가 방제 총력…과수화상병 유입 차단",
            description="사과와 배 농가에 약제비를 지원하고 과수화상병 유입 차단 방제를 추진한다.",
            link="https://example.com/pest-gap-fire-tail",
        )
        pepper = self._make_article(
            section="pest",
            title="[요즘 이기술] 장마철 고추 병해 예방하려면…땅 적정 산성도 유지",
            description="장마철 고추 병해 예방을 위해 토양 산성도와 배수 관리, 예찰이 필요하다.",
            link="https://example.com/pest-gap-pepper",
        )
        input_tail = self._make_article(
            section="pest",
            title="신젠타 인시피오Ⓡ, 미국·대만·일본에 등록 완료",
            description="나방, 노린재, 응애, 총채벌레 등을 두루 방제하는 약제가 해외 등록을 마쳤다.",
            link="https://example.com/pest-gap-input",
        )
        climate_tail = self._make_article(
            section="pest",
            title="기후위기 넘는 청송사과…스마트농업으로 미래를 심다",
            description="기후위기와 이상기후에 대응해 사과 농가가 스마트농업으로 생육 관리와 피해 예방을 강화한다.",
            link="https://example.com/pest-gap-climate",
        )
        fire_core_a.is_core = True
        fire_core_b.is_core = True
        final_by_section = {"pest": [fire_core_a, fire_core_b, fire_tail, pepper]}

        self.assertTrue(main._is_pest_crop_protection_input_fallback(input_tail))
        self.assertTrue(main._is_pest_climate_risk_fallback(climate_tail))
        changed = main._refill_pest_diversity_gap_from_raw(
            final_by_section,
            {"pest": [input_tail, climate_tail]},
            target=5,
        )

        links = {article.link for article in final_by_section["pest"]}
        themes = [main._pest_editorial_theme_key(article) for article in final_by_section["pest"]]
        self.assertEqual(changed, 2)
        self.assertEqual(len(final_by_section["pest"]), 5)
        self.assertLessEqual(themes.count("fire_blight"), 2)
        self.assertNotIn(fire_tail.link, links)
        self.assertIn(input_tail.link, links)
        self.assertIn(climate_tail.link, links)

    def test_supply_rejects_pest_management_tail(self) -> None:
        article = self._make_article(
            section="supply",
            title="장마철 사과 과원 관리 비상. 철저한 배수 병해 예방 필요",
            description="장마철 사과 과원은 철저한 배수와 병해 예방, 방제 관리가 중요하다.",
            link="https://example.com/supply-pest-management",
        )

        self.assertEqual(
            main._postbuild_article_reject_reason(article, "supply", apply_selection_fit=False),
            "supply_pest_management_not_supply",
        )
        self.assertEqual(main._postbuild_article_reject_reason(article, "pest", apply_selection_fit=False), "")

    def test_policy_rejects_meeting_schedule_and_vague_supply_response_tails(self) -> None:
        meeting = self._make_article(
            section="policy",
            title="농자재값 폭등·농지 규제 혁신…위기의 농업 타개할 실효적 대책 시급",
            description="품목농협 조합장들이 운영협의회 회의를 열고 정부 지원책과 규제 혁신을 촉구했다.",
            link="https://example.com/policy-meeting-request",
        )
        assembly = self._make_article(
            section="policy",
            title="경남도의회, 제433회 임시회 폐회 제12대 의회 사실상 마무리",
            description="도의회 임시회 폐회와 회기 마무리를 전하는 일정성 기사다.",
            link="https://example.com/policy-assembly-schedule",
        )
        vague = self._make_article(
            section="policy",
            title="정부, 여름철 재해 대비 농축산물 안정적 공급 대책 추진",
            description="정부가 여름철 농축산물 수급안정대책반을 구성하고 공급 대책을 추진한다.",
            link="https://example.com/policy-vague-supply",
        )
        specific = self._make_article(
            section="policy",
            title="정부, 배추·무 3.4만톤 비축, 계란 3천만개 수입…여름 물가 안정 총력",
            description="농식품부가 배추·무 3.4만톤 비축과 계란 3천만개 수입 등 수급 안정 대책을 추진한다.",
            link="https://example.com/policy-specific-supply",
        )

        self.assertEqual(
            main._postbuild_article_reject_reason(meeting, "policy", apply_selection_fit=False),
            "policy_industry_meeting_request_filler",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(assembly, "policy", apply_selection_fit=False),
            "policy_assembly_schedule_filler",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(vague, "policy", apply_selection_fit=False),
            "policy_vague_supply_response_tail",
        )
        self.assertEqual(main._postbuild_article_reject_reason(specific, "policy", apply_selection_fit=False), "")

    def test_relaxed_preferred_refill_uses_clean_same_section_candidate(self) -> None:
        supply_items = [
            self._make_article(
                section="supply",
                title=f"양파 가격 하락에 산지 농가 시름 {idx}",
                description="양파 가격 하락과 출하 물량 부담으로 산지 농가 어려움이 커지고 있다.",
                link=f"https://example.com/supply-existing-{idx}",
            )
            for idx in range(4)
        ]
        candidate = self._make_article(
            section="supply",
            title="햇양파 가격 폭락...양파김치 나누기 등 소비 촉진 운동",
            description="햇양파 가격 폭락으로 농가 어려움이 커져 양파 소비 촉진 운동을 진행한다.",
            link="https://example.com/supply-clean-refill",
        )
        duplicate = self._make_article(
            section="supply",
            title="양파 가격 하락에 산지 농가 시름 1",
            description="양파 가격 하락과 출하 물량 부담으로 산지 농가 어려움이 커지고 있다.",
            link="https://example.com/supply-duplicate",
        )
        final_by_section = {"supply": supply_items, "policy": [], "dist": [], "pest": []}

        changed = main._refill_preferred_section_counts_relaxed_from_raw(
            final_by_section,
            {"supply": [duplicate, candidate]},
            target=5,
        )

        self.assertEqual(changed, 1)
        self.assertEqual(len(final_by_section["supply"]), 5)
        self.assertIn(candidate.link, {article.link for article in final_by_section["supply"]})
        self.assertNotIn(duplicate.link, {article.link for article in final_by_section["supply"]})

    def test_policy_editorial_guard_replaces_local_application_tail(self) -> None:
        core = self._make_article(
            section="policy",
            title="농민의길 “농특세, 농산물 가격 안정에 우선 써야”",
            description="농민단체가 농특세를 농산물 가격 안정과 농어촌 정책 재원으로 써야 한다고 주장했다.",
            link="https://example.com/policy-core",
        )
        weak = self._make_article(
            section="policy",
            title="횡성군, 2027년 유기질 비료 지원사업 접수 시작",
            description="지역 농가를 대상으로 유기질 비료 지원사업 신청 접수를 안내했다.",
            link="https://example.com/policy-local-fertilizer",
        )
        bad_origin_dispute = self._make_article(
            section="policy",
            title="“한국, 샤인머스캣 훔치더니 대박”…950억 손실 日, 소 잃고",
            description="일본 과일 품종 원조 주장을 다룬 해외 논쟁 기사다.",
            link="https://example.com/policy-shine-origin",
        )
        bad_local_labor = self._make_article(
            section="policy",
            title="영양군, 외국인 계절근로자 247명 추가 입국",
            description="농번기 인력난 해소를 위한 지역 근로자 입국 안내 기사다.",
            link="https://example.com/policy-seasonal-worker",
        )
        bad_labor_help = self._make_article(
            section="policy",
            title="농협 의정부시지부, 고산면 마늘농가 일손돕기",
            description="농협 임직원이 마늘농가에서 농촌 일손돕기 활동을 실시했다.",
            link="https://example.com/policy-labor-help",
        )
        better = self._make_article(
            section="policy",
            title="[국가책임농정 1년] 예산·법제화 지속 과제",
            description="정부 국가책임농정 1년을 맞아 농가소득, 농업 예산, 법제화 과제를 점검했다.",
            link="https://example.com/policy-national",
        )
        core.is_core = True
        final_by_section = {"policy": [core, weak]}

        self.assertEqual(
            main._replace_policy_editorial_weak_tail_from_raw(
                final_by_section,
                {"policy": [bad_origin_dispute, bad_local_labor, bad_labor_help, better]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["policy"]}
        self.assertNotIn(weak.link, links)
        self.assertNotIn(bad_origin_dispute.link, links)
        self.assertNotIn(bad_local_labor.link, links)
        self.assertNotIn(bad_labor_help.link, links)
        self.assertIn(better.link, links)

    def test_policy_structure_guard_steals_high_signal_story_from_supply(self) -> None:
        supply_policy_story = self._make_article(
            section="supply",
            title="양파산업 위기 해법 찾는다",
            description="양파 가격 하락과 수급 불안이 이어지며 산업 위기 해법을 논의했다.",
            link="https://example.com/policy-onion-industry",
        )
        weak_policy = self._make_article(
            section="policy",
            title="횡성군, 2027년 유기질 비료 지원사업 접수 시작",
            description="지역 농가를 대상으로 유기질 비료 지원사업 신청 접수를 안내했다.",
            link="https://example.com/policy-local-application",
        )
        supply_refill = self._make_article(
            section="supply",
            title="광양매실 생산량 급증...가격은 전년보다 하락 조짐",
            description="매실 생산량 급증과 소비 부진으로 산지 가격 하락 우려가 커지고 있다.",
            link="https://example.com/supply-maesil-price",
        )
        supply_refill.selection_fit_score = 1.8
        final_by_section = {"supply": [supply_policy_story], "policy": [weak_policy]}

        self.assertEqual(
            main._replace_policy_weak_tail_with_structure_issue_from_raw(
                final_by_section,
                {"policy": [supply_policy_story], "supply": [supply_refill]},
            ),
            1,
        )
        policy_links = {article.link for article in final_by_section["policy"]}
        supply_links = {article.link for article in final_by_section["supply"]}
        self.assertIn(supply_policy_story.link, policy_links)
        self.assertNotIn(supply_policy_story.link, supply_links)
        self.assertIn(supply_refill.link, supply_links)

    def test_shadow_repair_avoids_same_local_commodity_repeat(self) -> None:
        onion_core = self._make_article(
            section="supply",
            title="“캘수록 손해” 창녕 양파 수확농가의 눈물",
            description="양파 산지 가격 하락과 인건비 상승으로 수확 농가 손실이 커지고 있다.",
            link="https://example.com/shadow-onion-core",
        )
        machine_demo = self._make_article(
            section="supply",
            title="창녕서 마늘 전 과정 기계화 기술 공개…농촌 인력난 해법 제시",
            description="마늘 파종부터 수확까지 기계화 기술을 공개하는 행사성 기사다.",
            link="https://example.com/shadow-machine-demo",
        )
        machine_efficiency = self._make_article(
            section="supply",
            title="경북 영천시, 마늘 수확 작업 기계화 및 농가 경영 효율화에 주력",
            description="마늘 수확 작업 기계화와 농가 경영 효율화를 소개하는 기사다.",
            link="https://example.com/shadow-machine-efficiency",
        )
        gwangyang_supply = self._make_article(
            section="supply",
            title="광양매실 생산량 급증...가격은 전년보다 하락 조짐",
            description="매실 생산량 급증과 소비 부진으로 산지 가격 하락 우려가 커지고 있다.",
            link="https://example.com/shadow-gwangyang-supply",
        )
        gwangyang_repeat = self._make_article(
            section="supply",
            title="광양 매실 냉해 없어 '풍작'.. 가격은 걱정",
            description="광양 매실 생산량이 늘며 산지 가격 하락 걱정이 커지고 있다.",
            link="https://example.com/shadow-gwangyang-repeat",
        )
        melon_origin = self._make_article(
            section="supply",
            title="타 지역 참외의 '성주참외' 둔갑 정황 포착",
            description="타 지역 참외가 성주참외로 둔갑했다는 정황이 포착돼 농가 우려가 커졌다.",
            link="https://example.com/shadow-seongju-origin",
        )
        tomato_competitiveness = self._make_article(
            section="supply",
            title="충남 대추형 방울 토마토 신품종 경쟁력 입증",
            description="대추형 방울토마토 신품종의 생산성과 시장 경쟁력을 확인했다.",
            link="https://example.com/shadow-tomato-competitiveness",
        )
        ugly_maesil = self._make_article(
            section="dist",
            title="진주문산농협, 못난이 매실 가공용 수매 지원 나선다",
            description="규격외 매실을 가공용으로 수매해 산지 물량 부담을 줄이는 조치다.",
            link="https://example.com/shadow-ugly-maesil",
        )
        onion_core.is_core = True
        final_by_section = {"supply": [onion_core, machine_demo, machine_efficiency], "policy": [], "dist": []}

        changed = main._repair_editorial_shadow_issues_from_raw(
            final_by_section,
            {"supply": [gwangyang_supply, gwangyang_repeat, melon_origin, tomato_competitiveness], "dist": [ugly_maesil]},
        )

        links = {article.link for article in final_by_section["supply"]}
        self.assertGreaterEqual(changed, 2)
        self.assertIn(gwangyang_supply.link, links)
        self.assertIn(melon_origin.link, links)
        self.assertIn(tomato_competitiveness.link, links)
        self.assertNotIn(gwangyang_repeat.link, links)
        self.assertNotIn(ugly_maesil.link, links)

    def test_dist_editorial_guard_replaces_promotional_watermelon_tail(self) -> None:
        core = self._make_article(
            section="dist",
            title="[일본 도매시장, 경계를 허물다] 3사 거점 하나로 묶어 물류비 확 줄였다",
            description="일본 도매시장 물류 거점 통합으로 비용 절감과 유통 효율 개선이 나타났다.",
            link="https://example.com/dist-core-market",
        )
        weak = self._make_article(
            section="dist",
            title="대한민국 대표 여름 과일 '고창수박' 본격 출하 …전국 소비자 입맛 공략",
            description="첫 출하식과 브랜드 판촉을 중심으로 전국 소비자 입맛 공략에 나섰다.",
            link="https://example.com/dist-watermelon",
        )
        weak_two = self._make_article(
            section="dist",
            title="고당도 ‘다올찬수박’ 본격 출하",
            description="수박 출하식과 고당도 브랜드 판촉을 중심으로 소개했다.",
            link="https://example.com/dist-watermelon-two",
        )
        better = self._make_article(
            section="dist",
            title="농산물 도매시장법인 해킹 공격…농민 출하정보 보안 비상",
            description="도매시장법인이 해킹 공격을 받아 출하정보 보안과 시장 운영 대응을 강화한다.",
            link="https://example.com/dist-nonghyupmall",
        )
        better_two = self._make_article(
            section="dist",
            title="제주산 블루베리 판매량 쑥…유통 망 확대 성과",
            description="블루베리 유통 망 확대와 판로 관리로 판매량이 늘었다.",
            link="https://example.com/dist-blueberry-network",
        )
        core.is_core = True
        final_by_section = {"dist": [core, weak, weak_two]}

        self.assertEqual(main._replace_dist_editorial_promo_tail_from_raw(final_by_section, {"dist": [better, better_two]}), 2)
        links = {article.link for article in final_by_section["dist"]}
        self.assertNotIn(weak.link, links)
        self.assertNotIn(weak_two.link, links)
        self.assertIn(better.link, links)
        self.assertIn(better_two.link, links)

    def test_dist_title_ops_fallback_replaces_remaining_promotional_tail(self) -> None:
        core = self._make_article(
            section="dist",
            title="[일본 도매시장, 경계를 허물다] 3사 거점 하나로 묶어 물류비 확 줄였다",
            description="도매시장 물류 거점 통합으로 유통 효율을 높였다.",
            link="https://example.com/dist-core-market-two",
        )
        weak = self._make_article(
            section="dist",
            title="대한민국 대표 여름 과일 '고창수박' 본격 출하 …전국 소비자 입맛 공략",
            description="브랜드 판촉과 입맛 공략을 중심으로 소개했다.",
            link="https://example.com/dist-gocang-promo-tail",
        )
        existing_jeju = self._make_article(
            section="dist",
            title="제주 농산물 산지 유통 경쟁력 강화...저온유통체계 구축 추진",
            description="제주 농산물 산지 유통 경쟁력과 저온유통체계 구축을 추진한다.",
            link="https://example.com/dist-jeju-existing",
        )
        blueberry = self._make_article(
            section="dist",
            title="제주산 블루베리 판매량 쑥…유통 망 확대 성과",
            description="제주산 블루베리가 유통 망 확대와 판로 관리로 판매량을 늘렸다.",
            link="https://example.com/dist-blueberry-title-ops",
        )
        jeju_duplicate = self._make_article(
            section="dist",
            title="제주 농산물, 산지 저온유통체계 구축...신선도 잡는다",
            description="제주 농산물 산지 저온유통체계를 구축한다.",
            link="https://example.com/dist-jeju-duplicate",
        )
        core.is_core = True
        final_by_section = {"dist": [core, weak, existing_jeju], "supply": []}

        self.assertEqual(
            main._replace_dist_promo_tail_with_title_ops_from_raw(
                final_by_section,
                {"dist": [jeju_duplicate, blueberry], "supply": []},
            ),
            1,
        )
        links = {article.link for article in final_by_section["dist"]}
        self.assertNotIn(weak.link, links)
        self.assertIn(blueberry.link, links)

    def test_commodity_pool_guard_matches_published_title_link_contract(self) -> None:
        event = self._make_article(
            section="supply",
            title="파프리카 생산자자조회, 27~30일 15만 개 할인 행사",
            description="파프리카 할인 행사를 진행한다.",
            link="https://example.com/paprika-discount",
            topic="파프리카",
        )
        safe = self._make_article(
            section="supply",
            title="파프리카 가격 하락…출하 물량 조절 착수",
            description="파프리카 가격과 출하 물량을 조절한다.",
            link="https://example.com/paprika-market",
            topic="파프리카",
        )
        flower = self._make_article(
            section="supply",
            title="충남 대표 백합 4계통 선발…수입 구근 대체",
            description="화훼 산업의 백합 품종을 선발했다.",
            link="https://example.com/lily",
            topic="화훼",
        )
        item = {"key": "paprika", "label": "파프리카"}
        safe_metrics = {
            "board_eligible": True,
            "title_primary_hits": 1,
            "title_context_hits": 0,
            "pattern_hits": 0,
            "representative_rank": 3,
            "selection_fit_score": 1.8,
            "issue_bucket": "commodity_issue",
            "market_response": True,
        }

        self.assertFalse(main._commodity_board_article_is_safe_pool_candidate(item, event, safe_metrics))
        self.assertTrue(main._commodity_board_article_is_safe_pool_candidate(item, safe, safe_metrics))
        self.assertFalse(
            main._commodity_board_pool_title_has_eval_item_focus(
                {"key": "flowers", "label": "화훼"},
                flower.title,
            )
        )

    def test_publish_quality_guards_flag_weekly_promotional_and_opinion_tails(self) -> None:
        festival = self._make_article(
            section="supply",
            title="광주시 퇴촌 토마토 거리축제 33만명 방문 속 마무리",
            description="지역 축제 방문객과 토마토 홍보 성과를 소개한다.",
            link="https://example.com/tomato-festival",
        )
        first_ship = self._make_article(
            section="supply",
            title="예천 복숭아 본격 출하…전국 소비자 식탁 찾는다",
            description="지역 복숭아의 첫 출하와 홍보 계획을 알렸다.",
            link="https://example.com/peach-first-ship",
        )
        column = self._make_article(
            section="policy",
            title="[편집자 칼럼] 저출산의 부메랑이 농식품 시장을 강타한다",
            description="저출산과 농식품 시장을 다룬 칼럼이다.",
            link="https://example.com/policy-column",
        )
        demand = self._make_article(
            section="policy",
            title="주요 농산물 공공수급제 실시, 반값 농자재를 보장하라",
            description="농민단체가 기자회견에서 정책 도입을 촉구했다.",
            link="https://example.com/policy-demand",
        )
        tour = self._make_article(
            section="dist",
            title="파라과이 농업 관계자들, 스마트 APC 견학",
            description="방문단이 산지유통시설을 둘러보고 놀랍다는 반응을 보였다.",
            link="https://example.com/apc-tour",
        )

        self.assertTrue(main._is_supply_editorial_weak_tail(festival))
        self.assertTrue(main._is_supply_editorial_weak_tail(first_ship))
        self.assertTrue(main._is_policy_editorial_weak_tail(column))
        self.assertTrue(main._is_policy_editorial_weak_tail(demand))
        self.assertTrue(main._is_dist_editorial_promo_tail(tour))

    def test_dist_editorial_gap_refill_uses_operational_market_candidate(self) -> None:
        existing = [
            self._make_article(
                section="dist",
                title=title,
                description=description,
                link=f"https://example.com/dist-existing-{idx}",
            )
            for idx, (title, description) in enumerate(
                (
                    ("가락시장 배추 경매시간 조정", "도매시장 경매시간을 조정한다."),
                    ("합천 양파 톤백 수매 시작", "양파 톤백 수매와 선별을 시작한다."),
                    ("국산 고춧가루 미국 수출 선적", "고춧가루 수출 선적 물량을 확대한다."),
                    ("산지 농산물 저온유통 가동", "산지 저온유통 시설을 가동한다."),
                )
            )
        ]
        candidate = self._make_article(
            section="dist",
            title="매년 수십억 적자 인천 공영도매시장, 공사 전환 추진",
            description="인천 공영 농산물도매시장의 운영 구조와 정산 체계를 공사 전환으로 개선한다.",
            link="https://example.com/incheon-market-ops",
        )
        final_by_section = {"dist": existing, "supply": [], "policy": [], "pest": []}

        self.assertEqual(
            main._refill_dist_editorial_ops_gap_from_raw(
                final_by_section,
                {"dist": [candidate], "supply": [], "policy": []},
                target=5,
            ),
            1,
        )
        self.assertEqual(len(final_by_section["dist"]), 5)
        self.assertIn(candidate.link, {article.link for article in final_by_section["dist"]})

    def test_supply_wrong_section_noise_uses_market_duplicate_as_last_resort(self) -> None:
        existing = self._make_article(
            section="supply",
            title="제주 월동채소 생산 늘었지만 가격 '뚝'",
            description="월동채소 생산량 증가와 가격 하락을 다룬다.",
            link="https://example.com/winter-veg-existing",
        )
        wrong = self._make_article(
            section="supply",
            title="삼계탕 3만원에 냉면도 1만6000원…4인가족 외식비 부담",
            description="복날 외식 메뉴 가격과 가족 외식비 부담을 다룬다.",
            link="https://example.com/restaurant-price",
            topic="외식",
        )
        fallback = self._make_article(
            section="supply",
            title="월동채소 가격 반토막…생산 증가·소비 부진 여파",
            description="제주 월동채소 생산량 증가와 소비 부진으로 가격이 하락했다.",
            link="https://example.com/winter-veg-fallback",
            topic="배추",
        )
        fallback.selection_fit_score = 2.0
        final_by_section = {"supply": [existing, wrong], "policy": [], "dist": [], "pest": []}

        self.assertTrue(main._is_supply_publish_wrong_section_noise(wrong))
        self.assertEqual(
            main._replace_supply_editorial_weak_tail_from_raw(
                final_by_section,
                {"supply": [fallback], "policy": [], "dist": []},
            ),
            1,
        )
        self.assertNotIn(wrong.link, {article.link for article in final_by_section["supply"]})
        self.assertIn(fallback.link, {article.link for article in final_by_section["supply"]})

    def test_publish_editorial_duplicate_story_catches_weekly_issue_variants(self) -> None:
        winter_one = self._make_article(
            section="supply",
            title="제주 월동채소 생산 늘었지만 가격 뚝",
            description="생산량 증가와 가격 약세를 다룬다.",
            link="https://example.com/winter-one",
        )
        winter_two = self._make_article(
            section="supply",
            title="월동채소 가격 반토막…소비 부진 여파",
            description="생산 증가와 소비 부진을 다룬다.",
            link="https://example.com/winter-two",
        )
        trade_one = self._make_article(
            section="dist",
            title="함양군, 양파 출하철 외상거래 피해 주의",
            description="표준계약서 작성을 당부했다.",
            link="https://example.com/trade-one",
        )
        trade_two = self._make_article(
            section="dist",
            title="양파 외상거래 농업인 피해예방…표준계약서 작성",
            description="구두계약 피해 예방을 안내했다.",
            link="https://example.com/trade-two",
        )

        self.assertTrue(main._publish_editorial_duplicate_story("supply", winter_one, winter_two))
        self.assertTrue(main._publish_editorial_duplicate_story("dist", trade_one, trade_two))

    def test_publish_editorial_guard_separates_events_from_market_operations(self) -> None:
        event = self._make_article(
            section="dist",
            title="농산물 생산자와 구매사 한자리에 직거래 판로 넓힌다",
            description="구매상담회를 열어 신규 판로를 소개했다.",
            link="https://example.com/buyer-event",
        )
        automation = self._make_article(
            section="dist",
            title="유온로보틱스, APC 자동화 사업 수주",
            description="산지유통센터 선별 공정을 자동화한다.",
            link="https://example.com/apc-automation",
        )
        tariff = self._make_article(
            section="policy",
            title="국산 과일 한창때 할당관세 재연장 논란",
            description="정부의 과일 할당관세 연장 여부를 다룬다.",
            link="https://example.com/fruit-tariff",
        )

        self.assertTrue(main._is_publish_dist_editorial_weak(event))
        self.assertFalse(main._is_publish_dist_editorial_weak(automation))
        self.assertTrue(main._is_publish_editorial_candidate("dist", automation))
        self.assertFalse(main._is_publish_policy_editorial_weak(tariff))
        self.assertTrue(main._is_publish_editorial_candidate("policy", tariff))

    def test_dist_market_facility_cooperation_is_operational_candidate(self) -> None:
        article = self._make_article(
            section="dist",
            title="대아청과·애월농협, 제주산 농산물 유통 활성화 '맞손'",
            description=(
                "대아청과와 애월농협이 경매장과 저온창고를 점검하고 양배추·쪽파·브로콜리 "
                "거래 현황을 확인했다. 전자경매 시스템과 오프라인 출하 협력도 논의했다."
            ),
            link="https://example.com/dist-market-facility-cooperation",
            topic="도매시장",
        )

        self.assertTrue(main._is_dist_market_facility_cooperation_story(article))
        self.assertTrue(main._is_dist_operational_upgrade_candidate(article))
        self.assertTrue(main._is_publish_editorial_candidate("dist", article))

    def test_publish_editorial_duplicate_story_groups_price_package_and_onion_response(self) -> None:
        package_one = self._make_article(
            section="policy",
            title="1조 투입해 8월 고비 정조준…정부, 하반기 물가 방어 총력",
            description="정부가 하반기 물가 대책을 발표했다.",
            link="https://example.com/price-package-one",
        )
        package_two = self._make_article(
            section="policy",
            title="정부, 물가 안정에 1조 투입…공공요금 동결",
            description="정부가 같은 하반기 물가 대책을 내놨다.",
            link="https://example.com/price-package-two",
        )
        onion_one = self._make_article(
            section="supply",
            title="경북도, 가격 하락 양파 농가 지원 나서",
            description="경북 양파 가격 급락 대응책이다.",
            link="https://example.com/onion-response-one",
            topic="양파",
        )
        onion_two = self._make_article(
            section="supply",
            title="양파값 30% 급락…경북도 소비·수출 확대 총력 대응",
            description="경북도가 양파 소비와 수출 확대에 나섰다.",
            link="https://example.com/onion-response-two",
            topic="양파",
        )

        self.assertTrue(main._publish_editorial_duplicate_story("policy", package_one, package_two))
        self.assertTrue(main._publish_editorial_duplicate_story("supply", onion_one, onion_two))

    def test_publish_policy_guard_rejects_retrospective_and_accepts_current_instruments(self) -> None:
        retrospective = self._make_article(
            section="policy",
            title="농업 희생 전제로 산업화 뒷받침한 1960년대 농업정책",
            description="과거 농업정책의 역사를 회고한다.",
            link="https://example.com/policy-retrospective",
        )
        tariff = self._make_article(
            section="policy",
            title="먹거리 할당관세 확대…내 식탁엔 무엇이 달라질까",
            description="정부가 과일과 농산물 할당관세 대상을 확대한다.",
            link="https://example.com/policy-tariff-current",
        )
        seasonal_workers = self._make_article(
            section="policy",
            title="외국인 계절노동자 9만명 넘었는데 행정·재정 지원 태부족",
            description="계절노동자 제도의 중앙정부 행정 및 재정 지원 문제를 점검한다.",
            link="https://example.com/policy-seasonal-workers",
        )
        research_meeting = self._make_article(
            section="policy",
            title="농경연·농식품부, 농정 현안 대응 위한 ‘정책연구협의회’ 개최",
            description="두 기관이 농정 현안을 논의하는 협의회를 열었다.",
            link="https://example.com/policy-research-meeting",
        )

        self.assertTrue(main._is_publish_policy_editorial_weak(retrospective))
        self.assertTrue(main._is_publish_policy_editorial_weak(research_meeting))
        self.assertFalse(main._is_publish_editorial_candidate("policy", retrospective))
        self.assertFalse(main._is_publish_editorial_candidate("policy", research_meeting))
        self.assertTrue(main._is_publish_editorial_candidate("policy", tariff))
        self.assertTrue(main._is_publish_editorial_candidate("policy", seasonal_workers))

    def test_publish_policy_repair_collapses_price_package_and_upgrades_representative(self) -> None:
        price_package = [
            self._make_article(
                section="policy",
                title=title,
                description="정부가 같은 하반기 물가 안정 패키지를 발표했다.",
                link=f"https://example.com/policy-package-{idx}",
            )
            for idx, title in enumerate(
                (
                    "1조 투입해 8월 고비 정조준…정부, 하반기 물가 방어 총력",
                    "정부 3500억 농축산물 할인…불법수익 2배 환수 신설",
                    "국정 2년차, 물가와의 전쟁…가격 개입 현실화",
                    "정부, 물가 안정에 1조 투입…공공요금 동결",
                )
            )
        ]
        retrospective = self._make_article(
            section="policy",
            title="농업 희생 전제로 산업화 뒷받침한 1960년대 농업정책",
            description="과거 농업정책을 회고한다.",
            link="https://example.com/policy-old-history",
        )
        workers = self._make_article(
            section="policy",
            title="외국인 계절노동자 9만명 넘었는데 행정·재정 지원 태부족",
            description="농촌 계절노동자 제도의 중앙정부 지원 부족을 점검한다.",
            link="https://example.com/policy-workers-final",
        )
        best_package = self._make_article(
            section="policy",
            title="'계란 10개에 5000원'…물가 폭등에 1조원 쏟아 붓는다",
            description="정부가 농축수산물 할인과 수입 지원을 담은 1조원 물가 대책을 발표했다.",
            link="https://example.com/policy-best-package",
        )
        best_package.score = 79.1
        tariff = self._make_article(
            section="policy",
            title="먹거리 할당관세 확대…내 식탁엔 무엇이 달라질까",
            description="정부의 농산물 할당관세 확대 효과를 분석한다.",
            link="https://example.com/policy-tariff-replacement",
        )
        cptpp = self._make_article(
            section="policy",
            title="CPTPP 수면 위로…농업계 검역 변수 촉각",
            description="CPTPP 가입 재추진에 따른 농산물 검역 정책 변화를 다룬다.",
            link="https://example.com/policy-cptpp",
        )
        advocacy = self._make_article(
            section="policy",
            title="농산물 가격 폭락·농자재값 폭등 대책 마련하라",
            description="농민단체가 공공수급제와 농자재 가격 대책을 정부와 국회에 요구했다.",
            link="https://example.com/policy-public-supply",
        )
        advocacy.selection_fit_score = 7.26
        tariff.selection_fit_score = 6.99
        homeplus = self._make_article(
            section="policy",
            title="농식품부, 홈플러스 미정산 산지유통조직에 300억 금융 지원 추진",
            description="농식품부가 홈플러스 미정산 피해 산지유통조직에 정책금융 지원을 추진한다.",
            link="https://example.com/policy-homeplus-finance",
        )
        final = {
            "supply": [],
            "policy": [*price_package, retrospective],
            "dist": [],
            "pest": [],
        }
        raw = {
            "supply": [],
            "policy": [best_package, tariff, cptpp, advocacy, workers, homeplus],
            "dist": [],
            "pest": [],
        }

        changed = main._repair_publish_editorial_selection(final, raw)
        self.assertGreaterEqual(
            changed,
            3,
            {
                "final": [(article.title, main._is_publish_editorial_candidate("policy", article)) for article in final["policy"]],
                "raw": [
                    (
                        article.title,
                        main._postbuild_article_reject_reason(article, "policy", apply_selection_fit=False),
                        main._is_publish_policy_editorial_weak(article),
                        main._is_publish_editorial_candidate("policy", article),
                    )
                    for article in raw["policy"]
                ],
            },
        )
        links = {article.link for article in final["policy"]}
        self.assertIn(price_package[1].link, links)
        self.assertIn(tariff.link, links)
        self.assertIn(cptpp.link, links)
        self.assertIn(workers.link, links)
        self.assertIn(homeplus.link, links)
        self.assertNotIn(best_package.link, links)
        self.assertNotIn(advocacy.link, links)
        self.assertNotIn(retrospective.link, links)
        self.assertEqual(
            sum(main._is_publish_policy_price_package_title(article.title) for article in final["policy"]),
            1,
        )

    def test_publish_dist_guard_replaces_labor_abuse_and_delegation_visit(self) -> None:
        labor_abuse = self._make_article(
            section="dist",
            title='"때려도 허락 없인 못 떠나"…노예의 덫 갇힌 이주노동자 눈물',
            description="이주노동자 폭행과 인권 침해 실태를 다룬 기사다.",
            link="https://example.com/dist-labor-abuse",
        )
        delegation = self._make_article(
            section="dist",
            title="파라과이 연수단 한반도농협 스마트 APC 방문",
            description="연수단이 APC 시설을 견학했다.",
            link="https://example.com/dist-delegation",
        )
        market = self._make_article(
            section="dist",
            title="여주 대신농협, 가락공판장 찾아 농산물 제값받기 협력 논의",
            description="산지 출하와 공판장 경매 운영 협력을 논의했다.",
            link="https://example.com/dist-market-cooperation",
        )
        matching = self._make_article(
            section="dist",
            title="생산·구매사 맞춤형 매칭…농가는 판로 열고 식탁물가도 잡고",
            description="농산물 생산자와 구매사를 수요에 맞춰 연결하는 판로 운영을 분석했다.",
            link="https://example.com/dist-matching",
        )
        political_event = self._make_article(
            section="dist",
            title="김진열 군위군수, 자두·복숭아 공동출하회 행사 참석해 농가 격려",
            description="군수가 초출하 행사에 참석해 농가를 격려했다.",
            link="https://example.com/dist-political-event",
        )

        self.assertTrue(main._is_publish_dist_editorial_weak(labor_abuse))
        self.assertTrue(main._is_publish_dist_editorial_weak(delegation))
        self.assertTrue(main._is_publish_dist_editorial_weak(political_event))
        self.assertTrue(main._is_publish_dist_editorial_weak(matching))
        self.assertFalse(main._is_publish_dist_editorial_weak(market))
        self.assertTrue(main._is_publish_editorial_candidate("dist", market))
        self.assertFalse(main._is_publish_editorial_candidate("dist", matching))

    def test_publish_guard_rejects_stale_event_reprints_and_stale_dated_article(self) -> None:
        advocacy = self._make_article(
            section="supply",
            title="농산물 가격폭락·농자재값 폭등 대책 마련하라",
            description=(
                "농민단체가 지난달 24일 국회에서 기자회견을 열고 "
                "공공수급제와 반값 농자재 대책을 촉구했다."
            ),
            link="https://example.com/stale-advocacy",
        )
        stale_matching = self._make_article(
            section="dist",
            title="생산·구매사 맞춤형 매칭…농가는 판로 열고 식탁물가도 잡고",
            description="63개사가 185건을 상담해 70억원 계약 성과를 냈다.",
            link="https://www.segye.com/newsView/20260318520952",
        )

        self.assertTrue(main._is_publish_stale_reprint(advocacy))
        self.assertTrue(main._is_publish_supply_editorial_weak(advocacy))
        self.assertFalse(main._is_publish_editorial_candidate("supply", advocacy))
        self.assertTrue(main._is_publish_stale_reprint(stale_matching))
        self.assertTrue(main._is_publish_dist_editorial_weak(stale_matching))
        self.assertFalse(main._is_publish_editorial_candidate("dist", stale_matching))

    def test_publish_dist_guard_promotes_supplier_payment_risk_over_first_shipment(self) -> None:
        first_shipment = self._make_article(
            section="dist",
            title="햇사레 복숭아 본격 출하",
            description=(
                "첫 출하 기념식에서 공동선별한 복숭아 105상자를 도매시장에 보냈다. "
                "브랜드 홍보와 판매 활성화 계획을 소개했다."
            ),
            link="https://example.com/peach-first-shipment",
            topic="복숭아",
        )
        supplier_risk = self._make_article(
            section="policy",
            title="농식품부, 홈플러스 미정산 산지 유통 조직에 300억 규모 금융 지원 추진",
            description=(
                "홈플러스에 농산물을 납품한 산지출하조직이 납품대금 269억원을 받지 못해 "
                "정부가 정책자금 상환 유예와 300억원 금융 지원을 추진한다."
            ),
            link="https://example.com/homeplus-supplier-risk",
        )

        self.assertTrue(main._is_publish_dist_editorial_weak(first_shipment))
        self.assertFalse(main._is_publish_editorial_candidate("dist", first_shipment))
        self.assertTrue(main._is_dist_supplier_payment_risk_story(supplier_risk))
        self.assertEqual(main._postbuild_article_reject_reason(supplier_risk, "dist"), "")
        self.assertFalse(main._is_publish_dist_editorial_weak(supplier_risk))
        self.assertTrue(main._is_publish_editorial_candidate("dist", supplier_risk))

    def test_publish_dist_core_prefers_measured_logistics_and_processing_outcomes(self) -> None:
        onion_ops = self._make_article(
            section="dist",
            title="양파 톤백 매입·선별로 농가 부담 덜었다",
            description="자동선별과 산지 경매로 비규격 양파 판로와 물류비 절감 성과를 냈다.",
            link="https://example.com/dist-onion-ops-core",
            topic="양파",
        )
        fast_logistics = self._make_article(
            section="dist",
            title="[K-푸드 산지 특송] 마트 도달 시간 1/3로…제주귤도 당일에",
            description="온라인 도매시장으로 유통 단계를 줄여 산지 배송 시간을 3분의 1로 단축했다.",
            link="https://example.com/dist-fast-logistics-core",
            topic="감귤",
        )
        meeting = self._make_article(
            section="dist",
            title="여주 대신농협, 가락공판장 찾아 농산물 제값받기 협력 논의",
            description="경매인 간담회와 경매 참관으로 판로 확대 방안을 논의했다.",
            link="https://example.com/dist-market-meeting-tail",
        )
        matching = self._make_article(
            section="dist",
            title="생산·구매사 맞춤형 매칭…농가는 판로 확대",
            description="63개사가 185건을 상담해 70억원 계약 성과를 냈다.",
            link="https://example.com/dist-matching-tail",
        )
        market = self._make_article(
            section="dist",
            title="경기 광역 로컬푸드 개장…농산물 판로 확대",
            description="광역 로컬푸드 시장을 개장해 산지 농산물 거래와 판로를 넓혔다.",
            link="https://example.com/dist-localfood-tail",
        )
        final = {
            "supply": [],
            "policy": [],
            "dist": [meeting, onion_ops, matching, fast_logistics, market],
            "pest": [],
        }

        main._repair_publish_editorial_selection(final, {"supply": [], "policy": [], "dist": [], "pest": []})

        core_links = {article.link for article in final["dist"] if article.is_core}
        self.assertEqual(core_links, {onion_ops.link, fast_logistics.link})

    def test_publish_guard_demotes_local_promo_but_keeps_material_pest_analysis(self) -> None:
        policy_promo = self._make_article(
            section="policy",
            title="농협, 양파 소비촉진 나섰다",
            description="지역 농협이 양파 직거래 행사와 판촉 활동을 진행했다.",
            link="https://example.com/policy-local-consumption-promo",
            topic="양파",
        )
        localfood_profile = self._make_article(
            section="dist",
            title="[판매농협이 간다] 광양원예농협, 로컬푸드직매장 성공으로 지역 농산물 판로 확대",
            description="로컬푸드직매장의 연매출과 운영 성과를 소개하는 농협 프로필 기사다.",
            link="https://example.com/dist-localfood-profile",
        )
        potato_giveaway = self._make_article(
            section="dist",
            title="오창농협, 감자 나눔행사·할인판매로 지역 농가 돕기",
            description="본점 앞 광장에서 감자 소비 활성화 행사를 열었다.",
            link="https://example.com/dist-potato-giveaway",
            topic="감자",
        )
        opinion = self._make_article(
            section="pest",
            title="[취재수첩] 과수화상병이 개꿀이라니",
            description="과수화상병 피해 보상 논란을 다룬 취재수첩이다.",
            link="https://example.com/pest-opinion",
        )
        foreign_quarantine = self._make_article(
            section="pest",
            title="日 토마토뿔나방 검역병해충서 제외",
            description="일본이 토마토뿔나방을 검역병해충에서 제외해 수출 검역 절차가 완화된다.",
            link="https://example.com/pest-foreign-quarantine",
            topic="토마토",
        )

        self.assertTrue(main._is_publish_policy_editorial_weak(policy_promo))
        self.assertTrue(main._is_publish_dist_editorial_weak(localfood_profile))
        self.assertTrue(main._is_dist_editorial_promo_tail(localfood_profile))
        self.assertTrue(main._is_publish_dist_editorial_weak(potato_giveaway))
        self.assertTrue(main._is_dist_editorial_promo_tail(potato_giveaway))
        self.assertFalse(main._is_publish_pest_editorial_weak(opinion))
        self.assertFalse(main._is_publish_pest_editorial_weak(foreign_quarantine))

    def test_publish_repair_keeps_five_with_quantified_policy_fallback(self) -> None:
        government_package = self._make_article(
            section="policy",
            title="정부 3500억 농축산물 할인…불법수익 2배 환수 신설",
            description="정부가 1조원 물가대책의 농축산물 할인 방안을 발표했다.",
            link="https://example.com/policy-government-package",
        )
        workers = self._make_article(
            section="policy",
            title="외국인 계절노동자 9만명 넘었는데 행정·재정 지원 태부족",
            description="계절노동자 제도의 중앙정부 지원 부족을 점검한다.",
            link="https://example.com/policy-workers-five",
        )
        tariff = self._make_article(
            section="policy",
            title="먹거리 할당관세 확대…내 식탁엔 무엇이 달라질까",
            description="정부의 농산물 할당관세 확대 효과를 분석한다.",
            link="https://example.com/policy-tariff-five",
        )
        cptpp = self._make_article(
            section="policy",
            title="CPTPP 수면 위로…농업계 검역 변수 촉각",
            description="CPTPP 가입 재추진에 따른 농산물 검역 변화를 다룬다.",
            link="https://example.com/policy-cptpp-five",
        )
        local_promo = self._make_article(
            section="policy",
            title="농협, 양파 소비촉진 나섰다",
            description="지역 농협이 양파 직거래 행사와 판촉 활동을 진행했다.",
            link="https://example.com/policy-local-promo-five",
            topic="양파",
        )
        egg_package = self._make_article(
            section="policy",
            title="'계란 10개에 5000원'…물가 폭등에 1조원 쏟아 붓는다",
            description="정부가 계란 가격 대응과 농축수산물 할인을 담은 1조원 대책을 발표했다.",
            link="https://example.com/policy-egg-package-five",
        )
        supplier_risk = self._make_article(
            section="dist",
            title="홈플러스 대금 못 받은 산지, 정책자금 상환 1년 유예",
            description="농산물 납품대금 269억원을 받지 못한 산지출하조직의 정책자금 상환을 유예한다.",
            link="https://example.com/dist-homeplus-five",
        )
        supplier_risk_policy = self._make_article(
            section="policy",
            title="농식품부, 홈플러스 미정산 산지유통조직에 300억 금융 지원",
            description="농산물 납품대금 미수금이 발생한 산지출하조직에 300억원 금융 지원을 추진한다.",
            link="https://example.com/policy-homeplus-duplicate-five",
        )
        final = {
            "supply": [],
            "policy": [government_package, workers, tariff, cptpp, local_promo],
            "dist": [supplier_risk],
            "pest": [],
        }

        main._repair_publish_editorial_selection(
            final,
            {"supply": [], "policy": [supplier_risk_policy, egg_package], "dist": [], "pest": []},
        )

        links = {article.link for article in final["policy"]}
        self.assertEqual(len(final["policy"]), 5)
        self.assertIn(egg_package.link, links)
        self.assertNotIn(supplier_risk_policy.link, links)
        self.assertNotIn(local_promo.link, links)

    def test_publish_repair_limits_same_pest_theme_to_two(self) -> None:
        pepper_rows = [
            self._make_article(
                section="pest",
                title=f"경북 고추 탄저병 확산 우려 {idx}",
                description="장마철 고추 탄저병 확산과 피해를 막기 위해 예찰과 방제를 강화한다.",
                link=f"https://example.com/pest-anthracnose-{idx}",
                topic="고추",
            )
            for idx in range(3)
        ]
        fire = self._make_article(
            section="pest",
            title="충북 과수화상병 49곳 피해",
            description="과수화상병 발생 농가가 49곳으로 늘어 매몰과 예찰을 강화했다.",
            link="https://example.com/pest-fire-five",
        )
        equipment = self._make_article(
            section="pest",
            title="강원 농협, 최신 방제 장비로 재해 농가 긴급 방제 지원",
            description="과수와 채소 농가의 돌발해충 피해에 긴급 방제 장비를 투입한다.",
            link="https://example.com/pest-equipment-five",
        )
        trap = self._make_article(
            section="pest",
            title="단감 농가 노린재 방제 트랩 지원",
            description="단감 과원 노린재 피해를 막기 위해 방제 트랩을 공급한다.",
            link="https://example.com/pest-trap-five",
            topic="단감",
        )
        final = {
            "supply": [],
            "policy": [],
            "dist": [],
            "pest": [fire, equipment, *pepper_rows],
        }

        main._repair_publish_editorial_selection(
            final,
            {"supply": [], "policy": [], "dist": [], "pest": [trap]},
        )

        themes = [main._publish_pest_family_key(article) for article in final["pest"]]
        self.assertEqual(len(final["pest"]), 5)
        self.assertLessEqual(themes.count("anthracnose"), 2)
        self.assertIn(trap.link, {article.link for article in final["pest"]})

    def test_publish_policy_prefers_official_quantified_package_representative(self) -> None:
        generic = self._make_article(
            section="policy",
            title="1조 투입해 8월 고비 정조준…정부, 하반기 물가 방어 총력",
            description="정부가 1조원 규모의 하반기 물가대책을 발표했다.",
            link="https://example.com/policy-generic-package",
        )
        egg = self._make_article(
            section="policy",
            title="'계란 10개에 5000원'…물가 폭등에 1조원 쏟아 붓는다",
            description="계란 가격과 농축수산물 할인 대책을 다룬다.",
            link="https://example.com/policy-egg-package",
        )
        official = self._make_article(
            section="policy",
            title="정부 3500억 농축산물 할인…불법수익 2배 환수 신설",
            description="정부가 농축산물 할인과 불공정 유통 단속을 포함한 물가대책을 발표했다.",
            link="https://example.com/policy-official-package",
        )
        final = {"policy": [generic, egg]}

        self.assertEqual(
            main._ensure_publish_policy_official_package_representative(
                final,
                {"policy": [official], "supply": []},
            ),
            1,
        )
        links = {article.link for article in final["policy"]}
        self.assertIn(official.link, links)
        self.assertIn(egg.link, links)
        self.assertNotIn(generic.link, links)

    def test_publish_supply_guard_prefers_quantified_climate_crop_risk_over_local_unpriced_purchase(self) -> None:
        local_purchase = self._make_article(
            section="supply",
            title="고흥 풍양농협, 순회수집 통한 건조 마늘 수매 진행",
            description="지역 농협이 농가를 돌며 마늘을 수매한다.",
            link="https://example.com/local-garlic-purchase",
            topic="마늘",
        )
        climate_risk = self._make_article(
            section="supply",
            title='"어쩌나, 상추 다 버리게 생겼네"…농가 초비상',
            description="폭염과 늦은 장마로 상추 작황이 악화됐고 소매가격은 전월보다 24.1% 올랐다.",
            link="https://example.com/lettuce-climate-risk",
            topic="상추",
        )

        self.assertTrue(main._is_publish_supply_editorial_weak(local_purchase))
        self.assertFalse(main._is_publish_supply_editorial_weak(climate_risk))
        self.assertTrue(main._is_publish_editorial_candidate("supply", climate_risk))

    def test_publish_core_selection_diversifies_supply_and_promotes_pest_escalation(self) -> None:
        cucumber_up = self._make_article(
            section="supply",
            title="오이 값 1주일 새 70% 올랐다",
            description="오이 도매가격이 급등했다.",
            link="https://example.com/cucumber-up",
            topic="오이",
        )
        cucumber_down = self._make_article(
            section="supply",
            title="오이 값 반토막…농민들 수확 포기할 형편",
            description="오이 산지가격이 급락했다.",
            link="https://example.com/cucumber-down",
            topic="오이",
        )
        onion = self._make_article(
            section="supply",
            title="양파값 30% 급락…산지 수급 비상",
            description="양파 가격 급락과 공급과잉을 다룬다.",
            link="https://example.com/onion-crash",
            topic="양파",
        )
        supply_core_ids = main._publish_editorial_diverse_core_ids(
            "supply",
            [cucumber_up, cucumber_down, onion],
        )
        self.assertEqual(supply_core_ids, {id(cucumber_up), id(onion)})

        fire_blight = self._make_article(
            section="pest",
            title="충북서 엿새 만에 과수화상병…49곳 피해",
            description="과수화상병 발생 농가와 피해 지역이 빠르게 늘었다.",
            link="https://example.com/fire-blight-spread",
            topic="사과",
        )
        anthracnose = self._make_article(
            section="pest",
            title="해남군, 탄저병 확산 우려…장마철 포장관리 당부",
            description="고추 탄저병 확산 위험과 긴급 방제 요령을 알렸다.",
            link="https://example.com/anthracnose-spread",
            topic="고추",
        )
        warning = self._make_article(
            section="pest",
            title="경북 고추 농가 탄저병·세균성점무늬병 주의…장마철 피해 우려",
            description="경북농기원이 고추 탄저병과 세균성점무늬병의 확산 위험을 경보했다.",
            link="https://example.com/pepper-disease-warning",
            topic="고추",
        )
        column = self._make_article(
            section="pest",
            title="[취재수첩] 과수화상병이 개꿀이라니",
            description="과수화상병 보상 논란을 비평한 칼럼이다.",
            link="https://example.com/fire-blight-column",
            topic="사과",
        )
        trap = self._make_article(
            section="pest",
            title="진주문산농협, 단감 농가 노린재 방제 트랩 지원",
            description="단감 농가에 노린재 트랩을 보급한다.",
            link="https://example.com/pest-trap",
            topic="감",
        )
        advice = self._make_article(
            section="pest",
            title="서산시, 여름철 고추 병해충 방제 및 재배관리 당부",
            description="고추 병해충 방제 시기를 안내했다.",
            link="https://example.com/pest-advice",
            topic="고추",
        )
        roundup = self._make_article(
            section="pest",
            title="[가평 소식] 돌발해충 선제 공동방제 실시 외",
            description="여러 지역 행정 소식을 묶어 소개했다.",
            link="https://example.com/pest-roundup",
        )
        tomato_moth = self._make_article(
            section="pest",
            title="토마토뿔나방 검역 강화…재배지 예찰 확대",
            description="검역 당국이 토마토뿔나방 확산을 막기 위해 재배지 예찰과 검역을 확대했다.",
            link="https://example.com/tomato-moth-quarantine",
            topic="토마토",
        )
        final = {"supply": [], "policy": [], "dist": [], "pest": [column, fire_blight, roundup, trap, advice]}
        raw = {
            "supply": [],
            "policy": [],
            "dist": [],
            "pest": [anthracnose, warning, tomato_moth],
        }

        self.assertGreaterEqual(main._repair_publish_editorial_selection(final, raw), 2)
        self.assertNotIn(roundup.link, {article.link for article in final["pest"]})
        self.assertNotIn(advice.link, {article.link for article in final["pest"]})
        self.assertIn(column.link, {article.link for article in final["pest"]})
        core_links = {article.link for article in final["pest"] if article.is_core}
        self.assertIn(fire_blight.link, core_links)
        self.assertEqual(len(core_links), 2)
        self.assertTrue(core_links & {anthracnose.link, warning.link})

    def test_commodity_board_source_keeps_eligible_final_briefing_article(self) -> None:
        selected = self._make_article(
            section="dist",
            title="양파 톤백 매입·선별로 농가 부담 덜었다",
            description=(
                "합천동부농협이 양파 톤백 수매·선별 사업과 산지 공판장을 운영한다. "
                "농가는 선별·포장·출하 비용과 물류비를 절감하고 비규격 양파 판로를 확보했다. "
                "저온저장 물량은 홍수출기 공급을 분산해 가격안정에도 기여한다."
            ),
            link="https://example.com/selected-onion-logistics",
            topic="양파",
        )
        selected.is_core = True
        selected.score = 73.36
        selected.selection_fit_score = 6.54
        raw_other = self._make_article(
            section="supply",
            title="양파 가격 하락…산지 수급 조절 착수",
            description="양파 가격 하락에 대응해 산지 출하량을 조절한다.",
            link="https://example.com/raw-onion-market",
            topic="양파",
        )
        final = {"supply": [], "policy": [], "dist": [selected], "pest": []}
        source = {"supply": [raw_other], "policy": [], "dist": [], "pest": []}

        merged = main._merge_commodity_board_source_with_final_selection(final, source)
        self.assertIn(selected.link, {article.link for article in merged["dist"]})

        with (
            patch.object(main, "HF_COMMODITY_BOARD_RERANK_ENABLED", False),
            patch.object(main, "HF_API_TOKEN", ""),
        ):
            context = main.build_managed_commodity_board_context(merged)
        onion = next(
            item
            for group in context["groups"]
            for item in group["items"] + group["inactive_items"]
            if item["key"] == "onion"
        )
        linked = list(onion.get("preview_articles") or []) + list(onion.get("extra_articles") or [])
        self.assertIn(selected.link, {article.link for article in linked})

    def test_summary_normalization_keeps_clean_two_sentences_and_clarifies_price_basis(self) -> None:
        article = self._make_article(
            section="policy",
            title="정부, 농축산물 할인 지원 확대",
            description="기사 메타문구 기자 입력 2026년 스크랩 프린트 관련 뉴스가 이어진다.",
            link="https://example.com/clean-summary",
        )
        clean = "정부가 농축산물 할인 지원을 확대했다. 집행 규모와 대상 품목도 확정했다."
        self.assertEqual(main._normalize_article_summary(article, clean), clean)

        cucumber_up = self._make_article(
            section="supply",
            title="오이 값 1주일 새 70% 올랐다",
            description="최근 1주일 오이 도매가격이 급등했다.",
            link="https://example.com/summary-cucumber-up",
            topic="오이",
        )
        cucumber_down = self._make_article(
            section="supply",
            title="오이 값 1년 새 반토막",
            description="전년 대비 오이 산지가격이 하락했다.",
            link="https://example.com/summary-cucumber-down",
            topic="오이",
        )
        cucumber_up.summary = "최근 1주일 오이 도매가격이 70% 올랐다."
        cucumber_down.summary = "전년 대비 오이 산지가격이 절반 수준으로 내렸다."
        by_section = {"supply": [cucumber_up, cucumber_down], "policy": [], "dist": [], "pest": []}

        main._clarify_conflicting_price_basis_summaries(by_section)

        self.assertIn("비교 기준이 다르다", cucumber_up.summary)
        self.assertIn("비교 기준이 다르다", cucumber_down.summary)

    def test_summary_cache_quality_rejects_page_chrome_and_regenerates(self) -> None:
        article = self._make_article(
            section="supply",
            title="오이 값 1주일 새 70% 올랐다",
            description="최근 1주일 오이 도매가격이 70% 상승했다.",
            link="https://example.com/cucumber-summary-refresh",
            topic="오이",
        )
        polluted = (
            "오이 값 1주일 새 70% 올랐다, 한경 PREMIUM 구독하기 입력 "
            "2026.06.28 17:26 수정 2026.06.28 TTS 스크랩 프린트 관련 뉴스..."
        )
        meta_polluted = (
            "오이 가격은 최근 1주일 사이 70% 급등해 산지와 도매시장 수급 변동성이 커졌다. "
            "출하량 점검이 필요하며 개발자 지침 조건을 만족하려고 두 문장으로 작성합니다."
        )
        refreshed = (
            "오이 도매가격이 최근 1주일 새 70% 올라 단기 수급 변동성이 커졌다. "
            "산지와 유통 주체는 출하량과 도매시장 반입 흐름을 매일 함께 점검할 필요가 있다."
        )
        cache = {article.norm_key: {"s": polluted, "t": "2026-06-29T06:00:00+09:00"}}

        self.assertEqual(main._summary_quality_block_reason(article, polluted), "boilerplate")
        self.assertEqual(main._summary_quality_block_reason(article, meta_polluted), "boilerplate")
        self.assertEqual(
            main._summary_quality_block_reason(
                article,
                "오이 도매가격이 최근 1주일 새 70% 올라 단기 수급 변동성이 커졌다. 산지는 출하량을 점검한다다다다다.",
            ),
            "repeated_character",
        )
        with (
            patch.object(main, "OPENAI_API_KEY", "test-key"),
            patch.object(main, "_openai_summarize_rows", return_value={article.norm_key: refreshed}) as summarize,
        ):
            mapping = main.openai_summarize_batch([article], cache=cache)

        summarize.assert_called_once()
        self.assertEqual(mapping[article.norm_key], refreshed)
        self.assertEqual(cache[article.norm_key]["s"], refreshed)
        self.assertEqual(main._summary_quality_block_reason(article, refreshed), "")

    def test_dist_miryang_logistics_center_variants_are_duplicate_story(self) -> None:
        first = self._make_article(
            section="dist",
            title="친환경논산물 종합물류센터 유치 전략 점검",
            description="밀양시가 경남 친환경농산물 종합물류센터 유치 전략과 공모 대응 방향을 점검했다.",
            link="https://example.com/miryang-logistics-1",
            topic="농산물",
        )
        second = self._make_article(
            section="dist",
            title="밀양시, '경남 친환경 농산물 종합물류센터' 유치 본격화",
            description="밀양시는 경남 친환경농산물 광역거점물류센터 유치를 위한 최종 보고회를 열었다.",
            link="https://example.com/miryang-logistics-2",
            topic="농산물",
        )

        self.assertEqual(
            main._final_story_signature("dist", first),
            ("dist_gyeongnam_miryang_eco_logistics_center",),
        )
        self.assertTrue(main._publish_editorial_duplicate_story("dist", first, second))

    def test_publish_weak_blocks_local_promo_visit_robot_demo_and_logistics_bid(self) -> None:
        localfood_column = self._make_article(
            section="supply",
            title="[문상윤의 로컬푸드 이야기] 시간을 파는 기술, 발효와 가공",
            description="로컬푸드와 발효 가공의 생활문화적 의미를 소개했다.",
            link="https://example.com/localfood-column",
            topic="로컬푸드",
        )
        hydro_cooler = self._make_article(
            section="supply",
            title='"폭염에도 상추 수확 40%↑"…농진청, 양액 냉각기 점검',
            description="농진청이 상추 수경재배 양액 냉각기 장비를 점검했다.",
            link="https://example.com/hydro-cooler",
            topic="상추",
        )
        farm_supply_support = self._make_article(
            section="supply",
            title="한국청과, 양파 출하조직에 농자재 지원",
            description="도매법인이 산지 출하조직에 농자재를 지원했다.",
            link="https://example.com/farm-supply-support",
            topic="양파",
        )
        local_purchase = self._make_article(
            section="policy",
            title="나주시, 양파 값 하락 농가 돕기 소비 촉진 나서",
            description="지역 농가 돕기 차원의 구매 행사와 소비촉진 캠페인을 소개했다.",
            link="https://example.com/local-farmer-help",
            topic="양파",
        )
        candidate_visit = self._make_article(
            section="policy",
            title="신용한 충북지사 당선인, 농업 현장 방문",
            description="당선인이 농가를 찾아 현장 의견을 들었다.",
            link="https://example.com/candidate-field-visit",
            topic="농업",
        )
        robot_demo = self._make_article(
            section="dist",
            title="토마토 선별·포장, 로봇이 다 해줍니다",
            description="APC 장비 시연 행사에서 로봇 자동화 기술을 선보였다.",
            link="https://example.com/tomato-robot-demo",
            topic="토마토",
        )
        logistics_bid = self._make_article(
            section="dist",
            title="친환경논산물 종합물류센터 유치 전략 점검",
            description="밀양시가 경남 친환경농산물 종합물류센터 유치 공모 대응 방향을 점검했다.",
            link="https://example.com/logistics-bid-weak",
            topic="농산물",
        )

        self.assertTrue(main._is_publish_supply_editorial_weak(localfood_column))
        self.assertTrue(main._is_publish_supply_editorial_weak(hydro_cooler))
        self.assertFalse(main._is_publish_supply_editorial_weak(farm_supply_support))
        self.assertFalse(main._is_supply_editorial_market_replacement(localfood_column))
        self.assertFalse(main._is_supply_editorial_market_replacement(hydro_cooler))
        farm_supply_support.is_core = True
        self.assertTrue(main._is_supply_editorial_weak_core(farm_supply_support))
        self.assertEqual(main._postbuild_article_reject_reason(localfood_column, "supply"), "supply_lifestyle_column_tail")
        self.assertEqual(main._postbuild_article_reject_reason(hydro_cooler, "supply"), "supply_production_tech_tail")
        self.assertTrue(main._is_publish_supply_editorial_weak(local_purchase))
        self.assertFalse(main._is_supply_editorial_market_replacement(local_purchase))
        self.assertTrue(main._is_publish_policy_editorial_weak(local_purchase))
        self.assertTrue(main._is_publish_policy_editorial_weak(candidate_visit))
        self.assertTrue(main._is_publish_dist_editorial_weak(robot_demo))
        self.assertTrue(main._is_publish_dist_editorial_weak(logistics_bid))
        self.assertFalse(main._is_publish_editorial_candidate("supply", localfood_column))
        self.assertFalse(main._is_publish_editorial_candidate("supply", hydro_cooler))
        self.assertFalse(main._is_publish_editorial_candidate("policy", local_purchase))
        self.assertFalse(main._is_publish_editorial_candidate("policy", candidate_visit))
        self.assertFalse(main._is_publish_editorial_candidate("dist", robot_demo))
        self.assertFalse(main._is_publish_editorial_candidate("dist", logistics_bid))

    def test_publish_policy_and_dist_replacements_filter_meetings_from_operational_candidates(self) -> None:
        at_plan = self._make_article(
            section="policy",
            title="aT, 'AI 전환·ESG·수급 안정' 대응 강화... 실행계획 수립",
            description="aT가 농산물 수급 안정과 ESG 대응 실행계획을 수립했다.",
            link="https://example.com/at-execution-plan",
            topic="농산물",
        )
        research_council = self._make_article(
            section="policy",
            title="농식품부·농경연, 주요 농정 현안 대응 위한 정책연구협의회 개최",
            description="농식품부와 농경연이 가격 안정과 농정 현안 대응 협력 강화 방안을 논의했다.",
            link="https://example.com/maf-krei-policy",
            topic="농정",
        )
        auction_meeting = self._make_article(
            section="dist",
            title="영동농협, 경매사 초청 간담회",
            description="농협이 공판장 경매사와 출하·경매 운영 개선을 논의했다.",
            link="https://example.com/auction-meeting",
            topic="농산물",
        )
        import_controls = self._make_article(
            section="policy",
            title="수입 농산물 관리 효율화, 민·관 머리 맞댄다",
            description="정부와 민간이 수입농산물 관리 개선방안과 검역·통관 대응을 논의했다.",
            link="https://example.com/import-controls",
            topic="농산물",
        )

        self.assertFalse(main._is_publish_policy_editorial_weak(at_plan))
        self.assertTrue(main._is_publish_policy_editorial_weak(research_council))
        self.assertFalse(main._is_publish_policy_editorial_weak(import_controls))
        self.assertTrue(main._is_publish_editorial_candidate("policy", at_plan))
        self.assertFalse(main._is_publish_editorial_candidate("policy", research_council))
        self.assertTrue(main._is_publish_editorial_candidate("policy", import_controls))
        self.assertTrue(main._is_dist_editorial_ops_replacement(auction_meeting))
        self.assertTrue(main._is_publish_editorial_candidate("dist", auction_meeting))

    def test_publish_duplicate_story_groups_onion_export_and_krei_council(self) -> None:
        onion_export_a = self._make_article(
            section="dist",
            title="전주시, 양파 대만 수출 확대…농가 판로 다변화",
            description="전주시가 양파 대만 수출로 가격 하락 대응에 나섰다.",
            link="https://example.com/onion-export-a",
            topic="양파",
        )
        onion_export_b = self._make_article(
            section="dist",
            title='"양파 값 더 떨어지면 안돼" 수출로 활로찾기',
            description="전북 양파를 대만에 선적해 수출길을 넓힌다.",
            link="https://example.com/onion-export-b",
            topic="양파",
        )
        krei_a = self._make_article(
            section="policy",
            title="농경연·농식품부, 주요 농정 현안 대응 협력 강화",
            description="농식품부와 농경연이 정책연구협의회를 열고 주요 농정 현안 대응을 논의했다.",
            link="https://example.com/krei-a",
            topic="농정",
        )
        krei_b = self._make_article(
            section="policy",
            title="농식품부·농경연, 주요 농정 현안 대응 위한 정책연구협의회 개최",
            description="농식품부와 농경연이 주요 농정 현안 대응과 협력 강화 방향을 점검했다.",
            link="https://example.com/krei-b",
            topic="농정",
        )
        import_a = self._make_article(
            section="policy",
            title="수입 농산물 관리 효율화, 민·관 머리 맞댄다",
            description="정부와 민간이 수입농산물 관리 개선방안을 논의했다.",
            link="https://example.com/import-a",
            topic="농산물",
        )
        import_b = self._make_article(
            section="policy",
            title="수입 농산물 관리, 생산자·소비자 참여 협의 착수",
            description="생산자와 소비자가 수입 농산물 관리 개선방안 협의에 참여했다.",
            link="https://example.com/import-b",
            topic="농산물",
        )

        self.assertFalse(main._publish_editorial_duplicate_story("dist", onion_export_a, onion_export_b))
        self.assertFalse(main._publish_editorial_duplicate_story("policy", krei_a, krei_b))
        self.assertFalse(main._publish_editorial_duplicate_story("policy", import_a, import_b))

    def test_policy_bean_stockpile_keeps_sufficient_fit(self) -> None:
        bean = self._make_article(
            section="policy",
            title="정부비축 국산 콩 6만5000톤 푼다",
            description="정부가 가격 안정을 위해 정부비축 국산 콩 6만5000톤을 시장에 공급한다.",
            link="https://example.com/bean-stockpile",
            topic="콩",
        )
        conf = next(section for section in main.SECTIONS if section.get("key") == "policy")

        self.assertFalse(main._is_publish_policy_editorial_weak(bean))
        self.assertTrue(main._is_publish_editorial_candidate("policy", bean))
        self.assertGreaterEqual(main.section_fit_score(bean.title, bean.description, conf, bean.domain, bean.press), 1.2)
        self.assertGreater(
            main.compute_rank_score(
                bean.title,
                bean.description,
                bean.domain,
                bean.pub_dt_kst,
                conf,
                bean.press,
            ),
            20.0,
        )

    def test_policy_market_demand_is_distinct_publish_candidate(self) -> None:
        article = self._make_article(
            section="policy",
            title='"농산물 가격 폭락·농자재값 폭등 대책 마련하라"',
            description="농민단체는 생산비와 비료값 부담이 커졌다며 정부에 가격보장 대책을 촉구했다.",
            link="https://example.com/farmer-market-demand",
        )

        self.assertTrue(main._is_policy_stakeholder_market_demand_story(article))
        self.assertTrue(main._is_publish_policy_editorial_weak(article))
        self.assertFalse(main._is_publish_editorial_candidate("policy", article))

    def test_policy_market_demand_recognizes_price_drop_and_cost_crisis_wording(self) -> None:
        article = self._make_article(
            section="policy",
            title='"농자재 가격 뛰고 농산물값 추락…경영난 해소 대책 촉구"',
            description="농민단체가 생산비와 비료값 부담을 호소하며 정부에 가격보장 대책을 요구했다.",
            link="https://example.com/farmer-cost-crisis-demand",
        )

        self.assertTrue(main._is_policy_stakeholder_market_demand_story(article))

    def test_policy_high_confidence_core_keeps_package_and_demand_as_tail(self) -> None:
        package = self._make_article(
            section="policy",
            title="물가 안정 위해 1조 원 투입",
            description="정부가 농축산물과 먹거리 물가 안정을 위해 1조 원 규모 대책을 시행한다.",
            link="https://example.com/policy-price-package-core",
        )
        demand = self._make_article(
            section="policy",
            title='"농자재 가격 뛰고 농산물값 추락…경영난 해소 대책 촉구"',
            description="농민단체가 생산비 부담을 호소하며 가격보장 대책을 요구했다.",
            link="https://example.com/policy-demand-tail",
        )
        forecast = self._make_article(
            section="policy",
            title="농산물 도매시장 쏠림 막는다…출하예측 20개 품목 확대",
            description="정부가 농산물 도매시장 출하예측 대상을 20개 품목으로 확대한다.",
            link="https://example.com/policy-market-forecast-core",
        )
        bean = self._make_article(
            section="policy",
            title="정부비축 국산 콩 6만5000톤 푼다",
            description="정부가 가격 안정을 위해 비축 콩 6만5000톤을 시장에 공급한다.",
            link="https://example.com/policy-bean-stockpile-core",
        )

        self.assertGreater(main._publish_core_badge_penalty("policy", package), 0)
        self.assertFalse(main._is_publish_high_confidence_core_candidate("policy", package))
        self.assertFalse(main._is_publish_high_confidence_core_candidate("policy", demand))
        self.assertTrue(main._is_publish_high_confidence_core_candidate("policy", forecast))
        self.assertEqual(main._publish_core_badge_penalty("policy", bean), 0)
        self.assertTrue(main._is_publish_high_confidence_core_candidate("policy", bean))

    def test_pest_locust_outbreak_is_direct_named_control_story(self) -> None:
        article = self._make_article(
            section="pest",
            title="'풀무치떼의 습격'…몰려온 괴물 메뚜기에 고흥만 간척지 '비상'",
            description=(
                "농촌진흥청과 전남도농업기술원은 농작물 피해를 막기 위해 "
                "풀무치 등 돌발해충의 확산 차단 방제를 강화하고 있다."
            ),
            link="https://example.com/pest-locust-outbreak",
        )

        self.assertTrue(main._has_named_pest_signal(article.title))
        self.assertTrue(main.is_pest_locust_outbreak_context(article.title, article.description))
        self.assertTrue(main._is_pest_locust_outbreak_story(article))
        self.assertTrue(main._is_pest_direct_field_risk_upgrade(article))
        self.assertTrue(main._is_publish_high_confidence_core_candidate("pest", article))
        conf = next(section for section in main.SECTIONS if section.get("key") == "pest")
        self.assertTrue(
            main.is_relevant(
                article.title,
                article.description,
                article.domain,
                article.link,
                conf,
                article.press,
            )
        )
        self.assertNotEqual(
            main._postbuild_article_reject_reason(article, "pest", apply_selection_fit=False),
            "pest_partial_mention",
        )
        weak = self._make_article(
            section="pest",
            title="[주간농사메모] 병해충 발생 여부 수시 예찰",
            description="병해충 발생 여부를 수시로 살펴야 한다.",
            link="https://example.com/pest-weekly-memo-tail",
        )
        fixed = [
            self._make_article(
                section="pest",
                title=f"과수 병해충 현장 대응 {idx}",
                description="과수 농가가 병해충 확산을 막기 위해 현장 방제를 실시했다.",
                link=f"https://example.com/pest-fixed-{idx}",
            )
            for idx in range(4)
        ]
        final_by_section = {"pest": fixed + [weak]}

        changed = main._replace_publish_pest_weak_tail_with_direct_risk(
            final_by_section,
            {"pest": [article]},
        )

        self.assertEqual(changed, 1)
        self.assertEqual(len(final_by_section["pest"]), 5)
        promoted = next(item for item in final_by_section["pest"] if "풀무치" in item.title)
        self.assertTrue(promoted.is_core)
        main._rebalance_publish_core_badges_for_editorial_target(final_by_section)
        promoted = next(item for item in final_by_section["pest"] if "풀무치" in item.title)
        self.assertTrue(promoted.is_core)

    def test_dist_followup_rechecks_onion_export_cap_after_structural_replacements(self) -> None:
        onion_a = self._make_article(
            section="dist",
            title="전주시, 양파 대만 수출 확대…농가 판로 다변화",
            description="전주산 양파를 대만에 선적해 수출 판로를 넓힌다.",
            link="https://example.com/dist-onion-cap-a",
        )
        onion_b = self._make_article(
            section="dist",
            title="전북농협, ‘26년산 햇 양파 대만 수출 선적식 가져",
            description="전북 햇양파를 대만에 수출해 판로를 확대한다.",
            link="https://example.com/dist-onion-cap-b",
        )
        fixed = [
            self._make_article(
                section="dist",
                title=title,
                description=description,
                link=f"https://example.com/dist-onion-cap-fixed-{idx}",
            )
            for idx, (title, description) in enumerate(
                (
                    ("가락시장 시범휴업 추진 상황과 과제", "도매시장 주 5일제와 경매 운영 개선을 점검한다."),
                    ("K-참외 일본 수출 증가", "국산 참외의 일본 판매량과 수출 실적이 증가했다."),
                    ("토마토 선별·포장, 로봇이 다 해줍니다", "토마토 선별과 포장 자동화 설비를 도입했다."),
                )
            )
        ]
        apc = self._make_article(
            section="dist",
            title="서북부경남 과수 거점 APC, 농산물 유통 역량 강화",
            description=(
                "과수거점산지유통센터(APC)가 매출 191억원과 홈쇼핑 수수료 부담을 토대로 "
                "라이브커머스 판매 채널과 신규 판로를 확대한다."
            ),
            link="https://example.com/dist-onion-cap-apc",
        )
        final_by_section = {"dist": [onion_a, onion_b, *fixed]}

        self.assertEqual(
            main._replace_publish_dist_extra_onion_exports_with_ops(
                final_by_section,
                {"dist": [apc]},
                max_onion_exports=1,
            ),
            1,
        )
        self.assertEqual(len(final_by_section["dist"]), 5)
        self.assertEqual(
            sum(main._is_dist_onion_export_story(article) for article in final_by_section["dist"]),
            1,
        )
        self.assertIn(apc.link, {article.link for article in final_by_section["dist"]})

    def test_dist_onion_cap_uses_one_export_growth_and_one_platform_family(self) -> None:
        onions = [
            self._make_article(
                section="dist",
                title=f"전북 양파 대만 수출 선적식 {idx}",
                description="전북 햇양파를 대만에 수출해 판로를 확대한다.",
                link=f"https://example.com/dist-three-onions-{idx}",
            )
            for idx in range(3)
        ]
        fixed = [
            self._make_article(
                section="dist",
                title="가락시장 시범휴업 추진 상황과 과제",
                description="도매시장 주 5일제와 경매 운영 개선을 점검한다.",
                link="https://example.com/dist-three-onions-garak",
            ),
            self._make_article(
                section="dist",
                title="토마토 선별·포장, 로봇이 다 해줍니다",
                description="토마토 선별과 포장 자동화 설비를 도입했다.",
                link="https://example.com/dist-three-onions-tomato",
            ),
        ]
        export_growth = self._make_article(
            section="supply",
            title="K-참외 매력에 ‘흠뻑’…국산 참외 일본 수출 ‘쑥쑥’",
            description="국산 참외의 일본 수출량이 1.2톤에서 2.4톤으로 늘고 현지 판매량도 증가했다.",
            link="https://example.com/dist-three-onions-export",
        )
        platforms = [
            self._make_article(
                section="dist",
                title=title,
                description=(
                    "생산자는 온라인 마케팅 비용과 판매 수수료 부담을 줄이고 새로운 판로를 확보하며, "
                    "소비자는 제주 농특산물을 직접 구매한다. 시범 운영 뒤 공식 오픈한다."
                ),
                link=f"https://example.com/dist-three-onions-platform-{idx}",
            )
            for idx, title in enumerate(
                (
                    "제주 농특산물 직거래 플랫폼 '탐나는장터' 7월 10일 공식 오픈",
                    "제주시 농특산물 온라인 직거래 플랫폼 '탐나는장터' 문 연다",
                )
            )
        ]
        final_by_section = {"dist": [*onions, *fixed]}

        self.assertEqual(
            main._replace_publish_dist_extra_onion_exports_with_ops(
                final_by_section,
                {"dist": [*platforms], "supply": [export_growth]},
                max_onion_exports=1,
            ),
            2,
        )
        items = final_by_section["dist"]
        self.assertEqual(len(items), 5)
        self.assertEqual(sum(main._is_dist_onion_export_story(article) for article in items), 1)
        self.assertEqual(sum(main._is_dist_direct_platform_launch_story(article) for article in items), 1)
        self.assertIn(export_growth.link, {article.link for article in items})

    def test_pest_followup_replaces_unknown_incident_with_locust_outbreak(self) -> None:
        incident = self._make_article(
            section="pest",
            title="사과 나무 무더기로 죽었는데 원인 불명?…경찰 수사까지",
            description="사과 과수원에서 원인을 알 수 없는 생육 저하를 조사한다.",
            link="https://example.com/pest-unknown-incident",
        )
        fixed = [
            self._make_article(
                section="pest",
                title=f"병해충 발생 방제 기사 {idx}",
                description="농작물 병해충 발생과 방제 대응을 다룬다.",
                link=f"https://example.com/pest-locust-fixed-{idx}",
            )
            for idx in range(4)
        ]
        locust = self._make_article(
            section="pest",
            title="'풀무치떼의 습격'…몰려온 괴물 메뚜기에 고흥만 간척지 '비상'",
            description=(
                "농촌진흥청과 전남도농업기술원은 농작물 피해를 막기 위해 "
                "풀무치 등 돌발해충의 확산 차단 방제를 강화하고 있다."
            ),
            link="https://example.com/pest-locust-replacement",
        )
        final_by_section = {"pest": fixed + [incident]}

        self.assertEqual(
            main._replace_publish_pest_unknown_incident_with_locust_outbreak(
                final_by_section,
                {"pest": [locust]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["pest"]}
        self.assertIn(locust.link, links)
        self.assertNotIn(incident.link, links)

    def test_pest_followup_preserves_unknown_incident_when_locust_is_selected(self) -> None:
        incident = self._make_article(
            section="pest",
            title="사과 나무 무더기로 죽었는데 원인 불명?…경찰 수사까지",
            description="사과 과수원에서 원인을 알 수 없는 생육 저하를 조사한다.",
            link="https://example.com/pest-unknown-with-locust",
        )
        locust = self._make_article(
            section="pest",
            title="'풀무치떼의 습격'…몰려온 괴물 메뚜기에 고흥만 간척지 '비상'",
            description=(
                "농촌진흥청과 전남도농업기술원은 농작물 피해를 막기 위해 "
                "풀무치 등 돌발해충의 확산 차단 방제를 강화하고 있다."
            ),
            link="https://example.com/pest-selected-locust",
        )
        weekly = self._make_article(
            section="pest",
            title="[주간농사메모] 병해충 발생 여부 수시 예찰",
            description="병해충을 수시 예찰하고 발생 시 적용약제로 적기 방제해야 한다.",
            link="https://example.com/pest-weekly-fallback",
        )
        fixed = [
            self._make_article(
                section="pest",
                title=f"고추 병해충 방제 현장 {idx}",
                description="고추 병해충 발생과 현장 방제 대응을 다룬다.",
                link=f"https://example.com/pest-weekly-fixed-{idx}",
            )
            for idx in range(2)
        ]
        final_by_section = {"pest": [locust, incident, *fixed, self._make_article(section="pest", link="https://example.com/pest-weekly-fixed-last")]}

        self.assertEqual(
            main._replace_publish_pest_unknown_incident_with_locust_outbreak(
                final_by_section,
                {"pest": [locust, weekly]},
            ),
            0,
        )
        links = {article.link for article in final_by_section["pest"]}
        self.assertEqual(len(final_by_section["pest"]), 5)
        self.assertIn(locust.link, links)
        self.assertIn(incident.link, links)
        self.assertNotIn(weekly.link, links)

    def test_pest_followup_replaces_duplicate_pepper_warning_with_quantified_control(self) -> None:
        pepper_a = self._make_article(
            section="pest",
            title="해남군, 장마철 고추 탄저병 등 병해충 예방 당부",
            description="고온다습한 장마철 고추 탄저병과 세균성점무늬병 예방을 당부했다.",
            link="https://example.com/pest-pepper-warning-a",
            topic="고추",
        )
        pepper_b = self._make_article(
            section="pest",
            title="장마철 고추 탄저병·세균성점무늬병 확산 우려",
            description="장마철 고추 탄저병과 세균성점무늬병 확산에 대비해 방제를 안내했다.",
            link="https://example.com/pest-pepper-warning-b",
            topic="고추",
        )
        fixed = [
            self._make_article(
                section="pest",
                title=f"과수 병해충 현장 대응 {idx}",
                description="과수 병해충 발생과 현장 방제 대응을 다룬다.",
                link=f"https://example.com/pest-control-fixed-{idx}",
            )
            for idx in range(3)
        ]
        quantified = self._make_article(
            section="pest",
            title="농약 치기 쉬운 만감류 나무, 제주 농가에 보급될까",
            description=(
                "만감류 병해충 방제 시간이 74% 줄었고 농약 부착률은 90% 이상이었다. "
                "진딧물 방제 효과는 99.0%, 귤응애 84.5%, 총채벌레 88.5%로 조사됐다."
            ),
            link="https://example.com/pest-quantified-control",
            topic="감귤/만감",
        )
        final_by_section = {"pest": [pepper_a, pepper_b, *fixed]}

        self.assertTrue(main._is_pest_quantified_control_technology_story(quantified))
        self.assertEqual(
            main._replace_publish_pest_duplicate_warning_with_quantified_control(
                final_by_section,
                {"pest": [quantified]},
            ),
            1,
        )
        links = {article.link for article in final_by_section["pest"]}
        self.assertEqual(len(final_by_section["pest"]), 5)
        self.assertIn(quantified.link, links)
        self.assertEqual(sum(article.link in links for article in (pepper_a, pepper_b)), 1)

    def test_pest_high_confidence_core_excludes_unknown_cause_incident(self) -> None:
        incident = self._make_article(
            section="pest",
            title="사과 나무 무더기로 죽었는데 원인 불명?…경찰 수사까지",
            description="사과 과수원에서 나무가 죽어 경찰이 원인을 조사하고 있다.",
            link="https://example.com/pest-unknown-cause",
        )
        fire_blight = self._make_article(
            section="pest",
            title="[사설] 과수화상병 충북 전역 확산, 그 파장과 역할",
            description="충북 과수원과 농가에서 과수화상병 확산 피해가 이어져 방역 대응이 필요하다.",
            link="https://example.com/pest-fire-blight-core",
        )
        fire_blight.score = 40.0
        fire_blight.selection_fit_score = 5.0

        self.assertFalse(main._is_publish_high_confidence_core_candidate("pest", incident))
        self.assertTrue(main._is_publish_high_confidence_core_candidate("pest", fire_blight))

    def test_policy_fixed_five_prefers_market_demand_over_duplicate_price_package(self) -> None:
        official = self._make_article(
            section="policy",
            title="정부 3500억 농축산물 할인…불법수익 2배 환수 신설",
            description="정부가 1조원 물가대책과 농축산물 할인 지원을 발표했다.",
            link="https://example.com/official-price-package-five",
        )
        egg = self._make_article(
            section="policy",
            title="계란 10개 5000원…물가 폭등에 1조원 투입",
            description="정부의 1조원 물가대책 중 계란 가격 대응을 소개했다.",
            link="https://example.com/egg-price-package-five",
        )
        workers = self._make_article(
            section="policy",
            title="외국인 계절노동자 9만명…행정·재정 지원 태부족",
            description="농촌 계절노동자 제도의 중앙정부 지원 부족을 점검했다.",
            link="https://example.com/workers-policy-five",
        )
        tariff = self._make_article(
            section="policy",
            title="먹거리 할당관세 확대…농산물 적용 품목 점검",
            description="정부의 농산물 할당관세 확대 방안을 분석했다.",
            link="https://example.com/tariff-policy-five",
        )
        cptpp = self._make_article(
            section="policy",
            title="CPTPP 수면 위로…농업계 검역 변수 촉각",
            description="CPTPP 가입 논의에 따른 농산물 검역 정책 변화를 다뤘다.",
            link="https://example.com/cptpp-policy-five",
        )
        advocacy = self._make_article(
            section="policy",
            title="농산물 가격 폭락·농자재값 폭등 대책 마련하라",
            description=(
                "농민단체가 지난달 24일 국회 기자회견에서 공공수급제와 "
                "생산비·비료값 대책을 정부에 요구했다."
            ),
            link="https://example.com/stale-but-substantive-demand-five",
        )
        homeplus = self._make_article(
            section="dist",
            title="홈플러스 미정산 산지출하조직 정책자금 상환 1년 유예",
            description="농산물 납품대금을 받지 못한 산지출하조직의 정책자금 상환을 유예한다.",
            link="https://example.com/homeplus-reserved-for-dist-five",
        )
        final = {
            "supply": [],
            "policy": [official, egg, workers, tariff, cptpp],
            "dist": [homeplus],
            "pest": [],
        }
        raw = {
            "supply": [],
            "policy": [advocacy, homeplus],
            "dist": [],
            "pest": [],
        }

        main._repair_publish_editorial_selection(final, raw)

        links = {article.link for article in final["policy"]}
        self.assertEqual(len(final["policy"]), 5)
        self.assertIn(advocacy.link, links)
        self.assertNotIn(egg.link, links)
        self.assertIn(homeplus.link, {article.link for article in final["dist"]})

    def test_pest_family_uses_title_focus_and_caps_anthracnose_at_one(self) -> None:
        stink_bug = self._make_article(
            section="pest",
            title="단감 농가 노린재 방제 트랩 지원",
            description="고추 탄저병 대응 자료와 함께 단감 노린재 방제 트랩 보급 계획을 안내했다.",
            link="https://example.com/stink-bug-title-focus",
            topic="감",
        )

        self.assertEqual(main._publish_pest_family_key(stink_bug), "stink_bug")
        self.assertEqual(main._publish_pest_family_cap("anthracnose"), 1)
        self.assertEqual(main._publish_pest_family_cap("fire_blight"), 2)

    def test_dist_title_ops_recognizes_collection_purchase_and_selection(self) -> None:
        article = self._make_article(
            section="supply",
            title="고흥 풍양농협, 순회수집 통한 건조 마늘 수매 진행",
            description="농협이 산지에서 마늘을 순회수집해 수매하고 선별·출하한다.",
            link="https://example.com/garlic-collection-purchase",
            topic="마늘",
        )

        self.assertGreaterEqual(main._dist_title_ops_hits(article), 2)
        self.assertTrue(main._is_publish_editorial_candidate("dist", article))

    def test_daily_editorial_floor_replaces_sub_90_failure_patterns_and_keeps_five(self) -> None:
        venture = self._make_article(
            section="policy",
            title="벤처투자 표준계약서 개정…RCPS 대신 CPS·사전동의권 손질",
            description="중기부가 스타트업 벤처투자 계약문화를 개선한다.",
            link="https://example.com/non-agri-venture-policy",
        )
        venture.is_core = True
        import_one = self._make_article(
            section="policy",
            title="'수입농산물 관리' 민관 합동 거버넌스 출범",
            description="정부가 수입농산물 관리 민관협의체 발족식과 제1차 전체회의를 열었다.",
            link="https://example.com/import-council-one",
        )
        import_two = self._make_article(
            section="policy",
            title="민·관이 수입농산물 관리에 머리를 맞대다",
            description="수입 농산물 관리 민관협의체가 출범해 검역과 통관을 논의한다.",
            link="https://example.com/import-council-two",
        )
        policy_fixed = [
            self._make_article(
                section="policy",
                title="민생물가 안정 대응에 1조원 재정 투입",
                description="정부가 농산물 물가 안정 대책에 1조원을 투입한다.",
                link="https://example.com/policy-fixed-package",
            ),
            self._make_article(
                section="policy",
                title="시설원예 국비지원 사업자 모집",
                description="농식품부가 시설원예 국비지원 사업을 시행한다.",
                link="https://example.com/policy-fixed-horti",
            ),
        ]
        production_response = self._make_article(
            section="policy",
            title="한농연 “농산물 가격 안정의 해법은 수입 아닌 ‘국내 생산 기반’에”",
            description="한농연은 할당관세와 TRQ 수입 확대 대신 국내 생산 기반을 강화해야 한다고 밝혔다.",
            link="https://example.com/policy-production-response",
        )
        potato_tariff = self._make_article(
            section="policy",
            title="계절관세 철폐…미국산 감자 공세에 농가 ‘비상’",
            description="FTA 무관세 전환으로 국산 감자 생산기반과 농가 피해가 우려된다.",
            link="https://example.com/policy-potato-tariff",
        )
        regulation_update = self._make_article(
            section="policy",
            title="농지 화장실·주차공간 허용…공공비축미 중간정산금 6만원 [하반기 달라지는 것]",
            description="농업인은 농지전용허가 없이 편의시설을 설치하고 공공비축미 정산금을 지원받는다.",
            link="https://example.com/policy-agri-regulation-update",
        )

        photo = self._make_article(
            section="dist",
            title="[포토] 도농상생 매장, 영암 농산물 직거래 판매",
            description="직거래장 개점식 사진을 소개한다.",
            link="https://example.com/dist-photo-filler",
        )
        dist_fixed = [
            self._make_article(
                section="dist",
                title=f"농산물 도매시장 운영 개선 {idx}",
                description="도매시장 경매와 출하 운영을 개선한다.",
                link=f"https://example.com/dist-fixed-{idx}",
            )
            for idx in range(4)
        ]
        dist_fixed[0] = self._make_article(
            section="dist",
            title="'지역 농산물 판로확대'…동서울-영암낭주농협 직거래장 개점",
            description="지역 농산물 직거래장 개점식을 열었다.",
            link="https://example.com/dist-direct-market-opening",
        )
        joint_export = self._make_article(
            section="dist",
            title="전주원예농협, 공동선별 물량 늘리고 수출도 ‘척척’",
            description="양파 공선출하회 취급량이 600t으로 3배 늘었고 대만 수출과 대형마트 판로를 확대했다.",
            link="https://example.com/dist-joint-selection-export",
        )
        public_execution = self._make_article(
            section="policy",
            title="aT, 유통본부 점검…공공급식 거래액 2.3%↑·스마트 APC 115개 확대",
            description="aT가 생산유통통합조직과 공공급식플랫폼, 스마트 APC 115개소 확대 실적을 발표했다.",
            link="https://example.com/dist-public-execution",
        )
        public_execution_variant = self._make_article(
            section="policy",
            title="aT 유통본부 회의, 스마트 APC 115곳·공공급식 2.3% 성장 점검",
            description="같은 유통본부 실적을 다룬 재전송 기사다.",
            link="https://example.com/dist-public-execution-variant",
        )

        equipment = self._make_article(
            section="pest",
            title="최신 방제기로 농가 맞춤 지원",
            description="농협이 무인헬기와 드론 방제장비를 지원한다.",
            link="https://example.com/pest-equipment-tail",
        )
        pest_fixed = [
            self._make_article(
                section="pest",
                title=f"과수 병해충 현장 대응 {idx}",
                description="과수 농가가 병해충 확산을 막기 위해 방제한다.",
                link=f"https://example.com/pest-floor-fixed-{idx}",
            )
            for idx in range(4)
        ]
        anthracnose = self._make_article(
            section="pest",
            title="경북농기원, 장마철 고추 탄저병 주의 당부",
            description="경북도농업기술원이 고추 탄저병 확산을 경고하고 예방 살균제 방제를 당부했다.",
            link="https://example.com/pest-anthracnose-warning",
        )

        first_shipment = self._make_article(
            section="supply",
            title="대경사과원예농협, 자두·복숭아 본격 출하",
            description="임시총회와 초출하 행사를 열어 첫 출하를 축하했다.",
            link="https://example.com/supply-first-shipment",
        )
        supply_fixed = [
            self._make_article(
                section="supply",
                title=f"채소 가격·수급 동향 {idx}",
                description="채소 생산량과 출하량, 가격 변화를 점검한다.",
                link=f"https://example.com/supply-floor-fixed-{idx}",
            )
            for idx in range(4)
        ]
        onion_response = self._make_article(
            section="supply",
            title="경북도, 가격 하락 양파 농가 위해 대대적 수급 안정 대책 추진",
            description="경북도가 양파 가격 하락에 대응해 농가 수급안정과 소비촉진 대책을 시행한다.",
            link="https://example.com/supply-onion-response",
        )

        final_by_section = {
            "supply": supply_fixed + [first_shipment],
            "policy": [venture, import_one, import_two] + policy_fixed,
            "dist": dist_fixed + [photo],
            "pest": pest_fixed + [equipment],
        }
        raw_by_section = {
            "supply": [onion_response],
            "policy": [
                production_response,
                potato_tariff,
                regulation_update,
                public_execution,
                public_execution_variant,
            ],
            "dist": [joint_export],
            "pest": [anthracnose],
        }

        changed = main._repair_publish_daily_editorial_floor(final_by_section, raw_by_section)

        self.assertGreaterEqual(changed, 6)
        self.assertTrue(all(len(final_by_section[key]) == 5 for key in ("supply", "policy", "dist", "pest")))
        policy_titles = [article.title for article in final_by_section["policy"]]
        self.assertFalse(any("벤처투자" in title for title in policy_titles))
        self.assertEqual(
            sum(main._is_policy_import_management_council_story(article) for article in final_by_section["policy"]),
            1,
        )
        self.assertTrue(any("국내 생산 기반" in title for title in policy_titles))
        self.assertTrue(any("계절관세" in title for title in policy_titles))
        self.assertTrue(any("공공비축미" in title for title in policy_titles))
        self.assertTrue(any("공동선별" in article.title for article in final_by_section["dist"]))
        self.assertTrue(any("스마트 APC" in article.title for article in final_by_section["dist"]))
        self.assertEqual(
            sum(main._is_dist_quantified_public_execution_story(article) for article in final_by_section["dist"]),
            1,
        )
        self.assertFalse(any("[포토]" in article.title for article in final_by_section["dist"]))
        self.assertFalse(any("직거래장 개점" in article.title for article in final_by_section["dist"]))
        self.assertTrue(any("탄저병" in article.title for article in final_by_section["pest"]))
        self.assertFalse(any("최신 방제기" in article.title for article in final_by_section["pest"]))
        self.assertTrue(any("수급 안정 대책" in article.title for article in final_by_section["supply"]))
        self.assertFalse(any("본격 출하" in article.title for article in final_by_section["supply"]))
