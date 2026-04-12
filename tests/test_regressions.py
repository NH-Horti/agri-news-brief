import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
DEV_VERIFY_WORKFLOW = ROOT / ".github" / "workflows" / "dev-verify.yml"
DAILY_WORKFLOW = ROOT / ".github" / "workflows" / "daily.yml"
MAINTENANCE_WORKFLOW = ROOT / ".github" / "workflows" / "maintenance.yml"
REBUILD_WORKFLOW = ROOT / ".github" / "workflows" / "rebuild.yml"
PROMOTE_WORKFLOW = ROOT / ".github" / "workflows" / "promote-dev.yml"
AUTO_PROMOTE_WORKFLOW = ROOT / ".github" / "workflows" / "auto-promote-dev.yml"
AUTO_SYNC_MAIN_TO_DEV_WORKFLOW = ROOT / ".github" / "workflows" / "auto-sync-main-to-dev.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SECRETS_CHECK_WORKFLOW = ROOT / ".github" / "workflows" / "secrets-check.yml"
DEV_LOADER_HTML = ROOT / "docs" / "dev" / "index.html"
DEV_LOADER_VERSION = ROOT / "docs" / "dev" / "version.json"

class TestRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MAIN.read_text(encoding="utf-8")
        cls.dev_verify_text = DEV_VERIFY_WORKFLOW.read_text(encoding="utf-8")
        cls.daily_text = DAILY_WORKFLOW.read_text(encoding="utf-8")
        cls.maintenance_text = MAINTENANCE_WORKFLOW.read_text(encoding="utf-8")
        cls.rebuild_text = REBUILD_WORKFLOW.read_text(encoding="utf-8")
        cls.promote_text = PROMOTE_WORKFLOW.read_text(encoding="utf-8")
        cls.auto_promote_text = AUTO_PROMOTE_WORKFLOW.read_text(encoding="utf-8")
        cls.auto_sync_text = AUTO_SYNC_MAIN_TO_DEV_WORKFLOW.read_text(encoding="utf-8")
        cls.ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
        cls.secrets_check_text = SECRETS_CHECK_WORKFLOW.read_text(encoding="utf-8")
        cls.dev_loader_text = DEV_LOADER_HTML.read_text(encoding="utf-8")
        cls.dev_loader_version_text = DEV_LOADER_VERSION.read_text(encoding="utf-8")

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
        self.assertIn('a[href],select,input,textarea,button', self.text)

    def test_rebuild_helpers_exist(self):
        self.assertIn("def _compute_window_for_report_date", self.text)
        self.assertIn("def maintenance_rebuild_date", self.text)
        self.assertIn("def maintenance_backfill_rebuild", self.text)

    def test_policy_market_brief_query_registry_exists(self):
        self.assertIn("POLICY_MARKET_BRIEF_QUERIES", self.text)
        self.assertIn('"농산물 가격 동향"', self.text)
        self.assertIn("POLICY_MARKET_BRIEF_RECALL_SIGNALS", self.text)
        self.assertIn("def _recall_common_queries", self.text)
        self.assertIn('"도매시장 경매"', self.text)
        self.assertIn('"농산물 수급 안정 대책"', self.text)
        self.assertIn('return _reject("flower_novelty_noise")', self.text)
        self.assertIn("def _build_web_recall_queries", self.text)
        self.assertIn("GOOGLE_NEWS_RECALL_ENABLED", self.text)
        self.assertIn("def build_google_news_rss_search_url", self.text)
        self.assertIn("def fetch_google_news_search_items", self.text)
        self.assertIn("def reset_debug_report", self.text)

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

    def test_kakao_status_tracking_exists(self):
        self.assertIn('KAKAO_STATUS_FILE = os.getenv("KAKAO_STATUS_FILE", "").strip()', self.text)
        self.assertIn("def _write_kakao_send_status", self.text)
        self.assertIn('_write_kakao_send_status("not_attempted")', self.text)

    def test_default_report_hour_moves_to_6am(self):
        self.assertIn('RUN_HOUR_KST", "6"', self.text)
        self.assertIn('REPORT_HOUR_KST = int(os.getenv("REPORT_HOUR_KST"', self.text)

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

    def test_view_tabs_for_briefing_and_commodity_exist(self):
        self.assertIn('class="viewTab isActive" data-view-tab="briefing"', self.text)
        self.assertIn('class="viewTab" data-view-tab="commodity"', self.text)
        self.assertIn("오늘의 브리핑", self.text)
        self.assertIn("briefingHeroTitle", self.text)
        self.assertIn("commodityHeadStats", self.text)
        self.assertIn("commodityBoardNav", self.text)
        self.assertIn("syncStickyOffsets", self.text)
        self.assertIn("syncFloatingChipbar", self.text)
        self.assertIn("syncMobileQuickNav", self.text)
        self.assertIn('id=\\"chipDock\\"', self.text)
        self.assertIn('id=\\"mobileQuickNav\\"', self.text)
        self.assertIn("--topbar-height", self.text)
        self.assertIn("--chipbar-height", self.text)
        self.assertIn("--nav-chip-height", self.text)
        self.assertIn("--chip-color", self.text)
        self.assertIn("--group-chip-color", self.text)
        self.assertIn(".chipDock{{position:fixed;", self.text)
        self.assertIn(".chip,.commodityGroupChip{{", self.text)
        self.assertIn(".chips,.commodityGroupNav{{display:flex;gap:10px;align-items:center;justify-content:flex-start;width:100%;}}", self.text)
        self.assertIn("@media (max-width: 900px) and (hover: none), (max-width: 900px) and (pointer: coarse){{", self.text)
        self.assertIn(".viewTabEyebrow{{display:none}}", self.text)
        self.assertIn("body.quickNavOpen{{overflow:hidden}}", self.text)
        self.assertIn(".mobileQuickNavBody .chips,", self.text)
        self.assertIn("viewTabTitle", self.text)
        self.assertIn("function activateView(viewKey, opts)", self.text)
        self.assertIn("resolveInitialView()", self.text)
        self.assertIn("function isCompactViewport() {{", self.text)
        self.assertIn("window.innerWidth <= (coarsePointer ? 900 : 640)", self.text)
        self.assertIn("rect.top < dockTop && rect.bottom <= dockTop", self.text)
        self.assertIn('toggle: "품목군 이동"', self.text)
        self.assertIn('title: "품목군 바로가기"', self.text)
        self.assertIn('toggle: "섹션 이동"', self.text)
        self.assertIn('title: "섹션 바로가기"', self.text)

    def test_external_links_use_plain_top_navigation(self):
        self.assertIn('class=\\"btnOpen\\" data-swipe-ignore=\\"1\\"', self.text)
        self.assertIn('class="commodityPrimaryStory"', self.text)
        self.assertIn('class="commoditySupportStory"', self.text)
        self.assertIn('class="commodityMoreStory"', self.text)
        self.assertIn('data-swipe-ignore="1"', self.text)
        self.assertIn('target=\\"_top\\"', self.text)
        self.assertNotIn('querySelectorAll(".btnOpen, .commodityPrimaryStory")', self.text)
        self.assertIn('if (blocked) {{', self.text)
        self.assertIn('swipeActive = false;', self.text)

    def test_dev_verify_does_not_extend_window(self):
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.dev_verify_text)
        self.assertIn("cron: '0 21 * * 0-4'", self.dev_verify_text)
        self.assertIn("if: github.event_name == 'schedule' || github.ref_name == 'dev'", self.dev_verify_text)
        self.assertIn("ref: ${{ github.event_name == 'schedule' && 'dev' || github.ref_name }}", self.dev_verify_text)
        self.assertIn("GH_CONTENT_REF: ${{ steps.vars.outputs.content_ref }}", self.dev_verify_text)
        self.assertIn("content_ref='dev'", self.dev_verify_text)
        self.assertIn("send_kakao='true'", self.dev_verify_text)
        self.assertIn("GH_CONTENT_BRANCH: codex/dev-preview", self.dev_verify_text)
        self.assertIn("PAGES_BRANCH: codex/dev-preview", self.dev_verify_text)
        self.assertIn("git fetch origin codex/dev-preview", self.dev_verify_text)
        self.assertIn('preview_ref = GH_CONTENT_BRANCH or GH_CONTENT_REF or "main"', self.text)

    def test_promote_workflow_exists_for_dev_to_main(self):
        self.assertIn("name: agri-news-brief (promote dev to main)", self.promote_text)
        self.assertIn("git merge --ff-only origin/dev", self.promote_text)
        self.assertIn("actions/workflows/rebuild.yml/dispatches", self.promote_text)
        self.assertIn("default: true", self.promote_text)
        self.assertIn('echo "- Rebuild Kakao requested: ${{ steps.vars.outputs.send_kakao }}"', self.promote_text)

    def test_auto_promote_workflow_promotes_verified_dev_pushes(self):
        self.assertIn("name: agri-news-brief (auto promote dev to main)", self.auto_promote_text)
        self.assertIn("workflow_run:", self.auto_promote_text)
        self.assertIn("agri-news-brief (dev verify rebuild)", self.auto_promote_text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.auto_promote_text)
        self.assertIn("github.event.workflow_run.head_branch == 'dev'", self.auto_promote_text)
        self.assertIn("github.event.workflow_run.event == 'push'", self.auto_promote_text)
        self.assertIn("git merge --ff-only origin/dev", self.auto_promote_text)
        self.assertIn("git push origin HEAD:main", self.auto_promote_text)

    def test_auto_sync_workflow_merges_main_back_into_dev(self):
        self.assertIn("name: agri-news-brief (auto sync main to dev)", self.auto_sync_text)
        self.assertIn("push:", self.auto_sync_text)
        self.assertIn("- main", self.auto_sync_text)
        self.assertIn("if: github.ref_name == 'main'", self.auto_sync_text)
        self.assertIn("actions: write", self.auto_sync_text)
        self.assertIn("git merge-base --is-ancestor origin/main origin/dev", self.auto_sync_text)
        self.assertIn("git merge --no-edit origin/main", self.auto_sync_text)
        self.assertIn("git push origin HEAD:dev", self.auto_sync_text)
        self.assertIn("steps.sync.outputs.synced == 'true'", self.auto_sync_text)
        self.assertIn("actions/workflows/dev-verify.yml/dispatches", self.auto_sync_text)

    def test_rebuild_and_dev_verify_report_actual_kakao_status(self):
        self.assertIn("KAKAO_STATUS_FILE: ${{ runner.temp }}/kakao-status.txt", self.rebuild_text)
        self.assertIn("id: kakao_status", self.rebuild_text)
        self.assertIn('echo "- Kakao actual: ${{ steps.kakao_status.outputs.actual }}"', self.rebuild_text)
        self.assertIn("KAKAO_STATUS_FILE: ${{ runner.temp }}/kakao-status.txt", self.dev_verify_text)
        self.assertIn('echo "- Kakao actual: ${{ steps.kakao_status.outputs.actual }}"', self.dev_verify_text)

    def test_secrets_check_workflow_exists(self):
        self.assertIn("name: agri-news-brief (validate API secrets)", self.secrets_check_text)
        self.assertIn("Validate Naver and Kakao secrets", self.secrets_check_text)
        self.assertIn("https://openapi.naver.com/v1/search/news.json", self.secrets_check_text)
        self.assertIn("https://kauth.kakao.com/oauth/token", self.secrets_check_text)
        self.assertIn('append_summary("- Kakao: success (token refresh)")', self.secrets_check_text)

    def test_dev_loader_uses_preview_branch_assets(self):
        self.assertIn("codex/dev-preview", self.dev_loader_text)
        self.assertIn("previewFrame", self.dev_loader_text)
        self.assertIn("requestedDate", self.dev_loader_text)
        self.assertIn("isMobileViewport()", self.dev_loader_text)
        self.assertIn("/archive/", self.dev_loader_text)
        self.assertIn("srcdoc", self.dev_loader_text)
        self.assertIn("postMessage", self.dev_loader_text)
        self.assertIn("createObjectURL", self.dev_loader_text)
        self.assertIn("revokeObjectURL", self.dev_loader_text)
        self.assertIn("raw preview", self.dev_loader_text)
        self.assertIn("body {", self.dev_loader_text)
        self.assertIn("height: calc(100vh - 180px);", self.dev_loader_text)
        self.assertIn("border-radius: 0;", self.dev_loader_text)
        self.assertIn('"mode": "loader"', self.dev_loader_version_text)
        self.assertIn('"preview_branch": "codex/dev-preview"', self.dev_loader_version_text)

    def test_prod_workflows_do_not_extend_window(self):
        self.assertIn("cron: '0 20 * * 0'", self.daily_text)
        self.assertIn("cron: '5 21 * * 1-4'", self.daily_text)
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.daily_text)
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.maintenance_text)
        self.assertIn("WINDOW_MIN_HOURS: '0'", self.rebuild_text)

    def test_daily_workflow_runs_eval_harness_and_feedback_loop(self):
        self.assertIn("OPENAI_SUMMARY_FEEDBACK_PATH: docs/evals/latest-feedback.txt", self.daily_text)
        self.assertIn("DEBUG_REPORT: '1'", self.daily_text)
        self.assertIn("DEBUG_REPORT_WRITE_JSON: '0'", self.daily_text)
        self.assertIn("scripts/evaluate_daily_report.py", self.daily_text)
        self.assertIn("latest-selection-feedback.json", self.daily_text)
        self.assertIn("docs/evals", self.daily_text)

    def test_dev_verify_workflow_evaluates_preview_report(self):
        self.assertIn("Evaluate rebuilt preview report", self.dev_verify_text)
        self.assertIn("docs/dev/index.html", self.dev_verify_text)
        self.assertIn("reports/evals/", self.dev_verify_text)
        self.assertIn("latest-selection-feedback.json", self.dev_verify_text)

    def test_maintenance_workflow_runs_tests_and_debuggable_backfill(self):
        self.assertIn("requirements-dev.txt", self.maintenance_text)
        self.assertIn("Run smoke checks before backfill", self.maintenance_text)
        self.assertIn("python scripts/run_smoke_checks.py", self.maintenance_text)
        self.assertIn("DEBUG_REPORT:", self.maintenance_text)
        self.assertIn("Write debug JSON for rebuilt archive pages", self.maintenance_text)

    def test_ci_workflow_uses_focused_regression_suite(self):
        self.assertIn("python scripts/run_ci_regression_suite.py", self.ci_text)
if __name__ == "__main__":
    unittest.main()
