'use strict';
/** Build search-term-triage.html from the three separate files. */
const fs = require('fs');
const path = require('path');
const dir = __dirname;
const css = fs.readFileSync(path.join(dir, 'style.css'), 'utf8');
const js = fs.readFileSync(path.join(dir, 'script.js'), 'utf8');
const html = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');

const out = html
  .replace(/<link rel="stylesheet" href="style\.css">/,
    `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'">\n  <style>\n${css}\n  </style>`)
  .replace(/<script src="script\.js"><\/script>/, `<script>\n${js}\n</script>`);

fs.writeFileSync(path.join(dir, 'search-term-triage.html'), out, 'utf8');
console.log('Wrote search-term-triage.html (' + out.length + ' bytes)');
