import os
import json
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

week_counter = 0
HOLD_FILE = "hold.json"
CHAT_ID = None   # Optional: set your group ID later for auto notifications


# ---------- Members ----------
def load_members():
    members = {}
    with open("members.txt", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                num, name = line.strip().split(",", 1)
                members[int(num)] = name
    return members


# ---------- Hold Data ----------
def load_hold():
    if not os.path.exists(HOLD_FILE):
        return {}
    with open(HOLD_FILE, "r") as f:
        return json.load(f)


def save_hold(data):
    with open(HOLD_FILE, "w") as f:
        json.dump(data, f)


async def clean_hold_and_notify(app):
    data = load_hold()
    members = load_members()
    today = datetime.date.today().isoformat()

    removed = []

    for num in list(data.keys()):
        if data[num]["until"] < today:
            removed.append(num)
            del data[num]

    if removed:
        save_hold(data)
        if CHAT_ID:
            text = "Hold expired:\n"
            for num in removed:
                name = members.get(int(num), "Unknown")
                text += f"{num} - {name}\n"
            await app.bot.send_message(chat_id=CHAT_ID, text=text)


# ---------- Weekly Queue ----------
def generate_week():
    global week_counter

    members = load_members()
    hold_data = load_hold()

    # Remove held members
    active = [ (num, name) for num, name in members.items() if str(num) not in hold_data ]

    if len(active) == 0:
        return "All members are on hold."

    active.sort()
    total = len(active)

    # Invitation Tokens (forward)
    start = (week_counter * 7) % total
    tokens = []
    for i in range(7):
        tokens.append(active[(start + i) % total][1])

    # Paws (reverse)
    rev = list(reversed(active))
    start2 = (week_counter * 7) % total
    paws = []
    for i in range(7):
        paws.append(rev[(start2 + i) % total][1])

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
    await clean_hold_and_notify(context.application)
    await update.message.reply_text(generate_week())


async def members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    members = load_members()
    text = "Members:\n"
    for num in sorted(members):
        text += f"{num}. {members[num]}\n"
    await update.message.reply_text(text)


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

    data = load_hold()
    until = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

    if num in data:
        data[num]["offense"] += 1
    else:
        data[num] = {"offense": 1}

    data[num]["until"] = until
    save_hold(data)

    name = members[int(num)]
    await update.message.reply_text(f"{name} on hold for {days} days.")


async def unhold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return

    num = context.args[0]
    data = load_hold()
    members = load_members()

    if num in data:
        del data[num]
        save_hold(data)
        name = members.get(int(num), "Unknown")
        await update.message.reply_text(f"{name} removed from hold.")


async def holdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_hold()
    members = load_members()

    if not data:
        await update.message.reply_text("No members on hold.")
        return

    text = "Hold List:\n"
    for num, info in data.items():
        name = members.get(int(num), "Unknown")
        text += f"{num}. {name} | Until: {info['until']} | Offense: {info['offense']}\n"

    await update.message.reply_text(text)


# ---------- Scheduler ----------
async def scheduled_week(context: ContextTypes.DEFAULT_TYPE):
    await clean_hold_and_notify(context.application)
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

    # Weekly auto post (optional)
    job_queue = app.job_queue
    if CHAT_ID:
        time_utc = datetime.time(hour=12, minute=0)  # Monday 5:30 PM IST
        job_queue.run_daily(
            scheduled_week,
            time=time_utc,
            days=(0,),
            chat_id=CHAT_ID
        )

    app.run_polling()


if __name__ == "__main__":
    main()
