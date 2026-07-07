#!/usr/bin/env python3
"""Correct retired-USPS-service fulfillment policies IN PLACE: swap every
shippingServiceCode "USPSFirstClass" -> "USPSGroundAdvantage" (USPS folded First Class
Package into Ground Advantage, mid-2023; listings on the dead service get throttled).

Updating the policy keeps its ID, so every live listing attached to it stays attached and
picks up the valid service -- no per-listing edits, no delete (which the attached items block
anyway). Name/handling/free-shipping/cost are left exactly as they were.

A 400 (e.g. bad service code) updates NOTHING -- the whole PUT is rejected -- so it is safe.

  python3 examples/fix_firstclass_to_ground.py 71421334019            # fix one
  python3 examples/fix_firstclass_to_ground.py 71421334019 --dry-run  # show before/after only
  python3 examples/fix_firstclass_to_ground.py ALL                    # fix all retired ones
"""
import json, os, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import ebay_pull

OLD, NEW = "USPSFirstClass", "USPSParcel"   # USPSParcel is what eBay now labels "USPS Ground Advantage"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
dry = "--dry-run" in sys.argv
if not args:
    print(__doc__); sys.exit(1)

tok = ebay_pull.refresh_access_token(json.load(open(os.path.join(LIB, "ebay_credentials.json"))))
BASE = "https://api.ebay.com"
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json",
     "Accept": "application/json", "Content-Language": "en-US"}

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, (json.load(r) if r.length != 0 else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw

# Resolve target IDs
all_pols = api("GET", "/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US")[1]["fulfillmentPolicies"]
if args == ["ALL"]:
    targets = [p["fulfillmentPolicyId"] for p in all_pols
               if any(s.get("shippingServiceCode") == OLD
                      for o in p.get("shippingOptions", []) for s in o.get("shippingServices", []))]
    print(f"retired-service policies: {targets}")
else:
    targets = args

for pid in targets:
    status, pol = api("GET", f"/sell/account/v1/fulfillment_policy/{pid}")
    if status != 200:
        print(f"{pid}: GET failed {status}: {pol}"); continue
    name = pol.get("name")
    swapped = 0
    for o in pol.get("shippingOptions", []):
        for s in o.get("shippingServices", []):
            if s.get("shippingServiceCode") == OLD:
                s["shippingServiceCode"] = NEW; swapped += 1
    print(f"\n{pid}  \"{name}\"  -- {swapped} service(s) {OLD} -> {NEW}")
    if swapped == 0:
        print("  nothing to change; skipped."); continue
    if dry:
        print("  --dry-run: not sent."); continue
    # PUT the full policy back, minus the read-only id.
    body = {k: v for k, v in pol.items() if k != "fulfillmentPolicyId"}
    st, resp = api("PUT", f"/sell/account/v1/fulfillment_policy/{pid}", body)
    if st in (200, 204):
        print(f"  UPDATED (HTTP {st}). Now ships {NEW}.")
    else:
        print(f"  NOT updated (HTTP {st}). eBay said:")
        print("  " + (json.dumps(resp) if isinstance(resp, (dict, list)) else str(resp)))
        print(f"  If '{NEW}' is invalid, that is the wrong Ground Advantage code -- tell me and I'll adjust.")
