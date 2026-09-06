import re
from urllib.parse import urlsplit

DOMAINS = {
    'instagram.com': 'instagram', 'tiktok.com': 'tiktok',
    'youtube.com': 'youtube', 'youtu.be': 'youtube',
    'facebook.com': 'facebook', 'fb.watch': 'facebook',
    'twitter.com': 'twitter', 'x.com': 'twitter',
}


def extract_link(content):
    for match in re.finditer(r'https?://[^\s<>]+', content, re.IGNORECASE):
        url = match.group().rstrip('.,!?;:)\'"')
        try:
            host = (urlsplit(url).hostname or '').lower()
        except ValueError:
            continue
        for domain, platform in DOMAINS.items():
            if host == domain or host.endswith('.' + domain):
                return url, platform
    return None
