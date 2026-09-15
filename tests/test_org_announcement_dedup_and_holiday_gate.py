"""2026-09-16 발행 차단 재발 방지: 같은 기관 발표의 매체별 변형 중복, 지자체 명절 종합대책 노이즈."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main

KST = timezone(timedelta(hours=9))


def _mk(title, desc="", section="dist", domain="news.example.com", hours=0):
    link = f"https://{domain}/{abs(hash(title)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description=desc,
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 9, 15, 18, 0, tzinfo=KST) + timedelta(hours=hours),
        domain=domain,
        press="언론사",
        norm_key=main.make_norm_key(link, "언론사", main.norm_title_key(title)),
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=10.0,
    )


class TestSameOrgAnnouncementDedup(unittest.TestCase):
    def test_nh_regional_aliases_collapse_to_one_key(self):
        self.assertEqual(main._org_subject_keys("인천농협"), frozenset({"농협:인천"}))
        self.assertEqual(main._org_subject_keys("농협 인천본부"), frozenset({"농협:인천"}))
        self.assertEqual(main._org_subject_keys("인천원예농협·농협 인천본부"), frozenset({"농협:인천"}))
        self.assertEqual(main._org_subject_keys("NHN KCP"), frozenset({"nhn kcp".replace(" ", "")}))

    def test_government_subjects_are_out_of_scope(self):
        for subject in ("농식품부", "대구 동구", "진천군", "경북도", "진천군농업기술센터", "한성숙 총리"):
            self.assertEqual(main._org_subject_keys(subject), frozenset(), subject)

    def test_incheon_inspection_variants_are_one_story(self):
        a = _mk("인천농협, 추석 명절 농산물 수급 상황 점검", domain="nongmin.com")
        b = _mk("농협 인천본부, 추석 앞두고 사과·배·무·배추 수급 점검", domain="shinailbo.co.kr")
        c = _mk(
            "인천원예농협·농협 인천본부, 추석 맞아 남촌 농산물 도매시장 현장 점검",
            "이기용 인천원예농협 조합장과 한상구 농협인천본부장은 지난 14일 남촌농산물도매시장을 찾아 "
            "주요 성수품의 가격 동향과 공급 상황을 정밀 점검하고 현장 유통 종사자들을 격려했다.",
            domain="wonyesanup.co.kr",
        )
        b.description = (
            "농협중앙회 인천본부가 추석을 앞두고 사과와 배, 무, 배추 등 주요 성수품의 공급 상황과 가격 동향을 점검했다. "
            "본부는 지난 14일 남촌농산물도매시장 내 인천원예농협 남촌공판장을 방문해 추석 명절 농산물 수급 상황을 살폈다고 밝혔다."
        )
        self.assertEqual(main._same_org_announcement_reason(a, b), "same_org_announcement")
        self.assertEqual(main._duplicate_story_pair_reason(a, b), "same_org_announcement")
        self.assertIn(main._duplicate_story_pair_reason(b, c), ("same_org_announcement", "same_org_announcement_lead"))

    def test_corporate_press_release_variants_are_one_story(self):
        a = _mk("농산물 경매대금도 카드로…NHN KCP, B2B 결제 확대", domain="etnews.com")
        b = _mk("NHN KCP, 농산물 도매시장에 경매 카드결제 인프라 구축", domain="newsis.com")
        c = _mk("NHN KCP, 농산물 경매 대금 카드결제 도입…중도매인 최장 30일 확보", domain="g-enews.com")
        # 제목 앞머리가 기관명이 아닌 변형(etnews)은 이 규칙 대상이 아니다 — 기존 규칙에 맡긴다
        self.assertEqual(main._same_org_announcement_reason(a, b), "")
        self.assertEqual(main._duplicate_story_pair_reason(b, c), "same_org_announcement")

    def test_same_org_different_events_stay_separate(self):
        a = _mk("농협, 추석 농축산물 할인행사…\"장바구니 부담 낮춘다\"")
        b = _mk("농협경제지주, 농축산물 수급 안정 점검")
        self.assertEqual(main._same_org_announcement_reason(a, b), "")
        c = _mk("이마트, 추석 선물세트 사전예약 매출 10% 증가")
        d = _mk("이마트, 무화과 요거트 케이크 출시")
        self.assertEqual(main._same_org_announcement_reason(c, d), "")

    def test_far_apart_publications_are_not_merged(self):
        a = _mk("NHN KCP, 농산물 도매시장에 경매 카드결제 인프라 구축")
        b = _mk("NHN KCP, 농산물 경매 대금 카드결제 도입…중도매인 최장 30일 확보", hours=72)
        self.assertEqual(main._same_org_announcement_reason(a, b), "")


class TestLeadAndTitleBackstops(unittest.TestCase):
    AFL_LEAD = (
        "[농수축산신문=김진오 기자]서울시농수산식품공사(사장 문영표)는 서울 가락동 농수산물도매시장의 시설현대화사업 "
        "단계별 추진과 연계한 파렛트 중심 물류체계를 넓히고자 다음 달 1일부터 느타리버섯과 봄동배추, 11월 1일부터 "
        "제주당근의 파렛트 출하 의무화를 시행한다고 지난 11일 밝혔다.파렛트 출하 확대는 농림축산식품부의 2023년 "
        "‘농산물 유통구조 선진화 방안’에 포함된 계획이다."
    )
    WONYE_LEAD = (
        "서울특별시농수산식품공사(사장 문영표)는 가락시장 시설현대화사업 단계별 추진과 연계하여 파렛트 중심 물류체계 "
        "확대를 위해 오는 10월 1일부터 느타리버섯과 봄동배추, 11월 1일부터 제주당근에 대해 파렛트 출하 의무화를 "
        "시행한다고 밝혔다.가락시장 파렛트 출하 확대는 농림축산식품부의 ‘23년 ‘농산물 유통구조 선진화 방안’에도 포함된 계획이다."
    )

    def test_truncated_lead_variant_is_caught_by_title_containment(self):
        a = _mk("느타리·봄동·제주당근까지…가락시장 파렛트 의무출하 가속", self.AFL_LEAD, section="supply", domain="aflnews.co.kr")
        b = _mk("봄동·당근 파렛트 출하 의무화",
                "[한국농어민신문 이두현 기자] 올해 연말부터 느타리버섯, 봄동배추, 제주당근 등의 가락동 농수산물도매시장 파렛트 출하가 의무화된다.",
                section="supply", domain="agrinet.co.kr")
        self.assertEqual(main._same_title_containment_reason(a, b), "same_title_containment")
        self.assertNotEqual(main._duplicate_story_pair_reason(a, b), "")

    def test_rewritten_press_release_lead_is_caught(self):
        a = _mk("느타리·봄동·제주당근까지…가락시장 파렛트 의무출하 가속", self.AFL_LEAD, domain="aflnews.co.kr")
        b = _mk("가락시장, 파렛트 중심 물류체계 전환 가속화", self.WONYE_LEAD, domain="wonyesanup.co.kr")
        self.assertEqual(main._same_lead_text_reason(a, b), "same_lead_text")
        # 같은 매체끼리는 템플릿 문구 오탐 위험이 있어 리드 규칙을 적용하지 않는다
        c = _mk("가락시장, 파렛트 중심 물류체계 전환 가속화", self.WONYE_LEAD, domain="aflnews.co.kr")
        self.assertEqual(main._same_lead_text_reason(a, c), "")

    def test_short_or_generic_titles_are_not_merged(self):
        a = _mk("추석 성수품 공급 확대")
        b = _mk("정부, 추석 성수품 공급 확대…할인지원 1490억원")
        self.assertEqual(main._same_title_containment_reason(a, b), "")
        c = _mk("사과 가격 하락세 지속", "사과 도매가격이 3주째 내렸다.")
        d = _mk("배 가격 하락세 지속…추석 수요 둔화", "배 도매가격이 내렸다.")
        self.assertEqual(main._same_title_containment_reason(c, d), "")


class TestMunicipalHolidayOmnibusGate(unittest.TestCase):
    DAEGU_LEAD = (
        "[사진=대구 동구] 대구 동구청(구청장 우성진)은 28일까지 귀성·귀경객과 구민 모두가 안전하고 편안한 "
        "추석 연휴를 보낼 수 있도록 ‘추석맞이 종합대책’을 수립하고, 연휴 전후로 분야별 대책을 집중 추진한다. "
        "이번 종합대책은 ▲구민 생활 안정 ▲구민 안전 확보 ▲따뜻한 명절 분위기 조성 ▲생활편의 증진 ▲공직기강 확립 등"
    )

    def test_municipal_omnibus_plan_is_rejected_in_policy(self):
        title = "대구 동구, 추석맞이 종합 대책 추진"
        self.assertTrue(main.is_municipal_holiday_omnibus_plan_context(title, self.DAEGU_LEAD))
        article = _mk(title, self.DAEGU_LEAD, section="policy", domain="sentv.co.kr")
        self.assertEqual(main._postbuild_article_reject_reason(article, "policy"), "municipal_holiday_omnibus_plan")
        self.assertTrue(main._is_policy_reader_filler(article))
        self.assertNotEqual(main._postbuild_article_reject_reason(article, "pest"), "municipal_holiday_omnibus_plan")

    def test_agri_anchored_holiday_plans_are_kept(self):
        self.assertFalse(main.is_municipal_holiday_omnibus_plan_context(
            "정부, 추석 성수품 수급안정 대책 추진", "농식품부는 사과·배 공급을 평시 대비 1.6배로 확대한다."))
        self.assertFalse(main.is_municipal_holiday_omnibus_plan_context(
            "제주시, 추석 농산물 물가안정 종합대책 추진", "제주시는 성수품 15개 품목의 가격 동향을 점검한다."))
        self.assertFalse(main.is_municipal_holiday_omnibus_plan_context(
            "용인시, 추석 연휴 종합대책 추진", "용인시는 성수품 공급 확대와 농산물 직거래장터를 운영한다."))
        self.assertFalse(main.is_municipal_holiday_omnibus_plan_context(
            "가락시장, 추석 성수기 교통소통 특별대책 시행", "서울시농수산식품공사는 반입 차량 동선을 조정한다."))
        self.assertFalse(main.is_municipal_holiday_omnibus_plan_context(
            "진주시, ‘추석맞이 농축산 종합대책’ 추진", "진주시는 유통부터 영농까지 분야별 대책을 마련했다."))


if __name__ == "__main__":
    unittest.main()
