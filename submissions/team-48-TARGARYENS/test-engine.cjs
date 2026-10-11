const assert = require("node:assert/strict");
const E = require("./engine.js");

const sample = '\uFEFFsearch_term,clicks,impressions,cost,conversions,campaign,conversion_value\r\n"red shoes, size 8",20,500,"₹1,200.50",2,Footwear,2400\r\n"quoted ""phrase""\ncontinued",4,80,35,1,Footwear,0\r\nno-data,30,600,500,0,Footwear,0\r\n';
const parsed = E.parseCsv(sample);
assert.equal(parsed.rows.length, 3);
assert.equal(parsed.rows[0]["Search term"], "red shoes, size 8");
assert.equal(parsed.rows[0].Cost, 1200.5);
assert.equal(parsed.rows[1]["Search term"], 'quoted "phrase"\ncontinued');
assert.equal(E.decide(parsed.rows[1], { promoteClicks: 20, promoteConversions: 2, blockClicks: 25, reviewBelowClicks: 8 }).decision, "REVIEW");
assert.equal(E.decide(parsed.rows[2], { promoteClicks: 20, promoteConversions: 2, blockClicks: 25, reviewBelowClicks: 8 }).decision, "BLOCK");
assert.throws(() => E.parseCsv("term,cost\na,1"), /Missing required columns/);

const large = [];
for (let i = 0; i < 25_000; i += 1) {
  const kind = i % 5;
  large.push({
    _rowId: i, "Search term": `query ${i}`, Clicks: [2, 20, 25, 7, 30][kind], Impressions: 100,
    Cost: [1, 20, 25, 7, 30][kind], Conversions: [0, 2, 0, 1, 1][kind], Campaign: `Campaign ${i % 4}`,
    "Conversion value": 0
  });
}
const policy = { promoteClicks: 20, promoteConversions: 2, blockClicks: 25, reviewBelowClicks: 8 };
const started = Date.now();
const analyzed = E.analyze(large, policy);
assert.equal(analyzed.length, 25_000);
const counts = analyzed.reduce((all, row) => (all[row.Decision] = (all[row.Decision] || 0) + 1, all), {});
assert.deepEqual(counts, { REVIEW: 15_000, PROMOTE: 5_000, BLOCK: 5_000 });
assert.ok(analyzed.every((row) => row.Reason && ["Low", "Medium", "High"].includes(row.Confidence)));
assert.ok(analyzed[1].Reason.includes("20 clicks"));

const duplicates = E.analyze([
  { "Search term": "Buy Shoes!", Clicks: 1, Impressions: 1, Cost: 1, Conversions: 0 },
  { "Search term": "buy shoes", Clicks: 2, Impressions: 2, Cost: 2, Conversions: 0 },
  { "Search term": "other", Clicks: 3, Impressions: 3, Cost: 3, Conversions: 0 }
], policy);
assert.deepEqual(duplicates.map((row) => row["Duplicate group size"]), [2, 2, 1]);
assert.match(E.csvText([{ term: 'one,"two"' }], ["term"]), /"one,""two"""/);
console.log(`PASS: parser, conservative decisions, explanations, exports, exact duplicate grouping, and ${analyzed.length.toLocaleString()} rows in ${Date.now() - started}ms.`);
