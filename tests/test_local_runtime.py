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
