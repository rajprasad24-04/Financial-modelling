from playwright.sync_api import sync_playwright
import time


class ScreenerScraper:
    def __init__(self, user_data="./playwright_data"):
        self.user_data = user_data

    def __enter__(self):
        self.pw = sync_playwright().start()
        self.ctx = self.pw.chromium.launch_persistent_context(
            self.user_data,
            headless=False,
            accept_downloads=True
        )
        self.page = self.ctx.pages[0]
        return self

    def __exit__(self, *args):
        self.ctx.close()
        self.pw.stop()

    def login(self):
        print("🔐 Ensuring Screener login...")
        self.page.goto("https://www.screener.in/login/", wait_until="domcontentloaded")

        try:
            self.page.wait_for_url("**/dash/**", timeout=10_000)
            print("✅ Already logged in")
            return
        except:
            pass

        print("👉 Please login manually in the browser window")
        self.page.wait_for_url("**/dash/**", timeout=120_000)
        print("✅ Login detected")

    def get_quarterly_reports(self):
        """
        Extract quarterly PDF links from the Quarters table on Screener.
        """
        print("📊 Collecting quarterly reports...")

        self.page.locator("#quarters").scroll_into_view_if_needed()
        self.page.wait_for_timeout(2000)

        links = self.page.locator('#quarters a[aria-label="Raw PDF"]').all()
        reports = []

        for a in links:
            href = a.get_attribute("href")
            if not href:
                continue

            parts = [p for p in href.split("/") if p]

            try:
                year = parts[-1]
                month = parts[-2]
                quarter = (int(month) - 1) // 3 + 1

                reports.append({
                    "type": "quarter",
                    "year": year,
                    "quarter": quarter,
                    "url": f"https://www.screener.in{href}"
                })
            except:
                continue

        print(f"✅ Found {len(reports)} quarterly reports")
        return reports

    def get_annual_reports(self):
        """
        Extract annual report PDF links from Screener.
        """
        print("📄 Collecting annual reports...")

        section = self.page.locator("div.documents.annual-reports")
        if section.count() == 0:
            print("⚠️ No annual reports section found")
            return []

        section.scroll_into_view_if_needed()
        self.page.wait_for_timeout(2000)

        reports = []
        items = section.locator("ul.list-links > li").all()

        for li in items:
            try:
                link = li.locator("a").first
                href = link.get_attribute("href")

                if not href or not href.endswith(".pdf"):
                    continue

                text = li.inner_text()
                year = None

                # Extract year from text
                for word in text.split():
                    if word.isdigit() and len(word) == 4:
                        year = word
                        break

                # Fallback: extract year from URL
                if not year:
                    import re
                    match = re.search(r"20\d{2}", href)
                    if match:
                        year = match.group(0)

                reports.append({
                    "type": "annual",
                    "year": year or "unknown",
                    "url": href
                })

            except:
                continue

        print(f"✅ Found {len(reports)} annual reports")
        return reports
    
    def get_concall_reports(self):
        """
        Extract concall transcript or PPT links from Screener.
        Preference: Transcript > PPT
        """
        print("🎤 Collecting concall reports...")

        section = self.page.locator("div.documents.concalls")
        if section.count() == 0:
            print("⚠️ No concalls section found")
            return []

        section.scroll_into_view_if_needed()
        self.page.wait_for_timeout(2000)

        reports = []
        items = section.locator("ul.list-links > li").all()

        for li in items:
            try:
                date_div = li.locator("div.ink-600")
                if date_div.count() == 0:
                    continue

                label = date_div.inner_text().strip()

                # Prefer Transcript
                transcript = li.locator('a.concall-link:has-text("Transcript")')
                if transcript.count() > 0:
                    href = transcript.first.get_attribute("href")
                    if href:
                        reports.append({
                            "type": "concall",
                            "label": f"{label} Transcript",
                            "url": href
                        })
                        continue

                # Else fallback to PPT
                ppt = li.locator('a.concall-link:has-text("PPT")')
                if ppt.count() > 0:
                    href = ppt.first.get_attribute("href")
                    if href:
                        reports.append({
                            "type": "concall",
                            "label": f"{label} PPT",
                            "url": href
                        })

            except:
                continue

        print(f"✅ Found {len(reports)} concall reports")
        return reports

    def get_all_reports(self):
        """
        Collect all types of reports: quarterly, annual, concall.
        """
        reports = []
        reports.extend(self.get_quarterly_reports())
        reports.extend(self.get_annual_reports())
        reports.extend(self.get_concall_reports())
        return reports
    
# # Example usage:
if __name__ == "__main__":
    with ScreenerScraper() as scraper:
        scraper.login()
        reports = scraper.get_all_reports()
        for report in reports:
            print(report) 

