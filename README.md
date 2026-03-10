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

Use two branches:

- `main`: production operation only
- `dev`: development and pre-merge verification

### Production workflows (main only)

- `.github/workflows/daily.yml`
- `.github/workflows/rebuild.yml`
- `.github/workflows/maintenance.yml`
- `.github/workflows/ux_patch.yml`

### Development verification workflow

- `.github/workflows/dev-verify.yml`

This workflow uses the branch where the workflow was dispatched as the source code branch.
It still rebuilds a single preview page and writes it to `docs/dev/index.html` on `main`, so the dev result can be checked without touching production pages.

Behavior:

- Dev run overwrites a single preview page: `docs/dev/index.html`
- Kakao link is fixed to dev preview URL: `${{ inputs.brief_view_url }}/index.html?v=<build>`
- Runtime guard blocks writes outside `docs/dev/index.html` when `DEV_SINGLE_PAGE_MODE=true`

### Simple operation flow

1. Develop code on `dev`
2. Run `dev-verify.yml` to check the result on `/dev/index.html`
3. When ready, merge `dev` into `main`
4. Keep production operation on `main`
