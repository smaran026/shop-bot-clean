import os
import json
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

week_counter = 0
HOLD_FILE = "hold.json"


# -------- Load Members --------
def load_members():
    members = []
    with open("members.txt", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                num, name = line.strip().split(",", 1)
                members.append((int(num), name))
    return sorted(members)


# -------- Hold Data --------
def load_hold():
    if not os.path.exists(HOLD_FILE):
        return {}
    with open(HOLD_FILE, "r") as f:
        return json.load(f)


def save_hold(data):
    with open(HOLD_FILE, "w") as f:
        json.dump(data, f)


def clean_hold():
    data = load_hold()
    today = datetime.date.today().isoformat()

    to_remove = []
    for num, info in data.items():
        if info["until"] < today:
            to_remove.append(num)

    for num in to_remove:
        del data[num]

    save_hold(data)


# -------- Weekly Generator --------
def generate_week():
    global week_counter

    clean_hold()
    hold_data = load_hold()

    members = load_members()

    active_members = [m for m in members if str(m[0]) not in hold_data]

    if len(active_members) == 0:
        return "All members are on hold."

    total = len(active_members)
    start = (week_counter * 7) % total
    end = start + 7

    tokens = []
    for i in range(start, end):
        tokens.append(active_members[i % total][1])

    rev_members = list(reversed(active_members))
    start_paws = (week_counter * 7) % total
    end_paws = start_paws + 7

    paws = []
    for i in range(start_paws, end_paws):
        paws.append(rev_members[i % total][1])

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
    await update.message.reply_text("Clan Rotation Bot active.")


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_week())


async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    members = load_members()
    text = "Members:\n"
    for num, name in members:
        text += f"{num}. {name}\n"
    await update.message.reply_text(text)


async def hold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /hold <number> <days>")
        return

    num = context.args[0]
    days = int(context.args[1])

    data = load_hold()
    until = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

    if num in data:
        data[num]["offense"] += 1
    else:
        data[num] = {"until": until, "offense": 1}

    data[num]["until"] = until
    save_hold(data)

    await update.message.reply_text(f"Member {num} on hold for {days} days.")


async def unhold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return

    num = context.args[0]
    data = load_hold()

    if num in data:
        del data[num]
        save_hold(data)
        await update.message.reply_text(f"Member {num} removed from hold.")


async def holdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_hold()

    if not data:
        await update.message.reply_text("No members on hold.")
        return

    text = "Hold List:\n"
    for num, info in data.items():
        text += f"{num} | Until: {info['until']} | Offense: {info['offense']}\n"

    await update.message.reply_text(text)


# -------- Scheduler --------
async def scheduled_week(context: ContextTypes.DEFAULT_TYPE):
    text = generate_week()
    await context.bot.send_message(chat_id=context.job.chat_id, text=text)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("members", members))
    app.add_handler(CommandHandler("hold", hold))
    app.add_handler(CommandHandler("unhold", unhold))
    app.add_handler(CommandHandler("holdlist", holdlist))

    job_queue = app.job_queue

    # Monday 5:30 PM IST = 12:00 UTC
    CHAT_ID = None
    time_utc = datetime.time(hour=12, minute=0)

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
