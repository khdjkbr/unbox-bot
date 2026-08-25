import os
import re
import asyncio
import logging
import aiohttp
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

# --- To'g'ridan-to'g'ri HD yuklash havolasini olish (Cobalt API orqali) ---
async def get_direct_download_link(url: str, quality: str) -> str:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "url": url,
        "vQuality": quality
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("https://api.cobalt.tools/", json=payload, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "url" in data:
                        return data["url"]
        except Exception as e:
            logging.error(f"Cobalt API xatolik: {e}")
    
    # Zaxira havola (agar API band bo'lsa)
    return f"https://cobalt.tools/?u={url}"

# --- Bepul videolarni yt-dlp orqali yuklab olish ---
def download_media(url: str, format_spec: str = "bestvideo+bestaudio/best") -> str:
    output_template = f"downloads/%(id)s_{format_spec.replace('/', '_')}.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'format': format_spec,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web_embedded']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith('.mp4'):
            filename = os.path.splitext(filename)[0] + '.mp4'
        return filename

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
        await message.answer("👋 Assalomu alaykum! Menga Instagram, TikTok yoki YouTube havolasini yuboring!")

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

    # Shaxsiy xabarlarda: obunani tekshirish
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
                ],
                [
                    InlineKeyboardButton(text="⭐ 2K / 4K Ultra HD (25 ⭐️)", callback_data="yt_max")
                ]
            ])
            await message.answer("🎬 YouTube videoni qaysi sifatda yuklab olmoqchisiz?", reply_markup=keyboard)
            return

    # Instagram / TikTok (yoki guruhlarda avtomatik)
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, "best[ext=mp4]/best")
        
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

# --- Pullik YouTube (720p / 1080p / 4K - 25 Yulduz) ---
@dp.callback_query(F.data.in_(["yt_720", "yt_1080", "yt_max"]))
async def process_paid_yt(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_links.get(user_id)
    if not url:
        await callback.answer("❌ Havola eskirgan, iltimos qaytadan yuboring.", show_alert=True)
        return

    res_labels = {
        "yt_720": "720p HD",
        "yt_1080": "1080p Full HD",
        "yt_max": "2K / 4K Ultra HD"
    }
    selected_label = res_labels.get(callback.data, "HD")
    quality_code = "720" if callback.data == "yt_720" else ("1080" if callback.data == "yt_1080" else "max")
    
    paid_downloads[user_id] = {"url": url, "quality": quality_code, "label": selected_label}

    prices = [LabeledPrice(label=f"{selected_label} sifatda yuklash", amount=25)]
    await callback.message.delete()
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"YouTube {selected_label} yuklash",
        description=f"Videoni yuqori sifatda ({selected_label}) to'g'ridan-to'g'ri yuklab olish havolasi.",
        payload=f"yt_hd_{user_id}",
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# --- To'lovdan so'ng to'g'ridan-to'g'ri yuklash havolasini taqdim etish ---
@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    user_id = message.from_user.id
    if user_id not in paid_downloads:
        return

    data = paid_downloads.pop(user_id)
    url = data["url"]
    quality = data["quality"]
    label = data["label"]

    # To'g'ridan-to'g'ri yuklash havolasini olish
    download_url = await get_direct_download_link(url, quality)

    download_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📥 {label} videoni yuklab olish", url=download_url)]
    ])

    await message.answer(
        f"⭐ <b>To'lov muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"🎬 <b>Video sifati:</b> {label}\n\n"
        f"Quyidagi tugma orqali videoni to'liq sifatda (ovozli) to'g'ridan-to'g'ri qurilmangizga yuklab olishingiz mumkin:\n\n"
        f"{PROMO_CAPTION}",
        reply_markup=download_keyboard,
        parse_mode="HTML"
    )

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
