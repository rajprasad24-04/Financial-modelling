import pdfplumber
import re


def detect_rou_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Right-of-Use (ROU) asset tables.
    Returns a list of page numbers.
    """

    # Strong semantic title patterns
    title_patterns = [
        r"right[-\s]?of[-\s]?use assets",
        r"right[-\s]?of[-\s]?use asset",
        r"rou"
    ]

    # Lease-specific anchors (ROU fingerprint)
    anchors = [
        r"gross carrying amount"
        r"amortization",
        r"right-of-use",
        r"balance as",
        r"depreciation"
    ]

    detected_pages = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            # ❌ Exclude pure accounting policy pages
            if "standalone" in text or "standalone financials" in text:
                continue

            # ❌ EXCLUDE: standalone mentioned on PREVIOUS page
            if i > 0:
                prev_text = (pdf.pages[i - 1].extract_text() or "").lower()
                if "standalone" in prev_text:
                    continue

            # 1️⃣ Title check (mandatory)
            title_match = any(
                re.search(pattern, text) for pattern in title_patterns
            )

            if not title_match:
                continue

            # 2️⃣ Anchor confirmation (light)
            anchor_hits = [a for a in anchors if a in text]

            if len(anchor_hits) >= 2:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


# if __name__ == "__main__":
#     pdf = "downloads/RELIANCE/annual/RELIANCE_Annual_2025.pdf"
#     pages = detect_rou_pages(pdf)
#     print("ROU pages:", pages)