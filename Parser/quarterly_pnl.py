import os
import sys
import pdfplumber
import re

# -------------------------------------------------
# Path setup
# ------------------------------------------------- 
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

pdf = os.path.join(
    BASE_DIR,
    "downloads",
    "TCS",
    "quarterly",
    "TCS_Q1_FY23.pdf"
)


# =================================================
# Quarterly P&L Page Detection
# =================================================


def detect_quarterly_pnl_pages(pdf_path: str, search_limit: int = 50):
    """
    Detect Quarterly Profit & Loss (Financial Results) pages.
    Returns a list of page numbers.
    """

    # 1️⃣ Quarterly P&L title patterns
    title_patterns = [
        r"unaudited financial results",
        r"audited consolidated statement of financial results"
        r"quarterly financial results",
        r"statement of unaudited financial results",
        r"consolidated statement"
    ]

    # 2️⃣ Quarterly P&L anchors
    anchors = [
        r"three months",
        r"quarter ended",
        r"total income",
        r"profit",
        r"earnings per share",
        r"basic",
        r"diluted"
        r"net profit",
    ]

    detected_pages = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            # ❌ Exclude standalone (current page)
            if "standalone" in text:
                continue

            # # ❌ Exclude standalone (previous page)
            # if i > 0:
            #     prev_text = (pdf.pages[i - 1].extract_text() or "").lower()
            #     if "standalone" in prev_text:
            #         continue

            # 1️⃣ Title check
            title_match = any(
                re.search(pattern, text) for pattern in title_patterns
            )
            if not title_match:
                continue

            # 2️⃣ Anchor validation (same format)
            anchor_hits = [a for a in anchors if a in text]

            if len(anchor_hits) >= 3:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


if __name__ == "__main__":
    pdf = "downloads/TCS/quarterly/TCS_Q1_2023.pdf"
    pages = detect_quarterly_pnl_pages(pdf)
    print("Quarterly P&L pages:", pages)