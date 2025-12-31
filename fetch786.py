import asyncio
import os
import re
from playwright.async_api import async_playwright

PROFILE_DIR = "profile"
OUT_FILE = "gc.txt"

GC_PATTERN = re.compile(r"/direct/t/[0-9A-Za-z_-]+")


def load_existing():
    if not os.path.exists(OUT_FILE):
        return set()
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        return set(x.strip() for x in f if x.strip())


def save_gc(url, existing):
    if url in existing:
        return
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")
    existing.add(url)
    print("[+] Saved:", url)


async def watch_url(page):
    existing = load_existing()
    last_url = ""

    print("\n✅ Login agar pehli baar hai toh manually karo")
    print("👉 DM inbox open rakho")
    print("👉 GC pe click karte jao — auto save hota rahega\n")

    while True:
        url = page.url
        if url != last_url:
            last_url = url
            clean = url.split("?")[0]
            if GC_PATTERN.search(clean):
                save_gc(clean, existing)
        await asyncio.sleep(1)


async def main():
    async with async_playwright() as p:
        # 🔥 PERSISTENT CONTEXT (SESSION SAVE)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Instagram open
        await page.goto("https://www.instagram.com/")

        await watch_url(page)


asyncio.run(main())
