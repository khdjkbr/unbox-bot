import os
import re
import glob
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, Message, CallbackQuery
)
import yt_dlp

# ========== SOZLAMALAR (НАСТРОЙКИ) ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@unbox_uzb"
CHANNEL_URL = "https://t.me/unbox_uzb"
PROMO_CAPTION = "📥 @videoni_yuklaydigan_bot orqali yuklab olindi!\n📢 Yanada qiziqarli ma'lumotlar @unbox_uzb kanalida, obuna bo'ling!"
PORT = int(os.getenv("PORT", 10000))
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LINK_REGEX = r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be)\S+)'

user_links = {}
paid_downloads = {}

# --- Kanalga obunani tekshirish ---
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Obunani tekshirishda xatolik: {e}")
        return False

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub_again")]
    ])

# --- Aniq va ishonchli yuklab olish funksiyasi ---
def download_media(url: str, format_spec: str = "bestvideo+bestaudio/best") -> str:
    unique_id = os.urandom(6).hex()
    output_template = f"downloads/{unique_id}_%(id)s.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'format': format_spec,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Diskda aynan yaratilgan tayyor faylni topish
    downloaded_files = glob.glob(f"downloads/{unique_id}_*")
    if not downloaded_files:
        raise FileNotFoundError("Yuklangan fayl diskda topilmadi.")
    
    return downloaded_files[0]

# --- /start buyrug'i ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.chat.type == "private":
        is_sub = await check_subscription(message.from_user.id)
        if not is_sub:
            await message.answer(
                f"👋 Assalomu alaykum! Botdan foydalanish va video yuklab olish uchun "
                f"kanalimizga obuna bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return
        await message.answer("👋 Assalomu alaykum! Menga Instagram, TikTok yoki YouTube havolasini yuboring, men mediafaylni yuklab beraman!")

# --- Obunani tekshirish tugmasi ---
@dp.callback_query(F.data == "check_sub_again")
async def cb_check_sub(callback: CallbackQuery):
    is_sub = await check_subscription(callback.from_user.id)
    if is_sub:
        await callback.message.delete()
        await callback.message.answer("✅ Obuna tasdiqlandi! Endi video havolasini yuborishingiz mumkin.")
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

# --- Havolalarni qabul qilish ---
@dp.message(F.text)
async def handle_links(message: Message):
    match = re.search(LINK_REGEX, message.text)
    if not match:
        return
    url = match.group(0)

    # Shaxsiy xabarlarda obunani tekshirish
    if message.chat.type == "private":
        is_sub = await check_subscription(message.from_user.id)
        if not is_sub:
            await message.answer(
                f"⚠️ Videoni yuklab olish uchun avval kanalimizga a'zo bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return

        # YouTube bo'lsa sifat tanlash menyusi
        if "youtube.com" in url or "youtu.be" in url:
            user_links[message.from_user.id] = url
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎬 360p (Bepul)", callback_data="yt_360"),
                    InlineKeyboardButton(text="🎬 480p (Bepul)", callback_data="yt_480")
                ],
                [
                    InlineKeyboardButton(text="⭐ 720p HD (25 ⭐️)", callback_data="yt_720"),
                    InlineKeyboardButton(text="⭐ 1080p FHD (25 ⭐️)", callback_data="yt_1080")
                ]
            ])
            await message.answer("🎬 YouTube videoni qaysi sifatda yuklab olmoqchisiz?", reply_markup=keyboard)
            return

    # Instagram / TikTok (yoki guruhlarda avtomatik)
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best")
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await message.reply("❌ Fayl hajmi Telegram cheklovidan (50 MB) oshib ketdi.")
            os.remove(file_path)
            return

        video_file = types.FSInputFile(file_path)
        await message.reply_video(video=video_file, caption=PROMO_CAPTION)
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.reply("❌ Videoni yuklab bo'lmadi. Havola to'g'riligini tekshiring.")

# --- Bepul YouTube (360p / 480p) ---
@dp.callback_query(F.data.in_(["yt_360", "yt_480"]))
async def process_free_yt(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_links.get(user_id)
    if not url:
        await callback.answer("❌ Havola eskirgan, iltimos qaytadan yuboring.", show_alert=True)
        return

    res = "360" if callback.data == "yt_360" else "480"
    await callback.message.delete()
    await bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_video")
    
    try:
        format_str = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]/best"
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, format_str)
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await callback.message.answer("❌ Fayl hajmi Telegram cheklovidan (50 MB) oshib ketdi.")
            os.remove(file_path)
            return

        video_file = types.FSInputFile(file_path)
        await callback.message.answer_video(video=video_file, caption=PROMO_CAPTION)
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await callback.message.answer("❌ Yuklab olishda xatolik yuz berdi.")

# --- Pullik YouTube (720p / 1080p - 25 Yulduz) ---
@dp.callback_query(F.data.in_(["yt_720", "yt_1080"]))
async def process_paid_yt(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_links.get(user_id)
    if not url:
        await callback.answer("❌ Havola eskirgan, iltimos qaytadan yuboring.", show_alert=True)
        return

    res = "720" if callback.data == "yt_720" else "1080"
    paid_downloads[user_id] = {"url": url, "res": res}

    prices = [LabeledPrice(label=f"{res}p sifatda yuklash", amount=25)]
    await callback.message.delete()
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"YouTube {res}p HD yuklash",
        description=f"Videoni yuqori sifatda ({res}p) to'liq yuklab olish.",
        payload=f"yt_hd_{user_id}",
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# --- To'lovdan so'ng videoni yuborish ---
@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    user_id = message.from_user.id
    if user_id not in paid_downloads:
        return

    data = paid_downloads.pop(user_id)
    url = data["url"]
    res = data["res"]

    await bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    try:
        format_str = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]/best"
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, format_str)
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await message.reply("❌ Fayl hajmi Telegram cheklovidan (50 MB) oshib ketdi.")
            os.remove(file_path)
            return

        video_file = types.FSInputFile(file_path)
        await message.reply_video(video=video_file, caption=PROMO_CAPTION)
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.reply("❌ To'lovdan so'ng yuklab olishda xatolik yuz berdi.")

# --- Serverni 24/7 ushlab turish ---
async def handle_ping(request):
    return web.Response(text="Bot faol va 24/7 ishlamoqda!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    await start_web_server()
    print("Bot muvaffaqiyatli ishga tushirildi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
