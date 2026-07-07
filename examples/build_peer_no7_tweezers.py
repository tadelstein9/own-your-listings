#!/usr/bin/env python3
"""Intake for a single preowned PEER No. 7 Swiss watchmaker's tweezer -- Style #7, curved
round points, smooth NON-magnetic tips, 4 1/2" overall; Peer Oxel, made in Switzerland;
stamped PEER STAINLESS / MADE IN SWITZERLAND / 46-207B. A bench TOOL, not a movement:
category 117039 (Watches, Parts & Accessories > Parts, Tools & Guides > Tools & Repair Kits),
pulled from the Taxonomy API. Uses the "eBay Standard Envelope" shipping policy (small, flat,
<3 oz, <$20) via a per-item override in ebay_meta.json. Downsizes >1600px on read.
Does NOT touch eBay -- run ebay_photos.py then ebay_sell.py --dry-run after.

  python3 examples/build_peer_no7_tweezers.py
  python3 ebay_photos.py --item tool-peer-no7-tweezers-01
  python3 ebay_sell.py  --list tool-peer-no7-tweezers-01 --dry-run
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import studio
from PIL import Image

VMSHARE = os.environ.get("VMSHARE", os.path.expanduser("~/vmshare"))

# Order: full side profile (hero) -> PEER STAINLESS stamp -> tips/curve macro -> other
#   full angle -> arm marks -> 46-207B part-no.
ORDER = [
    "20260706_094153.jpg",  # 1 hero: full tool, MADE IN SWITZERLAND on arm
    "20260706_094306.jpg",  # 2 PEER STAINLESS stamp, curved tips clear
    "20260706_094248.jpg",  # 3 tips / curve macro, PEER STAINLESS
    "20260706_094216.jpg",  # 4 full tool, opposite side
    "20260706_094207.jpg",  # 5 full tool, PEER STAINLESS / SWISS on arm
    "20260706_094327.jpg",  # 6 handle end: 46-207B part number
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

SKU = "TOOL-PEER-NO7-TWEEZERS-01"
TITLE = "Peer No. 7 Swiss Watchmaker Tweezers Non-Magnetic Curved Smooth Tips Stainless"
DESC = (
    "Peer No. 7 Swiss watchmaker's tweezers -- Style #7, with curved round points and smooth, "
    "non-magnetic tips. Overall length 4 1/2\". Peer Oxel, made in Switzerland. Sold "
    "individually (one tweezer).\n\n"
    "The Style #7 curved shank lets you rest your hand on the bench as you work, for steady "
    "control during assembly -- a practical choice for handling small watch, jewelry, and fine "
    "components, including hairspring work. Beveled edges, plain-finish points.\n\n"
    "Preowned, in good working order: light surface scratches and minor spotting consistent "
    "with bench use; tips aligned. Please review all photos."
)
COND_DESC = (
    "Preowned, good working order. Non-magnetic Swiss stainless (Peer Oxel), Style #7 curved "
    "tips. Light surface scratches and minor spotting from bench use; tips aligned and smooth. "
    "Please review all photos."
)
CAL = ("Peer No. 7 (Style #7) watchmaker's tweezers; curved round points, smooth non-magnetic "
       "tips; 4 1/2\" overall; Peer Oxel, Swiss; stamped PEER STAINLESS / 46-207B.")
COND = "Preowned; good working order; light scratches/spotting from bench use; tips aligned"

create = {"brand": "Peer", "what": "watchmaker's tweezers (Style #7, curved)",
          "caliber": CAL, "condition": COND, "title": TITLE,
          "description": DESC, "price": "19.00", "sku": SKU}
slug = studio.create_item(create, files)
print(f"\ncreated item slug = {slug}")

# eBay draft meta. Category 117039 (Taxonomy). Only REQUIRED aspect is Brand; the rest are
# recommended (Type of Tool, Country of Origin, Model, MPN, Unit Quantity/Type) -- filled.
# CONDITION: USED_EXCELLENT is tentative; the pre-flight validator (getItemConditionPolicies
# at --list) confirms or rejects it for 117039. No store_category: your store has no "Tools"
# custom category yet, so we omit it rather than land in a mismatched one.
# fulfillment_policy_id overrides ebay_app.json -> eBay Standard Envelope (small flat item).
meta = {
    "sku": SKU,
    "title": TITLE,
    "description": DESC,
    "price": 19.00,
    "quantity": 1,
    "condition": "USED_EXCELLENT",           # TENTATIVE -- confirm vs getItemConditionPolicies(117039)
    "condition_description": COND_DESC,
    "category_id": 117039,                    # Parts, Tools & Guides > Tools & Repair Kits
    "fulfillment_policy_id": "275341890019",  # eBay Standard Envelope
    "aspects": {
        "Brand": ["Peer"],
        "Type of Tool": ["Tweezers"],
        "Model": ["No. 7"],
        "MPN": ["46-207B"],
        "Country of Origin": ["Switzerland"],
        "Unit Type": ["Unit"],
        "Unit Quantity": ["1"],
    },
}
meta_path = os.path.join(LIB, "photos", slug, "ebay_meta.json")
json.dump(meta, open(meta_path, "w"), indent=2)
print(f"wrote ebay_meta.json in photos/{slug}/  (category {meta['category_id']}, "
      f"{meta['condition']}, ${meta['price']}, ship=eBay Standard Envelope)")
print(f"\nNEXT (needs credentials): python3 ebay_photos.py --item {slug}")
print(f"THEN: python3 ebay_sell.py --list {slug} --dry-run  # validator confirms condition/aspects + eSE")
