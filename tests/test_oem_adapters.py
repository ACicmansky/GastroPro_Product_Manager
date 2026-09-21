"""Unit tests for OEM specification adapters and adapter registry."""

from src.scrapers.oem import (
    ForcoldAdapter,
    HendiAdapter,
    LiebherrAdapter,
    RobotCoupeAdapter,
    RollerGrillAdapter,
    StalgastAdapter,
    find_oem_adapter,
    get_all_oem_adapters,
)


def test_get_all_oem_adapters():
    adapters = get_all_oem_adapters()
    assert len(adapters) == 6
    types = [type(a) for a in adapters]
    assert ForcoldAdapter in types
    assert LiebherrAdapter in types
    assert StalgastAdapter in types
    assert RobotCoupeAdapter in types
    assert RollerGrillAdapter in types
    assert HendiAdapter in types


def test_find_oem_adapter_routing():
    assert isinstance(find_oem_adapter("F840130", "Forcold chladnička"), ForcoldAdapter)
    assert isinstance(find_oem_adapter("LIEBHERR MRFVC 3501", "Chladnička"), LiebherrAdapter)
    assert isinstance(find_oem_adapter("S801501", "Umývačka Stalgast"), StalgastAdapter)
    assert isinstance(find_oem_adapter("ROC_R8", "Kuter Robot-Coupe"), RobotCoupeAdapter)
    assert isinstance(find_oem_adapter("ROLLER GRILL_WDL200", "Vitrína"), RollerGrillAdapter)
    assert isinstance(find_oem_adapter("H588031", "Fľaša na šľahačku"), HendiAdapter)
    assert find_oem_adapter("UNKNOWN_123", "Neznámy produkt") is None


# --- Robot-Coupe Tests ---


def test_robot_coupe_can_handle():
    adapter = RobotCoupeAdapter()
    assert adapter.can_handle("ROC_R8", "Kuter R 8")
    assert adapter.can_handle("ROC_ROBOTCOOK", "Robot Cook")
    assert adapter.can_handle("ROC_CL50", "Krájač zeleniny CL 50")
    assert adapter.can_handle("ROC_ 27046", "Plátkovací kotúč 2 mm")
    assert adapter.can_handle("OTHER", "Robot-Coupe Kuter R 4")
    assert not adapter.can_handle("S801501", "Stalgast umývačka")


def test_robot_coupe_extract_model():
    adapter = RobotCoupeAdapter()
    assert adapter.extract_model("ROC_R8", "Kuter R 8") == "R 8"
    assert adapter.extract_model("ROC_R5VV", "Kuter R 5 V.V.") == "R 5 V.V."
    assert adapter.extract_model("ROC_CL50", "Krájač CL 50") == "CL 50"
    assert adapter.extract_model("ROC_ROBOTCOOK", "Robot Cook") == "ROBOT COOK"
    assert adapter.extract_model("ROC_ 27046", "Plátkovací kotúč") == "27046"


def test_robot_coupe_specs():
    adapter = RobotCoupeAdapter()

    # R 8 Cutter
    specs_r8 = adapter.get_specs("ROC_R8", "Kuter R 8")
    assert specs_r8 is not None
    assert specs_r8["power_w"] == 2200
    assert specs_r8["voltage_v"] == "400"
    assert specs_r8["volume_l"] == 8.0
    assert specs_r8["width_mm"] == 315
    assert specs_r8["depth_mm"] == 545
    assert specs_r8["height_mm"] == 585
    assert "robot-coupe.com" in specs_r8["source_url"]

    # Robot Cook
    specs_rc = adapter.get_specs("ROC_ROBOTCOOK", "Robot Cook")
    assert specs_rc is not None
    assert specs_rc["power_w"] == 1800
    assert specs_rc["voltage_v"] == "230"
    assert specs_rc["volume_l"] == 3.7
    assert "+20°C" in specs_rc["temp_range"]

    # CL 50
    specs_cl50 = adapter.get_specs("ROC_CL50", "Krájač zeleniny CL 50")
    assert specs_cl50 is not None
    assert specs_cl50["power_w"] == 550
    assert specs_cl50["width_mm"] == 350
    assert specs_cl50["depth_mm"] == 320
    assert specs_cl50["height_mm"] == 590

    # R 60 Large Floor Cutter
    specs_r60 = adapter.get_specs("ROC_R60", "Kuter R 60")
    assert specs_r60 is not None
    assert specs_r60["power_w"] == 11000
    assert specs_r60["volume_l"] == 60.0

    # Accessory code (numeric)
    specs_acc = adapter.get_specs("ROC_ 27046", "Plátkovací kotúč")
    assert specs_acc is not None
    assert specs_acc["model_code"] == "27046"
    assert "query=27046" in specs_acc["source_url"]


# --- Roller Grill Tests ---


def test_roller_grill_can_handle():
    adapter = RollerGrillAdapter()
    assert adapter.can_handle("ROLLER GRILL_WDL200", "Vitrína WDL 200")
    assert adapter.can_handle("ROLLER GRILL_WD780S", "Vitrína WD 780 S")
    assert adapter.can_handle("ROLLER GRILL_SGM800", "Salamander SGM 800")
    assert adapter.can_handle("OTHER", "Roller Grill kontaktný gril Panini")
    assert not adapter.can_handle("ROC_R8", "Robot-Coupe kuter")


def test_roller_grill_extract_model():
    adapter = RollerGrillAdapter()
    assert adapter.extract_model("ROLLER GRILL_WDL200", "Vitrína WDL 200") == "WDL 200"
    assert adapter.extract_model("ROLLER GRILL_WD780S", "Vitrína WD 780 S") == "WD 780 S"
    assert adapter.extract_model("ROLLER GRILL_SEM800PDS", "Salamander SEM 800 PDS") == "SEM 800 PDS"
    assert adapter.extract_model("ROLLER GRILL_MF 120 R", "Fritéza MF 120 R") == "MF 120 R"


def test_roller_grill_specs():
    adapter = RollerGrillAdapter()

    # WDL 200 Showcase
    specs_wdl = adapter.get_specs("ROLLER GRILL_WDL200", "Vitrína WDL 200")
    assert specs_wdl is not None
    assert specs_wdl["power_w"] == 650
    assert specs_wdl["voltage_v"] == "230"
    assert specs_wdl["width_mm"] == 590
    assert specs_wdl["depth_mm"] == 350
    assert specs_wdl["height_mm"] == 480
    assert specs_wdl["temp_range"] == "+20°C až +90°C"
    assert "rollergrill.com" in specs_wdl["source_url"]

    # SGM 800 Salamander
    specs_sgm = adapter.get_specs("ROLLER GRILL_SGM800", "Salamander SGM 800")
    assert specs_sgm is not None
    assert specs_sgm["power_w"] == 4000
    assert specs_sgm["voltage_v"] == "400"
    assert specs_sgm["width_mm"] == 800

    # MF 120 R Fryer
    specs_mf = adapter.get_specs("ROLLER GRILL_MF 120 R", "Fritéza MF 120 R")
    assert specs_mf is not None
    assert specs_mf["power_w"] == 3200
    assert specs_mf["volume_l"] == 12
    assert specs_mf["width_mm"] == 350
    assert specs_mf["depth_mm"] == 470
    assert specs_mf["height_mm"] == 350

    # Panini Contact Grill
    specs_panini = adapter.get_specs("ROLLER GRILL_PANINI", "Kontaktný gril Panini")
    assert specs_panini is not None
    assert specs_panini["power_w"] == 3000
    assert specs_panini["width_mm"] == 430
    assert specs_panini["temp_range"] == "+50°C až +300°C"


# --- Hendi Tests ---


def test_hendi_can_handle():
    adapter = HendiAdapter()
    assert adapter.can_handle("H588031", "Fľaša na šľahačku")
    assert adapter.can_handle("H154601", "Gastropekáč MINI")
    assert adapter.can_handle("OTHER", "Hendi digitálna váha")
    assert not adapter.can_handle("ROC_R8", "Robot-Coupe kuter")


def test_hendi_extract_article_number():
    adapter = HendiAdapter()
    assert adapter.extract_article_number("H588031", "Fľaša na šľahačku") == "588031"
    assert adapter.extract_article_number("H154601", "Gastropekáč") == "154601"
    assert adapter.extract_article_number("OTHER", "Hendi váha 580233") == "580233"


def test_hendi_specs():
    adapter = HendiAdapter()

    # Whipper 588031
    specs_whip = adapter.get_specs("H588031", "Fľaša na šľahačku 0,25 l")
    assert specs_whip is not None
    assert specs_whip["volume_l"] == 0.25
    assert specs_whip["source_url"] == "https://www.hendi.com/sk-sk/product/588031"

    # Roaster 154601
    specs_roast = adapter.get_specs("H154601", "Gastropekáč Hendi MINI")
    assert specs_roast is not None
    assert specs_roast["power_w"] == 5800
    assert specs_roast["width_mm"] == 340
    assert specs_roast["depth_mm"] == 540
    assert specs_roast["height_mm"] == 300

    # Scale 580233
    specs_scale = adapter.get_specs("H580233", "Kuchynská digitálna váha MIDI")
    assert specs_scale is not None
    assert specs_scale["width_mm"] == 200
    assert specs_scale["depth_mm"] == 150
    assert specs_scale["height_mm"] == 30
