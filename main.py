import os
import requests
from datetime import datetime
import csv
import pandas as pd

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

SYMBOL = "SPY"

def fetch_intraday_data(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&outputsize=compact&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    # Alpha Vantage may return an error if the key is invalid or limit exceeded
    if "Time Series (5min)" not in data:
        print("No data returned from Alpha Vantage.")
        return None
    df = pd.DataFrame.from_dict(data["Time Series (5min)"], orient="index", dtype=float)
    df = df.sort_index()
    df["close"] = df["4. close"]
    df["volume"] = df["5. volume"]
    return df

def calculate_vwap(df):
    vwap = (df["close"] * df["volume"]).sum() / df["volume"].sum()
    return vwap

def calculate_ema(df, period=9):
    return df["close"].ewm(span=period, adjust=False).mean().iloc[-1]

def send_discord_alert(message):
    payload = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload)
        if response.status_code == 204:
            print("Discord alert sent successfully.")
        else:
            print(f"Failed to send Discord alert. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending Discord alert: {e}")

def log_alert_csv(message):
    file_path = "alerts_log.csv"
    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Message"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message])

def main():
    print("Fetching intraday data...")
    df = fetch_intraday_data(SYMBOL)
    if df is None:
        return

    latest_close = df["close"].iloc[-1]
    vwap = calculate_vwap(df)
    ema9 = calculate_ema(df)

    print(f"Latest Close: {latest_close:.2f}, VWAP: {vwap:.2f}, 9EMA: {ema9:.2f}")

    signals = []

    # Long signals
    if latest_close > vwap:
        signals.append("Price reclaimed VWAP (Long)")
    if latest_close > ema9:
        signals.append("Price crossed above 9EMA (Long)")

    # Short signals
    if latest_close < vwap:
        signals.append("Price dropped below VWAP (Short)")
    if latest_close < ema9:
        signals.append("Price crossed below 9EMA (Short)")

    if signals:
        message = f"📊 {SYMBOL} Alert ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
        message += f"Price: {latest_close:.2f}\nVWAP: {vwap:.2f}\n9 EMA: {ema9:.2f}\n\n"
        message += "🔔 Signals:\n- " + "\n- ".join(signals)
        send_discord_alert(message)
        log_alert_csv(message)
    else:
        print("No signal this time.")

if __name__ == "__main__":
    main()
