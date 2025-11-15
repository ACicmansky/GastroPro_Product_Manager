"""
XML Parser for new 138-column format.
Parses XML feeds directly to new e-shop format.
"""

import pandas as pd
import xml.etree.ElementTree as ET
from typing import Dict


class XMLParserNewFormat:
    """Parser for XML feeds outputting to new 138-column format."""

    def __init__(self, config: Dict):
        """
        Initialize XML parser with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config
        self.xml_feeds = config.get("xml_feeds", {})

    def parse_gastromarket(self, xml_content: str) -> pd.DataFrame:
        """
        Parse Gastromarket XML feed to new format.

        Args:
            xml_content: XML content as string

        Returns:
            DataFrame with new format columns
        """
        print("\nParsing Gastromarket XML feed...")

        feed_config = self.xml_feeds.get("gastromarket", {})
        root_element = feed_config.get("root_element", "PRODUKTY")
        item_element = feed_config.get("item_element", "PRODUKT")
        mapping = feed_config.get("mapping", {})

        # Parse XML
        root = ET.fromstring(xml_content)

        # Extract data
        data = []
        for item in root.findall(f".//{item_element}"):
            row = {}
            for xml_field, new_field in mapping.items():
                element = item.find(xml_field)
                value = element.text if element is not None and element.text else ""
                row[new_field] = value

            # Add feed name
            row["xmlFeedName"] = "gastromarket"
            data.append(row)

        df = pd.DataFrame(data)

        # Process images - check if IMAGE column exists in result
        if "IMAGE" in df.columns:
            df = self._split_images(df, "IMAGE")

        # Clean prices
        if "price" in df.columns:
            df = self._clean_prices(df)

        # Ensure all values are strings and replace NaN
        for col in df.columns:
            df[col] = df[col].astype(str).replace("nan", "").replace("None", "")

        print(f"  Parsed {len(df)} products from Gastromarket")
        return df

    def parse_forgastro(self, xml_content: str) -> pd.DataFrame:
        """
        Parse ForGastro XML feed to new format.

        Args:
            xml_content: XML content as string

        Returns:
            DataFrame with new format columns
        """
        print("\nParsing ForGastro XML feed...")

        feed_config = self.xml_feeds.get("forgastro", {})
        root_element = feed_config.get("root_element", "products")
        item_element = feed_config.get("item_element", "product")
        mapping = feed_config.get("mapping", {})

        # Parse XML
        root = ET.fromstring(xml_content)

        # Extract data
        data = []
        for item in root.findall(f".//{item_element}"):
            row = {}
            for xml_field, new_field in mapping.items():
                element = item.find(xml_field)
                value = element.text if element is not None and element.text else ""
                row[new_field] = value

            # Add feed name
            row["xmlFeedName"] = "forgastro"
            data.append(row)

        df = pd.DataFrame(data)

        # Process images - check if IMAGES column exists in result
        if "IMAGES" in df.columns:
            df = self._split_images(df, "IMAGES")

        # Clean prices
        if "price" in df.columns:
            df = self._clean_prices(df)

        # Ensure all values are strings and replace NaN
        for col in df.columns:
            df[col] = df[col].astype(str).replace("nan", "").replace("None", "")

        print(f"  Parsed {len(df)} products from ForGastro")
        return df

    def _split_images(self, df: pd.DataFrame, image_column: str) -> pd.DataFrame:
        """
        Split image URLs into separate columns.

        Args:
            df: DataFrame with image column
            image_column: Name of column containing images

        Returns:
            DataFrame with split image columns
        """
        # Define image column names
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
            df[col] = ""

        # Split images (can be pipe or comma separated)
        for idx, row in df.iterrows():
            images_str = str(row[image_column]) if pd.notna(row[image_column]) else ""
            if images_str and images_str not in ["nan", "None", ""]:
                # Try pipe separator first, then comma
                if "|" in images_str:
                    images = [
                        img.strip() for img in images_str.split("|") if img.strip()
                    ]
                else:
                    images = [
                        img.strip() for img in images_str.split(",") if img.strip()
                    ]

                # Assign to columns (max 8)
                for i, img_url in enumerate(images[:8]):
                    df.at[idx, image_columns[i]] = img_url

        # Remove original image column if it exists
        if image_column in df.columns and image_column not in image_columns:
            df = df.drop(columns=[image_column])

        return df

    def _clean_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean price values (comma to dot conversion).

        Args:
            df: DataFrame with price column

        Returns:
            DataFrame with cleaned prices
        """
        if "price" in df.columns:
            # Replace comma with dot for decimal separator
            df["price"] = df["price"].astype(str).str.replace(",", ".", regex=False)
            # Remove any currency symbols
            df["price"] = df["price"].str.replace("€", "", regex=False).str.strip()

        return df
