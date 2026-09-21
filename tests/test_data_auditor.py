import pandas as pd
from src.domain.specs.auditor import CatalogAuditor


def test_auditor_detects_insulation_mismatch():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "F840130",
                "name": "Forcold chladnička 1300l",
                "defaultCategory": "Chladenie > Skriňové chladničky",
                "shortDescription": "Hrúbka steny: 70 mm.",
                "description": "Izolácia s hrúbkou 70 mm.",
                "filteringProperty:Hrúbka izolácie (mm)": "60",
            }
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert len(issues) == 1
    assert issues.iloc[0]["code"] == "F840130"
    assert issues.iloc[0]["issue_type"] == "TEXT_PARAM_MISMATCH"
    assert issues.iloc[0]["detected_in_text"] == "70"
    assert issues.iloc[0]["param_value"] == "60"


def test_auditor_detects_conflicting_text_insulation():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "TEST1",
                "name": "Test fridge",
                "shortDescription": "Izolácia: 60 mm.",
                "description": "Hrúbka steny: 70 mm.",
            }
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert len(issues) == 1
    assert issues.iloc[0]["issue_type"] == "CONFLICTING_TEXT_VALUES"


def test_auditor_detects_power_mismatch():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "TEST2",
                "name": "Test oven",
                "shortDescription": "Výkon: 5.5 kW.",
                "description": "",
                "filteringProperty:Príkon (W)": "2000",
            }
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert any(i["issue_type"] == "TEXT_PARAM_MISMATCH" for _, i in issues.iterrows())


def test_auditor_detects_geometric_impossibility():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "TEST3",
                "name": "Tardis Box",
                "filteringProperty:Šírka (mm)": "500",
                "filteringProperty:Hĺbka (mm)": "500",
                "filteringProperty:Výška (mm)": "500",  # Gross volume = 125 L
                "filteringProperty:Objem (l)": "300",  # Impossible: 300 L inside 125 L outer box
            }
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert any(i["issue_type"] == "GEOMETRIC_IMPOSSIBILITY" for _, i in issues.iterrows())


def test_auditor_passes_clean_data():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "CLEAN1",
                "name": "Clean Refrigerator",
                "shortDescription": "Hrúbka steny: 60 mm. Výkon: 0.5 kW / 230 V. Rozmery: 1480x830x2010 mm.",
                "description": "Izolácia s hrúbkou 60 mm.",
                "filteringProperty:Hrúbka izolácie (mm)": "60",
                "filteringProperty:Príkon (W)": "500",
                "filteringProperty:Napätie (V)": "230",
                "filteringProperty:Šírka (mm)": "1480",
                "filteringProperty:Hĺbka (mm)": "830",
                "filteringProperty:Výška (mm)": "2010",
                "filteringProperty:Objem (l)": "1300",
            }
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert len(issues) == 0


def test_auditor_ignores_sink_basin_subcomponent_dimension():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "S980727110",
                "name": "Umývací stôl krytovaný s drezom 1100x700x850mm",
                "shortDescription": "Zabudovaný drez s rozmermi 500x500x250 mm.",
                "description": "Vanička drezu: 500x500x250 mm.",
                "filteringProperty:Šírka (mm)": "1100",
                "filteringProperty:Hĺbka (mm)": "700",
                "filteringProperty:Výška (mm)": "850",
            }
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert len(issues) == 0


def test_auditor_handles_multi_power_and_split_power():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "LAMP1",
                "name": "Lapač hmyzu 2x 6W",
                "shortDescription": "Žiarivky: 2x 6W.",
                "description": "",
                "filteringProperty:Príkon (W)": "12",
            },
            {
                "code": "PIZZA1",
                "name": "Pizza stôl",
                "shortDescription": "Chladiaci výkon 0,24 + 0,12 kW.",
                "description": "",
                "filteringProperty:Príkon (W)": "360",
            },
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert len(issues) == 0


def test_auditor_allows_sous_vide_circulator_volume():
    auditor = CatalogAuditor()
    df = pd.DataFrame(
        [
            {
                "code": "S691100",
                "name": "Cirkulátor SOUS-VIDE EKO",
                "defaultCategory": "Varenie > Sous-vide",
                "filteringProperty:Šírka (mm)": "145",
                "filteringProperty:Hĺbka (mm)": "115",
                "filteringProperty:Výška (mm)": "325",
                "filteringProperty:Objem (l)": "26",  # 26 L water bath capacity
            }
        ]
    )
    issues = auditor.audit_dataframe(df)
    assert len(issues) == 0
