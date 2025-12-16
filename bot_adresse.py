import os
import re
from urllib.parse import quote_plus

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters


def build_links(address: str) -> tuple[str, str]:
    q = quote_plus(address)
    google = f"https://www.google.com/maps/search/?api=1&query={q}"
    waze = f"https://waze.com/ul?q={q}&navigate=yes"
    return google, waze


def clean_text(text: str) -> str:
    text = (text or "").strip()

    text = re.sub(r"^@\w+\s+", "", text).strip()


    return text


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = clean_text(msg.text)

    if text.startswith("/"):
        return

    if len(text) < 5:
        return
    
    me = context.bot.username or ""
    mentioned = f"@{me}".lower() in msg.text.lower() if me else False

    
    google, waze = build_links(text)
    await msg.reply_text(f"Google: {google}\nWaze: {waze}")


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN manquant. Ajoute-le dans Render > Environment.")

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
