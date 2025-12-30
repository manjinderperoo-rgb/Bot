import argparse
import os
import re
import json
import asyncio
import random
import time
from instagrapi import Client
from instagrapi.exceptions import ClientError, LoginRequired

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

def extract_thread_id(url):
    """Extract thread ID from Instagram DM URL like https://www.instagram.com/direct/t/123/"""
    try:
        match = re.search(r'/direct/t/(\d+)/', url)
        if match:
            return match.group(1)
        return None
    except:
        return None

async def login(args, session_path):
    """Async login with instagrapi"""
    cl = Client()
    try:
        if os.path.exists(session_path):
            cl.load_settings(session_path)
            cl.login(args.username, args.password)
            print("Loaded existing session.")
            return cl
        else:
            print("Logging in to Instagram...")
            cl.login(args.username, args.password)
            cl.dump_settings(session_path)
            print("Login successful, saving session.")
            return cl
    except Exception as e:
        print(f"Login error: {e}")
        return None

async def send_to_thread(cl, thread_id, msg):
    """Send message to thread with retries"""
    max_retries = 2
    for retry in range(max_retries):
        try:
            cl.direct_send(msg, thread_ids=[thread_id])
            print(f"Sent '{msg[:50]}...' to thread {thread_id}")
            return True
        except (ClientError, LoginRequired) as e:
            print(f"Send retry {retry+1}/{max_retries} failed for thread {thread_id} with '{msg[:50]}...': {e}")
            if retry < max_retries - 1:
                await asyncio.sleep(1)
            else:
                print(f"Failed after {max_retries} retries, skipping.")
                return False
    return False

async def main():
    """Main function: Sequential infinite loop over threads with 1.5s delays"""
    parser = argparse.ArgumentParser(description="Instagram DM Sequential Looper using Instagrapi for Windows")
    parser.add_argument('--username', required=True, help='Instagram username')
    parser.add_argument('--password', required=True, help='Instagram password')
    parser.add_argument('--thread-url', required=True, help='Comma-separated Instagram direct thread URLs')
    parser.add_argument('--names', nargs='+', default=['m.txt'], help='Messages list or .txt file (default: m.txt)')
    parser.add_argument('--session', default='session.json', help='Path to session file (default: session.json)')
    
    args = parser.parse_args()
    args.names = sanitize_input(args.names)

    thread_urls = [u.strip() for u in args.thread_url.split(',') if u.strip()]
    if not thread_urls:
        print("Error: No valid thread URLs provided.")
        return

    # Extract thread IDs
    thread_ids = []
    for url in thread_urls:
        tid = extract_thread_id(url)
        if tid:
            thread_ids.append(tid)
        else:
            print(f"Warning: Invalid thread URL: {url}")

    if not thread_ids:
        print("Error: No valid thread IDs extracted.")
        return

    print(f"Extracted {len(thread_ids)} thread IDs from URLs.")

    session_path = args.session
    do_login = True  # Always attempt login or load session

    cl = await login(args, session_path)
    if not cl:
        print("Login failed, exiting.")
        return

    try:  
        messages = parse_messages(args.names)  
    except ValueError as e:  
        print(f"Error parsing messages: {e}")  
        return  

    if not messages:  
        print("Error: No valid messages provided.")  
        return  

    print(f"Parsed {len(messages)} messages. Cycling through {len(thread_ids)} threads sequentially with 1.5s delays. Press Ctrl+C to stop.")

    total_processed = 0
    loop_num = 0
    msg_idx = 0
    tid_idx = 0

    try:
        while True:
            print(f"\n--- Loop {loop_num + 1}, Thread {tid_idx + 1}/{len(thread_ids)} ---")
            thread_id = thread_ids[tid_idx]
            msg = messages[msg_idx % len(messages)]
            
            success = await send_to_thread(cl, thread_id, msg)
            if success:
                total_processed += 1
                print(f"Success. Total sent: {total_processed}")
            
            # Cycle indices
            tid_idx = (tid_idx + 1) % len(thread_ids)
            msg_idx += 1
            
            # 1.5s delay after each send
            await asyncio.sleep(1.5)
            
            if tid_idx == 0:
                loop_num += 1
                print(f"Completed loop {loop_num}. Restarting from first thread.")

    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C). Cleaning up...")
    finally:
        print(f"Stopped. Total messages sent: {total_processed}")

if __name__ == "__main__":
    asyncio.run(main())