-- library.db — the local inventory "brain".
-- The database is the source of truth; a marketplace (eBay, Etsy) is just one place you project it to.
-- One item, its photos in a deliberate order, and its item specifics.

CREATE TABLE items (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  slug          TEXT UNIQUE NOT NULL,   -- derived from the SKU
  what          TEXT,
  brand         TEXT,
  category_id   INTEGER,
  category_path TEXT,
  caliber       TEXT,                   -- domain field (this toolkit was built listing watches)
  sell_as       TEXT,                   -- single | lot | variation
  state         TEXT,                   -- new | drafted | listed | sold
  title         TEXT,
  condition     TEXT,
  description   TEXT,
  price         REAL,                   -- NULL: pricing is the seller's call
  folder_path   TEXT,
  template_id   INTEGER REFERENCES templates(id),
  created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE photos (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id            INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  file_path          TEXT NOT NULL,     -- reference only; the original file is never moved
  kind               TEXT,              -- photo | video
  role               TEXT,              -- hero | movement | caseback | running-demo ...
  shows              TEXT,
  condition_evidence TEXT,
  representative     INTEGER DEFAULT 0, -- seller-verified flag: the seller's eye overrides the camera
  sort_order         INTEGER,
  source             TEXT,
  source_url         TEXT,
  original_name      TEXT,
  sha256             TEXT,
  width              INTEGER,
  height             INTEGER
);

CREATE TABLE item_specifics (
  id      INTEGER PRIMARY KEY,
  item_id INTEGER NOT NULL REFERENCES items(id),
  name    TEXT NOT NULL,
  value   TEXT,
  source  TEXT DEFAULT 'ebay'
);

CREATE TABLE listings (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id      INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  ebay_item_no TEXT,
  status       TEXT,                    -- draft | active | ended | sold
  listed_at    TEXT,
  ended_at     TEXT,
  created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE templates (
  id          TEXT PRIMARY KEY,
  name        TEXT,
  category_id TEXT,
  updated_at  TEXT,
  doc         TEXT NOT NULL
);

CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT
);
