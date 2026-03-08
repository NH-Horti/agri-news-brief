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

These workflows are now guarded with `if: github.ref_name == 'main'` and fixed content target:

- `GH_CONTENT_REF=main`
- `GH_CONTENT_BRANCH=main`

### Development verification workflow

- `.github/workflows/dev-verify.yml`

Run this workflow and set `target_branch` (e.g. `develop`) to verify changed code and optional Kakao delivery.
If `target_branch` does not exist, the workflow creates it from `main` automatically before checkout.
`dev-verify.yml` prefers `KAKAO_*_DEV` secrets, and falls back to production Kakao secrets if those are not set.
It writes generated artifacts to the current dev branch via:

- `GH_CONTENT_REF=${{ inputs.target_branch }}`
- `GH_CONTENT_BRANCH=${{ inputs.target_branch }}`

### Promotion flow

1. Develop and verify on `develop` branch (`dev-verify.yml`)
2. Confirm generated page + Kakao message
3. Merge `develop` -> `main`
4. Continue daily production operation on `main`
