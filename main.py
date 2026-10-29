import asyncio
import os

import httpx
from aiohttp import web
from pyrogram import Client, filters, idle

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 10000))
SELF_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Render sets this automatically

app = Client(
    "button_test",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)


# ---------- Raw Bot API sender (works even if Kurigram lacks `style`) ----------
async def send_raw(chat_id: int, text: str, keyboard: list):
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": keyboard},
            },
        )
        return r.json()


def main_keyboard():
    return [
        [{"text": "📦 Send All", "callback_data": "sendall", "style": "success"}],
        [
            {"text": "🎬 Quality", "callback_data": "quality", "style": "primary"},
            {"text": "🌐 Language", "callback_data": "language", "style": "primary"},
            {"text": "📅 Year", "callback_data": "year", "style": "primary"},
        ],
        [
            {"text": "Page 1", "callback_data": "page1", "style": "primary"},
            {"text": "Next ➢", "callback_data": "next", "style": "primary"},
        ],
        [{"text": "🗑 Close", "callback_data": "close", "style": "danger"}],
    ]


# ---------- Handlers ----------
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    text = (
        "<b>Colored button test</b>\n\n"
        "Green = <code>success</code>\n"
        "Blue = <code>primary</code>\n"
        "Red = <code>danger</code>\n\n"
        "<blockquote>Colors show only on Telegram versions released "
        "after Feb 9, 2026.</blockquote>"
    )
    result = await send_raw(message.chat.id, text, main_keyboard())
    if not result.get("ok"):
        await message.reply_text(f"Bot API error:\n<code>{result}</code>")


@app.on_message(filters.command("icon") & filters.private)
async def icon_cmd(client, message):
    """Usage: /icon <custom_emoji_id>  - tests icon_custom_emoji_id on a button."""
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/icon CUSTOM_EMOJI_ID</code>")
        return
    emoji_id = message.command[1]
    keyboard = [[{
        "text": "Icon test",
        "callback_data": "icon",
        "style": "success",
        "icon_custom_emoji_id": emoji_id,
    }]]
    result = await send_raw(message.chat.id, "Icon button test", keyboard)
    if not result.get("ok"):
        await message.reply_text(f"Bot API error:\n<code>{result}</code>")


@app.on_callback_query()
async def on_click(client, query):
    data = query.data
    if data == "close":
        await query.message.delete()
        return
    await query.answer(f"You clicked: {data}")


# ---------- Web server for Render ----------
async def health(request):
    return web.Response(text="Bot is running")


async def start_web():
    web_app = web.Application()
    web_app.router.add_get("/", health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()


async def self_ping():
    if not SELF_URL:
        return
    while True:
        await asyncio.sleep(300)  # every 5 minutes
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                await client.get(SELF_URL)
        except Exception:
            pass


async def main():
    await start_web()
    await app.start()
    asyncio.create_task(self_ping())
    print("Bot started")
    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
