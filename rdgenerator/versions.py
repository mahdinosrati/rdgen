"""Only successful release builds are offered by the form."""
import json
from pathlib import Path

def stable_versions():
    return json.loads(Path(__file__).with_name('supported_versions.json').read_text())['stable']

def version_choices():
    return [(v, v) for v in stable_versions()] + [('master', 'nightly')]
