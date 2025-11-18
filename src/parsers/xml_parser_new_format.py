"""
XML Parser for new 138-column format.
Parses XML feeds directly to new e-shop format.
"""

import pandas as pd
import xml.etree.ElementTree as ET
from typing import Dict
import html
import re
from bs4 import BeautifulSoup


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
        root_element = feed_config.get("root_element", "channel")
        item_element = feed_config.get("item_element", "item")
        mapping = feed_config.get("mapping", {})
        namespace_url = feed_config.get("namespace")

        xml_root = ET.fromstring(xml_content)

        # Register namespace if provided
        namespaces = {}
        if namespace_url:
            namespaces = {"g": namespace_url}
            # Register namespace for ElementTree
            ET.register_namespace("g", namespace_url)

        root = xml_root.find(root_element)

        # Extract data
        data = []
        for item in root.findall(f".//{item_element}"):
            row = {}
            for xml_field, new_field in mapping.items():
                # Use namespace prefix if configured
                if namespace_url:
                    element = item.find(f"g:{xml_field}", namespaces)
                else:
                    element = item.find(xml_field)

                value = element.text if element is not None and element.text else ""
                row[new_field] = value

            # Add feed name
            row["source"] = "gastromarket"
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
            row["source"] = "forgastro"
            data.append(row)

        df = pd.DataFrame(data)

        # Process HTML content in description field
        if "description" in df.columns:
            df = self._process_forgastro_html(df)

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

    def _process_forgastro_html(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process HTML content from ForGastro feed.
        Extracts clean text from 'popis' tab for description (long desc)
        and parameters from 'parametre' tab for shortDescription (appended if exists).
        If no tabs present, extracts clean text from entire HTML to description.

        Args:
            df: DataFrame with description column containing HTML

        Returns:
            DataFrame with processed shortDescription and description
        """
        for idx, row in df.iterrows():
            html_content = row.get("description", "")

            if not html_content or not isinstance(html_content, str):
                continue

            try:
                decoded_html = html.unescape(html_content)

                # Check if content has tab structure
                has_tabs = "{tab title=" in decoded_html

                if has_tabs:
                    # Extract content from tabs
                    popis_pattern = re.compile(
                        r'\{tab title="popis"\}(.*?)(?:\{tab title|\{/tabs\}|$)',
                        re.DOTALL,
                    )
                    parametre_pattern = re.compile(
                        r'\{tab title="parametre"\}(.*?)(?:\{tab title|\{/tabs\}|$)',
                        re.DOTALL,
                    )

                    popis_match = popis_pattern.search(decoded_html)
                    parametre_match = parametre_pattern.search(decoded_html)

                    popis_content = popis_match.group(1) if popis_match else ""
                    parametre_content = (
                        parametre_match.group(1) if parametre_match else ""
                    )

                    popis_text = (
                        BeautifulSoup(popis_content, "html.parser").get_text(
                            separator=" ", strip=True
                        )
                        if popis_content
                        else ""
                    )

                    params_text = ""
                    if parametre_content:
                        soup_params = BeautifulSoup(parametre_content, "html.parser")
                        tables = soup_params.find_all("table")
                        if tables:
                            param_lines = []
                            for table_row in tables[0].find_all("tr")[1:]:
                                cols = table_row.find_all(["td", "th"])
                                if len(cols) >= 2:
                                    param_name = cols[0].get_text(strip=True)
                                    param_value = cols[1].get_text(strip=True)
                                    if param_value:
                                        param_lines.append(
                                            f"{param_name} {param_value}"
                                        )
                            params_text = "\n".join(param_lines)
                        else:
                            params_text = soup_params.get_text(
                                separator=" ", strip=True
                            )
                else:
                    # No tabs - extract clean text from entire HTML content
                    popis_text = BeautifulSoup(decoded_html, "html.parser").get_text(
                        separator=" ", strip=True
                    )
                    params_text = ""

                # Update DataFrame - matching old version behavior:
                # 1. popis_text goes to description (Dlhý popis)
                if "description" in df.columns and popis_text:
                    df.at[idx, "description"] = popis_text

                # 2. params_text goes to shortDescription (Krátky popis), appended if exists
                if "shortDescription" in df.columns and params_text:
                    current_short = str(row.get("shortDescription", "")).strip()
                    if current_short and current_short not in ["nan", "None", ""]:
                        df.at[idx, "shortDescription"] = (
                            f"{current_short}\n{params_text}"
                        )
                    else:
                        df.at[idx, "shortDescription"] = params_text

            except Exception as e:
                print(
                    f"  Warning: Error processing HTML for product at index {idx}: {e}"
                )
                continue

        return df
