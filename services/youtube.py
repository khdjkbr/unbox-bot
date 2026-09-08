import asyncio
import logging
import os
import time
from uuid import uuid4
from urllib.parse import urlsplit
import aiohttp
from services.downloader import download_media
from services.http_download import save_response

_lock = asyncio.Lock()
_next_request = 0.0
_blocked_until = 0.0

async def _request(session, endpoint, params, key):
    global _next_request, _blocked_until
    async with _lock:
        now = time.monotonic()
        if now < _blocked_until:
            raise RuntimeError('Yoinku quota cooldown')
        await asyncio.sleep(max(0, _next_request - now))
        _next_request = time.monotonic() + 13
        async with session.get('https://yoinku.com/api/v1' + endpoint, params=params,
                               headers={'x-api-key': key}, allow_redirects=False) as response:
            if response.status == 429:
                try:
                    delay = max(60, float(response.headers.get('Retry-After', '3600')))
                except ValueError:
                    delay = 3600
                _blocked_until = time.monotonic() + delay
                raise RuntimeError('Yoinku quota exceeded')
            if response.status != 200:
                raise RuntimeError(f'Yoinku HTTP {response.status}')
            data = await response.json()
            if data.get('ok') is not True:
                raise RuntimeError('Yoinku request failed')
            return data

def _format(info):
    formats = [f for f in info.get('data', {}).get('formats', [])
               if f.get('container') == 'mp4' and f.get('hasVideo')
               and f.get('hasAudio') and 0 < (f.get('height') or 0) <= 720]
    if not formats:
        raise RuntimeError('No MP4 format with audio available')
    return max(formats, key=lambda f: f['height'])['id']

async def _yoinku(url, key):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=180)) as session:
        info = await _request(session, '/info', {'url': url}, key)
        result = await _request(session, '/download',
                                {'url': url, 'format': _format(info)}, key)
        media_url = result.get('url', '')
        parsed = urlsplit(media_url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username:
            raise RuntimeError('Invalid Yoinku download URL')
        os.makedirs('downloads', exist_ok=True)
        path = f'downloads/youtube_{uuid4().hex}.mp4'
        # Do not forward API credentials to the file host.
        async with session.get(media_url) as response:
            if response.content_length and response.content_length > 50 * 1024 * 1024:
                raise ValueError('Media exceeds 50 MB')
            return await save_response(response, path)

async def download_youtube(url):
    try:
        return await download_media(url)
    except Exception:
        logging.warning('YouTube direct download failed; checking fallback')
        key = os.getenv('YOINKU_API_KEY')
        if not key:
            logging.warning('YouTube fallback disabled: YOINKU_API_KEY missing')
            raise
    return await _yoinku(url, key)
