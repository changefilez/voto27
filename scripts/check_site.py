"""Check generated data and static navigation; rebuild only in a temporary copy."""
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
feed = json.loads((ROOT / 'data/polls.json').read_text())
derived = json.loads((ROOT / 'data/derived.json').read_text())
config = json.loads((ROOT / 'data/config.json').read_text())
html = (ROOT / 'index.html').read_text()

class Navigation(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.labels, self.radios = [], [], set()
        self.circles = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'label' and 'for' in attrs:
            self.labels.append(attrs['for'])
        if tag == 'input' and attrs.get('type') == 'radio':
            assert attrs.get('name') == 'tabs'
            self.radios.add(attrs['id'])
        if tag == 'circle':
            self.circles += 1

nav = Navigation()
nav.feed(html)
assert len(nav.ids) == len(set(nav.ids)), 'Duplicate HTML IDs'
assert set(nav.labels) <= set(nav.ids), 'Broken label navigation'
for poll in feed['polls']:
    page = 'poll-' + poll['id']
    assert page in nav.ids and 'tab-' + page in nav.radios
    assert f'#tab-{page}:checked ~ .app #{page}{{display:block}}' in html
assert json.loads(re.search(r'const CONFIG = (.*?);', html)[1]) == config
assert config['data_last_update'] == derived['current']['date']
assert config['sources_verified_on'] == config['cards_updated_on'] == feed['verified_on']
assert f'PASS</b> ({len(feed["polls"])} sondaggi nel feed)' in html
assert nav.circles == 13 * len(derived['snapshots']), 'Missing chart points'

# Recompute from original observations, independently of the generated summaries.
for snapshot in derived['snapshots']:
    day = date.fromisoformat(snapshot['date'])
    eligible = [p for p in feed['polls'] if p['comparable']
                and 0 <= (day - date.fromisoformat(p['published'])).days <= 42]
    latest = {inst: max((p for p in eligible if p['institute'] == inst),
                       key=lambda p: (p['published'], p['id']))
              for inst in {p['institute'] for p in eligible}}
    assert set(snapshot['selected_polls']) == {p['id'] for p in latest.values()}
    for party, mean in snapshot['parties'].items():
        observations = [p for p in latest.values() if party in p['values']]
        weights = [math.exp(-(day - date.fromisoformat(p['published'])).days / 21)
                   for p in observations]
        calculated = math.fsum(p['values'][party] * w for p, w in zip(observations, weights)) / math.fsum(weights)
        assert math.isclose(mean, calculated, abs_tol=1e-12)
        assert set(snapshot['coverage'][party]) == {p['id'] for p in observations}
        assert len(observations) >= 3 and max(weights) / sum(weights) <= .6
current = derived['current']
assert current == derived['snapshots'][-1]
today = re.search(r'<main id="oggi".*?</main>', html, re.S)[0]
for party, value in current['parties'].items():
    row = re.search(r'<details class="party party-' + party + r'".*?</details>', today, re.S)[0]
    assert f'{value:.2f}'.replace('.', ',') + '%' in row
assert not any(p['id'] in current['selected_polls'] for p in feed['polls'] if not p['comparable'])

files = ['index.html', 'sw.js', 'data/config.json', 'data/derived.json']
with tempfile.TemporaryDirectory() as directory:
    copy = Path(directory)
    shutil.copytree(ROOT / 'data', copy / 'data')
    shutil.copytree(ROOT / 'scripts', copy / 'scripts')
    for name in ['index.html', 'sw.js']:
        shutil.copy(ROOT / name, copy / name)
    subprocess.run([sys.executable, str(copy / 'scripts/update_site.py')], check=True, stdout=subprocess.DEVNULL)
    for name in files:
        assert (copy / name).read_bytes() == (ROOT / name).read_bytes(), f'Non-reproducible: {name}'
assert hashlib.sha256(html.encode()).hexdigest()[:12] in (ROOT / 'sw.js').read_text()
print(f'PASS: {len(feed["polls"])} schede, {len(current["selected_polls"])} istituti, '
      f'{len(derived["snapshots"])} snapshot; date, navigazione, medie, grafici e rigenerazione coerenti.')
