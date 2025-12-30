import asyncio
import re
from playwright.async_api import async_playwright

OUTPUT_FILE = "gc.txt"
SEEN_IDS = set()

def save_gc(tid, name):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"https://www.instagram.com/direct/t/{tid}/ | {name}\n")


async def main():
    sessionid = input("Enter Instagram sessionid: ").strip()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,   # HEADFUL
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )

        context = await browser.new_context(
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        # 1️⃣ First open Instagram root (IMPORTANT)
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")

        # 2️⃣ Inject sessionid AFTER domain load
        await context.add_cookies([
            {
                "name": "sessionid",
                "value": sessionid,
                "domain": ".instagram.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ])

        # 3️⃣ Reload to apply cookie
        await page.reload(wait_until="networkidle")

        # 4️⃣ Now go to DM inbox
        await page.goto(
            "https://www.instagram.com/direct/inbox/",
            wait_until="networkidle"
        )

        print("[+] If session is valid, DM inbox should be open")

        async def handle_response(response):
            try:
                if "graphql" not in response.url:
                    return

                text = await response.text()
                ids = re.findall(r'"thread_id":"(340\d+)"', text)

                for tid in ids:
                    if tid in SEEN_IDS:
                        continue
                    SEEN_IDS.add(tid)

                    name_match = re.search(
                        rf'"thread_id":"{tid}".+?"thread_title":"(.*?)"',
                        text
                    )
                    name = name_match.group(1) if name_match else "NO_NAME"

                    print(f"[+] GC FOUND: {tid} | {name}")
                    save_gc(tid, name)

            except Exception:
                pass

        page.on("response", handle_response)

        print("[*] Scrolling DM list...")

        for _ in range(60):
            await page.mouse.wheel(0, 2500)
            await page.wait_for_timeout(1800)

        print("\n✅ DONE — check gc.txt")
        await browser.close()


asyncio.run(main())
