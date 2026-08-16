"""P5·P6: 품목 별칭이 선정과 평가에서 어긋나지 않는지, 같은 기관 보도자료를
재가공한 기사가 한 건으로 묶이는지 검증한다.

배경(2026-08 주간):
- 08-11 화훼 대표기사("고온기 견디는 장미 20계통 품평회")가 '품목명 없음'으로
  걸려 독자품질이 84로 캡됐다. 선정 레지스트리는 장미를 화훼 별칭으로 알고
  있었지만 평가기의 별칭 표에는 없었다.
- 08-14 농진청 참깨 방제 보도자료가 두 장으로 실렸는데, 제목 유사도 기반
  dedup 은 재가공 기사를 잡지 못했다.
"""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import report_eval  # noqa: E402
import story_dedup  # noqa: E402


class CommodityAliasSyncTests(unittest.TestCase):
    """선정이 아는 품목 별칭은 평가도 알아야 한다."""

    def test_every_registry_alias_is_recognised_by_the_judge(self) -> None:
        import main

        drift: list[str] = []
        for entry in main.COMMODITY_REGISTRY:
            label = str(entry.get("display_name") or entry.get("topic") or "").strip()
            if not label:
                continue
            for alias in entry.get("aliases") or []:
                if not report_eval._commodity_item_focus_from_text(label, str(alias)):
                    drift.append(f"{label}<-{alias}")
        self.assertEqual(drift, [], msg=f"평가기가 모르는 별칭: {drift}")

    def test_flower_species_count_as_the_flower_item(self) -> None:
        for title in (
            "고온기 견디는 장미 20계통 품평회 개최",
            "국화 경매가 약세…추석 성수기 앞두고 물량 증가",
            "백합 출하 확대",
        ):
            with self.subTest(title=title):
                self.assertTrue(report_eval._commodity_item_focus_from_text("화훼", title))

    def test_unrelated_item_does_not_match(self) -> None:
        self.assertFalse(report_eval._commodity_item_focus_from_text("화훼", "배추 도매가격 상승"))
        self.assertFalse(report_eval._commodity_item_focus_from_text("사과", "배 출하량 감소"))


class AgencyPressReleaseDedupTests(unittest.TestCase):
    """같은 기관·작물·조치는 매체가 달라도 한 건의 소식이다."""

    SESAME_A = (
        "참깨 수확 앞두고 병해충 확산 우려…“발생 초기에 방제 해야”",
        "8~9월 고온·잦은 비로 발생 우려가 커 농촌진흥청은 참깨 주요 병해충 관리법을 안내했다. "
        "참깨에 발생한 세균점무늬병 사진과 함께 초기 방제를 강조했다.",
    )
    SESAME_B = (
        "농진청, 참깨 수확 앞두고 병해충 적기 방제 당부",
        "농촌진흥청이 참깨 수확기를 앞두고 세균점무늬병과 잎마름병, 왕담배나방, 노린재류 등 "
        "주요 병해충의 발생 여부를 미리 살펴 적기에 방제해 달라고 당부했다.",
    )

    def test_reworked_press_release_is_one_event(self) -> None:
        self.assertEqual(
            story_dedup.duplicate_event_reason(*self.SESAME_A, *self.SESAME_B),
            "same_agency_advisory",
        )

    def test_multi_pest_release_is_not_split_by_which_disease_the_body_lists(self) -> None:
        """보도자료가 여러 병해충을 다루면 매체마다 언급 순서가 달라진다."""
        left = story_dedup.canonical_event_fingerprint(*self.SESAME_A)
        right = story_dedup.canonical_event_fingerprint(*self.SESAME_B)
        self.assertTrue(left)
        self.assertEqual(left, right)

    def test_different_crops_stay_separate(self) -> None:
        other = (
            "농진청, 고추 탄저병 적기 방제 당부",
            "농촌진흥청이 고추 탄저병 방제를 당부했다.",
        )
        self.assertEqual(story_dedup.duplicate_event_reason(*self.SESAME_B, *other), "")

    def test_different_agencies_stay_separate(self) -> None:
        other = (
            "전남농업기술원, 참깨 병해충 적기 방제 당부",
            "전남도농업기술원이 참깨 병해충 적기 방제를 당부했다.",
        )
        self.assertEqual(story_dedup.duplicate_event_reason(*self.SESAME_B, *other), "")

    def test_named_pest_in_the_title_keeps_advisories_apart(self) -> None:
        anthracnose = (
            "농진청, 고추 탄저병 방제 당부",
            "농촌진흥청이 고추 탄저병 적기 방제를 당부했다.",
        )
        mite = (
            "농진청, 고추 응애 방제 당부",
            "농촌진흥청이 고추 응애 적기 방제를 당부했다.",
        )
        self.assertEqual(story_dedup.duplicate_event_reason(*anthracnose, *mite), "")

    def test_agency_name_alone_is_not_enough_to_merge(self) -> None:
        left = (
            "농진청, 스마트농업 연구성과 발표",
            "농촌진흥청이 스마트농업 연구성과를 발표했다.",
        )
        right = (
            "농진청, 청년농 지원 사업 공고",
            "농촌진흥청이 청년농 지원 사업을 공고했다.",
        )
        self.assertEqual(story_dedup.canonical_event_fingerprint(*left), ())
        self.assertEqual(story_dedup.duplicate_event_reason(*left, *right), "")


if __name__ == "__main__":
    unittest.main()
