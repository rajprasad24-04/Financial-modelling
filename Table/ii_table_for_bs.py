# import os
# import sys
# import camelot
# import pandas as pd
# import re
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname((current_dir))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# from Parser.bs import detect_bs_pages



# # ============================================================
# # Helper functions
# # ============================================================

# def detect_data_start_row(df):
#     """
#     Detects the first Balance Sheet data row dynamically.
#     """

#     SECTION_HEADERS = {
#         "assets",
#         "liabilities",
#         "equity",
#         "non-current assets",
#         "current assets",
#         "total assets",
#         "total non-current assets",
#         "total current assets",
#     }

#     for i in range(len(df)):
#         first_col = str(df.iloc[i, 0]).strip().lower()

#         # Skip empty / nan rows
#         if not first_col or first_col == "nan":
#             continue

#         # Skip section headers
#         if first_col in SECTION_HEADERS:
#             continue

#         # Check if numeric data exists in row
#         row_vals = df.iloc[i, 1:].astype(str)

#         if row_vals.str.contains(r"\d", regex=True).any():
#             return i

#     return None

# def extract_statement_title(df):
#     return str(df.iloc[0, 0]).strip()


# def extract_unit(df):
#     row = df.iloc[1].dropna().astype(str).str.strip()
#     return row.values[0] if len(row) > 0 else None



# def build_columns(df):
#     # Find first row that looks like a header (contains 'Note' or 'As at')
#     header_row_idx = None
#     for i in range(5):
#         row_text = " ".join(df.iloc[i].astype(str)).lower()
#         if "note" in row_text or "as at" in row_text:
#             header_row_idx = i
#             break

#     if header_row_idx is None:
#         return [""] * df.shape[1]

#     header_1 = df.iloc[header_row_idx].fillna("").astype(str)
#     header_2 = df.iloc[header_row_idx + 1].fillna("").astype(str)

#     SECTION_HEADERS = {"assets", "liabilities", "equity"}

#     columns = []
#     for h1, h2 in zip(header_1, header_2):
#         h1, h2 = h1.strip(), h2.strip()

#         if h1.lower() in SECTION_HEADERS:
#             columns.append("")
#         elif h1 and h2:
#             columns.append(f"{h1} {h2}")
#         elif h1:
#             columns.append(h1)
#         elif h2:
#             columns.append(h2)
#         else:
#             columns.append("")

#     return columns

# def detect_data_columns(df, start_row):
#     data_cols = []
#     for i in range(1 , df.shape[1]):
#         col_vals = df.iloc[start_row:, i].astype(str)
#         if col_vals.str.contains(r"\d{2,}", regex=True).any():
#             data_cols.append(i)
#     return data_cols


# def align_headers_to_data(columns, data_cols):
#     header_map = {}
#     data_iter = iter(data_cols)

#     for col_name in columns:
#         if not col_name.strip():
#             continue

#         # 🔥 Skip Particulars explicitly
#         if col_name.strip().lower() == "particulars":
#             continue

#         try:
#             header_map[next(data_iter)] = col_name
#         except StopIteration:
#             break

#     return header_map


# def to_float(x):
#     if pd.isna(x):
#         return None
#     x = str(x).replace(",", "").strip()
#     return float(x) if re.match(r"^-?\d+(\.\d+)?$", x) else None


# # ============================================================
# # Main Camelot Parser
# # ============================================================

# def camelot_parser(path_pdf):
#     """
#     Using detected Balance sheet pages, we extract page no. and give it as an input
#     """

#     bs_pages = detect_bs_pages(path_pdf)  
#     if not bs_pages:
#         print("No Balance Sheet pages detected.")
#         return {}
    
#     print(f"Detected Balance Sheet pages: {bs_pages}")

#     all_results = {}

#     for page_number in bs_pages:
#         tables = camelot.read_pdf(
#             path_pdf,
#             pages=str(page_number),
#             flavor="stream",
#             edge_tol=80,
#             row_tol=6,
#             column_tol=5,
#             split_text=False,
#             strip_text="\n"
#         )

#         print(f"[DEBUG] Page {page_number}: Camelot found {len(tables)} tables")

#         if len(tables) == 0:
#             raise ValueError(f"No tables detected on page {page_number}")

#         structured_tables = []

#         for idx, t in enumerate(tables):
#             df = t.df

#             # ----------------------------------------------------
#             # Basic junk filter
#             # ----------------------------------------------------
#             if df.shape[0] < 6 or df.shape[1] < 3:
#                 continue
#             print(f"[DEBUG] Page {page_number}, Table {idx}: shape {df.shape}")

#             try:
#             # ------------------------------------------------
#             # STEP 1: Extract metadata
#             # ------------------------------------------------
#                 title = extract_statement_title(df)
#                 unit = extract_unit(df)

#             # ------------------------------------------------
#             # STEP 2: Build header candidates
#             # ------------------------------------------------
#                 columns = build_columns(df)

#             # ------------------------------------------------
#             # STEP 3: Detect where numeric data exists
#             # ------------------------------------------------
#                 DATA_START_ROW = detect_data_start_row(df)
#                 if DATA_START_ROW is None:
#                     continue
#                 data_cols = detect_data_columns(df, DATA_START_ROW)

#                 if not data_cols:
#                     continue
                
#                 print(f"[DEBUG] Page {page_number}, Table {idx}: data columns detected at {data_cols}")
#             # ------------------------------------------------
#             # STEP 4: Align headers to shifted data
#             # ------------------------------------------------
#                 header_map = align_headers_to_data(columns, data_cols)

#                 if not header_map:
#                     continue
                
#                 print(f"[DEBUG] Page {page_number}, Table {idx}: header map {header_map}")
#             # ------------------------------------------------
#             # STEP 5: Extract Particulars (column 0)
#             # ------------------------------------------------
#                 particulars = (
#                     df.iloc[DATA_START_ROW:, 0]
#                     .astype(str)
#                     .str.strip()
#                     .reset_index(drop=True)
#                 )

#             # ------------------------------------------------
#             # STEP 6: Extract data columns
#             # ------------------------------------------------
#                 data_df = (
#                     df.iloc[DATA_START_ROW:, list(header_map.keys())]
#                     .reset_index(drop=True)
#                 )
#                 data_df.columns = list(header_map.values())

#             # Insert Particulars as first column
#                 if "Particulars" not in data_df.columns:
#                     data_df.insert(0, "Particulars", particulars)

#             # ------------------------------------------------
#             # 🔥 FILTER: keep only MAIN Balance Sheet table
#             # ------------------------------------------------
#                 if "Note" not in data_df.columns:
#                     continue
                
#                 print(f"[DEBUG] Page {page_number}, Table {idx}: Passed main BS table filter")
#             # ------------------------------------------------
#             # STEP 7: Enforce dtypes
#             # ------------------------------------------------
#             # Particulars → string
#                 data_df["Particulars"] = (
#                     data_df["Particulars"]
#                     .astype(str)
#                     .str.strip()
#                 )

#             # Note → string (if present)
#                 if "Note" in data_df.columns:
#                     data_df["Note"] = (
#                         data_df["Note"]
#                         .astype(str)
#                         .str.strip()
#                     )

#             # Value columns → float
#                 for col in data_df.columns:
#                     if col not in ["Particulars", "Note"]:
#                         data_df[col] = data_df[col].apply(to_float)

#             # ------------------------------------------------
#             # STEP 8: Attach metadata
#             # ------------------------------------------------
#                 data_df.attrs["title"] = title
#                 data_df.attrs["unit"] = unit
#                 data_df.attrs["source_page"] = page_number
#                 data_df.attrs["table_index"] = idx

#                 structured_tables.append(data_df)

#             except Exception as e:
#                 print(f"⚠️ Skipping table {idx} on page {page_number}: {e}")
    
#         if structured_tables:
#             all_results[f"page_{page_number}"] = structured_tables
#             print(f"✅ PAGE {page_number}: Extracted {len(structured_tables)} structured tables")
#             print(type(all_results))
#     return all_results

# #Example usage:
# if __name__ == "__main__":
#     pdf = "downloads/KAYNES/annual/KAYNES_Annual_2023.pdf"
#     # page_num = 191
#     results = camelot_parser(pdf)
#     for page_key, tables in results.items():
#         print(f"\nTables on {page_key}:")
#         for idx, df in enumerate(tables):
#             print(f"Table {idx} on {page_key}:")
#             print(df.head(20))    
#             print("\n")   

#     #exported csvs
#         for idx, df in enumerate(tables):
#             csv_filename = f"{page_key}_table_{idx}.csv"
#             df.to_csv(csv_filename, index=False)
#             print(f"Exported {csv_filename}")



import os
import sys
import camelot
import pandas as pd
import re
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname((current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Parser.bs import detect_bs_pages



# ============================================================
# Helper functions
# ============================================================

def detect_data_start_row(df):
    """
    Detects the first Balance Sheet data row dynamically.
    """

    SECTION_HEADERS = {
        "assets",
        "liabilities",
        "equity",
        "non-current assets",
        "current assets",
        "total assets",
        "total non-current assets",
        "total current assets",
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
    return str(df.iloc[0, 0]).strip()


def extract_unit(df):
    row = df.iloc[1].dropna().astype(str).str.strip()
    return row.values[0] if len(row) > 0 else None



def build_columns(df):
    # Find first row that looks like a header (contains 'Note' or 'As at')
    header_row_idx = None
    for i in range(5):
        row_text = " ".join(df.iloc[i].astype(str)).lower()
        if "note" in row_text or "as at" in row_text:
            header_row_idx = i
            break

    if header_row_idx is None:
        return [""] * df.shape[1]

    header_1 = df.iloc[header_row_idx].fillna("").astype(str)
    header_2 = df.iloc[header_row_idx + 1].fillna("").astype(str)

    SECTION_HEADERS = {"assets", "liabilities", "equity"}

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
    for i in range(1 , df.shape[1]):
        col_vals = df.iloc[start_row:, i].astype(str)
        if col_vals.str.contains(r"\d{2,}", regex=True).any():
            data_cols.append(i)
    return data_cols


def align_headers_to_data(columns, data_cols):
    header_map = {}
    data_iter = iter(data_cols)

    for col_name in columns:
        if not col_name.strip():
            continue

        # 🔥 Skip Particulars explicitly
        if col_name.strip().lower() == "particulars":
            continue

        try:
            header_map[next(data_iter)] = col_name
        except StopIteration:
            break

    return header_map


def to_float(x):
    if pd.isna(x):
        return None
    x = str(x).replace(",", "").strip()
    return float(x) if re.match(r"^-?\d+(\.\d+)?$", x) else None


# ============================================================
# Main Camelot Parser
# ============================================================

def camelot_parser(path_pdf):
    """
    Using detected Balance sheet pages, we extract page no. and give it as an input
    """

    bs_pages = detect_bs_pages(path_pdf)  
    if not bs_pages:
        print("No Balance Sheet pages detected.")
        return {}
    
    print(f"Detected Balance Sheet pages: {bs_pages}")

    all_results = {}

    for page_number in bs_pages:
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

        if len(tables) == 0:
            raise ValueError(f"No tables detected on page {page_number}")

        structured_tables = []

        for idx, t in enumerate(tables):
            df = t.df

            # ----------------------------------------------------
            # Basic junk filter
            # ----------------------------------------------------
            if df.shape[0] < 6 or df.shape[1] < 3:
                continue
            print(f"[DEBUG] Page {page_number}, Table {idx}: shape {df.shape}")

            try:
            # ------------------------------------------------
            # STEP 1: Extract metadata
            # ------------------------------------------------
                title = extract_statement_title(df)
                unit = extract_unit(df)

            # ------------------------------------------------
            # STEP 2: Build header candidates
            # ------------------------------------------------
                columns = build_columns(df)

            # ------------------------------------------------
            # STEP 3: Detect where numeric data exists
            # ------------------------------------------------
                DATA_START_ROW = detect_data_start_row(df)
                if DATA_START_ROW is None:
                    continue
                data_cols = detect_data_columns(df, DATA_START_ROW)

                if not data_cols:
                    continue
                
                print(f"[DEBUG] Page {page_number}, Table {idx}: data columns detected at {data_cols}")
            # ------------------------------------------------
            # STEP 4: Align headers to shifted data
            # ------------------------------------------------
                header_map = align_headers_to_data(columns, data_cols)

                if not header_map:
                    continue
                
                print(f"[DEBUG] Page {page_number}, Table {idx}: header map {header_map}")
            # ------------------------------------------------
            # STEP 5: Extract Particulars (column 0)
            # ------------------------------------------------
                particulars = (
                    df.iloc[DATA_START_ROW:, 0]
                    .astype(str)
                    .str.strip()
                    .reset_index(drop=True)
                )

            # ------------------------------------------------
            # STEP 6: Extract data columns
            # ------------------------------------------------
                data_df = (
                    df.iloc[DATA_START_ROW:, list(header_map.keys())]
                    .reset_index(drop=True)
                )
                data_df.columns = list(header_map.values())

            # Insert Particulars as first column
                if "Particulars" not in data_df.columns:
                    data_df.insert(0, "Particulars", particulars)

            # ------------------------------------------------
            # 🔥 FILTER: keep only MAIN Balance Sheet table
            # ------------------------------------------------
                if "Note" not in data_df.columns and "Notes" not in data_df.columns:
                    continue
                
                print(f"[DEBUG] Page {page_number}, Table {idx}: Passed main BS table filter")
            # ------------------------------------------------
            # STEP 7: Enforce dtypes
            # ------------------------------------------------
            # Particulars → string
                data_df["Particulars"] = (
                    data_df["Particulars"]
                    .astype(str)
                    .str.strip()
                )

            # Note → string (if present)
                if "Note" in data_df.columns:
                    data_df["Note"] = (
                        data_df["Note"]
                        .astype(str)
                        .str.strip()
                    )

            # Value columns → float
                for col in data_df.columns:
                    if col not in ["Particulars", "Note"]:
                        data_df[col] = data_df[col].apply(to_float)

            # ------------------------------------------------
            # STEP 8: Attach metadata
            # ------------------------------------------------
                data_df.attrs["title"] = title
                data_df.attrs["unit"] = unit
                data_df.attrs["source_page"] = page_number
                data_df.attrs["table_index"] = idx

                structured_tables.append(data_df)

            except Exception as e:
                print(f"⚠️ Skipping table {idx} on page {page_number}: {e}")
    
        if structured_tables:
            all_results[f"page_{page_number}"] = structured_tables
            print(f"✅ PAGE {page_number}: Extracted {len(structured_tables)} structured tables")
            print(type(all_results))
    return all_results

#Example usage:
if __name__ == "__main__":
    pdf = "downloads/KAYNES/annual/KAYNES_Annual_2025.pdf"
    # page_num = 191
    results = camelot_parser(pdf)
    for page_key, tables in results.items():
        print(f"\nTables on {page_key}:")
        for idx, df in enumerate(tables):
            print(f"Table {idx} on {page_key}:")
            print(df.head(20))    
            print("\n")   

    #exported csvs
        for idx, df in enumerate(tables):
            csv_filename = f"{page_key}_table_{idx}.csv"
            df.to_csv(csv_filename, index=False)
            print(f"Exported {csv_filename}")