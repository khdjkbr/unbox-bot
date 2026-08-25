import os
import logging
from aiogram import Router, F, types
from aiogram.types import (
    CallbackQuery, Message, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import PROMO_CAPTION
from services.youtube import cascade_download_youtube, get_browser_download_url

router = Router()

user_links = {}
paid_downloads = {}

# --- Bepul YouTube 360p / 480p ---
@router.callback_query(F.data.in_(["yt_360", "yt_480"]))
async def process_free_yt(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_links.get(user_id)
    if not url:
        await callback.answer("❌ Havola eskirgan, iltimos qaytadan yuboring.", show_alert=True)
        return

    res = "360" if callback.data == "yt_360" else "480"
    await callback.message.delete()
    await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action="upload_video")

    # Kaskad orqali faylni Telegramga yuklashga urinish
    try:
        file_path = await cascade_download_youtube(url, res)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb <= 50:
            video_file = types.FSInputFile(file_path)
            await callback.message.answer_video(video=video_file, caption=PROMO_CAPTION)
            os.remove(file_path)
            return
        os.remove(file_path)
    except Exception as e:
        logging.warning(f"Fayl yuklab bo'lmadi, brauzer havolasiga o'tilmoqda: {e}")

    # Agar fayl yuklanmasa yoki 50 MB dan katta bo'lsa -> Brauzer havolasi
    download_url = get_browser_download_url(url)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🌐 {res}p videoni brauzerda yuklab olish", url=download_url)]
    ])
    await callback.message.answer(
        f"🎬 <b>YouTube {res}p videoni yuklab olish havolasi tayyor!</b>\n\n{PROMO_CAPTION}",
        reply_markup=kb,
        parse_mode="HTML"
    )

# --- Pullik YouTube 720p / 1080p (25 Yulduz) ---
@router.callback_query(F.data.in_(["yt_720", "yt_1080"]))
async def process_paid_yt(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_links.get(user_id)
    if not url:
        await callback.answer("❌ Havola eskirgan, iltimos qaytadan yuboring.", show_alert=True)
        return

    res = "720" if callback.data == "yt_720" else "1080"
    paid_downloads[user_id] = {"url": url, "res": res}

    prices = [LabeledPrice(label=f"{res}p HD sifatda yuklash", amount=25)]
    await callback.message.delete()
    await callback.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"YouTube {res}p HD yuklash",
        description=f"Videoni yuqori sifatda ({res}p HD) to'liq yuklab olish.",
        payload=f"yt_hd_{user_id}",
        currency="XTR",
        prices=prices
    )

@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# --- To'lovdan so'ng videoni kaskadli yuborish ---
@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    user_id = message.from_user.id
    if user_id not in paid_downloads:
        return

    data = paid_downloads.pop(user_id)
    url = data["url"]
    res = data["res"]

    await message.bot.send_chat_action(chat_id=message.chat.id, action="upload_video")

    # Kaskad orqali faylni Telegramga yuklashga urinish
    try:
        file_path = await cascade_download_youtube(url, res)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb <= 50:
            video_file = types.FSInputFile(file_path)
            await message.reply_video(video=video_file, caption=PROMO_CAPTION)
            os.remove(file_path)
            return
        os.remove(file_path)
    except Exception as e:
        logging.warning(f"HD fayl yuklab bo'lmadi, brauzer havolasiga o'tilmoqda: {e}")

    # Agar fayl 50 MB dan katta bo'lsa yoki yuklanmasa -> Brauzer havolasi
    download_url = get_browser_download_url(url)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📥 {res}p HD videoni yuklab olish", url=download_url)]
    ])
    await message.answer(
        f"⭐ <b>To'lov muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"🎬 <b>Video sifati:</b> {res}p HD\n\n"
        f"Quyidagi tugma orqali videoni yuqori sifatda brauzeringizda yuklab oling:\n\n{PROMO_CAPTION}",
        reply_markup=kb,
        parse_mode="HTML"
    )
