"""
Pytest configuration and fixtures for GastroPro Product Manager tests.
"""

import pytest
import pandas as pd
import json
from pathlib import Path


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_old_format_df():
    """Create sample DataFrame in old format."""
    data = {
        "Kat. číslo": ["TEST001", "TEST002", "TEST003"],
        "Názov tovaru": ["Product 1", "Product 2", "Product 3"],
        "Bežná cena": ["100.00", "200.00", "300.00"],
        "Výrobca": ["Manufacturer A", "Manufacturer B", "Manufacturer A"],
        "Hlavna kategória": [
            "Category1/SubCat1",
            "Category2/SubCat2",
            "Category1/SubCat1",
        ],
        "Krátky popis": ["Short desc 1", "Short desc 2", "Short desc 3"],
        "Dlhý popis": ["Long desc 1", "Long desc 2", "Long desc 3"],
        "Váha": ["1.5", "2.0", "0.5"],
        "Obrázky": ["img1.jpg,img2.jpg", "img3.jpg", "img4.jpg,img5.jpg,img6.jpg"],
        "Viditeľný": ["1", "1", "1"],
        "Spracovane AI": ["False", "False", "False"],
        "AI_Processed_Date": ["", "", ""],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_new_format_df():
    """Create sample DataFrame in new format."""
    data = {
        "code": ["TEST001", "TEST002", "TEST003"],
        "name": ["Product 1", "Product 2", "Product 3"],
        "price": ["100.00", "200.00", "300.00"],
        "manufacturer": ["Manufacturer A", "Manufacturer B", "Manufacturer A"],
        "defaultCategory": [
            "Tovary a kategórie > Category1 > SubCat1",
            "Tovary a kategórie > Category2 > SubCat2",
            "Tovary a kategórie > Category1 > SubCat1",
        ],
        "categoryText": [
            "Tovary a kategórie > Category1 > SubCat1",
            "Tovary a kategórie > Category2 > SubCat2",
            "Tovary a kategórie > Category1 > SubCat1",
        ],
        "shortDescription": ["Short desc 1", "Short desc 2", "Short desc 3"],
        "description": ["Long desc 1", "Long desc 2", "Long desc 3"],
        "weight": ["1.5", "2.0", "0.5"],
        "image": ["img2.jpg", "", "img5.jpg"],
        "image2": ["", "", "img6.jpg"],
        "aiProcessed": ["False", "False", "False"],
        "aiProcessedDate": ["", "", ""],
        "currency": ["EUR", "EUR", "EUR"],
        "includingVat": ["1", "1", "1"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_category_mappings():
    """Create sample category mappings."""
    return [
        {"oldCategory": "Category1/SubCat1", "newCategory": "Mapped Category 1"},
        {"oldCategory": "Category2/SubCat2", "newCategory": "Mapped Category 2"},
    ]


@pytest.fixture
def sample_xml_gastromarket():
    """Sample GastroMarket XML data with Google Base namespace (prefixed)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
<channel>
    <title>Partner Feed SK</title>
    <description>Partner Feed SK</description>
    <link>https://www.gastromarket.sk</link>
    <item>
        <g:UPDATE>2025-11-06 14:19:34.297869</g:UPDATE>
        <g:KATALOG_CISLO>GM001</g:KATALOG_CISLO>
        <g:MENO>GastroMarket Product 1</g:MENO>
        <g:POPIS>Short description from GM</g:POPIS>
        <g:CENA_KATALOG>150.00</g:CENA_KATALOG>
        <g:KATEGORIA_KOMPLET>Nerezový nábytok/Pracovné stoly, pevné</g:KATEGORIA_KOMPLET>
        <g:OBRAZOK_1>http://example.com/gm1.jpg</g:OBRAZOK_1>
        <g:META_POPIS>Meta description</g:META_POPIS>
        <g:DOSTUPNOST>11.0</g:DOSTUPNOST>
        <g:META_TITUL>Meta title</g:META_TITUL>
    </item>
</channel>
</rss>"""


@pytest.fixture
def sample_xml_forgastro():
    """Sample ForGastro XML data."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<products>
    <product>
        <product_sku>FG001</product_sku>
        <product_name>ForGastro Product 1</product_name>
        <product_price>250.00</product_price>
        <manufacturer>FG Manufacturer</manufacturer>
        <category>FG Category</category>
        <product_s_desc>Short desc from FG</product_s_desc>
        <product_desc>Long desc from FG</product_desc>
        <images>
            <item>
                <url>http://example.com/fg1.jpg</url>
            </item>
        </images>
        <product_weight>3.5</product_weight>
    </product>
</products>"""


@pytest.fixture
def sample_xml_forgastro_with_html():
    """Sample ForGastro XML data with HTML content in description."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<products>
    <product>
        <product_sku>FG002</product_sku>
        <product_name>ForGastro Product with HTML</product_name>
        <product_price>350.00</product_price>
        <manufacturer>FG Manufacturer</manufacturer>
        <category>FG Category</category>
        <product_s_desc>Initial short desc</product_s_desc>
        <product_desc>{tab title="popis"}&lt;p&gt;This is a professional gastronomy product with excellent features.&lt;/p&gt;{tab title="parametre"}&lt;table&gt;&lt;tr&gt;&lt;th&gt;Parameter&lt;/th&gt;&lt;th&gt;Value&lt;/th&gt;&lt;/tr&gt;&lt;tr&gt;&lt;td&gt;Width&lt;/td&gt;&lt;td&gt;600mm&lt;/td&gt;&lt;/tr&gt;&lt;tr&gt;&lt;td&gt;Height&lt;/td&gt;&lt;td&gt;850mm&lt;/td&gt;&lt;/tr&gt;&lt;/table&gt;{/tabs}</product_desc>
        <images>
            <item>
                <url>http://example.com/fg2.jpg</url>
            </item>
        </images>
        <product_weight>5.0</product_weight>
    </product>
</products>"""
