# own-your-listings

A local-first toolkit for listing your **own** inventory on eBay through the Sell API — from a database you control, with your own developer keys, and a publish step that fires only when you pull the trigger.

It grew out of a plain discovery: **you can't just upload a listing to eBay anymore.** The old flat-file / bulk path is all but gone for the ordinary seller; the one programmatic door left is the API, and the API makes you become a registered developer to walk through it. This is a working, honest reference implementation of that walk — built while listing vintage watches and parts.

> Companion essay: [*"You Can't Just Sell on eBay Anymore"*](https://tomadelstein.substack.com/p/you-cant-just-sell-on-ebay-anymore) — Unfound Exits.

## What it does

1. **Keeps your inventory in a local SQLite database** (`schema.sql`) — the source of truth, on your drive, not eBay's.
2. **Hosts your photos on eBay's own picture servers (EPS).** The modern REST Inventory API refuses raw image files — it accepts only URLs. So photos go up through the *old* Trading API call `UploadSiteHostedPictures` and come back as hosted URLs. This is the piece most people get stuck on.
3. **Builds a draft listing** via the Sell Inventory API (`createOrReplaceInventoryItem` + `createOffer`). Nothing publishes on its own.
4. **Publishes only on an explicit command** (`ebay_sell.py --publish`). Your account, your keys, your finger on the trigger.

## The files

| File | Role |
|---|---|
| `ebay_pull.py` | OAuth (refresh-token → access-token) + `GetItem`. Pull your own live listings and read eBay's expected shape like a spec. |
| `ebay_photos.py` | Upload local photos to EPS through the Trading API; write the hosted URLs back into the item's `ebay_meta.json`. |
| `ebay_sell.py` | Build the inventory item + offer (draft); `--publish` takes it live. `--list` is idempotent. |
| `studio.py` | The local library layer over `schema.sql`. |
| `examples/build_movement.py` | A real worked example: one loose watch movement, from nothing to a draft. |
| `schema.sql` | The inventory database spec. |

## Setup

You need an **eBay Developer** account.

1. **Get a keyset** (App ID, Cert ID, Dev ID) from the eBay Developer Program.
2. **Authorize your selling account once** through the OAuth user-consent flow for the `sell.inventory` and `sell.account` scopes, and save the **refresh token**.
3. Copy the templates and fill them in (the real files are git-ignored):
   ```sh
   cp ebay_credentials.json.example ebay_credentials.json   # client_id / client_secret / refresh_token
   cp ebay_app.json.example         ebay_app.json           # your business-policy + location IDs
   ```
4. Create your **business policies** (fulfillment, payment, return) and an **inventory location** in Seller Hub, then paste their IDs into `ebay_app.json`.

## Usage

```sh
# 1. put an item + its photos into the local library
python3 examples/build_movement.py

# 2. host the photos on eBay's picture servers (writes URLs into ebay_meta.json)
python3 ebay_photos.py --item <slug> --creds ebay_credentials.json

# 3. preview the draft payload (nothing is sent)
python3 ebay_sell.py --list <slug> --dry-run

# 4. create the UNPUBLISHED draft offer
python3 ebay_sell.py --list <slug>

# 5. publish it live — only when YOU say so
python3 ebay_sell.py --publish <slug>
```

## A note on category quirks

eBay validates the condition and the required item specifics **only at publish time, and one error at a time.** For example, the Pocket Watches category (`3937`) rejects the `USED_GOOD` condition and requires a `Department` specific — neither shows up until you try to publish. You learn a category's rules by walking into them, so write them into your item template once and they're paid for.

## Security

- **Never commit your real `ebay_credentials.json` / `ebay_app.json`.** The `.gitignore` blocks them; only the `*.example` templates ship.
- Credentials live in files, read from disk — never in the code.
- Everything runs as *you*, on *your* machine, against *your* account.

## Credit

The core insight — that the REST Inventory API can't take image bytes, so images must route through the Trading API's `UploadSiteHostedPictures` — came from studying the open-source **hahm-ebay-lister** project. This code reimplements that logic cleanly, local-first, on the author's own keyset.

## License

MIT © 2026 Tom Adelstein
