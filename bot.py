import os
import asyncio
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PORT
from services.database import init_db
from handlers import start, media, admin

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Routerlarni ulash
dp.include_router(admin.router)
dp.include_router(start.router)
dp.include_router(media.router)

async def handle_ping(request):
    return web.Response(text="Bot faol va 24/7 ishlamoqda!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# --- Serverni uxlatmaslik uchun avto-ping funksiyasi ---
async def keep_awake_task():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        logging.info("RENDER_EXTERNAL_URL topilmadi, tashqi pinger orqali ushlab turiladi.")
        return

    await asyncio.sleep(30) # Server ishga tushishini kutish
    logging.info(f"Avto-ping ishga tushdi: {render_url}")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(render_url, timeout=10) as resp:
                    logging.info(f"Ping muvaffaqiyatli: {resp.status}")
            except Exception as e:
                logging.warning(f"Ping xatolik: {e}")
            await asyncio.sleep(600) # Har 10 daqiqada o'zini o'zi chaqirish

async def main():
    init_db()  # Bazani ishga tushirish
    await start_web_server()
    asyncio.create_task(keep_awake_task()) # Avto-pingni orqa fonda ishga tushirish
    print("Bot muvaffaqiyatli ishga tushirildi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
