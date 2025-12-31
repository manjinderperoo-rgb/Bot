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

async def main():
    """Windows main function with infinite parallel-load sequential-send 7-tab batch looping over GCs"""
    parser = argparse.ArgumentParser(description="Instagram DM Infinite 7-Tab Batch Looper for Windows")
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
    print(f"Using {batch_size} persistent tabs to loop over {len(thread_urls)} GC threads in batches infinitely. Press Ctrl+C to stop.")

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
        batch_num = 0
        msg_idx = 0
        url_idx = 0

        try:
            while True:
                print(f"\n--- Batch {batch_num + 1} ---")
                batch_success = 0
                batch_urls = []
                load_tasks = []

                # Parallel load next batch of URLs
                for i in range(batch_size):
                    this_url_idx = url_idx % len(thread_urls)
                    url = thread_urls[this_url_idx]
                    batch_urls.append(url)
                    
                    if not same_thread(pages[i].url, url):
                        load_tasks.append(pages[i].goto(url, timeout=60000))
                        print(f"Tab {i+1} loading new {url[:50]}...")
                    else:
                        load_tasks.append(asyncio.sleep(0))
                        print(f"Tab {i+1} already on {url[:50]}...")
                    
                    url_idx += 1

                # Execute loads in parallel
                load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
                for j, res in enumerate(load_results):
                    if isinstance(res, Exception):
                        print(f"Tab {j+1} load failed: {res}")
                
                print("Batch of 7 GCs loaded.")

                # Sequential sends with 0.5s delay between
                for i in range(batch_size):
                    url = batch_urls[i]
                    msg = messages[msg_idx % len(messages)]
                    
                    try:
                        await pages[i].click(dm_selector)
                        await pages[i].fill(dm_selector, msg)
                        await pages[i].press(dm_selector, 'Enter')
                        print(f"Tab {i+1} sent '{msg[:50]}...' to {url[:50]}...")
                        batch_success += 1
                    except Exception as e:
                        print(f"Tab {i+1} failed to send '{msg[:50]}...' to {url[:50]}...: {e}")
                    
                    msg_idx += 1
                    
                    # 0.5s delay between sends (not after last)
                    if i < batch_size - 1:
                        await asyncio.sleep(0.5)

                total_processed += batch_success
                print(f"Batch {batch_num + 1} completed: {batch_success}/{batch_size} messages sent to GCs. Total: {total_processed}")

                # Check for full cycle completion
                if (url_idx - batch_size) % len(thread_urls) == 0 and url_idx % len(thread_urls) == 0:
                    print("1 cycle complete")
                elif url_idx % len(thread_urls) == 0:
                    print("1 cycle complete")

                # 1.4s cooldown after batch
                await asyncio.sleep(1.4)
                
                batch_num += 1

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