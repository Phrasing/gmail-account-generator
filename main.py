import os
import asyncio
import requests
import random
import datetime
import names
import csv
import string
import re
import logging

import nodriver as uc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DAISY_API_KEY = os.getenv("DAISY_API_KEY", "YOUR_DAISY_API_KEY")
DAISY_SERVICE = os.getenv("DAISY_SERVICE", "service_code_here")
DELAY_FACTOR = float(os.getenv("DELAY_FACTOR", "1.0"))
CATCHALL_DOMAIN = os.getenv("CATCHALL_DOMAIN")
RECOVERY_EMAIL = os.getenv("RECOVERY_EMAIL")


async def apply_delay(duration):
    await asyncio.sleep(duration * DELAY_FACTOR)


async def random_sleep(min_delay=0.1, max_delay=0.35):
    await apply_delay(random.uniform(min_delay, max_delay))


async def human_type(element, text, min_delay=0.05, max_delay=0.2):
    for char in text:
        await element.send_keys(char)
        await apply_delay(random.uniform(min_delay, max_delay))


def get_random_proxy(file="proxies.txt"):
    try:
        with open(file, "r") as pf:
            lines = [l.strip() for l in pf if l.strip()]
        return random.choice(lines) if lines else None
    except Exception:
        return None


def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


# SMS verification service
def get_daisy_balance(api_key):
    resp = requests.get(
        "https://daisysms.com/stubs/handler_api.php",
        params={"api_key": api_key, "action": "getBalance"}
    )
    if resp.ok and resp.text.startswith("ACCESS_BALANCE"):
        return float(resp.text.split(":")[1])
    raise RuntimeError(f"Error getting balance: {resp.text}")


def get_daisy_number(api_key, service, max_price=1.0):
    resp = requests.get(
        "https://daisysms.com/stubs/handler_api.php", 
        params={
            "api_key": api_key,
            "action": "getNumber",
            "service": service,
            "max_price": max_price
        }
    )
    if resp.ok and resp.text.startswith("ACCESS_NUMBER"):
        _, session_id, number = resp.text.strip().split(":")
        return session_id, number
    raise RuntimeError(f"Error getting number: {resp.text}")


def get_daisy_status(api_key, session_id):
    resp = requests.get(
        "https://daisysms.com/stubs/handler_api.php",
        params={"api_key": api_key, "action": "getStatus", "id": session_id}
    )
    return resp.text.strip()


def cancel_daisy_number(api_key, session_id):
    requests.get(
        "https://daisysms.com/stubs/handler_api.php",
        params={"api_key": api_key, "action": "setStatus", "status": 8, "id": session_id}
    )


# Browser safe operations
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
    # Focus element before typing
    try:
        await el.evaluate("el => el.focus()")
    except Exception:
        pass
    
    try:
        await human_type(el, text)
    except Exception as e:
        # Fallback: set value via JS if typing fails
        try:
            await el.evaluate(f"el => {{ el.value = '{text}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
        except Exception:
            raise RuntimeError(f"{name} - typing '{text}' failed: {e}")
            
    await random_sleep(0.05, 0.2)


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
    
    # Use Brave if available
    brave_path = os.getenv("BRAVE_PATH", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
    if os.path.exists(brave_path):
        config.browser_executable_path = brave_path
    else:
        logger.info(f"Brave binary not found at {brave_path}, using default browser")
        
    if args:
        config.args = args
        
    return await uc.start(config=config)


# Form filling functions
async def fill_name(tab, first, last):
    first_input = await safe_select(tab, "input[name='firstName']", "fill_name firstName")
    await safe_click(first_input, "fill_name firstName click")
    await random_sleep()
    
    try:
        await safe_type(first_input, first, "fill_name firstName type")
    except Exception:
        # JS fallback
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
    await random_sleep(2, 5)
    
    # Generate random birth date (18-50 years old)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    year = random.randint(datetime.date.today().year - 50, datetime.date.today().year - 18)
    
    # Month dropdown
    await tab.evaluate(
        f"(sel => {{ sel.value = '{month}'; sel.dispatchEvent(new Event('change', {{ bubbles: true }})); }})(document.querySelector('select#month'));"
    )
    await random_sleep()
    
    # Day field
    day_input = await safe_select(tab, "input#day", "fill_dob_gender day")
    await safe_click(day_input, "fill_dob_gender day click")
    await random_sleep()
    await safe_type(day_input, str(day), "fill_dob_gender day type")
    await random_sleep()
    
    # Year field
    year_input = await safe_select(tab, "input#year", "fill_dob_gender year")
    await safe_click(year_input, "fill_dob_gender year click")
    await random_sleep()
    await safe_type(year_input, str(year), "fill_dob_gender year type")
    await random_sleep()
    
    # Gender dropdown
    gender_map = {"Female": "2", "Male": "1", "Rather not say": "3"}
    gender = random.choice(list(gender_map.values()))
    await tab.evaluate(
        f"(sel => {{ sel.value = '{gender}'; sel.dispatchEvent(new Event('change', {{ bubbles: true }})); }})(document.querySelector('select#gender'));"
    )
    await random_sleep()
    
    next_btn = await safe_select(tab, "button[jsname='LgbsSe']", "fill_dob_gender next")
    await safe_click(next_btn, "fill_dob_gender next click")
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
    
    btn = await safe_select(tab, "button[jsname='LgbsSe']", "fill_username next")
    await safe_click(btn, "fill_username next click")
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
    
    btn = await safe_select(tab, "button[jsname='LgbsSe']", "fill_password next")
    await safe_click(btn, "fill_password next click")
    await apply_delay(0.5)


async def handle_phone_verification(tab, api_key):
    logger.info("starting phone verification")
    interval = 5
    
    while True:
        logger.info("requesting new number")
        try:
            session, number = get_daisy_number(api_key, DAISY_SERVICE)
        except Exception as e:
            raise RuntimeError(e)
                            
        logger.info(f"got number: {number}, session: {session}")
        inp = await safe_select(tab, "#phoneNumberId", "phone_verif input")
        await safe_click(inp, "phone_verif input click")
        await random_sleep()
        await safe_type(inp, number, "phone_verif type")
        await random_sleep()
        
        btn = await safe_select(tab, "button[jsname='LgbsSe']", "phone_verif send")
        await safe_click(btn, "phone_verif send click")
        logger.info("number sent, checking unusable")
        await random_sleep()
        
        # Check for immediate number errors
        error_element = None
        try:
            error_element = await tab.select("div.o6cuMc", timeout=3)
        except Exception:
            pass
            
        if error_element:
            error_text = await error_element.evaluate("el => el.textContent")
            if "used too many times" in error_text:
                logger.info(f"Number {number} used too many times; restarting account creation...")
                cancel_daisy_number(api_key, session)
                raise RuntimeError("phone number used too many times")
            if "cannot be used for verification" in error_text:
                logger.info(f"Number {number} rejected by Google. Cancelling session and retrying...")
                cancel_daisy_number(api_key, session)
                await random_sleep()
                continue
                
        logger.info("polling for code")
        code = None
        waited = 0
        
        while waited < 60:
            status = get_daisy_status(api_key, session)
            logger.info(f"poll status: {status}")
            match = re.search(r"\b(\d{6})\b", status)
            if match:
                code = match.group(1)
                logger.info(f"received code: {code}")
                break
            await apply_delay(interval)
            waited += interval
            
        if not code:
            logger.warning("Phone verification timed out, restarting account creation")
            cancel_daisy_number(api_key, session)
            raise RuntimeError("SMS verification timed out")
            
        logger.info("entering verification code")
        code_input = await safe_select(tab, "input#code", "phone_verif code input")
        await safe_click(code_input, "phone_verif code click")
        await random_sleep()
        await safe_type(code_input, code, "phone_verif code type")
        await random_sleep()
        
        next_btn = await safe_select(tab, "button[jsname='LgbsSe']", "phone_verif next")
        await safe_click(next_btn, "phone_verif next click")
        logger.info("code submitted, verification step complete")
        await random_sleep()
        break


async def fill_recovery_email(tab, recovery):
    # Skip recovery email step if none provided
    if not recovery:
        logger.info("No recovery email provided, skipping this step.")
        # Click 'Skip' button
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
        next_btn = await safe_find(tab, "Next", "fill_recovery next")
    except Exception:
        await random_sleep()
        next_btn = await safe_select(tab, "button[jsname='LgbsSe']", "fill_recovery next fallback")
        
    await apply_delay(2)
    await safe_click(next_btn, "fill_recovery next click")
    await apply_delay(2)


async def accept_terms(tab):
    next_btn = await safe_select(tab, "button[jsname='LgbsSe']", "accept_terms next")
    await safe_click(next_btn, "accept_terms next click")
    await random_sleep()
    
    try:
        agree_btn = await safe_find(tab, "I agree", "accept_terms agree")
        await safe_click(agree_btn, "accept_terms agree click")
        await random_sleep()
    except:
        pass
        
    try:
        confirm_btn = await safe_find(tab, "Confirm", "accept_terms confirm")
        await safe_click(confirm_btn, "accept_terms confirm click")
        await random_sleep()
    except:
        pass


async def create_gmail_account(email_to_create, recovery_email, first_name, last_name, password):
    logger.info(f"[create] Starting account creation for {email_to_create}")
    browser = await start_browser_with_proxy(headless=False)
    tab = await browser.get("https://accounts.google.com/signup")
    
    try:
        logger.info("fill_name")
        await fill_name(tab, first_name, last_name)
        
        logger.info("fill_dob_gender")
        await fill_dob_gender(tab)
        
        logger.info("fill_username")
        await fill_username(tab, email_to_create)
        
        logger.info("fill_password")
        await fill_password(tab, password)
        
        logger.info("handle_phone_verification")
        await handle_phone_verification(tab, DAISY_API_KEY)
        
        logger.info("fill_recovery_email")
        await fill_recovery_email(tab, recovery_email)
        
        logger.info("accept_terms")
        await accept_terms(tab)
        
        logger.info("applying final delay")
        await apply_delay(5)
        return "success"
    except Exception as e:
        return str(e)
    finally:
        try:
            await tab.close()
            await browser.close()
        except:
            pass


def read_gmail_csv(csv_path):
    rows = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
    return rows


def write_gmail_csv(csv_path, rows):
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        logger.error(f"Error writing CSV: {e}")


def main():
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
            
        # Generate random names and recovery address
        first_name = names.get_first_name()
        last_name = names.get_last_name()
        
        if RECOVERY_EMAIL:
            recovery_addr = RECOVERY_EMAIL
        elif CATCHALL_DOMAIN:
            recovery_addr = f"recovery{random.randint(10000,99999)}@{CATCHALL_DOMAIN}"
        else:
            recovery_addr = None
            
        password = generate_password()
        
        try:
            result = asyncio.run(create_gmail_account(
                email, recovery_addr, first_name, last_name, password
            ))
            
            if result == "retry":
                logger.info(f"Retrying {email}...")
                continue  
            
            if result == "success":
                row["Status"] = "Yes"
                row["Recovery Address"] = recovery_addr
                row["Password"] = password
                logger.info(f"Successfully created: {email}")
            else:
                error_msg = result.lower()
                
                if "username taken" in error_msg:
                    row["Status"] = "No"
                    row["Recovery Address"] = recovery_addr
                    logger.warning(f"Username taken: {email}. Marking as No.")
                elif "sms verification timed out" in error_msg or "phone number used too many times" in error_msg:
                    row["Status"] = "Skipped"
                    logger.error(f"Skipping {email} due to phone error: {result}")
                elif "no_money" in error_msg:
                    logger.error("Insufficient Funds in daisySMS. Stopping.")
                    break
                else:
                    logger.error(f"Error creating {email}: {result}. Retrying...")
                    continue
        except Exception as e:
            logger.error(f"Error creating {email}: {e}. Retrying...")
            continue
        
        changed = True
        write_gmail_csv(csv_path, rows)
        i += 1
        
    if not changed:
        logger.info("No accounts to create or all have already been created.")


if __name__ == "__main__":
    main()