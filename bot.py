import os
import logging
import asyncio
import json
import aiohttp
from datetime import datetime, time, timezone, timedelta
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

# Store users who pressed /start (for reminders)
USERS_FILE = "/tmp/mm_users.json"

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f)
    except Exception as e:
        logger.error(f"Save users error: {e}")

# ── PROXY ──
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
                timeout=aiohttp.ClientTimeout(total=120)
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

# ── BOT ──
async def start_bot():
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN not set, skipping bot")
        return
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            name = user.first_name or "друг"
            # Save user for reminders
            users = load_users()
            users[str(user.id)] = {
                "name": name,
                "chat_id": update.effective_chat.id,
                "joined": datetime.now().isoformat()
            }
            save_users(users)

            keyboard = [[InlineKeyboardButton(text="🍽️ Открыть MealMeter", web_app=WebAppInfo(url=WEBAPP_URL))]]
            await update.message.reply_text(
                f"👋 Привет, {name}!\n\n"
                f"🍏 *MealMeter* — твой умный счётчик калорий.\n\n"
                f"📸 Сфотографируй блюдо и ИИ подсчитает:\n"
                f"• Калории\n• Белки, жиры, углеводы\n\n"
                f"💬 Напиши `/help` для списка команд\n"
                f"🔔 Напиши `/reminders` чтобы включить напоминания\n\n"
                f"Нажми кнопку ниже 👇",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "ℹ️ *Команды MealMeter*\n\n"
                "/start — открыть приложение\n"
                "/reminders — включить/выключить напоминания\n"
                "/stop_reminders — выключить напоминания\n\n"
                "Внутри приложения:\n"
                "📸 Камера — снять блюдо\n"
                "🖼 Галерея — выбрать фото\n"
                "✏️ Вручную — ввести текстом\n"
                "📊 Штрих-код — отсканировать упаковку\n"
                "💬 Диетолог — задать вопрос ИИ\n"
                "⭐ Избранное — сохранять блюда\n"
                "🔥 Стрик — дни подряд",
                parse_mode="Markdown"
            )

        async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            users = load_users()
            uid = str(user.id)
            if uid not in users:
                users[uid] = {"name": user.first_name, "chat_id": update.effective_chat.id}
            users[uid]["reminders"] = True
            save_users(users)
            await update.message.reply_text(
                "🔔 *Напоминания включены!*\n\n"
                "Я буду напоминать тебе:\n"
                "🌅 09:00 — записать завтрак\n"
                "🌞 14:00 — записать обед\n"
                "🌆 19:00 — записать ужин\n\n"
                "Чтобы выключить — /stop_reminders",
                parse_mode="Markdown"
            )

        async def stop_reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            users = load_users()
            uid = str(user.id)
            if uid in users:
                users[uid]["reminders"] = False
                save_users(users)
            await update.message.reply_text("🔕 Напоминания выключены. Включить — /reminders")

        app_bot = Application.builder().token(BOT_TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("help", help_cmd))
        app_bot.add_handler(CommandHandler("reminders", reminders_cmd))
        app_bot.add_handler(CommandHandler("stop_reminders", stop_reminders_cmd))
        await app_bot.initialize()
        await app_bot.start()
        await app_bot.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot polling started")

        # Start reminder task
        asyncio.create_task(reminder_loop(app_bot.bot))

    except Exception as e:
        logger.error(f"Bot error: {e}")

# ── REMINDERS ──
async def reminder_loop(bot):
    """Send reminders at 9:00, 14:00, 19:00 (MSK)"""
    # MSK = UTC+3
    msk = timezone(timedelta(hours=3))
    reminder_times = [
        (9, 0, "🌅 Доброе утро! Не забудь записать завтрак в MealMeter 🥐"),
        (14, 0, "🌞 Время обеда! Сфотографируй еду и добавь в дневник 🍽️"),
        (19, 0, "🌆 Как прошёл день? Запиши ужин и проверь прогресс по калориям 📊"),
    ]
    sent_today = set()

    while True:
        try:
            now = datetime.now(msk)
            current_key = (now.date(), now.hour, now.minute)

            for hour, minute, msg in reminder_times:
                key = (now.date(), hour, minute)
                if now.hour == hour and now.minute == minute and key not in sent_today:
                    users = load_users()
                    for uid, u in users.items():
                        if u.get("reminders"):
                            try:
                                await bot.send_message(chat_id=u["chat_id"], text=msg)
                            except Exception as e:
                                logger.error(f"Reminder send error for {uid}: {e}")
                    sent_today.add(key)
                    # Cleanup old keys
                    sent_today = {k for k in sent_today if k[0] == now.date()}

            await asyncio.sleep(45)  # check every 45 seconds
        except Exception as e:
            logger.error(f"Reminder loop error: {e}")
            await asyncio.sleep(60)

# ── MAIN ──
async def main():
    app_web = web.Application(client_max_size=50*1024*1024)
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
