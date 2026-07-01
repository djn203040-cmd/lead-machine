// Build the compact Danish geography dataset used by the discovery location
// picker (apps/web/lib/geo/denmark.geo.json) from DAWA / dataforsyningen.dk.
//
//   node scripts/catalog/gen_geo.js
//
// Emits { regions:[[kode,navn]], kommuner:[[kode,navn,regionskode]],
//         postnumre:[[nr,navn(by),[kommunekoder]]] } — see apps/web/lib/geo.ts.
const fs = require("fs");
const path = require("path");
const https = require("https");

const OUT = path.join(__dirname, "..", "..", "apps/web/lib/geo/denmark.geo.json");
const num = (s) => parseInt(s, 10);

function get(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (res) => {
        let body = "";
        res.on("data", (c) => (body += c));
        res.on("end", () => resolve(JSON.parse(body)));
      })
      .on("error", reject);
  });
}

(async () => {
  const [P, K, R] = await Promise.all([
    get("https://api.dataforsyningen.dk/postnumre"),
    get("https://api.dataforsyningen.dk/kommuner"),
    get("https://api.dataforsyningen.dk/regioner"),
  ]);
  const regions = R.map((r) => [num(r.kode), r.navn.replace(/^Region /, "")]).sort(
    (a, b) => a[0] - b[0],
  );
  const kommuner = K.filter((k) => !k.udenforkommuneinddeling)
    .map((k) => [num(k.kode), k.navn, num(k.regionskode)])
    .sort((a, b) => a[1].localeCompare(b[1], "da"));
  const postnumre = P.filter((p) => num(p.nr) >= 1000 && num(p.nr) <= 9999)
    .map((p) => [num(p.nr), p.navn, (p.kommuner || []).map((c) => num(c.kode))])
    .sort((a, b) => a[0] - b[0]);
  fs.writeFileSync(OUT, JSON.stringify({ regions, kommuner, postnumre }));
  console.log(
    `wrote ${OUT} — ${regions.length} regions, ${kommuner.length} kommuner, ${postnumre.length} postnumre`,
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
