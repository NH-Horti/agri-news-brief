"""Shared, source-independent fingerprints for concrete agricultural events."""

from __future__ import annotations

import re
import unicodedata

from crop_risk_vocab import crop_bucket, named_pest_bucket


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


# 같은 기관 보도자료를 여러 매체가 다시 쓴 경우. 제목 표현은 서로 달라도
# (기관, 작물, 병해충, 조치)가 모두 같으면 독자에게는 한 건의 소식이다.
# 2026-08-14 에 농진청 참깨 방제 보도자료가 두 카드로 실렸는데, 제목 유사도
# 기반 dedup 은 이런 재가공을 잡지 못했다.
_ADVISORY_AUTHORITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("농진청", ("농촌진흥청", "농진청")),
    ("검역본부", ("농림축산검역본부", "검역본부")),
    ("농식품부", ("농림축산식품부", "농식품부")),
    ("농업기술원", ("농업기술원", "농기원")),
    ("농업기술센터", ("농업기술센터", "농기센터")),
    ("산림청", ("산림청",)),
)
_ADVISORY_ACTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("control", ("방제", "약제 살포", "약제살포", "적기 방제", "긴급 방제")),
    ("watch", ("예찰", "주의보", "경보", "발생 우려", "확산 우려", "예방")),
    ("guidance", ("당부", "관리 요령", "안내", "지도", "요령")),
)


# 정부의 농산물 수급·물가 안정 발표. 브리핑 한 건을 여러 매체가 서로 다른
# 각도로 쓰기 때문에(같은 날 '평년보다 낮아', '배추값 32%↓', '추석까지 안정
# 공급'이 각각 카드가 됐다) 제목만으로는 같은 사안인지 알 수 없다. 편집 평가는
# 이런 묶음을 duplicate_story/duplicate_theme 로 계속 지적했다.
_GOV_STABILIZATION_ACTORS = ("정부", "농식품부", "농림축산식품부", "기재부", "기획재정부")
# 수급·물가 안정이라는 성격이 분명할 때만 묶는다. '대책'·'지원' 같은 총칭은
# 면세유·스마트팜처럼 전혀 다른 정책까지 합쳐버리므로 넣지 않는다.
_GOV_STABILIZATION_MEASURES = (
    "수급 안정", "수급안정", "가격 안정", "가격안정", "물가",
    "할인 지원", "할인지원", "할인", "비축", "방출", "공급 확대", "공급확대",
    "수급 대책", "수급대책",
)
# '평년'·'안정 공급'·'가격 점검'까지 넣어 같은 브리핑의 모든 변형을 잡아보려 했지만,
# 그 어휘는 개별 정책 기사(할인 지원 사업, 전자송장 가격 대응 등)까지 한 사건으로
# 합쳐 버렸다. 좁게 유지하고, 못 잡는 변형은 남겨둔다.
_GOV_STABILIZATION_TARGETS = (
    "농산물", "농축산물", "채소", "과일", "청과", "밥상물가", "장바구니", "성수품",
)


def _gov_stabilization_signature(title_n: str, spaced: str, compact: str) -> EventFingerprint:
    """정부의 명절 수급·물가 대책 발표.

    '정부 + 농산물 + 가격 조치'만으로는 사건을 특정하지 못한다. 하루치 지면에도
    계란 할인, 가격안정제 토론회, 노지채소 도매가 설명처럼 서로 다른 정부
    이야기가 함께 실리기 때문이다(그렇게 묶었더니 실제로 별개 정책이 하나로
    합쳐졌다). 명절 대책처럼 시점이 특정되는 발표만 한 사건으로 본다.
    """
    occasion = ""
    for token in ("추석", "설 명절", "설명절", "명절"):
        if token in spaced:
            occasion = "추석" if token == "추석" else "명절"
            break
    if not occasion:
        return ()
    if not any(_compact(term) in compact for term in _GOV_STABILIZATION_ACTORS):
        return ()
    # 조치어는 공백을 살린 텍스트로 찾는다. 공백을 지우면 '농산물 가격'이
    # '농산물가격'이 되면서 '물가'가 그 안에서 잡혀, 전혀 다른 정책 기사까지
    # 같은 사건으로 묶였다.
    if not any(term in spaced for term in _GOV_STABILIZATION_MEASURES):
        return ()
    if not any(term in compact for term in _GOV_STABILIZATION_TARGETS):
        return ()
    # 품목이 제목에 특정되면 그 품목까지 키에 넣는다. 같은 명절 대책이라도 정부가
    # 품목별로 따로 발표하면 별개 사안이기 때문이다.
    return ("gov_supply_stabilization", occasion, crop_bucket(title_n))


def _advisory_authority(compact: str) -> str:
    for key, terms in _ADVISORY_AUTHORITIES:
        if any(_compact(term) in compact for term in terms):
            return key
    return ""


def _advisory_action(compact: str) -> str:
    """가장 강한 조치 하나만 고른다.

    같은 보도자료라도 매체마다 '적기 방제 당부'와 '발생 초기에 방제해야'처럼
    동사 조합이 달라진다. 조치 집합 전체를 키에 넣으면 그 차이 때문에 같은
    사건이 갈라지므로, 방제 > 예찰 > 안내 순으로 대표 조치를 정한다.
    """
    for key, terms in _ADVISORY_ACTIONS:
        if any(_compact(term) in compact for term in terms):
            return key
    return ""


def canonical_event_fingerprint(title: str, description: str = "") -> EventFingerprint:
    """Return a conservative event key, or an empty tuple when evidence is weak."""
    title_n = _normalize(title)
    lead_n = _normalize(description)[:700]
    compact = _compact(f"{title_n} {lead_n}")
    title_compact = _compact(title_n)
    if not compact:
        return ()

    gov_signature = _gov_stabilization_signature(title_n, f"{title_n} {lead_n}", compact)
    if gov_signature:
        return gov_signature

    authority = _advisory_authority(compact)
    if authority:
        crop = crop_bucket(title_n) or crop_bucket(f"{title_n} {lead_n}")
        # 병해충은 제목에 적힌 것만 본다. 기관 보도자료는 여러 병해충을 한꺼번에
        # 다루는 일이 많아, 본문에서 뽑으면 매체마다 다른 이름이 잡혀 같은
        # 보도자료가 갈라진다(농진청 참깨 안내가 실제로 그랬다).
        pest = named_pest_bucket(title_n)
        action = _advisory_action(compact)
        # 작물이나 병해충 중 하나는 특정돼야 하고, 조치도 드러나야 한다.
        # 기관 이름만 같다는 이유로 서로 다른 소식을 묶지 않는다.
        if (crop or pest) and action:
            return ("agency_advisory", authority, crop, pest, action)

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
        "agency_advisory": "same_agency_advisory",
        "gov_supply_stabilization": "same_gov_supply_stabilization",
    }.get(left[0], "same_canonical_event")
