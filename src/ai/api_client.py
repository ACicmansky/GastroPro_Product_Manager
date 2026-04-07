"""Gemini API client with quota management and retry logic."""

import json
import time
import os
import logging
import threading
from typing import Dict, List, Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class GeminiClient:
    """Low-level Gemini API operations with quota tracking."""

    def __init__(self, config: Dict):
        load_dotenv()

        ai_config = config.get("ai_enhancement", {})
        self.api_key = os.getenv("GOOGLE_API_KEY") or ai_config.get("api_key", "")
        self.model_name = ai_config.get("model", "gemini-2.5-flash-lite")
        self.temperature = ai_config.get("temperature", 0.1)
        self.retry_delay = ai_config.get("retry_delay", 60)
        self.retry_attempts = ai_config.get("retry_attempts", 3)

        # Initialize client
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini API client: {e}")

        # Quota tracking (thread-safe)
        self._calls_lock = threading.Lock()
        self._calls_in_current_minute = 0
        self._tokens_in_current_minute = 0
        self._minute_start_time = time.time()

    @property
    def is_available(self) -> bool:
        return self.client is not None and bool(self.api_key)

    def check_and_wait_for_quota(self, tokens_needed: int = 0):
        """Block until quota is available. Thread-safe."""
        while True:
            wait_time = 0

            with self._calls_lock:
                current_time = time.time()

                if current_time - self._minute_start_time >= 60:
                    self._calls_in_current_minute = 0
                    self._tokens_in_current_minute = 0
                    self._minute_start_time = current_time

                if self._calls_in_current_minute >= 15:
                    wait_time = 60 - (current_time - self._minute_start_time)
                elif self._tokens_in_current_minute + tokens_needed > 250000:
                    wait_time = 60 - (current_time - self._minute_start_time)

                if wait_time <= 0:
                    self._calls_in_current_minute += 1
                    self._tokens_in_current_minute += tokens_needed
                    return

            if wait_time > 0:
                logger.info(f"Quota limit reached, waiting {wait_time:.1f}s...")
                time.sleep(wait_time + 0.1)

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> Optional[List[Dict]]:
        """Make a single API call and parse JSON response.

        Returns parsed JSON list or None on failure.
        """
        if not self.is_available:
            return None

        estimated_tokens = int(len(user_prompt) * 1.5)
        self.check_and_wait_for_quota(estimated_tokens)

        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        api_config = types.GenerateContentConfig(
            tools=[grounding_tool],
            system_instruction=system_prompt,
            temperature=temperature or self.temperature,
        )

        for attempt in range(self.retry_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    config=api_config,
                    contents=user_prompt,
                )

                # Track actual token usage
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    actual_tokens = response.usage_metadata.total_token_count
                    with self._calls_lock:
                        self._tokens_in_current_minute = (
                            self._tokens_in_current_minute - estimated_tokens + actual_tokens
                        )

                if response and response.text:
                    return self._parse_json_response(response.text)

                logger.error(f"Invalid response: {response.text if response else 'None'}")
                return None

            except Exception as e:
                if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    logger.warning(f"Rate limit hit, waiting {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"Error in API call: {e}")
                    if attempt < self.retry_attempts - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise

        return None

    def upload_file(self, file_path: str) -> str:
        """Upload a JSONL file to Google Cloud. Returns the file name."""
        uploaded = self.client.files.upload(
            file=file_path,
            config=types.UploadFileConfig(mime_type="application/jsonl"),
        )
        return uploaded.name

    def create_batch_job(self, uploaded_file_name: str):
        """Create a batch processing job. Returns the batch job object."""
        return self.client.batches.create(
            model=self.model_name,
            src=uploaded_file_name,
        )

    def get_batch_job(self, job_name: str):
        """Poll batch job status."""
        return self.client.batches.get(name=job_name)

    def download_file(self, file_name: str) -> str:
        """Download a file and return its content as string."""
        content_bytes = self.client.files.download(file=file_name)
        return content_bytes.decode("utf-8")

    def delete_file(self, file_name: str):
        """Delete a remote file."""
        try:
            self.client.files.delete(name=file_name)
        except Exception as e:
            logger.warning(f"Could not delete file {file_name}: {e}")

    @staticmethod
    def _parse_json_response(text: str) -> Optional[List[Dict]]:
        """Parse JSON from API response text."""
        text = text.strip().replace("```json", "").replace("```", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if "[" in text and "]" in text:
                json_str = text[text.find("["):text.rfind("]") + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        return None
