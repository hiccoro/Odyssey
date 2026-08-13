import os
import json
import requests
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

API_URL = (
    "https://www.cinemacity.cz/cz/data-api-service/v1/"
    "quickbook/10101/cinema-events/in-group/prague/"
    "with-film/7268s2r/at-date/{date}?attr=&lang=cs_CZ"
)
DATA_FILE = "known_showings.json"
CINEMA_ID = "1052"
MOVIE_ID = "7268s2r"
TOTAL_SEATS = 385
PRAGUE = ZoneInfo("Europe/Prague")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()

def load_known():
    if not os.path.exists(DATA_FILE):
        return set()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(str(showing_id) for showing_id in data)
    except Exception:
        return set()

def save_known(showings):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            sorted(showings),
            f,
            ensure_ascii=False,
            indent=2,
        )

def get_showings_for_date(date):
    url = API_URL.format(
        date=date.strftime("%Y-%m-%d")
    )
    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )
    response.raise_for_status()
    data = response.json()
    events = data.get("body", {}).get("events", [])
    result = []
    for event in events:
        # Nur Cinema City Flora
        if event.get("cinemaId") != CINEMA_ID:
            continue
        # Nur Odyssea
        if event.get("filmId") != MOVIE_ID:
            continue
        attributes = event.get("attributeIds", [])
        # Nur 70-mm-Vorstellungen
        if "70-mm" not in attributes:
            continue
        event_id = event.get("id")
        event_datetime = event.get("eventDateTime")
        if not event_id or not event_datetime:
            continue
        result.append({
            "id": str(event_id),
            "datetime": event_datetime,
            "date": event.get("businessDay"),
            "auditorium": event.get("auditorium"),
            "auditoriumTinyName": event.get("auditoriumTinyName"),
            "soldOut": event.get("soldOut", False),
            "availabilityRatio": event.get("availabilityRatio"),
            "bookingLink": event.get("bookingLink"),
            "attributes": attributes,
        })
    return result

def save_to_git():
    import subprocess
    subprocess.run(
        [
            "git",
            "config",
            "user.name",
            "github-actions[bot]"
        ],
        check=True
    )
    subprocess.run(
        [
            "git",
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com"
        ],
        check=True
    )
    subprocess.run(
        ["git", "add", DATA_FILE],
        check=True
    )
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    )
    # Keine Änderung → nichts committen
    if result.returncode == 0:
        return
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Update known showings"
        ],
        check=True
    )
    subprocess.run(
        ["git", "push"],
        check=True
    )

def main():
    check_counter = 1
    while check_counter <= 10000:
        print(f"=== ODYSSEY MONITOR {check_counter} ===")
        now = datetime.now(PRAGUE)
        # Alle jemals bekannten Vorstellungen laden
        known = load_known()
        print(
            f"{len(known)} bereits bekannte Vorstellung(en)."
        )
        current = {}
        # Wir prüfen die nächsten 6 Wochen.
        for days_ahead in range(42):
            date = now.date() + timedelta(days=days_ahead)
            print(
                f"Prüfe {date}..."
            )
            try:
                events = get_showings_for_date(date)
            except Exception as e:
                print(
                    f"Fehler bei {date}: {e}"
                )
                continue
            for event in events:
                event_id = str(event["id"])
                current[event_id] = event
                print(
                    event["datetime"],
                    "|",
                    "available:",
                    round(TOTAL_SEATS * event["availabilityRatio"])
                )
        current_ids = set(current.keys())
        # Nur Vorstellungen melden, die noch NIE zuvor
        # in known_showings.json gespeichert wurden.
        new_ids = current_ids - known
        if not new_ids:
            print(
                "Keine neuen Vorstellungen."
            )
            # WICHTIG:
            # Bereits bekannte IDs bleiben erhalten.
            # Nur neue IDs werden hinzugefügt.
            updated_known = known | current_ids
            if updated_known != known:
                save_known(updated_known)
                save_to_git()
            else:
                print(
                    "Keine Änderung an known_showings.json."
                )
            
        print(
            f"{len(new_ids)} neue Vorstellung(en) gefunden!"
        )
        for event_id in sorted(new_ids):
            event = current[event_id]
            dt = datetime.fromisoformat(
                event["datetime"]
            )
            date_text = dt.strftime(
                "%d.%m.%Y"
            )
            time_text = dt.strftime(
                "%H:%M"
            )
            #spam_counter = 1
            #while spam_counter < 120:
            #    send_telegram("Neue Odyssey-Vorstellung!")
            #    spam_counter += 1
            #    time.sleep(1)
            message = (
                "Neue Odyssey-Vorstellung!\n\n"
                "Cinema City Praha Flora\n"
                "IMAX 70 mm\n\n"
                f"{date_text} {time_text}\n"
            )
            if event["auditorium"]:
                message += (
                    f"{event['auditorium']}\n"
                )
            if event["soldOut"]:
                message += "\nAUSVERKAUFT"
            else:
                availability_ratio = event.get(
                    "availabilityRatio"
                )
                if availability_ratio is not None:
                    free_seats = round(
                        TOTAL_SEATS * availability_ratio
                    )
                    occupied_percent = round(
                        (1 - availability_ratio) * 100
                    )
                    message += (
                        f"\n{free_seats} / {TOTAL_SEATS} Plätze frei"
                        f"\n{occupied_percent} % belegt"
                    )
                else:
                    message += (
                        "\nTickets verfügbar"
                    )
            if event["bookingLink"]:
                message += (
                    "\n\n"
                    f"{event['bookingLink']}"
                )
            send_telegram(message)
            print(
                f"Telegram-Nachricht gesendet: "
                f"{event_id}"
            )
        # Ganz wichtig:
        # Nicht current_ids speichern!
        #
        # Stattdessen:
        # bisher bekannte IDs
        # +
        # neu gefundene IDs
        #
        # Dadurch werden alte Vorstellungen niemals gelöscht.
        updated_known = known | current_ids
        save_known(updated_known)
        save_to_git()
        print(
            f"{len(updated_known)} Vorstellung(en) "
            f"insgesamt dauerhaft gespeichert."
        )
        check_counter += 1
        time.sleep(10)
if __name__ == "__main__":
    main()
