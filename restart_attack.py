#!/usr/bin/env python3
"""Kill all attack processes and restart"""
import subprocess, os, time, signal

REPO = "/workspaces/codespaces-blank/123aaaa"

subprocess.run("pkill -f direct_stresser", shell=True)
subprocess.run("pkill -f 'attack.py'", shell=True)
time.sleep(2)

for f in os.listdir(os.path.join(REPO, "logs")):
    os.remove(os.path.join(REPO, "logs", f))

log = open("/tmp/attack_launcher.log", "w")
subprocess.Popen(
    ["python3", os.path.join(REPO, "attack.py")],
    stdout=log, stderr=subprocess.STDOUT,
    cwd=REPO
)
print("ATTACK RESTARTED")
