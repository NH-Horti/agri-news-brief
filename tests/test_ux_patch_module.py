import unittest

from ux_patch import ensure_swipe_ignore_attributes, insert_nav_loading_badge


class TestUxPatchModule(unittest.TestCase):
    def test_insert_nav_loading_badge(self):
        html = '<div class="navRow">x</div><div class="wrap">y</div>'

        def _extract(text: str):
            s = text.find('<div class="navRow">')
            if s < 0:
                return None
            e = text.find('</div>', s)
            if e < 0:
                return None
            e += len('</div>')
            return (s, e, text[s:e])

        out = insert_nav_loading_badge(html, _extract)
        self.assertIn('id="navLoading"', out)
        self.assertIn('<div class="wrap">y</div>', out)

    def test_ensure_swipe_ignore_attributes_is_idempotent(self):
        html = '<div class="chipbar" data-swipe-ignore="1"><div class="chips" data-swipe-ignore="1"></div></div>'
        out = ensure_swipe_ignore_attributes(html)
        self.assertEqual(out.count('data-swipe-ignore="1"'), 2)


if __name__ == "__main__":
    unittest.main()
