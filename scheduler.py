#!/usr/bin/env python3
"""
Adhan scheduler — fires a webhook at each Abu Dhabi prayer time.

Runs on a 5-minute GitHub Actions cron (GitHub's minimum). To get finer
resolution despite that, each invocation LOOPS internally, re-checking every
60 seconds for ~5 minutes. When a prayer is near it sleeps to the exact second
and calls ADHAN_WEBHOOK_URL (a Voice Monkey / Virtual Smart Home trigger that
runs your "play adhan" Alexa routine).

A state file (last_fired.json) prevents firing the same prayer twice per day.
Most runs exit in seconds — the per-minute loop only kicks in near a prayer.
"""

import os
import sys
import json
import time
import datetime
import urllib.request

LAT = os.environ.get("LATITUDE", "24.4539")
LON = os.environ.get("LONGITUDE", "54.3773")
METHOD = os.environ.get("CALC_METHOD", "16")            # 16 = Dubai/UAE, 8 = Gulf
WEBHOOK = os.environ.get("ADHAN_WEBHOOK_URL", "").strip()

ALL_PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
ENABLED = [p.strip() for p in os.environ.get("ADHAN_PRAYERS", ",".join(ALL_PRAYERS)).split(",") if p.strip()]

STATE_FILE = "last_fired.json"
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "300"))  # loop ~5 min per invocation
CHECK_EVERY = 60      # re-check every 60 seconds
LEAD = 75             # within this many secs of a prayer: sleep to exact, then fire
CATCH = 300          # still fire if a prayer was missed up to this many secs ago
ACTIVE = RUN_SECONDS + LEAD  # if nothing is within this window at start, exit fast


def dubai_now():
    # Dubai is a fixed UTC+4 offset, no DST.
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)


def fetch_times(ddmmyyyy):
    url = (
        f"https://api.aladhan.com/v1/timings/{ddmmyyyy}"
        f"?latitude={LAT}&longitude={LON}&method={METHOD}&timezonestring=Asia/Dubai"
    )
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)["data"]["timings"]


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def fire_webhook():
    req = urllib.request.Request(WEBHOOK, headers={"User-Agent": "adhan-scheduler"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def target_for(prayer, timings, ref):
    """Datetime today (Dubai) for a prayer's HH:mm."""
    h, m = map(int, str(timings[prayer]).strip()[:5].split(":"))
    return ref.replace(hour=h, minute=m, second=0, microsecond=0)


def main():
    if not WEBHOOK:
        print("ERROR: ADHAN_WEBHOOK_URL secret is not set.")
        sys.exit(1)

    start = dubai_now()
    today = start.strftime("%Y-%m-%d")
    timings = fetch_times(start.strftime("%d-%m-%Y"))

    state = load_state()
    if state.get("date") != today:
        state = {"date": today, "fired": []}

    def pending():
        return [p for p in ALL_PRAYERS if p in ENABLED and p not in state["fired"]]

    # Fast exit: if no pending prayer is within [-CATCH, ACTIVE] right now,
    # there's nothing to wait for this run.
    now = dubai_now()
    near = any(
        -CATCH <= (target_for(p, timings, now) - now).total_seconds() <= ACTIVE
        for p in pending()
    )
    if not near:
        print("Nothing near. Today:", today,
              "| times:", {p: str(timings[p])[:5] for p in ALL_PRAYERS},
              "| fired:", state["fired"])
        return

    # Per-minute loop for ~RUN_SECONDS.
    deadline = time.monotonic() + RUN_SECONDS
    while True:
        now = dubai_now()
        for p in pending():
            delta = (target_for(p, timings, now) - now).total_seconds()
            if -CATCH <= delta <= LEAD:
                if delta > 0:
                    print(f"{p} at {str(timings[p])[:5]} — sleeping {int(delta)}s to exact time")
                    time.sleep(delta)
                print(f"Firing Adhan webhook for {p}")
                try:
                    print("  webhook HTTP", fire_webhook())
                    state["fired"].append(p)
                    save_state(state)
                except Exception as e:
                    print("  webhook error:", e)
        if not pending() or time.monotonic() >= deadline:
            break
        time.sleep(CHECK_EVERY)

    print("Done. Today:", today,
          "| times:", {p: str(timings[p])[:5] for p in ALL_PRAYERS},
          "| fired:", state["fired"])


if __name__ == "__main__":
    main()
