"""Shared, source-independent fingerprints for concrete agricultural events."""

from __future__ import annotations

import re
import unicodedata


EventFingerprint = tuple[str, ...]


_ADMIN_REGION_RE = re.compile(r"([가-힣]{2,8})(?:시|군|구)(?=[\s,·…'\"‘’“”은는이가에서의과와을를]|$)")
_MONEY_EXPRESSION_RE = re.compile(
    r"(?:\d+(?:\.\d+)?(?:천억|백억|십억|조|억|천만|백만|십만|만))+원?"
)
_MONEY_PART_RE = re.compile(r"(\d+(?:\.\d+)?)(천억|백억|십억|조|억|천만|백만|십만|만)")
_MONEY_MULTIPLIER = {
    "조": 1_000_000_000_000,
    "천억": 100_000_000_000,
    "백억": 10_000_000_000,
    "십억": 1_000_000_000,
    "억": 100_000_000,
    "천만": 10_000_000,
    "백만": 1_000_000,
    "십만": 100_000,
    "만": 10_000,
}

_PROVINCE_ALIASES = (
    ("서울특별시", "서울"), ("서울시", "서울"),
    ("부산광역시", "부산"), ("부산시", "부산"),
    ("대구광역시", "대구"), ("대구시", "대구"),
    ("인천광역시", "인천"), ("인천시", "인천"),
    ("광주광역시", "광주"), ("광주시", "광주"),
    ("대전광역시", "대전"), ("대전시", "대전"),
    ("울산광역시", "울산"), ("울산시", "울산"),
    ("세종특별자치시", "세종"), ("세종시", "세종"),
    ("경기도", "경기"), ("경기", "경기"),
    ("강원특별자치도", "강원"), ("강원도", "강원"), ("강원", "강원"),
    ("충청북도", "충북"), ("충북도", "충북"), ("충북", "충북"),
    ("충청남도", "충남"), ("충남도", "충남"), ("충남", "충남"),
    ("전북특별자치도", "전북"), ("전라북도", "전북"), ("전북도", "전북"), ("전북", "전북"),
    ("전라남도", "전남"), ("전남도", "전남"), ("전남", "전남"),
    ("경상북도", "경북"), ("경북도", "경북"), ("경북", "경북"),
    ("경상남도", "경남"), ("경남도", "경남"), ("경남", "경남"),
    ("제주특별자치도", "제주"), ("제주도", "제주"), ("제주", "제주"),
)


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or "")).lower()
    return re.sub(r"\s+", " ", value).strip()


def _compact(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", _normalize(text))


def _region_anchor(title: str, lead: str) -> str:
    for source in (title, lead[:280]):
        normalized = _normalize(source)
        for alias, canonical in _PROVINCE_ALIASES:
            if alias in normalized:
                return canonical
        match = _ADMIN_REGION_RE.search(normalized)
        if match:
            return match.group(1)
    return ""


def _money_amounts(text: str) -> frozenset[int]:
    compact = _compact(text)
    amounts: set[int] = set()
    for expression in _MONEY_EXPRESSION_RE.findall(compact):
        total = 0.0
        for raw_value, unit in _MONEY_PART_RE.findall(expression):
            total += float(raw_value) * _MONEY_MULTIPLIER[unit]
        if total >= 10_000_000:
            amounts.add(int(round(total)))
    return frozenset(amounts)


def canonical_event_fingerprint(title: str, description: str = "") -> EventFingerprint:
    """Return a conservative event key, or an empty tuple when evidence is weak."""
    title_n = _normalize(title)
    lead_n = _normalize(description)[:700]
    compact = _compact(f"{title_n} {lead_n}")
    title_compact = _compact(title_n)
    if not compact:
        return ()

    facility_family = bool(
        "apc" in compact
        or "산지유통센터" in compact
        or "농산물산지유통센터" in compact
    )
    facility_change = any(
        term in compact
        for term in (
            "스마트", "첨단화", "고도화", "현대화", "전환사업", "선별정보시스템",
            "erp", "포장라인", "냉동시설", "냉동창고", "시설보완", "구축완료",
        )
    ) or any(term in title_compact for term in ("구축", "완료", "전환", "보완"))
    if facility_family and facility_change:
        region = _region_anchor(title_n, lead_n)
        if region:
            return ("facility_upgrade", "apc", region)

    supply_program = bool(
        any(term in compact for term in ("과채류", "채소류", "원예농산물"))
        and "수급안정" in compact
        and any(term in compact for term in ("투입", "지원", "대책", "추진", "협력"))
    )
    if supply_program:
        # 기사 제목마다 총사업비가 생략되기도 하므로, 같은 날의 강한
        # 주체+대상+사업명 조합을 금액보다 먼저 사건의 정체성으로 쓴다.
        if (
            "농협" in compact
            and any(term in compact for term in ("농식품부", "농림축산식품부"))
            and "과채류" in compact
        ):
            return ("supply_stabilization_program", "농협_농식품부_과채류")
        amounts = sorted(_money_amounts(f"{title_n} {lead_n}"))
        if amounts:
            return ("supply_stabilization_program", str(amounts[-1]))

    # 동일 보도자료가 어떤 매체에서는 물가 안정, 다른 매체에서는 가격
    # 인상 또는 원가 지원을 제목 전면에 놓는다. 기관·대상·조치가 모두
    # 일치할 때만 묶어 일반적인 식품 물가 기사끼리의 과잉 병합을 피한다.
    if (
        "식품업계" in compact
        and any(term in compact for term in ("농식품부", "농림축산식품부"))
        and "원가" in compact
        and "부담" in compact
        and any(term in compact for term in ("완화", "지원"))
        and any(term in compact for term in ("인상", "물가", "가격"))
    ):
        return ("food_industry_cost_relief", "농식품부")

    if any(
        program in compact
        for program in ("농산물가격안정제", "농산물가격안정관리제", "가격안정관리제")
    ):
        # 제도명만 같다는 이유로 정책토론회·기준가격·생산량 조절처럼
        # 독자 가치가 다른 후속 보도를 합치지 않는다. 같은 구체 쟁점까지
        # 일치할 때만 사건 지문을 만든다.
        policy_aspects = (
            ("reference_price", ("기준가격",)),
            ("production_control", ("생산량조절", "과잉생산", "차액보전요건")),
            ("implementation_uncertainty", ("핵심사항안갯속", "시행안갯속")),
            ("design_discussion", ("정책토론회", "제도설계", "도입방향논의")),
        )
        for aspect, terms in policy_aspects:
            if any(term in compact for term in terms):
                return ("named_policy_program", "농산물가격안정제", aspect)

    return ()


def duplicate_event_reason(
    left_title: str,
    left_description: str,
    right_title: str,
    right_description: str,
) -> str:
    """Return a stable reason when both stories have the same strong fingerprint."""
    left = canonical_event_fingerprint(left_title, left_description)
    right = canonical_event_fingerprint(right_title, right_description)
    if not left or left != right:
        return ""
    return {
        "facility_upgrade": "same_facility_upgrade",
        "supply_stabilization_program": "same_supply_stabilization_program",
        "food_industry_cost_relief": "same_food_industry_cost_relief",
        "named_policy_program": "same_named_policy_program",
    }.get(left[0], "same_canonical_event")
