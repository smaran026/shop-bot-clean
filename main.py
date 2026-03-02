import os
import json
from datetime import datetime, timedelta, time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

MEMBERS_FILE = "members.json"
TOKENS_QUEUE_FILE = "tokens_queue.json"
PAWS_QUEUE_FILE = "paws_queue.json"
HOLD_FILE = "hold.json"
COOLDOWN_FILE = "cooldown.json"

GROUP_SIZE = 7
IST_OFFSET = timedelta(hours=5, minutes=30)

# ---------- Helpers ----------

def now_ist():
    return datetime.utcnow() + IST_OFFSET

def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)
        return default
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# ---------- Load Members ----------

def load_members():
    return load_json(MEMBERS_FILE, [])

def initialize_queues():
    members = load_members()
    ids = [m["id"] for m in members]

    tokens = load_json(TOKENS_QUEUE_FILE, ids)
    paws = load_json(PAWS_QUEUE_FILE, ids)

    if not tokens:
        save_json(TOKENS_QUEUE_FILE, ids)
    if not paws:
        save_json(PAWS_QUEUE_FILE, ids)

# ---------- Restrictions ----------

def active_member_ids():
    members = load_members()
    ids = [m["id"] for m in members]

    hold = load_json(HOLD_FILE, {})
    cooldown = load_json(COOLDOWN_FILE, {})

    now = now_ist()

    # remove expired hold
    for mid in list(hold.keys()):
        if now >= datetime.fromisoformat(hold[mid]):
            del hold[mid]
    save_json(HOLD_FILE, hold)

    # remove expired cooldown
    for mid in list(cooldown.keys()):
        if now >= datetime.fromisoformat(cooldown[mid]):
            del cooldown[mid]
    save_json(COOLDOWN_FILE, cooldown)

    blocked = set(int(x) for x in hold.keys()) | set(int(x) for x in cooldown.keys())

    return [i for i in ids if i not in blocked]

# ---------- Weekly Selection ----------

def week_number():
    ref = datetime(2026, 1, 5)
    return ((now_ist() - ref).days) // 7

def generate_week():
    initialize_queues()

    members = load_members()
    member_map = {m["id"]: m["name"] for m in members}

    active_ids = active_member_ids()

    tokens_queue = load_json(TOKENS_QUEUE_FILE, [])
    paws_queue = load_json(PAWS_QUEUE_FILE, [])

    # Filter queues by active members
    tokens_queue = [i for i in tokens_queue if i in active_ids]
    paws_queue = [i for i in paws_queue if i in active_ids]

    w = week_number()

    start_t = (w * GROUP_SIZE) % len(tokens_queue)
    tokens_ids = []
    for i in range(GROUP_SIZE):
        tokens_ids.append(tokens_queue[(start_t + i) % len(tokens_queue)])

    # Paws: pick 7 that are not in tokens
    paws_candidates = [i for i in paws_queue if i not in tokens_ids]

    start_p = (w * GROUP_SIZE) % len(paws_candidates)
    paws_ids = []
    for i in range(GROUP_SIZE):
        paws_ids.append(paws_candidates[(start_p + i) % len(paws_candidates)])

    text = f"Week {w+1}\n\n"

    text += "Invitation Tokens:\n"
    for mid in tokens_ids:
        text += f"{mid}. {member_map[mid]}\n"

    text += "\nPaws:\n"
    for mid in paws_ids:
        text += f"{mid}. {member_map[mid]}\n"

    return text

# ---------- Commands ----------

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_week())

# Permanent swap inside Tokens queue
async def swap_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        return

    a, b = int(context.args[0]), int(context.args[1])
    q = load_json(TOKENS_QUEUE_FILE, [])

    if a in q and b in q:
        ia, ib = q.index(a), q.index(b)
        q[ia], q[ib] = q[ib], q[ia]
        save_json(TOKENS_QUEUE_FILE, q)
        await update.message.reply_text("Tokens queue updated")

# Permanent swap inside Paws queue
async def swap_paws(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        return

    a, b = int(context.args[0]), int(context.args[1])
    q = load_json(PAWS_QUEUE_FILE, [])

    if a in q and b in q:
        ia, ib = q.index(a), q.index(b)
        q[ia], q[ib] = q[ib], q[ia]
        save_json(PAWS_QUEUE_FILE, q)
        await update.message.reply_text("Paws queue updated")

# Hold (30 days → next Monday handled automatically)
async def hold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    mid = context.args[0]
    hold = load_json(HOLD_FILE, {})

    return_time = now_ist() + timedelta(days=30)
    hold[mid] = return_time.isoformat()
    save_json(HOLD_FILE, hold)

    await update.message.reply_text(f"{mid} on hold for 30 days")

# Cooldown (1 day)
async def cooldown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    mid = context.args[0]
    cd = load_json(COOLDOWN_FILE, {})
    cd[mid] = (now_ist() + timedelta(days=1)).isoformat()
    save_json(COOLDOWN_FILE, cd)

    await update.message.reply_text(f"{mid} on cooldown for 1 day")

# ---------- Main ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("swap_tokens", swap_tokens))
    app.add_handler(CommandHandler("swap_paws", swap_paws))
    app.add_handler(CommandHandler("hold", hold))
    app.add_handler(CommandHandler("cooldown", cooldown))

    app.run_polling()

if __name__ == "__main__":
    main()
