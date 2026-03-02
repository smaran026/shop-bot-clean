import os
import json
from datetime import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1228141945

DATA_FILE = "data.json"
MEMBERS_FILE = "members.json"
BUYERS_PER_WEEK = 7

# ---------- Load Members ----------
def load_members():
    with open(MEMBERS_FILE, "r", encoding="utf-8") as f:
        members = json.load(f)
    return members

members_data = load_members()
member_lookup = {m["name"]: m["id"] for m in members_data}
member_names = [m["name"] for m in members_data]

# ---------- Data ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "inv_queue": member_names.copy(),
            "paws_queue": member_names.copy(),
            "current_inv": [],
            "current_paws": []
        }
        save_data(data)
        return data

    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def is_admin(user_id):
    return user_id == ADMIN_ID

# ---------- Weekly Logic ----------
def generate_week():
    global data

    inv_queue = data["inv_queue"]
    paws_queue = data["paws_queue"]

    # Invitation → first 7
    invitation_week = inv_queue[:BUYERS_PER_WEEK]

    # Paws → from end, avoid overlap
    paws_week = []
    for name in reversed(paws_queue):
        if name not in invitation_week:
            paws_week.append(name)
        if len(paws_week) == BUYERS_PER_WEEK:
            break

    data["current_inv"] = invitation_week
    data["current_paws"] = paws_week

    # Rotate queues
    data["inv_queue"] = inv_queue[BUYERS_PER_WEEK:] + inv_queue[:BUYERS_PER_WEEK]
    data["paws_queue"] = paws_queue[-BUYERS_PER_WEEK:] + paws_queue[:-BUYERS_PER_WEEK]

    save_data(data)

# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Clan Rotation Bot Active")

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["current_inv"]:
        await update.message.reply_text("No week generated yet.")
        return

    msg = "📅 Weekly Buyers\n\n"

    msg += "🎟 Invitation Tokens:\n"
    for name in data["current_inv"]:
        msg += f"{member_lookup[name]}. {name}\n"

    msg += "\n🐾 Paws:\n"
    for name in data["current_paws"]:
        msg += f"{member_lookup[name]}. {name}\n"

    msg += "\nReset: Monday 5:30 PM IST"

    await update.message.reply_text(msg)

async def full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Full Members List:\n"
    for m in members_data:
        msg += f"{m['id']}. {m['name']}\n"
    await update.message.reply_text(msg)

# ---------- Scheduler ----------
async def weekly_job(context: ContextTypes.DEFAULT_TYPE):
    generate_week()
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="Weekly rotation generated"
    )

# ---------- Main ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("full", full))

    # Monday 5:30 PM IST = 12:00 UTC
    job_queue = app.job_queue
    job_queue.run_daily(
        weekly_job,
        time=time(hour=12, minute=0)
    )

    app.run_polling()

if __name__ == "__main__":
    main()    for idx in to_remove:
        del data["hold"][idx]

    available = [
        i for i in range(len(data["rotation"]))
        if str(i) not in data["hold"]
    ]

    selected = []

    # Priority from swap queue
    for idx in data["swap"]:
        if idx in available and len(selected) < BUYERS_PER_WEEK:
            selected.append(idx)
            available.remove(idx)

    # Fill remaining from rotation order
    for idx in available:
        if len(selected) < BUYERS_PER_WEEK:
            selected.append(idx)

    data["current_week"] = selected

    # Move selected to end
    names = data["rotation"]
    selected_names = [names[i] for i in selected]
    remaining = [names[i] for i in range(len(names)) if i not in selected]
    data["rotation"] = remaining + selected_names

    data["swap"] = []
    data["last_run"] = str(datetime.utcnow())
    save_data(data)

# ---------- Commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Clan Rotation Bot Active")

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["current_week"]:
        await update.message.reply_text("No week generated yet.")
        return

    text = "This Week Buyers:\n"
    for idx in data["current_week"]:
        text += f"{idx+1}. {data['rotation'][idx]}\n"
    await update.message.reply_text(text)

async def full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Full Queue:\n"
    for i, name in enumerate(data["rotation"]):
        text += f"{i+1}. {name}\n"
    await update.message.reply_text(text)

async def request_swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        idx = int(context.args[0]) - 1
        if idx not in data["swap"]:
            data["swap"].append(idx)
            save_data(data)
            await update.message.reply_text("Added to swap queue.")
    except:
        await update.message.reply_text("Usage: /request <number>")

async def hold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        idx = int(context.args[0]) - 1
        days = int(context.args[1]) if len(context.args) > 1 else 7

        key = str(idx)
        offenses = data["hold"].get(key, {}).get("offenses", 0) + 1
        days += (offenses - 1) * 3

        data["hold"][key] = {"days": days, "offenses": offenses}
        save_data(data)

        await update.message.reply_text(
            f"Member {idx+1} on hold for {days} days. Offenses: {offenses}"
        )
    except:
        await update.message.reply_text("Usage: /hold <number> <days>")

async def holdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["hold"]:
        await update.message.reply_text("Hold list empty.")
        return

    text = "Hold List:\n"
    for idx, info in data["hold"].items():
        name = data["rotation"][int(idx)]
        text += f"{int(idx)+1}. {name} | Days: {info['days']} | Offenses: {info['offenses']}\n"
    await update.message.reply_text(text)

async def unhold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        idx = str(int(context.args[0]) - 1)
        if idx in data["hold"]:
            del data["hold"][idx]
            save_data(data)
            await update.message.reply_text("Removed from hold.")
    except:
        await update.message.reply_text("Usage: /unhold <number>")

# ---------- Scheduler ----------

async def scheduler(context: ContextTypes.DEFAULT_TYPE):
    run_weekly_rotation()
    await context.bot.send_message(chat_id=ADMIN_ID, text="Weekly rotation executed.")

# ---------- Main ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("full", full))
    app.add_handler(CommandHandler("request", request_swap))
    app.add_handler(CommandHandler("hold", hold))
    app.add_handler(CommandHandler("holdlist", holdlist))
    app.add_handler(CommandHandler("unhold", unhold))

    # Run scheduler every day (checks weekly logic)
    job_queue = app.job_queue
    job_queue.run_daily(scheduler, time=datetime.utcnow().time())

    app.run_polling()

if __name__ == "__main__":
    main()
