"""Patch RustDesk network constants and fail if upstream no longer matches."""
import json
import os
from pathlib import Path
import re


def patch(root, env):
    root = Path(root)
    port = int(env['serverPort'])
    if not 1 <= port <= 65532:
        raise ValueError('Invalid rendezvous port')
    config_path = root / 'libs/hbb_common/src/config.rs'
    common_path = root / 'src/common.rs'
    config = config_path.read_text(encoding='utf-8')
    common = common_path.read_text(encoding='utf-8')
    values = {
        'RENDEZVOUS_SERVERS': '&[' + json.dumps(env['server']) + ']',
        'RS_PUB_KEY': json.dumps(env['key']),
        'RENDEZVOUS_PORT': str(port),
        'RELAY_PORT': str(port + 1),
        'WS_RENDEZVOUS_PORT': str(port + 2),
        'WS_RELAY_PORT': str(port + 3),
    }
    for name, value in values.items():
        pattern = rf'(pub const {name}: [^=]+ = )[^;]+;'
        config, count = re.subn(pattern, lambda m: m[1] + value + ';', config)
        if count != 1:
            raise RuntimeError(f'Expected one {name} declaration, found {count}')
    api_literal = '"https://admin.rustdesk.com"'
    if api_literal not in common:
        raise RuntimeError('Upstream API server default changed; refusing an unconfigured build')
    common = common.replace(api_literal, json.dumps(env['apiServer']))
    config_path.write_text(config, encoding='utf-8')
    common_path.write_text(common, encoding='utf-8')
    print('Verified and applied all network constants.')


if __name__ == '__main__':
    patch('.', os.environ)
