#!/usr/bin/env python3
"""Intake for a single loose A. Schild AS 1686 wristwatch movement, RUNNING, under a
PANDAN-signed dial (17 jewels, Incabloc, center-seconds, Swiss). Priced from Tom's SOLD
comps (AS 1686 running $24.02; AS 1686 movement+dial $35.00 -> ours runs AND has a dial).
Category 57720 (Movements) pulled from Taxonomy, not a comp. Downsizes >1600px photos to
1600 on read (raw stays untouched in vmshare). Creates the library item + ebay_meta.json.
Does NOT touch eBay -- run ebay_photos.py then ebay_sell.py after (needs credentials).

  python3 examples/build_aschild_1686.py
  python3 ebay_photos.py --item mvt-as1686-pandan-01
  python3 ebay_sell.py  --list mvt-as1686-pandan-01 --dry-run
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import studio
from PIL import Image

VMSHARE = os.environ.get("VMSHARE", "/home/tom/vmshare")

# Order (JPEG stills; the running video attaches separately via ebay_video.py, and leads):
#   hero mechanism -> Pandan dial -> mechanism angles -> keyless/side.
ORDER = [
    "20260705_120654.jpg",  # 1 hero: mechanism, balance + jewels sharp (hi-res, downsized)
    "20260705_120718.jpg",  # 2 dial side: PANDAN 17 JEWELS INCABLOC SWISS
    "20260705_120659.jpg",  # 3 mechanism, second angle (hi-res, downsized)
    "20260705_115849.jpg",  # 4 movement, balance + crown/stem clear
    "20260705_115917.jpg",  # 5 movement angle
    "20260705_115943.jpg",  # 6 movement angle
    "20260705_120050.jpg",  # 7 movement angle
    "20260705_120102.jpg",  # 8 movement angle
    "20260705_120111.jpg",  # 9 movement angle
    "20260705_120631.jpg",  # 10 movement / detail
    "20260705_120726.jpg",  # 11 dial / side
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
print(f"selected {len(paths)} photos in order (video attaches separately, leads):")
for i, p in enumerate(paths, 1):
    print(f"  {i:2d}. {os.path.basename(p)}")

files = {"photos": [(os.path.basename(p), load_1600(p)) for p in paths]}

SKU = "MVT-AS1686-PANDAN-01"
TITLE = "A. Schild AS 1686 Wristwatch Movement RUNNING 17 Jewels Incabloc Pandan Swiss"
DESC = (
    "A genuine Swiss A. Schild AS 1686 -- the 11.5-ligne, 17-jewel manual-wind caliber "
    "with Incabloc shock protection and center seconds -- under a PANDAN signed dial.\n\n"
    "Running at the time of listing (see the video), with a lively balance. A sound running "
    "movement for a restoration, a running donor, or a dial-and-movement project.\n\n"
    "Shown honestly from both sides and in motion; some age to the dial consistent with its "
    "years. Please review all photos and the video."
)
COND_DESC = (
    "Running at the time of listing (see the video); lively balance. Genuine A. Schild AS "
    "1686, 17 jewels, Incabloc, Swiss, with a PANDAN signed dial. Some age to the dial "
    "consistent with its years. Please review all photos and the video."
)
CAL = ("A. Schild AS 1686, 11.5 ligne, 17 jewels, Incabloc, center seconds, manual wind; "
       "PANDAN signed dial; Swiss. Running.")
COND = "Vintage; running at time of listing; 17 jewels, Incabloc; PANDAN dial with some age"

create = {"brand": "A. Schild", "what": "loose wristwatch movement (running)",
          "caliber": CAL, "condition": COND, "title": TITLE,
          "description": DESC, "price": "34.99", "sku": SKU}
slug = studio.create_item(create, files)
print(f"\ncreated item slug = {slug}")

# eBay draft meta. Category 57720 = Movements (Taxonomy, not a comp).
# CONDITION: tentative below -- category 57720 restricts conditions (it forbids USED_GOOD;
# FOR_PARTS is valid). getItemConditionPolicies (ebay_metadata.py, run at --list) returns the
# EXACT allowed conditionIds for 57720; the pre-flight validator will confirm or reject this
# value. A running movement is NOT for-parts, so we need the category's graded-used option --
# resolve against the live policy before publishing.
meta = {
    "sku": SKU,
    "title": TITLE,
    "description": DESC,
    "price": 34.99,
    "quantity": 1,
    "condition": "USED_VERY_GOOD",       # TENTATIVE -- confirm vs getItemConditionPolicies(57720)
    "condition_description": COND_DESC,
    "category_id": 57720,                # Parts, Tools & Guides > Parts > Movements
    "store_category": "Movements",
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
      f"{meta['condition']} [tentative], ${meta['price']})")
print(f"\nNEXT (needs credentials): python3 ebay_photos.py --item {slug}")
print(f"THEN: python3 ebay_sell.py --list {slug} --dry-run  # validator confirms condition/aspects")
