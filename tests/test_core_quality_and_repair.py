"""P2·P3: 코어 슬롯을 하드뉴스가 차지하는지, 발행 직전 교체안이 한 장 때문에
통째로 버려지지 않는지 검증한다.

배경(2026-08 주간 편집 평가):
- 코어로 올라온 약체 카드가 반복됐다 — 의회 건의문, 공사장 안전 논란, 지자체
  현장 방문 동정, 일회성 설명회, 지역 첫 출하. core_pick_quality 는 6개 항목
  중 최저(56~62)였다.
- 08-14 에는 정책 섹션 저티어 한 건 때문에 네 섹션 교체안이 통째로 기각돼
  병해충 중복 제거와 유통 코어 교체까지 함께 사라졌다.
"""
import unittest
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main  # noqa: E402


def _article(section: str, title: str, desc: str, url: str, press: str = "연합뉴스") -> main.Article:
    canon = main.canonicalize_url(url)
    title_key = main.norm_title_key(title)
    return main.Article(
        section=section,
        title=title,
        description=desc,
        link=url,
        originallink=url,
        pub_dt_kst=datetime.now(main.KST),
        domain=main.domain_of(url),
        press=press,
        norm_key=main.make_norm_key(canon, press, title_key),
        title_key=title_key,
        canon_url=canon,
        topic="",
        score=20.0,
    )


class CorePromotionQualityTests(unittest.TestCase):
    """편집 평가가 약한 코어로 지적한 패턴은 tail 로만 남아야 한다."""

    WEAK_CORES = (
        ("policy", "영양군의회, 고추재배농가 생존권 보장 건의문 등 채택",
         "영양군의회가 고추 재배농가 생존권 보장을 촉구하는 건의문을 채택했다."),
        ("policy", "농식품부·aT, 동남아 수출 설명회 열고 할랄·식품안전 규제 대응법 짚어",
         "농식품부와 aT가 동남아 수출 설명회를 열어 할랄 인증 대응법을 설명했다."),
        ("dist", "안전시설 미흡 논란… 89억 원대 영주 과수거점 APC 공사 현장 '주의'",
         "영주 과수거점 APC 공사 현장에서 안전시설 미흡 논란이 제기됐다."),
        ("dist", "철원군, 가락동 도매 현장 방문해 농가 소득향상 노력",
         "철원군수가 가락동 도매시장을 방문해 출하 농가를 격려했다."),
        ("supply", "상주 경천대 캠벨얼리 포도 '첫 출하'",
         "상주 경천대 작목반이 캠벨얼리 포도 첫 출하 행사를 열었다."),
    )

    HARD_CORES = (
        ("dist", "가락시장 폭염 대응 경매 시간 앞당긴다…출하 물량 신선도 확보",
         "가락시장이 폭염에 대응해 경매 개시 시간을 앞당기고 반입 물량 신선도 관리를 강화한다."),
        ("policy", "정부, 농축산물 할인에 3천억 투입…농할상품권 매월 200억 발행",
         "농식품부가 여름철 농축산물 할인 지원에 3000억원을 투입하는 대책을 시행한다."),
        ("supply", "제주 감귤 첫 출하…초매식서 5㎏ 상자 최고가 12만원",
         "제주 노지감귤 첫 출하 초매식에서 5kg 상자가 최고가 12만원에 거래됐다."),
    )

    def test_weak_core_patterns_are_demoted(self) -> None:
        for section, title, desc in self.WEAK_CORES:
            with self.subTest(title=title):
                article = _article(section, title, desc, "https://example.com/weak")
                article.is_core = True
                self.assertTrue(
                    main._soft_news_core_demote_reason(article),
                    msg=f"{title} 가 코어로 남는다",
                )

    def test_hard_news_keeps_its_core_slot(self) -> None:
        for section, title, desc in self.HARD_CORES:
            with self.subTest(title=title):
                article = _article(section, title, desc, "https://example.com/hard")
                article.is_core = True
                self.assertEqual(main._soft_news_core_demote_reason(article), "")

    def test_publish_time_gate_demotes_the_weak_core(self) -> None:
        weak = _article(
            "dist",
            "철원군, 가락동 도매 현장 방문해 농가 소득향상 노력",
            "철원군수가 가락동 도매시장을 방문해 출하 농가를 격려했다.",
            "https://example.com/visit",
        )
        weak.is_core = True
        strong = _article(
            "dist",
            "가락시장 폭염 대응 경매 시간 앞당긴다…출하 물량 신선도 확보",
            "가락시장이 폭염에 대응해 경매 개시 시간을 앞당기고 반입 물량 신선도 관리를 강화한다.",
            "https://example.com/ops",
        )
        final_by_section = {"supply": [], "policy": [], "dist": [weak, strong], "pest": []}
        main._demote_soft_news_final_cores(final_by_section, {"dist": []})
        self.assertFalse(weak.is_core)


class PartialRepairTests(unittest.TestCase):
    """한 섹션이 검증에 걸려도 나머지 섹션 개선은 살아남아야 한다."""

    SECTION_FIXTURES = {
        "supply": (
            "배추 도매가격 {i}% 상승…출하 물량 12만톤 감소",
            "여름배추 출하 물량이 줄면서 도매가격이 전년 대비 {i}% 올랐다.",
        ),
        "policy": (
            "농식품부, 수급 안정에 {i}00억 투입…비축 물량 방출 확대",
            "농식품부가 농산물 수급 안정을 위해 {i}00억원을 투입하고 비축 물량을 방출한다.",
        ),
        "dist": (
            "가락시장 하역 운영 조정 {i}…물류 차질 최소화",
            "가락시장이 하역 인력과 물류 운영을 조정해 출하 차질을 줄인다.",
        ),
        "pest": (
            "고추 탄저병 확산 우려…{i}개 시군 긴급 방제",
            "고추 재배지에서 탄저병 발생이 늘어 시군별 긴급 방제와 예찰을 강화한다.",
        ),
    }

    def _raw_pool(self) -> dict[str, list[main.Article]]:
        raw: dict[str, list[main.Article]] = {}
        for section in main._section_keys():
            title_tpl, desc_tpl = self.SECTION_FIXTURES[section]
            raw[section] = [
                _article(
                    section,
                    title_tpl.format(i=idx + 1),
                    desc_tpl.format(i=idx + 1),
                    f"https://www.yna.co.kr/{section}/{idx}",
                )
                for idx in range(main.MAX_PER_SECTION + 2)
            ]
        return raw

    def _repair_payload(self, raw, *, broken_section: str) -> dict:
        sections = {}
        for section in main._section_keys():
            pool = raw[section]
            if section == broken_section:
                rows = [{"link": "https://example.com/not-in-pool", "is_core": False}]
                rows += [{"link": a.link, "is_core": i < 2} for i, a in enumerate(pool[: main.MAX_PER_SECTION - 1])]
            else:
                rows = [{"link": a.link, "is_core": i < 2} for i, a in enumerate(pool[: main.MAX_PER_SECTION])]
            sections[section] = rows
        return {"sections": sections}

    def test_one_bad_card_no_longer_discards_every_section(self) -> None:
        raw = self._raw_pool()
        current = {section: list(raw[section][: main.MAX_PER_SECTION]) for section in main._section_keys()}
        payload = self._repair_payload(raw, broken_section="policy")

        errors: list[dict] = []
        legacy = main._apply_model_editorial_repair(payload, raw, validation_errors=list(errors))
        self.assertIsNone(legacy, msg="예전 동작(전량 기각)이 유지돼야 비교가 성립한다")

        accepted = main._apply_model_editorial_repair(
            payload,
            raw,
            validation_errors=errors,
            current_by_section=current,
        )
        self.assertIsNotNone(accepted)
        assert accepted is not None
        self.assertNotIn("policy", accepted)
        for section in main._section_keys():
            if section == "policy":
                continue
            with self.subTest(section=section):
                self.assertIn(section, set(accepted), msg=f"accepted={sorted(accepted)}")
                self.assertEqual(len(accepted[section]), main.MAX_PER_SECTION)
        self.assertTrue(any(str(e.get("reason")) == "link_not_in_raw_pool" for e in errors))

    def test_partial_repair_still_reports_nothing_when_every_section_fails(self) -> None:
        raw = self._raw_pool()
        current = {section: list(raw[section][: main.MAX_PER_SECTION]) for section in main._section_keys()}
        payload = {"sections": {section: [] for section in main._section_keys()}}
        accepted = main._apply_model_editorial_repair(
            payload,
            raw,
            validation_errors=[],
            current_by_section=current,
        )
        self.assertIsNone(accepted)


if __name__ == "__main__":
    unittest.main()
