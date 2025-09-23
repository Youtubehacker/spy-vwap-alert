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
    if "Global Quote" not in data:
        print("No price data returned from Alpha Vantage.")
        return None
    return float(data["Global Quote"]["05. price"])

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
    print("Fetching latest price and intraday data...")

    latest_price = fetch_latest_price(SYMBOL)
    if latest_price is None:
        return

    df = fetch_intraday_data(SYMBOL)
    if df is None:
        return

    vwap = calculate_vwap(df)
    ema9 = calculate_ema(df)

    # Determine signals
    signals = []
    if latest_price > vwap:
        signals.append("Above VWAP")
    else:
        signals.append("Below VWAP")
    if latest_price > ema9:
        signals.append("Above 9EMA")
    else:
        signals.append("Below 9EMA")

    # Convert timestamp to EST
    est = pytz.timezone("US/Eastern")
    timestamp = datetime.now(est).strftime("%Y-%m-%d %H:%M:%S")

    # Compact Discord message
    message = (
        f"📊 {SYMBOL} {latest_price:.2f} ({timestamp})\n"
        f"VWAP: {vwap:.2f} | 9EMA: {ema9:.2f}\n"
        f"🔔 {' | '.join(signals)}"
    )

    print(message)
    send_discord_alert(message)

if __name__ == "__main__":
    main()
