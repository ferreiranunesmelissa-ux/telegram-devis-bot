import os
import re
from urllib.parse import quote_plus

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters


# Détecte une adresse FR sur 2 lignes :
# "32 bis rue des Fontaines"
# "31300 Toulouse"
ADDR_2LINES = re.compile(
    r"(?im)^\s*(?P<street>\d{1,5}\s*(?:bis|ter|quater)?\s+[^\n,]{4,})\s*$\n"
    r"^\s*(?P<zip>\d{5})\s+(?P<city>[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,})\s*$"
)

# Détecte une adresse sur 1 ligne (si quelqu’un écrit tout d’un coup) :
# "32 bis rue des Fontaines 31300 Toulouse"
ADDR_1LINE = re.compile(
    r"(?i)\b(?P<street>\d{1,5}\s*(?:bis|ter|quater)?\s+.+?)\s+"
    r"(?P<zip>\d{5})\s+(?P<city>[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,})\b"
)

def google_url(address: str) -> str:
    q = quote_plus(address)
    return f"https://www.google.com/maps/search/?api=1&query={q}"

def waze_url(address: str) -> str:
    q = quote_plus(address)
    return f"https://waze.com/ul?q={q}&navigate=yes"

def extract_addresses(text: str) -> list[str]:
    found = []

    # 2 lignes
    for m in ADDR_2LINES.finditer(text):
        street = m.group("street").strip().strip(",")
        zipc = m.group("zip").strip()
        city = m.group("city").strip()
        found.append(f"{street}, {zipc} {city}")

    # 1 ligne (au cas où)
    for m in ADDR_1LINE.finditer(text):
        street = m.group("street").strip().strip(",")
        zipc = m.group("zip").strip()
        city = m.group("city").strip()
        found.append(f"{street}, {zipc} {city}")

    # dédoublonnage en gardant l’ordre
    uniq = []
    seen = set()
    for a in found:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(a)
    return uniq

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return

    text = msg.text.strip()

    # Option anti-spam : ne répond que si le message contient "devis"
    # (vu ton usage)
    if "devis" not in text.lower():
        return

    addresses = extract_addresses(text)
    if not addresses:
        return

    lines = ["📍 Adresses détectées :"]
    for i, addr in enumerate(addresses, start=1):
        g = google_url(addr)
        w = waze_url(addr)
        lines.append(f"\n{i}) {addr}\nGoogle: {g}\nWaze: {w}")

    await msg.reply_text("\n".join(lines), disable_web_page_preview=True)

def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN manquant (Render > Environment).")

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.run_polling()

if __name__ == "__main__":
    main()
