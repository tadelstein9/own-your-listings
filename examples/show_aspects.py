#!/usr/bin/env python3
"""Read-only: show category 57720's item aspects (required/recommended) cross-referenced
against what we've filled in the item's ebay_meta.json. Surfaces fill-gaps (Cassini)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import ebay_pull, ebay_taxonomy

SLUG = sys.argv[1] if len(sys.argv) > 1 else "mvt-as1686-pandan-01"
meta = json.load(open(os.path.join(LIB, "photos", SLUG, "ebay_meta.json")))
have = {k: v for k, v in meta["aspects"].items()}
cat = meta["category_id"]

creds = json.load(open(os.path.join(LIB, "ebay_credentials.json")))
tok = ebay_pull.refresh_access_token(creds)
req, opt = ebay_taxonomy.aspects(tok, cat)

def row(a, required):
    name = a["name"]
    filled = have.get(name)
    mark = "REQ " if required else "    "
    tick = "✓ " + ", ".join(filled) if filled else "·  (empty)"
    eg = f"   [eg: {', '.join(a['values'][:4])}]" if a["values"] and not filled else ""
    print(f"  {mark}{name:34} {tick}{eg}")

print(f"Category {cat} aspects — filled vs available for {SLUG}\n")
print("REQUIRED:")
for a in req: row(a, True)
print("\nRECOMMENDED / OPTIONAL:")
for a in opt: row(a, False)

names = {a["name"] for a in req} | {a["name"] for a in opt}
extra = [k for k in have if k not in names]
if extra:
    print("\nWE SET (not in category's list -- eBay may drop these):")
    for k in extra: print(f"    {k:38} ✓ {', '.join(have[k])}")
