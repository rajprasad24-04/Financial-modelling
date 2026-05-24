import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname((current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Table.iii_table_for_pnl import camelot_parser as camelot_parser_pnl

def parse_all_pdfs(base_dir="downloads", tickers=None):
    if tickers is None:
        tickers = os.listdir(base_dir)

    all_company_results = {}

    for ticker in tickers:
        annual_dir = os.path.join(base_dir, ticker, "annual")

        if not os.path.isdir(annual_dir):
            continue

        for file in os.listdir(annual_dir):
            if not file.lower().endswith(".pdf"):
                continue

            pdf_path = os.path.join(annual_dir, file)
            print(f"\n📄 Processing {ticker}: {file}")

            try:
                results = camelot_parser_pnl(pdf_path)
                if results:
                    all_company_results[f"{ticker}/{file}"] = results
            except Exception as e:
                print(f"❌ Failed {ticker}/{file}: {e}")

    return all_company_results