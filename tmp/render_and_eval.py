# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("NAVER_CLIENT_ID", "dummy")
os.environ.setdefault("NAVER_CLIENT_SECRET", "dummy")
# keep OPENAI_API_KEY from real env (loaded by caller) but summaries use snapshot cache (allow_openai=False)
os.environ["PUBLISH_MODE"] = "local"
os.environ["PLACEMENT_ONLY"] = "0"
os.environ["MAX_PER_SECTION"] = "5"
os.environ["HF_SEMANTIC_RERANK_ENABLED"] = "false"
os.environ["HF_COMMODITY_BOARD_RERANK_ENABLED"] = "false"
os.environ["REPLAY_SNAPSHOT_PATH"] = "tmp/2026-06-15.snapshot.json"
os.environ["REPLAY_WRITE_SNAPSHOT"] = "false"
sys.path.insert(0, ".")
import main
from datetime import datetime
import pathlib

main._resolve_replay_snapshot_path = lambda rd: pathlib.Path("tmp/2026-06-15.snapshot.json")
# avoid GitHub: rely on snapshot summary cache only
main.load_summary_cache = lambda repo, token: {}
main._list_archive_dates = lambda repo, token: {"2026-06-15"}
main._list_dev_preview_archive_dates = lambda repo, token: {"2026-06-15"}

rd = "2026-06-15"
by_section, summary_cache, s, e = main._build_sections_for_report(
    "owner/repo", "tok", rd, datetime.now(main.KST), datetime.now(main.KST),
    allow_openai=False, replay_snapshot=True,
)
main._finalize_sections_for_render(by_section)
html = main.render_daily_page(rd, s, e, by_section, [rd], "https://nh-horti.github.io/agri-news-brief")
out = pathlib.Path("tmp/rebuilt_0615.html")
out.write_text(html, encoding="utf-8")
print("WROTE", out, len(html), "bytes")
# quick policy check
import re
print("POLICY titles in HTML:")
for m in re.findall(r'data-section="policy"[^>]*data-article-title="([^"]*)"', html)[:8]:
    import html as H
    print("   -", H.unescape(m)[:70])
print("CJ in html:", "CJ프레시웨이" in html, "| 방산 in html:", "방산 퍼즐" in html)
