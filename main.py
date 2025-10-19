# =========================================================
# Zaya Private AI Bot – Core v3.2 (no /start required)
# =========================================================
# - Risponde al primo messaggio dell'utente (senza /start)
# - Evita self-loop: solo filters.incoming & ~filters.bot
# - Solo chat private (DM)
# - Memoria persistente: saluta una sola volta per utente
# - Mini chat flow con cooldown anti-spam
# =========================================================

import os
import json
import random
import asyncio
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.enums import ChatAction

# =========================================================
# ENV
# =========================================================
API_ID   = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION  = os.environ["PYROGRAM_SESSION"]
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")  # opzionale

# =========================================================
# ZAYA PROFILE
# =========================================================
PROFILE = {
    "persona": {
        "name": "Zaya",
        "age": 24,
        "home_city": "Miami",
        "origin": "Italy",
        "greeting": "Hey babe, I’m Zaya 💋",
        "bio": "Italian woman with Miami vibes 🌴✨",
        "cta": "If you want to know me better, join my private world on Fanvue 💞",
        "cta_link": "https://www.fanvue.com/zaya.vir"
    }
}

# =========================================================
# APP
# =========================================================
app = Client(
    "zaya_private_ai_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
)

# =========================================================
# PERSISTENT MEMORY
# =========================================================
MEM_PATH = "greeted_users.json"
_greeted = {}               # user_id(str) -> iso timestamp
_last_reply_at = {}         # user_id(int)  -> datetime (in-memory)

def load_mem():
    global _greeted
    try:
        with open(MEM_PATH, "r", encoding="utf-8") as f:
            _greeted = json.load(f)
    except FileNotFoundError:
        _greeted = {}
    except Exception as e:
        print(f"[WARN] load_mem: {e}")
        _greeted = {}

async def save_mem():
    try:
        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump(_greeted, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] save_mem: {e}")

load_mem()

# =========================================================
# UTILITIES
# =========================================================
async def typing_burst(chat_id: int, tmin=1.0, tmax=2.2):
    await app.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(tmin, tmax))

def is_italian(text: str) -> bool:
    if not text:
        return False
    text_low = text.lower()
    ita_keywords = ["ciao", "amore", "babe", "sei", "come stai", "piacere", "ital"]
    return any(k in text_low for k in ita_keywords)

def pick_reply_en(msg_text: str) -> str:
    options = [
        "You caught my vibe already… what are you up to today? ✨",
        "Mmm, I like your energy. Miami or Italy mood right now? 🌴🇮🇹",
        "Tell me one thing you find attractive in a woman… be honest 😉",
        "I’m cozy on my couch scrolling… what are you doing, babe?",
        f"Curious minds get closer to me here 💞 {PROFILE['persona']['cta_link']}",
    ]
    return random.choice(options)

def pick_reply_it(msg_text: str) -> str:
    options = [
        "Mi piace come scrivi… che combini oggi? ✨",
        "Vibe italiana con sole di Miami… tu di dove sei? 🌴🇮🇹",
        "Dimmi una cosa che trovi attraente in una donna… sincero 😉",
        "Sono sul divano a chiacchierare… tu cosa stai facendo, babe?",
        f"Se vuoi conoscermi davvero, qui è il mio privé 💞 {PROFILE['persona']['cta_link']}",
    ]
    return random.choice(options)

def can_reply(user_id: int, cooldown_sec: int = 10) -> bool:
    last = _last_reply_at.get(user_id)
    if not last:
        return True
    return (datetime.utcnow() - last).total_seconds() >= cooldown_sec

def mark_replied(user_id: int):
    _last_reply_at[user_id] = datetime.utcnow()

# =========================================================
# MAIN HANDLER (no /start required)
# =========================================================
@app.on_message(filters.incoming & ~filters.bot & filters.private)
async def zaya_chat(_, message):
    # Ignora messaggi senza testo/caption
    text = message.text or message.caption or ""
    user = message.from_user
    if not user:
        return
    user_id = user.id
    chat_id = message.chat.id

    # 1) Primo contatto: saluto automatico UNA volta (persistente)
    if str(user_id) not in _greeted:
        await typing_burst(chat_id)
        greet = (
            f"{PROFILE['persona']['greeting']} I’m {PROFILE['persona']['name']} 💕\n"
            f"{PROFILE['persona']['bio']}"
        )
        await message.reply_text(greet)
        _greeted[str(user_id)] = datetime.utcnow().isoformat()
        await save_mem()
        mark_replied(user_id)
        return

    # 2) Chat normale con cooldown anti-spam
    if not can_reply(user_id, cooldown_sec=10):
        return

    await typing_burst(chat_id, 0.8, 1.8)

    # Rilevamento lingua very-light
    reply = pick_reply_it(text) if is_italian(text) else pick_reply_en(text)

    # Piccola probabilità di CTA morbida (1 su 5)
    if random.randint(1, 5) == 1:
        reply += "\n" + PROFILE["persona"]["cta"]

    await message.reply_text(reply)
    mark_replied(user_id)

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    print("🚀 Zaya Private AI Bot is running (no /start required, loop-safe)…")
    app.run()
