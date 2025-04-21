import os
import asyncio
import requests
import random
import datetime
import names
import csv
import string
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

import nodriver as uc
from nodriver import *

# Placeholder for your DaisySMS API key and service code
DAISY_API_KEY = os.getenv("DAISY_API_KEY", "YOUR_DAISY_API_KEY")
DAISY_SERVICE = os.getenv("DAISY_SERVICE", "service_code_here")

DELAY_FACTOR = float(os.getenv("DELAY_FACTOR", "1.0"))
CATCHALL_DOMAIN = os.getenv("CATCHALL_DOMAIN")
ENV_RECOVERY_EMAIL = os.getenv("RECOVERY_EMAIL")

async def apply_delay(duration):
    """Sleep scaled by DELAY_FACTOR"""
    await asyncio.sleep(duration * DELAY_FACTOR)

class DaisySMS:
    BASE_URL = "https://daisysms.com/stubs/handler_api.php"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_balance(self) -> float:
        resp = requests.get(self.BASE_URL, params={
            "api_key": self.api_key,
            "action": "getBalance"
        })
        if resp.ok and resp.text.startswith("ACCESS_BALANCE"):
            return float(resp.text.split(":")[1])
        raise RuntimeError(f"Error getting balance: {resp.text}")

    def get_number(self, service: str, max_price: float = 1.0):
        resp = requests.get(self.BASE_URL, params={
            "api_key": self.api_key,
            "action": "getNumber",
            "service": service,
            "max_price": max_price
        })
        if resp.ok and resp.text.startswith("ACCESS_NUMBER"):
            _, session_id, number = resp.text.strip().split(":")
            return session_id, number
        raise RuntimeError(f"Error getting number: {resp.text}")

    def get_status(self, session_id: str) -> str:
        resp = requests.get(self.BASE_URL, params={
            "api_key": self.api_key,
            "action": "getStatus",
            "id": session_id
        })
        return resp.text.strip()

    def cancel_number(self, session_id: str):
        requests.get(self.BASE_URL, params={
            "api_key": self.api_key,
            "action": "setStatus",
            "status": 8,
            "id": session_id
        })

async def human_type(element, text, min_delay=0.05, max_delay=0.2):
    for char in text:
        await element.send_keys(char)
        await apply_delay(random.uniform(min_delay, max_delay))

async def random_sleep(min_delay=0.1, max_delay=0.35):
    """Sleep a random interval for human-like pacing scaled by DELAY_FACTOR"""
    await apply_delay(random.uniform(min_delay, max_delay))

async def start_browser_with_proxy(headless=False):
    proxy_line = get_random_proxy()
    args = []
    if proxy_line:
        host, port, user, pwd = proxy_line.split(":", 3)
        from urllib.parse import quote_plus
        proxy_url = f"http://{user}:{quote_plus(pwd)}@{host}:{port}"
        args.append(f"--proxy-server={proxy_url}")
        logger.info(f"Using proxy {host}:{port}")
    else:
        logger.info("No proxy found in proxies.txt")

    config = uc.Config()
    config.headless = headless
    # Fallback to default if Brave not installed
    brave_path = os.getenv("BRAVE_PATH", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
    if os.path.exists(brave_path):
        config.browser_executable_path = brave_path
    else:
        logger.info(f"Brave binary not found at {brave_path}, using default browser")
    if args:
        config.args = args
    browser = await uc.start(config=config)
    return browser

async def fill_name(tab, first, last):
    first_input = await safe_select(tab, "input[name='firstName']", "fill_name firstName")
    await safe_click(first_input, "fill_name firstName click")
    await random_sleep()
    try:
        await safe_type(first_input, first, "fill_name firstName type")
    except Exception:
        # JS fallback: set value directly without typing
        await first_input.evaluate(f"el => {{ el.value = '{first}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
    await random_sleep()
    last_input = await safe_select(tab, "input[name='lastName']", "fill_name lastName")
    await safe_click(last_input, "fill_name lastName click")
    await random_sleep()
    try:
        await safe_type(last_input, last, "fill_name lastName type")
    except Exception:
        await last_input.evaluate(f"el => {{ el.value = '{last}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
    await random_sleep()
    next_btn = await safe_select(tab, "button[jsname='LgbsSe']", "fill_name next")
    await safe_click(next_btn, "fill_name next click")
    await random_sleep()

async def fill_dob_gender(tab):
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    year = random.randint(datetime.date.today().year - 50, datetime.date.today().year - 18)
    # Month
    await tab.evaluate(
        f"(sel => {{ sel.value = '{month}'; sel.dispatchEvent(new Event('change', {{ bubbles: true }})); }})(document.querySelector('select#month'));"
    )
    await random_sleep()
    # Day
    day_input = await safe_select(tab, "input#day", "fill_dob_gender day")
    await safe_click(day_input, "fill_dob_gender day click")
    await random_sleep()
    await safe_type(day_input, str(day), "fill_dob_gender day type")
    await random_sleep()
    # Year
    year_input = await safe_select(tab, "input#year", "fill_dob_gender year")
    await safe_click(year_input, "fill_dob_gender year click")
    await random_sleep()
    await safe_type(year_input, str(year), "fill_dob_gender year type")
    await random_sleep()
    # Gender
    gender_map = {"Female": "2", "Male": "1", "Rather not say": "3"}
    gender = random.choice(list(gender_map.values()))
    await tab.evaluate(
        f"(sel => {{ sel.value = '{gender}'; sel.dispatchEvent(new Event('change', {{ bubbles: true }})); }})(document.querySelector('select#gender'));"
    )
    await random_sleep()
    next_btn2 = await safe_select(tab, "button[jsname='LgbsSe']", "fill_dob_gender next")
    await safe_click(next_btn2, "fill_dob_gender next click")
    await random_sleep()

async def fill_username(tab, email):
    try:
        btn = await safe_find(tab, "Create your own Gmail address", "fill_username customAddrBtn")
        await safe_click(btn, "fill_username customAddrBtn click")
        await random_sleep()
    except Exception:
        pass
    username = email.split("@")[0]
    input_el = await safe_select(tab, "input[name='Username']", "fill_username input")
    await safe_click(input_el, "fill_username input click")
    await random_sleep()
    await safe_type(input_el, username, "fill_username type")
    await random_sleep()
    btn3 = await safe_select(tab, "button[jsname='LgbsSe']", "fill_username next")
    await safe_click(btn3, "fill_username next click")
    await random_sleep()
    # Check if username is already taken
    if await tab.evaluate("document.body.innerText.includes('That username is taken. Try another.')"):
        raise RuntimeError("fill_username - username taken")

async def fill_password(tab, password):
    p1 = await safe_select(tab, "input[name='Passwd']", "fill_password first")
    await safe_click(p1, "fill_password first click")
    await random_sleep()
    await safe_type(p1, password, "fill_password first type")
    await random_sleep()
    p2 = await safe_select(tab, "input[name='PasswdAgain']", "fill_password confirm")
    await safe_click(p2, "fill_password confirm click")
    await random_sleep()
    await safe_type(p2, password, "fill_password confirm type")
    await random_sleep()
    btn4 = await safe_select(tab, "button[jsname='LgbsSe']", "fill_password next")
    await safe_click(btn4, "fill_password next click")
    await apply_delay(0.5 * DELAY_FACTOR)

async def handle_phone_verification(tab, daisysms):
    logger.info("starting phone verification")
    import re
    interval = 5
    while True:
        logger.info("requesting new number")
        try:
            session, number = daisysms.get_number(DAISY_SERVICE)
        except Exception as e:
            logger.warning(f"Error getting number: {e}. Retrying new number...")
            await apply_delay(random.uniform(1, 3))
            continue
        logger.info(f"got number: {number}, session: {session}")
        inp = await safe_select(tab, "#phoneNumberId", "phone_verif input")
        await safe_click(inp, "phone_verif input click")
        await random_sleep()
        await safe_type(inp, number, "phone_verif type")
        await random_sleep()
        btn5 = await safe_select(tab, "button[jsname='LgbsSe']", "phone_verif send")
        await safe_click(btn5, "phone_verif send click")
        logger.info("number sent, checking unusable")
        await random_sleep()
        
        try:
            await apply_delay(1)
            err = await safe_select(tab, "div.o6cuMc", "phone_verif error")
            if "cannot be used for verification" in (await err.evaluate("el => el.textContent")):
                logger.info("number unusable, cancelling session")
                daisysms.cancel_number(session)
                await random_sleep()
                continue
        except:
            pass
        
        logger.info("polling for code")
        code = None
        waited = 0
        while waited < 60:
            st = daisysms.get_status(session)
            logger.info(f"poll status: {st}")
            m = re.search(r"\b(\d{6})\b", st)
            if m:
                code = m.group(1)
                logger.info(f"received code: {code}")
                break
            await apply_delay(interval)
            waited += interval
        if not code:
            logger.warning("Phone verification timed out, restarting account creation")
            daisysms.cancel_number(session)
            raise RuntimeError("SMS verification timed out")

        logger.info("entering verification code")
        ci = await safe_select(tab, "input#code", "phone_verif code input")
        await safe_click(ci, "phone_verif code click")
        await random_sleep()
        await safe_type(ci, code, "phone_verif code type")
        await random_sleep()
        nb6 = await safe_select(tab, "button[jsname='LgbsSe']", "phone_verif next")
        await safe_click(nb6, "phone_verif next click")
        logger.info("code submitted, verification step complete")
        await random_sleep()
        break

async def fill_recovery_email(tab, recovery):
    if not recovery:
        logger.info("No recovery email provided, skipping this step.")
        try:
            skip_btn = await safe_find(tab, "Skip", "fill_recovery skip")
        except:
            skip_btn = await safe_select(tab, "//button[.//span[contains(text(),'Skip')]]", "fill_recovery skip fallback")
        await safe_click(skip_btn, "fill_recovery skip click")
        await random_sleep()
        return
        
    rec = await safe_select(tab, "input#recoveryEmailId", "fill_recovery input")
    await safe_click(rec, "fill_recovery input click")
    await random_sleep()
    await safe_type(rec, recovery, "fill_recovery type")
    try:
        nxt = await safe_find(tab, "Next", "fill_recovery next")
    except Exception:
        await random_sleep()
        nxt = await safe_select(tab, "button[jsname='LgbsSe']", "fill_recovery next fallback")
    await apply_delay(2)
    await safe_click(nxt, "fill_recovery next click")
    await apply_delay(2)
    

async def accept_terms(tab):
    n8 = await safe_select(tab, "button[jsname='LgbsSe']", "accept_terms next")
    await safe_click(n8, "accept_terms next click")
    await random_sleep()
    try:
        ag = await safe_find(tab, "I agree", "accept_terms agree")
        await safe_click(ag, "accept_terms agree click")
        await random_sleep()
    except:
        pass
    try:
        cf = await safe_find(tab, "Confirm", "accept_terms confirm")
        await safe_click(cf, "accept_terms confirm click")
        await random_sleep()
    except:
        pass

async def create_gmail_account(email_to_create, recovery_email, first_name_value, last_name_value, password):
    logger.info(f"[create] Starting account creation for {email_to_create}")
    browser = await start_browser_with_proxy(headless=False)
    tab = await browser.get("https://accounts.google.com/signup")
    sms_client = DaisySMS(DAISY_API_KEY)
    try:
        logger.info("fill_name")
        await fill_name(tab, first_name_value, last_name_value)
        logger.info("fill_dob_gender")
        await fill_dob_gender(tab)
        logger.info("fill_username")
        await fill_username(tab, email_to_create)
        logger.info("fill_password")
        await fill_password(tab, password)
        logger.info("handle_phone_verification")
        await handle_phone_verification(tab, sms_client)
        logger.info("fill_recovery_email")
        await fill_recovery_email(tab, recovery_email)
        logger.info("accept_terms")
        await accept_terms(tab)
        logger.info("applying final delay")
        await apply_delay(5)
    finally:
        await tab.close()
        try:
            await browser.close()
        except Exception:
            pass

async def safe_select(tab, selector, name):
    try:
        return await tab.select(selector)
    except Exception as e:
        raise RuntimeError(f"{name} - selector {selector} failed: {e}")

async def safe_find(tab, text, name):
    try:
        return await tab.find(text)
    except Exception as e:
        raise RuntimeError(f"{name} - find '{text}' failed: {e}")

async def safe_click(el, name):
    try:
        await el.click()
        await random_sleep()
    except Exception as e:
        raise RuntimeError(f"{name} - click failed: {e}")

async def safe_type(el, text, name):
    try:
        await el.evaluate("el => el.focus()")
    except Exception:
        pass
    try:
        await human_type(el, text)
    except Exception as e:
        # Fallback: set value via JS if typing fails (avoids focus issues)
        try:
            await el.evaluate(f"el => {{ el.value = '{text}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
        except Exception:
            raise RuntimeError(f"{name} - typing '{text}' failed: {e}")
    await random_sleep(0.05, 0.2)

def read_gmail_csv(csv_path):
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def write_gmail_csv(csv_path, rows):
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_random_proxy(file="proxies.txt"):
    try:
        with open(file, "r") as pf:
            lines = [l.strip() for l in pf if l.strip()]
        return random.choice(lines)
    except Exception:
        return None

if __name__ == "__main__":
    csv_path = "gmails_to_create.csv"
    rows = read_gmail_csv(csv_path)
    changed = False
    
    i = 0
    while i < len(rows):
        row = rows[i]
        email = row.get("Email", "").strip()
        status = row.get("Status", "").strip().lower()
        
        if not email or status in ("yes", "no"):
            i += 1
            continue
        
        first_name = names.get_first_name()
        last_name = names.get_last_name()
        
        if ENV_RECOVERY_EMAIL:
            recovery_addr = ENV_RECOVERY_EMAIL
        elif CATCHALL_DOMAIN:
            recovery_addr = f"recovery{random.randint(10000,99999)}@{CATCHALL_DOMAIN}"
        else:
            recovery_addr = None
            
        password = generate_password()
        try:
            result = asyncio.run(create_gmail_account(email, recovery_addr, first_name, last_name, password))
            if result == "retry":
                logger.info(f"Retrying {email}...")
                continue  # retry same row
            row["Status"] = "Yes"
            row["Recovery Address"] = recovery_addr
            row["Password"] = password
            logger.info(f"Successfully created: {email}")
        except RuntimeError as e:
            if "username taken" in str(e):
                row["Status"] = "No"
                row["Recovery Address"] = recovery_addr
                logger.info(f"Username taken: {email}. Marking as No.")
            else:
                logger.info(f"Error creating {email}: {e}. Retrying...")
                continue
        except Exception as e:
            logger.info(f"Error creating {email}: {e}. Retrying...")
            continue
        changed = True
        write_gmail_csv(csv_path, rows)
        i += 1
    if not changed:
        logger.info("No accounts to create or all have already been created.")