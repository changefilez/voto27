/* Progressive enhancement: the HTML remains the source of displayed poll data. */
(() => {
  'use strict';
  const radios = [...document.querySelectorAll('input.tab-radio')];
  const nav = [...document.querySelectorAll('nav label[for]')];
  radios.forEach(radio => {
    radio.tabIndex = -1;
    radio.setAttribute('aria-hidden', 'true');
    radio.addEventListener('change', () => {
      if (radio.checked) activate(radio.id.slice(4), {push: true, focus: true});
    });
  });
  const blocked = () => document.body.classList.contains('blackout-active');
  function activate(id, {push = false, focus = false} = {}) {
    const radio = document.getElementById('tab-' + id);
    if (!radio || !radios.includes(radio)) return false;
    if (blocked() && id !== 'metodo') return false;
    radio.checked = true;
    nav.forEach(label => {
      const current = label.htmlFor === 'tab-' + (id.startsWith('poll-') ? 'sondaggi' : id);
      if (current) label.setAttribute('aria-current', 'page');
      else label.removeAttribute('aria-current');
    });
    const page = document.getElementById(id);
    document.title = (page?.querySelector('h1,h2')?.textContent || 'Oggi') + ' — VOTO27';
    if (push && location.hash !== '#' + id) history.pushState(null, '', '#' + id);
    if (focus) {
      window.scrollTo({top: 0, behavior: 'instant'});
      const heading = page?.querySelector('h1,h2');
      heading?.setAttribute('tabindex', '-1');
      heading?.focus({preventScroll: true});
    }
    return true;
  }
  // Labels preserve the script-free radio navigation; expose keyboard controls too.
  document.querySelectorAll('label[for^="tab-"]').forEach(label => {
    label.tabIndex = 0;
    label.setAttribute('role', 'button');
    label.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault(); label.click();
      }
    });
    label.addEventListener('click', event => {
      event.preventDefault();
      activate(label.htmlFor.slice(4), {push: true, focus: true});
    });
  });
  function restore() {
    const id = location.hash.slice(1) || 'oggi';
    activate(id) || activate(blocked() ? 'metodo' : 'oggi');
  }
  window.addEventListener('popstate', () => {restore(); window.scrollTo(0, 0);});
  window.addEventListener('hashchange', restore);
  restore();

  const tools = document.querySelector('.archive-tools');
  const search = document.getElementById('poll-search');
  const status = document.getElementById('poll-status');
  const entries = [...document.querySelectorAll('#sondaggi [data-poll-state]')];
  const normalize = text => text.toLocaleLowerCase('it').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
  function filter() {
    let count = 0;
    const query = normalize(search.value);
    entries.forEach(entry => {
      const visible = normalize(entry.textContent).includes(query) &&
        (status.value === 'all' || entry.dataset.pollState === status.value);
      entry.hidden = !visible;
      if (visible) count++;
    });
    document.getElementById('poll-count').textContent = `${count} di ${entries.length} rilevazioni`;
    document.getElementById('poll-empty').hidden = count > 0;
  }
  if (tools && search && status) {
    tools.hidden = false;
    search.addEventListener('input', filter);
    status.addEventListener('change', filter);
    filter();
  }
  const offline = document.getElementById('connection-status');
  function connection() { if (offline) offline.hidden = navigator.onLine; }
  addEventListener('online', connection); addEventListener('offline', connection); connection();
  const refresh = document.getElementById('refresh-site');
  if (refresh) {
    refresh.hidden = false;
    refresh.addEventListener('click', async () => {
      refresh.disabled = true;
      refresh.textContent = 'Aggiornamento…';
      try { await navigator.serviceWorker?.getRegistration().then(reg => reg?.update()); }
      catch (_) { /* A reload still works if service workers are disabled. */ }
      location.reload();
    });
  }
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js', {updateViaCache: 'none'}).then(reg => {
        reg.update().catch(() => {});
      }).catch(() => {});
    });
  }
})();
