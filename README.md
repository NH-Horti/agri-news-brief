# agri-news-brief

## Local Validation (optional)

Run local checks manually:

```bash
python -m py_compile main.py collector.py io_github.py retry_utils.py schemas.py ux_patch.py ranking.py orchestrator.py observability.py replay.py hf_semantics.py
python -m mypy --config-file mypy.ini
python -m unittest discover -s tests -p "test_*.py"
```

## Optional Hugging Face semantic reranking

The final article selection stage can optionally add a small semantic boost using Hugging Face embeddings.

- Purpose: improve ordering among close candidates without removing the existing rule-based filters
- Default: off
- Recommended model: `intfloat/multilingual-e5-large`
- Required env:
  - `HF_TOKEN=...`
- Optional env:
  - `HF_SEMANTIC_RERANK_ENABLED` (`true` / `false`, omitted = auto-enable when `HF_TOKEN` exists)
  - `HF_SEMANTIC_MODEL`
  - `HF_SEMANTIC_MAX_CANDIDATES`
  - `HF_SEMANTIC_MAX_BOOST`
  - `HF_SEMANTIC_TIMEOUT_SEC`

Behavior:

- thresholding and hard filters still use the existing rule-based system
- Hugging Face only nudges ranking among already-eligible candidates
- if the token is missing or the API call fails, the pipeline falls back to the original behavior

## Daily Report Evaluation Harness

The repo now includes a daily report quality harness.

- Core module: `report_eval.py`
- CLI: `scripts/evaluate_daily_report.py`
- Published artifacts: `docs/evals/`
- Auto-feedback loop: `docs/evals/latest-feedback.txt` is fed back into the next OpenAI summary run
- Selection guardrails: `docs/evals/latest-selection-feedback.json` is fed back into the next card/core/commodity selection run
- Editorial score: fixed weighted sum of six rubric components; the model-reported total is diagnostic only
- Daily editorial acceptance: weighted score >= 88, no blocking/major issue, critical components >= 85, all components >= 80, and deterministic publish gates passing
- Quality tiers: 88 daily pass, 92 excellent, 95 stretch

Local example:

```powershell
python scripts/evaluate_daily_report.py `
  --report-date 2026-04-10 `
  --snapshot-path docs/replay/2026-04-10.snapshot.json `
  --html-path docs/archive/2026-04-10.html
```

## Local Rebuild

You can run rebuilds locally without waiting for GitHub Actions.

1. Copy `.env.local.example` to `.env.local`, `.env.dev.local`, or `.env.final.local`
2. Fill in the local secrets you need
3. Use one of the scripts below from the repo root

Dry-run only:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-local-dryrun.ps1 -ReportDate 2026-03-20
```

This mode:

- auto-loads `.env.local`
- prefers `.env.dev.local` when present
- reads source files from the current workspace
- writes generated outputs under `.local-builds/`
- does not write to GitHub

Fast replay from the last dry-run snapshot:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-local-replay.ps1 -ReportDate 2026-03-20
```

This mode:

- reuses `.local-builds/dryrun/main/.agri_replay/YYYY-MM-DD.snapshot.json`
- skips Naver collection entirely
- reruns section reassignment, scoring, commodity board selection, and HTML rendering
- writes replay outputs under `.local-builds/replay/`
- can optionally re-run OpenAI summaries with `-AllowOpenAI`

Publish preview from your local machine:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-local-rebuild.ps1 -Target dev -ReportDate 2026-03-20 -DebugReport
```

Publish production from your local machine:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-local-rebuild.ps1 -Target prod -ReportDate 2026-03-20
```

Notes:

- `.env.local` is auto-loaded by `main.py` when present
- `scripts/run-local-dryrun.ps1` prefers `.env.dev.local`
- `scripts/run-local-dryrun.ps1` also saves a replay snapshot for the same date
- `scripts/run-local-replay.ps1` prefers `.env.dev.local`
- `scripts/run-local-rebuild.ps1 -Target dev` prefers `.env.dev.local`
- `scripts/run-local-rebuild.ps1 -Target prod` prefers `.env.final.local`
- local publish uses `gh auth token` if `GH_TOKEN` or `GITHUB_TOKEN` is not already set
- local dry-run does not require a GitHub token

Recommended fast iteration loop:

1. Run `run-local-dryrun.ps1` once when queries/scrapers changed or you need a fresh candidate pool
2. Tune scoring/filtering rules and verify with `run-local-replay.ps1`
3. Run `run-local-dryrun.ps1` again only when you want a fresh scrape
4. Use `run-local-rebuild.ps1` only for final dev/prod publish

## Admin Dashboard / GA4

The static admin dashboard lives under `docs/admin/`.

- Beginner setup guide: `docs/admin-dashboard-setup.md`
- Event / IA design doc: `docs/admin-dashboard-design.md`
- Local export: `powershell -ExecutionPolicy Bypass -File scripts/run-local-admin-dashboard.ps1 -Strict`
- Auto-register custom dimensions: `powershell -ExecutionPolicy Bypass -File scripts/run-local-register-ga4-custom-dimensions.ps1 -DryRun`
- Scheduled export workflow: `.github/workflows/admin-dashboard.yml`

## Pre-Push Hook

This repo includes `.githooks/pre-push`.

- Default: skip local checks and rely on GitHub Actions (good for GitHub Desktop only workflow)
- Strict mode: run local checks by setting `AGRI_PREPUSH_STRICT=1`

One-time setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-hooks.ps1
```

Strict mode example (PowerShell):

```powershell
$env:AGRI_PREPUSH_STRICT="1"
git push
```

## Dev / Prod Separation

Use three branches:

- `main`: production operation only
- `dev`: development code and pre-merge verification
- `codex/dev-preview`: generated preview artifacts only

### Production workflows (main only)

- `.github/workflows/daily.yml`
- `.github/workflows/daily-watchdog.yml` (06:10/06:20/06:35/06:50 KST delivery-receipt recovery)
- `.github/workflows/rebuild.yml`
- `.github/workflows/maintenance.yml`
- `.github/workflows/ux_patch.yml`

`main` is the only branch that publishes production Pages content under `docs/`.

### Daily prepublish quality gate

The production daily workflow starts at 06:05 KST and treats 06:50 KST as the
publication deadline. Before it writes the daily page, updates the index/state,
or sends the normal Kakao briefing, it now:

1. generates the candidate briefing with `gpt-5.6-sol` at low reasoning effort;
2. runs the deterministic report evaluator and a `gpt-5.6-sol` editorial review;
3. if the acceptance gate fails, asks the same model at medium reasoning effort
   to select exactly five validated raw-pool links per section and regenerates
   changed summaries plus any selected summary explicitly rejected by the review;
4. re-evaluates the repaired edition, with at most five applied repair attempts;
5. normally accepts an editorial score of 82 and operational/reader scores of
   85; and
6. if only soft editorial targets still miss, publishes the same formal
   four-section, five-card-per-section page through the SLA fallback when the
   deterministic operational and reader scores are at least 78, all summaries
   are present, and no hard reader or editorial issue exists.

The fallback never creates an alert-only or reduced page. It continues through
the normal page renderer and normal Kakao summary builder. After a successful
Kakao send, `docs/delivery/YYYY-MM-DD.json` is written as the authoritative
delivery receipt. A same-day rerun suppresses duplicate sends when that receipt
already exists. The watchdog checks the receipt rather than the mere existence
of an Actions run and dispatches a forced deterministic recovery when delivery
is still missing and no daily run is active.

Full model review runs
daily until 20 consecutive evaluated reports pass with
an operational score of at least 95, every editorial score at least 85, and an
average editorial score of at least 90. After that stabilization period, the
free deterministic checks still run every day; full model review runs on Monday
audits or whenever a deterministic anomaly appears. The workflow records token
usage, estimated API cost, repair count, and gate status in the evaluation JSON
and GitHub Actions summary. The post-run publishing step reuses this result and
does not call the model a second time.

Required repository secret: `OPENAI_API_KEY`. The existing Naver, Kakao, and
GitHub configuration remains unchanged.

### Development verification workflow (`dev`)

- `.github/workflows/dev-verify.yml`

This workflow uses `dev` as the source code branch, reads production content from `main`, and writes preview artifacts to `codex/dev-preview`.
The stable `/dev/` URL on GitHub Pages stays on `main`, but now acts as a loader page that fetches the latest preview assets from `codex/dev-preview`.

Behavior:

- Dev run never writes generated preview files back to `main`
- Preview artifacts live on `codex/dev-preview`:
  - `docs/dev/index.html`
  - `docs/dev/version.json`
  - `docs/dev/debug/YYYY-MM-DD.json`
- Stable loader URL: `https://nh-horti.github.io/agri-news-brief/dev/`
- Raw preview asset base: `https://raw.githubusercontent.com/NH-Horti/agri-news-brief/codex/dev-preview/docs/dev`
- Runtime guard blocks writes outside the dev preview paths when `DEV_SINGLE_PAGE_MODE=true`

### Branch sync workflows

- `.github/workflows/promote-dev.yml`
- `.github/workflows/auto-promote-dev.yml`
- `.github/workflows/auto-sync-main-to-dev.yml`

This workflow fast-forwards `main` to `origin/dev` and can optionally dispatch a production rebuild after promotion.
The workflow is intentionally `ff-only` so development history stays clean and production only moves to code that already exists on `dev`.
`auto-promote-dev.yml` runs the same fast-forward automatically after a successful `dev-verify.yml` push run on `dev`.
`auto-sync-main-to-dev.yml` merges `main` back into `dev` after production changes land and then dispatches `dev-verify.yml`, so the preview branch refresh stays close to production code.

### Simple operation flow

1. Develop code on `dev`
2. Push to `dev` or run `dev-verify.yml` manually
3. Review the result on `/dev/`
4. Successful `dev` push runs are auto-promoted to `main`
5. Production changes on `main` are auto-synced back into `dev`
6. Use `promote-dev.yml` only when you want a manual fast-forward or an immediate rebuild dispatch
