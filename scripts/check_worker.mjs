// Exercise real SW event handlers on both root and project hosting paths.
import vm from 'node:vm';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const source = fs.readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
for (const scope of ['https://example.test/', 'https://example.test/voto27/']) {
  const events = {}, saved = new Map();
  let online = true, networkBody = '<html>verified 29 October; poll 26 October</html>', calls = 0;
  const cache = {
    addAll: async urls => { for (const url of urls) saved.set(url, new Response('asset')); },
    put: async (key, value) => saved.set(key, value),
    match: async key => saved.get(key)?.clone()
  };
  const sandbox = {URL, Response, setTimeout, clearTimeout,
    self: {registration: {scope}, addEventListener: (name, fn) => events[name] = fn,
      skipWaiting: async () => {}, clients: {claim: async () => {}}},
    caches: {open: async () => cache, keys: async () => [], delete: async () => true},
    fetch: async () => {calls++; if (!online) throw Error('offline'); return new Response(networkBody);}
  };
  vm.runInNewContext(source, sandbox);
  let lifetime;
  events.install({waitUntil: p => lifetime = p}); await lifetime;
  assert([...saved.keys()].every(key => key.startsWith(scope)), 'Precache must stay under project scope');
  async function navigate(url, mode = 'navigate') {
    let result; const pending = [];
    events.fetch({request: {url, method: 'GET', mode}, waitUntil: p => pending.push(p), respondWith: p => result = p});
    const response = result ? await result : undefined;
    await Promise.all(pending);
    return response;
  }
  assert.equal(await (await navigate(scope)).text(), networkBody);
  online = false;
  assert.equal(await (await navigate(scope)).text(), networkBody, 'Offline must preserve dates and values exactly');
  assert.equal(await navigate(scope + 'not-found'), undefined, 'Do not mask missing pages');
  online = true; networkBody = '<html>new verified version</html>';
  assert.equal(await (await navigate(scope)).text(), networkBody, 'New deployments must replace saved HTML');
  assert.equal(await (await navigate(scope + 'index.html')).text(), networkBody);
  assert.equal(calls, 4);
}
console.log('PASS: root/subpath caches, exact offline content, new versions and real 404s.');
