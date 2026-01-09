import asyncio
from playwright.async_api import async_playwright

WELCOME_TEXT = "👋 Welcome! Thanks for your message."

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await browser.new_page()

        # Open Instagram DM
        await page.goto("https://www.instagram.com/direct/inbox/")
        print("🔐 Login manually in browser")

        # wait for user confirmation
        input("❓ have you reached ig ? type 'yes' and press enter: ")

        print("👀 Watching for new messages...")

        replied_messages = set()

        while True:
            try:
                # latest message container which has reply icon
                messages = page.locator(
                    'div:has(svg[aria-label^="Reply message"])'
                )

                count = await messages.count()

                for i in range(count):
                    msg = messages.nth(i)

                    msg_id = await msg.inner_text()

                    if msg_id in replied_messages:
                        continue

                    # hover to show reply icon
                    await msg.hover()
                    await asyncio.sleep(0.5)

                    # click reply
                    reply_btn = msg.locator(
                        'svg[aria-label^="Reply message"]'
                    )
                    await reply_btn.click(force=True)

                    # type welcome message
                    await page.keyboard.type(WELCOME_TEXT, delay=50)
                    await page.keyboard.press("Enter")

                    replied_messages.add(msg_id)

                    print("✅ Replied to new message")

                await asyncio.sleep(3)

            except Exception as e:
                print("⚠️ error:", e)
                await asyncio.sleep(5)

asyncio.run(main())
