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
_WEAK_SELECTION_STAGE_TOKENS = ("backfill", "bridge", "swap", "recycle")
_QUALITY_STAGE_PREFIXES = ("dist_anchor", "supply_board", "supply_feature")
_COMMODITY_ISSUE_TERMS = (
    "가격",
    "수급",
    "출하",
    "반입",
    "경락",
    "도매",
    "공판",
    "작황",
    "피해",
    "병해충",
    "방제",
    "생산량",
    "공급",
    "재배면적",
    "수출",
    "저장",
    "안정",
    "폭락",
    "폭등",
    "급등",
    "급락",
    "하락",
    "상승",
    "물량",
)
_COMMODITY_WEAK_TERMS = (
    "교육",
    "총회",
    "인터뷰",
    "행사",
    "축제",
    "체험",
    "홍보",
    "맛집",
    "레시피",
    "요리",
    "뷰티",
    "협약",
    "개소",
    "개장",
    "선정",
    "브랜드",
    "시식",
)


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
    item_key: str = ""
    item_label: str = ""
    representative_rank: int = -1
    representative_score: float = 0.0
    board_score: float = 0.0
    selection_fit_score: float = 0.0
    selection_stage: str = ""


def _float_attr(value: Any) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return 0.0


def _int_attr(value: str | None, default: int = -1) -> int:
    try:
        return int(str(value or "").strip())
    except (TypeError, ValueError):
        return default


def _bool_attr(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


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
                    is_core=_bool_attr(attr_map.get("data-is-core")),
                    item_key=str(attr_map.get("data-item-key", "")).strip(),
                    item_label=str(attr_map.get("data-item-label", "")).strip(),
                    representative_rank=_int_attr(attr_map.get("data-representative-rank")),
                    representative_score=_float_attr(attr_map.get("data-representative-score")),
                    board_score=_float_attr(attr_map.get("data-board-score")),
                    selection_fit_score=_float_attr(attr_map.get("data-selection-fit")),
                    selection_stage=str(attr_map.get("data-selection-stage", "")).strip(),
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


def _iter_snapshot_items(snapshot_payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    raw_by_section = snapshot_payload.get("raw_by_section", {})
    if not isinstance(raw_by_section, dict):
        return items
    for section, section_items in raw_by_section.items():
        if not isinstance(section_items, list):
            continue
        for item in section_items:
            if not isinstance(item, dict):
                continue
            payload = dict(item)
            payload.setdefault("section", str(section or "").strip())
            items.append(payload)
    return items


def _selection_fit(item: dict[str, Any] | None) -> float:
    if not isinstance(item, dict):
        return 0.0
    return _float_attr(item.get("selection_fit_score") or item.get("fit_score") or item.get("fit"))


def _selection_stage(item: dict[str, Any] | None) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("selection_stage") or item.get("stage") or "").strip()


def _stage_has_core_signal(stage: str) -> bool:
    return "core" in str(stage or "").strip().lower()


def _stage_is_weak(stage: str) -> bool:
    stage_l = str(stage or "").strip().lower()
    if not stage_l:
        return False
    if any(stage_l.startswith(p) for p in _QUALITY_STAGE_PREFIXES):
        return False
    return any(token in stage_l for token in _WEAK_SELECTION_STAGE_TOKENS)


def _score_percentile(item: dict[str, Any] | None, pool: list[dict[str, Any]]) -> float:
    target = _float_attr((item or {}).get("score") if isinstance(item, dict) else 0.0)
    scores = [
        _float_attr(candidate.get("score"))
        for candidate in pool
        if isinstance(candidate, dict)
    ]
    if not scores:
        return 0.5
    lower_or_equal = sum(1 for score in scores if score <= target)
    return _rate(lower_or_equal, len(scores), default=0.5)


def _item_alias_terms(label: str) -> list[str]:
    raw = _normalize_spaces(label)
    aliases = {raw.lower(), raw.replace(" ", "").lower()}
    aliases.update(part.lower() for part in re.split(r"[\s/·,()]+", raw) if part.strip())
    return [alias for alias in aliases if alias]


def _contains_any_term(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    haystack = _normalize_spaces(text).lower()
    return any(str(term or "").lower() in haystack for term in terms if str(term or "").strip())


def _commodity_item_focus(article: SurfaceArticle) -> bool:
    if not article.item_label:
        return False
    title_l = _normalize_spaces(article.title).lower()
    title_compact = title_l.replace(" ", "")
    for alias in _item_alias_terms(article.item_label):
        if alias in title_l or alias.replace(" ", "") in title_compact:
            return True
    return False


def _has_representative_issue_signal(title: str, body: str) -> bool:
    text = f"{title} {body}"
    for noise in ("공선출하회", "공동출하회", "출하회", "출하식"):
        text = text.replace(noise, " ")
    return _contains_any_term(text, _COMMODITY_ISSUE_TERMS)


def _is_weak_commodity_representative(title: str, body: str) -> bool:
    text = f"{title} {body}"
    return _contains_any_term(text, _COMMODITY_WEAK_TERMS) and not _has_representative_issue_signal(title, body)


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
    for item in _iter_snapshot_items(snapshot_payload):
        for key in ("link", "originallink", "canon_url", "url"):
            url_key = normalize_url(str(item.get(key, "") or ""))
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


def _average(values: list[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def evaluate_report(report_date: str, html_text: str, snapshot_payload: dict[str, Any]) -> dict[str, Any]:
    articles = parse_report_html(html_text)
    briefing_articles = [article for article in articles if article.surface == BRIEFING_SURFACE]
    commodity_articles = [article for article in articles if article.surface in COMMODITY_SURFACES]
    commodity_primary_articles = [article for article in commodity_articles if article.surface == "commodity_primary"]
    all_surface_articles = briefing_articles + commodity_articles

    raw_by_section = snapshot_payload.get("raw_by_section", {})
    if not isinstance(raw_by_section, dict):
        raw_by_section = {}
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
    section_raw_pools = {
        section: list(raw_by_section.get(section, [])) if isinstance(raw_by_section.get(section, []), list) else []
        for section in SECTION_KEYS
    }
    matched_count = 0
    within_48h = 0
    within_72h = 0
    stale_older_than_96h = 0
    freshness_samples: list[dict[str, Any]] = []
    briefing_match_records: list[dict[str, Any]] = []

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
        title_candidates = list(by_title.get(normalize_title_key(article.title), []))
        best_fit = _selection_fit(match)
        best_section = str(match.get("section", "")).strip() or article.section
        for candidate in title_candidates:
            candidate_fit = _selection_fit(candidate)
            if candidate_fit > best_fit:
                best_fit = candidate_fit
                best_section = str(candidate.get("section", "")).strip() or best_section
        fit_score = _selection_fit(match)
        stage = _selection_stage(match)
        briefing_match_records.append(
            {
                "title": article.title,
                "section": article.section,
                "is_core": bool(article.is_core),
                "fit_score": fit_score,
                "stage": stage,
                "score_percentile": _score_percentile(match, section_raw_pools.get(article.section, [])),
                "cross_section_gap": max(0.0, best_fit - fit_score),
                "best_section": best_section,
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

    section_fit_values = [float(record.get("fit_score") or 0.0) for record in briefing_match_records]
    section_alignment_fit_avg = _average(section_fit_values)
    section_alignment_low_fit_rate = _rate(
        sum(1 for record in briefing_match_records if float(record.get("fit_score") or 0.0) < 0.85),
        len(briefing_match_records),
        default=0.0,
    )
    section_alignment_cross_gap_rate = _rate(
        sum(
            1
            for record in briefing_match_records
            if float(record.get("cross_section_gap") or 0.0) >= 0.35
            and str(record.get("best_section") or "") != str(record.get("section") or "")
        ),
        len(briefing_match_records),
        default=0.0,
    )
    section_alignment_weak_stage_rate = _rate(
        sum(1 for record in briefing_match_records if _stage_is_weak(str(record.get("stage") or ""))),
        len(briefing_match_records),
        default=0.0,
    )
    section_alignment_score = 100.0 * (
        _score_between(section_alignment_fit_avg, 0.8, 1.35) * 0.45
        + _score_inverse(section_alignment_low_fit_rate, 0.08, 0.3) * 0.2
        + _score_inverse(section_alignment_cross_gap_rate, 0.02, 0.18) * 0.2
        + _score_inverse(section_alignment_weak_stage_rate, 0.06, 0.24) * 0.15
    )

    section_alignment_section_scores: dict[str, float] = {}
    for section in SECTION_KEYS:
        records = [record for record in briefing_match_records if record.get("section") == section]
        if not records:
            section_alignment_section_scores[section] = 1.0 if briefing_counts[section] <= 0 else 0.0
            continue
        fit_avg = _average([float(record.get("fit_score") or 0.0) for record in records])
        low_fit_rate = _rate(sum(1 for record in records if float(record.get("fit_score") or 0.0) < 0.85), len(records))
        section_alignment_section_scores[section] = (
            _score_between(fit_avg, 0.8, 1.35) * 0.7
            + _score_inverse(low_fit_rate, 0.08, 0.3) * 0.3
        )

    core_match_records = [record for record in briefing_match_records if bool(record.get("is_core"))]
    core_fit_avg = _average([float(record.get("fit_score") or 0.0) for record in core_match_records])
    core_rank_percentile_avg = _average([float(record.get("score_percentile") or 0.0) for record in core_match_records], default=0.5)
    core_stage_core_rate = _rate(
        sum(1 for record in core_match_records if _stage_has_core_signal(str(record.get("stage") or ""))),
        len(core_match_records),
        default=0.0,
    )
    weak_core_rate = _rate(
        sum(
            1
            for record in core_match_records
            if float(record.get("fit_score") or 0.0) < 0.95
            or float(record.get("score_percentile") or 0.0) < 0.6
            or _stage_is_weak(str(record.get("stage") or ""))
        ),
        len(core_match_records),
        default=0.0,
    )
    if core_counts and sum(core_counts.values()) == 0 and briefing_articles:
        core_quality_score = 0.0
    elif core_match_records:
        core_quality_score = 100.0 * (
            _score_between(core_fit_avg, 0.95, 1.5) * 0.45
            + _score_between(core_rank_percentile_avg, 0.55, 0.9) * 0.25
            + _score_between(core_stage_core_rate, 0.35, 0.8) * 0.15
            + _score_inverse(weak_core_rate, 0.05, 0.35) * 0.15
        )
    else:
        core_quality_score = 40.0 if briefing_articles else 100.0

    core_quality_section_scores: dict[str, float] = {}
    for section in SECTION_KEYS:
        records = [record for record in core_match_records if record.get("section") == section]
        if not records:
            core_quality_section_scores[section] = 1.0 if core_counts[section] <= 0 else 0.0
            continue
        fit_avg = _average([float(record.get("fit_score") or 0.0) for record in records])
        pct_avg = _average([float(record.get("score_percentile") or 0.0) for record in records], default=0.5)
        weak_rate = _rate(
            sum(
                1
                for record in records
                if float(record.get("fit_score") or 0.0) < 0.95
                or float(record.get("score_percentile") or 0.0) < 0.6
                or _stage_is_weak(str(record.get("stage") or ""))
            ),
            len(records),
        )
        core_quality_section_scores[section] = (
            _score_between(fit_avg, 0.95, 1.5) * 0.55
            + _score_between(pct_avg, 0.55, 0.9) * 0.25
            + _score_inverse(weak_rate, 0.05, 0.35) * 0.2
        )

    commodity_primary_records: list[dict[str, Any]] = []
    for article in commodity_primary_articles:
        match = _find_snapshot_match(article, by_url, by_title)
        body = ""
        if isinstance(match, dict):
            body = _normalize_spaces(
                " ".join(
                    str(match.get(field) or "")
                    for field in ("description", "summary", "desc")
                    if str(match.get(field) or "").strip()
                )
            )
        fit_score = float(article.selection_fit_score or 0.0) or _selection_fit(match)
        stage = article.selection_stage or _selection_stage(match)
        representative_rank = int(article.representative_rank)
        if representative_rank < 0:
            if _stage_has_core_signal(stage) and fit_score >= 1.3:
                representative_rank = 3
            elif fit_score >= 0.9:
                representative_rank = 1
            else:
                representative_rank = 0
        commodity_primary_records.append(
            {
                "title": article.title,
                "item_label": article.item_label,
                "item_focus": _commodity_item_focus(article),
                "issue_signal": _has_representative_issue_signal(article.title, body),
                "weak_story": _is_weak_commodity_representative(article.title, body),
                "fit_score": fit_score,
                "representative_rank": representative_rank,
            }
        )

    commodity_primary_item_focus_rate = _rate(
        sum(1 for record in commodity_primary_records if bool(record.get("item_focus"))),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_issue_signal_rate = _rate(
        sum(1 for record in commodity_primary_records if bool(record.get("issue_signal"))),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_weak_rate = _rate(
        sum(1 for record in commodity_primary_records if bool(record.get("weak_story"))),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_fit_avg = _average([float(record.get("fit_score") or 0.0) for record in commodity_primary_records])
    commodity_primary_rank_avg = _average(
        [float(record.get("representative_rank") or 0.0) for record in commodity_primary_records],
        default=0.0,
    )
    if commodity_articles and not commodity_primary_articles:
        commodity_board_quality_score = 0.0
    elif commodity_primary_records:
        commodity_board_quality_score = 100.0 * (
            commodity_primary_item_focus_rate * 0.28
            + _score_between(commodity_primary_issue_signal_rate, 0.45, 0.8) * 0.25
            + _score_inverse(commodity_primary_weak_rate, 0.05, 0.25) * 0.22
            + _score_between(commodity_primary_fit_avg, 0.8, 1.35) * 0.15
            + _score_between(commodity_primary_rank_avg, 1.4, 3.2) * 0.1
        )
    else:
        commodity_board_quality_score = 100.0

    overall_score = (
        completeness_score * 0.20
        + diversity_score * 0.18
        + summary_score * 0.16
        + freshness_score * 0.14
        + retrieval_score * 0.08
        + section_alignment_score * 0.12
        + core_quality_score * 0.07
        + commodity_board_quality_score * 0.05
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
    if section_alignment_score < 78.0 or section_alignment_low_fit_rate > 0.18 or section_alignment_cross_gap_rate > 0.1:
        improvement_hints.append(
            "섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요."
        )
    if core_quality_score < 78.0 or weak_core_rate > 0.18:
        improvement_hints.append(
            "핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요."
        )
    if commodity_board_quality_score < 80.0 or commodity_primary_weak_rate > 0.15 or commodity_primary_item_focus_rate < 0.9:
        improvement_hints.append(
            "품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요."
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
            "section_alignment": round(section_alignment_score, 2),
            "core_quality": round(core_quality_score, 2),
            "commodity_board_quality": round(commodity_board_quality_score, 2),
        },
        "counts": {
            "briefing_total": len(briefing_articles),
            "commodity_total": len(commodity_articles),
            "commodity_primary_total": len(commodity_primary_articles),
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
            "section_alignment_fit_avg": round(section_alignment_fit_avg, 4),
            "section_alignment_low_fit_rate": round(section_alignment_low_fit_rate, 4),
            "section_alignment_cross_gap_rate": round(section_alignment_cross_gap_rate, 4),
            "section_alignment_weak_stage_rate": round(section_alignment_weak_stage_rate, 4),
            "core_fit_avg": round(core_fit_avg, 4),
            "core_rank_percentile_avg": round(core_rank_percentile_avg, 4),
            "core_stage_core_rate": round(core_stage_core_rate, 4),
            "weak_core_rate": round(weak_core_rate, 4),
            "commodity_primary_item_focus_rate": round(commodity_primary_item_focus_rate, 4),
            "commodity_primary_issue_signal_rate": round(commodity_primary_issue_signal_rate, 4),
            "commodity_primary_weak_rate": round(commodity_primary_weak_rate, 4),
            "commodity_primary_fit_avg": round(commodity_primary_fit_avg, 4),
            "commodity_primary_rank_avg": round(commodity_primary_rank_avg, 4),
        },
        "section_scores": {
            "briefing_fill": {section: round(section_fill_scores[section], 4) for section in SECTION_KEYS},
            "core_fill": {section: round(core_fill_scores[section], 4) for section in SECTION_KEYS},
            "retrieval_pool": {section: round(retrieval_pool_scores[section], 4) for section in SECTION_KEYS},
            "seed_coverage": {section: round(score, 4) for section, score in seed_section_scores.items()},
            "section_alignment": {section: round(section_alignment_section_scores[section], 4) for section in SECTION_KEYS},
            "core_quality": {section: round(core_quality_section_scores[section], 4) for section in SECTION_KEYS},
        },
        "freshness_samples": sorted(freshness_samples, key=lambda item: item["age_hours"], reverse=True)[:8],
        "improvement_hints": improvement_hints,
    }
    result["selection_guardrails"] = build_selection_guardrails(result)
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
    if float(metrics.get("weak_core_rate", 0.0)) > 0.2:
        feedback.append("핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.")

    if not feedback:
        feedback = [
            "각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.",
            "기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.",
            "비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.",
        ]
    return feedback[:4]


def build_selection_guardrails(result: dict[str, Any]) -> dict[str, Any]:
    scores = result.get("scores", {}) if isinstance(result, dict) else {}
    metrics = result.get("metrics", {}) if isinstance(result, dict) else {}

    section_alignment_score = float(scores.get("section_alignment", 100.0) or 100.0)
    core_quality_score = float(scores.get("core_quality", 100.0) or 100.0)
    commodity_board_quality_score = float(scores.get("commodity_board_quality", 100.0) or 100.0)

    section_alignment_low_fit_rate = float(metrics.get("section_alignment_low_fit_rate", 0.0) or 0.0)
    section_alignment_cross_gap_rate = float(metrics.get("section_alignment_cross_gap_rate", 0.0) or 0.0)
    weak_core_rate = float(metrics.get("weak_core_rate", 0.0) or 0.0)
    commodity_primary_item_focus_rate = float(metrics.get("commodity_primary_item_focus_rate", 1.0) or 1.0)
    commodity_primary_issue_signal_rate = float(metrics.get("commodity_primary_issue_signal_rate", 1.0) or 1.0)
    commodity_primary_weak_rate = float(metrics.get("commodity_primary_weak_rate", 0.0) or 0.0)

    section_card_min_fit = {
        "default": 0.8,
        "supply": 0.82,
        "policy": 0.82,
        "dist": 0.95,
        "pest": 0.78,
    }
    core_fit_min = {
        "default": 1.2,
        "supply": 1.4,
        "policy": 1.4,
        "dist": 1.6,
        "pest": 1.2,
    }
    core_relaxed_min_fit = {
        "default": 1.0,
        "supply": 1.18,
        "policy": 1.15,
        "dist": 1.35,
        "pest": 1.0,
    }
    low_fit_rescue_min = 0.15
    high_score_low_fit_rescue_margin = 3.0
    tail_score_floor_delta = 0.0
    disable_relaxed_core_fill = False
    commodity_active_min_rank = 1
    commodity_program_core_min_rank = 1
    commodity_require_issue_signal = False
    commodity_require_direct_item_focus = False

    reasons: list[str] = []

    if (
        section_alignment_score < 78.0
        or section_alignment_low_fit_rate > 0.18
        or section_alignment_cross_gap_rate > 0.1
    ):
        reasons.append("section_alignment")
        for key, delta in (("supply", 0.08), ("policy", 0.08), ("dist", 0.12), ("pest", 0.06)):
            section_card_min_fit[key] += delta
        section_card_min_fit["default"] += 0.08
        low_fit_rescue_min = max(low_fit_rescue_min, 0.3)
        high_score_low_fit_rescue_margin = max(high_score_low_fit_rescue_margin, 4.0)
        tail_score_floor_delta += 0.6

    if (
        section_alignment_score < 65.0
        or section_alignment_low_fit_rate > 0.26
        or section_alignment_cross_gap_rate > 0.14
    ):
        reasons.append("section_alignment_severe")
        for key, delta in (("supply", 0.08), ("policy", 0.08), ("dist", 0.1), ("pest", 0.06)):
            section_card_min_fit[key] += delta
        section_card_min_fit["default"] += 0.08
        low_fit_rescue_min = max(low_fit_rescue_min, 0.45)
        high_score_low_fit_rescue_margin = max(high_score_low_fit_rescue_margin, 4.8)
        tail_score_floor_delta += 0.4

    if core_quality_score < 78.0 or weak_core_rate > 0.18:
        reasons.append("core_quality")
        for key in ("default", "supply", "policy", "dist", "pest"):
            core_fit_min[key] += 0.08
            core_relaxed_min_fit[key] += 0.12
        disable_relaxed_core_fill = weak_core_rate > 0.32 or core_quality_score < 68.0

    if core_quality_score < 55.0 or weak_core_rate > 0.5:
        reasons.append("core_quality_severe")
        for key in ("default", "supply", "policy", "dist", "pest"):
            core_fit_min[key] += 0.08
            core_relaxed_min_fit[key] += 0.1
        disable_relaxed_core_fill = True

    if (
        commodity_board_quality_score < 80.0
        or commodity_primary_weak_rate > 0.15
        or commodity_primary_item_focus_rate < 0.9
    ):
        reasons.append("commodity_board")
        commodity_active_min_rank = 2
        commodity_program_core_min_rank = 3
        commodity_require_direct_item_focus = (
            commodity_primary_item_focus_rate < 0.96 or commodity_primary_weak_rate > 0.12
        )
        commodity_require_issue_signal = (
            commodity_primary_issue_signal_rate < 0.7 or commodity_primary_weak_rate > 0.15
        )

    if commodity_board_quality_score < 68.0 or commodity_primary_weak_rate > 0.25:
        reasons.append("commodity_board_severe")
        commodity_active_min_rank = 2
        commodity_program_core_min_rank = 3
        commodity_require_direct_item_focus = True
        commodity_require_issue_signal = True

    # ── ceiling caps: 가드레일이 지나치게 엄격해져 기사 선정 자체가 불가능한 피드백 루프를 방지 ──
    _CAPS: dict[str, float] = {
        "section_card_min_fit": 1.05,
        "core_fit_min": 1.7,
        "core_relaxed_min_fit": 1.5,
        "tail_score_floor_delta": 0.8,
        "section_low_fit_rescue_min": 0.5,
        "high_score_low_fit_rescue_margin": 5.5,
    }
    for key in section_card_min_fit:
        section_card_min_fit[key] = min(section_card_min_fit[key], _CAPS["section_card_min_fit"])
    for key in core_fit_min:
        core_fit_min[key] = min(core_fit_min[key], _CAPS["core_fit_min"])
    for key in core_relaxed_min_fit:
        core_relaxed_min_fit[key] = min(core_relaxed_min_fit[key], _CAPS["core_relaxed_min_fit"])
    tail_score_floor_delta = min(tail_score_floor_delta, _CAPS["tail_score_floor_delta"])
    low_fit_rescue_min = min(low_fit_rescue_min, _CAPS["section_low_fit_rescue_min"])
    high_score_low_fit_rescue_margin = min(high_score_low_fit_rescue_margin, _CAPS["high_score_low_fit_rescue_margin"])

    def _round_map(values: dict[str, float]) -> dict[str, float]:
        return {key: round(float(value), 3) for key, value in values.items()}

    return {
        "driver_tags": list(dict.fromkeys(reasons)),
        "section_card_min_fit": _round_map(section_card_min_fit),
        "section_low_fit_rescue_min": round(low_fit_rescue_min, 3),
        "high_score_low_fit_rescue_margin": round(high_score_low_fit_rescue_margin, 3),
        "tail_score_floor_delta": round(tail_score_floor_delta, 3),
        "core_fit_min": _round_map(core_fit_min),
        "core_relaxed_min_fit": _round_map(core_relaxed_min_fit),
        "disable_relaxed_core_fill": bool(disable_relaxed_core_fill),
        "commodity_active_min_rank": int(commodity_active_min_rank),
        "commodity_program_core_min_rank": int(commodity_program_core_min_rank),
        "commodity_require_issue_signal": bool(commodity_require_issue_signal),
        "commodity_require_direct_item_focus": bool(commodity_require_direct_item_focus),
    }


def build_selection_feedback_payload(result: dict[str, Any]) -> dict[str, Any]:
    scores = result.get("scores", {}) if isinstance(result, dict) else {}
    metrics = result.get("metrics", {}) if isinstance(result, dict) else {}
    guardrails = result.get("selection_guardrails")
    if not isinstance(guardrails, dict):
        guardrails = build_selection_guardrails(result)

    return {
        "report_date": result.get("report_date"),
        "generated_at_kst": result.get("generated_at_kst"),
        "scores": {
            "section_alignment": round(float(scores.get("section_alignment", 0.0) or 0.0), 2),
            "core_quality": round(float(scores.get("core_quality", 0.0) or 0.0), 2),
            "commodity_board_quality": round(float(scores.get("commodity_board_quality", 0.0) or 0.0), 2),
        },
        "metrics": {
            "section_alignment_low_fit_rate": round(float(metrics.get("section_alignment_low_fit_rate", 0.0) or 0.0), 4),
            "section_alignment_cross_gap_rate": round(float(metrics.get("section_alignment_cross_gap_rate", 0.0) or 0.0), 4),
            "weak_core_rate": round(float(metrics.get("weak_core_rate", 0.0) or 0.0), 4),
            "commodity_primary_item_focus_rate": round(float(metrics.get("commodity_primary_item_focus_rate", 0.0) or 0.0), 4),
            "commodity_primary_issue_signal_rate": round(float(metrics.get("commodity_primary_issue_signal_rate", 0.0) or 0.0), 4),
            "commodity_primary_weak_rate": round(float(metrics.get("commodity_primary_weak_rate", 0.0) or 0.0), 4),
        },
        "selection_guardrails": guardrails,
    }


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
        f"retrieval={scores.get('retrieval_support', 0):.1f}, section_fit={scores.get('section_alignment', 0):.1f}, "
        f"core={scores.get('core_quality', 0):.1f}, commodity={scores.get('commodity_board_quality', 0):.1f}\n"
        f"- Briefing cards: {counts.get('briefing_total', 0)} / Commodity cards: {counts.get('commodity_total', 0)}\n"
        f"- Sections: {section_summary}\n"
        f"- Metrics: title_unique={metrics.get('briefing_title_unique_rate', 0):.2f}, "
        f"domain_diversity={metrics.get('briefing_domain_diversity_rate', 0):.2f}, "
        f"summary_presence={metrics.get('summary_presence_rate', 0):.2f}, "
        f"summary_numeric={metrics.get('summary_numeric_rate', 0):.2f}, "
        f"fresh_72h={metrics.get('within_72h_rate', 0):.2f}, "
        f"fit_avg={metrics.get('section_alignment_fit_avg', 0):.2f}, "
        f"weak_core={metrics.get('weak_core_rate', 0):.2f}, "
        f"commodity_weak={metrics.get('commodity_primary_weak_rate', 0):.2f}\n\n"
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
        "section_alignment": result.get("scores", {}).get("section_alignment", 0),
        "core_quality": result.get("scores", {}).get("core_quality", 0),
        "commodity_board_quality": result.get("scores", {}).get("commodity_board_quality", 0),
        "briefing_total": counts.get("briefing_total", 0),
        "commodity_total": counts.get("commodity_total", 0),
        "summary_presence_rate": metrics.get("summary_presence_rate", 0),
        "within_72h_rate": metrics.get("within_72h_rate", 0),
        "briefing_title_unique_rate": metrics.get("briefing_title_unique_rate", 0),
        "guardrail_driver_tags": (result.get("selection_guardrails") or {}).get("driver_tags", []),
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, body: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
