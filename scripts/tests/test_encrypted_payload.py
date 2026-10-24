import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.github/scripts'))
from decrypt_payload import decrypt


class EncryptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        numbers = key.public_key().public_numbers()
        def enc(n):
            return base64.urlsafe_b64encode(n.to_bytes((n.bit_length() + 7) // 8, 'big')).rstrip(b'=').decode()
        cls.jwk = {'kty': 'RSA', 'n': enc(numbers.n), 'e': enc(numbers.e), 'alg': 'RSA-OAEP-256', 'ext': True}

    def encrypt_in_javascript(self, config):
        source = (ROOT / 'web/pages.js').read_text(encoding='utf-8')
        functions = source[source.index('function toBase64'):source.index('function networkPreview')]
        javascript = """
const fs = require('fs');
const crypto = require('crypto').webcrypto;
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const fetch = async () => ({ok: true, json: async () => input.key});
""" + functions + "\nencryptConfig(JSON.stringify(input.config)).then(x => process.stdout.write(JSON.stringify(x)));"
        result = subprocess.run(['node', '-e', javascript], input=json.dumps({'key': self.jwk, 'config': config}), capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_browser_to_python_large_config(self):
        data = {'serverIP': 'test.invalid', 'permanentPassword': 'synthetic-test-only',
                'iconfile': 'data:image/png;base64,' + 'a' * 7100000}
        envelope = self.encrypt_in_javascript(data)
        self.assertEqual(decrypt(envelope, self.pem), data)
        self.assertNotIn('synthetic-test-only', json.dumps(envelope))

    def test_tampering_is_rejected(self):
        envelope = self.encrypt_in_javascript({'serverIP': 'test.invalid'})
        ciphertext = bytearray(base64.b64decode(envelope['data']))
        ciphertext[0] ^= 1
        envelope['data'] = base64.b64encode(ciphertext).decode()
        with self.assertRaises(InvalidTag):
            decrypt(envelope, self.pem)

