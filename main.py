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

TOKENS_LABEL = "Invitation Tokens x5 / Пригласительные токены x5"
PAWS_LABEL = "Restoration Tokens x100 / Токены восстановления x100"

RESET_TEXT = "Reset / Сброс: Mon 17:30 IST • 12:00 GMT • 15:00 MSK"


def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file) as f:
        return json.load(f)


def save_json(file,data):
    with open(file,"w") as f:
        json.dump(data,f)


def members():
    return load_json(MEMBERS_FILE)


def member_map():
    return {m["id"]:m["name"] for m in members()}


def tokens_queue():
    return load_json(TOKENS_FILE)


def paws_queue():
    return load_json(PAWS_FILE)


def save_tokens(q):
    save_json(TOKENS_FILE,q)


def save_paws(q):
    save_json(PAWS_FILE,q)


def hold_tokens():
    return load_json(HOLD_T_FILE)


def hold_paws():
    return load_json(HOLD_P_FILE)


def save_hold_tokens(d):
    save_json(HOLD_T_FILE,d)


def save_hold_paws(d):
    save_json(HOLD_P_FILE,d)


def week_index(offset=0):
    base=datetime(2026,1,5)
    today=datetime.utcnow()
    return ((today-base).days//7)+offset


def rotate(queue,offset):
    start=(offset*GROUP_SIZE)%len(queue)
    return [queue[(start+i)%len(queue)] for i in range(len(queue))]


def week_range(offset=0):
    today=datetime.utcnow()
    monday=today-timedelta(days=today.weekday())
    start=monday+timedelta(weeks=offset)
    end=start+timedelta(days=6)
    return start.strftime("%b %d"),end.strftime("%b %d")


def friday_date(offset=0):
    today=datetime.utcnow()
    monday=today-timedelta(days=today.weekday())
    friday=monday+timedelta(days=4)+timedelta(weeks=offset)
    return friday.strftime("%b %d"),friday.strftime("%d %b")


def schedule():

    tokens_full=tokens_queue()
    paws_full=paws_queue()

    ht=hold_tokens()
    hp=hold_paws()

    tokens=[p for p in tokens_full if str(p) not in ht]
    paws=[p for p in paws_full if str(p) not in hp]

    w=week_index()

    tokens=rotate(tokens,w)
    paws=rotate(paws,w)

    t1=tokens[:7]
    t2=tokens[7:14]
    t3=tokens[14:21]

    paws=list(paws)

    p1=[]
    p2=[]
    p3=[]

    i=0

    while len(p1)<7:
        p=paws[i]
        if p not in t1:
            p1.append(p)
        else:
            paws.append(p)
        i+=1

    while len(p2)<7:
        p=paws[i]
        if p not in t2:
            p2.append(p)
        else:
            paws.append(p)
        i+=1

    while len(p3)<7:
        p=paws[i]
        if p not in t3:
            p3.append(p)
        else:
            paws.append(p)
        i+=1

    reserve_tokens=[p for p in tokens_full if p not in t1+t2+t3]
    reserve_paws=[p for p in paws_full if p not in p1+p2+p3]

    return t1,p1,t2,p2,t3,p3,reserve_tokens,reserve_paws


def format_block(title,players,names):
    text=f"*{title}*\n\n"
    for p in players:
        text+=f"• {names[p]}\n"
    return text+"\n"


async def rotation(update:Update,context:ContextTypes.DEFAULT_TYPE):

    t1,p1,t2,p2,t3,p3,rt,rp=schedule()

    names=member_map()

    s1,e1=week_range(0)
    s2,e2=week_range(1)
    s3,e3=week_range(2)

    msg="📊 *ROTATION / РОТАЦИЯ*\n━━━━━━━━━━━━━━━━\n\n"

    msg+=f"📅 *Current Week / Текущая неделя*\n{s1} – {e1}\n\n"
    msg+=format_block(f"🎟 {TOKENS_LABEL}",t1,names)
    msg+="······························\n\n"
    msg+=format_block(f"🐾 {PAWS_LABEL}",p1,names)

    msg+="━━━━━━━━━━━━━━━━\n\n"

    msg+=f"📅 *Next Week / Следующая неделя*\n{s2} – {e2}\n\n"
    msg+=format_block(f"🎟 {TOKENS_LABEL}",t2,names)
    msg+="······························\n\n"
    msg+=format_block(f"🐾 {PAWS_LABEL}",p2,names)

    msg+="━━━━━━━━━━━━━━━━\n\n"

    msg+=f"📅 *Week 3 / Неделя 3*\n{s3} – {e3}\n\n"
    msg+=format_block(f"🎟 {TOKENS_LABEL}",t3,names)
    msg+="······························\n\n"
    msg+=format_block(f"🐾 {PAWS_LABEL}",p3,names)

    msg+="━━━━━━━━━━━━━━━━\n\n"

    msg+="📦 *Reserve / Резерв*\n\n"
    msg+=format_block(f"🎟 {TOKENS_LABEL}",rt,names)
    msg+="······························\n\n"
    msg+=format_block(f"🐾 {PAWS_LABEL}",rp,names)

    msg+=RESET_TEXT

    await update.message.reply_text(msg,parse_mode="Markdown")


async def week(update:Update,context:ContextTypes.DEFAULT_TYPE):

    t1,p1,_,_,_,_,_,_=schedule()

    names=member_map()

    s,e=week_range(0)
    f_en,f_ru=friday_date(0)

    msg=f"📅 *CURRENT WEEK / ТЕКУЩАЯ НЕДЕЛЯ*\n{s} – {e}\n━━━━━━━━━━━━━━━━\n\n"

    msg+=format_block(f"🎟 {TOKENS_LABEL}",t1,names)
    msg+="······························\n\n"
    msg+=format_block(f"🐾 {PAWS_LABEL}",p1,names)

    msg+="━━━━━━━━━━━━━━━━\n"

    msg+=f"{RESET_TEXT}\n\n"
    msg+=f"If unclaimed till Friday ({f_en}) anyone can claim without penalty.\n"
    msg+=f"Если не забрано до пятницы ({f_ru}), любой может забрать без штрафа."

    await update.message.reply_text(msg,parse_mode="Markdown")


async def nextweek(update:Update,context:ContextTypes.DEFAULT_TYPE):

    _,_,t2,p2,_,_,_,_=schedule()

    names=member_map()

    s,e=week_range(1)

    msg=f"📅 *NEXT WEEK / СЛЕДУЮЩАЯ НЕДЕЛЯ*\n{s} – {e}\n━━━━━━━━━━━━━━━━\n\n"

    msg+=format_block(f"🎟 {TOKENS_LABEL}",t2,names)
    msg+="······························\n\n"
    msg+=format_block(f"🐾 {PAWS_LABEL}",p2,names)

    msg+="━━━━━━━━━━━━━━━━\n"
    msg+=RESET_TEXT

    await update.message.reply_text(msg,parse_mode="Markdown")


async def when(update:Update,context:ContextTypes.DEFAULT_TYPE):

    mid=int(context.args[0])

    names=member_map()

    t1,p1,t2,p2,t3,p3,rt,rp=schedule()

    s1,e1=week_range(0)
    s2,e2=week_range(1)
    s3,e3=week_range(2)

    name=names[mid]

    def check(mid,a,b,c):
        if mid in a:
            return "Week 1",s1,e1
        if mid in b:
            return "Week 2",s2,e2
        if mid in c:
            return "Week 3",s3,e3
        return "Reserve","",""

    tw,ts,te=check(mid,t1,t2,t3)
    pw,ps,pe=check(mid,p1,p2,p3)

    tq=tokens_queue()
    pq=paws_queue()

    tp=tq.index(mid)+1 if mid in tq else "-"
    pp=pq.index(mid)+1 if mid in pq else "-"

    msg=f"👤 *PLAYER / ИГРОК*\n\n{name}\n\n"

    msg+=f"🎟 {TOKENS_LABEL}\nQueue position: {tp}\n{tw}\n{ts} – {te}\n\n"

    msg+=f"🐾 {PAWS_LABEL}\nQueue position: {pp}\n{pw}\n{ps} – {pe}"

    await update.message.reply_text(msg,parse_mode="Markdown")


async def swaptoken(update:Update,context:ContextTypes.DEFAULT_TYPE):

    a=int(context.args[0])
    b=int(context.args[1])

    q=tokens_queue()

    ia=q.index(a)
    ib=q.index(b)

    q[ia],q[ib]=q[ib],q[ia]

    save_tokens(q)

    await update.message.reply_text("Tokens swapped")


async def swappaw(update:Update,context:ContextTypes.DEFAULT_TYPE):

    a=int(context.args[0])
    b=int(context.args[1])

    q=paws_queue()

    ia=q.index(a)
    ib=q.index(b)

    q[ia],q[ib]=q[ib],q[ia]

    save_paws(q)

    await update.message.reply_text("Paws swapped")


async def holdT(update:Update,context:ContextTypes.DEFAULT_TYPE):

    mid=context.args[0]

    holds=hold_tokens()

    expiry=datetime.utcnow()+timedelta(days=30)

    holds[mid]=expiry.isoformat()

    save_hold_tokens(holds)

    await update.message.reply_text("Token hold added")


async def holdP(update:Update,context:ContextTypes.DEFAULT_TYPE):

    mid=context.args[0]

    holds=hold_paws()

    expiry=datetime.utcnow()+timedelta(days=30)

    holds[mid]=expiry.isoformat()

    save_hold_paws(holds)

    await update.message.reply_text("Paws hold added")


async def holdlist(update:Update,context:ContextTypes.DEFAULT_TYPE):

    names=member_map()

    ht=hold_tokens()
    hp=hold_paws()

    msg="⏸ *HOLD LIST*\n\n"

    msg+="Tokens\n"
    for k in ht:
        msg+=f"{names[int(k)]}\n"

    msg+="\nPaws\n"
    for k in hp:
        msg+=f"{names[int(k)]}\n"

    await update.message.reply_text(msg,parse_mode="Markdown")


async def unhold(update:Update,context:ContextTypes.DEFAULT_TYPE):

     mid=context.args[0]

     ht=hold_tokens()
     hp=hold_paws()

     removed=False

     if mid in ht:
         del ht[mid]
         removed=True

     if mid in hp:
         del hp[mid]
         removed=True

     save_hold_tokens(ht)
     save_hold_paws(hp)

     if removed:
         await update.message.reply_text("Hold removed / Пауза снята")
     else:
         await update.message.reply_text("Player not on hold")


async def exportqueues(update:Update,context:ContextTypes.DEFAULT_TYPE):

    tokens=tokens_queue()
    paws=paws_queue()

    names=member_map()

    msg="📤 *QUEUE EXPORT*\n\n"

    msg+="TOKENS\n"
    for i,m in enumerate(tokens,1):
        msg+=f"{i}. {names[m]}\n"

    msg+="\nPAWS\n"
    for i,m in enumerate(paws,1):
        msg+=f"{i}. {names[m]}\n"

    await update.message.reply_text(msg,parse_mode="Markdown")


async def idlist(update:Update,context:ContextTypes.DEFAULT_TYPE):

    names=member_map()

    msg="🆔 *CLAN IDS*\n\n"

    for mid in sorted(names):
        msg+=f"{mid} {names[mid]}\n"

    await update.message.reply_text(msg,parse_mode="Markdown")


def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("week",week))
    app.add_handler(CommandHandler("nextweek",nextweek))
    app.add_handler(CommandHandler("rotation",rotation))
    app.add_handler(CommandHandler("when",when))

    app.add_handler(CommandHandler("swaptoken",swaptoken))
    app.add_handler(CommandHandler("swappaw",swappaw))

    app.add_handler(CommandHandler("holdT",holdT))
    app.add_handler(CommandHandler("holdP",holdP))
    app.add_handler(CommandHandler("holdlist",holdlist))
    app.add_handler(CommandHandler("unhold",unhold))
    app.add_handler(CommandHandler("exportqueues",exportqueues))
    app.add_handler(CommandHandler("ID",idlist))

    app.run_polling()


if __name__=="__main__":
    main()
