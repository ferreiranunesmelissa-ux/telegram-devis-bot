import os
import logging
import re
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
        # mais s'il y a vraiment un X, on garde (genre "5 x 4 m²")
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
        # sécurité : pas de builtins, juste eval des nombres
        value = eval(expr, {"__builtins__": {}}, {})
    except Exception as e:
        logger.warning(f"Erreur de calcul pour '{line}' -> '{expr}': {e}")
        return None, None

    # unité : s'il y a une multiplication, on considère m², sinon m linéaire
    unit = "m²" if "*" in expr else "m"
    return value, unit


def format_number(v: float) -> str:
    """Format genre 30,8 / 11,06 / 17,6 (virgule et suppression des zéros inutiles)."""
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
    "wc", "salle à manger", "salle a manger"
}

SUPPORTS = {"plafond", "sol", "mur", "façade", "facade", "porte", "fenêtre", "fenetre", "escalier"}


def format_devis(text: str) -> str:
    lines = [l.rstrip() for l in text.splitlines()]
    if not lines:
        return ""

    # on ignore la première ligne "devis"
    if lines[0].strip().lower().startswith("devis"):
        lines = lines[1:]

    output_lines = []
    current_support_total = 0.0
    current_support_name = None
    current_support_unit = None

    def flush_support_total():
        nonlocal current_support_total, current_support_name, current_support_unit
        if current_support_name and current_support_total > 0 and current_support_unit:
            out = f"TOTAL {current_support_name} : {format_number(current_support_total)} {current_support_unit}"
            output_lines.append(out)
        current_support_total = 0.0
        current_support_name = None
        current_support_unit = None

    for raw in lines:
        line = raw.strip()
        if not line:
            output_lines.append("")
            continue

        lower = line.lower()

        # ligne = nom de pièce
        if lower in PIECES:
            flush_support_total()
            output_lines.append(f"▶️{line}")
            continue

        # ligne = support (plafond / mur / sol...)
        if lower in SUPPORTS:
            flush_support_total()
            current_support_name = line
            current_support_unit = None
            output_lines.append(f"▫️{line}")
            continue

        # lignes normales avec puce
        value, unit = compute_line(line)
        if value is not None:
            # on mémorise l'unité pour TOTAL
            if current_support_unit is None:
                current_support_unit = unit
            # si on mélange m et m² dans le même support, on sépare
            elif current_support_unit != unit:
                flush_support_total()
                current_support_name = None
                current_support_unit = unit
            current_support_total += value
            out_line = f"{line} (🔸 {format_number(value)} {unit})"
            output_lines.append(out_line)
        else:
            output_lines.append(line)

    flush_support_total()
    return "\n".join(output_lines)


# ----------------- TELEGRAM ----------------- #

BOT_TOKEN = os.getenv("BOT_TOKEN")  # sur Render
if not BOT_TOKEN:
    # si tu veux tester en local sans Render, colle ton token ici :
    BOT_TOKEN = "TON_TOKEN_ICI"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text

    # on déclenche seulement si le message commence par "devis"
    if not text.strip().lower().startswith("devis"):
        return

    formatted = format_devis(text)
    if not formatted:
        return

    # petite en-tête propre
    await message.reply_text(f"📄 Devis – Calcul\n\n{formatted}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    logger.info("Bot devis CALCUL démarré.")
    app.run_polling()


if __name__ == "__main__":
    main()

