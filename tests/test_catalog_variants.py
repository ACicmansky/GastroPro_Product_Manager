"""Tests for CatalogVariantService and variant export in OutputTransformer."""

import pandas as pd
import pytest

from src.domain.products.variant_service import CatalogVariantService
from src.domain.transform.output_transformer import OutputTransformer


class TestCatalogVariantService:
    def test_extract_dimension_from_name(self):
        service = CatalogVariantService()

        base, dim = service.extract_dimension_from_name("Nástenný odsávač pary - hranatý 2900x1200x450mm")
        assert base == "Nástenný odsávač pary - hranatý"
        assert dim == "2900x1200x450 mm"

        base, dim = service.extract_dimension_from_name("Pracovný stôl so zadným lemom  1200x600 mm")
        assert base == "Pracovný stôl so zadným lemom"
        assert dim == "1200x600 mm"

        base, dim = service.extract_dimension_from_name("Konvektomat 6x GN 1/1")
        # No 2D/3D dimension match (6x alone without secondary dimension is not matched)
        assert base is None
        assert dim is None

        base, dim = service.extract_dimension_from_name("")
        assert base is None
        assert dim is None

    def test_parse_mebella_code(self):
        service = CatalogVariantService()

        base, htype = service.parse_mebella_code("CONTI NEW 4R DINING")
        assert base == "CONTI NEW 4R"
        assert htype == "DINING"

        base, htype = service.parse_mebella_code("INOX SQUARE 10 BAR -POL-")
        assert base == "INOX SQUARE 10 -POL-"
        assert htype == "BAR"

        base, htype = service.parse_mebella_code("FLAT ROUND 09 COFFEE")
        assert base == "FLAT ROUND 09"
        assert htype == "COFFEE"

        base, htype = service.parse_mebella_code("SOMETHING ELSE")
        assert base is None
        assert htype is None

    def test_normalize_legacy_float_groups(self):
        service = CatalogVariantService()
        products = {
            "BT100-1200-1200": {
                "pairCode": "13.0",
                "name": "Mraziaci box BT100",
                "defaultCategory": "Chladenie",
            },
            "TN70-1140-1140": {
                "pairCode": "11.0",
                "name": "Chladiaci box TN70",
                "defaultCategory": "Chladenie",
            },
            "R888604": {
                "pairCode": "2.0",  # Singleton
                "name": "SPLIT agregát",
                "defaultCategory": "Chladenie",
            },
        }

        updates, stats = service.normalize_legacy_float_groups(products)
        assert stats["legacy_variants_normalized"] == 2
        assert stats["legacy_singletons_cleared"] == 1

        assert updates["BT100-1200-1200"]["pairCode"] == "BT100"
        assert updates["BT100-1200-1200"]["variantVisibility"] == "1"
        assert updates["BT100-1200-1200"]["variant:Rozmer"] == "1200x1200 mm"

        assert updates["TN70-1140-1140"]["pairCode"] == "TN70"
        assert updates["TN70-1140-1140"]["variantVisibility"] == "1"
        assert updates["TN70-1140-1140"]["variant:Rozmer"] == "1140x1140 mm"

        assert updates["R888604"]["pairCode"] == ""
        assert updates["R888604"]["variantVisibility"] == ""

    def test_pair_mebella_bases(self):
        service = CatalogVariantService()
        products = {
            "FLAT 01 BAR": {"name": "FLAT 01 BAR", "defaultCategory": "Podnože"},
            "FLAT 01 DINING": {"name": "FLAT 01 DINING", "defaultCategory": "Podnože"},
            "SINGLETON DINING": {"name": "SINGLETON DINING", "defaultCategory": "Podnože"},
        }

        updates, stats = service.pair_mebella_bases(products, excluded_codes=set())
        assert stats["mebella_families_created"] == 1
        assert stats["mebella_products_paired"] == 2

        assert updates["FLAT 01 BAR"]["pairCode"] == "FLAT 01"
        assert "Barová výška" in updates["FLAT 01 BAR"]["variant:Prevedenie"]
        assert updates["FLAT 01 BAR"]["variantVisibility"] == "1"

        assert updates["FLAT 01 DINING"]["pairCode"] == "FLAT 01"
        assert "Jedálenská výška" in updates["FLAT 01 DINING"]["variant:Prevedenie"]

        assert "SINGLETON DINING" not in updates

    def test_pair_catalog_dimension_variants(self):
        service = CatalogVariantService()
        products = {
            "ST1001": {
                "name": "Nástenný stôl 1000x600 mm",
                "defaultCategory": "Stoly",
                "manufacturer": "Stalgast",
            },
            "ST1002": {
                "name": "Nástenný stôl 1200x600 mm",
                "defaultCategory": "Stoly",
                "manufacturer": "Stalgast",
            },
            "DIFF_CAT": {
                "name": "Nástenný stôl 1400x600 mm",
                "defaultCategory": "Iná kategória",
                "manufacturer": "Stalgast",
            },
        }

        updates, stats = service.pair_catalog_dimension_variants(products, excluded_codes=set())
        assert stats["dim_groups_created"] == 1
        assert stats["dim_products_paired"] == 2

        assert updates["ST1001"]["pairCode"] == "ST100"
        assert updates["ST1001"]["variant:Rozmer"] == "1000x600 mm"
        assert updates["ST1001"]["variantVisibility"] == "1"

        assert updates["ST1002"]["pairCode"] == "ST100"
        assert updates["ST1002"]["variant:Rozmer"] == "1200x600 mm"

        assert "DIFF_CAT" not in updates

    def test_generate_all_updates_end_to_end(self):
        service = CatalogVariantService()
        products = {
            "BT100-1200-1200": {
                "pairCode": "13.0",
                "name": "Mraziaci box BT100",
                "defaultCategory": "Chladenie",
                "manufacturer": "JKS",
            },
            "CONTI BAR": {
                "pairCode": "",
                "name": "CONTI BAR",
                "defaultCategory": "Podnože",
                "manufacturer": "Mebella",
            },
            "CONTI DINING": {
                "pairCode": "",
                "name": "CONTI DINING",
                "defaultCategory": "Podnože",
                "manufacturer": "Mebella",
            },
            "STANDALONE": {
                "pairCode": "",
                "name": "Unikátna fritéza 10L",
                "defaultCategory": "Varenie",
                "manufacturer": "Roller Grill",
            },
        }

        updates, stats, (p1, p2, p3) = service.generate_all_updates(products)
        assert stats["total_products_paired"] == 3
        assert updates["BT100-1200-1200"]["pairCode"] == "BT100"
        assert updates["CONTI BAR"]["pairCode"] == "CONTI"
        assert updates["CONTI DINING"]["pairCode"] == "CONTI"
        assert "STANDALONE" not in updates


class TestOutputTransformerVariantForwarding:
    def test_variant_parameters_forwarded_and_visibility_set(self):
        config = {
            "output_mapping": {
                "mappings": {
                    "code": "code",
                    "pairCode": "pairCode",
                    "name": "name",
                    "variantVisibility": "variantVisibility",
                },
                "special_mappings": {},
                "default_values": {"currency": "EUR"},
                "new_output_columns": ["code", "pairCode", "name", "variantVisibility"],
            }
        }
        transformer = OutputTransformer(config)

        input_df = pd.DataFrame(
            [
                {
                    "code": "CONTI BAR",
                    "pairCode": "CONTI",
                    "name": "CONTI BAR",
                    "variantVisibility": "",
                    "variant:Prevedenie": "Barová výška",
                },
                {
                    "code": "STANDALONE",
                    "pairCode": "",
                    "name": "Fritéza",
                    "variantVisibility": "",
                },
            ]
        )

        output_df = transformer.transform(input_df)

        # variant:Prevedenie must be preserved in output
        assert "variant:Prevedenie" in output_df.columns
        assert output_df.loc[0, "variant:Prevedenie"] == "Barová výška"

        # variantVisibility must be "1" for paired item, empty for standalone
        assert output_df.loc[0, "variantVisibility"] == "1"
        assert output_df.loc[1, "variantVisibility"] != "1"
