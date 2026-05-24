import os
import sys
from typing import List

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname((current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Parser.main import detect_all_relevant_pages
from Table.ii_table_for_bs import camelot_parser as camelot_parser_bs
from Table.iii_table_for_pnl import camelot_parser_pnl


def all_tables_parser(pdf_path: str):
    """
    Parses all relevant tables from the pdf using detected page numbers
    and returns tables in dict format.
    """

    relevant_pages: List[int] = detect_all_relevant_pages(pdf_path)
    parsed_tables = {}

    for page_num in relevant_pages:
        page_key = f"page_{page_num}"

        try:
            _, bs_tables = camelot_parser_bs(pdf_path, page_num)
            parsed_tables.setdefault(page_key, {})["balance_sheet"] = bs_tables
        except Exception as e:
            print(f"Error parsing BS on page {page_num}: {e}")

        try:
            _, pnl_tables = camelot_parser_pnl(pdf_path, page_num)
            parsed_tables.setdefault(page_key, {})["pnl"] = pnl_tables
        except Exception as e:
            print(f"Error parsing P&L on page {page_num}: {e}")

    return parsed_tables

# Example usage:
if __name__ == "__main__":
    pdf_file = "downloads/TCS/annual/TCS_Annual_2023.pdf"
    all_tables = all_tables_parser(pdf_file)

    for page, tables_dict in all_tables.items():
        print(f"\nTables on {page}:")
        for table_type, tables in tables_dict.items():
            print(f"  {table_type}: {len(tables)} tables")
            for idx, df in enumerate(tables):
                print(f"    Table {idx} preview:")
                print(df.head(5))
                print("\n")

# ============================================================
#Exported csvs for all tables
# ============================================================
    for page, tables_dict in all_tables.items():
        for table_type, tables in tables_dict.items():
            for idx, df in enumerate(tables):
                csv_name = f"{page}_{table_type}_table_{idx}.csv"
                df.to_csv(csv_name, index=False)
                print(f"Exported {csv_name}")