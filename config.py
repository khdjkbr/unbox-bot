import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
CHANNEL_USERNAME = "@unbox_uzb"
CHANNEL_URL = "https://t.me/unbox_uzb"
PROMO_CAPTION = "📥 @videoni_yuklaydigan_bot orqali yuklab olindi!\n📢 Yanada qiziqarli ma'lumotlar @unbox_uzb kanalida, obuna bo'ling!"
PORT = int(os.getenv("PORT", 10000))
