import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import yt_dlp
from yt_dlp.postprocessor import PostProcessor


class CaptureFile(PostProcessor):
    def __init__(self):
        super().__init__()
        self.paths = []

    def run(self, info):
        self.paths.append(info['filepath'])
        return [], info


def download_sync(url: str) -> str:
    os.makedirs('downloads', exist_ok=True)
    folder = tempfile.mkdtemp(prefix='media_', dir='downloads')
    capture = CaptureFile()
    options = {
        'format': 'best[ext=mp4][height<=720]/bestvideo[height<=720]+bestaudio/best',
        'outtmpl': os.path.join(folder, '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'playlistend': 1,
        'socket_timeout': 20,
        'retries': 2,
        'fragment_retries': 2,
        'max_filesize': 50 * 1024 * 1024,
        'js_runtimes': {'node': {}},
        'quiet': True,
    }
    if os.getenv('YTDLP_COOKIES_FILE'):
        # yt-dlp writes its cookie jar on exit; Render secrets may be read-only.
        cookie_source = os.environ['YTDLP_COOKIES_FILE']
        options['cookiefile'] = os.path.join(folder, 'cookies.txt')
    try:
        if os.getenv('YTDLP_COOKIES_FILE'):
            shutil.copyfile(cookie_source, options['cookiefile'])
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.add_post_processor(capture, when='after_move')
            downloader.download([url])
        for filename in capture.paths:
            path = Path(filename)
            if path.is_file() and path.stat().st_size:
                result = Path('downloads') / (Path(folder).name + path.suffix)
                shutil.move(str(path), result)
                return str(result)
        raise FileNotFoundError('No complete media file downloaded (possibly too large).')
    finally:
        shutil.rmtree(folder)


async def download_media(url: str) -> str:
    return await asyncio.to_thread(download_sync, url)
