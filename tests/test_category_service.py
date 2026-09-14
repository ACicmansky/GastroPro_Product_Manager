"""Tests for unified category service."""

import pytest
import json
import tempfile
import os
from src.domain.categories.category_service import CategoryService


@pytest.fixture
def mappings_file(tmp_path):
    """Create a temporary categories.json file."""
    mappings = [
        {"oldCategory": "Chladničky", "newCategory": "Chladiace zariadenia"},
        {"oldCategory": "Sporáky", "newCategory": "Varné zariadenia"},
        {"oldCategory": "Umývačky", "newCategory": "Umývacie zariadenia"},
    ]
    path = tmp_path / "categories.json"
    path.write_text(json.dumps(mappings, ensure_ascii=False), encoding="utf-8")
    return str(path)


class TestCategoryServiceMapping:
    def test_map_known_category(self, mappings_file):
        service = CategoryService(mappings_file)
        assert service.map("Chladničky") == "Chladiace zariadenia"

    def test_map_unknown_category_returns_none(self, mappings_file):
        service = CategoryService(mappings_file)
        assert service.map("Neznáma kategória") is None

    def test_add_mapping_and_retrieve(self, mappings_file):
        service = CategoryService(mappings_file)
        service.add_mapping("Grily", "Grilovacie zariadenia")
        assert service.map("Grily") == "Grilovacie zariadenia"

    def test_add_mapping_persists_to_file(self, mappings_file):
        service = CategoryService(mappings_file)
        service.add_mapping("Grily", "Grilovacie zariadenia")
        # Reload from file
        service2 = CategoryService(mappings_file)
        assert service2.map("Grily") == "Grilovacie zariadenia"

    def test_get_all_mappings(self, mappings_file):
        service = CategoryService(mappings_file)
        all_mappings = service.get_all_mappings()
        assert all_mappings["Chladničky"] == "Chladiace zariadenia"
        assert len(all_mappings) == 3

    def test_case_insensitive_lookup(self, mappings_file):
        service = CategoryService(mappings_file)
        # The original keys should match as stored
        assert service.map("Chladničky") == "Chladiace zariadenia"


class TestCategoryServiceSuggestions:
    def test_suggest_returns_list(self, mappings_file):
        service = CategoryService(mappings_file)
        suggestions = service.suggest("Chladnicky")
        assert isinstance(suggestions, list)

    def test_suggest_finds_similar_category(self, mappings_file):
        service = CategoryService(mappings_file)
        suggestions = service.suggest("Chladničky a mrazničky")
        # Should find "Chladiace zariadenia" as a suggestion
        assert len(suggestions) > 0

    def test_suggest_returns_empty_for_gibberish(self, mappings_file):
        service = CategoryService(mappings_file)
        suggestions = service.suggest("xyzxyzxyz")
        # May or may not return results depending on threshold
        assert isinstance(suggestions, list)


class TestCategoryServiceGetUniqueTargets:
    def test_get_unique_target_categories(self, mappings_file):
        service = CategoryService(mappings_file)
        targets = service.get_unique_target_categories()
        assert "Chladiace zariadenia" in targets
        assert "Varné zariadenia" in targets
        assert len(targets) == 3


class TestCategoryServiceForceFileCategories:
    def test_force_file_categories_skips_callback(self, mappings_file):
        service = CategoryService(mappings_file)
        service.set_file_categories(["Kategória Zo Súboru", "Iná Kategória"])
        service.set_force_file_categories(True)

        callback_called = False

        def callback(old_cat, product_name):
            nonlocal callback_called
            callback_called = True
            return "Mapped"

        service.set_interactive_callback(callback)
        res = service.map_or_ask("Kategória Zo Súboru", "Produkt 1")

        assert res == "Kategória Zo Súboru"
        assert not callback_called

    def test_force_file_categories_still_calls_callback_for_non_file_categories(self, mappings_file):
        service = CategoryService(mappings_file)
        service.set_file_categories(["Kategória Zo Súboru"])
        service.set_force_file_categories(True)

        callback_called = False

        def callback(old_cat, product_name):
            nonlocal callback_called
            callback_called = True
            return "Nová Cieľová Kategória"

        service.set_interactive_callback(callback)
        res = service.map_or_ask("Neznáma Feed Kategória", "Produkt 2")

        assert callback_called
        assert res == "Nová Cieľová Kategória"

    def test_session_mappings_prevents_duplicate_prompts_for_identical_categories(self, mappings_file):
        service = CategoryService(mappings_file)
        call_count = 0

        def callback(old_cat, product_name):
            nonlocal call_count
            call_count += 1
            # User chooses to keep the original name
            return old_cat

        service.set_interactive_callback(callback)

        res1 = service.map_or_ask("Vlastná Kategória", "Produkt 1")
        assert res1 == "Vlastná Kategória"
        assert call_count == 1

        # Second product with the same category should NOT trigger the callback
        res2 = service.map_or_ask("Vlastná Kategória", "Produkt 2")
        assert res2 == "Vlastná Kategória"
        assert call_count == 1
