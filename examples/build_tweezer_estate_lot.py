#!/usr/bin/env python3
"""Intake for a 3-piece watchmaker's ESTATE LOT of tweezers: two PEER-VIGOR Switzerland
brass tweezers (mark "AM"; brass = non-magnetic) + one no-brand STAINLESS NON-MAGNETIC
No.3. Pooling all 15 photos into one lot clears the thin-photo-count quality flag that
3-5 photos per single would trip. Category 117039 (Tools & Repair Kits) from Taxonomy.
Ships Ground Advantage (ebay_app.json default policy 71421334019, now USPSParcel = Ground
Advantage). Best Offer on by default. NO coupon text in the listing -- Tom applies that via
Seller Hub promotions after it goes live. Copy is TOM'S, corrected only to match the three
actual tools (2 brass + 1 stainless). Does NOT touch eBay -- run ebay_photos.py then
ebay_sell.py --dry-run after.

  python3 examples/build_tweezer_estate_lot.py
  python3 ebay_photos.py --item tool-tweezer-estate-lot-01
  python3 ebay_sell.py  --list tool-tweezer-estate-lot-01 --dry-run
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import studio
from PIL import Image

VMSHARE = os.environ.get("VMSHARE", os.path.expanduser("~/vmshare"))

# Order: full-tool shot of each of the three (lot hero row) -> maker marks -> tips -> angles.
ORDER = [
    "20260706_105401.jpg",  # 1 brass #1 full tool
    "20260706_110254.jpg",  # 2 brass #2 full tool
    "20260706_111001.jpg",  # 3 stainless full tool
    "20260706_105346.jpg",  # 4 brass #1 mark: PEER-VIGOR SWITZERLAND AM
    "20260706_110144.jpg",  # 5 brass #2 mark: BRASS
    "20260706_110232.jpg",  # 6 brass #2 mark: PEER-VIGOR SWITZERLAND AM
    "20260706_110946.jpg",  # 7 stainless mark: STAINLESS NON-MAGNETIC 3
    "20260706_110913.jpg",  # 8 stainless tips
    "20260706_105337.jpg",  # 9 brass #1 angle
    "20260706_110223.jpg",  # 10 brass #2 detail (hi-res)
    "20260706_110243.jpg",  # 11 brass #2 detail (hi-res)
    "20260706_110859.jpg",  # 12 stainless angle
    "20260706_110908.jpg",  # 13 stainless angle
    "20260706_110924.jpg",  # 14 stainless angle
    "20260706_110952.jpg",  # 15 stainless angle
]


def load_1600(path):
    """Return JPEG bytes, downsized so the long edge <= 1600 (raw file untouched)."""
    im = Image.open(path)
    w, h = im.size
    if max(w, h) > 1600:
        scale = 1600.0 / max(w, h)
        im = im.convert("RGB").resize((round(w * scale), round(h * scale)))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()


paths = [os.path.join(VMSHARE, n) for n in ORDER]
for p in paths:
    assert os.path.exists(p), f"missing photo: {p}"
print(f"selected {len(paths)} photos in order:")
for i, p in enumerate(paths, 1):
    print(f"  {i:2d}. {os.path.basename(p)}")

files = {"photos": [(os.path.basename(p), load_1600(p)) for p in paths]}

SKU = "TOOL-TWEEZER-ESTATE-LOT-01"
TITLE = "Watchmaker Estate Tweezers x3 Peer-Vigor Brass + Non-Magnetic Stainless No.3"
# Tom's copy, corrected to the real contents (2 Peer-Vigor brass + 1 stainless).
DESC = (
    "This is a 3-piece lot of professional watchmaker's tweezers, ideal for movement work, "
    "parts handling, and general bench use. Includes:\n\n"
    "Peer-Vigor Swiss Brass Tweezers (two) -- marked PEER-VIGOR SWITZERLAND; fine straight "
    "tips, good alignment. Brass is naturally non-magnetic. Light cosmetic patina from bench "
    "use.\n\n"
    "Non-Magnetic Stainless No.3 Tweezer -- marked STAINLESS NON-MAGNETIC; fine tips, tested "
    "non-magnetic; ideal for hairsprings, balance work, and handling small steel components "
    "without magnetizing them.\n\n"
    "All three came from a retired watchmaker's estate and were used regularly, so they carry "
    "the honest patina you expect from estate tools. No bends, cracks, rust, or tip damage; "
    "all tips align and grip cleanly. Perfect for watchmakers, hobbyists, restorers, or anyone "
    "building out a reliable set of bench tweezers."
)
COND_DESC = (
    "All three tweezers come from a retired watchmaker's estate. They show normal bench wear "
    "from use but no bends, cracks, or tip damage. All tips align properly and grip cleanly. "
    "The stainless No.3 tested non-magnetic with small steel screws; the brass pair is "
    "non-magnetic by material."
)
CAL = ("3-piece watchmaker tweezer lot: 2x Peer-Vigor Switzerland brass (mark AM, non-magnetic) "
       "+ 1x stainless No.3 non-magnetic; estate tools, used, tips aligned.")
COND = "Preowned estate lot; bench wear, no bends/cracks/tip damage; tips align; non-magnetic"

create = {"brand": "Peer-Vigor", "what": "watchmaker tweezer estate lot (3 pieces)",
          "caliber": CAL, "condition": COND, "title": TITLE,
          "description": DESC, "price": "39.99", "sku": SKU}
slug = studio.create_item(create, files)
print(f"\ncreated item slug = {slug}")

# eBay draft meta. Category 117039 (Taxonomy). No fulfillment_policy_id override -> uses the
# ebay_app.json default (71421334019 = Ground Advantage). Best Offer stays on (engine default).
# No store_category (store has no Tools category yet). Condition USED_EXCELLENT tentative;
# validator confirms at --list.
meta = {
    "sku": SKU,
    "title": TITLE,
    "description": DESC,
    "price": 39.99,
    "quantity": 1,
    "condition": "USED_EXCELLENT",           # TENTATIVE -- confirm vs getItemConditionPolicies(117039)
    "condition_description": COND_DESC,
    "category_id": 117039,                    # Parts, Tools & Guides > Tools & Repair Kits
    "aspects": {
        "Brand": ["Peer-Vigor"],
        "Type of Tool": ["Tweezers"],
        "Country of Origin": ["Switzerland"],
        "Unit Quantity": ["3"],
        "Unit Type": ["Unit"],
    },
}
meta_path = os.path.join(LIB, "photos", slug, "ebay_meta.json")
json.dump(meta, open(meta_path, "w"), indent=2)
print(f"wrote ebay_meta.json in photos/{slug}/  (category {meta['category_id']}, "
      f"{meta['condition']}, ${meta['price']}, ship=Ground Advantage default, Best Offer on)")
print(f"\nNEXT (needs credentials): python3 ebay_photos.py --item {slug}")
print(f"THEN: python3 ebay_sell.py --list {slug} --dry-run")
