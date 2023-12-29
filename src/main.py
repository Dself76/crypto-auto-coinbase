import requests
import logging
import json
import base64
import hmac
import hashlib
import time
from datetime import datetime, timedelta
import pandas as pd
import os



# Configure logging to write to a file
logging.basicConfig(filename='bot_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Replace with  Coinbase Pro API creds when ready after mock test passes
API_KEY = 'API_KEY'
API_SECRET = 'API_SECRET'
API_PASSPHRASE = 'API_PASSPHRASE'

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

            # Append data to CSV
            append_to_csv(data, 'historical_data.csv')

            return data
        else:
            logging.warning(f"Failed to fetch historical data for {product_id}: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error fetching historical data for {product_id}: {e}")
        return pd.DataFrame()

def fetch_current_price_data(product_id):
    try:
        endpoint = f'/products/{product_id}/ticker'
        headers = create_request_headers(endpoint, 'GET')
        response = requests.get(API_URL + endpoint, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return float(data['price'])  # Assuming the response contains a 'price' field
        else:
            logging.warning(f"Failed to fetch current price for {product_id}: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching current price for {product_id}: {e}")
        return None




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

def append_to_csv(data, file_name):
    """
    Appends a DataFrame to a CSV file. Creates the file if it does not exist.

    :param data: DataFrame to append
    :param file_name: Name of the CSV file
    """
    try:
        # Check if the file exists
        file_exists = os.path.isfile(file_name)

        # Append data to the CSV file; create a new file if it doesn't exist
        data.to_csv(file_name, mode='a', header=not file_exists, index=False)
        logging.info(f"Data appended to {file_name}")
    except Exception as e:
        logging.error(f"Error appending data to CSV: {e}")


def check_and_execute_buy(product_id, last_checked_price):
    try:
        now = datetime.now()

        # Checking buy conditions
        # You may adjust or add more conditions as needed
        is_buy_condition_met = False

        # Condition 1: 10% increase over the past 2 hours
        start_time_2h = now - timedelta(hours=2)
        historical_data_2h = fetch_historical_data(product_id, start_time_2h, now)
        if not historical_data_2h.empty:
            price_increase_2h = (historical_data_2h['close'].iloc[-1] - historical_data_2h['open'].iloc[0]) / \
                                historical_data_2h['open'].iloc[0] * 100
            if price_increase_2h >= 10:
                is_buy_condition_met = True

        # Condition 2: 10% increase over the past 1 hour
        start_time_1h = now - timedelta(hours=1)
        historical_data_1h = fetch_historical_data(product_id, start_time_1h, now)
        if not historical_data_1h.empty:
            price_increase_1h = (historical_data_1h['close'].iloc[-1] - historical_data_1h['open'].iloc[0]) / \
                                historical_data_1h['open'].iloc[0] * 100
            if price_increase_1h >= 10:
                is_buy_condition_met = True

        # Condition 3: 5% increase since the last API call
        current_price = fetch_current_price_data(product_id)
        if current_price is not None and last_checked_price is not None:
            price_increase_since_last_check = (current_price - last_checked_price) / last_checked_price * 100
            if price_increase_since_last_check >= 5:
                is_buy_condition_met = True

        # If any buy condition is met, execute buy order
        if is_buy_condition_met:
            global held_crypto, owned_crypto
            # Execute buy order logic
            # Define the amount to buy or the funds to use
            buy_order_data = {
                'type': 'market',
                'product_id': product_id,
                'funds': 'FIAT_AMOUNT_TO_SPEND'  # Replace with the fiat amount you want to spend
            }

            endpoint = '/orders'
            body = json.dumps(buy_order_data)
            headers = create_request_headers(endpoint, 'POST', body)
            response = requests.post(API_URL + endpoint, headers=headers, data=body)

            if response.status_code == 200:
                response_data = response.json()
                # Assuming response contains the amount of crypto bought
                amount_bought = response_data['filled_size']
                purchase_price = response_data['executed_value'] / amount_bought

                # Update held_crypto
                held_crypto = {
                    'product_id': product_id,
                    'purchase_price': purchase_price,
                    'amount': amount_bought,
                    'time': datetime.now()
                }

                # Append order details to CSV
                order_details_df = pd.DataFrame([{
                    'product_id': product_id,
                    'purchase_price': purchase_price,
                    'amount_bought': amount_bought,
                    'time': datetime.now()
                }])
                append_to_csv(order_details_df, 'buy_orders.csv')

                logging.info(f"Successfully executed buy order for {product_id}: Bought {amount_bought} units at {purchase_price} each.")
            else:
                logging.warning(f"Failed to execute buy order for {product_id}: {response.status_code}, Response: {response.text}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    return False



def check_sell_condition(product_id, purchase_price, highest_price, previous_price, purchase_time):
    current_data = fetch_current_price_data(product_id)  # Implement this function to get the current price
    if current_data.empty:
        return False

    current_price = current_data['price']
    price_drop_from_previous = (current_price - previous_price) / previous_price * 100
    price_drop_from_highest = (current_price - highest_price) / highest_price * 100
    price_gain_from_purchase = (current_price - purchase_price) / purchase_price * 100

    # Check the selling conditions
    if price_drop_from_previous <= -5 or price_drop_from_highest <= -5 or price_gain_from_purchase >= 25:
        return True
    return False

def execute_sell_order():
    global held_crypto, owned_crypto

    # Check if there's any cryptocurrency held
    if not owned_crypto or not held_crypto:
        logging.info("No cryptocurrency currently held to sell.")
        return

    product_id = held_crypto['product_id']
    amount_to_sell = held_crypto['amount']  # Amount of cryptocurrency to sell

    try:
        sell_order_data = {
            'type': 'market',
            'product_id': product_id,
            'size': str(amount_to_sell)
        }
        endpoint = '/orders'
        body = json.dumps(sell_order_data)
        headers = create_request_headers(endpoint, 'POST', body)
        response = requests.post(API_URL + endpoint, headers=headers, data=body)

        if response.status_code == 200:
            response_data = response.json()
            logging.info(f"Successfully executed sell order for {product_id}: Sold {amount_to_sell} units.")

            # Append order details to CSV
            order_details_df = pd.DataFrame([{
                'product_id': product_id,
                'amount_sold': amount_to_sell,
                'time': datetime.now(),
                # Include other relevant details from response_data if needed
            }])
            append_to_csv(order_details_df, 'sell_orders.csv')

            # Resetting owned_crypto and held_crypto after successful sell
            owned_crypto = False
            held_crypto = None
        else:
            logging.warning(f"Failed to execute sell order for {product_id}: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logging.error(f"Error executing sell order for {product_id}: {e}")

def rate_limiter():
    """
    Ensures that the requests do not exceed 20 per second. limit is 30 but this is safe
    """
    time.sleep(1 / 20)
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
                    rate_limiter()  # Apply rate limiting here
                    if check_buy_condition(product_id):
                        execute_buy_order(product_id)
                        owned_crypto = True
                        held_crypto = {'product_id': product_id, 'purchase_price': purchase_price, 'time': current_time}
                        break  # Exit the loop after buying a cryptocurrency

            # Update the highest price and check sell condition for the owned cryptocurrency
            if owned_crypto and held_crypto:
                rate_limiter()  # Apply rate limiting here
                current_data = fetch_current_price_data(held_crypto['product_id'])
                if not current_data.empty and current_data['price'] > highest_price:
                    highest_price = current_data['price']

                if check_sell_condition(held_crypto['product_id'], held_crypto['purchase_price'], highest_price, held_crypto['time']):
                    execute_sell_order(held_crypto['product_id'])
                    owned_crypto = False
                    held_crypto = None
                    highest_price = 0  # Reset the highest price

            time.sleep(1)  # Sleep to avoid to much CPU usage and hitting rate limits

        except Exception as e:
            logging.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    main()


