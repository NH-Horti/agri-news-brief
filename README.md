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

Use three branches:

- `main`: production operation only
- `dev`: development code and pre-merge verification
- `codex/dev-preview`: generated preview artifacts only

### Production workflows (main only)

- `.github/workflows/daily.yml`
- `.github/workflows/rebuild.yml`
- `.github/workflows/maintenance.yml`
- `.github/workflows/ux_patch.yml`

`main` is the only branch that publishes production Pages content under `docs/`.

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

### Promotion workflow

- `.github/workflows/promote-dev.yml`

This workflow fast-forwards `main` to `origin/dev` and can optionally dispatch a production rebuild after promotion.
The workflow is intentionally `ff-only` so development history stays clean and production only moves to code that already exists on `dev`.

### Simple operation flow

1. Develop code on `dev`
2. Push to `dev` or run `dev-verify.yml` manually
3. Review the result on `/dev/`
4. When ready, run `promote-dev.yml` to fast-forward `main` to `dev`
5. Optionally trigger `rebuild.yml` for the production date and Kakao send
