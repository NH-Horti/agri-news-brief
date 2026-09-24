# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("NAVER_CLIENT_ID", "dummy")
os.environ.setdefault("NAVER_CLIENT_SECRET", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ["PUBLISH_MODE"] = "local"
os.environ["PLACEMENT_ONLY"] = "1"
os.environ["MAX_PER_SECTION"] = "5"
os.environ["HF_SEMANTIC_RERANK_ENABLED"] = "false"
os.environ["HF_COMMODITY_BOARD_RERANK_ENABLED"] = "false"
os.environ["REPLAY_SNAPSHOT_PATH"] = "tmp/2026-06-15.snapshot.json"
os.environ["REPLAY_WRITE_SNAPSHOT"] = "false"
sys.path.insert(0, ".")
import main
from datetime import datetime

# Point loader at our snapshot path
main._resolve_replay_snapshot_path = lambda rd: __import__("pathlib").Path("tmp/2026-06-15.snapshot.json")

by_section, _sc, s, e = main._build_sections_for_report(
    "owner/repo", "tok", "2026-06-15",
    datetime.now(main.KST), datetime.now(main.KST),
    allow_openai=False, replay_snapshot=True,
)
print("\n================ FINAL POLICY SECTION ================")
pol = by_section.get("policy", [])
print("count:", len(pol))
for a in pol:
    flag = "  <<< CJ/동원 TARGET" if ("CJ프레시웨이" in (a.title or "") or "컨펙스" in (a.title or "")) else ""
    print(f" - [{a.selection_stage or '-'}] fit={getattr(a,'selection_fit_score',0):.2f} core={a.is_core} {(a.title or '')[:70]}{flag}")

print("\nCounts all sections:", {k: len(v) for k, v in by_section.items()})
target_in_policy = any("CJ프레시웨이" in (a.title or "") or "컨펙스" in (a.title or "") for a in pol)
print("\nTARGET STILL IN POLICY:", target_in_policy)
