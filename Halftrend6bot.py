import requests
import pandas as pd
import numpy as np
import time
import datetime

# ==============================
# 🔹 USER CONFIG
# ==============================
TELEGRAM_BOT_TOKEN = "7567841237:AAGgfQf1WQJl-CbMV688JME7ax1PqQ-anx8"
TELEGRAM_CHAT_ID = "887306673"

INTERVAL = "4h"   # Fixed 4-hour timeframe
VOLUME_MULTIPLIER = 1.2
PRICE_CHANGE_FILTER = 1.0

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

def get_binance_pairs():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        res = requests.get(url, timeout=10).json()
        pairs = [s["symbol"] for s in res["symbols"] if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"]
        return pairs
    except Exception as e:
        print("Pair fetch error:", e)
        return []

def get_klines(symbol, interval="4h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=[
            'time','o','h','l','c','v','close_time','quote_av','trades','tb_base','tb_quote','ignore'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df[['o','h','l','c','v']] = df[['o','h','l','c','v']].astype(float)
        return df
    except:
        return None

def halftrend_signal(df):
    df['avg'] = (df['h'] + df['l']) / 2
    df['direction'] = np.where(df['avg'] > df['avg'].shift(1), 1, -1)
    df['signal'] = np.where(df['direction'] != df['direction'].shift(1), df['direction'], 0)
    if df['signal'].iloc[-1] == 1:
        return "BUY"
    elif df['signal'].iloc[-1] == -1:
        return "SELL"
    else:
        return None

def main():
    print(f"🚀 Starting HalfTrend Scan | {datetime.datetime.utcnow()} UTC")
    pairs = get_binance_pairs()
    print(f"Total pairs found: {len(pairs)}")

    alerts = []

    for symbol in pairs:
        df = get_klines(symbol, INTERVAL)
        if df is None or len(df) < 50:
            continue

        avg_vol = df['v'].mean()
        if df['v'].iloc[-1] < VOLUME_MULTIPLIER * avg_vol:
            continue

        price_change = abs((df['c'].iloc[-1] - df['c'].iloc[-2]) / df['c'].iloc[-2]) * 100
        if price_change < PRICE_CHANGE_FILTER:
            continue

        signal = halftrend_signal(df)
        if signal:
            alerts.append(f"{symbol}: {signal} | {price_change:.2f}% | Vol: {df['v'].iloc[-1]:.0f}")

    if alerts:
        message = "📊 *HalfTrend 4H Signals*\n\n" + "\n".join(alerts)
        send_telegram_message(message)
        print("✅ Alerts sent:", len(alerts))
    else:
        print("No new signals found.")

    print("Scan complete.")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60 * 60 * 4)  # every 4 hours
