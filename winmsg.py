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
            await page.goto("https://www.instagram.com/", timeout=60000)
            await page.goto(url, timeout=60000)
            await page.wait_for_selector(dm_selector, timeout=30000)
            init_success = True
            break
        except Exception as init_e:
            print(f"Tab for {url[:30]}... try {init_try+1}/3 failed: {init_e}")
            if init_try < 2:
                await asyncio.sleep(2)
    return init_success

async def sender(tab_id, args, messages, context, page):
    """Windows async sender coroutine"""
    dm_selector = 'div[role="textbox"][aria-label="Message"]'
    print(f"Tab {tab_id} ready, starting infinite message loop.")
    current_page = page
    cycle_start = time.time()
    msg_index = 0
    
    while True:
        elapsed = time.time() - cycle_start
        if elapsed >= 60:
            try:
                print(f"Tab {tab_id} reloading thread after {elapsed:.1f}s")
                await current_page.reload(timeout=60000)
                await current_page.wait_for_selector(dm_selector, timeout=30000)
            except Exception as reload_e:
                print(f"Tab {tab_id} reload failed after {elapsed:.1f}s: {reload_e}")
                raise Exception(f"Tab {tab_id} reload failed: {reload_e}")
            cycle_start = time.time()
            continue
            
        msg = messages[msg_index]
        send_success = False
        max_retries = 2
        
        for retry in range(max_retries):
            try:
                if not current_page.locator(dm_selector).is_visible():
                    print(f"Tab {tab_id} selector not visible on retry {retry+1}/{max_retries} for '{msg[:50]}...', attempting Enter to clear.")
                    try:
                        await current_page.press(dm_selector, 'Enter')
                        await asyncio.sleep(0.2)
                    except:
                        pass
                    await asyncio.sleep(0.5)
                    continue

                await current_page.click(dm_selector)
                await current_page.fill(dm_selector, msg)
                await current_page.press(dm_selector, 'Enter')
                print(f"Tab {tab_id} sent message {msg_index + 1}/{len(messages)} on retry {retry+1}")
                send_success = True
                break
            except Exception as send_e:
                print(f"Tab {tab_id} send error on retry {retry+1}/{max_retries} for message {msg_index + 1}: {send_e}")
                if retry < max_retries - 1:
                    print(f"Tab {tab_id} retrying after brief pause...")
                    await asyncio.sleep(0.5)
                else:
                    print(f"Tab {tab_id} all retries failed for message {msg_index + 1}, triggering restart.")
        
        if not send_success:
            raise Exception(f"Tab {tab_id} failed to send after {max_retries} retries")
        
        await asyncio.sleep(0.24)
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
    parser.add_argument('--tabs', type=int, default=1, help='Number of parallel tabs (1-5)')
    
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

    tabs = min(max(args.tabs, 1), 5)  
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
        pages = []
        tasks = []
        
        try:
            while True:
                for page in pages:
                    try:
                        await page.close()
                    except Exception:
                        pass
                pages = []
                for task in tasks:
                    try:
                        task.cancel()
                    except Exception:
                        pass
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                tasks = []

                page_urls = []
                for url in thread_urls:
                    for i in range(tabs):
                        page = await context.new_page()
                        page_urls.append((page, url))

                init_tasks = [asyncio.create_task(init_page(page, url, dm_selector)) for page, url in page_urls]
                init_results = await asyncio.gather(*init_tasks, return_exceptions=True)

                for idx, result in enumerate(init_results):
                    page, url = page_urls[idx]
                    if isinstance(result, Exception) or not result:
                        print(f"Tab for {url} failed to initialize after 3 tries, skipping.")
                        try:
                            await page.close()
                        except:
                            pass
                    else:
                        pages.append(page)
                        print(f"Tab {len(pages)} ready for {url[:50]}...")

                if not pages:
                    print("No tabs could be initialized, exiting.")
                    return

                actual_tabs = len(pages)
                tasks = [asyncio.create_task(sender(j + 1, args, messages, context, pages[j])) for j in range(actual_tabs)]
                print(f"Starting {actual_tabs} tab(s) in infinite message loop. Press Ctrl+C to stop.")

                pending = set(tasks)
                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        if task.exception():
                            exc = task.exception()
                            print(f"Tab task raised exception: {exc}")
                            for t in list(pending):
                                t.cancel()
                            await asyncio.gather(*pending, return_exceptions=True)
                            pending.clear()
                            break
                    else:
                        continue
                    break
        except KeyboardInterrupt:
            print("\nStopping all tabs...")
        finally:
            for page in pages:
                try:
                    await page.close()
                except Exception:
                    pass
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())