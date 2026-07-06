#!/usr/bin/env python3
"""Cross-list Bynari-Library (Etsy) items onto eBay from their GOOD edited photos + honest
copy on the external drive. Reads each item's etsy_meta (description + price) from the drive,
copies its photos in, maps to the right eBay category + aspects, writes ebay_meta.json.
Does NOT touch eBay -- run ebay_photos.py + ebay_sell.py per slug after.

  python3 examples/crosslist_from_drive.py
"""
import io, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.dirname(HERE)
sys.path.insert(0, LIB)
import studio
from PIL import Image

DRIVE = "/media/tom/11FC93012098BB98/Bynari-Library"

# Per-item eBay mapping. Title <=80. Descriptions/prices pulled from the drive's etsy_meta.
CONFIG = [
    {   # Arnex full hunter, genuine Unitas 6498, serviced/running, gold-tone
        "drive": "pwt-arx-70-002", "ebay_sku": "PWT-ARX-70-002", "category": 3937,
        "title": "Unitas 6498 Arnex Full Hunter Pocket Watch 17 Jewels Swiss Serviced Running",
        "condition": "USED_EXCELLENT",
        "aspects": {
            "Brand": ["Arnex"], "Department": ["Men"], "Type": ["Pocket Watch"],
            "Movement": ["Mechanical (Manual)"], "Style": ["Full Hunter"], "Display": ["Analog"],
            "Case Color": ["Gold"], "Case Material": ["Gold Plated"], "Dial Color": ["Gold"],
            "Number of Jewels": ["17"], "Escapement Type": ["Lever"], "Vintage": ["Yes"],
            "Year Manufactured": ["1970-1979"], "Country of Origin": ["Switzerland"]},
    },
    {   # Arnex full hunter #855, Unitas 6498, rose enamel dial, Incabloc, serviced
        "drive": "pwt-arx-70-003", "ebay_sku": "PWT-ARX-70-003", "category": 3937,
        "title": "Unitas 6498 Arnex Full Hunter Pocket Watch 17 Jewels Swiss Rose Enamel Serviced",
        "condition": "USED_EXCELLENT",
        "aspects": {
            "Brand": ["Arnex"], "Department": ["Men"], "Type": ["Pocket Watch"],
            "Movement": ["Mechanical (Manual)"], "Style": ["Full Hunter"], "Display": ["Analog"],
            "Case Color": ["Gold"], "Case Material": ["Gold Plated"], "Dial Color": ["White"],
            "Number of Jewels": ["17"], "Escapement Type": ["Lever"], "Vintage": ["Yes"],
            "Year Manufactured": ["1970-1979"], "Country of Origin": ["Switzerland"]},
    },
    {   # Unitas 6445/6341 loose movement, runs -> Movements category
        "drive": "mvt-unitas-6445-01", "ebay_sku": "MVT-UNITAS-6445-01", "category": 57720,
        "title": "Unitas 6445 6341 Swiss Pocket Watch Movement 17 Jewels Manual Wind Runs",
        "condition": "USED_EXCELLENT",
        "aspects": {
            "Brand": ["Unitas"], "Type": ["Movement"], "Movement Type": ["Mechanical (Manual)"],
            "MPN": ["6445"], "Country of Origin": ["Switzerland"], "Material": ["Brass"],
            "Unit Type": ["Unit"], "Unit Quantity": ["1"]},
    },
]


def load_1600(path):
    im = Image.open(path); w, h = im.size
    if max(w, h) > 1600:
        s = 1600.0 / max(w, h); im = im.convert("RGB").resize((round(w*s), round(h*s)))
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=90); return buf.getvalue()


for c in CONFIG:
    src = os.path.join(DRIVE, "photos", c["drive"])
    em = json.load(open(os.path.join(src, "etsy_meta.json")))
    jpgs = sorted(f for f in os.listdir(src) if f.lower().endswith(".jpg") and f[0].isdigit())
    files = {"photos": [(f, load_1600(os.path.join(src, f))) for f in jpgs]}
    title = c["title"]
    assert len(title) <= 80, f"{c['ebay_sku']} title {len(title)} > 80"
    create = {"brand": c["aspects"].get("Brand", [""])[0], "what": "cross-listed from Etsy",
              "title": title, "condition": c["condition"], "description": em["description"],
              "price": str(em["price"]), "sku": c["ebay_sku"]}
    slug = studio.create_item(create, files)
    meta = {"sku": c["ebay_sku"], "title": title, "description": em["description"],
            "price": float(em["price"]), "quantity": 1, "condition": c["condition"],
            "condition_description": em["description"].split("\n\n")[0][:800],
            "category_id": c["category"],
            "store_category": "Movements" if c["category"] == 57720 else "Pocket Watches",
            "aspects": c["aspects"]}
    json.dump(meta, open(os.path.join(LIB, "photos", slug, "ebay_meta.json"), "w"), indent=2)
    print(f"{slug}: {len(jpgs)} photos, cat {c['category']}, ${em['price']}, title({len(title)})")
