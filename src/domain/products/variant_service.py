"""Domain service for catalog product variant detection, pairing and parameter extraction."""

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Canonical mapping for legacy float pairCode groups imported from old format
FLOAT_GROUP_MAP: Dict[str, str] = {
    "13.0": "BT100",
    "11.0": "TN70",
    "21.0": "GAUS10",
    "17.0": "GAUSD1S",
    "15.0": "GAUSD2S",
    "19.0": "GAUSP21",
    "20.0": "GAUS21",
    "18.0": "GAUSD10",
    "12.0": "T-PZ-1",
    "16.0": "GAUSD21",
    "14.0": "GADL31",
    "1.0": "R88861",
    "3.0": "R88841",
    "5.0": "R88840",
    "8.0": "R88821",
    "10.0": "R88820",
    "7.0": "R88821-HIGH",
    "9.0": "R88820-HIGH",
    # Singletons (count=1 in catalog) — not variants, pairCode must be cleared
    "2.0": "",
    "4.0": "",
    "6.0": "",
}

# Mebella height types and Slovak display labels for Shoptet variant dropdown
MEBELLA_HEIGHT_TYPES: Set[str] = {"BAR", "DINING", "COFFEE", "LOUNGE"}

MEBELLA_HEIGHT_LABELS: Dict[str, str] = {
    "BAR": "Barová výška (cca 110 cm)",
    "DINING": "Štandardná / Jedálenská výška (cca 72 cm)",
    "COFFEE": "Konferenčná / Coffee výška (cca 45 cm)",
    "LOUNGE": "Lounge výška",
}


class CatalogVariantService:
    """Service to identify, normalize, and pair product variants in catalog."""

    @staticmethod
    def extract_dimension_from_name(name: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract base name and normalized dimension string from product name.

        Example:
            'Nástenný odsávač pary - hranatý 2900x1200x450mm'
            -> ('Nástenný odsávač pary - hranatý', '2900x1200x450 mm')
        """
        if not name:
            return None, None

        # Match dimension expressions like 2900x1200x450mm, 1000x600 mm, 1000x600
        match = re.search(r"(\d+)\s*[xX*×]\s*(\d+)(?:\s*[xX*×]\s*(\d+))?\s*(?:mm)?", name)
        if not match:
            return None, None

        dim_raw = match.group(0).strip()
        dim_norm = re.sub(r"\s*[xX*×]\s*", "x", dim_raw)
        if not dim_norm.endswith("mm"):
            dim_norm = f"{dim_norm} mm"
        else:
            dim_norm = re.sub(r"\s*mm$", " mm", dim_norm)

        base_name = name.replace(dim_raw, "").strip()
        base_name = re.sub(r"\s+", " ", base_name).strip(" ,-–")
        return base_name, dim_norm

    @staticmethod
    def parse_mebella_code(code: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse Mebella code into base model and height type.

        Example:
            'CONTI NEW 4R DINING' -> ('CONTI NEW 4R', 'DINING')
            'INOX SQUARE 10 BAR -POL-' -> ('INOX SQUARE 10 -POL-', 'BAR')
        """
        if not code:
            return None, None

        pattern = r"\b(" + "|".join(sorted(MEBELLA_HEIGHT_TYPES)) + r")\b"
        match = re.search(pattern, code, flags=re.IGNORECASE)
        if not match:
            return None, None

        htype = match.group(1).upper()
        base = re.sub(pattern, "", code, count=1, flags=re.IGNORECASE)
        base = re.sub(r"\s+", " ", base).strip()
        return base, htype

    def normalize_legacy_float_groups(
        self, products: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
        """Normalize legacy float pairCode entries ('1.0' - '21.0').

        Returns:
            Tuple of (updates_dict, stats_dict)
        """
        updates: Dict[str, Dict[str, Any]] = {}
        cleared_singletons = 0
        normalized_variants = 0

        for code, data in products.items():
            pair_code = str(data.get("pairCode", "")).strip()
            if pair_code in FLOAT_GROUP_MAP:
                new_pair = FLOAT_GROUP_MAP[pair_code]
                upd: Dict[str, Any] = {"pairCode": new_pair}

                if new_pair:
                    normalized_variants += 1
                    upd["variantVisibility"] = "1"

                    # Extract dimensions for cold rooms and cutlery cabinets
                    if new_pair in ("BT100", "TN70", "T-PZ-1"):
                        m = re.search(r"-(\d+)-(\d+)$", code)
                        if m:
                            upd["variant:Rozmer"] = f"{m.group(1)}x{m.group(2)} mm"
                    elif new_pair.startswith("GAUS") or new_pair.startswith("GADL"):
                        # Extract dimension from name or code
                        m_name = re.search(r"(\d{3,4})\s*[xX*×]\s*(\d{3})", data.get("name", ""))
                        if m_name:
                            upd["variant:Rozmer"] = f"{m_name.group(1)}x{m_name.group(2)} mm"
                        else:
                            m_code = re.search(r"(\d{4})(\d{2})$", code)
                            if m_code:
                                upd["variant:Rozmer"] = f"{m_code.group(1)}x{int(m_code.group(2)) * 10} mm"
                else:
                    cleared_singletons += 1
                    upd["variantVisibility"] = ""

                updates[code] = upd

        stats = {
            "legacy_float_updated": len(updates),
            "legacy_singletons_cleared": cleared_singletons,
            "legacy_variants_normalized": normalized_variants,
        }
        return updates, stats

    def pair_mebella_bases(
        self, products: Dict[str, Dict[str, Any]], excluded_codes: Set[str]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
        """Group and pair Mebella table bases by base model and height.

        Returns:
            Tuple of (updates_dict, stats_dict)
        """
        candidates: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = defaultdict(list)

        for code, data in products.items():
            if code in excluded_codes:
                continue
            base, htype = self.parse_mebella_code(code)
            if base and htype:
                candidates[base].append((code, htype, data))

        updates: Dict[str, Dict[str, Any]] = {}
        multi_families = 0

        for base, items in candidates.items():
            # Only form variant group if at least 2 variants exist
            if len(items) > 1:
                multi_families += 1
                for code, htype, _ in items:
                    updates[code] = {
                        "pairCode": base,
                        "variant:Prevedenie": MEBELLA_HEIGHT_LABELS.get(htype, htype),
                        "variantVisibility": "1",
                    }

        stats = {
            "mebella_families_created": multi_families,
            "mebella_products_paired": len(updates),
        }
        return updates, stats

    def pair_catalog_dimension_variants(
        self, products: Dict[str, Dict[str, Any]], excluded_codes: Set[str]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
        """Pair general catalog products differing only by dimension in their name.

        Ensures strict uniqueness of extracted dimensions within each variant family.

        Returns:
            Tuple of (updates_dict, stats_dict)
        """
        cat_groups: Dict[Tuple[str, str, str], List[Tuple[str, str, Dict[str, Any]]]] = defaultdict(list)

        for code, data in products.items():
            if code in excluded_codes:
                continue

            name = str(data.get("name", "")).strip()
            cat = str(data.get("defaultCategory", "")).strip()
            mfr = str(data.get("manufacturer", "")).strip()

            base_name, dim_str = self.extract_dimension_from_name(name)
            if base_name and len(base_name) >= 8 and dim_str:
                key = (cat, mfr, base_name.lower())
                cat_groups[key].append((code, dim_str, data))

        updates: Dict[str, Dict[str, Any]] = {}
        groups_created = 0

        for (cat, mfr, _), items in cat_groups.items():
            dims = [it[1] for it in items]
            # Must have >= 2 items and ALL dimensions must be distinct
            if len(items) >= 2 and len(dims) == len(set(dims)):
                groups_created += 1
                codes = [it[0] for it in items]

                # Select canonical pairCode: longest common prefix (min 5 chars), else first code
                common = []
                for chars in zip(*codes):
                    if all(c == chars[0] for c in chars):
                        common.append(chars[0])
                    else:
                        break
                prefix = "".join(common).strip("-_ ")
                canonical_pair = prefix if len(prefix) >= 5 else codes[0]

                for code, dim_str, _ in items:
                    updates[code] = {
                        "pairCode": canonical_pair,
                        "variant:Rozmer": dim_str,
                        "variantVisibility": "1",
                    }

        stats = {
            "dim_groups_created": groups_created,
            "dim_products_paired": len(updates),
        }
        return updates, stats

    def generate_all_updates(
        self, products: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """Generate comprehensive variant updates for the entire catalog.

        Applies 3 sequential stages:
        1. Legacy float group normalization.
        2. Mebella table base height pairing.
        3. General catalog dimension-variant clustering.
        """
        # Stage 1
        part1_updates, s1 = self.normalize_legacy_float_groups(products)
        excluded: Set[str] = set(part1_updates.keys())

        # Stage 2
        part2_updates, s2 = self.pair_mebella_bases(products, excluded_codes=excluded)
        excluded.update(part2_updates.keys())

        # Stage 3
        part3_updates, s3 = self.pair_catalog_dimension_variants(products, excluded_codes=excluded)

        all_updates: Dict[str, Dict[str, Any]] = {}
        all_updates.update(part1_updates)
        all_updates.update(part2_updates)
        all_updates.update(part3_updates)

        total_paired = sum(1 for u in all_updates.values() if u.get("pairCode"))
        stats = {
            **s1,
            **s2,
            **s3,
            "total_products_updated": len(all_updates),
            "total_products_paired": total_paired,
            "total_catalog_products": len(products),
            "pairing_percentage": round(total_paired / len(products) * 100, 2) if products else 0.0,
        }

        breakdown = (part1_updates, part2_updates, part3_updates)
        return all_updates, stats, breakdown
