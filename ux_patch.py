from __future__ import annotations

import re
from typing import Callable


NavBlockExtractor = Callable[[str], tuple[int, int, str] | None]


def insert_nav_loading_badge(html_text: str, extract_navrow_block: NavBlockExtractor) -> str:
    """Insert navLoading badge right after navRow only when missing."""
    if not html_text or 'id="navLoading"' in html_text:
        return html_text

    got = extract_navrow_block(html_text)
    if not got:
        return html_text

    _s, e, _blk = got
    loading_block = '''
      <div id="navLoading" class="navLoading" aria-live="polite" aria-atomic="true">
        <span class="badge">날짜 이동 중…</span>
      </div>
'''
    return html_text[:e] + loading_block + html_text[e:]


def ensure_swipe_ignore_attributes(html_text: str) -> str:
    """Add swipe-ignore attributes once (idempotent)."""
    if not html_text:
        return html_text

    out = re.sub(
        r'(<div\s+class="chipbar"(?![^>]*\bdata-swipe-ignore=))',
        r'\1 data-swipe-ignore="1"',
        html_text,
        count=1,
        flags=re.I,
    )
    out = re.sub(
        r'(<div\s+class="chips"(?![^>]*\bdata-swipe-ignore=))',
        r'\1 data-swipe-ignore="1"',
        out,
        count=1,
        flags=re.I,
    )
    return out
