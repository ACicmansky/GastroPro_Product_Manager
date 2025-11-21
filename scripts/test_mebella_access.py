import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_access():
    url = "https://mebella.pl/en/product-category/table-bases/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    try:
        logger.info(f"Testing access to {url}...")
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)

        logger.info(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            logger.info("Success! Page content length: %d", len(response.content))
            with open("mebella_test.html", "wb") as f:
                f.write(response.content)
            logger.info("Saved content to mebella_test.html")
        else:
            logger.error("Failed to access page.")
            logger.error(f"Headers: {response.headers}")

    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    test_access()
