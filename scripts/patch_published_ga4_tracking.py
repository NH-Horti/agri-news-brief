from __future__ import annotations

import argparse
import re
from pathlib import Path


HEAD_MARKER = '<meta name="agri-build" content="'
INDEX_SCRIPT_MARKER = '  <script>\n    (function() {'
ARCHIVE_SCRIPT_MARKER = '  <script>\n    (function() {'


def head_snippet(measurement_id: str) -> str:
    return (
        f'  <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>\n'
        "  <script>\n"
        "    window.dataLayer = window.dataLayer || [];\n"
        "    window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };\n"
        '    window.gtag("js", new Date());\n'
        f'    window.gtag("config", "{measurement_id}", {{ send_page_view: false }});\n'
        "  </script>\n"
    )


def archive_tracking_snippet(report_date: str) -> str:
    return f"""  <script>
    (function() {{
      if (window.__agriArchiveTrackingInstalled) return;
      window.__agriArchiveTrackingInstalled = true;

      var reportDate = {report_date!r};
      var buildId = (document.querySelector('meta[name="agri-build"]') || {{}}).content || "";
      var sectionLabelMap = {{
        "수급": "supply",
        "정책": "policy",
        "유통": "dist",
        "병해충": "pest",
        "리스크": "pest"
      }};

      function track(eventName, params) {{
        try {{
          if (typeof window.gtag !== "function") return;
          var payload = Object.assign({{
            build_id: buildId,
            report_date: reportDate,
            transport_type: "beacon"
          }}, params || {{}});
          window.gtag("event", eventName, payload);
        }} catch (_trackErr) {{}}
      }}

      function getViewMode() {{
        var active = document.querySelector('.viewPane.isActive[data-view-pane]');
        if (active) return active.getAttribute('data-view-pane') || '';
        var url = new URL(window.location.href);
        var view = (url.searchParams.get('view') || '').toLowerCase();
        return view === 'commodity' ? 'commodity' : 'briefing';
      }}

      function getSectionKeyFromText(text) {{
        var raw = String(text || '').trim();
        return sectionLabelMap[raw] || raw;
      }}

      function getArticleParams(target, surface) {{
        var href = '';
        var title = '';
        var section = '';
        if (!target) return null;
        if (target.matches('.btnOpen')) {{
          href = target.getAttribute('href') || '';
          var card = target.closest('.card');
          title = card && card.querySelector('.ttl') ? (card.querySelector('.ttl').textContent || '').trim() : '';
          section = card && card.closest('section[id^="sec-"]') ? ((card.closest('section[id^="sec-"]').id || '').replace(/^sec-/, '')) : '';
        }} else if (target.matches('.commodityPrimaryStory')) {{
          href = target.getAttribute('href') || '';
          title = (target.textContent || '').trim();
          var meta = target.parentElement && target.parentElement.querySelector('.commodityPrimaryMeta');
          var firstMeta = meta ? String(meta.textContent || '').split('·')[0].trim() : '';
          section = getSectionKeyFromText(firstMeta);
        }} else if (target.matches('.commoditySupportStory, .commodityMoreStory')) {{
          href = target.getAttribute('href') || '';
          title = target.querySelector('.commoditySupportText') ? (target.querySelector('.commoditySupportText').textContent || '').trim() : (target.textContent || '').trim();
          var label = target.querySelector('.commoditySupportLabel');
          section = getSectionKeyFromText(label ? label.textContent : '');
        }} else if (target.matches('.card[data-href]')) {{
          href = target.getAttribute('data-href') || '';
          title = target.querySelector('.ttl') ? (target.querySelector('.ttl').textContent || '').trim() : '';
          section = target.closest('section[id^="sec-"]') ? ((target.closest('section[id^="sec-"]').id || '').replace(/^sec-/, '')) : '';
        }}
        if (!href && !title) return null;
        var host = '';
        try {{
          host = href ? (new URL(href, window.location.href).hostname || '') : '';
        }} catch (_urlErr) {{}}
        return {{
          article_id: "",
          article_title: title,
          section: section,
          surface: surface,
          target_domain: host
        }};
      }}

      track('page_view', {{
        page_type: 'archive',
        view_mode: getViewMode(),
        page_title: document.title || '',
        page_path: window.location.pathname || '',
        page_location: window.location.href || ''
      }});

      document.addEventListener('click', function(event) {{
        var card = event.target.closest && event.target.closest('.card[data-href]');
        if (card && !event.target.closest('a,button,select,input,textarea,.topic')) {{
          var cardParams = getArticleParams(card, 'briefing_card');
          if (cardParams) track('article_open', cardParams);
        }}

        var articleLink = event.target.closest && event.target.closest('.btnOpen, .commodityPrimaryStory, .commoditySupportStory, .commodityMoreStory');
        if (articleLink) {{
          var surface = articleLink.matches('.btnOpen') ? 'briefing_open' :
            (articleLink.matches('.commodityPrimaryStory') ? 'commodity_primary' :
            (articleLink.matches('.commoditySupportStory') ? 'commodity_support' : 'commodity_more'));
          var articleParams = getArticleParams(articleLink, surface);
          if (articleParams) track('article_open', articleParams);
        }}

        var jumpLink = event.target.closest && event.target.closest('.chip[href^="#sec-"], .commodityGroupChip[href^="#commodity-group-"]');
        if (jumpLink) {{
          var href = jumpLink.getAttribute('href') || '';
          track('section_jump', {{
            section: href.replace(/^#(?:sec-|commodity-group-)/, ''),
            surface: jumpLink.classList.contains('commodityGroupChip') ? 'commodity_group_chip' : 'briefing_chip'
          }});
        }}

        var topic = event.target.closest && event.target.closest('.topic');
        if (topic) {{
          track('section_jump', {{
            section: (topic.textContent || '').trim(),
            surface: 'topic_badge'
          }});
        }}

        var viewTab = event.target.closest && event.target.closest('.viewTab[data-view-tab]');
        if (viewTab) {{
          var currentActive = document.querySelector('.viewPane.isActive[data-view-pane]');
          var fromView = currentActive ? (currentActive.getAttribute('data-view-pane') || '') : '';
          var toView = viewTab.getAttribute('data-view-tab') || '';
          if (fromView && toView && fromView !== toView) {{
            track('view_tab_switch', {{
              from_view: fromView,
              to_view: toView
            }});
          }}
        }}

        var navLink = event.target.closest && event.target.closest('.navRow a[data-nav]');
        if (navLink) {{
          var navKey = navLink.getAttribute('data-nav') || '';
          var navType = navKey === 'prev' ? 'prev_date' : (navKey === 'next' ? 'next_date' : 'archive_index');
          var toDate = '';
          try {{
            var match = (navLink.getAttribute('href') || '').match(/(\\d{{4}}-\\d{{2}}-\\d{{2}})\\.html/);
            if (match) toDate = match[1];
          }} catch (_navErr) {{}}
          track('archive_nav', {{
            nav_type: navType,
            from_date: reportDate,
            to_date: toDate
          }});
        }}
      }});

      var dateSelect = document.getElementById('dateSelect');
      if (dateSelect) {{
        dateSelect.addEventListener('change', function() {{
          var toDate = '';
          try {{
            var match = String(dateSelect.value || '').match(/(\\d{{4}}-\\d{{2}}-\\d{{2}})\\.html/);
            if (match) toDate = match[1];
          }} catch (_dateErr) {{}}
          track('archive_nav', {{
            nav_type: 'select_date',
            from_date: reportDate,
            to_date: toDate
          }});
        }});
      }}
    }})();
  </script>
"""


def index_tracking_snippet() -> str:
    return """  <script>
    (function() {
      if (window.__agriIndexTrackingInstalled) return;
      window.__agriIndexTrackingInstalled = true;

      var buildId = (document.querySelector('meta[name="agri-build"]') || {}).content || "";
      var lastSearchKey = "";
      var sectionLabelMap = {
        "수급": "supply",
        "정책": "policy",
        "유통": "dist",
        "병해충": "pest",
        "리스크": "pest"
      };

      function track(eventName, params) {
        try {
          if (typeof window.gtag !== "function") return;
          window.gtag("event", eventName, Object.assign({
            build_id: buildId,
            page_type: "home",
            transport_type: "beacon"
          }, params || {}));
        } catch (_trackErr) {}
      }

      function getSectionKey(text) {
        var raw = String(text || "").trim();
        return sectionLabelMap[raw] || raw;
      }

      track("page_view", {
        page_type: "home",
        view_mode: "",
        page_title: document.title || "",
        page_path: window.location.pathname || "",
        page_location: window.location.href || ""
      });

      document.addEventListener("click", function(event) {
        var navLink = event.target.closest && event.target.closest(".btn[href], .grid .card[href]");
        if (navLink) {
          var href = navLink.getAttribute("href") || "";
          var match = href.match(/(\\d{4}-\\d{2}-\\d{2})\\.html/);
          track("archive_nav", {
            nav_type: navLink.classList.contains("btn") ? "latest_brief" : "archive_card",
            from_date: "",
            to_date: match ? match[1] : ""
          });
        }

        var articleLink = event.target.closest && event.target.closest("#results .rLinks a[target='_blank']");
        if (articleLink) {
          var result = articleLink.closest(".result");
          var chips = result ? result.querySelectorAll(".chip") : [];
          var reportDate = chips.length ? (chips[0].textContent || "").trim() : "";
          var sectionText = chips.length > 1 ? (chips[1].textContent || "").trim() : "";
          var titleEl = result ? result.querySelector(".rTitle") : null;
          var host = "";
          try {
            host = articleLink.href ? (new URL(articleLink.href, window.location.href).hostname || "") : "";
          } catch (_urlErr) {}
          track("article_open", {
            article_id: "",
            article_title: titleEl ? (titleEl.textContent || "").trim() : "",
            report_date: reportDate,
            section: getSectionKey(sectionText),
            surface: "search_result",
            target_domain: host
          });
        }
      });

      function trackSearchState() {
        var input = document.getElementById("q");
        var secSel = document.getElementById("secSel");
        var sortSel = document.getElementById("sortSel");
        var fromDate = document.getElementById("fromDate");
        var toDate = document.getElementById("toDate");
        var groupToggle = document.getElementById("groupToggle");
        var box = document.getElementById("results");
        if (!input || !box) return;
        var q = String(input.value || "").trim();
        if (q.length < 2) return;
        var resultCount = box.querySelectorAll(".result").length;
        var eventKey = [
          q,
          secSel ? (secSel.value || "") : "",
          sortSel ? (sortSel.value || "") : "",
          fromDate ? (fromDate.value || "") : "",
          toDate ? (toDate.value || "") : "",
          groupToggle && groupToggle.checked ? "date" : "flat",
          resultCount
        ].join("|");
        if (eventKey === lastSearchKey) return;
        lastSearchKey = eventKey;
        track("search_submit", {
          query: q,
          query_length: q.length,
          result_count: resultCount,
          section_filter: secSel ? (secSel.value || "") : "",
          sort_mode: sortSel ? (sortSel.value || "") : "",
          group_mode: groupToggle && groupToggle.checked ? "date" : "flat"
        });
      }

      var results = document.getElementById("results");
      if (results && typeof MutationObserver !== "undefined") {
        var observer = new MutationObserver(function() {
          window.setTimeout(trackSearchState, 0);
        });
        observer.observe(results, { childList: true, subtree: true });
      }
    })();
  </script>
"""


def inject_once(text: str, marker: str, snippet: str, sentinel: str) -> str:
    if sentinel in text:
        return text
    return text.replace(marker, snippet + marker, 1)


def patch_index(path: Path, measurement_id: str) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = original
    updated = inject_once(updated, '  <meta name="agri-build" content="', head_snippet(measurement_id) + '  <meta name="agri-build" content="', "window.__agriIndexTrackingInstalled")
    updated = inject_once(updated, INDEX_SCRIPT_MARKER, index_tracking_snippet() + INDEX_SCRIPT_MARKER, "window.__agriIndexTrackingInstalled")
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def patch_archive(path: Path, measurement_id: str) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = original
    updated = inject_once(updated, '  <meta name="agri-build" content="', head_snippet(measurement_id) + '  <meta name="agri-build" content="', "window.__agriArchiveTrackingInstalled")
    updated = inject_once(updated, ARCHIVE_SCRIPT_MARKER, archive_tracking_snippet(path.stem) + ARCHIVE_SCRIPT_MARKER, "window.__agriArchiveTrackingInstalled")
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch published static HTML pages with GA4 tracking.")
    parser.add_argument("--measurement-id", required=True)
    parser.add_argument("--root", default="docs")
    args = parser.parse_args()

    docs_root = Path(args.root)
    changed = 0

    index_path = docs_root / "index.html"
    if index_path.is_file() and patch_index(index_path, args.measurement_id.strip()):
        changed += 1

    archive_dir = docs_root / "archive"
    for archive_path in sorted(archive_dir.glob("*.html")):
        if patch_archive(archive_path, args.measurement_id.strip()):
            changed += 1

    print(f"[patch-ga4] changed files: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
