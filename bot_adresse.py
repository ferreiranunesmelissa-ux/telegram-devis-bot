print("BOT ADRESSE DEMARRE")
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8465880472:AAE7oQi4QwfgddUPj8ux1anMVYVQrdk8q54"

async def detect_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Détection simple : numéro + rue + ville
    if re.search(r"\d+ .*", text):
        adresse = text.replace("\n", " ")
        google = f"https://www.google.com/maps/search/?api=1&query={adresse}"
        waze = f"https://waze.com/ul?q={adresse}"

        await update.message.reply_text(
            f"📍 Adresse détectée\n\n"
            f"Google Maps 👉 {google}\n"
            f"Waze 👉 {waze}"
        )

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, detect_address))
app.run_polling()
print("BOT ADRESSE EN COURS")
