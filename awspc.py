import time
import pyautogui
import threading
from queue import Queue
import requests
import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Replace with your bot token
TOKEN = '7636057735:AAG1gkwcj9sDNzuhKZPsjfiq4W0QamuSDow'

# Replace with your Telegram user ID (owner)
OWNER_ID = 5926435353  # Set your actual user ID here

# Authorized users set (in memory, add persistence if needed)
authorized_users = set()

updater = Application.builder().token(TOKEN).build()

# Globals
profile_index = 0
phone_index = 0
address_index = 0
postal_index = 0
running = False
input_queue = Queue()
cancel_flag = False  # Added for global cancel

# Profiles data
profiles = [
    {
        "name": "Himanshu Pandya",
        "dob": "19860929",
        "pan": "CILPP5462N",
        "image_pos": (842, 214)
    },
    {
        "name": "Basanti Singh",
        "dob": "19940101",
        "pan": "EHNPB8786A",
        "image_pos": (848, 198)
    },
    {
        "name": "Patel Naresh",
        "dob": "19741116",
        "pan": "AQDPP0397G",
        "image_pos": (841, 236)
    },
    {
        "name": "Rojivadiya Rakesh",
        "dob": "19800101",
        "pan": "AXQPR6743Q",
        "image_pos": (850, 260)
    }
]

phones_list = ["7499318341", "9892201762", "7066436781", "9922246664", "9307520831"]
addresses_list = ["Vanothapada near pond", "Waliv station road", "Grand road mumbai", "bilalpada road", "navjivan road"]
postals_list = ["401208", "401209", "400050", "400058", "400001", "400028"]

EMAIL, PHONE, UPI = range(3)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# ========== GLOBAL CANCEL COMMAND ==========
async def global_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global cancel_flag, running

    user_id = update.effective_user.id

    # 🔐 Authorization check (same as /aws)
    if user_id != OWNER_ID and user_id not in authorized_users:
        await update.message.reply_text("You are not authorised to use dm @spyther to get access ❌")
        return

    if not running:
        await update.message.reply_text("No automation is currently running.")
        return

    cancel_flag = True
    input_queue.put("/CANCEL_COMMAND")

    await update.message.reply_text("Cancelling automation... 🚫")

# ========== VALIDATION FUNCTIONS ==========
def is_valid_email(email: str) -> bool:
    """Check if email contains @ symbol"""
    return '@' in email and len(email) > 3

def is_valid_upi(upi: str) -> bool:
    """Check if UPI contains @ symbol"""
    return '@' in upi and len(upi) > 3

def is_valid_phone(phone: str) -> bool:
    """Check if phone is in international format (+ followed by digits)"""
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone))

def is_valid_keyword(input_text: str, expected_keywords: str) -> bool:
    """Check if input is a valid keyword (done/right/skip)"""
    if not expected_keywords:
        return False
    
    # Extract the actual keywords from the expected text
    keywords = [kw.strip().lower() for kw in expected_keywords.split('/') if kw.strip()]
    return input_text.lower() in keywords

def is_valid_otp(otp: str) -> bool:
    """Check if OTP contains only digits"""
    return otp.isdigit()

# ========== MODIFIED MESSAGE HANDLER WITH VALIDATIONS ==========
async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    
    # Check for cancel command
    if user_input.strip() == '/cancel':
        await global_cancel(update, context)
        return ConversationHandler.END
    
    # Email validation
    if not is_valid_email(user_input):
        await update.message.reply_text("invalid email send proper email")
        return EMAIL
    
    context.user_data['email'] = user_input
    await update.message.reply_text('Enter your no in this format +919876543210 or for poland country +489876543210 📱')
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    
    # Check for cancel command
    if user_input.strip() == '/cancel':
        await global_cancel(update, context)
        return ConversationHandler.END
    
    # Phone validation
    if not is_valid_phone(user_input):
        await update.message.reply_text("invalid format please enter in proper format")
        return PHONE
    
    context.user_data['verify_phone'] = user_input
    await update.message.reply_text('Enter upi id 💳')
    return UPI

async def upi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text
    
    # Check for cancel command
    if user_input.strip() == '/cancel':
        await global_cancel(update, context)
        return ConversationHandler.END
    
    # UPI validation
    if not is_valid_upi(user_input):
        await update.message.reply_text("invalid upi id")
        return UPI
    
    context.user_data['upi'] = user_input
    global input_queue, running, cancel_flag
    input_queue = Queue()
    running = True
    cancel_flag = False  # Reset cancel flag
    chat_id = update.effective_chat.id
    t = threading.Thread(target=run_automation, args=(TOKEN, chat_id, context.user_data.copy()))
    t.start()
    await update.message.reply_text('Automation starting in 3 seconds. Switch to your browser screen now. 🚀')
    return ConversationHandler.END

# ========== MODIFIED AUTOMATION FUNCTION WITH CANCEL CHECKS ==========
def run_automation(token, chat_id, user_data):
    global running, cancel_flag
    
    def check_cancel():
        """Check if cancel was requested"""
        if cancel_flag:
            # Execute cancel code exactly as specified
            click(1143, 50)
            time.sleep(3.832)
            send_text("automation has stopped !")
            running = False
            raise SystemExit(0)  # Stop the thread
    
    def safe_sleep(seconds):
        """Sleep with cancel checking"""
        interval = 0.5  # Check every 0.5 seconds
        remaining = seconds
        while remaining > 0:
            time.sleep(min(interval, remaining))
            remaining -= interval
            check_cancel()
    
    def safe_get():
        """Get from queue with cancel checking"""
        while True:
            try:
                # Check for cancel before getting
                check_cancel()
                
                # Try to get with timeout to allow cancel checking
                try:
                    item = input_queue.get(timeout=0.5)
                except:
                    continue
                
                # Check if it's the cancel command
                if item == "/CANCEL_COMMAND":
                    click(1143, 50)
                    time.sleep(3.832)
                    send_text("automation has stopped !")
                    running = False
                    raise SystemExit(0)
                
                return item
            except SystemExit:
                raise
            except:
                continue
    
    running = True
    cancel_flag = False
    profile = user_data['profile']
    email = user_data['email']
    verify_phone = user_data['verify_phone']
    upi = user_data['upi']
    address_phone = user_data['address_phone']
    address_str = user_data['address']
    postal_code = user_data['postal']
    password = 'Spyther@786'
    raw_digits = ''.join(c for c in verify_phone if c.isdigit())

    if verify_phone.startswith('+91'):
        verify_phone_num = raw_digits[-10:]   # India = 10 digits
    elif verify_phone.startswith('+48'):
        verify_phone_num = raw_digits[-9:]    # Poland = 9 digits
    else:
        verify_phone_num = raw_digits

    def send_text(text):
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text})
        except Exception as e:
            print(f"Send text error: {e}")

    def send_screenshot(caption):
        try:
            pyautogui.screenshot('temp.png')
            time.sleep(2)
            with open('temp.png', 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': chat_id, 'caption': caption}
                requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", files=files, data=data)
        except Exception as e:
            print(f"Send screenshot error: {e}")
        finally:
            if os.path.exists('temp.png'):
                os.remove('temp.png')

    def click(x, y):
        pyautogui.moveTo(x, y)
        pyautogui.click()

    def handle_email_captcha():
        send_screenshot("Email verification clicked - check for captcha 🔍")
        send_text("Did you see captcha in this image? If yes, send captcha text. If no captcha popup, send 'skip' ❓")
        
        while True:
            first_resp = safe_get()
            
            # Check for cancel
            check_cancel()
            
            if is_valid_keyword(first_resp, "skip"):
                send_text("Skipped captcha ⏭️")
                return
            else:
                # User sent something, assume it's captcha text
                captcha = first_resp
                send_text("Entered captcha 🔑")
                click(408, 658)
                safe_sleep(16.89)
                pyautogui.typewrite(captcha)
                safe_sleep(3.97)
                pyautogui.press('enter')
                safe_sleep(1)
                pyautogui.press('enter')
                safe_sleep(1)
                safe_sleep(1)
                safe_sleep(10.009)
                send_screenshot("Captcha submitted - check result")
                send_text("See your captcha result: if right send 'right', if not send 'new' ✅/❌")
                
                while True:
                    verdict = safe_get().lower()
                    check_cancel()
                    
                    if is_valid_keyword(verdict, "right"):
                        send_text("Captcha correct! ✅")
                        return
                    elif verdict == 'new':
                        break
                    else:
                        send_text(f"invalid please send (right / new)")
                        continue
                
                # Handle new captcha
                click(828, 557)
                safe_sleep(8.084)
                send_screenshot("New captcha loaded 🔄")
                send_text("Enter captcha 🔑")
                captcha = safe_get()
                check_cancel()
                send_text("Entered captcha 🔑")
                click(379, 655)
                safe_sleep(8.005)
                pyautogui.typewrite(captcha)
                safe_sleep(3.97)
                pyautogui.press('enter')
                safe_sleep(1)
                pyautogui.press('enter')
                safe_sleep(1)
                safe_sleep(1)
                safe_sleep(10.009)
                send_screenshot("New captcha submitted - check result")
                send_text("See your captcha result: if right send 'right', if not send 'new' ✅/❌")

    def handle_email_otp():
        send_text("Enter email OTP 📧")
        
        while True:
            otp = safe_get()
            check_cancel()
            
            if is_valid_otp(otp):
                send_text("Entered OTP ✅")
                click(683, 652)
                safe_sleep(8.709)
                pyautogui.typewrite(otp)
                safe_sleep(2.837)
                click(746, 710)
                safe_sleep(4.205)
                return
            else:
                send_text("invalid otp please enter valid otp")

    def handle_mobile_captcha():
        send_screenshot("SMS sent - check for captcha 🔍")
        send_text("See captcha in this image and send captcha 🔑")
        
        while True:
            captcha = safe_get()
            check_cancel()
            
            # Accept any input for captcha (as per requirements, don't modify captcha flow)
            break
        
        send_text("Entered captcha 🔑")
        click(408, 658)
        safe_sleep(16.89)
        pyautogui.typewrite(captcha)
        safe_sleep(3.97)
        pyautogui.press('enter')
        safe_sleep(1)
        pyautogui.press('enter')
        safe_sleep(1)
        safe_sleep(1)
        safe_sleep(10.009)
        send_screenshot("Captcha submitted - check result")
        send_text("See your captcha result: if right send 'right', if not send 'new' ✅/❌")
        
        while True:
            verdict = safe_get().lower()
            check_cancel()
            
            if is_valid_keyword(verdict, "right"):
                send_text("Captcha correct! ✅")
                return
            elif verdict == 'new':
                break
            else:
                send_text(f"invalid please send (right / new)")
                continue
        
        # Handle new captcha
        click(828, 557)
        safe_sleep(5.084)
        send_screenshot("New captcha loaded 🔄")
        send_text("Enter captcha 🔑")
        
        while True:
            captcha = safe_get()
            check_cancel()
            break
        
        send_text("Entered captcha 🔑")
        click(379, 655)
        safe_sleep(8.005)
        pyautogui.typewrite(captcha)
        safe_sleep(3.97)
        pyautogui.press('enter')
        safe_sleep(1)
        pyautogui.press('enter')
        safe_sleep(1)
        safe_sleep(1)
        safe_sleep(10.009)
        send_screenshot("New captcha submitted - check result")
        send_text("See your captcha result: if right send 'right', if not send 'new' ✅/❌")
        
        while True:
            verdict = safe_get().lower()
            check_cancel()
            
            if is_valid_keyword(verdict, "right"):
                send_text("Captcha correct! ✅")
                return
            else:
                send_text(f"invalid please send (right / new)")
                continue

    def handle_mobile_otp():
        send_text("Enter SMS OTP 📱")
        
        while True:
            otp = safe_get()
            check_cancel()
            
            if is_valid_otp(otp):
                send_text("Entered OTP ✅")
                click(816, 548)
                safe_sleep(20.023)
                pyautogui.typewrite(otp)
                safe_sleep(2.51)
                click(749, 605)
                safe_sleep(7.959)
                return
            else:
                send_text("invalid otp please enter valid otp")

    try:
        # Determine country for verification
        if verify_phone.startswith('+91'):
            country_type_str = 'india'
            country_click_x, country_click_y = 668, 612
            country_sleep_after_type = 9.024
            country_sleep_after_click = 5.726
            country_arrow_x, country_arrow_y = 893, 646
            country_sleep_after_arrow = 10.783
        else:
            country_type_str = 'poland'
            country_click_x, country_click_y = 676, 615
            country_sleep_after_type = 6.667
            country_sleep_after_click = 4.627
            country_arrow_x, country_arrow_y = 895, 647
            country_sleep_after_arrow = 5.098

        # Start automation
        check_cancel()
        safe_sleep(3.6)
        
        # Clicked brave
        click(77, 534)
        send_screenshot("Clicked Brave browser 🌐")
        safe_sleep(0.0)
        
        # Click brave 2nd time
        pyautogui.press('enter')
        safe_sleep(6.892)
        pyautogui.typewrite('aws.com')
        pyautogui.press('enter')
        safe_sleep(4.8)
        send_screenshot("Navigated to aws.com 🏠")
        
        # Create account
        pyautogui.click(980, 250)
        safe_sleep(4.905)
        send_screenshot("Clicked Create account ➕")
        
        # Input email
        click(699, 528)
        safe_sleep(8.879)
        pyautogui.typewrite(email)
        safe_sleep(2.94)
        send_screenshot("Entered email 📧")
        
        # Input account name
        click(706, 632)
        safe_sleep(5.989)
        pyautogui.typewrite(profile['name'])
        safe_sleep(4.100)
        send_screenshot("Entered account name 👤")
        
        # Verify email address
        click(775, 690)
        safe_sleep(12.198)
        handle_email_captcha()
        
        # Input verification code email otp
        handle_email_otp()
        send_screenshot("Email verified ✅")
        
        # Input password
        click(746, 710)
        safe_sleep(2.015)
        pyautogui.typewrite(password)
        safe_sleep(2.013)
        send_screenshot("Entered password 🔒")
        
        # Input password again
        click(910, 784)
        safe_sleep(2.218)
        pyautogui.typewrite(password)
        safe_sleep(2.538)
        send_screenshot("Confirmed password 🔒")
        
        # Continue
        click(747, 860)
        safe_sleep(8.368)
        send_screenshot("Continued to next step ➡️")
        
        # Save info
        click(855, 394)
        safe_sleep(0.001)
        click(855, 394)
        send_screenshot("Saved info 💾")
        
        # Choose paid
        click(807, 1014)
        safe_sleep(25.031)
        send_screenshot("Selected paid plan 💰")
        
        # Click personal
        click(631, 601)
        safe_sleep(13.705)
        send_screenshot("Selected personal use 👤")
        
        # Full name
        click(654, 710)
        safe_sleep(1.861)
        pyautogui.typewrite(profile['name'])
        safe_sleep(1.900)
        send_screenshot("Entered full name 👤")
        
        # Country arrow
        click(715, 780)
        safe_sleep(2.927)
        pyautogui.typewrite('india')
        safe_sleep(4.081)
        
        # Click india
        click(670, 747)
        safe_sleep(4.531)
        send_screenshot("Selected country India 🇮🇳")
        
        # Input phone no
        click(768, 782)
        safe_sleep(5.737)
        pyautogui.typewrite(address_phone)
        safe_sleep(13.432)
        send_screenshot("Entered address phone 📱")
        
        # Click country arrow again
        click(894, 854)
        safe_sleep(5.97)
        pyautogui.typewrite('india')
        safe_sleep(5.319)
        
        # Click india again
        click(716, 822)
        safe_sleep(5.747)
        send_screenshot("Reselected billing country 🇮🇳")
        
        # Input address line
        click(661, 917)
        safe_sleep(6.715)
        pyautogui.typewrite(address_str)
        safe_sleep(12.698)
        send_screenshot("Entered address 🏠")
        
        # Click down arrow multiple times
        for _ in range(17):
            click(1152, 1052)
            safe_sleep(0.0)
            check_cancel()
        safe_sleep(6.29)
        
        # Input city
        click(697, 410)
        safe_sleep(4.209)
        pyautogui.typewrite('Mumbai')
        safe_sleep(4.722)
        send_screenshot("Entered city 🏙️")
        
        # Input state
        click(668, 488)
        safe_sleep(4.656)
        pyautogui.typewrite('Maharashtra')
        safe_sleep(3.4)
        send_screenshot("Entered state 🗺️")
        
        # Input postal code
        click(682, 562)
        safe_sleep(23.618)
        pyautogui.typewrite(postal_code)
        safe_sleep(5.96)
        send_screenshot("Entered postal code 📮")
        
        # Click tos check box
        click(624, 696)
        safe_sleep(5.389)
        send_screenshot("Checked TOS ✅")
        
        # Click agree and continue
        click(745, 757)
        safe_sleep(7.423)
        send_screenshot("Agreed and continued ➡️")
        
        # Click save address
        click(842, 467)
        safe_sleep(21.309)
        send_screenshot("Saved address 💾")
        
        # Few click
        click(1003, 650)
        safe_sleep(8.954)
        
        # Click down arrow multiple
        for i in range(3):
            click(1152, 1046)
            check_cancel()
            safe_sleep(8.352 if i == 2 else 0.0)
        
        # Input upi id
        click(759, 425)
        safe_sleep(29.554)
        pyautogui.typewrite(upi)
        safe_sleep(4.356)
        send_screenshot("Entered UPI ID 💳")
        
        # Click verify and continue
        click(738, 775)
        safe_sleep(13.993)
        send_screenshot("Clicked verify UPI 🔍")
        
        # Click verify
        click(801, 688)
        safe_sleep(40.882)  # wait for payment
        send_screenshot("Clicked payment verify 💳")
        send_text("Have you done your payment? If done, send 'done' ❓")
        
        while True:
            done_input = safe_get().lower()
            check_cancel()
            
            if is_valid_keyword(done_input, "done"):
                send_text("Payment done! ✅")
                safe_sleep(15)
                break
            else:
                send_text(f"invalid please send (done)")
        
        # Click I'd verification option arrow
        click(880, 569)
        safe_sleep(8.051)
        send_screenshot("Opened ID verification 🆔")
        
        # Click personal use
        click(687, 701)
        safe_sleep(6.567)
        
        # Click ownership type
        click(878, 686)
        safe_sleep(5.948)
        
        # Click individual
        click(672, 617)
        safe_sleep(8.048)
        send_screenshot("Selected individual 👤")
        
        # Input dob
        click(661, 924)
        safe_sleep(25.371)
        pyautogui.typewrite(profile['dob'])
        safe_sleep(8.194)
        send_screenshot("Entered DOB 🎂")
        
        # Click down arrow
        for i in range(3):
            click(1150, 1047)
            check_cancel()
            safe_sleep(11.57 if i == 2 else 0.0)
        
        # Click name checkbox
        click(636, 305)
        safe_sleep(7.716)
        send_screenshot("Checked name verification ✅")
        
        # Input enter pan account no
        click(693, 399)
        safe_sleep(32.166)
        pyautogui.typewrite(profile['pan'])
        safe_sleep(5.96)
        send_screenshot("Entered PAN 🆔")
        
        # Click choose file
        click(684, 541)
        safe_sleep(10.183)
        
        # Click image
        click(*profile['image_pos'])
        safe_sleep(6.239)
        send_screenshot("Selected PAN image 📸")
        
        # Click select
        click(1659, 927)
        safe_sleep(12.604)
        
        # Click checkbox toc
        click(637, 714)
        safe_sleep(5.422)
        
        # Click continue
        click(751, 817)
        safe_sleep(7.953)
        send_screenshot("Uploaded PAN and continued ➡️")
        
        # Click country arrow for mobile
        click(country_arrow_x, country_arrow_y)
        safe_sleep(country_sleep_after_arrow)
        pyautogui.typewrite(country_type_str)
        safe_sleep(country_sleep_after_type)
        
        # Click country
        click(country_click_x, country_click_y)
        safe_sleep(country_sleep_after_click)
        send_screenshot("Selected verification country 🌍")
        
        # Input mob no
        click(689, 717)
        safe_sleep(20.021)
        pyautogui.typewrite(verify_phone_num)
        safe_sleep(2.95)
        send_screenshot("Entered mobile number 📱")
        
        # Click send sms
        click(750, 774)
        safe_sleep(6.68)
        handle_mobile_captcha()
        
        # Input verify code
        handle_mobile_otp()
        send_screenshot("Mobile verified ✅")

        # Confirm
        click(822, 622)
        safe_sleep(6.915)
        
        # Click complete sign up
        click(557, 1030)
        safe_sleep(15.379)
        send_screenshot("Completed signup 🎉")
        
        # Click go to AWS management console
        click(222, 731)
        safe_sleep(13.223)
        
        # Click ec2
        click(188, 619)
        safe_sleep(13.261)
        send_screenshot("Reached EC2 console ☁️")
        
        # Click x close browser finish
        click(1143, 50)
        safe_sleep(3.832)
        send_screenshot("Automation finished 🏁")
        send_text("Successfully made AWS account ✅\nYour account pass: Spyther@786 🔑")
        
    except SystemExit:
        # Clean exit on cancel
        pass
    except Exception as e:
        print(f"Automation error: {e}")
    finally:
        running = False
        cancel_flag = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to Spyther's AWS account creating bot ✅\nType /help to see available commands 📋")

async def help_com(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
Available Commands:

/start - Welcome message 🌟
/help - Show this help ℹ️
/aws - Start AWS account creation (authorized users only) ☁️
/cancel - Cancel current automation (works anywhere) 🚫
/add <user_id> - Add authorized user (admin only) ➕
/remove <user_id> - Remove authorized user (admin only) ➖
/users - List authorized users (admin only) 👥
    """
    await update.message.reply_text(help_text)

async def add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("You are not an admin ❌")
        return
    if not context.args:
        await update.message.reply_text("Usage: /add <user_id> ➕")
        return
    try:
        uid = int(context.args[0])
        authorized_users.add(uid)
        await update.message.reply_text(f"Added user {uid} ✅")
    except ValueError:
        await update.message.reply_text("Invalid user_id ❌")

async def remove_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("You are not an admin ❌")
        return
    if not context.args:
        await update.message.reply_text("Usage: /remove <user_id> ➖")
        return
    try:
        uid = int(context.args[0])
        if authorized_users.discard(uid):
            await update.message.reply_text(f"Removed user {uid} ✅")
        else:
            await update.message.reply_text(f"User {uid} not found ❌")
    except ValueError:
        await update.message.reply_text("Invalid user_id ❌")

async def users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("You are not an admin ❌")
        return
    if not authorized_users:
        await update.message.reply_text("No authorized users 👥")
    else:
        user_list = ", ".join(map(str, authorized_users))
        await update.message.reply_text(f"Authorized users: {user_list} 👥")

async def aws_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id != OWNER_ID and user_id not in authorized_users:
        await update.message.reply_text("You are not authorised to use this bot. To get access, DM @spyther ❌")
        return ConversationHandler.END
    global running
    if running:
        await update.message.reply_text("A task is already running. Please wait, try after 10-15 mins ⏳")
        return ConversationHandler.END
    global profile_index, phone_index, address_index, postal_index
    profile = profiles[profile_index]
    profile_index = (profile_index + 1) % len(profiles)
    address_phone = phones_list[phone_index]
    phone_index = (phone_index + 1) % len(phones_list)
    address_str = addresses_list[address_index]
    address_index = (address_index + 1) % len(addresses_list)
    postal_code = postals_list[postal_index]
    postal_index = (postal_index + 1) % len(postals_list)
    context.user_data.update({
        'profile': profile,
        'address_phone': address_phone,
        'address': address_str,
        'postal': postal_code
    })
    await update.message.reply_text('Enter email 📧')
    return EMAIL

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Cancelled. ❌')
    return ConversationHandler.END

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global running, input_queue
    if running:
        input_queue.put(update.message.text)
    else:
        await update.message.reply_text('Use /aws to begin. ☁️')

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('aws', aws_start)],
    states={
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
        UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, upi)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

updater.add_handler(conv_handler)
updater.add_handler(CommandHandler('start', start))
updater.add_handler(CommandHandler('help', help_com))
updater.add_handler(CommandHandler('cancel', global_cancel))  # Global cancel handler
updater.add_handler(CommandHandler('add', add_handler))
updater.add_handler(CommandHandler('remove', remove_handler))
updater.add_handler(CommandHandler('users', users_handler))
updater.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

if __name__ == '__main__':
    updater.run_polling()