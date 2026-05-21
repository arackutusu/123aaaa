"""
Minecraft Server Stress Tester - Capacity Finder
For testing YOUR OWN server's limits - measures when performance degrades
"""
import socket, time, threading, sys
from colorama import init, Fore
init(autoreset=True)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
BASE_THREADS = 25      # Start conservative
TEST_DURATION = 15     # Seconds per step
THREAD_INCREMENT = 25  # How much to increase each step
MAX_THREADS = 300      # Absolute safety stop
SUCCESS_THRESHOLD = 0.8 # Below 80% success = distress
LATENCY_THRESHOLD = 1.0 # Seconds - above this = laggy

# ─── STATS TRACKING ───────────────────────────────────────────────────────────
class ConnectionStats:
    def __init__(self):
        self.success = 0
        self.fail = 0
        self.total_latency = 0.0
        self.latency_count = 0
        self.lock = threading.Lock()
    
    def add_result(self, success, latency):
        with self.lock:
            if success:
                self.success += 1
                self.total_latency += latency
                self.latency_count += 1
            else:
                self.fail += 1
    
    def get_rates(self):
        with self.lock:
            total = self.success + self.fail
            success_rate = self.success / max(total, 1)
            avg_latency = self.total_latency / max(self.latency_count, 1)
            return self.success, self.fail, success_rate, avg_latency

stats = ConnectionStats()

# ─── NETWORK TESTER ───────────────────────────────────────────────────────────
def connection_worker(ip, port, stop_event):
    """Worker that attempts connections and measures latency"""
    while not stop_event.is_set():
        start = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(2.0)
            s.connect((ip, port))
            s.close()
            elapsed = time.time() - start
            stats.add_result(True, elapsed)
        except Exception:
            stats.add_result(False, 0.0)
        finally:
            try: s.close()
            except: pass

# ─── TEST PROCEDURE ───────────────────────────────────────────────────────────
def run_stress_test():
    """Gradually increase load until server shows distress"""
    print("[🔬] Minecraft Server Capacity Finder")
    print(f"[🎯] Target: {TARGET_IP}:{TARGET_PORT}")
    print("[ℹ️] Finds maximum sustainable connection rate\n")
    
    # Initial connectivity check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((TARGET_IP, TARGET_PORT))
        s.close()
        print("[✅] Server reachable\n")
    except Exception as e:
        print(f"[❌] Cannot connect: {e}")
        return
    
    thread_count = BASE_THREADS
    test_round = 1
    max_sustainable = 0
    
    try:
        while thread_count <= MAX_THREADS:
            # Reset stats for this round
            global stats
            stats = ConnectionStats()
            stop_event = threading.Event()
            workers = []
            
            print(f"[🧪] Round {test_round}: {thread_count} threads for {TEST_DURATION}s")
            
            # Start workers
            for _ in range(thread_count):
                w = threading.Thread(
                    target=connection_worker, 
                    args=(TARGET_IP, TARGET_PORT, stop_event), 
                    daemon=True
                )
                w.start()
                workers.append(w)
            
            # Monitor test
            start_time = time.time()
            try:
                while time.time() - start_time < TEST_DURATION:
                    elapsed = time.time() - start_time
                    succ, fail, success_rate, avg_latency = stats.get_rates()
                    
                    # Calculate current rate
                    current_rate = succ / max(elapsed, 0.1)
                    
                    # Status line
                    status = "🟢" if success_rate >= SUCCESS_THRESHOLD else "🔴"
                    latency_status = "⚡" if avg_latency < LATENCY_THRESHOLD else "🐌"
                    
                    print(f"\r[⏱️] {elapsed:.0f}s | {status} {succ}/{succ+fail} ({success_rate*100:.0f}%) | "
                          f"{latency_status} {avg_latency:.2f}s latency | "
                          f"📈 {current_rate:.0f}/s | "
                          f"🎯 Target: {thread_count} threads", 
                          end="", flush=True)
                    time.sleep(0.3)
            except KeyboardInterrupt:
                print("\n[!] Test interrupted")
                stop_event.set()
                break
            
            # End of round
            stop_event.set()
            for w in workers:
                w.join(timeout=1)
            
            succ, fail, success_rate, avg_latency = stats.get_rates()
            print(f"\n[📊] Result: {succ} success, {fail} fail "
                  f"({success_rate*100:.0f}% success, {avg_latency:.2f}s avg latency)")
            
            # Check if this round was sustainable
            if success_rate >= SUCCESS_THRESHOLD and avg_latency <= LATENCY_THRESHOLD:
                max_sustainable = thread_count
                print(f"[✅] Sustainable at {thread_count} threads")
            else:
                print(f"[⚠️] Distress detected at {thread_count} threads")
                print(f"[📉] Success rate dropped below {SUCCESS_THRESHOLD*100:.0f}% or "
                      f"latency exceeded {LATENCY_THRESHOLD}s")
                break
            
            thread_count += THREAD_INCREMENT
            test_round += 1
            
    except KeyboardInterrupt:
        print("\n[!] Test stopped by user")
    
    # Final report
    print(f"\n[🏁] TEST COMPLETE")
    if max_sustainable > 0:
        print(f"[🎯] MAX SUSTAINABLE LOAD: {max_sustainable} concurrent connection attempts")
        print(f"[💡] This is approximately your server's connection handling capacity")
        print(f"[📝] For gameplay: estimate {max_sustainable//10} - {max_sustainable//5} players")
        print(f"[🛡️] Recommendation: Stay below {max_sustainable*0.7:.0f} threads for safety margin")
    else:
        print(f"[❌] Even {BASE_THREADS} threads caused distress")
        print(f"[💡] Server may be underpowered or misconfigured")
    
    print(f"\n[⚠️] IMPORTANT: This measures connection attempt rate,")
    print(f"    not actual gameplay load. Real players generate less")
    print(f"    network traffic but more CPU load (world interaction, AI, etc.)")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def run_tester():
    """Main tester logic"""
    print("[🔬] Minecraft Server Capacity Finder")
    print(f"[🎯] Target: {TARGET_IP}:{TARGET_PORT}")
    print("[ℹ️] Finds maximum sustainable connection rate\n")
    
    # Initial connectivity check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((TARGET_IP, TARGET_PORT))
        s.close()
        print("[✅] Server reachable\n")
    except Exception as e:
        print(f"[❌] Cannot connect: {e}")
        return
    
    thread_count = BASE_THREADS
    test_round = 1
    max_sustainable = 0
    
    try:
        while thread_count <= MAX_THREADS:
            # Reset stats for this round
            global stats
            stats = ConnectionStats()
            stop_event = threading.Event()
            workers = []
            
            print(f"[🧪] Round {test_round}: {thread_count} threads for {TEST_DURATION}s")
            
            # Start workers
            for _ in range(thread_count):
                w = threading.Thread(
                    target=connection_worker, 
                    args=(TARGET_IP, TARGET_PORT, stop_event), 
                    daemon=True
                )
                w.start()
                workers.append(w)
            
            # Monitor test
            start_time = time.time()
            try:
                while time.time() - start_time < TEST_DURATION:
                    elapsed = time.time() - start_time
                    succ, fail, success_rate, avg_latency = stats.get_rates()
                    
                    # Calculate current rate
                    current_rate = succ / max(elapsed, 0.1)
                    
                    # Status line
                    status = "🟢" if success_rate >= SUCCESS_THRESHOLD else "🔴"
                    latency_status = "⚡" if avg_latency < LATENCY_THRESHOLD else "🐌"
                    
                    print(f"\r[⏱️] {elapsed:.0f}s | {status} {succ}/{succ+fail} ({success_rate*100:.0f}%) | "
                          f"{latency_status} {avg_latency:.2f}s latency | "
                          f"📈 {current_rate:.0f}/s | "
                          f"🎯 Target: {thread_count} threads", 
                          end="", flush=True)
                    time.sleep(0.3)
            except KeyboardInterrupt:
                print("\n[!] Test interrupted")
                stop_event.set()
                break
            
            # End of round
            stop_event.set()
            for w in workers:
                w.join(timeout=1)
            
            succ, fail, success_rate, avg_latency = stats.get_rates()
            print(f"\n[📊] Result: {succ} success, {fail} fail "
                  f"({success_rate*100:.0f}% success, {avg_latency:.2f}s avg latency)")
            
            # Check if this round was sustainable
            if success_rate >= SUCCESS_THRESHOLD and avg_latency <= LATENCY_THRESHOLD:
                max_sustainable = thread_count
                print(f"[✅] Sustainable at {thread_count} threads")
            else:
                print(f"[⚠️] Distress detected at {thread_count} threads")
                print(f"[📉] Success rate dropped below {SUCCESS_THRESHOLD*100:.0f}% or "
                      f"latency exceeded {LATENCY_THRESHOLD}s")
                break
            
            thread_count += THREAD_INCREMENT
            test_round += 1
            
    except KeyboardInterrupt:
        print("\n[!] Test stopped by user")
    
    # Final report
    print(f"\n[🏁] TEST COMPLETE")
    if max_sustainable > 0:
        print(f"[🎯] MAX SUSTAINABLE LOAD: {max_sustainable} concurrent connection attempts")
        print(f"[💡] This is approximately your server's connection handling capacity")
        print(f"[📝] For gameplay: estimate {max_sustainable//10} - {max_sustainable//5} players")
        print(f"[🛡️] Recommendation: Stay below {max_sustainable*0.7:.0f} threads for safety margin")
    else:
        print(f"[❌] Even {BASE_THREADS} threads caused distress")
        print(f"[💡] Server may be underpowered or misconfigured")
    
    print(f"\n[⚠️] IMPORTANT: This measures connection attempt rate,")
    print(f"    not actual gameplay load. Real players generate less")
    print(f"    network traffic but more CPU load (world interaction, AI, etc.)")

def main():
    """Entry point with exception handling"""
    try:
        run_tester()
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
    except Exception as e:
        print(f"[❌] Fatal error: {e}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main_worker()
