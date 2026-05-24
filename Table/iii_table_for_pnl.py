import os
import sys
import camelot
import pandas as pd
import re

# ------------------------------------------------------------
# Path setup
# ------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Parser.pnl import detect_pnl_pages


# ============================================================
# Helper functions
# ============================================================
def trim_above_notes_row(df):
    """
    Removes all junk rows ABOVE the Notes row.
    Returns trimmed DataFrame and notes_row index (reset).
    """

    notes_row = extract_row_of_notes(df)

    if notes_row is None:
        # If Notes not found, return original df
        return df.copy(), None

    trimmed_df = df.iloc[notes_row:].copy()
    trimmed_df = trimmed_df.reset_index(drop=True)

    return trimmed_df, 0



def detect_data_start_row(df):
    """
    Detects the first actual data row dynamically.
    """

    SECTION_HEADERS = {
        "particulars",
        "particular",
        "income"
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


def extract_statement_title(df):
    """
    Detect P&L statement title.
    """
    title = str(df.iloc[0, 0]).lower()
    if "consolidated statement of profit and loss" in title:
        return title.strip()
    return None

def extract_row_of_notes(df, max_scan=8):
    """
    Detect the row index containing 'Notes' / 'Note No.'
    Returns row index or None
    """

    NOTES_KEYWORDS = {
        "notes",
        "note",
        "note no",
        "note nos",
        "note number"
    }

    for i in range(min(max_scan, len(df))):
        row_text = " ".join(
            df.iloc[i].fillna("").astype(str)
        ).lower()

        # normalize broken words: n o t e s → notes
        row_text = re.sub(r"\s+", " ", row_text)

        if any(k in row_text for k in NOTES_KEYWORDS):
            return i

    return None

def split_particulars_and_notes(df):
    """
    Splits inline note numbers from Particulars column.
    Example:
      'Revenue from operations 23' → ('Revenue from operations', '23')
    """

    particulars = []
    notes = []

    for val in df.iloc[:, 0].astype(str):
        text = val.strip()

        # Match trailing note numbers like:
        # 'Revenue 23', 'Revenue (23)', 'Revenue - 23'
        match = re.search(r"(.*?)(?:\(|\s|-)?(\d{1,2})\)?$", text)

        if match:
            particulars.append(match.group(1).strip())
            notes.append(match.group(2))
        else:
            particulars.append(text)
            notes.append("")

    df.insert(1, "Notes", notes)
    df.iloc[:, 0] = particulars
    df.columns.values[0] = "Particulars"

    return df

def split_merged_fy_columns_by_decimal(df):
    """
    Split merged data values within FY columns.
    Handles cases where column headers are separate but data is merged.
    Example: FY_2025 column contains "27,217.5218,046.19"
    """

    fy_cols = [c for c in df.columns if c.startswith("FY_")]

    if len(fy_cols) == 0:
        print(f"[DEBUG] No FY columns found. Skipping split.")
        return df

    # Pattern = ONE complete accounting number with EXACTLY 2 decimals
    # Matches: 27,217.52 or (123.45) or -456.78
    # Does NOT match: 1,234.567 (more than 2 decimals)
    pattern = r"\(?-?\d[\d,]*\.\d{2}\)?"

    # Check if any FY column has merged data and track which one
    has_merged_data = False
    merged_col = None
    
    for col in fy_cols:
        # Sample first few non-empty values
        sample_vals = df[col].astype(str).replace('', 'nan').replace('nan', pd.NA).dropna().head(5)
        
        for val in sample_vals:
            # Find all decimal numbers in the value
            matches = re.findall(pattern, str(val))
            if len(matches) >= 2:  # Found multiple numbers merged
                has_merged_data = True
                merged_col = col
                print(f"[DEBUG] Detected merged data in column '{col}': '{val}'")
                break
        
        if has_merged_data:
            break

    if not has_merged_data:
        print(f"[DEBUG] Found {len(fy_cols)} FY columns: {fy_cols}. No merged data detected.")
        return df

    # If we have 2 FY columns and data is merged, split the column with merged data
    if len(fy_cols) == 2:
        fy_col = merged_col  # Split the column that has merged data
        print(f"[DEBUG] Splitting merged data in column '{fy_col}'")
        
        left_vals = []
        right_vals = []

        for val in df[fy_col].astype(str):
            text = val.strip()
            
            # Skip empty or NaN values
            if not text or text.lower() == 'nan':
                left_vals.append("")
                right_vals.append("")
                continue

            match = re.search(pattern, text)

            if match:
                left_vals.append(match.group().strip())
                right_vals.append(text[match.end():].strip())
            else:
                # If no decimal number found, keep original in left column
                left_vals.append(text)
                right_vals.append("")

        # Debug: Show what we're splitting
        print(f"[DEBUG] Sample splits from '{fy_col}':")
        for i in range(min(5, len(left_vals))):
            if left_vals[i] or right_vals[i]:
                print(f"  '{df[fy_col].iloc[i]}' -> Left: '{left_vals[i]}' | Right: '{right_vals[i]}'")

        # Determine which column should get which values
        # If FY_2024 has merged data like "27,217.5218,046.19"
        # Then: left (27,217.52) is FY_2025, right (18,046.19) is FY_2024
        
        if merged_col == fy_cols[1]:  # If second column (FY_2024) has merged data
            # The first number is current year, second is previous year
            df[fy_cols[0]] = left_vals   # FY_2025 gets first number
            df[fy_cols[1]] = right_vals  # FY_2024 gets second number
        else:  # If first column (FY_2025) has merged data
            # The first number is current year, second is previous year
            df[fy_cols[0]] = left_vals   # FY_2025 gets first number
            df[fy_cols[1]] = right_vals  # FY_2024 gets second number

        return df

    # If only 1 FY column with merged data, split it into two
    elif len(fy_cols) == 1:
        fy_col = fy_cols[0]
        
        try:
            base_year = int(fy_col.replace("FY_", ""))
        except ValueError:
            return df

        fy_current = f"FY_{base_year}"
        fy_previous = f"FY_{base_year - 1}"

        left_vals = []
        right_vals = []

        for val in df[fy_col].astype(str):
            text = val.strip()
            
            if not text or text.lower() == 'nan':
                left_vals.append("")
                right_vals.append("")
                continue

            match = re.search(pattern, text)

            if match:
                left_vals.append(match.group().strip())
                right_vals.append(text[match.end():].strip())
            else:
                left_vals.append(text)
                right_vals.append("")

        # Assign new columns
        df[fy_current] = left_vals
        df[fy_previous] = right_vals

        # Drop merged column
        df.drop(columns=[fy_col], inplace=True)

        # Safe column order
        ordered_cols = []
        if "Particulars" in df.columns:
            ordered_cols.append("Particulars")
        if "Notes" in df.columns:
            ordered_cols.append("Notes")

        ordered_cols.extend([fy_current, fy_previous])

        return df[ordered_cols]

    return df

# def clean_and_standardize_header(df):
#     """
#     Standardizes headers even when Notes are inline with Particulars.
#     """

#     # --------------------------------------------------
#     # Extract years from top rows
#     # --------------------------------------------------
#     header_text = " ".join(
#         df.iloc[:3].fillna("").astype(str).values.flatten()
#     ).lower()

#     years = re.findall(r"(20\d{2})", header_text)
#     years = list(dict.fromkeys(years))  # preserve order

#     if not years:
#         return df, list(df.columns)

#     columns = ["Particulars"] + [f"FY_{y}" for y in years]

#     # --------------------------------------------------
#     # Remove header rows (keep only data rows)
#     # --------------------------------------------------
#     df = df.iloc[2:].reset_index(drop=True)
#     df = df.iloc[:, :len(columns)]
#     df.columns = columns

#     # --------------------------------------------------
#     # Split inline Notes
#     # --------------------------------------------------
#     df = split_particulars_and_notes(df)

#     return df, df.columns.tolist()

def clean_and_standardize_header(df):
    """
    Standardizes headers by identifying and dropping the Note column structural column
    BEFORE mapping financial years to prevent column alignment shifting.
    """
    # 1. Identify which raw column index contains the "Note" text header
    note_col_idx = None
    for col_idx in range(df.shape[1]):
        col_text = " ".join(df.iloc[:3, col_idx].fillna("").astype(str)).lower()
        if any(k in col_text for k in ["note", "notes", "note no", "note no."]):
            note_col_idx = col_idx
            break

    # 2. Extract years from the header rows across all columns
    header_text = " ".join(
        df.iloc[:3].fillna("").astype(str).values.flatten()
    ).lower()
    years = re.findall(r"(20\d{2})", header_text)
    years = list(dict.fromkeys(years))  # Deduplicate while preserving chronological order

    # 3. If a distinct Note column was found, drop it from the raw DataFrame completely
    if note_col_idx is not None:
        print(f"[FIX] Removing structural raw Note column at index {note_col_idx}")
        df = df.drop(columns=[df.columns[note_col_idx]])
        df = df.reset_index(drop=True)

    # 4. Enforce clean standardized schema: Particulars followed by found fiscal years
    columns = ["Particulars"] + [f"FY_{y}" for y in years]

    # 5. Crop rows to clear out structural text headers and match width
    df = df.iloc[2:].reset_index(drop=True)
    df = df.iloc[:, :len(columns)]
    df.columns = columns

    # 6. Run safe cleanup for remaining inline/pasted numbers
    df = split_particulars_and_notes(df)

    return df, df.columns.tolist()

def build_columns(df):
    """
    Build table columns using the Notes row as anchor.
    """

    notes_row = extract_row_of_notes(df)
    print(f"Row of note: {notes_row}")

    if notes_row is None:
        return [""] * df.shape[1]

    header_1 = df.iloc[notes_row].fillna("").astype(str)

    if notes_row + 1 < len(df):
        header_2 = df.iloc[notes_row + 1].fillna("").astype(str)
    else:
        header_2 = [""] * df.shape[1]

    columns = []

    for h1, h2 in zip(header_1, header_2):
        h1, h2 = h1.strip(), h2.strip()

        # Ignore standalone "Notes" column name
        if h1.lower() in {"notes", "note"}:
            columns.append("Notes")
        elif h1 and h2:
            columns.append(f"{h1} {h2}")
        elif h1:
            columns.append(h1)
        elif h2:
            columns.append(h2)
        else:
            columns.append("")

    return columns

 


# ============================================================
# Camelot Parser
# ============================================================

def camelot_parser(path_pdf):
    """
    Extract structured P&L tables from detected P&L pages.
    """

    pnl_pages = detect_pnl_pages(path_pdf)
    print(f"Debug page no: {pnl_pages}")

    all_results = {}

    for page_number in pnl_pages:
        tables = camelot.read_pdf(
            path_pdf,
            pages=str(page_number),
            flavor="stream",
            edge_tol=80,
            row_tol=6,
            column_tol=5,
            split_text=False,
            strip_text="\n"
        )

        print(f"[DEBUG] Page {page_number}: Camelot found {len(tables)} tables")

        if not tables:
            continue

        structured_tables = []

        for idx, t in enumerate(tables):
            df = t.df

            # --------------------------------------------
            # Basic junk filter
            # --------------------------------------------
            if df.shape[0] < 6 or df.shape[1] < 3:
                continue

            print(f"[DEBUG] Page {page_number}, Table {idx}: shape {df.shape}")

            try:
                # --------------------------------------------
                # STEP 1: Extract title (BEFORE trimming)
                # --------------------------------------------
                title = extract_statement_title(df)
                print(f"[DEBUG] Table {idx}: title = {title}")
                print(f"[DEBUG] Original df shape: {df.shape}")
                print(f"[DEBUG] Original first 3 rows:")
                print(df.head(3))

                # --------------------------------------------
                # STEP 2: Remove junk rows above Notes
                # --------------------------------------------
                df, notes_row = trim_above_notes_row(df)

                if notes_row is not None:
                    df, columns = clean_and_standardize_header(df)
                else:
                    print(f"[DEBUG] Table {idx}: Notes inline with particulars")
                    df, columns = clean_and_standardize_header(df)

                
                df = split_merged_fy_columns_by_decimal(df)

                print(f"[DEBUG] Table {idx}: standardized columns = {df.columns.tolist()}")

                if df.empty or len(df.columns) < 3:
                    continue

                # --------------------------------------------
                # STEP 4: Store result
                # --------------------------------------------
                structured_tables.append({
                    "title": title,
                    "page": page_number,
                    "table_index": idx,
                    "data": df
                })

            except Exception as e:
                print(f"[ERROR] Page {page_number}, Table {idx}: {e}")
                import traceback
                traceback.print_exc()

        if structured_tables:
            all_results[page_number] = structured_tables

    return all_results

#Example usage:
# Example usage:
if __name__ == "__main__":
    pdf = "downloads/KAYNES/annual/KAYNES_Annual_2024.pdf"
    # page_num = 182

    # MUST be a list
    results = camelot_parser(pdf)

    for page_key, tables in results.items():
        print(f"\n{'='*60}")
        print(f"Tables on page {page_key}:")
        print(f"{'='*60}")
        for idx, table in enumerate(tables):
            print(f"\nTable {idx}")
            print("Title:", table["title"])
            print("\nColumns:", table["data"].columns.tolist())
            print("\nData:")
            print(table["data"].head(20))

