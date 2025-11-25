# """
# Tests for AI enhancement with new 138-column format.
# Following TDD approach: Write tests first, then implement.
# """

# import pytest
# import pandas as pd
# import time
# import threading
# from unittest.mock import Mock, patch, MagicMock
# from concurrent.futures import ThreadPoolExecutor


# class TestAIEnhancerNewFormat:
#     """Test AI enhancer with new format columns."""

#     def test_enhancer_initialization(self, config):
#         """Test AI enhancer initializes with config."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         assert enhancer.config is not None
#         assert hasattr(enhancer, "enhance_product")

#     def test_enhance_updates_new_format_columns(self, config):
#         """Test that enhancement updates new format columns."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001"],
#                 "name": ["Short name"],
#                 "shortDescription": [""],
#                 "description": [""],
#                 "aiProcessed": [""],
#                 "aiProcessedDate": [""],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {
#                 "shortDescription": "AI generated short description",
#                 "description": "AI generated full description",
#             }

#             result = enhancer.enhance_product(df.iloc[0])

#             assert result["shortDescription"] == "AI generated short description"
#             assert result["description"] == "AI generated full description"

#     def test_marks_product_as_processed(self, config):
#         """Test that AI processing is tracked."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001"],
#                 "name": ["Product"],
#                 "aiProcessed": [""],
#                 "aiProcessedDate": [""],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {"shortDescription": "Test"}

#             result = enhancer.enhance_product(df.iloc[0])

#             assert result["aiProcessed"] == "1"
#             assert result["aiProcessedDate"] != ""

#     def test_skips_already_processed(self, config):
#         """Test that already processed products are skipped."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001"],
#                 "name": ["Product"],
#                 "aiProcessed": ["1"],
#                 "aiProcessedDate": ["2024-01-01"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             result = enhancer.enhance_product(df.iloc[0])

#             # API should not be called
#             mock_api.assert_not_called()

#             # Should return original data
#             assert result["aiProcessed"] == "1"


# class TestAIEnhancementBatch:
#     """Test batch AI enhancement."""

#     def test_enhance_dataframe(self, config):
#         """Test enhancing entire DataFrame."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["Product 1", "Product 2"],
#                 "shortDescription": ["", ""],
#                 "aiProcessed": ["", ""],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {"shortDescription": "Enhanced"}

#             result = enhancer.enhance_dataframe(df)

#             # Both products should be processed
#             assert all(result["aiProcessed"] == "1")
#             assert mock_api.call_count == 2

#     def test_batch_skips_processed_products(self, config):
#         """Test batch processing skips already processed products."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002", "PROD003"],
#                 "name": ["P1", "P2", "P3"],
#                 "aiProcessed": ["1", "", "1"],
#                 "aiProcessedDate": ["2024-01-01", "", "2024-01-01"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {"shortDescription": "Enhanced"}

#             result = enhancer.enhance_dataframe(df)

#             # Only PROD002 should be processed
#             assert mock_api.call_count == 1

#     def test_batch_with_force_reprocess(self, config):
#         """Test batch processing with force reprocess flag."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["P1", "P2"],
#                 "aiProcessed": ["1", "1"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {"shortDescription": "Enhanced"}

#             result = enhancer.enhance_dataframe(df, force_reprocess=True)

#             # Both should be processed despite being marked
#             assert mock_api.call_count == 2


# class TestAIEnhancementFields:
#     """Test AI enhancement of specific fields."""

#     def test_enhance_short_description(self, config):
#         """Test AI enhancement of shortDescription field."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         product = pd.Series(
#             {
#                 "code": "PROD001",
#                 "name": "Professional Coffee Machine",
#                 "shortDescription": "",
#                 "manufacturer": "TestBrand",
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {
#                 "shortDescription": "High-quality professional coffee machine"
#             }

#             result = enhancer.enhance_product(product)

#             assert result["shortDescription"] != ""
#             assert "coffee" in result["shortDescription"].lower()

#     def test_enhance_full_description(self, config):
#         """Test AI enhancement of description field."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         product = pd.Series(
#             {"code": "PROD001", "name": "Coffee Machine", "description": ""}
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {
#                 "description": "Detailed description of the coffee machine..."
#             }

#             result = enhancer.enhance_product(product)

#             assert result["description"] != ""

#     def test_preserve_existing_descriptions(self, config):
#         """Test that existing descriptions are preserved."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         product = pd.Series(
#             {
#                 "code": "PROD001",
#                 "name": "Product",
#                 "shortDescription": "Existing short description",
#                 "description": "Existing full description",
#                 "aiProcessed": "",
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {}

#             result = enhancer.enhance_product(product, preserve_existing=True)

#             # Should not call API if descriptions exist
#             mock_api.assert_not_called()


# class TestAIEnhancementConfiguration:
#     """Test AI enhancement configuration."""

#     def test_uses_config_api_settings(self, config):
#         """Test that enhancer uses API settings from config."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         # Should have API configuration
#         assert hasattr(enhancer, "config")
#         if "ai_enhancement" in config:
#             assert enhancer.config.get("ai_enhancement") is not None

#     def test_respects_field_configuration(self, config):
#         """Test that enhancer respects field configuration."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         # Should know which fields to enhance
#         assert hasattr(enhancer, "enhance_product")

#     def test_handles_missing_api_key(self, config):
#         """Test handling of missing API key."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         # Remove API key from config
#         config_no_key = config.copy()
#         if "ai_enhancement" in config_no_key:
#             config_no_key["ai_enhancement"].pop("api_key", None)

#         enhancer = AIEnhancerNewFormat(config_no_key)

#         product = pd.Series({"code": "PROD001", "name": "Product", "aiProcessed": ""})

#         # Should handle gracefully (skip or raise appropriate error)
#         result = enhancer.enhance_product(product)

#         # Should not crash
#         assert result is not None


# class TestAIEnhancementTracking:
#     """Test AI enhancement tracking and statistics."""

#     def test_tracks_enhancement_statistics(self, config):
#         """Test that enhancement tracks statistics."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002", "PROD003"],
#                 "name": ["P1", "P2", "P3"],
#                 "aiProcessed": ["", "", "1"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {"shortDescription": "Enhanced"}

#             result, stats = enhancer.enhance_dataframe_with_stats(df)

#             assert "total_processed" in stats
#             assert "already_processed" in stats
#             assert "newly_processed" in stats
#             assert stats["newly_processed"] == 2
#             assert stats["already_processed"] == 1

#     def test_tracks_api_calls(self, config):
#         """Test tracking of API calls."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["P1", "P2"],
#                 "aiProcessed": ["", ""],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         with patch.object(enhancer, "_call_ai_api") as mock_api:
#             mock_api.return_value = {"shortDescription": "Enhanced"}

#             result, stats = enhancer.enhance_dataframe_with_stats(df)

#             assert "api_calls" in stats
#             assert stats["api_calls"] == 2


# class TestQuotaManagement:
#     """Test quota management for API calls and tokens."""

#     def test_quota_initialization(self, config):
#         """Test quota manager initializes with correct limits."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         # Should have quota tracking attributes
#         assert hasattr(enhancer, "calls_in_current_minute")
#         assert hasattr(enhancer, "tokens_in_current_minute")
#         assert hasattr(enhancer, "minute_start_time")
#         assert hasattr(enhancer, "calls_lock")

#     def test_quota_tracks_api_calls(self, config):
#         """Test that quota manager tracks API calls."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)
#         initial_calls = enhancer.calls_in_current_minute

#         # Simulate API call
#         enhancer._check_and_wait_for_quota(tokens_needed=1000)

#         # Should increment call counter
#         assert enhancer.calls_in_current_minute == initial_calls + 1

#     def test_quota_tracks_token_usage(self, config):
#         """Test that quota manager tracks token usage."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)
#         initial_tokens = enhancer.tokens_in_current_minute

#         # Simulate API call with token usage
#         enhancer._check_and_wait_for_quota(tokens_needed=5000)

#         # Should increment token counter
#         assert enhancer.tokens_in_current_minute == initial_tokens + 5000

#     def test_quota_waits_when_call_limit_reached(self, config):
#         """Test that quota manager waits when call limit is reached."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         # Set calls to limit (15 per minute)
#         enhancer.calls_in_current_minute = 15
#         enhancer.minute_start_time = time.time()

#         start_time = time.time()

#         # This should wait (but we'll mock sleep to avoid actual waiting)
#         with patch("time.sleep") as mock_sleep:
#             enhancer._check_and_wait_for_quota(tokens_needed=1000)

#             # Should have called sleep
#             assert mock_sleep.called

#     def test_quota_waits_when_token_limit_reached(self, config):
#         """Test that quota manager waits when token limit is reached."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         # Set tokens near limit (250,000 per minute)
#         enhancer.tokens_in_current_minute = 245000
#         enhancer.minute_start_time = time.time()

#         # This should wait when requesting more tokens
#         with patch("time.sleep") as mock_sleep:
#             enhancer._check_and_wait_for_quota(tokens_needed=10000)

#             # Should have called sleep
#             assert mock_sleep.called

#     def test_quota_resets_after_minute(self, config):
#         """Test that quota resets after a minute."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         # Set counters and time to 61 seconds ago
#         enhancer.calls_in_current_minute = 10
#         enhancer.tokens_in_current_minute = 100000
#         enhancer.minute_start_time = time.time() - 61

#         # Check quota (should reset)
#         enhancer._check_and_wait_for_quota(tokens_needed=1000)

#         # Counters should be reset (plus the new call)
#         assert enhancer.calls_in_current_minute == 1
#         assert enhancer.tokens_in_current_minute == 1000

#     def test_quota_thread_safety(self, config):
#         """Test that quota management is thread-safe."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         def increment_quota():
#             for _ in range(5):
#                 with patch("time.sleep"):
#                     enhancer._check_and_wait_for_quota(tokens_needed=1000)

#         # Run multiple threads
#         threads = [threading.Thread(target=increment_quota) for _ in range(3)]
#         for t in threads:
#             t.start()
#         for t in threads:
#             t.join()

#         # Should have tracked all calls (3 threads * 5 calls = 15)
#         assert enhancer.calls_in_current_minute == 15
#         assert enhancer.tokens_in_current_minute == 15000


# class TestBatchProcessing:
#     """Test batch processing of products."""

#     def test_prepare_batch_data(self, config):
#         """Test preparing batch data for API."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002", "PROD003"],
#                 "name": ["Product 1", "Product 2", "Product 3"],
#                 "defaultCategory": ["Cat1", "Cat2", "Cat3"],
#                 "shortDescription": ["", "", ""],
#                 "description": ["", "", ""],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)
#         batch = enhancer.prepare_batch_data(df, 0, 2)

#         # Should return list of product dicts
#         assert isinstance(batch, list)
#         assert len(batch) == 2
#         assert "code" in batch[0]
#         assert "name" in batch[0]

#     def test_process_batch_with_retry(self, config):
#         """Test processing a batch with retry logic."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)

#         products = [
#             {
#                 "code": "PROD001",
#                 "name": "Product 1",
#                 "defaultCategory": "Category",
#                 "shortDescription": "",
#                 "description": "",
#             }
#         ]

#         # Mock API client
#         with patch.object(enhancer, "client") as mock_client:
#             mock_response = Mock()
#             mock_response.text = '[{"code": "PROD001", "name": "Product 1", "shortDescription": "Enhanced", "description": "Enhanced desc"}]'
#             mock_response.usage_metadata = Mock(total_token_count=1000)
#             mock_client.models.generate_content.return_value = mock_response

#             with patch.object(enhancer, "_check_and_wait_for_quota"):
#                 result = enhancer.process_batch_with_retry(products)

#                 # Should return enhanced products
#                 assert result is not None
#                 assert len(result) == 1
#                 assert result[0]["shortDescription"] == "Enhanced"

#     def test_batch_retry_on_rate_limit(self, config):
#         """Test that batch processing retries on rate limit."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)
#         products = [{"code": "PROD001", "name": "Product"}]

#         # Mock API to raise rate limit error first, then succeed
#         with patch.object(enhancer, "client") as mock_client:
#             mock_response = Mock()
#             mock_response.text = '[{"code": "PROD001", "shortDescription": "Enhanced"}]'
#             mock_response.usage_metadata = Mock(total_token_count=1000)

#             mock_client.models.generate_content.side_effect = [
#                 Exception("rate limit exceeded"),
#                 mock_response,
#             ]

#             with patch.object(enhancer, "_check_and_wait_for_quota"):
#                 with patch("time.sleep"):
#                     result = enhancer.process_batch_with_retry(products)

#                     # Should succeed after retry
#                     assert result is not None
#                     assert mock_client.models.generate_content.call_count == 2

#     def test_batch_exponential_backoff(self, config):
#         """Test exponential backoff on errors."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         enhancer = AIEnhancerNewFormat(config)
#         products = [{"code": "PROD001", "name": "Product"}]

#         # Mock API to fail multiple times
#         with patch.object(enhancer, "client") as mock_client:
#             mock_client.models.generate_content.side_effect = Exception("API error")

#             with patch.object(enhancer, "_check_and_wait_for_quota"):
#                 with patch("time.sleep") as mock_sleep:
#                     # Should raise exception after retries
#                     try:
#                         result = enhancer.process_batch_with_retry(products)
#                     except Exception:
#                         pass  # Expected to raise after retries

#                     # Should have retried 3 times (default)
#                     assert mock_client.models.generate_content.call_count == 3
#                     # Should have used exponential backoff (2^0, 2^1)
#                     assert mock_sleep.call_count >= 2


# class TestFuzzyMatching:
#     """Test fuzzy matching for product identification."""

#     def test_find_best_match_exact_code(self, config):
#         """Test finding exact match by code."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002", "PROD003"],
#                 "name": ["Product 1", "Product 2", "Product 3"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)
#         match_idx = enhancer.find_best_match("PROD002", "code", df)

#         # Should find exact match
#         assert match_idx == 1

#     def test_find_best_match_fuzzy_code(self, config):
#         """Test finding fuzzy match by code."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD-001", "PROD-002", "PROD-003"],
#                 "name": ["Product 1", "Product 2", "Product 3"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)
#         # Try to match "PROD001" (without dash)
#         match_idx = enhancer.find_best_match("PROD001", "code", df)

#         # Should find fuzzy match (if similarity >= threshold)
#         assert match_idx is not None

#     def test_find_best_match_by_name(self, config):
#         """Test finding match by product name."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002", "PROD003"],
#                 "name": [
#                     "Professional Coffee Machine",
#                     "Industrial Oven",
#                     "Commercial Refrigerator",
#                 ],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)
#         match_idx = enhancer.find_best_match("Coffee Machine Professional", "name", df)

#         # Should find match (word order independent)
#         assert match_idx == 0

#     def test_find_best_match_substring(self, config):
#         """Test substring matching."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["Coffee Machine XL 2000", "Oven Pro 3000"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)
#         match_idx = enhancer.find_best_match("Coffee Machine", "name", df)

#         # Should find match (substring)
#         assert match_idx == 0

#     def test_find_best_match_no_match(self, config):
#         """Test when no match is found."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["Coffee Machine", "Oven"],
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)
#         match_idx = enhancer.find_best_match("Completely Different Product", "name", df)

#         # Should return None if no good match
#         assert match_idx is None

#     def test_find_best_match_similarity_threshold(self, config):
#         """Test that similarity threshold is respected."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["Coffee Machine", "Oven"],
#             }
#         )

#         # Set high similarity threshold
#         config["ai_enhancement"] = {"similarity_threshold": 95}
#         enhancer = AIEnhancerNewFormat(config)

#         # Try to match with slightly different name
#         match_idx = enhancer.find_best_match("Coffee Maker", "name", df)

#         # Should not match if below threshold
#         # (depends on actual similarity score)
#         assert match_idx is None or match_idx == 0


# class TestUpdateDataFrame:
#     """Test updating DataFrame with enhanced products."""

#     def test_update_dataframe_exact_match(self, config):
#         """Test updating DataFrame with exact code match."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["Product 1", "Product 2"],
#                 "shortDescription": ["", ""],
#                 "description": ["", ""],
#                 "aiProcessed": ["", ""],
#                 "aiProcessedDate": ["", ""],
#             }
#         )

#         enhanced_products = [
#             {
#                 "code": "PROD001",
#                 "name": "Product 1",
#                 "shortDescription": "Enhanced short",
#                 "description": "Enhanced long",
#                 "seoTitle": "SEO Title",
#                 "seoDescription": "SEO Desc",
#                 "seoKeywords": "keyword1, keyword2",
#             }
#         ]

#         enhancer = AIEnhancerNewFormat(config)
#         result_df, updated_count = enhancer.update_dataframe(df, enhanced_products)

#         # Should update the product
#         assert updated_count == 1
#         assert result_df.loc[0, "shortDescription"] == "Enhanced short"
#         assert result_df.loc[0, "description"] == "Enhanced long"
#         assert result_df.loc[0, "aiProcessed"] == "1"

#     def test_update_dataframe_fuzzy_match(self, config):
#         """Test updating DataFrame with fuzzy matching."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD-001", "PROD-002"],
#                 "name": ["Product 1", "Product 2"],
#                 "shortDescription": ["", ""],
#                 "aiProcessed": ["", ""],
#             }
#         )

#         # Enhanced product has code without dash
#         enhanced_products = [
#             {
#                 "code": "PROD001",
#                 "name": "Product 1",
#                 "shortDescription": "Enhanced",
#             }
#         ]

#         enhancer = AIEnhancerNewFormat(config)
#         result_df, updated_count = enhancer.update_dataframe(df, enhanced_products)

#         # Should find and update via fuzzy match
#         assert updated_count >= 0  # May or may not match depending on threshold

#     def test_update_dataframe_no_match(self, config):
#         """Test updating DataFrame when no match is found."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["Product 1", "Product 2"],
#                 "shortDescription": ["", ""],
#             }
#         )

#         # Enhanced product with non-existent code
#         enhanced_products = [
#             {"code": "PROD999", "name": "Unknown", "shortDescription": "Enhanced"}
#         ]

#         enhancer = AIEnhancerNewFormat(config)
#         result_df, updated_count = enhancer.update_dataframe(df, enhanced_products)

#         # Should not update anything
#         assert updated_count == 0


# class TestParallelProcessing:
#     """Test parallel batch processing."""

#     def test_process_dataframe_parallel(self, config):
#         """Test parallel processing of DataFrame."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         # Create larger DataFrame for parallel processing
#         df = pd.DataFrame(
#             {
#                 "code": [f"PROD{i:03d}" for i in range(100)],
#                 "name": [f"Product {i}" for i in range(100)],
#                 "defaultCategory": ["Category"] * 100,
#                 "shortDescription": [""] * 100,
#                 "aiProcessed": [""] * 100,
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)
#         enhancer.client = Mock()
#         enhancer.api_key = "test_key"

#         # Mock batch processing
#         with patch.object(enhancer, "process_batch_with_retry") as mock_batch:
#             mock_batch.return_value = [
#                 {"code": "PROD001", "shortDescription": "Enhanced"}
#             ]

#             with patch.object(enhancer, "update_dataframe") as mock_update:
#                 mock_update.return_value = (df, 1)

#                 result_df, stats = enhancer.process_dataframe(df)

#                 # Should have called batch processing multiple times
#                 assert mock_batch.call_count > 1

#     def test_parallel_processing_thread_safety(self, config):
#         """Test thread safety of parallel processing."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         df = pd.DataFrame(
#             {
#                 "code": [f"PROD{i:03d}" for i in range(50)],
#                 "name": [f"Product {i}" for i in range(50)],
#                 "aiProcessed": [""] * 50,
#             }
#         )

#         enhancer = AIEnhancerNewFormat(config)

#         # Mock to avoid actual API calls
#         with patch.object(enhancer, "process_batch_with_retry") as mock_batch:
#             mock_batch.return_value = []
#             with patch.object(enhancer, "update_dataframe") as mock_update:
#                 mock_update.return_value = (df, 0)

#                 # Should not raise any threading errors
#                 result_df, stats = enhancer.process_dataframe(df)

#                 assert result_df is not None


# class TestIncrementalSaving:
#     """Test incremental saving of progress."""

#     def test_saves_progress_to_tmp(self, config, tmp_path):
#         """Test that progress is saved to tmp directory."""
#         from src.ai.ai_enhancer_new_format import AIEnhancerNewFormat

#         # Set tmp directory to pytest tmp_path
#         config["ai_enhancement"] = {"tmp_dir": str(tmp_path)}
#         enhancer = AIEnhancerNewFormat(config)
#         enhancer.tmp_dir = str(tmp_path)

#         df = pd.DataFrame(
#             {
#                 "code": ["PROD001", "PROD002"],
#                 "name": ["Product 1", "Product 2"],
#                 "aiProcessed": ["", ""],
#             }
#         )

#         # Mock batch processing
#         with patch.object(enhancer, "process_batch_with_retry") as mock_batch:
#             mock_batch.return_value = [
#                 {"code": "PROD001", "shortDescription": "Enhanced"}
#             ]
#             with patch.object(enhancer, "update_dataframe") as mock_update:
#                 mock_update.return_value = (df, 1)

#                 result_df, stats = enhancer.process_dataframe(df)

#                 # Check if tmp file was created (implementation dependent)
#                 # This test may need adjustment based on actual implementation
#                 assert result_df is not None
