import camelot
import pandas as pd


def camelot_parser(path_pdf, page_number):
    tables = camelot.read_pdf(
        path_pdf,
        pages=str(page_number),
        flavor="stream",
        edge_tol=50,
        # row_tol=4,
        # column_tol=4,
        
        strip_text='\n'
    )

    if len(tables) == 0:
        raise ValueError(f"No tables detected on page {page_number}")

    valid_tables = []

    for idx, t in enumerate(tables):
        df = t.df

        # Filter junk tables
        if df.shape[0] >= 4 and df.shape[1] >= 2:
            df.attrs["source_page"] = page_number
            df.attrs["table_index"] = idx
            valid_tables.append(df)
    
    

    print(f"df.columns: {df.columns}")
    print(f"✅ PAGE {page_number}: Extracted {len(valid_tables)} valid tables")

    return (f"page_{page_number}", valid_tables)




#Example usage:

if __name__ == "__main__":
    pdf = "downloads/KAYNES/quarterly/KAYNES_Q2_2023.pdf"
    page_num = 3
    page_key, tables = camelot_parser(pdf, page_num)
    for idx, df in enumerate(tables):
        print(f"Table {idx} on {page_key}:")
        print(df.head(20))    
        print("\n")   

    #exported csvs
    for idx, df in enumerate(tables):
        csv_filename = f"{page_key}_table_{idx}.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Exported {csv_filename}")
