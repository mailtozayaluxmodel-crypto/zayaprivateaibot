import os
from pyrogram import Client, filters

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["PYROGRAM_SESSION"]

app = Client(
    "zaya",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
)

@app.on_message(filters.private & ~filters.me)
async def auto_reply(client, message):
    await message.reply_text("Ciao… sono qui 💋")

print("✅ Avvio Pyrogram…")
app.run()

