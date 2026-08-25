import re

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

# --- SaveFrom (ssyoutube) orqali to'g'ridan-to'g'ri yuklash havolasi ---
def get_browser_download_url(url: str) -> str:
    video_id = extract_youtube_id(url)
    if video_id:
        return f"https://ssyoutube.com/watch?v={video_id}"
    return f"https://en.savefrom.net/1-youtube-video-downloader-22wW/?url={url}"
