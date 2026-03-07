from __future__ import annotations

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

    # 0.5) Rebuild navRow from existing archive pages (avoid stale href -> 404)
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

    # 0) Canonicalize label (older pages may have "최신/아카이브")
    html_new = html_new.replace("최신/아카이브", "아카이브")

    # 1) Ensure first nav button is "아카이브" + stable style hook
    html_new = re.sub(
        r'<a\s+class="navBtn([^"]*)"\s*([^>]*)>\s*아카이브\s*</a>',
        lambda m: f'<a class="navBtn navArchive{m.group(1)}" {m.group(2)}>아카이브</a>',
        html_new,
        count=1,
        flags=re.I,
    )
    if "navArchive" not in html_new:
        html_new = re.sub(
            r'<a\s+class="navBtn([^"]*)"\s*([^>]*)>\s*최신/아카이브\s*</a>',
            lambda m: f'<a class="navBtn navArchive{m.group(1)}" {m.group(2)}>아카이브</a>',
            html_new,
            count=1,
            flags=re.I,
        )

    # 2) Ensure navLoading badge exists
    html_new = strip_swipe_hint_blocks(html_new)
    html_new = insert_nav_loading_badge(html_new, extract_navrow_block)

    # 3) Mark chipbar/chips as swipe-ignore
    html_new = ensure_swipe_ignore_attributes(html_new)

    # 4) Upsert canonical UX JS patch block
    js_block = """
  <!-- UX_PATCH_BEGIN v20260301-uxnav-toast -->
  <script>
  (function(){
    var navRow = document.querySelector('.navRow');
    var navLoading = document.getElementById('navLoading');

    function _hideLoading(){ try{ if(navLoading) navLoading.classList.remove('show'); }catch(e){} }
    function _showLoading(){
      try{
        if(navLoading) navLoading.classList.add('show');
        setTimeout(_hideLoading, 1200);
      }catch(e){}
    }

    function _toast(msg){
      try{
        var t = document.getElementById('uxToast');
        if(!t){
          t = document.createElement('div');
          t.id = 'uxToast';
          t.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);background:rgba(17,24,39,.92);color:#fff;padding:10px 12px;border-radius:12px;font-size:14px;max-width:90vw;z-index:99999;display:none;box-shadow:0 6px 16px rgba(0,0,0,.25);';
          document.body.appendChild(t);
        }
        t.textContent = msg || '이동할 브리핑이 없습니다.';
        t.style.display = 'block';
        clearTimeout(t.__t);
        t.__t = setTimeout(function(){ t.style.display='none'; }, 1600);
      }catch(e){}
    }

    function _getHref(el){
      if(!el) return '';
      try{
        var tag = (el.tagName||'').toLowerCase();
        if(tag === 'a') return el.getAttribute('href') || el.href || '';
        return el.getAttribute('data-href') || el.getAttribute('href') || '';
      }catch(e){ return ''; }
    }
    function _isDisabled(el){
      try{
        if(!el) return true;
        if(el.disabled) return true;
        if(el.classList && el.classList.contains('disabled')) return true;
        return false;
      }catch(e){ return true; }
    }

    function _pick(kind){
      if(!navRow) return null;
      var el = navRow.querySelector('[data-nav="' + kind + '"]');
      if(el) return el;
      var btns = navRow.querySelectorAll('a.navBtn,button.navBtn');
      for(var i=0;i<btns.length;i++){
        var t = (btns[i].textContent||'') + ' ' + (btns[i].getAttribute? (btns[i].getAttribute('title')||'') : '');
        if(kind==='prev' && t.indexOf('이전')>=0) return btns[i];
        if(kind==='next' && t.indexOf('다음')>=0) return btns[i];
      }
      return null;
    }

    function _bindNav(el, msg){
      if(!el || !el.addEventListener) return;
      el.addEventListener('click', function(e){
        var href = _getHref(el);
        if(!href || _isDisabled(el)){
          try{ e.preventDefault(); }catch(_e){}
          _hideLoading();
          _toast(msg);
          return false;
        }
        _showLoading();
      }, true);
    }

    var prev = _pick('prev');
    var next = _pick('next');
    _bindNav(prev, '이전 브리핑이 없습니다.');
    _bindNav(next, '다음 브리핑이 없습니다.');

    var sel = document.getElementById('dateSelect');
    if(sel){
      try{ sel.setAttribute('data-swipe-ignore','1'); }catch(e){}
      sel.addEventListener('change', function(){
        var v = sel.value;
        if(!v) return;
        _showLoading();
        window.location.href = v;
      });
    }

    var sx=0, sy=0;
    var swipeArea = document.querySelector('.wrap') || document.documentElement || document.body;
    if(swipeArea && swipeArea.addEventListener){
      swipeArea.addEventListener('touchstart', function(e){
        try{
          var t = e.changedTouches[0];
          sx = t.clientX; sy = t.clientY;
        }catch(_e){}
      }, {passive:true});
      swipeArea.addEventListener('touchend', function(e){
        try{
          var t = e.changedTouches[0];
          var dx = t.clientX - sx;
          var dy = t.clientY - sy;
          if(Math.abs(dx) < 60) return;
          if(Math.abs(dx) < Math.abs(dy)) return;
          if(dx > 0) {
            var p = prev || _pick('prev');
            var href = _getHref(p);
            if(!href || _isDisabled(p)){ _hideLoading(); _toast('이전 브리핑이 없습니다.'); return; }
            _showLoading(); window.location.href = href; return;
          } else {
            var n = next || _pick('next');
            var href2 = _getHref(n);
            if(!href2 || _isDisabled(n)){ _hideLoading(); _toast('다음 브리핑이 없습니다.'); return; }
            _showLoading(); window.location.href = href2; return;
          }
        }catch(_e){}
      }, {passive:true});
    }
  })();
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
    else:
        html_new = re.sub(r"<script>[\s\S]*?(touchstart|touchend)[\s\S]*?</script>\s*", "", html_new, flags=re.S | re.I)
        html_new = re.sub(r"(</body>)", lambda _m: js_block + _m.group(1), html_new, count=1, flags=re.I)

    # 6) Safety: never commit if HTML looks broken
    if "</html>" not in html_new.lower() or "</body>" not in html_new.lower():
        return None
    if "<style" in html_new.lower() and "</style>" not in html_new.lower():
        return None

    if html_new == raw_html:
        return None

    # nav patch from manifest-based dates
    try:
        dates_desc = get_manifest_dates_desc_cached()
        if dates_desc:
            nav_block = extract_navrow_block(html_new)
            if nav_block:
                s, e, _old = nav_block
                new_nav = build_navrow_html_for_date(iso_date, dates_desc, site_path)
                html_new = html_new[:s] + new_nav + html_new[e:]
    except Exception:
        pass

    return html_new