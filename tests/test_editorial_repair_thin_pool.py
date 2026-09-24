"""2026-09-22 과제 1 회귀 방지: 편집 교체안이 얇은 pest 섹션에서 구조적으로 기각되던 결함.

- 검증기(_apply_model_editorial_repair)의 저티어 상한에 결정적 체인(_cap_final_low_tier_sources)의
  pest 예외(보호 카드가 있으면 cap+1)가 없어 두 기준이 어긋났다.
- raw 풀이 티어1 4/8인 날은 "티어1 1장 이하이면서 5장"이 불가능한데 검증기가 정확히 5장을
  요구해 모델이 다섯 번 제안하고 다섯 번 기각됐다. 섹션별 목표 행 수를 계산해 낮추고
  (_editorial_repair_section_targets), 프롬프트·스키마·검증·finalize 검사가 같은 목표를 쓴다.
- 결정적 체인이 다른 섹션 raw 에서 끌어온 현재 지면 카드는 모델이 유지할 수 없었다
  (link_not_in_raw_pool) → 현재 지면 카드를 그 섹션 후보로 인정한다.
"""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import editorial_eval
import main
import report_eval

KST = timezone(timedelta(hours=9))


def _mk(section, title, *, press="테스트신문", domain="example.com", link="", score=10.0, fit=2.0, is_core=False):
    link = link or f"https://{domain}/{section}/{abs(hash(title)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description="가격 물량 정책 유통 병해충 현장 대응",
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 9, 21, 16, 0, tzinfo=KST),
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


def _tier_by_domain(press, domain):
    if domain.startswith("t1."):
        return 1
    if domain.startswith("t4."):
        return 4
    return 2


def _thin_pest_raw():
    """9/22 pest raw 축소판: 티어2+ 유효 3건 + 티어1 4건 (+ 게이트에 걸리는 티어2 1건)."""
    high = [_mk("pest", f"티어2 병해충 기사 {i}", domain="t2.example.com") for i in range(3)]
    low = [_mk("pest", f"티어1 병해충 기사 {i}", domain="t1.example.com") for i in range(4)]
    broken = _mk("pest", "본문 깨진 티어2 기사", domain="t2.example.com")
    return high, low, broken


class TestSharedLowTierSectionCap(unittest.TestCase):
    def test_pest_allows_cap_plus_one_only_with_protected_card(self):
        a, b = _mk("pest", "a", domain="t1.example.com"), _mk("pest", "b", domain="t1.example.com")
        with patch.object(main, "_is_protected_low_tier_pest_card", side_effect=lambda art: art is a):
            self.assertFalse(main._low_tier_section_cap_exceeded("pest", [a, b]))
        with patch.object(main, "_is_protected_low_tier_pest_card", return_value=False):
            self.assertTrue(main._low_tier_section_cap_exceeded("pest", [a, b]))
        with patch.object(main, "_is_protected_low_tier_pest_card", return_value=True):
            self.assertTrue(main._low_tier_section_cap_exceeded("pest", [a, b, _mk("pest", "c", domain="t1.example.com")]))
            self.assertTrue(main._low_tier_section_cap_exceeded("supply", [a, b]))
        self.assertFalse(main._low_tier_section_cap_exceeded("supply", [a]))

    def test_repair_validator_accepts_pest_composition_the_deterministic_chain_accepts(self):
        high, low, _broken = _thin_pest_raw()
        raw = {"pest": high + low, "supply": [], "policy": [], "dist": []}
        current = {"pest": list(high) + low[:2], "supply": [], "policy": [], "dist": []}
        repair = {"sections": {"pest": [{"link": a.link, "is_core": i < 2} for i, a in enumerate(high + low[:2])]}}
        errors: list[dict] = []
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
            # 검증기는 후보를 복제하므로 객체 동일성이 아니라 제목으로 보호 카드를 가려낸다.
            patch.object(main, "_is_protected_low_tier_pest_card", side_effect=lambda art: art.title == low[0].title),
        ):
            accepted = main._apply_model_editorial_repair(
                repair, raw, validation_errors=errors, current_by_section=current,
                section_targets={"pest": 5, "supply": 5, "policy": 5, "dist": 5},
            )
        self.assertIsNotNone(accepted)
        assert accepted is not None
        self.assertEqual(len(accepted["pest"]), 5)
        self.assertFalse([e for e in errors if e["reason"] == "low_tier_source_section_cap"])

        errors.clear()
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
            patch.object(main, "_is_protected_low_tier_pest_card", return_value=False),
        ):
            accepted = main._apply_model_editorial_repair(
                repair, raw, validation_errors=errors, current_by_section=current,
            )
        self.assertIsNone(accepted)
        cap_errors = [e for e in errors if e["reason"] == "low_tier_source_section_cap"]
        self.assertEqual([e["section"] for e in cap_errors], ["pest"])
        # 기각 사유의 피해 카드는 저티어 카드여야 한다.
        self.assertIn(cap_errors[0]["link"], {a.link for a in low[:2]})


class TestRepairSectionTargets(unittest.TestCase):
    def test_thin_pest_pool_lowers_target_to_feasible_count(self):
        high, low, broken = _thin_pest_raw()
        raw = {"pest": high + low + [broken], "supply": [], "policy": [], "dist": []}

        def _reject(article, section, *, apply_selection_fit=True):
            return "pest_partial_mention" if article is broken else ""

        with (
            patch.object(main, "_postbuild_article_reject_reason", side_effect=_reject),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
            patch.object(main, "_is_protected_low_tier_pest_card", return_value=False),
        ):
            targets = main._editorial_repair_section_targets(raw)
        self.assertEqual(targets["pest"], 4)
        # 다른 섹션은 raw 가 비어도 SOFT_MIN 아래로 내려가지 않는다.
        self.assertEqual(targets["supply"], main.SOFT_MIN_PER_SECTION)

    def test_protected_low_tier_card_restores_five(self):
        high, low, _broken = _thin_pest_raw()
        raw = {"pest": high + low, "supply": [], "policy": [], "dist": []}
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
            patch.object(main, "_is_protected_low_tier_pest_card", side_effect=lambda art: art is low[0]),
        ):
            targets = main._editorial_repair_section_targets(raw)
        self.assertEqual(targets["pest"], 5)

    def test_current_edition_cross_section_card_counts_toward_target(self):
        high, low, _broken = _thin_pest_raw()
        raw = {"pest": high + low, "supply": [], "policy": [], "dist": []}
        carried = _mk("pest", "정책 raw 에서 끌어온 재해복구비 기사", domain="t4.example.com")
        current = {"pest": list(high) + [carried, low[0]], "supply": [], "policy": [], "dist": []}
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
            patch.object(main, "_is_protected_low_tier_pest_card", return_value=False),
        ):
            self.assertEqual(main._editorial_repair_section_targets(raw)["pest"], 4)
            self.assertEqual(main._editorial_repair_section_targets(raw, current)["pest"], 5)
            extra = main._current_edition_repair_candidates(current, raw)
        self.assertEqual([row["title"] for row in extra["pest"]], [carried.title])
        self.assertEqual(extra["pest"][0]["press_tier"], 4)
        self.assertEqual(extra["pest"][0]["selection_stage"], "current_edition")

    def test_prior_validation_exclusions_shrink_the_pool(self):
        high, low, _broken = _thin_pest_raw()
        raw = {"pest": high + low, "supply": [], "policy": [], "dist": []}
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
            patch.object(main, "_is_protected_low_tier_pest_card", return_value=False),
        ):
            targets = main._editorial_repair_section_targets(
                raw, excluded_links_by_section={"pest": {high[0].link}},
            )
        # 티어2+ 2건 + 티어1 1건 = 3 → SOFT_MIN(4)이 하한
        self.assertEqual(targets["pest"], main.SOFT_MIN_PER_SECTION)


class TestRepairValidatorHonorsSectionTargets(unittest.TestCase):
    def test_four_card_pest_proposal_is_accepted_when_target_is_four(self):
        high, low, _broken = _thin_pest_raw()
        raw = {"pest": high + low, "supply": [], "policy": [], "dist": []}
        current = {"pest": list(high) + [low[0]], "supply": [], "policy": [], "dist": []}
        proposal = [{"link": a.link, "is_core": i < 2} for i, a in enumerate(high + [low[1]])]
        errors: list[dict] = []
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
        ):
            rejected = main._apply_model_editorial_repair(
                {"sections": {"pest": proposal}}, raw, validation_errors=errors, current_by_section=current,
            )
            accepted = main._apply_model_editorial_repair(
                {"sections": {"pest": proposal}}, raw, validation_errors=errors, current_by_section=current,
                section_targets={"pest": 4},
            )
        self.assertIsNone(rejected)
        self.assertEqual(errors[0]["reason"], "section_card_count_invalid")
        self.assertIsNotNone(accepted)
        assert accepted is not None
        self.assertEqual([a.title for a in accepted["pest"]], [a.title for a in high + [low[1]]])

    def test_current_edition_card_outside_raw_pool_is_a_valid_link(self):
        high, low, _broken = _thin_pest_raw()
        raw = {"pest": high + low, "supply": [], "policy": [], "dist": []}
        carried = _mk("pest", "정책 raw 에서 끌어온 재해복구비 기사", domain="t4.example.com")
        current = {"pest": list(high) + [carried, low[0]], "supply": [], "policy": [], "dist": []}
        proposal = [{"link": a.link, "is_core": i < 2} for i, a in enumerate([carried] + high + [low[2]])]
        errors: list[dict] = []
        with (
            patch.object(main, "_postbuild_article_reject_reason", return_value=""),
            patch.object(main, "press_tier", side_effect=_tier_by_domain),
        ):
            accepted = main._apply_model_editorial_repair(
                {"sections": {"pest": proposal}}, raw, validation_errors=errors, current_by_section=current,
                section_targets={"pest": 5},
            )
        self.assertIsNotNone(accepted)
        assert accepted is not None
        self.assertEqual(accepted["pest"][0].title, carried.title)
        self.assertFalse([e for e in errors if e["reason"] == "link_not_in_raw_pool"])

    def test_repair_section_target_defaults_and_clamps(self):
        self.assertEqual(main._repair_section_target(None, "pest"), main.MAX_PER_SECTION)
        self.assertEqual(main._repair_section_target({"pest": 4}, "pest"), 4)
        self.assertEqual(main._repair_section_target({"pest": 4}, "supply"), main.MAX_PER_SECTION)
        self.assertEqual(main._repair_section_target({"pest": 99}, "pest"), main.MAX_PER_SECTION)
        self.assertEqual(main._repair_section_target({"pest": 1}, "pest"), main.MIN_FALLBACK_PER_SECTION)
        self.assertEqual(main._repair_section_target({"pest": None}, "pest"), main.MAX_PER_SECTION)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = json.dumps(payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class TestProposeRepairUsesSectionTargets(unittest.TestCase):
    def setUp(self):
        self.snapshot_payload = {
            "report_date": "2026-09-22",
            "window": {},
            "raw_by_section": {
                section: [
                    {
                        "title": f"{section} 기사 {i}",
                        "description": "본문",
                        "domain": "example.com",
                        "canon_url": f"https://example.com/{section}/{i}",
                        "link": f"https://example.com/{section}/{i}",
                        "score": 10 - i,
                        "press_tier": 2,
                    }
                    for i in range(6)
                ]
                for section in report_eval.SECTION_KEYS
            },
        }

    def test_prompt_schema_and_parser_follow_per_section_targets(self):
        requests_seen: list[dict] = []

        class Session:
            def post(self, url, headers=None, json=None, timeout=None):
                requests_seen.append(json)
                prompt_payload = editorial_eval.json.loads(json["input"][1]["content"])
                targets = prompt_payload["repair_card_targets_by_section"]
                candidates = prompt_payload["raw_candidates_by_section"]
                sections = {
                    section: [
                        {"link": row["link"], "is_core": index < 2}
                        for index, row in enumerate(candidates[section][: targets[section]])
                    ]
                    for section in report_eval.SECTION_KEYS
                }
                return _FakeResponse({"output_text": json_dumps({"sections": sections, "rationale": "ok"})})

        def json_dumps(value):
            return json.dumps(value, ensure_ascii=False)

        extra = {
            "pest": [
                {
                    "title": "현재 지면의 교차 섹션 카드",
                    "description": "본문",
                    "domain": "korea.kr",
                    "canon_url": "https://www.korea.kr/pest/carried",
                    "link": "https://www.korea.kr/pest/carried",
                    "score": 1.0,
                    "press_tier": 4,
                }
            ]
        }
        result = editorial_eval.propose_editorial_repair(
            "2026-09-22",
            "<html></html>",
            self.snapshot_payload,
            {"counts": {}, "scores": {}, "metrics": {}},
            {"status": "success", "score": 70, "issues": []},
            api_key="test-key",
            max_raw_per_section=5,
            section_card_targets={"pest": 4},
            extra_candidates_by_section=extra,
            session_factory=Session,
        )
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(len(result["sections"]["pest"]), 4)
        self.assertEqual(len(result["sections"]["supply"]), 5)
        self.assertEqual(result["section_card_targets"], {"supply": 5, "policy": 5, "dist": 5, "pest": 4})
        request = requests_seen[0]
        schema = request["text"]["format"]["schema"]["properties"]["sections"]["properties"]
        self.assertEqual((schema["pest"]["minItems"], schema["pest"]["maxItems"]), (4, 4))
        self.assertEqual((schema["supply"]["minItems"], schema["supply"]["maxItems"]), (5, 5))
        self.assertIn("pest=4", request["input"][0]["content"])
        prompt_payload = json.loads(request["input"][1]["content"])
        pest_links = [row["link"] for row in prompt_payload["raw_candidates_by_section"]["pest"]]
        self.assertIn("https://www.korea.kr/pest/carried", pest_links)
        # 점수 상한(5)에 걸리지 않고 항상 노출되며, selection_stage 로 현재 지면 카드임을 알린다.
        carried = next(row for row in prompt_payload["raw_candidates_by_section"]["pest"] if row["link"].endswith("carried"))
        self.assertEqual(carried["selection_stage"], "current_edition")
        self.assertEqual(carried["source_tier"], 4)

    def test_wrong_row_count_for_lowered_target_is_an_error(self):
        class Session:
            def post(self, url, headers=None, json=None, timeout=None):
                prompt_payload = editorial_eval.json.loads(json["input"][1]["content"])
                candidates = prompt_payload["raw_candidates_by_section"]
                sections = {
                    section: [{"link": row["link"], "is_core": index < 2} for index, row in enumerate(candidates[section][:5])]
                    for section in report_eval.SECTION_KEYS
                }
                return _FakeResponse({"output_text": editorial_eval.json.dumps({"sections": sections, "rationale": "ok"})})

        result = editorial_eval.propose_editorial_repair(
            "2026-09-22",
            "<html></html>",
            self.snapshot_payload,
            {"counts": {}, "scores": {}, "metrics": {}},
            {"status": "success", "score": 70, "issues": []},
            api_key="test-key",
            max_raw_per_section=5,
            section_card_targets={"pest": 4},
            session_factory=Session,
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("exactly 4 cards", result["reason"])


if __name__ == "__main__":
    unittest.main()
