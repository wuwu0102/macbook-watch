import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

KEYWORDS = [
    "MacBook M1 16G",
    "MacBook M2 16G",
    "MacBook Pro M1 16G",
    "MacBook Air M1 16G",
    "MacBook Air M2 16G",
]

MAX_PRICE = 26000

BLOCK_WORDS = [
    "8G",
    "8GB",
    "2018",
    "2019",
    "Intel",
    "i5",
    "i7",
    "i9",
]

SHOPEE_SEARCH_URL = "https://shopee.tw/search?keyword={keyword}"


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram env not set. Message:")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }

    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()


def looks_like_good_listing(title: str, price_text: str) -> bool:
    text = f"{title} {price_text}".upper()

    if "16G" not in text and "16GB" not in text:
        return False

    if "M1" not in text and "M2" not in text:
        return False

    for word in BLOCK_WORDS:
        if word.upper() in text:
            return False

    price_numbers = re.findall(r"\d[\d,]*", price_text.replace("$", ""))
    if price_numbers:
        price = int(price_numbers[0].replace(",", ""))
        if price > MAX_PRICE:
            return False

    return True


def search_shopee(keyword: str):
    url = SHOPEE_SEARCH_URL.format(keyword=quote(keyword))
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    # 蝦皮很多內容是 JS 動態載入，所以這個方法可能抓不到完整商品。
    # 但如果頁面有渲染到商品文字，這裡可以先抓。
    text = soup.get_text(" ", strip=True)

    if "16G" in text or "16GB" in text:
        results.append({
            "title": f"可能找到：{keyword}",
            "price": "請點開確認",
            "url": url,
        })

    return results


def main():
    all_hits = []

    for keyword in KEYWORDS:
        print(f"Searching: {keyword}")
        try:
            hits = search_shopee(keyword)
            all_hits.extend(hits)
        except Exception as e:
            print(f"Search failed for {keyword}: {e}")

    if not all_hits:
        print("No matching MacBook found.")
        return

    lines = ["找到可能符合的 MacBook 16G："]

    for item in all_hits:
        lines.append("")
        lines.append(item["title"])
        lines.append(item["price"])
        lines.append(item["url"])

    message = "\n".join(lines)
    send_telegram(message)


if __name__ == "__main__":
    main()
