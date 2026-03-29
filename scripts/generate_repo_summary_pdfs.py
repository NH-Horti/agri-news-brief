from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs"
FONT_REGULAR = "RepoMalgun"
FONT_BOLD = "RepoMalgunBold"
FONT_REGULAR_PATH = Path(r"C:\Windows\Fonts\malgun.ttf")
FONT_BOLD_PATH = Path(r"C:\Windows\Fonts\malgunbd.ttf")
SUMMARY_PDF = OUTPUT_DIR / "agri-news-brief-summary-ko.pdf"
DETAIL_PDF = OUTPUT_DIR / "agri-news-brief-details-ko.pdf"


SUMMARY_DATA: dict[str, Any] = {
    "title": "agri-news-brief 레포 요약",
    "what_it_is": (
        "이 앱은 원예·농산물 수급 관련 뉴스를 매일 수집하고, 중복 제거·선별·요약을 거쳐 "
        "정적 HTML 브리프로 발행하는 자동화 파이프라인이다. GitHub Pages 아카이브를 갱신하고, "
        "필요 시 카카오 발송과 GA4 기반 관리자 대시보드까지 연결한다."
    ),
    "who_for": (
        "주 사용자로 보이는 대상은 원예·농산물 브리핑 운영 담당자다. "
        "명시적 페르소나 설명은 Not found in repo."
    ),
    "features": [
        "네이버 뉴스 검색 API로 섹션별·키워드별 기사 후보를 수집한다.",
        "중복 제거, 노이즈 차단, 섹션 재배정, 점수화를 통해 최종 기사를 고른다.",
        "OpenAI 요약을 배치·재시도·캐시 방식으로 채워 비용과 실패율을 줄인다.",
        "Hugging Face 임베딩을 선택적으로 써서 근접 후보의 순서를 미세 조정한다.",
        "GitHub Pages용 `docs/index.html`, `docs/archive/*.html`, `docs/search_index.json`을 갱신한다.",
        "리플레이 스냅샷으로 네이버 재수집 없이 특정 날짜 브리프를 다시 만들 수 있다.",
        "카카오 발송과 `docs/admin/` 기반 정적 관리자 대시보드 운영 흐름이 함께 있다.",
    ],
    "architecture": [
        "실행 계층 - `.github/workflows/*.yml` 또는 로컬 PowerShell 스크립트가 `main.py`를 호출하고 `orchestrator.py`가 실행 분기를 조정한다.",
        "수집·선정 계층 - `collector.py`, `main.py`, `ranking.py`, `hf_semantics.py`가 네이버 수집, 규칙 기반 필터링, 재랭킹, 요약 채우기를 맡는다.",
        "저장·배포 계층 - `replay.py`, `.agri_state.json`, `.agri_summary_cache.json`, `io_github.py`가 상태·캐시·스냅샷 관리와 GitHub Contents API 기반 게시를 처리한다.",
        "출력 계층 - 공개 결과물은 `docs/` 정적 페이지, 운영 분석 화면은 `docs/admin/`와 `scripts/build_admin_analytics.py` 조합으로 유지된다.",
    ],
    "run_steps": [
        "`.env.local.example`를 `.env.local` 또는 `.env.dev.local`로 복사한다.",
        "네이버, OpenAI, 카카오 등 필요한 비밀값을 채운다.",
        "`.venv\\Scripts\\python.exe -m pip install -r requirements.txt`로 기본 의존성을 설치한다.",
        "로컬 검증은 `powershell -ExecutionPolicy Bypass -File scripts/run-local-dryrun.ps1 -ReportDate 2026-03-20`로 시작한다.",
    ],
}


DETAIL_DATA: dict[str, Any] = {
    "title": "agri-news-brief 상세 정리",
    "sections": [
        {
            "heading": "1. 앱 개요",
            "body": [
                "이 레포는 원예·농산물 수급 관련 뉴스를 자동으로 모아 일자별 브리프를 만들고 GitHub Pages에 게시하는 Python 중심 프로젝트다.",
                "README와 `main.py` 설명을 보면 평일 정기 실행, 날짜별 재생성, 개발용 프리뷰, 운영용 배포를 함께 다루도록 설계돼 있다.",
            ],
        },
        {
            "heading": "2. 누구를 위한가",
            "body": [
                "코드와 문서에서 직접 드러나는 업무 맥락은 원예수급, 농산물 가격·유통·정책, 병해충, 수출·검역 모니터링이다.",
                "따라서 실제 사용자는 원예·농산물 브리핑 운영 담당자나 검토자일 가능성이 높다.",
                "명시적 사용자 페르소나 문서는 Not found in repo.",
            ],
        },
        {
            "heading": "3. 확인된 핵심 기능",
            "bullets": [
                "네이버 뉴스/웹 검색 기반 수집과 페이지네이션",
                "섹션별 쿼리 구성, 품목 사전, 정책·유통·병해충 등 카테고리 분류",
                "강한 규칙 기반 필터링과 중복 제거",
                "OpenAI 요약 생성, 캐시 저장, 배치 처리, 재시도",
                "Hugging Face 임베딩 기반 보조 재랭킹",
                "날짜별 HTML 브리프, 검색 인덱스, 아카이브 매니페스트 생성",
                "리플레이 스냅샷 기반 재생성",
                "카카오 나에게 보내기 알림",
                "GA4 정적 관리자 대시보드 및 데이터 export 흐름",
            ],
        },
        {
            "heading": "4. 아키텍처 요약",
            "body": [
                "실행 진입점은 `main.py`이며, `orchestrator.py`가 일일 실행, 리빌드, 리플레이, UX 패치 같은 모드를 분기한다.",
                "기사 수집은 `collector.py`가 네이버 API 호출과 재시도를 맡고, 본문 로직은 `main.py`가 대량의 규칙, 점수, 렌더링 로직을 포함한다.",
                "보조 모듈로 `ranking.py`는 정렬 규칙, `hf_semantics.py`는 임베딩 기반 유사도 보정, `retry_utils.py`는 백오프, `observability.py`는 메트릭 누적을 담당한다.",
                "결과 저장은 GitHub Contents API 래퍼인 `io_github.py`를 통해 이뤄지며, 산출물은 주로 `docs/` 아래 정적 HTML과 JSON이다.",
                "상태 저장소는 파일 기반이다. 전용 DB 서버나 ORM 사용 흔적은 Not found in repo.",
            ],
        },
        {
            "heading": "5. 데이터 흐름",
            "bullets": [
                "GitHub Actions 또는 로컬 스크립트가 실행 트리거를 만든다.",
                "네이버 검색 결과를 수집하고 후보 기사를 쌓는다.",
                "중복 제거, 노이즈 차단, 섹션 재배정, 점수화를 거쳐 최종 기사군을 만든다.",
                "기사 요약은 캐시를 우선 사용하고 부족할 때만 OpenAI 호출로 채운다.",
                "최종 결과를 HTML 브리프, 검색 인덱스, 아카이브 목록, 디버그 JSON으로 렌더링한다.",
                "GitHub API로 `docs/`를 갱신하고 필요 시 카카오 링크를 발송한다.",
                "별도 흐름으로 GA4 데이터를 수집해 `docs/admin/data/*.json`을 갱신한다.",
            ],
        },
        {
            "heading": "6. 최소 실행 방법",
            "bullets": [
                "환경 파일 복사 - `.env.local.example`를 `.env.local` 또는 `.env.dev.local`로 복사",
                "필수 값 입력 - 최소한 네이버, OpenAI, 카카오 관련 비밀값을 환경에 채움",
                "기본 의존성 설치 - `.venv\\Scripts\\python.exe -m pip install -r requirements.txt`",
                "로컬 수집 검증 - `powershell -ExecutionPolicy Bypass -File scripts/run-local-dryrun.ps1 -ReportDate 2026-03-20`",
                "리플레이 검증 - `powershell -ExecutionPolicy Bypass -File scripts/run-local-replay.ps1 -ReportDate 2026-03-20`",
                "최종 게시 - `powershell -ExecutionPolicy Bypass -File scripts/run-local-rebuild.ps1 -Target dev -ReportDate 2026-03-20 -DebugReport`",
            ],
        },
        {
            "heading": "7. 근거 파일",
            "bullets": [
                "`README.md`",
                "`main.py`",
                "`collector.py`",
                "`orchestrator.py`",
                "`hf_semantics.py`",
                "`io_github.py`",
                "`replay.py`",
                "`.github/workflows/daily.yml`",
                "`docs/admin-dashboard-setup.md`",
                "`docs/admin-dashboard-design.md`",
            ],
        },
    ],
}


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(FONT_REGULAR_PATH)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_BOLD_PATH)))


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


def build_styles(body_size: float = 9.2, bullet_size: float = 8.8, heading_size: float = 11.0) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}
    styles["title"] = ParagraphStyle(
        "RepoTitle",
        parent=base["Title"],
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#173F35"),
        alignment=TA_LEFT,
        spaceAfter=6,
        wordWrap="CJK",
    )
    styles["meta"] = ParagraphStyle(
        "RepoMeta",
        parent=base["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=8.2,
        leading=10,
        textColor=colors.HexColor("#5A665F"),
        spaceAfter=8,
        wordWrap="CJK",
    )
    styles["section"] = ParagraphStyle(
        "RepoSection",
        parent=base["Heading2"],
        fontName=FONT_BOLD,
        fontSize=heading_size,
        leading=14,
        textColor=colors.HexColor("#245245"),
        spaceBefore=6,
        spaceAfter=4,
        wordWrap="CJK",
    )
    styles["body"] = ParagraphStyle(
        "RepoBody",
        parent=base["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=body_size,
        leading=body_size + 2.2,
        textColor=colors.HexColor("#222222"),
        spaceAfter=4,
        wordWrap="CJK",
    )
    styles["bullet"] = ParagraphStyle(
        "RepoBullet",
        parent=base["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=bullet_size,
        leading=bullet_size + 2.1,
        leftIndent=0,
        textColor=colors.HexColor("#222222"),
        wordWrap="CJK",
    )
    return styles


def make_bullets(items: list[str], styles: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [
            ListItem(Paragraph(item, styles["bullet"]))
            for item in items
        ],
        bulletType="bullet",
        start="-",
        bulletFontName=FONT_BOLD,
        bulletFontSize=8.8,
        leftIndent=10,
        bulletOffsetY=0,
        spaceBefore=1,
        spaceAfter=4,
    )


def build_summary_story(styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = [
        Paragraph(SUMMARY_DATA["title"], styles["title"]),
        Paragraph("레포 근거 기반 1페이지 요약", styles["meta"]),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#A7B8AE"), spaceAfter=6),
        Paragraph("무엇인가", styles["section"]),
        Paragraph(SUMMARY_DATA["what_it_is"], styles["body"]),
        Paragraph("누구를 위한가", styles["section"]),
        Paragraph(SUMMARY_DATA["who_for"], styles["body"]),
        Paragraph("무엇을 하는가", styles["section"]),
        make_bullets(SUMMARY_DATA["features"], styles),
        Paragraph("어떻게 동작하는가", styles["section"]),
        make_bullets(SUMMARY_DATA["architecture"], styles),
        Paragraph("어떻게 실행하는가", styles["section"]),
        make_bullets(SUMMARY_DATA["run_steps"], styles),
    ]
    return story


def build_detail_story(styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = [
        Paragraph(DETAIL_DATA["title"], styles["title"]),
        Paragraph("레포 확인 결과를 바탕으로 정리한 상세판", styles["meta"]),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#A7B8AE"), spaceAfter=8),
    ]
    for section in DETAIL_DATA["sections"]:
        story.append(Paragraph(section["heading"], styles["section"]))
        for text in section.get("body", []):
            story.append(Paragraph(text, styles["body"]))
        bullets = section.get("bullets", [])
        if bullets:
            story.append(make_bullets(list(bullets), styles))
        story.append(Spacer(1, 3))
    return story


def page_count(pdf_path: Path) -> int:
    return len(PdfReader(str(pdf_path)).pages)


def build_summary_pdf(target: Path) -> None:
    configs = [
        {"body_size": 9.0, "bullet_size": 8.6, "heading_size": 10.8},
        {"body_size": 8.7, "bullet_size": 8.4, "heading_size": 10.4},
        {"body_size": 8.4, "bullet_size": 8.1, "heading_size": 10.1},
    ]
    for cfg in configs:
        styles = build_styles(**cfg)
        doc = SimpleDocTemplate(
            str(target),
            pagesize=A4,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=12 * mm,
            bottomMargin=11 * mm,
            title="agri-news-brief 레포 요약",
            author="Codex",
        )
        doc.build(build_summary_story(styles))
        if page_count(target) == 1:
            return
    raise RuntimeError("1페이지 요약 PDF를 1페이지 안에 맞추지 못했습니다.")


def build_detail_pdf(target: Path) -> None:
    styles = build_styles(body_size=9.6, bullet_size=9.2, heading_size=11.4)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="agri-news-brief 상세 정리",
        author="Codex",
    )
    doc.build(build_detail_story(styles))


def render_pdf_pages(pdf_path: Path, output_prefix: str) -> list[Path]:
    doc = fitz.open(pdf_path)
    out_paths: list[Path] = []
    try:
        for idx, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            out_path = TMP_DIR / f"{output_prefix}-{idx + 1}.png"
            pix.save(out_path)
            out_paths.append(out_path)
    finally:
        doc.close()
    return out_paths


def main() -> None:
    ensure_dirs()
    register_fonts()
    build_summary_pdf(SUMMARY_PDF)
    build_detail_pdf(DETAIL_PDF)
    render_pdf_pages(SUMMARY_PDF, "summary")
    render_pdf_pages(DETAIL_PDF, "details")
    print(SUMMARY_PDF)
    print(DETAIL_PDF)
    print(f"summary_pages={page_count(SUMMARY_PDF)}")
    print(f"detail_pages={page_count(DETAIL_PDF)}")


if __name__ == "__main__":
    main()
