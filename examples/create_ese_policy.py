#!/usr/bin/env python3
"""Create a single eBay fulfillment (shipping) business policy named "eBay Standard Envelope"
on Stanley's account (Sell Account API, EBAY_US). Mirrors the shape of the existing
"First Class" policy (learned via GET). A 400 (e.g. bad shippingServiceCode) creates
NOTHING -- the whole request is rejected -- so it is safe to run and adjust.

Tries the primary eSE service code first; on rejection, prints eBay's error so we can
swap in the valid code and rerun. Idempotency guard: refuses if a policy with this name
already exists.

  python3 examples/create_ese_policy.py            # create
  python3 examples/create_ese_policy.py --dry-run  # print the body, send nothing
"""
import json, os, sys, urllib.request, urllib.error, argparse

HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import ebay_pull

NAME = "eBay Standard Envelope"
# eSE service code candidates (Sell Account API). Primary first; the rest are fallbacks
# to try by hand if the primary 400s as an invalid shippingServiceCode.
SERVICE_CODE = "US_eBayStandardEnvelope"   # fallbacks: "eBayStandardEnvelope", "USPSStandardEnvelope"
CARRIER_CODE = "USPS"
FREE_SHIPPING = True                        # absorb the ~$0.66-$1 eSE cost; set False to charge buyer
FLAT_COST = "0.0"                           # buyer-paid cost when FREE_SHIPPING is False
HANDLING_DAYS = 1

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

creds = json.load(open(os.path.join(LIB, "ebay_credentials.json")))
tok = ebay_pull.refresh_access_token(creds)
BASE = "https://api.ebay.com"
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json",
     "Accept": "application/json", "Content-Language": "en-US"}

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw

# Guard: do not duplicate a same-named policy.
_, existing = api("GET", "/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US")
for p in existing.get("fulfillmentPolicies", []):
    if p["name"].strip().lower() == NAME.lower():
        print(f"ALREADY EXISTS: {p['fulfillmentPolicyId']}  {p['name']}  -- nothing to do.")
        sys.exit(0)

policy = {
    "name": NAME,
    "marketplaceId": "EBAY_US",
    "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES", "default": False}],
    "handlingTime": {"value": HANDLING_DAYS, "unit": "DAY"},
    "shippingOptions": [{
        "optionType": "DOMESTIC",
        "costType": "FLAT_RATE",
        "shippingServices": [{
            "sortOrder": 1,
            "shippingCarrierCode": CARRIER_CODE,
            "shippingServiceCode": SERVICE_CODE,
            "shippingCost": {"value": ("0.0" if FREE_SHIPPING else FLAT_COST), "currency": "USD"},
            "additionalShippingCost": {"value": "0.0", "currency": "USD"},
            "freeShipping": FREE_SHIPPING,
            "buyerResponsibleForShipping": False,
            "buyerResponsibleForPickup": False,
        }],
        "shippingDiscountProfileId": "0",
        "shippingPromotionOffered": False,
    }],
}

print(json.dumps(policy, indent=2))
if args.dry_run:
    print("\n--dry-run: nothing sent.")
    sys.exit(0)

status, resp = api("POST", "/sell/account/v1/fulfillment_policy", policy)
print(f"\nHTTP {status}")
if status in (200, 201):
    print(f"CREATED  fulfillmentPolicyId = {resp.get('fulfillmentPolicyId')}   name = {resp.get('name')}")
else:
    print("NOT created. eBay said:")
    print(json.dumps(resp, indent=2) if isinstance(resp, (dict, list)) else resp)
    print(f"\nIf the error is an invalid shippingServiceCode, edit SERVICE_CODE "
          f"(try: eBayStandardEnvelope, USPSStandardEnvelope) and rerun.")
