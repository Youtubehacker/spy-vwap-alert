import os
import requests
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
SYMBOL = "SPY"

def fetch_latest_price(symbol):
    """Fetch the most recent price using Alpha Vantage Global Quote."""
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    try:
        return float(data["Global Quote"]["05. price"])
    except (KeyError, TypeError, ValueError):
        print("No live price returned from Alpha Vantage.")
        return None

def fetch_intraday_data(symbol):
    """Fetch intraday OHLCV data (5-min candles)."""
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&outputsize=compact&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "Time Series (5min)" not in data:
        print("No intraday data returned from Alpha Vantage.")
        return None
    df = pd.DataFrame.from_dict(data["Time Series (5min)"], orient="index", dtype=float)
    df = df.sort_index()
    df["close"] = df["4. close"]
    df["volume"] = df["5. volume"]
    return df

def calculate_vwap(df):
    return (df["close"] * df["volume"]).sum() / df["volume"].sum()

def calculate_ema(df, period=9):
    return df["close"].ewm(span=period, adjust=False).mean().iloc[-1]

def send_discord_alert(message):
    payload = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK, json=payload)
    except Exception as e:
        print(f"Error sending Discord alert: {e}")

def main():
    # Restrict to 9:30–11:30 AM ET
    est = pytz.timezone("US/Eastern")
    now = datetime.now(est)
    if not (now.hour == 9 and now.minute >= 30) and not (9 < now.hour < 11) and not (now.hour == 11 and now.minute <= 30):
        print("Outside trading window. Skipping run.")
        return

    latest_price = fetch_latest_price(SYMBOL)
    if latest_price is None:
        return

    df = fetch_intraday_data(SYMBOL)
    if df is None:
        return

    vwap = calculate_vwap(df)
    ema9 = calculate_ema(df)

    # Determine signal
    if latest_price > vwap and latest_price > ema9:
        signal = "Long"
    elif latest_price < vwap and latest_price < ema9:
        signal = "Short"
    else:
        signal = "Neutral"

    # Compose compact Discord message
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S EST")
    message = (
        f"📊 {SYMBOL} {latest_price:.2f} | {timestamp}\n"
        f"VWAP: {vwap:.2f} | 9EMA: {ema9:.2f}\n"
        f"🔔 Signal: {signal}"
    )

    print(message)
    send_discord_alert(message)

if __name__ == "__main__":
    main()
