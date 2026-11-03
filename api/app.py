"""
Smart Parking Tracker - API server
----------------------------------
POST /api/cars                -> the IoT camera reports a car entering
POST /api/cars/<plate>/exit   -> a car leaves the parking lot
GET  /api/cars                -> the dashboard pulls the current state
GET  /api/health              -> health check (used by Docker + CI)

Data in Redis:
  parking:inside          HASH  plate -> entry time   (cars currently inside)
  parking:log             LIST  JSON events, newest first (last 100)
  parking:total_entries   STRING counter of all entries ever
"""
import json
import os
import re
from datetime import datetime, timezone

import redis
from flask import Flask, jsonify, request

app = Flask(__name__)

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,  # get str instead of bytes
)

CAPACITY = int(os.getenv("PARKING_CAPACITY", "50"))
INSIDE_KEY = "parking:inside"
LOG_KEY = "parking:log"
TOTAL_KEY = "parking:total_entries"
LOG_LIMIT = 100

# Israeli plates: 7 or 8 digits (dashes/spaces are stripped first)
PLATE_RE = re.compile(r"^\d{7,8}$")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_plate(raw):
    return re.sub(r"[\s-]", "", str(raw or ""))


def log_event(pipe, plate, event, ts):
    pipe.lpush(LOG_KEY, json.dumps({"plate": plate, "event": event, "time": ts}))
    pipe.ltrim(LOG_KEY, 0, LOG_LIMIT - 1)  # keep only the newest 100


@app.post("/api/cars")
def car_entry():
    data = request.get_json(silent=True) or {}
    plate = normalize_plate(data.get("plate"))

    if not PLATE_RE.match(plate):
        return jsonify(error="invalid plate - expected 7-8 digits"), 400
    if r.hlen(INSIDE_KEY) >= CAPACITY:
        return jsonify(error="parking lot is full"), 409

    ts = now_iso()
    # HSETNX = set only if the field does not exist -> atomic duplicate check
    if not r.hsetnx(INSIDE_KEY, plate, ts):
        return jsonify(error="car is already inside"), 409

    pipe = r.pipeline()  # send several commands in one round-trip
    log_event(pipe, plate, "entry", ts)
    pipe.incr(TOTAL_KEY)
    pipe.execute()
    return jsonify(plate=plate, entered_at=ts), 201


@app.post("/api/cars/<plate>/exit")
def car_exit(plate):
    plate = normalize_plate(plate)
    if r.hdel(INSIDE_KEY, plate) == 0:
        return jsonify(error="car is not inside"), 404

    pipe = r.pipeline()
    log_event(pipe, plate, "exit", now_iso())
    pipe.execute()
    return jsonify(plate=plate, status="exited"), 200


@app.get("/api/cars")
def get_cars():
    inside = r.hgetall(INSIDE_KEY)
    cars = sorted(
        ({"plate": p, "entered_at": t} for p, t in inside.items()),
        key=lambda c: c["entered_at"],
        reverse=True,
    )
    events = [json.loads(e) for e in r.lrange(LOG_KEY, 0, 19)]
    return jsonify(
        count=len(cars),
        capacity=CAPACITY,
        total_entries=int(r.get(TOTAL_KEY) or 0),
        cars=cars,
        recent_events=events,
    )


@app.get("/api/health")
def health():
    try:
        r.ping()
        return jsonify(status="ok", redis="up"), 200
    except redis.RedisError:
        return jsonify(status="error", redis="down"), 503


if __name__ == "__main__":  # local dev only; in Docker we use gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)
