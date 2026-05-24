import pdfplumber
import re


def detect_depreciation_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Depreciation / Amortisation expense notes.
    Excludes standalone and accounting policy pages.
    Returns a list of page numbers.
    """

    # 1️⃣ Semantic title patterns
    title_patterns = [
        r"depreciation",
        r"depreciation and amortisation",
        r"depreciation & amortisation",
        r"depreciation expense",
        r"amortisation expense"
    ]

    # 2️⃣ Depreciation-specific anchors
    anchors = [
        "property, plant and equipment",
        "right of use",
        "intangible",
        "amortisation",
        "useful life",
        "depreciation charge",
        "charged to profit and loss"
    ]

    detected_pages = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            # ❌ Exclude standalone (current page)
            if "standalone" in text:
                continue

            # ❌ Exclude standalone (previous page)
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

            # 2️⃣ Anchor confirmation
            anchor_hits = [a for a in anchors if a in text]

            if len(anchor_hits) >= 2:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


# if __name__ == "__main__":
#     pdf = "downloads/RELIANCE/annual/RELIANCE_Annual_2025.pdf"
#     pages = detect_depreciation_pages(pdf)
#     print("Depreciation pages:", pages)