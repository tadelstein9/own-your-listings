#!/usr/bin/env python3
"""ebay_video.py — upload a listing video to eBay's Media API and get a videoId
to attach via Inventory product.videoIds. Stdlib only; reuses ebay_pull for OAuth.

Flow (eBay Media API):
  1. createVideo  POST /commerce/media/v1_beta/video          declare title + EXACT byte size + classification
  2. uploadVideo  POST /commerce/media/v1_beta/video/{id}/upload   the .mp4 (MPEG-4 AVC) bytes, size MUST match
  3. getVideo     GET  /commerce/media/v1_beta/video/{id}      poll PENDING_UPLOAD -> PROCESSING -> LIVE
  4. attach       returned videoId -> meta["video_ids"] -> Inventory product.videoIds (ebay_sell.py)

BYOK: the real upload writes a video to YOUR eBay account, so it fires only when
you run it WITHOUT --dry-run. --dry-run proves exactly what createVideo would send.
(Live createVideo host: confirm api.ebay.com vs apim.ebay.com on your first real run.)

  python3 ebay_video.py --file clip.mp4 --title "Running demo" --dry-run
  python3 ebay_video.py --file clip.mp4 --title "Running demo"     # real: create + upload + poll
  python3 ebay_video.py --status <videoId>
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

import ebay_pull

MEDIA = "https://api.ebay.com/commerce/media/v1_beta"


def _json(method, token, path, body=None):
    req = urllib.request.Request(
        MEDIA + path,
        data=(json.dumps(body).encode() if body is not None else None),
        method=method,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return r.status, dict(r.headers), (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


def create_video(token, title, size):
    code, hdrs, data = _json("POST", token, "/video",
                             {"title": title[:80], "size": size, "classification": ["ITEM"]})
    if code not in (200, 201):
        sys.exit(f"createVideo failed [{code}]: {data}")
    loc = hdrs.get("Location") or hdrs.get("location") or ""
    return loc.rstrip("/").split("/")[-1]


def upload_video(token, vid, path):
    with open(path, "rb") as f:
        blob = f.read()
    req = urllib.request.Request(f"{MEDIA}/video/{vid}/upload", data=blob, method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/octet-stream"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status
    except urllib.error.HTTPError as e:
        sys.exit(f"uploadVideo failed [{e.code}]: {e.read().decode('utf-8', 'replace')[:400]}")


def get_video(token, vid):
    _, _, data = _json("GET", token, f"/video/{vid}")
    return data if isinstance(data, dict) else {"raw": data}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="path to an .mp4 (MPEG-4 AVC)")
    ap.add_argument("--title", default="Item video")
    ap.add_argument("--status", metavar="VIDEO_ID", help="poll a video's processing status")
    ap.add_argument("--dry-run", action="store_true", help="show the createVideo payload; send nothing")
    ap.add_argument("--creds", default=ebay_pull.DEFAULT_CREDS)
    args = ap.parse_args()

    creds = ebay_pull.load_creds(args.creds)
    token = ebay_pull.refresh_access_token(creds)

    if args.status:
        v = get_video(token, args.status)
        print(json.dumps({k: v.get(k) for k in ("videoId", "status", "size")}, indent=2))
        return
    if not args.file:
        ap.error("use --file <mp4> [--dry-run] or --status <videoId>")
    if not os.path.exists(args.file):
        sys.exit(f"no such file: {args.file}")

    size = os.path.getsize(args.file)
    ext = os.path.splitext(args.file)[1].lower()
    payload = {"title": args.title[:80], "size": size, "classification": ["ITEM"]}
    print(f"file  : {args.file}")
    print(f"size  : {size:,} bytes")
    print(f"type  : {ext}  {'(ok)' if ext == '.mp4' else '(WARN: eBay wants MPEG-4 AVC .mp4)'}")
    print(f"createVideo payload: {json.dumps(payload)}")
    if args.dry_run:
        print("--dry-run: nothing sent. Re-run without --dry-run to upload to YOUR account.")
        return

    vid = create_video(token, args.title, size)
    print(f"created videoId = {vid}")
    print(f"uploading {size:,} bytes ...")
    print(f"  upload HTTP {upload_video(token, vid, args.file)}")
    v = get_video(token, vid)
    print(f"status = {v.get('status')}  (PENDING_UPLOAD -> PROCESSING -> LIVE)")
    print(f'attach: add  "video_ids": ["{vid}"]  to the item\'s ebay_meta.json')


if __name__ == "__main__":
    main()
