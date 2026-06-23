import { extractDesiTracer } from '../src/core/catalog-loader.js';

const cases = new Map([
  ['desi-dr1:BGS:123', 'BGS'],
  ['desi-dr1:LRG:456', 'LRG'],
  ['desi-dr1:ELG:789', 'ELG'],
  ['desi-dr1:QSO:999', 'QSO'],
  ['2mrs:01380899-3251169', null],
  ['desi-dr1:UNKNOWN:1', null],
]);
for (const [value, expected] of cases) {
  const actual = extractDesiTracer(value);
  if (actual !== expected) throw new Error(`${value}: expected ${expected}, received ${actual}`);
}
console.log('DESI tracer parser checks passed.');
