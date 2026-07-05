#!/usr/bin/env python3
"""Intake for a SERVICED, RUNNING Unitas/ETA 6498 pocket-watch movement, signed
ARNEX TIME Co INC, 17 jewels, gilt (gold-tone) finish, ~1970s. Two running videos.
Distinct from the parts-only Arnex 6498 in build_movement.py. Category 57720 (Movements);
57720-valid aspects only (no Model/Jewels/Features -- eBay silently drops those). Downsizes
>1600px on read (raw untouched). Creates the library item + ebay_meta.json. No eBay contact.

  python3 examples/build_unitas6498_serviced.py
  python3 ebay_photos.py --item mvt-unitas6498-arnex-serviced-01
  python3 ebay_sell.py  --list mvt-unitas6498-arnex-serviced-01 --dry-run
"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import studio
from PIL import Image

VMSHARE = os.environ.get("VMSHARE", "/home/tom/vmshare")

# JPEG stills; the two running videos attach separately via ebay_video.py and lead.
ORDER = [
    "20260705_150734.jpg",  # 1 hero: gilt mechanism, going train + balance (hi-res, downsized)
    "20260705_150904.jpg",  # 2 ARNEX TIME Co INC signature close (hi-res, downsized)
    "20260705_150931.jpg",  # 3 whole movement in hand, clean/serviced
    "20260705_150237.jpg",  # 4 motion-works / keyless side
    "20260705_150254.jpg",  # 5 angle
    "20260705_150313.jpg",  # 6 angle
    "20260705_150641.jpg",  # 7 angle
    "20260705_150714.jpg",  # 8 angle
    "20260705_150858.jpg",  # 9 angle
]


def load_1600(path):
    im = Image.open(path); w, h = im.size
    if max(w, h) > 1600:
        s = 1600.0 / max(w, h); im = im.convert("RGB").resize((round(w*s), round(h*s)))
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=90); return buf.getvalue()


paths = [os.path.join(VMSHARE, n) for n in ORDER]
for p in paths:
    assert os.path.exists(p), f"missing photo: {p}"
print(f"selected {len(paths)} photos (2 running videos attach separately, lead):")
for i, p in enumerate(paths, 1):
    print(f"  {i:2d}. {os.path.basename(p)}")
files = {"photos": [(os.path.basename(p), load_1600(p)) for p in paths]}

SKU = "MVT-UNITAS6498-ARNEX-SERVICED-01"
TITLE = "Unitas ETA 6498 Serviced Running Pocket Watch Movement 17 Jewels Swiss Arnex Gilt"
DESC = (
    "A genuine Swiss Unitas/ETA 6498 -- the 16.5-ligne, 17-jewel manual-wind pocket-watch "
    "caliber -- signed ARNEX TIME Co INC, in a gilt (gold-tone) finish.\n\n"
    "Recently serviced and running strong (see both videos), with a healthy balance. The 6498 "
    "is the robust 16.5-ligne hand-wind that watchmaking schools teach on -- an excellent "
    "running movement for a restoration, a build, or a running donor.\n\n"
    "Shown honestly from both sides and in motion. Please review all photos and both videos."
)
COND_DESC = (
    "Serviced and running (see both videos); healthy balance. Genuine Swiss Unitas/ETA 6498, "
    "16.5 ligne, 17 jewels, signed ARNEX TIME Co INC, gilt finish. Please review all photos "
    "and videos."
)
CAL = ("Unitas/ETA 6498, 16.5 ligne, 17 jewels, lever escapement, manual wind; signed ARNEX "
       "TIME Co INC; gilt finish; Swiss. Serviced and running.")
COND = "Vintage; serviced and running; 17 jewels; signed ARNEX; gilt finish"

create = {"brand": "Unitas", "what": "loose pocket watch movement (serviced, running)",
          "caliber": CAL, "condition": COND, "title": TITLE,
          "description": DESC, "price": "149.99", "sku": SKU}
slug = studio.create_item(create, files)
print(f"\ncreated item slug = {slug}")

meta = {
    "sku": SKU, "title": TITLE, "description": DESC, "price": 149.99, "quantity": 1,
    "condition": "USED_EXCELLENT",        # serviced+running -> the top used grade 57720 allows
    "condition_description": COND_DESC,
    "category_id": 57720, "store_category": "Movements",
    "aspects": {
        "Brand": ["Unitas"],
        "Type": ["Movement"],
        "Movement Type": ["Mechanical (Manual)"],
        "MPN": ["6498"],
        "Country of Origin": ["Switzerland"],
        "Material": ["Brass"],
        "Unit Type": ["Unit"],
        "Unit Quantity": ["1"],
    },
}
meta_path = os.path.join(LIB, "photos", slug, "ebay_meta.json")
json.dump(meta, open(meta_path, "w"), indent=2)
print(f"wrote ebay_meta.json ({meta['category_id']}, {meta['condition']}, ${meta['price']})")
print(f"\nNEXT: python3 ebay_photos.py --item {slug}")
