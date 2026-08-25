import os
import re
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

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@unbox_uzb"
CHANNEL_URL = "https://t.me/unbox_uzb"
PROMO_CAPTION = "📥 Скачано через бота\n📢 Подписывайся на наш канал: @unbox_uzb"
PORT = int(os.getenv("PORT", 10000))
# ===============================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LINK_REGEX = r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be)\S+)'
paid_downloads = {}

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub_again")]
    ])

def download_media(url: str, format_spec: str = "bestvideo+bestaudio/best") -> str:
    output_template = f"downloads/%(id)s_{format_spec.replace('/', '_')}.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = {
        'format': format_spec,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith('.mp4'):
            filename = os.path.splitext(filename)[0] + '.mp4'
        return filename

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.chat.type == "private":
        is_sub = await check_subscription(message.from_user.id)
        if not is_sub:
            await message.answer(
                f"👋 Привет! Чтобы пользоваться ботом для скачивания видео, "
                f"подпишитесь на наш канал {CHANNEL_USERNAME}:",
                reply_markup=get_sub_keyboard()
            )
            return
        await message.answer("👋 Привет! Отправь мне ссылку на видео из Instagram, TikTok или YouTube!")

@dp.callback_query(F.data == "check_sub_again")
async def cb_check_sub(callback: CallbackQuery):
    is_sub = await check_subscription(callback.from_user.id)
    if is_sub:
        await callback.message.delete()
        await callback.message.answer("✅ Отлично, подписка подтверждена! Теперь отправь ссылку на видео.")
    else:
        await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)

@dp.message(F.text)
async def handle_links(message: Message):
    match = re.search(LINK_REGEX, message.text)
    if not match:
        return
    url = match.group(0)

    if message.chat.type == "private":
        is_sub = await check_subscription(message.from_user.id)
        if not is_sub:
            await message.answer(
                f"⚠️ Для скачивания видео необходимо быть подписанным на канал {CHANNEL_USERNAME}:",
                reply_markup=get_sub_keyboard()
            )
            return

        if "youtube.com" in url or "youtu.be" in url:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🎬 360p (Бесплатно)", callback_data=f"yt_free_360:{url}"),
                    InlineKeyboardButton(text="🎬 480p (Бесплатно)", callback_data=f"yt_free_480:{url}")
                ],
                [
                    InlineKeyboardButton(text="⭐ 720p HD (25 ⭐️)", callback_data=f"yt_paid_720:{url}"),
                    InlineKeyboardButton(text="⭐ 1080p FHD (25 ⭐️)", callback_data=f"yt_paid_1080:{url}")
                ]
            ])
            await message.answer("🎬 Выберите качество для загрузки с YouTube:", reply_markup=keyboard)
            return

    status_msg = await message.reply("⏳ Скачиваю видео, пожалуйста, подождите...")
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, "best[ext=mp4]/best")
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await status_msg.edit_text("❌ Файл превышает лимит Telegram (50 МБ).")
            os.remove(file_path)
            return

        video_file = types.FSInputFile(file_path)
        await message.reply_video(video=video_file, caption=PROMO_CAPTION)
        await status_msg.delete()
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Не удалось скачать видео. Проверьте ссылку.")

@dp.callback_query(F.data.startswith("yt_free_"))
async def process_free_yt(callback: CallbackQuery):
    quality, url = callback.data.split(":", 1)
    res = "360" if "360" in quality else "480"
    await callback.message.edit_text(f"⏳ Скачиваю YouTube в {res}p...")
    try:
        format_str = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]/best"
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, format_str)
        video_file = types.FSInputFile(file_path)
        await callback.message.reply_video(video=video_file, caption=PROMO_CAPTION)
        await callback.message.delete()
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await callback.message.edit_text("❌ Ошибка при скачивании.")

@dp.callback_query(F.data.startswith("yt_paid_"))
async def process_paid_yt(callback: CallbackQuery):
    quality, url = callback.data.split(":", 1)
    res = "720" if "720" in quality else "1080"
    user_id = callback.from_user.id
    paid_downloads[user_id] = {"url": url, "res": res}

    prices = [LabeledPrice(label=f"Скачивание в {res}p", amount=25)]
    await callback.message.delete()
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"Загрузка YouTube в {res}p HD",
        description=f"Скачивание выбранного видео в повышенном качестве {res}p.",
        payload=f"yt_hd_{user_id}",
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    user_id = message.from_user.id
    if user_id not in paid_downloads:
        await message.answer("✅ Оплата получена! Спасибо!")
        return

    data = paid_downloads.pop(user_id)
    url = data["url"]
    res = data["res"]

    status_msg = await message.answer(f"⭐ Оплата подтверждена! Скачиваю видео в {res}p...")
    try:
        format_str = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]/best"
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, format_str)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await status_msg.edit_text("❌ Файл превышает лимит Telegram в 50 МБ.")
            os.remove(file_path)
            return

        video_file = types.FSInputFile(file_path)
        await message.reply_video(video=video_file, caption=PROMO_CAPTION)
        await status_msg.delete()
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Ошибка при скачивании после оплаты.")

async def handle_ping(request):
    return web.Response(text="Bot is running on Render 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    await start_web_server()
    print("Бот запущен на Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
