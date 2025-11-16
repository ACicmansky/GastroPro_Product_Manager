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
                from .ai_prompts_new_format import create_system_prompt

                self.api_config = types.GenerateContentConfig(
                    tools=[grounding_tool],
                    system_instruction=create_system_prompt(),
                    temperature=self.temperature,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini API client: {e}")
                self.client = None
        else:
            self.client = None

        # Quota tracking (thread-safe)
        self.calls_lock = threading.Lock()
        self.calls_in_current_minute = 0
        self.tokens_in_current_minute = 0
        self.minute_start_time = time.time()

        # Ensure tmp directory exists
        self.tmp_dir = self.ai_config.get("tmp_dir", os.path.join(os.path.dirname(__file__), "tmp"))
        os.makedirs(self.tmp_dir, exist_ok=True)

    def _check_and_wait_for_quota(self, tokens_needed: int = 0):
        """
        Check quota and wait if necessary.
        
        Thread-safe quota management for API calls and tokens.
        Limits: 15 calls/minute, 250,000 tokens/minute
        """
        with self.calls_lock:
            current_time = time.time()

            # Reset counters if a minute has passed
            if current_time - self.minute_start_time >= 60:
                self.calls_in_current_minute = 0
                self.tokens_in_current_minute = 0
                self.minute_start_time = current_time

            # Check if we need to wait
            need_to_wait = False
            wait_reason = ""

            # Check call limit (15 calls per minute)
            if self.calls_in_current_minute >= 15:
                need_to_wait = True
                wait_reason = "call limit"

            # Check token limit (250,000 tokens per minute)
            if self.tokens_in_current_minute + tokens_needed > 250000:
                need_to_wait = True
                wait_reason = "token limit"

            if need_to_wait:
                # Calculate wait time until next minute
                time_to_wait = 60 - (current_time - self.minute_start_time)
                if time_to_wait > 0:
                    logger.info(
                        f"Quota limit reached ({wait_reason}), waiting {time_to_wait:.1f} seconds..."
                    )
                    time.sleep(time_to_wait)

                # Reset counters
                self.calls_in_current_minute = 0
                self.tokens_in_current_minute = 0
                self.minute_start_time = time.time()

            # Increment counters
            self.calls_in_current_minute += 1
            self.tokens_in_current_minute += tokens_needed

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
            product = {
                "code": str(row.get("code", "")),
                "name": str(row.get("name", "")),
                "defaultCategory": str(row.get("defaultCategory", "")),
                "shortDescription": str(row.get("shortDescription", "")),
                "description": str(row.get("description", "")),
            }
            products.append(product)

        return products

    def process_batch_with_retry(
        self, products: List[Dict[str, str]]
    ) -> Optional[List[Dict[str, str]]]:
        """
        Process a batch of products with retry logic.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            List of enhanced product dictionaries or None on failure
        """
        if not products or not self.client:
            return []

        # Estimate tokens needed (rough estimation)
        estimated_tokens = len(json.dumps(products)) * 1.5
        self._check_and_wait_for_quota(int(estimated_tokens))

        for attempt in range(self.retry_attempts):
            try:
                # Prepare prompt
                user_prompt = json.dumps(products, ensure_ascii=False, indent=None)

                # Send to Gemini API
                response = self.client.models.generate_content(
                    model=self.model_name, config=self.api_config, contents=user_prompt
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
                        response_text = response_text.replace('```json', '').replace('```', '')
                        
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
        self, df: pd.DataFrame, progress_callback=None
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Process entire dataframe with AI enhancement using parallel processing.
        
        Args:
            df: DataFrame to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (processed dataframe, statistics dict)
        """
        if not self.api_key or not self.client:
            logger.warning("No API key provided, skipping AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        # Add AI processing columns if they don't exist
        if "aiProcessed" not in df.columns:
            df["aiProcessed"] = ""
        if "aiProcessedDate" not in df.columns:
            df["aiProcessedDate"] = ""

        # Normalize 'aiProcessed' column
        df["aiProcessed"] = df["aiProcessed"].apply(
            lambda x: (
                "1"
                if str(x).strip().upper() in ["TRUE", "1", "YES"]
                else "" if str(x).strip().upper() in ["FALSE", "0", "NO", ""] else x
            )
        )

        # Filter products needing processing
        needs_processing = df[df["aiProcessed"].isin(["", "0", "False"])]
        total_products = len(needs_processing)

        if total_products == 0:
            logger.info("No products need AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}

        logger.info(f"Processing {total_products} products with AI enhancement")

        # Store the indices of products that need processing
        needs_processing_indices = needs_processing.index
        processed_count = 0

        # Process in batches with parallel execution
        batches = []
        for i in range(0, total_products, self.batch_size):
            batch_end = min(i + self.batch_size, total_products)
            batch_indices = needs_processing.index[i:batch_end]
            products = self.prepare_batch_data(needs_processing, i, batch_end)
            if products:
                batches.append((products, batch_indices, len(batches) + 1))

        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.max_parallel_calls) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(
                    self._process_single_batch, batch_data, batch_indices, batch_num
                ): batch_num
                for batch_data, batch_indices, batch_num in batches
            }

            # Process completed batches
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    result = future.result()
                    if result:
                        enhanced_products, batch_indices = result
                        df, updated_count = self.update_dataframe(
                            df, enhanced_products, valid_indices=needs_processing_indices
                        )
                        processed_count += updated_count

                        # Save incremental progress
                        self._save_progress(df, batch_num)

                        logger.info(f"Processed batch {batch_num}/{len(batches)}")
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")

                # Update progress
                if progress_callback:
                    progress_callback(processed_count, total_products)

        # Final save
        self._save_progress(df, "final")

        logger.info(
            f"AI enhancement completed. Processed {processed_count} products out of {total_products}"
        )
        statistics = {
            "ai_should_process": total_products,
            "ai_processed": processed_count,
        }
        return df, statistics

    def _process_single_batch(
        self, products: List[Dict[str, str]], batch_indices: pd.Index, batch_num: int
    ):
        """
        Process a single batch of products.
        
        Args:
            products: List of product dicts to process
            batch_indices: Original DataFrame indices for these products
            batch_num: Batch number for logging
            
        Returns:
            Tuple of (enhanced products, batch indices) or None
        """
        enhanced_products = self.process_batch_with_retry(products)
        if enhanced_products:
            return enhanced_products, batch_indices
        return None

    def _save_progress(self, df: pd.DataFrame, batch_identifier):
        """
        Save progress to tmp directory.
        
        Args:
            df: DataFrame to save
            batch_identifier: Batch number or 'final'
        """
        tmp_file = os.path.join(self.tmp_dir, "processed_tmp.csv")
        try:
            df_copy = df.copy()

            # Try UTF-8 first (preferred)
            try:
                df_copy.to_csv(tmp_file, index=False, encoding="utf-8", sep=";")
            except Exception:
                # Fallback to cp1250 if needed
                try:
                    df_copy.to_csv(tmp_file, index=False, encoding="cp1250", sep=";")
                except Exception as e:
                    logger.error(f"Failed to save progress: {e}")
                    return

            logger.info(f"Saved progress (batch {batch_identifier}) to {tmp_file}")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    def enhance_product(
        self,
        product: pd.Series,
        preserve_existing: bool = True,
        force_reprocess: bool = False,
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
        enhancements = self._call_ai_api(result)

        # Apply enhancements
        for field, value in enhancements.items():
            result[field] = value

        # Mark as processed
        result["aiProcessed"] = "1"
        result["aiProcessedDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return result

    def enhance_dataframe(
        self, df: pd.DataFrame, force_reprocess: bool = False
    ) -> pd.DataFrame:
        """
        Enhance entire DataFrame with AI.

        Args:
            df: DataFrame to enhance
            force_reprocess: If True, reprocess even if already processed

        Returns:
            Enhanced DataFrame
        """
        print("\n" + "=" * 60)
        print("AI ENHANCEMENT")
        print("=" * 60)

        result_df = df.copy()

        # Ensure tracking columns exist
        if "aiProcessed" not in result_df.columns:
            result_df["aiProcessed"] = ""
        if "aiProcessedDate" not in result_df.columns:
            result_df["aiProcessedDate"] = ""

        processed_count = 0
        skipped_count = 0

        for idx, row in result_df.iterrows():
            # Skip if already processed (unless force_reprocess)
            if not force_reprocess and str(row.get("aiProcessed", "")) == "1":
                skipped_count += 1
                continue

            # Enhance product
            enhanced = self.enhance_product(
                row,
                preserve_existing=not force_reprocess,
                force_reprocess=force_reprocess,
            )

            # Update DataFrame
            for col in enhanced.index:
                result_df.at[idx, col] = enhanced[col]

            processed_count += 1

            if processed_count % 10 == 0:
                print(f"  Processed {processed_count} products...")

        print(f"\nAI Enhancement complete:")
        print(f"  Processed: {processed_count}")
        print(f"  Skipped: {skipped_count}")
        print("=" * 60)

        return result_df

    def enhance_dataframe_with_stats(
        self, df: pd.DataFrame, force_reprocess: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Enhance DataFrame and return statistics.

        Args:
            df: DataFrame to enhance
            force_reprocess: If True, reprocess even if already processed

        Returns:
            Tuple of (enhanced DataFrame, statistics dict)
        """
        # Count already processed
        already_processed = 0
        if "aiProcessed" in df.columns:
            already_processed = (df["aiProcessed"] == "1").sum()

        # Enhance
        result_df = self.enhance_dataframe(df, force_reprocess)

        # Calculate statistics
        total_processed = (result_df["aiProcessed"] == "1").sum()
        newly_processed = total_processed - (
            0 if force_reprocess else already_processed
        )

        stats = {
            "total_processed": int(total_processed),
            "already_processed": int(already_processed),
            "newly_processed": int(newly_processed),
            "api_calls": int(newly_processed),
        }

        return result_df, stats

    def _call_ai_api(self, product: pd.Series) -> Dict:
        """
        Call AI API to generate enhancements.

        This is a placeholder for actual API integration.
        In production, this would call OpenAI, Anthropic, or similar.

        Args:
            product: Product data

        Returns:
            Dictionary of field -> enhanced value
        """
        # Check if API key is available
        if not self.api_key:
            print("  Warning: No API key configured, skipping AI enhancement")
            return {}

        # Placeholder implementation
        # In production, this would make actual API calls
        enhancements = {}

        # Generate short description if missing
        if str(product.get("shortDescription", "")) in ["", "nan", "None"]:
            name = str(product.get("name", ""))
            manufacturer = str(product.get("manufacturer", ""))
            if name:
                enhancements["shortDescription"] = (
                    f"{name} - Professional quality product"
                )
                if manufacturer and manufacturer not in ["", "nan", "None"]:
                    enhancements["shortDescription"] += f" by {manufacturer}"

        # Generate full description if missing
        if str(product.get("description", "")) in ["", "nan", "None"]:
            name = str(product.get("name", ""))
            if name:
                enhancements["description"] = (
                    f"Detailed description for {name}. High-quality professional equipment suitable for commercial use."
                )

        return enhancements
