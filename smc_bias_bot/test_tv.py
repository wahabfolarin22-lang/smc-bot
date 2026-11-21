"""Step 1 test: can we pull candles from TradingView? Prints PASS/FAIL per pair. Tickers come from config.py."""
import time
try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    from tvdatafeed import TvDatafeed, Interval
from config import TICKERS

TFS = {"H4": Interval.in_4_hour, "H1": Interval.in_1_hour, "M15": Interval.in_15_minute}

def fetch(tv, exchange, symbol, interval, tries=3):
    for _ in range(tries):
        try:
            df = tv.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=150)
            if df is not None and len(df) > 0:
                return df
        except Exception as e:
            print(f"    error: {e}")
        time.sleep(2)
    return None

def main():
    tv = TvDatafeed()
    results = {}
    for pair, ticker in TICKERS.items():
        exchange, symbol = ticker.split(":")
        print(f"\n== {pair} ({ticker})")
        ok = True
        for tf, interval in TFS.items():
            df = fetch(tv, exchange, symbol, interval)
            if df is None:
                print(f"  {tf}: FAIL (no data)")
                ok = False
            else:
                print(f"  {tf}: OK  bars={len(df)}  last={df.index[-1]}  close={df.iloc[-1]['close']}")
            time.sleep(1)
        results[pair] = ok
    print("\n===== SUMMARY =====")
    for pair, ok in results.items():
        print(f"{pair}: {'PASS' if ok else 'FAIL'}")
    print("\nAll pairs passed." if all(results.values()) else "\nSome pairs failed. Send the log to Claude.")

if __name__ == "__main__":
    main()
