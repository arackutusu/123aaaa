import socket
hosts = [("5.133.100.33", 25600), ("5.133.100.33", 25660), ("play.furymine.com", 25565)]
for h, p in hosts:
    try:
        s = socket.socket(); s.settimeout(3); s.connect((h, p)); s.close()
        print(f"[OK] {h}:{p}")
    except Exception as e:
        print(f"[FAIL] {h}:{p} - {e}")
