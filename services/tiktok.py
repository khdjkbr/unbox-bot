import os
import re
import glob
import asyncio
import logging
import aiohttp
import yt_dlp

# --- 1-USUL: TikWM API orqali yuklash ---
async def _download_tikwm(url: str) -> str:
    os.makedirs("downloads", exist_ok=True)
    temp_path = f"downloads/tiktok_{os.urandom(6).hex()}.mp4"
    
    clean_url = re.search(r'https?://[^\s]+', url).group(0)
    api_url = f"https://www.tikwm.com/api/?url={clean_url}&hd=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=headers, timeout=12) as resp:
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
                                with open(temp_path, "wb") as f:
                                    while True:
                                        chunk = await v_resp.content.read(1024 * 64)
                                        if not chunk:
                                            break
                                        f.write(chunk)
                                return temp_path
    raise Exception("TikWM orqali yuklab bo'lmadi")

# --- 2-USUL: Tiklydown API orqali yuklash ---
async def _download_tiklydown(url: str) -> str:
    os.makedirs("downloads", exist_ok=True)
    temp_path = f"downloads/tiktok_{os.urandom(6).hex()}.mp4"
    
    clean_url = re.search(r'https?://[^\s]+', url).group(0)
    api_url = f"https://api.tiklydown.eu.org/api/download?url={clean_url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=headers, timeout=12) as resp:
            if resp.status == 200:
                result = await resp.json()
                video_url = result.get("video", {}).get("noWatermark") or result.get("video", {}).get("watermark")
                if video_url:
                    async with session.get(video_url, headers=headers, timeout=35) as v_resp:
                        if v_resp.status == 200:
                            with open(temp_path, "wb") as f:
                                while True:
                                    chunk = await v_resp.content.read(1024 * 64)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                            return temp_path
    raise Exception("Tiklydown orqali yuklab bo'lmadi")

# --- 3-USUL: yt-dlp zaxira ---
def _download_ytdlp_sync(url: str) -> str:
    unique_id = os.urandom(6).hex()
    output_template = f"downloads/tt_ytdlp_{unique_id}_%(id)s.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'format': 'best',
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
    
    downloaded_files = glob.glob(f"downloads/tt_ytdlp_{unique_id}_*")
    if not downloaded_files:
        raise FileNotFoundError("TikTok video yuklanmadi.")
    return downloaded_files[0]

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
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_ytdlp_sync, url)
