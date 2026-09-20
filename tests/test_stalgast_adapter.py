from src.scrapers.oem.stalgast_adapter import StalgastAdapter


def test_stalgast_adapter_can_handle():
    adapter = StalgastAdapter()
    assert adapter.can_handle("S852172", "Vitrína na zákusky")
    assert adapter.can_handle("ST265031", "Stojan na tácky")
    assert not adapter.can_handle("F840130", "Forcold chladnička")


def test_stalgast_adapter_specs():
    adapter = StalgastAdapter()
    specs = adapter.get_specs("S852172", "Vitrína na zákusky")
    assert specs is not None
    assert specs["model_code"] == "852172"
    assert specs["source_url"] == "https://stalgast.com/produkt/852172"
