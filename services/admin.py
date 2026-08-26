from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_ID
from services.database import get_stats

router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    # Faqat bot egasiga ko'rsatish
    if message.from_user.id != ADMIN_ID:
        return

    stats = get_stats()
    text = (
        "📊 <b>Bot statistikasi:</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> <code>{stats['total_users']} ta</code>\n"
        f"🆕 <b>Bugun qo'shilganlar:</b> <code>{stats['today_users']} ta</code>\n"
        f"📥 <b>Jami yuklab olishlar:</b> <code>{stats['total_downloads']} ta</code>"
    )
    await message.answer(text, parse_mode="HTML")
