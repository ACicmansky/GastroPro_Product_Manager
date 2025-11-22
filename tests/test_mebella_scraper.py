import unittest
from unittest.mock import MagicMock
from src.scrapers.mebella_scraper import MebellaScraper


class TestMebellaScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = MebellaScraper()
        # Mock the session directly on the instance
        self.scraper.session = MagicMock()

    def test_get_category_links(self):
        links = self.scraper.get_category_links()
        self.assertEqual(
            links,
            [
                "https://mebella.pl/en/product-category/table-bases/gerro-en/",
                "https://mebella.pl/en/product-category/table-bases/bow-en/",
                "https://mebella.pl/en/product-category/table-bases/conti-new-en/",
                "https://mebella.pl/en/product-category/table-bases/bea-en/",
                "https://mebella.pl/en/product-category/table-bases/unique-en/",
                "https://mebella.pl/en/product-category/table-bases/pod-en/",
                "https://mebella.pl/en/product-category/table-bases/plus-en/",
                "https://mebella.pl/en/product-category/table-bases/flat-en/",
                "https://mebella.pl/en/product-category/table-bases/oval-en/",
                "https://mebella.pl/en/product-category/table-bases/yeti-en/",
                "https://mebella.pl/en/product-category/table-bases/inox-en/",
                "https://mebella.pl/en/product-category/table-bases/brass-en/",
            ],
        )

    @unittest.mock.patch("playwright.sync_api.sync_playwright")
    def test_get_product_urls(self, mock_sync_playwright):
        # Setup mock playwright
        mock_playwright = mock_sync_playwright.return_value.__enter__.return_value
        mock_browser = mock_playwright.chromium.launch.return_value
        mock_page = mock_browser.new_page.return_value

        # Mock "Show more" button visibility (False = no button, loop breaks immediately)
        mock_page.is_visible.return_value = False

        # Mock product links found on the page
        mock_link1 = MagicMock()
        mock_link1.get_attribute.return_value = (
            "https://mebella.pl/en/produkt/test-product-1/"
        )

        mock_link2 = MagicMock()
        mock_link2.get_attribute.return_value = (
            "https://mebella.pl/en/produkt/test-product-2/"
        )

        mock_page.query_selector_all.return_value = [mock_link1, mock_link2]

        urls = self.scraper.get_product_urls(
            "https://mebella.pl/en/product-category/table-bases/gerro-en/"
        )

        # Verify Playwright was used
        mock_sync_playwright.assert_called_once()
        mock_page.goto.assert_called_with(
            "https://mebella.pl/en/product-category/table-bases/gerro-en/",
            timeout=60000,
        )

        # Verify results
        self.assertIn("https://mebella.pl/en/produkt/test-product-1/", urls)
        self.assertIn("https://mebella.pl/en/produkt/test-product-2/", urls)

    def test_scrape_product_detail(self):
        # Mock response for product page
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Realistic HTML snippet based on actual site analysis
        mock_response.content = b"""
        <html>
            <head><title>Test Product &#8211; Mebella</title></head>
            <body class="product-template-default single single-product postid-4821 wp-custom-logo theme-hello-elementor woocommerce woocommerce-page woocommerce-no-js woolentor_current_theme_ woolentor-empty-cart elementor-default elementor-template-full-width elementor-kit-5 elementor-page-5616">
                <div data-elementor-type="product" class="elementor elementor-5616 elementor-270 elementor-location-single post-4821 product type-product status-publish has-post-thumbnail product_cat-bea-en product_cat-table-bases pa_material-steel pa_wysokosc-mm-720-en first instock product-type-simple product">
                    <span class="sku">Test Product SKU</span>
                    <div class="woocommerce-product-gallery__image">
                        <a href="https://mebella.pl/img/test.jpg"></a>
                    </div>
                    <div class="elementor-widget-woocommerce-product-content">
                        <p>Test description.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        self.scraper.session.get.return_value = mock_response
        self.scraper.session.get.side_effect = None  # Reset side effect from previous test if any (though setUp resets scraper)

        data = self.scraper.scrape_product_detail(
            "https://mebella.pl/en/produkt/test-product/"
        )

        self.assertIsNotNone(data)
        self.assertEqual(data["name"], "Test Product SKU")
        self.assertTrue(data["description"].startswith("Test description."))
        self.assertIn("Material: Steel", data["description"])
        self.assertIn("Wysokosc mm: 720", data["description"])
        self.assertEqual(data["defaultImage"], "https://mebella.pl/img/test.jpg")


if __name__ == "__main__":
    unittest.main()
