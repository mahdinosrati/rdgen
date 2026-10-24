"""Decrypt browser-uploaded configuration; never print its contents."""
import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from serverless_config import prepare, export_env


def decrypt(envelope, private_pem):
    if envelope.get('version') != 1:
        raise ValueError('Unsupported encrypted configuration version')
    key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    secret = key.decrypt(base64.b64decode(envelope['key'], validate=True),
                         padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    plaintext = AESGCM(secret).decrypt(base64.b64decode(envelope['iv'], validate=True),
                                      base64.b64decode(envelope['data'], validate=True), b'rdgen-config-v1')
    return json.loads(plaintext)


if __name__ == '__main__':
    pem = os.environ.get('RDGEN_PRIVATE_KEY', '')
    if not pem:
        raise ValueError('Repository RDGEN_PRIVATE_KEY secret is not configured')
    payload = Path(os.environ['RUNNER_TEMP']) / 'rdgen-encrypted-payload.json'
    try:
        data = decrypt(json.loads(payload.read_text(encoding='utf-8')), pem)
    finally:
        payload.unlink(missing_ok=True)
    export_env(prepare(data))
    print('Encrypted configuration authenticated, decrypted and validated.')
