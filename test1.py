import requests
import json
import base64
import hmac
import hashlib
import time
from datetime import datetime, timedelta
import pandas as pd
import logging

# Configure logging to write to a file
logging.basicConfig(filename='bot_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Replace with your Coinbase Pro API credentials
API_KEY = 'YOUR_API_KEY'
API_SECRET = 'YOUR_API_SECRET'
API_PASSPHRASE = 'YOUR_API_PASSPHRASE'

# Coinbase Pro API endpoints
API_URL = 'https://api.pro.coinbase.com'


def create_request_headers(endpoint, method='GET', body=''):
    try:
        timestamp = str(time.time())
        message = timestamp + method + endpoint + (body if body else '')
        signature = hmac.new(
            key=base64.b64decode(API_SECRET),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        headers = {
            'CB-ACCESS-KEY': API_KEY,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': API_PASSPHRASE,
            'Content-Type': 'application/json'
        }
        return headers
    except Exception as e:
        logging.error(f"Error creating request headers: {e}")
        return None


def fetch_historical_data(product_id, start_time, end_time, granularity=300):
    try:
        endpoint = f'/products/{product_id}/candles'
        params = {
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'granularity': granularity
        }
        headers = create_request_headers(endpoint, 'GET')
        response = requests.get(API_URL + endpoint, headers=headers, params=params)

        if response.status_code == 200:
            data = pd.DataFrame(response.json(), columns=['time', 'low', 'high', 'open', 'close', 'volume'])
            return data
        else:
            logging.warning(f"Failed to fetch historical data for {product_id}: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error fetching historical data for {product_id}: {e}")
        return pd.DataFrame()


def get_available_products():
    try:
        endpoint = '/products'
        headers = create_request_headers(endpoint, 'GET')
        response = requests.get(API_URL + endpoint, headers=headers)

        if response.status_code == 200:
            products = json.loads(response.text)
            return [product['id'] for product in products if product['trading_disabled'] == False]
        else:
            logging.warning(f"Failed to fetch products: {response.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error fetching products: {e}")
        return []


def check_buy_condition(product_id):
    now = datetime.now()
    start_time = now - timedelta(hours=2)
    historical_data = fetch_historical_data(product_id, start_time, now)

    if not historical_data.empty:
        price_increase = (historical_data['close'].iloc[-1] - historical_data['open'].iloc[0]) / \
                         historical_data['open'].iloc[0] * 100
        return price_increase >= 10
    return False


def execute_buy_order(product_id):
    # Implement your buy order logic here
    pass


def check_sell_condition(product_id, purchase_price, highest_price, purchase_time):
    current_data = fetch_current_price_data(product_id)  # Implement this function to get the current price
    if current_data.empty:
        return False

    current_price = current_data['price']
    price_drop_from_purchase = (current_price - purchase_price) / purchase_price * 100
    price_drop_from_highest = (current_price - highest_price) / highest_price * 100
    price_gain_from_purchase = price_drop_from_purchase * -1  # Invert to get the gain

    # Check the selling conditions
    if price_drop_from_highest <= -4 or price_drop_from_purchase <= -5 or price_gain_from_purchase >= 20:
        return True
    return False

def execute_sell_order(product_id):
    # Implement your sell order logic here
    # Use your Coinbase Pro API to place a sell order
    try:
        # Example sell order API call (you'll need to implement the details)
        sell_order_data = {
            'type': 'market',
            'product_id': product_id,
            'size': 'YOUR_CRYPTO_AMOUNT_TO_SELL'
        }
        endpoint = '/orders'
        body = json.dumps(sell_order_data)
        headers = create_request_headers(endpoint, 'POST', body)
        response = requests.post(API_URL + endpoint, headers=headers, data=body)

        if response.status_code == 200:
            logging.info(f"Successfully executed sell order for {product_id}")
        else:
            logging.warning(f"Failed to execute sell order for {product_id}: {response.status_code}")
    except Exception as e:
        logging.error(f"Error executing sell order for {product_id}: {e}")


owned_crypto = False
held_crypto = None

def main():
    global owned_crypto, held_crypto
    highest_price = 0  # Initialize the highest price
    while True:
        try:
            current_time = datetime.now()

            # Check buy conditions only if no cryptocurrency is currently owned
            if not owned_crypto and current_time.minute == 0 and current_time.second == 0:
                available_products = get_available_products()
                for product_id in available_products:
                    if check_buy_condition(product_id):
                        execute_buy_order(product_id)
                        owned_crypto = True
                        held_crypto = {'product_id': product_id, 'purchase_price': purchase_price, 'time': current_time}
                        break  # Exit the loop after buying a cryptocurrency

            # Update the highest price and check sell condition for the owned cryptocurrency
            if owned_crypto and held_crypto:
                current_data = fetch_current_price_data(held_crypto['product_id'])
                if not current_data.empty and current_data['price'] > highest_price:
                    highest_price = current_data['price']

                if check_sell_condition(held_crypto['product_id'], held_crypto['purchase_price'], highest_price, held_crypto['time']):
                    execute_sell_order(held_crypto['product_id'])
                    owned_crypto = False
                    held_crypto = None
                    highest_price = 0  # Reset the highest price

            time.sleep(1)  # Sleep to avoid high CPU usage and hitting rate limits

        except Exception as e:
            logging.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    main()

