"""
XML Parser Factory for automatic feed detection.
"""

import pandas as pd
from typing import Dict

from src.parsers.xml_parser_new_format import XMLParserNewFormat


class XMLParserFactory:
    """Factory for creating appropriate XML parsers based on feed type."""

    @staticmethod
    def get_parser(feed_name: str, config: Dict):
        """
        Get appropriate parser based on feed name.

        Args:
            feed_name: Name of the feed (e.g., 'gastromarket', 'forgastro')
            config: Configuration dictionary

        Returns:
            XMLParserNewFormat instance
        """
        # For now, all feeds use the same parser
        return XMLParserNewFormat(config)

    @staticmethod
    def parse(feed_name: str, xml_content: str, config: Dict) -> pd.DataFrame:
        """
        Parse XML feed automatically detecting type.

        Args:
            feed_name: Name of the feed
            xml_content: XML content as string
            config: Configuration dictionary

        Returns:
            DataFrame with parsed data in new format
        """
        parser = XMLParserFactory.get_parser(feed_name, config)

        # Route to appropriate parsing method
        if feed_name.lower() == "gastromarket":
            return parser.parse_gastromarket(xml_content)
        elif feed_name.lower() == "forgastro":
            return parser.parse_forgastro(xml_content)
        else:
            raise ValueError(f"Unknown feed name: {feed_name}")
