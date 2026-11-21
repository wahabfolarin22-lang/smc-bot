"""
Offline self-test (no internet, no Telegram). Builds crafted candles and checks the bot's logic:
structure, order blocks, bias/zone, brief/tap/sweep/flip alerts, no duplicate alerts, brief spacing.
Run:  python selftest.py
"""
import numpy as np, pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import main, notify, structure as st

LON = ZoneInfo("Europe/London")
PASS, FAIL = [], []

def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (f"   {extra}" if extra and not cond else ""))

def build(pivots, n, noise=0.05, seed=0, freq="4h", start="2026-09-01"):
    rng = np.random.default_rng(seed)
    xs, ys = zip(*pivots)
    c = np.interp(np.arange(n), xs, ys) + rng.normal(0, noise, n)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.08, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 0.08, n))
    return pd.DataFrame({"time": pd.date_range(start, periods=n, freq=freq), "open": o, "high": h, "low": l, "close": c})

def setc(df, i, o, h, l, c):
    df.loc[i, ["open", "high", "low", "close"]] = [o, h, l, c]

# ---- crafted market: H4 uptrend (HH/HL) with a bullish demand OB, price pulled back into Discount ----
def make_h4():
    df = build([(0, 100), (40, 110), (65, 104), (100, 118), (130, 108.6), (170, 126), (199, 112.5)], 200)
    setc(df, 130, 109.0, 109.1, 108.0, 108.2)   # bearish candle = the order block (zone 108.0 - 109.1)
    setc(df, 131, 108.2, 112.3, 108.1, 112.2)   # displacement up, breaks structure
    return df

def make_h1():
    return build([(0, 100), (50, 110), (80, 105), (130, 118), (170, 112), (199, 116)], 200, freq="1h")

def make_m15(last):
    df = build([(0, 114), (99, 109.5)], 100, noise=0.03, freq="15min")
    setc(df, 99, *last)
    return df

class Fx:  # fake fetcher
    def __init__(self, m15_last, h4=None, h1=None):
        self.d = {"H4": h4 if h4 is not None else make_h4(),
                  "H1": h1 if h1 is not None else make_h1(),
                  "M15": make_m15(m15_last)}
    def __call__(self, pair, tf, n):
        return self.d[tf].copy()

SENT = []
notify.send = lambda text: SENT.append(text)

# ===== 1. structure =====
h4, h1 = make_h4(), make_h1()
check("H4 trend = Bullish", st.trend(h4, 3) == "Bullish", st.trend(h4, 3))
check("H1 trend = Bullish", st.trend(h1, 3) == "Bullish", st.trend(h1, 3))
a = st.analyze(h4, h1, 109.4)
check("Zone = Discount at 109.4", a["zone"] == "Discount", a["zone"])
check("Bias = Bullish (H4 + H1 aligned)", a["bias"] == "Bullish" and "aligned" in a["bias_text"], a["bias_text"])
check("Range high ~126, low ~108", 125.5 < a["rh"] < 127 and 107.5 < a["rl"] < 108.3, f'{a["rh"]:.2f} {a["rl"]:.2f}')
check("Demand OB found 108.0-109.1, unmitigated, in Discount",
      a["demand"] is not None and abs(a["demand"]["lo"] - 108.0) < 0.01 and abs(a["demand"]["hi"] - 109.1) < 0.01)
check("OB has a formed date", bool(a["demand"] and a["demand"]["formed"]), str(a["demand"]))
check("Target = an external high above price", a["target"] is not None and a["target"] > 109.4)
a_prem = st.analyze(h4, h1, 124.0)
check("Zone = Premium at 124", a_prem["zone"] == "Premium", a_prem["zone"])
a_eq = st.analyze(h4, h1, 117.0)
check("Zone = Equilibrium at 117", a_eq["zone"].startswith("Equilibrium"), a_eq["zone"])

# ===== 2. process(): brief at slot time, tap alert, no duplicates =====
state = {}
now = datetime(2026, 11, 23, 9, 5, tzinfo=LON)     # Monday 09:05 London
today = now.strftime("%Y-%m-%d")
fx = Fx((109.6, 109.8, 108.9, 109.4))           # last M15 candle wicks into the demand OB
SENT.clear()
main.process("NAS100", 0, now, today, state, False, fetch=fx)
kinds = [s.split("·")[0].strip() for s in SENT]
check("09:05 pair #0 sends a brief", any("BUY BIAS" in k for k in kinds), str(kinds))
check("09:05 pair #0 sends a TAP alert (demand OB touched, bias Bullish)", any("TAP" in k for k in kinds), str(kinds))
n1 = len(SENT)
main.process("NAS100", 0, now.replace(minute=20), today, state, False, fetch=fx)
check("Second run: no duplicate brief/tap", len(SENT) == n1, f"{len(SENT)} vs {n1}")

# ===== 3. brief spacing: pair #1 slot is 09:10 =====
SENT.clear()
state2 = {}
main.process("XAUUSD", 1, now, today, state2, False, fetch=Fx((112, 113, 111.5, 112.5)))
check("09:05 pair #1 (slot 09:10) sends nothing", not any("BIAS" in s or "RANGING" in s for s in SENT), str(SENT[:1]))
main.process("XAUUSD", 1, now.replace(minute=11), today, state2, False, fetch=Fx((112, 113, 111.5, 112.5)))
check("09:11 pair #1 sends its brief", any("BUY BIAS" in s for s in SENT))

# ===== 4. sweep of a fresh external high, closed back below =====
SENT.clear()
state3 = {"US30": {"last_brief": today, "h4_dir": "Bullish", "alerts": {}}}
main.process("US30", 3, now, today, state3, False, fetch=Fx((125.2, 126.6, 125.0, 125.5)))
check("Sweep alert on high swept + closed back below", any("SWEEP" in s and "swept, closed back below" in s for s in SENT), str(SENT))

# ===== 5. bias flip only Bullish<->Bearish =====
SENT.clear()
state4 = {"GER40": {"last_brief": today, "h4_dir": "Bearish", "alerts": {}}}
main.process("GER40", 2, now, today, state4, False, fetch=Fx((112, 113, 111.5, 112.5)))
check("Bearish -> Bullish sends a BIAS CHANGE", any("BIAS CHANGE" in s for s in SENT))
check("Stored direction updated to Bullish", state4["GER40"]["h4_dir"] == "Bullish")

# ===== 6. tap alerts follow bias (Bearish bias must not alert on a demand tap) =====
bear_h4 = build([(0, 126), (40, 116), (65, 122), (100, 108), (130, 117.4), (170, 100), (199, 113.5)], 200)
setc(bear_h4, 130, 117.0, 118.0, 116.9, 117.8)        # bullish candle = supply OB (116.9 - 118.0)
setc(bear_h4, 131, 117.8, 117.9, 113.8, 113.9)        # displacement down
bear_h1 = build([(0, 126), (50, 116), (80, 121), (130, 108), (170, 114), (199, 110)], 200, freq="1h")
a_b = st.analyze(bear_h4, bear_h1, 117.5)
check("Bearish market: bias Bearish", a_b["bias"] == "Bearish", a_b["bias_text"])
check("Bearish market: supply OB found in Premium", a_b["supply"] is not None and a_b["zone"] == "Premium",
      f'{a_b["supply"]} {a_b["zone"]}')

# ===== 6b. zone-entry alerts =====
SENT.clear()
sz = {"NAS100": {"last_brief": today, "h4_dir": "Bullish", "zone": "Equilibrium (mid-range)", "alerts": {}}}
main.process("NAS100", 0, now, today, sz, False, fetch=Fx((109.6, 109.7, 109.5, 109.6)))
check("Zone alert: entered Discount with Bullish bias", any("ZONE" in s and "entered Discount" in s and "matches bias" in s for s in SENT), str(SENT))
n = len(SENT)
sz["NAS100"]["zone"] = "Equilibrium (mid-range)"
main.process("NAS100", 0, now.replace(minute=20), today, sz, False, fetch=Fx((109.6, 109.7, 109.5, 109.6)))
check("Zone alert: cooldown stops a repeat", len(SENT) == n, f"{len(SENT)} vs {n}")
SENT.clear()
main.process("GER40", 2, now, today, {"GER40": {"last_brief": today, "h4_dir": "Bullish", "alerts": {}}}, False, fetch=Fx((109.6, 109.7, 109.5, 109.6)))
check("Zone alert: first run (no previous zone) stays quiet", not any("ZONE" in s for s in SENT))
SENT.clear()
main.process("US30", 3, now, today, {"US30": {"last_brief": today, "h4_dir": "Bullish", "zone": "Premium", "alerts": {}}}, False, fetch=Fx((124.0, 124.2, 123.8, 124.0)))
check("Zone alert: entering Premium with Bullish bias is not alerted", not any("ZONE" in s for s in SENT), str(SENT))

# ===== 7. fetch failure handling =====
SENT.clear()
ok = main.process("USDJPY", 6, now, today, {}, False, fetch=lambda p, tf, n: None)
check("Failed fetch returns False and does not crash", ok is False)

# ===== 8. window + state round trip =====
check("Window: Monday 10:00 London is inside", main.in_window(datetime(2026, 11, 23, 10, 0, tzinfo=LON)))
check("Window: Monday 08:30 London is outside", not main.in_window(datetime(2026, 11, 23, 8, 30, tzinfo=LON)))
check("Window: Saturday 10:00 is outside", not main.in_window(datetime(2026, 11, 21, 10, 0, tzinfo=LON)))
import json
check("State is JSON-serialisable", bool(json.dumps(state)))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    raise SystemExit(1)
