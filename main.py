import os
import json
from datetime import datetime, timedelta, time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

ADMIN_ID = 1228141945
GROUP_CHAT_ID = None  # PUT YOUR GROUP ID HERE (-100xxxxxxxx)

MEMBERS_FILE = "members.json"
TOKENS_QUEUE_FILE = "tokens_queue.json"
PAWS_QUEUE_FILE = "paws_queue.json"
HOLD_FILE = "hold.json"

GROUP_SIZE = 7
IST_OFFSET = timedelta(hours=5, minutes=30)


# ------------------ BASIC HELPERS ------------------

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


def is_admin(update: Update):
    return update.effective_user.id == ADMIN_ID


# ------------------ MEMBERS ------------------

def load_members():
    return load_json(MEMBERS_FILE, [])


def initialize_queues():
    members = load_members()
    ids = [m["id"] for m in members]

    if not os.path.exists(TOKENS_QUEUE_FILE):
        save_json(TOKENS_QUEUE_FILE, ids)

    if not os.path.exists(PAWS_QUEUE_FILE):
        save_json(PAWS_QUEUE_FILE, ids)


# ------------------ HOLD ------------------

def clean_expired_holds():
    hold = load_json(HOLD_FILE, {})
    now = now_ist()

    changed = False
    for mid in list(hold.keys()):
        if now >= datetime.fromisoformat(hold[mid]):
            del hold[mid]
            changed = True

    if changed:
        save_json(HOLD_FILE, hold)

    return hold


def active_member_ids():
    members = load_members()
    ids = [m["id"] for m in members]
    hold = clean_expired_holds()
    blocked = set(int(x) for x in hold.keys())
    return [i for i in ids if i not in blocked]


# ------------------ WEEK CALCULATION ------------------

def week_number(offset=0):
    ref = datetime(2026, 1, 5)
    return ((now_ist() - ref).days // 7) + offset


def generate_week(offset=0):
    initialize_queues()

    members = load_members()
    member_map = {m["id"]: m["name"] for m in members}

    active_ids = active_member_ids()

    tokens_queue = load_json(TOKENS_QUEUE_FILE, [])
    paws_queue = load_json(PAWS_QUEUE_FILE, [])

    tokens_queue = [i for i in tokens_queue if i in active_ids]
    paws_queue = [i for i in paws_queue if i in active_ids]

    if len(tokens_queue) < GROUP_SIZE:
        return "Not enough active members."

    w = week_number(offset)

    start_t = (w * GROUP_SIZE) % len(tokens_queue)
    tokens_ids = [
        tokens_queue[(start_t + i) % len(tokens_queue)]
        for i in range(GROUP_SIZE)
    ]

    paws_candidates = [i for i in paws_queue if i not in tokens_ids]

    if len(paws_candidates) < GROUP_SIZE:
        return "Not enough members for paws."

    start_p = (w * GROUP_SIZE) % len(paws_candidates)
    paws_ids = [
        paws_candidates[(start_p + i) % len(paws_candidates)]
        for i in range(GROUP_SIZE)
    ]

    text = f"Week {w+1}\n\n"

    text += "Invitation Tokens:\n"
    for mid in tokens_ids:
        text += f"{mid}. {member_map[mid]}\n"

    text += "\nPaws:\n"
    for mid in paws_ids:
        text += f"{mid}. {member_map[mid]}\n"

    return text


# ------------------ COMMANDS ------------------

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_week())


async def nextweek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_week(offset=1))


async def rotation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    initialize_queues()

    members = load_members()
    member_map = {m["id"]: m["name"] for m in members}
    active_ids = active_member_ids()

    tokens_queue = load_json(TOKENS_QUEUE_FILE, [])
    paws_queue = load_json(PAWS_QUEUE_FILE, [])

    tokens_queue = [i for i in tokens_queue if i in active_ids]
    paws_queue = [i for i in paws_queue if i in active_ids]

    w = week_number()

    start_t = (w * GROUP_SIZE) % len(tokens_queue)
    ordered_tokens = [
        tokens_queue[(start_t + i) % len(tokens_queue)]
        for i in range(len(tokens_queue))
    ]

    current_tokens = ordered_tokens[:GROUP_SIZE]
    paws_candidates = [i for i in paws_queue if i not in current_tokens]

    start_p = (w * GROUP_SIZE) % len(paws_candidates)
    ordered_paws = [
        paws_candidates[(start_p + i) % len(paws_candidates)]
        for i in range(len(paws_candidates))
    ]

    text = "Current Rotation Flow\n\n"

    text += "Invitation Tokens Order:\n"
    for mid in ordered_tokens:
        text += f"{mid}. {member_map.get(mid,'Unknown')}\n"

    text += "\nPaws Order:\n"
    for mid in ordered_paws:
        text += f"{mid}. {member_map.get(mid,'Unknown')}\n"

    await update.message.reply_text(text)


async def swap_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or len(context.args) != 2:
        return

    if not context.args[0].isdigit() or not context.args[1].isdigit():
        return

    a, b = int(context.args[0]), int(context.args[1])
    q = load_json(TOKENS_QUEUE_FILE, [])

    if a in q and b in q:
        ia, ib = q.index(a), q.index(b)
        q[ia], q[ib] = q[ib], q[ia]
        save_json(TOKENS_QUEUE_FILE, q)
        await update.message.reply_text("Tokens queue updated.")


async def swap_paws(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or len(context.args) != 2:
        return

    if not context.args[0].isdigit() or not context.args[1].isdigit():
        return

    a, b = int(context.args[0]), int(context.args[1])
    q = load_json(PAWS_QUEUE_FILE, [])

    if a in q and b in q:
        ia, ib = q.index(a), q.index(b)
        q[ia], q[ib] = q[ib], q[ia]
        save_json(PAWS_QUEUE_FILE, q)
        await update.message.reply_text("Paws queue updated.")


async def hold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or not context.args:
        return

    if not context.args[0].isdigit():
        return

    mid = context.args[0]
    hold = load_json(HOLD_FILE, {})
    hold[mid] = (now_ist() + timedelta(days=30)).isoformat()
    save_json(HOLD_FILE, hold)

    await update.message.reply_text(f"{mid} placed on 30-day hold.")


async def holdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hold = load_json(HOLD_FILE, {})
    members = load_members()
    member_map = {m["id"]: m["name"] for m in members}

    if not hold:
        await update.message.reply_text("No members on hold.")
        return

    text = "Hold List:\n\n"
    for mid, return_time in hold.items():
        rt = datetime.fromisoformat(return_time)
        text += f"{mid}. {member_map.get(int(mid),'Unknown')} → {rt.strftime('%d %b %Y %H:%M')}\n"

    await update.message.reply_text(text)


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message with /mute <hours>")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: reply + /mute <hours>")
        return

    hours = int(context.args[0])
    user_id = update.message.reply_to_message.from_user.id
    until = datetime.utcnow() + timedelta(hours=hours)

    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until
    )

    await update.message.reply_text("User muted.")


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message with /unmute")
        return

    user_id = update.message.reply_to_message.from_user.id

    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=ChatPermissions(can_send_messages=True)
    )

    await update.message.reply_text("User unmuted.")


# ------------------ MONDAY AUTO POST ------------------

async def monday_post(context: ContextTypes.DEFAULT_TYPE):
    if GROUP_CHAT_ID:
        text = generate_week()
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)


# ------------------ MAIN ------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("nextweek", nextweek))
    app.add_handler(CommandHandler("rotation", rotation))
    app.add_handler(CommandHandler("swap_tokens", swap_tokens))
    app.add_handler(CommandHandler("swap_paws", swap_paws))
    app.add_handler(CommandHandler("hold", hold))
    app.add_handler(CommandHandler("holdlist", holdlist))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))

    job_queue = app.job_queue
    if GROUP_CHAT_ID:
        job_queue.run_daily(
            monday_post,
            time=time(hour=12, minute=0),  # 5:30 PM IST
            days=(0,)
        )

    app.run_polling()


if __name__ == "__main__":
    main()
