"""편집 평가 wrong_section 카드의 섹션 이동(2026-10-01 후속).

10/1 복구 발송에서 '위상 높인 농산물 수급조절위 8기 닻 올려'가 supply wrong_section 으로 지목되며
"정책으로 이동하고 정책의 약한 홍보성 기사를 제외한다"는 지시가 붙었지만, 게이트는 절제(제거+재충원)만
할 줄 알아서 당일 최상위 정책 후보가 지면에서 사라졌다(missed_candidate major).

- suggested_action 의 이동 지시("~로 이동/보내/내리/돌리")에서 목적 섹션을 읽는다.
- 목적 섹션 게이트를 통과하고 같은 사건이 지면에 없으면 옮긴다. 꽉 찼으면 평가가 지목한 약한 카드,
  없으면 더 약한 비핵심 카드를 밀어낸다. 못 옮기면 major 는 기존처럼 절제, moderate 는 제자리.
- 원래 섹션 refill 은 옮긴 카드와 같은 사건을 다시 끌어오지 못한다.
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


def _mk(section, title, *, desc="", domain="example.com", is_core=False, score=10.0):
    link = f"https://{domain}/{section}/{abs(hash(title + domain)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description=desc,
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 9, 30, 16, 0, tzinfo=KST),
        domain=domain,
        press="테스트신문",
        norm_key=main.make_norm_key(link, "테스트신문", main.norm_title_key(title)),
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=score,
        is_core=is_core,
        selection_fit_score=2.0,
    )


def _issue(section, title, action, *, severity="major", issue_type="wrong_section"):
    return {"type": issue_type, "severity": severity, "section": section, "title": title,
            "reason": "섹션 부적합", "suggested_action": action}


class RelocationHintParsingTests(unittest.TestCase):
    def test_reads_destination_from_move_instructions(self):
        cases = [
            ("supply", "정책으로 이동하고 정책의 약한 홍보성 기사를 제외한다.", ["policy"]),
            ("policy", "dist로 이동하거나 제외.", ["dist"]),
            ("policy", "policy 대신 dist tail로 내리거나 제외.", ["dist"]),
            ("dist", "supply로 보내거나 가락시장 AI 후보로 교체.", ["supply"]),
            ("dist", "dist 대신 supply로 돌리거나 제외.", ["supply"]),
            ("policy", "공급면으로 이동하거나 정책 집행 기사로 교체한다.", ["supply"]),
            ("policy", "제외하거나 pest의 비핵심 꼬리 카드로 이동한다.", ["pest"]),
            ("policy", "수급으로 이동하거나 정책 후보로 교체한다.", ["supply"]),
            ("dist", "공급 또는 정책으로 이동하고 유통 카드에는 출하 기사를 넣는다.", ["policy", "supply"]),
            ("supply", "Move to policy section.", ["policy"]),
        ]
        for current, action, expected in cases:
            self.assertEqual(
                main._editorial_relocation_sections(_issue(current, "x", action), current), expected, action
            )

    def test_replace_or_drop_instructions_are_not_moves(self):
        for current, action in (
            ("policy", "제외하고 농산물 수급조절위원회 기사로 교체한다."),
            ("pest", "병해충 섹션에서 제외하고 화상병·탄저병 기사로 대체."),
            ("pest", "재해·생산 섹션으로 이동하거나 명시적 병해충 후보로 교체한다."),
            ("supply", "supply에서 제외하고 pest/기타 후보로만 검토하거나 삭제."),
            ("supply", "코어에서 내려야 한다."),
        ):
            self.assertEqual(main._editorial_relocation_sections(_issue(current, "x", action), current), [], action)


class _GateStateMixin:
    def setUp(self):
        main._GATE_EXCISED_LINK_KEYS.clear()
        main._GATE_EXCISED_ARTICLES.clear()
        main._GATE_EXCISION_KEEP_LINK_KEYS.clear()
        main._GATE_RELOCATED_OUT.clear()

    def tearDown(self):
        self.setUp()


def _sections():
    return {
        "supply": [
            _mk("supply", "사과 도매가 3주째 하락", is_core=True, score=30.0),
            _mk("supply", "배추 출하량 전년 대비 12% 감소", is_core=True, score=28.0),
            _mk("supply", "위상 높인 농산물 수급조절위 8기 닻 올려… 과수까지 품고 수급관리", score=26.0),
            _mk("supply", "양파 저장량 늘어 가격 약세", score=20.0),
            _mk("supply", "감귤 조생종 출하 시작", score=18.0),
        ],
        "policy": [
            _mk("policy", "농식품부, 농안법 시행령 개정안 입법예고", is_core=True, score=31.0),
            _mk("policy", "2025년도 면적당 농산물 소득 7.7% 줄었다", is_core=True, score=27.0),
            _mk("policy", "추석 농축산물 할인, 장바구니 너머 농가의 이야기도 들어보니", score=12.0),
            _mk("policy", "농업인 월급제 참여 농가 확대", score=19.0),
            _mk("policy", "스마트팜 청년 창업 지원 공모", score=15.0),
        ],
        "dist": [_mk("dist", f"유통 기사 {i}", domain=f"d{i}.com", is_core=i < 2, score=20.0 - i) for i in range(5)],
        "pest": [_mk("pest", f"병해충 기사 {i}", domain=f"b{i}.com", is_core=i < 2, score=20.0 - i) for i in range(5)],
    }


def _chain_patches(refill=None):
    def _recover(working, raw, max_items=5):
        if refill is not None:
            for section, article in refill:
                if not main._postbuild_article_reject_reason(article, section) and len(working[section]) < max_items:
                    working[section].append(article)
        return 0

    return (
        patch.object(main, "_recover_preferred_section_counts_from_raw", side_effect=_recover),
        patch.object(main, "_final_global_story_dedupe", return_value=(0, 0)),
        patch.object(main, "_cap_final_low_tier_sources", return_value=0),
        patch.object(main, "_ensure_final_selection_fit", return_value=0),
        patch.object(main, "_demote_soft_news_final_cores", return_value=0),
        patch.object(main, "fill_summaries", side_effect=lambda s, **kw: s),
        patch.object(main, "_finalize_sections_for_render", return_value=0),
        patch.object(main, "_fresh_section_fit", return_value=2.5),
    )


def _run(sections, editorial_issues, *, refill=None, reject=None):
    targets = main._editorial_excision_targets({"issues": editorial_issues}, sections)
    patches = list(_chain_patches(refill))
    if reject is not None:
        original = main._postbuild_article_reject_reason

        def _reject(article, section, *, apply_selection_fit=True):
            forced = reject(article, section)
            if forced is not None:
                return forced
            return original(article, section, apply_selection_fit=apply_selection_fit)

        patches.append(patch.object(main, "_postbuild_article_reject_reason", side_effect=_reject))
    for p in patches:
        p.start()
    try:
        result = main._excise_flagged_cards_and_refill(sections, {}, targets, {})
    finally:
        for p in reversed(patches):
            p.stop()
    return targets, result


def _titles(rows):
    return [a.title for a in rows]


class RelocationMechanicsTests(_GateStateMixin, unittest.TestCase):
    MOVED = "위상 높인 농산물 수급조절위 8기 닻 올려… 과수까지 품고 수급관리"
    PROMO = "추석 농축산물 할인, 장바구니 너머 농가의 이야기도 들어보니"

    def test_moves_into_full_section_displacing_flagged_weak_card(self):
        sections = _sections()
        issues = [
            _issue("supply", self.MOVED, "정책으로 이동하고 정책의 약한 홍보성 기사를 제외한다."),
            _issue("policy", self.PROMO, "정책 효과 기사로 교체", severity="moderate", issue_type="promotional_filler"),
        ]
        refill_card = _mk("supply", "복숭아 산지 가격 회복", score=17.0)
        targets, result = _run(sections, issues, refill=[("supply", refill_card)])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn(self.MOVED, _titles(result["policy"]))
        self.assertNotIn(self.PROMO, _titles(result["policy"]))
        self.assertNotIn(self.MOVED, _titles(result["supply"]))
        self.assertIn(refill_card.title, _titles(result["supply"]))
        moved = next(a for a in result["policy"] if a.title == self.MOVED)
        self.assertEqual(moved.section, "policy")
        self.assertEqual(moved.reassigned_from, "supply")
        self.assertEqual(targets[0]["relocation"], "moved")
        self.assertEqual(targets[0]["displaced_title"], self.PROMO)
        # 원본 선정은 건드리지 않는다
        self.assertIn(self.MOVED, _titles(sections["supply"]))
        # 옮긴 카드는 절제 목록에 오르지 않는다(정책 지면에서 막히면 안 됨)
        self.assertEqual(main._postbuild_article_reject_reason(moved, "policy", apply_selection_fit=False) != "editorial_issue_excised", True)

    def test_source_refill_cannot_bring_back_same_story(self):
        sections = _sections()
        issues = [_issue("supply", self.MOVED, "policy로 이동하고 공급에는 품목별 출하 기사를 배치한다.")]
        variant = _mk("supply", "농산물 수급조절위 8기 닻 올려…과수까지 품고 수급관리", domain="other.com", score=25.0)
        with patch.object(main, "_duplicate_story_pair_reason", side_effect=lambda a, b: (
            "same_story" if "수급조절위" in (a.title or "") and "수급조절위" in (b.title or "") else ""
        )):
            targets, result = _run(sections, issues, refill=[("supply", variant)])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(targets[0]["relocation"], "moved")
        self.assertNotIn(variant.title, _titles(result["supply"]))
        self.assertEqual(len(result["supply"]), 4)

    def test_major_wrong_section_falls_back_to_excision_when_destination_rejects(self):
        sections = _sections()
        issues = [_issue("supply", self.MOVED, "정책으로 이동한다.")]
        targets, result = _run(
            sections,
            issues,
            reject=lambda article, section: "policy_org_event_not_policy"
            if section == "policy" and "수급조절위" in (article.title or "") else None,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertNotIn(self.MOVED, _titles(result["policy"]))
        self.assertNotIn(self.MOVED, _titles(result["supply"]))
        self.assertIn("policy:policy_org_event_not_policy", targets[0]["relocation_rejections"])
        self.assertTrue(main._repair_article_link_keys(targets[0]["article"]) & main._GATE_EXCISED_LINK_KEYS)

    def test_moderate_relocation_stays_put_when_no_weaker_card(self):
        sections = _sections()
        for article in sections["policy"]:
            article.score = 99.0
        issues = [
            _issue("dist", "유통 기사 3", "제외하고 교체", severity="blocking", issue_type="off_topic"),
            _issue("supply", self.MOVED, "정책으로 이동한다.", severity="moderate"),
        ]
        targets, result = _run(sections, issues)
        self.assertIsNotNone(result)
        assert result is not None
        moved_target = next(t for t in targets if t["title"] == self.MOVED)
        self.assertEqual(moved_target["relocation"], "skipped")
        # 제자리(같은 순서)로 돌아오고 절제·이동 차단 목록에 오르지 않는다
        self.assertEqual(_titles(result["supply"]).index(self.MOVED), 2)
        self.assertFalse(main._repair_article_link_keys(moved_target["article"]) & main._GATE_EXCISED_LINK_KEYS)
        self.assertFalse(main._GATE_RELOCATED_OUT)
        self.assertNotIn("유통 기사 3", _titles(result["dist"]))

    def test_same_story_already_on_destination_is_excised_not_moved(self):
        sections = _sections()
        twin = _mk("policy", "농산물 수급조절위 8기 출범…과수 수급관리 확대", score=22.0)
        sections["policy"][4] = twin
        issues = [_issue("supply", self.MOVED, "정책으로 이동한다.")]
        with patch.object(main, "_duplicate_story_pair_reason", side_effect=lambda a, b: (
            "same_story" if "수급조절위" in (a.title or "") and "수급조절위" in (b.title or "") else ""
        )):
            targets, result = _run(sections, issues)
        self.assertEqual(targets[0]["relocation"], "failed_duplicate_on_page")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(_titles(result["policy"]).count(twin.title), 1)
        self.assertNotIn(self.MOVED, _titles(result["policy"]))

    def test_relocate_only_issues_do_not_open_a_round_alone(self):
        sections = _sections()
        moderate_only = [_issue("supply", self.MOVED, "정책으로 이동한다.", severity="moderate")]
        self.assertEqual(main._editorial_excision_targets({"issues": moderate_only}, sections), [])
        with_hard = moderate_only + [
            _issue("dist", "유통 기사 3", "제외하고 교체", severity="blocking", issue_type="off_topic"),
        ]
        targets = main._editorial_excision_targets({"issues": with_hard}, sections)
        self.assertEqual([t["title"] for t in targets], ["유통 기사 3", self.MOVED])
        self.assertTrue(targets[1]["relocate_only"])

    def test_kill_switch_restores_excision_only(self):
        sections = _sections()
        issues = [
            _issue("supply", self.MOVED, "정책으로 이동한다."),
            _issue("dist", "유통 기사 3", "supply로 이동", severity="moderate"),
        ]
        with patch.object(main, "PREPUBLISH_WRONG_SECTION_RELOCATION", False):
            targets = main._editorial_excision_targets({"issues": issues}, sections)
        self.assertEqual([t["title"] for t in targets], [self.MOVED])
        self.assertNotIn("relocate_to", targets[0])

    def test_carry_forward_drops_moved_and_displaced_issues_only(self):
        targets = [
            {"section": "supply", "title": self.MOVED, "relocation": "moved", "displaced_title": self.PROMO},
            {"section": "dist", "title": "유통 기사 3", "relocation": "skipped"},
        ]
        issues = [
            _issue("supply", self.MOVED, "정책으로 이동"),
            _issue("policy", self.PROMO, "교체", severity="moderate", issue_type="promotional_filler"),
            _issue("dist", "유통 기사 3", "supply로 이동", severity="moderate"),
        ]
        with patch("editorial_eval._apply_editorial_acceptance_gate", return_value=None):
            carried = main._editorial_result_without_excised({"issues": issues}, targets, {})
        self.assertEqual([i["title"] for i in carried["issues"]], ["유통 기사 3"])


class UnverifiedRepairRegressionGuardTests(unittest.TestCase):
    """10/1 end-to-end replay: 검증 88.9 상태 → 미검증 교체안(호출 상한) → 최종 80.7 발행."""

    def _verified(self, operational, blockers=()):
        return {"editorial": {"status": "success"}, "operational_score": operational, "_blockers": list(blockers)}

    def test_reverts_only_when_verified_state_was_publishable_and_better(self):
        with patch.object(main, "_prepublish_sla_fallback_blockers", side_effect=lambda r: r.get("_blockers", [])):
            self.assertTrue(main._unverified_repair_regresses(self._verified(93.45), {"operational_score": 89.1}))
            self.assertFalse(main._unverified_repair_regresses(self._verified(89.0), {"operational_score": 89.1}))
            # 직전 상태가 발행 불가(hard issue)면 교체안이 유일한 출구일 수 있다
            self.assertFalse(main._unverified_repair_regresses(
                self._verified(93.45, ["editorial_hard_issues:1"]), {"operational_score": 80.0}
            ))
            # 직전 상태도 모델 검증을 못 받았으면 비교하지 않는다
            self.assertFalse(main._unverified_repair_regresses(
                {"editorial": {"status": "skipped"}, "operational_score": 95.0}, {"operational_score": 80.0}
            ))


if __name__ == "__main__":
    unittest.main()
