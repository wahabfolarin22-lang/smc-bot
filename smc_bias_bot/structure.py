import numpy as np
import pandas as pd
from config import *

def swing_idx(df, n):
    h, l = df["high"].values, df["low"].values
    hi, lo = [], []
    for i in range(n, len(df) - n):
        if h[i] == h[i - n:i + n + 1].max() and not (hi and i - hi[-1] <= n and h[i] == h[hi[-1]]):
            hi.append(i)
        if l[i] == l[i - n:i + n + 1].min() and not (lo and i - lo[-1] <= n and l[i] == l[lo[-1]]):
            lo.append(i)
    return hi, lo

def trend(df, n):
    hi, lo = swing_idx(df, n)
    if len(hi) < 2 or len(lo) < 2:
        return "Ranging"
    H, L = df["high"].values, df["low"].values
    if H[hi[-1]] > H[hi[-2]] and L[lo[-1]] > L[lo[-2]]:
        return "Bullish"
    if H[hi[-1]] < H[hi[-2]] and L[lo[-1]] < L[lo[-2]]:
        return "Bearish"
    return "Ranging"

def dealing_range(h4):
    hi, lo = swing_idx(h4, RANGE_SWING_N)
    H, L = h4["high"].values, h4["low"].values
    if hi and lo:
        start = min(hi[-1], lo[-1])
        rh, rl = H[start:].max(), L[start:].min()
    else:
        rh, rl = H.max(), L.min()
    if rh <= rl:
        rh, rl = H.max(), L.min()
    return float(rh), float(rl)

def order_blocks(df):
    o, c, h, l = (df[k].values for k in ("open", "close", "high", "low"))
    body = np.abs(c - o)
    avg = pd.Series(body).rolling(20).mean().shift(1).values
    obs, seen = [], set()
    for i in range(21, len(df)):
        if np.isnan(avg[i]) or avg[i] == 0:
            continue
        rng = h[i] - l[i]
        if rng == 0 or body[i] < OB_DISPLACEMENT * avg[i]:
            continue
        bull = c[i] > o[i] and c[i] >= h[i] - 0.25 * rng and c[i] > h[max(0, i - 5):i].max()
        bear = c[i] < o[i] and c[i] <= l[i] + 0.25 * rng and c[i] < l[max(0, i - 5):i].min()
        if not (bull or bear):
            continue
        for j in range(i - 1, max(i - 4, 0), -1):
            if (bull and c[j] < o[j]) or (bear and c[j] > o[j]):
                if j in seen:
                    break
                seen.add(j)
                mid = (l[j] + h[j]) / 2
                if bull:
                    mit = bool((l[i + 1:] <= mid).any())
                else:
                    mit = bool((h[i + 1:] >= mid).any())
                try:
                    formed = pd.Timestamp(df["time"].iloc[j]).strftime("%d %b")
                except Exception:
                    formed = ""
                obs.append({"type": "demand" if bull else "supply", "lo": float(l[j]),
                            "hi": float(h[j]), "idx": j, "mitigated": mit, "formed": formed})
                break
    return obs

def fresh_levels(h4):
    """External swing highs/lows that no H4 candle has closed through yet."""
    hi, lo = swing_idx(h4, RANGE_SWING_N)
    H, L, C = h4["high"].values, h4["low"].values, h4["close"].values
    highs = [float(H[i]) for i in hi if not (C[i + 1:] > H[i]).any()]
    lows = [float(L[i]) for i in lo if not (C[i + 1:] < L[i]).any()]
    return highs, lows

def analyze(h4, h1, price):
    rh, rl = dealing_range(h4)
    rh, rl = max(rh, price), min(rl, price)  # live price can sit beyond the last closed H4 extremes
    eq = (rh + rl) / 2
    pos = (price - rl) / (rh - rl)
    if pos > 0.5 + EQ_BAND:
        zone = "Premium"
    elif pos < 0.5 - EQ_BAND:
        zone = "Discount"
    else:
        zone = "Equilibrium (mid-range)"

    t4, t1 = trend(h4, BIAS_SWING_N), trend(h1, BIAS_SWING_N)
    if t4 == "Ranging":
        bias, btxt = "Ranging", f"Ranging (H4 ranging, H1 {t1})"
    elif t4 == t1:
        bias, btxt = t4, f"{t4} (H4 + H1 aligned)"
    else:
        bias, btxt = t4, f"{t4} on H4, H1 is {t1} (retracement)"

    obs = [o for o in order_blocks(h4) if not o["mitigated"]]
    dem_all = [o for o in obs if o["type"] == "demand" and (o["lo"] + o["hi"]) / 2 < eq]
    sup_all = [o for o in obs if o["type"] == "supply" and (o["lo"] + o["hi"]) / 2 > eq]
    dem = max([o for o in dem_all if o["lo"] <= price], key=lambda o: o["hi"], default=None)
    sup = min([o for o in sup_all if o["hi"] >= price], key=lambda o: o["lo"], default=None)

    hi, lo = swing_idx(h4, RANGE_SWING_N)
    H, L = h4["high"].values, h4["low"].values
    ext_high = min([float(H[i]) for i in hi if H[i] > price], default=None)
    ext_low = max([float(L[i]) for i in lo if L[i] < price], default=None)
    if bias == "Bullish":
        target = ext_high or rh
    elif bias == "Bearish":
        target = ext_low or rl
    else:
        target = None

    return {"rh": rh, "rl": rl, "eq": eq, "zone": zone, "bias": bias, "bias_text": btxt,
            "h4_bias": t4, "demand": dem, "supply": sup, "demand_all": dem_all,
            "supply_all": sup_all, "ext_high": ext_high, "ext_low": ext_low, "target": target}
