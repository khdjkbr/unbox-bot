import os
import re
import logging
from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_USERNAME, PROMO_CAPTION
from services.subscription import check_subscription, get_sub_keyboard
from services.instagram import download_instagram
from services.tiktok import download_tiktok
from services.facebook import download_facebook
from services.youtube import get_browser_download_url
from services.database import add_user, increment_download, get_user_and_global_stats

router = Router()

LINK_REGEX = r'(https?://[^\s]*(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be|facebook\.com|fb\.watch)[^\s]*)'

# Shaxsiy va umumiy statistikani faqat LICHKADA yuborish
async def send_stats_post(message: Message, user_id: int):
    # Guruhlarga yuborilmaydi, faqat shaxsiy yozishmada (lichkada) chiqadi
    if message.chat.type != "private":
        return

    try:
        stats = get_user_and_global_stats(user_id)
        stats_text = (
            "📊 <b>Foydalanish statistikasi:</b>\n\n"
            f"👤 <b>Sizning faolligingiz:</b>\n"
            f"📥 Yuklab olgan videolaringiz: <b>{stats['user_downloads']} ta</b>\n\n"
            f"🌐 <b>Umumiy bot statistikasi:</b>\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['total_users']} ta</b>\n"
            f"🚀 Jami yuklab olishlar: <b>{stats['total_downloads']} ta</b>\n\n"
            f"📢 <i>Kanalimizga a'zo bo'ling:</i> @unbox_uzb"
        )
        await message.answer(stats_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Statistika yuborishda xatolik: {e}")

@router.message(F.text | F.caption)
async def handle_links(message: Message):
    content = message.text or message.caption or ""
    match = re.search(LINK_REGEX, content)
    if not match:
        return
    url = match.group(0)

    # Foydalanuvchini aniqlash (guruhda ham, lichkada ham ishlaydi)
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    username = message.from_user.username if message.from_user else (message.sender_chat.title if message.sender_chat else "")

    # Barcha foydalanuvchilarni (guruhdagilarni ham) global bazaga qo'shish
    if user_id:
        add_user(user_id, username)

    # Shaxsiy xabarlarda: obunani tekshirish
    if message.chat.type == "private":
        is_sub = await check_subscription(message.bot, user_id)
        if not is_sub:
            await message.answer(
                f"⚠️ Videoni yuklab olish uchun avval kanalimizga a'zo bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return

    is_youtube = ("youtube.com" in url or "youtu.be" in url)

    # 1. YouTube havolalari: SaveFrom havolasi
    if is_youtube:
        if user_id:
            increment_download(user_id)
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
        if user_id:
            await send_stats_post(message, user_id)
        return

    # 2. Instagram, TikTok va Facebook: Faylni Telegramga yuklash
    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    try:
        if "tiktok.com" in url:
            file_path = await download_tiktok(url)
        elif "facebook.com" in url or "fb.watch" in url:
            file_path = await download_facebook(url)
        else:
            file_path = await download_instagram(url)
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await message.reply("❌ Fayl hajmi Telegram cheklovidan (50 MB) oshib ketdi.")
            os.remove(file_path)
            return

        video_file = types.FSInputFile(file_path)
        await message.reply_video(video=video_file, caption=PROMO_CAPTION)
        if user_id:
            increment_download(user_id)
        os.remove(file_path)
        
        # Statistikani yuborish (faqat lichkada chiqadi)
        if user_id:
            await send_stats_post(message, user_id)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.reply("❌ Videoni yuklab bo'lmadi. Havola to'g'riligini tekshiring.")
