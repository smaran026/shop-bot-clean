import os
import json
from datetime import datetime, timedelta, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

MEMBERS_FILE = "members.json"
HOLD_FILE = "hold.json"

GROUP_SIZE = 7
IST_OFFSET = timedelta(hours=5, minutes=30)

# ------------------ FILE HELPERS ------------------

def load_members():
    with open(MEMBERS_FILE, "r") as f:
        return json.load(f)

def save_members(data):
    with open(MEMBERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_hold():
    if not os.path.exists(HOLD_FILE):
        return {}
    with open(HOLD_FILE, "r") as f:
        return json.load(f)

def save_hold(data):
    with open(HOLD_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ------------------ TIME LOGIC ------------------

def now_ist():
    return datetime.utcnow() + IST_OFFSET

def next_monday_530(after_date):
    target = after_date + timedelta(days=30)

    days_ahead = 0 - target.weekday()  # Monday = 0
    if days_ahead <= 0:
        days_ahead += 7

    next_monday = target + timedelta(days=days_ahead)
    return datetime.combine(next_monday.date(), time(17, 30))

# ------------------ HOLD PROCESSING ------------------

def process_expired_holds():
    hold = load_hold()
    members = load_members()
    now = now_ist()

    changed = False

    for mid in list(hold.keys()):
        return_time = datetime.fromisoformat(hold[mid]["return_time"])
        if now >= return_time:
            # Move member to end
            member = next(m for m in members if m["id"] == int(mid))
            members = [m for m in members if m["id"] != int(mid)]
            members.append(member)

            del hold[mid]
            changed = True

    if changed:
        save_members(members)
        save_hold(hold)

# ------------------ QUEUE ------------------

def active_members():
    process_expired_holds()
    members = load_members()
    hold = load_hold()
    return [m for m in members if str(m["id"]) not in hold]

def week_number():
    start = datetime(2026, 1, 5)  # Monday reference
    now = now_ist()
    return ((now - start).days // 7)

def get_week_groups():
    members = active_members()
    w = week_number()

    start = (w * GROUP_SIZE) % len(members)

    invitation = []
    for i in range(GROUP_SIZE):
        invitation.append(members[(start + i) % len(members)])

    paws = [m for m in members if m not in invitation]

    return invitation, paws

# ------------------ COMMANDS ------------------

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    invitation, paws = get_week_groups()

    msg = "📅 This Week\n\n"
    msg += "Invitation Tokens:\n"
    for m in invitation:
        msg += f"{m['id']}. {m['name']}\n"

    msg += "\nPaws:\n"
    for m in paws:
        msg += f"{m['id']}. {m['name']}\n"

    await update.message.reply_text(msg)

async def queues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    members = load_members()
    msg = "Full Queue Order:\n"
    for m in members:
        msg += f"{m['id']}. {m['name']}\n"

    await update.message.reply_text(msg)

async def hold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /hold <number>")
        return

    mid = context.args[0]
    hold = load_hold()
    members = load_members()

    member = next((m for m in members if str(m["id"]) == mid), None)
    if not member:
        await update.message.reply_text("Invalid member number")
        return

    return_time = next_monday_530(now_ist())

    hold[mid] = {
        "name": member["name"],
        "return_time": return_time.isoformat()
    }

    save_hold(hold)

    await update.message.reply_text(
        f"{member['name']} on hold.\nReturns: {return_time.strftime('%d %b %Y, %I:%M %p IST')}"
    )

async def unhold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    mid = context.args[0]
    hold = load_hold()

    if mid in hold:
        del hold[mid]
        save_hold(hold)
        await update.message.reply_text("Removed from hold")

async def holdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hold = load_hold()

    if not hold:
        await update.message.reply_text("No members on hold")
        return

    msg = "Hold List:\n"
    for mid, data in hold.items():
        rt = datetime.fromisoformat(data["return_time"])
        msg += f"{mid}. {data['name']} → {rt.strftime('%d %b %Y')}\n"

    await update.message.reply_text(msg)

# NEW FUNCTION
async def swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /swap A B")
        return

    a, b = int(context.args[0]), int(context.args[1])
    members = load_members()

    idx_a = next(i for i,m in enumerate(members) if m["id"] == a)
    idx_b = next(i for i,m in enumerate(members) if m["id"] == b)

    members[idx_a], members[idx_b] = members[idx_b], members[idx_a]
    save_members(members)

    await update.message.reply_text("Members swapped")

# ------------------ START ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Clan Rotation Bot Active")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("queues", queues))
    app.add_handler(CommandHandler("hold", hold))
    app.add_handler(CommandHandler("unhold", unhold))
    app.add_handler(CommandHandler("holdlist", holdlist))
    app.add_handler(CommandHandler("swap", swap))

    app.run_polling()

if __name__ == "__main__":
    main()
