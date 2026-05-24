import pdfplumber
import re


def detect_cwip_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Capital Work-in-Progress (CWIP) tables.
    Returns a list of page numbers.
    """

    # Semantic title patterns
    title_patterns = [
        r"capital work[-\s]?in[-\s]?progress"
        r"cwip",
        r"Capital work-in-progress"
    ]

    # CWIP-specific anchors
    anchors = [
        r"(cwip)",
        r"gross carrying amount",
        r"total capital work-in-progress",
        r"property, plant and equipment",
        r"projects in progress"
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

            if len(anchor_hits) >= 2:
                detected_pages.add(i + 1)

    return sorted(detected_pages)

# if __name__ == "__main__":
#     pdf = "downloads/RELIANCE/annual/RELIANCE_Annual_2025.pdf"
#     pages = detect_cwip_pages(pdf)
#     print("CWIP pages:", pages)
