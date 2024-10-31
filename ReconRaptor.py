import aiohttp
import asyncio
import os
import time
import random
from stem import Signal
from stem.control import Controller
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style, init

# Initialize colorama for color output
init(autoreset=True)

# ASCII Art and Introduction
def print_intro():
    os.system('clear')  # Clear screen
    print(Fore.BLUE + r"""


  _____                      _____             _             
 |  __ \                    |  __ \           | |            
 | |__) |___  ___ ___  _ __ | |__) |__ _ _ __ | |_ ___  _ __ 
 |  _  // _ \/ __/ _ \| '_ \|  _  // _` | '_ \| __/ _ \| '__|
 | | \ \  __/ (_| (_) | | | | | \ \ (_| | |_) | || (_) | |   
 |_|  \_\___|\___\___/|_| |_|_|  \_\__,_| .__/ \__\___/|_|   
                                        | |                  
                                        |_|                  

  
""")
    time.sleep(0.5)
    print(Fore.MAGENTA + "Developed by: Dr. Aubrey W. Love II (AKA Rogue Payload)")
    time.sleep(0.5)
    print(Fore.GREEN + "ReconRaptor: Advanced payload injector and domain reconnaissance tool.")
    time.sleep(0.5)
    print(Fore.YELLOW + "Testing Proxies...")

# File paths for our data
DOMAINS_FILE = "domains.txt"
PAYLOADS_FILE = "payloads.txt"
USERAGENTS_FILE = "useragents.txt"
RESULTS_FILE = "hacked.txt"
PROXIES_FILE = "proxies.txt"

# Tor setup
TOR_PROXY = 'socks5h://127.0.0.1:9050'
controller = Controller.from_port(port=9051)

def init_tor():
    try:
        controller.authenticate()  # Assumes no password is set in torrc for control port
        print("[INFO] Tor connection authenticated.")
    except:
        print(Fore.RED + "[ERROR] Tor authentication failed. Ensure Tor is running.")

def renew_tor_ip():
    controller.signal(Signal.NEWNYM)
    time.sleep(5)

def load_file(filename):
    try:
        with open(filename, 'r') as file:
            return [line.strip() for line in file if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        print(Fore.RED + f"[ERROR] File not found: {filename}")
        return []

# Rotate user agents and proxies for each request
def get_random_user_agent(user_agents):
    return random.choice(user_agents)

def get_next_proxy(proxies, current_proxy_index):
    if not proxies:
        return None, -1
    next_index = (current_proxy_index + 1) % len(proxies)
    proxy_url = f'socks5://{proxies[next_index]}' if proxies[next_index] else None
    return proxy_url, next_index

async def check_proxy(proxy, session):
    try:
        test_url = "https://www.google.com"
        async with session.get(test_url, proxy=proxy, timeout=5) as response:
            return response.status == 200
    except:
        return False

async def test_proxies(proxies):
    async with aiohttp.ClientSession() as session:
        active_proxies = []
        for proxy in proxies:
            proxy_url = f'socks5://{proxy}'
            if await check_proxy(proxy_url, session):
                active_proxies.append(proxy)
                print(Fore.GREEN + f"[INFO] Proxy {proxy_url} is active.")
            else:
                print(Fore.RED + f"[WARNING] Proxy {proxy_url} is inactive.")
        return active_proxies

async def fetch_url(session, url, payload, user_agent, proxy):
    headers = {"User-Agent": user_agent}
    try:
        async with session.get(url, headers=headers, proxy=proxy, timeout=10) as response:
            if response.status == 200:
                text = await response.text()
                return text
    except Exception as e:
        print(f"[ERROR] {url} - {e}")
    return None

async def test_payloads(domain, payloads, user_agents, proxies):
    async with aiohttp.ClientSession() as session:
        proxy_index = -1
        for payload in payloads:
            url = f"https://{domain}/{payload}"
            user_agent = get_random_user_agent(user_agents)
            proxy, proxy_index = get_next_proxy(proxies, proxy_index)

            while proxy:
                if await check_proxy(proxy, session):
                    print(Fore.GREEN + f"[INFO] Using proxy {proxy} for {url}")
                    break
                else:
                    print(Fore.YELLOW + f"[INFO] Proxy {proxy} failed. Trying next proxy...")
                    proxy, proxy_index = get_next_proxy(proxies, proxy_index)

            print(Fore.YELLOW + f"[INFO] Testing payload: {payload} on {domain}")
            before_content = await fetch_url(session, url, "", user_agent, proxy)
            if not before_content:
                continue

            injected_url = f"{url}/{payload}"
            after_content = await fetch_url(session, injected_url, payload, user_agent, proxy)

            if after_content and before_content != after_content:
                print(Fore.GREEN + f"[SUCCESS] Potential vulnerability found on {url} with payload {payload}")
                with open(RESULTS_FILE, "a") as result_file:
                    result_file.write(f"URL: {url}\nPayload: {payload}\n--- Before ---\n{before_content[:500]}\n--- After ---\n{after_content[:500]}\n{'-'*50}\n")

            user_agent = get_random_user_agent(user_agents)
            proxy, proxy_index = get_next_proxy(proxies, proxy_index)

async def main():
    print_intro()

    domains = load_file(DOMAINS_FILE)
    payloads = load_file(PAYLOADS_FILE)
    user_agents = load_file(USERAGENTS_FILE)
    proxies = load_file(PROXIES_FILE)

    init_tor()

    active_proxies = await test_proxies(proxies)
    print(Fore.GREEN + f"Total Number of Proxies I can use: {len(active_proxies)}")
    print(Fore.YELLOW + f"Locked onto {len(domains)} Domains!")

    with ThreadPoolExecutor() as executor:
        futures = []
        for domain in domains:
            futures.append(asyncio.ensure_future(test_payloads(domain, payloads, user_agents, active_proxies)))

        await asyncio.gather(*futures)

    print(Fore.GREEN + "[COMPLETED] All domains and payloads tested.")

if __name__ == "__main__":
    asyncio.run(main())
