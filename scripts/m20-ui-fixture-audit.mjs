#!/usr/bin/env node
/** Fail if production acceptance build was not compiled for live data source. */
import fs from 'node:fs';
import path from 'node:path';

const assetsDir = path.join('apps', 'web', 'dist', 'assets');
const js = fs.readdirSync(assetsDir).find((f) => f.startsWith('index-') && f.endsWith('.js'));
if (!js) {
  console.error('missing built index js');
  process.exit(1);
}
const text = fs.readFileSync(path.join(assetsDir, js), 'utf8');
if (!text.includes('live') || text.includes('VITE_DATA_SOURCE","fixture"')) {
  console.error('live data source not detected in acceptance build');
  process.exit(1);
}
console.log('Fixture contamination audit: PASS (live build)');
