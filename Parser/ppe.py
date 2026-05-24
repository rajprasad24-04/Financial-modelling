import pdfplumber
import io
import re
from pypdf import PdfReader, PdfWriter


def detect_ppe_pages(pdf_path: str):
    """
    Detect pages containing Property, Plant and Equipment (PPE) schedules.
    Uses rotation-aware logic and anchor validation.
    """

    ppe_regex = r"[.\d]*\s*property,?\s+plant\s+and\s+equipment"

    anchors = [
        r"gross carrying amount",
        r"accumulated depreciation",
        r"net carrying amount",
        r"additions",
        r"deletions",
        r"depreciation",
        r"cost as at",
    ]

    detected_pages = []

    reader = PdfReader(pdf_path)

    for i in range(len(reader.pages)):
        page_num = i + 1
        page = reader.pages[i]

        try:

            if i > 0:
                prev_page_text = (reader.pages[i - 1].extract_text() or "").lower()
                if "standalone" in prev_page_text:
                    continue  # ❌ Skip standalone context


            # Rotate page to handle landscape tables
            page.rotate(90)

            writer = PdfWriter()
            writer.add_page(page)
            buffer = io.BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            with pdfplumber.open(buffer) as temp_pdf:
                text = (temp_pdf.pages[0].extract_text() or "").lower()

                if(
                    "standalone" in text
                    or "standalone financials" in text
                ):
                    continue

                # 1️⃣ Title check
                title_match = re.search(ppe_regex, text)
                if not title_match:
                    continue
                # 2️⃣ Anchor validation
                anchor_hits = [a for a in anchors if a in text]
                if len(anchor_hits) >= 3:
                    detected_pages.append(page_num)

        except Exception as e:
            print("Error on page", page_num, ":", e)


    return detected_pages

if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_ppe_pages(pdf)
    print("PPE pages:", pages)