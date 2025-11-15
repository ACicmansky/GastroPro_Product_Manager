"""
OutputTransformer module for converting internal format to new 147-column e-shop format.

This module handles:
- Direct column mappings
- Image URL splitting (1 column -> 8 columns)
- Category transformation (prefix + separator replacement)
- Code uppercase conversion
- Default value application
- Ensuring all 147 columns exist
"""

import pandas as pd
from typing import Dict, List


class OutputTransformer:
    """Transforms internal data format to new 147-column e-shop output format."""

    def __init__(self, config: Dict):
        """
        Initialize OutputTransformer with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config
        self.output_mapping = config.get("output_mapping", {})
        self.mappings = self.output_mapping.get("mappings", {})
        self.default_values = self.output_mapping.get("default_values", {})
        self.new_output_columns = config.get("new_output_columns", [])

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Complete transformation from old format to new 147-column format.

        Args:
            df: Input DataFrame with old format

        Returns:
            DataFrame with new 147-column format
        """
        print("\n" + "=" * 60)
        print("OUTPUT TRANSFORMATION PROCESS")
        print("=" * 60)

        # 1. Apply direct mappings (excluding Obrázky which we'll handle specially)
        output_df = self.apply_direct_mappings(df)

        # 2. Split images into multiple columns
        output_df = self.split_images(df, output_df)

        # 3. Apply category transformation
        output_df = self.transform_category(df, output_df)

        # 4. Apply code uppercase
        output_df = self.uppercase_code(output_df)

        # 5. Ensure all columns exist
        output_df = self._ensure_all_columns(output_df)

        # 6. Apply default values
        output_df = self.apply_default_values(output_df)

        print("\n" + "=" * 60)
        print("TRANSFORMATION COMPLETE")
        print(f"Output columns: {len(output_df.columns)}")
        print(f"Output rows: {len(output_df)}")
        print("=" * 60)

        return output_df

    def apply_direct_mappings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply direct column mappings from old to new format.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with mapped columns
        """
        print("\nApplying direct mappings...")

        output_df = pd.DataFrame()

        for old_col, new_col in self.mappings.items():
            if old_col in df.columns and new_col != "Obrázky":
                output_df[new_col] = df[old_col].astype(str).fillna("")
                print(f"  Mapped: {old_col} -> {new_col}")

        print(f"  Mapped {len(output_df.columns)} columns")
        return output_df

    def split_images(
        self, df: pd.DataFrame, output_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Split comma-separated image URLs into 8 separate columns.

        Args:
            df: Input DataFrame with 'Obrázky' column
            output_df: Output DataFrame to populate (optional)

        Returns:
            DataFrame with split image columns
        """
        print("\nSplitting image URLs...")

        if output_df is None:
            output_df = pd.DataFrame(index=df.index)

        if "Obrázky" not in df.columns:
            print("  Warning: 'Obrázky' column not found")
            # Initialize empty image columns
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
            for col in image_columns:
                output_df[col] = ""
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
            images_str = str(row["Obrázky"]) if pd.notna(row["Obrázky"]) else ""
            if images_str and images_str != "nan":
                # Split by comma and strip whitespace
                images = [img.strip() for img in images_str.split(",") if img.strip()]

                # Assign to columns (max 8)
                for i, img_url in enumerate(images[:8]):
                    output_df.at[idx, image_columns[i]] = img_url

        print(f"  Split images into {len(image_columns)} columns")
        return output_df

    def transform_category(
        self, df: pd.DataFrame, output_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Transform category: add prefix and replace separator.

        Transformation:
        - Add prefix: "Tovary a kategórie > "
        - Replace "/" with " > "

        Args:
            df: Input DataFrame with 'Hlavna kategória' column
            output_df: Output DataFrame to populate (optional)

        Returns:
            DataFrame with transformed categories
        """
        print("\nTransforming categories...")

        if output_df is None:
            output_df = pd.DataFrame(index=df.index)

        if "Hlavna kategória" not in df.columns:
            print("  Warning: 'Hlavna kategória' column not found")
            output_df["defaultCategory"] = ""
            output_df["categoryText"] = ""
            return output_df

        # Transform each category
        transformed_categories = []
        for idx, row in df.iterrows():
            category = (
                str(row["Hlavna kategória"])
                if pd.notna(row["Hlavna kategória"])
                else ""
            )

            if category and category != "nan":
                # Replace "/" with " > "
                category = category.replace("/", " > ")
                # Add prefix
                category = "Tovary a kategórie > " + category
            else:
                category = "Tovary a kategórie > "

            transformed_categories.append(category)

        # Apply to both defaultCategory and categoryText
        output_df["defaultCategory"] = transformed_categories
        output_df["categoryText"] = transformed_categories

        print(f"  Transformed {len(transformed_categories)} categories")
        return output_df

    def uppercase_code(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert catalog codes to uppercase.

        Args:
            df: DataFrame with 'code' column

        Returns:
            DataFrame with uppercased codes
        """
        print("\nConverting codes to uppercase...")

        if "code" in df.columns:
            df["code"] = df["code"].astype(str).str.upper()
            print(f"  Converted {len(df)} codes to uppercase")
        else:
            print("  Warning: 'code' column not found")

        return df

    def apply_default_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply default values to empty cells only.

        Args:
            df: DataFrame to apply defaults to

        Returns:
            DataFrame with defaults applied
        """
        print("\nApplying default values...")

        applied_count = 0
        for col, default_value in self.default_values.items():
            if col in df.columns:
                # Apply default only where cell is empty or NaN
                mask = (df[col].isna()) | (df[col] == "") | (df[col] == "nan")
                df.loc[mask, col] = default_value
                applied_count += mask.sum()

        print(f"  Applied {applied_count} default values")
        return df

    def _ensure_all_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure all 147 columns exist in the output DataFrame.

        Args:
            df: DataFrame to check

        Returns:
            DataFrame with all columns
        """
        print("\nEnsuring all columns exist...")

        missing_columns = []
        for col in self.new_output_columns:
            if col not in df.columns:
                df[col] = ""
                missing_columns.append(col)

        if missing_columns:
            print(f"  Added {len(missing_columns)} missing columns")
        else:
            print("  All columns already present")

        # Reorder columns to match configuration
        df = df[self.new_output_columns]

        return df
