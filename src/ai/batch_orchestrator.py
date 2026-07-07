"""Batch processing orchestration for AI enhancement."""

import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable

import pandas as pd

from .api_client import GeminiClient
from .result_parser import ResultParser
from .prompts import (
    build_response_schema,
    create_params_only_prompt,
    create_system_prompt,
    create_system_prompt_no_dimensions,
    load_category_parameters,
)
from src.data.database.batch_job_db import BatchJobDB

logger = logging.getLogger(__name__)


class BatchOrchestrator:
    """Manages batch AI processing: job creation, monitoring, result application."""

    COMPLETED_STATES = {
        "JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED",
    }

    def __init__(
        self,
        client: GeminiClient,
        result_parser: ResultParser,
        batch_job_db: Optional[BatchJobDB] = None,
        config: Optional[Dict] = None,
    ):
        self.client = client
        self.parser = result_parser
        self.batch_job_db = batch_job_db

        ai_config = (config or {}).get("ai_enhancement", {})
        self.batch_size = ai_config.get("batch_size", 45)
        self.temperature = ai_config.get("temperature", 0.1)
        self.tmp_dir = ai_config.get("tmp_dir", os.path.join("out", "batch_requests"))
        os.makedirs(self.tmp_dir, exist_ok=True)

        self.category_parameters = load_category_parameters()

    def process(
        self,
        df: pd.DataFrame,
        group1_indices: set,
        progress_callback: Optional[Callable] = None,
        force_reprocess: bool = False,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Run batch processing for products needing AI enhancement.

        Args:
            df: Full product DataFrame
            group1_indices: Indices of variant products (no-dimensions prompt)
            progress_callback: Optional progress callback
            force_reprocess: If True, reprocess all products

        Returns:
            Tuple of (updated DataFrame, stats dict)
        """
        if not self.client.is_available:
            logger.warning("No API key, skipping AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        # Check for active job to resume
        if self.batch_job_db:
            active_job = self.batch_job_db.get_active_job()
            if active_job:
                logger.info(f"Resuming active batch job: {active_job['job_name']}")
                if progress_callback:
                    progress_callback(0, 0, f"Obnovovanie existujucej ulohy (Job ID: {active_job['job_name'][-10:]})...")
                return self._monitor_and_apply(
                    df, active_job["job_name"], active_job["uploaded_file_name"],
                    progress_callback,
                )

        # Determine which products need processing
        if "aiProcessed" not in df.columns:
            df["aiProcessed"] = ""
        if "aiProcessedDate" not in df.columns:
            df["aiProcessedDate"] = ""

        df["aiProcessed"] = df["aiProcessed"].apply(
            lambda x: "1" if str(x).strip().upper() in ("TRUE", "1", "YES", "1.0")
            else "0" if str(x).strip().upper() in ("FALSE", "0", "NO", "", "0.0")
            else x
        )

        needs_processing = df if force_reprocess else df[df["aiProcessed"] != "1"]
        total = len(needs_processing)

        if total == 0:
            logger.info("No products need AI enhancement")
            if progress_callback:
                progress_callback(0, 0, "Ziadne produkty na vylepsenie.")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        logger.info(f"Processing {total} products with Batch API")

        # Build JSONL requests
        if progress_callback:
            progress_callback(0, total, "Priprava davok (Batch Requests)...")

        jsonl_requests = []
        self._build_category_requests(needs_processing, group1_indices, jsonl_requests, is_group1=True)
        group2_indices = [idx for idx in needs_processing.index if idx not in group1_indices]
        self._build_category_requests(needs_processing, set(group2_indices), jsonl_requests, is_group1=False)

        if not jsonl_requests:
            logger.info("No valid batch requests generated.")
            return df, {"ai_should_process": total, "ai_processed": 0}

        return self._submit_and_monitor(df, jsonl_requests, progress_callback, total)

    def process_missing_params(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[Callable] = None,
        model: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Second pass: grounded re-ask for filter params still missing after enhancement.

        Params-only responses can't clobber descriptions — the parser writes
        text fields only when present in the response.
        """
        if not self.client.is_available:
            logger.warning("No API key, skipping missing-params pass")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        jsonl_requests, product_count = self._build_missing_param_requests(df)
        if not jsonl_requests:
            logger.info("No products with missing parameters")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        logger.info(
            "Missing-params pass: %d products in %d requests (model=%s)",
            product_count, len(jsonl_requests), model or self.client.model_name,
        )
        return self._submit_and_monitor(
            df, jsonl_requests, progress_callback, product_count, model=model
        )

    def _build_missing_param_requests(self, df: pd.DataFrame) -> Tuple[list, int]:
        """Group products by category and list each one's unfilled expected params."""
        by_cat: Dict[str, list] = {}
        for _, row in df.iterrows():
            cat = self._category_of(row)
            expected = self.category_parameters.get(cat)
            if not expected:
                continue
            missing = [
                p for p in expected
                if str(row.get(f"filteringProperty:{p}", "") or "").strip().lower() in ("", "nan")
            ]
            if not missing:
                continue
            by_cat.setdefault(cat, []).append({
                "code": str(row.get("code", "")),
                "name": str(row.get("name", "")),
                "shortDescription": str(row.get("shortDescription", "")),
                "chybajuce_parametre": missing,
            })

        jsonl_requests = []
        product_count = 0
        for cat_name, products in by_cat.items():
            sys_prompt = create_params_only_prompt(cat_name)
            for i in range(0, len(products), self.batch_size):
                chunk = products[i:i + self.batch_size]
                product_count += len(chunk)
                jsonl_requests.append({
                    "key": f"fill_{hash(cat_name)}_{i}",
                    "request": {
                        "systemInstruction": {"parts": [{"text": sys_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": json.dumps(chunk, ensure_ascii=False)}]}],
                        # ponytail: no responseMimeType — google_search + JSON mime conflict; parser strips fences
                        "tools": [{"google_search": {}}],
                        "generationConfig": {"temperature": self.temperature},
                    },
                })
        return jsonl_requests, product_count

    def _submit_and_monitor(
        self,
        df: pd.DataFrame,
        jsonl_requests: list,
        progress_callback: Optional[Callable],
        total: int,
        model: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Write JSONL, upload, create batch job, and monitor to completion."""
        jsonl_path = os.path.join(
            self.tmp_dir, f"batch_requests_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jsonl"
        )
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for req in jsonl_requests:
                f.write(json.dumps(req, ensure_ascii=False) + "\n")

        if progress_callback:
            progress_callback(0, total, "Nahravanie suboru na Google Cloud...")

        try:
            uploaded_name = self.client.upload_file(jsonl_path)

            if progress_callback:
                progress_callback(0, total, "Vytvaranie davkovej ulohy (Batch Job)...")

            batch_job = self.client.create_batch_job(uploaded_name, model=model)
            logger.info(f"Batch Job Created: {batch_job.name}")

            if self.batch_job_db:
                self.batch_job_db.add_job(
                    batch_job.name, batch_job.state.name, jsonl_path, uploaded_name
                )

            return self._monitor_and_apply(df, batch_job.name, uploaded_name, progress_callback, total)

        except Exception as e:
            logger.error(f"Failed to create Batch Job: {e}")
            return df, {"ai_should_process": total, "ai_processed": 0}

    @staticmethod
    def _category_of(row) -> str:
        """First non-empty of newCategory/defaultCategory (empty column != missing column)."""
        for col in ("newCategory", "defaultCategory"):
            val = str(row.get(col) or "").strip()
            if val and val.lower() != "nan":
                return val
        return ""

    def _build_category_requests(
        self, needs_processing: pd.DataFrame, indices: set,
        jsonl_requests: list, is_group1: bool
    ):
        """Build JSONL requests grouped by category."""
        if not indices:
            return

        group_df = needs_processing.loc[list(indices)].copy()
        group_df["_temp_cat"] = group_df.apply(self._category_of, axis=1)

        for cat_name, cat_subset in group_df.groupby("_temp_cat"):
            if not cat_name and self.category_parameters:
                logger.warning(f"Skipping {len(cat_subset)} products with no category.")
                continue

            expected_params = self.category_parameters.get(cat_name, [])

            if is_group1:
                sys_prompt = create_system_prompt_no_dimensions(cat_name, expected_params)
            else:
                sys_prompt = create_system_prompt(cat_name, expected_params)

            param_cols = [c for c in cat_subset.columns if c.startswith("filteringProperty:")]

            for i in range(0, len(cat_subset), self.batch_size):
                batch_end = min(i + self.batch_size, len(cat_subset))
                batch_df = cat_subset.iloc[i:batch_end]

                products = []
                for _, row in batch_df.iterrows():
                    product = {
                        "code": str(row.get("code", "")),
                        "name": str(row.get("name", "")),
                        "shortDescription": str(row.get("shortDescription", "")),
                        "description": str(row.get("description", "")),
                    }
                    # Known params differentiate copy for near-identical variants
                    existing = {
                        c.split(":", 1)[1]: str(row[c]).strip()
                        for c in param_cols
                        if str(row.get(c, "") or "").strip().lower() not in ("", "nan")
                    }
                    if existing:
                        product["existingParameters"] = existing
                    products.append(product)

                if products:
                    req_key = f"req_{'g1' if is_group1 else 'g2'}_{hash(cat_name)}_{i}"
                    jsonl_requests.append({
                        "key": req_key,
                        "request": {
                            "systemInstruction": {"parts": [{"text": sys_prompt}]},
                            "contents": [{"role": "user", "parts": [{"text": json.dumps(products, ensure_ascii=False)}]}],
                            "generationConfig": {
                                "temperature": self.temperature,
                                "responseMimeType": "application/json",
                                "responseSchema": build_response_schema(expected_params),
                            },
                        },
                    })

    def _monitor_and_apply(
        self, df: pd.DataFrame, job_name: str, uploaded_file_name: str,
        progress_callback=None, original_total: int = 0,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Poll batch job until completion and apply results."""
        start_time = time.time()

        while True:
            try:
                batch_job = self.client.get_batch_job(job_name)
                state = batch_job.state.name
            except Exception as e:
                logger.error(f"Error polling job {job_name}: {e}")
                time.sleep(30)
                continue

            if self.batch_job_db:
                self.batch_job_db.update_status(job_name, state)

            logger.info(f"Batch Job {job_name} Status: {state}")
            if progress_callback:
                elapsed = int((time.time() - start_time) / 60)
                progress_callback(0, original_total or 100, f"Spracovava sa v cloude (Cas: {elapsed}m, Stav: {state})...")

            if state in self.COMPLETED_STATES:
                break

            time.sleep(30)

        if state != "JOB_STATE_SUCCEEDED":
            logger.error(f"Batch Job failed. Final state: {state}")
            return df, {"ai_should_process": original_total, "ai_processed": 0}

        # Download results
        if progress_callback:
            progress_callback(90, 100, "Stahovanie vysledkov...")

        if not batch_job.dest or not batch_job.dest.file_name:
            logger.error("No destination file in batch job response.")
            return df, {"ai_should_process": original_total, "ai_processed": 0}

        try:
            file_content = self.client.download_file(batch_job.dest.file_name)
        except Exception as e:
            logger.error(f"Failed to download results: {e}")
            return df, {"ai_should_process": original_total, "ai_processed": 0}

        # Clean up uploaded file
        if uploaded_file_name:
            self.client.delete_file(uploaded_file_name)

        return self.parser.parse_batch_results(df, file_content, progress_callback)
