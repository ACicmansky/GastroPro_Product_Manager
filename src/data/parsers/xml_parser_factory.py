"""
XML Parser Factory for automatic feed detection.
"""

import logging
import time
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
    def fetch_and_parse(
        feed_name: str, url: str, config: Dict, retries: int = 3
    ) -> pd.DataFrame:
        """Fetch XML feed from URL (with retries) and parse it.

        Feeds are generated on demand server-side and occasionally answer
        with a transient 502 while generating. Returns an empty DataFrame
        only after all attempts fail.
        """
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/xml,text/xml,*/*;q=0.9",
            },
        )
        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    xml_content = response.read().decode("utf-8")
                return XMLParserFactory.parse(feed_name, xml_content, config)
            except Exception as e:
                if attempt == retries:
                    logger.error(
                        f"Failed to fetch feed {feed_name} from {url} "
                        f"after {retries} attempts: {e}"
                    )
                    return pd.DataFrame()
                logger.warning(
                    f"Fetch attempt {attempt}/{retries} for {feed_name} failed: "
                    f"{e} — retrying in {5 * attempt}s"
                )
                time.sleep(5 * attempt)
        return pd.DataFrame()

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
