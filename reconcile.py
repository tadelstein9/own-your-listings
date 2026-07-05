#!/usr/bin/env python3
"""reconcile.py — owned auto-delist. Detect sales per channel, delist the item on the
others, keep the local catalog (library.db) as the source of truth. Local + BYOK.

  python3 reconcile.py migrate                       # add multi-channel cols to `listings`
  python3 reconcile.py register --item <slug> --channel ebay \
          --id <listingId> --ref <offerId> [--status active]
  python3 reconcile.py status                         # what's live where
  python3 reconcile.py run                            # DETECT sales; show what it WOULD delist
  python3 reconcile.py run --apply                    # ...and actually withdraw the others

FB has no seller API -> its rows are 'manual'; reconcile prints a task instead of delisting.
Only eBay detect+delist are implemented here; Etsy is stubbed (see AUTODELIST_DESIGN.md §6).
"""
import argparse, datetime, json, os, sqlite3, sys, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ebay_pull

DB = os.path.join(HERE, "library.db")
SELL_BASE = "https://api.ebay.com"
NEW_COLS = {"channel": "TEXT", "external_id": "TEXT", "external_ref": "TEXT", "sku": "TEXT"}


def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c


def now_z():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ---- schema migration (idempotent) ----------------------------------------
def migrate(con):
    have = {r["name"] for r in con.execute("PRAGMA table_info(listings)")}
    for col, typ in NEW_COLS.items():
        if col not in have:
            con.execute(f"ALTER TABLE listings ADD COLUMN {col} {typ}")
    con.commit()
    print("listings columns:", [r["name"] for r in con.execute("PRAGMA table_info(listings)")])


# ---- eBay HTTP ------------------------------------------------------------
def _req(method, token, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(SELL_BASE + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "Accept": "application/json", "Content-Language": "en-US"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read(); return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw


def ebay_detect_sales(token, since):
    """Return [(sku, qty)] for orders created since `since` (ISO Z)."""
    status, d = _req("GET", token,
        f"/sell/fulfillment/v1/order?filter=creationdate:%5B{since}..%5D&limit=200")
    if status != 200:
        print(f"  ! getOrders HTTP {status}: {str(d)[:200]}"); return []
    sold = []
    for o in d.get("orders", []):
        for li in o.get("lineItems", []):
            if li.get("sku"):
                sold.append((li["sku"], int(li.get("quantity", 1))))
    return sold


def ebay_delist(token, offer_id, apply):
    if not apply:
        print(f"    [dry-run] would withdraw eBay offer {offer_id}"); return True
    status, d = _req("POST", token, f"/sell/inventory/v1/offer/{offer_id}/withdraw")
    if status in (200, 204):
        print(f"    withdrew eBay offer {offer_id} [{status}]"); return True
    # idempotent: an already-ended offer is a success for our purposes
    if status == 400 and "cannot be withdrawn" in str(d).lower():
        print(f"    eBay offer {offer_id} already ended [{status}]"); return True
    print(f"    ! withdraw {offer_id} failed [{status}]: {str(d)[:160]}"); return False


# ---- catalog helpers ------------------------------------------------------
def register(con, slug, channel, external_id, external_ref, status):
    it = con.execute("SELECT id FROM items WHERE slug=?", (slug,)).fetchone()
    if not it: sys.exit(f"no item with slug {slug}")
    sku = con.execute("SELECT slug FROM items WHERE id=?", (it["id"],)).fetchone()["slug"]
    con.execute("INSERT INTO listings (item_id, channel, external_id, external_ref, sku,"
                " ebay_item_no, status, listed_at) VALUES (?,?,?,?,?,?,?,?)",
                (it["id"], channel, external_id, external_ref, slug.upper(),
                 external_id if channel == "ebay" else None, status, now_z()))
    con.commit()
    print(f"registered {channel} listing {external_id} for {slug} [{status}]")


def status_report(con):
    rows = con.execute(
        "SELECT i.slug, l.channel, l.external_id, l.external_ref, l.status "
        "FROM listings l JOIN items i ON i.id=l.item_id "
        "WHERE l.channel IS NOT NULL ORDER BY i.slug, l.channel").fetchall()
    if not rows: print("no channel-tagged listings yet (run register)"); return
    print(f"{'item':30} {'channel':7} {'external_id':16} {'status'}")
    for r in rows:
        print(f"{r['slug']:30} {r['channel']:7} {str(r['external_id'] or ''):16} {r['status']}")


# ---- the loop -------------------------------------------------------------
def run(con, apply):
    creds = json.load(open(os.path.join(HERE, "ebay_credentials.json")))
    token = ebay_pull.refresh_access_token(creds)
    last = con.execute("SELECT value FROM settings WHERE key='reconcile.last_run'").fetchone()
    since = last["value"] if last else (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    print(f"eBay: detecting sales since {since}  ({'APPLY' if apply else 'dry-run'})")

    sold = ebay_detect_sales(token, since)
    if not sold: print("  no sold SKUs in window.")
    for sku, qty in sold:
        print(f"  SOLD on eBay: {sku} x{qty}")
        it = con.execute("SELECT id FROM items WHERE slug=?", (sku.lower(),)).fetchone()
        if not it:
            print(f"    (no catalog item for sku {sku} -- skipping)"); continue
        con.execute("UPDATE listings SET status='sold' WHERE item_id=? AND channel='ebay'", (it["id"],))
        con.execute("UPDATE items SET state='sold' WHERE id=?", (it["id"],))
        others = con.execute("SELECT * FROM listings WHERE item_id=? AND channel!='ebay' "
                             "AND status='active'", (it["id"],)).fetchall()
        for o in others:
            if o["channel"] == "fb":
                print(f"    MANUAL: end FB listing for {sku}")
            elif o["channel"] == "etsy":
                print(f"    TODO(etsy adapter): set listing {o['external_id']} inactive")
            else:
                ok = ebay_delist(token, o["external_ref"], apply)
                if ok and apply:
                    con.execute("UPDATE listings SET status='ended', ended_at=? WHERE id=?",
                                (now_z(), o["id"]))
    if apply:
        con.execute("INSERT INTO settings(key,value) VALUES('reconcile.last_run',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (now_z(),))
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    rp = sub.add_parser("register")
    rp.add_argument("--item", required=True); rp.add_argument("--channel", required=True)
    rp.add_argument("--id", required=True); rp.add_argument("--ref", default=None)
    rp.add_argument("--status", default="active")
    sub.add_parser("status")
    rr = sub.add_parser("run"); rr.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    con = db()
    if a.cmd == "migrate": migrate(con)
    elif a.cmd == "register": migrate(con); register(con, a.item, a.channel, a.id, a.ref, a.status)
    elif a.cmd == "status": status_report(con)
    elif a.cmd == "run": migrate(con); run(con, a.apply)


if __name__ == "__main__":
    main()
