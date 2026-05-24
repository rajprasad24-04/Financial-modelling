# import os
# import sys
# import logging
# import re

# import pandas as pd

# # -------------------------------------------------
# # Path setup
# # -------------------------------------------------
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir)
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# from Integration.loop_pnl import parse_all_pdfs

# # -------------------------------------------------
# # Logging
# # -------------------------------------------------
# logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
# logger = logging.getLogger(__name__)


# # =================================================
# # Helpers
# # =================================================
# def _to_numeric(value) -> float | None:
#     """
#     Coerces a single cell to a numeric float.

#     Handles common PDF artefacts:
#         "1,23,456"   ->  123456.0
#         "(500)"      ->  -500.0        (parentheses = negative)
#         "—" / "-"    ->  NaN
#         already int/float -> unchanged
#     """
#     if isinstance(value, (int, float)):
#         return float(value)

#     if not isinstance(value, str):
#         return None                        # unknown type -> None (becomes NaN)

#     value = value.strip()

#     if value in ("", "—", "-", "–", "N/A", "nil", "Nil"):
#         return None

#     # parentheses denote negative:  (500) -> -500
#     negative = value.startswith("(") and value.endswith(")")
#     if negative:
#         value = value[1:-1]

#     # strip commas (Indian or international)
#     value = value.replace(",", "")

#     try:
#         num = float(value)
#         return -num if negative else num
#     except ValueError:
#         logger.warning("Could not parse value to numeric: '%s'", value)
#         return None


# # =================================================
# # STEP 1: Convert ONE PnL table to LONG format
# # =================================================
# def pnl_table_to_long(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Converts a single P&L DataFrame (wide) to long format:
#         Particulars | Year | Value

#     - Handles both 'Particulars' and 'Particular' column names.
#     - Extracts the 4-digit year from each column header.
#     - Coerces every Value cell to numeric.
#     """
#     df = df.copy()

#     # Check for both 'Particulars' and 'Particular' column names
#     particulars_col = None
#     if "Particulars" in df.columns:
#         particulars_col = "Particulars"
#     elif "Particular" in df.columns:
#         particulars_col = "Particular"
#         # Rename to standardize
#         df = df.rename(columns={"Particular": "Particulars"})
#     else:
#         logger.warning("Skipping table: Neither 'Particulars' nor 'Particular' column found. Columns: %s", list(df.columns))
#         return pd.DataFrame(columns=["Particulars", "Year", "Value"])

#     # Drop Notes column if present
#     if "Notes" in df.columns:
#         df = df.drop(columns=["Notes"])

#     records: list[dict] = []

#     for col in df.columns:
#         if col == "Particulars":
#             continue

#         match = re.search(r"\d{4}", str(col))
#         if not match:
#             logger.warning("Skipping column '%s': no 4-digit year found.", col)
#             continue

#         year = int(match.group())

#         for _, row in df.iterrows():
#             records.append({
#                 "Particulars": row["Particulars"],
#                 "Year":        year,
#                 "Value":       _to_numeric(row[col]),
#             })

#     return pd.DataFrame(records)


# # =================================================
# # STEP 2: Stack all tables & build master order
# # =================================================
# def collect_pnl_long_with_progressive_order(
#     all_results: dict,
# ) -> tuple[pd.DataFrame, list[str]]:
#     """
#     Iterates over every parsed table, stacks them into one long DataFrame,
#     and builds a *master_order* list that preserves the evolving row order
#     across annual reports (new line-items are slotted relative to their
#     neighbours in the statement they first appear in).

#     Returns:
#         long_df      : columns [Particulars, Year, Value]
#         master_order : ordered list of unique Particulars strings
#     """
#     all_long: list[pd.DataFrame] = []
#     master_order: list[str] = []

#     for pdf_name, page_data in all_results.items():
#         for page_key, tables_list in page_data.items():
#             # tables_list is a list of dicts with keys: 'title', 'page', 'table_index', 'data'
#             for table_dict in tables_list:
#                 # Extract the actual DataFrame from the 'data' key
#                 df = table_dict.get("data")
                
#                 if df is None or not isinstance(df, pd.DataFrame):
#                     logger.warning(
#                         "[%s / %s] Skipping table: 'data' key not found or not a DataFrame.",
#                         pdf_name, page_key,
#                     )
#                     continue

#                 # Check for both 'Particulars' and 'Particular' column names
#                 if "Particulars" not in df.columns and "Particular" not in df.columns:
#                     logger.warning(
#                         "[%s / %s] Skipping table without 'Particulars' or 'Particular' column.",
#                         pdf_name, page_key,
#                     )
#                     continue

#                 # Standardize column name
#                 if "Particular" in df.columns and "Particulars" not in df.columns:
#                     df = df.rename(columns={"Particular": "Particulars"})

#                 particulars = list(df["Particulars"])

#                 # ---------- evolve master_order ----------
#                 for idx, p in enumerate(particulars):
#                     if p in master_order:
#                         continue                           # already tracked

#                     # nearest previous row already in master_order
#                     prev_known = next(
#                         (particulars[j] for j in range(idx - 1, -1, -1) if particulars[j] in master_order),
#                         None,
#                     )
#                     # nearest next row already in master_order
#                     next_known = next(
#                         (particulars[j] for j in range(idx + 1, len(particulars)) if particulars[j] in master_order),
#                         None,
#                     )

#                     if prev_known is not None:
#                         insert_at = master_order.index(prev_known) + 1
#                     elif next_known is not None:
#                         insert_at = master_order.index(next_known)
#                     else:
#                         # No overlap with master_order yet — append to end.
#                         insert_at = len(master_order)

#                     master_order.insert(insert_at, p)

#                 # ---------- melt to long ----------
#                 long_df = pnl_table_to_long(df)
#                 if not long_df.empty:
#                     all_long.append(long_df)

#     if not all_long:
#         return pd.DataFrame(columns=["Particulars", "Year", "Value"]), []

#     return pd.concat(all_long, ignore_index=True), master_order


# # =================================================
# # STEP 3: Pivot & produce final wide P&L
# # =================================================
# def horizontal_stack_pnl(all_results: dict) -> pd.DataFrame:
#     """
#     Produces the final horizontally stacked P&L with year columns sorted
#     in ascending order and rows in the progressive statement order.

#     Duplicate (Particulars, Year) pairs are warned about; the *last*
#     occurrence wins (typically the most recent / restated figure).
#     """
#     long_df, master_order = collect_pnl_long_with_progressive_order(all_results)

#     if long_df.empty:
#         logger.info("No data collected — returning empty DataFrame.")
#         return long_df

#     # ---------- warn on duplicates ----------
#     dup_mask = long_df.duplicated(subset=["Particulars", "Year"], keep=False)
#     if dup_mask.any():
#         dup_pairs = (
#             long_df.loc[dup_mask]
#             .drop_duplicates(subset=["Particulars", "Year"])[["Particulars", "Year"]]
#         )
#         for _, row in dup_pairs.iterrows():
#             logger.warning(
#                 "Duplicate entry — Particulars='%s', Year=%d. Keeping last occurrence.",
#                 row["Particulars"], row["Year"],
#             )

#     # ---------- pivot (keep=last via drop_duplicates) ----------
#     deduped = long_df.drop_duplicates(subset=["Particulars", "Year"], keep="last")

#     merged = (
#         deduped
#         .pivot_table(
#             index="Particulars",
#             columns="Year",
#             values="Value",
#             aggfunc="first",       # safe now: exactly one row per key
#             dropna=False,
#         )
#         .reset_index()
#     )

#     # ---------- enforce progressive row order ----------
#     merged = (
#         merged
#         .set_index("Particulars")
#         .reindex(master_order)
#         .reset_index()
#     )

#     # ---------- sort year columns ascending ----------
#     year_cols = sorted(c for c in merged.columns if isinstance(c, (int, float)))
#     merged = merged[["Particulars"] + year_cols]

#     return merged


# # =================================================
# # Entry-point
# # =================================================
# if __name__ == "__main__":
#     # parse_all_pdfs returns a single dict: { "ticker/file.pdf": page_data, ... }
#     all_results = parse_all_pdfs(tickers=["TCS"])

#     final_pnl = horizontal_stack_pnl(all_results)

#     print("\n===== ORDER-PRESERVED MERGED P&L =====")
#     print(final_pnl.head(30))

#     os.makedirs("output", exist_ok=True)
#     output_path = "output/TCS_merged_pnl_sheet.csv"
#     final_pnl.to_csv(output_path, index=False)

#     print(f"\n✅ Exported: {output_path}")



import os
import sys
import logging
import re

import pandas as pd

# -------------------------------------------------
# Path setup
# -------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Integration.loop_pnl import parse_all_pdfs

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# =================================================
# Helpers
# =================================================
def _to_numeric(value) -> float | None:
    """
    Coerces a single cell to a numeric float.

    Handles common PDF artefacts:
        "1,23,456"   ->  123456.0
        "(500)"      ->  -500.0        (parentheses = negative)
        "—" / "-"    ->  NaN
        already int/float -> unchanged
    """
    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        return None                        # unknown type -> None (becomes NaN)

    value = value.strip()

    if value in ("", "—", "-", "–", "N/A", "nil", "Nil"):
        return None

    # parentheses denote negative:  (500) -> -500
    negative = value.startswith("(") and value.endswith(")")
    if negative:
        value = value[1:-1]

    # strip commas (Indian or international)
    value = value.replace(",", "")

    try:
        num = float(value)
        return -num if negative else num
    except ValueError:
        logger.warning("Could not parse value to numeric: '%s'", value)
        return None


# =================================================
# STEP 1: Convert ONE PnL table to LONG format
# =================================================
def pnl_table_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts a single P&L DataFrame (wide) to long format:
        Particulars | Year | Value

    - Handles both 'Particulars' and 'Particular' column names.
    - Extracts the 4-digit year from each column header.
    - Coerces every Value cell to numeric.
    """
    df = df.copy()

    # Check for both 'Particulars' and 'Particular' column names
    particulars_col = None
    if "Particulars" in df.columns:
        particulars_col = "Particulars"
    elif "Particular" in df.columns:
        particulars_col = "Particular"
        # Rename to standardize
        df = df.rename(columns={"Particular": "Particulars"})
    else:
        logger.warning("Skipping table: Neither 'Particulars' nor 'Particular' column found. Columns: %s", list(df.columns))
        return pd.DataFrame(columns=["Particulars", "Year", "Value"])

    # 🔥 FIX: Dynamically find and drop any variation of the Note/Notes column
    cols_to_drop = [
        c for c in df.columns 
        if str(c).strip().lower() in ["note", "notes", "note no", "note no.", "note nos", "note number"]
    ]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        logger.info("Dropped note column(s): %s", cols_to_drop)

    records: list[dict] = []

    for col in df.columns:
        if col == "Particulars":
            continue

        match = re.search(r"\d{4}", str(col))
        if not match:
            logger.warning("Skipping column '%s': no 4-digit year found.", col)
            continue

        year = int(match.group())

        for _, row in df.iterrows():
            records.append({
                "Particulars": row["Particulars"],
                "Year":        year,
                "Value":       _to_numeric(row[col]),
            })

    return pd.DataFrame(records)


# =================================================
# STEP 2: Stack all tables & build master order
# =================================================
def collect_pnl_long_with_progressive_order(
    all_results: dict,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Iterates over every parsed table, stacks them into one long DataFrame,
    and builds a *master_order* list that preserves the evolving row order
    across annual reports (new line-items are slotted relative to their
    neighbours in the statement they first appear in).

    Returns:
        long_df      : columns [Particulars, Year, Value]
        master_order : ordered list of unique Particulars strings
    """
    all_long: list[pd.DataFrame] = []
    master_order: list[str] = []

    for pdf_name, page_data in all_results.items():
        for page_key, tables_list in page_data.items():
            # tables_list is a list of dicts with keys: 'title', 'page', 'table_index', 'data'
            for table_dict in tables_list:
                # Extract the actual DataFrame from the 'data' key
                df = table_dict.get("data")
                
                if df is None or not isinstance(df, pd.DataFrame):
                    logger.warning(
                        "[%s / %s] Skipping table: 'data' key not found or not a DataFrame.",
                        pdf_name, page_key,
                    )
                    continue

                # Check for both 'Particulars' and 'Particular' column names
                if "Particulars" not in df.columns and "Particular" not in df.columns:
                    logger.warning(
                        "[%s / %s] Skipping table without 'Particulars' or 'Particular' column.",
                        pdf_name, page_key,
                    )
                    continue

                # Standardize column name
                if "Particular" in df.columns and "Particulars" not in df.columns:
                    df = df.rename(columns={"Particular": "Particulars"})

                particulars = list(df["Particulars"])

                # ---------- evolve master_order ----------
                for idx, p in enumerate(particulars):
                    if p in master_order:
                        continue                           # already tracked

                    # nearest previous row already in master_order
                    prev_known = next(
                        (particulars[j] for j in range(idx - 1, -1, -1) if particulars[j] in master_order),
                        None,
                    )
                    # nearest next row already in master_order
                    next_known = next(
                        (particulars[j] for j in range(idx + 1, len(particulars)) if particulars[j] in master_order),
                        None,
                    )

                    if prev_known is not None:
                        insert_at = master_order.index(prev_known) + 1
                    elif next_known is not None:
                        insert_at = master_order.index(next_known)
                    else:
                        # No overlap with master_order yet — append to end.
                        insert_at = len(master_order)

                    master_order.insert(insert_at, p)

                # ---------- melt to long ----------
                long_df = pnl_table_to_long(df)
                if not long_df.empty:
                    all_long.append(long_df)

    if not all_long:
        return pd.DataFrame(columns=["Particulars", "Year", "Value"]), []

    return pd.concat(all_long, ignore_index=True), master_order


# =================================================
# STEP 3: Pivot & produce final wide P&L
# =================================================
def horizontal_stack_pnl(all_results: dict) -> pd.DataFrame:
    """
    Produces the final horizontally stacked P&L with year columns sorted
    in ascending order and rows in the progressive statement order.

    Duplicate (Particulars, Year) pairs are warned about; the *last*
    occurrence wins (typically the most recent / restated figure).
    """
    long_df, master_order = collect_pnl_long_with_progressive_order(all_results)

    if long_df.empty:
        logger.info("No data collected — returning empty DataFrame.")
        return long_df

    # ---------- warn on duplicates ----------
    dup_mask = long_df.duplicated(subset=["Particulars", "Year"], keep=False)
    if dup_mask.any():
        dup_pairs = (
            long_df.loc[dup_mask]
            .drop_duplicates(subset=["Particulars", "Year"])[["Particulars", "Year"]]
        )
        for _, row in dup_pairs.iterrows():
            logger.warning(
                "Duplicate entry — Particulars='%s', Year=%d. Keeping last occurrence.",
                row["Particulars"], row["Year"],
            )

    # ---------- pivot (keep=last via drop_duplicates) ----------
    deduped = long_df.drop_duplicates(subset=["Particulars", "Year"], keep="last")

    merged = (
        deduped
        .pivot_table(
            index="Particulars",
            columns="Year",
            values="Value",
            aggfunc="first",       # safe now: exactly one row per key
            dropna=False,
        )
        .reset_index()
    )

    # ---------- enforce progressive row order ----------
    merged = (
        merged
        .set_index("Particulars")
        .reindex(master_order)
        .reset_index()
    )

    # ---------- sort year columns ascending ----------
    year_cols = sorted(c for c in merged.columns if isinstance(c, (int, float)))
    merged = merged[["Particulars"] + year_cols]

    return merged


# =================================================
# Entry-point
# =================================================
if __name__ == "__main__":
    # parse_all_pdfs returns a single dict: { "ticker/file.pdf": page_data, ... }
    all_results = parse_all_pdfs(tickers=["TCS"])

    final_pnl = horizontal_stack_pnl(all_results)

    print("\n===== ORDER-PRESERVED MERGED P&L =====")
    print(final_pnl.head(30))

    os.makedirs("output", exist_ok=True)
    output_path = "output/TCS_merged_pnl_sheet.csv"
    final_pnl.to_csv(output_path, index=False)

    print(f"\n✅ Exported: {output_path}")