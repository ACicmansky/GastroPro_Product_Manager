"""
AI Enhancer for new 139-column format with full Gemini API integration.
Includes quota management, batch processing, retry logic, fuzzy matching, and parallel processing.
"""

import json
import time
import os
import pandas as pd
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class AIEnhancerNewFormat:
    """AI enhancer for new format with aiProcessed tracking."""

    def __init__(self, config: Dict):
        """
        Initialize AI enhancer with configuration.

        Args:
            config: Configuration dictionary from config.json
        """
        load_dotenv()

        self.config = config
        self.ai_config = config.get("ai_enhancement", {})

        # API configuration
        self.api_key = os.getenv("GOOGLE_API_KEY") or self.ai_config.get("api_key", "")
        self.model_name = self.ai_config.get("model", "gemini-2.5-flash-lite")
        self.temperature = self.ai_config.get("temperature", 0.1)
        self.batch_size = self.ai_config.get("batch_size", 45)
        self.retry_delay = self.ai_config.get("retry_delay", 60)
        self.retry_attempts = self.ai_config.get("retry_attempts", 3)
        self.max_parallel_calls = self.ai_config.get("max_parallel_calls", 5)
        self.similarity_threshold = self.ai_config.get("similarity_threshold", 85)

        # Initialize Gemini API client if API key available
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                grounding_tool = types.Tool(google_search=types.GoogleSearch())

                # Import prompts
                from .ai_prompts_new_format import (
                    create_system_prompt,
                    create_system_prompt_no_dimensions,
                )

                # Standard config (Group 2)
                self.api_config_standard = types.GenerateContentConfig(
                    tools=[grounding_tool],
                    system_instruction=create_system_prompt(),
                    temperature=self.temperature,
                )

                # No dimensions config (Group 1 - Variants)
                self.api_config_no_dimensions = types.GenerateContentConfig(
                    tools=[grounding_tool],
                    system_instruction=create_system_prompt_no_dimensions(),
                    temperature=self.temperature,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini API client: {e}")
                self.client = None
                self.api_config_standard = None
                self.api_config_no_dimensions = None
        else:
            self.client = None

        # Quota tracking (thread-safe)
        self.calls_lock = threading.Lock()
        self.calls_in_current_minute = 0
        self.tokens_in_current_minute = 0
        self.minute_start_time = time.time()

        # Ensure tmp directory exists
        self.tmp_dir = self.ai_config.get(
            "tmp_dir", os.path.join(os.path.dirname(__file__), "tmp")
        )
        os.makedirs(self.tmp_dir, exist_ok=True)

        # Load category parameters if available
        self.category_parameters = {}
        cat_params_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "categories_with_parameters.json"
        )
        if os.path.exists(cat_params_path):
            try:
                with open(cat_params_path, 'r', encoding='utf-8') as f:
                    params_data = json.load(f)
                    if isinstance(params_data, list):
                        for item in params_data:
                            if isinstance(item, dict) and "kategoria" in item and "filtre" in item:
                                self.category_parameters[item["kategoria"]] = item["filtre"]
                logger.info(f"Loaded {len(self.category_parameters)} category parameter configurations.")
            except Exception as e:
                logger.warning(f"Failed to load category parameters: {e}")

    def _check_and_wait_for_quota(self, tokens_needed: int = 0):
        """
        Check quota and wait if necessary.

        Thread-safe quota management for API calls and tokens.
        Limits: 15 calls/minute, 250,000 tokens/minute
        """
        while True:
            wait_time = 0
            wait_reason = ""

            with self.calls_lock:
                current_time = time.time()

                # Reset counters if a minute has passed
                if current_time - self.minute_start_time >= 60:
                    self.calls_in_current_minute = 0
                    self.tokens_in_current_minute = 0
                    self.minute_start_time = current_time

                # Check call limit (15 calls per minute)
                if self.calls_in_current_minute >= 15:
                    wait_time = 60 - (current_time - self.minute_start_time)
                    wait_reason = "call limit"
                # Check token limit (250,000 tokens per minute)
                elif self.tokens_in_current_minute + tokens_needed > 250000:
                    wait_time = 60 - (current_time - self.minute_start_time)
                    wait_reason = "token limit"

                if wait_time <= 0:
                    # No wait needed, reserve quota
                    self.calls_in_current_minute += 1
                    self.tokens_in_current_minute += tokens_needed
                    return

            # Wait outside the lock
            if wait_time > 0:
                logger.info(
                    f"Quota limit reached ({wait_reason}), waiting {wait_time:.1f} seconds..."
                )
                # Sleep a bit extra to ensure we are in the next minute
                time.sleep(wait_time + 0.1)

    def prepare_batch_data(
        self, df: pd.DataFrame, start_idx: int, end_idx: int
    ) -> List[Dict[str, str]]:
        """
        Prepare batch data for AI processing.

        Args:
            df: DataFrame containing products
            start_idx: Start index in DataFrame
            end_idx: End index in DataFrame

        Returns:
            List of product dictionaries ready for API
        """
        batch_df = df.iloc[start_idx:end_idx].copy()

        products = []
        for _, row in batch_df.iterrows():
            category = str(row.get("newCategory", row.get("defaultCategory", "")))
            product = {
                "code": str(row.get("code", "")),
                "name": str(row.get("name", "")),
                "shortDescription": str(row.get("shortDescription", "")),
                "description": str(row.get("description", "")),
            }

            # We DO NOT inject expected parameters per-product anymore; 
            # it's handled at the batch's system_instruction level.

            products.append(product)

        return products

    def process_batch_with_retry(
        self,
        products: List[Dict[str, str]],
        config: Optional[types.GenerateContentConfig] = None,
    ) -> Optional[List[Dict[str, str]]]:
        """
        Process a batch of products with retry logic.

        Args:
            products: List of product dictionaries
            config: Optional API config to use (defaults to standard)

        Returns:
            List of enhanced product dictionaries or None on failure
        """
        if not products or not self.client:
            return []

        # Use provided config or standard config
        api_config = config or self.api_config_standard

        # Estimate tokens needed (rough estimation)
        estimated_tokens = len(json.dumps(products)) * 1.5
        self._check_and_wait_for_quota(int(estimated_tokens))

        for attempt in range(self.retry_attempts):
            try:
                # Prepare prompt
                user_prompt = json.dumps(products, ensure_ascii=False, indent=None)

                # Send to Gemini API
                response = self.client.models.generate_content(
                    model=self.model_name, config=api_config, contents=user_prompt
                )

                # Track actual tokens used
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    actual_tokens = response.usage_metadata.total_token_count
                    with self.calls_lock:
                        # Adjust token count with actual usage
                        self.tokens_in_current_minute = (
                            self.tokens_in_current_minute
                            - int(estimated_tokens)
                            + actual_tokens
                        )

                # Parse response
                if response and response.text:
                    # Try to parse JSON response
                    try:
                        # Clean response text
                        response_text = response.text.strip()
                        response_text = response_text.replace("```json", "").replace(
                            "```", ""
                        )

                        # Try direct JSON parse
                        enhanced_products = json.loads(response_text)
                        return enhanced_products
                    except json.JSONDecodeError:
                        # If response is not valid JSON, try to extract JSON from text
                        if "[" in response.text and "]" in response.text:
                            json_start = response.text.find("[")
                            json_end = response.text.rfind("]") + 1
                            json_str = response.text[json_start:json_end]
                            enhanced_products = json.loads(json_str)
                            return enhanced_products

                logger.error(
                    f"Invalid response format: {response.text if response else 'No response'}"
                )
                return None

            except Exception as e:
                if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    logger.warning(
                        f"Rate limit hit, waiting {self.retry_delay} seconds..."
                    )
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"Error processing batch: {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(2**attempt)  # Exponential backoff
                        continue
                    raise

        return None

    def find_best_match(
        self, enhanced_product_name: str, column_name: str, df: pd.DataFrame
    ) -> Optional[int]:
        """
        Find the best matching product in the dataframe using fuzzy matching.

        Args:
            enhanced_product_name: Product name/code from API response
            column_name: Column to match against ('code' or 'name')
            df: DataFrame to search in

        Returns:
            Index of best match or None if no good match found
        """
        best_match_idx = None
        best_score = 0

        # Convert enhanced product name to lowercase for comparison
        enhanced_name_lower = enhanced_product_name.lower()

        # Check each product in the dataframe
        for idx, row in df.iterrows():
            df_product_name = str(row[column_name])
            df_name_lower = df_product_name.lower()

            # Calculate similarity scores using different methods
            # 1. Check if enhanced name is a substring of df name or vice versa
            substring_match = (
                enhanced_name_lower in df_name_lower
                or df_name_lower in enhanced_name_lower
            )

            # 2. Check for partial ratio (fuzzy substring matching)
            partial_score = fuzz.partial_ratio(enhanced_name_lower, df_name_lower)

            # 3. Check for token sort ratio (for word order independence)
            token_score = fuzz.token_sort_ratio(enhanced_name_lower, df_name_lower)

            # Use the highest score among the three methods
            max_score = max(partial_score, token_score)

            # If it's a substring match, give it a boost
            if substring_match:
                max_score = max(max_score, 90)  # Boost substring matches

            # Update best match if this score is higher
            if max_score > best_score and max_score >= self.similarity_threshold:
                best_score = max_score
                best_match_idx = idx

        return best_match_idx

    def update_dataframe(
        self,
        df: pd.DataFrame,
        enhanced_products: List[Dict[str, str]],
        valid_indices: Optional[pd.Index] = None,
    ) -> Tuple[pd.DataFrame, int]:
        """
        Update dataframe with enhanced descriptions.

        Args:
            df: The full dataframe to update
            enhanced_products: List of enhanced product dicts from API
            valid_indices: Indices of products that were sent for processing

        Returns:
            Tuple of (updated dataframe, count of updated products)
        """
        updated_count = 0

        # Create a subset view for searching if valid_indices provided
        search_df = df.loc[valid_indices] if valid_indices is not None else df

        for enhanced_product in enhanced_products:
            best_match_idx = None

            # Strategy 1: Exact match on 'code' (most reliable)
            code = str(enhanced_product.get("code", "")).strip()
            if code:
                exact_matches = search_df[
                    search_df["code"].astype(str).str.strip() == code
                ]

                if len(exact_matches) == 1:
                    # Perfect - exactly one match
                    best_match_idx = exact_matches.index[0]
                    logger.debug(f"Exact match found for {code}")
                elif len(exact_matches) > 1:
                    # Multiple exact matches - use the first one and log warning
                    best_match_idx = exact_matches.index[0]
                    logger.warning(
                        f"Multiple exact matches for {code}, using first: {best_match_idx}"
                    )
                else:
                    # Strategy 2: Fuzzy match on catalog number
                    best_match_idx = self.find_best_match(code, "code", search_df)
                    if best_match_idx is not None:
                        logger.info(f"Fuzzy match on code for {code}: {best_match_idx}")
                    else:
                        # Strategy 3: Fuzzy match on product name (last resort)
                        product_name = enhanced_product.get("name", "")
                        if product_name:
                            best_match_idx = self.find_best_match(
                                product_name, "name", search_df
                            )
                            if best_match_idx is not None:
                                logger.info(
                                    f"Fuzzy match on name for {product_name}: {best_match_idx}"
                                )

            if best_match_idx is not None:
                # Update columns INDIVIDUALLY to preserve dtypes
                if "shortDescription" in enhanced_product:
                    df.at[best_match_idx, "shortDescription"] = enhanced_product[
                        "shortDescription"
                    ]
                if "description" in enhanced_product:
                    df.at[best_match_idx, "description"] = enhanced_product[
                        "description"
                    ]
                if "seoTitle" in enhanced_product:
                    df.at[best_match_idx, "seoTitle"] = enhanced_product["seoTitle"]
                if "metaDescription" in enhanced_product:
                    df.at[best_match_idx, "metaDescription"] = enhanced_product[
                        "metaDescription"
                    ]

                if "parameters" in enhanced_product and isinstance(enhanced_product["parameters"], dict):
                    for param_key, param_val in enhanced_product["parameters"].items():
                        if param_val:
                            col_name = f"filteringProperty:{param_key}"
                            df.at[best_match_idx, col_name] = str(param_val)

                # Set tracking columns
                df.at[best_match_idx, "aiProcessed"] = "1"
                df.at[best_match_idx, "aiProcessedDate"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                updated_count += 1
            else:
                logger.error(
                    f"No match found for product {enhanced_product.get('code', 'UNKNOWN')}"
                )

        return df, updated_count

    def process_dataframe(
        self,
        df: pd.DataFrame,
        progress_callback=None,
        force_reprocess: bool = False,
        database_instance=None
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Process entire dataframe with AI enhancement using Gemini Batch API.

        Args:
            df: DataFrame to process
            progress_callback: Optional callback for progress updates
            database_instance: A ProductDatabase instance to manage job state

        Returns:
            Tuple of (processed dataframe, statistics dict)
        """
        if not self.api_key or not self.client:
            logger.warning("No API key provided, skipping AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        # Check if there is an active batch job to resume
        if database_instance:
            active_job = database_instance.get_active_batch_job()
            if active_job:
                logger.info(f"Resuming active batch job: {active_job['job_name']}")
                if progress_callback:
                    progress_callback(0, 0, f"Obnovovanie existujúcej úlohy (Job ID: {active_job['job_name'][-10:]})...")
                # Resume tracking this job instead of starting a new one
                return self._monitor_and_apply_batch_job(df, active_job["job_name"], active_job["uploaded_file_name"], database_instance, progress_callback)

        # Add AI processing columns if they don't exist
        if "aiProcessed" not in df.columns:
            df["aiProcessed"] = ""
        if "aiProcessedDate" not in df.columns:
            df["aiProcessedDate"] = ""

        # Normalize 'aiProcessed' column
        df["aiProcessed"] = df["aiProcessed"].apply(
            lambda x: (
                "1"
                if str(x).strip().upper() in ["TRUE", "1", "YES", "1.0"]
                else "0"
                if str(x).strip().upper() in ["FALSE", "0", "NO", "", "0.0"]
                else x
            )
        )

        if force_reprocess:
            needs_processing = df
        else:
            needs_processing = df[df["aiProcessed"] != "1"]
            
        total_products = len(needs_processing)

        if total_products == 0:
            logger.info("No products need AI enhancement")
            if progress_callback:
                progress_callback(0, 0, "Žiadne produkty na vylepšenie.")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        logger.info(f"Processing {total_products} products with Batch API")
        
        # Identify Group 1 indices (Variants / PairCodes)
        group1_indices = set()
        if "pairCode" in df.columns:
            all_pair_codes = set(df["pairCode"].dropna().unique())
            all_pair_codes.discard("")
            for idx, row in needs_processing.iterrows():
                code = str(row.get("code", "")).strip()
                pair_code = str(row.get("pairCode", "")).strip()
                if pair_code or (code and code in all_pair_codes):
                    group1_indices.add(idx)

        # Build requests for Group 1 (no dimensions) and Group 2 (standard)
        from .ai_prompts_new_format import create_system_prompt, create_system_prompt_no_dimensions
        
        jsonl_requests = []
        
        # Helper to group by category and generate requests
        def build_category_requests(indices, is_group1):
            if not indices:
                return
            group_df = needs_processing.loc[indices]
            # Group by category (fallback to empty string if missing)
            group_df["_temp_cat"] = group_df.apply(lambda r: str(r.get("newCategory", r.get("defaultCategory", ""))), axis=1)
            
            for category_name, cat_subset in group_df.groupby("_temp_cat"):
                # If category is missing/skipping logic (we decided to skip products with unknown categories if needed, 
                # but currently we just pass empty lists for parameters if category not found)
                if not category_name and len(self.category_parameters) > 0:
                    logger.warning(f"Skipping {len(cat_subset)} products because they have no defaultCategory mapped.")
                    continue
                
                expected_params = self.category_parameters.get(category_name, [])
                
                # Get the correct system prompt content
                if is_group1:
                    sys_prompt_text = create_system_prompt_no_dimensions(category_name, expected_params)
                else:
                    sys_prompt_text = create_system_prompt(category_name, expected_params)
                    
                # Batch products inside this category
                for i in range(0, len(cat_subset), self.batch_size):
                    batch_end = min(i + self.batch_size, len(cat_subset))
                    products_subset = self.prepare_batch_data(cat_subset, i, batch_end)
                    if products_subset:
                        req_key = f"req_{'g1' if is_group1 else 'g2'}_{hash(category_name)}_{i}"
                        
                        # Build standard GenerateContentRequest dictionary compatible with JSONL upload
                        jsonl_requests.append({
                            "key": req_key,
                            "request": {
                                "systemInstruction": {"parts": [{"text": sys_prompt_text}]},
                                "contents": [{"role": "user", "parts": [{"text": json.dumps(products_subset, ensure_ascii=False)}] }],
                                "generationConfig": {"temperature": self.temperature, "responseMimeType": "application/json"}
                            }
                        })
        
        # Build for both groups
        if progress_callback:
            progress_callback(0, total_products, "Príprava dávok (Batch Requests)...")
            
        build_category_requests(list(group1_indices), True)
        group2_indices = [idx for idx in needs_processing.index if idx not in group1_indices]
        build_category_requests(group2_indices, False)

        if not jsonl_requests:
            logger.info("No valid batch requests generated (perhaps missing categories?).")
            return df, {"ai_should_process": total_products, "ai_processed": 0}

        # Write requests to a temporary JSONL file
        jsonl_file_path = os.path.join(self.tmp_dir, f"batch_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
        with open(jsonl_file_path, "w", encoding="utf-8") as f:
            for req in jsonl_requests:
                f.write(json.dumps(req, ensure_ascii=False) + "\n")

        # Upload and create batch
        if progress_callback:
            progress_callback(0, total_products, "Nahrávanie súboru na Google Cloud...")
            
        try:
            uploaded_file = self.client.files.upload(
                file=jsonl_file_path, 
                config=types.UploadFileConfig(mime_type='application/jsonl')
            )
            
            if progress_callback:
                progress_callback(0, total_products, "Vytváranie dávkovej úlohy (Batch Job)...")
                
            batch_job = self.client.batches.create(
                model=self.model_name, 
                src=uploaded_file.name
            )
            
            logger.info(f"Batch Job Created: {batch_job.name}")
            
            # Save into database
            if database_instance:
                database_instance.add_batch_job(batch_job.name, batch_job.state.name, jsonl_file_path, uploaded_file.name)
            
            # Monitor the job
            return self._monitor_and_apply_batch_job(df, batch_job.name, uploaded_file.name, database_instance, progress_callback, total_products)

        except Exception as e:
            logger.error(f"Failed to create Batch Job: {e}")
            return df, {"ai_should_process": total_products, "ai_processed": 0}

    def _monitor_and_apply_batch_job(
        self, df: pd.DataFrame, job_name: str, uploaded_file_name: str, database_instance, progress_callback=None, original_total: int = 0
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Polls the Google Batch API until completion and applies results to DataFrame.
        """
        start_time = time.time()
        completed_states = {'JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED'}
        
        while True:
            try:
                batch_job = self.client.batches.get(name=job_name)
                state = batch_job.state.name
            except Exception as e:
                logger.error(f"Error polling job {job_name}: {e}")
                time.sleep(30)
                continue
                
            if database_instance:
                database_instance.update_batch_job_status(job_name, state)
                
            logger.info(f"Batch Job {job_name} Status: {state}")
            if progress_callback:
                elapsed_mins = int((time.time() - start_time) / 60)
                progress_callback(0, original_total or 100, f"Spracováva sa v cloude (Čas: {elapsed_mins}m, Stav: {state})...")
                
            if state in completed_states:
                break
                
            time.sleep(30)
            
        # Job ended
        if state != 'JOB_STATE_SUCCEEDED':
            logger.error(f"Batch Job failed or cancelled. Final state: {state}")
            return df, {"ai_should_process": original_total, "ai_processed": 0}
            
        # Download results
        if progress_callback:
            progress_callback(90, 100, "Sťahovanie výsledkov...")
            
        if not batch_job.dest or not batch_job.dest.file_name:
            logger.error("No destination file name found in batch job response.")
            return df, {"ai_should_process": original_total, "ai_processed": 0}
            
        result_file_name = batch_job.dest.file_name
        try:
            file_content_bytes = self.client.files.download(file=result_file_name)
            file_content = file_content_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to download results: {e}")
            return df, {"ai_should_process": original_total, "ai_processed": 0}
            
        # Clean up input file if exists
        try:
            if uploaded_file_name:
                self.client.files.delete(name=uploaded_file_name)
        except Exception as e:
            logger.warning(f"Could not delete uploaded file {uploaded_file_name}: {e}")
            
        return self._parse_batch_results(df, file_content, progress_callback)
        
    def _parse_batch_results(self, df: pd.DataFrame, file_content: str, progress_callback=None) -> Tuple[pd.DataFrame, Dict]:
        """Parse JSONL output from Batch API and update the DataFrame."""
        if progress_callback:
            progress_callback(95, 100, "Aplikovanie výsledkov do tabuľky...")
            
        enhanced_products_all = []
        
        for line in file_content.splitlines():
            if not line:
                continue
            try:
                parsed_response = json.loads(line)
                
                # Check for successful response
                if 'response' in parsed_response and parsed_response['response']:
                    # Extract the generated text piece
                    for part in parsed_response['response']['candidates'][0]['content']['parts']:
                        if 'text' in part:
                            json_str = part['text'].strip()
                            json_str = json_str.replace("```json", "").replace("```", "")
                            
                            try:
                                # This should be a list of enhanced product dicts for this category batch
                                enhanced_list = json.loads(json_str)
                                if isinstance(enhanced_list, list):
                                    enhanced_products_all.extend(enhanced_list)
                            except json.JSONDecodeError as je:
                                logger.error(f"Failed to decode text payload inside batch response: {je}")
                                
                elif 'error' in parsed_response:
                    logger.error(f"Batch item error: {parsed_response['error']}")
            except Exception as e:
                logger.error(f"Error parsing batch line: {e}")

        # Update DataFrame with collected products
        if enhanced_products_all:
            updated_df, updated_count = self.update_dataframe(df, enhanced_products_all)
            return updated_df, {"ai_should_process": len(enhanced_products_all), "ai_processed": updated_count}
            
        return df, {"ai_should_process": 0, "ai_processed": 0}



    def enhance_product(
        self,
        product: pd.Series,
        preserve_existing: bool = True,
        force_reprocess: bool = False,
        config: Optional[types.GenerateContentConfig] = None,
    ) -> pd.Series:
        """
        Enhance a single product with AI-generated content.

        Args:
            product: Product data as Series
            preserve_existing: If True, skip if descriptions already exist
            force_reprocess: If True, process even if already marked as processed

        Returns:
            Enhanced product Series
        """
        result = product.copy()

        # Skip if already processed (unless force_reprocess)
        if not force_reprocess and str(result.get("aiProcessed", "")) == "1":
            return result

        # Skip if descriptions exist and preserve_existing is True
        if preserve_existing:
            has_short = str(result.get("shortDescription", "")) not in [
                "",
                "nan",
                "None",
            ]
            has_full = str(result.get("description", "")) not in ["", "nan", "None"]
            if has_short and has_full:
                return result

        # Call AI API to enhance
        enhancements = self._call_ai_api(result, config)

        # Apply enhancements
        for field, value in enhancements.items():
            result[field] = value

        # Mark as processed
        result["aiProcessed"] = "1"
        result["aiProcessedDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return result

    def enhance_dataframe_with_stats(
        self, df: pd.DataFrame, force_reprocess: bool = False, database_instance=None
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Enhance DataFrame and return statistics.

        Args:
            df: DataFrame to enhance
            force_reprocess: If True, reprocess even if already processed

        Returns:
            Tuple of (enhanced DataFrame, statistics dict)
        """
        # Pass the database implementation to track Batch Jobs
        return self.process_dataframe(df, force_reprocess=force_reprocess, database_instance=database_instance)

    def _call_ai_api(
        self, product: pd.Series, config: Optional[types.GenerateContentConfig] = None
    ) -> Dict:
        """
        Call AI API to generate enhancements.

        Args:
            product: Product data
            config: Optional API config to use

        Returns:
            Dictionary of field -> enhanced value
        """
        # Check if API key is available
        if not self.api_key:
            print("  Warning: No API key configured, skipping AI enhancement")
            return {}

        # Prepare single product for batch API
        product_dict = {
            "code": str(product.get("code", "")),
            "name": str(product.get("name", "")),
            "defaultCategory": str(product.get("defaultCategory", "")),
            "shortDescription": str(product.get("shortDescription", "")),
            "description": str(product.get("description", "")),
        }

        # Call API using the batch method (list of 1)
        # This handles retry logic, quota management, and JSON parsing
        enhanced_list = self.process_batch_with_retry([product_dict], config)

        if enhanced_list and len(enhanced_list) > 0:
            return enhanced_list[0]

        return {}
