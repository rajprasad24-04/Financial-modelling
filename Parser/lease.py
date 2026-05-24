import pdfplumber
import re


def detect_lease_liability_pages(pdf_path: str, search_limit: int = 400):
    """
    Detect lease liability schedules.
    Returns:
    {
        "long_term": [page numbers],
        "short_term": [page numbers]
    }
    """

    # Long-term lease liability titles
    long_term_titles = [
        r"long[-\s]?term lease liabilities",
        r"non[-\s]?current lease liabilities",
        r"lease liabilities \(non[-\s]?current\)"
    ]

    # Short-term lease liability titles
    short_term_titles = [
        r"short[-\s]?term lease liabilities",
        r"current lease liabilities",
        r"lease liabilities \(current\)"
    ]

    # Lease-specific anchors
    anchors = [
        "lease term",
        "interest",
        "discount",
        "maturity",
        "present value",
        "repayable",
        "lease payment"
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

            # ❌ Exclude standalone (previous page)
            if i > 0:
                prev_text = (pdf.pages[i - 1].extract_text() or "").lower()
                if "standalone" in prev_text:
                    continue

            

            # -----------------------------
            # Anchor validation (SAME STYLE)
            # -----------------------------
            anchor_hits = [a for a in anchors if a in text]

            # 🔹 Long-term lease liabilities
            if any(re.search(p, text) for p in long_term_titles):
                if len(anchor_hits) >= 2:
                    results["long_term"].add(i + 1)

            # 🔹 Short-term lease liabilities
            if any(re.search(p, text) for p in short_term_titles):
                if len(anchor_hits) >= 2:
                    results["short_term"].add(i + 1)

    return {
        "long_term": sorted(results["long_term"]),
        "short_term": sorted(results["short_term"])
    }


if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_lease_liability_pages(pdf)
    print("Lease Liability pages:", pages)