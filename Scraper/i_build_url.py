def build_company_url(ticker: str, standalone: bool = False) -> str:
    """
    Builds Screener company URL.
    Default is consolidated.
    Use standalone=True only if standalone reports are needed.
    """
    ticker = ticker.upper().strip()
    suffix = "" if standalone else "consolidated"
    return f"https://www.screener.in/company/{ticker}/{suffix}/"


# # Example usage:
if __name__ == "__main__":
    print(build_company_url("TCS"))  # Default consolidated URL
    print(build_company_url("TCS", standalone=True))  # Standalone URL