"""AI-powered commercial product image generator for gastronomy equipment."""

import html
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def clean_text_from_html(text: str) -> str:
    """Strip HTML tags and unescape HTML entities, returning cleaned text."""
    if not text:
        return ""
    # Unescape HTML entities
    unescaped = html.unescape(str(text))
    # Replace common HTML breaks/lists with punctuation or spaces
    unescaped = re.sub(r"</?(li|p|div|br\s*/?)>", " ", unescaped, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    clean = re.sub(r"<[^>]+>", " ", unescaped)
    # Normalize whitespaces
    return re.sub(r"\s+", " ", clean).strip()


def sanitize_filename(filename: str) -> str:
    """Sanitize a string to be a valid, safe filename across all operating systems."""
    # Replace illegal filename characters with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", str(filename).strip())
    return sanitized or "product"


class ProductImageGenerator:
    """Generates high-resolution commercial studio product photographs using Gemini multimodal models."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, api_key: Optional[str] = None):
        """Initialize the image generator with configuration and Gemini client."""
        config = config or {}
        img_config = config.get("image_generation", {})

        if api_key is not None:
            self.api_key = api_key
        else:
            load_dotenv()
            self.api_key = os.getenv("GOOGLE_API_KEY") or config.get("ai_enhancement", {}).get("api_key", "")

        self.model_name = img_config.get("model", "gemini-2.5-flash-image")
        self.output_dir = Path(img_config.get("output_dir", "out/generated_images"))
        self.aspect_ratio = img_config.get("aspect_ratio", "1:1")

        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini Client for image generation: {e}")

    @property
    def is_available(self) -> bool:
        """Check if client and API key are configured and ready."""
        return self.client is not None and bool(self.api_key)

    def build_image_prompt(self, product: Dict[str, Any]) -> str:
        """Construct a high-converting commercial photography prompt from product attributes."""
        name = clean_text_from_html(product.get("name", ""))
        category = clean_text_from_html(product.get("defaultCategory", "") or product.get("categoryText", ""))
        manufacturer = str(product.get("manufacturer", "")).strip()

        # Clean descriptions
        short_desc = clean_text_from_html(product.get("shortDescription", ""))
        desc = clean_text_from_html(product.get("description", ""))

        # Collect dimensions and key parameters
        spec_parts = []
        for key in ["variant:Dĺžka (mm)", "variant:Hĺbka (mm)", "variant:Šírka (mm)", "variant:Objem boxu"]:
            val = product.get(key)
            if val and str(val).strip():
                clean_key = key.replace("variant:", "")
                spec_parts.append(f"{clean_key}: {val}")

        for dim_key, dim_name in [
            ("feedWidth", "Width"),
            ("feedDepth", "Depth"),
            ("feedHeight", "Height"),
            ("weight", "Weight"),
        ]:
            val = product.get(dim_key)
            if val and str(val).strip() and str(val) != "nan":
                spec_parts.append(f"{dim_name}: {val}")

        specs_text = "; ".join(spec_parts)

        # Context summary from descriptions
        context_summary = short_desc or (desc[:300] if desc else "")

        prompt_lines = [
            f"Commercial studio product photograph of a professional gastro equipment item: {name}.",
        ]

        if category and "Neznáma kategória" not in category:
            prompt_lines.append(f"Product Category: {category}.")

        if manufacturer and manufacturer.lower() != "nan":
            prompt_lines.append(f"Manufacturer / Brand: {manufacturer}.")

        if specs_text:
            prompt_lines.append(f"Specifications / Dimensions: {specs_text}.")

        if context_summary:
            prompt_lines.append(f"Product Details: {context_summary[:350]}.")

        prompt_lines.extend(
            [
                "Visual Style & Environment:",
                "- Commercial e-commerce studio product photography.",
                "- Isolated on a seamless pure white background (#FFFFFF) with no background distractions.",
                "- Realistic materials (stainless steel INOX finish, chrome, or heavy-duty powder coating as appropriate).",
                "- Professional softbox studio lighting creating soft, natural reflections and a subtle soft drop shadow underneath.",
                "- Perspective: Front 3/4 three-quarters view showing depth and full product silhouette.",
                "- High sharpness, photorealistic, pristine catalog standard.",
                "- ABSOLUTELY NO text, NO watermarks, NO badges, NO human hands or people, NO messy kitchen background.",
            ]
        )

        return "\n".join(prompt_lines)

    def generate_image(
        self,
        product: Dict[str, Any],
        output_dir: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an image for a product and save it to disk.

        Returns:
            dict containing:
                success: bool
                code: str
                file_path: Optional[str]
                prompt: str
                prompt_tokens: int
                candidate_tokens: int
                total_tokens: int
                error: Optional[str]
        """
        code = str(product.get("code", "unknown")).strip()
        safe_code = sanitize_filename(code)
        target_dir = Path(output_dir) if output_dir else self.output_dir

        if not self.is_available:
            err_msg = "Gemini Client is not available or GOOGLE_API_KEY is missing."
            logger.error(err_msg)
            return {
                "success": False,
                "code": code,
                "file_path": None,
                "prompt": "",
                "error": err_msg,
            }

        prompt = custom_prompt or self.build_image_prompt(product)

        try:
            logger.info(f"Generating image for product '{code}' with model '{self.model_name}'...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )

            # Check response candidates
            if not response.candidates:
                err_msg = "No candidates returned by Gemini model."
                logger.error(f"Image generation failed for '{code}': {err_msg}")
                return {
                    "success": False,
                    "code": code,
                    "file_path": None,
                    "prompt": prompt,
                    "error": err_msg,
                }

            first_candidate = response.candidates[0]
            if not first_candidate.content or not first_candidate.content.parts:
                err_msg = "Empty content parts in candidate response."
                logger.error(f"Image generation failed for '{code}': {err_msg}")
                return {
                    "success": False,
                    "code": code,
                    "file_path": None,
                    "prompt": prompt,
                    "error": err_msg,
                }

            image_bytes = None
            for part in first_candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break

            if not image_bytes:
                err_msg = "No image data found in response parts."
                logger.error(f"Image generation failed for '{code}': {err_msg}")
                return {
                    "success": False,
                    "code": code,
                    "file_path": None,
                    "prompt": prompt,
                    "error": err_msg,
                }

            # Ensure output directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            output_file = target_dir / f"{safe_code}.png"
            output_file.write_bytes(image_bytes)

            # Token tracking
            prompt_tokens = 0
            candidate_tokens = 0
            total_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                candidate_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                total_tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0

            logger.info(
                f"Successfully generated and saved image to '{output_file}' "
                f"(Tokens: {total_tokens} total, {candidate_tokens} candidates)"
            )

            return {
                "success": True,
                "code": code,
                "file_path": str(output_file),
                "prompt": prompt,
                "prompt_tokens": prompt_tokens,
                "candidate_tokens": candidate_tokens,
                "total_tokens": total_tokens,
                "error": None,
            }

        except Exception as e:
            logger.exception(f"Exception during image generation for '{code}': {e}")
            return {
                "success": False,
                "code": code,
                "file_path": None,
                "prompt": prompt,
                "error": str(e),
            }

    def generate_batch(
        self,
        products: List[Dict[str, Any]],
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate images for a batch of products sequentially."""
        results = []
        total = len(products)
        for idx, product in enumerate(products, 1):
            res = self.generate_image(product, output_dir=output_dir)
            results.append(res)
            if progress_callback:
                progress_callback(idx, total, res)
        return results
