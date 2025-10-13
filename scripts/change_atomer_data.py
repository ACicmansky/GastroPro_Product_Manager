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
    category_id: int,
    title_sk: str,
    alias_sk: str,
    short_text_sk: str,
    text_sk: str = "",
    price: float = 0.0,
    catalog_id: str = "",
    **kwargs
) -> Dict[str, str]:
    """
    Create a product update payload with all required fields
    
    Args:
        category_id: Category section ID
        title_sk: Product title in Slovak
        alias_sk: Product URL alias
        short_text_sk: Short description (HTML)
        text_sk: Long description (HTML)
        price: Product price
        catalog_id: Catalog ID
        **kwargs: Additional optional fields
        
    Returns:
        Dictionary with form data ready for POST request
    """
    payload = {
        "cbSectionID": str(category_id),
        "tbNadpisSK": title_sk,
        "tbAliasSK": alias_sk,
        "tbAliasOriginalSK": alias_sk,
        "tbShortTextSK": short_text_sk,
        "tbTextSK": text_sk,
        "cbManufacterID": "0",
        "nova_hodnota_1": "",
        "cbVisible": "1",
        "cbDeliveryDate": "0",
        "cbDeliveryFree": "0",
        "chbTop": "2",
        "tbDatumStart": "",
        "tbDatumKoniec": "",
        "tbPrice": str(price),
        "sbPriceType": "1",
        "tbFlagPrice": str(price),
        "sbFlagPriceType": "1",
        "tbPriceOriginal": str(price),
        "sbPriceOriginalType": "1",
        "tbPriceOld": "0",
        "sbPriceOldType": "0",
        "cbDPH": "23",
        "tbBodyNavyse": "0",
        "tbCatalogID": catalog_id,
        "cbMernaJednotka": "ks",
        "cbMernaJednotkaIne": "ks",
        "tbEANcode": "",
        "tbWeight": "0.1",
        "tbOldWeight": "0.1",
        "tbCount": "0",
        "cbExtranetSklad_sklad": "0",
        "tbExtranetSklad_count": "1",
        "cbExtranetSklad_jednotka": "ks",
        "tbExtranetSklad_nakupnaPrice": "",
        "cbExtranetSklad_nakupnaPriceType": "1",
        "cbExtranetSklad_nakupnaDPH": "23",
        "tbMinOrderCount": "1",
        "tbMinOrderCountManual": "1",
        "btnSaveStuff": "Uložiť",
        "save": "1"
    }
    
    # Update with any additional fields
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
    
    # Example: Fetch product data
    product_id = 28735852
    print(f"Fetching product data for ID: {product_id}")
    response = client.get_product_categories(product_id)
    
    if response:
        print(f"GET Request successful! Status: {response.status_code}")
        print(f"Response length: {len(response.text)} characters")
        # You can parse the HTML response here to extract data
        with open("product_data.html", "w", encoding="utf-8") as f:
            f.write(response.text)
    else:
        print("GET Request failed!")
        return
    
    # Example: Update product data
    print("\n" + "="*50)
    print("Preparing product update...")
    
    # category_id = 1298877
    # product_data = create_product_update_payload(
    #     category_id=category_id,
    #     title_sk="Ohrevný vozík na 100 tanierov",
    #     alias_sk="ohrevny-vozik-na-100-tanierov-1",
    #     short_text_sk="<strong>Profesionálny ohrevný vozík</strong> na 100 tanierov, vyrobený z odolného nerezu AISI 445, s presnou reguláciou teploty a dvoma podávacími šachtami s automatickým zdvíhaním tanierov. Ideálne riešenie pre efektívnu a hygienickú výdaj jedál v komerčných kuchyniach a reštauráciách. <br><br><strong>Kľúčové parametre:</strong><br><ul><li>Kapacita: 100 tanierov</li><li>Materiál: Nerez AISI 445</li><li>Regulácia teploty: Áno</li><li>Podávacie šachty: 2 ks s automatickým zdvíhaním</li><li>Rozmery (ŠxHxV): 1000 x 510 x 880 mm</li><li>Výkon: 3 kW / 230 V</li></ul>",
    #     text_sk="<p>Zabezpečte bezproblémový a efektívny výdaj jedál s týmto profesionálnym ohrevným vozíkom na 100 tanierov. Vyrobený z kvalitnej nehrdzavejúcej ocele AISI 445, tento vozík spĺňa najvyššie štandardy pre <strong>horeca prevádzky</strong> a komerčné kuchyne. Jeho robustná konštrukcia zaručuje dlhú životnosť a jednoduchú údržbu.</p><p><strong>Technické vlastnosti:</strong></p><ul><li><strong>Kapacita:</strong> Navrhnutý na uskladnenie a ohrev až 100 tanierov štandardných rozmerov.</li><li><strong>Materiál:</strong> Celonerezové prevedenie z AISI 445 pre maximálnu hygienu a odolnosť voči korózii.</li><li><strong>Regulácia teploty:</strong> Presný termostat umožňuje nastaviť optimálnu teplotu pre udržanie jedál v ideálnom stave.</li><li><strong>Podávacie šachty:</strong> Dve praktické podávacie šachty s funkciou automatického zdvíhania tanierov výrazne zrýchľujú a zjednodušujú proces výdaja.</li><li><strong>Rozmery:</strong> Kompaktné rozmery 1000 x 510 x 880 mm umožňujú ľahké umiestnenie aj v priestorovo obmedzených kuchyniach.</li><li><strong>Výkon:</strong> S príkonom 3 kW a napájaním 230 V je tento vozík energeticky efektívny a pripravený na okamžité použitie.</li></ul><p><strong>Výhody pre vašu prevádzku:</strong></p><ul><li><strong>Zvýšenie efektivity:</strong> Automatické zdvíhanie tanierov a dostatočná kapacita urýchľujú obsluhu počas špičiek.</li><li><strong>Udržanie kvality jedla:</strong> Konštantná teplota zaisťuje, že jedlo zostane teplé a chutné až do podania.</li><li><strong>Hygiena a bezpečnosť:</strong> Nerezový materiál sa ľahko čistí a spĺňa prísne hygienické normy pre profesionálne kuchyne.</li><li><strong>Dlhodobá investícia:</strong> Kvalitné spracovanie zaručuje spoľahlivosť a dlhú životnosť zariadenia.</li></ul><p>Tento ohrevný vozík je ideálnym doplnkom pre každú <strong>komerčnú kuchyňu</strong>, jedáleň, hotelovú reštauráciu alebo cateringovú spoločnosť, ktorá kladie dôraz na rýchlosť, kvalitu a profesionalitu.</p>",
    #     price=909.27,
    #     catalog_id="fc7239a56d27b79893cc58951fb91912"
    # )
    
    # print(f"Updating product ID: {product_id} with category ID: {category_id}")
    # response = client.update_product_category(product_id, category_id, product_data)
    
    # if response:
    #     print(f"POST Request successful! Status: {response.status_code}")
    #     print(f"Response length: {len(response.text)} characters")
    # else:
    #     print("POST Request failed!")
    
    # Example: Update SEO data
    print("\n" + "="*50)
    print("Preparing SEO update...")
    
    category_id = 1298877
    seo_data = create_seo_update_payload(
        title_sk="Ohrevný vozík na 100 tanierov - Nerez AISI 445",
        description_sk="GastroPro.sk | Ohrevný vozík na 100 tanierov z nerezu s automatickým zdvíhaním. Ideálny pre profesionálne kuchyne. Objednajte teraz!",
        keywords_sk="ohrevný vozík, vozík na taniere, gastro výdaj, profesionálne gastro vybavenie, ohrev jedla, nerezový vozík"
    )
    
    print(f"Updating SEO for product ID: {product_id} with category ID: {category_id}")
    response = client.update_product_seo(product_id, category_id, seo_data)
    
    if response:
        print(f"SEO POST Request successful! Status: {response.status_code}")
        print(f"Response length: {len(response.text)} characters")
    else:
        print("SEO POST Request failed!")


if __name__ == "__main__":
    main()
