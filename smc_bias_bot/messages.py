def f(p):
    if p is None:
        return "N/A"
    if p >= 1000:
        return f"{p:,.1f}"
    if p >= 100:
        return f"{p:,.2f}"
    return f"{p:,.3f}"

FOOT = "⚠️ Not an entry signal. Bias only."

def _fm(ob):
    return f", formed {ob['formed']}" if ob.get("formed") else ""

def brief(pair, a, price):
    emoji = {"Bullish": "🟢", "Bearish": "🔴"}.get(a["bias"], "⚪")
    word = {"Bullish": "BUY BIAS", "Bearish": "SELL BIAS"}.get(a["bias"], "RANGING")
    L = [f"{emoji} {word} · {pair} · H4→H1",
         f"H4 range: {f(a['rh'])} – {f(a['rl'])} · EQ {f(a['eq'])}",
         f"Price {f(price)} → {a['zone']}",
         f"Bias: {a['bias_text']}"]
    if a["supply"]:
        L.append(f"Supply OB: {f(a['supply']['lo'])}–{f(a['supply']['hi'])} (Premium, unmitigated{_fm(a['supply'])})")
    if a["demand"]:
        L.append(f"Demand OB: {f(a['demand']['lo'])}–{f(a['demand']['hi'])} (Discount, unmitigated{_fm(a['demand'])})")
    if a["ext_high"]:
        L.append(f"External high: {f(a['ext_high'])}")
    if a["ext_low"]:
        L.append(f"External low: {f(a['ext_low'])}")
    if a["target"]:
        L.append(f"Target: {f(a['target'])}")
    if a["bias"] == "Bullish" and a["zone"] == "Premium":
        L.append("⏳ Price is in Premium. Wait for a pullback into Discount.")
    if a["bias"] == "Bearish" and a["zone"] == "Discount":
        L.append("⏳ Price is in Discount. Wait for a pullback into Premium.")
    if a["zone"].startswith("Equilibrium"):
        L.append("⏳ Mid-range. Avoid trading equilibrium.")
    L.append(FOOT)
    return "\n".join(L)

def tap(pair, ob, a, price):
    kind = "Demand" if ob["type"] == "demand" else "Supply"
    zone = "Discount" if ob["type"] == "demand" else "Premium"
    return (f"🎯 TAP · {pair} · H4 level\n"
            f"Price tapped {kind} OB {f(ob['lo'])}–{f(ob['hi'])} ({zone}, unmitigated{_fm(ob)})\n"
            f"Price {f(price)} · Bias: {a['bias_text']}\n"
            f"Next: wait for your M15 MSS / entry model.\n{FOOT}")

def sweep(pair, side, level, a, price):
    if side == "SSL":
        txt = f"External low {f(level)} swept, closed back above"
    else:
        txt = f"External high {f(level)} swept, closed back below"
    return (f"🧲 SWEEP · {pair} · M15 on H4 liquidity\n{txt}\n"
            f"Price {f(price)} → {a['zone']} · Bias: {a['bias_text']}\n{FOOT}")

def flip(pair, old, new, a):
    return (f"🔄 BIAS CHANGE · {pair}\nH4 structure: {old} → {new}\n"
            f"Current read: {a['bias_text']}\n{FOOT}")


def zone(pair, a, price):
    z = a["zone"]
    side = "Discount" if z == "Discount" else "Premium"
    limit = "below 45%" if z == "Discount" else "above 55%"
    L = [f"📍 ZONE · {pair} · H4 range",
         f"Price entered {side} ({limit} of the range) at {f(price)}",
         f"Range: {f(a['rh'])} – {f(a['rl'])} · EQ {f(a['eq'])}",
         f"Bias: {a['bias_text']}"]
    aligned = (z == "Discount" and a["bias"] == "Bullish") or (z == "Premium" and a["bias"] == "Bearish")
    if aligned:
        L.append("✅ Zone matches bias.")
    else:
        L.append("⏳ Zone does not match bias. Be careful.")
    ob = a["demand"] if z == "Discount" else a["supply"]
    if ob:
        kind = "Demand" if z == "Discount" else "Supply"
        L.append(f"Nearest {kind} OB: {f(ob['lo'])}–{f(ob['hi'])}")
    L.append(FOOT)
    return "\n".join(L)
