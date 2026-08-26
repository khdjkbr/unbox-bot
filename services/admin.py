from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_ID
from services.database import get_stats

router = Router()

@router.message(Command("stats"))
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
        stats = get_stats()
        text = (
            "📊 <b>Bot statistikasi:</b>\n\n"
            f"👥 <b>Jami foydalanuvchilar:</b> <code>{stats['total_users']} ta</code>\n"
            f"🆕 <b>Bugun qo'shilganlar:</b> <code>{stats['today_users']} ta</code>\n"
            f"📥 <b>Jami yuklab olishlar:</b> <code>{stats['total_downloads']} ta</code>"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Statistikani olishda xatolik yuz berdi: {e}")
