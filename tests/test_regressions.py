import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
DEV_VERIFY_WORKFLOW = ROOT / ".github" / "workflows" / "dev-verify.yml"
DAILY_WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"
MAINTENANCE_WORKFLOW = ROOT / ".github" / "workflows" / "maintenance.yml"
REBUILD_WORKFLOW = ROOT / ".github" / "workflows" / "rebuild.yml"

class TestRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MAIN.read_text(encoding="utf-8")
        cls.dev_verify_text = DEV_VERIFY_WORKFLOW.read_text(encoding="utf-8")
        cls.daily_text = DAILY_WORKFLOW.read_text(encoding="utf-8")
        cls.maintenance_text = MAINTENANCE_WORKFLOW.read_text(encoding="utf-8")
        cls.rebuild_text = REBUILD_WORKFLOW.read_text(encoding="utf-8")

    def test_has_data_nav_buttons(self):
        self.assertIn('data-nav="prev"', self.text)
        self.assertIn('data-nav="next"', self.text)

    def test_date_select_has_change_handler(self):
        # older pages: JS must bind change handler on #dateSelect
        self.assertIn('getElementById("dateSelect")', self.text)
        self.assertIn('addEventListener("change"', self.text)

    def test_desktop_swipe_support_exists(self):
        self.assertIn('window.PointerEvent', self.text)
        self.assertIn('addEventListener("pointerdown"', self.text)
        self.assertIn('addEventListener("pointerup"', self.text)
        self.assertIn('addEventListener("mousedown"', self.text)
        self.assertIn('addEventListener("mouseup"', self.text)
        self.assertIn('setDesktopSwipeMode(true)', self.text)
        self.assertIn('selection.removeAllRanges()', self.text)
        self.assertIn('addEventListener("dragstart"', self.text)
        self.assertIn('handleWheelSwipe(e)', self.text)
        self.assertIn('addEventListener("wheel"', self.text)
        self.assertIn('gotoByOffset(-1', self.text)

    def test_rebuild_helpers_exist(self):
        self.assertIn("def _compute_window_for_report_date", self.text)
        self.assertIn("def maintenance_rebuild_date", self.text)
        self.assertIn("def maintenance_backfill_rebuild", self.text)

    def test_policy_market_brief_query_registry_exists(self):
        self.assertIn("POLICY_MARKET_BRIEF_QUERIES", self.text)
        self.assertIn('"농산물 가격 동향"', self.text)
        self.assertIn("POLICY_MARKET_BRIEF_RECALL_SIGNALS", self.text)

    def test_manual_force_report_date_short_circuits_in_main(self):
        idx_main = self.text.find("def main(")
        self.assertNotEqual(idx_main, -1)
        main_head = self.text[idx_main: idx_main + 9000]
        idx_force = main_head.find("if FORCE_REPORT_DATE:")
        idx_kakao = main_head.find("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN")
        self.assertTrue(idx_force != -1 and idx_kakao != -1 and idx_force < idx_kakao)

    def test_main_dispatches_with_orchestrator(self):
        self.assertIn("from orchestrator import OrchestratorContext, OrchestratorHandlers, execute_orchestration", self.text)
        self.assertIn("execute_orchestration(ctx, handlers)", self.text)

    def test_main_uses_ux_patch_module_builder(self):
        self.assertIn("from ux_patch import build_archive_ux_html", self.text)
        self.assertIn("html_new = build_archive_ux_html(", self.text)

    def test_newdaily_economy_mapping_exists(self):
        self.assertIn('"biz.newdaily.co.kr": "뉴데일리경제"', self.text)

    def test_dist_and_pest_generalized_rules_exist(self):
        self.assertIn('도매시장/농산물시장 인프라·이전·현대화 이슈는 유통·현장 섹션 우선', self.text)
        self.assertIn('벼 기사라도 병해충/방제가 제목·본문에서 명확하면 완전 배제하지 않고 보수 감점', self.text)


    def test_section_event_key_generalization_helpers_exist(self):
        self.assertIn("_EVENT_KEY_SECTIONS = frozenset({\"supply\", \"dist\", \"policy\"})", self.text)
        self.assertIn("def _section_story_signature", self.text)
        self.assertIn("if section_key in _EVENT_KEY_SECTIONS:", self.text)


    def test_cache_busting_and_no_cache_meta_exist(self):
        self.assertIn('def build_daily_url', self.text)
        self.assertIn('cache_bust=True', self.text)
        self.assertIn('http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"', self.text)
    def test_fishery_only_filter_exists(self):
        self.assertIn('FISHERY_STRICT_TERMS', self.text)
        self.assertIn('return _reject("fishery_only")', self.text)


    def test_dev_preview_has_version_probe_markers(self):
        self.assertIn("agri-rendered-at-kst", self.text)
        self.assertIn("agri-dev-version-url", self.text)
        self.assertIn("syncLatestDevBuild", self.text)
        self.assertIn("build_dev_preview_version_json", self.text)

    def test_dev_verify_does_not_extend_window(self):
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.dev_verify_text)

    def test_prod_workflows_do_not_extend_window(self):
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.daily_text)
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.maintenance_text)
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.rebuild_text)
if __name__ == "__main__":
    unittest.main()
