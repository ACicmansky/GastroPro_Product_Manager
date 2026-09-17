"""Unit tests for ProductImageGenerator and prompt building."""

from unittest.mock import MagicMock, patch
from src.ai.image_generator import (
    ProductImageGenerator,
    clean_text_from_html,
    sanitize_filename,
)


def test_clean_text_from_html():
    """Test HTML cleaning and entity unescaping."""
    raw = "<strong>Profesionálny</strong> chafing dish &amp; príslušenstvo.<br><ul><li>Rozmer GN 1/1</li></ul>"
    cleaned = clean_text_from_html(raw)
    assert "Profesionálny" in cleaned
    assert "chafing dish & príslušenstvo." in cleaned
    assert "Rozmer GN 1/1" in cleaned
    assert "<" not in cleaned
    assert ">" not in cleaned

    assert clean_text_from_html("") == ""
    assert clean_text_from_html(None) == ""


def test_sanitize_filename():
    """Test filename sanitization for various dangerous characters."""
    assert sanitize_filename("ST:133/081?*<>|") == "ST_133_081_____"
    assert sanitize_filename("   PRODUCT123   ") == "PRODUCT123"
    assert sanitize_filename("") == "product"


def test_generator_initialization(config):
    """Test initialization with config."""
    generator = ProductImageGenerator(config=config, api_key="fake-key")
    assert generator.model_name == "gemini-2.5-flash-image"
    assert str(generator.output_dir).replace("\\", "/") == "out/generated_images"
    assert generator.api_key == "fake-key"
    assert generator.is_available is True


def test_generator_not_available_without_key():
    """Test is_available is False without API key."""
    with patch.dict("os.environ", {}, clear=True):
        generator = ProductImageGenerator(config={}, api_key="")
        assert generator.is_available is False


def test_build_image_prompt():
    """Test commercial photography prompt generation."""
    generator = ProductImageGenerator(config={}, api_key="fake-key")
    product = {
        "code": "S436120",
        "name": "Chafing Dish GN 1/1 | odnímateľné veko | nerez | STALGAST 436120",
        "defaultCategory": "Gastro Prevádzky > Bufetové systémy",
        "manufacturer": "STALGAST",
        "shortDescription": "<strong>Profesionálny chafing dish s ohrevom na palivovú pastu.</strong>",
        "variant:Dĺžka (mm)": "620",
        "variant:Hĺbka (mm)": "360",
        "variant:Šírka (mm)": "320",
    }
    prompt = generator.build_image_prompt(product)
    assert "Commercial studio product photograph" in prompt
    assert "Chafing Dish GN 1/1" in prompt
    assert "STALGAST" in prompt
    assert "Dĺžka (mm): 620" in prompt
    assert "Bufetové systémy" in prompt
    assert "seamless pure white background (#FFFFFF)" in prompt
    assert "ABSOLUTELY NO text, NO watermarks" in prompt


def test_generate_image_not_available():
    """Test generate_image fails safely when client not available."""
    with patch.dict("os.environ", {}, clear=True):
        generator = ProductImageGenerator(config={}, api_key="")
        result = generator.generate_image({"code": "TEST1"})
        assert result["success"] is False
        assert "not available" in result["error"].lower()


def test_generate_image_success(tmp_path):
    """Test successful image generation with mocked GenAI client."""
    generator = ProductImageGenerator(config={}, api_key="fake-key")

    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.inline_data.data = b"\x89PNG\r\n\x1a\nFakeImageData"
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_response.candidates = [mock_candidate]

    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 150
    mock_usage.candidates_token_count = 1290
    mock_usage.total_token_count = 1440
    mock_response.usage_metadata = mock_usage

    generator.client.models.generate_content = MagicMock(return_value=mock_response)

    product = {
        "code": "PROD-999",
        "name": "Nerezový pracovný stôl",
    }
    out_dir = tmp_path / "test_images"
    result = generator.generate_image(product, output_dir=str(out_dir))

    assert result["success"] is True
    assert result["code"] == "PROD-999"
    assert result["prompt_tokens"] == 150
    assert result["candidate_tokens"] == 1290
    assert result["total_tokens"] == 1440
    assert result["file_path"] is not None

    saved_file = tmp_path / "test_images" / "PROD-999.png"
    assert saved_file.exists()
    assert saved_file.read_bytes() == b"\x89PNG\r\n\x1a\nFakeImageData"


def test_generate_batch(tmp_path):
    """Test batch generation calling callback."""
    generator = ProductImageGenerator(config={}, api_key="fake-key")

    mock_result = {
        "success": True,
        "code": "TEST",
        "file_path": "/fake/path.png",
        "prompt": "prompt",
        "prompt_tokens": 10,
        "candidate_tokens": 20,
        "total_tokens": 30,
        "error": None,
    }
    generator.generate_image = MagicMock(return_value=mock_result)

    products = [{"code": "P1"}, {"code": "P2"}]
    progress_calls = []

    def callback(current, total, res):
        progress_calls.append((current, total, res["code"]))

    results = generator.generate_batch(products, output_dir=str(tmp_path), progress_callback=callback)

    assert len(results) == 2
    assert progress_calls == [(1, 2, "TEST"), (2, 2, "TEST")]
