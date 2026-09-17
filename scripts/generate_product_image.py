"""CLI tool to generate commercial studio product photos for gastro equipment using Gemini AI."""

import argparse
import json
import logging
import re
import sqlite3
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai.image_generator import ProductImageGenerator

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def is_valid_image(val) -> bool:
    """Check if value is a valid image URL or non-empty string."""
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "null", "false", "0", "[]", "{}", ""):
        return False
    return True


def get_product_from_db(db_path: str, code: str) -> dict:
    """Fetch product by code from SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT code, product_data FROM products WHERE code = ?", (code,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"Product with code '{code}' not found in database '{db_path}'.")

    p = json.loads(row[1])
    if not p.get("code"):
        p["code"] = row[0]
    return p


def get_first_product_without_image(db_path: str) -> dict:
    """Find the first product in database that has no images."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT code, product_data FROM products")
    img_key_re = re.compile(r"^image\d*$")

    for code, data_str in cursor.fetchall():
        if not data_str:
            continue
        try:
            p = json.loads(data_str)
            has_image = any(is_valid_image(v) for k, v in p.items() if img_key_re.match(k))
            if not has_image:
                conn.close()
                if not p.get("code"):
                    p["code"] = code
                return p
        except Exception:
            continue

    conn.close()
    raise ValueError("No products without images found in database.")


def main():
    parser = argparse.ArgumentParser(description="Generate commercial studio image for a gastro product.")
    parser.add_argument(
        "--code",
        type=str,
        default=None,
        help="Specific product code (SKU). If omitted, picks the first product without images.",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/products.db",
        help="Path to products database (default: data/products.db).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to config.json (default: config.json).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for generated images (default from config or out/generated_images).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override Gemini image model (e.g. gemini-2.5-flash-image).",
    )
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Only display the generated prompt without making an API call.",
    )

    args = parser.parse_args()

    # Load configuration
    cfg = {}
    if Path(args.config).exists():
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    if args.model:
        cfg.setdefault("image_generation", {})["model"] = args.model

    generator = ProductImageGenerator(config=cfg)

    # Fetch product
    if args.code:
        logger.info(f"Fetching product '{args.code}' from '{args.db}'...")
        product = get_product_from_db(args.db, args.code)
    else:
        logger.info(f"Searching for first product without image in '{args.db}'...")
        product = get_first_product_without_image(args.db)

    code = product.get("code", "unknown")
    name = product.get("name", "Unknown Name")
    category = product.get("defaultCategory", "Unknown Category")

    print("\n" + "=" * 60)
    print(f"PRODUCT CODE: {code}")
    print(f"NAME:         {name}")
    print(f"CATEGORY:     {category}")
    print("=" * 60 + "\n")

    prompt = generator.build_image_prompt(product)
    print("--- GENERATED PROMPT ---")
    print(prompt)
    print("------------------------\n")

    if args.prompt_only:
        print("[PROMPT-ONLY MODE] Skipping image generation.")
        return

    if not generator.is_available:
        print("ERROR: Google GenAI Client is not available or GOOGLE_API_KEY is not set.")
        sys.exit(1)

    print(f"Generating image using model '{generator.model_name}'...")
    start_time = time.time()
    result = generator.generate_image(product, output_dir=args.output_dir)
    elapsed = time.time() - start_time

    if result.get("success"):
        file_path = result.get("file_path")
        prompt_tokens = result.get("prompt_tokens", 0)
        candidate_tokens = result.get("candidate_tokens", 0)
        total_tokens = result.get("total_tokens", 0)

        # Estimate cost: Gemini 2.5 Flash image output is ~$0.0004 USD per image
        cost_usd = (prompt_tokens * 0.10 / 1_000_000) + (candidate_tokens * 0.40 / 1_000_000)

        print("\n" + "=" * 60)
        print(" IMAGE GENERATION SUCCESSFUL!")
        print(f"File Saved To:     {file_path}")
        print(f"Generation Time:   {elapsed:.2f} seconds")
        print(f"Prompt Tokens:     {prompt_tokens:,}")
        print(f"Image Tokens:      {candidate_tokens:,}")
        print(f"Total Tokens:      {total_tokens:,}")
        print(f"Estimated Cost:    ${cost_usd:.6f} USD (~{cost_usd * 100:.3f} cents)")
        print("=" * 60 + "\n")
    else:
        print("\n" + "!" * 60)
        print(" IMAGE GENERATION FAILED!")
        print(f"Error: {result.get('error')}")
        print("!" * 60 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
