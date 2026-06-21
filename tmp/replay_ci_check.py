# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("NAVER_CLIENT_ID", "dummy"); os.environ.setdefault("NAVER_CLIENT_SECRET", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ["PUBLISH_MODE"]="local"; os.environ["PLACEMENT_ONLY"]="1"; os.environ["MAX_PER_SECTION"]="5"
os.environ["HF_SEMANTIC_RERANK_ENABLED"]="false"; os.environ["HF_COMMODITY_BOARD_RERANK_ENABLED"]="false"
os.environ["REPLAY_SNAPSHOT_PATH"]="tmp/snap_ci_0615.json"; os.environ["REPLAY_WRITE_SNAPSHOT"]="false"
sys.path.insert(0,".")
import main, pathlib
from datetime import datetime
main._resolve_replay_snapshot_path = lambda rd: pathlib.Path("tmp/snap_ci_0615.json")
by_section,_sc,s,e = main._build_sections_for_report("o/r","t","2026-06-15",datetime.now(main.KST),datetime.now(main.KST),allow_openai=False,replay_snapshot=True)
for sk in ("supply","policy","dist","pest"):
    lst=by_section.get(sk,[])
    print(f"\n=== {sk} ({len(lst)}) ===")
    for a in lst:
        print(f"  [{a.selection_stage or '-'}] core={a.is_core} {(a.title or '')[:62]}")
sup=by_section.get("supply",[])
print("\n쉼터 in supply:", any('쉼터' in (a.title or '') for a in sup))
