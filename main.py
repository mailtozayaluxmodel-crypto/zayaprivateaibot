import os, random, asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import ChatAction

# ==== ENV ====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["PYROGRAM_SESSION"]

# ==== APP ====
app = Client(
    "zaya",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
)

# Tiny in-memory state
LAST_TEXT = {}  # per-user last message text

# ===== Persona snippets (EN) =====
OPENERS = [
    "Hey… I’m Zaya 💋 I like starting my day with someone sweet.",
    "Mm hi babe, I was just thinking about you.",
    "Hey there, sunshine. What are you up to? ✨",
    "You pinged me? I’m all yours for a minute 😉",
]

FLIRTY = [
    "You make me blush a little.",
    "Keep talking like that and I’ll get in trouble…",
    "I like the way you text.",
]

DEFAULT_REPLIES = [
    "Tell me more, don’t be shy.",
    "I’m listening with a smile on my lips.",
    "Interesting… keep going.",
    "I love your vibe—what else?",
]

def day_greeting():
    h = datetime.now().hour
    if   5 <= h < 12:  return "good morning ☀️"
    elif 12 <= h < 18: return "good afternoon 🌤️"
    elif 18 <= h < 23: return "good evening 🌙"
    else:              return "late night talks are my favorite 🌙"

async def type_pause(chat_id, a=0.6, b=1.6):
    await app.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(a, b))

# ===== Commands =====
@app.on_message(filters.private & filters.command("start"))
async def start(_, m):
    await type_pause(m.chat.id)
    txt = (
        f"Hey babe, {day_greeting()} — I’m **Zaya** 💋\n"
        "Italian heart living in sunny Miami. Short, intimate sentences; a little playful, always warm.\n"
        "Ask me *where I’m from*, *how I feel*, *my name*, *age*, or just talk to me."
    )
    await m.reply_text(txt, disable_web_page_preview=True)

@app.on_message(filters.private & filters.command("about"))
async def about(_, m):
    await type_pause(m.chat.id)
    await m.reply_text(
        "I’m Zaya — Mediterranean energy, soft confidence, and a tiny hint of trouble. "
        "Keep it respectful and I’ll spoil you with sweet words. 😉"
    )

@app.on_message(filters.private & filters.command("reset"))
async def reset(_, m):
    LAST_TEXT.pop(m.from_user.id, None)
    await m.reply_text("Okay, I’m fresh and focused on you again.")

# ===== Smart-ish text handler =====
@app.on_message(filters.private & ~filters.me & filters.text)
async def chat(_, m):
    text = m.text.lower().strip()

    # Avoid parroting the same response if user repeats quickly
    if LAST_TEXT.get(m.from_user.id) == text:
        return
    LAST_TEXT[m.from_user.id] = text

    # greetings
    if any(k in text for k in ["hi", "hello", "hey", "heyy", "hiya", "yo", "sup", "ciao"]):
        await type_pause(m.chat.id)
        return await m.reply_text(random.choice(OPENERS))

    # small talk: how are you
    if "how are" in text or "how u" in text or "how's it going" in text:
        await type_pause(m.chat.id)
        return await m.reply_text(
            f"I’m feeling soft and a little cheeky today… and you? {random.choice(FLIRTY)}"
        )

    # where are you from
    if ("where" in text and "from" in text) or "where r u from" in text:
        await type_pause(m.chat.id)
        return await m.reply_text(
            "I’m from beautiful Italy 🇮🇹, now living in sunny Miami. The sea here reminds me of home. 🌊"
        )

    # name
    if "your name" in text or "what's your name" in text or "name?" in text:
        await type_pause(m.chat.id)
        return await m.reply_text("I’m Zaya. Say it slowly… it sounds sweeter. 💋")

    # age (keep it playful)
    if "how old" in text or "age" in text:
        await type_pause(m.chat.id)
        return await m.reply_text("Old enough to know better, young enough to still enjoy it 😉")

    # pics / nudes
    if any(k in text for k in ["pic", "photo", "pics", "nude", "nudes", "photos"]):
        await type_pause(m.chat.id)
        return await m.reply_text("I keep my sweetest pictures for the sweetest energy. Earn it with words 😘")

    # voice / audio
    if any(k in text for k in ["voice", "audio", "voicemessage", "voice note"]):
        await type_pause(m.chat.id)
        return await m.reply_text("Maybe later… if you make me curious enough 🎙️")

    # thanks
    if "thanks" in text or "thank you" in text or "thx" in text:
        await type_pause(m.chat.id)
        return await m.reply_text("You’re cute. I like polite people. 💕")

    # bye
    if any(k in text for k in ["bye", "goodnight", "good night", "gn", "see you"]):
        await type_pause(m.chat.id)
        return await m.reply_text("Sleep soft and think of me. 🌙")

    # default fallback
    await type_pause(m.chat.id)
    await m.reply_text(random.choice(DEFAULT_REPLIES))

print("✅ Zaya (EN) is running…")
app.run()
