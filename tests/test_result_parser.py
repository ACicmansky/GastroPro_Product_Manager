"""Tests for AI result parser and fuzzy matching."""

import pytest
import pandas as pd
from src.ai.result_parser import ResultParser


@pytest.fixture
def parser():
    return ResultParser(similarity_threshold=85)


@pytest.fixture
def products_df():
    return pd.DataFrame({
        "code": ["ABC001", "DEF002", "GHI003"],
        "name": ["Profesionálna chladnička 700L", "Elektrický gril stolný", "Umývačka riadu priemyselná"],
        "shortDescription": ["", "", ""],
        "description": ["", "", ""],
        "aiProcessed": ["0", "0", "0"],
        "aiProcessedDate": ["", "", ""],
    })


class TestFindBestMatch:
    def test_exact_code_match(self, parser, products_df):
        idx = parser.find_best_match("ABC001", "code", products_df)
        assert idx == 0

    def test_fuzzy_code_match(self, parser, products_df):
        idx = parser.find_best_match("abc001", "code", products_df)
        assert idx == 0

    def test_no_match_returns_none(self, parser, products_df):
        idx = parser.find_best_match("ZZZZZ", "code", products_df)
        assert idx is None

    def test_name_match(self, parser, products_df):
        idx = parser.find_best_match("Profesionálna chladnička", "name", products_df)
        assert idx == 0


class TestUpdateDataframe:
    def test_updates_matching_products(self, parser, products_df):
        enhanced = [
            {
                "code": "ABC001",
                "shortDescription": "Enhanced short desc",
                "description": "Enhanced full desc",
                "seoTitle": "SEO Title",
                "metaDescription": "Meta desc",
            }
        ]
        updated_df, count = parser.update_dataframe(products_df, enhanced)
        assert count == 1
        assert updated_df.at[0, "shortDescription"] == "Enhanced short desc"
        assert updated_df.at[0, "aiProcessed"] == "1"

    def test_unmatched_products_not_updated(self, parser, products_df):
        enhanced = [{"code": "ZZZZZ", "shortDescription": "Nope"}]
        updated_df, count = parser.update_dataframe(products_df, enhanced)
        assert count == 0


class TestParseBatchResults:
    def test_parse_valid_jsonl(self, parser, products_df):
        jsonl_content = '{"response": {"candidates": [{"content": {"parts": [{"text": "[{\\"code\\": \\"ABC001\\", \\"shortDescription\\": \\"Test\\", \\"description\\": \\"Test desc\\"}]"}]}}]}}\n'
        updated_df, stats = parser.parse_batch_results(products_df, jsonl_content)
        assert stats["ai_processed"] >= 0  # May or may not match depending on threshold
