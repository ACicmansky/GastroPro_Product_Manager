
import sys
from unittest.mock import MagicMock

# Mock dependencies
mock_pandas = MagicMock()
sys.modules["pandas"] = mock_pandas

mock_bs4 = MagicMock()
sys.modules["bs4"] = mock_bs4

mock_requests = MagicMock()
sys.modules["requests"] = mock_requests

mock_tqdm = MagicMock()
sys.modules["tqdm"] = mock_tqdm

# Mock other imports if necessary
sys.modules["PyQt5"] = MagicMock()
sys.modules["PyQt5.QtCore"] = MagicMock()
sys.modules["PyQt5.QtWidgets"] = MagicMock()

import unittest
from src.services.scraper import TopchladenieScraper

class TestCSVInjection(unittest.TestCase):
    def test_csv_injection_in_product_name(self):
        # Setup mocks
        mock_bs4.BeautifulSoup.return_value = MagicMock()
        mock_soup_instance = mock_bs4.BeautifulSoup.return_value

        scraper = TopchladenieScraper()
        scraper.session = MagicMock()

        # Malicious product name starting with '='
        malicious_name = "=1+1"

        # Mock finding the name
        mock_name_element = MagicMock()
        mock_name_element.text.strip.return_value = malicious_name

        # Mock finding the price
        mock_price_element = MagicMock()
        mock_price_element.__getitem__.return_value = "100"
        mock_price_element.get.return_value = "100"

        # Mock category div
        mock_category_div = MagicMock()
        mock_cat_link = MagicMock()
        mock_cat_link.get.return_value = "/e-shop/some-category"
        mock_category_div.find_all.return_value = [mock_cat_link]

        def select_one_side_effect(selector):
            if selector == 'h1[itemprop="name"]':
                return mock_name_element
            return None

        def find_side_effect(tag, class_=None, **kwargs):
            if tag == "p" and class_ == ['big', 'red']:
                return mock_price_element
            if tag == "h2" and kwargs.get("string") == "Hlavní parametre":
                return None
            if tag == "section" and kwargs.get("class_"):
                return None
            if tag == "div" and kwargs.get("id") == "productGallery":
                return None
            if tag == "div" and class_ == "category":
                return mock_category_div
            return None

        mock_soup_instance.select_one.side_effect = select_one_side_effect
        mock_soup_instance.find.side_effect = find_side_effect

        # Mock response
        mock_response = MagicMock()
        mock_response.content = b"content"
        scraper.session.get.return_value = mock_response

        # Execute
        data = scraper.extract_product_details("http://example.com/product")

        # Verify
        self.assertIsNotNone(data)
        # The original assertion (expecting raw malicious name) is removed.
        # We now check for the sanitized version below.

        # Check if it starts with potentially dangerous characters
        dangerous_chars = ('=', '+', '-', '@')
        # It should NOT start with dangerous chars anymore (it should be sanitized)
        # But wait, we modified it to prepend "'".
        # So we should check that it starts with "'" + malicious_name

        expected_sanitized_name = "'" + malicious_name
        self.assertEqual(data["Kat. číslo"], expected_sanitized_name)
        self.assertEqual(data["Názov tovaru"], expected_sanitized_name)

        self.assertTrue(data["Kat. číslo"].startswith("'"))
        print("Fix verified: Product name is sanitized")

if __name__ == "__main__":
    unittest.main()
