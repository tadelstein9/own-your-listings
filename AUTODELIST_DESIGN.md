# Auto-Delist + Cross-List — Build Spec

*own-your-listings · 2026-07-05. The owned answer to Vendoo's sale-detection: your
catalog is the source of truth; marketplaces are disposable projections. Local, BYOK.*

---

## 1. Model — one catalog item, many channel projections

`library.db` already holds `items` (the catalog) and `listings` (projections). Today `listings`
is eBay-only. Generalize it to multi-channel:

```sql
-- migration (idempotent; reconcile.py applies it): add columns to `listings`
ALTER TABLE listings ADD COLUMN channel      TEXT;   -- ebay | etsy | fb
ALTER TABLE listings ADD COLUMN external_id  TEXT;   -- eBay listingId / Etsy listing_id
ALTER TABLE listings ADD COLUMN external_ref TEXT;   -- eBay offerId (needed to withdraw); Etsy n/a
ALTER TABLE listings ADD COLUMN sku          TEXT;   -- denormalized for fast sale->listing lookup
-- status stays: draft | active | ended | sold
```

One item, N rows:
```
item  sku=MVT-AS1686-PANDAN-01  qty=1  state=listed
  listing{ channel=ebay  external_id=298482344008  external_ref=200373209011  status=active }
  listing{ channel=etsy  external_id=4531xxxxxx     external_ref=null          status=active }
  listing{ channel=fb    external_id=null           external_ref=null          status=manual }
```

## 2. The reconcile loop — `reconcile.py` (systemd timer, ~10 min)

```
for adapter in [ebay, etsy]:            # fb has no API -> manual
    for (sku, qty) in adapter.detect_sales(since=last_run):
        sold = find active listing (sku, adapter.channel)  ; mark it status=sold
        mark item state=sold  (qty>1: decrement; delist only at 0)
        for other in active listings(sku) where channel != adapter.channel:
            other_adapter.delist(other.external_ref or external_id)   # end it elsewhere
            mark other status=ended, ended_at=now
        log(action)                     # audit = "what's live where"
settings['reconcile.last_run'] = now
```

Default **dry-run** (prints what it *would* delist); `--apply` performs the withdrawals.

## 3. Per-channel adapter interface

| method | eBay | Etsy | FB |
|---|---|---|---|
| `detect_sales(since)` | `GET /sell/fulfillment/v1/order?filter=creationdate:[since..now]` → lineItems[].sku | `GET /v3/application/shops/{id}/receipts?min_created=..` → transactions[].sku | — |
| `delist(ref)` | `POST /sell/inventory/v1/offer/{offerId}/withdraw` | `PATCH /v3/application/shops/{id}/listings/{listing_id}` state=inactive | emit manual task |
| `register(...)` | after publish: store listingId + offerId | after publish: store listing_id | store nothing (manual) |

Reuses existing auth: `ebay_pull.refresh_access_token`, the `_req` helper shape from `ebay_sell.py`.
Etsy adapter reuses `etsy_push` token handling.

## 4. Honest hard parts (Vendoo shares all of these)
1. **Race window** — a qty-1 item can sell on two channels between polls. 10-min polling shrinks it; never zero. State it plainly; faster polling = smaller window, not a guarantee.
2. **Idempotent delist** — ending an already-ended listing must return success (treat 404 / "already ended" as done) so retries are safe.
3. **Reconcile-on-start** — each run first syncs each channel's live state into `listings` (marketplace = truth for "still live"), so hand-ended listings and missed sales self-heal.
4. **Token refresh** per channel before each run.

---

## 5. Cross-list operational plan (what Tom asked for)

### A. Move a couple of Etsy items onto eBay
Per-item, deliberate — not a bulk dump. For each chosen Etsy piece:

1. **Confirm it's the right kind for eBay** — a movement/part or a piece with horology-collector demand (eBay's audience). Skip the ones that are Etsy-native (decor-framed, story-led).
2. **Pull its Etsy data** (title, description, price, photos) → but **re-derive the eBay category + aspects from the Taxonomy API** (Etsy has no category discipline; a movement must land in 57720, not a guess). Same `show_aspects.py` check to avoid silent drops.
3. **Host photos on EPS** (`ebay_photos.py`) — Etsy photo URLs won't work in eBay's Inventory API.
4. **Build + validate + draft** (`ebay_sell.py --list`), publish on your trigger.
5. **Register both projections** under one SKU in `listings` (etsy row already implicit; add the ebay row). Now reconcile guards the pair.
6. **Rule to honor:** no off-platform references *inside* either listing (can't mention Etsy on eBay or vice-versa — [[ebay-off-platform-sales-rule]]). Titles/descriptions are channel-independent facts; that's fine.

**Candidates to pick from** (query the catalog / Etsy actives): the loose movements and pocket watches — they have the strongest eBay-collector pull. Pristine wearable vintage can also go, but Etsy may already be its best home. *You pick the couple; I'll pull the list.*

### B. The 6498 on BOTH platforms
The serviced running 6498 is a strong dual-channel candidate (running + serviced = broad appeal). Build **once**, project **twice**:

1. **Build the catalog item once** from the vmshare photos + video (the pipeline we just ran).
2. **eBay projection:** category 57720, aspects, USED_EXCELLENT (or the running grade the policy allows), EPS photos, video, `--list` → publish.
3. **Etsy projection:** `etsy_push` draft (Etsy needs 20+ yr for "vintage" — a 6498 caliber qualifies; confirm the specific piece's age). Etsy attributes (Style/Band/etc.) set at build.
4. **Register both** in `listings` under the one SKU (`channel=ebay`, `channel=etsy`).
5. **Turn on reconcile** for that SKU — the moment it sells on either, the other gets withdrawn automatically (eBay withdrawOffer / Etsy state=inactive). Until reconcile is battle-tested, treat the first few as **--dry-run + manual delist** so you watch it work before trusting it.

**Price note:** the two channels can carry different prices (eBay fees ~13% vs Etsy ~6.5% + listing) — the catalog holds one item; each projection can set its own price. Not a cross-listing violation.

---

## 6. Build order
1. **Now:** `reconcile.py` — listings migration + eBay `detect_sales` (getOrders) + `delist` (withdrawOffer), dry-run default. Register the live AS 1686 eBay listing so the table has real data.
2. **Next:** `register` on publish (retrofit `ebay_sell.py` to record listingId+offerId into `listings`).
3. **Then:** Etsy adapter (`detect_sales` via getShopReceipts, `delist` via updateListing inactive) — reuses `etsy_push` auth.
4. **Then:** the systemd timer (Linux-book Ch.8 example) + a `--status` "what's live where" report.
