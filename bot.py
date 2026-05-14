import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-vercel-app.vercel.app")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "друг"

    keyboard = [[
        InlineKeyboardButton(
            text="🍽️ Открыть MealMeter",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Привет, {name}!\n\n"
        f"🍏 *MealMeter* — твой умный счётчик калорий.\n\n"
        f"📸 Просто сфотографируй блюдо и ИИ автоматически подсчитает:\n"
        f"• Калории\n"
        f"• Белки, жиры, углеводы\n"
        f"• Полезность блюда\n\n"
        f"Нажми кнопку ниже чтобы начать 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *MealMeter — помощь*\n\n"
        "*/start* — открыть приложение\n\n"
        "Как пользоваться:\n"
        "1. Нажми «Открыть MealMeter»\n"
        "2. При первом входе введи API ключ Anthropic\n"
        "3. Нажми «+ Добавить» и сфотографируй блюдо\n"
        "4. ИИ проанализирует и покажет КБЖУ\n"
        "5. Добавь в дневник одним нажатием\n\n"
        "📊 Следи за прогрессом в календаре!",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    logger.info("MealMeter bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
