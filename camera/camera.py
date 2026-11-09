"""
IoT camera simulator.
Pretends to be the gate camera: every few seconds it "reads" a plate
and sends it to the API with an HTTP POST - exactly like the real camera.
Sometimes it also sends an exit for a car that is inside.
Uses only the standard library (no pip install needed).
"""
import json
import os
import random
import time
import urllib.error
import urllib.request

API_URL = os.getenv("API_URL", "http://api:5000/api")
INTERVAL = float(os.getenv("INTERVAL_SECONDS", "3"))

inside = []  # plates this simulator sent in


def post(url, body=None):
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def random_plate():
    length = random.choice([7, 8])
    return "".join(random.choice("0123456789") for _ in range(length))


def main():
    print(f"[camera] sending to {API_URL} every {INTERVAL}s", flush=True)
    while True:
        try:
            if inside and random.random() < 0.3:
                plate = inside.pop(random.randrange(len(inside)))
                status, body = post(f"{API_URL}/cars/{plate}/exit")
                print(f"[camera] EXIT  {plate} -> {status} {body}", flush=True)
            else:
                plate = random_plate()
                status, body = post(f"{API_URL}/cars", {"plate": plate})
                if status == 201:
                    inside.append(plate)
                print(f"[camera] ENTRY {plate} -> {status} {body}", flush=True)
        except (urllib.error.URLError, ConnectionError) as e:
            print(f"[camera] API not reachable: {e}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
