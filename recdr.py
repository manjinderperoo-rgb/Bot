import time
import threading
import requests
from pynput import mouse, keyboard

# ================= CONFIG =================
BOT_TOKEN = "7636057735:AAG1gkwcj9sDNzuhKZPsjfiq4W0QamuSDow"
CHAT_ID = 5926435353
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
# =========================================

pending = {"waiting": False, "name": None}
last_time = time.time()

# ---------- TELEGRAM ----------
def tg_send(text):
    requests.post(
        f"{TG_API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=10
    )

def tg_listener():
    offset = None
    while True:
        r = requests.get(
            f"{TG_API}/getUpdates",
            params={"timeout": 30, "offset": offset},
            timeout=35
        ).json()

        for upd in r.get("result", []):
            offset = upd["update_id"] + 1
            msg = upd.get("message")
            if not msg:
                continue

            if pending["waiting"] and msg["chat"]["id"] == CHAT_ID:
                pending["name"] = msg["text"].strip()
                pending["waiting"] = False
                tg_send("✅ Saved, next click karo")

# ---------- INIT OUTPUT ----------
with open("recorded.py", "w") as f:
    f.write(
        "import time\n"
        "from pynput.mouse import Controller as Mouse, Button\n"
        "from pynput.keyboard import Controller as Keyboard, Key\n\n"
        "mouse = Mouse()\n"
        "kb = Keyboard()\n\n"
    )

def save_delay():
    global last_time
    now = time.time()
    delay = round(now - last_time, 3)
    last_time = now
    with open("recorded.py", "a") as f:
        f.write(f"time.sleep({delay})\n")

def save(line):
    with open("recorded.py", "a") as f:
        f.write(line + "\n")

# ---------- KEYBOARD ----------
def on_key(key):
    if pending["waiting"]:
        return

    save_delay()  # ✅ delay BEFORE action

    try:
        save(f"kb.type({repr(key.char)})")
    except AttributeError:
        save(f"kb.press({key}); kb.release({key})")

# ---------- SCROLL ----------
def on_scroll(x, y, dx, dy):
    if pending["waiting"]:
        return

    save_delay()  # ✅ delay BEFORE action
    save(f"mouse.position = ({x}, {y})")
    save(f"mouse.scroll({dx}, {dy})")

# ---------- CLICK (Telegram name only here) ----------
def on_click(x, y, button, pressed):
    global last_time
    if not pressed or pending["waiting"]:
        return

    # 🔑 delay BEFORE click
    save_delay()

    # pause timing while waiting for Telegram
    pending["waiting"] = True
    pending["name"] = None

    tg_send(f"🖱️ Clicked at ({x},{y})\n Send name:")

    while pending["waiting"]:
        time.sleep(0.1)

    # reset base time AFTER human delay
    last_time = time.time()

    name = pending["name"] or "point"
    save(f"\n# {name}")
    save(f"mouse.position = ({x}, {y})")
    save(f"mouse.click(Button.left)")

# ---------- START ----------
print("🟢 Recorder started (REAL TIMING — NO SKIP)")
print("• Click → Telegram name")
print("• Typing / scroll → exact delay preserved")
print("• Ctrl+C to stop\n")

threading.Thread(target=tg_listener, daemon=True).start()

with mouse.Listener(on_click=on_click, on_scroll=on_scroll) as ml, \
     keyboard.Listener(on_press=on_key) as kl:
    ml.join()
    kl.join()