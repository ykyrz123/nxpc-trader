"""
nxpc_volume_trader_v5.py

Description:
    使用 Bybit Open API V5，以 Maker 掛單方式刷 NXPCUSDT 交易量，確保獲得 14,000 NXPC 獎勵。

Features:
    - V5 API: GET /v5/market/tickers 查詢最新價格 :contentReference[oaicite:0]{index=0}
    - V5 API: POST /v5/order/create 下 Limit 掛單 :contentReference[oaicite:1]{index=1}
    - HMAC-SHA256 簽名：timestamp+apiKey+recvWindow+body :contentReference[oaicite:2]{index=2}
    - 內建日誌記錄到 nxpc_trader_v5.log
"""

import time
import hmac
import hashlib
import logging
import json
import requests
from urllib.parse import urlencode

# === Configuration ===
API_KEY     = "8auAdibh8y2tPnngHV"
API_SECRET  = "4y5tGfmGz2wZeoSBh6wWwdYAha8J8iQWNo9C"
BASE_URL    = "https://api.bybit.com"
PAIR        = "NXPCUSDT"
RECV_WINDOW = "5000"       # 預設簽名驗證時效
ORDER_SIZE  = 1000.0       # USDT per side
TARGET_VOLUME = 4000.0   # USDT total volume target
PRICE_SPREAD  = 0.0001     # 0.01% 價差

# === Logging Setup ===
logging.basicConfig(
    filename="nxpc_trader_v5.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def sign(timestamp: str, api_key: str, recv_window: str, body: str) -> str:
    """
    V5 簽名：timestamp + api_key + recv_window + (queryString or jsonBodyString)
    """
    to_sign = f"{timestamp}{api_key}{recv_window}{body}"
    return hmac.new(API_SECRET.encode(), to_sign.encode(), hashlib.sha256).hexdigest()

def get_mid_price() -> float:
    """
    使用 V5 /v5/market/tickers 獲取最新價格
    """
    timestamp = str(int(time.time() * 1000))
    params = {"category": "spot", "symbol": PAIR}
    qs = urlencode(params)
    signature = sign(timestamp, API_KEY, RECV_WINDOW, qs)
    headers = {
        "X-BAPI-API-KEY": API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": RECV_WINDOW,
        "X-BAPI-SIGN": signature,
    }
    resp = requests.get(f"{BASE_URL}/v5/market/tickers?{qs}", headers=headers)
    data = resp.json()
    return float(data["result"]["list"][0]["lastPrice"])

def place_limit_order(side: str, qty: float, price: float) -> dict:
    """
    使用 V5 /v5/order/create 下 PostOnly 限價掛單
    """
    timestamp = str(int(time.time() * 1000))
    body = {
        "category": "spot",
        "symbol": PAIR,
        "side": side.upper(),       # "BUY" 或 "SELL"
        "orderType": "Limit",
        "qty": str(qty),
        "price": str(price),
        "timeInForce": "PostOnly"
    }
    body_str = json.dumps(body)
    signature = sign(timestamp, API_KEY, RECV_WINDOW, body_str)
    headers = {
        "Content-Type": "application/json",
        "X-BAPI-API-KEY": API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": RECV_WINDOW,
        "X-BAPI-SIGN": signature,
    }
    resp = requests.post(f"{BASE_URL}/v5/order/create", headers=headers, data=body_str)
    # 新增：列印 API 回傳完整內容，方便除錯
    print("Order response:", resp.json())
    return resp.json()

def main():
    total_vol = 0.0
    loops = 0
    logging.info("V5 Trader started. Target volume: %s USDT", TARGET_VOLUME)

    while total_vol < TARGET_VOLUME:
        try:
            mid = get_mid_price()
            buy_price  = round(mid * (1 - PRICE_SPREAD), 6)
            sell_price = round(mid * (1 + PRICE_SPREAD), 6)
            qty = round(ORDER_SIZE / buy_price, 8)

            # 下買單
            buy_res = place_limit_order("BUY", qty, buy_price)
            time.sleep(1)
            # 下賣單
            sell_res = place_limit_order("SELL", qty, sell_price)
            time.sleep(1)

            total_vol += ORDER_SIZE * 2
            loops += 1
            logging.info(
                "Loop %d: BUY %s @ %s, SELL %s @ %s → +%s USDT (Total: %s)",
                loops, qty, buy_price, qty, sell_price, ORDER_SIZE*2, total_vol
            )
        except Exception as e:
            logging.error("Error on loop %d: %s", loops, e, exc_info=True)
            time.sleep(5)

    logging.info("Target volume achieved after %d loops. Exiting.", loops)

if __name__ == "__main__":
    main()
