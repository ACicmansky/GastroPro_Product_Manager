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
        self.assertEqual(links, ["https://mebella.pl/en/product-category/table-bases/"])

    def test_get_product_urls(self):
        # Mock response for category page
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Minimal HTML with one product link
        mock_response.content = b"""
        <html>
            <body>
                <div class="product_title">
                    <a href="https://mebella.pl/en/produkt/test-product/">Test Product</a>
                </div>
            </body>
        </html>
        """

        # Mock the session.get to return the page first, then 404 to stop the loop
        self.scraper.session.get.side_effect = [
            mock_response,
            MagicMock(status_code=404),
        ]

        urls = self.scraper.get_product_urls(
            "https://mebella.pl/en/product-category/table-bases/"
        )
        self.assertIn("https://mebella.pl/en/produkt/test-product/", urls)

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
