#!/usr/bin/env python3
"""Cross-list intake: Vintage Bulova gold-tone OPEN-FACE pocket watch, ~1950s, 17-jewel
Swiss manual wind (Unitas 497 family), sub-seconds. Complete watch -> eBay category 3937
(Pocket Watches), NOT 57720. Photos recovered from Trash (July-1 shoot). Downsizes >1600px.
Two fields left for Tom (T&S -- don't fabricate): running? and case material (gold-filled
vs plated -- caseback shows no hallmark). Creates the library item + ebay_meta.json.

  python3 examples/build_bulova_pw.py
  python3 ebay_sell.py --list mvt-bulova-pw-goldtone-01 --dry-run
"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import studio
from PIL import Image

VMSHARE = os.environ.get("VMSHARE", "/home/tom/vmshare")
ORDER = [
    "20260701_093227.jpg",  # 1 hero: dial front, close (Bulova, sub-seconds)
    "20260701_093414.jpg",  # 2 caseback (plain polished gold-tone)
    "20260701_093311.jpg",  # 3
    "20260701_093339.jpg",  # 4
    "20260701_093545.jpg",  # 5
    "20260701_094724.jpg",  # 6
    "20260701_094809.jpg",  # 7
    "20260701_094829.jpg",  # 8
]


def load_1600(path):
    im = Image.open(path); w, h = im.size
    if max(w, h) > 1600:
        s = 1600.0 / max(w, h); im = im.convert("RGB").resize((round(w*s), round(h*s)))
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=90); return buf.getvalue()


paths = [os.path.join(VMSHARE, n) for n in ORDER]
for p in paths:
    assert os.path.exists(p), f"missing photo: {p}"
files = {"photos": [(os.path.basename(p), load_1600(p)) for p in paths]}
print(f"selected {len(paths)} photos")

SKU = "MVT-BULOVA-PW-GOLDTONE-01"
TITLE = "Vintage Bulova Pocket Watch Gold Tone Open Face 17 Jewels Swiss Manual Wind 1950s"
DESC = (
    "A vintage Bulova open-face pocket watch in a gold-tone case, ~1950s. Signed Bulova dial "
    "with applied gold markers and a sub-seconds register at 6; 17-jewel Swiss manual-wind "
    "movement (Unitas 497 family).\n\n"
    "Shown honestly from both sides on the stand; some light surface wear to the case "
    "consistent with age. Please review all photos.\n\n"
    "[CONFIRM WITH TOM before publish: running status; case material gold-filled vs plated.]"
)
COND_DESC = ("Vintage Bulova gold-tone open-face pocket watch, ~1950s, 17-jewel Swiss manual "
             "wind. Light surface wear consistent with age; please review all photos. "
             "[running status TBD by seller]")
CAL = "Bulova, 17 jewels, Swiss manual wind (Unitas 497 family), sub-seconds; open face; ~1950s"
COND = "Vintage; open-face gold-tone pocket watch; 17 jewels Swiss; light age wear"

create = {"brand": "Bulova", "what": "open-face pocket watch (complete)",
          "caliber": CAL, "condition": COND, "title": TITLE,
          "description": DESC, "price": "199.00", "sku": SKU}
slug = studio.create_item(create, files)
print(f"created item slug = {slug}")

meta = {
    "sku": SKU, "title": TITLE, "description": DESC, "price": 199.00, "quantity": 1,
    "condition": "USED_GOOD",             # TENTATIVE -- depends on running status; validator confirms allowed set for 3937
    "condition_description": COND_DESC,
    "category_id": 3937, "store_category": None,
    "aspects": {
        "Brand": ["Bulova"],
        "Department": ["Men"],
        "Type": ["Pocket Watch"],
        "Movement": ["Mechanical (Manual)"],
        "Style": ["Open Face"],
        "Display": ["Analog"],
        "Case Color": ["Gold"],
        "Dial Color": ["Silver"],
        "Number of Jewels": ["17"],
        "Escapement Type": ["Lever"],
        "Vintage": ["Yes"],
        "Year Manufactured": ["1950-1959"],
        "Country of Origin": ["Switzerland"],
        # Case Material left blank -- confirm gold-filled vs plated with Tom
    },
}
meta_path = os.path.join(LIB, "photos", slug, "ebay_meta.json")
json.dump(meta, open(meta_path, "w"), indent=2)
print(f"wrote ebay_meta.json ({meta['category_id']}, {meta['condition']} [tentative], ${meta['price']})")
