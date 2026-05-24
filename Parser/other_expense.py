import pdfplumber
import re


def detect_other_expense_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect pages containing Other Expenses / Other Operating Expenses tables.
    Excludes standalone and accounting policy pages.
    Returns a list of page numbers.
    """

    # 1️⃣ Semantic title patterns
    title_patterns = [
        r"other expenses",
        r"other expenditure",
        r"other operating expenses"
    ]

    # 2️⃣ Expense-specific anchors
    anchors = [
        r"travelling",
        r"travel",
        r"rent",
        r"power",
        r"fuel",
        r"repairs",
        r"maintenance",
        r"fees",
        r"communication"
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
                if "standalone" in prev_text or "standalone financials" in prev_text:
                    continue

            # 1️⃣ Title check (mandatory)
            title_match = any(
                re.search(pattern, text) for pattern in title_patterns
            )

            if not title_match:
                continue

            # 2️⃣ Anchor confirmation
            anchor_hits = [a for a in anchors if a in text]

            if len(anchor_hits) >= 3:
                detected_pages.add(i + 1)

    return sorted(detected_pages)


if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_other_expense_pages(pdf)
    print("Other Expense pages:", pages)