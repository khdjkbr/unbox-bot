from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_ID
from services.database import get_user_and_global_stats

router = Router()

@router.message(Command("stats", "stat"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    
    # Agar ADMIN_ID hali Render'da sozlanmagan bo'lsa (0 bo'lsa):
    if ADMIN_ID == 0:
        await message.answer(
            f"ℹ️ <b>ADMIN_ID hali sozlanmagan!</b>\n\n"
            f"Sizning Telegram ID: <code>{user_id}</code>\n\n"
            f"Ushbu raqamni nusxalab, Render'dagi Environment bo'limiga <b>ADMIN_ID</b> nomi bilan kiriting va saqlang.",
            parse_mode="HTML"
        )
        return

    # Agar boshqa foydalanuvchi yozsa — e'tiborsiz qoldirish
    if user_id != ADMIN_ID:
        return

    try:
        stats = get_user_and_global_stats(user_id)
        text = (
            "📊 <b>Foydalanish statistikasi:</b>\n\n"
            f"👤 <b>Sizning faolligingiz:</b>\n"
            f"📥 Yuklab olgan videolaringiz: <b>{stats['user_downloads']} ta</b>\n\n"
            f"🌐 <b>Umumiy bot statistikasi:</b>\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['total_users']} ta</b>\n"
            f"🚀 Jami yuklab olishlar: <b>{stats['total_downloads']} ta</b>\n\n"
            f"📢 <i>Kanalimizga a'zo bo'ling:</i> @unbox_uzb"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Statistikani olishda xatolik yuz berdi: {e}")
