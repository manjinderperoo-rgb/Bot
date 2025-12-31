import argparse
import os
import time
import re
import unicodedata
import json
import asyncio
from playwright.async_api import async_playwright

MOBILE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
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

async def init_page(page, url, dm_selector):
    """Initialize a single page with retries for Windows"""
    init_success = False
    for init_try in range(3):
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector(dm_selector, timeout=30000)
            init_success = True
            break
        except Exception as init_e:
            print(f"Tab init try {init_try+1}/3 failed for {url[:30]}...: {init_e}")
            if init_try < 2:
                await asyncio.sleep(2)
    return init_success

async def sender(tab_id, args, messages, page):
    """Windows async sender coroutine with per-tab failure handling"""
    dm_selector = 'div[role="textbox"][aria-label="Message"]'
    print(f"Tab {tab_id} starting infinite message loop.")
    msg_index = 0
    max_send_retries_without_reload = 2  # First fail: retry send once more, then reload if still fails
    
    while True:
        msg = messages[msg_index]
        send_success = False
        
        # Try sending with retries without reload
        for retry in range(max_send_retries_without_reload):
            try:
                if not page.locator(dm_selector).is_visible():
                    print(f"Tab {tab_id} selector not visible on retry {retry+1}/{max_send_retries_without_reload} for '{msg[:50]}...', attempting Enter to clear.")
                    try:
                        await page.press(dm_selector, 'Enter')
                        await asyncio.sleep(0.2)
                    except:
                        pass
                    await asyncio.sleep(0.5)
                    continue

                await page.click(dm_selector)
                await page.fill(dm_selector, msg)
                await page.press(dm_selector, 'Enter')
                print(f"Tab {tab_id} sent message {msg_index + 1}/{len(messages)} on retry {retry+1}")
                send_success = True
                break
            except Exception as send_e:
                print(f"Tab {tab_id} send error on retry {retry+1}/{max_send_retries_without_reload} for message {msg_index + 1}: {send_e}")
                if retry < max_send_retries_without_reload - 1:
                    print(f"Tab {tab_id} retrying after brief pause...")
                    await asyncio.sleep(0.5)
        
        # If still not successful after retries, reload this tab only and try once more
        if not send_success:
            print(f"Tab {tab_id} all send retries failed for message {msg_index + 1}, reloading page.")
            try:
                await page.reload(wait_until='networkidle', timeout=60000)
                await page.wait_for_selector(dm_selector, timeout=30000)
                print(f"Tab {tab_id} reloaded and selector ready, trying send once more.")
                
                # Try send after reload
                try:
                    await page.click(dm_selector)
                    await page.fill(dm_selector, msg)
                    await page.press(dm_selector, 'Enter')
                    print(f"Tab {tab_id} sent message {msg_index + 1}/{len(messages)} after reload")
                    send_success = True
                except Exception as post_reload_e:
                    print(f"Tab {tab_id} failed send even after reload: {post_reload_e}")
                    # Proceed to next message anyway
            except Exception as reload_e:
                print(f"Tab {tab_id} reload failed: {reload_e}")
                # Proceed to next message
        
        # Always sleep and cycle to next message
        await asyncio.sleep(1.4)
        msg_index = (msg_index + 1) % len(messages)

async def main():
    """Windows main function"""
    parser = argparse.ArgumentParser(description="Instagram DM Auto Sender for Windows")
    parser.add_argument('--username', required=False, help='Instagram username')
    parser.add_argument('--password', required=False, help='Instagram password')
    parser.add_argument('--thread-url', required=True, help='Instagram direct thread URL')
    parser.add_argument('--names', nargs='+', required=True, help='Messages list or .txt file')
    parser.add_argument('--headless', default='true', choices=['true', 'false'], help='Run in headless mode')
    parser.add_argument('--storage-state', required=True, help='Path to JSON file for login state')
    parser.add_argument('--tabs', type=int, default=1, help='Number of parallel tabs (1-25)')
    
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

    print(f"Parsed {len(messages)} messages.")  

    tabs = min(max(args.tabs, 1), 25)  
    total_tabs = len(thread_urls) * tabs
    print(f"Using {tabs} tabs per URL across {len(thread_urls)} URLs (total: {total_tabs} tabs).")  

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
        
        # Create all pages
        page_urls = []
        for url in thread_urls:
            for i in range(tabs):
                page = await context.new_page()
                page_urls.append((page, url))

        # Parallel initialization
        print("Initializing all tabs in parallel...")
        init_tasks = [asyncio.create_task(init_page(page, url, dm_selector)) for page, url in page_urls]
        init_results = await asyncio.gather(*init_tasks, return_exceptions=True)
        
        pages = []
        for idx, result in enumerate(init_results):
            page, url = page_urls[idx]
            if isinstance(result, Exception):
                print(f"Init task {idx+1} for {url[:50]}... raised exception: {result}")
                try:
                    await page.close()
                except:
                    pass
            elif result:  # Success bool
                pages.append(page)
                print(f"Tab {len(pages)} ready for {url[:50]}...")
            else:
                print(f"Init failed after retries for tab {idx+1} ({url[:50]}...), closing.")
                try:
                    await page.close()
                except:
                    pass

        if not pages:
            print("No tabs could be initialized, exiting.")
            await context.close()
            await browser.close()
            return

        actual_tabs = len(pages)
        print(f"All {actual_tabs} tabs ready. Starting message loops.")
        tasks = [asyncio.create_task(sender(j + 1, args, messages, pages[j])) for j in range(actual_tabs)]
        print(f"Starting {actual_tabs} tab(s) in infinite message loop. Press Ctrl+C to stop.")

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\nStopping all tabs...")
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            for page in pages:
                try:
                    await page.close()
                except Exception:
                    pass
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())