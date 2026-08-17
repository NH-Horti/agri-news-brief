"""Tests for event-level story dedup, section gates, soft-news core demotion,
and summary artifact sanitization (generalized algorithm improvements)."""
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


def _mk(section, title, desc="", press="언론사", domain="news.example.com",
        link="", score=10.0, is_core=False, fit=2.0):
    link = link or f"https://{domain}/{abs(hash(title)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description=desc,
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 7, 1, 9, 0, tzinfo=KST),
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


class TestEventQuantityNormalization(unittest.TestCase):
    """'2만7000t'과 '2.7만t'을 같은 수량으로 정규화해야 한다."""

    def test_korean_composite_number_equals_decimal_scale(self):
        q1 = main._extract_event_quantities("정부, 여름배추 2만7000t 확보")
        q2 = main._extract_event_quantities("배추 정부가용물량 2.7만t 확보")
        self.assertTrue(q1 & q2, f"quantities should intersect: {q1} vs {q2}")

    def test_won_scale_normalization(self):
        q1 = main._extract_event_quantities("민생물가 안정에 1조원 투입")
        q2 = main._extract_event_quantities("물가 대책에 1조 원 규모 재원")
        self.assertTrue(q1 & q2)

    def test_different_quantities_do_not_match(self):
        q1 = main._extract_event_quantities("마늘 200톤 출하")
        q2 = main._extract_event_quantities("마늘 500톤 출하")
        self.assertFalse(q1 & q2)


class TestReviewRegressionFixes(unittest.TestCase):
    """코드리뷰에서 발견된 결함들의 회귀 방지."""

    def test_composite_korean_amount_no_double_scaling(self):
        # '1억5000만원'(=1.5억)과 '1.5억원'은 같은 수량
        q1 = main._extract_event_quantities("사업비 1억5000만원 투입")
        q2 = main._extract_event_quantities("사업비 1.5억원 투입")
        self.assertTrue(q1 & q2, f"{q1} vs {q2}")

    def test_metric_evidence_with_korean_particle(self):
        # 한글 조사('톤을')가 붙어도 수치 근거로 인정 (\b는 한글 경계에서 성립하지 않음)
        self.assertTrue(main._has_market_metric_evidence(
            "농협이 사과 5,000톤을 수매해 가격 안정에 나섰다"))
        self.assertTrue(main._has_market_metric_evidence("마늘값 30% 뛰자 정부가 방출 확대"))

    def test_at_corp_not_matched_inside_latin_words(self):
        self.assertNotIn("at", main._extract_event_gov_actors("NH Digital Platform 출시"))
        self.assertIn("at", main._extract_event_gov_actors("aT 수급 점검"))

    def test_different_diseases_not_same_event(self):
        # 같은 품목·지역·방제 행위라도 병명이 다르면 별개 사건
        reason = main._same_event_story_reason(
            "경북 사과 탄저병 방제 비상", "경북도가 사과 탄저병 방제를 당부했다",
            "경북 사과 과수화상병 매몰 확산", "경북 사과 과수원에서 과수화상병 매몰이 늘고 있다",
        )
        self.assertEqual(reason, "")

    def test_summary_note_survives_trim(self):
        # 요약이 길어도 가격 기준 주석은 잘리지 않아야 한다
        long_summary = "가락시장 도매가격이 급등했다. " * 8
        note = "단기 도매 흐름으로, 전년 대비 산지가격 약세 기사와 비교 기준이 다르다."
        out = main._append_summary_note(long_summary, note)
        self.assertIn(note, out)

    def test_pest_core_only_reason_does_not_block_tail(self):
        a = _mk("pest", "과수화상병 예방 약제 공급 확대", "약제가 농가에 공급된다")
        self.assertEqual(
            main._editorial_safe_core_demote_reason(a, "pest"), "pest_no_active_risk_core")
        block = main._preferred_tail_block_reason(a, "pest", current_count=4, raw_count=20)
        self.assertNotEqual(block, "pest_no_active_risk_core",
                            "core 전용 사유가 tail 배치를 막으면 안 된다")

    def test_gov_actor_soft_news_kept_as_tail(self):
        a = _mk("policy", "농식품부-지자체, 여름배추 수급안정 업무협약",
                "정부와 지자체가 수급 안정을 위해 협약을 맺었다")
        block = main._preferred_tail_block_reason(a, "policy", current_count=4, raw_count=20)
        self.assertFalse(block.startswith("soft_news"),
                         "정부 행위자 실행 기사는 tail로 유지되어야 한다")

    def test_weak_noise_sentence_kept_with_agri_context(self):
        out = main._sanitize_summary_text(
            "농협은 화훼 구독 서비스를 확대한다. 정기배송 물량은 전년 대비 30% 늘었다.")
        self.assertIn("구독 서비스", out)
        out2 = main._sanitize_summary_text(
            "배추 가격이 급등했다. 구독과 좋아요 부탁드립니다.")
        self.assertNotIn("좋아요", out2)


class TestSameEventMultiOutlet(unittest.TestCase):
    """같은 사건의 다매체 기사는 매체가 달라도 하나의 사건으로 판정."""

    def test_same_event_different_outlets(self):
        reason = main._same_event_story_reason(
            "정부, 여름배추 2만7000t 확보…폭염·폭우 수급 불안 막는다", "",
            "배추 정부가용물량 2.7만t 확보…송미령 \"안정적 생산 총력\"", "",
        )
        self.assertTrue(reason)

    def test_same_gov_commodity_action(self):
        reason = main._same_event_story_reason(
            "\"가을 금배추 없도록\"…농식품부, 여름철 배추 생산 안정화 총력 지원",
            "농식품부는 비축량 확대 등 수급 대응에 나섰다",
            "여름 배추 수급 '비상등'…정부, 태백 고랭지 찾아 작황 점검",
            "정부가 생산 현장을 점검하며 수급 안정 대응에 나섰다",
        )
        self.assertTrue(reason)

    def test_different_commodities_not_same_event(self):
        reason = main._same_event_story_reason(
            "정부, 여름배추 2만7000t 확보", "",
            "양파 가격 폭락에 전남 농가 시름", "",
        )
        self.assertEqual(reason, "")

    def test_cabbage_vs_napa_cabbage_not_confused(self):
        # '배추'⊂'양배추' 부분문자열 오탐 방지
        comm_a = main._extract_event_commodities("서산 양배추값 폭락에 농민들 시름")
        self.assertIn("양배추", " ".join(comm_a))
        self.assertNotIn("배추", {c for c in comm_a if c == "배추"} - {"양배추"} or set())
        reason = main._same_event_story_reason(
            "서산 양배추값 폭락에 농민들 '밭 갈아엎을 판'", "",
            "여름배추 가격 급등에 정부 비축분 방출", "",
        )
        self.assertEqual(reason, "")

    def test_generic_small_numbers_do_not_merge_gov_stories(self):
        # 서로 다른 정부 관련 기사가 '1kg당', 소액 가격, 비율 등 흔한 수치 공유로 병합되면 안 된다
        reason = main._same_event_story_reason(
            "'계란 10개에 5000원'…물가 폭등에 '1조원' 쏟아 붓는다",
            "정부가 1조원을 투입한다. 상추 1kg당 1100원, 20% 급등",
            "\"어쩌나, 상추 다 버리게 생겼네\"…농가 '초비상'",
            "한국농수산식품유통공사에 따르면 상추 1kg당 1100원으로 급등했다. 재배면적 126ha",
        )
        self.assertEqual(reason, "")

    def test_salient_quantity_merges_same_gov_package(self):
        reason = main._same_event_story_reason(
            "정부, 민생물가 안정에 1조원 투입", "정부가 물가 안정 대책을 발표했다",
            "'계란 10개에 5000원'…물가 폭등에 '1조원' 쏟아 붓는다",
            "정부는 1조원 규모 물가 안정 대책과 농축산물 할인 지원을 발표했다",
        )
        self.assertTrue(reason)

    def test_different_region_market_open_not_same_event(self):
        # 지역이 다른 별개 산지 경매 개장은 같은 사건이 아니다 (테마 상한으로만 제어)
        reason = main._same_event_story_reason(
            "합천군, 마늘 산지경매 본격 시작", "합천동부농협 초매식",
            "영천 신녕농협, 마늘 초매식 열어", "영천 마늘경매식집하장",
        )
        self.assertEqual(reason, "")

    def test_ganghwa_county_pest_reports_are_same_event(self):
        self.assertIn("강화군", main._region_set("강화군 고추 탄저병 주의"))
        reason = main._same_event_story_reason(
            "강화군 고추 탄저병 주의",
            "강화군은 노지 고추 탄저병 확산에 대비해 현장 방제를 당부했다",
            "강화군, '탄저병·역병 확산' 비상…노지 고추 현장관리 강화",
            "강화군 농업기술센터가 고추 탄저병 예찰과 방제를 강화했다",
        )
        self.assertTrue(reason)

    def test_online_wholesale_logistics_reports_are_same_program(self):
        reason = main._same_event_story_reason(
            "온라인 도매시장 권역별 거점물류센터 4곳 9월 가동",
            "농식품부와 aT가 온라인 도매시장 물류망을 구축한다",
            "농식품부·aT, 거점물류센터 시범사업 협의체 첫 회의",
            "온라인도매시장 권역 물류망 구축과 센터 운영을 논의했다",
        )
        self.assertEqual(reason, "same_online_market_logistics_program")

    def test_same_apc_upgrade_is_deduped_across_outlets(self):
        articles = [
            _mk(
                "dist",
                "무주군, 스마트 APC 전환으로 산지유통센터 첨단화",
                "무주군이 7억7000만원을 투입해 ERP 포장라인과 복분자 냉동창고를 구축했다.",
                press="전라일보",
                domain="jeollailbo.com",
            ),
            _mk(
                "dist",
                "무주군, 농산물산지유통센터 고도화…선별 체계·냉동시설 보완",
                "전북 무주군은 농림식품부 공모사업으로 산지유통센터의 선별 체계와 냉동시설을 보완했다.",
                press="연합뉴스",
                domain="yna.co.kr",
            ),
            _mk(
                "dist",
                "무주 농산물산지유통센터 첨단화 완료…산지유통 경쟁력 강화",
                "무주군이 스마트 APC 전환사업을 마치고 연간 6000톤 선별 기반을 마련했다.",
                press="뉴스핌",
                domain="newspim.com",
            ),
        ]

        self.assertTrue(main._duplicate_story_pair_reason(articles[0], articles[1]))
        self.assertTrue(main._duplicate_story_pair_reason(articles[0], articles[2]))
        final = {"supply": [], "policy": [], "dist": list(articles), "pest": []}
        removed, _refilled = main._final_global_story_dedupe(final, None, min_keep=1)
        self.assertEqual(removed, 2)
        self.assertEqual(len(final["dist"]), 1)

    def test_same_province_smart_apc_program_is_deduped(self):
        left = _mk(
            "dist",
            "경북도, AI 기반 스마트 APC 확대…농산물 유통 혁신 속도",
            "경상북도는 2030년까지 1433억원을 투입해 스마트 APC 26곳을 구축한다.",
        )
        right = _mk(
            "dist",
            "AI가 선별하고 로봇이 포장…경북, 스마트 APC 26곳 구축",
            "경북도는 노후 APC 88곳을 개선하고 국비 506억원을 포함해 총 1433억원을 투입한다.",
            domain="other.example.com",
        )

        self.assertEqual(main._duplicate_story_pair_reason(left, right), "same_facility_upgrade")

    def test_same_quantified_supply_program_is_cross_section_duplicate(self):
        supply = _mk(
            "supply",
            "농협·농식품부, 여름 과채류 수급 안정에 12억4천만원 투입",
            "여름철 과채류 가격과 출하 안정을 위해 농가 지원에 나선다.",
            press="연합뉴스",
            domain="yna.co.kr",
        )
        policy = _mk(
            "policy",
            "농협, 폭염 대응 하절기 과채류 수급 안정 대책 추진…12억4천만원 투입",
            "농림축산식품부와 농협이 할인 지원과 출하비 지원 대책을 시행한다.",
            press="세계일보",
            domain="segye.com",
        )

        self.assertTrue(main._duplicate_story_pair_reason(supply, policy))

    def test_same_supply_program_matches_when_one_headline_omits_amount(self):
        detailed = _mk(
            "policy",
            "농협, 폭염 대응 하절기 과채류 수급 안정 대책 추진…12억4천만원 투입",
            "농림축산식품부와 농협이 생산부터 유통까지 지원한다.",
            press="세계일보",
            domain="segye.com",
        )
        short = _mk(
            "policy",
            "농협-농식품부, 과채류 수급 안정에 협력",
            "주요 과채류의 도매가격이 기준가격 아래면 참여 농가를 지원한다.",
            press="보건신문",
            domain="bokuennews.com",
        )

        self.assertEqual(
            main._duplicate_story_pair_reason(detailed, short),
            "same_supply_stabilization_program",
        )

    def test_same_food_cost_relief_release_matches_across_headline_angles(self):
        price_angle = _mk(
            "policy",
            '농식품부, 식품업계 원가부담 완화 지원…"물가 안정 총력"',
            "수입 원재료 할당관세와 원료 구매자금 융자를 지원한다.",
            press="SBS",
            domain="biz.sbs.co.kr",
        )
        industry_angle = _mk(
            "policy",
            '식품업계 잇단 인상에…농식품부 "원가 부담 완화 지원"',
            "식품업체의 가격 인상 시기를 분산하고 할인 행사를 확대한다.",
            press="연합뉴스TV",
            domain="yonhapnewstv.co.kr",
        )

        self.assertEqual(
            main._duplicate_story_pair_reason(price_angle, industry_angle),
            "same_food_industry_cost_relief",
        )

    def test_field_price_collapse_is_owned_by_supply_not_distribution(self):
        article = _mk(
            "dist",
            '"가락시장 수수료도 안 나와"…밭에서 썩는 고랭지 배추',
            (
                "강원 고랭지에서 배추 가격 폭락으로 수확을 포기하는 농가가 늘었다. "
                "가락시장 가격이 생산비와 포장비, 운임에도 못 미쳐 팔수록 손해다."
            ),
            press="YTN",
            domain="ytn.co.kr",
            score=40.0,
        )
        raw = {"supply": [], "policy": [], "dist": [article], "pest": []}

        self.assertTrue(main.is_dist_primary_supply_price_story(article.title, article.description))
        self.assertEqual(
            main._postbuild_article_reject_reason(article, "dist", apply_selection_fit=False),
            "dist_primary_supply_price_story",
        )
        self.assertEqual(
            main._preferred_tail_block_reason(
                article,
                "supply",
                current_count=4,
                raw_count=20,
            ),
            "",
        )
        self.assertTrue(
            main._is_supply_priority_threshold_rescue(
                article,
                "supply",
                main._get_section_conf("supply") or {},
            )
        )
        main._global_section_reassign(
            raw,
            datetime(2026, 7, 28, 6, 0, tzinfo=KST),
            datetime(2026, 7, 29, 6, 0, tzinfo=KST),
        )
        self.assertIn(article, raw["supply"])
        self.assertNotIn(article, raw["dist"])
        self.assertEqual(article.selection_stage, "section_owner_reassign")
        self.assertGreater(article.selection_fit_score, 4.0)

    def test_onion_price_recovery_reports_are_same_event(self):
        reason = main._same_event_story_reason(
            "양파값 회복에 882억 투입한 농협, 효과 봤다",
            "정부와 지자체의 수급안정 대책으로 1kg당 570원에서 1022원으로 회복됐다",
            "농협, 정부·지자체와 양파 수급 잡고 가격 회복세",
            "882억원 규모 대책 이후 양파 도매가격이 kg당 1022원으로 올랐다",
        )
        self.assertTrue(reason)

    def test_price_recovery_dedupe_survives_truncated_republication_body(self):
        reason = main._same_event_story_reason(
            "양파값 회복에 882억 투입한 농협, 효과 봤다",
            "정부 수급안정 대책으로 양파 도매가격이 570원에서 1022원으로 회복됐다",
            "농협·정부·지자체 전방위 대책으로 양파값 두 달 만에 80% 회복",
            "중생종 양파 출하를 늦추는 농가의 손실을 보전했다",
        )
        self.assertEqual(reason, "same_commodity_price_recovery")

    def test_verb_endings_are_not_regions(self):
        self.assertNotIn("따르면", main._region_set("농협 발표에 따르면 양파 가격이 회복됐다"))
        self.assertNotIn("발생하면", main._region_set("병해충이 발생하면 즉시 방제한다"))


class TestFinalSourceQualityBudget(unittest.TestCase):
    """모든 후반 보정 뒤에도 저티어 매체 예산을 지킨다."""

    def test_press_tier_recognizes_established_secondary_outlets(self):
        self.assertEqual(main.press_tier("신아일보", "shinailbo.co.kr"), 2)
        self.assertEqual(main.press_tier("오마이뉴스", "ohmynews.com"), 2)
        self.assertEqual(main.press_tier("뉴스클레임", "newsclaim.co.kr"), 1)
        self.assertEqual(main.press_tier("gpkorea", "gpkorea.com"), 1)

    def test_excess_low_tier_cards_are_replaced_by_qualified_sources(self):
        low = [
            _mk("pest", f"고추 병해충 현장 점검 {idx}", press=f"인터넷매체{idx}",
                domain=f"low{idx}.example.com", score=11.0)
            for idx in range(5)
        ]
        trusted = [
            _mk("pest", f"과수 병해충 예찰 강화 {idx}", press=press_name,
                domain=f"trusted{idx}.example.com", score=20.0 + idx)
            for idx, press_name in enumerate(("연합뉴스", "농민신문", "한국농어민신문", "신아일보"))
        ]
        final = {"supply": [], "policy": [], "dist": [], "pest": list(low)}
        raw = {"supply": [], "policy": [], "dist": [], "pest": list(low) + trusted}

        with (
            patch.object(main, "_fresh_section_fit", return_value=2.0),
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "_soft_news_core_demote_reason", return_value=""),
            patch.object(main, "_preferred_tail_block_reason", return_value=""),
            patch.object(main, "_is_stale_swap_candidate", return_value=False),
            patch.object(main, "_violates_section_theme_cap", return_value=False),
            patch.object(main, "_duplicate_story_pair_reason", return_value=""),
        ):
            changed = main._cap_final_low_tier_sources(
                final,
                raw,
                max_per_section=1,
                max_total=4,
            )

        self.assertGreaterEqual(changed, 4)
        self.assertEqual(len(final["pest"]), 5)
        self.assertLessEqual(
            sum(main.press_tier(article.press, article.domain) == 1 for article in final["pest"]),
            1,
        )

    def test_named_authoritative_pest_warning_beats_generic_weather_notice(self):
        victim = _mk(
            "pest",
            "외식 가맹점 장비 지원",
            press="인터넷매체",
            domain="low.example.com",
            score=10.0,
        )
        generic = _mk(
            "pest",
            "충남도 농기원, 여름철 농작물 고온·장마·해충 피해 선제 대응",
            "농업기술원이 장마 피해 예방과 시설물 관리를 당부했다",
            press="농수축산신문",
            domain="generic.example.com",
            score=25.13,
        )
        whitefly = _mk(
            "pest",
            "농진청, 토마토 농가 담배가루이 초기 방제 총력 당부",
            "농촌진흥청은 토마토황화잎말림바이러스 확산을 막기 위해 담배가루이 예찰과 방제를 당부했다",
            press="농축유통신문",
            domain="whitefly.example.com",
            score=19.89,
        )
        final = {"supply": [], "policy": [], "dist": [], "pest": [victim]}
        raw = {"supply": [], "policy": [], "dist": [], "pest": [victim, generic, whitefly]}

        with (
            patch.object(main, "_fresh_section_fit", return_value=2.0),
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "_soft_news_core_demote_reason", return_value=""),
            patch.object(main, "_preferred_tail_block_reason", return_value=""),
            patch.object(main, "_is_stale_swap_candidate", return_value=False),
            patch.object(main, "_violates_section_theme_cap", return_value=False),
            patch.object(main, "_duplicate_story_pair_reason", return_value=""),
        ):
            changed = main._cap_final_low_tier_sources(
                final,
                raw,
                max_per_section=0,
                max_total=0,
            )

        self.assertEqual(changed, 1)
        self.assertIs(final["pest"][0], whitefly)


class TestCrossSectionDedupe(unittest.TestCase):
    """같은 사건이 supply와 policy에 동시 배치되면 하나만 남긴다."""

    def test_cross_section_duplicate_removed(self):
        supply_core = _mk("supply", "배추 정부가용물량 2.7만t 확보…송미령 \"안정적 생산 총력\"",
                          "농식품부가 정부가용물량을 확보했다", is_core=True, score=20.0, fit=3.0)
        policy_dup = _mk("policy", "정부, 여름배추 2만7000t 확보…폭염·폭우 수급 불안 막는다",
                         "농식품부 발표", score=15.0, fit=2.0)
        policy_other = _mk("policy", "농산물 검역 규제 개선안 시행", "정부가 검역 절차를 개선한다", score=12.0)
        final = {"supply": [supply_core], "policy": [policy_dup, policy_other], "dist": [], "pest": []}
        removed, _refilled = main._final_global_story_dedupe(final, None)
        self.assertGreaterEqual(removed, 1)
        self.assertIn(supply_core, final["supply"])
        self.assertNotIn(policy_dup, final["policy"])
        self.assertIn(policy_other, final["policy"])

    def test_within_section_multi_outlet_duplicate_removed(self):
        a1 = _mk("supply", "정부, 여름배추 2만7000t 확보…수급 불안 막는다", press="매체A", score=18.0, fit=3.0)
        a2 = _mk("supply", "배추 정부가용물량 2.7만t 확보…생산 총력", press="매체B", score=12.0, fit=2.0)
        final = {"supply": [a1, a2], "policy": [], "dist": [], "pest": []}
        removed, _ = main._final_global_story_dedupe(final, None)
        self.assertEqual(removed, 1)
        self.assertEqual(len(final["supply"]), 1)

    def test_theme_repetition_capped(self):
        arts = [
            _mk("dist", "합천군, 마늘 산지경매 본격 시작", "초매식이 열렸다", score=15.0),
            _mk("dist", "영천 신녕농협, 마늘 초매식 열어", "경매가 시작됐다", score=14.0),
            _mk("dist", "창녕 건마늘 경매 300톤 첫 출하", "초매식 개최", score=13.0),
            _mk("dist", "가락시장 하계 휴업 일정 확정", "도매시장 경매 일정 변경", score=12.0),
        ]
        final = {"supply": [], "policy": [], "dist": list(arts), "pest": []}
        removed, _ = main._final_global_story_dedupe(final, None)
        garlic_market = [a for a in final["dist"] if "마늘" in a.title]
        self.assertLessEqual(len(garlic_market), 2)
        self.assertIn(arts[3], final["dist"])


class TestSoftNewsCoreDemotion(unittest.TestCase):
    """행사·홍보·교육·인사·칼럼성 기사는 core로 승격되지 않는다."""

    def test_education_event_demoted(self):
        a = _mk("dist", "청년 양돈농가, 공판장서 축산유통 배웠다", "현장교육이 열렸다")
        self.assertTrue(main._soft_news_core_demote_reason(a))

    def test_promo_event_demoted(self):
        a = _mk("dist", "대아청과·애월 농협, 제주산 농산물 유통 활성화 '맞손'", "간담회를 열었다")
        self.assertTrue(main._soft_news_core_demote_reason(a))

    def test_regional_roundup_demoted(self):
        a = _mk("dist", "[2일 경북도] 'daily 여름과일 특별전' 진행 등", "경북도가 특별전을 연다")
        self.assertTrue(main._soft_news_core_demote_reason(a))

    def test_opinion_column_demoted(self):
        a = _mk("pest", "[취재수첩] 과수화상병이 '개꿀'이라니", "칼럼")
        self.assertTrue(main._soft_news_core_demote_reason(a))

    def test_hard_market_news_not_demoted(self):
        a = _mk("supply", "배추 도매가격 30% 급등…반입량 20% 감소", "가락시장 경락 가격이 급등했다")
        self.assertEqual(main._soft_news_core_demote_reason(a), "")

    def test_ceremony_with_hard_numbers_not_demoted(self):
        # 초매식이라도 가격·물량 수치가 있으면 시장 뉴스로 취급 (core 강등 아님)
        a = _mk("dist", "창녕 건마늘 경매 200톤 출하…최고가 8,000원",
                "마늘공판장 초매식에서 대서종 최고가 8000원을 기록했다")
        self.assertEqual(main._soft_news_core_demote_reason(a), "")

    def test_final_core_gate_demotes_and_repairs(self):
        weak_core = _mk("dist", "청년 양돈농가, 공판장서 축산유통 배웠다", "교육 행사", is_core=True, score=15.0)
        hard_tail = _mk("dist", "가락시장 반입량 15% 감소…경락가 강세", "도매시장 반입이 줄었다", score=14.0, fit=3.0)
        final = {"supply": [], "policy": [], "dist": [weak_core, hard_tail], "pest": []}
        changed = main._demote_soft_news_final_cores(final)
        self.assertGreaterEqual(changed, 1)
        self.assertFalse(weak_core.is_core)
        self.assertTrue(hard_tail.is_core)


class TestPestSectionGate(unittest.TestCase):
    """병해충 무관 기사는 pest 섹션에 진입할 수 없다."""

    def test_inauguration_article_rejected(self):
        a = _mk("pest", "보은군, 최재형 군수 취임식 생략한 채 민선 9기 민생 행보 본격화",
                "취임식을 생략하고 민생 현장을 찾았다")
        reason = main._postbuild_article_reject_reason(a, "pest", apply_selection_fit=False)
        # 기존 세부 사유(pest_partial_mention 등)가 먼저 발화해도 무방 — 거부 자체가 계약
        self.assertTrue(reason.startswith("pest_"), f"expected pest rejection, got: {reason!r}")
        self.assertFalse(main._has_pest_or_growth_risk_signal(a.title, a.description))

    def test_pest_control_article_accepted(self):
        a = _mk("pest", "농진청, 고흥 풀무치 긴급 방제 현장 점검", "돌발해충 풀무치 예찰·방제")
        self.assertTrue(main._has_pest_or_growth_risk_signal(a.title, a.description))

    def test_growth_risk_with_crop_context_accepted(self):
        a = _mk("pest", "과수 냉해 피해 확산…사과 농가 비상", "저온피해가 과원에 번지고 있다")
        self.assertTrue(main._has_pest_or_growth_risk_signal(a.title, a.description))

    def test_weather_without_crop_context_rejected(self):
        self.assertFalse(main._has_pest_or_growth_risk_signal(
            "폭염에 전력수요 최고치 경신", "전력거래소는 전력 수요가 급증했다고 밝혔다"))

    def test_authoritative_whitefly_warning_is_not_a_weak_notice(self):
        article = _mk(
            "pest",
            "농진청, 토마토 농가 담배가루이 초기 방제 총력 당부",
            "농촌진흥청은 토마토황화잎말림바이러스 확산을 막기 위해 담배가루이 예찰과 초기 방제를 당부했다",
            press="농축유통신문",
            domain="amnews.co.kr",
            score=19.89,
        )
        self.assertTrue(main._has_named_pest_signal(article.title))
        self.assertFalse(main._is_weak_pest_tail(article))
        self.assertFalse(main._is_generic_pest_notice_tail(article))
        self.assertEqual(
            main._preferred_tail_block_reason(article, "pest", current_count=5, raw_count=30),
            "",
        )


class TestPolicyOrgEventGate(unittest.TestCase):
    """조합·단체 행사 기사는 정책 섹션에 들어오지 못한다."""

    def test_org_event_rejected_from_policy(self):
        a = _mk("policy", "경기동부 원예농협, '햇사레 복숭아' 출하협의회 열어",
                "조합원·농산물도매시장 관계자 등 300여명 참석")
        reason = main._postbuild_article_reject_reason(a, "policy", apply_selection_fit=False)
        self.assertEqual(reason, "policy_org_event_not_policy")

    def test_gov_policy_meeting_kept(self):
        self.assertFalse(main._is_policy_org_event_without_policy_action(
            "농식품부, 여름철 수급안정 대책회의 개최", "정부가 수급 안정 대책을 논의했다"))

    def test_org_event_with_policy_action_kept(self):
        self.assertFalse(main._is_policy_org_event_without_policy_action(
            "농협, 할당관세 확대 건의…정부 협의회 참석", "관세 정책 건의"))

    def test_school_food_donation_is_rejected_from_policy_refill(self):
        article = _mk(
            "policy",
            "학생들의 정성이 이웃의 밥상을 채웠다…양파 절...",
            "학생들이 직접 재배한 양파로 만든 음식을 어려운 이웃에게 기부했다. "
            "양파절임을 나눔냉장고에 전달해 훈훈함을 더했다. "
            + ("지역사회 나눔 활동을 설명하는 내용이다. " * 40)
            + "관련 기사 푸터에는 소비자정책심의위원회 소식도 포함됐다.",
            press="중도일보",
            domain="joongdo.co.kr",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(article, "policy", apply_selection_fit=False),
            "policy_community_noise",
        )


class TestSectionPlacementSignals(unittest.TestCase):
    """가격 전망은 supply, 물류 운영은 dist로 보내는 신호를 보존한다."""

    def test_vegetable_price_outlook_is_supply_context(self):
        self.assertTrue(main.is_supply_price_outlook_context(
            "장맛비 끝나면 채소값 오르나…산지 출하 감소에 가격 상승 조짐",
            "장마 뒤 산지 출하량이 줄어 도매가격과 채솟값이 오를 수 있다는 전망이다",
        ))

    def test_online_wholesale_logistics_is_distribution_context(self):
        self.assertTrue(main.is_dist_market_ops_context(
            "농식품부·aT, 거점물류센터 시범사업 협의체 첫 회의",
            "온라인도매시장 4대 권역 물류망 구축과 센터 가동 방안을 논의했다",
        ))


class TestFoodserviceMenuGate(unittest.TestCase):
    """외식·프랜차이즈 메뉴 가격 기사는 supply에 들어가지 못한다."""

    def test_franchise_menu_price_rejected(self):
        a = _mk("supply", "중량 줄이더니 가격도…굽네치킨, 일부 사이드 메뉴 인상",
                "프랜차이즈 치킨 브랜드가 사이드 메뉴 가격을 올렸다")
        reason = main._postbuild_article_reject_reason(a, "supply", apply_selection_fit=False)
        self.assertTrue(reason, "외식 메뉴 가격 기사는 supply에서 거부되어야 한다")

    def test_foodservice_supply_chain_story_kept(self):
        self.assertFalse(main.is_foodservice_menu_price_story(
            "치킨값 인상 압박…닭고기 산지 수급난에 원물 가격 급등",
            "산지 출하량 감소로 원물 가격이 올랐다"))

    def test_farm_price_story_kept(self):
        self.assertFalse(main.is_foodservice_menu_price_story(
            "양파 도매가격 급락…산지 출하 몰려", "도매시장 반입이 늘었다"))

    def test_franchise_kitchen_equipment_promo_is_rejected(self):
        article = _mk(
            "pest",
            "나나방콕, 가맹점 자동 칼질기계 도입비 전액 지원",
            "외식 프랜차이즈 본사가 가맹점주의 주방 조리 효율을 위해 장비 구매비를 지원한다",
            press="gpkorea",
            domain="gpkorea.com",
        )
        self.assertEqual(
            main._postbuild_article_reject_reason(article, "pest", apply_selection_fit=False),
            "non_agri_foodservice_equipment_promo",
        )

    def test_real_agricultural_sorting_equipment_story_is_kept(self):
        self.assertFalse(main.is_non_agri_foodservice_equipment_promo_context(
            "농협 APC, 양파 공동선별 자동화 장비 도입",
            "산지 농가의 양파 공동선별과 공선출하 효율을 높이는 설비다",
        ))


class TestStrongCandidatePriority(unittest.TestCase):
    """중복 그룹에서 정보량·적합도 높은 대표 기사가 살아남는다."""

    def test_higher_fit_and_info_wins(self):
        strong = _mk("supply", "정부, 여름배추 2만7000t 확보…수급 안정 총력",
                     "농식품부가 가용물량 2만7000t을 확보하고 비축을 확대한다",
                     press="연합뉴스", score=20.0, fit=3.5)
        weak = _mk("policy", "배추 가용물량 2.7만t 확보", "정부 확보", score=8.0, fit=1.0)
        self.assertGreater(main._story_keep_priority(strong), main._story_keep_priority(weak))

    def test_core_flag_dominates(self):
        core = _mk("supply", "배추 수급 대책", "", is_core=True, score=5.0, fit=1.0)
        tail = _mk("policy", "배추 수급 대책 발표", "", score=50.0, fit=5.0)
        self.assertGreater(main._story_keep_priority(core), main._story_keep_priority(tail))


class TestSummarySanitization(unittest.TestCase):
    """요약 특수토큰·반복 문장·크롤링 잡음·절단 정리."""

    def test_model_token_head_kept(self):
        s = ("농식품부는 정부가용물량 2.7만t을 확보하고 수입안정보험을 도입했다 .〈/s〉"
             "강원 태백 고랭지 배추 재배단지에서 여름배추 생육 점검이 이뤄졌다. 농식품부는 배추 정부가용물량")
        out = main._sanitize_summary_text(s)
        self.assertNotIn("〈/s〉", out)
        self.assertNotIn("/s", out)
        self.assertIn("수입안정보험", out)
        self.assertNotIn("생육 점검이 이뤄졌다", out)  # 토큰 이후 잘린 꼬리 제거

    def test_ascii_model_token_stripped(self):
        out = main._sanitize_summary_text("가격이 급등했다.</s>가격이 급등했다.")
        self.assertNotIn("</s>", out)

    def test_crawl_metadata_stripped(self):
        s = ("안성 고삼농협, 친환경 양파 미계약 물량 전량 매입 입력 : 2026-07-02 18:38 "
             "수정 : 2026-07-02 18:38 TTS 스크랩 프린트 작게 크게 0 페이스북 트위터 네이버 "
             "카카오톡 주소복사 가격 폭락 속 '못난이 양파'까지 매입하기로 했다.")
        out = main._sanitize_summary_text(s)
        self.assertNotIn("입력 :", out)
        self.assertNotIn("스크랩", out)
        self.assertNotIn("주소복사", out)
        self.assertIn("매입", out)

    def test_byline_stripped(self):
        out = main._sanitize_summary_text(
            "(창녕=국제뉴스) 홍성만 기자 = 경남 창녕농협은 건마늘 경매 초매식을 열었다.")
        self.assertNotIn("기자", out)
        self.assertIn("창녕농협", out)

    def test_numbers_preserved(self):
        # UI 잡음 제거가 수량·연도 숫자를 침식하면 안 된다 (회귀 방지)
        s = "2026년산 건마늘 경매가 시작됐다. 1㎏ 최고가는 5000원이었고 100여명이 참석했다."
        out = main._sanitize_summary_text(s)
        self.assertIn("2026년산", out)
        self.assertIn("5000원", out)
        self.assertIn("100여명", out)

    def test_repeated_sentences_removed(self):
        out = main._sanitize_summary_text(
            "배추 가격이 급등했다. 정부가 대책을 발표했다. 배추 가격이 급등했다.")
        self.assertEqual(out.count("배추 가격이 급등했다"), 1)

    def test_truncation_repaired(self):
        out = main._repair_summary_truncation(
            "정부가 배추 수급 안정 대책을 발표했다. 농식품부는 비축 물량을 확대하고 수입안정보험")
        self.assertTrue(out.endswith("발표했다."))

    def test_title_echo_avoided_when_description_exists(self):
        a = _mk("supply", "안성 고삼농협, 친환경 양파 미계약 물량 전량 매입",
                "가격 폭락 속 못난이 양파까지 전량 매입하기로 했다. 농가 손실을 줄이기 위한 조치다.")
        out = main._normalize_article_summary(a, a.title)
        self.assertNotEqual(
            out.replace(" ", ""), a.title.replace(" ", ""),
            "제목 그대로 반복하는 요약은 본문 조각으로 대체되어야 한다",
        )


class TestSummaryQualityGate(unittest.TestCase):
    def test_model_token_blocks_cache(self):
        a = _mk("supply", "배추 수급 대책", "정부 대책")
        reason = main._summary_quality_block_reason(
            a, "배추 수급 대책이 발표됐다.</s>배추 수급 대책이 발표됐다. 정부가 비축량을 확대하기로 했다.")
        self.assertEqual(reason, "model_token")


class TestBoundedTermMatching(unittest.TestCase):
    """한글은 \\w라서 \\b가 성립하지 않는다. 짧은 노이즈 어휘가 다른 단어 안에
    우연히 들어앉아 정상 기사를 죽이던 오탐을 막는다."""

    def test_korean_term_inside_other_word_is_not_matched(self):
        self.assertEqual(main.count_any_bounded("별도로 계약재배 물량을 매입", ("도로",)), 0)
        self.assertEqual(main.count_any_bounded("우수사무소에 선정됐다", ("수사",)), 0)
        self.assertEqual(main.count_any_bounded("행정 절차로 진행한다", ("차로",)), 0)

    def test_korean_term_with_particle_still_matches(self):
        # 뒤에는 조사가 붙으므로 뒤경계는 요구하지 않는다
        self.assertEqual(main.count_any_bounded("도로를 넓히고", ("도로",)), 1)
        self.assertEqual(main.count_any_bounded("검찰 수사가 시작됐다", ("수사",)), 1)

    def test_latin_abbreviation_requires_word_boundary(self):
        self.assertEqual(main.count_any_bounded("public logistics", ("ic",)), 0)
        self.assertEqual(main.count_any_bounded("양재ic 교통 정체", ("ic",)), 1)

    def test_counts_distinct_terms_like_count_any(self):
        self.assertEqual(main.count_any_bounded("도로 확장과 차로 조정", ("도로", "차로")), 2)
        self.assertEqual(main.count_any_bounded("", ("도로",)), 0)


class TestNonAgriTransportPolicyGate(unittest.TestCase):
    def test_incidental_body_substring_does_not_make_it_a_transport_story(self):
        # 2026-08-11: 본문 '별도로'의 '도로' 한 번으로 정부 특별매입 기사가 교통 기사로 분류됐다
        self.assertFalse(main.is_non_agri_transport_policy_context(
            "과잉 보리 2만5000톤 특별 매입",
            "정부와 주정업계가 기존 계약재배 물량과 별도로 추가 매입을 추진하기로 합의했다",
        ))

    def test_real_transport_policy_still_blocked(self):
        self.assertTrue(main.is_non_agri_transport_policy_context(
            "여객선 조타실 cctv 의무화 추진", "해양사고 예방을 위한 안전 대책"))
        self.assertTrue(main.is_non_agri_transport_policy_context(
            "성남~서초 고속도로 민간투자사업 우선협상대상자 선정", "양재나들목 교통 정체 개선"))

    def test_far_body_transport_mention_alone_does_not_trigger(self):
        # 리드 밖(360자 이후) 우연 등장은 판정 근거가 되지 않는다
        filler = "농산물 수급 안정을 위한 협의가 이어졌다. " * 20
        self.assertFalse(main.is_non_agri_transport_policy_context(
            "특별매입 물량 확대", filler + "고속도로 사업도 추진된다"))


class TestNhInternalNegativeGate(unittest.TestCase):
    def test_award_history_in_body_is_not_negative(self):
        # 2026-08-10: 본문 '우수사무소'의 '수사'로 산지유통 우수사례 기사가 차단됐다
        self.assertFalse(main.is_nh_internal_negative(
            "여주 ‘가지’ 경쟁력 제고 팔걷어",
            "가남농협이 공동선별·출하와 수급조절을 도맡았다. 농산물우수관리 인증도 받았다",
        ))

    def test_genuine_corruption_story_still_blocked(self):
        self.assertTrue(main.is_nh_internal_negative("농협 회장 비리 의혹 수사 착수"))
        self.assertTrue(main.is_nh_internal_negative(
            "농협중앙회 임원 횡령 혐의", "검찰이 배임 혐의로 구속영장을 청구했다"))

    def test_non_nh_story_is_never_negative(self):
        self.assertFalse(main.is_nh_internal_negative("지자체 공무원 비리 수사"))


class TestPreferredTailMarketActionVocabulary(unittest.TestCase):
    """정부 시장개입(매입·수매·방출·비축)과 수요 진작(농식품 바우처)도 수급 신호다."""

    def test_government_voucher_program_is_not_a_weak_supply_tail(self):
        a = _mk("supply", "'농식품 바우처 꾸러미' 전국 확대…온라인 주문, 집 앞까지 배송",
                "농식품바우처는 생계급여 수급 가구의 식품 접근성을 높이는 사업이다. "
                "농식품부는 고기·채소와 멜론·복숭아 등 제철과일로 구성된 농산물 꾸러미를 공급한다",
                press="대한민국정책브리핑", domain="korea.kr", score=59.5)
        self.assertEqual(
            main._preferred_tail_block_reason(a, "supply", current_count=4, raw_count=300), "")

    def test_special_purchase_title_is_not_policy_anchorless(self):
        a = _mk("policy", "과잉 보리 2만5000톤 특별 매입",
                "정부와 주정업계가 과잉 생산된 보리를 특별 매입해 산지가격 하락을 막는다",
                score=47.9)
        self.assertEqual(
            main._preferred_tail_block_reason(a, "policy", current_count=4, raw_count=84), "")

    def test_wholesale_actor_title_is_not_treated_as_anchorless(self):
        # 원천 API가 제목을 42자 부근에서 자르므로 꼬리의 '지원'을 신뢰할 수 없다.
        # 도매 시장 행위자(청과·공판장)가 앵커 역할을 해야 한다.
        # (다른 정책 게이트는 이 테스트의 관심사가 아니므로 anchorless 사유만 본다.)
        for title in (
            "“농가에 힘이 되겠습니다”…서울청과, 6개월간 2억4200만원 출하비 지...",
            "대아청과, 폭염 속 농산물 신선도 유지 총력",
            "농협 공판장 출하 물량 확대",
        ):
            a = _mk("policy", title, "가락시장 도매시장법인이 출하 기반을 뒷받침한다", score=40.4)
            self.assertNotEqual(
                main._preferred_tail_block_reason(a, "policy", current_count=4, raw_count=84),
                "policy_anchorless_preferred_tail",
                f"도매 행위자 제목이 앵커 없음으로 차단됨: {title}",
            )

    def test_market_intervention_title_is_not_treated_as_anchorless(self):
        for title in ("과잉 보리 2만5000톤 특별 매입", "채소 비축물량 2만t 방출", "쌀 공공비축 수매 확대"):
            a = _mk("policy", title, "산지가격 하락을 막기 위한 조치다", score=47.9)
            self.assertNotEqual(
                main._preferred_tail_block_reason(a, "policy", current_count=4, raw_count=84),
                "policy_anchorless_preferred_tail",
                f"시장개입 제목이 앵커 없음으로 차단됨: {title}",
            )

    def test_market_signal_vocabulary_has_no_scattered_copy(self):
        # 어휘 사본이 흩어지면 드리프트가 생긴다(기상 어휘 3사본 전례). lead는 base의 확장이어야 한다.
        for term in main._SUPPLY_MARKET_SIGNAL_TERMS:
            self.assertIn(term, main._SUPPLY_MARKET_LEAD_TERMS)


if __name__ == "__main__":
    unittest.main()
