"""
XML Parser Factory for automatic feed detection.
"""

import logging
import urllib.request

import pandas as pd
from typing import Dict

from .xml_parser import XMLParser

logger = logging.getLogger(__name__)


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
            XMLParser instance
        """
        return XMLParser(config)

    @staticmethod
    def fetch_and_parse(feed_name: str, url: str, config: Dict) -> pd.DataFrame:
        """Fetch XML feed from URL and parse it.

        Returns an empty DataFrame on fetch failure.
        """
        try:
            with urllib.request.urlopen(url) as response:
                xml_content = response.read().decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_name} from {url}: {e}")
            return pd.DataFrame()
        return XMLParserFactory.parse(feed_name, xml_content, config)

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
        elif feed_name.lower() == "gastromarket_stalgast":
            return parser.parse_gastromarket_stalgast(xml_content)
        elif feed_name.lower() == "forgastro":
            return parser.parse_forgastro(xml_content)
        else:
            raise ValueError(f"Unknown feed name: {feed_name}")
