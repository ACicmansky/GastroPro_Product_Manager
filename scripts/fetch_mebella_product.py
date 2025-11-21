import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_product():
    url = "https://mebella.pl/en/produkt/bea-big-dining/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        logger.info(f"Fetching {url}...")
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            with open("mebella_product_test.html", "wb") as f:
                f.write(response.content)
            logger.info("Saved to mebella_product_test.html")
        else:
            logger.error(f"Failed: {response.status_code}")

    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    fetch_product()
