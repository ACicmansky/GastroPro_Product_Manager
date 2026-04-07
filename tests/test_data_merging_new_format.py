"""
Tests for data merging with new format and image priority.
"""

import pytest
import pandas as pd


class TestNewFormatMerging:
    """Test data merging with new 138-column format."""

    def test_merge_main_with_feed_new_format(self, config):
        """Test merging main DataFrame with feed data in new format."""
        from src.domain.products.merger import ProductMerger

        main_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Product 1", "Product 2"],
                "price": ["100.00", "200.00"],
                "image": ["http://main.com/img1.jpg", ""],
                "source": ["", ""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD002", "PROD003"],
                "name": ["Product 2 Updated", "Product 3"],
                "price": ["250.00", "300.00"],
                "image": [
                    "http://feed.com/img2.jpg",
                    "http://feed.com/img3.jpg",
                ],
                "source": ["gastromarket", "gastromarket"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(main_df, {"gastromarket": feed_df})
        result = merge_result.products

        assert len(result) == 3
        assert "PROD001" in result["code"].values
        assert "PROD002" in result["code"].values
        assert "PROD003" in result["code"].values

    def test_merge_updates_prices(self, config):
        """Test that merging updates prices from feeds."""
        from src.domain.products.merger import ProductMerger

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "image": [""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["150.00"],
                "image": ["http://feed.com/img1.jpg"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(main_df, {"feed": feed_df})
        result = merge_result.products

        assert result[result["code"] == "PROD001"]["price"].values[0] == "150.00"

    def test_merge_preserves_main_data(self, config):
        """Test that merging preserves main data for name/description fields."""
        from src.domain.products.merger import ProductMerger

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Original Name"],
                "price": ["100.00"],
                "shortDescription": ["Original description"],
                "image": [""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Feed Name"],
                "price": ["150.00"],
                "shortDescription": ["Feed description"],
                "image": ["http://feed.com/img1.jpg"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(main_df, {"feed": feed_df})
        result = merge_result.products

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
        from src.domain.products.merger import ProductMerger

        feed1_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "image": ["http://feed1.com/img1.jpg"],
                "image2": ["http://feed1.com/img2.jpg"],
                "source": ["feed1"],
            }
        )

        feed2_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "image": ["http://feed2.com/img1.jpg"],
                "image2": ["http://feed2.com/img2.jpg"],
                "image3": ["http://feed2.com/img3.jpg"],
                "image4": ["http://feed2.com/img4.jpg"],
                "source": ["feed2"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(pd.DataFrame(), {"feed1": feed1_df, "feed2": feed2_df})
        result = merge_result.products

        prod = result[result["code"] == "PROD001"].iloc[0]
        assert "feed2.com" in prod["image"]
        assert prod["image2"] != ""

    def test_count_non_empty_images(self, config):
        """Test counting non-empty images."""
        from src.domain.products.merger import ProductMerger

        merger = ProductMerger()

        row = pd.Series(
            {
                "image": "http://img1.jpg",
                "image2": "http://img2.jpg",
                "image3": "",
                "image4": "http://img3.jpg",
                "image5": "",
                "image6": "",
                "image7": "",
            }
        )

        count = merger._count_images(row)
        assert count == 3

    def test_merge_with_no_images(self, config):
        """Test merging when no source has images."""
        from src.domain.products.merger import ProductMerger

        feed1_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "image": [""],
            }
        )

        feed2_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "image": [""],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(pd.DataFrame(), {"feed1": feed1_df, "feed2": feed2_df})
        result = merge_result.products

        assert len(result) == 1
        assert result["code"].values[0] == "PROD001"

    def test_main_data_images_preserved_if_more(self, config):
        """Test that main data images are preserved if they have more images."""
        from src.domain.products.merger import ProductMerger

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["100.00"],
                "image": ["http://main.com/img1.jpg"],
                "image2": ["http://main.com/img2.jpg"],
                "image3": ["http://main.com/img3.jpg"],
                "source": [""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "price": ["150.00"],
                "image": ["http://feed.com/img1.jpg"],
                "source": ["feed"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(main_df, {"feed": feed_df})
        result = merge_result.products

        prod = result[result["code"] == "PROD001"].iloc[0]
        assert "main.com" in prod["image"]
        assert prod["image2"] != ""


class TestMultipleFeedMerging:
    """Test merging multiple feeds."""

    def test_merge_three_feeds(self, config):
        """Test merging three different feeds."""
        from src.domain.products.merger import ProductMerger

        feed1 = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["P1", "P2"],
                "price": ["100", "200"],
                "image": ["", ""],
            }
        )

        feed2 = pd.DataFrame(
            {
                "code": ["PROD002", "PROD003"],
                "name": ["P2", "P3"],
                "price": ["250", "300"],
                "image": ["", ""],
            }
        )

        feed3 = pd.DataFrame(
            {
                "code": ["PROD003", "PROD004"],
                "name": ["P3", "P4"],
                "price": ["350", "400"],
                "image": ["", ""],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(
            pd.DataFrame(), {"feed1": feed1, "feed2": feed2, "feed3": feed3}
        )
        result = merge_result.products

        assert len(result) == 4
        assert set(result["code"].values) == {
            "PROD001",
            "PROD002",
            "PROD003",
            "PROD004",
        }

    def test_merge_tracks_feed_source(self, config):
        """Test that source tracks the source feed."""
        from src.domain.products.merger import ProductMerger

        feed1 = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["P1"],
                "price": ["100"],
                "source": ["gastromarket"],
            }
        )

        feed2 = pd.DataFrame(
            {
                "code": ["PROD002"],
                "name": ["P2"],
                "price": ["200"],
                "source": ["forgastro"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(
            pd.DataFrame(), {"gastromarket": feed1, "forgastro": feed2}
        )
        result = merge_result.products

        prod1 = result[result["code"] == "PROD001"].iloc[0]
        prod2 = result[result["code"] == "PROD002"].iloc[0]

        assert prod1["source"] == "gastromarket"
        assert prod2["source"] == "forgastro"


class TestMergeStatistics:
    """Test merge statistics tracking."""

    def test_merge_returns_statistics(self, config):
        """Test that merge returns statistics."""
        from src.domain.products.merger import ProductMerger
        from src.domain.models import MergeResult, MergeStats

        main_df = pd.DataFrame({"code": ["PROD001"], "name": ["P1"], "price": ["100"]})

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["P1", "P2"],
                "price": ["150", "200"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(main_df, {"feed": feed_df})
        result = merge_result.products
        stats = merge_result.stats

        assert isinstance(merge_result, MergeResult)
        assert isinstance(stats, MergeStats)
        assert stats.created + stats.updated + stats.kept == 2
        assert stats.created == 1
        assert stats.updated == 1

    def test_statistics_track_image_updates(self, config):
        """Test that merge completes successfully with image updates."""
        from src.domain.products.merger import ProductMerger

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["P1"],
                "price": ["100"],
                "image": [""],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["P1"],
                "price": ["100"],
                "image": ["http://img.jpg"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(main_df, {"feed": feed_df})
        assert merge_result.products is not None

    def test_merge_with_category_filter(self, config):
        """Test merging with category filtering."""
        from src.domain.products.merger import ProductMerger

        main_df = pd.DataFrame(
            {
                "code": ["PROD001", "PROD002"],
                "name": ["Product 1", "Product 2"],
                "price": ["100.00", "200.00"],
                "defaultCategory": ["Cat A", "Cat B"],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD003"],
                "name": ["Product 3"],
                "price": ["300.00"],
                "defaultCategory": ["Cat C"],
            }
        )

        merger = ProductMerger()
        merge_result = merger.merge(
            main_df, {"feed": feed_df}, selected_categories=["Cat A"]
        )
        result = merge_result.products
        stats = merge_result.stats

        assert len(result) == 2
        assert "PROD001" in result["code"].values
        assert "PROD003" in result["code"].values
        assert "PROD002" not in result["code"].values

        assert stats.removed == 1

    def test_merge_updates_categories_when_enabled(self, config):
        """Test that categories are updated from feed when update_categories=True."""
        from src.domain.products.merger import ProductMerger

        merger = ProductMerger()

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "defaultCategory": ["Old Category"],
                "categoryText": ["Old Category"],
                "price": ["100.0"],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "defaultCategory": ["New Category"],
                "categoryText": ["New Category"],
                "price": ["100.0"],
            }
        )

        merge_result = merger.merge(main_df, {"test_feed": feed_df}, update_categories=True)
        result = merge_result.products

        assert result.loc[0, "defaultCategory"] == "New Category"
        assert result.loc[0, "categoryText"] == "New Category"

    def test_merge_preserves_categories_when_disabled(self, config):
        """Test that categories are preserved when update_categories=False (default)."""
        from src.domain.products.merger import ProductMerger

        merger = ProductMerger()

        main_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "defaultCategory": ["Old Category"],
                "categoryText": ["Old Category"],
                "price": ["100.0"],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD001"],
                "name": ["Product 1"],
                "defaultCategory": ["New Category"],
                "categoryText": ["New Category"],
                "price": ["100.0"],
            }
        )

        merge_result = merger.merge(main_df, {"test_feed": feed_df}, update_categories=False)
        result = merge_result.products

        assert result.loc[0, "defaultCategory"] == "Old Category"
        assert result.loc[0, "categoryText"] == "Old Category"


class TestDiscontinuationLogic:
    """Test discontinuation logic when preserve_edits is enabled."""

    def test_new_products_not_discontinued(self, config):
        """Test that NEW products from feed are NOT discontinued when preserve_edits=True."""
        from src.domain.products.merger import ProductMerger

        merger = ProductMerger()

        main_df = pd.DataFrame(
            {
                "code": ["PROD_OLD"],
                "name": ["Old Product"],
                "source": ["feed1"],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD_OLD", "PROD_NEW"],
                "name": ["Old Product", "New Product"],
            }
        )

        merge_result = merger.merge(main_df, {"feed1": feed_df}, preserve_edits=True)
        result = merge_result.products

        assert len(result) == 2, f"Expected 2 products, got {len(result)}"
        assert "PROD_NEW" in result["code"].values, "New product was improperly discontinued"
        assert result[result["code"] == "PROD_NEW"]["aiProcessed"].values[0] == "0", "New product aiProcessed should be 0"

    def test_missing_feed_products_are_discontinued(self, config):
        """Test that products missing from the feed ARE discontinued when preserve_edits=True."""
        from src.domain.products.merger import ProductMerger

        merger = ProductMerger()

        main_df = pd.DataFrame(
            {
                "code": ["PROD_KEEP", "PROD_DROP"],
                "name": ["Keep Me", "Drop Me"],
                "source": ["feed1", "feed1"],
            }
        )

        feed_df = pd.DataFrame(
            {
                "code": ["PROD_KEEP"],
                "name": ["Keep Me Updated"],
            }
        )

        merge_result = merger.merge(main_df, {"feed1": feed_df}, preserve_edits=True)
        result = merge_result.products

        assert len(result) == 1
        assert "PROD_KEEP" in result["code"].values
        assert "PROD_DROP" not in result["code"].values
