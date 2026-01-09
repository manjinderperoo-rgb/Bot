import asyncio
import logging
from playwright.async_api import async_playwright

# ================= CONFIG =================
PROFILE_DIR = "ig_profile"
WELCOME_TEXT = "👋 Welcome! Thanks for messaging."
CHECK_INTERVAL = 3  # seconds

# ================= LOGGING =================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("IG-BOT")

# ================= MAIN =================
async def main():
    async with async_playwright() as p:
        log.info("Launching persistent browser")

        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        log.info("Opening Instagram inbox")
        await page.goto("https://www.instagram.com/direct/inbox/", timeout=60000)

        input("❓ Have you reached Instagram inbox? type 'yes' & ENTER: ")

        log.info("Started watching for new messages")

        replied_cache = set()

        while True:
            try:
                messages = page.locator(
                    'div:has(svg[aria-label^="Reply message"])'
                )
                count = await messages.count()

                log.debug(f"Messages with reply icon found: {count}")

                for i in range(count):
                    msg = messages.nth(i)

                    try:
                        msg_text = (await msg.inner_text()).strip()
                    except:
                        msg_text = f"msg_{i}"

                    if msg_text in replied_cache:
                        continue

                    log.info("New message detected")
                    log.debug(f"Message preview: {msg_text[:80]}")

                    # hover to show reply
                    await msg.hover()
                    await asyncio.sleep(0.6)

                    reply_btn = msg.locator(
                        'svg[aria-label^="Reply message"]'
                    )

                    if await reply_btn.count() == 0:
                        log.warning("Reply button not visible after hover")
                        continue

                    await reply_btn.click(force=True)
                    log.debug("Reply button clicked")

                    await page.keyboard.type(WELCOME_TEXT, delay=60)
                    await page.keyboard.press("Enter")

                    log.info("Welcome reply sent")

                    replied_cache.add(msg_text)
                    await asyncio.sleep(2)

                await asyncio.sleep(CHECK_INTERVAL)

            except Exception as e:
                log.error(f"Loop error: {e}", exc_info=True)
                await asyncio.sleep(5)

asyncio.run(main())
