"""Batch image generation script using Google GenAI Batch API.

Generates commercial studio product photography for products lacking images,
saves them named by product code in out/generated_images/{code}.png,
and tracks token usage and costs.
"""

import argparse
import base64
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.ai.image_generator import ProductImageGenerator, sanitize_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def is_valid_image(val: Any) -> bool:
    """Check if value is a valid, non-empty image string."""
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "null", "false", "0", "[]", "{}", ""):
        return False
    return True


def get_products_without_images(db_path: str, limit: int = 0) -> List[Dict[str, Any]]:
    """Query SQLite database for all products missing an image."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT code, product_data FROM products")
    img_re = re.compile(r"^image\d*$")

    products = []
    for code, data_str in cur.fetchall():
        if not data_str:
            continue
        try:
            p = json.loads(data_str)
            has_img = any(is_valid_image(v) for k, v in p.items() if img_re.match(k))
            if not has_img:
                if not p.get("code"):
                    p["code"] = code
                products.append(p)
                if limit and len(products) >= limit:
                    break
        except Exception:
            continue

    conn.close()
    return products


def build_batch_requests(
    products: List[Dict[str, Any]],
    generator: ProductImageGenerator,
    existing_images_dir: Path,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Build Batch JSONL requests with 'key' as product code.

    Skips products whose image file already exists.
    """
    requests = []
    skipped_existing = []

    for p in products:
        code = str(p.get("code", "")).strip()
        if not code:
            continue

        safe_code = sanitize_filename(code)
        target_file = existing_images_dir / f"{safe_code}.png"
        if target_file.exists() and target_file.stat().st_size > 1000:
            skipped_existing.append(code)
            continue

        prompt = generator.build_image_prompt(p)
        req_body = {
            "key": code,
            "request": {
                "contents": [{"parts": [{"text": prompt}]}],
                "generation_config": {"response_modalities": ["IMAGE"]},
            },
        }
        requests.append(req_body)

    return requests, skipped_existing


def submit_batch_job(
    client: genai.Client,
    jsonl_path: Path,
    model_name: str,
) -> Any:
    """Upload JSONL file and create Google GenAI Batch Job."""
    logger.info(f"Uploading batch file '{jsonl_path}' ({jsonl_path.stat().st_size:,} bytes)...")
    uploaded = client.files.upload(
        file=str(jsonl_path),
        config=types.UploadFileConfig(mime_type="application/jsonl"),
    )
    logger.info(f"Uploaded file name: {uploaded.name}")

    logger.info(f"Submitting Batch Job for model '{model_name}'...")
    batch_job = client.batches.create(
        model=model_name,
        src=uploaded.name,
    )
    logger.info(f"Batch Job submitted: {batch_job.name} (Initial state: {batch_job.state})")
    return batch_job


def poll_batch_job(client: genai.Client, job_name: str, poll_interval: int = 20) -> Any:
    """Poll batch job until completion and return final BatchJob object."""
    start_time = time.time()
    last_state = None

    while True:
        job = client.batches.get(name=job_name)
        state_str = str(job.state)

        if state_str != last_state:
            elapsed = int(time.time() - start_time)
            logger.info(f"Batch Job {job_name} state: {state_str} (Elapsed: {elapsed}s)")
            last_state = state_str

        if "SUCCEEDED" in state_str:
            return job
        elif "FAILED" in state_str:
            err = getattr(job, "error", "Unknown error")
            raise RuntimeError(f"Batch Job failed: {err}")
        elif "CANCELLED" in state_str:
            raise RuntimeError("Batch Job was cancelled.")

        time.sleep(poll_interval)


def extract_images_from_batch_results(
    client: genai.Client,
    output_file_name: str,
    output_dir: Path,
    code_order: List[str],
) -> Dict[str, Any]:
    """Download batch results and decode base64 PNG images to disk."""
    logger.info(f"Downloading batch results from '{output_file_name}'...")
    content_bytes = client.files.download(file=output_file_name)
    content_text = content_bytes.decode("utf-8", errors="ignore")

    output_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    failed_count = 0
    prompt_tokens_total = 0
    candidate_tokens_total = 0
    total_tokens_all = 0

    lines = [line.strip() for line in content_text.splitlines() if line.strip()]
    logger.info(f"Processing {len(lines)} result lines from batch output...")

    for idx, line in enumerate(lines):
        try:
            record = json.loads(line)
        except Exception as e:
            logger.error(f"Line {idx}: Failed to parse JSON: {e}")
            failed_count += 1
            continue

        # Extract code from key, falling back to index in code_order
        code = record.get("key")
        if not code and idx < len(code_order):
            code = code_order[idx]
        if not code:
            code = f"unknown_{idx}"

        safe_code = sanitize_filename(code)
        out_path = output_dir / f"{safe_code}.png"

        # Check for errors in the record
        if "error" in record and record["error"]:
            logger.error(f"Error for product '{code}': {record['error']}")
            failed_count += 1
            continue

        response = record.get("response", {})
        candidates = response.get("candidates", [])
        if not candidates:
            logger.error(f"No candidates for product '{code}'")
            failed_count += 1
            continue

        # Token usage
        usage = response.get("usageMetadata") or {}
        p_tok = usage.get("promptTokenCount", 0)
        c_tok = usage.get("candidatesTokenCount", 0)
        t_tok = usage.get("totalTokenCount", 0)
        prompt_tokens_total += p_tok
        candidate_tokens_total += c_tok
        total_tokens_all += t_tok

        # Extract image bytes
        image_bytes = None
        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                b64_data = inline["data"]
                image_bytes = base64.b64decode(b64_data)
                break

        if not image_bytes:
            logger.error(f"No image bytes found in response for product '{code}'")
            failed_count += 1
            continue

        out_path.write_bytes(image_bytes)
        saved_count += 1
        if saved_count % 25 == 0 or saved_count == len(lines):
            logger.info(f"Saved {saved_count}/{len(lines)} images to '{output_dir}'...")

    return {
        "saved_count": saved_count,
        "failed_count": failed_count,
        "prompt_tokens": prompt_tokens_total,
        "candidate_tokens": candidate_tokens_total,
        "total_tokens": total_tokens_all,
    }


def update_database_with_generated_images(db_path: str, output_dir: Path) -> int:
    """Update products in database that are missing images with generated PNG paths."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT code, product_data FROM products")

    img_re = re.compile(r"^image\d*$")
    updated_count = 0

    for code, data_str in cur.fetchall():
        if not code or not data_str:
            continue
        try:
            p = json.loads(data_str)
            has_img = any(is_valid_image(v) for k, v in p.items() if img_re.match(k))
            if has_img:
                continue

            safe_code = sanitize_filename(code)
            img_file = output_dir / f"{safe_code}.png"
            if img_file.exists():
                p["image"] = str(img_file).replace("\\", "/")
                cur.execute(
                    "UPDATE products SET product_data = ?, last_updated = ? WHERE code = ?",
                    (json.dumps(p, ensure_ascii=False), datetime.now().isoformat(), code),
                )
                updated_count += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    return updated_count


def main():
    parser = argparse.ArgumentParser(description="Batch generate commercial product images for gastro catalog.")
    parser.add_argument("--db", type=str, default="data/products.db", help="Path to products SQLite database.")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config.json.")
    parser.add_argument("--output-dir", type=str, default="out/generated_images", help="Target directory for PNGs.")
    parser.add_argument(
        "--model", type=str, default=None, help="Override image model (default: gemini-2.5-flash-image)."
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional limit of products to process.")
    parser.add_argument("--dry-run", action="store_true", help="Generate requests JSONL only without calling API.")
    parser.add_argument(
        "--resume-job", type=str, default=None, help="Resume monitoring an already-created batch job name."
    )
    parser.add_argument("--update-db", action="store_true", help="Update database with generated image paths.")

    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    cfg = {}
    if Path(args.config).exists():
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    model_name = args.model or cfg.get("image_generation", {}).get("model", "gemini-2.5-flash-image")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=api_key)
    generator = ProductImageGenerator(config=cfg, api_key=api_key)

    # 1. Check if resuming existing batch job
    if args.resume_job:
        logger.info(f"Resuming existing batch job: {args.resume_job}...")
        completed_job = poll_batch_job(client, args.resume_job)
        dest_file = completed_job.dest.file_name
        summary = extract_images_from_batch_results(client, dest_file, output_dir, [])
        print("\n" + "=" * 60)
        print(f"BATCH JOB RESUMED & COMPLETED: {args.resume_job}")
        print(f"Saved Images:    {summary['saved_count']}")
        print(f"Failed Images:   {summary['failed_count']}")
        print(f"Total Tokens:    {summary['total_tokens']:,}")
        print("=" * 60 + "\n")
        return

    # 2. Query products without images
    logger.info(f"Scanning '{args.db}' for products lacking images...")
    missing_products = get_products_without_images(args.db, limit=args.limit)
    total_missing = len(missing_products)
    logger.info(f"Found {total_missing} products without images in database.")

    if total_missing == 0:
        logger.info("All products already have images. Nothing to generate!")
        return

    # 3. Build Batch requests
    requests, skipped = build_batch_requests(missing_products, generator, output_dir)
    logger.info(f"Built {len(requests)} batch requests (Skipped {len(skipped)} already generated).")

    if not requests:
        logger.info("All missing products already have generated images in output directory.")
        if args.update_db:
            cnt = update_database_with_generated_images(args.db, output_dir)
            logger.info(f"Updated {cnt} products in database with existing generated images.")
        return

    # 4. Save JSONL payload
    batch_dir = Path("out/batch_requests")
    batch_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = batch_dir / f"image_requests_{ts}.jsonl"

    logger.info(f"Writing {len(requests)} requests to '{jsonl_path}'...")
    code_order = []
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for req in requests:
            code_order.append(req["key"])
            f.write(json.dumps(req, ensure_ascii=False) + "\n")

    if args.dry_run:
        print(f"\n[DRY RUN COMPLETE] Created '{jsonl_path}' with {len(requests)} items. No API call made.")
        return

    # 5. Submit batch job
    job = submit_batch_job(client, jsonl_path, model_name)
    job_name = job.name

    # Save job info locally in case of interruption
    job_info_path = batch_dir / f"job_info_{ts}.json"
    with open(job_info_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "job_name": job_name,
                "created_at": datetime.now().isoformat(),
                "model": model_name,
                "product_count": len(requests),
                "jsonl_path": str(jsonl_path),
                "codes": code_order,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 60)
    print(f"BATCH JOB LAUNCHED: {job_name}")
    print(f"Products to generate: {len(requests)}")
    print("To resume monitoring later, run:")
    print(f"  uv run python scripts/batch_generate_images.py --resume-job {job_name}")
    print("=" * 60 + "\n")

    # 6. Poll until completion
    completed_job = poll_batch_job(client, job_name)
    dest_file = completed_job.dest.file_name

    # 7. Extract images
    summary = extract_images_from_batch_results(client, dest_file, output_dir, code_order)

    # 8. Optional database update
    db_updated = 0
    if args.update_db:
        db_updated = update_database_with_generated_images(args.db, output_dir)

    # 9. Print final statistics
    p_tok = summary["prompt_tokens"]
    c_tok = summary["candidate_tokens"]
    t_tok = summary["total_tokens"]
    cost_usd = (p_tok * 0.10 / 1_000_000) + (c_tok * 0.40 / 1_000_000)

    print("\n" + "=" * 60)
    print(" BATCH IMAGE GENERATION FINISHED!")
    print(f"Saved Images:       {summary['saved_count']}")
    print(f"Failed Images:      {summary['failed_count']}")
    print(f"Output Directory:   {output_dir}")
    print(f"Prompt Tokens:      {p_tok:,}")
    print(f"Image Tokens:       {c_tok:,}")
    print(f"Total Tokens:       {t_tok:,}")
    print(f"Total Cost:         ${cost_usd:.4f} USD (~{cost_usd * 100:.2f} cents)")
    if args.update_db:
        print(f"Database Updated:   {db_updated} products updated with local image paths.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
