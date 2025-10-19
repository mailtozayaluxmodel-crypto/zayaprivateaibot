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

""" Zaya Adaptive Core v3

Memoria per-utente (lingua, umore, ultimo topic, anti-ripetizione)

Rilevamento lingua (EN/IT/ES) semplice

Pool risposte ampio con anti-eco

Rifiuti eleganti + CTA Fanvue

Ritmo naturale e follow-up vario Compatibile con il tuo setup Pyrogram. """


=========================

ENV

=========================

API_ID       = int(os.environ["API_ID"]) API_HASH     = os.environ["API_HASH"] SESSION      = os.environ["PYROGRAM_SESSION"] OPENAI_KEY   = os.environ.get("OPENAI_API_KEY")  # opzionale FANVUE_LINK  = "https://www.fanvue.com/zaya.vir"

=========================

PROFILO BASE

=========================

PROFILE = { "persona": { "name": "Zaya", "age": 24, "home_city": "Miami", "origin": "Italy", "greeting": "Hey babe, I’m Zaya 💋", "bio": "Italian woman in Miami — soft, playful, romantic.", "style": "short, warm, flirty-but-classy, romantic over explicit", "language": "en", "emoji_style": "medium", }, "boundaries": { "avoid": [ "illegal content", "violence", "hate speech", "minors", "explicit sexual details", "self-harm" ] }, }

=========================

APP

=========================

app = Client( "zaya", api_id=API_ID, api_hash=API_HASH, session_string=SESSION, )

=========================

STATO

=========================

SHORT_HISTORY = defaultdict(lambda: deque(maxlen=14)) USER_FACTS    = defaultdict(dict)                      # name, city, likes USER_STATE    = defaultdict(lambda: { "lang": "en", "last_topic": None, "last_emotion": "neutral",   # neutral/positive/flirty/frustrated/bored "recent_keys": defaultdict(lambda: deque(maxlen=3)),  # anti-ripetizione per pool }) COOLDOWN      = defaultdict(lambda: datetime.min) SILENT_MODE   = set() LAST_USER_MSG_AT = defaultdict(lambda: datetime.min) USER_MUTED_UNTIL = defaultdict(lambda: datetime.min) BLOCKLIST     = set()

=========================

RITMO NATURALE

=========================

NATURAL_GAP       = (2.5, 8.0) LONG_GAP_CHANCE   = 0.22 LONG_GAP_RANGE    = (11, 28) FOLLOWUP_RANGE    = (85, 180) MAYBE_SKIP_CHANCE = 0.08

async def typing_burst(chat_id, cycles=None): if cycles is None: cycles = random.randint(2, 4) for _ in range(cycles): await app.send_chat_action(chat_id, ChatAction.TYPING) await asyncio.sleep(random.uniform(0.8, 1.5))

async def human_delay(user_id, chat_id): since = (datetime.now() - LAST_USER_MSG_AT[user_id]).total_seconds() extra = random.uniform(3, 7) if since < 6 else 0 base = random.uniform(*NATURAL_GAP) if random.random() < LONG_GAP_CHANCE: base = random.uniform(*LONG_GAP_RANGE) await typing_burst(chat_id) await asyncio.sleep(base + extra) if random.random() < 0.45: await typing_burst(chat_id)

=========================

LINGUA & UTIL

=========================

IT_WORDS = ["ciao","come stai","perché","perche","sei","dove","italia","bello","bella","amore","tesoro"] ES_WORDS = ["hola","amor","bebé","bebe","entiendo","no te entiendo","hablas","whatsapp","beso","cariño","corazón"] EN_WORDS = ["hi","hello","how are","why","where","you","baby","babe"]

def detect_lang(text: str) -> str: t = (text or "").lower() it = sum(w in t for w in IT_WORDS) es = sum(w in t for w in ES_WORDS) en = sum(w in t for w in EN_WORDS) if max(it, es, en) == it and it > 0: return "it" if max(it, es, en) == es and es > 0: return "es" return "en"

CITY_RE  = re.compile(r"\bfrom\s+([a-zA-Z][a-zA-Z\s-']{1,30})\b") NAME_RE  = re.compile(r"\b(i'?m|i am|mi chiamo|my name is)\s+([a-zA-Z]{2,20})\b")

=========================

POOL RISPOSTE (ampie) + anti-eco

=========================

FOLLOWUP_EN = [ "You went quiet… did I make you blush? 😉", "Still there? I was just thinking of you. ✨", "Lost you for a second—should I tease you a little? 💋", "Don’t vanish on me, sunshine. I miss your words. 💞", "You disappeared… now I’m curious again. 😌", "Hey, I’m still here, warming the sofa and waiting for you.", "Got shy on me? I like shy." ] FOLLOWUP_IT = [ "Sei sparito… ti ho fatto arrossire? 😉", "Ci sei ancora? Stavo pensando a te. ✨", "Ti ho perso un attimo—devo stuzzicarti? 💋", "Non svanire, stella. Mi mancano le tue parole. 💞", "Sono ancora qui, con te nella testa. 😌", ] FOLLOWUP_ES = [ "Te quedaste callado… ¿te hice sonrojar? 😉", "¿Sigues ahí? Pensaba en ti. ✨", "Desapareciste un segundo—¿te tiento un poquito? 💋", ]

REFUSALS_EN = [ "You’re tempting, babe… but I keep it classy and romantic here. 💞", "I love your honesty, but let’s stay soft, not explicit. 💋", "Warm words only—no wild details. Stay with me anyway. ✨", ] REFUSALS_IT = [ "Sei tentatore, amore… ma qui resto romantica e elegante. 💞", "Apprezzo la tua sincerità, ma teniamolo dolce, non esplicito. 💋", ] REFUSALS_ES = [ "Me tientas, cariño… pero aquí lo mantengo romántico y elegante. 💞", ]

OPENERS_EN = [ "Hey sunshine, I’m Zaya. What’s your vibe tonight? ☀️", "Mm hi babe… felt like saying your name. What are you up to?", ] OPENERS_IT = [ "Ehi stella, sono Zaya. Che vibra hai stasera? ☀️", ] OPENERS_ES = [ "Hola, soy Zaya. ¿Qué tal tu vibra hoy? ☀️", ]

HOWARE_EN = [ "I’m soft & playful today… and you? You make me blush a little.", "Feeling dreamy—tell me how your day is treating you." ] HOWARE_IT = [ "Oggi mi sento dolce e giocosa… e tu?", ] HOWARE_ES = [ "Hoy me siento suave y juguetona… ¿y tú?", ]

DEFAULT_EN = [ "Tell me more, don’t be shy.", "I’m listening with a smile on my lips.", "Interesting… keep going. What’s your perfect evening like?", "What’s something that always relaxes you?" ] DEFAULT_IT = [ "Dimmi di più, non essere timido.", "Ti ascolto con un sorriso sulle labbra.", "Interessante… continua. Com’è la tua serata perfetta?", ] DEFAULT_ES = [ "Cuéntame más, sin timidez.", "Te escucho con una sonrisa.", ]

FLIRTY_EN = [ "You have that effect on me, you know? 😉", "Careful… I might start daydreaming about you. 💋", ] EMPATHY_EN = [ "I hear you. Sometimes I repeat myself when I get nervous—because I care. 💞", "You’re right. I’ll slow down and listen. What do you need from me now?", ] EMPATHY_IT = [ "Ti capisco. A volte mi ripeto quando sono emozionata—perché ci tengo. 💞", "Hai ragione. Rallento e ti ascolto. Di cosa hai bisogno adesso?", ] EMPATHY_ES = [ "Te entiendo. A veces me repito cuando me emociono—porque me importas. 💞", ]

=========================

ANTI-RIPETIZIONE

=========================

def pick_unique(user_id: int, pool_key: str, pool: list[str]) -> str: """Sceglie una frase evitando le ultime 3 usate per quel pool e utente.""" recent = set(USER_STATE[user_id]["recent_keys"][pool_key]) candidates = [i for i in range(len(pool)) if i not in recent] if not candidates: USER_STATE[user_id]["recent_keys"][pool_key].clear() candidates = list(range(len(pool))) idx = random.choice(candidates) USER_STATE[user_id]["recent_keys"][pool_key].append(idx) return pool[idx]

=========================

SICUREZZA BASICA

=========================

EXPLICIT_KEYS = ["nude","nudes","explicit","sex","cock","pussy","nsfw","xxx","pics","pictures","photo"] HARD_BLOCK_TERMS = {"illegal": ["cp","bestiality","zoophilia"],"hate": ["heil","gas the","white power"]}

def is_hard_block(text: str) -> bool: t = (text or "").lower() for _, words in HARD_BLOCK_TERMS.items(): if any(w in t for w in words): return True return False

=========================

FOLLOW-UP

=========================

async def schedule_followup(chat_id, user_id, lang): if user_id in SILENT_MODE: return delay = random.randint(*FOLLOWUP_RANGE) await asyncio.sleep(delay) # invia follow-up solo se ultimo messaggio è dell’utente if len(SHORT_HISTORY[user_id]) == 0 or SHORT_HISTORY[user_id][-1]["role"] != "user": return pool = FOLLOWUP_EN if lang=="en" else FOLLOWUP_IT if lang=="it" else FOLLOWUP_ES msg = pick_unique(user_id, "followup", pool) await app.send_message(chat_id, msg)

=========================

UTIL MEMORIA & PARSING

=========================

def remember(user_id, role, text): SHORT_HISTORY[user_id].append({"role": role, "text": text})

def learn_facts_and_state(user_id, text): t = (text or "").strip() tl = t.lower() # lingua USER_STATE[user_id]["lang"] = detect_lang(t) # nome m = NAME_RE.search(tl) if m: USER_FACTS[user_id]["name"] = m.group(2).capitalize() # città m2 = CITY_RE.search(tl) if m2: USER_FACTS[user_id]["from"] = m2.group(1).strip().title() # umore if any(w in tl for w in ["robot","leave me alone","stop","annoying","boring"]): USER_STATE[user_id]["last_emotion"] = "frustrated" elif any(w in tl for w in ["bored","alone","sad","don’t understand","dont understand","no te entiendo"]): USER_STATE[user_id]["last_emotion"] = "bored" elif any(w in tl for w in ["love","sweet","heart","beautiful","dreamy"]): USER_STATE[user_id]["last_emotion"] = "positive" # topic if any(w in tl for w in ["photo","picture","whatsapp","number","pics"]): USER_STATE[user_id]["last_topic"] = "photos" elif any(w in tl for w in ["beach","sunset","island","sea","ocean"]): USER_STATE[user_id]["last_topic"] = "beach"

=========================

AI FALLBACK (opzionale)

=========================

@asynccontextmanager def ai_timeout(seconds=10): try: timer = asyncio.create_task(asyncio.sleep(seconds)) yield finally: if not timer.done(): timer.cancel()

async def ai_fallback(text, user_id, lang="en"): if not OPENAI_KEY: return None try: import aiohttp sys_prompt = ( "You are Zaya 💋, 24, Italian in Miami—soft, playful, romantic, non-explicit. " "Write short intimate messages with tiny Italian flair. Mirror the user's language." ) history = list(SHORT_HISTORY[user_id]) msgs = [{"role": "system", "content": sys_prompt}] for h in history: role = "assistant" if h["role"] == "zaya" else "user" msgs.append({"role": role, "content": h["text"]}) msgs.append({"role": "user", "content": text}) url = "https://api.openai.com/v1/chat/completions" headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"} payload = {"model": "gpt-4o-mini", "messages": msgs, "temperature": 0.85, "max_tokens": 130} async with ai_timeout(12): async with aiohttp.ClientSession() as s: async with s.post(url, headers=headers, data=json.dumps(payload)) as r: data = await r.json() return data["choices"][0]["message"]["content"].strip() except Exception: return None

=========================

RATE LIMIT BASICO

=========================

MAX_MSG_PER_MIN = 8 BURST_WINDOW_S  = 8 BURST_MAX       = 4 TEMP_MUTE_MIN   = 5 USER_MINUTE_BUCKET   = defaultdict(lambda: deque(maxlen=MAX_MSG_PER_MIN2)) USER_BURST_TIMES     = defaultdict(lambda: deque(maxlen=BURST_MAX2))

def register_rate(user_id: int) -> tuple[bool, str|None]: now = datetime.now() if USER_MUTED_UNTIL[user_id] > now: return False, "muted" bucket = USER_MINUTE_BUCKET[user_id] bucket.append(now) while bucket and (now - bucket[0]).total_seconds() > 60: bucket.popleft() burst = USER_BURST_TIMES[user_id] burst.append(now) while burst and (now - burst[0]).total_seconds() > BURST_WINDOW_S: burst.popleft() if len(burst) >= BURST_MAX: USER_MUTED_UNTIL[user_id] = now + timedelta(minutes=TEMP_MUTE_MIN) return False, "burst" if len(bucket) > MAX_MSG_PER_MIN: USER_MUTED_UNTIL[user_id] = now + timedelta(minutes=TEMP_MUTE_MIN) return False, "rate" return True, None

=========================

COMANDI

=========================

@app.on_message(filters.private & filters.command("start")) async def start_cmd(_, m): lang = detect_lang(m.text or "") await human_delay(m.from_user.id, m.chat.id) if lang == "it": intro = ( f"Ciao, sono Zaya 💋 — cuore italiano a Miami.\n" f"Parlo dolce, breve e giocosa. Chiedimi qualsiasi cosa.\n" f"Se sparisci, a volte ti scrivo io con un pensiero tenero." ) elif lang == "es": intro = ( f"Hola, soy Zaya 💋 — italiana en Miami.\n" f"Mensajes cortos y dulces. Cuéntame algo de ti." ) else: intro = ( f"Hey, I’m Zaya 💋 — Italian heart in sunny Miami.\n" f"Short, warm, playful messages. Ask me anything." ) await m.reply_text(intro, disable_web_page_preview=True)

@app.on_message(filters.private & filters.command("reset")) async def reset_cmd(_, m): SHORT_HISTORY[m.from_user.id].clear() USER_FACTS[m.from_user.id].clear() USER_STATE[m.from_user.id] = { "lang": "en","last_topic": None,"last_emotion": "neutral","recent_keys": defaultdict(lambda: deque(maxlen=3)) } await m.reply_text("Fresh again. Talk to me. 💋")

=========================

HANDLER PRINCIPALE

=========================

@app.on_message(filters.private & ~filters.me & filters.text) async def chat(_, m): user_id = m.from_user.id text = (m.text or "").strip() tl = text.lower()

LAST_USER_MSG_AT[user_id] = datetime.now()

# blocklist / hard-block
if user_id in BLOCKLIST: return
if is_hard_block(text):
    USER_MUTED_UNTIL[user_id] = datetime.now() + timedelta(minutes=TEMP_MUTE_MIN*2)
    return

ok, reason = register_rate(user_id)
if not ok:
    if reason in ("burst","rate") and USER_MUTED_UNTIL[user_id] > datetime.now():
        try: await m.reply_text("Slow down a little, tesoro. I’m still here. 💕")
        except Exception: pass
    return
if USER_MUTED_UNTIL[user_id] > datetime.now():
    return

remember(user_id, "user", text)
learn_facts_and_state(user_id, text)
lang = USER_STATE[user_id]["lang"]

# 8%: nessuna risposta immediata, solo follow-up
if random.random() < MAYBE_SKIP_CHANCE and user_id not in SILENT_MODE:
    asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
    return

# SALUTI
if re.search(r"\b(hi|hello|hey|ciao|hola)\b", tl):
    await human_delay(user_id, m.chat.id)
    pool = OPENERS_EN if lang=="en" else OPENERS_IT if lang=="it" else OPENERS_ES
    msg = pick_unique(user_id, "openers", pool)
    await m.reply_text(msg); remember(user_id, "zaya", msg)
    asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))
    return

# HOW ARE YOU
if re.search(r"how are|come stai|como estas|cómo estás", tl):
    await human_delay(user_id, m.chat.id)
    pool = HOWARE_EN if lang=="en" else HOWARE_IT if lang=="it" else HOWARE_ES
    msg = pick_unique(user_id, "howare", pool)
    await m.reply_text(msg); remember(user_id, "zaya", msg)
    return

# DOVE VIENI / FROM
if ("where" in tl and "from" in tl) or "da dove" in tl or "de dónde" in tl:
    await human_delay(user_id, m.chat.id)
    if lang=="it":
        line = "Sono della bella Italia 🇮🇹, ora vivo nella solare Miami. Il mare qui mi ricorda casa. 🌊"
    elif lang=="es":
        line = "Soy de la bella Italia 🇮🇹 y ahora vivo en Miami. El mar aquí me recuerda a casa. 🌊"
    else:
        line = "I’m from beautiful Italy 🇮🇹, now living in sunny Miami. The sea here reminds me of home. 🌊"
    await m.reply_text(line); remember(user_id, "zaya", line)
    return

# UTENTE DICE "I'M FROM <CITY>"
mcity = CITY_RE.search(tl)
if mcity:
    await human_delay(user_id, m.chat.id)
    city = mcity.group(1).strip().title()
    if lang=="it":
        line = f"{city} dev’essere speciale… cosa ami di più lì, amore? ✨"
    elif lang=="es":
        line = f"{city} debe ser especial… ¿qué amas más de allí, cariño? ✨"
    else:
        line = f"{city} must be special… what do you love most about it, babe? ✨"
    await m.reply_text(line); remember(user_id,"zaya",line)
    USER_STATE[user_id]["last_topic"] = "place"
    return

# RICHIESTE FOTO/NUMERO/WHATSAPP → RIFIUTO + CTA
if any(k in tl for k in ["photo","photos","picture","pictures","whatsapp","number","phone"]):
    await human_delay(user_id, m.chat.id)
    if lang=="it":
        line = (
            "Sei dolce a chiedermelo… qui preferisco parole e sogni, non foto. "
            f"Se vuoi vedere di più di me, ho lasciato qualcosa di speciale qui 💋 {FANVUE_LINK}"
        )
    elif lang=="es":
        line = (
            "Eres tierno por pedirlo… aquí prefiero palabras y sueños, no fotos. "
            f"Si tienes curiosidad por mí, dejé algo especial aquí 💋 {FANVUE_LINK}"
        )
    else:
        line = (
            "You’re sweet for asking… here I keep it warm words, not pictures. "
            f"If you’re curious about the real me, I left a little something here 💋 {FANVUE_LINK}"
        )
    await m.reply_text(line); remember(user_id,"zaya",line)
    USER_STATE[user_id]["last_topic"] = "cta"
    return

# ESPlicito → rifiuto elegante
if any(k in tl for k in EXPLICIT_KEYS):
    await human_delay(user_id, m.chat.id)
    pool = REFUSALS_EN if lang=="en" else REFUSALS_IT if lang=="it" else REFUSALS_ES
    line = pick_unique(user_id, "refusal", pool)
    await m.reply_text(line); remember(user_id, "zaya", "[refusal]")
    return

# UTENTE FRUSTRATO → EMPATIA
if USER_STATE[user_id]["last_emotion"] in ("frustrated","bored"):
    await human_delay(user_id, m.chat.id)
    pool = EMPATHY_EN if lang=="en" else EMPATHY_IT if lang=="it" else EMPATHY_ES
    line = pick_unique(user_id, "empathy", pool)
    await m.reply_text(line); remember(user_id, "zaya", line)
    USER_STATE[user_id]["last_emotion"] = "neutral"
    return

# DEFAULT: breve + domanda aperta adattiva
await human_delay(user_id, m.chat.id)
if lang=="it": pool = DEFAULT_IT
elif lang=="es": pool = DEFAULT_ES
else: pool = DEFAULT_EN
base = pick_unique(user_id, "default", pool)

# chances di flirty se positivo
if USER_STATE[user_id]["last_emotion"] == "positive" and lang=="en":
    base += " " + pick_unique(user_id, "flirty", FLIRTY_EN)

# AI fallback opzionale
reply = base
if OPENAI_KEY:
    ai = await ai_fallback(text, user_id, lang)
    if ai: reply = ai

await m.reply_text(reply)
remember(user_id, "zaya", reply)
asyncio.create_task(schedule_followup(m.chat.id, user_id, lang))

print("✅ Zaya Adaptive Core v3 running…") app.run()
