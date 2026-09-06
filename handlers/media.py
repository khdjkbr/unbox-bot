import os
import asyncio
from services.links import extract_link
import logging
from aiogram import Router, F, types
from aiogram.types import Message
from config import CHANNEL_USERNAME, PROMO_CAPTION
from services.subscription import check_subscription, get_sub_keyboard
from services.instagram import download_instagram
from services.tiktok import download_tiktok
from services.facebook import download_facebook
from services.twitter import download_twitter
from services.youtube import download_youtube
from services.database import add_user, increment_download, get_user_and_global_stats
from services.converter import convert_for_ios

router = Router()



# Shaxsiy va umumiy statistikani faqat LICHKADA yuborish
async def send_stats_post(message: Message, user_id: int):
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
    match = extract_link(content)
    if not match:
        return
    url, platform = match

    # Foydalanuvchini bazaga qo'shish
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    username = message.from_user.username if message.from_user else (message.sender_chat.title if message.sender_chat else "")

    if user_id:
        add_user(user_id, username)

    # Shaxsiy xabarlarda: obunani tekshirish
    if message.chat.type == "private":
        is_sub = await check_subscription(message.bot, user_id)
        if is_sub is None:
            await message.answer("⚠️ Obunani tekshirib bo‘lmadi. Keyinroq urinib ko‘ring.")
            return
        if not is_sub:
            await message.answer(
                f"⚠️ Videoni yuklab olish uchun avval kanalimizga a'zo bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return

    file_path = None
    progress = None
    try:
        progress = await message.answer("⏳ Havola qabul qilindi, video yuklanmoqda…")
        await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")
        if platform == "youtube":
            file_path = await download_youtube(url)
        elif platform == "tiktok":
            file_path = await download_tiktok(url)
        elif platform == "facebook":
            file_path = await download_facebook(url)
        elif platform == "twitter":
            file_path = await download_twitter(url)
        else:
            file_path = await download_instagram(url)
        
        # Agar rasm (foto-stories) bo'lsa:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            photo_file = types.FSInputFile(file_path)
            await message.reply_photo(photo=photo_file, caption=PROMO_CAPTION)
        else:
            # Agar video bo'lsa: iPhone uchun H.264 formatlash
            file_path = await asyncio.to_thread(convert_for_ios, file_path)

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > 50:
                await message.reply("❌ Fayl hajmi Telegram cheklovidan (50 MB) oshib ketdi.")
                return

            video_file = types.FSInputFile(file_path)
            await message.reply_video(
                video=video_file, 
                caption=PROMO_CAPTION,
                supports_streaming=True
            )

        if user_id:
            increment_download(user_id)
        
        # Statistikani yuborish (faqat lichkada)
        if user_id:
            await send_stats_post(message, user_id)
        if progress:
            await progress.delete()
    except Exception:
        logging.exception("Media download/upload failed: platform=%s", platform)
        if progress:
            await progress.edit_text("❌ Yuklab bo‘lmadi. Havola ochiq va to‘g‘ri ekanini tekshiring.")
        else:
            await message.reply("❌ Yuklab bo‘lmadi. Havola ochiq va to‘g‘ri ekanini tekshiring.")

    finally:
        if file_path and os.path.isfile(file_path):
            os.remove(file_path)
