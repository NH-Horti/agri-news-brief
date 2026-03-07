# agri-news-brief

## Local Validation

Run local checks before push:

```bash
python -m py_compile main.py collector.py io_github.py retry_utils.py schemas.py ux_patch.py ranking.py orchestrator.py observability.py
python -m mypy --config-file mypy.ini
python -m unittest discover -s tests -p "test_*.py"
```

## Pre-Push Hook

This repo includes `.githooks/pre-push` so push is blocked when checks fail.

One-time setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-hooks.ps1
```
