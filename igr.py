import argparse
import os
import json
import time
import re
from instagrapi import Client

def sanitize_input(raw):
    """Fix shell-truncated input"""
    if isinstance(raw, list):
        raw = " ".join(raw)
    return raw

def parse_messages(names_arg):
    """Robust parser for messages from file or string"""
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
                return msgs
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

def extract_thread_ids(thread_url_arg):
    """Extract thread IDs from comma-separated Instagram direct URLs"""
    urls = [u.strip() for u in thread_url_arg.split(',') if u.strip()]
    thread_ids = []
    for url in urls:
        try:
            tid = url.split('/direct/t/')[1].split('/')[0]
            thread_ids.append(tid)
        except IndexError:
            print(f"Invalid URL format: {url}")
    return thread_ids

def login_or_load(username, password, session_path):
    """Login to Instagram and save/load session"""
    cl = Client()
    if os.path.exists(session_path):
        print("Using existing session, loading...")
        try:
            cl.load_settings(session_path)
            cl.login(username, password)  # Validate session
            print("Session loaded successfully.")
            return cl
        except Exception as e:
            print(f"Session invalid: {e}. Performing fresh login.")

    print("Logging in to Instagram...")
    try:
        cl.login(username, password)
        cl.dump_settings(session_path)
        print("Login successful, saving session.")
        return cl
    except Exception as e:
        print(f"Login failed: {e}")
        raise

def main():
    """Instagram DM Infinite Sequential Sender using Instagrapi"""
    parser = argparse.ArgumentParser(description="Instagram DM Infinite Sequential Sender using Instagrapi")
    parser.add_argument('--username', required=True, help='Instagram username')
    parser.add_argument('--password', required=True, help='Instagram password')
    parser.add_argument('--thread-url', required=True, help='Comma-separated Instagram direct thread URLs')
    parser.add_argument('--names', nargs='+', default=['m.txt'], help='Messages list or .txt file (default: m.txt)')
    parser.add_argument('--session-state', default='session.json', help='Path to JSON file for session state (default: session.json)')

    args = parser.parse_args()
    args.names = sanitize_input(args.names)

    thread_ids = extract_thread_ids(args.thread_url)
    if not thread_ids:
        print("Error: No valid thread IDs extracted from URLs.")
        return

    session_path = args.session_state

    try:
        messages = parse_messages(args.names)
    except ValueError as e:
        print(f"Error parsing messages: {e}")
        return

    if not messages:
        print("Error: No valid messages provided.")
        return

    print(f"Parsed {len(messages)} messages from {args.names}. Cycling through them.")
    print(f"Looping over {len(thread_ids)} GC threads sequentially and infinitely. Press Ctrl+C to stop.")

    cl = login_or_load(args.username, args.password, session_path)

    total_processed = 0
    cycle_num = 0
    msg_idx = 0

    try:
        while True:
            print(f"\n--- Cycle {cycle_num + 1} ---")
            cycle_success = 0
            for tid_str in thread_ids:
                tid = int(tid_str)
                msg = messages[msg_idx % len(messages)]
                try:
                    cl.direct_send(msg, thread_ids=[tid])
                    print(f"Sent '{msg[:50]}...' to thread {tid}...")
                    cycle_success += 1
                except Exception as e:
                    print(f"Failed to send '{msg[:50]}...' to thread {tid}: {e}")

                msg_idx += 1
                time.sleep(1.6)  # 1.6s delay after each send

            total_processed += cycle_success
            print(f"Cycle {cycle_num + 1} completed: {cycle_success}/{len(thread_ids)} messages sent to GCs. Total: {total_processed}")
            print("1 cycle complete")

            cycle_num += 1

    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C). Cleaning up...")
    finally:
        cl.dump_settings(session_path)  # Save session on exit
        print(f"Stopped. Total messages sent: {total_processed}")

if __name__ == "__main__":
    main()