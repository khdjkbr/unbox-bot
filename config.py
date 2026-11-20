import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_FALLBACK_KEY = os.getenv("RAPIDAPI_FALLBACK_KEY", RAPIDAPI_KEY)
CHANNEL_USERNAME = "@unbox_uzb"
CHANNEL_URL = "https://t.me/unbox_uzb"
PROMO_CAPTION = (
    "📥 <b>Yuklab olindi</b>\n"
    '🤖 <a href="https://t.me/videoni_yuklaydigan_bot">@videoni_yuklaydigan_bot</a>\n'
    f'📢 <a href="{CHANNEL_URL}">UNBOX kanaliga obuna bo‘ling</a>'
)
PORT = int(os.getenv("PORT", 10000))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
