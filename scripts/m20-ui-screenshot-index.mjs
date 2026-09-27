#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const dir = process.argv[2] ?? path.join('artifacts', 'screenshots', 'ui-final');
const manifestPath = path.join(dir, 'manifest.json');
const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, 'utf8')) : { frames: [] };

const rows = manifest.frames
  .map(
    (f) =>
      `<tr><td><img src="${f.filename}" width="360" alt="${f.filename}"/></td><td>${f.filename}</td><td>${f.connection ?? ''}</td><td>${f.event_cursor ?? ''}</td><td>${f.semantic ?? ''}</td></tr>`,
  )
  .join('\n');

const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>M20 UI frames</title>
<style>body{font-family:system-ui;background:#0a0a0c;color:#e8e8ec}table{border-collapse:collapse;width:100%}td,th{border:1px solid #333;padding:8px;vertical-align:top}</style>
</head><body><h1>M20 UI acceptance (${manifest.frames.length} frames)</h1>
<table><thead><tr><th>Preview</th><th>File</th><th>Conn</th><th>Seq</th><th>Semantic</th></tr></thead><tbody>${rows}</tbody></table></body></html>`;

const out = path.join(dir, 'index.html');
fs.writeFileSync(out, html);
console.log('Wrote', out);
