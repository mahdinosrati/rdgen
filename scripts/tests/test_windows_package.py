import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import brotli

spec = importlib.util.spec_from_file_location('verifier', Path(__file__).resolve().parents[2] / '.github/scripts/verify_windows_package.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def payload(config, loader=b'client uses custom_.txt', corrupt=False):
    result = b'MZ stub rustdesk unrelated bytes\x00rustdesk'
    for name, data in ((b'./custom_.txt', base64.b64encode(json.dumps(config).encode())), (b'./client.exe', loader)):
        compressed = brotli.compress(data)
        digest = b'0' * 32 if corrupt else hashlib.md5(data).hexdigest().encode()
        result += len(name).to_bytes(4, 'big') + name + len(compressed).to_bytes(4, 'big') + compressed + digest
    return result + b'rustdesk./client.exe'


class PackageTests(unittest.TestCase):
    def check(self, blob, expected):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'client.exe'
            path.write_bytes(blob)
            return verifier.verify(path, expected)

    def test_config_and_loader_match(self):
        config = {'override-settings': {'custom-rendezvous-server': 'example.org:30116'}}
        self.assertTrue(self.check(payload(config), config)['configuration_matches'])

    def test_wrong_config_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.check(payload({'key': 'wrong'}), {'key': 'expected'})

    def test_unpatched_loader_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not reference'):
            self.check(payload({}, loader=b'client uses custom.txt'), {})

    def test_corrupt_data_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.check(payload({}, corrupt=True), {})

    def test_truncated_blob_is_rejected(self):
        with self.assertRaises(ValueError):
            self.check(payload({})[:-24], {})


if __name__ == '__main__':
    unittest.main()
