"""Local replay build + result verification.

Usage:
    python scripts/local_replay_verify.py [--date 2026-04-07]

Runs a replay build locally (no API calls), then prints:
  - Core articles per section
  - Articles per section
  - Duplicate detection summary
  - Non-horti articles in supply

Typical run time: 10-30 seconds.
"""
import os, sys, json, re
from pathlib import Path

# Fix encoding on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Set env for local dry-run
os.environ.setdefault("NAVER_CLIENT_ID", "dummy")
os.environ.setdefault("NAVER_CLIENT_SECRET", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("KAKAO_REST_API_KEY", "")
os.environ.setdefault("KAKAO_REFRESH_TOKEN", "")
os.environ.setdefault("GH_TOKEN", "")
os.environ.setdefault("GITHUB_REPO", "NH-Horti/agri-news-brief")
os.environ.setdefault("PUBLISH_MODE", "local")
os.environ.setdefault("REPLAY_WRITE_SNAPSHOT", "false")
os.environ.setdefault("MAX_PER_SECTION", "5")
os.environ.setdefault("HF_SEMANTIC_RERANK_ENABLED", "false")  # skip HF for speed

report_date = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else "2026-04-07"

# Set replay snapshot path
snapshot_path = ROOT / ".agri_replay" / f"{report_date}.snapshot.json"
if not snapshot_path.exists():
    print(f"ERROR: snapshot not found: {snapshot_path}")
    sys.exit(1)

os.environ["REPLAY_SNAPSHOT_PATH"] = str(snapshot_path)
os.environ["FORCE_REPORT_DATE"] = report_date
os.environ["FORCE_RUN_ANYDAY"] = "true"
os.environ["MAINTENANCE_TASK"] = "replay"

print(f"=== Local Replay Build: {report_date} ===")
print(f"Snapshot: {snapshot_path} ({snapshot_path.stat().st_size // 1024}KB)")
print()

import main

# Find output HTML
output_dir = ROOT / "output" / report_date
html_files = list(output_dir.glob("*.html")) if output_dir.exists() else []
if not html_files:
    # Check docs/archive
    archive_html = ROOT / "docs" / "archive" / f"{report_date}.html"
    if archive_html.exists():
        html_files = [archive_html]

# Also check local output path
local_out = ROOT / "output"
if local_out.exists():
    for f in local_out.rglob(f"*{report_date}*.html"):
        if f not in html_files:
            html_files.append(f)

if not html_files:
    print("WARNING: No HTML output found, checking main.py output location...")
    # The replay build may output differently; let's analyze from the build result

print("\n=== VERIFICATION ===\n")

# Read the generated HTML
for html_path in html_files:
    raw = html_path.read_text(encoding="utf-8")
    print(f"HTML: {html_path} ({len(raw)} bytes)")

    # Count articles per section
    for sec in ("supply", "policy", "dist", "pest"):
        count = len(re.findall(f'data-section="{sec}" data-surface="briefing_card"', raw))
        print(f"  {sec}: {count}건")

    # Extract core articles
    print("\n--- 핵심 기사 ---")
    blocks = re.split(r'<div class="card"', raw)
    for block in blocks:
        if 'badgeCore' in block:
            sec_m = re.search(r'data-section="(\w+)"', block)
            ttl_m = re.search(r'data-article-title="([^"]*)"', block)
            if sec_m and ttl_m:
                import html as htmlmod
                sec = sec_m.group(1)
                ttl = htmlmod.unescape(ttl_m.group(1))
                horti = "✓" if any(w in ttl for w in main._SUPPLY_HORTI_GATE_ITEMS) else "✗"
                livestock = "⚠축산" if any(w in ttl.lower() for w in main._SUPPLY_LIVESTOCK_ITEMS) else ""
                mgmt = "⚠인사" if any(w in ttl.lower() for w in main._SUPPLY_MGMT_ITEMS) else ""
                flag = f" [{livestock}{mgmt}]" if livestock or mgmt else ""
                print(f"  [{sec:8s}] {horti} {ttl[:70]}{flag}")

    # Check supply for non-horti articles
    print("\n--- supply 비원예 기사 점검 ---")
    supply_titles = re.findall(
        r'data-article-title="([^"]*)"[^>]*data-report-date="[^"]*"[^>]*data-section="supply"',
        raw
    )
    seen_titles = set()
    non_horti_count = 0
    for t in supply_titles:
        t = re.sub(r'&#\d+;', '', t)
        import html as htmlmod
        t = htmlmod.unescape(t)
        if t in seen_titles:
            continue
        seen_titles.add(t)
        if not any(w in t for w in main._SUPPLY_HORTI_GATE_ITEMS):
            non_horti_count += 1
            print(f"  ✗ {t[:70]}")
    if non_horti_count == 0:
        print("  (없음 - 모두 원예 품목 포함)")
    else:
        print(f"  → 비원예 {non_horti_count}건 발견")

    # Check dedup: similar titles
    print("\n--- 중복 기사 점검 ---")
    all_titles = re.findall(r'data-article-title="([^"]*)"[^>]*data-section="(\w+)"', raw)
    seen = {}
    dupes = []
    for t, sec in all_titles:
        import html as htmlmod
        t = htmlmod.unescape(t)
        # Normalize for comparison: first 15 chars
        key = re.sub(r'[^\w]', '', t)[:15]
        if key in seen:
            if seen[key][1] not in [x[1] for x in dupes if x[0] == key]:
                dupes.append((key, seen[key][0], seen[key][1]))
            dupes.append((key, t, sec))
        else:
            seen[key] = (t, sec)

    if dupes:
        groups = {}
        for key, t, sec in dupes:
            groups.setdefault(key, []).append((t[:50], sec))
        for key, items in groups.items():
            print(f"  중복그룹: {items[0][0]}...")
            for t, sec in items:
                print(f"    [{sec}] {t}")
    else:
        print("  (중복 없음)")

print("\n=== DONE ===")
