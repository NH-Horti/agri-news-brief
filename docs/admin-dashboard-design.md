# Admin Dashboard Design

## 1. Goal

이 문서는 `agri-news-brief`에 방문/탐색/기사 클릭 데이터를 수집하고, 이를 관리자용 대시보드로 시각화하기 위한 설계안이다.

핵심 목표:

- 방문 추이 확인
- 많이 본 기사 확인
- 섹션/화면별 관심도 확인
- 검색/탐색 사용성 확인
- 현재 정적 배포 구조를 최대한 유지

비목표:

- 로그인 기반 개인 사용자 이력 조회
- 원시 로그를 공개 정적 파일로 배포
- 실시간 초단위 모니터링

## 2. Current Constraints

현재 서비스는 Python 스크립트가 정적 HTML/JSON을 생성하고 GitHub Pages로 배포하는 구조다.

- 메인 산출물: `docs/index.html`, `docs/archive/*.html`, `docs/search_index.json`
- 런타임 서버 없음
- 관리자 전용 API/DB 없음
- 기사 메타데이터는 이미 생성 시점에 잘 정리되어 있음

따라서 권장 구조는 다음과 같다.

1. 브리핑 페이지에서 이벤트를 수집한다.
2. 외부 분석 도구에 저장한다.
3. GitHub Action이 집계 결과를 가져와 정적 JSON으로 만든다.
4. 관리자 페이지는 이 JSON을 읽어 대시보드로 표시한다.

## 3. Recommended Architecture

### 3.1 Preferred Option

`GA4 + GitHub Action 집계 + 정적 관리자 페이지`

구성:

- 수집: GA4
- 집계 배치: GitHub Actions
- 관리자 UI: `docs/admin/index.html`
- 관리자 데이터: `docs/admin/data/*.json`

장점:

- 현재 배포 구조와 충돌이 적음
- 별도 DB 없이 시작 가능
- 페이지뷰와 기사 클릭을 함께 추적 가능
- 검색/탭/섹션 이동 이벤트까지 확장 가능

한계:

- GitHub Pages에 올린 관리자 페이지는 공개 접근 전제
- 내부 전용이 필요하면 관리자 대시보드는 별도 호스트로 분리해야 함
- 로그인 없는 상태에서는 익명 세션 중심의 분석만 가능

### 3.2 Deployment Recommendation

운영 선택지는 두 가지다.

1. 빠른 도입형

- 공개 브리핑: GitHub Pages 유지
- 관리자 대시보드: `docs/admin/`에 같이 배포
- 배포 데이터: 집계 데이터만 공개

2. 권장 운영형

- 공개 브리핑: GitHub Pages 유지
- 관리자 대시보드: Cloudflare Access, Vercel Protected Deployment, Netlify + Auth 등 보호된 호스트로 분리
- 집계 JSON은 비공개 저장소 또는 보호된 API 경유 제공

## 4. Dashboard Information Architecture

### 4.1 Navigation

상단 네비게이션:

- 대시보드
- 기사 분석
- 탐색 분석
- 운영 상태

상단 공통 필터:

- 기간: 오늘 / 7일 / 30일 / 90일 / 사용자 지정
- 비교: 이전 기간 대비
- 섹션: 전체 / 수급 / 정책 / 유통 / 리스크
- 화면: 전체 / 홈 / 아카이브 / 품목 보드
- 마지막 집계 시각

### 4.2 Dashboard Page

첫 화면 블록:

- KPI 카드 6개
- 방문 추이 차트
- 섹션 관심도 차트
- 상위 기사 표
- 최근 검색어 패널

#### KPI Cards

- 방문수
- 사용자수
- 페이지뷰
- 기사 클릭수
- 기사 클릭률
- 평균 참여시간

#### Charts

- 일자별 방문/클릭 추이 line chart
- 페이지 유형별 비중 doughnut chart
- 섹션별 클릭수 horizontal bar chart
- 화면 모드 비중 stacked bar chart

### 4.3 Article Analysis Page

목표:

- 어떤 기사가 가장 많이 클릭되는지 확인
- 어떤 섹션/화면에서 클릭이 발생하는지 확인

표 컬럼:

- 순위
- 기사 제목
- 날짜
- 섹션
- 클릭수
- 사용자수
- CTR
- 클릭 유입 surface
- 아카이브 링크
- 원문 링크

보조 차트:

- 날짜별 기사 클릭 추이
- 섹션별 상위 기사 수 분포
- 도메인별 클릭 비중

### 4.4 Navigation Analysis Page

목표:

- 사용자가 어떤 UI를 많이 쓰는지 확인

블록:

- 섹션 칩 클릭수
- 날짜 이동 사용량
- 이전/다음 버튼 사용량
- 품목 보드 진입 비율
- 검색 사용 비율
- 검색 결과 없음 키워드

### 4.5 Health Page

목표:

- 추적 누락, 집계 지연, 설정 오류를 확인

블록:

- 마지막 이벤트 수집 시각
- 마지막 집계 성공 시각
- 최근 7일 데이터 존재 여부
- 추적 스크립트 버전
- 집계 실패 이력
- 내부 트래픽 필터 적용 여부

## 5. Wireframe

### 5.1 Dashboard

```text
+----------------------------------------------------------------------------------+
| Admin Dashboard                                          Last updated 2026-03-23 |
| [7d] [30d] [90d] [Custom]   [Compare prev]   [Section v] [Surface v]             |
+----------------------------------------------------------------------------------+
| Visits        Users         Pageviews      Article Clicks  CTR       Avg Engage  |
| 12,480        4,210         18,930         6,420           33.9%     01:42       |
+----------------------------------------------------------------------------------+
| Visits / Clicks Trend                           | Clicks by Section              |
|                                                 | supply   2,140                 |
|  line chart                                     | policy   1,580                 |
|                                                 | dist     1,920                 |
|                                                 | pest       780                 |
+----------------------------------------------------------------------------------+
| Top Articles                                                                     |
| # | Title                         | Date       | Section | Clicks | Users | CTR  |
| 1 | 양파가격 폭락...              | 2026-03-20 | supply  | 422    | 311   | 42%  |
| 2 | 공영도매시장 경락값...        | 2026-03-23 | dist    | 388    | 290   | 37%  |
+----------------------------------------------------------------------------------+
| Top Searches                         | Navigation Usage                           |
| 참외 가격                            | chip clicks                                |
| 사과 병해충                          | tab switch                                 |
| 양파 수급                            | prev/next navigation                       |
+----------------------------------------------------------------------------------+
```

### 5.2 Article Analysis

```text
+----------------------------------------------------------------------------------+
| Article Analysis                                                                  |
| [Date Range] [Section] [Surface] [Sort: Clicks v]                                 |
+----------------------------------------------------------------------------------+
| Top Article Ranking                                                                |
| # | Title | Date | Section | Surface | Clicks | Users | CTR | Archive | Source   |
+----------------------------------------------------------------------------------+
| Article Click Trend                                                                |
| multi-line chart by top selected articles                                          |
+----------------------------------------------------------------------------------+
| Domain Breakdown                                                                   |
| chosun.com / yna.co.kr / agrinet.co.kr / ...                                       |
+----------------------------------------------------------------------------------+
```

### 5.3 Navigation Analysis

```text
+----------------------------------------------------------------------------------+
| Navigation Analysis                                                                |
+----------------------------------------------------------------------------------+
| Search Usage          | Section Jump Usage    | View Tab Switches                  |
| search count          | chip click count      | briefing -> commodity              |
+----------------------------------------------------------------------------------+
| Date Navigation                                                                  |
| prev clicks / next clicks / date select changes                                    |
+----------------------------------------------------------------------------------+
| Zero Result Queries                                                                |
| query | count                                                                       |
+----------------------------------------------------------------------------------+
```

## 6. Event Tracking Spec

### 6.1 Naming Principles

- 이벤트명은 소문자 snake_case 사용
- 공통 파라미터는 모든 이벤트에 최대한 일관되게 포함
- 기사 관련 이벤트는 반드시 `article_id`, `report_date`, `section` 포함

### 6.2 Common Parameters

모든 이벤트 공통:

- `page_type`: `home` | `archive`
- `report_date`: `YYYY-MM-DD`
- `view_mode`: `briefing` | `commodity` | `none`
- `build_id`: 배포 버전 식별값
- `page_path`: 현재 경로
- `is_dev_preview`: `true` | `false`

### 6.3 Event List

#### `page_view`

목적:

- 홈/아카이브 방문 추적

파라미터:

- `page_type`
- `report_date`
- `view_mode`

#### `article_open`

목적:

- 원문 기사 클릭 추적

파라미터:

- `article_id`
- `article_title`
- `report_date`
- `section`
- `surface`
- `target_domain`
- `article_rank`

`surface` 값 후보:

- `briefing_card`
- `briefing_btn_open`
- `commodity_primary`
- `commodity_support`
- `commodity_more`
- `search_result_archive`
- `search_result_source`

#### `search_submit`

목적:

- 검색 사용량과 검색 품질 확인

파라미터:

- `query`
- `query_length`
- `result_count`
- `section_filter`
- `sort_mode`
- `group_mode`

#### `section_jump`

목적:

- 섹션 칩/빠른 이동 사용량 측정

파라미터:

- `section`
- `surface`

`surface` 값 후보:

- `top_chipbar`
- `briefing_chipbar`
- `mobile_quick_nav`

#### `view_tab_switch`

목적:

- 브리핑/품목 보드 선호도 확인

파라미터:

- `from_view`
- `to_view`

#### `archive_nav`

목적:

- 날짜 이동 행태 확인

파라미터:

- `nav_type`: `prev` | `next` | `select`
- `from_date`
- `to_date`

### 6.4 Derived Metrics

대시보드에서 계산할 주요 지표:

- `article_ctr = article_clicks / archive_pageviews`
- `search_rate = search_submit_users / total_users`
- `commodity_entry_rate = commodity_view_users / archive_users`
- `section_click_share = section_article_clicks / total_article_clicks`

## 7. Data Output Spec

관리자 페이지는 원시 이벤트를 직접 읽지 않고, 집계된 JSON만 읽는다.

### 7.1 `docs/admin/data/summary.json`

```json
{
  "generated_at": "2026-03-23T23:10:00+09:00",
  "range": {
    "from": "2026-03-17",
    "to": "2026-03-23"
  },
  "totals": {
    "visits": 12480,
    "users": 4210,
    "pageviews": 18930,
    "article_clicks": 6420,
    "article_ctr": 0.339,
    "avg_engagement_sec": 102
  },
  "delta_prev": {
    "visits": 0.082,
    "users": 0.041,
    "pageviews": 0.095,
    "article_clicks": 0.121,
    "article_ctr": 0.018,
    "avg_engagement_sec": -0.034
  }
}
```

### 7.2 `docs/admin/data/timeseries.json`

```json
{
  "generated_at": "2026-03-23T23:10:00+09:00",
  "daily": [
    {
      "date": "2026-03-17",
      "visits": 1700,
      "users": 620,
      "pageviews": 2530,
      "article_clicks": 830
    }
  ]
}
```

### 7.3 `docs/admin/data/top_articles.json`

```json
{
  "generated_at": "2026-03-23T23:10:00+09:00",
  "items": [
    {
      "article_id": "1a8dd743c67c",
      "title": "수급 불안정 해소하려… 저산소 저장고·스마트팜 늘리는 마트들",
      "date": "2026-03-23",
      "section": "supply",
      "surface_top": "briefing_btn_open",
      "clicks": 388,
      "users": 290,
      "ctr": 0.37,
      "archive_url": "/agri-news-brief/archive/2026-03-23.html#sec-supply",
      "source_url": "https://www.chosun.com/economy/market_trend/2026/03/23/AQQW5L6WP5C65PK7RAHZN3NCWA/"
    }
  ]
}
```

### 7.4 `docs/admin/data/navigation.json`

```json
{
  "generated_at": "2026-03-23T23:10:00+09:00",
  "section_jump": [
    { "section": "supply", "clicks": 840 },
    { "section": "dist", "clicks": 610 }
  ],
  "view_switch": [
    { "from": "briefing", "to": "commodity", "count": 280 }
  ],
  "archive_nav": [
    { "nav_type": "prev", "count": 490 },
    { "nav_type": "next", "count": 210 },
    { "nav_type": "select", "count": 350 }
  ]
}
```

### 7.5 `docs/admin/data/search_terms.json`

```json
{
  "generated_at": "2026-03-23T23:10:00+09:00",
  "top_terms": [
    { "query": "양파 가격", "count": 73, "avg_result_count": 5.2 }
  ],
  "zero_result_terms": [
    { "query": "토마토 병", "count": 14 }
  ]
}
```

### 7.6 `docs/admin/data/health.json`

```json
{
  "generated_at": "2026-03-23T23:10:00+09:00",
  "collection": {
    "tracking_enabled": true,
    "last_event_at": "2026-03-23T22:58:12+09:00",
    "tracking_build_id": "d88804b"
  },
  "pipeline": {
    "last_success_at": "2026-03-23T23:10:00+09:00",
    "status": "ok"
  },
  "warnings": []
}
```

## 8. Implementation Plan By File

### 8.1 Existing File Changes

#### `main.py`

변경 목표:

- 추적에 필요한 `data-*` 메타 삽입
- 공통 추적 스크립트 주입
- 홈/아카이브 페이지에서 이벤트 발생

예상 변경 범위:

- `render_daily_page(...)`
  - 기사 카드에 `data-article-id`
  - `data-report-date`
  - `data-section`
  - `data-surface`
  - `data-rank`
- `render_index_page(...)`
  - 홈 페이지 추적 스크립트 포함
- 공통 JS 렌더 영역
  - 카드 클릭
  - 원문 버튼 클릭
  - 탭 전환
  - 검색 실행
  - 섹션 칩 이동
  - 날짜 이동 이벤트 전송

### 8.2 New Static Admin Files

#### `docs/admin/index.html`

역할:

- 관리자 메인 대시보드 쉘
- 필터 바와 각 패널의 DOM 구조 정의

포함 요소:

- 상단 헤더
- 필터 바
- KPI 카드 영역
- 차트 캔버스
- 상위 기사 표
- 상태 패널

#### `docs/admin/assets/admin.css`

역할:

- 관리자 전용 스타일

포인트:

- 정보 밀도 높은 레이아웃
- 카드형 요약 + 표 중심
- 모바일에서 세로 스택, 데스크톱에서는 다단 그리드

#### `docs/admin/assets/admin.js`

역할:

- JSON fetch
- 필터 상태 관리
- 차트 렌더
- 표 렌더
- 비교 구간 표시

구성 함수 예시:

- `loadAdminData()`
- `applyFilters()`
- `renderSummaryCards()`
- `renderTimeseriesChart()`
- `renderSectionChart()`
- `renderTopArticlesTable()`
- `renderNavigationPanels()`
- `renderHealthPanel()`

### 8.3 New Build/Batch Files

#### `scripts/build_admin_analytics.py`

역할:

- 분석 API 조회
- 응답 정규화
- 집계 JSON 생성

주요 책임:

- 기간별 KPI 집계
- 일자별 시계열 생성
- 상위 기사 랭킹 생성
- 검색/탐색 이벤트 집계
- 건강 상태 JSON 작성

입력:

- Analytics property id
- service account credentials 또는 access token
- 출력 대상 디렉토리

출력:

- `docs/admin/data/*.json`

#### `.github/workflows/admin-dashboard.yml`

역할:

- 집계 배치 자동 실행

권장 스케줄:

- 매시 1회 또는 하루 4회

단계:

1. checkout
2. python setup
3. dependency install
4. analytics credentials 주입
5. `scripts/build_admin_analytics.py` 실행
6. 변경 시 `docs/admin/data/` 커밋

## 9. Tracking Injection Plan

### 9.1 Article ID Rule

가능하면 기존 검색 인덱스 생성 규칙과 동일한 `article_id`를 사용한다.

현재 규칙:

- `md5("{report_date}|{section}|{url}|{title}")[:12]`

이 규칙을 페이지 HTML에도 그대로 넣으면, 검색 인덱스와 이벤트 데이터를 자연스럽게 조인할 수 있다.

### 9.2 Page Instrumentation Points

아카이브 페이지에서 반드시 추적해야 할 요소:

- `.card[data-href]` 카드 전체 클릭
- `.btnOpen`
- `.commodityPrimaryStory`
- `.commoditySupportStory`
- `.commodityMoreStory`
- `.viewTab[data-view-tab]`
- `.chip`
- `#dateSelect`
- `[data-nav="prev"]`
- `[data-nav="next"]`

홈 페이지에서 추적해야 할 요소:

- 최신 브리핑 진입 버튼
- 검색 실행
- 검색 결과에서 아카이브 링크 클릭
- 검색 결과에서 원문 링크 클릭
- 날짜별 아카이브 카드 클릭

## 10. Privacy / Security Rules

필수 원칙:

- 원시 방문 로그를 `docs/`에 저장하지 않는다
- IP, user agent 원문, 세션 식별값을 정적 파일로 배포하지 않는다
- 검색어는 개인정보 가능성을 고려해 길이 제한 및 마스킹 정책을 둔다
- 내부 테스트 트래픽은 필터링한다

권장:

- 검색어가 이메일/전화번호 형태면 저장 제외
- 관리 페이지 공개 배포 시 기사 클릭 집계까지만 노출
- 내부 운영용 상세 지표는 보호된 호스트에서만 제공

## 11. Phased Rollout

### Phase 1

목표:

- 방문/기사 클릭 추적 시작

범위:

- `page_view`
- `article_open`
- 공통 파라미터

성공 기준:

- 일자별 방문수와 기사 클릭수 집계 가능

### Phase 2

목표:

- 기본 대시보드 오픈

범위:

- `summary.json`
- `timeseries.json`
- `top_articles.json`
- `docs/admin/index.html`

성공 기준:

- 방문 추이와 인기 기사 확인 가능

### Phase 3

목표:

- 탐색 분석 확장

범위:

- `search_submit`
- `section_jump`
- `view_tab_switch`
- `archive_nav`

성공 기준:

- 어떤 UI가 많이 쓰이는지 판단 가능

### Phase 4

목표:

- 내부 운영 품질 강화

범위:

- 보호된 관리자 배포
- 상태/경고 패널
- 누락 탐지

성공 기준:

- 운영자가 공개 노출 없이 내부 지표를 안정적으로 확인 가능

## 12. Immediate Next Build Scope

가장 먼저 구현할 실제 범위는 아래가 적절하다.

1. `main.py`에 기사/페이지 추적 메타 심기
2. GA4 이벤트 전송 스크립트 삽입
3. `scripts/build_admin_analytics.py` 추가
4. `docs/admin/index.html`, `docs/admin/assets/admin.js`, `docs/admin/assets/admin.css` 추가
5. `admin-dashboard.yml` 워크플로 추가

이 단계가 끝나면 다음이 가능해진다.

- 일자별 방문 추이 확인
- 상위 기사 확인
- 섹션별 클릭 비중 확인
- 기본 관리자 대시보드 운영
