import asyncio
import json
from urllib.parse import quote_plus
import nodriver as uc
from main import get_random_proxy

async def get_ip(args=None):
    browser = await uc.start(headless=True, args=args or [])
    tab = await browser.get("https://api.ipify.org?format=json")
    await asyncio.sleep(1)
    content = await tab.evaluate("document.body.innerText")
    await browser.close()
    return json.loads(content).get("ip")

async def main():
    print("Testing without proxy...")
    ip_no = await get_ip()
    print(f"IP without proxy: {ip_no}")
    
    proxy_line = get_random_proxy("proxies.txt")
    if not proxy_line:
        print("No proxy found in proxies.txt")
        return
    host, port, user, pwd = proxy_line.split(":", 3)
    proxy_url = f"http://{user}:{quote_plus(pwd)}@{host}:{port}"
    print(f"Testing with proxy {host}:{port}...")
    ip_proxy = await get_ip(args=[f"--proxy-server={proxy_url}"])
    print(f"IP with proxy: {ip_proxy}")

if __name__ == "__main__":
    asyncio.run(main())
