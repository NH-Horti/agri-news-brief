"""생육 리스크 어휘와 pest 테마 버킷 — 선정 가드와 평가 심판의 공용 기준.

main.py 의 선정 가드는 발행 전에 같은 테마가 3장 이상 쌓이지 않도록 카드를
빼거나 교체하고, report_eval.py 의 평가는 같은 테마가 3장 이상이면 감점한다.
두 쪽이 서로 다른 분류기를 쓰면 가드는 통과시킨 지면을 평가가 감점하는
상태가 되고, 실제로 2026-08 주간 점수가 그 상태에 묶여 있었다.
(reports/2026-08-16-weekly-score-improvement-plan.md)

분류는 기사 본인의 제목과 본문만 읽는다. 평가 쪽에는 우리가 생성한 요약문도
있지만, 가드는 요약 생성 이전 단계에서 돌기 때문에 요약문을 함께 넣으면 이
모듈이 없애려는 비대칭이 그대로 되살아난다.
"""
from __future__ import annotations

import re
import unicodedata

# ── 기상 생육 리스크 어휘 ────────────────────────────────────────────
# 그 자체로 작물 피해를 뜻하는 말. pest 섹션의 관련성·코어 게이트가
# "병해충 신호"와 동급으로 취급한다.
CROP_WEATHER_RISK_TERMS: tuple[str, ...] = (
    # 기존 어휘 — 그대로 유지한다.
    "냉해", "동해", "서리", "한파", "저온피해", "우박", "폭우", "집중호우", "태풍", "폭설",
    # 추가 — 역시 작물 피해를 직접 가리키는 말이다.
    "저온 피해", "고온피해", "고온 피해", "일소", "습해", "침수",
)

# 기상 현상 자체를 가리키는 말. 여름 기사에서는 물가·복지·정치·해외 기사에도
# 흔히 등장하기 때문에, 단독으로는 생육 리스크 신호로 인정하지 않는다.
# 아래 피해 신호와 함께 나올 때만 pest 신호가 된다.
CROP_WEATHER_EVENT_TERMS: tuple[str, ...] = (
    "가뭄", "폭염", "호우", "장마", "열대야", "고온기", "고온다습",
)

# 작물이 실제로 상했거나 농가가 대응에 나섰다는 신호.
CROP_WEATHER_DAMAGE_SIGNALS: tuple[str, ...] = (
    "시들", "고사", "말라", "마르", "타들어", "낙과", "열과", "갈변",
    "생육 부진", "생육부진", "착과 불량", "결실 불량", "수확 포기", "파종 지연",
    "일소", "급수", "관수", "물주기", "가뭄대책", "가뭄 대책", "재해보험",
    "생육 관리", "생육관리", "방제", "예찰",
)

# 제목이 "작물/농가가 지금 당하고 있다"고 말하는 표현. 위 DAMAGE_SIGNALS 는
# 본문에서 구체적 피해 양상(시들·낙과·급수 등)을 찾는 용도라 제목에는 잘 안 쓰인다.
# 실제 헤드라인은 "가뭄 피해 확산", "폭염에 농가 비상"처럼 총칭으로 쓰기 때문에
# 선발 게이트(main)와 평가(report_eval)가 같은 어휘로 판단하도록 여기서 공유한다.
CROP_WEATHER_HEADLINE_DAMAGE_TERMS: tuple[str, ...] = (
    "피해", "비상", "확산", "경보", "주의보", "특보", "고사", "시들",
)

# 기상 리스크를 테마 버킷으로 묶을 때 쓰는 하위 분류.
_WEATHER_THEME_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("weather_drought", ("가뭄",)),
    ("weather_heat", ("폭염", "고온피해", "고온 피해", "고온기", "고온다습", "일소", "열대야")),
    ("weather_storm", ("태풍", "집중호우", "호우", "폭우", "침수", "습해", "장마", "우박")),
    ("weather_cold", ("냉해", "동해", "서리", "한파", "저온피해", "저온 피해", "폭설")),
)

# ── 생리장해 피해 어휘 ──────────────────────────────────────────────
# 열과·낙과는 병해충 이름도 기상 현상도 아니지만 작물이 실제로 상했다는 말이라
# 기상 피해 어휘(CROP_WEATHER_RISK_TERMS)와 같은 등급의 생육 리스크 신호다.
# 2026-09-22 KBS '레드향 열과 피해 벌써 20%' 기사가 병해충·기상 어휘 어디에도
# 걸리지 않아 pest 후보가 되지 못했다.
# 앞에 한글이 붙은 '계열과'·'진열과 판매'·'탈락과'는 다른 낱말이므로 이 어휘는
# 부분문자열이 아니라 physiological_disorder_hits() 의 앞경계 매칭으로 센다.
CROP_PHYSIOLOGICAL_DISORDER_TERMS: tuple[str, ...] = (
    "열과", "낙과", "생리장해", "생리 장해", "기형과", "착색 불량", "착색불량",
)
# '열과 성을 다하다'의 '열과(熱과)'는 관용구다. 뒤에 '성'이 오면 세지 않는다.
_PHYSIOLOGICAL_DISORDER_IDIOM_GUARD: dict[str, str] = {"열과": r"(?!\s*성)"}


def _physiological_disorder_rx(term: str) -> "re.Pattern[str]":
    return re.compile(rf"(?<![가-힣]){re.escape(term)}{_PHYSIOLOGICAL_DISORDER_IDIOM_GUARD.get(term, '')}")


_PHYSIOLOGICAL_DISORDER_RX: tuple[tuple[str, "re.Pattern[str]"], ...] = tuple(
    (term, _physiological_disorder_rx(term)) for term in CROP_PHYSIOLOGICAL_DISORDER_TERMS
)

# 생리장해 하위 테마. 기상 테마처럼 제목에서만 판정한다. 같은 장해면 같은 버킷,
# 다른 장해면 다른 버킷이어야 pest 테마 중복 가드·심판이 어긋나지 않는다.
_PHYSIOLOGICAL_THEME_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("physio_cracking", ("열과",)),
    ("physio_fruit_drop", ("낙과",)),
    ("physio_disorder", ("생리장해", "생리 장해", "기형과", "착색 불량", "착색불량")),
)

# 병해·해충 고유명. 같은 병해충끼리는 묶고 서로 다른 병해충은 나눈다.
# 역병은 아래 제목 규칙과 같은 키를 쓴다(본문에서 잡혀도 같은 버킷).
_NAMED_PEST_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("phytophthora", ("역병",)),
    ("anthracnose", ("탄저병",)),
    ("downy_mildew", ("노균병",)),
    ("powdery_mildew", ("흰가루병",)),
    ("gray_mold", ("잿빛곰팡이",)),
    ("soft_rot", ("무름병",)),
    ("wilt", ("시들음병", "풋마름병")),
    ("canker", ("궤양병",)),
    ("bacterial_spot", ("세균성점무늬병", "점무늬병")),
    ("virus", ("바이러스병",)),
    ("root_knot", ("뿌리혹병",)),
    ("white_rot", ("흰비단병",)),
    ("nematode", ("선충",)),
    ("mite", ("응애",)),
    ("aphid", ("진딧물",)),
    ("thrips", ("총채벌레",)),
    ("stink_bug", ("노린재",)),
    ("gall_midge", ("혹파리",)),
    ("planthopper", ("벼멸구", "멸구", "매미충", "선녀벌레", "꽃매미")),
    ("scale_insect", ("깍지벌레", "가루이")),
    ("moth", ("나방",)),
    ("slug", ("민달팽이", "달팽이")),
    ("locust", ("풀무치", "메뚜기")),
)

# 품목 토큰. 병해충 이름이 없을 때 "무슨 작물 이야기인지"로 버킷을 나눈다.
# COMMODITY_REGISTRY 를 그대로 쓰지 않는 이유는 이 모듈이 main.py 에 의존하면
# 평가 쪽에서 import 할 수 없기 때문이다. 버킷 키 계산에만 쓰는 어휘다.
_CROP_TOKENS: tuple[str, ...] = (
    "샤인머스캣", "샤인머스켓", "고랭지배추", "방울토마토", "파프리카", "블루베리", "아로니아",
    "브로콜리", "카네이션", "클레멘틴", "칸탈루프", "복숭아", "만감류", "한라봉", "천혜향",
    "애호박", "떫은감", "황금향", "레드향", "만다린", "꽃시장", "신고배", "나주배",
    "토마토", "양배추", "얼갈이", "미나리", "시금치", "느타리", "거베라", "주키니", "쥬키니",
    "고구마", "옥수수", "참다래", "허니듀", "하미과", "딸기", "참외", "수박", "멜론", "감귤",
    "사과", "포도", "단감", "곶감", "자두", "살구", "매실", "키위", "유자", "만감", "피망",
    "대추", "호두", "배추", "당근", "양파", "마늘", "대파", "쪽파", "생강", "알밤",
    "고추", "오이", "가지", "호박", "상추", "부추", "깻잎", "쑥갓", "감자", "절화", "생화",
    "참깨", "들깨", "인삼", "버섯", "표고", "화훼", "장미", "국화", "백합",
    "튤립", "메밀", "녹두",
    # 한 글자 품목은 앞뒤가 한글이면 매칭하지 않는다(배추/배수/무름병 오탐 방지).
    "배", "무", "파", "콩", "밤", "팥",
)
# 앞뒤에 한글이 붙으면 매칭하지 않는 토큰.
# 한 글자 품목 외에, 다른 낱말에 통째로 들어가는 두 글자 품목도 포함한다.
# ("만감이 교차"의 만감, "생화학"의 생화 오탐 방지)
_SHORT_CROP_TOKENS = frozenset({"배", "무", "파", "콩", "밤", "팥", "만감", "생화"})

# 같은 품목의 표기 변형·수식형은 한 버킷으로 모은다. 그러지 않으면 '신고배'와
# '나주배' 기사가 서로 다른 테마로 잡혀 중복 가드를 그대로 통과한다.
# (품종이 실제로 다른 만감류·화훼 세부 품목은 기존 방식대로 각자 버킷을 갖는다.)
_CROP_TOKEN_CANON: dict[str, str] = {
    "샤인머스켓": "샤인머스캣",
    "신고배": "배",
    "나주배": "배",
    "알밤": "밤",
    "쥬키니": "주키니",
    "만감": "만감류",
    "절화": "화훼",
    "생화": "화훼",
    "꽃시장": "화훼",
}

# 테마를 못 붙였지만 병해충 지면인 것은 분명한 카드용 최종 폴백.
_GENERAL_PEST_TERMS: tuple[str, ...] = ("병해충", "병해", "해충", "방제", "예찰")


def normalize(text: str) -> str:
    """NFKC 정규화 + 공백 정리 + 소문자."""
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _has_crop_token(title: str, token: str) -> bool:
    if token not in _SHORT_CROP_TOKENS:
        return token in title
    return re.search(rf"(?<![가-힣]){re.escape(token)}(?![가-힣])", title) is not None


def crop_bucket(title: str) -> str:
    """제목에 드러난 품목 토큰(가장 긴 것 우선)."""
    for token in _CROP_TOKENS:
        if _has_crop_token(title, token):
            return _CROP_TOKEN_CANON.get(token, token)
    return ""


def weather_bucket(text: str) -> str:
    """기상 생육 리스크 하위 테마."""
    for theme, terms in _WEATHER_THEME_TERMS:
        if any(term in text for term in terms):
            return theme
    return ""


def physiological_disorder_hits(text: str) -> int:
    """생리장해 피해 어휘 히트 수(앞경계 매칭).

    '열과'는 '계열과'·'진열과'에, '낙과'는 '탈락과'에 통째로 들어앉는다. 다른
    낱말 안의 부분문자열을 세지 않도록 앞에 한글이 없을 때만 인정한다. 뒤에는
    조사가 붙으므로('열과가', '낙과율') 뒤경계는 요구하지 않는다.
    """
    normalized = normalize(text)
    if not normalized:
        return 0
    return sum(1 for _term, rx in _PHYSIOLOGICAL_DISORDER_RX if rx.search(normalized))


def physiological_disorder_bucket(text: str) -> str:
    """생리장해 하위 테마(앞경계 매칭)."""
    normalized = normalize(text)
    if not normalized:
        return ""
    for theme, terms in _PHYSIOLOGICAL_THEME_TERMS:
        for term in terms:
            if _physiological_disorder_rx(term).search(normalized):
                return theme
    return ""


def weather_event_damage_signal(title: str, body: str = "") -> bool:
    """기상 현상 + 작물 피해·대응 신호가 함께 있는가.

    '폭염'이나 '가뭄'만으로 pest 신호를 인정하면 여름 물가 기사, 폭염 대응
    행정 기사, 해외 가뭄 소식까지 섹션 후보로 들어온다. 실제로 작물이 상했다는
    신호를 함께 요구해 그런 기사를 걸러낸다.
    """
    title_l = normalize(title)
    text = normalize(f"{title} {body}")
    if not any(term in text for term in CROP_WEATHER_EVENT_TERMS):
        return False
    if not any(term in text for term in CROP_WEATHER_DAMAGE_SIGNALS):
        return False
    # 제목이 기상 현상을 말하고 있거나, 제목 자체가 피해를 말해야 한다.
    return any(term in title_l for term in CROP_WEATHER_EVENT_TERMS) or any(
        term in title_l for term in CROP_WEATHER_DAMAGE_SIGNALS
    )


def named_pest_bucket(text: str) -> str:
    """병해·해충 고유명 테마."""
    for theme, terms in _NAMED_PEST_TERMS:
        if any(term in text for term in terms):
            return theme
    return ""


def classify_pest_theme(title: str, body: str = "", *, fire_blight_hint: bool = False) -> str:
    """pest 카드의 편집 테마 버킷.

    같은 값이 3장 이상 나오면 중복으로 본다. 그래서 버킷은 "같은 사안이면 같은
    값, 다른 사안이면 다른 값"이어야 한다. 예전에는 본문에 '병해충'만 있으면
    전부 general_pest 로 묶여서, 씨스트선충과 콩꼬투리혹파리처럼 서로 다른
    기사가 중복으로 감점되는 동안 정작 같은 보도자료를 재가공한 참깨 기사
    두 건은 그대로 통과했다.

    fire_blight_hint 는 main.py 의 과수화상병 농가피해 문맥 판정 결과다.
    평가 쪽에는 해당 판정기가 없으므로 기본값 False 로 두고, 화상병 표기가
    본문에 있으면 어느 쪽에서든 같은 버킷이 된다.
    """
    title_l = normalize(title)
    text = normalize(f"{title} {body}")
    if not text:
        return ""

    if "식물검역증명서" in text or ("해외 직구 씨앗" in text and "검역" in text):
        return "plant_quarantine"
    if fire_blight_hint or "과수화상병" in text or "화상병" in text:
        return "fire_blight"
    if "역병" in title_l:
        return "phytophthora"
    if "돌발해충" in title_l:
        return "outbreak_pest"
    if "육묘장" in title_l and "병해충" in title_l:
        return "nursery_pest"
    if "토양 소독" in title_l or "토양소독" in title_l:
        return "soil_disinfection"
    if "벼" in text and "병해충" in text:
        return "rice_pest"

    named = named_pest_bucket(title_l)
    if named:
        return named
    crop = crop_bucket(title_l)
    if crop:
        return f"crop_{crop}"
    weather = weather_bucket(title_l)
    if weather:
        return weather
    # 생리장해 어휘가 pest 신호로 인정되면서 들어오는 카드가 general_pest 폴백에
    # 몰리지 않도록 마지막 폴백 앞에서 갈라 둔다. 품목·기상 버킷이 있는 카드의
    # 분류는 그대로다(폴백 버킷을 쪼갤 뿐이라 중복 감점이 늘지 않는다).
    physio = physiological_disorder_bucket(title_l)
    if physio:
        return physio
    if any(term in text for term in _GENERAL_PEST_TERMS):
        return "general_pest"
    return ""
