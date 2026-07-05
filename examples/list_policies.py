#!/usr/bin/env python3
"""Read-only: list Stanley's business-policy names+IDs and inventory locations,
so we can populate ebay_app.json. Touches nothing (GET only)."""
import json, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import ebay_pull

creds = json.load(open(os.path.join(LIB, "ebay_credentials.json")))
tok = ebay_pull.refresh_access_token(creds)

def get(path):
    r = urllib.request.Request("https://api.ebay.com" + path,
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.load(resp)

print("== FULFILLMENT (shipping) ==")
for p in get("/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US")["fulfillmentPolicies"]:
    print(f"  {p['fulfillmentPolicyId']}  {p['name']}")
print("== PAYMENT ==")
for p in get("/sell/account/v1/payment_policy?marketplace_id=EBAY_US")["paymentPolicies"]:
    print(f"  {p['paymentPolicyId']}  {p['name']}")
print("== RETURN ==")
for p in get("/sell/account/v1/return_policy?marketplace_id=EBAY_US")["returnPolicies"]:
    print(f"  {p['returnPolicyId']}  {p['name']}")
print("== LOCATIONS ==")
for l in get("/sell/inventory/v1/location")["locations"]:
    a = l["location"]["address"]
    print(f"  {l['merchantLocationKey']}  {a.get('city')},{a.get('stateOrProvince')} {a.get('postalCode')}  [{l.get('merchantLocationStatus')}]")
