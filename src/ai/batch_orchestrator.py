"""Batch processing orchestration for AI enhancement.

A run is split into chunks (~chunk_size products each). Each chunk is its own
batch job, processed sequentially: build JSONL -> upload -> create job -> poll
-> download -> apply -> mark chunk applied. Interruption at any point loses at
most one chunk's cloud time; run/chunk state lives in RunDB so `process()`
picks up a resumable run automatically, and `resume()` continues explicitly.
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable

import pandas as pd

from .api_client import GeminiClient
from .result_parser import ResultParser
from .run_control import RunControl
from .prompts import (
    build_response_schema,
    create_params_only_prompt,
    create_system_prompt,
    create_system_prompt_no_dimensions,
    load_category_parameters,
)
from src.data.database.batch_job_db import BatchJobDB
from src.data.database.run_db import RunDB

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
        run_db: Optional[RunDB] = None,
        config: Optional[Dict] = None,
    ):
        self.client = client
        self.parser = result_parser
        self.batch_job_db = batch_job_db
        self.run_db = run_db

        ai_config = (config or {}).get("ai_enhancement", {})
        self.batch_size = ai_config.get("batch_size", 45)
        self.temperature = ai_config.get("temperature", 0.1)
        self.tmp_dir = ai_config.get("tmp_dir", os.path.join("out", "batch_requests"))
        self.chunk_size = ai_config.get("chunk_size", 500)
        self.poll_failure_limit = ai_config.get("poll_failure_limit", 20)
        os.makedirs(self.tmp_dir, exist_ok=True)

        self.category_parameters = load_category_parameters()

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def process(
        self,
        df: pd.DataFrame,
        group1_indices: set,
        progress_callback: Optional[Callable] = None,
        force_reprocess: bool = False,
        control: Optional[RunControl] = None,
        on_chunk_applied: Optional[Callable[[pd.DataFrame], None]] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Run (or resume) chunked batch processing for products needing AI enhancement."""
        if not self.client.is_available:
            logger.warning("No API key, skipping AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        if self.run_db:
            resumable = self.run_db.get_resumable_run()
            if resumable:
                logger.info(
                    "Resuming run %s: %d/%d products done",
                    resumable["id"], resumable["processed_products"], resumable["total_products"],
                )
                return self._run_chunks(df, resumable["id"], group1_indices, progress_callback, control, on_chunk_applied)

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

        if not self.run_db:
            # No run tracking (isolated CLI micro-tests): legacy single-job, non-resumable path.
            return self._process_untracked(df, needs_processing, group1_indices, progress_callback, total)

        codes = [str(df.at[idx, "code"]).strip() for idx in needs_processing.index]
        chunks = [codes[i:i + self.chunk_size] for i in range(0, len(codes), self.chunk_size)]
        run_id = self.run_db.create_run(force_reprocess, chunks)
        return self._run_chunks(df, run_id, group1_indices, progress_callback, control, on_chunk_applied)

    def resume(
        self,
        df: pd.DataFrame,
        run_id: int,
        group1_indices: set,
        progress_callback: Optional[Callable] = None,
        control: Optional[RunControl] = None,
        on_chunk_applied: Optional[Callable[[pd.DataFrame], None]] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Continue a specific run by id (used when the caller already resolved it)."""
        return self._run_chunks(df, run_id, group1_indices, progress_callback, control, on_chunk_applied)

    def process_missing_params(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[Callable] = None,
        model: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Second pass: grounded re-ask for filter params still missing after enhancement.

        Params-only responses can't clobber descriptions — the parser writes
        text fields only when present in the response. Single job, not chunked:
        this pass is optional and re-runnable in full if interrupted.
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
        try:
            job_name, uploaded_name = self._submit_chunk(jsonl_requests, model=model)
        except Exception as e:
            logger.error(f"Failed to create Batch Job: {e}")
            return df, {"ai_should_process": product_count, "ai_processed": 0}

        outcome, batch_job = self._wait_for_job(job_name, progress_callback, product_count, None)
        if outcome != "succeeded":
            logger.error(f"Missing-params batch job did not succeed: {outcome}")
            return df, {"ai_should_process": product_count, "ai_processed": 0}

        return self._download_and_apply(df, batch_job, uploaded_name, progress_callback, product_count)

    # ------------------------------------------------------------------
    # Chunked run execution
    # ------------------------------------------------------------------

    def _run_chunks(
        self,
        df: pd.DataFrame,
        run_id: int,
        group1_indices: set,
        progress_callback: Optional[Callable],
        control: Optional[RunControl],
        on_chunk_applied: Optional[Callable[[pd.DataFrame], None]],
    ) -> Tuple[pd.DataFrame, Dict]:
        run = self.run_db.get_run(run_id)
        total = run["total_products"]
        stats = {"ai_should_process": total, "ai_processed": run["processed_products"]}
        chunks = self.run_db.chunks_for(run_id)

        for chunk in chunks:
            if chunk["status"] == "applied":
                continue

            if control and control.is_cancel_requested:
                self.run_db.update_run(run_id, status="cancelled")
                return df, stats

            chunk_codes = set(chunk["codes"])
            valid_indices = df.index[df["code"].astype(str).str.strip().isin(chunk_codes)]
            if len(valid_indices) == 0:
                self.run_db.mark_chunk(chunk["id"], "applied", detail="no matching rows")
                continue

            if chunk["status"] == "submitted" and chunk["job_name"]:
                # ponytail: uploaded_file_name isn't persisted per chunk, so a resumed chunk skips
                # remote-file cleanup after download (Google auto-expires uploaded files anyway).
                job_name, uploaded_name = chunk["job_name"], ""
            else:
                jsonl_requests = self._build_chunk_requests(df, valid_indices, group1_indices)
                if not jsonl_requests:
                    self.run_db.mark_chunk(chunk["id"], "applied", detail="no requests generated")
                    continue
                if progress_callback:
                    progress_callback(
                        stats["ai_processed"], total,
                        f"Beh {run_id}: davka {chunk['chunk_index'] + 1}/{len(chunks)}, "
                        f"priprava a odosielanie...",
                    )
                try:
                    job_name, uploaded_name = self._submit_chunk(jsonl_requests)
                except Exception as e:
                    logger.error(f"Chunk {chunk['chunk_index']} submit failed: {e}")
                    self.run_db.mark_chunk(chunk["id"], "failed", detail=str(e))
                    self.run_db.update_run(run_id, status="interrupted", detail=str(e))
                    return df, stats
                self.run_db.mark_chunk(chunk["id"], "submitted", job_name=job_name)

            def chunk_progress(_current, _total, message, _chunk=chunk, _chunks=chunks, _stats=stats):
                if progress_callback:
                    progress_callback(
                        _stats["ai_processed"], total,
                        f"Beh {run_id}: davka {_chunk['chunk_index'] + 1}/{len(_chunks)}, "
                        f"{_stats['ai_processed']}/{total} produktov, {message}",
                    )

            outcome, batch_job = self._wait_for_job(job_name, chunk_progress, total, control)

            if outcome == "paused":
                self.run_db.update_run(run_id, status="paused")
                return df, stats
            if outcome == "cancelled":
                self.run_db.update_run(run_id, status="cancelled")
                return df, stats
            if outcome == "interrupted":
                self.run_db.update_run(run_id, status="interrupted", detail="network/API unreachable")
                return df, stats
            if outcome == "failed":
                state = batch_job.state.name if batch_job else "unknown"
                self.run_db.mark_chunk(chunk["id"], "failed", detail=f"job state {state}")
                continue

            df, applied = self._download_and_apply(
                df, batch_job, uploaded_name, chunk_progress, total, valid_indices=valid_indices,
            )
            if applied.get("error"):
                # Job succeeded in the cloud; keep chunk "submitted" so resume re-downloads it.
                self.run_db.update_run(run_id, status="interrupted", detail=applied["error"])
                return df, stats
            applied_count = applied.get("ai_processed", 0)
            stats["ai_processed"] += applied_count
            self.run_db.mark_chunk(chunk["id"], "applied")
            self.run_db.update_run(run_id, processed_delta=applied_count)
            if on_chunk_applied:
                on_chunk_applied(df.loc[valid_indices])

        final_chunks = self.run_db.chunks_for(run_id)
        failed = [c for c in final_chunks if c["status"] == "failed"]
        self.run_db.update_run(
            run_id, status="completed",
            detail=f"{len(failed)} chunks failed" if failed else "",
        )
        return df, stats

    def _build_chunk_requests(self, df: pd.DataFrame, valid_indices, group1_indices: set) -> list:
        chunk_df = df.loc[valid_indices]
        jsonl_requests = []
        g1 = set(valid_indices) & group1_indices
        self._build_category_requests(chunk_df, g1, jsonl_requests, is_group1=True)
        g2 = set(i for i in valid_indices if i not in group1_indices)
        self._build_category_requests(chunk_df, g2, jsonl_requests, is_group1=False)
        return jsonl_requests

    def _submit_chunk(self, jsonl_requests: list, model: Optional[str] = None) -> Tuple[str, str]:
        """Write JSONL, upload, create batch job. Returns (job_name, uploaded_file_name)."""
        jsonl_path = os.path.join(
            self.tmp_dir, f"batch_requests_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jsonl"
        )
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for req in jsonl_requests:
                f.write(json.dumps(req, ensure_ascii=False) + "\n")

        uploaded_name = self.client.upload_file(jsonl_path)
        batch_job = self.client.create_batch_job(uploaded_name, model=model)
        logger.info(f"Batch Job Created: {batch_job.name}")

        if self.batch_job_db:
            self.batch_job_db.add_job(batch_job.name, batch_job.state.name, jsonl_path, uploaded_name)

        return batch_job.name, uploaded_name

    def _wait_for_job(
        self, job_name: str, progress_callback: Optional[Callable], original_total: int,
        control: Optional[RunControl],
    ) -> Tuple[str, Optional[object]]:
        """Poll until the job completes or control/failure ceiling interrupts.

        Returns (outcome, batch_job) where outcome is one of:
        succeeded | failed | paused | cancelled | interrupted.
        """
        start_time = time.time()
        consecutive_errors = 0

        while True:
            if control and control.is_cancel_requested:
                try:
                    self.client.cancel_batch_job(job_name)
                except Exception as e:
                    logger.warning(f"Could not cancel job {job_name}: {e}")
                return "cancelled", None
            if control and control.is_pause_requested:
                return "paused", None

            try:
                batch_job = self.client.get_batch_job(job_name)
                state = batch_job.state.name
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error polling job {job_name}: {e} ({consecutive_errors}/{self.poll_failure_limit})")
                # ponytail: fixed ceiling, not exponential backoff — batch jobs are long-running anyway
                if consecutive_errors >= self.poll_failure_limit:
                    return "interrupted", None
                time.sleep(30)
                continue

            if self.batch_job_db:
                self.batch_job_db.update_status(job_name, state)

            logger.info(f"Batch Job {job_name} Status: {state}")
            if progress_callback:
                elapsed = int((time.time() - start_time) / 60)
                progress_callback(0, original_total or 100, f"stav v cloude: {state} ({elapsed}m)")

            if state in self.COMPLETED_STATES:
                return ("succeeded" if state == "JOB_STATE_SUCCEEDED" else "failed"), batch_job

            time.sleep(30)

    def _download_and_apply(
        self, df: pd.DataFrame, batch_job, uploaded_file_name: str,
        progress_callback: Optional[Callable], original_total: int, valid_indices=None,
    ) -> Tuple[pd.DataFrame, Dict]:
        if not batch_job.dest or not batch_job.dest.file_name:
            logger.error("No destination file in batch job response.")
            return df, {"ai_should_process": original_total, "ai_processed": 0,
                        "error": "no destination file in batch job"}

        try:
            file_content = self.client.download_file(batch_job.dest.file_name)
        except Exception as e:
            logger.error(f"Failed to download results: {e}")
            return df, {"ai_should_process": original_total, "ai_processed": 0,
                        "error": f"download failed: {e}"}

        if uploaded_file_name:
            self.client.delete_file(uploaded_file_name)

        return self.parser.parse_batch_results(df, file_content, progress_callback, valid_indices=valid_indices)

    def _process_untracked(
        self, df: pd.DataFrame, needs_processing: pd.DataFrame, group1_indices: set,
        progress_callback: Optional[Callable], total: int,
    ) -> Tuple[pd.DataFrame, Dict]:
        """Legacy single-job path for callers without a RunDB (isolated CLI micro-tests)."""
        jsonl_requests = []
        self._build_category_requests(needs_processing, group1_indices, jsonl_requests, is_group1=True)
        group2_indices = set(idx for idx in needs_processing.index if idx not in group1_indices)
        self._build_category_requests(needs_processing, group2_indices, jsonl_requests, is_group1=False)

        if not jsonl_requests:
            logger.info("No valid batch requests generated.")
            return df, {"ai_should_process": total, "ai_processed": 0}

        try:
            job_name, uploaded_name = self._submit_chunk(jsonl_requests)
        except Exception as e:
            logger.error(f"Failed to create Batch Job: {e}")
            return df, {"ai_should_process": total, "ai_processed": 0}

        outcome, batch_job = self._wait_for_job(job_name, progress_callback, total, None)
        if outcome != "succeeded":
            logger.error(f"Batch Job did not succeed: {outcome}")
            return df, {"ai_should_process": total, "ai_processed": 0}

        return self._download_and_apply(df, batch_job, uploaded_name, progress_callback, total)

    # ------------------------------------------------------------------
    # Request building (unchanged shape, scoped by the caller's indices)
    # ------------------------------------------------------------------

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
