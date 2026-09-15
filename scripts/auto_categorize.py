"""Autonomous Subagent for Automatic Product Categorization.

Classifies uncategorized products against authoritative categories from
categories_with_parameters.json using Gemini 3.8 Flash, validates matches,
and updates data/products.db and the active Excel file.
"""

import io
import json
import logging
import os
import shutil
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

from google import genai
from google.genai import types
import pandas as pd
from rapidfuzz import fuzz, process

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.getcwd())

from src.config.config_loader import read_api_key  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = "data/products.db"
EXCEL_PATH = "C:/Users/Andrej/Downloads/2026_09_16_GastroPro.xlsx"
CATEGORIES_PATH = "categories_with_parameters.json"
BATCH_SIZE = 60
MAX_WORKERS = 4


def load_allowed_categories() -> Tuple[List[str], set]:
    """Load authoritative 211 categories."""
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    categories = [item["kategoria"] for item in data if "kategoria" in item]
    return categories, set(categories)


def fetch_uncategorized_products(db_path: str) -> List[Dict]:
    """Fetch products with empty defaultCategory from products.db."""
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT code, product_data FROM products")
    uncategorized = []
    for code, data_str in cur:
        try:
            p = json.loads(data_str)
        except Exception:
            continue
        cat = p.get("defaultCategory") or p.get("categoryText") or ""
        if not str(cat).strip() or str(cat).strip().lower() == "nan":
            name = str(p.get("name") or "").strip()
            desc = str(p.get("shortDescription") or p.get("description") or "").strip()[:150]
            uncategorized.append(
                {
                    "code": code,
                    "name": name,
                    "description": desc,
                }
            )
    conn.close()
    return uncategorized


def build_system_prompt(allowed_categories: List[str]) -> str:
    categories_str = "\n".join(f"- {c}" for c in allowed_categories)
    return f"""Si špičkový expert na klasifikáciu gastronomických produktov a gastro techniky.
Tvojou úlohou je zaradiť každý zadaný gastro produkt do najvhodnejšej kategórie z nižšie uvedeného zoznamu platných kategórií.

DÔLEŽITÉ PRAVIDLÁ:
1. Musíš vybrať PRESNÝ NÁZOV KATEGÓRIE zo zoznamu. Nevymýšľaj žiadne vlastné kategórie ani skratky.
2. Formát kategórie musí byť presne taký, ako v zozname (napr. 'Gastro Prevádzky a Profesionáli > Príprava surovín > Mlynčeky na mäso').
3. Vráť odpoveď ako JSON pole objektov, kde každý objekt má 'code' a 'category'.

ZOZNAM POVOLENÝCH KATEGÓRIÍ:
{categories_str}
"""


SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "category": {"type": "string"},
        },
        "required": ["code", "category"],
    },
}


def classify_batch(
    client: genai.Client,
    batch: List[Dict],
    system_instruction: str,
    allowed_categories: List[str],
    allowed_set: set,
    batch_num: int,
    total_batches: int,
) -> List[Tuple[str, str, float]]:
    """Classify a single batch of products using Gemini."""
    payload = [{"code": item["code"], "name": item["name"], "shortDesc": item["description"][:100]} for item in batch]
    user_content = json.dumps(payload, ensure_ascii=False)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[user_content],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=SCHEMA,
                ),
            )
            raw_text = response.text
            parsed = json.loads(raw_text)

            results = []
            exact_matches = 0
            fuzzy_matches = 0

            for entry in parsed:
                code = entry.get("code")
                cat = entry.get("category", "").strip()

                if cat in allowed_set:
                    results.append((code, cat, 1.0))
                    exact_matches += 1
                else:
                    match, score, _ = process.extractOne(cat, allowed_categories, scorer=fuzz.ratio)
                    if score >= 80:
                        results.append((code, match, score / 100.0))
                        fuzzy_matches += 1
                    else:
                        logger.warning(f"[{code}] Low confidence match: '{cat}' -> '{match}' ({score}%)")
                        results.append((code, match, score / 100.0))

            logger.info(
                f"[Dávka {batch_num}/{total_batches}] Spracovaných {len(results)}/{len(batch)} "
                f"(presné: {exact_matches}, fuzzy: {fuzzy_matches})"
            )
            return results

        except Exception as e:
            logger.warning(f"[Dávka {batch_num}/{total_batches}] Pokus {attempt + 1} zlyhal: {e}")
            time.sleep(2 * (attempt + 1))

    logger.error(f"[Dávka {batch_num}/{total_batches}] Zlyhali všetky pokusy!")
    return []


def update_database(db_path: str, code_to_cat: Dict[str, str]):
    """Update products.db with new categories."""
    logger.info(f"Zapisujem {len(code_to_cat)} kategórií priamo do SQLite {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    updated = 0
    cur.execute("SELECT code, product_data FROM products")
    rows = cur.fetchall()

    for code, data_str in rows:
        if code in code_to_cat:
            cat = code_to_cat[code]
            try:
                p = json.loads(data_str)
                p["defaultCategory"] = cat
                p["categoryText"] = cat
                new_data_str = json.dumps(p, ensure_ascii=False)
                cur.execute(
                    "UPDATE products SET product_data = ?, last_updated = CURRENT_TIMESTAMP WHERE code = ?",
                    (new_data_str, code),
                )
                updated += 1
            except Exception as e:
                logger.error(f"Chyba pri aktualizácii {code}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Úspešne aktualizovaných {updated} produktov v SQLite!")


def update_excel_file(excel_path: str, code_to_cat: Dict[str, str]):
    """Update Excel file with categorized products."""
    if not os.path.exists(excel_path):
        logger.info(f"Excel súbor {excel_path} neexistuje, preskakujem aktualizáciu Excelu.")
        return

    logger.info(f"Aktualizujem vstupný Excel {excel_path}...")
    # Create safety backup
    bak_path = excel_path + ".bak"
    if not os.path.exists(bak_path):
        shutil.copyfile(excel_path, bak_path)
        logger.info(f"Vytvorená záloha Excelu: {bak_path}")

    df = pd.read_excel(excel_path)
    matched = 0
    for idx, row in df.iterrows():
        code = str(row.get("code", "")).strip()
        if code in code_to_cat:
            cat = code_to_cat[code]
            df.at[idx, "defaultCategory"] = cat
            if "categoryText" in df.columns:
                df.at[idx, "categoryText"] = cat
            matched += 1

    df.to_excel(excel_path, index=False)
    logger.info(f"Úspešne aktualizovaných {matched} riadkov v Exceli {excel_path}!")


def main():
    start_time = time.time()
    api_key = read_api_key()
    if not api_key:
        logger.error("GOOGLE_API_KEY nie je nastavený!")
        return

    client = genai.Client(api_key=api_key)

    allowed_categories, allowed_set = load_allowed_categories()
    logger.info(f"Načítaných {len(allowed_categories)} autoritatívnych kategórií.")

    uncategorized = fetch_uncategorized_products(DB_PATH)
    logger.info(f"Nájdených {len(uncategorized)} nezaradených produktov na klasifikáciu.")

    if not uncategorized:
        logger.info("Všetky produkty už majú priradenú kategóriu! Žiadna práca.")
        return

    system_instruction = build_system_prompt(allowed_categories)

    batches = [uncategorized[i : i + BATCH_SIZE] for i in range(0, len(uncategorized), BATCH_SIZE)]
    total_batches = len(batches)
    logger.info(
        f"Rozdelených do {total_batches} dávok po {BATCH_SIZE} produktov. Spúšťam {MAX_WORKERS} paralelných vlákien..."
    )

    all_results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_batch = {
            executor.submit(
                classify_batch,
                client,
                batch,
                system_instruction,
                allowed_categories,
                allowed_set,
                idx + 1,
                total_batches,
            ): idx
            for idx, batch in enumerate(batches)
        }

        for future in as_completed(future_to_batch):
            batch_res = future.result()
            all_results.extend(batch_res)

    elapsed = time.time() - start_time
    logger.info(f"Klasifikácia dokončená za {elapsed:.1f} sekúnd! Získaných {len(all_results)} klasifikácií.")

    code_to_cat = {code: cat for code, cat, _ in all_results if code and cat}

    # 1. Update SQLite DB
    update_database(DB_PATH, code_to_cat)

    # 2. Update Excel File
    update_excel_file(EXCEL_PATH, code_to_cat)

    # 3. Save report
    os.makedirs("out", exist_ok=True)
    report_path = "out/categorization_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_uncategorized": len(uncategorized),
                "total_classified": len(code_to_cat),
                "elapsed_seconds": round(elapsed, 1),
                "sample_mappings": [
                    {"code": c, "category": cat, "confidence": conf} for c, cat, conf in all_results[:30]
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"Podrobný report uložený do {report_path}.")
    logger.info("=== HOTOVO! VŠETKY PRODUKTY SÚ ÚSPEŠNE ZARADENÉ DO KATEGÓRIÍ ===")


if __name__ == "__main__":
    main()
