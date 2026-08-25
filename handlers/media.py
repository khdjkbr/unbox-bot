import os
import re
import logging
from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_USERNAME, PROMO_CAPTION
from services.subscription import check_subscription, get_sub_keyboard
from services.instagram import download_instagram
from services.tiktok import download_tiktok
from services.youtube import cascade_download_youtube, get_browser_download_url
from handlers.payments import user_links

router = Router()

LINK_REGEX = r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be)\S+)'

@router.message(F.text)
async def handle_links(message: Message):
    match = re.search(LINK_REGEX, message.text)
    if not match:
        return
    url = match.group(0)

    # Shaxsiy xabarlarda obunani tekshirish
    if message.chat.type == "private":
        is_sub = await check_subscription(message.bot, message.from_user.id)
        if not is_sub:
            await message.answer(
                f"⚠️ Videoni yuklab olish uchun avval kanalimizga a'zo bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return

    is_youtube = ("youtube.com" in url or "youtu.be" in url)
    is_shorts = ("/shorts/" in url)

    # 1. Agar YouTube to'liq video bo'lsa (Shorts EMAS):
    if is_youtube and not is_shorts:
        if message.chat.type == "private":
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
            await message.answer("🎬 YouTube videoni qaysi formatda yuklab olmoqchisiz?", reply_markup=keyboard)
        else:
            download_url = get_browser_download_url(url)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Videoni brauzerda yuklab olish", url=download_url)]
            ])
            await message.reply(
                f"🎬 YouTube videoni yuklab olish uchun quyidagi tugmani bosing:\n\n{PROMO_CAPTION}",
                reply_markup=kb
            )
        return

    # 2. Instagram, TikTok va YouTube Shorts: Kaskadli yuklash
    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
    file_path = None
    try:
        if is_shorts:
            file_path = await cascade_download_youtube(url, "720")
        elif "instagram.com" in url:
            file_path = await download_instagram(url)
        else:
            file_path = await download_tiktok(url)
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            os.remove(file_path)
            # 50 MB dan oshsa, to'g'ridan-to'g'ri brauzer havolasini taqdim etish
            download_url = get_browser_download_url(url) if is_shorts else url
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Videoni brauzerda yuklab olish (50 MB+)", url=download_url)]
            ])
            await message.reply(f"ℹ️ Fayl 50 MB dan katta bo'lgani uchun brauzer orqali yuklang:\n\n{PROMO_CAPTION}", reply_markup=kb)
            return

        video_file = types.FSInputFile(file_path)
        await message.reply_video(video=video_file, caption=PROMO_CAPTION)
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Yuklashda barcha usullar xatolik berdi: {e}")
        # Agar fayl yuklab bo'lmasa, zaxira brauzer havolasini yuborish
        if is_shorts:
            download_url = get_browser_download_url(url)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Shorts videoni brauzerda yuklab olish", url=download_url)]
            ])
            await message.reply(f"🎬 Videoni yuklab olish havolasi tayyor:\n\n{PROMO_CAPTION}", reply_markup=kb)
        else:
            await message.reply("❌ Videoni yuklab bo'lmadi. Havola to'g'riligini tekshiring.")
