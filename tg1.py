# kento_bot_multi.py
import asyncio
import json
import os
import random
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import logging
import yt_dlp
from gtts import gTTS
import requests
import io

# ---------------------------
# CONFIG
# ---------------------------
TOKENS = [
    "8218925478:AAFxhw8_G-MhP7t5HAg0dURe5g-ncZBR0B8",
    "8503330095:AAEoK2ZrGulf9xpBqKwqo24CgWIyd_4vxnw",
    "8327928283:AAHouuv3o9nOmvVEULSTI6Q-1dipN-ioTbU",
    "7805620547:AAEcg1sNxr9VEn7XpDp9iF0stlCicPcAJo0",
    "8215726610:AAG7EKHIYxqeW5zGL9MfwDrjkOYQ_nLeqLM",
    "8504193969:AAHu5GNnY9BAmcPr5W1UgBKJ3fQAiCwXb9A",
    "8047880599:AAEFv_l_6rG5JanU0eIeVgcLsaJxKYiG7lU",
    "8439116853:AAHLWoWoJnFf3ZYnGYsYY_HZt4kB7Z4LrXs",
    "8588867217:AAELcrw0LWevTCicus-5sKTsnlsopWd4Dvk",
    "8526799865:AAEcSO3Q0ETsdj2CYKKwoJ8CiBGAp8hrBGU",
    "8493593131:AAG4puV2QT9VmqmTR5aKFu4ZtE2SikNesjk",
    "8249563826:AAF3Opho_3ovsLquYXH_iDrYmF8PTZOwtBU",
    "8224230339:AAHqgVfA5WDwtoTY3ZVUoUAFLsJ5ZHiBNBE",
    "8335754812:AAF0WteWEJMbGErUpeqezEvDwIYBjOKDPZQ",
    "8467159142:AAH9UiRo3VdgVbHnspIcLeLLs0hCdiv9LP0"
]

CHAT_ID = 6918968298
OWNER_ID = 6918968298
SUDO_FILE = "sudo_users.json"
STICKER_FILE = "stickers.json"
VOICE_CLONES_FILE = "voice_clones.json"
tempest_API_KEY = "sk_e326b337242b09b451e8f18041fd0a7149cc895648e36538"

# ---------------------------
# tempest VOICE CHARACTERS
# ---------------------------
VOICE_CHARACTERS = {
    1: {
        "name": "Urokodaki",
        "voice_id": "VR6AewLTigWG4xSOukaG",  # Deep Indian voice
        "description": "Deep Indian voice - Urokodaki style",
        "style": "deep_masculine"
    },
    2: {
        "name": "Kanae", 
        "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Cute sweet voice
        "description": "Cute sweet voice - Kanae style",
        "style": "soft_feminine"
    },
    3: {
        "name": "Uppermoon",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",  # Creepy dark voice
        "description": "Creepy dark deep voice - Uppermoon style", 
        "style": "dark_creepy"
    },
    4: {
        "name": "Tanjiro",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "description": "Heroic determined voice",
        "style": "heroic"
    },
    5: {
        "name": "Nezuko",
        "voice_id": "EXAVITQu4vr4xnSDxMaL", 
        "description": "Cute mute sounds",
        "style": "cute_mute"
    },
    6: {
        "name": "Zenitsu",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "description": "Scared whiny voice",
        "style": "scared_whiny"
    },
    7: {
        "name": "Inosuke",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "description": "Wild aggressive voice",
        "style": "wild_aggressive"
    },
    8: {
        "name": "Muzan",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "description": "Evil mastermind voice",
        "style": "evil_calm"
    },
    9: {
        "name": "Shinobu",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "description": "Gentle but deadly voice",
        "style": "gentle_deadly"
    },
    10: {
        "name": "Giyu",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "description": "Silent serious voice",
        "style": "silent_serious"
    }
}

# ---------------------------
# TEXTS
# ---------------------------
RAID_TEXTS = [
 "×~🌷GAY🌷×~",
"~×🌼BITCH🌼×~",
"~×🌻LESBIAN🌻×~",
"~×🌺CHAPRI🌺×~",
"~×🌹TMKC🌹×~",
"~×🏵️TMR🏵×~️",
"~×🪷TMKB🪷×~",
"~×💮CHUS💮×~",
"~×🌸HAKLE🌸×~",
"~×🌷GAREEB🌷×~",
"~×🌼RANDY🌼×~",
"~×🌻POOR🌻×~",
"~×🌺TATTI🌺×~",
"~×🌹CHOR🌹×~",
"~×🏵️CHAMAR🏵️×~",
"~×🪷SPERM COLLECTOR🪷×~",
"~×💮CHUTI LULLI💮×~",
"~×🌸KALWA🌸×~",
"~×🌷CHUD🌷×~",
"~×🌼CHUTKHOR🌼×~",
"~×🌻BAUNA🌻×~",
"~×🌺MOTE🌺×~",
"~×🌹GHIN ARHA TUJHSE🌹×~",
"~×🏵️CHI POOR🏵×~️",
"~🪷PANTY CHOR🪷~",
"~×💮LAND CHUS💮×~",
"~×🌸MUH MAI LEGA🌸×~",
"~×🌷GAND MARE 🌷×~",
"~×🌼MOCHI WALE 🌼×~",
"~×🌻GANDMARE 🌻×~",
"~×🌺KIDDE 🌺×~",
"~×🌹LAMO 🌹×~",
"~×🏵️BIHARI 🏵×~️",
"~×🪷MULLE 🪷×~",
"~×💮NAJAYESH LADKE 💮×~",
"~×🌸GULAM 🌸×~",
"~×🌷CHAMCHA🌷×~",
"~×🌼EWW 🌼×~",
"~×🌻CHOTE TATTE 🌻×~",
"~×🌺SEX WORKER 🌺×~",
"~×🌹CHINNAR MA KE LADKE 🌹×~"
]

exonc_TEXTS = [
    "×🌼×","×🌻×","×🪻×","×🏵️×","×💮×","×🌸×","×🪷×","×🌷×",
    "×🌺×","×🥀×","×🌹×","×💐×","×💋×","×❤️‍🔥×","×❤️‍🩹×","×❣️×",
    "×♥️×","×💟×","×💌×","×💕×","×💞×","×💓×","×💗×","×💖×",
    "×💝×","×💘×","×🩷×","×🤍×","×🩶×","×🖤×","🤎×","×💜×",
    "×💜×","×🩵×","×💛×","×🧡×","×❤️×","×🌼×","×🌻×","×🪻×",
"×🏵️×","×💮×","×🌸×","×🪷×","×🌷×",
    "×🌺×","×🥀×","×🌹×","×💐×","×💋×","×❤️‍🔥×","×❤️‍🩹×","×❣️×",
    "×♥️×","×💟×","×💌×","×💕×","×💞×","×💓×","×💗×","×💖×",
    "×💝×","×💘×","×🩷×","×🤍×","×🩶×","×🖤×","🤎×","×💜×",
    "×💜×","×🩵×","×💛×","×🧡×","×❤️×",
]

NCEMO_EMOJIS = [
  "😀","😃","😄","😁","😆","😅","😂","🤣","😭","😉","😗","😗","😚","😘","🥰","😍",
"🤩","🥳","🫠","🙃","🙂","🥲","🥹","😊","☺️","😌","🙂‍↕️","🙂‍↔️",
  "😏","🤤","😋","😛","😝","😜","🤪","🥴","😔","🥺","😬","😑","😐","😶","😶‍🌫️",
"🫥","🤐","🫡","🤔","🤫","🫢","🤭","🥱","🤗","🫣","😱","🤨","🧐","😒","🙄","😮‍💨","😤",
"😠","😡","🤬","😞","😓",
  "😟","😥","😢","☹️","🙁","🫤","😕","😰","😨","😧","😦","😮","😯","😲","😳",
  "🤯","😖","😣","😩","😵","😵‍💫","🫨","🥶","🥵","🤢","🤮","😴","😪","🤧","🤒",
  "🤒","🤕","😷","😇","🤠","🤑","🤓","😎","🥸",
]

# ---------------------------
# GLOBAL STATE
# ---------------------------
if os.path.exists(SUDO_FILE):
    try:
        with open(SUDO_FILE, "r") as f:
            _loaded = json.load(f)
            SUDO_USERS = set(int(x) for x in _loaded)
    except Exception:
        SUDO_USERS = {OWNER_ID}
else:
    SUDO_USERS = {OWNER_ID}

# Initialize data files
if os.path.exists(STICKER_FILE):
    try:
        with open(STICKER_FILE, "r") as f:
            user_stickers = json.load(f)
    except:
        user_stickers = {}
else:
    user_stickers = {}

if os.path.exists(VOICE_CLONES_FILE):
    try:
        with open(VOICE_CLONES_FILE, "r") as f:
            voice_clones = json.load(f)
    except:
        voice_clones = {}
else:
    voice_clones = {}

def save_sudo():
    with open(SUDO_FILE, "w") as f: 
        json.dump(list(SUDO_USERS), f)

def save_stickers():
    with open(STICKER_FILE, "w") as f: 
        json.dump(user_stickers, f)

def save_voice_clones():
    with open(VOICE_CLONES_FILE, "w") as f: 
        json.dump(voice_clones, f)

# Global state variables
group_tasks = {}         
spam_tasks = {}
react_tasks = {}
slide_targets = set()    
slidespam_targets = set()
exonc_tasks = {}
sticker_mode = True
apps, bots = [], []
delay = 0.1
spam_delay = 0.5
exonc_delay = 0.05

logging.basicConfig(level=logging.INFO)

# ---------------------------
# DECORATORS
# ---------------------------
def only_sudo(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in SUDO_USERS:
            await update.message.reply_text("🐕❌AUKAT BANA KUTIYA KE LADKE🐕❌.")
            return
        return await func(update, context)
    return wrapper

def only_owner(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid != OWNER_ID:
            await update.message.reply_text("🤬BHAG JA TERI AUKAT NHI TMKC🤬.")
            return
        return await func(update, context)
    return wrapper

# ---------------------------
# tempest VOICE FUNCTIONS
# ---------------------------
async def generate_tempest_voice(text, voice_id, stability=0.5, similarity_boost=0.8):
    """Generate voice using tempest API"""
    url = f"https://api.tempest.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": tempest_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return io.BytesIO(response.content)
        else:
            logging.error(f"tempest API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"tempest request failed: {e}")
        return None

async def generate_multiple_voices(text, character_numbers):
    """Generate voices for multiple characters"""
    voices = []
    
    for char_num in character_numbers:
        if char_num in VOICE_CHARACTERS:
            voice_data = VOICE_CHARACTERS[char_num]
            audio_data = await generate_tempest_voice(text, voice_data["voice_id"])
            if audio_data:
                voices.append({
                    "character": voice_data["name"],
                    "audio": audio_data,
                    "description": voice_data["description"]
                })
    
    return voices

# ---------------------------
# LOOP FUNCTIONS - OPTIMIZED FOR MULTI-GC
# ---------------------------
async def bot_loop(bot, chat_id, base, mode):
    i = 0
    while True:
        try:
            if mode == "gcnc":
                text = f"{base} {RAID_TEXTS[i % len(RAID_TEXTS)]}"
            else:
                text = f"{base} {NCEMO_EMOJIS[i % len(NCEMO_EMOJIS)]}"
            asyncio.create_task(safe_set_title(bot, chat_id, text))
            i += 1
            await asyncio.sleep(delay)
        except:
            await asyncio.sleep(0.5)

async def safe_set_title(bot, chat_id, text):
    try:
        await asyncio.wait_for(bot.set_chat_title(chat_id, text), timeout=3)
    except:
        pass

async def safe_send_message(bot, chat_id, text):
    try:
        await asyncio.wait_for(bot.send_message(chat_id, text), timeout=3)
    except:
        pass

async def ncbaap_loop(bot, chat_id, base):
    i = 0
    while True:
        try:
            patterns = [
                f"{base} {RAID_TEXTS[i % len(RAID_TEXTS)]}",
                f"{base} {NCEMO_EMOJIS[i % len(NCEMO_EMOJIS)]}",
                f"{base} {exonc_TEXTS[i % len(exonc_TEXTS)]}",
            ]
            tasks = [safe_set_title(bot, chat_id, p) for p in patterns]
            await asyncio.gather(*tasks, return_exceptions=True)
            i += 1
            await asyncio.sleep(0.05)
        except:
            await asyncio.sleep(0.3)

async def spam_loop(bot, chat_id, text):
    while True:
        try:
            asyncio.create_task(safe_send_message(bot, chat_id, text))
            await asyncio.sleep(spam_delay)
        except:
            await asyncio.sleep(0.5)

async def exonc_godspeed_loop(bot, chat_id, base_text):
    i = 0
    while True:
        try:
            patterns = [
                f"{base_text} {exonc_TEXTS[i % len(exonc_TEXTS)]}",
                f"{exonc_TEXTS[i % len(exonc_TEXTS)]} {base_text}",
                f"{base_text}{exonc_TEXTS[i % len(exonc_TEXTS)]}",
                f"{exonc_TEXTS[(i+1) % len(exonc_TEXTS)]} {base_text}",
                f"{base_text} {exonc_TEXTS[(i+2) % len(exonc_TEXTS)]}",
            ]
            tasks = [safe_set_title(bot, chat_id, p) for p in patterns]
            await asyncio.gather(*tasks, return_exceptions=True)
            i += 1
            await asyncio.sleep(0.02)
        except:
            await asyncio.sleep(0.2)

async def exonc_loop(bot, chat_id, base_text):
    i = 0
    while True:
        try:
            text = f"{base_text} {exonc_TEXTS[i % len(exonc_TEXTS)]}"
            asyncio.create_task(safe_set_title(bot, chat_id, text))
            i += 1
            await asyncio.sleep(exonc_delay)
        except:
            await asyncio.sleep(0.3)

# ---------------------------
# CORE COMMANDS
# ---------------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🪷 BABY NC 🪷\nUse /help")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """🪷 BABY NC MENU 🪷

🎀 NC:
/ncloop <name>
/ncemo <name>
/ncbaap <name>
/stopncloop | /stopncemo | /stopncbaap
/stopall | /delay <sec>

😹 Spam:
/spam <text> | /unspam

🪐 React:
/emojispam <emoji> | /stopemojispam

🪼 Slide:
/targetslide | /stopslide
/slidespam | /stopslidespam

⚡ Exonc:
/exonc | /exoncfast | /exoncgodspeed
/stopexonc

🎵 Voice:
/animevn <1-10> <text>
/voices | /tempest <text>

👑 SUDO:
/addsudo | /delsudo | /listsudo

🦚 Misc:
/myid | /ready | /status"""
    await update.message.reply_text(help_text)

async def ready_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.time()
    msg = await update.message.reply_text("💭 Hmm...")
    end = time.time()
    await msg.edit_text(f"✅ All set! ")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your ID: {update.effective_user.id}")

# ---------------------------
# NAME CHANGER COMMANDS
# ---------------------------
@only_sudo
async def ncloop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /ncloop <name>")
    
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    
    # Stop existing tasks
    if chat_id in group_tasks:
        for task in group_tasks[chat_id]:
            task.cancel()
    
    # Start new tasks
    tasks = []
    for bot in bots:
        task = asyncio.create_task(bot_loop(bot, chat_id, base, "gcnc"))
        tasks.append(task)
    
    group_tasks[chat_id] = tasks
    await update.message.reply_text("🔄चुदाई Suru target ka")

@only_sudo
async def ncemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /ncemo <name>")
    
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    
    # Stop existing tasks
    if chat_id in group_tasks:
        for task in group_tasks[chat_id]:
            task.cancel()
    
    # Start new tasks
    tasks = []
    for bot in bots:
        task = asyncio.create_task(bot_loop(bot, chat_id, base, "ncemo"))
        tasks.append(task)
    
    group_tasks[chat_id] = tasks
    await update.message.reply_text("🌹emoji cycle started 🌹")

@only_sudo
async def ncbaap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GOD LEVEL Name Changer - 5 changes in 0.1 seconds"""
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /ncbaap <name>")
    
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    
    # Stop existing tasks
    if chat_id in group_tasks:
        for task in group_tasks[chat_id]:
            task.cancel()
    
    # Start ultra fast tasks
    tasks = []
    for bot in bots:
        task = asyncio.create_task(ncbaap_loop(bot, chat_id, base))
        tasks.append(task)
    
    group_tasks[chat_id] = tasks
    await update.message.reply_text("💀🔥 GOD SPEED NCBAAP LOOP STARTED 💀🔥")

@only_sudo
async def stopncloop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        for task in group_tasks[chat_id]:
            task.cancel()
        del group_tasks[chat_id]
        await update.message.reply_text("⏹ NC Loop Stopped!")
    else:
        await update.message.reply_text("❌ No active NC loop")

@only_sudo
async def stopncemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        for task in group_tasks[chat_id]:
            task.cancel()
        del group_tasks[chat_id]
        await update.message.reply_text("⏹ Emoji Name Changer Stopped!")
    else:
        await update.message.reply_text("❌ No active emoji changer")

@only_sudo
async def stopncbaap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        for task in group_tasks[chat_id]:
            task.cancel()
        del group_tasks[chat_id]
        await update.message.reply_text("⏹ GOD LEVEL NCBAAP Stopped!")
    else:
        await update.message.reply_text("❌ No active ncbaap")

# ---------------------------
# exonc COMMANDS - FIXED
# ---------------------------
@only_sudo
async def exonc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /exonc <name>")
    
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    
    # Stop existing tasks
    if chat_id in exonc_tasks:
        for task in exonc_tasks[chat_id]:
            task.cancel()
    
    # Start new tasks
    tasks = []
    for bot in bots:
        task = asyncio.create_task(exonc_loop(bot, chat_id, base))
        tasks.append(task)
    
    exonc_tasks[chat_id] = tasks
    await update.message.reply_text("💀 exonc Mode Activated!")

@only_sudo
async def exoncfast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global exonc_delay
    exonc_delay = 0.03
    
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /exoncfast <name>")
    
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    
    if chat_id in exonc_tasks:
        for task in exonc_tasks[chat_id]:
            task.cancel()
    
    tasks = []
    for bot in bots:
        task = asyncio.create_task(exonc_loop(bot, chat_id, base))
        tasks.append(task)
    
    exonc_tasks[chat_id] = tasks
    await update.message.reply_text("⚡ Faster exonc Activated!")

@only_sudo
async def exoncgodspeed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ULTRA FAST GOD SPEED MODE - FIXED"""
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /exoncgodspeed <name>")
    
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    
    # Stop existing tasks
    if chat_id in exonc_tasks:
        for task in exonc_tasks[chat_id]:
            task.cancel()
    
    # Start GOD SPEED tasks
    tasks = []
    for bot in bots:
        task = asyncio.create_task(exonc_godspeed_loop(bot, chat_id, base))
        tasks.append(task)
    
    exonc_tasks[chat_id] = tasks
    await update.message.reply_text("👑🔥 GOD SPEED exonc ACTIVATED! 5 NC in 0.05s! 🚀")

@only_sudo
async def stopexonc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in exonc_tasks:
        for task in exonc_tasks[chat_id]:
            task.cancel()
        del exonc_tasks[chat_id]
        await update.message.reply_text("🛑 exonc Stopped!")
    else:
        await update.message.reply_text("❌ No active exonc")

# ---------------------------
# SPAM COMMANDS
# ---------------------------
@only_sudo
async def spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /spam <text>")
    
    text = " ".join(context.args)
    chat_id = update.message.chat_id
    
    # Stop existing spam
    if chat_id in spam_tasks:
        for task in spam_tasks[chat_id]:
            task.cancel()
    
    # Start new spam
    tasks = []
    for bot in bots:
        task = asyncio.create_task(spam_loop(bot, chat_id, text))
        tasks.append(task)
    
    spam_tasks[chat_id] = tasks
    await update.message.reply_text("💥 SPAM STARTED!")

@only_sudo
async def unspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in spam_tasks:
        for task in spam_tasks[chat_id]:
            task.cancel()
        del spam_tasks[chat_id]
        await update.message.reply_text("🛑 Spam Stopped!")
    else:
        await update.message.reply_text("❌ No active spam")

# ---------------------------
# SLIDE COMMANDS - FIXED
# ---------------------------
@only_sudo
async def targetslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a user's message")
    
    target_id = update.message.reply_to_message.from_user.id
    slide_targets.add(target_id)
    await update.message.reply_text(f"🎯 Target slide added: {target_id}")

@only_sudo
async def stopslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a user's message")
    
    target_id = update.message.reply_to_message.from_user.id
    slide_targets.discard(target_id)
    await update.message.reply_text(f"🛑 Slide stopped: {target_id}")

@only_sudo
async def slidespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a user's message")
    
    target_id = update.message.reply_to_message.from_user.id
    slidespam_targets.add(target_id)
    await update.message.reply_text(f"💥 Slide spam started: {target_id}")

@only_sudo
async def stopslidespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a user's message")
    
    target_id = update.message.reply_to_message.from_user.id
    slidespam_targets.discard(target_id)
    await update.message.reply_text(f"🛑 Slide spam stopped: {target_id}")

# ---------------------------
# VOICE COMMANDS - tempest INTEGRATION
# ---------------------------
@only_sudo
async def animevn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anime voice with tempest - FIXED SYNTAX"""
    if not context.args or len(context.args) < 2:
        return await update.message.reply_text("⚠️ Usage: /animevn <character_numbers> <text>\nExample: /animevn 1 2 3 Hello world")
    
    try:
        # Parse character numbers
        char_numbers = []
        text_parts = []
        
        for arg in context.args:
            if arg.isdigit() and int(arg) in VOICE_CHARACTERS:
                char_numbers.append(int(arg))
            else:
                text_parts.append(arg)
        
        if not char_numbers:
            return await update.message.reply_text("❌ Please provide valid character numbers (1-10)")
        
        text = " ".join(text_parts)
        if not text:
            return await update.message.reply_text("❌ Please provide text to speak")
        
        await update.message.reply_text(f"🎭 Generating voices for characters: {', '.join([VOICE_CHARACTERS[num]['name'] for num in char_numbers])}...")
        
        # Generate voices
        voices = await generate_multiple_voices(text, char_numbers)
        
        if not voices:
            # Fallback to gTTS if tempest fails
            tts = gTTS(text=text, lang='ja', slow=False)
            voice_file = io.BytesIO()
            tts.write_to_fp(voice_file)
            voice_file.seek(0)
            
            character_names = [VOICE_CHARACTERS[num]['name'] for num in char_numbers]
            await update.message.reply_voice(
                voice=voice_file, 
                caption=f"🎀 {' + '.join(character_names)}: {text}"
            )
        else:
            # Send each voice
            for voice in voices:
                await update.message.reply_voice(
                    voice=voice["audio"],
                    caption=f"🎀 {voice['character']}: {text}\n{voice['description']}"
                )
                await asyncio.sleep(1)  # Delay between voices
        
    except Exception as e:
        await update.message.reply_text(f"❌ Voice error: {e}")

@only_sudo
async def tempest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Default tempest voice"""
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /tempest <text>")
    
    text = " ".join(context.args)
    
    # Use Urokodaki voice as default
    audio_data = await generate_tempest_voice(text, VOICE_CHARACTERS[1]["voice_id"])
    
    if audio_data:
        await update.message.reply_voice(
            voice=audio_data,
            caption=f"🎙️ {VOICE_CHARACTERS[1]['name']}: {text}"
        )
    else:
        # Fallback to gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        voice_file = io.BytesIO()
        tts.write_to_fp(voice_file)
        voice_file.seek(0)
        await update.message.reply_voice(voice=voice_file, caption=f"🗣️ Fallback TTS: {text}")

@only_sudo
async def voices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available voices"""
    voice_list = "🎭 Available Anime Voices:\n\n"
    for num, voice in VOICE_CHARACTERS.items():
        voice_list += f"{num}. {voice['name']} - {voice['description']}\n"
    
    voice_list += "\n🎀 Usage: /animevn 1 2 3 Hello world"
    await update.message.reply_text(voice_list)

# Other voice commands remain the same...
@only_sudo
async def music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /music <song>")
    
    song = " ".join(context.args)
    await update.message.reply_text(f"🎶 Downloading: {song}")

@only_sudo
async def clonevn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a voice message")
    
    await update.message.reply_text("🎤 Voice cloning started...")

@only_sudo
async def clonedvn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /clonedvn <text>")
    
    text = " ".join(context.args)
    await update.message.reply_text(f"🎙️ Speaking in cloned voice: {text}")

# ---------------------------
# REACT COMMANDS
# ---------------------------
@only_sudo
async def emojispam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /emojispam <emoji>")
    
    emoji = context.args[0]
    chat_id = update.message.chat_id
    
    async def react_loop(bot, chat_id, emoji):
        while True:
            await asyncio.sleep(1)
    
    if chat_id in react_tasks:
        for task in react_tasks[chat_id]:
            task.cancel()
    
    tasks = []
    for bot in bots:
        task = asyncio.create_task(react_loop(bot, chat_id, emoji))
        tasks.append(task)
    
    react_tasks[chat_id] = tasks
    await update.message.reply_text(f"🎭 Auto-reaction: {emoji}")

@only_sudo
async def stopemojispam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in react_tasks:
        for task in react_tasks[chat_id]:
            task.cancel()
        del react_tasks[chat_id]
        await update.message.reply_text("🛑 Reactions Stopped!")
    else:
        await update.message.reply_text("❌ No active reactions")

# ---------------------------
# STICKER SYSTEM
# ---------------------------
@only_sudo
async def newsticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return await update.message.reply_text("⚠️ Reply to a photo with /newsticker")
    
    await update.message.reply_text("✅ Sticker creation ready! Choose emoji for sticker")

@only_sudo
async def delsticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) in user_stickers:
        del user_stickers[str(user_id)]
        save_stickers()
        await update.message.reply_text("✅ Your stickers deleted!")
    else:
        await update.message.reply_text("❌ No stickers found")

@only_sudo
async def multisticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Creating 5 stickers...")

@only_sudo
async def stickerstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_stickers = sum(len(stickers) for stickers in user_stickers.values())
    await update.message.reply_text(f"📊 Sticker Status: {total_stickers} stickers total")

@only_owner
async def stopstickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sticker_mode
    sticker_mode = False
    await update.message.reply_text("🛑 Stickers disabled")

@only_owner
async def startstickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sticker_mode
    sticker_mode = True
    await update.message.reply_text("✅ Stickers enabled")

# ---------------------------
# CONTROL COMMANDS
# ---------------------------
@only_sudo
async def stopall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Stop all tasks
    for chat_tasks in group_tasks.values():
        for task in chat_tasks:
            task.cancel()
    group_tasks.clear()
    
    for chat_tasks in spam_tasks.values():
        for task in chat_tasks:
            task.cancel()
    spam_tasks.clear()
    
    for chat_tasks in react_tasks.values():
        for task in chat_tasks:
            task.cancel()
    react_tasks.clear()
    
    for chat_tasks in exonc_tasks.values():
        for task in chat_tasks:
            task.cancel()
    exonc_tasks.clear()
    
    slide_targets.clear()
    slidespam_targets.clear()
    
    await update.message.reply_text("⏹ ALL ACTIVITIES STOPPED!")

@only_sudo
async def delay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global delay
    if not context.args:
        return await update.message.reply_text(f"⏱ Current delay: {delay}s")
    
    try:
        delay = max(0.1, float(context.args[0]))
        await update.message.reply_text(f"✅ Delay set to {delay}s")
    except:
        await update.message.reply_text("❌ Invalid number")

# ---------------------------
# STATUS COMMANDS
# ---------------------------
@only_sudo
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = f"""
📊 Nexa V4 Status:

🎀 Name Changers: {sum(len(tasks) for tasks in group_tasks.values())}
⚡ exonc Sessions: {sum(len(tasks) for tasks in exonc_tasks.values())}
😹 Spam Sessions: {sum(len(tasks) for tasks in spam_tasks.values())}
🪐 Reactions: {sum(len(tasks) for tasks in react_tasks.values())}
🪼 Slide Targets: {len(slide_targets)}
💥 Slide Spam: {len(slidespam_targets)}

⏱ Delay: {delay}s
⚡ exonc Delay: {exonc_delay}s
🤖 Active Bots: {len(bots)}
👑 SUDO Users: {len(SUDO_USERS)}
🎭 Voice Characters: {len(VOICE_CHARACTERS)}
    """
    await update.message.reply_text(status_text)

# ---------------------------
# SUDO MANAGEMENT
# ---------------------------
@only_owner
async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a user")
    
    uid = update.message.reply_to_message.from_user.id
    SUDO_USERS.add(uid)
    save_sudo()
    await update.message.reply_text(f"✅ SUDO added: {uid}")

@only_owner
async def delsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a user")
    
    uid = update.message.reply_to_message.from_user.id
    if uid in SUDO_USERS:
        SUDO_USERS.remove(uid)
        save_sudo()
        await update.message.reply_text(f"🗑 SUDO removed: {uid}")
    else:
        await update.message.reply_text("❌ User not in SUDO")

@only_sudo
async def listsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sudo_list = "\n".join([f"👑 {uid}" for uid in SUDO_USERS])
    await update.message.reply_text(f"👑 SUDO Users:\n{sudo_list}")

# ---------------------------
# AUTO REPLY HANDLER - FIXED
# ---------------------------
async def auto_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    
    # Handle slide targets
    if uid in slide_targets:
        for text in RAID_TEXTS[:3]:
            await update.message.reply_text(text)
            await asyncio.sleep(0.1)
    
    # Handle slidespam targets
    if uid in slidespam_targets:
        for text in RAID_TEXTS:
            await update.message.reply_text(text)
            await asyncio.sleep(0.05)

# ---------------------------
# BOT SETUP
# ---------------------------
def build_app(token):
    app = Application.builder().token(token).build()
    
    # Core commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ready", ready_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("status", status_cmd))
    
    # Name changer commands
    app.add_handler(CommandHandler("ncloop", ncloop))
    app.add_handler(CommandHandler("ncemo", ncemo))
    app.add_handler(CommandHandler("ncbaap", ncbaap))
    app.add_handler(CommandHandler("stopncloop", stopncloop))
    app.add_handler(CommandHandler("stopncemo", stopncemo))
    app.add_handler(CommandHandler("stopncbaap", stopncbaap))
    app.add_handler(CommandHandler("stopall", stopall))
    app.add_handler(CommandHandler("delay", delay_cmd))
    
    # exonc commands
    app.add_handler(CommandHandler("exonc", exonc))
    app.add_handler(CommandHandler("exoncfast", exoncfast))
    app.add_handler(CommandHandler("exoncgodspeed", exoncgodspeed))
    app.add_handler(CommandHandler("stopexonc", stopexonc))
    
    # Spam commands
    app.add_handler(CommandHandler("spam", spam))
    app.add_handler(CommandHandler("unspam", unspam))
    
    # React commands
    app.add_handler(CommandHandler("emojispam", emojispam))
    app.add_handler(CommandHandler("stopemojispam", stopemojispam))
    
    # Slide commands
    app.add_handler(CommandHandler("targetslide", targetslide))
    app.add_handler(CommandHandler("stopslide", stopslide))
    app.add_handler(CommandHandler("slidespam", slidespam))
    app.add_handler(CommandHandler("stopslidespam", stopslidespam))
    
    # Sticker commands
    app.add_handler(CommandHandler("newsticker", newsticker))
    app.add_handler(CommandHandler("delsticker", delsticker))
    app.add_handler(CommandHandler("multisticker", multisticker))
    app.add_handler(CommandHandler("stickerstatus", stickerstatus))
    app.add_handler(CommandHandler("stopstickers", stopstickers))
    app.add_handler(CommandHandler("startstickers", startstickers))
    
    # Voice commands
    app.add_handler(CommandHandler("animevn", animevn))
    app.add_handler(CommandHandler("tempest", tempest_cmd))
    app.add_handler(CommandHandler("music", music))
    app.add_handler(CommandHandler("clonevn", clonevn))
    app.add_handler(CommandHandler("clonedvn", clonedvn))
    app.add_handler(CommandHandler("voices", voices))
    
    # SUDO management
    app.add_handler(CommandHandler("addsudo", addsudo))
    app.add_handler(CommandHandler("delsudo", delsudo))
    app.add_handler(CommandHandler("listsudo", listsudo))
    
    # Auto replies
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_replies))
    
    return app

async def run_all_bots():
    global apps, bots
    for token in TOKENS:
        if token.strip():
            try:
                app = build_app(token)
                apps.append(app)
                bots.append(app.bot)
                print(f"✅ Bot initialized: {token[:10]}...")
            except Exception as e:
                print(f"❌ Failed building app: {e}")

    # Start all bots
    for app in apps:
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            print(f"🚀 Bot started successfully!")
        except Exception as e:
            print(f"❌ Failed starting app: {e}")

    print(f"🎉 Exorcist V4 Ultra Multi is running with {len(bots)} bots!")
    print("📊 Chat ID:", CHAT_ID)
    print("🤖 Active Bots:", len(bots))
    print("💀 NCBAAP Mode: READY (5 NC in 0.1s)")
    print("👑 GOD SPEED Mode: READY (5 NC in 0.05s)")
    print("🎭 tempest Voices: ✅ ACTIVE WITH YOUR API KEY")
    print("⚡ All Features: ACTIVATED")
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(run_all_bots())
    except KeyboardInterrupt:
        print("\n🛑 Nexa V4 Shutting Down...")
    except Exception as e:
        print(f"❌ Error: {e}")
