#!/usr/bin/env python3
"""Kill attack processes safely, then restart"""
import subprocess, os, time, signal

REPO = "/workspaces/codespaces-blank/123aaaa"
LOG = "/tmp/restart.log"

with open(LOG, "w") as f:
    # Kill only old direct_stresser and attack.py (not this process or SSH)
    r1 = subprocess.run("ps aux | grep direct_stresser | grep -v grep | awk '{print $2}'", shell=True, capture_output=True, text=True)
    for pid in r1.stdout.strip().split("\n"):
        if pid:
            os.kill(int(pid), 9)
            f.write(f"Killed direct_stresser {pid}\n")

    r2 = subprocess.run("ps aux | grep 'python3.*attack.py' | grep -v grep | awk '{print $2}'", shell=True, capture_output=True, text=True)
    for pid in r2.stdout.strip().split("\n"):
        if pid:
            os.kill(int(pid), 9)
            f.write(f"Killed attack.py {pid}\n")

    time.sleep(2)

    for fname in os.listdir(os.path.join(REPO, "logs")):
        os.remove(os.path.join(REPO, "logs", fname))

    logf = open("/tmp/attack_launcher.log", "w")
    p = subprocess.Popen(["python3", os.path.join(REPO, "attack.py")], stdout=logf, stderr=subprocess.STDOUT, cwd=REPO)
    f.write(f"Started attack.py PID {p.pid}\n")
    print("RESTARTED")
