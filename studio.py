#!/usr/bin/env python3
"""studio.py — a local screen for your own inventory + listing workflow.

Runs on your machine, talks to nobody but you. It is a thin shell over the
scripts you already proved (preview.py, etsy_push.py, ebay_sell.py): it does
NOT contain listing logic, so it cannot break a listing — it only stages data
and presses the buttons you would otherwise type.

  python3 studio.py            # then open http://127.0.0.1:8765

What it does:
  - New item  : drop photos + answer a few prompts -> writes the items row and
                copies the photos into photos/<slug>/, the same shape as every
                existing item. From that moment the item is in inventory.
  - Edit      : fill the channel fields (Etsy or eBay) -> writes the sidecar
                (etsy_meta.json / ebay_meta.json) the push scripts read.
  - Preview   : runs preview.py and shows the page.
  - Dry run   : runs the push script with --dry-run (sends nothing).
  - Create draft: runs the push script for real (still a DRAFT; you publish).

Stdlib only, plus Pillow (already installed) to read image sizes. Set
BYNARI_LIB to point at a different library dir (used for safe testing).
"""
import cgi  # only for parse_header; multipart parsed by hand below
import datetime
import hashlib
import html
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image

LIB = os.environ.get("BYNARI_LIB", os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(LIB, "library.db")
PHOTOS = os.path.join(LIB, "photos")
PORT = int(os.environ.get("BYNARI_PORT", "8765"))
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


# ---------------------------------------------------------------- data
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s or "item"


def unique_slug(base):
    con = db()
    taken = {r["slug"] for r in con.execute("SELECT slug FROM items")}
    con.close()
    slug, n = base, 2
    while slug in taken or os.path.exists(os.path.join(PHOTOS, slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def load_sidecar(slug, name):
    p = os.path.join(PHOTOS, slug, name)
    return json.load(open(p)) if os.path.exists(p) else {}


def write_sidecar(slug, name, data):
    folder = os.path.join(PHOTOS, slug)
    os.makedirs(folder, exist_ok=True)
    json.dump(data, open(os.path.join(folder, name), "w"), indent=2)


# ---------------------------------------------------------------- multipart
def parse_multipart(body, boundary):
    """Minimal multipart/form-data parser. Returns (fields, files) where
    fields is name->str and files is name->list of (filename, bytes)."""
    fields, files = {}, {}
    sep = b"--" + boundary.encode()
    for part in body.split(sep):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        head, _, value = part.partition(b"\r\n\r\n")
        head = head.decode("utf-8", "replace")
        disp = ""
        for line in head.split("\r\n"):
            if line.lower().startswith("content-disposition"):
                disp = line
        _, params = cgi.parse_header(disp)
        name = params.get("name")
        if not name:
            continue
        if "filename" in params:
            fn = params["filename"]
            if fn:  # skip empty file inputs
                files.setdefault(name, []).append((fn, value))
        else:
            fields[name] = value.decode("utf-8", "replace")
    return fields, files


# ---------------------------------------------------------------- html
CSS = """
*{box-sizing:border-box} body{font-family:system-ui,Arial,sans-serif;max-width:920px;
margin:24px auto;padding:0 18px;color:#1f1f1f}
a{color:#0a5bd3;text-decoration:none} a:hover{text-decoration:underline}
h1{font-size:22px} h2{font-size:18px;margin-top:28px}
.bar{display:flex;gap:14px;align-items:center;border-bottom:1px solid #e3e3e3;padding-bottom:10px}
.grid{display:flex;flex-wrap:wrap;gap:14px;margin-top:14px}
.card{border:1px solid #ddd;border-radius:10px;padding:10px;width:200px}
.card img{width:100%;height:140px;object-fit:contain;background:#fafafa;border-radius:6px}
.tag{font-size:11px;color:#666} .price{font-weight:700}
label{display:block;font-size:13px;color:#555;margin:12px 0 3px}
input[type=text],input[type=number],textarea,select{width:100%;padding:8px;
border:1px solid #ccc;border-radius:6px;font:inherit}
textarea{min-height:90px}
.row{display:flex;gap:14px} .row>div{flex:1}
button,.btn{background:#0a5bd3;color:#fff;border:0;border-radius:7px;padding:9px 16px;
font:inherit;cursor:pointer;margin-top:14px;display:inline-block}
.btn.alt{background:#444} .btn.ghost{background:#eee;color:#222}
.note{background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:10px;font-size:13px;margin:12px 0}
pre{background:#0d1117;color:#d6deeb;padding:14px;border-radius:8px;overflow:auto;font-size:12.5px}
.drop{border:2px dashed #aaa;border-radius:10px;padding:18px;text-align:center;color:#666}
"""


def page(title, body):
    return ("<!doctype html><meta charset=utf-8><title>" + html.escape(title) +
            "</title><style>" + CSS + "</style>" +
            "<div class=bar><a href='/'><b>Bynari Studio</b></a>"
            "<a href='/new'>+ New item</a></div>" + body)


def rep_thumb(slug):
    folder = os.path.join(PHOTOS, slug)
    if not os.path.isdir(folder):
        return None
    con = db()
    r = con.execute("SELECT p.file_path FROM photos p JOIN items i ON i.id=p.item_id "
                    "WHERE i.slug=? AND p.kind='photo' "
                    "ORDER BY p.representative DESC, p.sort_order LIMIT 1", (slug,)).fetchone()
    con.close()
    if r and os.path.exists(r["file_path"]):
        return os.path.basename(r["file_path"])
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(IMG_EXT):
            return f
    return None


# ---------------------------------------------------------------- views
def view_list():
    con = db()
    items = con.execute("SELECT * FROM items ORDER BY updated_at DESC, id DESC").fetchall()
    con.close()
    cards = []
    for it in items:
        slug = it["slug"]
        thumb = rep_thumb(slug)
        img = (f"<img src='/photos/{urllib.parse.quote(slug)}/{urllib.parse.quote(thumb)}'>"
               if thumb else "<div class=tag style='height:140px'>no photo</div>")
        etsy = "Etsy✓" if load_sidecar(slug, "etsy_draft.json") else ""
        ebay = "eBay✓" if load_sidecar(slug, "ebay_offer.json") else ""
        price = f"${it['price']:.2f}" if it["price"] is not None else "—"
        cards.append(
            f"<div class=card><a href='/item/{urllib.parse.quote(slug)}'>{img}</a>"
            f"<div class=tag>{html.escape(it['state'] or 'new')} {etsy} {ebay}</div>"
            f"<div><a href='/item/{urllib.parse.quote(slug)}'>"
            f"{html.escape(it['title'] or it['what'] or slug)}</a></div>"
            f"<div class=price>{price}</div></div>")
    return page("Bynari Studio",
                f"<h1>Inventory <span class=tag>({len(items)} items)</span></h1>"
                "<div class=grid>" + "".join(cards) + "</div>")


def view_new():
    body = """
    <h1>New item</h1>
    <form method=post action='/new' enctype='multipart/form-data'>
      <label>Photos (select all the shots for this item)</label>
      <div class=drop><input type=file name=photos multiple accept='image/*'></div>
      <div class=row>
        <div><label>Brand *</label><input type=text name=brand placeholder='Arnex'></div>
        <div><label>What is it? *</label><input type=text name=what placeholder='pocket watch'></div>
      </div>
      <div class=row>
        <div><label>Model / caliber</label><input type=text name=caliber></div>
        <div><label>Condition *</label><input type=text name=condition placeholder='Used - running'></div>
      </div>
      <label>Title</label><input type=text name=title>
      <label>Description</label><textarea name=description></textarea>
      <div class=row>
        <div><label>Price (USD)</label><input type=number step=0.01 name=price></div>
        <div><label>SKU / slug (optional)</label><input type=text name=sku placeholder='auto from brand+what'></div>
      </div>
      <button type=submit>Create item &amp; import photos</button>
    </form>"""
    return page("New item", body)


def view_item(slug):
    con = db()
    it = con.execute("SELECT * FROM items WHERE slug=?", (slug,)).fetchone()
    con.close()
    if not it:
        return None
    et = load_sidecar(slug, "etsy_meta.json")
    eb = load_sidecar(slug, "ebay_meta.json")
    folder = os.path.join(PHOTOS, slug)
    photos = sorted(f for f in os.listdir(folder) if f.lower().endswith(IMG_EXT)) \
        if os.path.isdir(folder) else []
    thumbs = "".join(
        f"<img src='/photos/{urllib.parse.quote(slug)}/{urllib.parse.quote(f)}' "
        "style='width:120px;height:120px;object-fit:contain;border:1px solid #ddd;"
        "border-radius:6px;margin:3px'>" for f in photos)

    def v(d, k, dflt=""):
        try:
            x = d[k]  # works for both dict and sqlite3.Row
        except (KeyError, IndexError):
            x = dflt
        return html.escape("" if x is None else str(x))

    etsy_drafted = load_sidecar(slug, "etsy_draft.json")
    ebay_offered = load_sidecar(slug, "ebay_offer.json")
    status = []
    if etsy_drafted:
        status.append(f"<a href='{html.escape(etsy_drafted.get('edit_url','#'))}' "
                      f"target=_blank>Etsy draft {etsy_drafted.get('listing_id','')}</a>")
    if ebay_offered:
        status.append(f"eBay offer {html.escape(str(ebay_offered.get('offer_id','')))} "
                      f"({html.escape(str(ebay_offered.get('state','')))})")
    status = " · ".join(status)

    body = f"""
    <h1>{html.escape(it['title'] or it['what'] or slug)}</h1>
    <div class=tag>slug {html.escape(slug)} · {len(photos)} photos · {html.escape(it['state'] or 'new')}
      {(' · ' + status) if status else ''}</div>
    <div style='margin:10px 0'>{thumbs}</div>

    <form method=post action='/item/{urllib.parse.quote(slug)}'>
      <h2>Item</h2>
      <div class=row>
        <div><label>Brand</label><input type=text name=brand value='{v(it,'brand')}'></div>
        <div><label>What</label><input type=text name=what value='{v(it,'what')}'></div>
      </div>
      <label>Title</label><input type=text name=title value='{v(it,'title')}'>
      <label>Description</label><textarea name=description>{v(it,'description')}</textarea>
      <div class=row>
        <div><label>Condition</label><input type=text name=condition value='{v(it,'condition')}'></div>
        <div><label>Price</label><input type=number step=0.01 name=price value='{v(it,'price')}'></div>
      </div>

      <h2>Etsy fields</h2>
      <div class=note>For Etsy, get a taxonomy id with:
        <code>python3 etsy.py taxonomy &lt;keyword&gt;</code>. who_made=someone_else for vintage resale.</div>
      <div class=row>
        <div><label>who_made</label><input type=text name=etsy_who_made value='{v(et,'who_made') or 'someone_else'}'></div>
        <div><label>when_made (e.g. 1970s)</label><input type=text name=etsy_when_made value='{v(et,'when_made')}'></div>
        <div><label>taxonomy_id</label><input type=text name=etsy_taxonomy_id value='{v(et,'taxonomy_id')}'></div>
      </div>
      <label>tags (comma separated, &le;13)</label><input type=text name=etsy_tags value='{v(et,'tags_csv') or ','.join(et.get('tags',[]))}'>
      <label>materials (comma separated)</label><input type=text name=etsy_materials value='{','.join(et.get('materials',[]))}'>

      <h2>eBay fields</h2>
      <div class=note>eBay needs a SKU and a category id. Net-new photos must be hosted
        (public URLs) before the eBay draft can carry images — Etsy takes local files directly.</div>
      <div class=row>
        <div><label>SKU</label><input type=text name=ebay_sku value='{v(eb,'sku') or slug}'></div>
        <div><label>category_id</label><input type=text name=ebay_category_id value='{v(eb,'category_id')}'></div>
        <div><label>condition (enum)</label><input type=text name=ebay_condition value='{v(eb,'condition') or 'USED_EXCELLENT'}'></div>
      </div>

      <button type=submit>Save fields</button>
    </form>

    <h2>Stage the listing</h2>
    <form method=post action='/run' style='display:inline'>
      <input type=hidden name=slug value='{html.escape(slug)}'>
      <input type=hidden name=channel value='etsy'>
      <button class='btn ghost' name=action value='preview' style='color:#222'>Preview Etsy</button>
      <button class='btn alt' name=action value='dryrun'>Etsy dry run</button>
      <button class='btn' name=action value='draft'>Create Etsy draft</button>
    </form>
    <form method=post action='/run' style='display:inline'>
      <input type=hidden name=slug value='{html.escape(slug)}'>
      <input type=hidden name=channel value='ebay'>
      <button class='btn ghost' name=action value='preview' style='color:#222'>Preview eBay</button>
      <button class='btn alt' name=action value='dryrun'>eBay dry run</button>
      <button class='btn' name=action value='draft'>Create eBay draft</button>
    </form>
    """
    return page(it["title"] or slug, body)


# ---------------------------------------------------------------- actions
def create_item(fields, files):
    brand = fields.get("brand", "").strip()
    what = fields.get("what", "").strip()
    base = slugify(fields.get("sku") or f"{brand}-{what}")
    slug = unique_slug(base)
    folder = os.path.join(PHOTOS, slug)
    os.makedirs(folder, exist_ok=True)

    con = db()
    cur = con.execute(
        "INSERT INTO items (slug,what,brand,caliber,state,title,condition,description,"
        "price,folder_path,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (slug, what, brand, fields.get("caliber", "").strip() or None, "new",
         fields.get("title", "").strip() or None, fields.get("condition", "").strip() or None,
         fields.get("description", "").strip() or None,
         float(fields["price"]) if fields.get("price", "").strip() else None,
         folder, now(), now()))
    item_id = cur.lastrowid

    saved = 0
    for fn, content in files.get("photos", []):
        ext = os.path.splitext(fn)[1].lower()
        if ext not in IMG_EXT:
            continue
        saved += 1
        dest_name = f"{saved:02d}{ext}"
        dest = os.path.join(folder, dest_name)
        open(dest, "wb").write(content)
        try:
            w, h = Image.open(io.BytesIO(content)).size
        except Exception:
            w = h = None
        con.execute(
            "INSERT INTO photos (item_id,file_path,kind,representative,sort_order,"
            "source,original_name,sha256,width,height) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (item_id, dest, "photo", 1 if saved == 1 else 0, saved, "intake",
             fn, hashlib.sha256(content).hexdigest(), w, h))
    con.commit()
    con.close()
    return slug


def save_fields(slug, fields):
    con = db()
    con.execute(
        "UPDATE items SET brand=?,what=?,title=?,description=?,condition=?,price=?,updated_at=? "
        "WHERE slug=?",
        (fields.get("brand", "").strip() or None, fields.get("what", "").strip() or None,
         fields.get("title", "").strip() or None, fields.get("description", "").strip() or None,
         fields.get("condition", "").strip() or None,
         float(fields["price"]) if fields.get("price", "").strip() else None,
         now(), slug))
    con.commit()
    con.close()

    def csv(name):
        return [x.strip() for x in fields.get(name, "").split(",") if x.strip()]

    etsy = load_sidecar(slug, "etsy_meta.json")
    etsy.update({
        "title": fields.get("title", "").strip() or None,
        "description": fields.get("description", "").strip() or None,
        "price": float(fields["price"]) if fields.get("price", "").strip() else None,
        "who_made": fields.get("etsy_who_made", "").strip() or "someone_else",
        "when_made": fields.get("etsy_when_made", "").strip() or None,
        "taxonomy_id": int(fields["etsy_taxonomy_id"]) if fields.get("etsy_taxonomy_id", "").strip().isdigit() else None,
        "tags": csv("etsy_tags")[:13],
        "materials": csv("etsy_materials"),
        "quantity": 1,
        "type": "physical",
    })
    write_sidecar(slug, "etsy_meta.json", etsy)

    ebay = load_sidecar(slug, "ebay_meta.json")
    ebay.update({
        "sku": fields.get("ebay_sku", "").strip() or slug,
        "title": fields.get("title", "").strip() or None,
        "description": fields.get("description", "").strip() or None,
        "price": float(fields["price"]) if fields.get("price", "").strip() else None,
        "condition": fields.get("ebay_condition", "").strip() or "USED_EXCELLENT",
        "category_id": fields.get("ebay_category_id", "").strip() or None,
        "quantity": 1,
    })
    write_sidecar(slug, "ebay_meta.json", ebay)


def run_script(slug, channel, action):
    """Shell out to the proven scripts. Returns combined output text."""
    py = sys.executable
    if action == "preview":
        cmd = [py, "preview.py", "--item", slug, "--channel", channel]
    elif channel == "etsy":
        cmd = [py, "etsy_push.py", "--item", slug] + (["--dry-run"] if action == "dryrun" else [])
    else:
        cmd = [py, "ebay_sell.py", "--list", slug] + (["--dry-run"] if action == "dryrun" else [])
    try:
        p = subprocess.run(cmd, cwd=LIB, capture_output=True, text=True, timeout=180)
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
        return " ".join(cmd), out or "(no output)"
    except Exception as e:
        return " ".join(cmd), f"ERROR running command: {e}"


# ---------------------------------------------------------------- http
class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype="text/html; charset=utf-8", code=200):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, loc):
        self.send_response(303)
        self.send_header("Location", loc)
        self.end_headers()

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            return self._send(view_list())
        if path == "/new":
            return self._send(view_new())
        if path.startswith("/item/"):
            slug = urllib.parse.unquote(path[len("/item/"):])
            v = view_item(slug)
            return self._send(v) if v else self._send("not found", code=404)
        if path.startswith("/photos/"):
            return self._serve_photo(urllib.parse.unquote(path[len("/photos/"):]))
        self._send("not found", code=404)

    def _serve_photo(self, rel):
        # rel = "<slug>/<filename>" — confine to PHOTOS, no traversal
        full = os.path.normpath(os.path.join(PHOTOS, rel))
        if not full.startswith(PHOTOS) or not os.path.isfile(full):
            return self._send("not found", code=404)
        ext = os.path.splitext(full)[1].lower()
        ctype = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                 ".webp": "image/webp", ".html": "text/html; charset=utf-8",
                 ".mp4": "video/mp4"}.get(ext, "application/octet-stream")
        self._send(open(full, "rb").read(), ctype=ctype)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        ctype = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        if "multipart/form-data" in ctype:
            _, params = cgi.parse_header(ctype)
            fields, files = parse_multipart(body, params["boundary"])
        else:
            fields = {k: v[0] for k, v in
                      urllib.parse.parse_qs(body.decode("utf-8", "replace")).items()}
            files = {}

        if path == "/new":
            slug = create_item(fields, files)
            return self._redirect(f"/item/{urllib.parse.quote(slug)}")
        if path.startswith("/item/"):
            slug = urllib.parse.unquote(path[len("/item/"):])
            save_fields(slug, fields)
            return self._redirect(f"/item/{urllib.parse.quote(slug)}")
        if path == "/run":
            slug = fields.get("slug", "")
            channel = fields.get("channel", "etsy")
            action = fields.get("action", "preview")
            cmd, out = run_script(slug, channel, action)
            if action == "preview" and "Wrote" in out:
                # preview.py wrote photos/<slug>/preview.html — show it inline
                return self._redirect(f"/photos/{urllib.parse.quote(slug)}/preview.html")
            body = page("run", f"<h1>{html.escape(action)} · {html.escape(channel)}</h1>"
                        f"<div class=tag>{html.escape(cmd)}</div><pre>{html.escape(out)}</pre>"
                        f"<a class='btn ghost' style='color:#222' "
                        f"href='/item/{urllib.parse.quote(slug)}'>&larr; back to item</a>")
            return self._send(body)
        self._send("not found", code=404)


def main():
    print(f"Bynari Studio — library: {LIB}")
    print(f"Open http://127.0.0.1:{PORT}  (Ctrl-C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
