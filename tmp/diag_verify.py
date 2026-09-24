# -*- coding: utf-8 -*-
import sys, io, json
sys.path.insert(0, ".")
import main, replay

payload = json.loads(io.open("tmp/2026-06-15.snapshot.json", encoding="utf-8").read())
raw_payload = payload.get("raw_by_section", {})
raw = {}
for key, arts in raw_payload.items():
    out = []
    for d in arts or []:
        try:
            out.append(main.Article(**replay.article_dict_to_kwargs(d)))
        except Exception:
            pass
    raw[key] = out

policy_conf = next((s for s in main.SECTIONS if s.get("key") == "policy"), {})

def is_target(a):
    t = a.title or ""
    return ("CJ프레시웨이" in t) or ("컨펙스" in t) or ("세광푸드" in t)

# 1) target behaviour
tgt = None
for sec, arts in raw.items():
    for a in arts:
        if is_target(a):
            tgt = a; break
    if tgt: break
print("=== TARGET ===")
print("title:", tgt.title)
print("predicate:", main.is_policy_private_commercial_deal_context(tgt.title, tgt.description, main.normalize_host(tgt.domain or ""), (tgt.press or "").strip()))
print("postbuild_reject(policy):", main._postbuild_article_reject_reason(tgt, "policy", apply_selection_fit=False))
print("recovery_rank:", main._policy_underfill_recovery_rank(tgt, policy_conf))
print()

# 2) regression: scan ALL raw articles across sections, flag any newly-rejected by the predicate
print("=== PREDICATE HITS across ALL raw sections (should ONLY be true B2B promo) ===")
hits = 0
for sec, arts in raw.items():
    for a in arts:
        if main.is_policy_private_commercial_deal_context(a.title, a.description, main.normalize_host(a.domain or ""), (a.press or "").strip()):
            hits += 1
            print(f"[{sec}] {(a.title or '')[:90]}")
print("total predicate hits:", hits)
