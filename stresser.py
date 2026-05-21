"""
Legitimate Load Tester for Minecraft Servers
Measures actual server capacity under load - safe for testing your own server
"""
import socket, time, threading, sys
from colorama import init, Fore
init(autoreset=True)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
THREADS = 50          # Fixed thread pool - no overhead from thousands of threads
DURATION = 30         # Seconds per test phase
RAMP_UP_STEP = 10     # Increase threads by this amount each phase
MAX_THREADS = 200     # Absolute safety limit
TIMEOUT = 2.0         # Socket timeout

# ─── STATS ────────────────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.success = 0
        self.fail = 0
        self.lock = threading.Lock()
    
    def add_success(self, n=1):
        with self.lock:
            self.success += n
    
    def add_fail(self, n=1):
        with self.lock:
            self.fail += n
    
    def get(self):
        with self.lock:
            return self.success, self.fail

stats = Stats()

# ─── WORKER ───────────────────────────────────────────────────────────────────
def connect_worker(stop_event, results):
    """Each worker rapidly attempts connections"""
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(TIMEOUT)
            s.connect((TARGET_IP, TARGET_PORT))
            s.close()
            stats.add_success()
        except Exception:
            stats.fail += 1
        finally:
            try: s.close()
            except: pass

# ─── TEST RUNNER ──────────────────────────────────────────────────────────────
def run_test_phase(thread_count, phase_name):
    """Run a test phase with fixed thread count"""
    global stats
    stats = Stats()
    stop_event = threading.Event()
    workers = []
    
    print(f"\n[🧪] {phase_name}: {thread_count} threads, {DURATION}s")
    print("[📊] Monitoring connection rate... (Ctrl+C to skip phase)")
    
    # Start workers
    for _ in range(thread_count):
        w = threading.Thread(target=connect_worker, args=(stop_event, stats), daemon=True)
        w.start()
        workers.append(w)
    
    # Monitor
    start = time.time()
    try:
        while time.time() - start < DURATION and not stop_event.is_set():
            elapsed = time.time() - start
            succ, fail = stats.get()
            rate = succ / max(elapsed, 0.1)
            fail_pct = (fail / max(succ + fail, 1)) * 100
            
            print(f"\r[⏱️] {elapsed:.0f}s | "
                  f"✅ {succ} ({rate:.0f}/s) | "
                  f"❌ {fail} ({fail_pct:.1f}%) | "
                  f"🎯 Target: {thread_count} threads", 
                  end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] Phase skipped")
        stop_event.set()
    
    stop_event.set()
    for w in workers:
        w.join(timeout=1)
    
    succ, fail = stats.get()
    elapsed = time.time() - start
    rate = succ / max(elapsed, 0.1)
    fail_pct = (fail / max(succ + fail, 1)) * 100
    
    print(f"\n[📈] Result: {succ} conn ({rate:.0f}/s), {fail} fails ({fail_pct:.1f}%)")
    return rate, fail_pct

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("[🔬] Minecraft Server Capacity Tester")
    print(f"[🎯] Target: {TARGET_IP}:{TARGET_PORT}")
    print("[ℹ️] Measures actual connection capacity - safe for own server\n")
    
    # Quick connectivity check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((TARGET_IP, TARGET_PORT))
        s.close()
        print("[✅] Connectivity confirmed\n")
    except Exception as e:
        print(f"[❌] Cannot connect to {TARGET_IP}:{TARGET_PORT}: {e}")
        print("[💡] Check: server IP, port, firewall, and that server is running")
        return
    
    # Ramp up test
    thread_count = THREADS
    max_rate = 0
    phase = 1
    
    try:
        while thread_count <= MAX_THREADS:
            rate, fail_pct = run_test_phase(thread_count, f"Phase {phase}")
            
            if rate > max_rate:
                max_rate = rate
            
            # Stop if failure rate too high (server struggling)
            if fail_pct > 50:
                print(f"[⚠️] High failure rate ({fail_pct:.1f}%) - server may be stressed")
                break
                
            # Stop if rate plateaus (we've found capacity)
            if phase > 1 and rate < max_rate * 0.7:
                print(f"[⚠️] Connection rate dropped - likely at capacity")
                break
                
            thread_count += RAMP_UP_STEP
            phase += 1
            print()  # New line for next phase
            
    except KeyboardInterrupt:
        print("\n[!] Test stopped by user")
    
    # Final report
    print(f"\n[🏁] TEST COMPLETE")
    print(f"[📈] Max sustainable rate: {max_rate:.0f} connections/second")
    print(f"[💡] This is approximately the server's connection acceptance capacity")
    print(f"[📝] For reference: 50 players online might generate ~5-15 auth/sec")
    print(f"[🛡️] Stay well below this rate during normal operation to avoid stress")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
    except Exception as e:
        print(f"[❌] Error: {e}")
