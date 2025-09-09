# src/utils/data_loader.py
import pandas as pd

def load_csv_data(file_path: str) -> pd.DataFrame:
    """Loads CSV data from the given path into a Pandas DataFrame, considering semicolon as separator and comma as decimal point."""
    encodings = ['cp1250', 'latin1', 'utf-8-sig']
    for encoding in encodings:
        try:
            df = pd.read_csv(
                file_path,
                sep=';',
                decimal=',',
                encoding=encoding,
                on_bad_lines='skip',
                dtype=str,
                keep_default_na=False
            )
            
            return df
        except UnicodeDecodeError:
            continue
    raise Exception(f"Nepodarilo sa načítať CSV súbor s kódovaním {encodings}.")
