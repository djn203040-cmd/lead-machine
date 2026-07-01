# Discovery reference data (branchekoder + geography)

Generators for the two reference datasets that power **Find virksomheder**
(`apps/web/app/leads/new`). Both are committed as generated artifacts — run these
only when refreshing the source data.

## Branchekoder — `gen_catalog.js`

Curated catalog of industries the discovery filter offers, grouped into
high-level categories.

- **Source of truth:** the *curated* `C` array + `GROUPS` inside `gen_catalog.js`.
- **Validation set:** `db25_leaf_codes.json` — the 738 leaf (6-digit) codes of the
  official **Dansk Branchekode DB25** (Danmarks Statistik, effective 2025-01-01).
  This is the scheme the live CVR register migrated to — DB07 codes (e.g. `960210`
  frisør) now match only ceased companies, so the catalog must use DB25 codes
  (e.g. `962100`). Every curated code is checked to exist in this list.
- **Outputs (both regenerated in place):**
  - `apps/web/lib/branchekoder.ts` (web UI + in-app discovery)
  - `services/worker/src/leadmachine/cvr/branchekoder.py` (worker discovery + scoring)

```bash
node scripts/catalog/gen_catalog.js
```

To add an industry: add a `[code, "Dansk label", "English hint", "group"]` row to
`C` (and a new `GROUPS` entry if needed), then re-run. Adding a brand-new group
key? Also add a benchmark for it in
`services/worker/src/leadmachine/financial/estimate.py` (`BENCHMARKS`).

### Refreshing `db25_leaf_codes.json`

Download the DB25 CSV from Danmarks Statistik
(<https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/db> → CSV export),
keep rows where `NIVEAU == 5`, and map each to
`{ code: KODE without dots, titel: TITEL }`.

## Geography — `gen_geo.js`

Regions → kommuner → postnumre/byer, used by the location autocomplete. CVR can
filter on `postnummer` and `kommuneKode` (not city name), so a city selection
resolves to its postnumre and a kommune/region selection to kommunekoder.

- **Source:** DAWA / dataforsyningen.dk (public, authoritative).
- **Output:** `apps/web/lib/geo/denmark.geo.json`

```bash
node scripts/catalog/gen_geo.js
```
