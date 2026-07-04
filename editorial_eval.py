from __future__ import annotations

from datetime import datetime
import json
import os
import re
from typing import Any

import requests

from report_eval import (
    BRIEFING_SURFACE,
    KST,
    MIN_FALLBACK_BRIEFING_COUNT_PER_SECTION,
    PREFERRED_BRIEFING_COUNT_PER_SECTION,
    SECTION_KEYS,
    SOFT_FALLBACK_BRIEFING_COUNT_PER_SECTION,
    parse_report_html,
)


EDITORIAL_RUBRIC_VERSION = 3
DEFAULT_EDITORIAL_MODEL = "gpt-5.5-2026-04-23"
DEFAULT_MAX_RAW_PER_SECTION = 24
DEFAULT_TIMEOUT_SEC = 90
EDITORIAL_DAILY_TARGET_SCORE = 88.0
EDITORIAL_EXCELLENT_SCORE = 92.0
EDITORIAL_STRETCH_SCORE = 95.0
EDITORIAL_CRITICAL_COMPONENT_MIN = 85.0
EDITORIAL_COMPONENT_MIN = 80.0
SECTION_COUNT_TARGET_SCORE = 95.0
COMMODITY_BOARD_TARGET_SCORE = 95.0

EDITORIAL_COMPONENTS = (
    "article_selection",
    "section_fit",
    "core_pick_quality",
    "summary_usefulness",
    "missed_opportunity",
    "noise_control",
)

EDITORIAL_COMPONENT_WEIGHTS = {
    "article_selection": 0.25,
    "section_fit": 0.15,
    "core_pick_quality": 0.20,
    "summary_usefulness": 0.15,
    "missed_opportunity": 0.15,
    "noise_control": 0.10,
}

EDITORIAL_CRITICAL_COMPONENTS = (
    "article_selection",
    "section_fit",
    "core_pick_quality",
    "summary_usefulness",
)

EDITORIAL_ISSUE_TYPES = (
    "false_positive",
    "off_topic",
    "factual_error",
    "unsafe_summary",
    "duplicate_story",
    "duplicate_theme",
    "wrong_section",
    "weak_core",
    "missed_candidate",
    "promotional_filler",
    "bad_summary",
    "underfill",
    "noise",
    "other",
)

EDITORIAL_SEVERITIES = (
    "blocking",
    "major",
    "moderate",
    "minor",
)

EDITORIAL_HARD_BLOCKING_TYPES = {
    "false_positive",
    "off_topic",
    "factual_error",
    "unsafe_summary",
}


def _score_schema() -> dict[str, Any]:
    return {"type": "number", "minimum": 0, "maximum": 100}


def _editorial_response_format() -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "editorial_quality_eval",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "score",
                    "scores",
                    "summary",
                    "issues",
                    "section_notes",
                    "improvement_suggestions",
                ],
                "properties": {
                    "score": _score_schema(),
                    "scores": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": list(EDITORIAL_COMPONENTS),
                        "properties": {
                            key: _score_schema()
                            for key in EDITORIAL_COMPONENTS
                        },
                    },
                    "summary": {"type": "string"},
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "type",
                                "severity",
                                "section",
                                "title",
                                "reason",
                                "suggested_action",
                            ],
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": list(EDITORIAL_ISSUE_TYPES),
                                },
                                "severity": {
                                    "type": "string",
                                    "enum": list(EDITORIAL_SEVERITIES),
                                },
                                "section": {"type": "string"},
                                "title": {"type": "string"},
                                "reason": {"type": "string"},
                                "suggested_action": {"type": "string"},
                            },
                        },
                    },
                    "section_notes": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": list(SECTION_KEYS),
                        "properties": {
                            section: {"type": "string"}
                            for section in SECTION_KEYS
                        },
                    },
                    "improvement_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        }
    }


def _truncate(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: Any, default: float = 0.0) -> float:
    return round(max(0.0, min(100.0, _as_float(value, default))), 2)


def _score_status(score: float, target: float = EDITORIAL_DAILY_TARGET_SCORE) -> str:
    if score >= target:
        return "target_met"
    if score >= 85.0:
        return "needs_minor_iteration"
    if score >= 80.0:
        return "needs_iteration"
    return "needs_major_iteration"


def _quality_tier(score: float) -> str:
    if score >= EDITORIAL_STRETCH_SCORE:
        return "stretch"
    if score >= EDITORIAL_EXCELLENT_SCORE:
        return "excellent"
    if score >= EDITORIAL_DAILY_TARGET_SCORE:
        return "daily_pass"
    if score >= 80.0:
        return "needs_iteration"
    return "needs_major_iteration"


def _raw_issue_type(value: Any) -> str:
    raw = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")
    return raw or "editorial_issue"


def _issue_type(value: Any) -> str:
    raw = _raw_issue_type(value)
    aliases = {
        "irrelevant_article": "off_topic",
        "duplicate": "duplicate_story",
        "duplication": "duplicate_story",
        "duplicate_url": "duplicate_story",
        "hard_duplicate": "duplicate_story",
        "same_issue_repeated": "duplicate_story",
        "theme_duplicate": "duplicate_theme",
        "theme_duplication": "duplicate_theme",
        "cross_section_overlap": "duplicate_theme",
        "section_mismatch": "wrong_section",
        "section_fit": "wrong_section",
        "weak_section_fit": "wrong_section",
        "wrong_section_or_priority": "wrong_section",
        "wrong_section_or_weak_fit": "wrong_section",
        "weak_core_pick": "weak_core",
        "core_pick_quality": "weak_core",
        "missed_better_core": "weak_core",
        "missed_opportunity": "missed_candidate",
        "missed_better_candidate": "missed_candidate",
        "missed_stronger_candidate": "missed_candidate",
        "under_selected_high_value": "missed_candidate",
        "summary_quality": "bad_summary",
        "summary_noise": "bad_summary",
        "summary_weak": "bad_summary",
        "summary_usefulness": "bad_summary",
        "thin_summary": "bad_summary",
        "count_underfill": "underfill",
        "promotional": "promotional_filler",
        "promotional_tail": "promotional_filler",
        "promotional_or_local_filler": "promotional_filler",
        "promotional_or_event_filler": "promotional_filler",
        "promotional_or_institutional": "promotional_filler",
        "filler": "promotional_filler",
        "weak_tail": "promotional_filler",
        "low_value_selection": "promotional_filler",
        "weak_selection": "noise",
        "weak_pick": "noise",
        "noisy_article": "noise",
        "backfill_noise": "noise",
    }
    normalized = aliases.get(raw, raw)
    return normalized if normalized in EDITORIAL_ISSUE_TYPES else "other"


def _issue_severity(value: Any, issue_type: str) -> str:
    raw = _raw_issue_type(value)
    aliases = {
        "critical": "blocking",
        "fatal": "blocking",
        "high": "major",
        "severe": "major",
        "medium": "moderate",
        "warn": "moderate",
        "warning": "moderate",
        "low": "minor",
    }
    normalized = aliases.get(raw, raw)
    if normalized not in EDITORIAL_SEVERITIES:
        normalized = "moderate"
    if issue_type in EDITORIAL_HARD_BLOCKING_TYPES:
        return "blocking"
    return normalized


def _weighted_editorial_score(scores: dict[str, float]) -> float:
    return _clamp_score(
        sum(
            _clamp_score(scores.get(component), 0.0) * weight
            for component, weight in EDITORIAL_COMPONENT_WEIGHTS.items()
        ),
        0.0,
    )


def _clean_issue(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "type": "other",
            "severity": "moderate",
            "section": "",
            "title": "",
            "reason": _truncate(item, 300),
            "suggested_action": "",
        }
    issue_type = _issue_type(item.get("type") or item.get("category"))
    return {
        "type": issue_type,
        "severity": _issue_severity(item.get("severity") or "moderate", issue_type),
        "section": str(item.get("section") or "").strip(),
        "title": _truncate(item.get("title"), 180),
        "reason": _truncate(item.get("reason") or item.get("evidence"), 360),
        "suggested_action": _truncate(item.get("suggested_action") or item.get("fix"), 280),
    }


def _section_count_row_score(got: int, preferred: int, soft: int, minimum: int) -> float:
    if preferred <= 0:
        return 100.0
    if got >= preferred:
        return 100.0
    if soft > 0 and got >= soft:
        return 92.0
    if minimum > 0 and got >= minimum:
        return 90.0
    if minimum > 0:
        return round(max(0.0, min(1.0, got / minimum)) * 75.0, 2)
    return 0.0


def _section_count_context(operational_result: dict[str, Any]) -> dict[str, Any]:
    counts = operational_result.get("counts", {}) if isinstance(operational_result, dict) else {}
    if not isinstance(counts, dict):
        counts = {}
    actual = counts.get("briefing_by_section", {})
    expected = counts.get("expected_briefing_by_section", {})
    raw_counts = counts.get("raw_by_section", {})
    core_counts = counts.get("core_by_section", {})
    if not isinstance(actual, dict):
        actual = {}
    if not isinstance(expected, dict):
        expected = {}
    if not isinstance(raw_counts, dict):
        raw_counts = {}
    if not isinstance(core_counts, dict):
        core_counts = {}

    rows: dict[str, dict[str, Any]] = {}
    section_scores: list[float] = []
    underfilled: list[str] = []
    soft_fallback_sections: list[str] = []
    minimum_fallback_sections: list[str] = []
    severe_underfilled_sections: list[str] = []
    for section in SECTION_KEYS:
        exp = max(0, int(_as_float(expected.get(section), 0.0)))
        raw = max(0, int(_as_float(raw_counts.get(section), 0.0)))
        preferred = min(PREFERRED_BRIEFING_COUNT_PER_SECTION, raw)
        if exp > 0:
            preferred = max(preferred, min(exp, raw))
        soft = min(SOFT_FALLBACK_BRIEFING_COUNT_PER_SECTION, raw)
        minimum = min(MIN_FALLBACK_BRIEFING_COUNT_PER_SECTION, raw)
        got = max(0, int(_as_float(actual.get(section), 0.0)))
        core = max(0, int(_as_float(core_counts.get(section), 0.0)))
        row_score = _section_count_row_score(got, preferred, soft, minimum)
        section_scores.append(row_score)
        fill_ratio = 1.0 if preferred <= 0 else min(1.0, got / preferred)
        if preferred > 0 and got < preferred:
            underfilled.append(section)
            if got >= soft:
                soft_fallback_sections.append(section)
            elif got >= minimum:
                minimum_fallback_sections.append(section)
            else:
                severe_underfilled_sections.append(section)
        rows[section] = {
            "actual": got,
            "expected": exp,
            "raw_candidates": raw,
            "preferred_count": preferred,
            "soft_fallback_count": soft,
            "minimum_fallback_count": minimum,
            "count_floor": minimum,
            "core_count": core,
            "fill_ratio": round(fill_ratio, 3),
            "score": row_score,
        }
    score = round(sum(section_scores) / len(section_scores), 2) if section_scores else 100.0
    if not underfilled and not severe_underfilled_sections:
        status = "target_met"
    elif score >= 90.0 and not severe_underfilled_sections:
        status = "soft_fallback" if soft_fallback_sections else "minimum_fallback"
    else:
        status = "underfilled"
    return {
        "score": score,
        "status": status,
        "sections": rows,
        "underfilled_sections": underfilled,
        "soft_fallback_sections": soft_fallback_sections,
        "minimum_fallback_sections": minimum_fallback_sections,
        "severe_underfilled_sections": severe_underfilled_sections,
        "preferred_count": PREFERRED_BRIEFING_COUNT_PER_SECTION,
        "soft_fallback_count": SOFT_FALLBACK_BRIEFING_COUNT_PER_SECTION,
        "minimum_fallback_count": MIN_FALLBACK_BRIEFING_COUNT_PER_SECTION,
        "target_score": SECTION_COUNT_TARGET_SCORE,
        "scoring_rule": (
            "Each section should try to carry 5 briefing cards when raw candidates exist. "
            "4 cards is a soft fallback below target, 3 cards is a minimum fallback, and broad fallback use caps editorial shadow below 95."
        ),
    }


def _apply_section_count_gate(result: dict[str, Any], operational_result: dict[str, Any]) -> dict[str, Any]:
    context = _section_count_context(operational_result)
    result["section_count_score"] = context["score"]
    result["section_count_status"] = context["status"]
    result["section_count_context"] = context
    score = _clamp_score(result.get("score"), 0.0)
    count_score = _as_float(context.get("score"), 100.0)
    if count_score >= SECTION_COUNT_TARGET_SCORE:
        return result
    if count_score >= 90.0:
        cap = 94.0
    elif count_score >= 75.0:
        cap = 88.0
    else:
        cap = 80.0
    if score > cap:
        result["section_count_adjustment"] = {
            "before": score,
            "after": cap,
            "reason": "section_count_floor_not_met",
            "underfilled_sections": context.get("underfilled_sections", []),
        }
        result["score"] = cap
        result["target_status"] = _score_status(cap)
    return result


def _apply_editorial_acceptance_gate(
    result: dict[str, Any],
    operational_result: dict[str, Any],
) -> dict[str, Any]:
    """Keep editorial judgment independent and decide whether the daily loop may stop."""
    score = _clamp_score(result.get("score"), 0.0)
    scores = result.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}
    issues = result.get("issues", [])
    if not isinstance(issues, list):
        issues = []

    section_count_context = result.get("section_count_context")
    if not isinstance(section_count_context, dict):
        section_count_context = _section_count_context(operational_result)
    operational_scores = operational_result.get("scores", {})
    if not isinstance(operational_scores, dict):
        operational_scores = {}

    blocking_issues = [
        issue
        for issue in issues
        if isinstance(issue, dict)
        and str(issue.get("severity") or "").lower() == "blocking"
    ]
    major_issues = [
        issue
        for issue in issues
        if isinstance(issue, dict)
        and str(issue.get("severity") or "").lower() == "major"
    ]
    critical_component_scores = {
        component: _clamp_score(scores.get(component), 0.0)
        for component in EDITORIAL_CRITICAL_COMPONENTS
    }
    all_component_scores = {
        component: _clamp_score(scores.get(component), 0.0)
        for component in EDITORIAL_COMPONENTS
    }

    checks = {
        "editorial_score_min": score >= EDITORIAL_DAILY_TARGET_SCORE,
        "no_blocking_issues": not blocking_issues,
        "no_major_issues": not major_issues,
        "critical_components_min": all(
            value >= EDITORIAL_CRITICAL_COMPONENT_MIN
            for value in critical_component_scores.values()
        ),
        "all_components_min": all(
            value >= EDITORIAL_COMPONENT_MIN
            for value in all_component_scores.values()
        ),
        "operational_score_min": _as_float(
            operational_result.get("operational_score"),
            _as_float(operational_result.get("overall_score"), 0.0),
        )
        >= 95.0,
        "section_count_score_min": _as_float(
            section_count_context.get("score"),
            0.0,
        )
        >= SECTION_COUNT_TARGET_SCORE,
        "no_section_underfill": not section_count_context.get("underfilled_sections"),
        "commodity_board_score_min": _as_float(
            operational_scores.get("commodity_board_quality"),
            0.0,
        )
        >= COMMODITY_BOARD_TARGET_SCORE,
    }
    passed = all(checks.values())
    failure_reasons = [name for name, ok in checks.items() if not ok]
    failed_status = _score_status(min(score, EDITORIAL_DAILY_TARGET_SCORE - 0.01))
    result["acceptance_gate"] = {
        "status": "target_met" if passed else failed_status,
        "passed": passed,
        "target_score": EDITORIAL_DAILY_TARGET_SCORE,
        "excellent_score": EDITORIAL_EXCELLENT_SCORE,
        "stretch_score": EDITORIAL_STRETCH_SCORE,
        "blocking_issue_count": len(blocking_issues),
        "major_issue_count": len(major_issues),
        "critical_component_min": EDITORIAL_CRITICAL_COMPONENT_MIN,
        "all_component_min": EDITORIAL_COMPONENT_MIN,
        "checks": checks,
        "failure_reasons": failure_reasons,
    }
    result["target_status"] = result["acceptance_gate"]["status"]
    return result


def _raw_candidates(snapshot_payload: dict[str, Any], max_raw_per_section: int) -> dict[str, list[dict[str, Any]]]:
    raw_by_section = snapshot_payload.get("raw_by_section", {})
    if not isinstance(raw_by_section, dict):
        return {section: [] for section in SECTION_KEYS}

    candidates: dict[str, list[dict[str, Any]]] = {}
    for section in SECTION_KEYS:
        rows = raw_by_section.get(section, [])
        if not isinstance(rows, list):
            candidates[section] = []
            continue
        sorted_rows = sorted(
            (row for row in rows if isinstance(row, dict)),
            key=lambda row: _as_float(row.get("score"), 0.0),
            reverse=True,
        )
        candidates[section] = [
            {
                "title": _truncate(row.get("title"), 180),
                "description": _truncate(row.get("description") or row.get("summary"), 520),
                "domain": _truncate(row.get("domain") or row.get("press"), 80),
                "link": _truncate(row.get("canon_url") or row.get("link") or row.get("originallink"), 260),
                "pub_dt_kst": _truncate(row.get("pub_dt_kst"), 40),
                "topic": _truncate(row.get("topic"), 80),
                "source_query": _truncate(row.get("source_query"), 100),
                "score": round(_as_float(row.get("score"), 0.0), 3),
                "selection_fit_score": round(_as_float(row.get("selection_fit_score"), 0.0), 3),
                "selection_stage": _truncate(row.get("selection_stage"), 80),
                "origin_section": _truncate(row.get("origin_section"), 40),
                "forced_section": _truncate(row.get("forced_section"), 40),
            }
            for row in sorted_rows[:max(1, max_raw_per_section)]
        ]
    return candidates


def build_editorial_payload(
    report_date: str,
    html_text: str,
    snapshot_payload: dict[str, Any],
    operational_result: dict[str, Any],
    *,
    max_raw_per_section: int = DEFAULT_MAX_RAW_PER_SECTION,
) -> dict[str, Any]:
    articles = [article for article in parse_report_html(html_text) if article.surface == BRIEFING_SURFACE]
    selected = [
        {
            "position": idx + 1,
            "section": article.section,
            "title": _truncate(article.title, 180),
            "summary": _truncate(article.summary, 420),
            "domain": _truncate(article.domain, 80),
            "href": _truncate(article.href, 260),
            "is_core": bool(article.is_core),
            "selection_fit_score": round(_as_float(article.selection_fit_score), 3),
            "selection_stage": _truncate(article.selection_stage, 80),
        }
        for idx, article in enumerate(articles)
    ]

    return {
        "rubric_version": EDITORIAL_RUBRIC_VERSION,
        "report_date": report_date,
        "target_score": EDITORIAL_DAILY_TARGET_SCORE,
        "window": snapshot_payload.get("window", {}),
        "selected_briefing_cards": selected,
        "raw_candidates_by_section": _raw_candidates(snapshot_payload, max_raw_per_section),
        "section_count_targets": _section_count_context(operational_result),
        "operational_eval": {
            "overall_score": operational_result.get("overall_score"),
            "status": operational_result.get("status"),
            "scores": operational_result.get("scores", {}),
            "metrics": operational_result.get("metrics", {}),
            "counts": operational_result.get("counts", {}),
            "selection_guardrails": operational_result.get("selection_guardrails", {}),
        },
        "instructions": {
            "audience": "NH horticulture/agricultural briefing readers in Korea",
            "score_meaning": {
                "95_100": "stretch quality with only tiny misses",
                "92_94": "excellent daily briefing",
                "88_91": "daily pass with no major editorial defect",
                "80_87": "usable but needs iteration",
                "below_80": "selection logic needs material correction",
            },
            "component_weights": EDITORIAL_COMPONENT_WEIGHTS,
        },
    }


def _extract_response_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    pieces: list[str] = []
    for output in payload.get("output", []) if isinstance(payload.get("output"), list) else []:
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []) if isinstance(output.get("content"), list) else []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                pieces.append(text.strip())
    return "\n".join(pieces).strip()


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Editorial response was not a JSON object.")
    return parsed


def _normalize_editorial_response(
    parsed: dict[str, Any],
    *,
    model: str,
    raw_text: str,
    operational_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_scores = parsed.get("scores", {})
    if not isinstance(raw_scores, dict):
        raw_scores = {}

    scores = {
        key: _clamp_score(raw_scores.get(key), 0.0)
        for key in EDITORIAL_COMPONENTS
    }
    model_reported_score = _clamp_score(
        parsed.get("score", parsed.get("overall_score")),
        0.0,
    )
    overall = _weighted_editorial_score(scores)

    issues = parsed.get("issues", [])
    if not isinstance(issues, list):
        issues = [issues]

    suggestions = parsed.get("improvement_suggestions") or parsed.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = [suggestions]

    section_notes = parsed.get("section_notes", {})
    if not isinstance(section_notes, dict):
        section_notes = {}

    result = {
        "status": "success",
        "rubric_version": EDITORIAL_RUBRIC_VERSION,
        "model": model,
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "score": overall,
        "model_reported_score": model_reported_score,
        "score_method": "weighted_components_v1",
        "component_weights": EDITORIAL_COMPONENT_WEIGHTS,
        "quality_tier": _quality_tier(overall),
        "target_score": EDITORIAL_DAILY_TARGET_SCORE,
        "excellent_score": EDITORIAL_EXCELLENT_SCORE,
        "stretch_score": EDITORIAL_STRETCH_SCORE,
        "target_status": _score_status(overall),
        "scores": scores,
        "summary": _truncate(parsed.get("summary") or parsed.get("rationale"), 700),
        "issues": [_clean_issue(item) for item in issues[:12]],
        "section_notes": {str(key): _truncate(value, 360) for key, value in section_notes.items()},
        "improvement_suggestions": [_truncate(item, 300) for item in suggestions[:10]],
        "raw_response_excerpt": _truncate(raw_text, 1200),
    }
    if operational_result is not None:
        result = _apply_section_count_gate(result, operational_result)
        result["quality_tier"] = _quality_tier(_clamp_score(result.get("score"), 0.0))
        result = _apply_editorial_acceptance_gate(result, operational_result)
    return result


def evaluate_editorial_quality(
    report_date: str,
    html_text: str,
    snapshot_payload: dict[str, Any],
    operational_result: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str | None = None,
    enabled: bool = True,
    max_raw_per_section: int = DEFAULT_MAX_RAW_PER_SECTION,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    session_factory: Any = requests.Session,
) -> dict[str, Any]:
    resolved_model = (
        model
        or os.getenv("EDITORIAL_OPENAI_MODEL")
        or DEFAULT_EDITORIAL_MODEL
    )
    resolved_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
    if not enabled:
        return {
            "status": "skipped",
            "reason": "disabled",
            "rubric_version": EDITORIAL_RUBRIC_VERSION,
            "model": resolved_model,
        }
    if not resolved_key:
        return {
            "status": "skipped",
            "reason": "missing_openai_api_key",
            "rubric_version": EDITORIAL_RUBRIC_VERSION,
            "model": resolved_model,
        }

    payload = build_editorial_payload(
        report_date,
        html_text,
        snapshot_payload,
        operational_result,
        max_raw_per_section=max_raw_per_section,
    )
    system_prompt = (
        "You are a strict editorial quality judge for a Korean agricultural daily news brief. "
        "Judge whether the selected articles are the right articles, not just whether the report format is valid. "
        "Penalize wrong-section stories, promotional/local-event filler, stale or duplicated items, weak core picks, "
        "and missed better candidates visible in the raw candidate pools. "
        "Section counts are part of editorial quality: if section_count_targets shows enough raw candidates, expect 5 selected cards when possible; "
        "4 is a soft fallback and 3 is a minimum fallback. Do not award 95 or higher when broad fallback use pulls section_count_targets below target. "
        "Conversely, when a raw pool is weak, concrete support/event articles may be acceptable as non-core tails to preserve the section count, "
        "but they should not displace stronger national or operational candidates. "
        "For dist, prefer concrete distribution, logistics, export-disruption, market-operation, and sales-channel stories over local promotions. "
        "For pest, prefer fire-blight escalation/response and named crop pest risks over generic local notices. "
        "Use only these issue types: "
        + ", ".join(EDITORIAL_ISSUE_TYPES)
        + ". Use only these severity levels: "
        + ", ".join(EDITORIAL_SEVERITIES)
        + ". Reserve blocking for false positives, off-topic items, factual errors, or unsafe summaries. "
        "Use major for a defect that prevents daily editorial acceptance, moderate for a meaningful but non-blocking weakness, and minor for polish. "
        "Return JSON only with keys: score, scores, summary, issues, section_notes, improvement_suggestions. "
        "section_notes must include supply, policy, dist, and pest. "
        "scores must include article_selection, section_fit, core_pick_quality, summary_usefulness, missed_opportunity, noise_control, each 0-100. "
        "Make the reported score consistent with the component scores; the application will recompute the authoritative score from fixed weights. "
        "Return at most 8 issues and at most 6 improvement suggestions. Keep every reason and suggested_action concise. "
        "issues should be objects with type, severity, section, title, reason, suggested_action."
    )
    request_body = {
        "model": resolved_model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "max_output_tokens": 5000,
        "text": _editorial_response_format(),
    }

    session = session_factory()
    raw_text = ""
    try:
        response = session.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {resolved_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=timeout_sec,
        )
        response.raise_for_status()
        response_payload = response.json()
        raw_text = _extract_response_text(response_payload)
        parsed = extract_json_object(raw_text)
        result = _normalize_editorial_response(
            parsed,
            model=resolved_model,
            raw_text=raw_text,
            operational_result=operational_result,
        )
        model_snapshot = str(response_payload.get("model") or "").strip()
        if model_snapshot:
            result["model_snapshot"] = model_snapshot
        return result
    except Exception as exc:
        return {
            "status": "error",
            "reason": str(exc),
            "rubric_version": EDITORIAL_RUBRIC_VERSION,
            "model": resolved_model,
            "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
            "raw_response_excerpt": _truncate(raw_text, 1200),
        }


def build_editorial_improvement_plan(
    editorial_result: dict[str, Any],
    operational_result: dict[str, Any],
    *,
    target_score: float = EDITORIAL_DAILY_TARGET_SCORE,
) -> dict[str, Any]:
    score = _clamp_score(editorial_result.get("score"), 0.0)
    issue_rows = editorial_result.get("issues", [])
    if not isinstance(issue_rows, list):
        issue_rows = []
    issue_types = {_issue_type(row.get("type")) for row in issue_rows if isinstance(row, dict)}

    actions: list[dict[str, Any]] = []
    guardrail_focus: list[str] = []

    if "weak_core" in issue_types:
        actions.append(
            {
                "kind": "selection_guardrail",
                "target": "core_fit_min",
                "direction": "tighten",
                "reason": "Core cards should not be filled by merely available articles.",
            }
        )
        guardrail_focus.append("core_quality")
    if "missed_candidate" in issue_types:
        actions.append(
            {
                "kind": "candidate_recall",
                "target": "raw_candidate_pool",
                "direction": "expand_or_rerank",
                "reason": "The raw pool contained stronger alternatives than selected cards.",
            }
        )
        guardrail_focus.append("missed_opportunity")
    if {"duplicate_story", "duplicate_theme"} & issue_types:
        actions.append(
            {
                "kind": "story_dedupe",
                "target": "story_signature_gate",
                "direction": "tighten",
                "reason": "Multiple cards covered the same issue and reduced briefing breadth.",
            }
        )
        guardrail_focus.append("article_selection")
    if {"noise", "promotional_filler", "false_positive", "off_topic"} & issue_types:
        actions.append(
            {
                "kind": "noise_filter",
                "target": "semantic_false_positive_gate",
                "direction": "tighten",
                "reason": "Selected cards included low editorial-value noise.",
            }
        )
        guardrail_focus.append("noise_control")
    if "wrong_section" in issue_types:
        actions.append(
            {
                "kind": "section_fit",
                "target": "section_card_min_fit",
                "direction": "tighten",
                "reason": "A selected card appears to fit another section better.",
            }
        )
        guardrail_focus.append("section_fit")
    if {"bad_summary", "factual_error", "unsafe_summary"} & issue_types:
        actions.append(
            {
                "kind": "summary_prompt",
                "target": "latest-feedback.txt",
                "direction": "add_editorial_feedback",
                "reason": "Summaries should explain impact and decision value, not just restate titles.",
            }
        )
        guardrail_focus.append("summary_usefulness")
    if "underfill" in issue_types:
        actions.append(
            {
                "kind": "section_fill",
                "target": "preferred_section_count",
                "direction": "restore",
                "reason": "Every section with enough candidates should reach its preferred card count.",
            }
        )
        guardrail_focus.append("section_count")

    acceptance_gate = editorial_result.get("acceptance_gate", {})
    if not isinstance(acceptance_gate, dict):
        acceptance_gate = {}
    passed = bool(acceptance_gate.get("passed"))
    plan_status = str(acceptance_gate.get("status") or "")
    if not plan_status:
        plan_status = _score_status(min(score, target_score - 0.01), target_score)
    if not passed and not actions:
        actions.append(
            {
                "kind": "manual_review",
                "target": "editorial_issues",
                "direction": "inspect",
                "reason": "Editorial score is below target but issue types were not mapped to automated knobs.",
            }
        )

    current_guardrails = operational_result.get("selection_guardrails", {})
    section_count_context = _section_count_context(operational_result)
    return {
        "mode": "shadow_replay_loop",
        "proposal_only": True,
        "target_score": float(target_score),
        "current_editorial_score": score,
        "model_reported_score": editorial_result.get("model_reported_score"),
        "quality_tier": editorial_result.get("quality_tier"),
        "target_status": plan_status,
        "iteration_budget": 0 if passed else 3,
        "promotion_gates": {
            "editorial_score_min": float(target_score),
            "critical_component_min": EDITORIAL_CRITICAL_COMPONENT_MIN,
            "all_component_min": EDITORIAL_COMPONENT_MIN,
            "no_blocking_issues": True,
            "no_major_issues": True,
            "operational_score_min": 95.0,
            "section_count_score_min": SECTION_COUNT_TARGET_SCORE,
            "commodity_board_score_min": COMMODITY_BOARD_TARGET_SCORE,
            "no_section_underfill": True,
        },
        "section_count_context": section_count_context,
        "guardrail_focus": list(dict.fromkeys(guardrail_focus)),
        "recommended_actions": actions[:8],
        "current_selection_guardrails": current_guardrails if isinstance(current_guardrails, dict) else {},
        "notes": (
            "Use this as the replay loop contract: iterate guardrails and ranking changes, then promote only "
            "when editorial, operational, preferred section-count, and commodity-board gates all pass."
        ),
    }
