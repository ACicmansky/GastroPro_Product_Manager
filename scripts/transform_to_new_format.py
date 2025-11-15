"""
Transform old CSV format to new XLSX format.

This script:
1. Loads old format CSV (semicolon-separated, cp1250 encoding)
2. Applies all output mappings from config.json
3. Splits multiple image URLs into separate columns
4. Applies category transformations and code uppercase
5. Applies default values where empty
6. Outputs XLSX file with new 147-column structure
"""

import pandas as pd
import json
import os
from pathlib import Path

# Hardcoded file path - change this to your input file
INPUT_FILE = r"c:\Source\Python\GastroPro_Product_Manager\data\2025_10_03_Merged_AI.csv"


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_old_format_csv(filepath):
    """Load old format CSV file."""
    print(f"Loading CSV from: {filepath}")

    # Try cp1250 encoding first, fallback to utf-8
    try:
        df = pd.read_csv(filepath, sep=";", encoding="cp1250")
        print(f"Loaded with cp1250 encoding")
    except:
        df = pd.read_csv(filepath, sep=";", encoding="utf-8")
        print(f"Loaded with utf-8 encoding")

    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")
    return df


def split_images(image_string):
    """
    Split comma-separated image URLs into list.

    Args:
        image_string: String with comma-separated URLs or single URL

    Returns:
        List of image URLs (up to 8)
    """
    if pd.isna(image_string) or image_string == "":
        return []

    # Split by comma and strip whitespace
    images = [img.strip() for img in str(image_string).split(",") if img.strip()]

    # Limit to 8 images (defaultImage + image + image2-7)
    return images[:8]


def apply_direct_mappings(df, mappings):
    """Apply direct column mappings."""
    print("\nApplying direct mappings...")
    output_df = pd.DataFrame(index=df.index)

    for internal_col, output_col in mappings.items():
        if internal_col in df.columns:
            output_df[output_col] = df[internal_col].copy()
            print(f"  Mapped: {internal_col} → {output_col}")

    return output_df


def apply_image_splitting(df, output_df):
    """
    Split Obrázky column into defaultImage, image, image2-7.

    Args:
        df: Input DataFrame with 'Obrázky' column
        output_df: Output DataFrame to populate
    """
    print("\nSplitting image URLs...")

    if "Obrázky" not in df.columns:
        print("  Warning: 'Obrázky' column not found")
        return output_df

    # Define image column names in order
    image_columns = [
        "defaultImage",
        "image",
        "image2",
        "image3",
        "image4",
        "image5",
        "image6",
        "image7",
    ]

    # Initialize all image columns as empty
    for col in image_columns:
        output_df[col] = ""

    # Split and assign images
    for idx, row in df.iterrows():
        images = split_images(row["Obrázky"])
        for i, img_url in enumerate(images):
            if i < len(image_columns):
                output_df.at[idx, image_columns[i]] = img_url

    print(f"  Split images into {len(image_columns)} columns")
    return output_df


def apply_category_transformation(df, output_df, config):
    """
    Transform category: add prefix and change separator.

    Transforms: "Vitríny/Chladiace vitríny"
    To: "Tovary a kategórie > Vitríny > Chladiace vitríny"
    """
    print("\nApplying category transformation...")

    if "Hlavna kategória" not in df.columns:
        print("  Warning: 'Hlavna kategória' column not found")
        return output_df

    special_mappings = config["output_mapping"].get("special_mappings", {})
    category_config = special_mappings.get("Hlavna kategória", {})

    prefix = category_config.get("prefix", "Tovary a kategórie > ")
    replacements = category_config.get("replace", {"/": " > "})
    target_columns = category_config.get(
        "target_columns", ["defaultCategory", "categoryText"]
    )

    # Transform categories
    transformed = df["Hlavna kategória"].copy()
    for old, new in replacements.items():
        transformed = transformed.str.replace(old, new, regex=False)
    transformed = prefix + transformed.astype(str)

    # Apply to target columns
    for col in target_columns:
        output_df[col] = transformed
        print(f"  Transformed: Hlavna kategória → {col}")

    return output_df


def apply_code_uppercase(df, output_df):
    """Apply uppercase transformation to catalog codes."""
    print("\nApplying code uppercase transformation...")

    if "code" in output_df.columns:
        output_df["code"] = output_df["code"].str.upper()
        print("  Uppercased: code column")

    return output_df


def apply_default_values(output_df, default_values):
    """Apply default values only to empty cells."""
    print("\nApplying default values...")

    applied_count = 0
    for col, default_value in default_values.items():
        if col in output_df.columns:
            # Apply default only where value is empty, None, or NaN
            mask = (
                output_df[col].isna()
                | (output_df[col] == "")
                | (output_df[col] == "nan")
            )
            count = mask.sum()
            if count > 0:
                output_df.loc[mask, col] = default_value
                applied_count += 1
                print(f"  Applied default to {col}: {count} cells")

    print(f"  Total: Applied defaults to {applied_count} columns")
    return output_df


def ensure_all_columns(output_df, new_output_columns):
    """Ensure all required columns exist in correct order."""
    print("\nEnsuring all output columns...")

    # Add missing columns as empty
    for col in new_output_columns:
        if col not in output_df.columns:
            output_df[col] = ""

    # Reorder to match new_output_columns
    output_df = output_df[new_output_columns]

    print(f"  Output has {len(output_df.columns)} columns")
    return output_df


def transform_to_new_format(df, config):
    """
    Main transformation function.

    Args:
        df: Input DataFrame with old format
        config: Configuration dictionary from config.json

    Returns:
        DataFrame with new 147-column format
    """
    print("\n" + "=" * 60)
    print("TRANSFORMATION PROCESS")
    print("=" * 60)

    output_mapping = config.get("output_mapping", {})
    mappings = output_mapping.get("mappings", {})
    default_values = output_mapping.get("default_values", {})
    new_output_columns = config.get("new_output_columns", [])

    # 1. Apply direct mappings (excluding Obrázky which we'll handle specially)
    output_df = apply_direct_mappings(df, mappings)

    # 2. Split images into multiple columns
    output_df = apply_image_splitting(df, output_df)

    # 3. Apply category transformation
    output_df = apply_category_transformation(df, output_df, config)

    # 4. Apply code uppercase
    output_df = apply_code_uppercase(df, output_df)

    # 5. Ensure all columns exist
    output_df = ensure_all_columns(output_df, new_output_columns)

    # 6. Apply default values
    output_df = apply_default_values(output_df, default_values)

    print("\n" + "=" * 60)
    print("TRANSFORMATION COMPLETE")
    print("=" * 60)

    return output_df


def save_to_xlsx(df, input_filepath):
    """Save DataFrame to XLSX with same name as input."""
    # Generate output filename
    input_path = Path(input_filepath)
    output_path = input_path.with_suffix(".xlsx")

    print(f"\nSaving to: {output_path}")

    # Save to Excel
    df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"✓ Saved {len(df)} rows to {output_path.name}")
    return output_path


def main():
    """Main execution function."""
    print("=" * 60)
    print("CSV TO NEW FORMAT TRANSFORMER")
    print("=" * 60)

    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"\n❌ ERROR: Input file not found: {INPUT_FILE}")
        print("\nPlease update the INPUT_FILE variable in this script.")
        return

    try:
        # Load configuration
        config = load_config()
        print(f"✓ Loaded configuration")

        # Load old format CSV
        df = load_old_format_csv(INPUT_FILE)

        # Transform to new format
        output_df = transform_to_new_format(df, config)

        # Save to XLSX
        output_path = save_to_xlsx(output_df, INPUT_FILE)

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Input:  {INPUT_FILE}")
        print(f"Output: {output_path}")
        print(f"Rows:   {len(output_df)}")
        print(f"Columns: {len(output_df.columns)}")
        print("\n✓ Transformation completed successfully!")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
