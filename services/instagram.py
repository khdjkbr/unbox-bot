import os
import glob
import asyncio
import yt_dlp

def _download_instagram_sync(url: str) -> str:
    unique_id = os.urandom(6).hex()
    output_template = f"downloads/{unique_id}_%(id)s.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    downloaded_files = glob.glob(f"downloads/{unique_id}_*")
    if not downloaded_files:
        raise FileNotFoundError("Instagram video yuklanmadi.")
    return downloaded_files[0]

async def download_instagram(url: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_instagram_sync, url)
