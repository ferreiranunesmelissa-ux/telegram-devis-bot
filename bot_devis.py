import re
import time
import logging
import requests

# Ton token de bot Telegram
TOKEN = "8287141115:AAGDr8xhnc7VkRNxrHp_g0FmNPc0bN7b--A"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

logging.basicConfig(level=logging.INFO)


# ---------- FORMATAGE NOMBRES ----------

def format_nombre(val: float) -> str:
    v = round(val, 2)
    s = f"{v:.2f}"
    s = s.replace(".", ",")
    if s.endswith("0"):
        s = s[:-1]
    return s


# ---------- CALCULS ----------

def extrait_parties_retirer(texte: str):
    parts = re.split(r"(?i)\bretirer\b", texte, maxsplit=1)
    avant = parts[0]
    apres = parts[1] if len(parts) > 1 else ""
    return avant, apres


def str_vers_float(num_str: str) -> float:
    return float(num_str.replace(",", ".").strip())


def calc_surface_segment(segment: str) -> float | None:
    if not re.search(r"[xX×]", segment):
        return None

    last_x_pos = max(segment.rfind("x"), segment.rfind("X"), segment.rfind("×"))
    if last_x_pos == -1:
        return None

    after = segment[last_x_pos + 1:]
    match_height = re.search(r"(\d+(?:,\d+)?)", after)
    if not match_height:
        return None
    hauteur = str_vers_float(match_height.group(1))

    before = segment[:last_x_pos]
    nums_before = re.findall(r"(\d+(?:,\d+)?)", before)
    if not nums_before:
        return None

    largeur_totale = sum(str_vers_float(n) for n in nums_before)
    return largeur_totale * hauteur


def calc_surface_ligne(ligne: str) -> float | None:
    avant, apres = extrait_parties_retirer(ligne)
    s1 = calc_surface_segment(avant)
    if s1 is None:
        return None

    s2 = 0.0
    if re.search(r"[xX×]", apres):
        seg2 = calc_surface_segment(apres)
        if seg2 is not None:
            s2 = seg2

    return s1 - s2


def calc_longueur_ligne(ligne: str) -> float | None:
    avant, apres = extrait_parties_retirer(ligne)

    nums_avant = re.findall(r"(\d+(?:,\d+)?)", avant)
    if not nums_avant:
        return None
    long1 = sum(str_vers_float(n) for n in nums_avant)

    long2 = 0.0
    nums_apres = re.findall(r"(\d+(?:,\d+)?)", apres)
    if nums_apres:
        long2 = sum(str_vers_float(n) for n in nums_apres)

    return long1 - long2


# ---------- LOGIQUE DE FORMATAGE DU DEVIS ----------

PIECES = {
    "salon",
    "cuisine",
    "couloir",
    "salle de bain",
    "salle de bains",
    "cage d'escalier",
    "cage d’éscalier",
    "cage d’escalier",
    "entree",
    "entrée",
    "garage",
    "chambre",
    "buanderie",
    "placard",
    "toilettes",
    "wc",
    "salle à manger",
    "salle a manger",
}

SUPPORTS = {
    "plafond",
    "sol",
    "mur",
    "façade",
    "facade",
    "porte",
    "fenêtre",
    "fenetre",
    "escalier",
}


def ajoute_repere_piece_ou_support(ligne: str) -> str:
    s = ligne.strip()
    s_lc = s.lower()

    if s_lc in PIECES:
        return f"▶️{s}"

    for sup in SUPPORTS:
        if s_lc == sup or s_lc.startswith(sup + " "):
            return "▫️" + s

    return ligne


def doit_ignorer_calc(ligne: str) -> bool:
    lcl = ligne.lower()
    if "m²" in lcl or "m2" in lcl:
        return True
    if re.search(r"\d+\s*[Hh]\b", ligne):
        return True
    return False


def ajoute_calcul_sur_ligne(ligne: str) -> str:
    base = ajoute_repere_piece_ou_support(ligne)
    if doit_ignorer_calc(ligne):
        return base

    if not re.search(r"\d", ligne):
        return base

    if re.search(r"[xX×]", ligne):
        surface = calc_surface_ligne(ligne)
        if surface is None:
            return base
        valeur = format_nombre(surface)
        return f"{base} (🔸 {valeur} m²)"

    longueur = calc_longueur_ligne(ligne)
    if longueur is None:
        return base
    valeur = format_nombre(longueur)
    return f"{base} (🔸 {valeur} m)"


def formate_devis_texte(texte: str) -> str:
    lignes = texte.splitlines()

    lignes_a_traiter: list[str] = []
    if lignes:
        first = lignes[0].strip()
        if first.lower().startswith("devis"):
            reste = first[5:].strip()
            if reste:
                lignes_a_traiter.append(reste)
            lignes_a_traiter.extend(lignes[1:])
        else:
            lignes_a_traiter = lignes
    else:
        return texte

    resultat = []
    for l in lignes_a_traiter:
        if l.strip() == "":
            resultat.append("")
        else:
            resultat.append(ajoute_calcul_sur_ligne(l))

    return "\n".join(resultat).strip()


# ---------- TELEGRAM ----------

def send_message(chat_id: int, text: str):
    try:
        requests.post(
            BASE_URL + "sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        logging.error(f"Erreur en envoyant le message: {e}")


def handle_message(message: dict):
    text = message.get("text")
    if not text:
        return

    if not text.lower().startswith("devis"):
        return

    devis_formate = formate_devis_texte(text)
    chat_id = message["chat"]["id"]
    send_message(chat_id, devis_formate)


def main():
    last_update_id = None

    logging.info("Bot devis CALCUL démarré (mode simple sans async).")

    while True:
        try:
            params = {"timeout": 30}
            if last_update_id is not None:
                params["offset"] = last_update_id + 1

            resp = requests.get(BASE_URL + "getUpdates", params=params, timeout=40)
            data = resp.json()

            for update in data.get("result", []):
                last_update_id = update["update_id"]
                message = update.get("message") or update.get("edited_message")
                if message:
                    handle_message(message)

        except Exception as e:
            logging.error(f"Erreur dans la boucle principale: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()

