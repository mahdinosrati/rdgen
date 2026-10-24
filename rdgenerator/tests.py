import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch, Mock
from django.test import SimpleTestCase, TestCase, override_settings
import pyzipper
from .configuration import build_custom_config
from .network import normalize_network
from .api_views import validate_generate_params
from .views import generate_custom_client

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / '.github/scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NetworkTests(SimpleTestCase):
    def test_network_all_directions_modes_platforms(self):
        for direction in ('incoming', 'outgoing', 'both'):
            for mode in ('default', 'override'):
                for platform in ('windows', 'windows-x86', 'macos', 'linux', 'android'):
                    with self.subTest(direction=direction, mode=mode, platform=platform):
                        config = build_custom_config({
                            'direction': direction, 'permissionsDorO': mode, 'platform': platform,
                            'serverIP': 'desk.example.org', 'serverPort': '30116',
                            'key': 'abc123=', 'apiServer': 'https://api.example.org/',
                        })
                        self.assertEqual(config['override-settings']['custom-rendezvous-server'], 'desk.example.org:30116')
                        self.assertEqual(config['override-settings']['key'], 'abc123=')
                        self.assertEqual(config['override-settings']['api-server'], 'https://api.example.org')
                        if direction == 'both':
                            self.assertNotIn('conn-type', config)

    def test_ipv6_and_api(self):
        network = normalize_network({'serverIP': '2001:db8::1', 'apiServer': 'example.org:21114'})
        self.assertEqual(network['endpoint'], '[2001:db8::1]:21116')
        self.assertEqual(network['apiServer'], 'http://example.org:21114')
        self.assertEqual(network['key'], '')

    def test_invalid_network_rejected(self):
        for values in ({'serverPort': '65533'}, {'serverPort': '-1'}, {'serverPort': 'abc'},
                       {'serverIP': 'https://example.org'}, {'apiServer': 'javascript:alert(1)'}, {'key': 'bad\nkey'}):
            with self.subTest(values=values):
                _, errors = validate_generate_params({'exename': 'client', **values})
                self.assertIn('network', errors)

    def test_no_invented_api_for_oss(self):
        self.assertEqual(normalize_network({'serverIP': 'example.org'})['apiServer'], '')

    def test_lan_disconnect_and_manual_settings(self):
        config = build_custom_config({'denyLan': True, 'autoClose': True, 'serverIP': 'example.org',
            'overrideManual': 'custom-rendezvous-server=old.example.org\nrelay-server=relay.example.org:21117'})
        self.assertEqual(config['default-settings']['enable-lan-discovery'], 'N')
        self.assertEqual(config['default-settings']['allow-auto-disconnect'], 'Y')
        self.assertNotIn('enable-lan-discovery', config)
        self.assertEqual(config['override-settings']['custom-rendezvous-server'], 'example.org:21116')
        self.assertEqual(config['override-settings']['relay-server'], 'relay.example.org:21117')

    def test_serverless_uses_same_config(self):
        env = script('serverless_config').prepare({'exename': 'test-client', 'serverIP': 'example.org',
            'serverPort': '30000', 'denyLan': 'on', 'enableDirectIP': 'false'})
        config = json.loads(base64.b64decode(env['custom']))
        self.assertEqual(config['override-settings']['custom-rendezvous-server'], 'example.org:30000')
        self.assertEqual(config['default-settings']['enable-lan-discovery'], 'N')
        self.assertEqual(config['default-settings']['direct-server'], 'N')
        self.assertEqual(env['rdgen'], 'standalone')

    def test_patcher_fails_on_upstream_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'libs/hbb_common/src').mkdir(parents=True)
            (root / 'src').mkdir()
            (root / 'libs/hbb_common/src/config.rs').write_text('pub const CHANGED: i32 = 42;')
            (root / 'src/common.rs').write_text('"https://admin.rustdesk.com"')
            with self.assertRaises(RuntimeError):
                script('patch_network').patch(root, normalize_network({}))


@override_settings(GHUSER='test', REPONAME='rdgen', ZIP_PASSWORD='test-password', GHBEARER='test')
class DispatchTests(TestCase):
    def test_encrypted_network_payload_and_empty_204(self):
        response = Mock(status_code=204, content=b'')
        with tempfile.TemporaryDirectory() as folder:
            previous = os.getcwd()
            try:
                os.chdir(folder)
                with patch('rdgenerator.views.requests.post', return_value=response), patch('rdgenerator.views.save_png', return_value=('false', 'false', 'false')):
                    result = generate_custom_client({'exename': 'client', 'serverIP': 'desk.example.org', 'serverPort': '31000', 'key': 'abc='}, 'https://generator.example.org')
                self.assertTrue(result['success'])
                with pyzipper.AESZipFile(next(Path('temp_zips').glob('*.zip'))) as zf:
                    zf.setpassword(b'test-password')
                    payload = json.loads(zf.read('secrets.json'))
                custom = json.loads(base64.b64decode(payload['custom']))
                self.assertEqual(payload['serverPort'], '31000')
                self.assertEqual(custom['override-settings']['custom-rendezvous-server'], 'desk.example.org:31000')
                self.assertEqual(custom['override-settings']['key'], 'abc=')
            finally:
                os.chdir(previous)

class RelayTests(SimpleTestCase):
    def test_explicit_relay_overrides_manual(self):
        c = build_custom_config({'relayServer': 'relay.example.org:21117', 'overrideManual': 'relay-server=old.example.org:21117'})
        self.assertEqual(c['override-settings']['relay-server'], 'relay.example.org:21117')

    def test_blank_relay_preserves_manual(self):
        c = build_custom_config({'relayServer': '', 'overrideManual': 'relay-server=old.example.org:21117'})
        self.assertEqual(c['override-settings']['relay-server'], 'old.example.org:21117')

    def test_relay_validation(self):
        from .network import normalize_relay
        self.assertEqual(normalize_relay('[2001:db8::1]:21117'), '[2001:db8::1]:21117')
        for value in ('https://relay.example.org', 'relay.example.org:70000', 'user@relay.example.org', 'relay.example.org/path'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_relay(value)
