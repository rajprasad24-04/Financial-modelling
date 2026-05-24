import os
import sys
import re
import pandas as pd

# -------------------------------------------------
# Path setup
# -------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Integration.loop_bs import parse_all_pdfs


# =================================================
# STEP 1: Convert ONE BS table to LONG format
# =================================================

def bs_table_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts a Balance Sheet table to long format:
    (Particulars, Year, Value)
    """
    df = df.copy()

    if "Note" in df.columns:
        df = df.drop(columns=["Note"])

    records = []

    for col in df.columns:
        if col == "Particulars":
            continue

        match = re.search(r"\d{4}", col)
        if not match:
            continue

        year = int(match.group())

        for _, row in df.iterrows():
            records.append({
                "Particulars": row["Particulars"],
                "Year": year,
                "Value": row[col]
            })

    return pd.DataFrame(records)


# =================================================
# STEP 2: Collect ALL BS tables + preserve order
# =================================================

def collect_bs_long_with_order(all_results: dict):
    """
    Returns:
    - long_df  : stacked values
    - order_map: dict {Particular -> first_seen_index}
    """

    all_long = []
    order_map = {}
    order_counter = 0

    for pdf_name, page_data in all_results.items():
        for page_key, tables in page_data.items():
            for df in tables:

                # Preserve first-seen order of Particulars
                for p in df["Particulars"]:
                    if p not in order_map:
                        order_map[p] = order_counter
                        order_counter += 1

                long_df = bs_table_to_long(df)
                if not long_df.empty:
                    all_long.append(long_df)

    if not all_long:
        return pd.DataFrame(columns=["Particulars", "Year", "Value"]), {}

    return pd.concat(all_long, ignore_index=True), order_map


# =================================================
# STEP 3: Horizontal stack (ORDER PRESERVED)
# =================================================

def horizontal_stack_bs(all_results: dict) -> pd.DataFrame:
    """
    Produces final horizontally stacked Balance Sheet
    with ORIGINAL PARTICULAR ORDER preserved
    """

    long_df, order_map = collect_bs_long_with_order(all_results)

    if long_df.empty:
        return long_df

    merged = (
        long_df
        .pivot_table(
            index="Particulars",
            columns="Year",
            values="Value",
            aggfunc="first",
            dropna=False
        )
        .reset_index()
    )

    # Reapply original order
    merged["_order"] = merged["Particulars"].map(order_map)
    merged = merged.sort_values("_order").drop(columns="_order")

    # Sort year columns ONLY
    year_cols = sorted([c for c in merged.columns if isinstance(c, int)])
    merged = merged[["Particulars"] + year_cols]

    return merged


# =================================================
# Example Usage
# =================================================

if __name__ == "__main__":

    all_results = parse_all_pdfs(tickers=["TCS"])

    merged_bs = horizontal_stack_bs(all_results)

    print("\n===== ORDER-PRESERVED MERGED BALANCE SHEET =====")
    print(merged_bs.head(30))

    os.makedirs("output", exist_ok=True)
    merged_bs.to_csv("output/TCS_merged_balance_sheet.csv", index=False)

    print("\n✅ Exported: output/TCS_merged_balance_sheet.csv")