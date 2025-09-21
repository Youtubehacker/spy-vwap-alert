import os
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from datetime import datetime

# === Load environment variables ===
load_dotenv()
API_KEY = os.getenv("ALPHAVANTAGE_KEY")
TICKER = "SPY"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1419406129707880589/XVsd-_5T96QVtzmm5uJo0K4v_FXf3nONPvZGqwk5u3iim04gert-tgxQkyJTaCBrv6v7"

# === Fetch intraday data ===
def fetch_intraday():
    print("Fetching intraday data...")
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={TICKER}&interval=5min&outputsize=full&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()

    time_series = data.get("Time Series (5min)", {})
    if not time_series:
        print("No data returned from Alpha Vantage.")
        return None

    df = pd.DataFrame.from_dict(time_series, orient="index", dtype=float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df.rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close",
        "5. volume": "volume"
    }, inplace=True)
    return df

# === Calculate VWAP ===
def calculate_vwap(df):
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    return vwap

# === Calculate 9 EMA ===
def calculate_ema(df, period=9):
    ema = df["close"].ewm(span=period, adjust=False).mean()
    return ema

# === Send Discord alert ===
def send_discord_alert(message):
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK, json=payload)

# === Main Logic ===
def main():
    df = fetch_intraday()
    if df is None:
        return

    df["vwap"] = calculate_vwap(df)
    df["ema9"] = calculate_ema(df)

    latest = df.iloc[-1]
    previous = df.iloc[-2]  # to detect crossovers

    signals = []

    # Check VWAP cross
    if previous["close"] < previous["vwap"] and latest["close"] > latest["vwap"]:
        signals.append("Price **reclaimed VWAP**")

    # Check EMA cross
    if previous["close"] < previous["ema9"] and latest["close"] > latest["ema9"]:
        signals.append("Price **crossed above 9EMA**")

    if signals:
        message = (
            f"📊 **SPY Alert** ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
            f"Price: {latest['close']:.2f}\n"
            f"VWAP: {latest['vwap']:.2f}\n"
            f"9 EMA: {latest['ema9']:.2f}\n\n"
            f"🔔 Signals:\n- " + "\n- ".join(signals)
        )
        send_discord_alert(message)
        print("Alert sent to Discord!")
    else:
        print("No signal this time.")

if __name__ == "__main__":
    main()
