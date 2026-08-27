import os
import glob
import asyncio
import logging
import aiohttp
from config import RAPIDAPI_KEY
import yt_dlp

# --- 1-USUL: RapidAPI orqali Stories va postlarni yuklash ---
async def _download_instagram_rapidapi(url: str) -> str:
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY mavjud emas")

    endpoint = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "social-download-all-in-one.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    payload = {"url": url}
    os.makedirs("downloads", exist_ok=True)

    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json=payload, headers=headers, timeout=15) as resp:
            if resp.status == 200:
                data = await resp.json()
                medias = data.get("medias", [])
                media_url = None
                is_image = False
                
                for m in medias:
                    if m.get("type") in ["video", "image"] or "mp4" in m.get("extension", "").lower():
                        media_url = m.get("url")
                        is_image = (m.get("type") == "image")
                        break
                
                if not media_url and "url" in data:
                    media_url = data["url"]

                if media_url:
                    ext = "jpg" if is_image else "mp4"
                    temp_path = f"downloads/ig_story_{os.urandom(6).hex()}.{ext}"
                    async with session.get(media_url, timeout=40) as v_resp:
                        if v_resp.status == 200:
                            with open(temp_path, "wb") as f:
                                while True:
                                    chunk = await v_resp.content.read(1024 * 64)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                            return temp_path
    raise Exception("RapidAPI orqali Instagram yuklab bo'lmadi")

# --- 2-USUL: yt-dlp orqali yuklash ---
def _download_instagram_ytdlp(url: str) -> str:
    unique_id = os.urandom(6).hex()
    output_template = f"downloads/ig_{unique_id}_%(id)s.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
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
    
    downloaded_files = glob.glob(f"downloads/ig_{unique_id}_*")
    if not downloaded_files:
        raise FileNotFoundError("Instagram media yuklanmadi.")
    return downloaded_files[0]

async def download_instagram(url: str) -> str:
    # 1. Agar Stories bo'lsa yoki RapidAPI bor bo'lsa — avval API orqali sinab ko'ramiz
    if "/stories/" in url or RAPIDAPI_KEY:
        try:
            return await _download_instagram_rapidapi(url)
        except Exception as e:
            logging.warning(f"Instagram Stories API xatolik: {e}")

    # 2. Zaxira: yt-dlp
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_instagram_ytdlp, url)
