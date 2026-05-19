import os
import logging
import asyncio
import json
import aiohttp
from aiohttp import web, ClientSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", 8080))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

logger.info(f"Starting MealMeter on port {PORT}")
logger.info(f"BOT_TOKEN set: {bool(BOT_TOKEN)}")
logger.info(f"ANTHROPIC_API_KEY set: {bool(ANTHROPIC_API_KEY)}")

async def handle_health(request):
    return web.Response(text="OK")

async def handle_options(request):
    return web.Response(status=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS"
    })

async def handle_proxy(request):
    try:
        body = await request.json()
        async with ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01"
                },
                json=body,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                data = await resp.json()
                return web.Response(
                    text=json.dumps(data),
                    content_type="application/json",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type",
                        "Access-Control-Allow-Methods": "POST, OPTIONS"
                    }
                )
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return web.Response(
            text=json.dumps({"error": str(e)}),
            status=500,
            content_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )

async def start_bot():
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN not set, skipping bot")
        return
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
        from telegram.ext import Application, CommandHandler, ContextTypes

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            name = update.effective_user.first_name or "друг"
            keyboard = [[InlineKeyboardButton(text="🍽️ Открыть MealMeter", web_app=WebAppInfo(url=WEBAPP_URL))]]
            await update.message.reply_text(
                f"👋 Привет, {name}!\n\n🍏 *MealMeter* — твой умный счётчик калорий.\n\nНажми кнопку ниже 👇",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        app_bot = Application.builder().token(BOT_TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        await app_bot.initialize()
        await app_bot.start()
        await app_bot.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot polling started")
    except Exception as e:
        logger.error(f"Bot error: {e}")

async def main():
    app_web = web.Application()
    app_web.router.add_get("/", handle_health)
    app_web.router.add_get("/health", handle_health)
    app_web.router.add_post("/proxy", handle_proxy)
    app_web.router.add_options("/proxy", handle_options)

    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server running on port {PORT}")

    await start_bot()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
