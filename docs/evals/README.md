# Daily Report Evaluation Harness

이 디렉터리는 데일리 리포트 품질 평가 결과와 다음 실행에 반영할 피드백을 저장한다.

파일 구성:

- `YYYY-MM-DD.json`: 날짜별 상세 평가 결과
- `YYYY-MM-DD.md`: 날짜별 사람이 읽기 쉬운 요약
- `latest.json`: 최신 평가 결과
- `latest.md`: 최신 평가 요약
- `latest-feedback.txt`: 다음 실행의 기사 요약 프롬프트에 자동 반영할 피드백
- `history.json`: 날짜별 핵심 점수 추이

로컬 실행 예시:

```powershell
python scripts/evaluate_daily_report.py `
  --report-date 2026-04-10 `
  --snapshot-path docs/replay/2026-04-10.snapshot.json `
  --html-path docs/archive/2026-04-10.html
```

자동 개선 루프:

1. `daily.yml`이 리포트를 생성한다.
2. `scripts/evaluate_daily_report.py`가 품질을 평가한다.
3. `latest-feedback.txt`를 갱신한다.
4. 다음 실행에서 `main.py`가 이 피드백을 OpenAI 요약 프롬프트에 자동 반영한다.
