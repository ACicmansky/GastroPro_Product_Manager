"""End-to-end chain on checked-in fixtures: parse -> merge -> transform.

Guards the two production bugs from 2026-07-06: products of unfetched
sources being discontinued, and categories wiped by the transformer.
"""

from pathlib import Path

import pytest

from src.config.config_loader import load_config
from src.data.loaders.xlsx_loader import load_xlsx
from src.data.parsers.xml_parser_factory import XMLParserFactory
from src.domain.products.merger import ProductMerger
from src.domain.transform.output_transformer import OutputTransformer

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def config():
    return load_config("config.json")


@pytest.fixture(scope="module")
def feed_dfs(config):
    return {
        name: XMLParserFactory.parse(
            name, (FIXTURES / f"{name}.xml").read_text(encoding="utf-8"), config
        )
        for name in ("gastromarket", "forgastro")
    }


@pytest.mark.integration
class TestPipelineChain:
    def test_feeds_parse(self, feed_dfs):
        gm, fg = feed_dfs["gastromarket"], feed_dfs["forgastro"]
        assert set(gm["code"]) == {"G1", "G3"}
        assert set(fg["code"]) == {"F1"}
        assert (gm["defaultCategory"] != "").all()
        assert (fg["defaultCategory"] != "").all()

    def test_merge_preserve_edits(self, feed_dfs):
        main_df = load_xlsx(FIXTURES / "main.xlsx")
        result = ProductMerger().merge(main_df, feed_dfs, preserve_edits=True)
        codes = set(result.products["code"])
        # G2 gone from its fetched feed -> discontinued
        assert "G2" not in codes
        # core, legacy web_scraping (scrapers not run) and variants survive;
        # G3 is new from the feed
        assert {"C1", "C2", "F1", "W1", "V1", "V2", "G1", "G3"} == codes

    def test_transform_keeps_categories(self, feed_dfs, config):
        main_df = load_xlsx(FIXTURES / "main.xlsx")
        merged = ProductMerger().merge(main_df, feed_dfs, preserve_edits=True).products
        output = OutputTransformer(config).transform(merged)

        assert len(output) == len(merged)
        out_by_code = output.set_index("code")["defaultCategory"]
        for _, row in merged.iterrows():
            if str(row["defaultCategory"]).strip():
                out_cat = out_by_code[row["code"]]
                assert out_cat.startswith("Tovary a kategórie > "), (
                    f"category wiped for {row['code']}: {out_cat!r}"
                )
