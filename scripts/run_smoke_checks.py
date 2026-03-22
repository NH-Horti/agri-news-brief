from __future__ import annotations

import py_compile
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMPILE_TARGETS = [
    "main.py",
    "collector.py",
    "io_github.py",
    "retry_utils.py",
    "schemas.py",
    "ux_patch.py",
    "ranking.py",
    "orchestrator.py",
    "observability.py",
    "replay.py",
]

SMOKE_PATTERNS = [
    "test_branch_isolation.py",
    "test_runtime_guards.py",
    "test_orchestrator.py",
    "test_contract_io_github.py",
    "test_contract_collector.py",
    "test_write_optimizations.py",
    "test_retry_utils.py",
    "test_commodity_board.py",
    "test_replay.py",
]


def run_py_compile() -> None:
    for rel_path in COMPILE_TARGETS:
        py_compile.compile(str(ROOT / rel_path), doraise=True)


def build_smoke_suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for pattern in SMOKE_PATTERNS:
        suite.addTests(loader.discover(str(ROOT / "tests"), pattern=pattern))
    return suite


def main() -> int:
    run_py_compile()
    suite = build_smoke_suite()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
