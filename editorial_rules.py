"""Cheap, source-text-only editorial guards shared by selection and scoring."""
from __future__ import annotations

import re
import unicodedata


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).lower()


def policy_issue_key(title: str) -> str:
    """Group named trade agreements even when no crop appears in the headline.

    Use the headline only: a passing reference in a long article must not
    collapse separate policy stories into the same issue.
    """
    title = _text(title)
    for key, names in (
        ("cptpp", ("cptpp", "포괄적·점진적 환태평양경제동반자협정", "포괄적 점진적 환태평양경제동반자협정")),
        ("rcep", ("rcep", "역내포괄적경제동반자협정")),
    ):
        if any(re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", title) for name in names):
            return key
    return ""


def remote_weather_feature(title: str, body: str) -> bool:
    """Overseas weather curiosities need an explicit Korean market connection."""
    title, text = _text(title), _text(f"{title} {body}")
    foreign = ("유럽", "벨기에", "프랑스", "독일", "스페인", "미국", "중국", "일본", "태국", "베트남", "호주")
    weather = ("폭염", "가뭄", "이상기후", "이상 기후", "기록적인 고온")
    curiosity = ("악어", "자연부화", "자연 부화", "탁구공", "동물원", "감튀 종주국")
    if not (any(w in title for w in foreign) and any(w in text for w in weather)
            and any(w in title for w in curiosity)):
        return False
    # A country name in the source/agency credit (e.g. 한국일보) is not evidence.
    domestic_link = re.search(
        r"(?:한국|국내|우리나라)(?:의|산|으로|에|에서는|에서)?\s*.{0,35}"
        r"(?:수입|수출|도매|수급|가격|검역|통관)", text
    )
    return domestic_link is None


def export_ceremony_filler(title: str, body: str) -> bool:
    """A first shipment's tonnage alone does not establish market impact."""
    title, text = _text(title), _text(f"{title} {body}")
    if "수출" not in title or not re.search(r"첫\s*수출|수출\s*(?:기념|선적|상차)식|수출길", title):
        return False
    if not any(w in text for w in ("상차식", "선적식", "기념식", "첫 수출", "첫수출")):
        return False
    # Preserve measured changes and practical trade constraints, not aspirational
    # prose about opening markets or expanding sales.
    operational = any(w in text for w in (
        "검역 요건", "검역요건", "검역 협상", "통관 지연", "물류비", "미수금",
        "계약 단가", "계약단가", "수출 중단", "수출 재개", "잔류농약 기준",
    ))
    measured_change = re.search(r"(?:전년|지난해|작년|전월).{0,65}\d+(?:\.\d+)?\s*%", text)
    # A standing supply channel (weekly/monthly/annual or contracted volume) or a
    # large first shipment is market information for a horticultural supply desk,
    # even when the article is framed around a ceremony.
    recurring_volume = re.search(
        r"(?:매주|매월|월\s?\d+회|주\s?\d+회|연간|연\s?\d+회|정기(?:적으로)?|계약(?:량|물량|재배)?)"
        r".{0,25}\d+(?:\.\d+)?\s*(?:톤|t|kg|㎏|상자|박스)",
        text,
    )
    large_shipment = any(
        float(m.group(1)) >= 30
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:톤|t)(?![a-z])", text)
    )
    return not (operational or measured_change or recurring_volume or large_shipment)
