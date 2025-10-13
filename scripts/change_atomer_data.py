"""
Atomer API Client - Script for fetching and updating product data
Handles GET requests to fetch product data and POST requests to update it.
"""

import requests
from typing import Dict, Optional, Any


class AtomerAPIClient:
    """Client for interacting with Atomer admin API"""
    
    BASE_URL = "https://www.atomer.com/admin/index.php"
    
    def __init__(self, session_cookies: Dict[str, str]):
        """
        Initialize the Atomer API client
        
        Args:
            session_cookies: Dictionary containing session cookies (PHPSESSID, LaVisitorId, LaSID)
        """
        self.session = requests.Session()
        self.session.cookies.update(session_cookies)
        
        # Common headers for all requests
        self.common_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,sk;q=0.8",
            "cache-control": "max-age=0",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        }
    
    def parse_product_form_data(self, html_content: str) -> Dict[str, str]:
        """
        Parse HTML response to extract current form field values
        
        Args:
            html_content: HTML content from GET request
            
        Returns:
            Dictionary with current form field values
        """
        from html.parser import HTMLParser
        
        class FormParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.form_data = {}
                self.current_textarea = None
                self.textarea_content = []
                
            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                
                if tag == 'input':
                    name = attrs_dict.get('name')
                    value = attrs_dict.get('value', '')
                    if name:
                        self.form_data[name] = value
                        
                elif tag == 'select':
                    # Store select name for option processing
                    self.current_select = attrs_dict.get('name')
                    
                elif tag == 'option' and hasattr(self, 'current_select'):
                    if 'selected' in attrs_dict:
                        value = attrs_dict.get('value', '')
                        if self.current_select:
                            self.form_data[self.current_select] = value
                            
                elif tag == 'textarea':
                    self.current_textarea = attrs_dict.get('name')
                    self.textarea_content = []
                    
            def handle_data(self, data):
                if self.current_textarea:
                    self.textarea_content.append(data)
                    
            def handle_endtag(self, tag):
                if tag == 'textarea' and self.current_textarea:
                    self.form_data[self.current_textarea] = ''.join(self.textarea_content)
                    self.current_textarea = None
                    self.textarea_content = []
                elif tag == 'select':
                    if hasattr(self, 'current_select'):
                        delattr(self, 'current_select')
        
        parser = FormParser()
        parser.feed(html_content)
        return parser.form_data
    
    def get_product_categories(self, id_tovar: int) -> Optional[requests.Response]:
        """
        Fetch product category data
        
        Args:
            id_tovar: Product ID
            
        Returns:
            Response object or None if request failed
        """
        params = {
            "modul": "eshop-tovar-kategorie",
            "id_tovar": id_tovar
        }
        
        headers = self.common_headers.copy()
        headers["sec-fetch-site"] = "none"
        
        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error fetching product data: {e}")
            return None
    
    def update_product_category(
        self,
        id_tovar: int,
        id_kategorie: int,
        product_data: Dict[str, Any]
    ) -> Optional[requests.Response]:
        """
        Update product category data
        
        Args:
            id_tovar: Product ID
            id_kategorie: Category ID
            product_data: Dictionary containing all product fields to update
            
        Returns:
            Response object or None if request failed
        """
        params = {
            "modul": "eshop-tovar-kategorie",
            "id_tovar": id_tovar,
            "id_kategorie": id_kategorie
        }
        
        headers = self.common_headers.copy()
        headers.update({
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.atomer.com",
            "referer": f"{self.BASE_URL}?modul=eshop-tovar-kategorie&id_tovar={id_tovar}",
            "sec-fetch-site": "same-origin"
        })
        
        try:
            response = self.session.post(
                self.BASE_URL,
                params=params,
                headers=headers,
                data=product_data,
                timeout=30
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error updating product data: {e}")
            return None
    
    def update_product_seo(
        self,
        id_tovar: int,
        id_kategorie: int,
        seo_data: Dict[str, str]
    ) -> Optional[requests.Response]:
        """
        Update product SEO data
        
        Args:
            id_tovar: Product ID
            id_kategorie: Category ID
            seo_data: Dictionary containing SEO fields (title, description, keywords)
            
        Returns:
            Response object or None if request failed
        """
        params = {
            "modul": "eshop-tovar-kategorie",
            "id_tovar": id_tovar,
            "id_kategorie": id_kategorie,
            "uprav_seo": ""
        }
        
        headers = self.common_headers.copy()
        headers.update({
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.atomer.com",
            "referer": f"{self.BASE_URL}?modul=eshop-tovar-kategorie&id_tovar={id_tovar}",
            "sec-fetch-site": "same-origin"
        })
        
        try:
            response = self.session.post(
                self.BASE_URL,
                params=params,
                headers=headers,
                data=seo_data,
                timeout=30
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error updating SEO data: {e}")
            return None


def create_product_update_payload(
    existing_data: Dict[str, str],
    category_id: int,
    short_text_sk: Optional[str] = None,
    text_sk: Optional[str] = None,
    **kwargs
) -> Dict[str, str]:
    """
    Create a product update payload by merging existing data with new values
    
    Args:
        existing_data: Dictionary with current form field values from GET request
        category_id: Category ID (cbSectionID)
        short_text_sk: New short description (HTML) - if None, keeps existing
        text_sk: New long description (HTML) - if None, keeps existing
        **kwargs: Additional fields to override
        
    Returns:
        Dictionary with form data ready for POST request
    """
    # Whitelist of fields needed for product update (based on working cURL)
    required_fields = [
        "tbNadpisSK", "tbAliasSK", "tbAliasOriginalSK", "tbShortTextSK", "tbTextSK",
        "cbManufacterID", "nova_hodnota_1", "cbVisible", "cbDeliveryDate", "cbDeliveryFree", 
        "chbTop", "tbDatumStart", "tbDatumKoniec", "tbPrice", "sbPriceType", "tbFlagPrice",
        "sbFlagPriceType", "tbPriceOriginal", "sbPriceOriginalType", "tbPriceOld",
        "sbPriceOldType", "cbDPH", "tbBodyNavyse", "tbCatalogID", "cbMernaJednotka",
        "cbMernaJednotkaIne", "tbEANcode", "tbWeight", "tbOldWeight", "tbCount",
        "cbExtranetSklad_sklad", "tbExtranetSklad_count", "cbExtranetSklad_jednotka", 
        "tbExtranetSklad_nakupnaPrice", "cbExtranetSklad_nakupnaPriceType", 
        "cbExtranetSklad_nakupnaDPH", "tbMinOrderCount", "tbMinOrderCountManual"
    ]
    
    # Build payload with only required fields from existing data
    payload = {}
    for field in required_fields:
        if field in existing_data:
            payload[field] = existing_data[field]
        else:
            # Provide defaults for missing fields
            payload[field] = ""
    
    # Add cbSectionID (category ID) - critical field
    payload["cbSectionID"] = str(category_id)
    
    # Update with new values if provided
    if short_text_sk is not None:
        payload["tbShortTextSK"] = short_text_sk
    if text_sk is not None:
        payload["tbTextSK"] = text_sk
    
    # Ensure required fields for save operation
    payload["kopiruj"] = "0"
    payload["btnSaveStuff"] = "Uložiť"
    payload["save"] = "1"
    
    # Update with any additional overrides
    payload.update(kwargs)
    
    return payload


def create_seo_update_payload(
    title_sk: str,
    description_sk: str = "",
    keywords_sk: str = "",
    language: str = "SK"
) -> Dict[str, str]:
    """
    Create an SEO update payload
    
    Args:
        title_sk: SEO title in Slovak
        description_sk: SEO description in Slovak
        keywords_sk: SEO keywords in Slovak (comma-separated)
        language: Language code (default: "SK")
        
    Returns:
        Dictionary with SEO form data ready for POST request
    """
    payload = {
        "tbTitulkaSK": title_sk,
        "tbPopisSK": description_sk,
        "tbKeywordsSK": keywords_sk,
        "cbSeoJazyk": language,
        "btnSeoSave": "Uložiť SEO"
    }
    
    return payload


def update_product_workflow(
    client: AtomerAPIClient,
    product_id: int,
    category_id: int,
    new_short_text: str,
    new_long_text: str,
    seo_title: str,
    seo_description: str,
    seo_keywords: str
) -> bool:
    """
    Complete workflow to update product and SEO data
    
    Args:
        client: AtomerAPIClient instance
        product_id: Product ID to update
        category_id: Category ID
        new_short_text: New short description (HTML)
        new_long_text: New long description (HTML)
        seo_title: SEO title
        seo_description: SEO meta description
        seo_keywords: SEO keywords (comma-separated)
        
    Returns:
        True if all updates successful, False otherwise
    """
    # Step 1: GET existing product data
    print(f"[1/5] Fetching existing product data for ID: {product_id}")
    response = client.get_product_categories(product_id)
    
    if not response:
        print("❌ Failed to fetch product data!")
        return False
    
    print(f"✓ GET Request successful! Status: {response.status_code}")
    
    # Step 2: Parse existing form data
    print("[2/5] Parsing existing form data...")
    existing_data = client.parse_product_form_data(response.text)
    print(f"✓ Parsed {len(existing_data)} form fields")
    
    # Debug: Show parsed field names
    print("\n[DEBUG] Parsed field names:")
    for key in sorted(existing_data.keys()):
        value_preview = str(existing_data[key])[:50] if existing_data[key] else "(empty)"
        print(f"  - {key}: {value_preview}")
    
    # Step 3: Create payload with only new descriptions
    print("\n[3/5] Creating product update payload...")
    product_data = create_product_update_payload(
        existing_data=existing_data,
        category_id=category_id,
        short_text_sk=new_short_text,
        text_sk=new_long_text
    )
    print(f"✓ Payload ready with {len(product_data)} fields")
    
    # Debug: Show what we're sending for the text fields
    print("\n[DEBUG] Text fields being sent:")
    print(f"  - tbShortTextSK: {product_data.get('tbShortTextSK', 'NOT FOUND')[:80]}...")
    print(f"  - tbTextSK: {product_data.get('tbTextSK', 'NOT FOUND')[:80]}...")
    
    # Debug: Save full payload to file for inspection
    import json
    with open("debug_payload.json", "w", encoding="utf-8") as f:
        json.dump(product_data, f, indent=2, ensure_ascii=False)
    print("  - Full payload saved to debug_payload.json")
    
    # Step 4: Update product category data
    print(f"\n[4/5] Updating product ID: {product_id} with category ID: {category_id}")
    response = client.update_product_category(product_id, category_id, product_data)
    
    if not response:
        print("❌ Failed to update product data!")
        return False
    
    print(f"✓ Product update successful! Status: {response.status_code}")
    
    # Step 5: Update SEO data
    print("[5/5] Updating SEO data...")
    seo_data = create_seo_update_payload(
        title_sk=seo_title,
        description_sk=seo_description,
        keywords_sk=seo_keywords
    )
    
    response = client.update_product_seo(product_id, category_id, seo_data)
    
    if not response:
        print("❌ Failed to update SEO data!")
        return False
    
    print(f"✓ SEO update successful! Status: {response.status_code}")
    print("\n" + "="*50)
    print("✅ All updates completed successfully!")
    return True


def main():
    """Main execution function"""
    
    # Session cookies - REPLACE WITH YOUR ACTUAL SESSION COOKIES
    cookies = {
        "PHPSESSID": "gmh61dm8hoeaqi8ksmovg2obh2",
        "LaVisitorId_YWxsNG5ldC5sYWRlc2suY29tLw": "v4uxog1f9c84evzh66ah2getaf4bz1gm",
        "LaSID": "892247fgf730jh1t0me9h2fa4ph0qcy7"
    }
    
    # Initialize API client
    client = AtomerAPIClient(cookies)
    
    # Product to update
    product_id = 28735852
    category_id = 1298877
    
    # New content to update
    new_short_description = """<strong>TEST Profesionálny ohrevný vozík</strong> na 100 tanierov, vyrobený z odolného nerezu AISI 445, s presnou reguláciou teploty a dvoma podávacími šachtami s automatickým zdvíhaním tanierov. Ideálne riešenie pre efektívnu a hygienickú výdaj jedál v komerčných kuchyniach a reštauráciách. <br><br><strong>Kľúčové parametre:</strong><br><ul><li>Kapacita: 100 tanierov</li><li>Materiál: Nerez AISI 445</li><li>Regulácia teploty: Áno</li><li>Podávacie šachty: 2 ks s automatickým zdvíhaním</li><li>Rozmery (ŠxHxV): 1000 x 510 x 880 mm</li><li>Výkon: 3 kW / 230 V</li></ul>"""
    
    new_long_description = """<p>TEST Zabezpečte bezproblémový a efektívny výdaj jedál s týmto profesionálnym ohrevným vozíkom na 100 tanierov. Vyrobený z kvalitnej nehrdzavejúcej ocele AISI 445, tento vozík spĺňa najvyššie štandardy pre <strong>horeca prevádzky</strong> a komerčné kuchyne. Jeho robustná konštrukcia zaručuje dlhú životnosť a jednoduchú údržbu.</p><p><strong>Technické vlastnosti:</strong></p><ul><li><strong>Kapacita:</strong> Navrhnutý na uskladnenie a ohrev až 100 tanierov štandardných rozmerov.</li><li><strong>Materiál:</strong> Celonerezové prevedenie z AISI 445 pre maximálnu hygienu a odolnosť voči korózii.</li><li><strong>Regulácia teploty:</strong> Presný termostat umožňuje nastaviť optimálnu teplotu pre udržanie jedál v ideálnom stave.</li><li><strong>Podávacie šachty:</strong> Dve praktické podávacie šachty s funkciou automatického zdvíhania tanierov výrazne zrýchľujú a zjednodušujú proces výdaja.</li><li><strong>Rozmery:</strong> Kompaktné rozmery 1000 x 510 x 880 mm umožňujú ľahké umiestnenie aj v priestorovo obmedzených kuchyniach.</li><li><strong>Výkon:</strong> S príkonom 3 kW a napájaním 230 V je tento vozík energeticky efektívny a pripravený na okamžité použitie.</li></ul><p><strong>Výhody pre vašu prevádzku:</strong></p><ul><li><strong>Zvýšenie efektivity:</strong> Automatické zdvíhanie tanierov a dostatočná kapacita urýchľujú obsluhu počas špičiek.</li><li><strong>Udržanie kvality jedla:</strong> Konštantná teplota zaisťuje, že jedlo zostane teplé a chutné až do podania.</li><li><strong>Hygiena a bezpečnosť:</strong> Nerezový materiál sa ľahko čistí a spĺňa prísne hygienické normy pre profesionálne kuchyne.</li><li><strong>Dlhodobá investícia:</strong> Kvalitné spracovanie zaručuje spoľahlivosť a dlhú životnosť zariadenia.</li></ul><p>Tento ohrevný vozík je ideálnym doplnkom pre každú <strong>komerčnú kuchyňu</strong>, jedáleň, hotelovú reštauráciu alebo cateringovú spoločnosť, ktorá kladie dôraz na rýchlosť, kvalitu a profesionalitu.</p>"""
    
    # SEO data
    seo_title = "TEST Ohrevný vozík na 100 tanierov - Nerez AISI 445"
    seo_description = "GastroPro.sk | Ohrevný vozík na 100 tanierov z nerezu s automatickým zdvíhaním. Ideálny pre profesionálne kuchyne. Objednajte teraz!"
    seo_keywords = "ohrevný vozík, vozík na taniere, gastro výdaj, profesionálne gastro vybavenie, ohrev jedla, nerezový vozík"
    
    # Execute complete workflow
    print("="*50)
    print("Starting Product Update Workflow")
    print("="*50 + "\n")
    
    success = update_product_workflow(
        client=client,
        product_id=product_id,
        category_id=category_id,
        new_short_text=new_short_description,
        new_long_text=new_long_description,
        seo_title=seo_title,
        seo_description=seo_description,
        seo_keywords=seo_keywords
    )
    
    if not success:
        print("\n⚠️ Workflow completed with errors!")
        return 1
    
    return 0


if __name__ == "__main__":
    main()
