import yfinance as yf

ticker = yf.Ticker("RSG")

# aapl_historical = ticker.history(start="2025-08-02", end="2025-08-07", interval="1m")

# aapl_historical = ticker.history(start="2025-08-02", end="2025-08-29", interval="1d")

aapl_historical = ticker.history(start="1900-06-21", end="2025-07-08", interval="1d")

print("Prices:", aapl_historical)