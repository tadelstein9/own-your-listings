#!/usr/bin/env python3
"""Read-only scan of active listings + their current shipping service, to flag the small-item
listings still on Ground Advantage (USPSParcel) that could move to the eBay Standard Envelope
policy. Uses Trading GetSellerList (covers legacy listings the Sell APIs don't). Prints a table;
flags GA rows, and highlights confirmed eSE-eligible categories (117039 Tools & Repair Kits).
Touches nothing.

  python3 examples/scan_active_shipping.py
"""
import json, os, sys, re, urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import ebay_pull

tok = ebay_pull.refresh_access_token(json.load(open(os.path.join(LIB, "ebay_credentials.json"))))

now = datetime.now(timezone.utc)
frm = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
to  = (now + timedelta(days=118)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

SVC = {"USPSParcel": "Ground Advantage", "USPSFirstClass": "First Class (RETIRED)",
       "US_eBayStandardEnvelope": "eBay Standard Envelope", "USPSPriority": "Priority",
       "USPSPriorityMailSmallFlatRateBox": "Priority Sm Flat Rate", "USPSParcelSelect": "Parcel Select"}
# categories confirmed eSE-eligible in this account's testing
ESE_OK = {"117039"}

def call(page):
    body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetSellerListRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <EndTimeFrom>{frm}</EndTimeFrom><EndTimeTo>{to}</EndTimeTo>
  <GranularityLevel>Fine</GranularityLevel>
  <Pagination><EntriesPerPage>200</EntriesPerPage><PageNumber>{page}</PageNumber></Pagination>
  <DetailLevel>ReturnAll</DetailLevel>
</GetSellerListRequest>"""
    req = urllib.request.Request("https://api.ebay.com/ws/api.dll", data=body.encode(),
        headers={"X-EBAY-API-CALL-NAME":"GetSellerList","X-EBAY-API-SITEID":"0",
                 "X-EBAY-API-COMPATIBILITY-LEVEL":"1193","X-EBAY-API-IAF-TOKEN":tok,
                 "Content-Type":"text/xml"})
    return urllib.request.urlopen(req, timeout=120).read().decode()

def tag(block, t):
    m = re.search(rf"<{t}>(.*?)</{t}>", block, re.S)
    return m.group(1) if m else ""

rows, page, pages = [], 1, 1
while page <= pages and page <= 5:
    xml = call(page)
    tp = tag(xml, "TotalNumberOfPages")
    pages = int(tp) if tp.isdigit() else 1
    for it in re.findall(r"<Item>(.*?)</Item>", xml, re.S):
        iid = tag(it, "ItemID"); title = tag(it, "Title")
        cat = tag(tag(it, "PrimaryCategory") or it, "CategoryID")
        # first domestic shipping service
        sopt = re.search(r"<ShippingServiceOptions>(.*?)</ShippingServiceOptions>", it, re.S)
        svc = tag(sopt.group(1), "ShippingService") if sopt else ""
        rows.append((iid, cat, svc, title[:48]))
    page += 1

print(f"active listings scanned: {len(rows)}\n")
ga = [r for r in rows if r[2] == "USPSParcel"]
print(f"=== ON GROUND ADVANTAGE (USPSParcel) -- candidates to move to eSE: {len(ga)} ===")
print(f"{'ItemID':<14}{'Cat':<8}{'eSE?':<6}{'Service':<18}Title")
for iid, cat, svc, title in ga:
    flag = "YES" if cat in ESE_OK else "chk"
    print(f"{iid:<14}{cat:<8}{flag:<6}{SVC.get(svc,svc):<18}{title}")

other = [r for r in rows if r[2] != "USPSParcel"]
if other:
    print(f"\n=== other services (not GA) : {len(other)} ===")
    for iid, cat, svc, title in other:
        print(f"{iid:<14}{cat:<8}{'':<6}{SVC.get(svc,svc):<18}{title}")
