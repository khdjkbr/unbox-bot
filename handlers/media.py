import os
import re
import logging
from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_USERNAME, PROMO_CAPTION
from services.subscription import check_subscription, get_sub_keyboard
from services.instagram import download_instagram
from services.tiktok import download_tiktok
from services.youtube import get_browser_download_url
from services.database import add_user, increment_download

router = Router()

LINK_REGEX = r'(https?://[^\s]*(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be)[^\s]*)'

@router.message(F.text | F.caption)
async def handle_links(message: Message):
    content = message.text or message.caption or ""
    match = re.search(LINK_REGEX, content)
    if not match:
        return
    url = match.group(0)

    # Foydalanuvchini bazaga saqlash
    if message.from_user:
        add_user(message.from_user.id, message.from_user.username)

    # Shaxsiy xabarlarda: obunani tekshirish
    if message.chat.type == "private":
        is_sub = await check_subscription(message.bot, message.from_user.id)
        if not is_sub:
            await message.answer(
                f"⚠️ Videoni yuklab olish uchun avval kanalimizga a'zo bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return

    is_youtube = ("youtube.com" in url or "youtu.be" in url)

    # 1. YouTube: SaveFrom havolasi
    if is_youtube:
        increment_download(message.from_user.id)
        download_url = get_browser_download_url(url)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Videoni yuklab olish (SaveFrom)", url=download_url)]
        ])
        
        text = (
            f"🎬 <b>YouTube videoni yuklab olish havolasi tayyor!</b>\n\n"
            f"Quyidagi tugma orqali videoni to'g'ridan-to'g'ri SaveFrom orqali yuklab olishingiz mumkin:\n\n"
            f"{PROMO_CAPTION}"
        )
        await message.reply(text, reply_markup=kb, parse_mode="HTML")
        return

    # 2. Instagram va TikTok: Faylni Telegramga yuklash
    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    try:
        if "tiktok.com" in url:
            file_path = await download_tiktok(url)
        else:
            file_path = await download_instagram(url)
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await message.reply("❌ Fayl hajmi Telegram cheklovidan (50 MB) oshib ketdi.")
            os.remove(file_path)
            return

        video_file = types.FSInputFile(file_path)
        await message.reply_video(video=video_file, caption=PROMO_CAPTION)
        increment_download(message.from_user.id)
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.reply("❌ Videoni yuklab bo'lmadi. Havola to'g'riligini tekshiring.")
