import json
import pandas as pd


def extract_products(num_products=50):
    """
    Extract product names and descriptions from CSV and save to JSON

    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output JSON file
        num_products (int): Number of products to extract (default: 50)
    """
    output_file = "scripts/products_with_descriptions.json"

    try:
        # Read the CSV file, limiting to num_products rows
        df = pd.read_csv(
            "scripts/ALLexport-products.csv",
            nrows=num_products,
            encoding="cp1250",
            sep=";",
            dtype=str,
            keep_default_na=False,
        )

        # Select only the required columns
        columns_needed = [
            "Názov tovaru",
            "Hlavna kategória",
            "Krátky popis",
            "Dlhý popis",
        ]

        # Check if all required columns exist
        missing_columns = [col for col in columns_needed if col not in df.columns]
        if missing_columns:
            print(
                f"Warning: The following columns are missing: {', '.join(missing_columns)}"
            )
            print("Available columns:", ", ".join(df.columns.tolist()))
            return False

        # Select and rename columns
        result = df[columns_needed]

        # Convert NaN values to empty strings
        result = result.fillna("")

        # Convert to list of dictionaries
        products = result.to_dict("records")

        # Save to JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"Successfully extracted {len(products)} products to {output_file}")
        return True

    except Exception as e:
        print(f"Error processing file: {e}")
        return False


def main():
    extract_products()


if __name__ == "__main__":
    main()
