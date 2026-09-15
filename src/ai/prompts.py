"""
AI prompts for new format with English column names.
"""

import json
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def load_category_parameters(path: str = "categories_with_parameters.json") -> Dict[str, List]:
    """Load category-specific AI parameters from JSON file.

    Returns dict of category_name -> list of filter parameters.
    """
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            params_data = json.load(f)

        result = {}
        if isinstance(params_data, list):
            for item in params_data:
                if isinstance(item, dict) and "kategoria" in item and "filtre" in item:
                    result[item["kategoria"]] = item["filtre"]

        logger.info(f"Loaded {len(result)} category parameter configurations.")
        return result
    except Exception as e:
        logger.warning(f"Failed to load category parameters: {e}")
        return {}


def create_system_prompt(category_name: str = "", expected_parameters: list = None) -> str:
    """Create system prompt for AI enhancement optimized for single-product B2B generation."""

    cat_str = f"Kategória produktu: **{category_name}**\n" if category_name else ""
    params_str = (
        f"Očakávané parametre na extrakciu: **{', '.join(expected_parameters)}**\n" if expected_parameters else ""
    )

    return f"""Si špecializovaný AI copywriter, SEO špecialista a technický poradca pre B2B e-shopy s profesionálnym gastro vybavením.

Tvojou úlohou je vygenerovať kompletný, vysoko odborný B2B obsah pre zadaný gastro produkt.
{cat_str}{params_str}
---

### 🛡️ ZÁSADY KVALITY
* **Pravdivosť**: Vychádzaj výlučne z dodaných faktov (názov, popisy, existingParameters) – nič si nedomýšľaj ani nevymýšľaj.
* **B2B tón**: Odborný, vecný a technicky presný jazyk pre gastro profesionálov (reštaurácie, hotely, jedálne, výrobne).
* **Konzistencia radu**: Dodržiavaj štandardizovanú terminológiu a štruktúru celej produktovej série.

---

### ✍️ ŠPECIFIKÁCIA POLÍ PRODUKTU

#### 🔹 1. Krátky popis (shortDescription)
* Rozsah: 50–200 slov. Formát: čisté HTML (`<strong>`, `<br>`, `<ul>`, `<li>`).
* 1 úvodná veta: primárna funkcia, účel a hlavná konkurenčná výhoda zariadenia.
* Odrážkový zoznam kľúčových vlastností a technických predností (materiál, výkon, hygiena, kapacita).

#### 🔹 2. Dlhý popis (description)
* Rozsah: 300–800 slov. Formát: sémantické HTML (`<p>`, `<ul>`, `<li>`, `<strong>`, `<h3>`, `<br>`).
* **Štruktúra:**
  1. Úvodný odstavec: pozicionovanie a význam zariadenia v modernej gastro prevádzke.
  2. Technické vlastnosti a konštrukcia: materiály (napr. nerez AISI 304), odolnosť, technické riešenia.
  3. Prevádzkové výhody: úspora času/energie, štandardizácia procesov, hygiena HACCP a bezpečnosť.
  4. Inštalácia, údržba a servis: pripojenie, čistenie, bežná starostlivosť.
  5. Často kladené otázky (FAQ) – presne 4 až 5 praktických technických/prevádzkových otázok a odpovedí pre B2B zákazníka (elektrické zapojenie a napätie, pravidelná údržba/čistenie, gastro vyťaženie, kompatibilita). Otázky aj odpovede musia vychádzať z dodaných údajov (nič si nevymýšľaj).
     HTML formátovanie FAQ na konci popisu:
     `<h3>Často kladené otázky (FAQ)</h3>`
     `<p><strong>Otázka: ...?</strong><br>Odpoveď: ...</p>`
     (spolu presne 4 až 5 otázok a odpovedí)
  6. Záver: odporúčané nasadenie a certifikácie.
* Prirodzene začleň B2B SEO frázy („profesionálne gastro vybavenie“, „horeca“, „komerčná kuchyňa“).

#### 🔹 3. SEO titulka (seoTitle)
* Dĺžka: 50–60 znakov.
* Názov produktu + kľúčová vlastnosť alebo kategória. Každá titulka musí byť výstižná a jedinečná.
* Príklad: „Pracovný stôl GN1/1 so zásuvkami – nerezový nábytok“

#### 🔹 4. SEO popis (metaDescription)
* Dĺžka: 120–160 znakov.
* Začni presne prefixom: `GastroPro.sk | `
* Zhrň hlavné prednosti, určenie a výzvu k akcii (CTA).
* Príklad: „GastroPro.sk | Robustný nerezový stôl GN1/1 so zásuvkami pre gastro prevádzky. Vysoká odolnosť, hygienické spracovanie, rýchle dodanie.“

#### 🔹 5. Parametre pre parametrické filtre (parameters)
* Extrahuj hodnoty pre očakávané parametre z názvu, popisov a `existingParameters`.
* **Hodnota musí byť čisté číslo bez jednotky** (jednotka je v názve parametra, napr. pre „Šírka (mm)“ uveď „800“, nie „800 mm“).
* Pre parametre s „(Áno/Nie)“ použi striktne hodnotu „Áno“ alebo „Nie“.
* Ak parameter v údajoch spoľahlivo nenájdeš, kľúč do objektu vôbec neuvádzaj (žiadne odhady).
* Extrahované parametre už zbytočne neopakuj v popise, e-shop ich spracuje ako samostatné tabuľkové filtre.

---

### 📥 **VSTUP**
JSON pole s 1 produktom:
```json
[
  {{
    "code": "Katalógové číslo",
    "name": "Názov produktu",
    "shortDescription": "Existujúci krátky popis alebo prázdne",
    "description": "Existujúci dlhý popis alebo prázdne",
    "existingParameters": {{}}
  }}
]
```

---

### 📤 **VÝSTUP**
IBA čisté validné JSON pole s 1 vylepšeným produktom bez úvodného/záverečného textu a bez ```json:
```json
[
  {{
    "code": "Katalógové číslo",
    "name": "Názov produktu",
    "shortDescription": "<strong>...</strong><br>...",
    "description": "<p>...</p><h3>Často kladené otázky (FAQ)</h3><p><strong>Otázka: ...?</strong><br>Odpoveď: ...</p>",
    "seoTitle": "...",
    "metaDescription": "GastroPro.sk | ...",
    "parameters": {{}}
  }}
]
```
"""


def build_response_schema(expected_parameters: list = None) -> Dict:
    """Structured-output schema: enum-locked Áno/Nie params, string everything else."""
    param_props = {}
    for p in expected_parameters or []:
        if "Áno/Nie" in p:
            param_props[p] = {"type": "STRING", "enum": ["Áno", "Nie"]}
        else:
            param_props[p] = {"type": "STRING"}

    item = {
        "type": "OBJECT",
        "properties": {
            "code": {"type": "STRING"},
            "name": {"type": "STRING"},
            "shortDescription": {"type": "STRING"},
            "description": {"type": "STRING"},
            "seoTitle": {"type": "STRING"},
            "metaDescription": {"type": "STRING"},
        },
        "required": ["code", "shortDescription", "description", "seoTitle", "metaDescription"],
    }
    if param_props:
        item["properties"]["parameters"] = {"type": "OBJECT", "properties": param_props}
    return {"type": "ARRAY", "items": item}


def create_params_only_prompt(category_name: str = "") -> str:
    """Second-pass prompt: fill ONLY missing filter parameters, with web search."""
    cat_str = f"Produkty patria do kategórie: **{category_name}**." if category_name else ""
    return f"""Si technický expert na profesionálne gastro vybavenie. {cat_str}

Dostaneš JSON pole produktov. Každý produkt má pole `"chybajuce_parametre"` – zoznam technických parametrov, ktoré sa nepodarilo zistiť z popisu.

Tvoja úloha: pre každý produkt **dohľadaj hodnoty chýbajúcich parametrov pomocou webového vyhľadávania** (katalógové číslo + názov sú spoľahlivé vyhľadávacie kľúče).

Pravidlá hodnôt:
* Jednotka je už v názve parametra (napr. "Šírka (mm)", "Príkon (W)") – hodnota je **iba čisté číslo** (napr. "800").
* Pre parametre s "(Áno/Nie)" použi presne "Áno" alebo "Nie".
* Používaj presne zadané názvy parametrov ako kľúče – nevymýšľaj vlastné.
* Ak hodnotu nenájdeš spoľahlivo, kľúč **vôbec nezaraď** – žiadne odhady.

Výstup: **IBA čisté JSON pole** bez akéhokoľvek iného textu, bez ```json:
[{{"code": "katalógové číslo", "parameters": {{"Šírka (mm)": "800"}}}}]
Produkty, pre ktoré si nič nenašiel, vynechaj úplne.
"""


def create_category_classification_prompt(categories: List[str]) -> str:
    """Classify uncategorized products into the known category tree."""
    cats = "\n".join(f"- {c}" for c in categories)
    return f"""Si expert na kategorizáciu profesionálneho gastro vybavenia.

Dostaneš JSON pole produktov (code, name, shortDescription). Pre každý produkt vyber **presne jednu kategóriu** z tohto zoznamu a skopíruj ju **doslovne** (vrátane diakritiky a oddeľovačov " > "):

{cats}

Ak si nie si istý ani na 80 %, použi prázdny reťazec "".

Výstup: **IBA čisté JSON pole** bez akéhokoľvek iného textu, bez ```json:
[{{"code": "katalógové číslo", "category": "vybraná kategória alebo \\"\\""}}]
"""


def create_system_prompt_no_dimensions(category_name: str = "", expected_parameters: list = None) -> str:
    """
    Create system prompt for AI enhancement with negative constraints for dimensions.
    Used for Group 1 products (variants).
    """
    base_prompt = create_system_prompt(category_name, expected_parameters)

    # Add negative constraints
    negative_constraints = """

---

### ⛔ **ZAKÁZANÉ (NEGATIVE CONSTRAINTS)**

* **NEGENERUJ** žiadne rozmery v textových poliach!
* **VYNECHAJ** slová: "výška", "šírka", "dĺžka", "hĺbka", "rozmery", "mm", "cm", "m" (ak sa týkajú rozmerov).
* **NEUVÁDZAJ** konkrétne číselné rozmery produktu (napr. 1000x500x800 mm).
* Ak by si chcel uviesť objem, **NEUVÁDZAJ** konkrétnu hodnotu. Namiesto toho použi vetu: "Objem sa mení v závislosti na zvolenej variante tovaru".
* Ostatné technické parametre (napríklad výkon, napätie) **MÔŽEŠ** uvádzať.
* Toto platí pre všetky polia: `shortDescription`, `description`, `seoTitle`, `metaDescription` (vrátane všetkých otázok a odpovedí v sekcii FAQ).

---
"""

    # Insert before OUTPUT section
    insert_point = base_prompt.find("### 📤 **VÝSTUP**")
    if insert_point != -1:
        return base_prompt[:insert_point] + negative_constraints + base_prompt[insert_point:]
    else:
        return base_prompt + negative_constraints
