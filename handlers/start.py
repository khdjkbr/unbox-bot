from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_USERNAME
from services.subscription import check_subscription, get_sub_keyboard
from services.database import add_user

router = Router()

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistikam", callback_data="show_stats"),
         InlineKeyboardButton(text="ℹ️ Yordam", callback_data="show_help")],
        [InlineKeyboardButton(text="📢 Kanalimiz", url="https://t.me/unbox_uzb")],
    ])

HELP_TEXT = ("ℹ️ <b>Botdan foydalanish:</b>\n\n"
             "Instagram, TikTok, Facebook, Twitter (X) yoki YouTube havolasini yuboring.\n"
             "Bot videoni yuklab, Telegramga yuboradi.\n\n"
             "📌 Faqat ochiq va ishlaydigan havolalar qo‘llab-quvvatlanadi.")

@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.chat.type == "private":
        add_user(message.from_user.id, message.from_user.username)
        is_sub = await check_subscription(message.bot, message.from_user.id)
        if is_sub is None:
            await message.answer("⚠️ Obunani tekshirib bo‘lmadi. Keyinroq urinib ko‘ring.")
            return
        if not is_sub:
            await message.answer(
                f"👋 Assalomu alaykum! Botdan foydalanish va video yuklab olish uchun "
                f"kanalimizga obuna bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return
        await message.answer("👋 Assalomu alaykum! Video havolasini yuboring.", reply_markup=main_keyboard())

@router.callback_query(F.data == "check_sub_again")
async def cb_check_sub(callback: CallbackQuery):
    is_sub = await check_subscription(callback.bot, callback.from_user.id)
    if is_sub is None:
        await callback.answer("⚠️ Obunani tekshirib bo‘lmadi. Keyinroq urinib ko‘ring.", show_alert=True)
        return
    if is_sub:
        await callback.answer()
        await callback.message.delete()
        await callback.message.answer("👋 Assalomu alaykum! Video havolasini yuboring.", reply_markup=main_keyboard())
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

@router.message(F.text == "/help")
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML", reply_markup=main_keyboard())

@router.callback_query(F.data == "show_help")
async def cb_help(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(HELP_TEXT, parse_mode="HTML")

@router.callback_query(F.data == "show_stats")
async def cb_stats(callback: CallbackQuery):
    from handlers.media import send_stats_post
    await callback.answer()
    await send_stats_post(callback.message, callback.from_user.id)
