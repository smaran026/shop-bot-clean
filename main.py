import os
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

GROUP_SIZE = 7

MEMBERS_FILE = "members.json"
TOKENS_FILE = "tokens_queue.json"
PAWS_FILE = "paws_queue.json"

HOLD_T_FILE = "hold_tokens.json"
HOLD_P_FILE = "hold_paws.json"

ADMIN_IDS = [1228141945]

RESET_TEXT = "Reset / Сброс: Mon 17:30 IST • 12:00 GMT • 15:00 MSK"

TOKENS_LABEL = "Invitation Tokens x5 / Пригласительные токены x5"
PAWS_LABEL = "Restoration Tokens x100 / Токены восстановления x100"


def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file) as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


def members():
    return load_json(MEMBERS_FILE)


def member_map():
    return {m["id"]: m["name"] for m in members()}


def tokens_queue():
    return load_json(TOKENS_FILE)


def paws_queue():
    return load_json(PAWS_FILE)


def save_tokens(q):
    save_json(TOKENS_FILE, q)


def save_paws(q):
    save_json(PAWS_FILE, q)


def hold_tokens():
    return load_json(HOLD_T_FILE)


def hold_paws():
    return load_json(HOLD_P_FILE)


def save_hold_tokens(d):
    save_json(HOLD_T_FILE, d)


def save_hold_paws(d):
    save_json(HOLD_P_FILE, d)


def is_admin(uid):
    return uid in ADMIN_IDS


def week_index(offset=0):
    base = datetime(2026, 1, 5)
    today = datetime.utcnow()
    return ((today - base).days // 7) + offset


def rotate(queue, offset):
    start = (offset * GROUP_SIZE) % len(queue)
    return [queue[(start + i) % len(queue)] for i in range(len(queue))]


def week_range(offset=0):
    today = datetime.utcnow()
    monday = today - timedelta(days=today.weekday())
    start = monday + timedelta(weeks=offset)
    end = start + timedelta(days=6)
    return start.strftime("%b %d"), end.strftime("%b %d")


def friday_date(offset=0):
    today = datetime.utcnow()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4) + timedelta(weeks=offset)
    return friday.strftime("%b %d"), friday.strftime("%d %b")


def clean_holds():
    today = datetime.utcnow().date()

    ht = hold_tokens()
    hp = hold_paws()

    for k, v in list(ht.items()):
        if datetime.fromisoformat(v).date() < today:
            del ht[k]

    for k, v in list(hp.items()):
        if datetime.fromisoformat(v).date() < today:
            del hp[k]

    save_hold_tokens(ht)
    save_hold_paws(hp)


def apply_hold(queue, hold_dict):
    return [p for p in queue if str(p) not in hold_dict]


def calculate():

    clean_holds()

    tokens = tokens_queue()
    paws = paws_queue()

    ht = hold_tokens()
    hp = hold_paws()

    tokens = apply_hold(tokens, ht)
    paws = apply_hold(paws, hp)

    w = week_index()

    tokens = rotate(tokens, w)
    paws = rotate(paws, w)

    t1 = tokens[:GROUP_SIZE]
    t2 = tokens[GROUP_SIZE:GROUP_SIZE * 2]
    t3 = tokens[GROUP_SIZE * 2:GROUP_SIZE * 3]

    p1 = []
    for p in paws:
        if p not in t1 and len(p1) < GROUP_SIZE:
            p1.append(p)

    p2 = []
    for p in paws:
        if p not in t2 and p not in p1 and len(p2) < GROUP_SIZE:
            p2.append(p)

    p3 = []
    for p in paws:
        if p not in t3 and p not in p1 and p not in p2 and len(p3) < GROUP_SIZE:
            p3.append(p)

    return t1, p1, t2, p2, t3, p3, tokens, paws


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):

    t1, p1, _, _, _, _, _, _ = calculate()
    names = member_map()

    s, e = week_range(0)
    f_en, f_ru = friday_date(0)

    msg = f"📅 CURRENT WEEK / ТЕКУЩАЯ НЕДЕЛЯ\n{s} – {e}\n━━━━━━━━━━━━━━━━\n\n"

    msg += f"🎟 {TOKENS_LABEL}\n"
    for i in t1:
        msg += f"• {names[i]}\n"

    msg += f"\n🐾 {PAWS_LABEL}\n"
    for i in p1:
        msg += f"• {names[i]}\n"

    msg += f"\n━━━━━━━━━━━━━━━━\n{RESET_TEXT}\n\n"

    msg += f"If unclaimed till Friday ({f_en}) anyone can claim without penalty.\n"
    msg += f"Если не забрано до пятницы ({f_ru}), любой может забрать без штрафа."

    await update.message.reply_text(msg)


async def nextweek(update: Update, context: ContextTypes.DEFAULT_TYPE):

    _, _, t2, p2, _, _, _, _ = calculate()
    names = member_map()

    s, e = week_range(1)

    msg = f"📅 NEXT WEEK / СЛЕДУЮЩАЯ НЕДЕЛЯ\n{s} – {e}\n━━━━━━━━━━━━━━━━\n\n"

    msg += f"🎟 {TOKENS_LABEL}\n"
    for i in t2:
        msg += f"• {names[i]}\n"

    msg += f"\n🐾 {PAWS_LABEL}\n"
    for i in p2:
        msg += f"• {names[i]}\n"

    await update.message.reply_text(msg)


async def rotation(update: Update, context: ContextTypes.DEFAULT_TYPE):

    t1, p1, t2, p2, t3, p3, tokens, paws = calculate()
    names = member_map()

    s1, e1 = week_range(0)
    s2, e2 = week_range(1)
    s3, e3 = week_range(2)

    msg = "📊 ROTATION / РОТАЦИЯ\n━━━━━━━━━━━━━━━━\n\n"

    msg += f"📅 Current Week / Текущая неделя\n{s1} – {e1}\n\n"

    msg += f"🎟 {TOKENS_LABEL}\n"
    for i in t1:
        msg += f"• {names[i]}\n"

    msg += f"\n🐾 {PAWS_LABEL}\n"
    for i in p1:
        msg += f"• {names[i]}\n"

    msg += "\n━━━━━━━━━━━━━━━━\n"

    msg += f"📅 Next Week / Следующая неделя\n{s2} – {e2}\n\n"

    msg += f"🎟 {TOKENS_LABEL}\n"
    for i in t2:
        msg += f"• {names[i]}\n"

    msg += f"\n🐾 {PAWS_LABEL}\n"
    for i in p2:
        msg += f"• {names[i]}\n"

    msg += "\n━━━━━━━━━━━━━━━━\n"

    msg += f"📅 Week 3 / Неделя 3\n{s3} – {e3}\n\n"

    msg += f"🎟 {TOKENS_LABEL}\n"
    for i in t3:
        msg += f"• {names[i]}\n"

    msg += f"\n🐾 {PAWS_LABEL}\n"
    for i in p3:
        msg += f"• {names[i]}\n"

    msg += "\n━━━━━━━━━━━━━━━━\n📦 Reserve / Резерв\n"

    for i in tokens[GROUP_SIZE * 3:]:
        msg += f"• {names[i]}\n"

    msg += f"\n{RESET_TEXT}"

    await update.message.reply_text(msg)


async def swaptoken(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    a = int(context.args[0])
    b = int(context.args[1])

    q = tokens_queue()

    ia = q.index(a)
    ib = q.index(b)

    q[ia], q[ib] = q[ib], q[ia]

    save_tokens(q)

    await update.message.reply_text("Tokens swapped / Токены поменяны")


async def swappaw(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    a = int(context.args[0])
    b = int(context.args[1])

    q = paws_queue()

    ia = q.index(a)
    ib = q.index(b)

    q[ia], q[ib] = q[ib], q[ia]

    save_paws(q)

    await update.message.reply_text("Paws swapped / Лапы поменяны")


async def exportqueues(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tokens = tokens_queue()
    paws = paws_queue()
    names = member_map()

    msg = "QUEUE EXPORT / ЭКСПОРТ ОЧЕРЕДИ\n\n"

    msg += f"{TOKENS_LABEL}\n"
    for i, m in enumerate(tokens, 1):
        msg += f"{i}. {names[m]}\n"

    msg += f"\n{PAWS_LABEL}\n"
    for i, m in enumerate(paws, 1):
        msg += f"{i}. {names[m]}\n"

    await update.message.reply_text(msg)


async def idlist(update: Update, context: ContextTypes.DEFAULT_TYPE):

    names = member_map()

    msg = "CLAN IDS / ID ИГРОКОВ\n\n"

    for mid in sorted(names):
        msg += f"{mid}  {names[mid]}\n"

    await update.message.reply_text(msg)


async def holdT(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    mid = context.args[0]

    holds = hold_tokens()

    expiry = datetime.utcnow() + timedelta(days=30)

    if mid in holds:
        expiry = datetime.fromisoformat(holds[mid]) + timedelta(days=30)

    holds[mid] = expiry.isoformat()

    save_hold_tokens(holds)

    await update.message.reply_text("Token hold added / Пауза токенов добавлена")


async def holdP(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    mid = context.args[0]

    holds = hold_paws()

    expiry = datetime.utcnow() + timedelta(days=30)

    if mid in holds:
        expiry = datetime.fromisoformat(holds[mid]) + timedelta(days=30)

    holds[mid] = expiry.isoformat()

    save_hold_paws(holds)

    await update.message.reply_text("Paws hold added / Пауза лап добавлена")


async def holdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):

    names = member_map()

    ht = hold_tokens()
    hp = hold_paws()

    msg = "⏸ HOLD LIST / СПИСОК ПАУЗЫ\n━━━━━━━━━━━━━━━━\n\n"

    msg += f"🎟 {TOKENS_LABEL}\n"

    if ht:
        for k, v in ht.items():
            msg += f"{names[int(k)]} — {v[:10]}\n"
    else:
        msg += "None\n"

    msg += f"\n🐾 {PAWS_LABEL}\n"

    if hp:
        for k, v in hp.items():
            msg += f"{names[int(k)]} — {v[:10]}\n"
    else:
        msg += "None\n"

    await update.message.reply_text(msg)


async def unhold(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    mid = context.args[0]

    ht = hold_tokens()
    hp = hold_paws()

    if mid in ht:
        del ht[mid]

    if mid in hp:
        del hp[mid]

    save_hold_tokens(ht)
    save_hold_paws(hp)

    await update.message.reply_text("Hold removed / Пауза снята")


def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("nextweek", nextweek))
    app.add_handler(CommandHandler("rotation", rotation))
    app.add_handler(CommandHandler("swaptoken", swaptoken))
    app.add_handler(CommandHandler("swappaw", swappaw))
    app.add_handler(CommandHandler("holdT", holdT))
    app.add_handler(CommandHandler("holdP", holdP))
    app.add_handler(CommandHandler("holdlist", holdlist))
    app.add_handler(CommandHandler("unhold", unhold))
    app.add_handler(CommandHandler("exportqueues", exportqueues))
    app.add_handler(CommandHandler("ID", idlist))

    app.run_polling()


if __name__ == "__main__":
    main()
