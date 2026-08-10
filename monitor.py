import os
import json
import re
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

CINEMA_URL = "https://www.cinemacity.cz/cinemas/Flora"
FILM_NAME = "Odyssea"

DATA_FILE = "known_showings.json"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=30,
    )

    response.raise_for_status()


def load_known():
    if not os.path.exists(DATA_FILE):
        return set()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_known(showings):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(showings), f, ensure_ascii=False, indent=2)


def get_page_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            locale="cs-CZ",
            timezone_id="Europe/Prague",
        )

        page.goto(
            CINEMA_URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        # Cinema City lädt Teile des Programms per JavaScript.
        page.wait_for_timeout(8000)

        text = page.locator("body").inner_text()

        browser.close()

        return text


def extract_odyssea_section(text):
    """
    Sucht den Abschnitt von 'Odyssea' bis zum nächsten Film.
    """

    start = text.find("Odyssea")

    if start == -1:
        return None

    remaining = text[start + len("Odyssea"):]

    # Die nächsten bekannten Film-/Programmbereiche sind schwer
    # vorherzusagen. Deshalb nehmen wir einen ausreichend großen
    # Abschnitt und filtern anschließend die relevanten Angaben.
    return remaining[:5000]


def extract_showings(section):
    """
    Extrahiert Uhrzeiten aus dem Odyssea-Abschnitt.

    Wir speichern zunächst die Kombination aus Datum + Uhrzeit +
    dem Format-/Sprachkontext der Seite.
    """

    times = re.findall(r"\b([01]?\d|2[0-3]):[0-5]\d\b", section)

    return sorted(set(times))


def main():

    print("Starte Cinema-City-Prüfung...")

    old = load_known()

    text = get_page_text()

    section = extract_odyssea_section(text)

    if section is None:
        print("Odyssea wurde auf der Flora-Seite nicht gefunden.")

        # Keine Nachricht schicken, damit ein vorübergehender
        # Fehler nicht als 'Film verschwunden' interpretiert wird.
        return

    times = extract_showings(section)

    print("Gefundene Uhrzeiten:", times)

    if not times:
        print("Keine Vorstellungen gefunden.")
        return

    today = datetime.now().strftime("%Y-%m-%d")

    current = {
        f"{today} {time}"
        for time in times
    }

    new_showings = current - old

    # Beim allerersten Lauf keine Alarmflut erzeugen.
    if not old:
        print("Erster Lauf – aktuelle Vorstellungen werden gespeichert.")
        save_known(current)
        return

    if new_showings:

        message = "🎬 NEUE ODYSSEA-VORSTELLUNG!\n\n"
        message += "📍 Cinema City Praha Flora\n"
        message += "🎞️ Odyssea\n\n"

        for showing in sorted(new_showings):
            message += f"🕐 {showing}\n"

        message += (
            "\n🎟️ Tickets:\n"
            "https://www.cinemacity.cz/films/odyssea/7268s2r"
        )

        send_telegram(message)

        print("Neue Vorstellung gemeldet!")

    else:
        print("Keine neuen Vorstellungen.")

    save_known(current)


if __name__ == "__main__":
    main()
