import os
import json
import requests
from playwright.sync_api import sync_playwright

URL = "https://www.cinemacity.cz/films/odyssea/7268s2r#/buy-tickets-by-film?in-cinema=prague&for-movie=7268s2r&view-mode=list"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

DATA_FILE = "known_showings.json"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=20,
    )


def load_known():
    if not os.path.exists(DATA_FILE):
        return set()

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_known(showings):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(showings), f, ensure_ascii=False, indent=2)


def get_showings():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            locale="cs-CZ",
            timezone_id="Europe/Prague",
        )

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        page.wait_for_timeout(8000)

        # Wir speichern zunächst den gesamten sichtbaren Inhalt.
        # Damit können wir erkennen, wie Cinema City die Vorstellungen ausgibt.
        text = page.locator("body").inner_text()

        browser.close()

        return text


def main():
    old = load_known()

    text = get_showings()

    # Vorläufig speichern wir den kompletten relevanten Seiteninhalt.
    # Im nächsten Schritt passen wir den Parser exakt an Cinema City an.
    current = {text}

    new = current - old

    if new:
        send_telegram(
            "🎬 Cinema City Flora – Odyssea\n\n"
            "Die Seite wurde aktualisiert.\n"
            "Es könnte eine neue Vorstellung geben.\n\n"
            "Ich prüfe jetzt die konkreten Termine."
        )

    save_known(current)


if __name__ == "__main__":
    main()
