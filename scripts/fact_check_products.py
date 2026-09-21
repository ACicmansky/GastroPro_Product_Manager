"""Targeted fact-checking script using Gemini with Google Search grounding on flagged anomalies."""

import argparse
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from google.genai import types

from src.ai.api_client import GeminiClient
from src.domain.specs.patcher import SpecPatcher


sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def fact_check_product(client: GeminiClient, code: str, name: str, discrepancy: str) -> Optional[Dict[str, Any]]:
    """Query Gemini with Google Search grounding to verify an ambiguous or contradictory specification."""
    if not client.is_available:
        logger.error("Gemini client is not available (check GOOGLE_API_KEY)")
        return None

    prompt = f"""You are a precise technical fact-checker for commercial catering equipment.
Product Code: {code}
Product Name: {name}
Reported Issue/Discrepancy: {discrepancy}

Search for the official manufacturer technical datasheet or catalog for this exact commercial product.
Verify and extract the exact factory specifications.

Respond with ONLY a raw JSON object (no markdown, no backticks) with these fields:
{{
    "code": "{code}",
    "verified_specs": {{
        "insulation_mm": <number or null>,
        "volume_l": <number or null>,
        "power_w": <number or null>,
        "voltage_v": <string or null>,
        "width_mm": <number or null>,
        "depth_mm": <number or null>,
        "height_mm": <number or null>,
        "temp_range": <string or null>
    }},
    "source_url": "<URL of manufacturer or primary distributor datasheet>",
    "confidence": <0.0 to 1.0>,
    "notes": "<short explanation of the verified truth>"
}}"""

    try:
        # Use live search grounding
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.0,
        )
        response = client.client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=config,
            contents=prompt,
        )
        raw_text = (response.text or "").strip()
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            data = json.loads(json_match.group(0), strict=False)
        else:
            data = json.loads(raw_text, strict=False)

        # Fallback to grounding metadata if source_url is missing
        if not data.get("source_url") and response.candidates:
            cand = response.candidates[0]
            gm = getattr(cand, "grounding_metadata", None)
            if gm and hasattr(gm, "grounding_chunks") and gm.grounding_chunks:
                for chunk in gm.grounding_chunks:
                    web = getattr(chunk, "web", None)
                    if web and getattr(web, "uri", None):
                        data["source_url"] = web.uri
                        break

        return data
    except Exception as e:
        logger.warning(f"Fact check failed for {code}: {e}")
        return None


def run_fact_checker(
    audit_csv: str = "reports/data_quality_audit.csv",
    db_path: str = "data/products.db",
    limit: int = 10,
    apply_fixes: bool = False,
):
    if not os.path.exists(audit_csv):
        logger.error(f"Audit file not found: {audit_csv}. Run scripts/audit_catalog.py first.")
        return

    with open("config.json", "r", encoding="utf-8") as f:
        app_config = json.load(f)

    client = GeminiClient(app_config)
    if not client.is_available:
        logger.error("Gemini API key is not configured in environment or .env")
        return

    df_audit = pd.read_csv(audit_csv)
    # Target high severity issues first
    target_issues = df_audit[df_audit["severity"].isin(["ERROR", "WARNING"])].head(limit)
    logger.info(f"Loaded {len(target_issues)} issues to fact-check (limit={limit})...")

    results: List[Dict[str, Any]] = []
    patcher = SpecPatcher(db_path=db_path) if apply_fixes else None

    for _, row in target_issues.iterrows():
        code = str(row["code"])
        name = str(row["name"])
        desc = str(row["description"])

        logger.info(f"Fact-checking {code}: {name} ({desc})...")
        res = fact_check_product(client, code, name, desc)
        if res:
            results.append(res)
            logger.info(f"Verified {code}: {res.get('notes')} (Source: {res.get('source_url')})")
            if apply_fixes and res.get("confidence", 0) >= 0.8:
                v_specs = res.get("verified_specs", {})
                v_specs["source_url"] = res.get("source_url")
                patcher.patch_product_in_db(
                    code, v_specs, verified_source="ai:grounded_verification", create_backup=True
                )

    # Save results
    os.makedirs("reports", exist_ok=True)
    out_json = "reports/fact_check_resolutions.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(results)} fact-check resolutions to {out_json}")


def main():
    parser = argparse.ArgumentParser(description="Targeted fact-checking with Gemini Google Search grounding")
    parser.add_argument("--audit", default="reports/data_quality_audit.csv", help="Path to audit CSV")
    parser.add_argument("--db", default="data/products.db", help="Path to SQLite DB")
    parser.add_argument("--limit", type=int, default=5, help="Max products to check")
    parser.add_argument("--apply", action="store_true", help="Apply fixes with confidence >= 0.8 to DB")
    args = parser.parse_args()

    run_fact_checker(audit_csv=args.audit, db_path=args.db, limit=args.limit, apply_fixes=args.apply)


if __name__ == "__main__":
    main()
