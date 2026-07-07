"""Tests for XLSX loading/writing (new format)."""

import pandas as pd

from src.data.loaders.xlsx_loader import load_xlsx
from src.data.writers.xlsx_writer import write_xlsx


class TestLoadXlsx:
    def test_load_xlsx_file(self, test_data_dir):
        xlsx_path = test_data_dir / "sample_new_format.xlsx"
        df = pd.DataFrame(
            {
                "code": ["TEST001", "TEST002"],
                "name": ["Product 1", "Product 2"],
                "price": ["100.50", "200.00"],
            }
        )
        df.to_excel(xlsx_path, index=False, engine="openpyxl")

        result = load_xlsx(xlsx_path)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "code" in result.columns
        assert "name" in result.columns

    def test_load_xlsx_with_special_chars(self, test_data_dir):
        xlsx_path = test_data_dir / "sample_special_chars.xlsx"
        df = pd.DataFrame(
            {
                "code": ["TEST001"],
                "name": ["Produkt č. 1 - špeciálne znaky"],
                "price": ["100.50"],
            }
        )
        df.to_excel(xlsx_path, index=False, engine="openpyxl")

        result = load_xlsx(xlsx_path)

        assert result.loc[0, "name"] == "Produkt č. 1 - špeciálne znaky"

    def test_load_xlsx_empty_file(self, test_data_dir):
        xlsx_path = test_data_dir / "empty.xlsx"
        pd.DataFrame().to_excel(xlsx_path, index=False, engine="openpyxl")

        result = load_xlsx(xlsx_path)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_load_xlsx_converts_all_to_string(self, test_data_dir):
        xlsx_path = test_data_dir / "sample_types.xlsx"
        df = pd.DataFrame(
            {
                "code": ["TEST001", "TEST002"],
                "price": ["100.50", "200.00"],
                "stock": ["10", "20"],
            }
        )
        df.to_excel(xlsx_path, index=False, engine="openpyxl")

        result = load_xlsx(xlsx_path)

        assert result.loc[0, "code"] == "TEST001"
        # Price is loaded as string; Excel may drop trailing zeros
        assert result.loc[0, "price"] in ["100.50", "100.5"]


class TestWriteXlsx:
    def test_write_xlsx_roundtrip(self, tmp_path):
        df = pd.DataFrame(
            {
                "code": ["TEST001"],
                "name": ["Produkt č. 1 - špeciálne znaky"],
                "defaultCategory": ["Tovary a kategórie > Vitríny"],
            }
        )
        output_path = tmp_path / "output_special.xlsx"

        write_xlsx(df, output_path)

        loaded_df = pd.read_excel(output_path, engine="openpyxl")
        assert loaded_df.loc[0, "name"] == "Produkt č. 1 - špeciálne znaky"

    def test_write_xlsx_preserves_column_order(self, tmp_path):
        columns = ["code", "name", "price", "image", "defaultCategory"]
        df = pd.DataFrame({col: ["test"] for col in columns})
        output_path = tmp_path / "output_order.xlsx"

        write_xlsx(df, output_path)

        loaded_df = pd.read_excel(output_path, engine="openpyxl")
        assert list(loaded_df.columns) == columns

    def test_write_xlsx_creates_parent_dirs(self, tmp_path):
        output_path = tmp_path / "nested" / "dir" / "output.xlsx"

        write_xlsx(pd.DataFrame({"code": ["TEST001"]}), output_path)

        assert output_path.exists()
