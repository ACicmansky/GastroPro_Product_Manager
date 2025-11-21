"""
Script to transform categories from old format to new format
"""

import pandas as pd
import json
import chardet
from pathlib import Path


def transform_categories(categories_filePath: str):
    with open(categories_filePath, "rb") as f:
        result = chardet.detect(f.read())
        encoding = result["encoding"]
    with open(categories_filePath, "r", encoding=encoding) as f:
        categories = json.load(f)

    df = pd.DataFrame(categories)

    df["newCategory"] = df["newCategory"].apply(
        lambda x: "Gastro prevádzky a profesionáli > " + x.replace("/", " > ")
    )

    json_str = df.to_json(orient="records", force_ascii=False, indent=2)
    json_str = json_str.replace("\\/", "/")

    with open(categories_filePath, "w", encoding=encoding) as f:
        f.write(json_str)


if __name__ == "__main__":
    current_dir = Path(__file__).parent
    transform_categories(current_dir.parent / "categories.json")
