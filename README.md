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
