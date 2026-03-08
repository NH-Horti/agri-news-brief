# agri-news-brief

## Local Validation (optional)

Run local checks manually:

```bash
python -m py_compile main.py collector.py io_github.py retry_utils.py schemas.py ux_patch.py ranking.py orchestrator.py observability.py
python -m mypy --config-file mypy.ini
python -m unittest discover -s tests -p "test_*.py"
```

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

Use two branches and separate workflows:

- `main`: production operation only
- non-`main` (recommended: `develop`): development verification

### Production workflows (main only)

- `.github/workflows/daily.yml`
- `.github/workflows/rebuild.yml`
- `.github/workflows/maintenance.yml`
- `.github/workflows/ux_patch.yml`

Production workflows now run under GitHub Environment `production`.

### Development verification workflow

- `.github/workflows/dev-verify.yml`

Run this workflow with:

- `target_branch`: code branch to verify (e.g. `develop`)
- `content_branch`: branch to publish dev preview page (recommended: `main`)
- `brief_view_url`: Kakao preview base URL (default: `https://nh-horti.github.io/agri-news-brief/dev`)

Behavior:

- Dev run overwrites a single preview page: `docs/dev/index.html`
- Kakao link is fixed to dev preview URL: `${{ inputs.brief_view_url }}/index.html?v=<build>`
- Dev workflow uses `KAKAO_*_DEV` secrets only (no prod fallback)
- Runtime guard blocks writes outside `docs/dev/index.html` when `DEV_SINGLE_PAGE_MODE=true`

### Promotion workflow (develop -> main)

- `.github/workflows/promote.yml`

Use this workflow to promote verified dev code to production:

1. Provide `source_branch` (e.g. `develop`)
2. Provide pinned `source_sha` (required)
3. Optionally enable `run_validation=true` for py_compile/mypy/tests revalidation

Safety built into promote flow:

- Verifies `source_sha` is reachable from source branch
- Enforces fast-forward-only merge into `main`
- Creates rollback tag before merge (`pre-prod-<timestamp>-<run_id>`)

## Safety Guardrails (1~7)

1. Main branch protection: apply via `.github/workflows/repo-hardening.yml`
2. GitHub environments split: `development` and `production`
3. Runtime write guard: dev single-page mode blocks non-dev output writes
4. Dev secrets isolation: `dev-verify.yml` uses only `KAKAO_*_DEV`
5. Promotion-only production update: `promote.yml` with pinned SHA + revalidation
6. Auto rollback point: pre-prod tag created in `promote.yml`
7. Post-run healthcheck: `scripts/post_run_healthcheck.py` verifies expected files and URL host/path

## Required GitHub Setup Checklist

1. Create Environment `development`
2. Create Environment `production` and configure required reviewers
3. Store production secrets in `production` environment (`KAKAO_*`, `NAVER_*`, `OPENAI_API_KEY`)
4. Store dev secrets in `development` environment (`KAKAO_*_DEV`)
5. Add repository secret `ADMIN_GITHUB_TOKEN` (repo admin scope) for branch-protection workflow
6. Run `.github/workflows/repo-hardening.yml` once to enforce main branch protection
7. In branch protection, keep required status check context: `agri-news-brief (ci) / lint-and-test`
