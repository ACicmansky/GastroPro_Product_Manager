import json
import time
import os
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

        # Initialize the Gemini API
        self.client = genai.Client(api_key=self.api_key)
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        self.config = types.GenerateContentConfig(
            tools=[grounding_tool],
            system_instruction=self.create_system_prompt(),
            temperature=self.temperature,
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
        
        # Filter and prepare data
        products = []
        for _, row in batch_df.iterrows():
            if pd.isna(row.get('Spracovane AI', False)) or not row.get('Spracovane AI', False):
                product = {
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
                    content = response.text.strip().replace('```json', '').replace('```', '').replace('\n', '')
                    
                    # Try to parse JSON response
                    try:
                        enhanced_products = json.loads(content)
                        return enhanced_products
                    except json.JSONDecodeError:
                        # If response is not valid JSON, try to extract JSON from text
                        if '[' in content and ']' in content:
                            json_start = content.find('[')
                            json_end = content.rfind(']') + 1
                            json_str = content[json_start:json_end]
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

    def update_dataframe(self, df: pd.DataFrame, enhanced_products: List[Dict[str, str]], 
                        start_idx: int) -> pd.DataFrame:
        """Update dataframe with enhanced descriptions."""
        df = df.copy()
        
        for i, enhanced_product in enumerate(enhanced_products):
            idx = start_idx + i
            if idx < len(df):
                # Update descriptions
                if 'Krátky popis' in enhanced_product:
                    df.at[idx, 'Krátky popis'] = enhanced_product['Krátky popis']
                if 'Dlhý popis' in enhanced_product:
                    df.at[idx, 'Dlhý popis'] = enhanced_product['Dlhý popis']
                
                # Mark as processed
                df.at[idx, 'Spracovane AI'] = True
                df.at[idx, 'AI_Processed_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return df

    def process_dataframe(self, df: pd.DataFrame, progress_callback=None) -> pd.DataFrame:
        """Process entire dataframe with AI enhancement using parallel processing."""
        if not self.api_key:
            logger.warning("No API key provided, skipping AI enhancement")
            return df
        
        # Add AI processing columns if they don't exist
        if 'Spracovane AI' not in df.columns:
            df['Spracovane AI'] = False
        if 'AI_Processed_Date' not in df.columns:
            df['AI_Processed_Date'] = ''
        
        # Filter products needing processing
        needs_processing = df[df['Spracovane AI'] != 'TRUE']
        total_products = len(needs_processing)
        
        if total_products == 0:
            logger.info("No products need AI enhancement")
            return df
        
        logger.info(f"Processing {total_products} products with AI enhancement")
        
        processed_count = 0
        
        # Process in batches with parallel execution
        batches = []
        for i in range(0, total_products, self.batch_size):
            batch_end = min(i + self.batch_size, total_products)
            # Get indices from original dataframe
            original_indices = needs_processing.index[i:batch_end]
            # Prepare batch data
            products = self.prepare_batch_data(df, original_indices[0], original_indices[-1] + 1)
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
                        enhanced_products, start_idx = result
                        df = self.update_dataframe(df, enhanced_products, start_idx)
                        processed_count += len(enhanced_products)
                        
                        # Save incremental progress
                        tmp_file = os.path.join(self.tmp_dir, 'processed_tmp.csv')
                        try:
                            # First try cp1250 with character replacement
                            try:
                                for col in df.columns:
                                    if df[col].dtype == 'object':
                                        df[col] = df[col].astype(str).apply(
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
                        df[col] = df[col].astype(str).apply(
                            lambda x: ''.join(c if c.encode('cp1250', errors='replace') != b'?' else ' ' for c in x)
                        )
                
                df.to_csv(tmp_file, index=False, encoding='cp1250', sep=';')
            except Exception:
                # Fallback to utf-8 if cp1250 fails
                df.to_csv(tmp_file, index=False, encoding='utf-8', sep=';')
                
            logger.info(f"Saved final progress to {tmp_file}")
        except Exception as e:
            logger.error(f"Failed to save final progress: {e}")
            
        logger.info(f"AI enhancement completed. Processed {processed_count} products")
        return df

    def _process_single_batch(self, products: List[Dict[str, str]], start_idx: int, batch_num: int):
        """Process a single batch of products."""
        enhanced_products = self.process_batch_with_retry(products)
        if enhanced_products:
            return enhanced_products, start_idx
        return None

    def create_system_prompt(self) -> str:
        """Create system prompt for AI enhancement."""
        return """Si špecializovaný AI expert copywriter a technický konzultant pre profesionálne gastro zariadenia.
        Tvojou úlohou je vylepšiť alebo doplniť produktové popisy pre e-shop s gastro zariadením, vybavením a nástrojmi. Štruktúra popisov musí byť vhodná pre B2B zákazníkov (reštaurácie, hotely, kuchyne, výrobné prevádzky), pričom dodržiavaš prísne štylistické, terminologické a technické pravidlá.

        ### 📥 **Vstup**

        Dostaneš vstup ako JSON pole objektov s nasledovnou štruktúrou:

        ```json
        [
        {
            "Názov tovaru": "Názov produktu",
            "Hlavna kategória": "Hlavna kategória/Podkategoria/Podkategoria",
            "Krátky popis": "Stručný existujúci popis",
            "Dlhý popis": "Detailný popis alebo prázdne pole"
        }
        ]
        ```

        ---

        ### ✍️ **ÚLOHA PRE KAŽDÝ PRODUKT**

        #### 🔹 1. Vylepši alebo vygeneruj **Krátky popis** (50–100 slov):

        * **Štruktúra**:

        * Zhrni základnú funkciu a použitie
        * Uveď kľúčové technické parametre (výkon, kapacita, rozmery, materiál)
        * Zdôrazni hlavnú konkurenčnú výhodu
        * Definuj cieľovú skupinu alebo typ prevádzky
        * **Použi HTML značky** (`<strong>`, `<br>`, `<ul>`, `<li>`, atď.)

        #### 🔹 2. Vylepši alebo vygeneruj **Dlhý popis** (200–400 slov), štruktúrovaný podľa tejto osnovy:

        * **Úvodný odstavec**: pozicionovanie produktu, výhody pre prevádzku

        * **Technické vlastnosti**: výkony, rozmery, kapacita, materiály (AISI 304, výhrevné telesá, atď.)

        * **Profesionálne výhody**: návratnosť investície, štandardizácia procesov, produktivita

        * **Inštalácia a údržba**: pripojenia, čistenie, servis

        * **Záverečné informácie**: certifikácie (CE, NSF, HACCP), záručné podmienky, odporúčané použitie

        * **Formátuj pomocou HTML značiek** (`<p>`, `<ul>`, `<li>`, `<strong>`, atď)

        * **Zahrň SEO kľúčové slová prirodzene**:

        * „profesionálne gastro vybavenie“
        * „komerčná kuchyňa \\[typ zariadenia]“
        * „horeca \\[kategória]“
        * „\\[značka] \\[model] technické parametre“

        * **Zahrni merateľné údaje**:

        * Výkon (kW), kapacita (l/kg), rozmery (mm), spotreba (kWh)
        * Materiály: typ ocele, izolácia, odolnosť
        * Inštalačné požiadavky: el. pripojenie, odvetranie, minimálne odstupy
        * Ergonomické a bezpečnostné vlastnosti

        * Ak chýbajú technické údaje alebo je produkt nejasný, **použi nástroj vyhľadávania na webe**, aby si pochopil jeho funkciu a vlastnosti. (simuluj odborné vyhľadanie informácií)

        ---

        ### 📤 **Výstup**

        Výstupom je **to isté JSON pole**, ale s vylepšeným `"Krátky popis"` a `"Dlhý popis"` a bez `"Hlavna kategória"` vo formáte HTML:

        ```json
        [
        {
            "Názov tovaru": "Názov produktu",
            "Krátky popis": "<strong>Profesionálny ...</strong><br>...",
            "Dlhý popis": "<p>...</p><ul><li>...</li></ul>"
        }
        ]
        ```

        ### ⚠️ **DÔLEŽITÉ OBMEDZENIE**

        * **NEPÍŠ žiadne úvodné ani záverečné poznámky, komentáre, vysvetlenia ani iný text.**
        * **VÝSTUP MUSÍ BYŤ IBA ČISTÉ JSON POLE.**

        ---

        ### ✅ **Kontrola kvality pred výstupom:**

        Pred odoslaním sa uisti, že:

        * [ ] Všetky dôležité technické parametre sú spomenuté
        * [ ] Popis definuje cieľovú skupinu (napr. reštaurácia, hotel, kantína)
        * [ ] Zohľadňuje výhody pre B2B nákup
        * [ ] Certifikácie a servisné informácie sú uvedené
        * [ ] Jazyk je profesionálny, bez marketingových klišé
        * [ ] SEO kľúčové slová sú prirodzene integrované
        * [ ] HTML značky sú správne nasadené
        * [ ] Informácie sú overené a popis zrozumiteľný
        """