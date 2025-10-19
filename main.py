# =========================================================
# Zaya Private AI Bot – Core v3
# =========================================================
# Adaptive Chatbot for Telegram built with Pyrogram
# Features:
# - User memory (language, mood, last topic, anti-repetition)
# - Automatic language detection (EN / IT / ES)
# - Natural rhythm and elegant fan engagement
# - CTA Fanvue and personality-based flow
# =========================================================

import os
import re
import json
import random
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from pyrogram import Client, filters
from pyrogram.enums import ChatAction

# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["PYROGRAM_SESSION"]
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

# =========================================================
# ZAYA PROFILE BASE
# =========================================================
PROFILE = {
    "persona": {
        "name": "Zaya",
        "age": 24,
        "home_city": "Miami",
        "origin": "Italy",
        "greeting": "Hey babe, I’m Zaya 💋",
        "bio": "Italian woman with Miami vibes 🌴✨",
    }
}

# =========================================================
# APP INITIALIZATION
# =========================================================
app = Client(
    "zaya_private_ai_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
)

# =========================================================
# UTILITY FUNCTIONS
# =========================================================
async def typing_burst(chat_id, duration=2.5):
    """Simula l’azione di scrittura per rendere la chat più naturale"""
    await app.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(duration)

def human_delay(min_t=0.8, max_t=2.5):
    """Ritardo umano casuale tra le risposte"""
    return random.uniform(min_t, max_t)

# =========================================================
# READY MESSAGE
# =========================================================
@app.on_message(filters.command("start") | filters.regex("(?i)hello|ciao|hi|hey"))
async def start_chat(client, message):
    await typing_burst(message.chat.id)
    await message.reply_text(
        f"{PROFILE['persona']['greeting']} "
        f"I’m {PROFILE['persona']['name']} 💕\n"
        f"{PROFILE['persona']['bio']}"
    )

# =========================================================
# RUN BOT
# =========================================================
if __name__ == "__main__":
    print("🚀 Zaya Private AI Bot is running...")
    app.run()
