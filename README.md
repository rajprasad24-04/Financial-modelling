# Screener.in Financial Statement Extractor & Aggregator

An automated, end-to-end Python pipeline designed to scrape corporate annual reports from Screener.in(for temporary later we can use directly nse), extract raw financial statement tables (Balance Sheet and Profit & Loss) directly from highly irregular PDF layouts, and blend them into unified, chronologically ordered historical timelines exported as clean CSV spreadsheets.

## Key Features

* **Smart Authentication Context:** Leverages Playwright's persistent browser context to store session data locally. You only need to perform a manual login once; subsequent sessions bypass authentication automatically.
* **Built-in PDF Viewer Bypass:** Intercepts network response streams directly at the routing layer to capture raw PDF bytes before Chromium's internal PDF plugin can corrupt or wrapper-render them into static HTML layers.
* **Adaptive Document Type Mapping:** Employs advanced `pdfplumber` textual tokenization matrices to scanning documents up to 400 pages long to instantly locate statement pages while filtering out standalone metrics.
* **Untangling Complex PDF Layouts:** Uses `camelot-py` stream flavors equipped with custom regex splitters to isolate inline note numbers glued to text labels, and intelligently separate multiple historical financial columns that have compressed into single text strings.
* **Order-Preserved Time Aggregation:** Normalizes accounting shorthand notations (parentheses to negative notation, null indicators to uniform float NaNs) and chains rows relatively to prevent chronological scrambled rows.

---

## 📁 System Architecture & Directory Flow

```text
Project Root/
│
├── Scraper/
│   ├── i_build_url.py                 # Constructs target Screener.in corporate URLs
│   ├── ii_screener_scraper.py         # Automates browser lifecycle & manual login fallback
│   ├── iii_google_drive_manager.py   # Cloud sync adapter (Disabled)
│   └── iv_collect_company_report.py   # Master orchestration pipeline manager
│
├── Parser/
│   ├── bs.py                          # Token locator for Balance Sheet anchors
│   └── pnl.py                         # Token locator for Profit & Loss anchors
│
├── Table/
│   ├── ii_table_for_bs.py             # Structural balance sheet layout extractor
│   └── iii_table_for_pnl.py            # Adaptive table text column schema aligning module
│
├── Integration/
│   ├── loop_bs.py                     # Batch wrapper running balance sheet parsing 
│   ├── loop_pnl.py                    # Batch wrapper running profit & loss parsing
│   ├── merge_bs.py                    # Formats, stacks and horizontal pivots balance sheets
│   └── merge_pnl.py                   # Cleans numerical strings & handles accounting restatements
│
├── downloads/                         # Automated output storage destination for source PDFs
└── output/                            # Destination for fully compiled wide chronological CSVs


Prerequisites
# Clone or navigate into your project workspace

# Initialize or enter your active Python virtual environment
source venv/bin/activate

# Install the required underlying system-level dependencies for parsing engine
pip install playwright camelot-py pdfplumber pandas openpyxl
playwright install chromium

python Scraper/iv_collect_company_report.py TCS
python Integration/merge_bs.py
python Integration/merge_pnl.py

## ⚠️ Current Limitations & Scope

While the pipeline is highly optimized for complex extraction tasks, it currently operates under the following structural limitations:

### 1. Stock / Company Generalization Constraint
* **Ticker Specialization:** The parsing engine's table column alignment, word-normalization logic, and layout cropping thresholds are heavily tuned based on specific corporate formatting layouts (e.g., TCS). 
* **Lack of Generalization:** Because financial report layouts vary drastically across different sectors and auditing firms, the current `camelot_parser` functions are not yet universal "generalists." Running different stock tickers through the parser without modifying the regex anchors or structural layout parameters may result in index shifts or length mismatches.

### 2. Statement Scope
* **Core Financials Only:** The pipeline is strictly engineered to locate, extract, and clean the **Consolidated Balance Sheet (BS)** and the **Consolidated Statement of Profit and Loss (P&L)**.
* **No Cash Flow Support:** The Consolidated Statement of Cash Flows is currently out of scope and ignored by the document processing loop.

### 3. Footnotes and Detailed Accounting Notes Exclusion
* **Reference Isolation Only:** The system treats the `Notes` column solely as "data noise." The code is designed to identify, isolate, and completely strip away these note reference numbers to ensure smooth wide-format horizontal timeline stacking.
* **No Notes Text Parsing:** The deep, textual financial footnotes and detailed schedule disclosures located at the back of annual reports are completely skipped and not parsed into data rows.