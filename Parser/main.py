import os
import sys
from typing import List, Set

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Parser.bs import detect_bs_pages
from Parser.cwip import detect_cwip_pages
from Parser.lease import detect_lease_liability_pages
from Parser.rou import detect_rou_pages
from Parser.finance_cost import detect_finance_cost_pages
from Parser.borrowings import detect_borrowing_pages
from Parser.ppe import detect_ppe_pages
from Parser.depreciation import detect_depreciation_pages
from Parser.intangible import detect_intangible_pages
from Parser.other_expense import detect_other_expense_pages
from Parser.pnl import detect_pnl_pages
from Parser.quarterly_pnl import detect_quarterly_pnl_pages
from Parser.quarterly_segment import detect_quarterly_segment_pages


def detect_all_relevant_pages(pdf_path: str) -> List[int]:
    """
    Runs all page detectors and returns ONE
    sorted unique list of relevant page numbers.
    """

    all_pages: Set[int] = set()

    # ---------------- Annual detectors ----------------
    all_pages.update(detect_bs_pages(pdf_path))
    # all_pages.update(detect_cwip_pages(pdf_path))
    # all_pages.update(detect_rou_pages(pdf_path))
    # all_pages.update(detect_finance_cost_pages(pdf_path))
    # all_pages.update(detect_ppe_pages(pdf_path))
    # all_pages.update(detect_depreciation_pages(pdf_path))
    # all_pages.update(detect_intangible_pages(pdf_path))
    # all_pages.update(detect_other_expense_pages(pdf_path))
    # all_pages.update(detect_pnl_pages(pdf_path))

    # ---------------- Lease liability (dict return) ----------------
    # lease_pages = detect_lease_liability_pages(pdf_path)
    # all_pages.update(lease_pages.get("long_term", []))
    # all_pages.update(lease_pages.get("short_term", []))

    # ---------------- Borrowings (dict return) ----------------
    # borrowings = detect_borrowing_pages(pdf_path)
    # all_pages.update(borrowings.get("long_term", []))
    # all_pages.update(borrowings.get("short_term", []))

    # ---------------- Quarterly detectors ----------------
    # all_pages.update(detect_quarterly_pnl_pages(pdf_path))
    # all_pages.update(detect_quarterly_segment_pages(pdf_path))

    return sorted(all_pages)


# # Example usage:
if __name__ == "__main__":
    pdf = "downloads/TCS/annual/TCS_Annual_2025.pdf"
    pages = detect_all_relevant_pages(pdf)
    print(pages)


