"""Tests for product merger."""

import pytest
import pandas as pd
from src.domain.products.merger import ProductMerger
from src.domain.models import MergeResult, MergeStats


@pytest.fixture
def main_df():
    return pd.DataFrame({
        "code": ["P001", "P002", "P003"],
        "name": ["Product 1", "Product 2", "Product 3"],
        "price": ["100", "200", "300"],
        "defaultCategory": ["Cat A", "Cat B", "Cat A"],
        "source": ["core", "core", "core"],
    })


@pytest.fixture
def feed_dfs():
    feed = pd.DataFrame({
        "code": ["P001", "P004"],
        "name": ["Product 1 Updated", "Product 4 New"],
        "price": ["110", "400"],
        "defaultCategory": ["Cat A", "Cat A"],
        "source": ["gastromarket", "gastromarket"],
    })
    return {"gastromarket": feed}


class TestProductMerger:
    def test_merge_returns_merge_result(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        assert isinstance(result, MergeResult)
        assert isinstance(result.stats, MergeStats)

    def test_merge_does_not_mutate_inputs(self, main_df, feed_dfs):
        merger = ProductMerger()
        original_main = main_df.copy()
        original_feed = feed_dfs["gastromarket"].copy()
        merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        pd.testing.assert_frame_equal(main_df, original_main)
        pd.testing.assert_frame_equal(feed_dfs["gastromarket"], original_feed)

    def test_feed_products_always_included(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        codes = result.products["code"].tolist()
        # P004 from feed should be included
        assert "P004" in codes

    def test_category_filter_applied(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A"])
        codes = result.products["code"].tolist()
        # P002 is Cat B, should be excluded
        assert "P002" not in codes

    def test_stats_populated(self, main_df, feed_dfs):
        merger = ProductMerger()
        result = merger.merge(main_df, feed_dfs, selected_categories=["Cat A", "Cat B"])
        assert result.stats.created >= 0
        assert result.stats.updated >= 0
        assert result.stats.kept >= 0


def _feed(codes):
    return pd.DataFrame({
        "code": codes,
        "name": [f"Name {c}" for c in codes],
        "defaultCategory": ["Cat A"] * len(codes),
    })


class TestRemoveDiscontinued:
    """preserve_edits: only products of feeds actually fetched this run may be removed."""

    @pytest.fixture
    def mixed_main_df(self):
        return pd.DataFrame({
            "code": ["C1", "G1", "G2", "W1", "F1"],
            "name": ["Core", "Gastro 1", "Gastro 2", "Scraped", "ForG"],
            "defaultCategory": ["Cat A"] * 5,
            "source": ["core", "gastromarket", "gastromarket", "web_scraping", "forgastro"],
        })

    def test_unfetched_source_products_survive(self, mixed_main_df):
        # gastromarket download failed / disabled — its products must stay
        merger = ProductMerger()
        result = merger.merge(
            mixed_main_df, {"forgastro": _feed(["F1"])}, preserve_edits=True
        )
        assert {"C1", "G1", "G2", "W1", "F1"} <= set(result.products["code"])

    def test_fetched_source_missing_product_removed(self, mixed_main_df):
        # gastromarket fetched, G2 gone from it — G2 removed, other sources untouched
        merger = ProductMerger()
        result = merger.merge(
            mixed_main_df, {"gastromarket": _feed(["G1"])}, preserve_edits=True
        )
        codes = set(result.products["code"])
        assert "G2" not in codes
        assert {"C1", "G1", "W1", "F1"} <= codes

    def test_legacy_web_scraping_removed_only_when_both_scrapers_ran(self, mixed_main_df):
        merger = ProductMerger()
        one_scraper = {"mebella": _feed(["M1"])}
        result = merger.merge(mixed_main_df, one_scraper, preserve_edits=True)
        assert "W1" in set(result.products["code"])

        both_scrapers = {"mebella": _feed(["M1"]), "topchladenie": _feed(["T1"])}
        result = merger.merge(mixed_main_df, both_scrapers, preserve_edits=True)
        assert "W1" not in set(result.products["code"])
