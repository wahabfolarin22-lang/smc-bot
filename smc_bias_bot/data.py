import time

_tv = None

def _client():
    global _tv
    if _tv is None:
        try:
            from tvDatafeed import TvDatafeed
        except ImportError:
            from tvdatafeed import TvDatafeed
        _tv = TvDatafeed()  # anonymous
    return _tv

def _interval(tf):
    try:
        from tvDatafeed import Interval
    except ImportError:
        from tvdatafeed import Interval
    return {"H4": Interval.in_4_hour, "H1": Interval.in_1_hour,
            "M15": Interval.in_15_minute}[tf]

def candles(pair, tf, n, tickers=None, tries=3):
    from config import TICKERS
    exchange, symbol = (tickers or TICKERS)[pair].split(":")
    for _ in range(tries):
        try:
            df = _client().get_hist(symbol=symbol, exchange=exchange,
                                    interval=_interval(tf), n_bars=n)
            if df is not None and len(df) >= int(n * 0.8):
                df = df.reset_index()
                df = df.rename(columns={df.columns[0]: "time"})
                df = df[["time", "open", "high", "low", "close"]]
                return df.iloc[:-1].reset_index(drop=True)  # drop the still-forming candle
        except Exception as e:
            print(f"  [{pair} {tf}] fetch error: {e}")
        time.sleep(2)
    return None
