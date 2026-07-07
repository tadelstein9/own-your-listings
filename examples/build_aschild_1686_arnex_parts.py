#!/usr/bin/env python3
"""Intake for a single loose A. Schild AS 1686 wristwatch movement, NOT RUNNING -- sold for
parts / repair / hobbyist. ELOGA-signed bridge, ARNEX-signed dial (17 jewels, Incabloc,
"Unbreakable Mainspring", Swiss). Same caliber as mvt-as1686-pandan-01 (that one RAN, PANDAN
dial); this is the parts version. Category 57720 (Movements) from Taxonomy, not a comp;
FOR_PARTS_OR_NOT_WORKING is valid there (validator confirms at --list). Downsizes >1600px on
read (raw stays untouched in vmshare). Creates the library item + ebay_meta.json.
Does NOT touch eBay -- run ebay_photos.py then ebay_sell.py --dry-run after.

  python3 examples/build_aschild_1686_arnex_parts.py
  python3 ebay_photos.py --item mvt-as1686-arnex-01
  python3 ebay_sell.py  --list mvt-as1686-arnex-01 --dry-run
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import studio
from PIL import Image

VMSHARE = os.environ.get("VMSHARE", os.path.expanduser("~/vmshare"))

# Order: hero Eloga bridge (signature + balance) -> Arnex dial (the value-add) -> mechanism
#   angles -> going train -> dial angles/side. (No running video: it does not run.)
ORDER = [
    "20260706_085644.jpg",  # 1 hero: ELOGA WATCH Co SWISS 17 JEWELS bridge, balance/jewels sharp
    "20260706_090552.jpg",  # 2 dial: arnex 17 JEWELS INCABLOC UNBREAKABLE MAINSPRING T SWISS
    "20260706_085529.jpg",  # 3 mechanism, balance + crown/stem clear
    "20260706_085554.jpg",  # 4 bridge signature, second angle
    "20260706_085703.jpg",  # 5 going train / barrel edge
    "20260706_085548.jpg",  # 6 movement angle
    "20260706_090602.jpg",  # 7 dial angle, arnex signature clear
    "20260706_085728.jpg",  # 8 dial side, hands present
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

SKU = "MVT-AS1686-ARNEX-01"
TITLE = "A. Schild AS 1686 17J Incabloc Wristwatch Movement FOR PARTS Not Running Arnex"
DESC = (
    "A genuine Swiss A. Schild AS 1686 -- the 11.5-ligne, 17-jewel manual-wind caliber with "
    "Incabloc shock protection and center seconds -- with an ELOGA signed bridge and an ARNEX "
    "signed dial (marked 17 JEWELS, INCABLOC, UNBREAKABLE MAINSPRING, SWISS).\n\n"
    "Sold for parts, repair, or a hobbyist project: the movement is NOT running. The dial "
    "shows some age and wear consistent with its years; the hands are present.\n\n"
    "The AS 1686 is a compact, well-supported Swiss caliber -- a useful donor or restoration "
    "project for a watchmaker or hobbyist. Shown honestly from both sides. Please review all "
    "photos and buy as-is: not running, for parts / repair."
)
COND_DESC = (
    "Not running -- sold for parts, repair, or hobbyist project. Genuine A. Schild AS 1686, "
    "17 jewels, Incabloc, center seconds, Swiss; ELOGA signed bridge, ARNEX signed dial with "
    "some age and wear. Hands present. Please review all photos; sold as-is."
)
CAL = ("A. Schild AS 1686, 11.5 ligne, 17 jewels, Incabloc, center seconds, manual wind; "
       "ELOGA signed bridge, ARNEX signed dial; Swiss. Not running -- for parts/repair.")
COND = "Vintage; not running, sold for parts/repair; 17 jewels, Incabloc; Arnex dial with some age"

create = {"brand": "A. Schild", "what": "loose wristwatch movement (for parts/repair)",
          "caliber": CAL, "condition": COND, "title": TITLE,
          "description": DESC, "price": "24.99", "sku": SKU}
slug = studio.create_item(create, files)
print(f"\ncreated item slug = {slug}")

# eBay draft meta. Category 57720 = Movements (Taxonomy, not a comp).
# FOR_PARTS_OR_NOT_WORKING = honest (not running) and valid for 57720; the pre-flight
# validator (ebay_validate.py, at --list) confirms condition + required aspects.
meta = {
    "sku": SKU,
    "title": TITLE,
    "description": DESC,
    "price": 24.99,
    "quantity": 1,
    "condition": "FOR_PARTS_OR_NOT_WORKING",
    "condition_description": COND_DESC,
    "category_id": 57720,                # Parts, Tools & Guides > Parts > Movements
    "store_category": "Movements",       # your eBay Store category (GetStore), not "Other"
    "aspects": {
        "Brand": ["A. Schild"],
        "Type": ["Movement"],
        "Movement Type": ["Mechanical (Manual)"],
        "Model": ["AS 1686"],
        "MPN": ["AS 1686"],
        "Number of Jewels": ["17"],
        "Features": ["Incabloc", "Center Seconds"],
        "Unit Type": ["Unit"],
        "Unit Quantity": ["1"],
        "Country/Region of Manufacture": ["Switzerland"],
    },
}
meta_path = os.path.join(LIB, "photos", slug, "ebay_meta.json")
json.dump(meta, open(meta_path, "w"), indent=2)
print(f"wrote ebay_meta.json in photos/{slug}/  (category {meta['category_id']}, "
      f"{meta['condition']}, ${meta['price']})")
print(f"\nNEXT (needs credentials): python3 ebay_photos.py --item {slug}")
print(f"THEN: python3 ebay_sell.py --list {slug} --dry-run  # validator confirms condition/aspects")
