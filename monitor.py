import os
from playwright.sync_api import sync_playwright

URL = "https://www.cinemacity.cz/films/odyssea/7268s2r#/buy-tickets-by-film?in-cinema=prague&at=2026-08-10&for-movie=7268s2r&view-mode=list"


def main():
    print("=== STARTE DIAGNOSE ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            locale="cs-CZ",
            timezone_id="Europe/Prague",
        )

        print("Öffne Cinema City...")

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print("Seite geladen.")

        # Warten, damit JavaScript die Vorstellungen laden kann
        page.wait_for_timeout(10000)

        print("JavaScript geladen.")

        print("\n=== SEITENTITEL ===")
        print(page.title())

        print("\n=== URL NACH DEM LADEN ===")
        print(page.url)

        print("\n=== SICHTBARER SEITENTEXT ===")

        text = page.locator("body").inner_text()

        print(text[:30000])

        print("\n=== ENDE ===")

        browser.close()


if __name__ == "__main__":
    main()
