import unittest

from ux_patch import build_archive_ux_html, ensure_swipe_ignore_attributes, insert_nav_loading_badge


ARCHIVE_LABEL = "\uc544\uce74\uc774\ube0c"
MOVING_LABEL = "\ub0a0\uc9dc \uc774\ub3d9 \uc911..."
PREV_BRIEF_MESSAGE = "\uc774\uc804 \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4."
NEXT_BRIEF_MESSAGE = "\ub2e4\uc74c \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4."


class TestUxPatchModule(unittest.TestCase):
    def test_insert_nav_loading_badge(self):
        html = '<div class="navRow">x</div><div class="wrap">y</div>'

        def _extract(text: str):
            s = text.find('<div class="navRow">')
            if s < 0:
                return None
            e = text.find("</div>", s)
            if e < 0:
                return None
            e += len("</div>")
            return (s, e, text[s:e])

        out = insert_nav_loading_badge(html, _extract)
        self.assertIn('id="navLoading"', out)
        self.assertIn(MOVING_LABEL, out)
        self.assertIn('<div class="wrap">y</div>', out)

    def test_ensure_swipe_ignore_attributes_is_idempotent(self):
        html = '<div class="chipbar" data-swipe-ignore="1"><div class="chips" data-swipe-ignore="1"></div></div>'
        out = ensure_swipe_ignore_attributes(html)
        self.assertEqual(out.count('data-swipe-ignore="1"'), 2)

    def test_build_archive_ux_html_contract(self):
        html = f"""
<html><body>
<div class="navRow"><a class="navBtn">{ARCHIVE_LABEL}</a></div>
<div class="chipbar"><div class="chips"></div></div>
<div class="wrap">body</div>
</body></html>
"""

        def _extract(text: str):
            marker = '<div class="navRow">'
            s = text.find(marker)
            if s < 0:
                return None
            e = text.find("</div>", s)
            if e < 0:
                return None
            e += len("</div>")
            return (s, e, text[s:e])

        out = build_archive_ux_html(
            html,
            iso_date="2026-03-07",
            site_path="/",
            strip_swipe_hint_blocks=lambda x: x,
            rebuild_missing_chipbar_from_sections=lambda x: x,
            normalize_existing_chipbar_titles=lambda x: x,
            get_ux_nav_dates_desc=lambda: ["2026-03-07", "2026-03-06"],
            extract_navrow_block=_extract,
            render_nav_row=lambda iso, dates, site: '<div class="navRow">nav</div>',
            get_manifest_dates_desc_cached=lambda: ["2026-03-07", "2026-03-06"],
            build_navrow_html_for_date=lambda iso, dates, site: '<div class="navRow">patched</div>',
            warn=lambda _msg: None,
        )

        self.assertIsInstance(out, str)
        self.assertIn('id="navLoading"', out)
        self.assertIn('data-swipe-ignore="1"', out)
        self.assertIn(MOVING_LABEL, out)
        self.assertIn(PREV_BRIEF_MESSAGE, out)
        self.assertIn(NEXT_BRIEF_MESSAGE, out)
        self.assertIn("PointerEvent", out)
        self.assertIn("function isBlockedTarget", out)
        self.assertIn('target.closest(\'.topbar\')', out)
        self.assertIn("_setDesktopSwipeMode", out)
        self.assertIn("removeAllRanges", out)
        self.assertIn("dragstart", out)
        self.assertIn("_handleWheelSwipe", out)
        self.assertIn("addEventListener('wheel'", out)
        self.assertIn("_openExternalLink", out)
        self.assertIn("querySelectorAll('.btnOpen, .commodityStory')", out)
        self.assertIn("window.top && window.top !== window", out)
        self.assertIn("pointerdown", out)
        self.assertIn("pointerup", out)
        self.assertIn("mousedown", out)
        self.assertIn("mouseup", out)

    def test_build_archive_ux_html_updates_nav_even_if_only_manifest_nav_changed(self):
        def _extract(text: str):
            marker = '<div class="navRow">'
            s = text.find(marker)
            if s < 0:
                return None
            e = text.find("</div>", s)
            if e < 0:
                return None
            e += len("</div>")
            return (s, e, text[s:e])

        seed = f"""
<html><body>
<div class="navRow"><a class="navBtn">{ARCHIVE_LABEL}</a></div>
<div class="chipbar" data-swipe-ignore="1"><div class="chips" data-swipe-ignore="1"></div></div>
<div class="wrap">body</div>
</body></html>
"""

        first = build_archive_ux_html(
            seed,
            iso_date="2026-03-07",
            site_path="/",
            strip_swipe_hint_blocks=lambda x: x,
            rebuild_missing_chipbar_from_sections=lambda x: x,
            normalize_existing_chipbar_titles=lambda x: x,
            get_ux_nav_dates_desc=lambda: [],
            extract_navrow_block=_extract,
            render_nav_row=lambda iso, dates, site: '<div class="navRow">nav-a</div>',
            get_manifest_dates_desc_cached=lambda: ["2026-03-07"],
            build_navrow_html_for_date=lambda iso, dates, site: '<div class="navRow">nav-a</div>',
            warn=lambda _msg: None,
        )
        self.assertIsInstance(first, str)

        second = build_archive_ux_html(
            first,
            iso_date="2026-03-07",
            site_path="/",
            strip_swipe_hint_blocks=lambda x: x,
            rebuild_missing_chipbar_from_sections=lambda x: x,
            normalize_existing_chipbar_titles=lambda x: x,
            get_ux_nav_dates_desc=lambda: [],
            extract_navrow_block=_extract,
            render_nav_row=lambda iso, dates, site: '<div class="navRow">nav-a</div>',
            get_manifest_dates_desc_cached=lambda: ["2026-03-07", "2026-03-06"],
            build_navrow_html_for_date=lambda iso, dates, site: '<div class="navRow">nav-b</div>',
            warn=lambda _msg: None,
        )

        self.assertIsInstance(second, str)
        self.assertIn("nav-b", second)


if __name__ == "__main__":
    unittest.main()
