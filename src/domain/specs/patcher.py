"""Spec patcher for safely updating parameters and synchronizing text descriptions."""

import json
import logging
import os
import re
import shutil
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Tuple


logger = logging.getLogger(__name__)


class SpecPatcher:
    """Synchronizes verified technical specifications into product parameters and text."""

    def __init__(self, db_path: str = "data/products.db"):
        self.db_path = db_path

    @staticmethod
    def patch_product_dict(
        product_data: Dict[str, Any],
        verified_specs: Dict[str, Any],
        verified_source: str = "oem",
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Apply verified specifications to a single product dictionary.

        Returns (updated_product_data, list_of_changes).
        """
        changes: List[str] = []
        pdata = dict(product_data)

        # 1. Check and patch insulation
        new_ins = verified_specs.get("insulation_mm")
        if new_ins is not None:
            old_ins_param = pdata.get("filteringProperty:Hrúbka izolácie (mm)")
            new_ins_str = str(new_ins)
            if old_ins_param != new_ins_str:
                pdata["filteringProperty:Hrúbka izolácie (mm)"] = new_ins_str
                changes.append(f"Param Hrúbka izolácie: {old_ins_param} -> {new_ins_str}")

            # Synchronize text if there was a previous value (e.g. 70 mm -> 60 mm)
            p1 = re.compile(
                r"((?:sten[a-záä-ž]*|izol[a-záä-ž]*|hr[uú]bk[a-záä-ž]*)(?:\s+(?:s|sten[a-záä-ž]*|izol[a-záä-ž]*|hr[uú]bk[a-záä-ž]*))*\s*[:\s-]*)\b\d+\s*mm\b",
                re.IGNORECASE,
            )
            p2 = re.compile(r"\b\d+\s*mm(\s+izol[a-záä-ž]*)", re.IGNORECASE)

            for text_field in ("shortDescription", "description", "metaDescription", "seoDescription"):
                val = pdata.get(text_field)
                if val and isinstance(val, str):
                    updated = p1.sub(rf"\g<1>{new_ins_str} mm", val)
                    updated = p2.sub(rf"{new_ins_str} mm\g<1>", updated)
                    if updated != val:
                        pdata[text_field] = updated
                        changes.append(f"Text {text_field}: updated insulation references to {new_ins_str} mm")

        # 2. Dimensions
        w = verified_specs.get("width_mm")
        d = verified_specs.get("depth_mm")
        h = verified_specs.get("height_mm")
        if w is not None:
            if str(pdata.get("filteringProperty:Šírka (mm)")) != str(w):
                changes.append(f"Param Šírka (mm): {pdata.get('filteringProperty:Šírka (mm)')} -> {w}")
                pdata["filteringProperty:Šírka (mm)"] = str(w)
        if d is not None:
            if str(pdata.get("filteringProperty:Hĺbka (mm)")) != str(d):
                changes.append(f"Param Hĺbka (mm): {pdata.get('filteringProperty:Hĺbka (mm)')} -> {d}")
                pdata["filteringProperty:Hĺbka (mm)"] = str(d)
        if h is not None:
            if str(pdata.get("filteringProperty:Výška (mm)")) != str(h):
                changes.append(f"Param Výška (mm): {pdata.get('filteringProperty:Výška (mm)')} -> {h}")
                pdata["filteringProperty:Výška (mm)"] = str(h)

        # 3. Volume
        vol = verified_specs.get("volume_l")
        if vol is not None:
            if str(pdata.get("filteringProperty:Objem (l)")) != str(vol):
                changes.append(f"Param Objem (l): {pdata.get('filteringProperty:Objem (l)')} -> {vol}")
                pdata["filteringProperty:Objem (l)"] = str(vol)

        # 4. Power & Voltage
        pwr = verified_specs.get("power_w")
        if pwr is not None:
            if str(pdata.get("filteringProperty:Príkon (W)")) != str(pwr):
                changes.append(f"Param Príkon (W): {pdata.get('filteringProperty:Príkon (W)')} -> {pwr}")
                pdata["filteringProperty:Príkon (W)"] = str(pwr)

        vlt = verified_specs.get("voltage_v")
        if vlt is not None:
            if str(pdata.get("filteringProperty:Napätie (V)")) != str(vlt):
                changes.append(f"Param Napätie (V): {pdata.get('filteringProperty:Napätie (V)')} -> {vlt}")
                pdata["filteringProperty:Napätie (V)"] = str(vlt)

        # 5. Temperature range
        tr = verified_specs.get("temp_range")
        if tr is not None:
            if str(pdata.get("filteringProperty:Teplotný rozsah (°C)")) != str(tr):
                changes.append(f"Param Teplotný rozsah: {pdata.get('filteringProperty:Teplotný rozsah (°C)')} -> {tr}")
                pdata["filteringProperty:Teplotný rozsah (°C)"] = str(tr)

        # 6. Audit stamp
        if changes:
            pdata["_verified_by"] = verified_source
            pdata["_verified_date"] = datetime.now().isoformat()
            if "source_url" in verified_specs:
                pdata["_verified_url"] = verified_specs["source_url"]

        return pdata, changes

    def patch_product_in_db(
        self,
        code: str,
        verified_specs: Dict[str, Any],
        verified_source: str = "oem",
        create_backup: bool = True,
    ) -> List[str]:
        """Patch a single product directly in SQLite DB."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        if create_backup:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/backups/products_backup_before_patch_{now_str}.db"
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Created safety backup: {backup_path}")

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT product_data FROM products WHERE code = ?", (code,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Product {code} not found in {self.db_path}")

            pdata = json.loads(row[0]) if row[0] else {}
            new_pdata, changes = self.patch_product_dict(pdata, verified_specs, verified_source)

            if changes:
                new_json = json.dumps(new_pdata, ensure_ascii=False)
                cursor.execute(
                    "UPDATE products SET product_data = ? WHERE code = ?",
                    (new_json, code),
                )
                conn.commit()
                logger.info(f"Patched {code}: {', '.join(changes)}")
            else:
                logger.info(f"No changes needed for {code}.")
            return changes
        finally:
            conn.close()
