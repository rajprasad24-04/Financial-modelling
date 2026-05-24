
import pdfplumber
import re


def detect_quarterly_segment_pages(pdf_path: str, search_limit: int = 50):
    """
    Detect Quarterly Segment Information pages.
    Returns a list of page numbers.
    """

    # 1️⃣ Segment title patterns
    title_patterns = [
        r"segment information",
        r"segment reporting",
        r"business segments",
        r"operating segments"
    ]

    # 2️⃣ Segment-specific anchors
    anchors = [
        "segment revenue",
        "segment results",
        "segment assets",
        "geographical",
        "india",
        "americas",
        "europe",
        "asia",
        "rest of the world"
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

            if len(anchor_hits) >= 2:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


# if __name__ == "__main__":
#     pdf = "downloads/RELIANCE/annual/RELIANCE_Annual_2025.pdf"
#     pages = detect_quarterly_segment_pages(pdf)
#     print("Quarterly Segment pages:", pages)