from services.http_download import save_response
import os
import logging
import aiohttp
import re
from config import RAPIDAPI_KEY, RAPIDAPI_FALLBACK_KEY
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


async def _download_instagram_looter(url: str) -> str:
    """Fallback API. It returns metadata; recursively find the first media URL."""
    if not RAPIDAPI_FALLBACK_KEY:
        raise ValueError("RAPIDAPI_FALLBACK_KEY mavjud emas")
    endpoint = "https://instagram-looter2.p.rapidapi.com/post"
    headers = {"x-rapidapi-key": RAPIDAPI_FALLBACK_KEY,
               "x-rapidapi-host": "instagram-looter2.p.rapidapi.com"}
    shortcode = (re.search(r"/(?:reel|p|tv)/([^/?#]+)", url) or [None, None])[1]
    attempts = [{"url": url}]
    if shortcode:
        attempts.append({"shortcode": shortcode})
    data = None
    async with aiohttp.ClientSession() as session:
        for params in attempts:
            logging.info("Instagram Looter запрос: params=%s", list(params))
            async with session.get(endpoint, params=params, headers=headers, timeout=20) as resp:
                body = await resp.text()
                logging.info("Instagram Looter ответ: HTTP %s, %s байт", resp.status, len(body))
                if resp.status == 200:
                    try:
                        data = await resp.json(content_type=None)
                    except Exception as exc:
                        logging.warning("Instagram Looter вернул не-JSON: %s", exc)
                    if data:
                        break
                elif resp.status not in (400, 404):
                    raise RuntimeError(f"Instagram Looter HTTP {resp.status}")
    if data is None:
        raise RuntimeError("Instagram Looter не вернул данные")
    media_url = _find_media_url(data)
    if not media_url:
        raise RuntimeError("Instagram Looter не вернул ссылку на media")
    ext = ".jpg" if any(x in media_url.lower() for x in (".jpg", ".jpeg", ".png", ".webp")) else ".mp4"
    path = f"downloads/ig_looter_{os.urandom(6).hex()}{ext}"
    async with aiohttp.ClientSession() as session:
        async with session.get(media_url, timeout=40) as resp:
            return await save_response(resp, path)


def _find_media_url(value):
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        low = value.lower()
        if any(x in low for x in (".mp4", ".m3u8", ".jpg", ".jpeg", ".png", ".webp")):
            return value
        # Instagram CDN media URLs commonly omit a file extension.
        if "instagram" in low or "cdn" in low or "fbcdn" in low:
            return value
    if isinstance(value, dict):
        for key in ("video_url", "video", "download_url", "media_url"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                return candidate
            found = _find_media_url(value.get(key))
            if found:
                return found
        # Generic URLs are accepted only after media-specific fields; this
        # handles CDN links that have no .mp4 suffix.
        found = _find_media_url(value.get("url"))
        if found:
            return found
        for item in value.values():
            found = _find_media_url(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_media_url(item)
            if found:
                return found
    return None

async def download_instagram(url: str) -> str:
    logging.info("Instagram pipeline: primary=%s fallback=%s", bool(RAPIDAPI_KEY), bool(RAPIDAPI_FALLBACK_KEY))
    # 1. Agar RapidAPI kaliti bo'lsa — avval API orqali sinab ko'ramiz
    if RAPIDAPI_KEY:
        try:
            return await _download_instagram_rapidapi(url)
        except Exception as e:
            logging.warning(f"Instagram RapidAPI xatolik: {e}")

    # 2. Fallback RapidAPI subscription, independent quota
    if RAPIDAPI_FALLBACK_KEY:
        try:
            return await _download_instagram_looter(url)
        except Exception as e:
            logging.warning(f"Instagram Looter fallback xatolik: {e}")

    # 3. Zaxira: yt-dlp
    return await download_media(url)
