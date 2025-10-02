import json
import time
import os
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from google import genai
from google.genai import types
from ..utils.parsers import parse_json
from ..services.ai_prompts import create_system_prompt
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

class AIEnhancementProcessor:
    def __init__(self, config: Dict[str, Any]):
        """Initialize AI enhancement processor."""
        
        load_dotenv()

        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.model_name = config.get('model', 'gemini-2.5-flash-lite')
        self.temperature = config.get('temperature', 0.7)
        self.batch_size = config.get('batch_size', 50)
        self.retry_delay = config.get('retry_delay', 60)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.max_parallel_calls = config.get('max_parallel_calls', 5)
        self.similarity_threshold = config.get('similarity_threshold', 85)

        # Initialize the Gemini API
        self.client = genai.Client(api_key=self.api_key)
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        self.config = types.GenerateContentConfig(
            tools=[grounding_tool],
            system_instruction=create_system_prompt(),
            temperature=self.temperature
        )
        
        # Quota tracking
        self.calls_lock = threading.Lock()
        self.calls_in_current_minute = 0
        self.tokens_in_current_minute = 0
        self.minute_start_time = time.time()
        
        # Ensure tmp directory exists
        self.tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
        os.makedirs(self.tmp_dir, exist_ok=True)

    def prepare_batch_data(self, df: pd.DataFrame, start_idx: int, end_idx: int) -> List[Dict[str, str]]:
        """Prepare batch data for AI processing."""
        batch_df = df.iloc[start_idx:end_idx].copy()
        
        # Prepare data (no need to filter again since we're working with already filtered data)
        products = []
        for _, row in batch_df.iterrows():
            product = {
                "Kat. číslo": str(row.get('Kat. číslo', '')),
                "Názov tovaru": str(row.get('Názov tovaru', '')),
                "Hlavna kategória": str(row.get('Hlavna kategória', '')),
                "Krátky popis": str(row.get('Krátky popis', '')),
                "Dlhý popis": str(row.get('Dlhý popis', ''))
            }
            products.append(product)
        
        return products

    def _check_and_wait_for_quota(self, tokens_needed: int = 0):
        """Check quota and wait if necessary."""
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
                    logger.info(f"Quota limit reached ({wait_reason}), waiting {time_to_wait:.1f} seconds until next minute...")
                    time.sleep(time_to_wait)
                
                # Reset counters
                self.calls_in_current_minute = 0
                self.tokens_in_current_minute = 0
                self.minute_start_time = time.time()
            
            # Increment counters
            self.calls_in_current_minute += 1
            self.tokens_in_current_minute += tokens_needed

    def process_batch_with_retry(self, products: List[Dict[str, str]]) -> Optional[List[Dict[str, str]]]:
        """Process a batch of products with retry logic."""
        if not products:
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
                    model=self.model_name,
                    config=self.config,
                    contents=user_prompt
                    )
                
                # Track actual tokens used
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    actual_tokens = response.usage_metadata.total_token_count
                    with self.calls_lock:
                        # Adjust token count with actual usage
                        self.tokens_in_current_minute = self.tokens_in_current_minute - estimated_tokens + actual_tokens
                
                # Parse response
                if response and response.text:
                    # content = response.text.strip().replace('```json', '').replace('```', '').replace('\n', '')
                    
                    # Try to parse JSON response
                    try:
                        enhanced_products = parse_json(response.text)
                        return enhanced_products
                    except json.JSONDecodeError:
                        # If response is not valid JSON, try to extract JSON from text
                        if '[' in response.text and ']' in response.text:
                            json_start = response.text.find('[')
                            json_end = response.text.rfind(']') + 1
                            json_str = response.text[json_start:json_end]
                            enhanced_products = json.loads(json_str)
                            return enhanced_products
                        
                logger.error(f"Invalid response format: {response.text if response else 'No response'}")
                return None
                
            except Exception as e:
                if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    logger.warning(f"Rate limit hit, waiting {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"Error processing batch: {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    raise
        
        return None

    def find_best_match(self, enhanced_product_name: str, column_name: str, df: pd.DataFrame) -> Optional[int]:
        """Find the best matching product in the dataframe using fuzzy matching."""
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
            substring_match = enhanced_name_lower in df_name_lower or df_name_lower in enhanced_name_lower
            
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
    
    def update_dataframe(self, df: pd.DataFrame, enhanced_products: List[Dict[str, str]]) -> Tuple[pd.DataFrame, int]:
        """Update dataframe with enhanced descriptions using fuzzy matching."""
        df = df.copy()
        updated_count = 0
        
        for enhanced_product in enhanced_products:
            # Find the best matching by Kat. číslo
            best_match_idx = self.find_best_match(enhanced_product['Kat. číslo'], 'Kat. číslo', df)
            if best_match_idx is None:
            # Find the best matching product using fuzzy matching
                best_match_idx = self.find_best_match(enhanced_product['Názov tovaru'], 'Názov tovaru', df)
            
            if best_match_idx is not None:
                # Update the matched product
                df.loc[best_match_idx, [
                    'Krátky popis', 'Dlhý popis', 'SEO titulka', 'SEO popis', 'SEO kľúčové slová',
                    'Spracovane AI', 'AI_Processed_Date'
                ]] = [
                    enhanced_product['Krátky popis'], enhanced_product['Dlhý popis'], enhanced_product['SEO titulka'],
                    enhanced_product['SEO popis'], enhanced_product['SEO kľúčové slová'], True, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
                updated_count += 1
        
        return df, updated_count

    def process_dataframe(self, df: pd.DataFrame, progress_callback=None) -> Tuple[pd.DataFrame, dict]:
        """Process entire dataframe with AI enhancement using parallel processing.
        Returns a tuple of (processed_dataframe, statistics_dict)"""
        if not self.api_key:
            logger.warning("No API key provided, skipping AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}
        
        # Add AI processing columns if they don't exist
        if 'Spracovane AI' not in df.columns:
            df['Spracovane AI'] = False
        if 'AI_Processed_Date' not in df.columns:
            df['AI_Processed_Date'] = ''
        
        # Filter products needing processing
        needs_processing = df[df['Spracovane AI'].isin([False, 'FALSE', ""])]
        total_products = len(needs_processing)
        
        if total_products == 0:
            logger.info("No products need AI enhancement")
            return df, {"ai_should_process": 0, "ai_processed": 0}
        
        logger.info(f"Processing {total_products} products with AI enhancement")
        
        processed_count = 0
        
        # Process in batches with parallel execution
        batches = []
        for i in range(0, total_products, self.batch_size):
            batch_end = min(i + self.batch_size, total_products)
            # Get indices from original dataframe
            original_indices = needs_processing.index[i:batch_end]
            # Prepare batch data using the correct slice of the filtered dataframe
            products = self.prepare_batch_data(needs_processing, i, batch_end)
            if products:
                batches.append((products, original_indices[0], len(batches) + 1))
        
        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.max_parallel_calls) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_single_batch, batch_data, start_idx, batch_num): batch_num
                for batch_data, start_idx, batch_num in batches
            }
            
            # Process completed batches
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    result = future.result()
                    if result:
                        enhanced_products = result[0]
                        df, updated_count = self.update_dataframe(df, enhanced_products)
                        processed_count += updated_count
                        
                        # Save incremental progress
                        tmp_file = os.path.join(self.tmp_dir, 'processed_tmp.csv')
                        try:
                            # First try cp1250 with character replacement
                            try:
                                for col in df.columns:
                                    if df[col].dtype == 'object':
                                        df[col] = df[col].astype(str)
                                        df[col] = df[col].apply(
                                            lambda x: ''.join(c if c.encode('cp1250', errors='replace') != b'?' else ' ' for c in x)
                                        )
                                
                                df.to_csv(tmp_file, index=False, encoding='cp1250', sep=';')
                            except Exception:
                                # Fallback to utf-8 if cp1250 fails
                                df.to_csv(tmp_file, index=False, encoding='utf-8', sep=';')
                            
                            logger.info(f"Saved incremental progress for batch {batch_num} to {tmp_file}")
                        except Exception as e:
                            logger.error(f"Failed to save incremental progress: {e}")
                        
                        logger.info(f"Processed batch {batch_num}/{len(batches)}")
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
                
                # Update progress
                if progress_callback:
                    progress_callback(processed_count, total_products)
        
        # Final save after all processing
        tmp_file = os.path.join(self.tmp_dir, 'processed_tmp.csv')
        try:
            # First try cp1250 with character replacement
            try:
                for col in df.columns:
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str)
                        df[col] = df[col].apply(
                            lambda x: ''.join(c if c.encode('cp1250', errors='replace') != b'?' else ' ' for c in x)
                        )
                
                df.to_csv(tmp_file, index=False, encoding='cp1250', sep=';')
            except Exception:
                # Fallback to utf-8 if cp1250 fails
                df.to_csv(tmp_file, index=False, encoding='utf-8', sep=';')
                
            logger.info(f"Saved final progress to {tmp_file}")
        except Exception as e:
            logger.error(f"Failed to save final progress: {e}")
            
        logger.info(f"AI enhancement completed. Processed {processed_count} products out of {total_products} eligible products")
        statistics = {
            "ai_should_process": total_products,
            "ai_processed": processed_count
        }
        return df, statistics

    def _process_single_batch(self, products: List[Dict[str, str]], start_idx: int, batch_num: int):
        """Process a single batch of products."""
        enhanced_products = self.process_batch_with_retry(products)
        if enhanced_products:
            return enhanced_products, len(enhanced_products)
        return None