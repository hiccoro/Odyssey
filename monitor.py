from playwright.sync_api import sync_playwright

URL = "https://www.cinemacity.cz/films/odyssea/7268s2r#/buy-tickets-by-film?in-cinema=prague&at=2026-08-10&for-movie=7268s2r&view-mode=list"


def main():

    print("=== NETZWERK-DIAGNOSE ===")

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            locale="cs-CZ",
            timezone_id="Europe/Prague",
        )

        def response_handler(response):

            url = response.url

            interesting = any(
                word in url.lower()
                for word in [
                    "show",
                    "session",
                    "schedule",
                    "screening",
                    "booking",
                    "ticket",
                    "film",
                    "movie",
                    "cinema",
                    "performance",
                    "api"
                ]
            )

            if interesting:
                print("\n--- INTERESSANTE ANFRAGE ---")
                print("URL:", url)
                print("Status:", response.status)
                print("Typ:", response.request.resource_type)

                content_type = response.headers.get(
                    "content-type",
                    ""
                )

                print("Content-Type:", content_type)

                if "json" in content_type.lower():
                    try:
                        body = response.text()
                        print("JSON/ANTWORT:")
                        print(body[:10000])
                    except Exception as e:
                        print("Konnte Antwort nicht lesen:", e)

        page.on("response", response_handler)

        print("Öffne Cinema City...")

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("Seite geladen.")

        # Genug Zeit für alle API-Anfragen
        page.wait_for_timeout(15000)

        print("\n=== NETZWERK-DIAGNOSE BEENDET ===")

        browser.close()


if __name__ == "__main__":
    main()
