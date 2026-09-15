"""Tests for input text pruning and token optimization."""

from src.ai.pruning import prune_text


def test_prune_text_none_and_empty():
    assert prune_text(None) == ""
    assert prune_text("") == ""
    assert prune_text("   \n\t  ") == ""


def test_prune_text_strips_html_and_unescapes():
    raw = "<p>Profesionálny <strong>nerezový</strong> stôl &amp; stolička.&nbsp;</p>"
    result = prune_text(raw)
    assert "<" not in result
    assert ">" not in result
    assert "&amp;" not in result
    assert "&nbsp;" not in result
    assert "Profesionálny nerezový stôl & stolička." in result


def test_prune_text_preserves_structure_with_newlines():
    raw = "<p>Úvodný text.</p><ul><li>Výkon: 2000 W</li><li>Napätie: 230 V</li></ul>"
    result = prune_text(raw)
    lines = result.splitlines()
    assert any("Úvodný text." in line for line in lines)
    assert any("Výkon: 2000 W" in line for line in lines)
    assert any("Napätie: 230 V" in line for line in lines)


def test_prune_text_truncates_on_word_boundary():
    text = "Slovo1 Slovo2 Slovo3 Slovo4 Slovo5 Slovo6 Slovo7 Slovo8"
    # Limit to 35 chars
    result = prune_text(text, max_chars=35)
    assert len(result) <= 35
    # Should not cut inside a word like 'Slov'
    assert not result.endswith("Slov")
    assert result.endswith("Slovo5")


def test_prune_text_leaves_short_text_intact():
    text = "Nerezový stôl 1200x700x850 mm"
    assert prune_text(text, max_chars=100) == text


def test_batch_orchestrator_prunes_input_descriptions():
    import json
    import pandas as pd
    from src.ai.batch_orchestrator import BatchOrchestrator

    class DummyClient:
        is_available = True
        model_name = "gemini-3.8-flash"

    orch = BatchOrchestrator(
        client=DummyClient(),
        result_parser=None,
        config={
            "ai_enhancement": {
                "max_desc_chars": 50,
                "max_short_desc_chars": 30,
            }
        },
    )

    long_html_desc = (
        "<p>Tento popis je <strong>mimoriadne dlhý</strong> a obsahuje mnoho slov ktoré presahujú limit.</p>"
    )
    long_html_sdesc = "<div>Krátky popis ktorý je príliš dlhý pre limit</div>"
    df = pd.DataFrame(
        [
            {
                "code": "TEST01",
                "name": "Názov",
                "defaultCategory": "Tovary a kategórie > Gastro",
                "shortDescription": long_html_sdesc,
                "description": long_html_desc,
            }
        ]
    )

    requests = []
    orch._build_category_requests(df, {0}, requests, is_group1=False)

    assert len(requests) == 1
    content_text = requests[0]["request"]["contents"][0]["parts"][0]["text"]
    products_payload = json.loads(content_text)
    product = products_payload[0]

    # HTML must be stripped and lengths constrained
    assert "<" not in product["shortDescription"]
    assert "<" not in product["description"]
    assert len(product["shortDescription"]) <= 30
    assert len(product["description"]) <= 50
