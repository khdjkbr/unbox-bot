import os
import re
import asyncio
import logging
import aiohttp
from config import RAPIDAPI_KEY
from services.instagram import _download_instagram_sync

def extract_youtube_id(url: str) -> str:
    patterns = [
        r'shorts\/([0-9A-Za-z_-]{11})',
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""

def get_browser_download_url(url: str) -> str:
    video_id = extract_youtube_id(url)
    if video_id:
        return f"https://ssyoutube.com/watch?v={video_id}"
    return f"https://10downloader.com/download?v={url}"

async def download_youtube_shorts(url: str) -> str:
    os.makedirs("downloads", exist_ok=True)
    temp_path = f"downloads/shorts_{os.urandom(6).hex()}.mp4"

    # 1. RapidAPI orqali yuklash
    if RAPIDAPI_KEY:
        try:
            endpoint = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
            headers = {
                "x-rapidapi-key": RAPIDAPI_KEY,
                "x-rapidapi-host": "social-download-all-in-one.p.rapidapi.com",
                "Content-Type": "application/json"
            }
            payload = {"url": url}
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        medias = data.get("medias", [])
                        video_url = None
                        for m in medias:
                            if m.get("type") == "video" or "mp4" in m.get("extension", "").lower():
                                video_url = m.get("url")
                                break
                        if not video_url and "url" in data:
                            video_url = data["url"]

                        if video_url:
                            async with session.get(video_url, timeout=40) as v_resp:
                                if v_resp.status == 200:
                                    with open(temp_path, "wb") as f:
                                        while True:
                                            chunk = await v_resp.content.read(1024 * 64)
                                            if not chunk:
                                                break
                                            f.write(chunk)
                                    return temp_path
        except Exception as e:
            logging.error(f"RapidAPI xatolik: {e}")

    # 2. Zaxira: yt-dlp
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_instagram_sync, url)
