from services.http_download import save_response
import os
import re
import logging
import aiohttp
from services.downloader import download_media

# --- 1-USUL: TikWM API orqali yuklash ---
async def _download_tikwm(url: str) -> str:
    os.makedirs("downloads", exist_ok=True)
    temp_path = f"downloads/tiktok_{os.urandom(6).hex()}.mp4"
    
    clean_url = re.search(r'https?://[^\s]+', url).group(0)
    api_url = "https://www.tikwm.com/api/"
    params = {"url": clean_url, "hd": "1"}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params, headers=headers, timeout=12) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("code") == 0:
                    data = result.get("data", {})
                    video_url = data.get("hdplay") or data.get("play") or data.get("wmplay")
                    if video_url:
                        if video_url.startswith("/"):
                            video_url = f"https://www.tikwm.com{video_url}"
                        
                        async with session.get(video_url, headers=headers, timeout=35) as v_resp:
                            if v_resp.status == 200:
                                return await save_response(v_resp, temp_path)
    raise Exception("TikWM orqali yuklab bo'lmadi")

# --- 2-USUL: Tiklydown API orqali yuklash ---
async def _download_tiklydown(url: str) -> str:
    os.makedirs("downloads", exist_ok=True)
    temp_path = f"downloads/tiktok_{os.urandom(6).hex()}.mp4"
    
    clean_url = re.search(r'https?://[^\s]+', url).group(0)
    api_url = "https://api.tiklydown.eu.org/api/download"
    params = {"url": clean_url}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params, headers=headers, timeout=12) as resp:
            if resp.status == 200:
                result = await resp.json()
                video_url = result.get("video", {}).get("noWatermark") or result.get("video", {}).get("watermark")
                if video_url:
                    async with session.get(video_url, headers=headers, timeout=35) as v_resp:
                        if v_resp.status == 200:
                            return await save_response(v_resp, temp_path)
    raise Exception("Tiklydown orqali yuklab bo'lmadi")

async def download_tiktok(url: str) -> str:
    # 1. TikWM
    try:
        return await _download_tikwm(url)
    except Exception as e:
        logging.warning(f"TikWM xatolik: {e}")

    # 2. Tiklydown
    try:
        return await _download_tiklydown(url)
    except Exception as e:
        logging.warning(f"Tiklydown xatolik: {e}")

    # 3. yt-dlp
    return await download_media(url)
