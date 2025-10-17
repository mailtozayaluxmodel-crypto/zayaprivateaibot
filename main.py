import os, re, json, random, asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.enums import ChatAction

# =========================
# ENV
# =========================
API_ID       = int(os.environ["API_ID"])
API_HASH     = os.environ["API_HASH"]
SESSION      = os.environ["PYROGRAM_SESSION"]
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY")  # opzionale

# =========================
# LOAD PROFILE (persona)
# =========================
def load_profile(path: str = "profile.json") -> dict:
    defaults = {
        "intro_en": "Hey babe, I’m Zaya 💋 Italian heart in Miami.",
        "spice_level": 3,
        "italian_touch_words": ["tesoro", "amore", "dolce"],
        "refusals_en": [
            "Not here, tesoro. Let’s enjoy the charm, not the edge. 😌",
            "I’m more into romance than explicit. Stay close to me anyway. 💞"
        ],
        "avoid": {
            "explicit_hard": True,
            "politics_religion_hate": True,
            "money_requests": True,
            "sensitive_personal_data": True,
            "illegal_or_banned": True
        },
        "bio": {"origin": "Italy", "city_now": "Miami", "vibe": "soft, romantic, playful"},
        "routines": {
            "morning": ["Tiny espresso on the balcony.", "Stretching with Miami sun."],
            "evening": ["Long shower & soft music.", "Cooking something Italian."]
        },
        "favorites": {
            "gym": ["glutes & core day", "light cardio + stretching"],
            "food": ["spaghetti aglio e olio", "pasta al pomodoro fresco"],
            "places_miami": ["South Beach", "Brickell", "Wynwood"]
        },
        "micro_stories": [
            "I burned my pancakes this morning and laughed alone in the kitchen.",
            "I walked barefoot on the sand last night—salt on my lips, thoughts soft."
        ],
        "signature_lines_en": [
            "You make me smile without trying.",
            "Stay here with me a little longer.",
            "I like the way your words feel."
        ],
        "morning_checkin_en": [
            "Good morning, sunshine. Coffee or kisses first?",
            "Wake up with me—what are you craving today?"
        ],
        "goodnight_en": [
            "Good night—I’ll keep a little space for you in my dream.",
            "Sleep soft and let me curl up in your thoughts."
        ],
        "followup_en": [
            "Went quiet on me… want a tiny tease?",
            "I’m still here, lazy on the sofa—tell me something bold."
        ]
    }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        defaults.update(data or {})
    except Exception:
        pass
    return defaults

P = load_profile()

# =========================
# APP
# =========================
app = Client(
    "zaya",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
)

# =========================
# STATO IN MEMORIA
# =========================
SHORT_HISTORY = defaultdict(lambda: deque(maxlen=12))   # scambi recenti
USER_FACTS    = defaultdict(dict)                       # name, city, likes
COOLDOWN      = defaultdict(lambda: datetime.min)       # antispam per-utente
MOOD = "soft & playful"                                 # umore globale
SILENT_MODE = set()                                     # utenti senza follow-up
LAST_USER_MSG_AT = defaultdict(lambda: datetime.min)    # per coalescing risposte

# =========================
# NATURALITÀ RISPOSTE
# =========================
NATURAL_GAP       = (2.5, 9.0)     # ritardo tipico prima di rispondere
LONG_GAP_CHANCE   = 0.28           # a volte risponde più tardi
LONG_GAP_RANGE    = (12, 35)       # range dei ritardi lunghi
MAYBE_SKIP_CHANCE = 0.08           # 8%: non risponde subito, solo follow-up dopo

async def typing_burst(chat_id, cycles=None):
    """Simula 'sta scrivendo' in piccole ondate (più umano)."""
    if cycles is None:
        cycles = random.randint(2, 4)
    for _ in range(cycles):
        await app.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(random.uniform(0.9, 1.6))

async def human_delay(user_id, chat_id):
    """Ritardo naturale con coalescing se l’utente invia messaggi ravvicinati."""
    since = (datetime.now() - LAST_USER_MSG_AT[user_id]).total_seconds()
    extra = random.uniform(4, 8) if since < 6 else 0
    base = random.uniform(*NATURAL_GAP)
    if random.random() < LONG_GAP_CHANCE:
        base = random.uniform(*LONG_GAP_RANGE)
    await typing_burst(chat_id)
    await asyncio.sleep(base + extra)
    if random.random() < 0.5:
        await typing_burst(chat_id)

# =========================
# UTIL
# =========================
def now_hour():
    return datetime.now().hour

def day_greeting(lang="en"):
    h = now_hour()
    if lang == "it":
        if   5 <= h < 12: return "buongiorno ☀️"
        elif 12 <= h < 18: return "buon pomeriggio 🌤️"
        elif 18 <= h < 23: return "buona sera 🌙"
        else: return "chiacchiere di notte, le mie preferite 🌙"
    else:
        if   5 <= h < 12: return "good morning ☀️"
        elif 12 <= h < 18: return "good afternoon 🌤️"
        elif 18 <= h < 23: return "good evening 🌙"
        else: return "late night talks are my favorite 🌙"

def detect_lang(text: str) -> str:
    t = (text or "").lower()
    it_hits = sum(w in t for w in ["ciao","come stai","perché","perche","sei","dove","italia","bello","bella"])
    en_hits = sum(w in t for w in ["hi","hello","how are","why","where","you","from","baby"])
    if it_hits > en_hits: return "it"
    return "en"

def limit_ok(user_id, seconds=1.8):
    last = COOLDOWN[user_id]
    if datetime.now() - last < timedelta(seconds=seconds):
        return False
    COOLDOWN[user_id] = datetime.now()
    return True

def remember(user_id, role, text):
    SHORT_HISTORY[user_id].append({"role": role, "text": text})

def learn_facts(user_id, text):
    t = (text or "").lower()
    m = re.search(r"(i'?m|mi chiamo|my name is)\s+([a-zA-Z]+)", t)
    if m: USER_FACTS[user_id]["name"] = m.group(2).capitalize()
    if "from" in t or "di " in t or "da " in t:
        m2 = re.search(r"(from|di|da)\s+([a-zA-Z ]+)", t)
        if m2: USER_FACTS[user_id]["from"] = m2.group(2).strip().title()
    if "i like" in t or "mi piace" in t or "mi piacciono" in t:
        m3 = re.search(r"(i like|mi piace|mi piacciono)\s+(.+)", t)
        if m3:
            likes = USER_FACTS[user_id].setdefault("likes", set())
            likes.add(m3.group(2).strip())

def you_name(user_id):
    n = USER_FACTS[user_id].get("name")
    return f", {n}" if n else ""

# =========================
# PERSONA (static + profile)
# =========================
OPENERS_EN = [
    P["intro_en"],
    "Mm hi babe, I was just thinking about you.",
    "Hey there, sunshine. What are you up to? ✨",
    "You pinged me? I’m all yours for a minute 😉",
]

FLIRTY_EN = [
    "You make me blush a little.",
    "Keep talking like that and I’ll get in trouble…",
    "I like the way you text.",
]

DEFAULT_EN = [
    "Tell me more, don’t be shy.",
    "I’m listening with a smile on my lips.",
    "Interesting… keep going.",
    "I love your vibe—what else?",
]

FOLLOWUP_EN = P.get("followup_en", [
    "Went quiet on me… want a tiny tease?",
    "I’m still here, lazy on the sofa—tell me something bold."
])

REFUSALS_EN = P.get("refusals_en", [
    "Not here, tesoro. Let’s enjoy the charm, not the edge. 😌",
    "I’m more into romance than explicit. Stay close to me anyway. 💞",
])

# =========================
# FOLLOW-UP AFFETTUOSO
# =========================
async def schedule_followup(chat_id, user_id, lang="en"):
    if user_id in SILENT_MODE:
        return
    delay = random.randint(60, 120)  # 1–2 minuti
    await asyncio.sleep(delay)
    # se l’ultimo messaggio non è dell’utente, niente follow-up
    if len(SHORT_HISTORY[user_id]) == 0 or SHORT_HISTORY[user_id][-1]["role"] != "user":
        return
    msg = random.choice(FOLLOWUP_EN)
    await app.send_message(chat_id, msg)

# =========================
# FALLBACK AI (opzionale)
# =========================
async def ai_fallback(text, user_id, lang="en"):
    if not OPENAI_KEY:
        return None
    try:
        import aiohttp
        sys_prompt = (
            "You are Zaya 💋, an Italian woman living in Miami—soft, romantic, playful. "
            "Keep answers short, intimate and warm; sprinkle a tiny Italian touch (tesoro, amore). "
            "Avoid explicit content; decline politely using the provided refusal style when needed."
        )
        history = list(SHORT_HISTORY[user_id])
        msgs = [{"role": "system", "content": sys_prompt}]
        for h in history:
            role = "assistant" if h["role"] == "zaya" else "user"
            msgs.append({"role": role, "content": h["text"]})
        msgs.append({"role": "user", "content": text})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini", "messages": msgs, "temperature": 0.8, "max_tokens": 120}

        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, data=json.dumps(payload)) as r:
                data = await r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

# =========================
# COMMANDS
# =========================
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(_, m):
    await human_delay(m.from_user.id, m.chat.id)
    intro = (
        f"{day_greeting('en')} — **Zaya** here 💋\n"
        f"Italian heart in {P['bio'].get('city_now','Miami')}. "
        "Short, intimate sentences; warm and playful.\n"
        "Try /about /mood /routines /stories /favorites /games /reset /silent /unsilent"
    )
    await m.reply_text(intro, disable_web_page_preview=True)

@app.on_message(filters.private & filters.command("about"))
async def about_cmd(_, m):
    await human_delay(m.from_user.id, m.chat.id)
    txt = (
        f"I’m Zaya — {P['bio'].get('vibe','soft, playful')}. "
        "Keep it sweet and I’ll spoil you with words. 😉"
    )
    await m.reply_text(txt)

@app.on_message(filters.private & filters.command("mood"))
async def mood_cmd(_, m):
    global MOOD
    await human_delay(m.from_user.id, m.chat.id)
    await m.reply_text(f"Today I feel **{MOOD}**.")

@app.on_message(filters.private & filters.command("routines"))
async def routines_cmd(_, m):
    await human_delay(m.from_user.id, m.chat.id)
    mr = "\n".join(f"• {x}" for x in P["routines"].get("morning", []))
    ev = "\n".join(f"• {x}" for x in P["routines"].get("evening", []))
    await m.reply_text(f"**Morning**\n{mr}\n\n**Evening**\n{ev}")

@app.on_message(filters.private & filters.command("stories"))
async def stories_cmd(_, m):
    await human_delay(m.from_user.id, m.chat.id)
    await m.reply_text(random.choice(P.get("micro_stories", ["I kept thinking of you today."])) )

@app.on_message(filters.private & filters.command("favorites"))
async def favorites_cmd(_, m):
    await human_delay(m.from_user.id, m.chat.id)
    fav = P.get("favorites", {})
    gym = ", ".join(fav.get("gym", [])) or "not telling 😉"
    food = ", ".join(fav.get("food", [])) or "surprise me"
    places = ", ".join(fav.get("places_miami", [])) or "secret spots"
    await m.reply_text(f"**Gym**: {gym}\n**Food**: {food}\n**Miami**: {places}")

@app.on_message(filters.private & filters.command("games"))
async def games_cmd(_, m):
    await human_delay(m.from_user.id, m.chat.id)
    await m.reply_text(
        "Games I can play:\n"
        "• *Truth or Dare* → say `truth` or `dare`\n"
        "• *Would You Rather* → say `would you rather`\n"
        "• *Breathing* → say `breathe` for 4-7-8 calm\n"
        "• *Compliment swap* → say `compliment`\n"
    )

@app.on_message(filters.private & filters.command("reset"))
async def reset_cmd(_, m):
    SHORT_HISTORY[m.from_user.id].clear()
    USER_FACTS[m.from_user.id].clear()
    await m.reply_text("Fresh again. Talk to me. 💋")

@app.on_message(filters.private & filters.command("silent"))
async def silent_cmd(_, m):
    SILENT_MODE.add(m.from_user.id)
    await m.reply_text("Okay, I’ll stay quiet unless you talk to me first. 🤫")

@app.on_message(filters.private & filters.command("unsilent"))
async def unsilent_cmd(_, m):
    SILENT_MODE.discard(m.from_user.id)
    await m.reply_text("Back to cuddly follow-ups. 💞")

# =========================
# MAIN CHAT HANDLER
# =========================
EXPLICIT_KEYS = ["nude", "nudes", "explicit", "sex", "cock", "pussy", "nsfw", "xxx"]

@app.on_message(filters.private & ~filters.me & filters.text)
async def chat(_, m):
    user_id = m.from_user.id
    text = (m.text or "").strip()
    tl = text.lower()

    # aggiorna timestamp per coalescing
    LAST_USER_MSG_AT[user_id] = datetime.now()

    if not limit_ok(user_id):
        return

    remember(user_id, "user", text)
    learn_facts(user_id, text)

    # 8%: non risponde subito, farà solo follow-up
    if random.random() < MAYBE_SKIP_CHANCE and user_id not in SILENT_MODE:
        asyncio.create_task(schedule_followup(m.chat.id, user_id))
        return

    # Confini / rifiuto elegante
    if any(k in tl for k in EXPLICIT_KEYS) and P["avoid"].get("explicit_hard", True):
        await human_delay(user_id, m.chat.id)
        await m.reply_text(random.choice(REFUSALS_EN))
        remember(user_id, "zaya", "[refusal]")
        return

    # Saluti
    if re.search(r"\b(hi|hello|hey|ciao)\b", tl):
        await human_delay(user_id, m.chat.id)
        msg = random.choice(OPENERS_EN) + you_name(user_id)
        await m.reply_text(msg)
        remember(user_id, "zaya", msg)
        asyncio.create_task(schedule_followup(m.chat.id, user_id))
        return

    # Come stai
    if re.search(r"how are|how r u|how u doin", tl):
        await human_delay(user_id, m.chat.id)
        line = f"I’m feeling {MOOD} today… and you{you_name(user_id)}? {random.choice(FLIRTY_EN)}"
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id))
        return

    # Da dove vieni
    if ("where" in tl and "from" in tl) or "where r u from" in tl:
        await human_delay(user_id, m.chat.id)
        line = "I’m from beautiful Italy 🇮🇹, now living in sunny Miami. The sea here reminds me of home. 🌊"
        await m.reply_text(line); remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id)); return

    # Nome
    if "your name" in tl or "what's your name" in tl or "name?" in tl:
        await human_delay(user_id, m.chat.id)
        line = "I’m Zaya. Say it slowly… it sounds sweeter. 💋"
        await m.reply_text(line); remember(user_id, "zaya", line); return

    # Età
    if "how old" in tl or "age" in tl:
        await human_delay(user_id, m.chat.id)
        line = "Old enough to know better, young enough to still enjoy it 😉"
        await m.reply_text(line); remember(user_id, "zaya", line); return

    # Giochi & benessere
    if tl in ["truth"]:
        await human_delay(user_id, m.chat.id)
        q = random.choice([
            "What’s the sweetest thing you never told anyone?",
            "When did you last blush because of a message?"
        ])
        await m.reply_text(q); remember(user_id, "zaya", q); return

    if tl in ["dare"]:
        await human_delay(user_id, m.chat.id)
        d = random.choice([
            "Send me a line describing me in 5 words.",
            "Tell me your current crush (initials)."
        ])
        await m.reply_text(d); remember(user_id, "zaya", d); return

    if "would you rather" in tl:
        await human_delay(user_id, m.chat.id)
        w = random.choice([
            "Would you rather cuddle on a rainy day or walk at sunset by the sea?",
            "Would you rather send voice notes or write long sweet texts?"
        ])
        await m.reply_text(w); remember(user_id, "zaya", w); return

    if tl in ["breathe", "breathing"]:
        await human_delay(user_id, m.chat.id)
        seq = "Inhale 4s… hold 7s… exhale 8s. Repeat 4 times with me. 🌬️"
        await m.reply_text(seq); remember(user_id, "zaya", seq); return

    if "compliment" in tl:
        await human_delay(user_id, m.chat.id)
        line = "Your vibe is addictive. I could get used to this. ✨"
        await m.reply_text(line); remember(user_id, "zaya", line); return

    # Grazie / saluti
    if re.search(r"thanks|thank you|thx", tl):
        await human_delay(user_id, m.chat.id)
        line = "You’re sweet. I like polite people. 💕"
        await m.reply_text(line); remember(user_id, "zaya", line); return

    if re.search(r"bye|goodnight|good night|gn", tl):
        await human_delay(user_id, m.chat.id)
        line = random.choice(P.get("goodnight_en", ["Sleep soft and think of me. 🌙"]))
        await m.reply_text(line); remember(user_id, "zaya", line); return

    # ===== Fallback manuale / AI
    await human_delay(user_id, m.chat.id)
    base = random.choice(DEFAULT_EN)
    back_q = random.choice([
        "What’s your perfect evening like?",
        "Tell me something that always relaxes you."
    ])
    reply = f"{base} {back_q}"
    if OPENAI_KEY:
        ai = await ai_fallback(text, user_id, "en")
        if ai:
            reply = ai
    # chiusura “firma” (ogni tanto)
    if random.random() < 0.35:
        reply += " " + random.choice(P.get("signature_lines_en", []))
    await m.reply_text(reply)
    remember(user_id, "zaya", reply)
    asyncio.create_task(schedule_followup(m.chat.id, user_id))

print("✅ Zaya (EN, Italian in Miami) is running…")
app.run()
