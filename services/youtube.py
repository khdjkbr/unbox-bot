import os
import re
import glob
import asyncio
import logging
import aiohttp
from config import RAPIDAPI_KEY
import yt_dlp

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.jing.rocks",
    "https://vid.puffyan.us",
    "https://invidious.private.coffee"
]

# --- 100% aniq YouTube ID ajratuvchi ---
def extract_youtube_id(url: str) -> str:
    # 1. Shorts: youtube.com/shorts/VIDEO_ID
    m = re.search(r'shorts\/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    
    # 2. Qisqa havola: youtu.be/VIDEO_ID
    m = re.search(r'youtu\.be\/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
    
    # 3. Standart havola: watch?v=VIDEO_ID
    m = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
        
    # 4. Embed havola: embed/VIDEO_ID
    m = re.search(r'embed\/([a-zA-Z0-9_-]{11})', url)
    if m:
        return m.group(1)
        
    return ""

# --- Brauzerda 100% ochiladigan havola ---
def get_browser_download_url(url: str) -> str:
    video_id = extract_youtube_id(url)
    if video_id:
        return f"https://10downloader.com/download?v=https://www.youtube.com/watch?v={video_id}"
    return f"https://10downloader.com/download?v={url}"

# --- 1-USUL: RapidAPI orqali yuklash ---
async def try_rapidapi(url: str) -> str:
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY mavjud emas")
    
    endpoint = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "social-download-all-in-one.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    payload = {"url": url}
    temp_path = f"downloads/yt_rapid_{os.urandom(6).hex()}.mp4"

    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json=payload, headers=headers, timeout=12) as resp:
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
    raise Exception("RapidAPI orqali yuklab bo'lmadi")

# --- 2-USUL: Invidious API orqali yuklash ---
async def try_invidious(url: str) -> str:
    video_id = extract_youtube_id(url)
    if not video_id:
        raise ValueError("Video ID topilmadi")
    
    temp_path = f"downloads/yt_inv_{os.urandom(6).hex()}.mp4"
    for instance in INVIDIOUS_INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=6) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        streams = data.get("formatStreams", [])
                        video_stream_url = None
                        for s in streams:
                            if "mp4" in s.get("type", "").lower() or "video" in s.get("type", "").lower():
                                video_stream_url = s.get("url")
                                break
                        
                        if video_stream_url:
                            async with session.get(video_stream_url, timeout=35) as v_resp:
                                if v_resp.status == 200:
                                    with open(temp_path, "wb") as f:
                                        while True:
                                            chunk = await v_resp.content.read(1024 * 64)
                                            if not chunk:
                                                break
                                            f.write(chunk)
                                    return temp_path
        except Exception as e:
            logging.warning(f"Invidious {instance} xatolik: {e}")
            continue
    raise Exception("Invidious orqali yuklab bo'lmadi")

# --- 3-USUL: yt-dlp orqali yuklash ---
def _try_ytdlp_sync(url: str, res: str = "720") -> str:
    unique_id = os.urandom(6).hex()
    output_template = f"downloads/yt_dlp_{unique_id}_%(id)s.%(ext)s"
    
    ydl_opts = {
        'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best',
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
    
    downloaded_files = glob.glob(f"downloads/yt_dlp_{unique_id}_*")
    if not downloaded_files:
        raise FileNotFoundError("yt-dlp orqali fayl topilmadi.")
    return downloaded_files[0]

async def try_ytdlp(url: str, res: str = "720") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _try_ytdlp_sync, url, res)

# --- BOSQICHMA-BOSQICH KASKAD YUKLOVCHI ---
async def cascade_download_youtube(url: str, res: str = "720") -> str:
    os.makedirs("downloads", exist_ok=True)

    # 1-qadam: RapidAPI
    try:
        logging.info("1-bosqich: RapidAPI orqali yuklanmoqda...")
        return await try_rapidapi(url)
    except Exception as e:
        logging.warning(f"1-bosqich xatolik: {e}")

    # 2-qadam: Invidious
    try:
        logging.info("2-bosqich: Invidious API orqali yuklanmoqda...")
        return await try_invidious(url)
    except Exception as e:
        logging.warning(f"2-bosqich xatolik: {e}")

    # 3-qadam: yt-dlp
    try:
        logging.info("3-bosqich: yt-dlp orqali yuklanmoqda...")
        return await try_ytdlp(url, res)
    except Exception as e:
        logging.warning(f"3-bosqich xatolik: {e}")

    raise RuntimeError("Barcha server yuklash usullari muvaffaqiyatsiz tugadi.")
