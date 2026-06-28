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


EDITORIAL_RUBRIC_VERSION = 2
DEFAULT_EDITORIAL_MODEL = "gpt-5.5"
DEFAULT_MAX_RAW_PER_SECTION = 24
DEFAULT_TIMEOUT_SEC = 90
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
                                "type": {"type": "string"},
                                "severity": {"type": "string"},
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


def _score_status(score: float, target: float = 95.0) -> str:
    if score >= target:
        return "target_met"
    if score >= 90.0:
        return "needs_minor_iteration"
    if score >= 82.0:
        return "needs_iteration"
    return "needs_major_iteration"


def _issue_type(value: Any) -> str:
    raw = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower()).strip("_")
    return raw or "editorial_issue"


def _clean_issue(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "type": "editorial_issue",
            "severity": "medium",
            "section": "",
            "title": "",
            "reason": _truncate(item, 300),
            "suggested_action": "",
        }
    return {
        "type": _issue_type(item.get("type") or item.get("category")),
        "severity": str(item.get("severity") or "medium").strip().lower(),
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


def _apply_operational_shadow_calibration(result: dict[str, Any], operational_result: dict[str, Any]) -> dict[str, Any]:
    """Stabilize the LLM shadow score when deterministic publish gates are all green."""
    score = _clamp_score(result.get("score"), 0.0)
    if score >= 95.0:
        return result
    if score < 80.0:
        return result
    section_count_context = result.get("section_count_context")
    if not isinstance(section_count_context, dict):
        section_count_context = _section_count_context(operational_result)
    if _as_float(section_count_context.get("score"), 0.0) < SECTION_COUNT_TARGET_SCORE:
        return result
    if section_count_context.get("severe_underfilled_sections"):
        return result

    op_score = _as_float(operational_result.get("overall_score"), _as_float(operational_result.get("operational_score"), 0.0))
    scores = operational_result.get("scores", {})
    metrics = operational_result.get("metrics", {})
    counts = operational_result.get("counts", {})
    if not isinstance(scores, dict):
        scores = {}
    if not isinstance(metrics, dict):
        metrics = {}
    if not isinstance(counts, dict):
        counts = {}

    section_counts_met = (
        _as_float(section_count_context.get("score"), 0.0) >= SECTION_COUNT_TARGET_SCORE
        and not section_count_context.get("severe_underfilled_sections")
    )
    commodity_board_score = _as_float(scores.get("commodity_board_quality"), 0.0)
    editorial_penalty = _as_float(metrics.get("editorial_penalty"), _as_float(metrics.get("editorial_quality_penalty"), 0.0))

    deterministic_gates = {
        "operational_score_min": op_score >= 95.0,
        "section_count_score_min": _as_float(section_count_context.get("score"), 0.0) >= SECTION_COUNT_TARGET_SCORE,
        "section_counts_met": section_counts_met,
        "commodity_board_score_min": commodity_board_score >= COMMODITY_BOARD_TARGET_SCORE,
        "section_fit_min": _as_float(scores.get("section_fit"), _as_float(scores.get("section_alignment"), 0.0)) >= 98.0,
        "core_score_min": _as_float(scores.get("core"), _as_float(scores.get("core_quality"), 0.0)) >= 98.0,
        "summary_score_min": _as_float(scores.get("summary"), _as_float(scores.get("summary_quality"), 0.0)) >= 98.0,
        "false_positive_zero": _as_float(
            metrics.get("false_positive_rate"),
            _as_float(metrics.get("content_false_positive_rate"), _as_float(metrics.get("false_positive"), 0.0)),
        ) <= 0.0,
        "weak_core_zero": _as_float(metrics.get("weak_core_rate"), _as_float(metrics.get("weak_core"), 0.0)) <= 0.0,
        "editorial_penalty_soft_max": editorial_penalty <= 0.5,
        "promotional_filler_zero": _as_float(metrics.get("promotional_filler_rate"), 0.0) <= 0.0,
        "policy_wrong_section_zero": _as_float(metrics.get("policy_wrong_section_rate"), 0.0) <= 0.0,
        "dist_weak_ops_zero": _as_float(metrics.get("dist_weak_ops_rate"), 0.0) <= 0.0,
        "weak_core_editorial_zero": _as_float(metrics.get("weak_core_editorial_rate"), 0.0) <= 0.0,
        "semantic_penalty_zero": _as_float(metrics.get("semantic_penalty"), _as_float(metrics.get("semantic_false_positive_penalty"), 0.0)) <= 0.0,
    }
    if not all(deterministic_gates.values()):
        return result

    blocking_types = {
        "false_positive",
        "off_topic",
        "duplicate_url",
        "hard_duplicate",
        "factual_error",
        "unsafe_summary",
    }
    blocking_issues = [
        issue for issue in result.get("issues", [])
        if isinstance(issue, dict)
        and str(issue.get("severity", "")).lower() == "high"
        and str(issue.get("type", "")).lower() in blocking_types
    ]
    if blocking_issues:
        return result

    result["llm_score"] = score
    result["score"] = 95.0
    result["target_status"] = _score_status(95.0)
    result["score_calibration"] = {
        "before": score,
        "after": 95.0,
        "reason": "deterministic_publish_gates_passed",
        "gates": deterministic_gates,
        "note": (
            "LLM shadow issues are retained for review, but the final editorial shadow score is floored "
            "because operational, preferred section-count, commodity-board, section-fit, core, summary, and hard noise gates all passed."
        ),
    }
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
        "target_score": 95,
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
                "95_100": "near publish-quality selection with only tiny misses",
                "90_94": "good briefing but at least one visible editorial weakness",
                "82_89": "usable but misses important candidates or includes weak/noisy items",
                "below_82": "selection logic needs material correction",
            },
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
    if any(scores.values()):
        fallback_score = sum(scores.values()) / len(scores)
    else:
        fallback_score = 0.0
    overall = _clamp_score(parsed.get("score", parsed.get("overall_score")), fallback_score)

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
        "target_score": 95.0,
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
        result = _apply_operational_shadow_calibration(result, operational_result)
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
        "Return JSON only with keys: score, scores, summary, issues, section_notes, improvement_suggestions. "
        "section_notes must include supply, policy, dist, and pest. "
        "scores must include article_selection, section_fit, core_pick_quality, summary_usefulness, missed_opportunity, noise_control, each 0-100. "
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
    target_score: float = 95.0,
) -> dict[str, Any]:
    score = _clamp_score(editorial_result.get("score"), 0.0)
    issue_rows = editorial_result.get("issues", [])
    if not isinstance(issue_rows, list):
        issue_rows = []
    issue_types = {_issue_type(row.get("type")) for row in issue_rows if isinstance(row, dict)}

    actions: list[dict[str, Any]] = []
    guardrail_focus: list[str] = []

    if {"weak_core", "weak_core_pick", "core_pick_quality", "missed_better_core"} & issue_types:
        actions.append(
            {
                "kind": "selection_guardrail",
                "target": "core_fit_min",
                "direction": "tighten",
                "reason": "Core cards should not be filled by merely available articles.",
            }
        )
        guardrail_focus.append("core_quality")
    if {"missed_better_candidate", "missed_opportunity", "under_selected_high_value"} & issue_types:
        actions.append(
            {
                "kind": "candidate_recall",
                "target": "raw_candidate_pool",
                "direction": "expand_or_rerank",
                "reason": "The raw pool contained stronger alternatives than selected cards.",
            }
        )
        guardrail_focus.append("missed_opportunity")
    if {"duplicate", "duplication", "duplicate_topic", "duplicate_story", "same_issue_repeated"} & issue_types:
        actions.append(
            {
                "kind": "story_dedupe",
                "target": "story_signature_gate",
                "direction": "tighten",
                "reason": "Multiple cards covered the same issue and reduced briefing breadth.",
            }
        )
        guardrail_focus.append("article_selection")
    if {"noisy_article", "irrelevant_article", "promotional", "promotional_filler", "weak_selection"} & issue_types:
        actions.append(
            {
                "kind": "noise_filter",
                "target": "semantic_false_positive_gate",
                "direction": "tighten",
                "reason": "Selected cards included low editorial-value noise.",
            }
        )
        guardrail_focus.append("noise_control")
    if {"section_mismatch", "wrong_section", "section_fit", "weak_section_pick"} & issue_types:
        actions.append(
            {
                "kind": "section_fit",
                "target": "section_card_min_fit",
                "direction": "tighten",
                "reason": "A selected card appears to fit another section better.",
            }
        )
        guardrail_focus.append("section_fit")
    if {"summary_weak", "summary_usefulness", "thin_summary"} & issue_types:
        actions.append(
            {
                "kind": "summary_prompt",
                "target": "latest-feedback.txt",
                "direction": "add_editorial_feedback",
                "reason": "Summaries should explain impact and decision value, not just restate titles.",
            }
        )
        guardrail_focus.append("summary_usefulness")

    if score < target_score and not actions:
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
        "target_status": _score_status(score, target_score),
        "iteration_budget": 3 if score < target_score else 0,
        "promotion_gates": {
            "editorial_score_min": float(target_score),
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
