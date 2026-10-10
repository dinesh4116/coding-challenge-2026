'use strict';
/**
 * Node tests for Search Term Triage Engine (pure logic only).
 * Run: node test-logic.js
 */
const {
  DEFAULTS, tableFromText, buildRows, judge, wilson, groupKey,
  computeAll, toCSV, safeCell, makeSample
} = require('./script.js');

let passed = 0, failed = 0;
function assert(cond, msg) {
  if (cond) { passed++; console.log('  PASS:', msg); }
  else { failed++; console.error('  FAIL:', msg); }
}

console.log('\n=== 1. Sample 5,000 rows end-to-end ===');
{
  const sample = makeSample(5000);
  const rows = buildRows(tableFromText(toCSV(sample)));
  assert(rows.length === 5000, `built ${rows.length} rows (expect 5000)`);
  const { acct, groups, patterns } = computeAll(rows, DEFAULTS);
  const counts = { promote: 0, block: 0, ignore: 0 };
  let review = 0;
  for (const r of rows) {
    counts[r.decision]++;
    if (r.review) review++;
  }
  console.log('    mix:', counts, 'review:', review);
  console.log('    account CVR:', (acct.p * 100).toFixed(2) + '%', 'CPA:', isFinite(acct.cpa) ? acct.cpa.toFixed(2) : 'n/a');
  console.log('    groups with 2+ variants:', groups.filter(g => g.members.length > 1).length);
  console.log('    block patterns:', patterns.length);
  assert(counts.promote > 0, 'has some promote');
  assert(counts.block > 0, 'has some block');
  assert(counts.ignore > 0, 'has some ignore');
  assert(review > 0, 'has some needs_review');
  assert(rows.every(r => r.decision && r.conf && r.reason), 'every term has decision/conf/reason');
}

console.log('\n=== 2. Google Ads style file (titles, quotes, Total row) ===');
{
  const ads = [
    'Search terms report',
    'Account: Demo Shop',
    'January 1, 2026 - January 7, 2026',
    '',
    'Search term,Match type,Campaign,Ad group,Impressions,Clicks,Cost,Conversions,Conversion value',
    '"buy red shoes",Exact,Shoes - Search,Core,"1,200",200,"$340.50",20,"1,500.00"',
    '"free diy tips",Broad,Care - Search,Generic,500,80,"$90.00",0,0',
    'Total: Search terms,-,-,-,"1,700",280,"$430.50",20,"1,500.00"'
  ].join('\n');
  const table = tableFromText(ads);
  const rows = buildRows(table);
  assert(rows.length === 2, `parsed ${rows.length} data rows (Total dropped)`);
  assert(rows[0].clicks === 200, `quoted clicks parsed as 200 (got ${rows[0].clicks})`);
  assert(rows[0].cost === 340.50, `quoted cost with $ parsed as 340.50 (got ${rows[0].cost})`);
  assert(rows[0].imp === 1200, `quoted impressions 1,200 -> 1200 (got ${rows[0].imp})`);
  assert(!rows.some(r => /total/i.test(r.q)), 'no Total row remains');
}

console.log('\n=== 3. Decision logic: thin / promote / block ===');
{
  const C = DEFAULTS;
  // Realistic account: ~4% CVR, CPA ~$25
  const acct = { p: 0.04, cpa: 25 };

  const thin = judge(2, 1, 5, acct, C);
  assert(thin.decision === 'ignore', `2c/1conv decision=ignore (got ${thin.decision})`);
  assert(thin.review === true, '2c/1conv flagged needs_review');
  assert(thin.decision !== 'promote', '2c/1conv NOT promoted');

  const winner = judge(200, 20, 400, acct, C);
  const [lo] = wilson(20, 200);
  assert(lo > acct.p, `Wilson lo ${lo.toFixed(4)} > account ${acct.p}`);
  assert(winner.decision === 'promote', `200c/20conv promote (got ${winner.decision})`);

  const loser = judge(300, 0, 500, acct, C);
  const z0 = Math.pow(1 - acct.p, 300);
  assert(z0 < C.alpha, `P(0 conv) ${(z0 * 100).toFixed(4)}% < alpha`);
  assert(loser.decision === 'block', `300c/0conv with spend blocked (got ${loser.decision})`);
}

console.log('\n=== 4. Grouping near-duplicates ===');
{
  const a = groupKey('buy red shoes');
  const b = groupKey('red shoes buy');
  const c = groupKey('buy red shoe');
  assert(a === b && b === c, `same group key: "${a}"`);
}

console.log('\n=== 5. Clear errors for bad files ===');
{
  let err1 = '';
  try {
    buildRows(tableFromText('foo,bar\n1,2'));
  } catch (e) { err1 = e.message; }
  assert(/header|Missing|Expected/i.test(err1), `no-header error: ${err1}`);

  let err2 = '';
  try {
    buildRows(tableFromText('Search term,Impressions\nbuy shoes,100'));
  } catch (e) { err2 = e.message; }
  assert(/Missing/i.test(err2) && /clicks/i.test(err2), `missing-cols error: ${err2}`);
  assert(/Columns found/i.test(err2), 'lists columns found');
}

console.log('\n=== 6. Formula-injection protection ===');
{
  assert(safeCell('=SUM(A1)') === "'=SUM(A1)", 'prefixes = formula');
  assert(safeCell('+cmd') === "'+cmd", 'prefixes +');
  assert(safeCell('-1.5') === '-1.5', 'plain negative number unchanged');
  assert(safeCell('buy shoes') === 'buy shoes', 'normal text unchanged');
}

console.log('\n=== Summary ===');
console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
