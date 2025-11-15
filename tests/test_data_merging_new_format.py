"""
Tests for data merging with new format and image priority.
Following TDD approach: Write tests first, then implement.
"""

import pytest
import pandas as pd


class TestNewFormatMerging:
    """Test data merging with new 147-column format."""

    def test_merge_main_with_feed_new_format(self, config):
        """Test merging main DataFrame with feed data in new format."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        # Main data
        main_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Product 1", "Product 2"],
                "price": ["100.00", "200.00"],
                "defaultImage": ["http://main.com/img1.jpg", ""],
                "xmlFeedName": ["", ""],
            }
        )

        # Feed data
        feed_df = pd.DataFrame(
            {
                "code": ["PROD002", "PROD003"],
                "name": ["Product 2 Updated", "Product 3"],
                "price": ["250.00", "300.00"],
                "defaultImage": [
                    "http://feed.com/img2.jpg",
                    "http://feed.com/img3.jpg",
                ],
                "xmlFeedName": ["gastromarket", "gastromarket"],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(main_df, {"gastromarket": feed_df})

        # Should have all 3 products
        assert len(result) == 3
        assert "PROD001" in result["code"].values
        assert "PROD002" in result["code"].values
        assert "PROD003" in result["code"].values

    def test_merge_updates_prices(self, config):
        """Test that merging updates prices from feeds."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "defaultImage": [""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["150.00"],
                "defaultImage": ["http://feed.com/img1.jpg"],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(main_df, {"feed": feed_df})

        # Price should be updated
        assert result[result["code"] == "PROD001"]["price"].values[0] == "150.00"

    def test_merge_preserves_main_data(self, config):
        """Test that merging preserves main data for non-price fields."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Original Name"],
                "price": ["100.00"],
                "shortDescription": ["Original description"],
                "defaultImage": [""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Feed Name"],
                "price": ["150.00"],
                "shortDescription": ["Feed description"],
                "defaultImage": ["http://feed.com/img1.jpg"],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(main_df, {"feed": feed_df})

        # Name and description should be preserved from main
        assert result[result["code"] == "PROD001"]["name"].values[0] == "Original Name"
        assert (
            result[result["code"] == "PROD001"]["shortDescription"].values[0]
            == "Original description"
        )


class TestImagePriorityMerging:
    """Test image priority merging logic."""

    def test_prefer_source_with_more_images(self, config):
        """Test that source with more images is preferred."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        # Feed 1 with 2 images
        feed1_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "defaultImage": ["http://feed1.com/img1.jpg"],
                "image": ["http://feed1.com/img2.jpg"],
                "image2": [""],
                "xmlFeedName": ["feed1"],
            }
        )

        # Feed 2 with 4 images
        feed2_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "defaultImage": ["http://feed2.com/img1.jpg"],
                "image": ["http://feed2.com/img2.jpg"],
                "image2": ["http://feed2.com/img3.jpg"],
                "image3": ["http://feed2.com/img4.jpg"],
                "xmlFeedName": ["feed2"],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(pd.DataFrame(), {"feed1": feed1_df, "feed2": feed2_df})

        # Should use images from feed2 (more images)
        prod = result[result["code"] == "PROD001"].iloc[0]
        assert "feed2.com" in prod["defaultImage"]
        assert prod["image2"] != ""  # Should have 3rd image

    def test_count_non_empty_images(self, config):
        """Test counting non-empty images."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        merger = DataMergerNewFormat(config)

        row = pd.Series(
            {
                "defaultImage": "http://img1.jpg",
                "image": "http://img2.jpg",
                "image2": "",
                "image3": "http://img3.jpg",
                "image4": "",
                "image5": "",
                "image6": "",
                "image7": "",
            }
        )

        count = merger._count_images(row)
        assert count == 3

    def test_merge_with_no_images(self, config):
        """Test merging when no source has images."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        feed1_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "defaultImage": [""],
                "image": [""],
            }
        )

        feed2_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "defaultImage": [""],
                "image": [""],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(pd.DataFrame(), {"feed1": feed1_df, "feed2": feed2_df})

        # Should still merge successfully
        assert len(result) == 1
        assert result["code"].values[0] == "PROD001"

    def test_main_data_images_preserved_if_more(self, config):
        """Test that main data images are preserved if they have more images."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        # Main with 3 images
        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "defaultImage": ["http://main.com/img1.jpg"],
                "image": ["http://main.com/img2.jpg"],
                "image2": ["http://main.com/img3.jpg"],
                "xmlFeedName": [""],
            }
        )

        # Feed with only 1 image
        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["150.00"],
                "defaultImage": ["http://feed.com/img1.jpg"],
                "image": [""],
                "xmlFeedName": ["feed"],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(main_df, {"feed": feed_df})

        # Should keep main images (more images)
        prod = result[result["code"] == "PROD001"].iloc[0]
        assert "main.com" in prod["defaultImage"]
        assert prod["image2"] != ""  # Should have 3rd image


class TestMultipleFeedMerging:
    """Test merging multiple feeds."""

    def test_merge_three_feeds(self, config):
        """Test merging three different feeds."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        feed1 = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["P1", "P2"],
                "price": ["100", "200"],
                "defaultImage": ["", ""],
            }
        )

        feed2 = pd.DataFrame(
            {
                "code": ["PROD002", "PROD003"],
                "name": ["P2", "P3"],
                "price": ["250", "300"],
                "defaultImage": ["", ""],
            }
        )

        feed3 = pd.DataFrame(
            {
                "code": ["PROD003", "PROD004"],
                "name": ["P3", "P4"],
                "price": ["350", "400"],
                "defaultImage": ["", ""],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(
            pd.DataFrame(), {"feed1": feed1, "feed2": feed2, "feed3": feed3}
        )

        # Should have all 4 unique products
        assert len(result) == 4
        assert set(result["code"].values) == {
            "PROD001",
            "PROD002",
            "PROD003",
            "PROD004",
        }

    def test_merge_tracks_feed_source(self, config):
        """Test that xmlFeedName tracks the source feed."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        feed1 = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["P1"],
                "price": ["100"],
                "xmlFeedName": ["gastromarket"],
            }
        )

        feed2 = pd.DataFrame(
            {
                "code": ["PROD002"],
                "name": ["P2"],
                "price": ["200"],
                "xmlFeedName": ["forgastro"],
            }
        )

        merger = DataMergerNewFormat(config)
        result = merger.merge(
            pd.DataFrame(), {"gastromarket": feed1, "forgastro": feed2}
        )

        # Each product should have its feed name
        prod1 = result[result["code"] == "PROD001"].iloc[0]
        prod2 = result[result["code"] == "PROD002"].iloc[0]

        assert prod1["xmlFeedName"] == "gastromarket"
        assert prod2["xmlFeedName"] == "forgastro"


class TestMergeStatistics:
    """Test merge statistics tracking."""

    def test_merge_returns_statistics(self, config):
        """Test that merge returns statistics."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        main_df = pd.DataFrame({"code": ["PROD001"], "name": ["P1"], "price": ["100"]})

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["P1", "P2"],
                "price": ["150", "200"],
            }
        )

        merger = DataMergerNewFormat(config)
        result, stats = merger.merge_with_stats(main_df, {"feed": feed_df})

        # Should have statistics
        assert "total_products" in stats
        assert "new_products" in stats
        assert "updated_products" in stats
        assert stats["total_products"] == 2
        assert stats["new_products"] == 1
        assert stats["updated_products"] == 1

    def test_statistics_track_image_updates(self, config):
        """Test that statistics track image updates."""
        from src.mergers.data_merger_new_format import DataMergerNewFormat

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["P1"],
                "price": ["100"],
                "defaultImage": [""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["P1"],
                "price": ["100"],
                "defaultImage": ["http://img.jpg"],
                "image": ["http://img2.jpg"],
            }
        )

        merger = DataMergerNewFormat(config)
        result, stats = merger.merge_with_stats(main_df, {"feed": feed_df})

        # Should track image updates
        assert "products_with_images_updated" in stats
        assert stats["products_with_images_updated"] >= 0
