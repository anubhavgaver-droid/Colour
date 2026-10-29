import asyncio
import html
import os

import httpx
from aiohttp import web
from pyrogram import Client, filters, idle

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 10000))
SELF_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Render sets this automatically

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
PER_PAGE = 5
BOT_USERNAME = ""

app = Client(
    "rich_button_test",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

# ---------- Sample data (replace with your DB results later) ----------
FILES = [
    ("3.25 GB", "Dhurandhar 2025 1080p 10Bit HEVC Hindi WEB DL mkv"),
    ("2.05 GB", "Dhurandhar 2025 1080p HEVC Hindi WEB DL mkv"),
    ("1.87 GB", "Dhurandhar 2025 720p Hindi WEB DL 5.1 ES mkv"),
    ("1.45 GB", "Dhurandhar 2025 720p 10Bit HEVC Hindi WEB DL mkv"),
    ("1.20 GB", "Dhurandhar 2025 720p HEVC Hindi WEB DL ESub mkv"),
    ("705 MB", "Dhurandhar 2025 480p Hindi WEB DL ESub mkv"),
    ("690 MB", "Dhurandhar 2025 480p HEVC Hindi WEB DL mkv"),
    ("1.10 GB", "Dhurandhar 2025 720p Hindi WEB DL mkv"),
    ("2.40 GB", "Dhurandhar 2025 1080p Hindi WEB DL ESub mkv"),
    ("900 MB", "Dhurandhar 2025 576p Hindi WEB DL mkv"),
    ("1.60 GB", "Dhurandhar 2025 720p 10Bit Hindi WEB DL mkv"),
    ("3.10 GB", "Dhurandhar 2025 1080p 10Bit Hindi WEB DL ESub mkv"),
]


# ---------- Rich message builders ----------
def btn(text_html: str, data: str, style: str = "primary") -> str:
    return (
        f'<tg-button type="callback_data" style="{style}" '
        f'data="{html.escape(data, quote=True)}">{text_html}</tg-button>'
    )


def row(*buttons: str) -> str:
    return "<tg-button-row>" + "".join(buttons) + "</tg-button-row>"


def build_page(page: int) -> str:
    pages = (len(FILES) + PER_PAGE - 1) // PER_PAGE
    page = max(0, min(page, pages - 1))
    chunk = FILES[page * PER_PAGE:(page + 1) * PER_PAGE]

    parts = ["<p><b>Search results: Dhurandhar</b></p>"]
    for i, (size, name) in enumerate(chunk, start=page * PER_PAGE):
        link = f"https://t.me/{BOT_USERNAME}?start=file_{i}"
        parts.append(
            f'<p>📁 <a href="{html.escape(link, quote=True)}">'
            f"[{html.escape(size)}] {html.escape(name)}</a></p>"
        )

    nav = []
    if page > 0:
        nav.append(btn("⬅ Prev", f"pg:{page - 1}"))
    nav.append(btn(f"Page {page + 1}/{pages}", "noop"))
    if page < pages - 1:
        nav.append(btn("Next ➢", f"pg:{page + 1}"))

    parts.append(row(btn("📦 Send All", f"sendall:{page}", "success")))
    parts.append(row(
        btn("🎬 Quality", "quality"),
        btn("🌐 Language", "language"),
        btn("📅 Year", "year"),
    ))
    parts.append(row(*nav))
    parts.append(row(btn("🗑 Close", "close", "danger")))
    return "".join(parts)


# ---------- Raw Bot API helpers ----------
async def api_call(method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{API}/{method}", json=payload)
        return r.json()


async def send_rich(chat_id: int, rich_html: str) -> dict:
    return await api_call("sendRichMessage", {
        "chat_id": chat_id,
        "rich_message": {"html": rich_html},
    })


async def edit_rich(chat_id: int, message_id: int, rich_html: str) -> dict:
    return await api_call("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "rich_message": {"html": rich_html},
    })


# ---------- Handlers ----------
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    # Deep links like /start file_3 land here too
    if len(message.command) > 1:
        await message.reply_text(f"Deep link received: <code>{html.escape(message.command[1])}</code>")
        return
    result = await send_rich(message.chat.id, build_page(0))
    if not result.get("ok"):
        await message.reply_text(
            "sendRichMessage failed:\n"
            f"<code>{html.escape(str(result))}</code>"
        )


@app.on_message(filters.command("emoji") & filters.private)
async def emoji_cmd(client, message):
    """/emoji <custom_emoji_id> : test a custom emoji icon inside a button."""
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/emoji CUSTOM_EMOJI_ID</code>")
        return
    eid = html.escape(message.command[1], quote=True)
    rich = "<p>Custom emoji button test</p>" + row(
        btn(f'<tg-emoji emoji-id="{eid}">📦</tg-emoji> Send All', "sendall", "success")
    )
    result = await send_rich(message.chat.id, rich)
    if not result.get("ok"):
        await message.reply_text(f"<code>{html.escape(str(result))}</code>")


@app.on_callback_query()
async def on_click(client, query):
    data = query.data or ""
    chat_id = query.message.chat.id
    msg_id = query.message.id

    if data == "close":
        await query.message.delete()
        return
    if data.startswith("pg:"):
        page = int(data.split(":")[1])
        result = await edit_rich(chat_id, msg_id, build_page(page))
        if not result.get("ok"):
            await query.answer(str(result.get("description", "Edit failed"))[:180], show_alert=True)
        else:
            await query.answer()
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
    global BOT_USERNAME
    await start_web()
    await app.start()
    BOT_USERNAME = (await app.get_me()).username
    asyncio.create_task(self_ping())
    print(f"Bot started as @{BOT_USERNAME}")
    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
