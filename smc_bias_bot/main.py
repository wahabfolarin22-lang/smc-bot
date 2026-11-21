import json, os, time
from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo
import data, notify
import structure as st
import messages as ms
from config import *

LONDON = ZoneInfo("Europe/London")
STATE_FILE = "state.json"

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}

def save_state(s):
    json.dump(s, open(STATE_FILE, "w"), indent=1)

def in_window(now):
    return now.weekday() < 5 and dtime(*WINDOW_START) <= now.time() <= dtime(*WINDOW_END)

def fresh(ps, key, now, hours=None):
    t = ps["alerts"].get(key)
    return t is None or now - datetime.fromisoformat(t) > timedelta(hours=hours or ALERT_COOLDOWN_HOURS)

def mark(ps, key, now):
    ps["alerts"][key] = now.isoformat()

def process(pair, i, now, today, state, force, fetch=data.candles):
    """Returns True if data was fetched and analysed, False if the fetch failed."""
    ps = state.setdefault(pair, {"last_brief": "", "h4_dir": None, "zone": None, "alerts": {}})
    h4, h1, m15 = (fetch(pair, "H4", BARS["H4"]), fetch(pair, "H1", BARS["H1"]),
                   fetch(pair, "M15", BARS["M15"]))
    if h4 is None or h1 is None or m15 is None:
        print(f"[{pair}] data fetch failed, skipping")
        return False
    price = float(m15["close"].iloc[-1])
    a = st.analyze(h4, h1, price)

    # 1) daily brief, one pair per BRIEF_GAP_MIN, starting at BRIEF_START (London time)
    slot = now.replace(hour=BRIEF_START[0], minute=BRIEF_START[1], second=0, microsecond=0) \
        + timedelta(minutes=BRIEF_GAP_MIN * i)
    if force or (ps["last_brief"] != today and now >= slot):
        notify.send(ms.brief(pair, a, price))
        ps["last_brief"] = today

    # 2) bias change: only Bullish <-> Bearish flips (a move into/out of Ranging is not alerted)
    if a["h4_bias"] in ("Bullish", "Bearish"):
        if ps.get("h4_dir") and ps["h4_dir"] != a["h4_bias"]:
            notify.send(ms.flip(pair, ps["h4_dir"], a["h4_bias"], a))
        ps["h4_dir"] = a["h4_bias"]

    # 2b) zone entry: price moved into Premium or Discount (only matching the bias, unless TAP_ONLY_WITH_BIAS is off)
    z, prev = a["zone"], ps.get("zone")
    if ZONE_ALERTS and prev is not None and z in ("Premium", "Discount") and z != prev:
        aligned = (z == "Discount" and a["bias"] == "Bullish") or (z == "Premium" and a["bias"] == "Bearish")
        key = f"zone:{z}"
        if (aligned or not TAP_ONLY_WITH_BIAS) and fresh(ps, key, now, ZONE_COOLDOWN_HOURS):
            notify.send(ms.zone(pair, a, price))
            mark(ps, key, now)
    ps["zone"] = z

    # 3) taps on unmitigated H4 order blocks (last two closed M15 candles)
    recent = m15.tail(2)
    obs = a["demand_all"] + a["supply_all"]
    if TAP_ONLY_WITH_BIAS:
        if a["bias"] == "Bullish":
            obs = a["demand_all"]
        elif a["bias"] == "Bearish":
            obs = a["supply_all"]
    for ob in obs:
        touched = ((recent["low"] <= ob["hi"]) & (recent["high"] >= ob["lo"])).any()
        key = f"tap:{ob['type']}:{ob['lo']:.5f}:{ob['hi']:.5f}"
        if touched and fresh(ps, key, now):
            notify.send(ms.tap(pair, ob, a, price))
            mark(ps, key, now)

    # 4) sweeps of fresh external H4 highs/lows, closed back through
    highs, lows = st.fresh_levels(h4)
    for _, c in recent.iterrows():
        for lv in highs:
            k = f"sweep:BSL:{lv:.5f}"
            if c["high"] > lv and c["close"] < lv and fresh(ps, k, now):
                notify.send(ms.sweep(pair, "BSL", lv, a, price))
                mark(ps, k, now)
        for lv in lows:
            k = f"sweep:SSL:{lv:.5f}"
            if c["low"] < lv and c["close"] > lv and fresh(ps, k, now):
                notify.send(ms.sweep(pair, "SSL", lv, a, price))
                mark(ps, k, now)
    print(f"[{pair}] ok  price={price}  bias={a['bias']}  zone={a['zone']}")
    return True

def run():
    force = os.getenv("FORCE", "").lower() == "true"
    now = datetime.now(LONDON)
    if not force and not in_window(now):
        print("Outside London trading window, nothing to do.")
        return
    state = load_state()
    today = now.strftime("%Y-%m-%d")
    ok = 0
    for i, pair in enumerate(ORDER):
        try:
            if process(pair, i, now, today, state, force):
                ok += 1
        except Exception as e:
            print(f"[{pair}] error: {e}")
        time.sleep(1)

    meta = state.setdefault("_meta", {})
    if ok == 0:  # nothing could be fetched: tell the user once in a while instead of failing silently
        last = meta.get("last_health")
        if not last or now - datetime.fromisoformat(last) > timedelta(hours=HEALTH_ALERT_HOURS):
            notify.send("⚠️ Bias bot: could not fetch data for any pair. TradingView may be "
                        "blocking GitHub or be down. Check the Actions log.")
            meta["last_health"] = now.isoformat()

    for k, ps in state.items():  # prune old alert records
        if k.startswith("_"):
            continue
        ps["alerts"] = {a: v for a, v in ps.get("alerts", {}).items()
                        if now - datetime.fromisoformat(v) < timedelta(hours=48)}
    save_state(state)

if __name__ == "__main__":
    run()
