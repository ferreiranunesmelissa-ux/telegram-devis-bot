import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ----------------- CALCULS ----------------- #

def normalize_expr(text: str) -> str:
    """
    Nettoie le texte pour en faire une expression mathématique safe.
    - remplace virgule par point
    - remplace x / X / × par *
    - remplace 'retirer' par -
    - garde seulement chiffres, + - * . et espaces
    """
    t = text.lower()
    t = t.replace("retirer", "-")
    t = t.replace(",", ".")
    t = t.replace("×", "*")
    t = t.replace("x", "*")

    allowed = set("0123456789.+-*() ")
    expr = "".join(ch for ch in t if ch in allowed)
    return expr.strip()


def has_operation(line: str) -> bool:
    """On ne calcule que s'il y a au moins un opérateur dans la ligne."""
    l = line.lower()
    if not any(op in l for op in ["x", "×", "*", "+", "retirer"]):
        return False

    # éviter les lignes du style "1 m² fixateur"
    if "m²" in l or "m2" in l:
        if not any(op in l for op in ["x", "×", "*"]):
            return False
    return True


def compute_line(line: str):
    """
    Retourne (valeur, unité) ou (None, None) si on ne calcule pas cette ligne.
    unité = 'm²' si multiplication présente, sinon 'm'.
    """
    if not any(ch.isdigit() for ch in line):
        return None, None
    if not has_operation(line):
        return None, None

    expr = normalize_expr(line)
    if not expr or not any(ch.isdigit() for ch in expr):
        return None, None

    try:
        value = eval(expr, {"__builtins__": {}}, {})
    except Exception as e:
        logger.warning(f"Erreur de calcul pour '{line}' -> '{expr}': {e}")
        return None, None

    unit = "m²" if "*" in expr else "m"
    return value, unit


def format_number(v: float) -> str:
    """Format genre 30,8 / 11,06 / 17,6"""
    s = f"{v:.2f}".replace(".", ",")
    if "," in s:
        head, tail = s.split(",")
        tail = tail.rstrip("0")
        if tail == "":
            return head
        return f"{head},{tail}"
    return s


# ----------------- PARSE DU MESSAGE ----------------- #

PIECES = {
    "salon", "cuisine", "couloir", "salle de bain", "salle-de-bain",
    "cage d'escalier", "cage d’escalier", "entrée", "entree",
    "garage", "chambre", "buanderie", "placard", "toilettes",
    "wc", "salle à manger", "salle a manger", "cellier"
}

SUPPORTS = {
    "plafond", "sol", "mur", "façade", "facade",
    "porte", "fenêtre", "fenetre", "escalier"
}


def format_devis(text: str) -> str:
    lines = [l.rstrip() for l in text.splitlines()]
    if not lines:
        return ""

    # on ignore la première ligne "devis"
    if lines[0].strip().lower().startswith("devis"):
        lines = lines[1:]

    output_lines = []

    for raw in lines:
        line = raw.strip()
        if not line:
            output_lines.append("")
            continue

        lower = line.lower()

        # ligne = nom de pièce
        if lower in PIECES:
            output_lines.append(f"▶️{line}")
            continue

        # ligne = support
        if lower in SUPPORTS:
            output_lines.append(f"▫️{line}")
            continue

        # ligne normale avec calcul
        value, unit = compute_line(line)
        if value is not None:
            out_line = f"{line} (🔸 {format_number(value)} {unit})"
            output_lines.append(out_line)
        else:
            output_lines.append(line)

    return "\n".join(output_lines)


# ----------------- TELEGRAM ----------------- #

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    BOT_TOKEN = "TON_TOKEN_ICI"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text

    # déclenchement seulement si le message commence par "devis"
    if not text.strip().lower().startswith("devis"):
        return

    formatted = format_devis(text)
    if not formatted:
        return

    await message.reply_text(f"📄 Devis – Calcul\n\n{formatted}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    logger.info("Bot devis CALCUL démarré.")
    app.run_polling()


if __name__ == "__main__":
    main()
