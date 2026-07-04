#!/usr/bin/env python3
"""One-shot intake for a single loose Swiss Unitas/ETA 6498 pocket-watch movement,
signed ARNEX TIME Co INC, 17 jewels, unadjusted. NOT running -- sold strictly for
parts / repair / hobbyist: complete, good freely-moving balance, likely needs a new
mainspring. Priced from Tom's SOLD comp (UT 6498 GOOD BALANCE (M4), $124.95). A comp gives
you the PRICE, never the category: that comp sat in 3937 Pocket Watches, but a loose movement
belongs in 57720 (Parts > Movements) -- filing it in the comp's category silently strips the
movement's item specifics. Creates the library item + ebay_meta.json.
Does NOT touch eBay -- run ebay_photos.py then ebay_sell.py after.

  python3 examples/build_movement.py
  python3 ebay_photos.py --item mvt-unitas-6498-01
  python3 ebay_sell.py  --list mvt-unitas-6498-01 --dry-run
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)          # repo root holds studio.py and (locally) your library.db
sys.path.insert(0, LIB)
import studio

VMSHARE = os.environ.get("VMSHARE", os.path.join(LIB, "photos-inbox"))

# Order: hero bridge (signature) -> signature in hand -> going train -> mainspring
# barrel edge -> good-balance macro -> dial/keyless sides -> Arnex catalog reference.
ORDER = [
    "20260703_104430.jpg",  # 1 hero: bridge, ARNEX TIME Co INC / 17 JEWELS SWISS legible
    "20260703_104612.jpg",  # 2 bridge in hand, signature clear
    "20260703_104002.jpg",  # 3 bridge, full going train + balance
    "20260703_104605.jpg",  # 4 edge macro: mainspring barrel (may need mainspring)
    "20260703_104507.jpg",  # 5 balance / regulator macro (good balance)
    "20260703_103937.jpg",  # 6 dial side / keyless works
    "20260703_103950.jpg",  # 7 dial side, second angle
    "20260703_103848.jpg",  # 8 Arnex movement catalog page (UT6497-8 #138, provenance)
]
paths = [os.path.join(VMSHARE, n) for n in ORDER]
for p in paths:
    assert os.path.exists(p), f"missing photo: {p}"
print(f"selected {len(paths)} photos in order:")
for i, p in enumerate(paths, 1):
    print(f"  {i:2d}. {os.path.basename(p)}  {os.path.getsize(p)//1024}K")
assert len(paths) == 8

files = {"photos": [(os.path.basename(p), open(p, "rb").read()) for p in paths]}

SKU = "MVT-UNITAS-6498-01"
TITLE = "UNITAS ETA UT 6498 SWISS 17J POCKET WATCH MOVEMENT, GOOD BALANCE, ARNEX"
DESC = (
    "A genuine Swiss Unitas/ETA 6498 -- the 16.5-ligne, 17-jewel manual-wind pocket-watch "
    "caliber -- signed ARNEX TIME Co INC.\n\n"
    "Sold for parts, repair, or a hobbyist project: the movement is NOT running. It is "
    "complete, with a good, freely-moving balance, and it likely needs a new mainspring to "
    "run again. The plates are signed SEVENTEEN 17 JEWELS, UNADJUSTED, SWISS; lever "
    "escapement and keyless works are present.\n\n"
    "The 6498 is the robust 16.5-ligne hand-wind that watchmaking schools teach on -- an "
    "ideal donor or restoration project for a watchmaker or hobbyist. Shown honestly from "
    "both sides, plus the period Arnex movement catalog reference (it is the 16.5-ligne "
    "UT6497-8 listing).\n\n"
    "Please review all photos and buy as-is: not running, for parts / repair. Good balance; "
    "may need a mainspring."
)
COND_DESC = ("Not running -- sold for parts, repair, or hobbyist project. Complete with a "
             "good, freely-moving balance; likely needs a new mainspring. Signed ARNEX TIME "
             "Co INC; 17 jewels, Swiss, unadjusted. Please review all photos; sold as-is.")
CAL = ("Swiss Unitas/ETA 6498, 16.5 ligne, 17 jewels, unadjusted, lever escapement, "
       "manual wind; signed ARNEX TIME Co INC. Not running, good balance, may need mainspring")
COND = "Vintage; not running, sold for parts/repair; complete, good balance, may need mainspring"

# Library item (studio derives slug from the SKU -> mvt-unitas-6498-01)
create = {"brand": "Unitas", "what": "loose pocket watch movement (for parts/repair)",
          "caliber": CAL, "condition": COND, "title": TITLE,
          "description": DESC, "price": "124.95", "sku": SKU}
slug = studio.create_item(create, files)
print(f"\ncreated item slug = {slug}")

# eBay draft meta consumed by ebay_sell.py.
# CATEGORY: a loose movement is NOT a pocket watch. It lives in 57720 --
#   Watches, Parts & Accessories > Parts, Tools & Guides > Parts > Movements.
# Item specifics (aspects) are scoped PER category. The aspects below are the ones
# category 57720 actually defines -- verified against the live listing. Filing this in
# the comp's category (3937 Pocket Watches) SILENTLY drops every specific 57720 doesn't
# share: eBay errors only on a category's REQUIRED fields, then publishes the rest wrong
# without complaint. Best practice: derive category + aspects from the eBay Taxonomy API
# (getCategorySuggestions + getItemAspectsForCategory), never from a comp.
meta = {
    "sku": SKU,
    "title": TITLE,
    "description": DESC,
    "price": 124.95,
    "quantity": 1,
    # FOR_PARTS_OR_NOT_WORKING = honest (not running) and valid for this category.
    "condition": "FOR_PARTS_OR_NOT_WORKING",
    "condition_description": COND_DESC,
    "category_id": 57720,                # Parts, Tools & Guides > Parts > Movements
    "aspects": {
        "Brand": ["Unitas"],
        "Compatible Brand": ["ETA"],
        "Type": ["Movement"],
        "Movement Type": ["Mechanical (Manual)"],
        "Unit Type": ["Unit"],
        "Compatible Model": ["ETA 6498"],
        "Material": ["Nickel"],
        "MPN": ["UT6498"],
        "Unit Quantity": ["1"],
        "Country of Origin": ["Switzerland"],
    },
}
meta_path = os.path.join(LIB, "photos", slug, "ebay_meta.json")
json.dump(meta, open(meta_path, "w"), indent=2)
print(f"wrote ebay_meta.json in photos/{slug}/  (category {meta['category_id']}, "
      f"{meta['condition']}, ${meta['price']})")
print(f"\nNEXT: python3 ebay_photos.py --item {slug}")
print(f"THEN: python3 ebay_sell.py  --list {slug} --dry-run")
print(slug)
