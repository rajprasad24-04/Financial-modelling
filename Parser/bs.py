import pdfplumber
import re


def detect_bs_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Consolidated Balance Sheet
    """

    titles = [
        r"consolidated balance sheet",
        r"consolidated statement of financial position"
    ]

    anchors = [
        r"non-current assets",
        r"current assets",
        r"total equity",
        r"liabilities",
        r"total current liabilities",
        r"equity",
        r"total assets",
    ]

    detected_pages = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            title_match = any(re.search(t, text) for t in titles)
            anchor_hits = [a for a in anchors if a in text]

            if title_match and len(anchor_hits) >= 3:
                detected_pages.add(i + 1)

    return sorted(detected_pages)

if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_bs_pages(pdf)
    print("Balance Sheet pages:", pages)