import os
import sys
import camelot
import pandas as pd
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname((current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Parser.quarterly_pnl import detect_quarterly_pnl_pages

# ============================================================
# Helpers
# ============================================================

def detect_data_start_row(df):
    """
    Detects the first PnL data row dynamically.
    """
    SECTION_HEADERS = {
        "consolidated statement of profit and loss"
    }

    for i in range(len(df)):
        first_col = str(df.iloc[i, 0]).strip().lower()

        # Skip empty / nan rows
        if not first_col or first_col == "nan":
            continue

        # Skip section headers
        if first_col in SECTION_HEADERS:
            continue

        # Check if numeric data exists in row
        row_vals = df.iloc[i, 1:].astype(str)

        if row_vals.str.contains(r"\d", regex=True).any():
            return i

    return None


def extract_unit_from_df(df):
    """
    Extract unit like '(₹ crore)' from top rows.
    """
    for i in range(min(3, len(df))):
        row_text = " ".join(df.iloc[i].astype(str).tolist()).lower()
        if "crore" in row_text:
            return row_text.strip()
    return None


def build_pnl_columns(df):
    # Find first row that looks like a header (contains 'Note' or 'year ended')
    header_row_idx = None
    for i in range(5):
        row_text = " ".join(df.iloc[i].astype(str)).lower()
        if "three month period ended " in row_text or "year ended" in row_text:
            header_row_idx = i
            break

    if header_row_idx is None:
        return [""] * df.shape[1]

    header_1 = df.iloc[header_row_idx].fillna("").astype(str)
    header_2 = df.iloc[header_row_idx + 1].fillna("").astype(str)

    # FIX 1: added missing commas — "₹ crore" and "lakhs" were silently
    # concatenated into "₹ crorelakhs" by Python's implicit string joining.
    SECTION_HEADERS = {
        "consolidated statement of profit and loss",
        "crore",
        "₹ crore",
        "lakhs",
        "₹ lakhs",
    }

    columns = []
    for h1, h2 in zip(header_1, header_2):
        h1, h2 = h1.strip(), h2.strip()

        if h1.lower() in SECTION_HEADERS:
            columns.append("")
        elif h1 and h2:
            columns.append(f"{h1} {h2}")
        elif h1:
            columns.append(h1)
        elif h2:
            columns.append(h2)
        else:
            columns.append("")

    return columns


def detect_data_columns(df, start_row):
    data_cols = []
    for i in range(df.shape[1]):
        col_vals = df.iloc[start_row:, i].astype(str)
        if col_vals.str.contains(r"\d", regex=True).any():
            data_cols.append(i)
    return data_cols


def align_headers_to_data(columns, data_cols):
    header_map = {}
    data_iter = iter(data_cols)

    for col_name in columns:
        if col_name.strip():
            try:
                header_map[next(data_iter)] = col_name
            except StopIteration:
                break
    return header_map


def split_particulars_and_note(text):
    """
    'Revenue from operations12'  -> ('Revenue from operations', '12')
    'Cost of software15(a)'      -> ('Cost of software', '15(a)')
    """
    if pd.isna(text):
        return text, None

    text = str(text).strip()
    match = re.search(r"(.*?)(\d+\s*\(?[a-zA-Z]?\)?)$", text)
    if match:
        particulars = match.group(1).strip()
        note = match.group(2).replace(" ", "")
        return particulars, note

    return text, None


def to_float(x):
    if pd.isna(x):
        return None
    x = (
        str(x)
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )
    return float(x) if re.match(r"^-?\d+(\.\d+)?$", x) else None


# ============================================================
# MAIN P&L PARSER
# ============================================================

def camelot_parser_pnl(path_pdf):

    page_numbers = detect_quarterly_pnl_pages(path_pdf)
    if not page_numbers:
        print("No P&L pages detected.")
        return {}

    print(f"Detected P&L pages: {page_numbers}")

    all_results = {}
    for page_number in page_numbers:
        tables = camelot.read_pdf(
            path_pdf,
            pages=str(page_number),
            flavor="stream",
            edge_tol=80,
            row_tol=6,
            column_tol=5,
            strip_text="\n"
        )
        print(f"[DEBUG] Page {page_number}: Camelot found {len(tables)} tables")

        # FIX 2: was `raise ValueError` — crashes entire run if one page has
        # no table. Changed to warning + skip so other pages still process.
        if len(tables) == 0:
            print(f"⚠️  Page {page_number}: No tables detected, skipping page.")
            continue

        structured_tables = []

        for idx, t in enumerate(tables):
            df = t.df

            # FIX 3: added debug print at shape guard — previously silent skip
            if df.shape[0] < 6 or df.shape[1] < 3:
                print(f"[DEBUG] Page {page_number}, Table {idx}: Skipped — shape too small {df.shape}")
                continue

            try:
                # -----------------------------------
                # STEP 1: Extract UNIT (top-most)
                # -----------------------------------
                unit = extract_unit_from_df(df)

                # -----------------------------------
                # STEP 2: Build headers
                # -----------------------------------
                columns = build_pnl_columns(df)
                DATA_START_ROW = detect_data_start_row(df)

                # FIX 4: added debug print at data-start guard — previously silent skip
                if DATA_START_ROW is None:
                    print(f"[DEBUG] Page {page_number}, Table {idx}: Skipped — no data start row found")
                    continue

                print(f"[DEBUG] Page {page_number}, Table {idx}: Data starts at row {DATA_START_ROW}")

                data_cols = detect_data_columns(df, DATA_START_ROW)
                header_map = align_headers_to_data(columns, data_cols)

                # FIX 5: was a silent `continue`. Now warns and shows what
                # header_map actually contains so you can diagnose misalignment.
                if "Note" not in header_map.values():
                    print(f"[DEBUG] Page {page_number}, Table {idx}: Skipped — 'Note' not in headers. "
                          f"header_map = {header_map}")
                    continue

                # -----------------------------------
                # STEP 3: Extract Particulars
                # -----------------------------------
                particulars_raw = (
                    df.iloc[DATA_START_ROW:, 0]
                    .astype(str)
                    .str.strip()
                    .reset_index(drop=True)
                )

                data_df = (
                    df.iloc[DATA_START_ROW:, list(header_map.keys())]
                    .reset_index(drop=True)
                )
                data_df.columns = list(header_map.values())
                data_df.insert(0, "Particulars", particulars_raw)

                # -----------------------------------
                # STEP 4: Fix Note (embedded in text)
                # -----------------------------------
                new_particulars = []
                new_notes = []

                for val in data_df["Particulars"]:
                    p, n = split_particulars_and_note(val)
                    new_particulars.append(p)
                    new_notes.append(n)

                data_df["Particulars"] = new_particulars
                data_df["Note"] = new_notes

                # -----------------------------------
                # STEP 5: Data types
                # -----------------------------------
                data_df["Particulars"] = data_df["Particulars"].astype(str)
                data_df["Note"] = data_df["Note"].astype(str).replace("None", "").str.strip()

                for col in data_df.columns:
                    if col not in ["Particulars", "Note"]:
                        data_df[col] = data_df[col].apply(to_float)

                # -----------------------------------
                # STEP 6: Metadata (UNIT on top)
                # -----------------------------------
                data_df.attrs["unit"] = unit
                data_df.attrs["source_page"] = page_number
                data_df.attrs["table_index"] = idx

                structured_tables.append(data_df)
                print(f"✅ Page {page_number}, Table {idx}: Extracted successfully ({data_df.shape[0]} rows)")

            except Exception as e:
                print(f"⚠️  Skipping table {idx} on page {page_number}: {e}")

        if structured_tables:
            all_results[f"page_{page_number}"] = structured_tables
            print(f"✅ PAGE {page_number}: Extracted {len(structured_tables)} structured tables")

    return all_results


# ============================================================
# Example usage
# ============================================================

if __name__ == "__main__":
    pdf = "downloads/TCS/quarterly/TCS_Q1_2023.pdf"
    results = camelot_parser_pnl(pdf)

    # FIX 6: CSV export loop was indented one level too deep — it was
    # nested inside the print loop so it only ran for the last page.
    # Moved to the same level as the display loop.
    for page_key, tables in results.items():
        print(f"\nTables on {page_key}:")
        for idx, df in enumerate(tables):
            print(f"Table {idx} on {page_key}:")
            print(df.head(20))
            print("\n")

    for page_key, tables in results.items():
        for idx, df in enumerate(tables):
            csv_filename = f"{page_key}_table_{idx}.csv"
            df.to_csv(csv_filename, index=False)
            print(f"Exported {csv_filename}")