"""Tests for event-level story dedup, section gates, soft-news core demotion,
and summary artifact sanitization (generalized algorithm improvements)."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
