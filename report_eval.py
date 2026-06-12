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
PREFERRED_BRIEFING_COUNT_PER_SECTION = 5
SOFT_FALLBACK_BRIEFING_COUNT_PER_SECTION = 4
MIN_FALLBACK_BRIEFING_COUNT_PER_SECTION = 3
MANAGED_COMMODITY_EVAL_ITEM_COUNT = 33
MANAGED_COMMODITY_DAILY_MIN_PRIMARY_COUNT = 6
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
    "폭염",
    "고온",
    "장마",
    "가뭄",
    "냉해",
    "기계화",
    "노동력",
    "절감",
    "무단 투기",
    "투기",
    "산지 폐기",
    "폐기",
    "수확",
    "검역",
    "통관",
    "호조",
    "소비촉진",
    "채소값",
    "채솟값",
    "농산물값",
    "밥상물가",
    "장바구니",
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
_FALSE_POSITIVE_AGRI_TITLE_KEEP_TERMS = (
    "농산물",
    "농업",
    "농가",
    "원예",
    "과수",
    "과일",
    "채소",
    "화훼",
    "도매시장",
    "공판장",
    "수급",
    "출하",
    "반입",
    "경락",
    "경매",
    "작황",
    "재배",
    "시세",
    "도매가격",
    "병해충",
    "방제",
)
_FALSE_POSITIVE_FINANCE_TERMS = (
    "증권",
    "리포트",
    "목표주가",
    "투자의견",
    "매수",
    "매도",
    "실적",
    "영업이익",
    "주가",
    "주식",
    "코스피",
    "코스닥",
    "밸류에이션",
    "시총",
    "상장",
    "상한가",
    "장중",
    "거래대금",
    "거래량",
    "투자자",
    "테마주",
    "종목",
    "광통신",
    "레이저다이오드",
    "주파수",
    "데이터센터",
    "ai 인프라",
)
_FALSE_POSITIVE_COMPANY_SUFFIX_RE = re.compile(
    r"[가-힣a-z0-9]{1,}(?:\s+)?(?:솔루션|테크|전자|바이오|시스템|홀딩스|통신|네트웍스|네트워크|장비|반도체|모빌리티|미디어|로보틱스)"
)
_FALSE_POSITIVE_MARKET_VENUE_TERMS = (
    "가락시장",
    "도매시장",
    "공영도매시장",
    "공판장",
    "농산물시장",
    "농산물 시장",
    "청과시장",
    "청과 시장",
)
_FALSE_POSITIVE_POLITICAL_ACTOR_TERMS = (
    "의원",
    "시의원",
    "도의원",
    "구의원",
    "대표",
    "후보",
    "예비후보",
    "위원장",
    "당대표",
    "구청장",
    "도지사",
    "국힘",
    "국민의힘",
    "민주당",
    "더불어민주당",
)
_FALSE_POSITIVE_POLITICAL_TERMS = (
    "공약",
    "1호 공약",
    "제1호 공약",
    "선거",
    "지방선거",
    "총선",
    "지선",
    "재선",
    "출마",
    "도전",
    "공천",
    "민심",
    "현장행보",
    "비전",
)
_FALSE_POSITIVE_REDEVELOPMENT_TERMS = (
    "용적률",
    "재개발",
    "재건축",
    "도시혁신구역",
    "화이트조닝",
    "주거지구",
    "주택시장",
    "아파트",
    "분양",
    "청약",
    "전세",
    "월세",
    "임대차",
    "대단지",
    "역세권",
    "준공업지역",
    "개발 계획",
    "개발계획",
    "개발 공약",
)
_FALSE_POSITIVE_HOUSING_TITLE_TERMS = (
    "주택시장",
    "아파트",
    "재건축",
    "재개발",
    "분양",
    "청약",
    "전세",
    "월세",
    "임대차",
)
_FALSE_POSITIVE_REAL_MARKET_TITLE_TERMS = (
    "가격",
    "수급",
    "경락",
    "경매",
    "반입",
    "출하",
    "하역",
    "물량",
    "물류",
    "운영",
    "제도개선",
    "검역",
    "원산지",
    "단속",
    "거래",
    "차질",
    "점검",
)

_OFF_SCOPE_FOREIGN_UNMANAGED_URL_FRAGMENTS = (
    "ajunews.com/view/20260518142237838",
)
_KNOWN_DUPLICATE_URL_FRAGMENTS = (
    "enewstoday.co.kr/news/articleView.html?idxno=2430514",
)
_OFF_SCOPE_FOREIGN_TERMS = ("베트남", "중국", "태국", "미국", "일본", "해외", "현지")
_OFF_SCOPE_UNMANAGED_COMMODITY_TERMS = ("두리안", "망고", "바나나", "아보카도", "파인애플")
_DUPLICATE_EVENT_TERMS = ("가격", "안정", "기금", "지원", "농가")


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
                is_core=_bool_attr(attr_map.get("data-is-core")),
                selection_fit_score=_float_attr(attr_map.get("data-selection-fit")),
                selection_stage=str(attr_map.get("data-selection-stage", "")).strip(),
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


def _term_hits(text: str, terms: tuple[str, ...]) -> int:
    value = str(text or "").lower()
    return sum(1 for term in terms if term and term in value)


_EDITORIAL_POLICY_ACTION_TERMS = (
    "정부", "농식품부", "농림축산식품부", "기재부",
    "대책", "정책", "수입", "관세", "할당관세", "법안", "발의", "개정", "규제",
    "보조", "공고", "고시", "시행", "검역", "방역", "수출",
    "자조금", "비축", "방출", "회의", "발표",
)
_EDITORIAL_POLICY_PRICE_REPORT_TERMS = (
    "가격 오름세", "오름세", "가격 상승", "가격 강세", "가격 동향", "시세", "입하", "반입",
    "품종 교체", "주산지 변동", "주산지", "출하량", "도매가격", "경락", "경매",
)
_EDITORIAL_PROMO_TERMS = (
    "홈쇼핑", "라이브커머스", "쇼호스트", "소비촉진", "판촉", "홍보", "캠페인",
    "행사", "현장투어", "협의회", "간담회", "업무협약", "협약", "교육", "기탁",
    "전달", "나눔", "후원", "지원", "선정", "육성", "개최",
)
_EDITORIAL_MARKET_IMPACT_TERMS = (
    "가격", "수급", "출하", "반입", "경매", "경락", "도매", "공판", "물량",
    "재고", "생산량", "피해", "발생", "확산", "방제", "검역", "수출", "계약",
)
_EDITORIAL_DIST_WEAK_TERMS = (
    "현장투어", "협의회", "간담회", "업무협약", "협약", "교육", "육성", "소득작목",
    "브랜드", "선정", "개최", "견학", "컨설팅",
)
_EDITORIAL_DIST_OPS_TERMS = (
    "출하", "공선", "공동선별", "경매", "경락", "도매시장", "공판장", "apc",
    "물류", "저장", "선별", "온라인도매", "수출", "입점", "판매액", "계약",
    "운영", "처리물량", "연합판매",
)


def _editorial_text(article: SurfaceArticle, snapshot_body: str = "") -> str:
    return _normalize_spaces(f"{article.title or ''} {snapshot_body or ''} {article.summary or ''}").lower()


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term and term.lower() in text for term in terms)


def _editorial_dist_hard_logistics_metric(text: str) -> bool:
    text_l = _normalize_spaces(text).lower()
    if not text_l:
        return False
    if not (_has_any(text_l, ("가락시장", "도매시장", "공판장")) and _has_any(text_l, ("파렛트", "팰릿", "물류", "운송지원", "운송 지원"))):
        return False
    hard_hits = _term_hits(
        text_l,
        (
            "출하량", "출하율", "거래액", "물류비", "운송비", "물동량", "반입량", "처리물량",
            "지원금", "하역", "정산", "감축", "절감", "순회수집",
        ),
    )
    metric_hit = re.search(
        r"(?:출하량|출하율|거래액|물류비|운송비|지원금|물동량|반입량|처리물량|경매가|경락가).{0,24}\d"
        r"|\d[\d,]*(?:\.\d+)?\s*(?:톤|t|kg|억원|만원|원|%|%포인트|포인트|건|상자|박스|ha|㏊).{0,24}"
        r"(?:출하|거래|물류|반입|정산|경매|경락|수출|운송|처리|하역|파렛트|팰릿|지원)",
        text_l,
    )
    return hard_hits >= 2 or bool(metric_hit)


def _editorial_policy_wrong_section_reason(article: SurfaceArticle, snapshot_body: str) -> str:
    if article.section != "policy":
        return ""
    text = _editorial_text(article, snapshot_body)
    if not _has_any(text, _EDITORIAL_POLICY_PRICE_REPORT_TERMS):
        return ""
    if _has_any(text, _EDITORIAL_POLICY_ACTION_TERMS):
        return ""
    return "policy_price_report_without_policy_action"


def _editorial_promotional_filler_reason(article: SurfaceArticle, snapshot_body: str) -> str:
    if article.section not in {"supply", "dist", "policy"}:
        return ""
    text = _editorial_text(article, snapshot_body)
    title_l = str(article.title or "").lower()
    if article.section == "dist" and _editorial_dist_hard_logistics_metric(text):
        return ""
    if any(term in text for term in ("홈쇼핑", "라이브커머스", "쇼호스트", "현장투어")):
        return "promotional_or_event_filler"
    if not _has_any(text, _EDITORIAL_PROMO_TERMS):
        return ""
    market_hits = _term_hits(text, tuple(term.lower() for term in _EDITORIAL_MARKET_IMPACT_TERMS))
    title_market_hits = _term_hits(title_l, tuple(term.lower() for term in _EDITORIAL_MARKET_IMPACT_TERMS))
    if market_hits <= 1 and title_market_hits == 0:
        return "promotional_or_event_filler"
    if article.is_core and article.section in {"supply", "dist"} and market_hits <= 2 and _has_any(text, ("지원", "행사", "협의회", "개최")):
        return "promotional_or_event_filler"
    return ""


def _editorial_dist_weak_ops_reason(article: SurfaceArticle, snapshot_body: str) -> str:
    if article.section != "dist":
        return ""
    text = _editorial_text(article, snapshot_body)
    if _editorial_dist_hard_logistics_metric(text):
        return ""
    weak_hits = _term_hits(text, tuple(term.lower() for term in _EDITORIAL_DIST_WEAK_TERMS))
    if weak_hits <= 0:
        return ""
    ops_hits = _term_hits(text, tuple(term.lower() for term in _EDITORIAL_DIST_OPS_TERMS))
    if "현장투어" in text or "소득작목" in text:
        return "dist_event_or_development_without_ops"
    if ops_hits <= 1:
        return "dist_event_or_development_without_ops"
    return ""


def _editorial_base_issue_reasons(article: SurfaceArticle, snapshot_body: str) -> list[str]:
    reasons: list[str] = []
    for reason in (
        _editorial_policy_wrong_section_reason(article, snapshot_body),
        _editorial_promotional_filler_reason(article, snapshot_body),
        _editorial_dist_weak_ops_reason(article, snapshot_body),
    ):
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def _pest_editorial_theme(article: SurfaceArticle, snapshot_body: str = "") -> str:
    if article.section != "pest":
        return ""
    text = _editorial_text(article, snapshot_body)
    if "과수화상병" in text or "화상병" in text:
        return "fire_blight"
    if "벼" in text and "병해충" in text:
        return "rice_pest"
    if "병해충" in text:
        return "general_pest"
    return ""


def _semantic_false_positive_reason(article: SurfaceArticle, snapshot_body: str) -> str:
    title_l = str(article.title or "").lower()
    body_l = str(snapshot_body or "").lower()
    combined = f"{title_l} {body_l}".strip()
    if not combined:
        return ""

    if article.section in {"supply", "policy", "dist"}:
        title_agri_keep = _term_hits(title_l, _FALSE_POSITIVE_AGRI_TITLE_KEEP_TERMS)
        finance_hits = _term_hits(combined, _FALSE_POSITIVE_FINANCE_TERMS)
        finance_title_hits = _term_hits(title_l, _FALSE_POSITIVE_FINANCE_TERMS)
        strong_finance_title_hits = _term_hits(
            title_l,
            tuple(term for term in _FALSE_POSITIVE_FINANCE_TERMS if term != "리포트"),
        )
        company_suffix_hit = _FALSE_POSITIVE_COMPANY_SUFFIX_RE.search(title_l) is not None
        if title_agri_keep == 0 and strong_finance_title_hits >= 1:
            return "finance_company_noise"
        if title_agri_keep == 0 and company_suffix_hit and finance_hits >= 2:
            return "finance_company_noise"
        housing_title_hits = _term_hits(title_l, _FALSE_POSITIVE_HOUSING_TITLE_TERMS)
        redevelopment_hits_all = _term_hits(combined, _FALSE_POSITIVE_REDEVELOPMENT_TERMS)
        real_market_title_hits = _term_hits(title_l, _FALSE_POSITIVE_REAL_MARKET_TITLE_TERMS)
        if article.section != "dist":
            if title_agri_keep == 0 and housing_title_hits >= 1 and real_market_title_hits == 0:
                return "housing_market_noise"
            if title_agri_keep == 0 and redevelopment_hits_all >= 2 and real_market_title_hits == 0:
                return "housing_market_noise"

    if article.section == "dist":
        venue_hits = _term_hits(title_l, _FALSE_POSITIVE_MARKET_VENUE_TERMS)
        actor_hits = _term_hits(title_l, _FALSE_POSITIVE_POLITICAL_ACTOR_TERMS)
        politics_hits = _term_hits(combined, _FALSE_POSITIVE_POLITICAL_TERMS)
        redevelopment_hits = _term_hits(combined, _FALSE_POSITIVE_REDEVELOPMENT_TERMS)
        real_market_title_hits = _term_hits(title_l, _FALSE_POSITIVE_REAL_MARKET_TITLE_TERMS)
        if (
            venue_hits >= 1
            and actor_hits >= 1
            and real_market_title_hits == 0
            and (politics_hits >= 1 or redevelopment_hits >= 2)
        ):
            return "political_market_pledge_noise"

    return ""


def _reader_hard_issue_reason(article: SurfaceArticle, snapshot_body: str) -> str:
    source_text = _normalize_spaces(f"{article.title or ''} {snapshot_body or ''}").lower()
    text = _normalize_spaces(f"{article.title or ''} {article.summary or ''} {snapshot_body or ''}").lower()
    if not text:
        return ""

    agri_keep_terms = (
        "농산물", "농업", "농가", "원예", "과수", "채소", "청과", "도매시장", "공판장",
        "수급", "출하", "경락", "반입", "병해충", "방제", "과수화상병", "사과", "배추",
        "양파", "마늘", "감자", "참외", "수박", "한라봉", "매실", "배 농가", "배 과원",
        "배 재배", "신고배", "무 농가", "무 재배", "무 출하", "무 가격", "가을무", "월동무",
    )
    has_agri_context = any(term in source_text for term in agri_keep_terms)

    if article.section in {"supply", "policy", "dist"}:
        industrial_hits = _term_hits(
            text,
            (
                "배터리", "k배터리", "분리막", "동박", "전해액", "양극재", "음극재", "이차전지",
                "반도체", "철강",
            ),
        )
        industrial_market_hits = _term_hits(text, ("가격반등", "가격 반등", "소재", "온기 확산", "업황", "실적", "주가"))
        if industrial_hits >= 1 and industrial_market_hits >= 1 and not has_agri_context:
            return "industrial_material_market_noise"

        transport_hits = _term_hits(text, ("여객선", "조타실", "선박", "해양사고", "선원", "해운", "항해", "cctv"))
        transport_policy_hits = _term_hits(text, ("의무화", "안전", "대전환", "도입", "규제", "법안"))
        if article.section == "policy" and transport_hits >= 1 and transport_policy_hits >= 1 and not has_agri_context:
            return "non_agri_transport_policy_noise"

        export_promo_hits = _term_hits(text, ("소비재전", "소비재 전", "수출길 청신호", "판로 확대", "해외 진출"))
        if article.section == "policy" and export_promo_hits >= 1 and not has_agri_context:
            return "non_agri_export_promo_noise"

    if article.section == "pest":
        no_damage = any(term in text for term in ("냉해 없어", "냉해 피해 없어", "피해 없어", "피해가 없어", "냉해가 없어"))
        crop_price = _term_hits(text, ("풍작", "작황", "수확", "생산량", "가격", "하락", "걱정", "우려")) >= 2
        pest_action = _term_hits(text, ("방제", "예찰", "약제", "살포", "확산", "발생", "차단", "병해충", "과수화상병", "탄저병"))
        if no_damage and crop_price and pest_action == 0:
            return "pest_no_damage_crop_price"

        diplomacy_hits = _term_hits(text, ("북", "北", "북한", "외교", "비타민c", "묘목"))
        if diplomacy_hits >= 2 and pest_action == 0:
            return "pest_diplomacy_not_pest"

    return ""


def _off_scope_content_reason(article: SurfaceArticle, snapshot_body: str) -> str:
    if article.section not in {"supply", "policy", "dist"}:
        return ""
    href_l = normalize_url(article.href).lower()
    if any(fragment in href_l for fragment in _OFF_SCOPE_FOREIGN_UNMANAGED_URL_FRAGMENTS):
        return "foreign_unmanaged_commodity"
    text = _normalize_spaces(f"{article.title} {article.summary} {snapshot_body}").lower()
    if not text:
        return ""
    if not any(term in text for term in _OFF_SCOPE_UNMANAGED_COMMODITY_TERMS):
        return ""
    if not any(term in text for term in _OFF_SCOPE_FOREIGN_TERMS):
        return ""
    return "foreign_unmanaged_commodity"


def _story_numbers(text: str) -> set[str]:
    return {value.replace(",", "") for value in re.findall(r"\d[\d,]*(?:\.\d+)?", str(text or ""))}


def _story_duplicate_reason(left: SurfaceArticle, right: SurfaceArticle) -> str:
    left_url = normalize_url(left.href)
    right_url = normalize_url(right.href)
    if left_url and right_url and left_url == right_url:
        return "same_url_duplicate"
    if any(fragment in right_url.lower() for fragment in _KNOWN_DUPLICATE_URL_FRAGMENTS):
        return "known_duplicate_url"

    left_text = _normalize_spaces(f"{left.title} {left.summary}").lower()
    right_text = _normalize_spaces(f"{right.title} {right.summary}").lower()
    shared_numbers = _story_numbers(left_text) & _story_numbers(right_text)
    if len(shared_numbers) < 2:
        return ""
    if "평창" not in left_text or "평창" not in right_text:
        return ""
    if not any(term in left_text for term in _DUPLICATE_EVENT_TERMS):
        return ""
    if not any(term in right_text for term in _DUPLICATE_EVENT_TERMS):
        return ""
    return "same_event_numbers"


def _briefing_story_duplicate_samples(articles: list[SurfaceArticle]) -> tuple[list[dict[str, Any]], set[int]]:
    samples: list[dict[str, Any]] = []
    duplicate_indices: set[int] = set()
    for left_idx, left in enumerate(articles):
        for right_idx in range(left_idx + 1, len(articles)):
            right = articles[right_idx]
            reason = _story_duplicate_reason(left, right)
            if not reason:
                continue
            duplicate_indices.add(right_idx)
            samples.append(
                {
                    "reason": reason,
                    "left_title": left.title,
                    "left_section": left.section,
                    "left_href": left.href,
                    "right_title": right.title,
                    "right_section": right.section,
                    "right_href": right.href,
                    "cross_section": left.section != right.section,
                }
            )
    return samples[:8], duplicate_indices


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


def _snapshot_window_hours(snapshot_payload: dict[str, Any]) -> float:
    window = snapshot_payload.get("window", {}) if isinstance(snapshot_payload, dict) else {}
    if not isinstance(window, dict):
        return 0.0
    start = parse_kst_datetime(window.get("start_kst"))
    end = parse_kst_datetime(window.get("end_kst"))
    if not start or not end:
        return 0.0
    return max(0.0, (end - start).total_seconds() / 3600.0)


def _freshness_weight_profile(report_date: str, snapshot_payload: dict[str, Any]) -> tuple[str, dict[str, float]]:
    try:
        report_day = datetime.strptime(str(report_date), "%Y-%m-%d").date()
        is_monday = report_day.weekday() == 0
    except ValueError:
        is_monday = False
    if is_monday or _snapshot_window_hours(snapshot_payload) >= 60.0:
        return "weekend_span", {"matched": 0.25, "within_48h": 0.10, "within_72h": 0.50, "stale": 0.15}
    return "regular", {"matched": 0.25, "within_48h": 0.25, "within_72h": 0.35, "stale": 0.15}


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
    raw = max(0, int(raw_count or 0))
    if raw <= 0:
        return 0
    return min(PREFERRED_BRIEFING_COUNT_PER_SECTION, raw)


def _soft_fallback_briefing_count(raw_count: int) -> int:
    raw = max(0, int(raw_count or 0))
    if raw <= 0:
        return 0
    return min(SOFT_FALLBACK_BRIEFING_COUNT_PER_SECTION, raw)


def _minimum_fallback_briefing_count(raw_count: int) -> int:
    raw = max(0, int(raw_count or 0))
    if raw <= 0:
        return 0
    return min(MIN_FALLBACK_BRIEFING_COUNT_PER_SECTION, raw)


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


_COMMODITY_ALIAS_EXTRA: dict[str, tuple[str, ...]] = {
    "대파": ("쪽파",),
    "풋고추": ("고추", "청양고추", "꽈리고추"),
    "참다래": ("키위",),
    "단감": ("감",),
    "감": ("단감", "곶감"),
    "감귤": ("만감류", "한라봉", "레드향", "천혜향"),
    "포도": ("샤인머스캣",),
    "화훼": ("절화", "생화", "꽃시장"),
}


def _item_alias_terms(label: str) -> list[str]:
    raw = _normalize_spaces(label)
    aliases = {raw.lower(), raw.replace(" ", "").lower()}
    aliases.update(part.lower() for part in re.split(r"[\s/·,()]+", raw) if part.strip())
    # 품목 동의어/약어 추가
    for base, extras in _COMMODITY_ALIAS_EXTRA.items():
        if base in aliases:
            aliases.update(e.lower() for e in extras)
    return [alias for alias in aliases if alias]


def _contains_any_term(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    haystack = _normalize_spaces(text).lower()
    return any(str(term or "").lower() in haystack for term in terms if str(term or "").strip())


def _commodity_item_focus(article: SurfaceArticle) -> bool:
    return _commodity_item_focus_from_text(article.item_label, article.title)


def _commodity_item_focus_from_text(item_label: str, *texts: str) -> bool:
    if not item_label:
        return False
    for text in texts:
        text_l = _normalize_spaces(text).lower()
        text_compact = text_l.replace(" ", "")
        if not text_l:
            continue
        for alias in _item_alias_terms(item_label):
            if alias in text_l or alias.replace(" ", "") in text_compact:
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
    soft_fallback_counts = {section: _soft_fallback_briefing_count(raw_counts[section]) for section in SECTION_KEYS}
    minimum_fallback_counts = {section: _minimum_fallback_briefing_count(raw_counts[section]) for section in SECTION_KEYS}
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
    preferred_slot_gaps = {
        section: max(0, expected_counts[section] - briefing_counts[section])
        for section in SECTION_KEYS
        if raw_counts[section] >= expected_counts[section] and expected_counts[section] > 0
    }
    preferred_slot_gap_total = sum(preferred_slot_gaps.values())
    preferred_slot_gap_rate = _rate(
        preferred_slot_gap_total,
        sum(expected_counts[section] for section in SECTION_KEYS if expected_counts[section] > 0),
        default=0.0,
    )
    broad_soft_fallback_sections = [
        section
        for section in SECTION_KEYS
        if preferred_slot_gaps.get(section, 0) > 0 and briefing_counts[section] >= soft_fallback_counts[section]
    ]
    preferred_slot_penalty = min(
        5.0,
        (preferred_slot_gap_total * 0.75) + (len(broad_soft_fallback_sections) * 0.35),
    )

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
    story_duplicate_samples, story_duplicate_indices = _briefing_story_duplicate_samples(briefing_articles)
    story_duplicate_rate = _rate(len(story_duplicate_indices), len(briefing_articles), default=0.0)
    cross_section_duplicate_rate = _rate(
        sum(1 for sample in story_duplicate_samples if bool(sample.get("cross_section"))),
        len(briefing_articles),
        default=0.0,
    )

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
        fit_score = article.selection_fit_score if float(article.selection_fit_score or 0.0) > 0.0 else _selection_fit(match)
        stage = article.selection_stage or _selection_stage(match)
        title_candidates = list(by_title.get(normalize_title_key(article.title), []))
        best_fit = fit_score
        best_section = str(match.get("section", "")).strip() or article.section
        for candidate in title_candidates:
            candidate_fit = _selection_fit(candidate)
            if candidate_fit > best_fit:
                best_fit = candidate_fit
                best_section = str(candidate.get("section", "")).strip() or best_section
        # 콘텐츠 관련성 검증: 매칭된 스냅샷 기사의 description으로 농업 관련성 체크
        _desc_text = _normalize_spaces(str(match.get("description", "") or ""))
        _combined_text = f"{article.title} {_desc_text}".lower()
        _AGRI_RELEVANCE_TERMS = (
            "농산물", "농업", "농가", "원예", "과수", "채소", "화훼", "도매시장",
            "공판장", "수급", "출하", "반입", "경락", "방제", "병해충", "작황",
            "재배", "수확", "비료", "농약", "묘목", "육묘", "종자", "경매",
            "산지", "가락시장", "유통", "농협", "농식품", "과일", "청과",
        )
        _agri_hits = sum(1 for t in _AGRI_RELEVANCE_TERMS if t in _combined_text)
        semantic_reason = _semantic_false_positive_reason(article, _desc_text)
        off_scope_reason = _off_scope_content_reason(article, _desc_text)
        hard_reader_reason = _reader_hard_issue_reason(article, _desc_text)
        false_positive_reason = semantic_reason or off_scope_reason or hard_reader_reason
        editorial_issue_reasons = _editorial_base_issue_reasons(article, _desc_text)
        if hard_reader_reason and hard_reader_reason not in editorial_issue_reasons:
            editorial_issue_reasons.append(hard_reader_reason)
        briefing_match_records.append(
            {
                "title": article.title,
                "href": article.href,
                "section": article.section,
                "is_core": bool(article.is_core),
                "fit_score": fit_score,
                "stage": stage,
                "score_percentile": _score_percentile(match, section_raw_pools.get(article.section, [])),
                "cross_section_gap": max(0.0, best_fit - fit_score),
                "best_section": best_section,
                "agri_relevance_hits": _agri_hits,
                "semantic_false_positive_reason": semantic_reason,
                "off_scope_reason": off_scope_reason,
                "reader_hard_issue_reason": hard_reader_reason,
                "false_positive_reason": false_positive_reason,
                "snapshot_body": _desc_text,
                "editorial_issue_reasons": editorial_issue_reasons,
            }
        )

    pest_theme_counts: Counter[str] = Counter()
    for record in briefing_match_records:
        if str(record.get("section") or "") != "pest":
            continue
        theme_article = SurfaceArticle(
            tag="",
            surface=BRIEFING_SURFACE,
            section="pest",
            title=str(record.get("title") or ""),
            href=str(record.get("href") or ""),
            article_id="",
            domain="",
        )
        theme = _pest_editorial_theme(theme_article, str(record.get("snapshot_body") or ""))
        if not theme:
            continue
        pest_theme_counts[theme] += 1
        if pest_theme_counts[theme] > 2:
            reasons = record.setdefault("editorial_issue_reasons", [])
            if isinstance(reasons, list):
                reasons.append(f"pest_theme_duplicate:{theme}")

    matched_rate = _rate(matched_count, len(briefing_articles), default=1.0)
    within_48h_rate = _rate(within_48h, matched_count, default=1.0)
    within_72h_rate = _rate(within_72h, matched_count, default=1.0)
    stale_rate = _rate(stale_older_than_96h, matched_count, default=0.0)

    freshness_window_mode, freshness_weights = _freshness_weight_profile(report_date, snapshot_payload)
    freshness_score = 100.0 * (
        matched_rate * freshness_weights["matched"]
        + _score_between(within_48h_rate, 0.5, 0.85) * freshness_weights["within_48h"]
        + _score_between(within_72h_rate, 0.7, 0.95) * freshness_weights["within_72h"]
        + _score_inverse(stale_rate, 0.03, 0.2) * freshness_weights["stale"]
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
    content_false_positive_count = sum(1 for record in briefing_match_records if str(record.get("false_positive_reason") or ""))
    content_false_positive_rate = _rate(
        content_false_positive_count,
        len(briefing_match_records),
        default=0.0,
    )
    content_irrelevant_rate = _rate(
        sum(
            1
            for record in briefing_match_records
            if int(record.get("agri_relevance_hits", 0)) < 1 or str(record.get("false_positive_reason") or "")
        ),
        len(briefing_match_records),
        default=0.0,
    )
    section_alignment_score = 100.0 * (
        _score_between(section_alignment_fit_avg, 0.8, 1.35) * 0.35
        + _score_inverse(section_alignment_low_fit_rate, 0.08, 0.3) * 0.15
        + _score_inverse(section_alignment_cross_gap_rate, 0.02, 0.18) * 0.15
        + _score_inverse(section_alignment_weak_stage_rate, 0.06, 0.24) * 0.10
        + _score_inverse(content_irrelevant_rate, 0.0, 0.15) * 0.25
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
    editorial_quality_issue_records = [
        record
        for record in briefing_match_records
        if isinstance(record.get("editorial_issue_reasons"), list)
        and bool(record.get("editorial_issue_reasons"))
    ]
    policy_wrong_section_rate = _rate(
        sum(
            1
            for record in briefing_match_records
            if "policy_price_report_without_policy_action" in (record.get("editorial_issue_reasons") or [])
        ),
        len(briefing_match_records),
        default=0.0,
    )
    promotional_filler_rate = _rate(
        sum(
            1
            for record in briefing_match_records
            if "promotional_or_event_filler" in (record.get("editorial_issue_reasons") or [])
        ),
        len(briefing_match_records),
        default=0.0,
    )
    promotional_core_rate = _rate(
        sum(
            1
            for record in core_match_records
            if "promotional_or_event_filler" in (record.get("editorial_issue_reasons") or [])
        ),
        len(core_match_records),
        default=0.0,
    )
    dist_weak_ops_rate = _rate(
        sum(
            1
            for record in briefing_match_records
            if "dist_event_or_development_without_ops" in (record.get("editorial_issue_reasons") or [])
        ),
        len(briefing_match_records),
        default=0.0,
    )
    pest_theme_duplicate_rate = _rate(
        sum(
            1
            for record in briefing_match_records
            if any(str(reason).startswith("pest_theme_duplicate:") for reason in (record.get("editorial_issue_reasons") or []))
        ),
        len(briefing_match_records),
        default=0.0,
    )
    weak_core_editorial_rate = _rate(
        sum(
            1
            for record in core_match_records
            if isinstance(record.get("editorial_issue_reasons"), list)
            and bool(record.get("editorial_issue_reasons"))
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
        title_item_focus = _commodity_item_focus(article)
        title_issue_signal = _has_representative_issue_signal(article.title, "")
        title_weak_story = _is_weak_commodity_representative(article.title, "")
        commodity_primary_records.append(
            {
                "title": article.title,
                "section": article.section,
                "item_label": article.item_label,
                "title_item_focus": title_item_focus,
                "title_issue_signal": title_issue_signal,
                "title_weak_story": title_weak_story,
                "strict_link": bool(title_item_focus and title_issue_signal and not title_weak_story and representative_rank >= 2),
                "item_focus": title_item_focus,
                "item_focus_with_body": _commodity_item_focus_from_text(article.item_label, article.title, body),
                "issue_signal": _has_representative_issue_signal(article.title, body),
                "weak_story": _is_weak_commodity_representative(article.title, body),
                "fit_score": fit_score,
                "representative_rank": representative_rank,
            }
        )

    commodity_primary_item_focus_rate = _rate(
        sum(1 for record in commodity_primary_records if bool(record.get("item_focus_with_body"))),
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
    commodity_primary_title_item_focus_rate = _rate(
        sum(1 for record in commodity_primary_records if bool(record.get("title_item_focus"))),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_title_issue_signal_rate = _rate(
        sum(1 for record in commodity_primary_records if bool(record.get("title_issue_signal"))),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_strict_link_rate = _rate(
        sum(1 for record in commodity_primary_records if bool(record.get("strict_link"))),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_low_rank_rate = _rate(
        sum(1 for record in commodity_primary_records if int(record.get("representative_rank") or 0) <= 1),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_count = len(commodity_primary_records)
    commodity_board_daily_min_primary_count = MANAGED_COMMODITY_DAILY_MIN_PRIMARY_COUNT
    commodity_board_low_coverage = commodity_primary_count < commodity_board_daily_min_primary_count
    commodity_board_coverage_rate = _rate(
        commodity_primary_count,
        MANAGED_COMMODITY_EVAL_ITEM_COUNT,
        default=0.0,
    )
    commodity_primary_title_item_missing_rate = _rate(
        sum(1 for record in commodity_primary_records if not bool(record.get("title_item_focus"))),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_body_only_rate = _rate(
        sum(
            1
            for record in commodity_primary_records
            if (not bool(record.get("title_item_focus"))) and bool(record.get("item_focus_with_body"))
        ),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_false_link_rate = _rate(
        sum(
            1
            for record in commodity_primary_records
            if (
                (not bool(record.get("title_item_focus")))
                or bool(record.get("title_weak_story"))
                or int(record.get("representative_rank") or 0) <= 1
            )
        ),
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_section_counter = Counter(
        str(record.get("section") or "") for record in commodity_primary_records if str(record.get("section") or "") in SECTION_KEYS
    )
    commodity_primary_dominant_section_rate = _rate(
        max(commodity_primary_section_counter.values()) if commodity_primary_section_counter else 0,
        len(commodity_primary_records),
        default=0.0,
    )
    commodity_primary_section_balance_score = _score_inverse(
        commodity_primary_dominant_section_rate,
        0.48,
        0.76,
    )
    commodity_primary_linkage_samples = [
        {
            "title": str(record.get("title") or ""),
            "item_label": str(record.get("item_label") or ""),
            "section": str(record.get("section") or ""),
            "representative_rank": int(record.get("representative_rank") or 0),
            "reasons": [
                reason
                for reason, present in (
                    ("title_item_missing", not bool(record.get("title_item_focus"))),
                    ("title_issue_missing", not bool(record.get("title_issue_signal"))),
                    ("weak_title_story", bool(record.get("title_weak_story"))),
                    ("low_representative_rank", int(record.get("representative_rank") or 0) <= 1),
                )
                if present
            ],
        }
        for record in commodity_primary_records
        if not bool(record.get("strict_link"))
    ][:8]
    if commodity_articles and not commodity_primary_articles:
        commodity_board_quality_score = 0.0
    elif commodity_primary_records:
        legacy_commodity_board_quality_score = 100.0 * (
            commodity_primary_item_focus_rate * 0.28
            + _score_between(commodity_primary_issue_signal_rate, 0.45, 0.8) * 0.25
            + _score_inverse(commodity_primary_weak_rate, 0.05, 0.25) * 0.22
            + _score_between(commodity_primary_rank_avg, 1.4, 3.2) * 0.25
        )
        linkage_quality_score = 100.0 * (
            commodity_primary_title_item_focus_rate * 0.25
            + _score_between(commodity_primary_title_issue_signal_rate, 0.45, 0.85) * 0.24
            + _score_between(commodity_primary_strict_link_rate, 0.45, 0.8) * 0.28
            + _score_inverse(commodity_primary_low_rank_rate, 0.05, 0.28) * 0.11
            + commodity_primary_section_balance_score * 0.12
        )
        commodity_board_quality_score = min(legacy_commodity_board_quality_score, linkage_quality_score)
    else:
        commodity_board_quality_score = 100.0

    hard_reader_issue_records = [
        record
        for record in briefing_match_records
        if str(record.get("reader_hard_issue_reason") or "")
    ]
    hard_reader_issue_count = len(hard_reader_issue_records)
    hard_reader_issue_rate = _rate(hard_reader_issue_count, len(briefing_match_records), default=0.0)
    hard_reader_core_issue_count = sum(1 for record in hard_reader_issue_records if bool(record.get("is_core")))
    pest_theme_duplicate_count = sum(
        1
        for record in briefing_match_records
        if any(str(reason).startswith("pest_theme_duplicate:") for reason in (record.get("editorial_issue_reasons") or []))
    )

    semantic_false_positive_penalty = min(18.0, content_false_positive_rate * 120.0)
    story_duplicate_penalty = min(12.0, story_duplicate_rate * 90.0)
    editorial_quality_penalty = min(
        10.0,
        policy_wrong_section_rate * 16.0
        + promotional_core_rate * 8.0
        + promotional_filler_rate * 2.0
        + dist_weak_ops_rate * 8.0
        + pest_theme_duplicate_rate * 8.0
        + weak_core_editorial_rate * 10.0,
    )
    operational_score = (
        completeness_score * 0.20
        + diversity_score * 0.18
        + summary_score * 0.16
        + freshness_score * 0.14
        + retrieval_score * 0.08
        + section_alignment_score * 0.12
        + core_quality_score * 0.07
        + commodity_board_quality_score * 0.05
    )
    operational_score = max(
        0.0,
        min(
            100.0,
            operational_score
            - semantic_false_positive_penalty
            - story_duplicate_penalty
            - editorial_quality_penalty
            - preferred_slot_penalty,
        ),
    )

    reader_quality_penalty = min(
        42.0,
        hard_reader_issue_count * 6.0
        + hard_reader_core_issue_count * 4.0
        + max(0, content_false_positive_count - hard_reader_issue_count) * 5.0
        + len(story_duplicate_indices) * 4.0
        + pest_theme_duplicate_count * 4.0
        + editorial_quality_penalty * 1.8
        + preferred_slot_gap_total * 1.5
        + commodity_primary_false_link_rate * 18.0,
    )
    reader_quality_cap = 100.0
    reader_quality_cap_reasons: list[str] = []

    def _cap(value: float, reason: str) -> None:
        nonlocal reader_quality_cap
        if value < reader_quality_cap:
            reader_quality_cap = value
        if reason not in reader_quality_cap_reasons:
            reader_quality_cap_reasons.append(reason)

    if hard_reader_issue_count >= 1:
        _cap(86.0, "hard_reader_issue")
    if hard_reader_issue_count >= 2:
        _cap(80.0, "multiple_hard_reader_issues")
    if hard_reader_issue_count >= 3:
        _cap(74.0, "severe_hard_reader_issues")
    if hard_reader_issue_count >= 4:
        _cap(70.0, "critical_hard_reader_issues")
    if hard_reader_core_issue_count >= 1:
        _cap(82.0, "hard_core_reader_issue")
    if len(story_duplicate_indices) >= 1:
        _cap(88.0, "story_duplicate")
    if pest_theme_duplicate_count >= 1:
        _cap(90.0, "pest_theme_duplicate")
    if commodity_primary_false_link_rate > 0.0:
        _cap(88.0, "commodity_false_link")
    if commodity_primary_false_link_rate >= 0.10:
        _cap(84.0, "commodity_false_link_severe")
    if preferred_slot_gap_total > 0:
        _cap(95.0, "preferred_slot_underfill")

    reader_quality_score = max(
        0.0,
        min(
            100.0,
            reader_quality_cap,
            operational_score - reader_quality_penalty,
        ),
    )
    overall_score = reader_quality_score

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
    if (
        commodity_board_quality_score < 80.0
        or commodity_primary_weak_rate > 0.15
        or commodity_primary_item_focus_rate < 0.9
        or commodity_primary_strict_link_rate < 0.65
        or commodity_primary_dominant_section_rate > 0.68
        or commodity_primary_false_link_rate > 0.0
    ):
        improvement_hints.append(
            "품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요."
        )
    if commodity_board_low_coverage:
        improvement_hints.append(
            "품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요."
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
    if preferred_slot_gap_total > 0 and raw_counts:
        improvement_hints.append(
            "raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: "
            + ", ".join(f"{section}(-{gap})" for section, gap in preferred_slot_gaps.items() if gap > 0)
            + ". 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요."
        )

    if content_false_positive_rate > 0.0:
        improvement_hints.append(
            f"금융·정치성 오탐이 브리핑에 섞였습니다 (비율 {content_false_positive_rate:.0%}). "
            "제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요."
        )
    if story_duplicate_rate > 0.0:
        improvement_hints.append(
            f"동일 사건이 브리핑 안에서 반복 노출됐습니다 (비율 {story_duplicate_rate:.0%}). "
            "같은 지역·숫자·지원/가격 이벤트가 겹치는 기사는 한 섹션에만 남기세요."
        )
    if editorial_quality_issue_records:
        issue_bits: list[str] = []
        if policy_wrong_section_rate > 0.0:
            issue_bits.append(f"policy_wrong_section={policy_wrong_section_rate:.0%}")
        if promotional_filler_rate > 0.0:
            issue_bits.append(f"promotional_filler={promotional_filler_rate:.0%}")
        if dist_weak_ops_rate > 0.0:
            issue_bits.append(f"dist_weak_ops={dist_weak_ops_rate:.0%}")
        if pest_theme_duplicate_rate > 0.0:
            issue_bits.append(f"pest_theme_duplicate={pest_theme_duplicate_rate:.0%}")
        improvement_hints.append(
            "편집 품질상 약한 기사 선택이 감지되었습니다"
            + (f" ({', '.join(issue_bits)})." if issue_bits else ".")
            + " 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요."
        )
    if content_irrelevant_rate > 0.0:
        improvement_hints.append(
            f"농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 {content_irrelevant_rate:.0%}). "
            "해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요."
        )
    if not improvement_hints:
        improvement_hints.append("전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.")

    result = {
        "report_date": report_date,
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "status": status,
        "overall_score": round(overall_score, 2),
        "operational_score": round(operational_score, 2),
        "reader_quality_score": round(reader_quality_score, 2),
        "reader_quality_gate": {
            "status": "capped" if reader_quality_cap_reasons else "clear",
            "headline_score": round(reader_quality_score, 2),
            "operational_score": round(operational_score, 2),
            "penalty": round(reader_quality_penalty, 2),
            "cap": round(reader_quality_cap, 2),
            "reasons": reader_quality_cap_reasons,
        },
        "scores": {
            "completeness": round(completeness_score, 2),
            "diversity": round(diversity_score, 2),
            "summary_quality": round(summary_score, 2),
            "freshness": round(freshness_score, 2),
            "retrieval_support": round(retrieval_score, 2),
            "section_alignment": round(section_alignment_score, 2),
            "core_quality": round(core_quality_score, 2),
            "commodity_board_quality": round(commodity_board_quality_score, 2),
            "reader_quality": round(reader_quality_score, 2),
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
            "soft_fallback_briefing_by_section": soft_fallback_counts,
            "minimum_fallback_briefing_by_section": minimum_fallback_counts,
            "preferred_slot_gap_by_section": preferred_slot_gaps,
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
            "freshness_window_mode": freshness_window_mode,
            "seed_coverage_score": round(seed_score, 4),
            "section_alignment_fit_avg": round(section_alignment_fit_avg, 4),
            "section_alignment_low_fit_rate": round(section_alignment_low_fit_rate, 4),
            "section_alignment_cross_gap_rate": round(section_alignment_cross_gap_rate, 4),
            "section_alignment_weak_stage_rate": round(section_alignment_weak_stage_rate, 4),
            "content_false_positive_rate": round(content_false_positive_rate, 4),
            "reader_hard_issue_count": int(hard_reader_issue_count),
            "reader_hard_issue_rate": round(hard_reader_issue_rate, 4),
            "reader_hard_core_issue_count": int(hard_reader_core_issue_count),
            "reader_quality_penalty": round(reader_quality_penalty, 4),
            "reader_quality_cap": round(reader_quality_cap, 4),
            "off_scope_foreign_rate": round(
                _rate(
                    sum(1 for record in briefing_match_records if str(record.get("off_scope_reason") or "")),
                    len(briefing_match_records),
                    default=0.0,
                ),
                4,
            ),
            "story_duplicate_rate": round(story_duplicate_rate, 4),
            "cross_section_duplicate_rate": round(cross_section_duplicate_rate, 4),
            "content_irrelevant_rate": round(content_irrelevant_rate, 4),
            "semantic_false_positive_penalty": round(semantic_false_positive_penalty, 4),
            "story_duplicate_penalty": round(story_duplicate_penalty, 4),
            "policy_wrong_section_rate": round(policy_wrong_section_rate, 4),
            "promotional_filler_rate": round(promotional_filler_rate, 4),
            "promotional_core_rate": round(promotional_core_rate, 4),
            "weak_core_editorial_rate": round(weak_core_editorial_rate, 4),
            "pest_theme_duplicate_rate": round(pest_theme_duplicate_rate, 4),
            "dist_weak_ops_rate": round(dist_weak_ops_rate, 4),
            "editorial_quality_penalty": round(editorial_quality_penalty, 4),
            "preferred_slot_gap_rate": round(preferred_slot_gap_rate, 4),
            "preferred_slot_gap_total": int(preferred_slot_gap_total),
            "preferred_slot_penalty": round(preferred_slot_penalty, 4),
            "core_fit_avg": round(core_fit_avg, 4),
            "core_rank_percentile_avg": round(core_rank_percentile_avg, 4),
            "core_stage_core_rate": round(core_stage_core_rate, 4),
            "weak_core_rate": round(weak_core_rate, 4),
            "commodity_primary_item_focus_rate": round(commodity_primary_item_focus_rate, 4),
            "commodity_primary_issue_signal_rate": round(commodity_primary_issue_signal_rate, 4),
            "commodity_primary_weak_rate": round(commodity_primary_weak_rate, 4),
            "commodity_primary_fit_avg": round(commodity_primary_fit_avg, 4),
            "commodity_primary_rank_avg": round(commodity_primary_rank_avg, 4),
            "commodity_primary_title_item_focus_rate": round(commodity_primary_title_item_focus_rate, 4),
            "commodity_primary_title_issue_signal_rate": round(commodity_primary_title_issue_signal_rate, 4),
            "commodity_primary_strict_link_rate": round(commodity_primary_strict_link_rate, 4),
            "commodity_primary_low_rank_rate": round(commodity_primary_low_rank_rate, 4),
            "commodity_primary_count": int(commodity_primary_count),
            "commodity_board_daily_min_primary_count": int(commodity_board_daily_min_primary_count),
            "commodity_board_low_coverage": bool(commodity_board_low_coverage),
            "commodity_board_coverage_rate": round(commodity_board_coverage_rate, 4),
            "commodity_primary_title_item_missing_rate": round(commodity_primary_title_item_missing_rate, 4),
            "commodity_primary_body_only_rate": round(commodity_primary_body_only_rate, 4),
            "commodity_primary_false_link_rate": round(commodity_primary_false_link_rate, 4),
            "commodity_primary_dominant_section_rate": round(commodity_primary_dominant_section_rate, 4),
            "commodity_primary_section_balance_score": round(commodity_primary_section_balance_score, 4),
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
        "content_false_positive_samples": [
            {
                "title": str(record.get("title") or ""),
                "href": str(record.get("href") or ""),
                "section": str(record.get("section") or ""),
                "reason": str(record.get("false_positive_reason") or ""),
            }
            for record in briefing_match_records
            if str(record.get("false_positive_reason") or "")
        ][:8],
        "reader_hard_issue_samples": [
            {
                "title": str(record.get("title") or ""),
                "href": str(record.get("href") or ""),
                "section": str(record.get("section") or ""),
                "reason": str(record.get("reader_hard_issue_reason") or ""),
            }
            for record in hard_reader_issue_records
        ][:8],
        "story_duplicate_samples": story_duplicate_samples,
        "commodity_primary_linkage_samples": commodity_primary_linkage_samples,
        "editorial_quality_samples": [
            {
                "title": str(record.get("title") or ""),
                "href": str(record.get("href") or ""),
                "section": str(record.get("section") or ""),
                "is_core": bool(record.get("is_core")),
                "reasons": list(record.get("editorial_issue_reasons") or []),
            }
            for record in editorial_quality_issue_records
        ][:8],
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
    content_false_positive_rate = float(metrics.get("content_false_positive_rate", 0.0) or 0.0)
    reader_hard_issue_count = int(metrics.get("reader_hard_issue_count", 0) or 0)
    weak_core_rate = float(metrics.get("weak_core_rate", 0.0) or 0.0)
    commodity_primary_item_focus_rate = float(metrics.get("commodity_primary_item_focus_rate", 1.0) or 1.0)
    commodity_primary_issue_signal_rate = float(metrics.get("commodity_primary_issue_signal_rate", 1.0) or 1.0)
    commodity_primary_weak_rate = float(metrics.get("commodity_primary_weak_rate", 0.0) or 0.0)
    commodity_primary_strict_link_rate = float(metrics.get("commodity_primary_strict_link_rate", 1.0) or 1.0)
    commodity_primary_dominant_section_rate = float(metrics.get("commodity_primary_dominant_section_rate", 0.0) or 0.0)
    commodity_board_coverage_rate = float(metrics.get("commodity_board_coverage_rate", 1.0) or 1.0)
    commodity_primary_false_link_rate = float(metrics.get("commodity_primary_false_link_rate", 0.0) or 0.0)
    try:
        commodity_primary_count = int(metrics.get("commodity_primary_count"))
    except (TypeError, ValueError):
        commodity_primary_count = int(round(commodity_board_coverage_rate * MANAGED_COMMODITY_EVAL_ITEM_COUNT))
    try:
        commodity_board_daily_min_primary_count = int(metrics.get("commodity_board_daily_min_primary_count"))
    except (TypeError, ValueError):
        commodity_board_daily_min_primary_count = MANAGED_COMMODITY_DAILY_MIN_PRIMARY_COUNT

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

    if content_false_positive_rate > 0.0:
        reasons.append("semantic_false_positive")
        for key, delta in (("supply", 0.08), ("policy", 0.06), ("dist", 0.1)):
            section_card_min_fit[key] += delta
        low_fit_rescue_min = max(low_fit_rescue_min, 0.35)
        high_score_low_fit_rescue_margin = max(high_score_low_fit_rescue_margin, 4.4)
        tail_score_floor_delta += 0.5

    if reader_hard_issue_count > 0:
        reasons.append("reader_hard_issue")
        for key, delta in (("supply", 0.08), ("policy", 0.1), ("dist", 0.08), ("pest", 0.08)):
            section_card_min_fit[key] += delta
        low_fit_rescue_min = max(low_fit_rescue_min, 0.4)
        high_score_low_fit_rescue_margin = max(high_score_low_fit_rescue_margin, 4.8)
        tail_score_floor_delta += 0.5

    if content_false_positive_rate >= 0.08:
        reasons.append("semantic_false_positive_severe")
        for key, delta in (("supply", 0.05), ("policy", 0.04), ("dist", 0.06)):
            section_card_min_fit[key] += delta
        low_fit_rescue_min = max(low_fit_rescue_min, 0.45)
        high_score_low_fit_rescue_margin = max(high_score_low_fit_rescue_margin, 5.0)
        tail_score_floor_delta += 0.3

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
        or commodity_primary_strict_link_rate < 0.65
        or commodity_primary_dominant_section_rate > 0.68
        or commodity_primary_false_link_rate > 0.0
    ):
        reasons.append("commodity_board")
        commodity_active_min_rank = 2
        commodity_program_core_min_rank = 3
        commodity_require_direct_item_focus = (
            commodity_primary_item_focus_rate < 0.96
            or commodity_primary_strict_link_rate < 0.72
            or commodity_primary_weak_rate > 0.12
        )
        commodity_require_issue_signal = (
            commodity_primary_issue_signal_rate < 0.7
            or commodity_primary_strict_link_rate < 0.65
            or commodity_primary_weak_rate > 0.15
        )

    if commodity_board_quality_score < 68.0 or commodity_primary_weak_rate > 0.25 or commodity_primary_strict_link_rate < 0.45:
        reasons.append("commodity_board_severe")
        commodity_active_min_rank = 2
        commodity_program_core_min_rank = 3
        commodity_require_direct_item_focus = True
        commodity_require_issue_signal = True
    if commodity_primary_count < commodity_board_daily_min_primary_count:
        reasons.append("commodity_board_low_coverage")

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
        "commodity_strict_primary_only": True,
        "commodity_disable_primary_fallback": True,
    }


def build_selection_feedback_payload(result: dict[str, Any]) -> dict[str, Any]:
    scores = result.get("scores", {}) if isinstance(result, dict) else {}
    metrics = result.get("metrics", {}) if isinstance(result, dict) else {}
    guardrails = result.get("selection_guardrails")
    if not isinstance(guardrails, dict):
        guardrails = build_selection_guardrails(result)
    editorial = result.get("editorial", {}) if isinstance(result, dict) else {}
    editorial_plan = result.get("editorial_improvement_plan", {}) if isinstance(result, dict) else {}
    guardrails = dict(guardrails)
    editorial_suggested_guardrails: dict[str, Any] | None = None
    if isinstance(editorial, dict) and editorial.get("status") == "success":
        editorial_suggested_guardrails = _apply_editorial_feedback_to_guardrails(dict(guardrails), editorial)

    payload = {
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
            "content_false_positive_rate": round(float(metrics.get("content_false_positive_rate", 0.0) or 0.0), 4),
            "reader_hard_issue_count": int(metrics.get("reader_hard_issue_count", 0) or 0),
            "reader_hard_issue_rate": round(float(metrics.get("reader_hard_issue_rate", 0.0) or 0.0), 4),
            "reader_quality_penalty": round(float(metrics.get("reader_quality_penalty", 0.0) or 0.0), 4),
            "reader_quality_cap": round(float(metrics.get("reader_quality_cap", 100.0) or 100.0), 4),
            "weak_core_rate": round(float(metrics.get("weak_core_rate", 0.0) or 0.0), 4),
            "policy_wrong_section_rate": round(float(metrics.get("policy_wrong_section_rate", 0.0) or 0.0), 4),
            "promotional_filler_rate": round(float(metrics.get("promotional_filler_rate", 0.0) or 0.0), 4),
            "promotional_core_rate": round(float(metrics.get("promotional_core_rate", 0.0) or 0.0), 4),
            "weak_core_editorial_rate": round(float(metrics.get("weak_core_editorial_rate", 0.0) or 0.0), 4),
            "pest_theme_duplicate_rate": round(float(metrics.get("pest_theme_duplicate_rate", 0.0) or 0.0), 4),
            "dist_weak_ops_rate": round(float(metrics.get("dist_weak_ops_rate", 0.0) or 0.0), 4),
            "editorial_quality_penalty": round(float(metrics.get("editorial_quality_penalty", 0.0) or 0.0), 4),
            "commodity_primary_item_focus_rate": round(float(metrics.get("commodity_primary_item_focus_rate", 0.0) or 0.0), 4),
            "commodity_primary_issue_signal_rate": round(float(metrics.get("commodity_primary_issue_signal_rate", 0.0) or 0.0), 4),
            "commodity_primary_weak_rate": round(float(metrics.get("commodity_primary_weak_rate", 0.0) or 0.0), 4),
            "commodity_primary_title_item_focus_rate": round(float(metrics.get("commodity_primary_title_item_focus_rate", 0.0) or 0.0), 4),
            "commodity_primary_title_issue_signal_rate": round(float(metrics.get("commodity_primary_title_issue_signal_rate", 0.0) or 0.0), 4),
            "commodity_primary_strict_link_rate": round(float(metrics.get("commodity_primary_strict_link_rate", 0.0) or 0.0), 4),
            "commodity_primary_low_rank_rate": round(float(metrics.get("commodity_primary_low_rank_rate", 0.0) or 0.0), 4),
            "commodity_primary_count": int(metrics.get("commodity_primary_count", 0) or 0),
            "commodity_board_daily_min_primary_count": int(metrics.get("commodity_board_daily_min_primary_count", MANAGED_COMMODITY_DAILY_MIN_PRIMARY_COUNT) or MANAGED_COMMODITY_DAILY_MIN_PRIMARY_COUNT),
            "commodity_board_low_coverage": bool(metrics.get("commodity_board_low_coverage", False)),
            "commodity_board_coverage_rate": round(float(metrics.get("commodity_board_coverage_rate", 0.0) or 0.0), 4),
            "commodity_primary_title_item_missing_rate": round(float(metrics.get("commodity_primary_title_item_missing_rate", 0.0) or 0.0), 4),
            "commodity_primary_body_only_rate": round(float(metrics.get("commodity_primary_body_only_rate", 0.0) or 0.0), 4),
            "commodity_primary_false_link_rate": round(float(metrics.get("commodity_primary_false_link_rate", 0.0) or 0.0), 4),
            "commodity_primary_dominant_section_rate": round(float(metrics.get("commodity_primary_dominant_section_rate", 0.0) or 0.0), 4),
        },
        "selection_guardrails": guardrails,
        "editorial_quality_samples": result.get("editorial_quality_samples", [])[:8],
        "reader_hard_issue_samples": result.get("reader_hard_issue_samples", [])[:8],
    }
    if isinstance(editorial, dict) and editorial.get("status") == "success":
        payload["editorial"] = {
            "score": editorial.get("score"),
            "target_score": editorial.get("target_score"),
            "target_status": editorial.get("target_status"),
            "section_count_score": editorial.get("section_count_score"),
            "section_count_status": editorial.get("section_count_status"),
            "scores": editorial.get("scores", {}),
            "issues": editorial.get("issues", [])[:8] if isinstance(editorial.get("issues"), list) else [],
        }
        if editorial_suggested_guardrails and editorial_suggested_guardrails != guardrails:
            payload["editorial_suggested_guardrails"] = editorial_suggested_guardrails
            payload["editorial_guardrail_mode"] = "advisory_only"
    if isinstance(editorial_plan, dict):
        payload["editorial_improvement_plan"] = editorial_plan
    return payload


def _editorial_issue_types(editorial: dict[str, Any]) -> set[str]:
    issues = editorial.get("issues", [])
    if not isinstance(issues, list):
        return set()
    issue_types: set[str] = set()
    for item in issues:
        if not isinstance(item, dict):
            continue
        normalized = re.sub(r"[^a-z0-9_]+", "_", str(item.get("type") or "").strip().lower()).strip("_")
        if normalized:
            issue_types.add(normalized)
    return issue_types


def _apply_editorial_feedback_to_guardrails(guardrails: dict[str, Any], editorial: dict[str, Any]) -> dict[str, Any]:
    try:
        editorial_score = float(editorial.get("score", 100.0) or 100.0)
    except (TypeError, ValueError):
        editorial_score = 100.0
    if editorial_score >= 95.0:
        return guardrails

    issue_types = _editorial_issue_types(editorial)
    if not issue_types:
        return guardrails

    driver_tags = list(guardrails.get("driver_tags", [])) if isinstance(guardrails.get("driver_tags"), list) else []

    def _tag(value: str) -> None:
        if value not in driver_tags:
            driver_tags.append(value)

    section_fit = guardrails.get("section_card_min_fit", {})
    if not isinstance(section_fit, dict):
        section_fit = {}
    section_fit = {key: float(value) for key, value in section_fit.items() if isinstance(value, (int, float))}

    core_fit = guardrails.get("core_fit_min", {})
    if not isinstance(core_fit, dict):
        core_fit = {}
    core_fit = {key: float(value) for key, value in core_fit.items() if isinstance(value, (int, float))}

    def _bump_section(section: str, delta: float, cap: float = 1.18) -> None:
        base = float(section_fit.get(section, section_fit.get("default", 0.8)) or 0.8)
        section_fit[section] = round(min(cap, base + delta), 3)

    def _bump_all_sections(delta: float) -> None:
        for section in ("default",) + SECTION_KEYS:
            _bump_section(section, delta)

    if issue_types & {"wrong_section", "section_mismatch", "section_fit", "weak_section_pick"}:
        _tag("editorial_section_fit")
        for section, delta in (("default", 0.05), ("supply", 0.08), ("policy", 0.08), ("dist", 0.1), ("pest", 0.06)):
            _bump_section(section, delta)
        guardrails["high_score_low_fit_rescue_margin"] = round(
            max(float(guardrails.get("high_score_low_fit_rescue_margin", 3.0) or 3.0), 4.2),
            3,
        )

    if issue_types & {"promotional", "promotional_filler", "noisy_article", "irrelevant_article", "weak_selection"}:
        _tag("editorial_noise_filter")
        _bump_all_sections(0.05)
        guardrails["section_low_fit_rescue_min"] = round(
            max(float(guardrails.get("section_low_fit_rescue_min", 0.15) or 0.15), 0.35),
            3,
        )
        guardrails["tail_score_floor_delta"] = round(
            min(1.2, float(guardrails.get("tail_score_floor_delta", 0.0) or 0.0) + 0.4),
            3,
        )

    if issue_types & {"duplicate", "duplication", "duplicate_topic", "duplicate_story", "same_issue_repeated"}:
        _tag("editorial_duplicate_topic")
        guardrails["tail_score_floor_delta"] = round(
            min(1.2, float(guardrails.get("tail_score_floor_delta", 0.0) or 0.0) + 0.4),
            3,
        )

    if issue_types & {"weak_core", "weak_core_pick", "core_pick_quality", "missed_better_core"}:
        _tag("editorial_core_pick")
        for section in ("default",) + SECTION_KEYS:
            base = float(core_fit.get(section, core_fit.get("default", 1.2)) or 1.2)
            core_fit[section] = round(min(1.75, base + 0.1), 3)
        guardrails["disable_relaxed_core_fill"] = True

    if issue_types & {"missed_opportunity", "missed_better_candidate", "under_selected_high_value"}:
        _tag("editorial_missed_opportunity")

    guardrails["driver_tags"] = driver_tags
    guardrails["section_card_min_fit"] = section_fit
    guardrails["core_fit_min"] = core_fit
    return guardrails


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
    quality_gate = result.get("quality_gate", {})
    quality_gate_line = ""
    if isinstance(quality_gate, dict) and quality_gate:
        quality_gate_line = (
            f"- Quality gate: **{float(quality_gate.get('headline_score', result.get('overall_score', 0.0)) or 0.0):.2f}** "
            f"({quality_gate.get('status', 'unknown')}, {quality_gate.get('reason', 'unknown')}; "
            f"editorial={float(quality_gate.get('editorial_score', 0.0) or 0.0):.1f}, "
            f"operational={float(quality_gate.get('operational_score', 0.0) or 0.0):.1f})\n"
        )
    reader_quality_gate = result.get("reader_quality_gate", {})
    reader_quality_line = ""
    if isinstance(reader_quality_gate, dict) and reader_quality_gate:
        reasons = reader_quality_gate.get("reasons", [])
        if not isinstance(reasons, list):
            reasons = []
        reason_text = ", ".join(str(reason) for reason in reasons[:4]) or "clear"
        reader_quality_line = (
            f"- Reader quality: **{float(result.get('reader_quality_score', result.get('overall_score', 0.0)) or 0.0):.2f}** "
            f"({reader_quality_gate.get('status', 'unknown')}; "
            f"penalty={float(reader_quality_gate.get('penalty', 0.0) or 0.0):.1f}, "
            f"cap={float(reader_quality_gate.get('cap', 100.0) or 100.0):.1f}, "
            f"reasons={reason_text})\n"
        )
    editorial = result.get("editorial", {})
    editorial_block = ""
    if isinstance(editorial, dict) and editorial:
        if editorial.get("status") == "success":
            editorial_scores = editorial.get("scores", {})
            editorial_issues = editorial.get("issues", [])
            issue_lines = "\n".join(
                f"- [{item.get('severity', 'medium')}] {item.get('type', 'issue')}: {item.get('title', '')} - {item.get('reason', '')}"
                for item in editorial_issues[:5]
                if isinstance(item, dict)
            )
            if not issue_lines:
                issue_lines = "- No major editorial issues reported."
            calibration = editorial.get("score_calibration", {})
            calibration_line = ""
            if isinstance(calibration, dict) and calibration:
                calibration_line = (
                    f"- Score calibration: {float(calibration.get('before', editorial.get('llm_score', 0.0)) or 0.0):.1f}"
                    f" -> {float(calibration.get('after', editorial.get('score', 0.0)) or 0.0):.1f}"
                    f" ({calibration.get('reason', 'calibrated')})\n"
                )
            editorial_block = (
                f"\n### Editorial Shadow Eval\n"
                f"- Editorial: **{float(editorial.get('score', 0.0) or 0.0):.2f}** "
                f"(target {float(editorial.get('target_score', 95.0) or 95.0):.0f}, {editorial.get('target_status', 'unknown')})\n"
                f"- Section count gate: {float(editorial.get('section_count_score', 100.0) or 100.0):.1f} "
                f"({editorial.get('section_count_status', 'unknown')})\n"
                f"{calibration_line}"
                f"- Components: article_selection={float(editorial_scores.get('article_selection', 0.0) or 0.0):.1f}, "
                f"section_fit={float(editorial_scores.get('section_fit', 0.0) or 0.0):.1f}, "
                f"core={float(editorial_scores.get('core_pick_quality', 0.0) or 0.0):.1f}, "
                f"summary={float(editorial_scores.get('summary_usefulness', 0.0) or 0.0):.1f}, "
                f"missed={float(editorial_scores.get('missed_opportunity', 0.0) or 0.0):.1f}, "
                f"noise={float(editorial_scores.get('noise_control', 0.0) or 0.0):.1f}\n"
                f"- Summary: {editorial.get('summary', '')}\n"
                f"{issue_lines}\n"
            )
        else:
            editorial_block = (
                f"\n### Editorial Shadow Eval\n"
                f"- Editorial: {editorial.get('status', 'unknown')} ({editorial.get('reason', 'no reason provided')})\n"
            )

    return (
        f"## Daily Eval ({result.get('report_date', '')})\n"
        f"- Overall: **{result.get('overall_score', 0):.2f}** ({result.get('status', 'unknown')})\n"
        f"- Operational: **{float(result.get('operational_score', result.get('overall_score', 0.0)) or 0.0):.2f}**\n"
        f"{reader_quality_line}"
        f"{quality_gate_line}"
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
        f"false_positive={metrics.get('content_false_positive_rate', 0):.2f}, "
        f"hard_reader_issues={int(metrics.get('reader_hard_issue_count', 0) or 0)}, "
        f"weak_core={metrics.get('weak_core_rate', 0):.2f}, "
        f"editorial_penalty={metrics.get('editorial_quality_penalty', 0):.1f}, "
        f"commodity_weak={metrics.get('commodity_primary_weak_rate', 0):.2f}, "
        f"commodity_items={int(metrics.get('commodity_primary_count', 0) or 0)}, "
        f"commodity_coverage={metrics.get('commodity_board_coverage_rate', 0):.2f}, "
        f"commodity_strict_link={metrics.get('commodity_primary_strict_link_rate', 0):.2f}, "
        f"commodity_false_link={metrics.get('commodity_primary_false_link_rate', 0):.2f}, "
        f"commodity_dominant_section={metrics.get('commodity_primary_dominant_section_rate', 0):.2f}, "
        f"semantic_penalty={metrics.get('semantic_false_positive_penalty', 0):.1f}\n\n"
        f"{editorial_block}\n"
        f"### Improvement Hints\n"
        f"{hint_lines}\n\n"
        f"### Next Summary Feedback\n"
        f"{feedback_lines}\n"
    )


def result_to_history_entry(result: dict[str, Any]) -> dict[str, Any]:
    counts = result.get("counts", {})
    metrics = result.get("metrics", {})
    quality_gate = result.get("quality_gate", {})
    if not isinstance(quality_gate, dict):
        quality_gate = {}
    reader_quality_gate = result.get("reader_quality_gate", {})
    if not isinstance(reader_quality_gate, dict):
        reader_quality_gate = {}
    return {
        "report_date": result.get("report_date"),
        "generated_at_kst": result.get("generated_at_kst"),
        "overall_score": result.get("overall_score"),
        "operational_score": result.get("operational_score", result.get("overall_score")),
        "reader_quality_score": result.get("reader_quality_score", result.get("overall_score")),
        "reader_quality_gate_status": reader_quality_gate.get("status"),
        "reader_quality_gate_reasons": reader_quality_gate.get("reasons", []),
        "editorial_score": result.get("editorial_score"),
        "editorial_status": (result.get("editorial") or {}).get("target_status") if isinstance(result.get("editorial"), dict) else None,
        "quality_gate_status": quality_gate.get("status"),
        "quality_gate_reason": quality_gate.get("reason"),
        "status": result.get("status"),
        "section_alignment": result.get("scores", {}).get("section_alignment", 0),
        "core_quality": result.get("scores", {}).get("core_quality", 0),
        "commodity_board_quality": result.get("scores", {}).get("commodity_board_quality", 0),
        "briefing_total": counts.get("briefing_total", 0),
        "commodity_total": counts.get("commodity_total", 0),
        "summary_presence_rate": metrics.get("summary_presence_rate", 0),
        "within_72h_rate": metrics.get("within_72h_rate", 0),
        "briefing_title_unique_rate": metrics.get("briefing_title_unique_rate", 0),
        "content_false_positive_rate": metrics.get("content_false_positive_rate", 0),
        "reader_hard_issue_count": metrics.get("reader_hard_issue_count", 0),
        "reader_quality_penalty": metrics.get("reader_quality_penalty", 0),
        "editorial_quality_penalty": metrics.get("editorial_quality_penalty", 0),
        "policy_wrong_section_rate": metrics.get("policy_wrong_section_rate", 0),
        "promotional_filler_rate": metrics.get("promotional_filler_rate", 0),
        "promotional_core_rate": metrics.get("promotional_core_rate", 0),
        "pest_theme_duplicate_rate": metrics.get("pest_theme_duplicate_rate", 0),
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
