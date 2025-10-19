from pyrogram import Client

API_ID = int(input("Enter your API_ID: "))
API_HASH = input("Enter your API_HASH: ")

with Client(name="session", api_id=API_ID, api_hash=API_HASH) as app:
    print("\n✅ Your SESSION_STRING:\n")
    print(app.export_session_string())
