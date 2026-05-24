"""
Run this ONCE from SC/ folder:
    python Scraper/debug_response.py

It will print the raw body of 3 URLs so we can see
what Screener actually returns (it's not a PDF).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scraper.ii_screener_scraper import ScreenerScraper

TEST_URLS = [
    # Quarterly
    "https://www.screener.in/company/source/quarter/2726/12/2024/",
    # Another quarterly
    "https://www.screener.in/company/source/quarter/2726/9/2024/",
    # One more just to confirm
    "https://www.screener.in/company/source/quarter/2726/6/2024/",
]

with ScreenerScraper() as scraper:
    scraper.login()

    for url in TEST_URLS:
        print(f"\n{'=' * 60}")
        print(f"URL: {url}")
        print(f"{'=' * 60}")

        response = scraper.page.goto(url, wait_until="networkidle", timeout=15000)

        if response:
            print(f"Status      : {response.status}")
            print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")

            body_bytes = response.body()
            print(f"Body size   : {len(body_bytes)} bytes")
            print(f"--- RAW BODY (text) ---")
            print(body_bytes.decode("utf-8", errors="replace"))
            print(f"--- END ---")

            # Also check if the page has any links or redirects after load
            print(f"\n--- PAGE URL AFTER LOAD ---")
            print(scraper.page.url())

            # Check for any <a> tags or iframe src on the page
            links = scraper.page.eval_js(
                "() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
            )
            print(f"\n--- ALL LINKS ON PAGE ---")
            for link in links:
                print(f"  {link}")

            iframes = scraper.page.eval_js(
                "() => Array.from(document.querySelectorAll('iframe')).map(i => i.src)"
            )
            if iframes:
                print(f"\n--- IFRAMES ---")
                for src in iframes:
                    print(f"  {src}")
        else:
            print("No response!")