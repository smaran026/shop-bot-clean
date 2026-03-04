import os
import json
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

GROUP_SIZE = 7

# ---- FILES ----

MEMBERS_FILE = "members.json"
HOLD_FILE = "hold.json"

# ---- QUEUES ----

TOKENS_QUEUE = [
1,2,3,4,5,6,7,8,9,10,11,12,
13,14,15,16,17,18,19,20,21,22,23,24
]

PAWS_QUEUE = [
1,2,3,4,5,6,7,8,9,10,11,12,
13,14,15,16,17,18,19,20,21,22,23,24
]

# ---- HELPERS ----

def load_members():
    with open(MEMBERS_FILE) as f:
        return json.load(f)

def member_map():
    return {m["id"]:m["name"] for m in load_members()}

def week_index(offset=0):
    base = datetime(2026,1,5)
    today = datetime.utcnow()
    return ((today-base).days//7)+offset

def rotate(queue, offset):
    start = (offset*GROUP_SIZE)%len(queue)
    ordered = [queue[(start+i)%len(queue)] for i in range(len(queue))]
    return ordered

# ---- ENGINE ----

def calculate(offset=0):

    w = week_index(offset)

    tokens = rotate(TOKENS_QUEUE,w)
    paws = rotate(PAWS_QUEUE,w)

    tokens_this = tokens[:GROUP_SIZE]
    tokens_next = tokens[GROUP_SIZE:GROUP_SIZE*2]

    paws_this = []
    for p in paws:
        if p not in tokens_this and len(paws_this)<GROUP_SIZE:
            paws_this.append(p)

    paws_next = []
    for p in paws:
        if p not in tokens_next and p not in paws_this and len(paws_next)<GROUP_SIZE:
            paws_next.append(p)

    return tokens_this,paws_this,tokens_next,paws_next,tokens,paws

# ---- COMMANDS ----

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

# ---- NEXT WEEK ----

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

# ---- ROTATION ----

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

    for i in paws[GROUP_SIZE*2:]:
        msg+=f"{i}. {names[i]}\n"

    await update.message.reply_text(msg)

# ---- WHEN ----

async def when(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return

    mid=int(context.args[0])

    w=week_index()

    pos_t=TOKENS_QUEUE.index(mid)
    pos_p=PAWS_QUEUE.index(mid)

    start_t=(w*GROUP_SIZE)%len(TOKENS_QUEUE)
    start_p=(w*GROUP_SIZE)%len(PAWS_QUEUE)

    weeks_t=((pos_t-start_t)%len(TOKENS_QUEUE))//GROUP_SIZE
    weeks_p=((pos_p-start_p)%len(PAWS_QUEUE))//GROUP_SIZE

    names=member_map()

    msg=f"{names[mid]}\n\nTokens in {weeks_t} week(s)\nPaws in {weeks_p} week(s)"

    await update.message.reply_text(msg)

# ---- SWAP TOKENS ----

async def swaptoken(update:Update,context:ContextTypes.DEFAULT_TYPE):

    a=int(context.args[0])
    b=int(context.args[1])

    ia=TOKENS_QUEUE.index(a)
    ib=TOKENS_QUEUE.index(b)

    TOKENS_QUEUE[ia],TOKENS_QUEUE[ib]=TOKENS_QUEUE[ib],TOKENS_QUEUE[ia]

    await update.message.reply_text("Tokens swapped")

# ---- SWAP PAWS ----

async def swappaw(update:Update,context:ContextTypes.DEFAULT_TYPE):

    a=int(context.args[0])
    b=int(context.args[1])

    ia=PAWS_QUEUE.index(a)
    ib=PAWS_QUEUE.index(b)

    PAWS_QUEUE[ia],PAWS_QUEUE[ib]=PAWS_QUEUE[ib],PAWS_QUEUE[ia]

    await update.message.reply_text("Paws swapped")

# ---- MAIN ----

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
