import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class ReleaseSelectionTests(unittest.TestCase):
    def select(self, releases, attempts=None, retry=False):
        js = "const {selectRelease}=require('./.github/scripts/release_selection.cjs');const x=JSON.parse(process.argv[1]);process.stdout.write(JSON.stringify(selectRelease(x.releases,['1.5.0'],x.attempts,x.retry)||null));"
        result = subprocess.run(['node', '-e', js, json.dumps({'releases': releases, 'attempts': attempts or {}, 'retry': retry})], cwd=ROOT, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def release(self, tag, **kwargs):
        return dict(tag_name=tag, draft=False, prerelease=False, updated_at='stamp', **kwargs)

    def test_newest_stable_numeric_order(self):
        releases = [self.release('1.5.1'), self.release('1.10.0'), self.release('1.4.9'), dict(tag_name='nightly', prerelease=True), dict(tag_name='2.0.0', draft=True)]
        self.assertEqual(self.select(releases)['tag_name'], '1.10.0')

    def test_failed_release_waits_for_retry(self):
        attempts = {'1.5.1': {'release_updated': 'stamp', 'result': 'failure'}}
        self.assertIsNone(self.select([self.release('1.5.1')], attempts))
        self.assertEqual(self.select([self.release('1.5.1')], attempts, True)['tag_name'], '1.5.1')

    def test_current_release_not_rebuilt(self):
        self.assertIsNone(self.select([self.release('1.5.0')]))
