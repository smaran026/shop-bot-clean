import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

GROUP_SIZE = 7

MEMBERS_FILE = "members.json"
TOKENS_FILE = "tokens_queue.json"
PAWS_FILE = "paws_queue.json"

ADMIN_IDS = [1228141945]

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

def calculate(offset=0):

    w=week_index(offset)

    tokens=rotate(tokens_queue(),w)
    paws=rotate(paws_queue(),w)

    tokens_this=tokens[:GROUP_SIZE]
    tokens_next=tokens[GROUP_SIZE:GROUP_SIZE*2]

    paws_this=[]
    for p in paws:
        if p not in tokens_this and len(paws_this)<GROUP_SIZE:
            paws_this.append(p)

    paws_next=[]
    for p in paws:
        if (
            p not in tokens_next
            and p not in paws_this
            and len(paws_next)<GROUP_SIZE
        ):
            paws_next.append(p)

    return tokens_this,paws_this,tokens_next,paws_next,tokens,paws

async def week(update:Update,context:ContextTypes.DEFAULT_TYPE):

    tokens,paws,_,_,_,_=calculate()

    names=member_map()

    msg="This Week\n\nInvitation Tokens\n"

    for i in tokens:
        msg+=names[i]+"\n"

    msg+="\nPaws\n"

    for i in paws:
        msg+=names[i]+"\n"

    await update.message.reply_text(msg)

async def nextweek(update:Update,context:ContextTypes.DEFAULT_TYPE):

    _,_,tokens,paws,_,_=calculate()

    names=member_map()

    msg="Next Week\n\nInvitation Tokens\n"

    for i in tokens:
        msg+=names[i]+"\n"

    msg+="\nPaws\n"

    for i in paws:
        msg+=names[i]+"\n"

    await update.message.reply_text(msg)

async def rotation(update:Update,context:ContextTypes.DEFAULT_TYPE):

    tokens_this,paws_this,tokens_next,paws_next,tokens,paws=calculate()

    names=member_map()

    msg="Current Rotation Flow\n\n"

    msg+="INVITATION TOKENS\nThis Week\n"

    for i in tokens_this:
        msg+=f"{i}. {names[i]}\n"

    msg+="\nNext Week\n"

    for i in tokens_next:
        msg+=f"{i}. {names[i]}\n"

    msg+="\nReserve\n"

    for i in tokens[GROUP_SIZE*2:]:
        msg+=f"{i}. {names[i]}\n"

    msg+="\n\nPAWS\nThis Week\n"

    for i in paws_this:
        msg+=f"{i}. {names[i]}\n"

    msg+="\nNext Week\n"

    for i in paws_next:
        msg+=f"{i}. {names[i]}\n"

    msg+="\nReserve\n"

reserve_paws = [p for p in paws if p not in paws_this and p not in paws_next]

for i in reserve_paws:
    msg+=f"{i}. {names[i]}\n"

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

async def when(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mid = int(context.args[0])

    tokens_this, paws_this, tokens_next, paws_next, tokens, paws = calculate()

    names = member_map()

    name = names[mid]

    # TOKENS
    if mid in tokens_this:
        token_msg = "This week"
    elif mid in tokens_next:
        token_msg = "Next week"
    else:
        tq = tokens_queue()
        w = week_index()

        pos = tq.index(mid)
        start = (w * GROUP_SIZE) % len(tq)

        weeks = ((pos - start) % len(tq)) // GROUP_SIZE
        token_msg = f"In {weeks} week(s)"

    # PAWS
    if mid in paws_this:
        paws_msg = "This week"
    elif mid in paws_next:
        paws_msg = "Next week"
    else:
        pq = paws_queue()
        w = week_index()

        pos = pq.index(mid)
        start = (w * GROUP_SIZE) % len(pq)

        weeks = ((pos - start) % len(pq)) // GROUP_SIZE
        paws_msg = f"In {weeks} week(s)"

    msg = f"{name}\n\nTokens: {token_msg}\nPaws: {paws_msg}"

    await update.message.reply_text(msg)

def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("week",week))
    app.add_handler(CommandHandler("nextweek",nextweek))
    app.add_handler(CommandHandler("rotation",rotation))
    app.add_handler(CommandHandler("when",when))
    app.add_handler(CommandHandler("swaptoken",swaptoken))
    app.add_handler(CommandHandler("swappaw",swappaw))

    app.run_polling()

if __name__=="__main__":
    main()
