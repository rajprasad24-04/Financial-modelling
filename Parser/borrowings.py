import pdfplumber
import re


def detect_borrowing_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect borrowing schedules using
    title + anchor-density logic (CWIP-style).

    Returns:
    {
        "long_term": [page numbers],
        "short_term": [page numbers]
    }
    """

    # 🔹 Long-term borrowing titles
    long_term_titles = [
        r"long[-\s]?term borrowings",
        r"non[-\s]?current borrowings",
        r"borrowings\s*\(non[-\s]?current\)",
        r"borrowings[-\s]non[-\s]current"
    ]

    # 🔹 Short-term borrowing titles
    short_term_titles = [
        r"short[-\s]?term borrowings",
        r"current borrowings",
        r"borrowings\s*\(current\)"
    ]

    # 🔹 Borrowing-specific anchors
    anchors = [
        r"secured",
        r"unsecured",
        r"term loan",
        r"bank",
        r"debenture",
        r"banks"
    ]

    results = {
        "long_term": set(),
        "short_term": set()
    }

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            # ❌ Exclude standalone (current page)
            if "standalone" in text:
                continue

            # ❌ Exclude standalone spillover (previous page)
            if i > 0:
                prev_text = (pdf.pages[i - 1].extract_text() or "").lower()
                if "standalone" in prev_text:
                    continue

            # 🔹 Anchor density check (CWIP-style)
            anchor_hits = [
                a for a in anchors
                if re.search(a, text)
            ]

            if len(anchor_hits) < 2:
                continue

            # 🔹 Long-term borrowings
            if any(re.search(p, text) for p in long_term_titles):
                results["long_term"].add(i + 1)

            # 🔹 Short-term borrowings
            if any(re.search(p, text) for p in short_term_titles):
                results["short_term"].add(i + 1)

    return {
        "long_term": sorted(results["long_term"]),
        "short_term": sorted(results["short_term"])
    }


if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_borrowing_pages(pdf)
    print("Borrowing pages:", pages)