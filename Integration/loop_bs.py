import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname((current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Table.ii_table_for_bs import camelot_parser as camelot_parser_bs

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
                results = camelot_parser_bs(pdf_path)
                if results:
                    all_company_results[f"{ticker}/{file}"] = results
            except Exception as e:
                print(f"❌ Failed {ticker}/{file}: {e}")

    return all_company_results

# # Example usage:
# if __name__ == "__main__":
#     all_results = parse_all_pdfs(tickers=["TCS"])

#     for pdf_name, page_data in all_results.items():
#         print(f"\n===== {pdf_name} =====")

#         ticker, pdf_file = pdf_name.split("/", 1)

#         export_dir = os.path.join("output", ticker)
#         os.makedirs(export_dir, exist_ok=True)

#         for page_key, tables in page_data.items():
#             for idx, df in enumerate(tables):
#                 csv_name = os.path.join(
#                     export_dir,
#                     f"{pdf_file}_{page_key}_table_{idx}.csv"
#                 )

                # df.to_csv(csv_name, index=False)
                # print(f"Exported {csv_name}")