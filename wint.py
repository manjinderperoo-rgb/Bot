import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch(
        headless=False
    )

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
            "Gecko/20100101 Firefox/122.0"
        ),
        locale="en-US"
    )

    page = context.new_page()

    print("[+] Opening aws.com...")
    page.goto("https://aws.amazon.com", wait_until="domcontentloaded")

    print("[+] Browser open hai. Ctrl + C dabao band karne ke liye.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Ctrl + C detected. Closing browser...")
        browser.close()
