"""Tests for variant service pair code logic."""

import pytest
from src.domain.products.variant_service import get_pair_code


class TestGetPairCode:
    def test_code_with_bar_suffix(self):
        assert get_pair_code("ABC123 BAR") == "ABC123"

    def test_code_with_dining_suffix(self):
        assert get_pair_code("ABC123 DINING") == "ABC123"

    def test_code_with_coffee_suffix(self):
        assert get_pair_code("ABC123 COFFEE") == "ABC123"

    def test_code_without_valid_suffix(self):
        assert get_pair_code("ABC123") == ""

    def test_code_with_invalid_suffix(self):
        assert get_pair_code("ABC123 TABLE") == ""

    def test_empty_code(self):
        assert get_pair_code("") == ""

    def test_none_code(self):
        assert get_pair_code(None) == ""

    def test_numeric_code(self):
        assert get_pair_code(12345) == ""

    def test_multi_word_code_with_suffix(self):
        assert get_pair_code("ABC 123 DEF BAR") == "ABC 123 DEF"
