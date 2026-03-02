import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Shop Bot is running.")

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Weekly queue will appear here.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))

    app.run_polling()

if __name__ == "__main__":
    main()
