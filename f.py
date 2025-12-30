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
            headless=False,   # ✅ HEADFUL (browser visible)
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )

        context = await browser.new_context(
            viewport=None,   # Full window
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        # 🔐 Inject sessionid cookie
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

        page = await context.new_page()

        print("[*] Opening Instagram DM inbox...")
        await page.goto(
            "https://www.instagram.com/direct/inbox/",
            wait_until="networkidle"
        )

        print("[+] Logged in using sessionid (if valid)")

        async def handle_response(response):
            try:
                if "graphql" not in response.url:
                    return

                text = await response.text()

                # REAL browser thread IDs (340…)
                ids = re.findall(r'"thread_id":"(340\d+)"', text)

                for tid in ids:
                    if tid in SEEN_IDS:
                        continue
                    SEEN_IDS.add(tid)

                    # Try to extract GC name
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

        print("[*] Scrolling DM list to load all GCs...")

        # Human-like slow scrolling
        for _ in range(60):
            await page.mouse.wheel(0, 2500)
            await page.wait_for_timeout(1800)

        print("\n✅ DONE — check gc.txt")
        await browser.close()


asyncio.run(main())
