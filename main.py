# =========================================================
# WELCOME / READY MESSAGE (debounce + safe filters)
# =========================================================
from pyrogram import filters

GREET_COOLDOWN_HOURS = 24
_last_greet_at = {}  # user_id -> datetime

@app.on_message(
    filters.incoming                                  # solo messaggi degli utenti
    & ~filters.bot                                    # ignora altri bot
    & filters.private                                 # solo DM
    & (
        filters.command("start")                      # /start
        | filters.regex(r"^(?i)(hello|ciao|hi|hey)\b")  # saluti all'inizio
      )
)
async def start_chat(client, message):
    user_id = message.from_user.id if message.from_user else message.chat.id

    # Cooldown di 24h per evitare ripetizioni
    now = datetime.utcnow()
    last = _last_greet_at.get(user_id)
    if last and (now - last) < timedelta(hours=GREET_COOLDOWN_HOURS):
        return  # già salutato di recente

    _last_greet_at[user_id] = now

    await typing_burst(message.chat.id)
    await asyncio.sleep(human_delay())
    await message.reply_text(
        f"{PROFILE['persona']['greeting']} "
        f"I’m {PROFILE['perso]()
