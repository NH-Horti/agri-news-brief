import json
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


def _load_build_admin_module():
    path = ROOT / "scripts" / "build_admin_analytics.py"
    spec = importlib.util.spec_from_file_location("build_admin_analytics", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestAdminDashboard(unittest.TestCase):
    def test_article_analytics_id_matches_search_index_generation(self):
        report_date = "2026-03-23"
        url = "https://example.com/article-1"
        title = "Tracked article"
        expected = main._article_analytics_id(report_date, "supply", url, title)

        items = main._make_search_items_for_day(
            report_date,
            {
                "supply": [
                    {
                        "url": url,
                        "title": title,
                        "press": "Example Press",
                        "summary": "Summary",
                        "score": 10.0,
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
            "/agri-news-brief/",
        )

        self.assertEqual(items[0]["id"], expected)

    def test_build_empty_outputs_includes_expected_files(self):
        module = _load_build_admin_module()
        outputs = module.build_empty_outputs(["missing config"])

        self.assertIn("summary", outputs)
        self.assertIn("timeseries", outputs)
        self.assertIn("top_articles", outputs)
        self.assertIn("navigation", outputs)
        self.assertIn("search_terms", outputs)
        self.assertIn("health", outputs)
        self.assertEqual(outputs["health"]["warnings"], ["missing config"])
        self.assertEqual(outputs["timeseries"]["daily"], [])

    def test_load_env_files_reads_explicit_file(self):
        module = _load_build_admin_module()

        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ, {}, clear=True):
            env_path = Path(td) / "ga4.env"
            env_path.write_text(
                "\n".join([
                    "GA4_PROPERTY_ID=123456789",
                    'GA4_MEASUREMENT_ID="G-TEST1234"',
                    "",
                ]),
                encoding="utf-8",
            )

            loaded = module.load_env_files(str(env_path))

            self.assertEqual(loaded, [str(env_path)])
            self.assertEqual(os.getenv("GA4_PROPERTY_ID"), "123456789")
            self.assertEqual(os.getenv("GA4_MEASUREMENT_ID"), "G-TEST1234")

    def test_strict_mode_returns_nonzero_when_config_is_missing(self):
        module = _load_build_admin_module()

        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ, {}, clear=True):
            search_index_path = Path(td) / "search_index.json"
            search_index_path.write_text('{"items":[]}\n', encoding="utf-8")
            output_dir = Path(td) / "out"

            with mock.patch.object(
                sys,
                "argv",
                [
                    "build_admin_analytics.py",
                    "--output-dir",
                    str(output_dir),
                    "--search-index",
                    str(search_index_path),
                    "--strict",
                ],
            ):
                exit_code = module.main()

            self.assertEqual(exit_code, 1)
            health = json.loads((output_dir / "health.json").read_text(encoding="utf-8"))
            self.assertIn("GA4_PROPERTY_ID is not configured.", health["warnings"])


if __name__ == "__main__":
    unittest.main()
