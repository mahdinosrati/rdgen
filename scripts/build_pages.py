"""Render the existing Django form as a GitHub Pages configuration editor."""
import os
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
html = html.replace('https://github.com/bryangerlach/rdgen', 'https://github.com/mahdinosrati/rdgen')
html = html.replace('</head>', '<link rel="stylesheet" href="pages.css"></head>')
html = html.replace('</body>', '<script src="pages.js"></script></body>')
(target / 'index.html').write_text(html, encoding='utf-8')
(target / '.nojekyll').touch()
for name in ('pages.js', 'pages.css'):
    shutil.copyfile(ROOT / 'web' / name, target / name)
print('Static site built in dist/')
