import pdfplumber
import re


def detect_finance_cost_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Finance Cost / Finance Expense tables.
    Excludes standalone and accounting policy pages.
    Returns a list of page numbers.
    """

    # 1️⃣ Semantic title patterns
    title_patterns = [
        r"finance costs",
        r"finance cost",
        r"finance expenses",
        r"borrowing costs"
    ]

    # 2️⃣ Finance cost specific anchors
    anchors = [
        "interest expense",
        "interest on borrowings",
        "interest on lease",
        "lease liabilities",
        "bank charges",
        "borrowing costs",
        "unwinding",
        "discount"
    ]

    detected_pages = set()

    with pdfplumber.open(pdf_path) as pdf:
        pages_to_scan = min(search_limit, len(pdf.pages))

        for i in range(pages_to_scan):
            text = (pdf.pages[i].extract_text() or "").lower()

            # ❌ Exclude standalone context (current page)
            if "standalone" in text:
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

            # 2️⃣ Anchor confirmation
            anchor_hits = [a for a in anchors if a in text]

            if len(anchor_hits) >= 1:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_finance_cost_pages(pdf)
    print("Finance Cost pages:", pages)