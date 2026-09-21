"""Unit tests for Liebherr OEM Adapter."""

from src.scrapers.oem.liebherr_adapter import LiebherrAdapter


def test_liebherr_can_handle():
    adapter = LiebherrAdapter()
    assert adapter.can_handle("LIEBHERR CTEL 2131", "Liebherr CTEL 2131")
    assert adapter.can_handle("LIEBHERR IRF 5101 PURE", "Liebherr IRf 5101 Pure")
    assert adapter.can_handle("RANDOM123", "Chladnička Liebherr 350L")
    assert not adapter.can_handle("F840130", "Forcold chladnička")


def test_liebherr_extract_model():
    adapter = LiebherrAdapter()
    assert adapter.extract_model("LIEBHERR CTEL 2131", "") == "CTEL 2131"
    assert adapter.extract_model("LIEBHERR IRF 5101 PURE", "") == "IRF 5101"
    assert adapter.extract_model("LIEBHERR SUIB 1550 PREMIUM", "") == "SUIB 1550"


def test_liebherr_get_known_specs():
    adapter = LiebherrAdapter()
    specs = adapter.get_specs("LIEBHERR CTEL 2131", "Liebherr CTEL 2131")
    assert specs is not None
    assert specs["volume_l"] == 196
    assert specs["width_mm"] == 550
    assert specs["depth_mm"] == 630
    assert specs["height_mm"] == 1241
    assert "CTel+2131" in specs["source_url"]


def test_liebherr_fallback_search_url():
    adapter = LiebherrAdapter()
    specs = adapter.get_specs("LIEBHERR UNKNOWN999", "Liebherr Unknown 999")
    assert specs is not None
    assert specs["volume_l"] is None
    assert "UNKNOWN999" in specs["source_url"]
