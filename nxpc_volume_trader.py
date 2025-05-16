"""
nxpc_volume_trader.py

Description:
    Bybit API script to efficiently inflate NXPCUSDT trading volume in order to secure the maximum 14,000 NXPC reward in the Tokensplash 活動 using limited capital.

Features:
    - Calculates required total trading volume based on pool and participants
    - Loops limit buy & sell (maker-only) orders to inflate volume
    - Configurable order size, target volume, and price spread
    - Robust HMAC-SHA256 signing for Bybit Spot API
    - Logging of each loop’s volume and any errors into `nxpc_trader.log`

Requirements:
    pip install requests
"""
import requests
import time
import hmac
import hashlib
import logging

# === Configuration ===
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
BASE_URL = "https://api.bybit.com"
PAIR = "NXPCUSDT"
INITIAL_CAPITAL = 1000.0      # USDT available for margin
ORDER_SIZE = 1000.0           # USDT per order side (<= INITIAL_CAPITAL)
# Total trading volume needed (USDT) to secure 14,000 NXPC:
#   Required ratio = 14,000 / 9,000,000 ≈ 0.0015556
#   If each of 600k participants trades ≥500 USDT, total ≈600k*500=300,000,000 USDT
#   V_needed = 0.0015556 * 300,000,000 ≈ 466,667 USDT
TARGET_VOLUME = 466667.0      # USDT total volume target
PRICE_SPREAD = 0.0001         # Limit order offset (0.01%)
FEE_RATE = 0.001              # Maker fee rate (0.1% for non-VIP)

# === Logging Setup ===
logging.basicConfig(
    filename="nxpc_trader.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

def sign(params: dict, secret: str) -> str:
    """
    Create HMAC-SHA256 signature required by Bybit API.
    """
    ordered = sorted(params.items())
    payload = "&".join([f"{k}={v}" for k, v in ordered])
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

def get_mid_price() -> float:
    """
    Fetch the current mid-market price for NXPCUSDT.
    """
    resp = requests.get(f"{BASE_URL}/spot/quote/v1/ticker/price", params={"symbol": PAIR})
    data = resp.json()
    return float(data["result"]["price"])

def place_limit_order(side: str, qty: float, price: float) -> dict:
    """
    Place a PostOnly limit order and return the API response.
    """
    path = "/spot/v1/order"
    timestamp = int(time.time() * 1000)
    params = {
        "apiKey": API_KEY,
        "symbol": PAIR,
        "orderType": "LIMIT",
        "side": side,
        "qty": str(qty),
        "price": str(price),
        "timeInForce": "PostOnly",
        "timestamp": timestamp
    }
    params["sign"] = sign(params, API_SECRET)
    resp = requests.post(BASE_URL + path, data=params)
    return resp.json()

def main():
    total_volume = 0.0
    loop_count = 0

    logging.info("Trader started. Target volume: %s USDT", TARGET_VOLUME)

    while total_volume < TARGET_VOLUME:
        try:
            mid = get_mid_price()
            buy_price = round(mid * (1 - PRICE_SPREAD), 6)
            sell_price = round(mid * (1 + PRICE_SPREAD), 6)
            qty = round(ORDER_SIZE / buy_price, 8)

            # Place buy maker order
            buy_resp = place_limit_order("BUY", qty, buy_price)
            time.sleep(1)

            # Place sell maker order
            sell_resp = place_limit_order("SELL", qty, sell_price)
            time.sleep(1)

            # Update stats
            total_volume += ORDER_SIZE * 2
            loop_count += 1
            logging.info(
                "Loop %d: BUY %s @ %s, SELL %s @ %s → +%s USDT volume (Total: %s)",
                loop_count, qty, buy_price, qty, sell_price, ORDER_SIZE*2, total_volume
            )

        except Exception as e:
            logging.error("Error on loop %d: %s", loop_count, e, exc_info=True)
            time.sleep(5)

    logging.info("Target volume achieved after %d loops. Exiting.", loop_count)

if __name__ == "__main__":
    main()
