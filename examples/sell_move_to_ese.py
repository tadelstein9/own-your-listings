#!/usr/bin/env python3
"""Move an INVENTORY-API-managed listing (one our engine created) to the eBay Standard
Envelope policy + a <=3oz package weight, so eSE surfaces at checkout. Trading ReviseItem
can't touch inventory-managed listings; this uses the Sell Inventory API instead:
  1) createOrReplaceInventoryItem  -> set packageWeightAndSize.weight = 2 oz
  2) updateOffer (published)       -> listingPolicies.fulfillmentPolicyId = eSE
GET-modify-PUT round-trips; a bad PUT errors and changes nothing.

  python3 examples/sell_move_to_ese.py TOOL-TWEEZER-ESTATE-LOT-01
"""
import json, os, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import ebay_pull

ESE = "275341890019"
SKU = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: sell_move_to_ese.py <SKU>")
tok = ebay_pull.refresh_access_token(json.load(open(os.path.join(LIB, "ebay_credentials.json"))))
BASE = "https://api.ebay.com"
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json",
     "Accept": "application/json", "Content-Language": "en-US"}

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw

# 1) weight on the inventory item
st, item = api("GET", f"/sell/inventory/v1/inventory_item/{SKU}")
if st != 200:
    sys.exit(f"GET inventory_item failed [{st}]: {item}")
item.pop("sku", None)
item.setdefault("packageWeightAndSize", {})
item["packageWeightAndSize"]["weight"] = {"value": 2, "unit": "OUNCE"}
sti, r = api("PUT", f"/sell/inventory/v1/inventory_item/{SKU}", item)
print(f"1) set weight 2 oz -> HTTP {sti}" + ("" if sti in (200,204) else f"  {r}"))

# 2) eSE policy on the (published) offer
st, offers = api("GET", f"/sell/inventory/v1/offer?sku={SKU}")
oid = offers["offers"][0]["offerId"]
st, offer = api("GET", f"/sell/inventory/v1/offer/{oid}")
for k in ("offerId", "listing", "status"):
    offer.pop(k, None)
offer.setdefault("listingPolicies", {})["fulfillmentPolicyId"] = ESE
sto, r2 = api("PUT", f"/sell/inventory/v1/offer/{oid}", offer)
print(f"2) set eSE policy on offer {oid} -> HTTP {sto}" + ("" if sto in (200,204) else f"  {r2}"))

# verify
st, chk = api("GET", f"/sell/inventory/v1/offer/{oid}")
st2, it2 = api("GET", f"/sell/inventory/v1/inventory_item/{SKU}")
print(f"VERIFY: fulfillmentPolicyId = {chk.get('listingPolicies',{}).get('fulfillmentPolicyId')}"
      f"   weight = {it2.get('packageWeightAndSize',{}).get('weight')}")
