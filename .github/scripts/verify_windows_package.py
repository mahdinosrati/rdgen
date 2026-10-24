"""Verify the actual portable EXE payload without executing the client.

RustDesk's portable packer embeds a 'rustdesk' blob with length-prefixed paths,
Brotli-compressed file contents and MD5 checksums. Inspecting that blob catches
packaging regressions that a successful compiler or upload step cannot catch.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

import brotli

MARKER = b'rustdesk'


def packaged_files(binary):
    start = 0
    while True:
        start = binary.find(MARKER, start)
        if start < 0:
            raise ValueError('No complete RustDesk portable payload found')
        cursor = start + len(MARKER)
        start = cursor
        files = {}
        try:
            for _ in range(10000):
                if binary[cursor:cursor + 8] == MARKER:
                    if any(name.endswith('.exe') for name in files) and 'custom_.txt' in files:
                        return files
                    break
                length = struct.unpack_from('>I', binary, cursor)[0]
                cursor += 4
                if not 1 <= length <= 4096:
                    break
                name = binary[cursor:cursor + length].decode('utf-8').replace('\\', '/').removeprefix('./')
                if '\x00' in name or name.startswith('/') or '..' in name.split('/'):
                    break
                cursor += length
                size = struct.unpack_from('>I', binary, cursor)[0]
                cursor += 4
                if cursor + size + 32 > len(binary):
                    break
                compressed = binary[cursor:cursor + size]
                cursor += size
                checksum = binary[cursor:cursor + 32].decode('ascii')
                cursor += 32
                files[name] = (compressed, checksum)
        except (UnicodeError, struct.error):
            continue


def unpack_entry(entry):
    compressed, expected_md5 = entry
    data = brotli.decompress(compressed)
    if hashlib.md5(data).hexdigest() != expected_md5:
        raise ValueError('Portable payload checksum mismatch')
    return data


def verify(path, expected_config):
    files = packaged_files(Path(path).read_bytes())
    config = json.loads(base64.b64decode(unpack_entry(files['custom_.txt']), validate=True))
    if config != expected_config:
        raise ValueError('Packaged custom_.txt differs from the requested configuration')
    # The embedded executable must load the same file that we ship beside it.
    client = next(name for name in files if '/' not in name and name.endswith('.exe'))
    if b'custom_.txt' not in unpack_entry(files[client]):
        raise ValueError('Packaged client does not reference custom_.txt')
    return {'filename': Path(path).name, 'embedded_files': len(files),
            'configuration_matches': True, 'loader_matches': True,
            'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest()}


if __name__ == '__main__':
    expected = json.loads(base64.b64decode(os.environ['custom'], validate=True))
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else 'SignOutput')
    executables = list(folder.glob('*.exe'))
    if not executables:
        raise ValueError('No portable Windows executable to verify')
    reports = [verify(path, expected) for path in executables]
    # The report intentionally contains no host, key, password or configuration.
    (folder / 'verification.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
    print('Verified packaged configuration, checksum and custom configuration loader.')
