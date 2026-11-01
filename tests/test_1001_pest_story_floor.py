"""2026-10-01 미발송 재발 방지.

06:05·06:20 두 런이 `section_underfill:pest=2/4`, `2/3`으로 차단됐다. pest 유효 후보 5건이
사건 2건(가평 돌발해충 2판·담양 딸기 스마트팜 3판)뿐인데 게이트가 매체별 판을 따로 세어
최소 3~4장을 요구했다. 첫 런은 pest 부족이 정책 off_topic(KTL 원장 취임) 절제까지 되돌려
blocking 이슈도 남았다.

- 유효 후보 수(achievable)는 같은 사건을 한 건으로 센다.
- 절제와 무관한 섹션이 원래부터 하한 아래여도 다른 섹션 절제를 되돌리지 않는다.
- 농업 맥락 없는 기관장 취임 기사는 정책 섹션에서 결정적으로 뺀다.
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

KST = timezone(timedelta(hours=9))


def _mk(section, title, *, desc="", press="테스트신문", domain="example.com", is_core=False):
    link = f"https://{domain}/{section}/{abs(hash(title + domain)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description=desc,
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 9, 30, 16, 0, tzinfo=KST),
        domain=domain,
        press=press,
        norm_key=main.make_norm_key(link, press, main.norm_title_key(title)),
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=10.0,
        is_core=is_core,
        selection_fit_score=2.0,
    )


class AchievableCountsCollapseSameStoryTests(unittest.TestCase):
    def test_same_story_variants_count_once(self):
        gapyeong_a = _mk("pest", "가평군, 돌발해충 확산 차단 총력", press="농민신문", domain="nongmin.com")
        gapyeong_b = _mk("pest", "가평군, 돌발해충 확산 차단 위한 공동방제 강화", press="전국매일신문", domain="jeonmae.co.kr")
        damyang_a = _mk("pest", "담양군, 국립농업과학원과 딸기 스마트팜 현장 점검", press="농수축산신문", domain="aflnews.co.kr")
        damyang_b = _mk("pest", "담양군, 국립농업과학원과 딸기 스마트팜 현장 점검", press="전남매일", domain="jndn.com")
        raw = {"pest": [gapyeong_a, damyang_a, damyang_b, gapyeong_b], "supply": [], "policy": [], "dist": []}
        with patch.object(main, "_postbuild_article_reject_reason", return_value=""):
            counts = main._section_achievable_counts(raw, None)
        self.assertEqual(counts["pest"], 2)
        # 최소치: 강제 복구 3장·SLA 4장 → 사건 수 2장
        result = {"counts": {"achievable_briefing_by_section": counts}}
        self.assertEqual(main._prepublish_section_minimums(result, 3)["pest"], 2)
        self.assertEqual(main._prepublish_section_minimums(result, 4)["pest"], 2)

    def test_healthy_section_keeps_unique_card_count(self):
        items = [_mk("supply", f"품목{i} 도매가격 {i}주째 하락", domain=f"n{i}.com") for i in range(8)]
        raw = {"supply": items, "policy": [], "dist": [], "pest": []}
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "_duplicate_story_pair_reason", return_value=""),
        ):
            counts = main._section_achievable_counts(raw, None)
        self.assertEqual(counts["supply"], 8)


class ExcisionNotVetoedByUntouchedThinSectionTests(unittest.TestCase):
    def setUp(self):
        main._GATE_EXCISED_LINK_KEYS.clear()
        main._GATE_EXCISED_ARTICLES.clear()
        main._GATE_EXCISION_KEEP_LINK_KEYS.clear()

    tearDown = setUp

    def _sections(self):
        return {
            "supply": [_mk("supply", f"공급 기사 {i}", domain=f"s{i}.com", is_core=i < 2) for i in range(5)],
            "policy": [_mk("policy", f"정책 기사 {i}", domain=f"p{i}.com", is_core=i < 2) for i in range(5)],
            "dist": [_mk("dist", f"유통 기사 {i}", domain=f"d{i}.com", is_core=i < 2) for i in range(5)],
            "pest": [_mk("pest", f"병해충 기사 {i}", domain=f"b{i}.com", is_core=i < 1) for i in range(2)],
        }

    def _excise(self, sections, targets, achievable, *, drop_pest=False):
        def _dedupe(working, raw, max_passes=3):
            if drop_pest:
                working["pest"] = working["pest"][:1]
            return (0, 0)

        with (
            patch.object(main, "_recover_preferred_section_counts_from_raw", return_value=0),
            patch.object(main, "_final_global_story_dedupe", side_effect=_dedupe),
            patch.object(main, "_cap_final_low_tier_sources", return_value=0),
            patch.object(main, "_ensure_final_selection_fit", return_value=0),
            patch.object(main, "_demote_soft_news_final_cores", return_value=0),
            patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
            patch.object(main, "_finalize_sections_for_render", return_value=0),
        ):
            return main._excise_flagged_cards_and_refill(
                sections, {}, targets, {}, achievable_by_section=achievable
            )

    def test_policy_excision_applies_when_pest_was_already_short(self):
        sections = self._sections()
        victim = sections["policy"][4]
        targets = [{"section": "policy", "article": victim, "title": victim.title, "link": victim.link}]
        # achievable 이 옛 계산처럼 과대(5)여도 pest 는 절제와 무관하므로 절제를 막지 않는다
        excised = self._excise(sections, targets, {"supply": 50, "policy": 50, "dist": 50, "pest": 5})
        self.assertIsNotNone(excised)
        assert excised is not None
        self.assertNotIn(victim, excised["policy"])
        self.assertEqual(len(excised["pest"]), 2)

    def test_untouched_section_that_shrinks_still_rejects(self):
        sections = self._sections()
        victim = sections["policy"][4]
        targets = [{"section": "policy", "article": victim, "title": victim.title, "link": victim.link}]
        self.assertIsNone(
            self._excise(sections, targets, {"supply": 50, "policy": 50, "dist": 50, "pest": 5}, drop_pest=True)
        )


class NonAgriOrgHeadInaugurationTests(unittest.TestCase):
    def test_ktl_head_inauguration_is_rejected_in_policy(self):
        title = "김선기 KTL 원장 취임…첨단 산업 시험인증·기업 수출 지원 강화"
        desc = (
            "정부의 '5극 3특' 정책과 연계한 지역 특화 산업 발전을 뒷받침하고, AI 기반 스마트 경영체계 "
            "구축도 추진한다. 강원 횡성군 출신인 김 원장은 고려대 사회학과를 졸업하고"
        )
        self.assertTrue(main.is_non_agri_org_head_inauguration_context(title, desc))
        article = _mk("policy", title, desc=desc, press="knpnews", domain="knpnews.com")
        self.assertEqual(
            main._postbuild_article_reject_reason(article, "policy"), "policy_non_agri_org_head_inauguration"
        )

    def test_agri_org_inauguration_is_kept(self):
        for title, desc in (
            ("홍문표 aT 사장 취임…농산물 수급 안정 최우선", ""),
            ("신임 농촌진흥청장 취임", "현장 중심 기술 보급을 강조했다."),
            ("○○원예농협 조합장 취임", "산지 유통 혁신을 약속했다."),
            ("김 원장 취임", "과수 농가 경영 안정을 위한 지원을 확대하겠다고 밝혔다."),
        ):
            self.assertFalse(main.is_non_agri_org_head_inauguration_context(title, desc), title)


class RepairTargetCappedByAchievableTests(unittest.TestCase):
    """복구 런: 장학금 카드를 뺀 교체안 1회차가 pest(사건 2건) 목표 4장 미달로 통째 기각됐다."""

    def test_thin_section_target_follows_story_count(self):
        targets = main._cap_repair_targets_by_achievable(
            {"supply": 5, "policy": 5, "dist": 5, "pest": 4},
            {"supply": 183, "policy": 56, "dist": 22, "pest": 2},
        )
        self.assertEqual(targets, {"supply": 5, "policy": 5, "dist": 5, "pest": 2})
        self.assertEqual(main._repair_section_target(targets, "pest"), 2)
        self.assertEqual(main._repair_section_target(targets, "supply"), 5)
        self.assertEqual(main._repair_section_target({}, "dist"), main.MAX_PER_SECTION)
        self.assertEqual(main._repair_section_target({"pest": 0}, "pest"), 0)


class CoopScholarshipRecruitmentNoticeTests(unittest.TestCase):
    """복구 런: 유통 지면 절제 → 재충원이 같은 부류(조합 장학금·채용) 카드를 다시 끌어와 blocking."""

    def test_scholarship_and_hiring_notices_are_rejected(self):
        scholarship = _mk(
            "dist",
            "성주농협, 조합원 대학생 자녀 장학금 전달",
            desc="지난 21일 성주농협은 농산물산지유통 센터 2층 회의실에서 임직원과 학부모 등 40여명이 참석한 가운데",
        )
        hiring = _mk("dist", "충북 농협 , 지역 농축협 하반기 신규 직원 동시 채용", desc="채용 직렬은 교육·신용·경제사업 일반관리직")
        for article in (scholarship, hiring):
            self.assertEqual(
                main._postbuild_article_reject_reason(article, "dist"), "coop_scholarship_or_recruitment_notice"
            )
        self.assertTrue(main.is_coop_scholarship_or_recruitment_notice_context("농협 , 하반기 농축협 신규직원 867명 공개채용", ""))

    def test_farm_labor_hiring_is_kept(self):
        for title in (
            "영암군, 외국인 계절근로자 120명 채용…농번기 일손 해소",
            "농협, 영농 인력 채용 지원 확대",
            "사과 도매가 3주째 하락…추석 수요 둔화",
        ):
            self.assertFalse(main.is_coop_scholarship_or_recruitment_notice_context(title, ""), title)


if __name__ == "__main__":
    unittest.main()
