# EDIT THESE to the exact tickers shown at the top of your TradingView charts ("EXCHANGE:SYMBOL")
TICKERS = {
    "NAS100": "OANDA:NAS100USD",
    "XAUUSD": "OANDA:XAUUSD",
    "GER40":  "OANDA:DE30EUR",
    "SP500":  "OANDA:SPX500USD",
    "US30":   "OANDA:US30USD",
    "XAGUSD": "OANDA:XAGUSD",
    "USDJPY": "OANDA:USDJPY",
}
ORDER = list(TICKERS)          # daily briefs go out in this order

# London time schedule
WINDOW_START = (9, 0)          # bot active from 09:00 London
WINDOW_END = (17, 0)           # until 17:00 London (Mon-Fri)
BRIEF_START = (9, 0)           # first daily brief
BRIEF_GAP_MIN = 10             # minutes between each pair's brief

BARS = {"H4": 200, "H1": 200, "M15": 100}   # timeframes: H4 range/bias, H1 bias, M15 taps and sweeps

RANGE_SWING_N = 5              # swing strength used for the H4 dealing range + external liquidity
BIAS_SWING_N = 3               # swing strength used for HH/HL, LH/LL bias
EQ_BAND = 0.05                 # +-5% around 50% = "Equilibrium (mid-range)"
OB_DISPLACEMENT = 1.8          # impulse candle body must be >= 1.8x the average body
ALERT_COOLDOWN_HOURS = 24      # same level won't alert twice within this time
TAP_ONLY_WITH_BIAS = True      # Bullish bias -> only demand taps, Bearish -> only supply taps (Ranging -> both)
ZONE_ALERTS = True             # alert when price enters Premium or Discount of the H4 range
ZONE_COOLDOWN_HOURS = 4        # same zone entry won't alert again within this time
HEALTH_ALERT_HOURS = 6         # if no pair can be fetched, warn on Telegram at most once per this many hours
