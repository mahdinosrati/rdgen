"""Network settings shared by the web service and serverless builds."""
import ipaddress
import re
from urllib.parse import urlsplit

DEFAULT_SERVER = 'rs-ny.rustdesk.com'
DEFAULT_KEY = 'OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw='


def normalize_network(params):
    host = str(params.get('serverIP') or DEFAULT_SERVER).strip()
    try:
        ipaddress.ip_address(host.strip('[]'))
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host):
            raise ValueError('Host must be a hostname or IP address, without a scheme or port.')
    host = host.strip('[]')
    port_text = str(params.get('serverPort') or '21116').strip()
    if not port_text.isascii() or not port_text.isdigit() or not 1 <= int(port_text) <= 65532:
        raise ValueError('Port must be between 1 and 65532 (three following ports are reserved).')
    port = str(int(port_text))
    endpoint_host = f'[{host}]' if ':' in host else host
    api = str(params.get('apiServer') or '').strip()
    if api:
        if '://' not in api:
            api = 'http://' + api
        parsed = urlsplit(api)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username or parsed.password or parsed.fragment
                or any(c in api for c in '\r\n\"\'`$\\|<> ')):
            raise ValueError('API server must be an HTTP(S) URL without credentials.')
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError('Invalid API server port.') from exc
        api = api.rstrip('/')
    key = str(params.get('key') or '').strip()
    if not key and host == DEFAULT_SERVER:
        key = DEFAULT_KEY
    if key and not re.fullmatch(r'[A-Za-z0-9+/=_-]+', key):
        raise ValueError('Invalid server public key.')
    return {'server': host, 'serverPort': port, 'key': key, 'apiServer': api,
            'endpoint': f'{endpoint_host}:{port}'}


def apply_network_settings(config, params):
    network = normalize_network(params)
    # Network must not depend on connection direction or permission mode.
    # Overrides also replace stale settings from a previously installed client.
    config['override-settings'].update({
        'custom-rendezvous-server': network['endpoint'],
        'key': network['key'],
        'api-server': network['apiServer'],
    })
    return network
