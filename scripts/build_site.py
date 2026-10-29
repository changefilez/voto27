"""Stage only public assets for GitHub Pages (no repository or scripts)."""
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir()
for name in ['index.html', '404.html', 'manifest.webmanifest', 'sw.js', 'robots.txt', 'sitemap.xml']:
    shutil.copy2(ROOT / name, OUT / name)
for name in ['assets', 'icons', 'data']:
    shutil.copytree(ROOT / name, OUT / name)
(OUT / '.nojekyll').touch()
print('Public site staged in _site/')
