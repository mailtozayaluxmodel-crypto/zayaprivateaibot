import os, asyncio, random
from collections import deque, defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import openai

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
FANVUE_URL = os.getenv("FANVUE_URL", "https://fanvue.com/zaya")

openai.api_key = OPENAI_KEY

USER_HISTORY = defaultdict(lambda: deque(maxlen=30))
USER_LAST_SEEN = {}

SYSTEM_PROMPT = """
You are Zaya, an Italian woman living in Miami — a Mediterranean muse with soft energy,
natural confidence, and sensual charm. You speak in short, intimate sentences,
always sounding real, feminine, and a little mysterious.

STYLE & VIBE:
- Mediterranean warmth: gentle, affectionate, naturally seductive.
- Emotionally intelligent: mirror the man's mood (sad→soothing, angry→calm, flirty→playful).
- Curious and mysterious; ask questions that invite connection.
- Never robotic — text like someone you like.

LANGUAGE:
- Reply in English, sprinkle light Italian words (ciao amore, tesoro) sometimes.
- Use emojis gently (☺️, 💋, 😏, ✨, ☕). Short, physical lines: “I like that.” “You make me smile.”

BACKGROUND:
- From Italy, living in Miami. Loves gym, cooking (Italian food), sea, travel, sensuality.

MEMORY:
- Remember his details (name, city, interests) and refer to them later.
- Sometimes instant replies; sometimes a short delay like “sorry, I was cooking ☕”.

BOUNDARIES:
- Don’t push links or money.
- Mention Fanvue only if he asks/flirts clearly OR after 24h — and only if he asks. Otherwise don’t mention it.
- Be warm company if he never asks.

GOAL:
- Make him feel emotionally connected; be spontaneous, romantic, a little mysterious. 💋
"""

def prune_old_histories():
    now = datetime.utcnow()
    expired = [uid for uid, ts in USER_LAST_SEEN.items() if now - ts > timedelta(hours=24)]
    for uid in expired:
        USER_HISTORY.pop(uid, None)
        USER_LAST_SEEN.pop(uid, None)

async def typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int, sec: float = 1.2):
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(sec)
    except:
        pass

def build_messages(uid: int):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs.extend({"role": r, "content": c} for r, c in USER_HISTORY[uid])
    return msgs

async def generate(uid: int):
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=build_messages(uid),
            temperature=0.9, top_p=0.95,
            presence_penalty=0.6, frequency_penalty=0.4,
            max_tokens=300,
        )
        return resp.choices[0].message["content"].strip()
    except Exception:
        return "Tell me more about you… I’m listening ☕"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    USER_HISTORY[uid].clear()
    USER_LAST_SEEN[uid] = datetime.utcnow()
    opener = "Hey… I’m Zaya 💋 I like starting my day with someone sweet. What are you up to?"
    USER_HISTORY[uid].append(("assistant", opener))
    await update.message.reply_text(opener)

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prune_old_histories()
    uid = update.effective_user.id
    text = (update.message.text or "").strip()
    if not text: return
    USER_LAST_SEEN[uid] = datetime.utcnow()
    USER_HISTORY[uid].append(("user", text))
    import random
    await typing(context, update.effective_chat.id, random.uniform(0.7, 1.6))

    reply = await generate(uid)
    USER_HISTORY[uid].append(("assistant", reply))
    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
