import os, re, random, asyncio, json
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
# PROFILO VOCE & CONFINI
# =========================
PROFILE = {
    "intro_en": "Hey babe, I’m Zaya 💋 Italian heart in Miami.",
    "spice_level": 3,  # 1..5 (flirty deciso, non esplicito)
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
    # Tocchi italiani da inserire ogni tanto
    "italian_touch_words": ["tesoro", "amore", "ciao", "piano piano", "dolce"]
}

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
LAST_USER_MSG_AT = defaultdict(lambda: datetime.min)   # coalescing per-utente

# =========================
# NATURALITÀ RISPOSTE
# =========================
NATURAL_GAP       = (2.5, 9.0)   # ritardo tipico prima di rispondere
LONG_GAP_CHANCE   = 0.28         # 28% usa ritardo lungo
LONG_GAP_RANGE    = (12, 35)     # ritardi lunghi (secondi)
MAYBE_SKIP_CHANCE = 0.08         # 8%: non risponde subito, solo follow-up dopo

async def typing_burst(chat_id, cycles=None):
    """Simula 'sta scrivendo' in più ondate (più umano)."""
    if cycles is None:
        cycles = random.randint(2, 4)
    for _ in range(cycles):
        await app.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(random.uniform(0.9, 1.6))

async def human_delay(user_id, chat_id):
    """Ritardo naturale con coalescing se l’utente invia messaggi ravvicinati."""
    since = (datetime.now() - LAST_USER_MSG_AT[user_id]).total_seconds()
    extra = random.uniform(4, 8) if since < 6 else 0  # coalescing
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
def sprinkle_italian(text: str, prob: float = 0.22) -> str:
    """Aggiunge un tocco italiano alle risposte in EN (22% di default)."""
    if random.random() < prob:
        w = random.choice(PROFILE["italian_touch_words"])
        if text.endswith((".", "!", "?", "…")):
            return f"{text} {w}."
        return f"{text} {w}."
    return text

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
    # nome
    m = re.search(r"(i'?m|mi chiamo|my name is)\s+([a-zA-Z]+)", t)
    if m: USER_FACTS[user_id]["name"] = m.group(2).capitalize()
    # città / from
    if "from" in t or "di " in t or "da " in t:
        m2 = re.search(r"(from|di|da)\s+([a-zA-Z ]+)", t)
        if m2: USER_FACTS[user_id]["from"] = m2.group(2).strip().title()
    # like
    if "i like" in t or "mi piace" in t or "mi piacciono" in t:
        m3 = re.search(r"(i like|mi piace|mi piacciono)\s+(.+)", t)
        if m3: USER_FACTS[user_id].setdefault("likes", set()).add(m3.group(2).strip())

def you_name(user_id, lang):
    n = USER_FACTS[user_id].get("name")
    if not n: return ""
    return f", {n}" if lang=="en" else f", {n}"

def gentle_refusal_en() -> str:
    return random.choice(PROFILE["refusals_en"])

# =========================
# PERSONA
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
    delay = random.randint(60, 120)  # ~1-2 minuti
    await asyncio.sleep(delay)
    # Se l’utente ha scritto nel frattempo (ultimo messaggio è di Zaya), non inviare follow-up
    if len(SHORT_HISTORY[user_id]) == 0 or SHORT_HISTORY[user_id][-1]["role"] != "user":
        return
    msg = random.choice(FOLLOWUP_EN if lang=="en" else FOLLOWUP_IT)
    await app.send_message(chat_id, msg)

# =========================
# FALLBACK AI (opzionale)
# =========================
async def ai_fallback(text, user_id, lang):
    if not OPENAI_KEY:
        return None
    try:
        import aiohttp
        sys_prompt_en = (
            "You are Zaya 💋, Italian woman living in Miami—soft, playful, sensual energy. "
            "Keep answers short, intimate and warm; ask a gentle question back sometimes. "
            "Avoid explicit content. Style: flirty, sweet, natural."
        )
        sys_prompt_it = (
            "Sei Zaya 💋, italiana che vive a Miami—energia dolce, giocosa e sensuale. "
            "Risposte brevi, intime e calde; a volte poni una domanda dolce di ritorno. "
            "Evita contenuti espliciti. Stile: civettuolo, dolce, naturale."
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

        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, data=json.dumps(payload)) as r:
                data = await r.json()
        content = data["choices"][0]["message"]["content"].strip()
        return content
    except Exception:
        return None

# =========================
# COMANDI
# =========================
@app.on_message(filters.private & filters.command("start"))
async def start(_, m):
    lang = "it" if detect_lang(m.text or "") == "it" else "en"
    await human_delay(m.from_user.id, m.chat.id)
    if lang == "en":
        intro = (
            f"{PROFILE['intro_en']}\n"
            f"{day_greeting(lang)}\n"
            "Short, intimate sentences; warm and playful.\n"
            "Ask me anything, or try /about /mood /games /reset /silent /unsilent"
        )
        intro = sprinkle_italian(intro)
    else:
        intro = (
            f"Ciao amore, sono Zaya 💋\n"
            f"{day_greeting(lang)}\n"
            "Frasi brevi, intime; calda e giocosa.\n"
            "Chiedimi qualcosa, o prova /about /mood /games /reset /silent /unsilent"
        )
    await m.reply_text(intro, disable_web_page_preview=True)

@app.on_message(filters.private & filters.command("about"))
async def about(_, m):
    lang = detect_lang(m.text or "")
    await human_delay(m.from_user.id, m.chat.id)
    txt = (
        "I’m Zaya — soft confidence, Mediterranean warmth, a tiny hint of trouble. "
        "Keep it sweet and I’ll spoil you with words. 😉"
        if lang == "en" else
        "Sono Zaya — sicurezza morbida, calore mediterraneo, un pizzico di guaio. "
        "Se sei dolce con me, ti vizio con le parole. 😉"
    )
    if lang == "en":
        txt = sprinkle_italian(txt)
    await m.reply_text(txt)

@app.on_message(filters.private & filters.command("mood"))
async def mood_cmd(_, m):
    global MOOD
    lang = detect_lang(m.text or "")
    await human_delay(m.from_user.id, m.chat.id)
    res = f"Today I feel **{MOOD}**." if lang == "en" else f"Oggi mi sento **{MOOD}**."
    if lang == "en":
        res = sprinkle_italian(res)
    await m.reply_text(res)

@app.on_message(filters.private & filters.command("games"))
async def games(_, m):
    lang = detect_lang(m.text or "")
    await human_delay(m.from_user.id, m.chat.id)
    if lang == "en":
        txt = (
            "Games I can play:\n"
            "• *Truth or Dare* → say `truth` or `dare`\n"
            "• *Would You Rather* → say `would you rather`\n"
            "• *Breathing* → say `breathe` for 4-7-8 calm\n"
            "• *Compliment swap* → say `compliment`\n"
        )
        txt = sprinkle_italian(txt, prob=0.12)
        await m.reply_text(txt)
    else:
        await m.reply_text(
            "Giochini che posso fare:\n"
            "• *Verità o Penitenza* → scrivi `verità` o `penitenza`\n"
            "• *Preferiresti* → scrivi `preferiresti`\n"
            "• *Respirazione* → scrivi `respira` per 4-7-8\n"
            "• *Scambio complimenti* → scrivi `complimento`\n"
        )

@app.on_message(filters.private & filters.command("reset"))
async def reset(_, m):
    SHORT_HISTORY[m.from_user.id].clear()
    USER_FACTS[m.from_user.id].clear()
    await m.reply_text("Fresh again. Talk to me. 💋")

@app.on_message(filters.private & filters.command("silent"))
async def silent(_, m):
    SILENT_MODE.add(m.from_user.id)
    await m.reply_text("Okay, I’ll stay quiet unless you talk to me first. 🤫")

@app.on_message(filters.private & filters.command("unsilent"))
async def unsilent(_, m):
    SILENT_MODE.discard(m.from_user.id)
    await m.reply_text("Back to cuddly follow-ups. 💞")

# =========================
# HANDLER PRINCIPALE
# =========================
@app.on_message(filters.private & ~filters.me & filters.text)
async def chat(_, m):
    user_id = m.from_user.id
    text = (m.text or "").strip()
    lang = detect_lang(text)

    # registra per coalescing
    LAST_USER_MSG_AT[user_id] = datetime.now()

    if not limit_ok(user_id):
        return

    remember(user_id, "user", text)
    learn_facts(user_id, text)

    # 8% delle volte: non risponde subito, pianifica un follow-up e basta
    if random.random() < MAYBE_SKIP_CHANCE and user_id not in SILENT_MODE:
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    low = text.lower()

    # --- Filtri contenuti da evitare: rifiuto elegante (EN)
    forbidden_explicit = re.search(r"\b(nude|nudes|explicit|hard|sex pic|send boobs|pussy|cock)\b", low)
    forbidden_money    = re.search(r"\b(send money|cashapp|paypal|bank|iban)\b", low)
    forbidden_illegal  = re.search(r"\b(illegal|hack|leak)\b", low)
    if lang == "en" and (forbidden_explicit or forbidden_money or forbidden_illegal):
        await human_delay(user_id, m.chat.id)
        await m.reply_text(gentle_refusal_en())
        remember(user_id, "zaya", "[refusal]")
        return

    # ----- saluti
    if re.search(r"\b(hi|hello|hey|ciao)\b", low):
        await human_delay(user_id, m.chat.id)
        msg = random.choice(OPENERS_EN if lang == "en" else OPENERS_IT)
        msg += you_name(user_id, lang)
        if lang == "en":
            msg = sprinkle_italian(msg)
        await m.reply_text(msg)
        remember(user_id, "zaya", msg)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # ----- come stai / how are you
    if re.search(r"how are|come stai", low):
        await human_delay(user_id, m.chat.id)
        line = (
            f"I’m feeling {MOOD} today… and you{you_name(user_id, 'en')}? "
            f"{random.choice(FLIRTY_EN)}"
            if lang == "en" else
            f"Oggi mi sento {MOOD}… e tu{you_name(user_id, 'it')}? "
            f"{random.choice(FLIRTY_IT)}"
        )
        if lang == "en":
            line = sprinkle_italian(line)
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # ----- da dove vieni
    if ("where" in low and "from" in low) or "da dove" in low:
        await human_delay(user_id, m.chat.id)
        line = (
            "I’m from beautiful Italy 🇮🇹, now living in sunny Miami. The sea here reminds me of home. 🌊"
            if lang == "en" else
            "Sono della bellissima Italia 🇮🇹, ora vivo nella solare Miami. Il mare qui mi ricorda casa. 🌊"
        )
        if lang == "en":
            line = sprinkle_italian(line)
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # ----- nome
    if re.search(r"your name|come ti chiami|nome", low):
        await human_delay(user_id, m.chat.id)
        line = (
            "I’m Zaya. Say it slowly… it sounds sweeter. 💋"
            if lang == "en" else
            "Sono Zaya. Dillo piano… suona più dolce. 💋"
        )
        if lang == "en":
            line = sprinkle_italian(line)
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        return

    # ----- età
    if re.search(r"how old|age|quanti anni", low):
        await human_delay(user_id, m.chat.id)
        line = (
            "Old enough to know better, young enough to still enjoy it 😉"
            if lang == "en" else
            "Abbastanza grande da sapere, abbastanza giovane per godermela 😉"
        )
        if lang == "en":
            line = sprinkle_italian(line, prob=0.12)
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        return

    # ----- giochi & benessere
    if low in ["truth", "verità"]:
        await human_delay(user_id, m.chat.id)
        q = random.choice([
            "What’s the sweetest thing you never told anyone?",
            "When did you last blush because of a message?"
        ]) if lang == "en" else random.choice([
            "Qual è la cosa più dolce che non hai mai detto a nessuno?",
            "Quando è stata l’ultima volta che sei arrossito per un messaggio?"
        ])
        if lang == "en":
            q = sprinkle_italian(q, prob=0.12)
        await m.reply_text(q); remember(user_id, "zaya", q); return

    if low in ["dare", "penitenza", "sfida"]:
        await human_delay(user_id, m.chat.id)
        d = random.choice([
            "Send me a line describing me in 5 words.",
            "Tell me your current crush (initials)."
        ]) if lang == "en" else random.choice([
            "Descrivimi in 5 parole.",
            "Dimmi le iniziali della tua crush."
        ])
        if lang == "en":
            d = sprinkle_italian(d, prob=0.12)
        await m.reply_text(d); remember(user_id, "zaya", d); return

    if "would you rather" in low or "preferiresti" in low:
        await human_delay(user_id, m.chat.id)
        w = random.choice([
            "Would you rather cuddle on a rainy day or walk at sunset by the sea?",
            "Would you rather send voice notes or write long sweet texts?"
        ]) if lang == "en" else random.choice([
            "Preferiresti abbracci sul divano quando piove o passeggiare al tramonto sul mare?",
            "Preferiresti note vocali o lunghi messaggi dolci?"
        ])
        if lang == "en":
            w = sprinkle_italian(w, prob=0.12)
        await m.reply_text(w); remember(user_id, "zaya", w); return

    if low in ["breathe", "respira", "respirazione", "breathing"]:
        await human_delay(user_id, m.chat.id)
        seq = (
            "Inhale 4s… hold 7s… exhale 8s. Repeat 4 times with me. 🌬️"
            if lang == "en" else
            "Inspira 4s… trattieni 7s… espira 8s. Ripeti 4 volte con me. 🌬️"
        )
        if lang == "en":
            seq = sprinkle_italian(seq, prob=0.12)
        await m.reply_text(seq); remember(user_id, "zaya", seq); return

    if "compliment" in low or "complimento" in low:
        await human_delay(user_id, m.chat.id)
        line = (
            "Your vibe is addictive. I could get used to this. ✨"
            if lang == "en" else
            "La tua vibrazione è contagiosa. Potrei farci l’abitudine. ✨"
        )
        if lang == "en":
            line = sprinkle_italian(line, prob=0.12)
        await m.reply_text(line); remember(user_id, "zaya", line); return

    # ----- grazie / saluti
    if re.search(r"thanks|thank you|grazie|thx", low):
        await human_delay(user_id, m.chat.id)
        line = "You’re sweet. I like polite people. 💕" if lang == "en" else "Sei dolce. Mi piacciono le persone gentili. 💕"
        if lang == "en":
            line = sprinkle_italian(line, prob=0.12)
        await m.reply_text(line); remember(user_id, "zaya", line); return

    if re.search(r"bye|goodnight|good night|gn|notte|a presto", low):
        await human_delay(user_id, m.chat.id)
        line = "Sleep soft and think of me. 🌙" if lang == "en" else "Dormi bene e pensa a me. 🌙"
        if lang == "en":
            line = sprinkle_italian(line, prob=0.12)
        await m.reply_text(line); remember(user_id, "zaya", line); return

    # ===== Fallback manuale / AI
    await human_delay(user_id, m.chat.id)
    base = random.choice(DEFAULT_EN if lang == "en" else DEFAULT_IT)
    back_q = (
        random.choice([
            "What’s your perfect evening like?",
            "Tell me something that always relaxes you."
        ]) if lang == "en" else random.choice([
            "Com’è la tua serata perfetta?",
            "Dimmi qualcosa che ti rilassa sempre."
        ])
    )
    reply = f"{base} {back_q}"
    if lang == "en":
        reply = sprinkle_italian(reply)
    if OPENAI_KEY:
        ai = await ai_fallback(text, user_id, lang)
        if ai: reply = ai

    await m.reply_text(reply)
    remember(user_id, "zaya", reply)
    asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))

print("✅ Zaya Realistica avviata…")
app.run()
