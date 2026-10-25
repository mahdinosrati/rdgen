"""Turn a saved RDGen configuration into masked build environment variables."""
import base64
import json
import os
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rdgenerator.configuration import build_custom_config
from rdgenerator.network import normalize_network
from rdgenerator.naming import normalize_app_name


def prepare(data):
    if not isinstance(data, dict):
        raise ValueError('Configuration must be a JSON object')
    data = dict(data)
    if data.get('platform', 'windows') != 'windows':
        raise ValueError('Standalone build supports Windows 64-bit only')
    # Saved web forms use "on" for checked boxes; JSON callers may use booleans.
    booleans = ('delayFix xOffline hidecm removeNewVersionNotif denyLan enableDirectIP '
                'autoClose enableKeyboard enableClipboard enableFileTransfer enableAudio '
                'enableTCP enableRemoteRestart enableRecording enableBlockingInput '
                'enableRemoteModi removeWallpaper enablePrinter enableCamera enableTerminal').split()
    for field in booleans:
        if field in data:
            if data[field] not in (True, False, 'on', 'true', 'false', 'off', '', 0, 1):
                raise ValueError(f'Invalid boolean: {field}')
            data[field] = data[field] in (True, 'on', 'true', 1)
    # These fields are interpolated by the legacy branding shell steps.
    for field in ('appname', 'compname', 'exename', 'androidappid', 'urlLink', 'downloadLink', 'app_version'):
        value = data.get(field, '')
        if not isinstance(value, str) or re.search(r'[&\\|\'"$`\r\n<>]', value):
            raise ValueError(f'Unsupported characters in {field}')
    for field, choices in {
        'direction': ('both', 'incoming', 'outgoing'),
        'permissionsDorO': ('default', 'override'),
        'permissionsType': ('custom', 'full', 'view'),
        'theme': ('system', 'light', 'dark'),
        'themeDorO': ('default', 'override'),
    }.items():
        if field in data and data[field] not in choices:
            raise ValueError(f'Invalid {field}')
    app = normalize_app_name(data.get('appname'))
    data['appname'] = app
    if not app.isascii():
        raise ValueError('Application name must use ASCII characters')
    slug = re.sub(r'[-\s]+', '-', re.sub(r'[^\w\s-]', '', app.lower()).strip())
    filename = data.get('exename') or 'rustdesk'
    if not re.fullmatch(r'[A-Za-z0-9_-]+', filename) or not slug:
        raise ValueError('Filename must contain only English letters, numbers, underscores or hyphens')
    network = normalize_network(data)
    config = build_custom_config(data)
    env = {k: v for k, v in network.items() if k != 'endpoint'}
    env.update({
        'custom': base64.b64encode(json.dumps(config).encode()).decode(),
        'uuid': str(uuid.uuid4()), 'rdgen': 'standalone', 'genurl': '',
        'appname': app, 'slug_appname': slug, 'filename': filename,
        'compname': data.get('compname') or 'Purslane Ltd',
        'androidappid': data.get('androidappid') or 'com.carriez.flutter_hbb',
        'urlLink': data.get('urlLink') or 'https://rustdesk.com',
        'downloadLink': data.get('downloadLink') or 'https://rustdesk.com/download',
        'update_public_key': '',
    })
    for field in ('delayFix', 'xOffline', 'removeNewVersionNotif'):
        env[field] = 'true' if data.get(field, field == 'delayFix') else 'false'
    for kind in ('icon', 'logo', 'privacy'):
        value = data.get(kind + 'file') or data.get(kind + 'base64')
        if value:
            if not isinstance(value, str) or not value.startswith('data:image/png;base64,'):
                raise ValueError(f'{kind} must be a PNG data URL')
            image = base64.b64decode(value.split(',', 1)[1], validate=True)
            if not image.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError(f'Invalid PNG: {kind}')
            folder = Path(os.environ['RUNNER_TEMP']) / 'rdgen-images'
            folder.mkdir(exist_ok=True)
            (folder / (kind + '.png')).write_bytes(image)
            env[kind + 'link_url'] = 'local'
        else:
            env[kind + 'link_url'] = 'false'
        env[kind + 'link_uuid'] = 'false'
        env[kind + 'link_file'] = kind + '.png'
    return env


def export_env(env):
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as output:
        for key, value in env.items():
            if '\n' in value or '\r' in value:
                raise ValueError(f'Multiline environment value: {key}')
            if value:
                print('::add-mask::' + value.replace('%', '%25'))
            output.write(f'{key}={value}\n')
    print('Configuration validated and loaded.')


if __name__ == '__main__':
    export_env(prepare(json.loads(os.environ['RDGEN_CONFIG'])))
