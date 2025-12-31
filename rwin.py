import argparse
import os
import time
import re
import unicodedata
import json
import asyncio
import random
from playwright.async_api import async_playwright

MOBILE_UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
MOBILE_VIEWPORT = {"width": 412, "height": 915}

LAUNCH_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--mute-audio",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-site-isolation-trials",
]

def sanitize_input(raw):
    """Fix shell-truncated input"""
    if isinstance(raw, list):
        raw = " ".join(raw)
    return raw

def parse_messages(names_arg):
    """
    Robust parser for messages for Windows
    """
    if isinstance(names_arg, list):
        names_arg = " ".join(names_arg)

    content = None  
    is_file = isinstance(names_arg, str) and names_arg.endswith('.txt') and os.path.exists(names_arg)  

    if is_file:  
        try:  
            msgs = []  
            with open(names_arg, 'r', encoding='utf-8') as f:  
                lines = [ln.rstrip('\n') for ln in f if ln.strip()]  
            for ln in lines:  
                m = json.loads(ln)  
                if isinstance(m, str):  
                    msgs.append(m)  
                else:  
                    raise ValueError("JSON line is not a string")  
            if msgs:  
                out = []  
                for m in msgs:  
                    out.append(m)  
                return out  
        except Exception:  
            pass  

        try:  
            with open(names_arg, 'r', encoding='utf-8') as f:  
                content = f.read()  
        except Exception as e:  
            raise ValueError(f"Failed to read file {names_arg}: {e}")  
    else:  
        content = str(names_arg)  

    if content is None:  
        raise ValueError("No valid content to parse")  

    content = (  
        content.replace('﹠', '&')  
        .replace('＆', '&')  
        .replace('⅋', '&')  
        .replace('ꓸ', '&')  
        .replace('︔', '&')  
    )  

    pattern = r'\s*(?:&|\band\b)\s*'  
    parts = [part.strip() for part in re.split(pattern, content, flags=re.IGNORECASE) if part.strip()]  
    return parts

def same_thread(current, target):
    """Compare Instagram DM threads by ID, ignoring extra params/redirects"""
    try:
        return current.split("/direct/t/")[1].split("/")[0] == \
               target.split("/direct/t/")[1].split("/")[0]
    except:
        return False

async def login(args, storage_path, headless):
    """Windows async login function"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=LAUNCH_ARGS
            )
            context = await browser.new_context(
                user_agent=MOBILE_UA,
                viewport=MOBILE_VIEWPORT,
                is_mobile=True,
                has_touch=True,
                device_scale_factor=2,
                color_scheme="dark"
            )
            page = await context.new_page()
            try:
                print("Logging in to Instagram...")
                await page.goto("https://www.instagram.com/", timeout=60000)
                await page.wait_for_selector('input[name="username"]', timeout=30000)
                await page.fill('input[name="username"]', args.username)
                await page.fill('input[name="password"]', args.password)
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/home**", timeout=60000)
                print("Login successful, saving storage state.")
                await context.storage_state(path=storage_path)
                return True
            except Exception as e:
                print(f"Login error: {e}")
                return False
            finally:
                await browser.close()
    except Exception as e:
        print(f"Unexpected login error: {e}")
        return False

async def process_tab(tab_id, page, target_url, msg, dm_selector):
    """Process a single tab: navigate only if needed, send one message without visibility check or retries"""
    try:
        # Avoid unnecessary goto if same thread ID
        if not same_thread(page.url, target_url):
            await page.goto(target_url, timeout=60000)
            print(f"Tab {tab_id} loaded {target_url[:50]}...")
        else:
            print(f"Tab {tab_id} already on thread of {target_url[:50]}..., skipping goto.")

        # Wait 0.5s after load before sending
        await asyncio.sleep(0.5)

        # Send message without waiting for visibility
        await page.click(dm_selector)
        await page.fill(dm_selector, msg)
        await page.press(dm_selector, 'Enter')
        print(f"Tab {tab_id} sent '{msg[:50]}...' to {target_url[:50]}...")
        await asyncio.sleep(random.uniform(1.0, 1.6))  # Settle after send
        return True
    except Exception as e:
        print(f"Tab {tab_id} failed for {target_url[:50]}... with '{msg[:50]}...': {e}")
        return False

async def main():
    """Windows main function with infinite sequential 7-tab batch looping over GCs"""
    parser = argparse.ArgumentParser(description="Instagram DM Infinite Sequential 7-Tab Batch Looper for Windows")
    parser.add_argument('--username', required=False, help='Instagram username')
    parser.add_argument('--password', required=False, help='Instagram password')
    parser.add_argument('--thread-url', required=True, help='Comma-separated Instagram direct thread URLs (any number of GCs)')
    parser.add_argument('--names', nargs='+', default=['m.txt'], help='Messages list or .txt file (default: m.txt)')
    parser.add_argument('--headless', default='true', choices=['true', 'false'], help='Run in headless mode')
    parser.add_argument('--storage-state', required=True, help='Path to JSON file for login state')
    
    args = parser.parse_args()
    args.names = sanitize_input(args.names)

    thread_urls = [u.strip() for u in args.thread_url.split(',') if u.strip()]
    if not thread_urls:
        print("Error: No valid thread URLs provided.")
        return

    headless = args.headless == 'true'  
    storage_path = args.storage_state  
    do_login = not os.path.exists(storage_path)  

    if do_login:  
        if not args.username or not args.password:  
            print("Error: Username and password required for initial login.")  
            return  
        success = await login(args, storage_path, headless)
        if not success:
            print("Login failed, exiting.")
            return
    else:  
        print("Using existing storage state, skipping login.")  

    try:  
        messages = parse_messages(args.names)  
    except ValueError as e:  
        print(f"Error parsing messages: {e}")  
        return  

    if not messages:  
        print("Error: No valid messages provided.")  
        return  

    print(f"Parsed {len(messages)} messages from {args.names}. Cycling through them.")

    batch_size = 7
    print(f"Using {batch_size} persistent tabs to loop over {len(thread_urls)} GC threads in sequential batches infinitely. Press Ctrl+C to stop.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=LAUNCH_ARGS
        )
        context = await browser.new_context(
            storage_state=storage_path,
            user_agent=MOBILE_UA,
            viewport=MOBILE_VIEWPORT,
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
            color_scheme="dark"
        )
        
        dm_selector = 'div[role="textbox"][aria-label="Message"]'
        pages = [await context.new_page() for _ in range(batch_size)]
        total_processed = 0
        cycle_num = 0
        msg_idx = 0

        try:
            while True:
                print(f"\n--- Cycle {cycle_num + 1} ---")
                cycle_success = 0
                for i in range(batch_size):
                    if msg_idx >= len(messages) * (cycle_num + 1):  # But since modulo, no need, but anyway
                        pass
                    url_idx = (cycle_num * batch_size + i) % len(thread_urls)
                    url = thread_urls[url_idx]
                    msg = messages[msg_idx % len(messages)]
                    success = await process_tab(i + 1, pages[i], url, msg, dm_selector)
                    if success:
                        cycle_success += 1
                    msg_idx += 1  # Advance for next

                    # 0.5s delay between sends in batch
                    if i < batch_size - 1:
                        await asyncio.sleep(0.5)

                total_processed += cycle_success
                print(f"Cycle {cycle_num + 1} completed: {cycle_success}/{batch_size} messages sent to GCs. Total: {total_processed}")
                print("1 cycle complete")

                # 1.4s cooldown after batch
                await asyncio.sleep(1.4)
                
                cycle_num += 1

        except KeyboardInterrupt:
            print("\nInterrupted by user (Ctrl+C). Cleaning up...")
        finally:
            for page in pages:
                try:
                    await page.close()
                except Exception:
                    pass
            await context.close()
            await browser.close()
            print(f"Stopped. Total messages sent: {total_processed}")

if __name__ == "__main__":
    asyncio.run(main())