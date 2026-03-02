import os
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

week_counter = 0


# -------- Load Members from File --------
def load_members():
    members = []
    try:
        with open("members.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    num, name = line.strip().split(",", 1)
                    members.append(name)
    except:
        members = []
    return members


# -------- Generate Weekly Lists --------
def generate_week():
    global week_counter
    members = load_members()

    if len(members) == 0:
        return "No members found."

    total = len(members)
    start = (week_counter * 7) % total
    end = start + 7

    # Invitation Tokens (forward rotation)
    tokens = []
    for i in range(start, end):
        tokens.append(members[i % total])

    # Paws (reverse rotation)
    rev_members = list(reversed(members))
    start_paws = (week_counter * 7) % total
    end_paws = start_paws + 7

    paws = []
    for i in range(start_paws, end_paws):
        paws.append(rev_members[i % total])

    week_counter += 1

    text = f"Week {week_counter}\n\n"
    text += "Invitation Tokens:\n"
    for i, name in enumerate(tokens, 1):
        text += f"{i}. {name}\n"

    text += "\nPaws:\n"
    for i, name in enumerate(paws, 1):
        text += f"{i}. {name}\n"

    return text


# -------- Commands --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Clan Rotation Bot is active.")


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = generate_week()
    await update.message.reply_text(text)


# -------- Scheduler (Monday 5:30 PM IST) --------
async def scheduled_week(context: ContextTypes.DEFAULT_TYPE):
    text = generate_week()
    await context.bot.send_message(chat_id=context.job.chat_id, text=text)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))

    # Scheduler setup
    job_queue = app.job_queue

    # Monday 5:30 PM IST = 12:00 UTC
    time_utc = datetime.time(hour=12, minute=0)

    # Replace YOUR TELEGRAM GROUP ID here later
    CHAT_ID = None

    if CHAT_ID:
        job_queue.run_daily(
            scheduled_week,
            time=time_utc,
            days=(0,),
            chat_id=CHAT_ID
        )

    app.run_polling()


if __name__ == "__main__":
    main()
