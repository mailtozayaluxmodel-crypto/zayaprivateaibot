import os, re, json, random, asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

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
# PROFILO (opzionale via profile.json)
# =========================
PROFILE = {
    "persona": {
        "name": "Zaya",
        "bio": "Italian woman living in Miami — soft, playful, feminine energy. Speaks short, intimate English lines with a tiny Italian flavor.",
        "style": "short, warm, flirty-but-classy, romantic over explicit",
        "language": "en",
        "spiciness": 2
    },
    "boundaries": {
        "avoid": ["illegal content", "violence", "hate speech", "minors", "explicit sexual details", "self-harm"],
        "refusals_en": [
            "I like to keep it romantic and classy, not explicit. Let’s keep it sweet, amore. 💕",
            "I’m more into warmth than graphic details. Stay close to me anyway. 💫"
        ]
    }
}
try:
    with open("profile.json", "r", encoding="utf-8") as f:
        PROFILE = {**PROFILE, **json.load(f)}
except Exception:
    pass

REFUSALS_EN = PROFILE["boundaries"]["refusals_en"]

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
SHORT_HISTORY = defaultdict(lambda: deque(maxlen=12))  # scambi recenti
USER_FACTS    = defaultdict(dict)                      # name, city, likes
COOLDOWN      = defaultdict(lambda: datetime.min)      # antispam per-utente
MOOD = "soft & playful"                                # umore globale
SILENT_MODE = set()                                    # utenti senza follow-up
LAST_USER_MSG_AT = defaultdict(lambda: datetime.min)   # coalescing

# =========================
# NATURALITÀ RISPOSTE
# =========================
NATURAL_GAP      = (2.5, 9.0)    # ritardo tipico prima di rispondere
LONG_GAP_CHANCE  = 0.28          # 28% delle volte usa un ritardo lungo
LONG_GAP_RANGE   = (12, 35)      # range ritardi lunghi
MAYBE_SKIP_CHANCE= 0.08          # 8%: non risponde subito, solo follow-up

async def typing_burst(chat_id, cycles=None):
    """Simula 'sta scrivendo' in ondate (più umano)."""
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
    """Semplice rate-limit per evitare flood/loop."""
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
        if m3: USER_FACTS[user_id].setdefault("likes", set()).add(m3.group(2).strip())

def you_name(user_id, lang):
    n = USER_FACTS[user_id].get("name")
    if not n: return ""
    return f", {n}" if lang=="en" else f", {n}"

# =========================
# PERSONA (Eng/It)
# =========================
OPENERS_EN = [
    "Hey… I’m Zaya 💋 I like starting my day with someone sweet.",
    "Mm hi babe, I was just thinking about you.",
    "Hey there, sunshine. What are you up to? ✨",
    "You pinged me? I’m all yours for a minute 😉"
]
OPENERS_IT = [
    "Ehi… sono Zaya 💋 Mi piace iniziare la giornata con qualcuno di dolce.",
    "Mm ciao amore, stavo pensando proprio a te.",
    "Ehi stella, che combini? ✨",
    "Mi hai cercata? Per un minuto sono tutta tua 😉",
]
FLIRTY_EN = [
    "You make me blush a little.",
    "Keep talking like that and I’ll get in trouble…",
    "I like the way you text."
]
FLIRTY_IT = [
    "Mi fai arrossire un pochino.",
    "Continua così e mi metti nei guai…",
    "Mi piace come scrivi."
]
DEFAULT_EN = [
    "Tell me more, don’t be shy.",
    "I’m listening with a smile on my lips.",
    "Interesting… keep going.",
    "I love your vibe—what else?"
]
DEFAULT_IT = [
    "Dimmi di più, non essere timido.",
    "Ti ascolto con un sorriso sulle labbra.",
    "Interessante… continua.",
    "Mi piace la tua energia—cos’altro?"
]
FOLLOWUP_EN = [
    "Went quiet on me. Should I tease you a bit more? 😉",
    "I’m still here, stretching on the sofa… tell me something bold.",
    "Thinking of a question for you… What’s your guilty pleasure?"
]
FOLLOWUP_IT = [
    "Sei sparito all’improvviso. Devo stuzzicarti un po’? 😉",
    "Sono ancora qui, distesa sul divano… dimmi qualcosa di audace.",
    "Sto pensando a una domanda… Qual è il tuo guilty pleasure?"
]

# =========================
# FOLLOW-UP AFFETTUOSO
# =========================
async def schedule_followup(chat_id, user_id, lang):
    if user_id in SILENT_MODE:
        return
    delay = random.randint(60, 120)
    await asyncio.sleep(delay)
    # manda follow-up solo se l’ultimo è dell’utente
    if len(SHORT_HISTORY[user_id]) == 0 or SHORT_HISTORY[user_id][-1]["role"] != "user":
        return
    msg = random.choice(FOLLOWUP_EN if lang=="en" else FOLLOWUP_IT)
    await app.send_message(chat_id, msg)

# =========================
# HARDENING: limiti, mute, blocklist, sicurezza
# =========================
MAX_MSG_PER_MIN = 8
BURST_WINDOW_S  = 8
BURST_MAX       = 4
TEMP_MUTE_MIN   = 5

USER_MINUTE_BUCKET   = defaultdict(lambda: deque(maxlen=MAX_MSG_PER_MIN*2))
USER_BURST_TIMES     = defaultdict(lambda: deque(maxlen=BURST_MAX*2))
USER_MUTED_UNTIL     = defaultdict(lambda: datetime.min)
BLOCKLIST            = set()

HARD_BLOCK_TERMS = {
    "illegal": ["cp", "bestiality", "zoophilia"],
    "hate": ["heil", "gas the", "white power"],
}
EXPLICIT_KEYS = ["nude", "nudes", "explicit", "sex", "cock", "pussy", "nsfw", "xxx"]

def is_hard_block(text: str) -> bool:
    t = (text or "").lower()
    for _, words in HARD_BLOCK_TERMS.items():
        if any(w in t for w in words):
            return True
    return False

def register_rate(user_id: int) -> tuple[bool, str|None]:
    now = datetime.now()
    if USER_MUTED_UNTIL[user_id] > now:
        return False, "muted"
    bucket = USER_MINUTE_BUCKET[user_id]
    bucket.append(now)
    while bucket and (now - bucket[0]).total_seconds() > 60:
        bucket.popleft()
    burst = USER_BURST_TIMES[user_id]
    burst.append(now)
    while burst and (now - burst[0]).total_seconds() > BURST_WINDOW_S:
        burst.popleft()
    if len(burst) >= BURST_MAX:
        USER_MUTED_UNTIL[user_id] = now + timedelta(minutes=TEMP_MUTE_MIN)
        return False, "burst"
    if len(bucket) > MAX_MSG_PER_MIN:
        USER_MUTED_UNTIL[user_id] = now + timedelta(minutes=TEMP_MUTE_MIN)
        return False, "rate"
    return True, None

@asynccontextmanager
async def ai_timeout(seconds=10):
    try:
        timer = asyncio.create_task(asyncio.sleep(seconds))
        yield
    finally:
        if not timer.done():
            timer.cancel()

# =========================
# FALLBACK AI (opzionale)
# =========================
async def ai_fallback(text, user_id, lang="en"):
    if not OPENAI_KEY:
        return None
    try:
        import aiohttp
        sys_prompt_en = (
            "You are Zaya 💋, an Italian woman living in Miami—soft, playful, romantic. "
            "Write short, intimate English messages with a tiny Italian flavor. "
            "No explicit sexual content; prefer romance, warmth, and classy teasing. "
            "Keep messages 1–2 sentences and ask gentle questions sometimes."
        )
        sys_prompt_it = (
            "Sei Zaya 💋, italiana a Miami—dolce, giocosa, romantica. "
            "Frasi brevi e intime. Mai contenuti sessuali espliciti; preferisci il calore e l’eleganza."
        )
        sys_prompt = sys_prompt_en if lang=="en" else sys_prompt_it
        history = list(SHORT_HISTORY[user_id])
        msgs = [{"role": "system", "content": sys_prompt}]
        for h in history:
            role = "assistant" if h["role"] == "zaya" else "user"
            msgs.append({"role": role, "content": h["text"]})
        msgs.append({"role": "user", "content": text})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini", "messages": msgs, "temperature": 0.8, "max_tokens": 120}

        async with ai_timeout(12):
            async with aiohttp.ClientSession() as s:
                async with s.post(url, headers=headers, data=json.dumps(payload)) as r:
                    data = await r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

# =========================
# COMANDI
# =========================
@app.on_message(filters.private & filters.command("start"))
async def start_cmd(_, m):
    lang = "it" if detect_lang(m.text or "") == "it" else "en"
    await human_delay(m.from_user.id, m.chat.id)
    intro = (
        f"{day_greeting(lang)} — I’m **{PROFILE['persona']['name']}** 💋\n"
        "Italian heart in sunny Miami. Short, intimate lines; warm and playful.\n"
        "Ask me anything, or try /about /mood /games /reset /silent /unsilent"
        if lang == "en" else
        f"{day_greeting(lang)} — **Zaya** qui 💋\n"
        "Musa mediterranea a Miami. Frasi brevi, intime; calda e giocosa.\n"
        "Chiedimi qualcosa, o prova /about /mood /games /reset /silent /unsilent"
    )
    await m.reply_text(intro, disable_web_page_preview=True)

@app.on_message(filters.private & filters.command("about"))
async def about_cmd(_, m):
    lang = detect_lang(m.text or "")
    await human_delay(m.from_user.id, m.chat.id)
    txt = (
        "I’m Zaya — soft confidence, Mediterranean warmth, a tiny hint of trouble. "
        "Keep it sweet and I’ll spoil you with words. 😉"
        if lang == "en" else
        "Sono Zaya — sicurezza morbida, calore mediterraneo, un pizzico di guaio. "
        "Se sei dolce con me, ti vizio con le parole. 😉"
    )
    await m.reply_text(txt)

@app.on_message(filters.private & filters.command("mood"))
async def mood_cmd(_, m):
    global MOOD
    lang = detect_lang(m.text or "")
    await human_delay(m.from_user.id, m.chat.id)
    res = f"Today I feel **{MOOD}**." if lang == "en" else f"Oggi mi sento **{MOOD}**."
    await m.reply_text(res)

@app.on_message(filters.private & filters.command("games"))
async def games_cmd(_, m):
    lang = detect_lang(m.text or "")
    await human_delay(m.from_user.id, m.chat.id)
    if lang == "en":
        await m.reply_text(
            "Games I can play:\n"
            "• *Truth or Dare* → say `truth` or `dare`\n"
            "• *Would You Rather* → say `would you rather`\n"
            "• *Breathing* → say `breathe` for 4-7-8 calm\n"
            "• *Compliment swap* → say `compliment`\n"
        )
    else:
        await m.reply_text(
            "Giochini che posso fare:\n"
            "• *Verità o Penitenza* → scrivi `verità` o `penitenza`\n"
            "• *Preferiresti* → scrivi `preferiresti`\n"
            "• *Respirazione* → scrivi `respira` per 4-7-8\n"
            "• *Scambio complimenti* → scrivi `complimento`\n"
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

# Admin: block / unblock / mutestatus
@app.on_message(filters.private & filters.command("block"))
async def cmd_block(_, m):
    try:
        target = int(m.text.split(maxsplit=1)[1])
    except Exception:
        return await m.reply_text("Use: /block <user_id>")
    BLOCKLIST.add(target)
    await m.reply_text(f"Blocked user {target}.")

@app.on_message(filters.private & filters.command("unblock"))
async def cmd_unblock(_, m):
    try:
        target = int(m.text.split(maxsplit=1)[1])
    except Exception:
        return await m.reply_text("Use: /unblock <user_id>")
    BLOCKLIST.discard(target)
    await m.reply_text(f"Unblocked user {target}.")

@app.on_message(filters.private & filters.command("mutestatus"))
async def cmd_mutestatus(_, m):
    until = USER_MUTED_UNTIL[m.from_user.id]
    if until > datetime.now():
        mins = int((until - datetime.now()).total_seconds()//60)+1
        return await m.reply_text(f"You're muted for ~{mins} min (anti-spam).")
    await m.reply_text("No mute active.")

# =========================
# HANDLER PRINCIPALE
# =========================
@app.on_message(filters.private & ~filters.me & filters.text)
async def chat(_, m):
    user_id = m.from_user.id
    text = (m.text or "").strip()
    tl = text.lower()
    lang = detect_lang(text)

    # coalescing
    LAST_USER_MSG_AT[user_id] = datetime.now()

    # blocklist
    if user_id in BLOCKLIST:
        return

    # hard-block (termini proibiti)
    if is_hard_block(text):
        USER_MUTED_UNTIL[user_id] = datetime.now() + timedelta(minutes=TEMP_MUTE_MIN*2)
        return

    # rate-limit / burst / mute
    ok, reason = register_rate(user_id)
    if not ok:
        if reason in ("burst", "rate") and USER_MUTED_UNTIL[user_id] > datetime.now():
            try:
                await m.reply_text("Slow down a little, tesoro. I’m still here. 💕")
            except Exception:
                pass
        return
    if USER_MUTED_UNTIL[user_id] > datetime.now():
        return

    remember(user_id, "user", text)
    learn_facts(user_id, text)

    # 8%: nessuna risposta immediata, solo follow-up
    if random.random() < MAYBE_SKIP_CHANCE and user_id not in SILENT_MODE:
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # saluti
    if re.search(r"\b(hi|hello|hey|ciao)\b", tl):
        await human_delay(user_id, m.chat.id)
        msg = random.choice(OPENERS_EN if lang == "en" else OPENERS_IT)
        msg += you_name(user_id, lang)
        await m.reply_text(msg)
        remember(user_id, "zaya", msg)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # come stai
    if re.search(r"how are|come stai", tl):
        await human_delay(user_id, m.chat.id)
        line = (
            f"I’m feeling {MOOD} today… and you{you_name(user_id, 'en')}? "
            f"{random.choice(FLIRTY_EN)}"
            if lang == "en" else
            f"Oggi mi sento {MOOD}… e tu{you_name(user_id, 'it')}? "
            f"{random.choice(FLIRTY_IT)}"
        )
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # da dove vieni
    if ("where" in tl and "from" in tl) or "da dove" in tl:
        await human_delay(user_id, m.chat.id)
        line = (
            "I’m from beautiful Italy 🇮🇹, now living in sunny Miami. The sea here reminds me of home. 🌊"
            if lang == "en" else
            "Sono della bellissima Italia 🇮🇹, ora vivo nella solare Miami. Il mare qui mi ricorda casa. 🌊"
        )
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # nome
    if re.search(r"your name|come ti chiami|nome", tl):
        await human_delay(user_id, m.chat.id)
        line = "I’m Zaya. Say it slowly… it sounds sweeter. 💋" if lang=="en" else "Sono Zaya. Dillo piano… suona più dolce. 💋"
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        return

    # età
    if re.search(r"how old|age|quanti anni", tl):
        await human_delay(user_id, m.chat.id)
        line = "Old enough to know better, young enough to still enjoy it 😉" if lang=="en" else "Abbastanza grande da sapere, abbastanza giovane per godermela 😉"
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        return

    # esplicito → rifiuto elegante
    if any(k in tl for k in EXPLICIT_KEYS):
        await human_delay(user_id, m.chat.id)
        await m.reply_text(random.choice(REFUSALS_EN))
        remember(user_id, "zaya", "[refusal]")
        recent = [h for h in list(SHORT_HISTORY[user_id])[-6:] if h["role"] == "user"]
        explicit_hits = sum(any(k in (h["text"] or "").lower() for k in EXPLICIT_KEYS) for h in recent)
        if explicit_hits >= 3:
            SILENT_MODE.add(user_id)
            USER_MUTED_UNTIL[user_id] = datetime.now() + timedelta(minutes=TEMP_MUTE_MIN)
        return

    # giochi & benessere
    if tl in ["truth", "verità"]:
        await human_delay(user_id, m.chat.id)
        q = random.choice([
            "What’s the sweetest thing you never told anyone?",
            "When did you last blush because of a message?"
        ]) if lang == "en" else random.choice([
            "Qual è la cosa più dolce che non hai mai detto a nessuno?",
            "Quando è stata l’ultima volta che sei arrossito per un messaggio?"
        ])
        await m.reply_text(q); remember(user_id, "zaya", q); return

    if tl in ["dare", "penitenza", "sfida"]:
        await human_delay(user_id, m.chat.id)
        d = random.choice([
            "Send me a line describing me in 5 words.",
            "Tell me your current crush (initials)."
        ]) if lang == "en" else random.choice([
            "Descrivimi in 5 parole.",
            "Dimmi le iniziali della tua crush."
        ])
        await m.reply_text(d); remember(user_id, "zaya", d); return

    if "would you rather" in tl or "preferiresti" in tl:
        await human_delay(user_id, m.chat.id)
        w = random.choice([
            "Would you rather cuddle on a rainy day or walk at sunset by the sea?",
            "Would you rather send voice notes or write long sweet texts?"
        ]) if lang == "en" else random.choice([
            "Preferiresti abbracci sul divano quando piove o passeggiare al tramonto sul mare?",
            "Preferiresti note vocali o lunghi messaggi dolci?"
        ])
        await m.reply_text(w); remember(user_id, "zaya", w); return

    if tl in ["breathe", "respira", "respirazione", "breathing"]:
        await human_delay(user_id, m.chat.id)
        seq = "Inhale 4s… hold 7s… exhale 8s. Repeat 4 times with me. 🌬️" if lang=="en" \
              else "Inspira 4s… trattieni 7s… espira 8s. Ripeti 4 volte con me. 🌬️"
        await m.reply_text(seq); remember(user_id,"zaya",seq); return

    if "compliment" in tl or "complimento" in tl:
        await human_delay(user_id, m.chat.id)
        line = "Your vibe is addictive. I could get used to this. ✨" if lang=="en" \
               else "La tua vibrazione è contagiosa. Potrei farci l’abitudine. ✨"
        await m.reply_text(line); remember(user_id,"zaya",line); return

    # fallback
    await human_delay(user_id, m.chat.id)
    base = random.choice(DEFAULT_EN if lang == "en" else DEFAULT_IT)
    back_q = random.choice([
        "What’s your perfect evening like?",
        "Tell me something that always relaxes you."
    ]) if lang == "en" else random.choice([
        "Com’è la tua serata perfetta?",
        "Dimmi qualcosa che ti rilassa sempre."
    ])
    reply = f"{base} {back_q}"
    if OPENAI_KEY:
        ai = await ai_fallback(text, user_id, lang)
        if ai: reply = ai
    await m.reply_text(reply)
    remember(user_id, "zaya", reply)
    asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))

print("✅ Zaya (EN) realistic + safeguards running…")
app.run()
