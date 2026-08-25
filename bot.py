import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, PORT
from handlers import start, payments, media

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Routerlarni ro'yxatdan o'tkazish
dp.include_router(start.router)
dp.include_router(payments.router)
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

async def main():
    await start_web_server()
    print("Bot muvaffaqiyatli ishga tushirildi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
