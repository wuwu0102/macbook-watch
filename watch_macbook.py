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
