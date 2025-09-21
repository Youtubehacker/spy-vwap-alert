print("Starting SPY data fetch...")

import requests
import json

API_KEY = "4VZ6ON5M22E4FW8R"
TICKER = "SPY"

url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={TICKER}&interval=5min&apikey={API_KEY}"
response = requests.get(url)
data = response.json()

# Just print the most recent price + volume
time_series = data.get("Time Series (5min)", {})
if time_series:
    latest_time = sorted(time_series.keys())[-1]
    latest_data = time_series[latest_time]
    print(f"Latest SPY data at {latest_time}:")
    print(f"Price: {latest_data['4. close']}")
    print(f"Volume: {latest_data['5. volume']}")
else:
    print("No data returned. Check API key or rate limits.")
