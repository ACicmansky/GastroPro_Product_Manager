from src.scrapers.oem.forcold_adapter import ForcoldAdapter


def test_forcold_adapter_can_handle():
    adapter = ForcoldAdapter()
    assert adapter.can_handle("F840130", "Forcold chladnička 1300l")
    assert adapter.can_handle("F840650", "Chladnička Forcold 650l")
    assert adapter.can_handle("OTHER", "Forcar chladiaca skriňa GN1410TN")
    assert not adapter.can_handle("ST265031", "Stalgast stôl")


def test_forcold_adapter_specs_f840130():
    adapter = ForcoldAdapter()
    specs = adapter.get_specs("F840130", "Forcold chladnička 1300l")
    assert specs is not None
    assert specs["insulation_mm"] == 60
    assert specs["volume_l"] == 1300
    assert specs["power_w"] == 508
    assert specs["voltage_v"] == "230"
    assert specs["width_mm"] == 1480
    assert specs["depth_mm"] == 830
    assert specs["height_mm"] == 2010
    assert "forcold.it" in specs["source_url"]


def test_forcold_adapter_specs_f840650():
    adapter = ForcoldAdapter()
    specs = adapter.get_specs("F840650", "Forcold chladnička 650l")
    assert specs is not None
    assert specs["insulation_mm"] == 60
    assert specs["volume_l"] == 650
    assert specs["power_w"] == 360
