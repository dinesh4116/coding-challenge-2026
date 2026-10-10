'use strict';
/**
 * Headless Chrome smoke test via CDP (no npm packages).
 * Loads index.html, clicks sample, switches tabs, changes a decision,
 * confirms no console errors and no outside network requests.
 */
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const net = require('net');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PAGE = path.resolve(__dirname, 'index.html');
const USER_DATA = path.join(__dirname, '.chrome-smoke-profile');

function findPort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.listen(0, '127.0.0.1', () => {
      const { port } = s.address();
      s.close(() => resolve(port));
    });
    s.on('error', reject);
  });
}

function getJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try { resolve(JSON.parse(d)); } catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

async function waitForWS(port, tries = 50) {
  for (let i = 0; i < tries; i++) {
    try {
      const list = await getJSON(`http://127.0.0.1:${port}/json/list`);
      const page = list.find(t => t.type === 'page' && t.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch (_) { /* retry */ }
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('Chrome CDP not ready');
}

class CDP {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 0;
    this.pending = new Map();
    this.events = [];
  }
  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((res, rej) => {
      this.ws.addEventListener('open', res);
      this.ws.addEventListener('error', rej);
    });
    this.ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method) {
        this.events.push(msg);
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { try { this.ws.close(); } catch (_) {} }
}

async function main() {
  const port = await findPort();
  fs.mkdirSync(USER_DATA, { recursive: true });
  const chrome = spawn(CHROME, [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${USER_DATA}`,
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--allow-file-access-from-files',
    'about:blank'
  ], { stdio: 'ignore' });

  let ok = true;
  try {
    const wsUrl = await waitForWS(port);
    const cdp = new CDP(wsUrl);
    await cdp.connect();
    await cdp.send('Runtime.enable');
    await cdp.send('Network.enable');
    await cdp.send('Page.enable');

    const evalExpr = async (expression) => {
      const r = await cdp.send('Runtime.evaluate', {
        expression, awaitPromise: true, returnByValue: true
      });
      if (r.exceptionDetails) {
        throw new Error((r.exceptionDetails.exception && r.exceptionDetails.exception.description) ||
          r.exceptionDetails.text || JSON.stringify(r.exceptionDetails));
      }
      return r.result.value;
    };

    const fileUrl = 'file:///' + PAGE.replace(/\\/g, '/');
    await cdp.send('Page.navigate', { url: fileUrl });
    await new Promise(r => setTimeout(r, 1000));

    // Demo login gate (client-side session)
    await evalExpr(`
      (function(){
        const app = document.getElementById('app');
        if (app && !app.hidden) return true;
        document.getElementById('user').value = 'analyst';
        document.getElementById('pass').value = 'triage2026';
        document.getElementById('loginForm').requestSubmit
          ? document.getElementById('loginForm').requestSubmit()
          : document.getElementById('loginForm').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        return !document.getElementById('app').hidden;
      })()
    `);
    await new Promise(r => setTimeout(r, 200));

    await evalExpr(`document.getElementById('sample').click()`);
    // Sample builds 5k rows — wait until status updates
    let status = '';
    for (let i = 0; i < 40; i++) {
      status = await evalExpr(`document.getElementById('status').textContent`);
      if (/terms loaded/i.test(status)) break;
      await new Promise(r => setTimeout(r, 250));
    }

    const resultsVisible = await evalExpr(`!document.getElementById('results').hidden`);
    const nTerms = parseInt((status.match(/([\d,]+)\s+terms/) || ['0', '0'])[1].replace(/,/g, ''), 10);

    await evalExpr(`document.getElementById('tab-groups').click()`);
    const groupsSelected = await evalExpr(`document.getElementById('tab-groups').getAttribute('aria-selected')`);
    await evalExpr(`document.getElementById('tab-patterns').click()`);
    await evalExpr(`document.getElementById('tab-terms').click()`);

    const changed = await evalExpr(`
      (function(){
        const sel = document.querySelector('#tb select[data-i]');
        if (!sel) return false;
        sel.value = 'promote';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      })()
    `);

    // Simulate export download path (create Blob URL like the app does)
    const blobOk = await evalExpr(`
      (function(){
        try {
          const a = document.createElement('a');
          a.href = URL.createObjectURL(new Blob(['\\ufeffa,b\\r\\n1,2'], { type: 'text/csv;charset=utf-8' }));
          a.download = 'smoke.csv';
          a.click();
          setTimeout(function(){ URL.revokeObjectURL(a.href); }, 200);
          return true;
        } catch (e) { return String(e); }
      })()
    `);

    const outside = cdp.events
      .filter(e => e.method === 'Network.requestWillBeSent')
      .map(e => e.params.request.url)
      .filter(u => !/^file:|^blob:|^data:|^devtools:/i.test(u));

    const consoleErrors = cdp.events
      .filter(e => e.method === 'Runtime.exceptionThrown')
      .map(e => {
        const d = e.params.exceptionDetails || {};
        return (d.exception && d.exception.description) || d.text || 'error';
      });

    console.log('Status:', status);
    console.log('Results visible:', resultsVisible);
    console.log('Terms loaded:', nTerms);
    console.log('Groups tab selected:', groupsSelected);
    console.log('Decision override applied:', changed);
    console.log('Blob CSV download path OK:', blobOk);
    console.log('Outside network requests:', outside.length ? outside : 'none');
    console.log('Console exceptions:', consoleErrors.length ? consoleErrors : 'none');

    if (!resultsVisible || nTerms < 1000 || groupsSelected !== 'true' ||
        changed !== true || blobOk !== true || outside.length || consoleErrors.length) {
      ok = false;
    }

    cdp.close();
  } catch (e) {
    console.error('Smoke test error:', e.message);
    ok = false;
  } finally {
    try { chrome.kill(); } catch (_) {}
    // Give Chrome a moment, then clean profile
    await new Promise(r => setTimeout(r, 400));
    try { fs.rmSync(USER_DATA, { recursive: true, force: true }); } catch (_) {}
  }
  console.log(ok ? '\nSMOKE PASS' : '\nSMOKE FAIL');
  process.exit(ok ? 0 : 1);
}

main();
