#!/usr/bin/env python3
"""Revise the shipping business policy on one or more LIVE listings to the eBay Standard
Envelope fulfillment policy (275341890019), via Trading ReviseFixedPriceItem. Changes only
the shipping profile -- nothing else on the listing. A category that does not allow eSE makes
eBay reject the revise (Ack=Failure), so the first item doubles as the eligibility test.

  python3 examples/revise_shipping_to_ese.py 306923944605            # one (test)
  python3 examples/revise_shipping_to_ese.py 306923944605 2982...    # batch
"""
import json, os, sys, re, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import ebay_pull

ESE_PROFILE = "275341890019"
items = sys.argv[1:]
if not items:
    print(__doc__); sys.exit(1)

tok = ebay_pull.refresh_access_token(json.load(open(os.path.join(LIB, "ebay_credentials.json"))))

def revise(item_id, call="ReviseFixedPriceItem"):
    # Attach the eSE policy AND declare a <=3oz flat-envelope package so eSE actually
    # surfaces at checkout (weight >3oz gates it out). 2 oz = chain + mailer, honest + safe.
    body = f"""<?xml version="1.0" encoding="utf-8"?>
<{call}Request xmlns="urn:ebay:apis:eBLBaseComponents">
  <Item>
    <ItemID>{item_id}</ItemID>
    <SellerProfiles>
      <SellerShippingProfile><ShippingProfileID>{ESE_PROFILE}</ShippingProfileID></SellerShippingProfile>
    </SellerProfiles>
    <ShippingPackageDetails>
      <WeightMajor unit="lbs">0</WeightMajor>
      <WeightMinor unit="oz">2</WeightMinor>
      <PackageDepth unit="inches">0.25</PackageDepth>
      <PackageLength unit="inches">6</PackageLength>
      <PackageWidth unit="inches">4</PackageWidth>
    </ShippingPackageDetails>
  </Item>
</{call}Request>"""
    req = urllib.request.Request("https://api.ebay.com/ws/api.dll", data=body.encode(),
        headers={"X-EBAY-API-CALL-NAME":call,"X-EBAY-API-SITEID":"0",
                 "X-EBAY-API-COMPATIBILITY-LEVEL":"1193","X-EBAY-API-IAF-TOKEN":tok,
                 "Content-Type":"text/xml"})
    try:
        return urllib.request.urlopen(req, timeout=90).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()

def field(xml, t):
    m = re.search(rf"<{t}>(.*?)</{t}>", xml, re.S); return m.group(1) if m else ""

for iid in items:
    xml = revise(iid)
    ack = field(xml, "Ack")
    # if this is an auction-style item, Trading tells us to use ReviseItem instead
    if ack == "Failure" and "ReviseItem" in xml and "FixedPrice" in xml:
        xml = revise(iid, "ReviseItem"); ack = field(xml, "Ack")
    errs = re.findall(r"<Errors>(.*?)</Errors>", xml, re.S)
    msgs = "; ".join(field(e, "LongMessage") for e in errs) if errs else ""
    print(f"{iid}: Ack={ack or '?'}   {msgs[:300]}")
