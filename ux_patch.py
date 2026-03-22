from __future__ import annotations

import json
import re
from typing import Callable


NavBlockExtractor = Callable[[str], tuple[int, int, str] | None]
WarnFn = Callable[[str], None]


# Callbacks used to keep UX patching logic independent from main.py globals.
StripFn = Callable[[str], str]
TransformFn = Callable[[str], str]
DatesSupplier = Callable[[], list[str]]
RenderNavRowFn = Callable[[str, list[str], str], str]
BuildNavRowFn = Callable[[str, list[str], str], str]

ARCHIVE_LABEL = "\uc544\uce74\uc774\ube0c"
LATEST_ARCHIVE_LABEL = "\ucd5c\uc2e0/\uc544\uce74\uc774\ube0c"
MOVING_LABEL = "\ub0a0\uc9dc \uc774\ub3d9 \uc911..."
EMPTY_BRIEF_MESSAGE = "\uc774\ub3d9\ud560 \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4."
PREV_BRIEF_MESSAGE = "\uc774\uc804 \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4."
NEXT_BRIEF_MESSAGE = "\ub2e4\uc74c \ube0c\ub9ac\ud551\uc774 \uc5c6\uc2b5\ub2c8\ub2e4."
PREV_LABEL = "\uc774\uc804"
NEXT_LABEL = "\ub2e4\uc74c"


def _has_modern_archive_interactions(html_text: str) -> bool:
    if not html_text:
        return False
    return (
        'function activateView(viewKey, opts)' in html_text
        or (
            'data-view-tab="commodity"' in html_text
            and 'data-view-pane="commodity"' in html_text
        )
        or 'id="mobileQuickNavSheet"' in html_text
    )


def insert_nav_loading_badge(html_text: str, extract_navrow_block: NavBlockExtractor) -> str:
    """Insert navLoading badge right after navRow only when missing."""
    if not html_text or 'id="navLoading"' in html_text:
        return html_text

    got = extract_navrow_block(html_text)
    if not got:
        return html_text

    _s, e, _blk = got
    loading_block = f"""
      <div id="navLoading" class="navLoading" aria-live="polite" aria-atomic="true">
        <span class="badge">{MOVING_LABEL}</span>
      </div>
"""
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


def _upsert_archive_nav_button(html_text: str) -> str:
    """Normalize the first nav button to the archive label and class hook."""
    html_text = html_text.replace(LATEST_ARCHIVE_LABEL, ARCHIVE_LABEL)
    return re.sub(
        r'<a\s+class="navBtn([^"]*)"\s*([^>]*)>.*?</a>',
        lambda m: f'<a class="navBtn navArchive{m.group(1)}" {m.group(2)}>{ARCHIVE_LABEL}</a>',
        html_text,
        count=1,
        flags=re.I | re.S,
    )


def build_archive_ux_html(
    raw_html: str,
    *,
    iso_date: str,
    site_path: str,
    strip_swipe_hint_blocks: StripFn,
    rebuild_missing_chipbar_from_sections: TransformFn,
    normalize_existing_chipbar_titles: TransformFn,
    get_ux_nav_dates_desc: DatesSupplier,
    extract_navrow_block: NavBlockExtractor,
    render_nav_row: RenderNavRowFn,
    get_manifest_dates_desc_cached: DatesSupplier,
    build_navrow_html_for_date: BuildNavRowFn,
    warn: WarnFn,
) -> str | None:
    html_new = strip_swipe_hint_blocks(raw_html)

    html_new = rebuild_missing_chipbar_from_sections(html_new)
    html_new = normalize_existing_chipbar_titles(html_new)

    # Rebuild navRow from archive dates first so legacy pages do not keep stale links.
    try:
        nav_dates_desc = get_ux_nav_dates_desc()
        if nav_dates_desc and iso_date not in nav_dates_desc:
            nav_dates_desc = [iso_date] + nav_dates_desc
        got_nav = extract_navrow_block(html_new)
        if got_nav and nav_dates_desc:
            s0, e0, _blk = got_nav
            html_new = html_new[:s0] + render_nav_row(iso_date, nav_dates_desc, site_path) + html_new[e0:]
    except Exception as exc:
        warn(f"[WARN] navRow rebuild in ux_patch failed: {exc}")

    html_new = _upsert_archive_nav_button(html_new)

    # Ensure navLoading badge exists.
    html_new = strip_swipe_hint_blocks(html_new)
    html_new = insert_nav_loading_badge(html_new, extract_navrow_block)

    # Mark chipbar/chips as swipe-ignore.
    html_new = ensure_swipe_ignore_attributes(html_new)

    # Safely escape Korean constants for JS string interpolation (XSS prevention).
    # ensure_ascii=False keeps Korean readable; [1:-1] strips outer quotes.
    _js_empty = json.dumps(EMPTY_BRIEF_MESSAGE, ensure_ascii=False)[1:-1]
    _js_prev_msg = json.dumps(PREV_BRIEF_MESSAGE, ensure_ascii=False)[1:-1]
    _js_next_msg = json.dumps(NEXT_BRIEF_MESSAGE, ensure_ascii=False)[1:-1]
    _js_prev_lbl = json.dumps(PREV_LABEL, ensure_ascii=False)[1:-1]
    _js_next_lbl = json.dumps(NEXT_LABEL, ensure_ascii=False)[1:-1]

    js_block = f"""
  <!-- UX_PATCH_BEGIN v20260314-uxnav-korean-copy -->
  <script>
  (function(){{
    var navRow = document.querySelector('.navRow');
    var navLoading = document.getElementById('navLoading');

    function _hideLoading(){{ try{{ if(navLoading) navLoading.classList.remove('show'); }}catch(e){{}} }}
    function _showLoading(){{
      try{{
        if(navLoading) navLoading.classList.add('show');
        setTimeout(_hideLoading, 1200);
      }}catch(e){{}}
    }}

    function _toast(msg){{
      try{{
        var t = document.getElementById('uxToast');
        if(!t){{
          t = document.createElement('div');
          t.id = 'uxToast';
          t.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);background:rgba(17,24,39,.92);color:#fff;padding:10px 12px;border-radius:12px;font-size:14px;max-width:90vw;z-index:99999;display:none;box-shadow:0 6px 16px rgba(0,0,0,.25);';
          document.body.appendChild(t);
        }}
        t.textContent = msg || '{_js_empty}';
        t.style.display = 'block';
        clearTimeout(t.__t);
        t.__t = setTimeout(function(){{ t.style.display='none'; }}, 1600);
      }}catch(e){{}}
    }}

    function _getHref(el){{
      if(!el) return '';
      try{{
        var tag = (el.tagName||'').toLowerCase();
        if(tag === 'a') return el.getAttribute('href') || el.href || '';
        return el.getAttribute('data-href') || el.getAttribute('href') || '';
      }}catch(e){{ return ''; }}
    }}
    function _isDisabled(el){{
      try{{
        if(!el) return true;
        if(el.disabled) return true;
        if(el.classList && el.classList.contains('disabled')) return true;
        return false;
      }}catch(e){{ return true; }}
    }}

    function _pick(kind){{
      if(!navRow) return null;
      var el = navRow.querySelector('[data-nav="' + kind + '"]');
      if(el) return el;
      var btns = navRow.querySelectorAll('a.navBtn,button.navBtn');
      for(var i=0;i<btns.length;i++){{
        var t = (btns[i].textContent||'') + ' ' + (btns[i].getAttribute ? (btns[i].getAttribute('title')||'') : '');
        if(kind==='prev' && t.indexOf('{_js_prev_lbl}')>=0) return btns[i];
        if(kind==='next' && t.indexOf('{_js_next_lbl}')>=0) return btns[i];
      }}
      return null;
    }}

    function _bindNav(el, msg){{
      if(!el || !el.addEventListener) return;
      el.addEventListener('click', function(e){{
        var href = _getHref(el);
        if(!href || _isDisabled(el)){{
          try{{ e.preventDefault(); }}catch(_e){{}}
          _hideLoading();
          _toast(msg);
          return false;
        }}
        _showLoading();
      }}, true);
    }}

    var prev = _pick('prev');
    var next = _pick('next');
    _bindNav(prev, '{_js_prev_msg}');
    _bindNav(next, '{_js_next_msg}');

    var sel = document.getElementById('dateSelect');
    if(sel){{
      try{{ sel.setAttribute('data-swipe-ignore','1'); }}catch(e){{}}
      sel.addEventListener('change', function(){{
        var v = sel.value;
        if(!v) return;
        _showLoading();
        window.location.href = v;
      }});
    }}

    var sx=0, sy=0, st=0;
    var swipeActive = false;
    var swipeSuppressSelection = false;
    var blocked = false;
    var swipeTarget = null;
    var swipePointerId = null;
    var swipeRootUserSelect = '';
    var swipeRootWebkitUserSelect = '';
    var swipeBodyCursor = '';
    var wheelSwipeDx = 0;
    var wheelSwipeDy = 0;
    var wheelSwipeAt = 0;
    var wheelSwipeLockUntil = 0;
    var swipeArea = document.querySelector('.wrap') || document.documentElement || document.body;
    function isBlockedTarget(target){{
      if(!target || !target.closest) return false;
      if(target.closest('[data-swipe-ignore="1"]')) return true;
      if(target.closest('.topbar')) return true;
      if(target.closest('a[href],select,input,textarea,button,[contenteditable="true"]')) return true;
      return false;
    }}
    function _eventPoint(e, phase){{
      try{{
        if(!e) return null;
        if(phase !== 'end' && e.touches && e.touches.length === 1) return {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
        if(phase === 'end' && e.changedTouches && e.changedTouches.length === 1) return {{ x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY }};
        if(typeof e.clientX === 'number' && typeof e.clientY === 'number') return {{ x: e.clientX, y: e.clientY }};
      }}catch(_evtErr){{}}
      return null;
    }}
    function _resetSwipe(){{
      try{{
        if(swipeArea && swipeArea.releasePointerCapture && swipePointerId !== null){{
          swipeArea.releasePointerCapture(swipePointerId);
        }}
      }}catch(_releaseErr){{}}
      _setDesktopSwipeMode(false);
      swipeActive = false;
      blocked = false;
      swipeTarget = null;
      swipePointerId = null;
    }}
    function _setDesktopSwipeMode(active){{
      var root = document.documentElement;
      try{{
        if(active){{
          if(swipeSuppressSelection) return;
          swipeSuppressSelection = true;
          swipeRootUserSelect = (root && root.style) ? (root.style.userSelect || '') : '';
          swipeRootWebkitUserSelect = (root && root.style) ? (root.style.webkitUserSelect || '') : '';
          swipeBodyCursor = (document.body && document.body.style) ? (document.body.style.cursor || '') : '';
          if(root && root.style){{
            root.style.userSelect = 'none';
            root.style.webkitUserSelect = 'none';
          }}
          if(document.body && document.body.style){{
            document.body.style.cursor = 'grabbing';
          }}
          return;
        }}
        if(!swipeSuppressSelection) return;
        swipeSuppressSelection = false;
        if(root && root.style){{
          root.style.userSelect = swipeRootUserSelect;
          root.style.webkitUserSelect = swipeRootWebkitUserSelect;
        }}
        if(document.body && document.body.style){{
          document.body.style.cursor = swipeBodyCursor;
        }}
      }}catch(_desktopSwipeErr){{}}
    }}
    function _resetWheelSwipe(){{
      wheelSwipeDx = 0;
      wheelSwipeDy = 0;
      wheelSwipeAt = 0;
    }}
    function _handleWheelSwipe(e){{
      if(!e) return;
      if(e.ctrlKey) return;
      if(isBlockedTarget(e.target)) return;
      var now = Date.now();
      if(wheelSwipeLockUntil && now < wheelSwipeLockUntil) return;
      if(!wheelSwipeAt || (now - wheelSwipeAt) > 240){{
        _resetWheelSwipe();
      }}
      wheelSwipeAt = now;
      wheelSwipeDx += Number(e.deltaX || 0);
      wheelSwipeDy += Number(e.deltaY || 0);
      if(Math.abs(wheelSwipeDx) < 120) return;
      if(Math.abs(wheelSwipeDx) < Math.abs(wheelSwipeDy) * 1.25) return;
      wheelSwipeLockUntil = now + 700;
      try{{
        if(e.cancelable && e.preventDefault) e.preventDefault();
      }}catch(_wheelPreventErr){{}}
      var totalDx = wheelSwipeDx;
      _resetWheelSwipe();
      if(totalDx > 0) {{
        var n = next || _pick('next');
        var href2 = _getHref(n);
        if(!href2 || _isDisabled(n)){{ _hideLoading(); _toast('{_js_next_msg}'); return; }}
        _showLoading(); window.location.href = href2; return;
      }}
      var p = prev || _pick('prev');
      var href = _getHref(p);
      if(!href || _isDisabled(p)){{ _hideLoading(); _toast('{_js_prev_msg}'); return; }}
      _showLoading(); window.location.href = href;
    }}
    function _beginSwipe(e){{
      if(!swipeArea) return;
      if(e && e.pointerType === 'mouse' && typeof e.button === 'number' && e.button !== 0) return;
      if(e && !e.pointerType && typeof e.button === 'number' && e.button !== 0) return;
      var point = _eventPoint(e, 'start');
      if(!point) return;
      blocked = isBlockedTarget(e ? e.target : null);
      if(blocked){{
        swipeActive = false;
        swipeTarget = null;
        swipePointerId = null;
        return;
      }}
      if(e && (e.pointerType === 'mouse' || (!e.pointerType && !e.touches))){{
        _setDesktopSwipeMode(true);
      }}
      swipeActive = true;
      swipeTarget = e ? (e.target || null) : null;
      swipePointerId = (e && typeof e.pointerId === 'number') ? e.pointerId : null;
      sx = point.x;
      sy = point.y;
      st = Date.now();
      try{{
        if(swipeArea.setPointerCapture && swipePointerId !== null) swipeArea.setPointerCapture(swipePointerId);
      }}catch(_captureErr){{}}
    }}
    function _endSwipe(e){{
      if(!swipeActive) return;
      if(swipePointerId !== null && e && typeof e.pointerId === 'number' && e.pointerId !== swipePointerId) return;
      var point = _eventPoint(e, 'end');
      var startedBlocked = blocked;
      var startedDesktopSwipe = swipeSuppressSelection;
      var startedTarget = swipeTarget;
      _resetSwipe();
      if(!point) return;
      if(startedBlocked || isBlockedTarget(e ? e.target : null) || isBlockedTarget(startedTarget)) return;
      try{{
        var selection = window.getSelection ? window.getSelection() : null;
        var selected = selection ? String(selection) : '';
        if(startedDesktopSwipe && selection && selection.removeAllRanges){{
          selection.removeAllRanges();
          selected = '';
        }}
        if(selected && selected.trim()) return;
      }}catch(_selectionErr){{}}
      var dx = point.x - sx;
      var dy = point.y - sy;
      var dt = Date.now() - st;
      if(dt > 900 || Math.abs(dx) < 60) return;
      if(Math.abs(dx) < Math.abs(dy) * 1.2) return;
      if(dx > 0) {{
        var p = prev || _pick('prev');
        var href = _getHref(p);
        if(!href || _isDisabled(p)){{ _hideLoading(); _toast('{_js_prev_msg}'); return; }}
        _showLoading(); window.location.href = href; return;
      }}
      var n = next || _pick('next');
      var href2 = _getHref(n);
      if(!href2 || _isDisabled(n)){{ _hideLoading(); _toast('{_js_next_msg}'); return; }}
      _showLoading(); window.location.href = href2;
    }}
    if(swipeArea && swipeArea.addEventListener){{
      if(window.PointerEvent){{
        swipeArea.addEventListener('pointerdown', function(e){{ _beginSwipe(e); }}, {{passive:true}});
        window.addEventListener('pointerup', function(e){{ _endSwipe(e); }}, {{passive:true}});
        window.addEventListener('pointercancel', function(){{ _resetSwipe(); }}, {{passive:true}});
      }} else {{
        swipeArea.addEventListener('touchstart', function(e){{ _beginSwipe(e); }}, {{passive:true}});
        swipeArea.addEventListener('touchend', function(e){{ _endSwipe(e); }}, {{passive:true}});
        swipeArea.addEventListener('mousedown', function(e){{ _beginSwipe(e); }});
        window.addEventListener('mouseup', function(e){{ _endSwipe(e); }});
      }}
      swipeArea.addEventListener('dragstart', function(e){{
        if(!swipeActive && !swipeSuppressSelection) return;
        try{{
          if(e && e.preventDefault) e.preventDefault();
        }}catch(_dragErr){{}}
      }});
      swipeArea.addEventListener('wheel', function(e){{
        _handleWheelSwipe(e);
      }}, {{passive:false}});
      window.addEventListener('blur', function(){{ _resetSwipe(); }});
    }}
  }})();
  </script>
  <!-- UX_PATCH_END -->
"""
    if "UX_PATCH_BEGIN" in html_new and "<!-- UX_PATCH_BEGIN" in html_new:
        html_new = re.sub(
            r"<!--\s*UX_PATCH_BEGIN.*?-->\s*<script>.*?</script>\s*<!--\s*UX_PATCH_END.*?-->\s*",
            lambda _m: js_block,
            html_new,
            flags=re.S | re.I,
        )
    elif not _has_modern_archive_interactions(html_new):
        html_new = re.sub(r"<script>[\s\S]*?(touchstart|touchend|pointerdown|pointerup|mousedown|mouseup)[\s\S]*?</script>\s*", "", html_new, flags=re.S | re.I)
        html_new = re.sub(r"(</body>)", lambda _m: js_block + _m.group(1), html_new, count=1, flags=re.I)

    # Safety: never commit if HTML looks broken.
    if "</html>" not in html_new.lower() or "</body>" not in html_new.lower():
        return None
    if "<style" in html_new.lower() and "</style>" not in html_new.lower():
        return None

    # Refresh nav once more from manifest-based dates.
    try:
        dates_desc = get_manifest_dates_desc_cached()
        if dates_desc:
            nav_block = extract_navrow_block(html_new)
            if nav_block:
                s, e, _old = nav_block
                new_nav = build_navrow_html_for_date(iso_date, dates_desc, site_path)
                html_new = html_new[:s] + new_nav + html_new[e:]
    except Exception as _nav_err:
        warn(f"[WARN] final nav refresh from manifest failed: {_nav_err}")

    if html_new == raw_html:
        return None

    return html_new
