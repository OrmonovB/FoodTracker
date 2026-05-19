import os
import logging
import asyncio
import json
from aiohttp import web, ClientSession
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PORT = int(os.environ.get("PORT", 8080))

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
                json=body
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

async def handle_options(request):
    return web.Response(
        status=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        }
    )

async def handle_health(request):
    return web.Response(text="OK", status=200)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "друг"
    keyboard = [[InlineKeyboardButton(
        text="🍽️ Открыть MealMeter",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )]]
    await update.message.reply_text(
        f"👋 Привет, {name}!\n\n"
        f"🍏 *MealMeter* — твой умный счётчик калорий.\n\n"
        f"📸 Сфотографируй блюдо и ИИ подсчитает:\n"
        f"• Калории\n• Белки, жиры, углеводы\n\n"
        f"Нажми кнопку ниже 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *MealMeter*\n\n*/start* — открыть приложение",
        parse_mode="Markdown"
    )

async def run_bot(app_bot):
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot polling started")

async def main():
    # Web server first
    app_web = web.Application()
    app_web.router.add_get("/", handle_health)
    app_web.router.add_get("/health", handle_health)
    app_web.router.add_post("/proxy", handle_proxy)
    app_web.router.add_options("/proxy", handle_options)

    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

    # Bot
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("help", help_cmd))

    await run_bot(app_bot)

    try:
        await asyncio.Event().wait()
    finally:
        await app_bot.updater.stop()
        await app_bot.stop()
        await app_bot.shutdown()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
