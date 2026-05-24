import os
import sys
import time
import json
import logging

# ---- Fix imports ----
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from Scraper.i_build_url import build_company_url
from Scraper.ii_screener_scraper import ScreenerScraper
# Commented out since we are not using Google Drive right now
# from Scraper.iii_google_drive_manager import GoogleDriveManager

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---- Constants ----
MAX_RETRIES = 3
RETRY_DELAY = 3
MIN_VALID_PDF_SIZE = 1024
PDF_MAGIC_BYTES = b"%PDF"


# ============================================================
# Folder & filename helpers
# ============================================================

def _build_local_path(base_dir: str, ticker: str, report: dict) -> tuple:
    """
    downloads/
    └── TICKER/
        ├── annual/
        ├── quarterly/
        └── concall/
    """
    folder_map = {"annual": "annual", "quarter": "quarterly", "concall": "concall"}
    subfolder = folder_map.get(report["type"], "other")
    folder_path = os.path.join(base_dir, ticker.upper(), subfolder)
    os.makedirs(folder_path, exist_ok=True)

    fname = _build_filename(ticker, report)
    return folder_path, os.path.join(folder_path, fname)


def _build_filename(ticker: str, report: dict) -> str:
    t = report["type"]
    if t == "annual":
        return f"{ticker.upper()}_Annual_{report['year']}.pdf"
    elif t == "quarter":
        return f"{ticker.upper()}_Q{report['quarter']}_{report['year']}.pdf"
    else:
        safe = (
            report.get("label", "unknown")
            .replace(" ", "_").replace("/", "-")
            .replace(":", "").replace("(", "").replace(")", "")
        )
        return f"{ticker.upper()}_Concall_{safe}.pdf"


# ============================================================
# PDF validation
# ============================================================

def _is_valid_pdf(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    if os.path.getsize(file_path) < MIN_VALID_PDF_SIZE:
        return False
    with open(file_path, "rb") as f:
        return f.read(4) == PDF_MAGIC_BYTES


# ============================================================
# Download single PDF
# ============================================================
# ROOT CAUSE:
#   Chromium has a built-in PDF viewer. When a URL returns content-type
#   application/pdf, Chrome intercepts the bytes and renders them inside
#   an <embed> tag. response.body() then returns Chrome's PDF-viewer
#   HTML wrapper (always ~345 bytes) instead of the actual PDF.
#
# FIX:
#   Use page.route() to intercept requests whose response is a PDF.
#   When we catch one, we store the raw bytes from the network response
#   BEFORE Chrome's PDF plugin gets them. Then we abort the page
#   navigation (we don't need it to render anything).
# ============================================================

def _download_pdf(page, url: str, file_path: str, fname: str) -> bool:
    """
    Downloads a PDF by intercepting the network response directly,
    bypassing Chromium's built-in PDF viewer.
    """
    captured_bytes = {}  # use dict so inner function can mutate it

    def handle_route(route):
        """
        Intercept the request. Fetch it ourselves, grab the body,
        store it, then abort the route so Chrome doesn't try to render it.
        """
        try:
            # Fetch the actual response from the network
            response = route.fetch()
            body = response.body()
            content_type = response.headers.get("content-type", "").lower()

            # Store if it looks like a PDF (by content-type OR magic bytes)
            if "pdf" in content_type or (body and body[:4] == PDF_MAGIC_BYTES):
                captured_bytes["data"] = body
                logger.info(f"    📥 Intercepted PDF: {len(body):,} bytes")

            # Fulfill the route so the page doesn't hang
            route.fulfill(response=response)

        except Exception as e:
            logger.warning(f"    ⚠️  Route intercept error: {e}")
            route.abort()

    for attempt in range(1, MAX_RETRIES + 1):
        captured_bytes.clear()

        try:
            logger.info(f"    ⬇️  Attempt {attempt}/{MAX_RETRIES}: {fname}")

            # Intercept ALL requests on this page
            page.route("**/*", handle_route)

            # Navigate — the route handler will capture the PDF bytes
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Remove the route after navigation is done
            page.unroute("**/*")

            # Check if we captured anything
            if "data" not in captured_bytes:
                logger.warning(f"    ⚠️  No PDF captured (attempt {attempt})")
                time.sleep(RETRY_DELAY)
                continue

            pdf_bytes = captured_bytes["data"]

            # Validate size
            if len(pdf_bytes) < MIN_VALID_PDF_SIZE:
                logger.warning(f"    ⚠️  Captured data too small: {len(pdf_bytes)} bytes")
                time.sleep(RETRY_DELAY)
                continue

            # Validate magic bytes
            if pdf_bytes[:4] != PDF_MAGIC_BYTES:
                logger.warning(f"    ⚠️  Captured data is not a valid PDF")
                time.sleep(RETRY_DELAY)
                continue

            # Write to disk
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)

            # Final check
            if _is_valid_pdf(file_path):
                logger.info(f"    ✅ Saved ({os.path.getsize(file_path):,} bytes): {fname}")
                return True
            else:
                os.remove(file_path)
                logger.warning(f"    ⚠️  File validation failed after write")
                time.sleep(RETRY_DELAY)

        except Exception as e:
            logger.error(f"    ❌ Error (attempt {attempt}): {e}")
            # Make sure route is cleaned up even on error
            try:
                page.unroute("**/*")
            except:
                pass
            if os.path.exists(file_path):
                os.remove(file_path)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    logger.error(f"    ❌ Failed after {MAX_RETRIES} attempts: {fname}")
    return False


# ============================================================
# Main pipeline
# ============================================================

def collect_company_reports(
    ticker: str,
    standalone: bool = False,
    download_dir: str = "downloads"
) -> dict:
    """
    Full pipeline in one browser session:
        1. Login to Screener
        2. Go to company page
        3. Scrape all report URLs
        4. Download each PDF (intercepting network to bypass Chrome PDF viewer)

    Parameters
    ----------
    ticker : str
        Company ticker (e.g. "RELIANCE")
    standalone : bool
        Use standalone reports instead of consolidated
    download_dir : str
        Base folder for downloads

    Returns
    -------
    dict
        Summary with keys: downloaded, skipped, failed, files
    """

    # ---- Google Drive setup [DISABLED] ----
    # drive = GoogleDriveManager()
    # drive.authenticate()
    # folders = drive.setup_company_folders(ticker)

    # ---- Tracking ----
    downloaded = 0
    skipped = 0
    failed = 0
    downloaded_files = []
    seen_urls = set()

    # ---- Build Screener URL ----
    company_url = build_company_url(ticker, standalone)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"🚀 Starting pipeline for: {ticker.upper()}")
    logger.info(f"🔗 Screener URL: {company_url}")
    logger.info(f"📁 Download dir: {os.path.abspath(download_dir)}")
    logger.info(f"{'=' * 60}\n")

    # ---- Single browser session ----
    with ScreenerScraper() as scraper:

        # Step 1: Login
        scraper.login()

        # Step 2: Go to company page
        scraper.page.goto(company_url, wait_until="domcontentloaded")
        scraper.page.wait_for_timeout(3000)

        # Step 3: Scrape all report URLs
        logger.info("📊 Scraping report URLs...")
        reports = scraper.get_all_reports()
        logger.info(f"📦 Found {len(reports)} total reports\n")

        if not reports:
            logger.warning("⚠️  No reports found. Exiting.")
            return {"downloaded": 0, "skipped": 0, "failed": 0, "files": []}

        # Step 4: Download each PDF
        logger.info(f"{'=' * 60}")
        logger.info("⬇️  DOWNLOADING REPORTS")
        logger.info(f"{'=' * 60}\n")

        for i, report in enumerate(reports, 1):
            url = report.get("url")
            if not url:
                logger.warning(f"  [{i}/{len(reports)}] No URL — skipping")
                skipped += 1
                continue

            # Deduplicate
            if url in seen_urls:
                skipped += 1
                continue
            seen_urls.add(url)

            # Build structured path
            folder_path, file_path = _build_local_path(download_dir, ticker, report)
            fname = os.path.basename(file_path)

            logger.info(f"  [{i}/{len(reports)}] {fname}")
            logger.info(f"    📍 {url}")

            # Skip if already valid on disk
            if _is_valid_pdf(file_path):
                logger.info(f"    ⏭️  Already exists — skipping")
                skipped += 1
                continue

            # Download using network interception
            success = _download_pdf(scraper.page, url, file_path, fname)

            if success:
                downloaded += 1
                downloaded_files.append(file_path)

                # ---- Google Drive Upload [DISABLED] ----
                # try:
                #     drive_folder_id = folders.get(report["type"])
                #     if drive_folder_id:
                #         drive.upload_file(file_path, drive_folder_id)
                #         logger.info(f"    ☁️  Uploaded to Drive")
                # except Exception as e:
                #     logger.error(f"    ❌ Drive upload failed: {e}")

                time.sleep(1)  # polite delay
            else:
                failed += 1

    # ---- Summary ----
    logger.info(f"\n{'=' * 60}")
    logger.info(f"✅ SUMMARY for {ticker.upper()}")
    logger.info(f"{'=' * 60}")
    logger.info(f"  📥 Downloaded : {downloaded}")
    logger.info(f"  ⏭️  Skipped   : {skipped}")
    logger.info(f"  ❌ Failed     : {failed}")
    logger.info(f"{'=' * 60}\n")

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "files": downloaded_files,
    }


# ============================================================
# Run from terminal
# ============================================================

if __name__ == "__main__":

    # Check if the user provided the ticker in the command line
    if len(sys.argv) >= 2:
        ticker = sys.argv[1].upper().strip()
    else:
        # Fallback: Ask interactively if they forgot to type it
        user_input = input("🏢 Enter company ticker symbol (e.g., RELIANCE, TCS): ")
        ticker = user_input.upper().strip()

    if not ticker:
        print("❌ Error: No ticker provided.")
        sys.exit(1)

    results = collect_company_reports(ticker)

    # Save summary JSON
    output_json = os.path.join("downloads", ticker.upper(), "summary.json")
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"💾 Summary saved: {output_json}")