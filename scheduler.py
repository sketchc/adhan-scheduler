#!/usr/bin/env python3
"""
Adhan scheduler — fires a webhook at each Abu Dhabi prayer time.

Run on a frequent cron (every 5 min). Each run:
  1. fetches today's prayer times from AlAdhan (Dubai/UAE method 16),
  2. if a prayer falls inside the firing window, sleeps to the exact minute,
  3. calls ADHAN_WEBHOOK_URL (a Voice Monkey / Virtual Smart Home trigger that
     runs your "play adhan" Alexa routine).

A small state file (last_fired.json) prevents firing the same prayer twice.
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
# Comma-separated list of prayers to play the Adhan for. Default: all five.
ENABLED = [p.strip() for p in os.environ.get("ADHAN_PRAYERS", ",".join(ALL_PRAYERS)).split(",") if p.strip()]

STATE_FILE = "last_fired.json"
LEAD = 290    # may fire up to ~4.8 min early (sleeps to the exact time)
CATCH = 290   # may fire up to ~4.8 min late (covers a skipped/delayed run)


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


def main():
    if not WEBHOOK:
        print("ERROR: ADHAN_WEBHOOK_URL secret is not set.")
        sys.exit(1)

    now = dubai_now()
    today = now.strftime("%Y-%m-%d")
    timings = fetch_times(now.strftime("%d-%m-%Y"))

    state = load_state()
    if state.get("date") != today:
        state = {"date": today, "fired": []}

    for prayer in ALL_PRAYERS:
        if prayer not in ENABLED or prayer in state["fired"]:
            continue
        hhmm = str(timings[prayer]).strip()[:5]
        h, m = map(int, hhmm.split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta = (target - now).total_seconds()

        if -CATCH <= delta <= LEAD:
            if delta > 0:
                print(f"{prayer} at {hhmm} — sleeping {int(delta)}s until exact time")
                time.sleep(delta)
            print(f"Firing Adhan webhook for {prayer} ({hhmm})")
            try:
                print("  webhook HTTP", fire_webhook())
            except Exception as e:
                print("  webhook error:", e)
                continue
            state["fired"].append(prayer)

    save_state(state)
    print("Today:", today, "| times:", {p: str(timings[p])[:5] for p in ALL_PRAYERS},
          "| fired:", state["fired"])


if __name__ == "__main__":
    main()
