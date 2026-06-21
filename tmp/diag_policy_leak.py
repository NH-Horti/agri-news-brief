# -*- coding: utf-8 -*-
import sys, io
sys.path.insert(0, ".")
import main
import replay
import json

payload = json.loads(io.open("tmp/2026-06-15.snapshot.json", encoding="utf-8").read())
raw_payload = payload.get("raw_by_section", {})
raw_by_section = {}
for key, arts in raw_payload.items():
    out = []
    for d in arts or []:
        try:
            out.append(main.Article(**replay.article_dict_to_kwargs(d)))
        except Exception:
            pass
    raw_by_section[key] = out
policy_conf = next((s for s in main.SECTIONS if s.get("key") == "policy"), {})

def find(arts):
    for a in arts or []:
        t = getattr(a, "title", "") or ""
        if "CJ프레시웨이" in t or "동원" in t or "컨펙스" in t or "세광푸드" in t:
            return a
    return None

art = None
for sec, arts in raw_by_section.items():
    art = find(arts)
    if art:
        print("FOUND in raw section:", sec)
        break

if not art:
    print("NOT FOUND in raw")
    sys.exit(0)

title, desc = art.title, art.description
dom = main.normalize_host(art.domain or "")
press = (art.press or "").strip()
text = main._nfkc_lower(f"{title} {desc}")

print("title:", title)
print("domain:", dom, "press:", press)
print("origin_section:", getattr(art, "origin_section", ""))
print()

rank = main._policy_underfill_recovery_rank(art, policy_conf)
print("recovery_rank =", rank)
print()

# Evaluate each signal
checks = {
 "reject_reason": main._postbuild_article_reject_reason(art, "policy", apply_selection_fit=False),
 "livestock_dominant": main.is_policy_livestock_dominant_context(title, desc, dom, press),
 "retail_sales_trend": main.is_retail_sales_trend_context(text),
 "policy_event_tail": main.is_policy_event_tail_context(title, desc, dom, press),
 "market_brief": main.is_policy_market_brief_context(text, dom, press),
 "stabilization": main.is_supply_stabilization_policy_context(text, dom, press),
 "announcement": main.is_policy_announcement_issue(text, dom, press),
 "macro": main.is_macro_policy_issue(text),
 "major_issue": main.is_policy_major_issue_context(title, desc, dom, press),
 "export_support": main.is_policy_export_support_brief_context(title, desc, dom, press),
 "price_stab_system": main.is_policy_price_stabilization_system_context(title, desc, dom, press),
 "local_price_support": main.is_policy_local_price_support_context(title, desc),
 "local_program": main.is_local_agri_policy_program_context(text),
 "price_collapse": main.is_policy_price_collapse_issue_context(title, desc),
 "legislative_reform": main.is_policy_legislative_reform_context(title, desc, dom, press),
}
anchor = main._policy_horti_anchor_stats(title, desc, dom, press)
checks["anchor_ok"] = bool(anchor.get("anchor_ok"))
try:
    checks["section_fit"] = round(float(main.section_fit_score(title, desc, policy_conf, art.domain or "", art.press or "")), 3)
except Exception as e:
    checks["section_fit"] = "ERR:%s" % e

for k, v in checks.items():
    print(f"  {k:22} = {v}")
