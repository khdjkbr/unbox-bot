from services.http_download import save_response
import os
import logging
import aiohttp
from config import RAPIDAPI_KEY
from services.downloader import download_media

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
            if resp.status != 200:
                raise RuntimeError(f"Instagram RapidAPI HTTP {resp.status}; check API subscription, quota and key")
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
                        if v_resp.status != 200:
                            raise RuntimeError(f"Instagram media HTTP {v_resp.status}")
                        if v_resp.status == 200:
                            return await save_response(v_resp, temp_path)
    raise Exception("RapidAPI orqali Instagram yuklab bo'lmadi")

async def download_instagram(url: str) -> str:
    # 1. Agar RapidAPI kaliti bo'lsa — avval API orqali sinab ko'ramiz
    if RAPIDAPI_KEY:
        try:
            return await _download_instagram_rapidapi(url)
        except Exception as e:
            logging.warning(f"Instagram RapidAPI xatolik: {e}")

    # 2. Zaxira: yt-dlp
    return await download_media(url)
