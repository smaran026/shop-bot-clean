import os
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 1228141945
DATA_FILE = "data.json"
BUYERS_PER_WEEK = 7

# Initial members (edit if needed)
DEFAULT_MEMBERS = [
"Руслан","Dimario","madness","Эд","CITADEL - VIP",
"Татьяна Русакова","Умар Раисов","Nikolay Kopnin",
"Jonce","Vladimir","Если честно...","Idris Mayar",
"Горыныч","@AK1200083","DeletE Маккейн",
"Smaran Shetty","Максим","Антон Суханов",
"Александр","Юрий","AIFFAI","Владимир","Эдгар Левин"
]

# ---------- Data Handling ----------

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "rotation": DEFAULT_MEMBERS.copy(),
            "hold": {},          # {index: {"days": X, "offenses": Y}}
            "swap": [],          # list of indices
            "current_week": [],
            "last_run": ""
        }
        save_data(data)
        return data

    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# ---------- Helper ----------

def is_admin(user_id):
    return user_id == ADMIN_ID

def next_monday_530_ist():
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    days_ahead = (0 - now.weekday()) % 7
    target = now + timedelta(days=days_ahead)
    target = target.replace(hour=17, minute=30, second=0, microsecond=0)
    return target

def run_weekly_rotation():
    global data

    # Reduce hold days
    to_remove = []
    for idx in data["hold"]:
        data["hold"][idx]["days"] -= 1
        if data["hold"][idx]["days"] <= 0:
            to_remove.append(idx)
    for idx in to_remove:
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
