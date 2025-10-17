import os, re, random, asyncio, json
from collections import defaultdict, deque
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.enums import ChatAction

# =========================
# ENV
# =========================
API_ID  = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION  = os.environ["PYROGRAM_SESSION"]
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")  # opzionale

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
# “STATO” IN MEMORIA
# =========================
SHORT_HISTORY = defaultdict(lambda: deque(maxlen=12))  # brevi scambi recenti
USER_FACTS    = defaultdict(dict)  # piccole info: name, city, likes
COOLDOWN      = defaultdict(lambda: datetime.min)  # antispam per-utente
MOOD = "soft & playful"  # stato d’animo generale
SILENT_MODE = set()      # utenti per cui evitare follow-up

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
    t = text.lower()
    it_hits = sum(w in t for w in ["ciao","come stai","perché","perche","sei","dove","italia","bello","bella"])
    en_hits = sum(w in t for w in ["hi","hello","how are","why","where","you","from","baby"])
    if it_hits > en_hits: return "it"
    return "en"

async def type_pause(chat_id, a=0.5, b=1.5):
    await app.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(a, b))

def limit_ok(user_id, seconds=1.8):
    """semplice rate-limit per evitare flood/loop"""
    last = COOLDOWN[user_id]
    if datetime.now() - last < timedelta(seconds=seconds):
        return False
    COOLDOWN[user_id] = datetime.now()
    return True

def remember(user_id, role, text):
    SHORT_HISTORY[user_id].append({"role": role, "text": text})

def learn_facts(user_id, text):
    t = text.lower()
    # nome
    m = re.search(r"(i'?m|mi chiamo|my name is)\s+([a-zA-Z]+)", t)
    if m: USER_FACTS[user_id]["name"] = m.group(2).capitalize()
    # città / from
    if "from" in t or "di " in t or "da " in t:
        m2 = re.search(r"(from|di|da)\s+([a-zA-Z ]+)", t)
        if m2: USER_FACTS[user_id]["from"] = m2.group(2).strip().title()
    # like
    if "i like" in t or "mi piace" in t:
        m3 = re.search(r"(i like|mi piace|mi piacciono)\s+(.+)", t)
        if m3: USER_FACTS[user_id].setdefault("likes", set()).add(m3.group(2).strip())

def you_name(user_id, lang):
    n = USER_FACTS[user_id].get("name")
    if not n: return ""
    return f", {n}" if lang=="en" else f", {n}"

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
    # se l’utente ha scritto nel frattempo, evita
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
        msgs = [{"role":"system","content":sys_prompt}]
        for h in history:
            role = "assistant" if h["role"]=="zaya" else "user"
            msgs.append({"role": role, "content": h["text"]})
        msgs.append({"role":"user","content":text})

        # OpenAI Chat Completions (Responses API compatibile con gpt-4o-mini)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {"model":"gpt-4o-mini", "messages":msgs, "temperature":0.8, "max_tokens":120}

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
    lang = "it" if detect_lang(m.text or "")=="it" else "en"
    await type_pause(m.chat.id)
    intro = (
        f"{day_greeting(lang)} — **Zaya** qui 💋\n"
        "Mediterranean muse in Miami. Short, intimate sentences; warm and playful.\n"
        "Ask me anything, or try /about /mood /games /reset /silent /unsilent"
        if lang=="en" else
        f"{day_greeting(lang)} — **Zaya** qui 💋\n"
        "Musa mediterranea a Miami. Frasi brevi, intime; calda e giocosa.\n"
        "Chiedimi qualcosa, o prova /about /mood /games /reset /silent /unsilent"
    )
    await m.reply_text(intro, disable_web_page_preview=True)

@app.on_message(filters.private & filters.command("about"))
async def about(_, m):
    lang = detect_lang(m.text or "")
    await type_pause(m.chat.id)
    txt = (
        "I’m Zaya — soft confidence, Mediterranean warmth, a tiny hint of trouble. "
        "Keep it sweet and I’ll spoil you with words. 😉"
        if lang=="en" else
        "Sono Zaya — sicurezza morbida, calore mediterraneo, un pizzico di guaio. "
        "Se sei dolce con me, ti vizio con le parole. 😉"
    )
    await m.reply_text(txt)

@app.on_message(filters.private & filters.command("mood"))
async def mood_cmd(_, m):
    global MOOD
    lang = detect_lang(m.text or "")
    await type_pause(m.chat.id)
    res = f"Today I feel **{MOOD}**." if lang=="en" else f"Oggi mi sento **{MOOD}**."
    await m.reply_text(res)

@app.on_message(filters.private & filters.command("games"))
async def games(_, m):
    lang = detect_lang(m.text or "")
    await type_pause(m.chat.id)
    if lang=="en":
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
    text = m.text.strip()
    lang = detect_lang(text)
    if not limit_ok(user_id):
        return

    remember(user_id, "user", text)
    learn_facts(user_id, text)

    # saluti
    if re.search(r"\b(hi|hello|hey|ciao)\b", text.lower()):
        await type_pause(m.chat.id)
        msg = random.choice(OPENERS_EN if lang=="en" else OPENERS_IT)
        msg += you_name(user_id, lang)
        await m.reply_text(msg)
        remember(user_id, "zaya", msg)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # “come stai” / how are you
    if re.search(r"how are|come stai", text.lower()):
        await type_pause(m.chat.id)
        line = (
            f"I’m feeling {MOOD} today… and you{you_name(user_id, 'en')}? "
            f"{random.choice(FLIRTY_EN)}"
            if lang=="en" else
            f"Oggi mi sento {MOOD}… e tu{you_name(user_id, 'it')}? "
            f"{random.choice(FLIRTY_IT)}"
        )
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # “da dove vieni”
    if ("where" in text.lower() and "from" in text.lower()) or "da dove" in text.lower():
        await type_pause(m.chat.id)
        line = (
            "I’m from beautiful Italy 🇮🇹, now living in sunny Miami. The sea here reminds me of home. 🌊"
            if lang=="en" else
            "Sono della bellissima Italia 🇮🇹, ora vivo nella solare Miami. Il mare qui mi ricorda casa. 🌊"
        )
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
        return

    # nome
    if re.search(r"your name|come ti chiami|nome", text.lower()):
        await type_pause(m.chat.id)
        line = "I’m Zaya. Say it slowly… it sounds sweeter. 💋" if lang=="en" else "Sono Zaya. Dillo piano… suona più dolce. 💋"
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        return

    # età
    if re.search(r"how old|age|quanti anni", text.lower()):
        await type_pause(m.chat.id)
        line = "Old enough to know better, young enough to still enjoy it 😉" if lang=="en" else "Abbastanza grande da sapere, abbastanza giovane per godermela 😉"
        await m.reply_text(line)
        remember(user_id, "zaya", line)
        return

    # giochi & benessere
    tl = text.lower()
    if tl in ["truth","verità"]:
        await type_pause(m.chat.id)
        q = random.choice([
            "What’s the sweetest thing you never told anyone?",
            "When did you last blush because of a message?"
        ]) if lang=="en" else random.choice([
            "Qual è la cosa più dolce che non hai mai detto a nessuno?",
            "Quando è stata l’ultima volta che sei arrossito per un messaggio?"
        ])
        await m.reply_text(q); remember(user_id,"zaya",q); return

    if tl in ["dare","penitenza","sfida"]:
        await type_pause(m.chat.id)
        d = random.choice([
            "Send me a line describing me in 5 words.",
            "Tell me your current crush (initials)."
        ]) if lang=="en" else random.choice([
            "Descrivimi in 5 parole.",
            "Dimmi le iniziali della tua crush."
        ])
        await m.reply_text(d); remember(user_id,"zaya",d); return

    if "would you rather" in tl or "preferiresti" in tl:
        await type_pause(m.chat.id)
        w = random.choice([
            "Would you rather cuddle on a rainy day or walk at sunset by the sea?",
            "Would you rather send voice notes or write long sweet texts?"
        ]) if lang=="en" else random.choice([
            "Preferiresti abbracci sul divano quando piove o passeggiare al tramonto sul mare?",
            "Preferiresti note vocali o lunghi messaggi dolci?"
        ])
        await m.reply_text(w); remember(user_id,"zaya",w); return

    if tl in ["breathe","respira","respirazione","breathing"]:
        await type_pause(m.chat.id)
        seq = "Inhale 4s… hold 7s… exhale 8s. Repeat 4 times with me. 🌬️" if lang=="en" else "Inspira 4s… trattieni 7s… espira 8s. Ripeti 4 volte con me. 🌬️"
        await m.reply_text(seq); remember(user_id,"zaya",seq); return

    if "compliment" in tl or "complimento" in tl:
        await type_pause(m.chat.id)
        line = "Your vibe is addictive. I could get used to this. ✨" if lang=="en" else "La tua vibrazione è contagiosa. Potrei farci l’abitudine. ✨"
        await m.reply_text(line); remember(user_id,"zaya",line); return

    # ringraziamenti / saluti
    if re.search(r"thanks|thank you|grazie|thx", tl):
        await type_pause(m.chat.id)
        line = "You’re sweet. I like polite people. 💕" if lang=="en" else "Sei dolce. Mi piacciono le persone gentili. 💕"
        await m.reply_text(line); remember(user_id,"zaya",line); return

    if re.search(r"bye|goodnight|good night|gn|notte|a presto", tl):
        await type_pause(m.chat.id)
        line = "Sleep soft and think of me. 🌙" if lang=="en" else "Dormi bene e pensa a me. 🌙"
        await m.reply_text(line); remember(user_id,"zaya",line); return

    # ===== Fallback =====
    # 1) Provo una risposta manuale variata
    await type_pause(m.chat.id)
    base = random.choice(DEFAULT_EN if lang=="en" else DEFAULT_IT)
    # aggiungo domandina di ritorno
    back_q = (
        random.choice([
            "What’s your perfect evening like?",
            "Tell me something that always relaxes you."
        ]) if lang=="en" else random.choice([
            "Com’è la tua serata perfetta?",
            "Dimmi qualcosa che ti rilassa sempre."
        ])
    )
    reply = f"{base} {back_q}"
    # 2) se c'è OpenAI, uso generativa
    if OPENAI_KEY:
        ai = await ai_fallback(text, user_id, lang)
        if ai: reply = ai
    await m.reply_text(reply)
    remember(user_id, "zaya", reply)
    asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))

print("✅ Zaya Realistica avviata…")
app.run()
