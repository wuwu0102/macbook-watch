import os
import re
import asyncio
import requests
from urllib.parse import quote
from playwright.async_api import async_playwright

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
    "8G", "8GB",
    "2018", "2019",
    "Intel", "i5", "i7", "i9",
    "iPad", "iPhone", "MSI", "ASUS",
]

SHOPEE_SEARCH_URL = "https://shopee.tw/search?keyword={keyword}"


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram env not set.")
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


def parse_price(text: str):
    text = text.replace(",", "")
    prices = re.findall(r"\$?\s*(\d{4,6})", text)
    if not prices:
        return None
    return min(int(p) for p in prices)


def is_good_text(text: str) -> bool:
    upper = text.upper()

    if "MACBOOK" not in upper:
        return False

    if "16G" not in upper and "16GB" not in upper:
        return False

    if "M1" not in upper and "M2" not in upper:
        return False

    for word in BLOCK_WORDS:
        if word.upper() in upper:
            return False

    price = parse_price(text)
    if price and price > MAX_PRICE:
        return False

    return True


async def search_shopee(page, keyword: str):
    url = SHOPEE_SEARCH_URL.format(keyword=quote(keyword))
    print(f"Searching: {url}")

    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(7000)

    for _ in range(5):
        await page.mouse.wheel(0, 1200)
        await page.wait_for_timeout(1500)

    links = await page.locator("a").evaluate_all("""
        els => els.map(a => ({
            text: a.innerText,
            href: a.href
        })).filter(x => x.text && x.href)
    """)

    hits = []

    for item in links:
        text = item.get("text", "").strip()
        href = item.get("href", "").strip()

        if not text or not href:
            continue

        if not is_good_text(text):
            continue

        price = parse_price(text)
        hits.append({
            "title": " ".join(text.split())[:120],
            "price": price,
            "url": href,
            "keyword": keyword,
        })

    return hits


async def main_async():
    all_hits = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        page = await browser.new_page(
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        )

        for keyword in KEYWORDS:
            try:
                hits = await search_shopee(page, keyword)
                all_hits.extend(hits)
            except Exception as e:
                print(f"Search failed for {keyword}: {e}")

        await browser.close()

    unique = {}
    for item in all_hits:
        unique[item["url"]] = item

    hits = list(unique.values())

    if not hits:
        send_telegram("目前沒有抓到符合條件的 MacBook 16G。")
        return

    lines = [f"找到 {len(hits)} 筆可能符合的 MacBook 16G："]

    for item in hits[:10]:
        lines.append("")
        lines.append(f"關鍵字：{item['keyword']}")
        lines.append(f"商品：{item['title']}")
        if item["price"]:
            lines.append(f"價格：約 ${item['price']}")
        lines.append(item["url"])

    send_telegram("\n".join(lines))


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
