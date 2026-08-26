from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from config import CHANNEL_USERNAME
from services.subscription import check_subscription, get_sub_keyboard
from services.database import add_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.chat.type == "private":
        add_user(message.from_user.id, message.from_user.username)
        is_sub = await check_subscription(message.bot, message.from_user.id)
        if not is_sub:
            await message.answer(
                f"👋 Assalomu alaykum! Botdan foydalanish va video yuklab olish uchun "
                f"kanalimizga obuna bo'ling: {CHANNEL_USERNAME}",
                reply_markup=get_sub_keyboard()
            )
            return
        await message.answer("👋 Assalomu alaykum! Menga Instagram, TikTok, Facebook yoki YouTube havolasini yuboring, men mediafaylni yuklab beraman!")

@router.callback_query(F.data == "check_sub_again")
async def cb_check_sub(callback: CallbackQuery):
    is_sub = await check_subscription(callback.bot, callback.from_user.id)
    if is_sub:
        await callback.message.delete()
        await callback.message.answer("👋 Assalomu alaykum! Menga Instagram, TikTok, Facebook yoki YouTube havolasini yuboring, men mediafaylni yuklab beraman!")
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)
