'use strict';
/**
 * Run the official PS-01 search_terms_report.csv through the triage engine
 * and write export CSVs into ./output/
 */
const fs = require('fs');
const path = require('path');
const {
  DEFAULTS, tableFromText, buildRows, computeAll, suggest,
  toCSV, resultRows, keywordRows, negativeRows, patternRows
} = require('./script.js');

const SRC = path.join(__dirname, 'data', 'PS-01_search_term_triage', 'search_terms_report.csv');
const OUT = path.join(__dirname, 'output');

console.log('Reading', SRC);
const text = fs.readFileSync(SRC, 'utf8');
const rows = buildRows(tableFromText(text));
console.log('Parsed', rows.length.toLocaleString(), 'terms');

const { acct, groups, patterns } = computeAll(rows, DEFAULTS);
suggest(rows);

const counts = { promote: 0, block: 0, ignore: 0 };
let review = 0;
for (const r of rows) {
  counts[r.decision]++;
  if (r.review) review++;
}

console.log('\nAccount baselines');
console.log('  conversion rate:', (acct.p * 100).toFixed(2) + '%');
console.log('  cost per conversion:', isFinite(acct.cpa) ? '$' + acct.cpa.toFixed(2) : 'n/a');
console.log('\nDecisions');
console.log('  promote:', counts.promote.toLocaleString());
console.log('  block:  ', counts.block.toLocaleString());
console.log('  ignore: ', counts.ignore.toLocaleString());
console.log('  need review:', review.toLocaleString());
console.log('  groups (2+ variants):', groups.filter(g => g.members.length > 1).length.toLocaleString());
console.log('  block patterns:', patterns.length.toLocaleString());

// Spot-check: thin conversion must not promote
const thin = rows.find(r => r.clicks === 2 && r.conv === 1);
if (thin) {
  console.log('\nSpot-check 2 clicks / 1 conv:', thin.q);
  console.log('  ->', thin.decision, thin.conf, 'review=' + thin.review);
  console.log('  ', thin.reason);
}

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'triage_output.csv'), toCSV(resultRows(rows)));
fs.writeFileSync(path.join(OUT, 'keywords_to_add.csv'), toCSV(keywordRows(rows)));
fs.writeFileSync(path.join(OUT, 'negatives_to_add.csv'), toCSV(negativeRows(rows)));
fs.writeFileSync(path.join(OUT, 'phrase_negatives.csv'), toCSV(patternRows(patterns)));

console.log('\nWrote exports to', OUT);
console.log('  triage_output.csv');
console.log('  keywords_to_add.csv  (' + keywordRows(rows).length + ' keywords)');
console.log('  negatives_to_add.csv (' + negativeRows(rows).length + ' negatives)');
console.log('  phrase_negatives.csv (' + patterns.length + ' patterns)');
console.log('\nDone. To review in the browser: open index.html and drop');
console.log('  data\\PS-01_search_term_triage\\search_terms_report.csv');
