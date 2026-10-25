"""Keep Windows client/service naming compatible with upstream installation."""
import re

def normalize_app_name(value, platform='windows'):
    value = value or 'rustdesk'
    if platform in ('windows', 'windows-x86'):
        value = re.sub(r'\s+', '', value).replace('_', '-')
        if not re.fullmatch(r'[A-Za-z0-9-]+', value):
            raise ValueError('Windows application name must contain English letters, numbers or hyphens.')
    return value
