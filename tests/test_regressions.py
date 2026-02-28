import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"

class TestRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MAIN.read_text(encoding="utf-8")

    def test_has_data_nav_buttons(self):
        self.assertIn('data-nav="prev"', self.text)
        self.assertIn('data-nav="next"', self.text)

    def test_date_select_has_change_handler(self):
        # older pages: JS must bind change handler on #dateSelect
        self.assertIn('getElementById("dateSelect")', self.text)
        self.assertIn('addEventListener("change"', self.text)

    def test_rebuild_helpers_exist(self):
        self.assertIn("def _compute_window_for_report_date", self.text)
        self.assertIn("def maintenance_rebuild_date", self.text)
        self.assertIn("def maintenance_backfill_rebuild", self.text)

    def test_mandarin_tariff_queries_exist(self):
        self.assertIn("만다린 무관세", self.text)

    def test_manual_force_report_date_short_circuits_in_main(self):
        idx_main = self.text.find("def main():")
        self.assertNotEqual(idx_main, -1)
        main_head = self.text[idx_main: idx_main + 9000]
        idx_force = main_head.find("if FORCE_REPORT_DATE:")
        idx_kakao = main_head.find("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN")
        self.assertTrue(idx_force != -1 and idx_kakao != -1 and idx_force < idx_kakao)

if __name__ == "__main__":
    unittest.main()
