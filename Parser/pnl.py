import pdfplumber
import re


def detect_pnl_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Consolidated Statement of Profit and Loss
    """

    title_patterns = [
        r"consolidated statement of profit and loss",
        r"consolidated statement of profit & loss",
        r"consolidated statement of profit"
    ]

    anchors = [
        r"other income",
        r"total income",
        r"basic",
        r"total expenses"
    ]

    detected_pages = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            if "standalone" in text:
                continue

            # ❌ EXCLUDE: standalone mentioned on PREVIOUS page
            if i > 0:
                prev_text = (pdf.pages[i - 1].extract_text() or "").lower()
                if "standalone" in prev_text:
                    continue

            # 1️⃣ Title check
            title_match = any(
                re.search(pattern, text) for pattern in title_patterns
            )

            # 2️⃣ Anchor validation
            anchor_hits = [a for a in anchors if a in text]

            if len(anchor_hits) >= 3:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_pnl_pages(pdf)
    print("P&L pages:", pages)