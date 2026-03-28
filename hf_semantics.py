from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Sequence


SessionFactory = Callable[[], Any]


@dataclass(frozen=True)
class HFSemanticConfig:
    api_token: str
    model: str = "intfloat/multilingual-e5-large"
    endpoint_template: str = "https://router.huggingface.co/hf-inference/models/{model}"
    timeout_sec: float = 20.0
    max_candidates: int = 12
    max_boost: float = 0.9
    min_candidates: int = 2

    def endpoint_url(self) -> str:
        return self.endpoint_template.format(model=self.model)


@dataclass(frozen=True)
class SemanticAdjustment:
    similarity: float
    boost: float
    model: str


_SECTION_INTENTS: dict[str, str] = {
    "supply": "원예 품목의 수급, 가격, 출하, 작황, 재고, 반입, 생산 차질, 품목별 시장 영향",
    "policy": "농산물 가격 안정 대책, 지원 정책, 검역, 할당관세, 단속, 제도 개편, 정부 공식 브리핑",
    "dist": "도매시장, 공판장, APC, 산지유통, 온라인 도매시장, 수출 물류, 선적, 검역 현장 운영",
    "pest": "병해충, 냉해, 저온피해, 방제, 예찰, 생육 리스크, 과수화상병, 탄저병, 해충 확산 대응",
}


def _take_unique(values: Sequence[Any], limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = str(raw or "").strip()
        if (not text) or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def build_section_profile(section_conf: dict[str, Any]) -> str:
    key = str(section_conf.get("key") or "").strip()
    title = str(section_conf.get("title") or key or "agri news").strip()
    intent = _SECTION_INTENTS.get(key, "농업 기사 중 섹션 핵심성과 직접 관련된 기사")
    queries = _take_unique(section_conf.get("queries") or [], 8)
    must_terms = _take_unique(section_conf.get("must_terms") or [], 12)

    parts = [
        f"query: {title}",
        f"의도: {intent}",
    ]
    if queries:
        parts.append("대표 질의: " + ", ".join(queries))
    if must_terms:
        parts.append("핵심 신호: " + ", ".join(must_terms))
    return ". ".join(parts).strip()


def build_article_passage(article: Any) -> str:
    title = str(getattr(article, "title", "") or "").strip()
    desc = str(getattr(article, "description", "") or "").strip()
    press = str(getattr(article, "press", "") or "").strip()
    source_query = str(getattr(article, "source_query", "") or "").strip()

    parts = [f"passage: 제목 {title}"]
    if desc:
        parts.append(f"요약 {desc}")
    if press:
        parts.append(f"매체 {press}")
    if source_query:
        parts.append(f"수집질의 {source_query}")
    return ". ".join(parts).strip()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and (not isinstance(value, bool))


def _mean_pool(matrix: Sequence[Any]) -> list[float]:
    rows = [row for row in matrix if isinstance(row, list) and row]
    if not rows:
        return []

    width = min(len(row) for row in rows if all(_is_number(v) for v in row))
    if width <= 0:
        return []

    pooled = [0.0] * width
    used = 0
    for row in rows:
        if (not isinstance(row, list)) or len(row) < width or (not all(_is_number(v) for v in row[:width])):
            continue
        for idx in range(width):
            pooled[idx] += float(row[idx])
        used += 1
    if used <= 0:
        return []
    return [value / used for value in pooled]


def _coerce_vector(payload: Any) -> list[float]:
    if isinstance(payload, list) and payload and all(_is_number(v) for v in payload):
        return [float(v) for v in payload]
    if isinstance(payload, list) and payload and all(isinstance(v, list) for v in payload):
        return _mean_pool(payload)
    return []


def _coerce_batch_vectors(payload: Any, expected: int) -> list[list[float]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("embeddings"), list):
            return _coerce_batch_vectors(payload.get("embeddings"), expected)
        if isinstance(payload.get("vectors"), list):
            return _coerce_batch_vectors(payload.get("vectors"), expected)
        if isinstance(payload.get("data"), list):
            nested = []
            for item in payload.get("data") or []:
                if isinstance(item, dict):
                    nested.append(
                        item.get("embedding")
                        or item.get("vector")
                        or item.get("values")
                        or item.get("features")
                    )
            return _coerce_batch_vectors(nested, expected)

    if not isinstance(payload, list) or not payload:
        return []

    if expected == 1:
        vec = _coerce_vector(payload)
        return [vec] if vec else []

    if len(payload) == expected:
        out = [_coerce_vector(item) for item in payload]
        return out if all(vec for vec in out) else []

    return []


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    width = min(len(left), len(right))
    if width <= 0:
        return 0.0

    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for idx in range(width):
        lv = float(left[idx])
        rv = float(right[idx])
        dot += lv * rv
        left_norm += lv * lv
        right_norm += rv * rv

    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _similarity_to_boost(similarity: float, minimum: float, maximum: float, max_boost: float) -> float:
    spread = maximum - minimum
    if spread < 0.015:
        return 0.0

    ratio = (similarity - minimum) / spread
    centered = ratio - 0.55
    max_penalty = min(0.35, max_boost * 0.4)
    return _clip(centered * (max_boost * 1.6), -max_penalty, max_boost)


def embed_texts(
    texts: Sequence[str],
    *,
    cfg: HFSemanticConfig,
    session_factory: SessionFactory,
) -> list[list[float]]:
    if not texts:
        return []

    payload = {
        "inputs": list(texts),
        "parameters": {
            "normalize": True,
            "truncate": True,
        },
        "options": {
            "wait_for_model": True,
            "use_cache": True,
        },
    }
    headers = {
        "Authorization": f"Bearer {cfg.api_token}",
        "Content-Type": "application/json",
    }

    response = session_factory().post(
        cfg.endpoint_url(),
        headers=headers,
        json=payload,
        timeout=max(3.0, float(cfg.timeout_sec)),
    )
    if not getattr(response, "ok", False):
        detail = ""
        try:
            detail = str(response.text or "").strip()
        except Exception:
            detail = ""
        raise RuntimeError(f"Hugging Face embedding request failed ({getattr(response, 'status_code', '?')}): {detail[:300]}")

    data = response.json()
    vectors = _coerce_batch_vectors(data, len(texts))
    if len(vectors) != len(texts):
        raise RuntimeError(f"Unexpected embedding response shape for {len(texts)} texts")
    return vectors


def score_section_candidates(
    section_conf: dict[str, Any],
    articles: Sequence[Any],
    *,
    cfg: HFSemanticConfig,
    session_factory: SessionFactory,
) -> list[SemanticAdjustment]:
    candidates = list(articles[: max(1, int(cfg.max_candidates or 1))])
    if len(candidates) < max(1, int(cfg.min_candidates or 1)):
        return []

    profile = build_section_profile(section_conf)
    passages = [build_article_passage(article) for article in candidates]
    return score_profile_passages(
        profile,
        passages,
        cfg=cfg,
        session_factory=session_factory,
    )


def score_profile_passages(
    profile: str,
    passages: Sequence[str],
    *,
    cfg: HFSemanticConfig,
    session_factory: SessionFactory,
) -> list[SemanticAdjustment]:
    docs = [str(text or "").strip() for text in passages if str(text or "").strip()]
    if len(docs) < max(1, int(cfg.min_candidates or 1)):
        return []

    vectors = embed_texts([str(profile or "").strip()] + docs, cfg=cfg, session_factory=session_factory)
    query_vec = vectors[0]
    sims = [_cosine_similarity(query_vec, doc_vec) for doc_vec in vectors[1:]]
    if not sims:
        return []

    min_sim = min(sims)
    max_sim = max(sims)
    return [
        SemanticAdjustment(
            similarity=round(float(sim), 6),
            boost=round(_similarity_to_boost(float(sim), min_sim, max_sim, float(cfg.max_boost or 0.0)), 6),
            model=cfg.model,
        )
        for sim in sims
    ]
