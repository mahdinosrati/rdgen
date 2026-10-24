"""Render the existing Django form as a GitHub Pages configuration editor."""
import os
import hashlib
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rdgen.settings')
import django
django.setup()
from django.template.loader import render_to_string
from rdgenerator.forms import GenerateForm

target = ROOT / 'dist'
target.mkdir(exist_ok=True)
form = GenerateForm(initial={'exename': 'rustdesk'})
html = render_to_string('generator.html', {'form': form})
panel = (ROOT / 'web/panel.html').read_text(encoding='utf-8')
html = html.replace('</h1>', '</h1>' + panel, 1)
html = html.replace('action="/generator"', 'action="#"')
html = html.replace('<button type="submit">', '<p id="generate-status" role="status" aria-live="polite" dir="auto"></p><button type="submit">')
html = html.replace('https://github.com/bryangerlach/rdgen', 'https://github.com/mahdinosrati/rdgen')
css_version = hashlib.sha256((ROOT / 'web/pages.css').read_bytes()).hexdigest()[:12]
js_version = hashlib.sha256((ROOT / 'web/pages.js').read_bytes()).hexdigest()[:12]
html = html.replace('</head>', f'<link rel="stylesheet" href="pages.css?v={css_version}"></head>')
html = html.replace('</body>', f'<script src="pages.js?v={js_version}"></script></body>')
(target / 'index.html').write_text(html, encoding='utf-8')
(target / '.nojekyll').touch()
for name in ('pages.js', 'pages.css', 'build-key.json'):
    shutil.copyfile(ROOT / 'web' / name, target / name)
print('Static site built in dist/')
