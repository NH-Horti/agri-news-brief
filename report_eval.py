from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


KST = timezone(timedelta(hours=9))
SECTION_KEYS = ("supply", "policy", "dist", "pest")
BRIEFING_SURFACE = "briefing_card"
COMMODITY_SURFACES = frozenset({"commodity_primary", "commodity_support", "commodity_more"})
TRACKING_QUERY_KEYS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "sc",
        "input",
    }
)

_NON_KO_WORD_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")
_SPACE_RE = re.compile(r"\s+")


@dataclass
class SurfaceArticle:
    tag: str
    surface: str
    section: str
    title: str
    href: str
    article_id: str
    domain: str
    summary: str = ""
    is_core: bool = False


class ReportHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.articles: list[SurfaceArticle] = []
        self._current_card: SurfaceArticle | None = None
        self._card_div_depth = 0
        self._summary_div_depth = 0
        self._summary_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        classes = set(str(attr_map.get("class", "")).split())
        surface = str(attr_map.get("data-surface", "")).strip()

        if tag == "div" and surface == BRIEFING_SURFACE:
            self._current_card = SurfaceArticle(
                tag=tag,
                surface=surface,
                section=str(attr_map.get("data-section", "")).strip(),
                title=str(attr_map.get("data-article-title", "")).strip(),
                href=str(attr_map.get("data-href", "")).strip(),
                article_id=str(attr_map.get("data-article-id", "")).strip(),
                domain=str(attr_map.get("data-target-domain", "")).strip(),
            )
            self._card_div_depth = 1
            self._summary_div_depth = 0
            self._summary_parts = []
            return

        if tag == "a" and surface in COMMODITY_SURFACES:
            self.articles.append(
                SurfaceArticle(
                    tag=tag,
                    surface=surface,
                    section=str(attr_map.get("data-section", "")).strip(),
                    title=str(attr_map.get("data-article-title", "")).strip(),
                    href=str(attr_map.get("href", "")).strip(),
                    article_id=str(attr_map.get("data-article-id", "")).strip(),
                    domain=str(attr_map.get("data-target-domain", "")).strip(),
                )
            )
            return

        if self._current_card is None:
            return

        if tag == "div":
            self._card_div_depth += 1
            if "sum" in classes:
                self._summary_div_depth = 1
                self._summary_parts = []
            elif self._summary_div_depth:
                self._summary_div_depth += 1

        if tag == "span" and "badgeCore" in classes:
            self._current_card.is_core = True

    def handle_endtag(self, tag: str) -> None:
        if self._current_card is None:
            return

        if tag == "div":
            if self._summary_div_depth:
                self._summary_div_depth -= 1
                if self._summary_div_depth == 0:
                    self._current_card.summary = _normalize_spaces(" ".join(self._summary_parts))
                    self._summary_parts = []

            self._card_div_depth -= 1
            if self._card_div_depth <= 0:
                self.articles.append(self._current_card)
                self._current_card = None
                self._card_div_depth = 0
                self._summary_div_depth = 0
                self._summary_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_card is not None and self._summary_div_depth:
            self._summary_parts.append(data)


def _normalize_spaces(text: str) -> str:
    return _SPACE_RE.sub(" ", str(text or "").replace("\xa0", " ")).strip()


def normalize_title_key(text: str) -> str:
    value = _normalize_spaces(unescape(str(text or "")).lower())
    return _NON_KO_WORD_RE.sub("", value)


def normalize_summary_opening(text: str) -> str:
    value = _normalize_spaces(unescape(str(text or "")))
    value = re.sub(r"[\"'“”‘’\[\]\(\){}]", "", value)
    return normalize_title_key(value[:18])


def normalize_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in TRACKING_QUERY_KEYS:
            continue
        query_pairs.append((key, value))
    query_pairs.sort()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query_pairs, doseq=True), ""))


def parse_kst_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST)


def parse_report_html(html_text: str) -> list[SurfaceArticle]:
    parser = ReportHTMLParser()
    parser.feed(html_text)
    parser.close()
    return parser.articles


def load_snapshot_payload(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Snapshot payload is not a JSON object: {path}")
    return payload


def _score_between(value: float, low: float, good: float) -> float:
    if good <= low:
        return 1.0 if value >= good else 0.0
    if value <= low:
        return 0.0
    if value >= good:
        return 1.0
    return (value - low) / (good - low)


def _score_inverse(value: float, good: float, high: float) -> float:
    if high <= good:
        return 1.0 if value <= good else 0.0
    if value <= good:
        return 1.0
    if value >= high:
        return 0.0
    return 1.0 - ((value - good) / (high - good))


def _expected_briefing_count(raw_count: int) -> int:
    if raw_count >= 24:
        return 3
    if raw_count >= 10:
        return 2
    if raw_count >= 3:
        return 1
    return 0


def _find_snapshot_match(
    article: SurfaceArticle,
    by_url: dict[str, dict[str, Any]],
    by_title: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    url_key = normalize_url(article.href)
    if url_key and url_key in by_url:
        return by_url[url_key]
    title_key = normalize_title_key(article.title)
    if title_key:
        for candidate in by_title.get(title_key, []):
            if str(candidate.get("section", "")).strip() == article.section:
                return candidate
        if by_title.get(title_key):
            return by_title[title_key][0]
    return None


def _build_snapshot_indexes(snapshot_payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_url: dict[str, dict[str, Any]] = {}
    by_title: dict[str, list[dict[str, Any]]] = {}
    raw_by_section = snapshot_payload.get("raw_by_section", {})
    if not isinstance(raw_by_section, dict):
        return by_url, by_title

    for items in raw_by_section.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            url_key = normalize_url(str(item.get("link", "") or ""))
            if url_key and url_key not in by_url:
                by_url[url_key] = item
            title_key = normalize_title_key(item.get("title", ""))
            if title_key:
                by_title.setdefault(title_key, []).append(item)
    return by_url, by_title


def _section_counts(articles: list[SurfaceArticle]) -> dict[str, int]:
    counter = Counter(a.section for a in articles if a.section in SECTION_KEYS)
    return {section: int(counter.get(section, 0)) for section in SECTION_KEYS}


def _rate(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator <= 0:
        return default
    return float(numerator) / float(denominator)


def _rolling_seed_score(snapshot_payload: dict[str, Any]) -> tuple[float, dict[str, float]]:
    debug_payload = snapshot_payload.get("debug", {})
    collections = debug_payload.get("collections", {}) if isinstance(debug_payload, dict) else {}
    section_scores: dict[str, float] = {}
    if not isinstance(collections, dict):
        return 0.5, section_scores

    for section in SECTION_KEYS:
        payload = collections.get(section, {})
        seed_coverage = payload.get("seed_coverage", []) if isinstance(payload, dict) else []
        if not isinstance(seed_coverage, list) or not seed_coverage:
            continue
        total = 0
        missing = 0
        for item in seed_coverage:
            if not isinstance(item, dict):
                continue
            total += 1
            if bool(item.get("missing", False)):
                missing += 1
        if total:
            section_scores[section] = 1.0 - _rate(missing, total)

    if not section_scores:
        return 0.5, {}

    return sum(section_scores.values()) / len(section_scores), section_scores


def evaluate_report(report_date: str, html_text: str, snapshot_payload: dict[str, Any]) -> dict[str, Any]:
    articles = parse_report_html(html_text)
    briefing_articles = [article for article in articles if article.surface == BRIEFING_SURFACE]
    commodity_articles = [article for article in articles if article.surface in COMMODITY_SURFACES]
    all_surface_articles = briefing_articles + commodity_articles

    raw_by_section = snapshot_payload.get("raw_by_section", {})
    raw_counts = {
        section: len(raw_by_section.get(section, [])) if isinstance(raw_by_section, dict) else 0
        for section in SECTION_KEYS
    }
    expected_counts = {section: _expected_briefing_count(raw_counts[section]) for section in SECTION_KEYS}
    briefing_counts = _section_counts(briefing_articles)
    core_counts = _section_counts([article for article in briefing_articles if article.is_core])
    commodity_counts = _section_counts(commodity_articles)

    section_fill_scores: dict[str, float] = {}
    core_fill_scores: dict[str, float] = {}
    for section in SECTION_KEYS:
        expected = expected_counts[section]
        actual = briefing_counts[section]
        if expected <= 0:
            section_fill_scores[section] = 1.0
            core_fill_scores[section] = 1.0
            continue
        section_fill_scores[section] = min(1.0, _rate(actual, expected))
        core_fill_scores[section] = 1.0 if actual <= 0 or core_counts[section] >= 1 else 0.0

    completeness_score = 100.0 * (
        (sum(section_fill_scores.values()) / len(SECTION_KEYS)) * 0.72
        + (sum(core_fill_scores.values()) / len(SECTION_KEYS)) * 0.28
    )

    unique_domains = {article.domain for article in briefing_articles if article.domain}
    unique_signatures = {normalize_title_key(article.title) for article in briefing_articles if article.title}
    title_unique_rate = _rate(len(unique_signatures), len(briefing_articles), default=1.0)
    domain_diversity_rate = _rate(len(unique_domains), len(briefing_articles), default=1.0)

    article_id_counts = Counter(article.article_id or normalize_title_key(article.title) for article in all_surface_articles)
    repeated_surface_articles = sum(max(0, count - 2) for count in article_id_counts.values())
    surface_reuse_penalty = _rate(repeated_surface_articles, len(all_surface_articles), default=0.0)

    diversity_score = 100.0 * (
        _score_between(title_unique_rate, 0.65, 0.9) * 0.45
        + _score_between(domain_diversity_rate, 0.35, 0.7) * 0.35
        + _score_inverse(surface_reuse_penalty, 0.05, 0.22) * 0.20
    )

    summary_lengths = [len(article.summary.strip()) for article in briefing_articles if article.summary.strip()]
    summary_presence_rate = _rate(len(summary_lengths), len(briefing_articles), default=1.0)
    summary_length_ok_rate = _rate(sum(1 for length in summary_lengths if 85 <= length <= 140), len(summary_lengths), default=1.0)
    summary_numeric_rate = _rate(
        sum(1 for article in briefing_articles if re.search(r"\d|[%억원톤kg℃]", article.summary)),
        len(briefing_articles),
        default=0.0,
    )
    summary_openings = {normalize_summary_opening(article.summary) for article in briefing_articles if article.summary.strip()}
    summary_opening_diversity = _rate(len(summary_openings), len(summary_lengths), default=1.0)

    summary_score = 100.0 * (
        summary_presence_rate * 0.35
        + summary_length_ok_rate * 0.30
        + _score_between(summary_numeric_rate, 0.15, 0.45) * 0.15
        + _score_between(summary_opening_diversity, 0.45, 0.85) * 0.20
    )

    snapshot_end = parse_kst_datetime(snapshot_payload.get("window", {}).get("end_kst"))
    by_url, by_title = _build_snapshot_indexes(snapshot_payload)
    matched_count = 0
    within_48h = 0
    within_72h = 0
    stale_older_than_96h = 0
    freshness_samples: list[dict[str, Any]] = []

    for article in briefing_articles:
        match = _find_snapshot_match(article, by_url, by_title)
        if not match:
            continue
        matched_count += 1
        pub_dt = parse_kst_datetime(match.get("pub_dt_kst"))
        if not snapshot_end or not pub_dt:
            continue
        age_hours = max(0.0, (snapshot_end - pub_dt).total_seconds() / 3600.0)
        if age_hours <= 48.0:
            within_48h += 1
        if age_hours <= 72.0:
            within_72h += 1
        if age_hours > 96.0:
            stale_older_than_96h += 1
        freshness_samples.append(
            {
                "title": article.title,
                "section": article.section,
                "age_hours": round(age_hours, 1),
            }
        )

    matched_rate = _rate(matched_count, len(briefing_articles), default=1.0)
    within_48h_rate = _rate(within_48h, matched_count, default=1.0)
    within_72h_rate = _rate(within_72h, matched_count, default=1.0)
    stale_rate = _rate(stale_older_than_96h, matched_count, default=0.0)

    freshness_score = 100.0 * (
        matched_rate * 0.25
        + _score_between(within_48h_rate, 0.5, 0.85) * 0.25
        + _score_between(within_72h_rate, 0.7, 0.95) * 0.35
        + _score_inverse(stale_rate, 0.03, 0.2) * 0.15
    )

    retrieval_pool_scores: dict[str, float] = {}
    for section in SECTION_KEYS:
        raw_count = raw_counts[section]
        expected = max(1, expected_counts[section])
        if raw_count <= 0:
            retrieval_pool_scores[section] = 0.0 if expected_counts[section] > 0 else 1.0
            continue
        good_target = max(expected * 6, 10)
        retrieval_pool_scores[section] = _score_between(float(raw_count), max(1.0, float(expected)), float(good_target))

    seed_score, seed_section_scores = _rolling_seed_score(snapshot_payload)
    retrieval_score = 100.0 * (
        (sum(retrieval_pool_scores.values()) / len(SECTION_KEYS)) * 0.7
        + seed_score * 0.3
    )

    overall_score = (
        completeness_score * 0.28
        + diversity_score * 0.24
        + summary_score * 0.20
        + freshness_score * 0.18
        + retrieval_score * 0.10
    )

    if overall_score >= 85.0:
        status = "pass"
    elif overall_score >= 70.0:
        status = "warn"
    else:
        status = "fail"

    low_sections = [section for section in SECTION_KEYS if section_fill_scores[section] < 0.7 and raw_counts[section] >= 6]
    improvement_hints: list[str] = []
    if low_sections:
        improvement_hints.append(
            "선정 결과가 약한 섹션이 있습니다: "
            + ", ".join(low_sections)
            + ". 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다."
        )
    if title_unique_rate < 0.8 or surface_reuse_penalty > 0.1:
        improvement_hints.append("동일 이슈가 브리핑/품목 보드에 반복 노출됩니다. story signature 중복 억제와 commodity surface 재사용 상한이 필요합니다.")
    if summary_length_ok_rate < 0.85 or summary_numeric_rate < 0.25 or summary_opening_diversity < 0.7:
        improvement_hints.append("요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.")
    if within_72h_rate < 0.85 or stale_rate > 0.08:
        improvement_hints.append("최신성 점수가 내려갔습니다. 동일 이벤트 중 최신 기사 우선, 96시간 초과 기사 감점을 더 강하게 주는 편이 안정적입니다.")
    if seed_section_scores and any(score < 0.5 for score in seed_section_scores.values()):
        weak_seed_sections = [section for section, score in seed_section_scores.items() if score < 0.5]
        improvement_hints.append("리콜 시드 결손이 보입니다: " + ", ".join(weak_seed_sections) + ". query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.")

    if not improvement_hints:
        improvement_hints.append("전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.")

    result = {
        "report_date": report_date,
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "status": status,
        "overall_score": round(overall_score, 2),
        "scores": {
            "completeness": round(completeness_score, 2),
            "diversity": round(diversity_score, 2),
            "summary_quality": round(summary_score, 2),
            "freshness": round(freshness_score, 2),
            "retrieval_support": round(retrieval_score, 2),
        },
        "counts": {
            "briefing_total": len(briefing_articles),
            "commodity_total": len(commodity_articles),
            "briefing_by_section": briefing_counts,
            "core_by_section": core_counts,
            "commodity_by_section": commodity_counts,
            "raw_by_section": raw_counts,
            "expected_briefing_by_section": expected_counts,
        },
        "metrics": {
            "briefing_title_unique_rate": round(title_unique_rate, 4),
            "briefing_domain_diversity_rate": round(domain_diversity_rate, 4),
            "surface_reuse_penalty": round(surface_reuse_penalty, 4),
            "summary_presence_rate": round(summary_presence_rate, 4),
            "summary_length_ok_rate": round(summary_length_ok_rate, 4),
            "summary_numeric_rate": round(summary_numeric_rate, 4),
            "summary_opening_diversity": round(summary_opening_diversity, 4),
            "matched_article_rate": round(matched_rate, 4),
            "within_48h_rate": round(within_48h_rate, 4),
            "within_72h_rate": round(within_72h_rate, 4),
            "stale_over_96h_rate": round(stale_rate, 4),
            "seed_coverage_score": round(seed_score, 4),
        },
        "section_scores": {
            "briefing_fill": {section: round(section_fill_scores[section], 4) for section in SECTION_KEYS},
            "core_fill": {section: round(core_fill_scores[section], 4) for section in SECTION_KEYS},
            "retrieval_pool": {section: round(retrieval_pool_scores[section], 4) for section in SECTION_KEYS},
            "seed_coverage": {section: round(score, 4) for section, score in seed_section_scores.items()},
        },
        "freshness_samples": sorted(freshness_samples, key=lambda item: item["age_hours"], reverse=True)[:8],
        "improvement_hints": improvement_hints,
    }
    result["summary_prompt_feedback"] = build_summary_feedback(result)
    return result


def build_summary_feedback(result: dict[str, Any]) -> list[str]:
    metrics = result.get("metrics", {}) if isinstance(result, dict) else {}
    feedback: list[str] = []

    if float(metrics.get("summary_length_ok_rate", 1.0)) < 0.9:
        feedback.append("각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.")
    if float(metrics.get("summary_numeric_rate", 1.0)) < 0.3:
        feedback.append("기사에 수치가 있으면 최소 1개는 요약에 남기고, 없으면 대응 주체나 시점을 또렷하게 적는다.")
    if float(metrics.get("summary_opening_diversity", 1.0)) < 0.75:
        feedback.append("같은 시작 표현을 반복하지 말고 첫 문장은 품목/지역/이슈, 둘째 문장은 대응/영향으로 구분한다.")
    if float(metrics.get("briefing_title_unique_rate", 1.0)) < 0.85:
        feedback.append("동일 이벤트로 보이는 기사들은 표현을 달리해도 같은 결로 요약하지 말고 차별점이 있을 때만 강조한다.")
    if float(metrics.get("within_72h_rate", 1.0)) < 0.9:
        feedback.append("오래된 기사일수록 배경 설명은 줄이고 이번 보고일 기준으로 새롭게 확인된 조치나 수급 신호를 먼저 적는다.")

    if not feedback:
        feedback = [
            "각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.",
            "기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.",
            "비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.",
        ]
    return feedback[:4]


def render_summary_feedback_text(result: dict[str, Any]) -> str:
    lines = [f"- {item}" for item in build_summary_feedback(result)]
    return "\n".join(lines) + "\n"


def render_evaluation_markdown(result: dict[str, Any]) -> str:
    counts = result.get("counts", {})
    metrics = result.get("metrics", {})
    scores = result.get("scores", {})
    section_counts = counts.get("briefing_by_section", {})
    raw_counts = counts.get("raw_by_section", {})
    expected_counts = counts.get("expected_briefing_by_section", {})

    section_summary = ", ".join(
        f"{section}:{section_counts.get(section, 0)}/{expected_counts.get(section, 0)} raw={raw_counts.get(section, 0)}"
        for section in SECTION_KEYS
    )
    hint_lines = "\n".join(f"- {item}" for item in result.get("improvement_hints", []))
    feedback_lines = "\n".join(f"- {item}" for item in result.get("summary_prompt_feedback", []))

    return (
        f"## Daily Eval ({result.get('report_date', '')})\n"
        f"- Overall: **{result.get('overall_score', 0):.2f}** ({result.get('status', 'unknown')})\n"
        f"- Scores: completeness={scores.get('completeness', 0):.1f}, diversity={scores.get('diversity', 0):.1f}, "
        f"summary={scores.get('summary_quality', 0):.1f}, freshness={scores.get('freshness', 0):.1f}, "
        f"retrieval={scores.get('retrieval_support', 0):.1f}\n"
        f"- Briefing cards: {counts.get('briefing_total', 0)} / Commodity cards: {counts.get('commodity_total', 0)}\n"
        f"- Sections: {section_summary}\n"
        f"- Metrics: title_unique={metrics.get('briefing_title_unique_rate', 0):.2f}, "
        f"domain_diversity={metrics.get('briefing_domain_diversity_rate', 0):.2f}, "
        f"summary_presence={metrics.get('summary_presence_rate', 0):.2f}, "
        f"summary_numeric={metrics.get('summary_numeric_rate', 0):.2f}, "
        f"fresh_72h={metrics.get('within_72h_rate', 0):.2f}\n\n"
        f"### Improvement Hints\n"
        f"{hint_lines}\n\n"
        f"### Next Summary Feedback\n"
        f"{feedback_lines}\n"
    )


def result_to_history_entry(result: dict[str, Any]) -> dict[str, Any]:
    counts = result.get("counts", {})
    metrics = result.get("metrics", {})
    return {
        "report_date": result.get("report_date"),
        "generated_at_kst": result.get("generated_at_kst"),
        "overall_score": result.get("overall_score"),
        "status": result.get("status"),
        "briefing_total": counts.get("briefing_total", 0),
        "commodity_total": counts.get("commodity_total", 0),
        "summary_presence_rate": metrics.get("summary_presence_rate", 0),
        "within_72h_rate": metrics.get("within_72h_rate", 0),
        "briefing_title_unique_rate": metrics.get("briefing_title_unique_rate", 0),
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, body: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
