import os
import json
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

week_counter = 0
HOLD_FILE = "hold.json"
PENDING_FILE = "pending_return.json"
MEMBER_FILE = "members.txt"

CHAT_ID = None  # Put group ID later for auto messages


# ---------- Members ----------
def load_members():
    members = {}
    with open(MEMBER_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                num, name = line.strip().split(",", 1)
                members[int(num)] = name
    return members


# ---------- Hold ----------
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


# ---------- Hold Expiry Check ----------
async def check_hold_expiry(app):
    hold = load_json(HOLD_FILE)
    pending = load_json(PENDING_FILE)
    members = load_members()

    today = datetime.date.today().isoformat()
    expired = []

    for num in list(hold.keys()):
        if hold[num]["until"] < today:
            expired.append(num)
            pending[num] = True
            del hold[num]

    if expired:
        save_json(HOLD_FILE, hold)
        save_json(PENDING_FILE, pending)

        if CHAT_ID:
            text = "Hold expired (will join next weekly cycle):\n"
            for num in expired:
                name = members.get(int(num), "Unknown")
                text += f"{num} - {name}\n"
            await app.bot.send_message(chat_id=CHAT_ID, text=text)


# ---------- Weekly Queue ----------
def generate_week():
    global week_counter

    members = load_members()
    hold = load_json(HOLD_FILE)
    pending = load_json(PENDING_FILE)

    # Active members = not on hold
    active = [num for num in members if str(num) not in hold]

    # Sort base order
    active.sort()

    # Move pending_return members to end
    end_list = [int(num) for num in pending.keys() if int(num) in active]
    active = [num for num in active if num not in end_list] + end_list

    # Clear pending after placing
    save_json(PENDING_FILE, {})

    total = len(active)
    if total == 0:
        return "No active members."

    # Forward list
    start = (week_counter * 7) % total
    tokens = []
    for i in range(7):
        tokens.append(members[active[(start + i) % total]])

    # Reverse list
    rev = list(reversed(active))
    start2 = (week_counter * 7) % total
    paws = []
    for i in range(7):
        paws.append(members[rev[(start2 + i) % total]])

    week_counter += 1

    text = f"Week {week_counter}\n\n"
    text += "Invitation Tokens:\n"
    for i, name in enumerate(tokens, 1):
        text += f"{i}. {name}\n"

    text += "\nPaws:\n"
    for i, name in enumerate(paws, 1):
        text += f"{i}. {name}\n"

    return text


# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Clan Rotation Bot active.")


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_hold_expiry(context.application)
    await update.message.reply_text(generate_week())


async def hold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /hold <number> <days>")
        return

    num = context.args[0]
    days = int(context.args[1])

    members = load_members()
    if int(num) not in members:
        await update.message.reply_text("Member not found.")
        return

    hold = load_json(HOLD_FILE)
    until = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

    if num in hold:
        hold[num]["offense"] += 1
    else:
        hold[num] = {"offense": 1}

    hold[num]["until"] = until
    save_json(HOLD_FILE, hold)

    await update.message.reply_text(
        f"{members[int(num)]} on hold for {days} days (will return next weekly cycle)."
    )


async def holdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hold = load_json(HOLD_FILE)
    members = load_members()

    if not hold:
        await update.message.reply_text("No members on hold.")
        return

    text = "Hold List:\n"
    for num, info in hold.items():
        name = members.get(int(num), "Unknown")
        text += f"{num}. {name} | Until: {info['until']} | Offense: {info['offense']}\n"

    await update.message.reply_text(text)


# ---------- Scheduler ----------
async def weekly_job(context: ContextTypes.DEFAULT_TYPE):
    await check_hold_expiry(context.application)
    text = generate_week()
    await context.bot.send_message(chat_id=context.job.chat_id, text=text)


async def daily_hold_check(context: ContextTypes.DEFAULT_TYPE):
    await check_hold_expiry(context.application)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("hold", hold))
    app.add_handler(CommandHandler("holdlist", holdlist))

    job_queue = app.job_queue

    if CHAT_ID:
        # Daily expiry check
        job_queue.run_daily(daily_hold_check, time=datetime.time(hour=0, minute=0))

        # Monday 5:30 PM IST (12:00 UTC)
        job_queue.run_daily(
            weekly_job,
            time=datetime.time(hour=12, minute=0),
            days=(0,),
            chat_id=CHAT_ID
        )

    app.run_polling()


if __name__ == "__main__":
    main()
