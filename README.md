# Adhan Scheduler

GitHub Actions cron that plays the Adhan on an Amazon Echo at each Abu Dhabi prayer
time. Times are fetched daily from [AlAdhan](https://aladhan.com) (method 16 = Dubai/UAE).

It works by calling a **webhook** that triggers an Alexa Routine — so **no Amazon
password or cookies are stored here**, only a webhook token.

## How it works

```
GitHub Actions (every 5 min)
   → fetch today's prayer times (AlAdhan)
   → at a prayer time, GET your ADHAN_WEBHOOK_URL
        → Voice Monkey / Virtual Smart Home triggers your Alexa Routine
             → routine runs "ask Prayer Alarm to play the adhan" → Adhan plays
```

## Setup

### 1. Get a webhook that triggers a routine
Use a free, Alexa-certified bridge skill (pick one):

- **Voice Monkey** — https://voicemonkey.io
  1. Sign up, enable the **Voice Monkey** skill in the Alexa app, link your account.
  2. Create a "monkey" (trigger device) and note your **trigger URL**, e.g.
     `https://api-v2.voicemonkey.io/trigger?token=ACCESS_SECRET&device=adhan`
- **Virtual Smart Home** — https://www.virtualsmarthome.xyz/url_routine_trigger
  1. Enable the skill, create a trigger, copy its **"URL to switch ON"**.

### 2. Create the Alexa Routine
In the Alexa app → **Routines → ＋**:
- **When:** the Voice Monkey / Virtual Smart Home device is triggered
- **Action → Custom:** `ask Prayer Alarm to play the adhan`
- **Device:** your Echo → **Save**

(Test the webhook URL in a browser — your Echo should play the Adhan.)

### 3. Add the secret to this repo
**Settings → Secrets and variables → Actions → New repository secret:**
- Name: `ADHAN_WEBHOOK_URL`
- Value: the full trigger URL from step 1

### 4. Done
The workflow runs automatically. Trigger it once manually to test:
**Actions → Adhan scheduler → Run workflow**.

## Options
Set as workflow env (see [`.github/workflows/adhan.yml`](.github/workflows/adhan.yml)):
- `CALC_METHOD` — `16` (Dubai/UAE, default) or `8` (Gulf Region)
- `ADHAN_PRAYERS` — e.g. `Fajr,Maghrib` to play only some prayers (default: all five)
- `LATITUDE` / `LONGITUDE` — defaults are Abu Dhabi city centre

## ⚠️ Limitations
- **Timing is best-effort.** GitHub's cron can be delayed several minutes or
  occasionally skip a run, so the Adhan may be a few minutes late. Not guaranteed
  punctual — don't rely on it as your sole prayer-time source.
- GitHub **pauses scheduled workflows after 60 days** of no repo activity; the state
  commits keep it active, but if it ever stops, push any commit to re-enable.
- Uses third-party webhook bridges; if that service changes, update the URL.
