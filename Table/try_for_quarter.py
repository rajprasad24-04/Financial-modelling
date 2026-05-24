
import os
import pandas as pd
import re

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    print("⚠️ Camelot not installed. Install with: pip install camelot-py[cv]")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PDF_PATH = "downloads/KAYNES/quarterly/KAYNES_Q1_2023.pdf"
PAGE_NO = "3"

OUTPUT_DIR = "/Users/rajprasad/Desktop/SC/output_csv"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_CSV = os.path.join(OUTPUT_DIR, "KAYNES_Q1_2023_pnl.csv")

# -------------------------------------------------
# EXTRACT WITH CAMELOT (STREAM – CORRECT FOR QUARTERLY)
# -------------------------------------------------
def extract_with_camelot_stream(pdf_path, page_no):
    print("⏳ Extracting with Camelot (stream mode)...")

    tables = camelot.read_pdf(
        pdf_path,
        pages=page_no,
        flavor="stream",
        # row_tol=3,
        # column_tol=1,
        edge_tol=50
    )

    print(f"✅ Found {len(tables)} table(s)")

    if len(tables) == 0:
        return None

    largest_table = max(tables, key=lambda t: t.shape[0] * t.shape[1])
    return largest_table.df

# -------------------------------------------------
# CLEAN DATAFRAME
# -------------------------------------------------
def fix_broken_text(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r'(?<=\w)\s+(?=\w)', '', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def clean_camelot_df(df):
    df = df.copy()
    df.columns = [f"col_{i}" for i in range(len(df.columns))]

    df.rename(columns={"col_0": "Particulars"}, inplace=True)
    df["Particulars"] = df["Particulars"].apply(fix_broken_text)

    # Drop section headers
    df = df[~df["Particulars"].isin(["Expenses", "Tax expense"])]

    # Clean numeric columns
    for col in df.columns[1:]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False)
            .str.strip()
        )
        df[col] = df[col].replace(["", "nan", "-"], pd.NA)

    df = df.dropna(subset=["Particulars"], how="all")
    return df.reset_index(drop=True)

# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    if not CAMELOT_AVAILABLE:
        print("❌ Camelot not available.")
        return

    df_stream = extract_with_camelot_stream(PDF_PATH, PAGE_NO)

    if df_stream is None:
        print("❌ Extraction failed.")
        return

    print("⏳ Cleaning data...")
    final_df = clean_camelot_df(df_stream)

    print(f"✅ Final: {final_df.shape[0]} rows × {final_df.shape[1]} columns")

    print("\nPREVIEW:")
    print(final_df.head(15).to_string(index=False))

    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()


# import os
# import pandas as pd
# import re

# try:
#     import camelot
#     CAMELOT_AVAILABLE = True
# except ImportError:
#     CAMELOT_AVAILABLE = False
#     print("⚠️ Camelot not installed. Install with: pip install camelot-py[cv]")

# # -------------------------------------------------
# # CONFIG
# # -------------------------------------------------
# PDF_PATH = "downloads/KAYNES/quarterly/KAYNES_Q1_2023.pdf"
# PAGE_NO = "3"

# OUTPUT_DIR = "/Users/rajprasad/Desktop/SC/output_csv"
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# OUTPUT_CSV = os.path.join(OUTPUT_DIR, "KAYNES_Q1_2023_pnl_structured.csv")

# # -------------------------------------------------
# # EXTRACT WITH CAMELOT
# # -------------------------------------------------
# def extract_with_camelot_stream(pdf_path, page_no):
#     print("⏳ Extracting with Camelot (stream mode)...")

#     tables = camelot.read_pdf(
#         pdf_path,
#         pages=page_no,
#         flavor="stream",
#         edge_tol=50
#     )

#     print(f"✅ Found {len(tables)} table(s)")

#     if len(tables) == 0:
#         return None

#     largest_table = max(tables, key=lambda t: t.shape[0] * t.shape[1])
#     return largest_table.df

# # -------------------------------------------------
# # CLEAN TEXT
# # -------------------------------------------------
# def fix_broken_text(text):
#     """Fix broken words and extra spaces"""
#     if not isinstance(text, str):
#         return text
#     text = re.sub(r'\s{2,}', ' ', text)
#     return text.strip()

# def clean_numeric_value(value):
#     """Clean and convert numeric values"""
#     if pd.isna(value) or value in ['', 'nan', '-']:
#         return None
    
#     value = str(value).strip()
    
#     if not value:
#         return None
    
#     # Handle parentheses as negative (both regular and curly braces)
#     is_negative = False
#     if '(' in value or '{' in value:
#         is_negative = True
#         value = value.replace('(', '').replace(')', '').replace('{', '').replace('}', '')
    
#     # Remove commas and spaces
#     value = value.replace(',', '').replace(' ', '')
    
#     # Try to convert to float
#     try:
#         num = float(value)
#         return -num if is_negative else num
#     except:
#         return None

# # -------------------------------------------------
# # RESTRUCTURE P&L DATA
# # -------------------------------------------------
# def restructure_pnl_data(df):
#     """Restructure the P&L data into a clean format"""
    
#     # Extract period headers from row 1 (columns 2-6)
#     periods = []
#     audit_status = []
    
#     for col_idx in range(2, min(7, len(df.columns))):
#         period = fix_broken_text(str(df.iloc[1, col_idx]))
#         status = fix_broken_text(str(df.iloc[2, col_idx]))
#         periods.append(period)
#         audit_status.append(status)
    
#     print(f"📅 Detected periods: {periods}")
#     print(f"📋 Audit status: {audit_status}")
    
#     # Create structured data
#     structured_data = []
    
#     current_section = ""
#     current_sno = ""
    
#     # Start from row 3 (after headers)
#     for idx in range(3, len(df)):
#         sno = str(df.iloc[idx, 0]).strip()
#         particulars = fix_broken_text(str(df.iloc[idx, 1]))
        
#         # Skip empty rows
#         if not particulars or particulars in ['', 'nan']:
#             continue
        
#         # Check if this is a serial number row
#         if sno and sno.isdigit():
#             current_sno = sno
#             # Check if particulars is a section header
#             if particulars in ['Income', 'Expenses', 'Tax expenses', 'Other comprehensive']:
#                 current_section = particulars
#                 continue
        
#         # Clean particulars - remove letter prefixes like a), b), c)
#         particulars_clean = re.sub(r'^[a-z]\)\s*', '', particulars, flags=re.IGNORECASE)
        
#         # Extract numeric values for each period
#         row_data = {
#             'S_No': current_sno,
#             'Section': current_section,
#             'Particulars': particulars_clean
#         }
        
#         # Add values for each period
#         has_values = False
#         for i, period in enumerate(periods):
#             col_idx = i + 2  # Columns 2-6
#             value = clean_numeric_value(df.iloc[idx, col_idx])
#             row_data[period] = value
#             if value is not None:
#                 has_values = True
        
#         # Only add row if it has at least one value
#         if has_values:
#             structured_data.append(row_data)
    
#     # Create DataFrame
#     result_df = pd.DataFrame(structured_data)
    
#     # Reorder columns
#     base_cols = ['S_No', 'Section', 'Particulars']
#     period_cols = periods
#     result_df = result_df[base_cols + period_cols]
    
#     return result_df

# # -------------------------------------------------
# # MAIN
# # -------------------------------------------------
# def main():
#     if not CAMELOT_AVAILABLE:
#         print("❌ Camelot not available.")
#         return

#     df_raw = extract_with_camelot_stream(PDF_PATH, PAGE_NO)

#     if df_raw is None:
#         print("❌ Extraction failed.")
#         return

#     print("⏳ Restructuring data...")
#     final_df = restructure_pnl_data(df_raw)

#     print(f"✅ Final: {final_df.shape[0]} rows × {final_df.shape[1]} columns")

#     print("\n📊 STRUCTURED OUTPUT:")
#     print(final_df.to_string(index=False))
    
#     # Save to CSV
#     final_df.to_csv(OUTPUT_CSV, index=False)
#     print(f"\n✅ Saved to: {OUTPUT_CSV}")
    
#     # Also create an Excel file with better formatting
#     excel_output = OUTPUT_CSV.replace('.csv', '.xlsx')
#     try:
#         with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
#             final_df.to_excel(writer, index=False, sheet_name='P&L Statement')
            
#             # Auto-adjust column widths
#             worksheet = writer.sheets['P&L Statement']
#             for idx, col in enumerate(final_df.columns):
#                 max_length = max(
#                     final_df[col].astype(str).map(len).max(),
#                     len(col)
#                 ) + 2
#                 col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
#                 worksheet.column_dimensions[col_letter].width = min(max_length, 50)
        
#         print(f"✅ Excel saved to: {excel_output}")
#     except Exception as e:
#         print(f"⚠️ Excel export failed: {e}")

# if __name__ == "__main__":
#     main()