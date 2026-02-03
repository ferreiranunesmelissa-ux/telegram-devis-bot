from telegram.ext import MessageHandler, filters
import re
from urllib.parse import quote_plus


def handle_message(update, context):
    message = update.message

    # Ignore les réponses au bot
    if message.reply_to_message:
        return

    text = message.text

    # Ignore les messages trop courts (emoji, ok, lol...)
    if len(text) < 10:
        return

    # Détection simple d'adresse (numéro + rue)
    pattern = r"\d+\s+(rue|avenue|av|bd|boulevard|chemin|route|impasse|allée)"
    if not re.search(pattern, text.lower()):
        return

    address = quote_plus(text)

    maps_link = f"https://www.google.com/maps/search/?api=1&query={address}"
    waze_link = f"https://waze.com/ul?q={address}"

    reply = (
        f"📍 Waze :\n{waze_link}\n\n"
        f"📍 Google Maps :\n{maps_link}"
    )

    message.reply_text(reply)
