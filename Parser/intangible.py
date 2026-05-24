import pdfplumber
import re


def detect_intangible_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Intangible Assets tables.
    Excludes standalone context and goodwill-only pages.
    Returns a list of page numbers.
    """

    # 1️⃣ Semantic title patterns
    title_patterns = [
        r"intangible assets",
        r"other intangible assets",
        r"intangible assets under development"
    ]

    # 2️⃣ Intangible-specific anchors
    anchors = [
        "gross carrying amount",
        "accumulated amortisation",
        "accumulated amortization",
        "amortisation",
        "amortization",
        "additions",
        "closing balance"
    ]

    detected_pages = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            # ❌ Exclude standalone context (current page)
            if "standalone" in text or "standalone financials" in text:
                continue

            # ❌ Exclude standalone context (previous page)
            if i > 0:
                prev_text = (pdf.pages[i - 1].extract_text() or "").lower()
                if "standalone" in prev_text:
                    continue

            

            # 1️⃣ Title check
            title_match = any(
                re.search(pattern, text) for pattern in title_patterns
            )

            if not title_match:
                continue

            # ❌ Exclude goodwill-only pages
            if "goodwill" in text and "intangible" not in text:
                continue

            # 2️⃣ Anchor confirmation
            anchor_hits = [a for a in anchors if a in text]

            if len(anchor_hits) >= 1:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_intangible_pages(pdf)
    print("Intangible pages:", pages)