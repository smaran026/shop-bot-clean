import os
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue

TOKEN = os.getenv("TOKEN")

GROUP_SIZE = 7

MEMBERS_FILE = "members.json"
TOKENS_FILE = "tokens_queue.json"
PAWS_FILE = "paws_queue.json"

ADMIN_IDS = [1228141945]

RESET_TEXT = "Reset: Monday 17:30 IST / 12:00 GMT / 15:00 MSK"


def load_json(file):
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


def is_admin(user_id):
    return user_id in ADMIN_IDS


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

    return start.strftime("%b %d"), end.strftime("%b %d")


def calculate(offset=0):

    w=week_index(offset)

    tokens=rotate(tokens_queue(),w)
    paws=rotate(paws_queue(),w)

    tokens_this=tokens[:GROUP_SIZE]
    tokens_next=tokens[GROUP_SIZE:GROUP_SIZE*2]
    tokens_w3=tokens[GROUP_SIZE*2:GROUP_SIZE*3]

    paws_this=[]
    for p in paws:
        if p not in tokens_this and len(paws_this)<GROUP_SIZE:
            paws_this.append(p)

    paws_next=[]
    for p in paws:
        if p not in tokens_next and p not in paws_this and len(paws_next)<GROUP_SIZE:
            paws_next.append(p)

    paws_w3=[]
    for p in paws:
        if p not in tokens_w3 and p not in paws_this and p not in paws_next and len(paws_w3)<GROUP_SIZE:
            paws_w3.append(p)

    return tokens_this,paws_this,tokens_next,paws_next,tokens_w3,paws_w3,tokens,paws


async def week(update:Update,context:ContextTypes.DEFAULT_TYPE):

    tokens,paws,_,_,_,_,_,_=calculate()
    names=member_map()

    start,end=week_range(0)

    msg=f"📅 CURRENT WEEK / ТЕКУЩАЯ НЕДЕЛЯ\n{start} – {end}\n"
    msg+="━━━━━━━━━━━━━━━━\n\n"

    msg+="🎟 TOKENS\n"
    for i in tokens:
        msg+="• "+names[i]+"\n"

    msg+="\n🐾 PAWS\n"
    for i in paws:
        msg+="• "+names[i]+"\n"

    msg+="\n"+RESET_TEXT

    await update.message.reply_text(msg)


async def nextweek(update:Update,context:ContextTypes.DEFAULT_TYPE):

    _,_,tokens,paws,_,_,_,_=calculate()
    names=member_map()

    start,end=week_range(1)

    msg=f"📅 NEXT WEEK / СЛЕДУЮЩАЯ НЕДЕЛЯ\n{start} – {end}\n"
    msg+="━━━━━━━━━━━━━━━━\n\n"

    msg+="🎟 TOKENS\n"
    for i in tokens:
        msg+="• "+names[i]+"\n"

    msg+="\n🐾 PAWS\n"
    for i in paws:
        msg+="• "+names[i]+"\n"

    await update.message.reply_text(msg)


async def rotation(update:Update,context:ContextTypes.DEFAULT_TYPE):

    t1,p1,t2,p2,t3,p3,tokens,_=calculate()
    names=member_map()

    s1,e1=week_range(0)
    s2,e2=week_range(1)
    s3,e3=week_range(2)

    msg="📊 ROTATION / РОТАЦИЯ\n━━━━━━━━━━━━━━━━\n\n"

    msg+=f"📅 Current Week\n{s1} – {e1}\n\n"
    msg+="🎟 TOKENS\n"
    for i in t1:
        msg+="• "+names[i]+"\n"

    msg+="\n🐾 PAWS\n"
    for i in p1:
        msg+="• "+names[i]+"\n"

    msg+="\n━━━━━━━━━━━━━━━━\n"

    msg+=f"📅 Next Week\n{s2} – {e2}\n\n"
    msg+="🎟 TOKENS\n"
    for i in t2:
        msg+="• "+names[i]+"\n"

    msg+="\n🐾 PAWS\n"
    for i in p2:
        msg+="• "+names[i]+"\n"

    msg+="\n━━━━━━━━━━━━━━━━\n"

    msg+=f"📅 Week 3\n{s3} – {e3}\n\n"
    msg+="🎟 TOKENS\n"
    for i in t3:
        msg+="• "+names[i]+"\n"

    msg+="\n🐾 PAWS\n"
    for i in p3:
        msg+="• "+names[i]+"\n"

    msg+="\n━━━━━━━━━━━━━━━━\n📦 Reserve\n"

    for i in tokens[GROUP_SIZE*3:]:
        msg+="• "+names[i]+"\n"

    msg+="\n"+RESET_TEXT

    await update.message.reply_text(msg)


async def when(update:Update,context:ContextTypes.DEFAULT_TYPE):

    mid=int(context.args[0])
    names=member_map()

    t1,p1,t2,p2,t3,p3,_,_=calculate()

    name=names[mid]

    def check(mid,a,b,c):
        if mid in a: return "Current Week"
        if mid in b: return "Next Week"
        if mid in c: return "Week 3"
        return "Later"

    tokens=check(mid,t1,t2,t3)
    paws=check(mid,p1,p2,p3)

    msg=f"📌 {name}\n\n🎟 Tokens: {tokens}\n🐾 Paws: {paws}"

    await update.message.reply_text(msg)


async def exportqueues(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    tokens=tokens_queue()
    paws=paws_queue()
    names=member_map()

    msg="QUEUE EXPORT\n\nINVITATION TOKENS\n"

    for i,m in enumerate(tokens,1):
        msg+=f"{i}. {names[m]}\n"

    msg+="\nPAWS\n"

    for i,m in enumerate(paws,1):
        msg+=f"{i}. {names[m]}\n"

    await update.message.reply_text(msg)


async def idlist(update:Update,context:ContextTypes.DEFAULT_TYPE):

    names=member_map()

    msg="CLAN IDS\n\n"

    for mid in sorted(names):
        msg+=f"{mid}  {names[mid]}\n"

    await update.message.reply_text(msg)


async def swaptoken(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    a=int(context.args[0])
    b=int(context.args[1])

    q=tokens_queue()

    ia=q.index(a)
    ib=q.index(b)

    q[ia],q[ib]=q[ib],q[ia]

    save_tokens(q)

    await update.message.reply_text("Tokens swapped permanently")


async def swappaw(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    a=int(context.args[0])
    b=int(context.args[1])

    q=paws_queue()

    ia=q.index(a)
    ib=q.index(b)

    q[ia],q[ib]=q[ib],q[ia]

    save_paws(q)

    await update.message.reply_text("Paws swapped permanently")


async def monday_post(context:ContextTypes.DEFAULT_TYPE):

    chat_ids=context.job.data

    tokens,paws,_,_,_,_,_,_=calculate()
    names=member_map()
    s,e=week_range(0)

    msg=f"📅 CURRENT WEEK\n{s} – {e}\n\n🎟 TOKENS\n"

    for i in tokens:
        msg+="• "+names[i]+"\n"

    msg+="\n🐾 PAWS\n"

    for i in paws:
        msg+="• "+names[i]+"\n"

    msg+="\n"+RESET_TEXT

    for chat in chat_ids:
        await context.bot.send_message(chat_id=chat,text=msg)


def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("week",week))
    app.add_handler(CommandHandler("nextweek",nextweek))
    app.add_handler(CommandHandler("rotation",rotation))
    app.add_handler(CommandHandler("when",when))
    app.add_handler(CommandHandler("ID",idlist))
    app.add_handler(CommandHandler("exportqueues",exportqueues))
    app.add_handler(CommandHandler("swaptoken",swaptoken))
    app.add_handler(CommandHandler("swappaw",swappaw))

    job_queue=app.job_queue

    chat_ids=[]

    job_queue.run_daily(
        monday_post,
        time=datetime.strptime("12:00","%H:%M").time(),
        days=(0,),
        data=chat_ids
    )

    app.run_polling()


if __name__=="__main__":
    main()
