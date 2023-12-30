import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
from src.main import (
    fetch_historical_data,
    fetch_current_price_data,
    fetch_last_checked_price,
    get_available_products,
    check_and_execute_buy
)


class TestCryptoBot(unittest.TestCase):

    @patch('src.main.requests.get')  # Updated patch path
    def test_fetch_historical_data_success(self, mock_get):
        # Mock the response from the API call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [1609459200, 29000, 29500, 29300, 29400, 100.0],  # Sample data
            # ... more sample data
        ]
        mock_get.return_value = mock_response

        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()
        granularity = 300
        product_id = 'BTC-USD'

        # Call the function with the mocked API response
        data = fetch_historical_data(product_id, start_time, end_time, granularity)

        # Assertions to verify function behavior
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)
        self.assertFalse(data.empty)
        # ... more assertions as needed

    # add more test methods here to test different scenarios


@patch('src.main.requests.get')  # Patch the 'requests.get' call within 'fetch_current_price_data' function
def test_fetch_current_price_data_success(self, mock_get):
    # Mock the response from the API call
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'price': '50000.0'  # Sample price data
    }
    mock_get.return_value = mock_response

    product_id = 'BTC-USD'

    # Call the function with the mocked API response
    price = fetch_current_price_data(product_id)

    # Assertions to verify function behavior
    self.assertIsNotNone(price)
    self.assertEqual(price, 50000.0)  # Assert that the returned price is as expected

@patch('src.main.pd.read_csv')
def test_fetch_last_checked_price_success(self, mock_read_csv):
    # Mock reading from a CSV file
    mock_read_csv.return_value = pd.DataFrame({
        'product_id': ['BTC-USD', 'ETH-USD'],
        'close': [45000.0, 3000.0]
    })

    product_id = 'BTC-USD'
    # Call the function
    last_checked_price = fetch_last_checked_price(product_id)

    # Assertions to verify function behavior
    self.assertEqual(last_checked_price, 45000.0)

@patch('src.main.requests.get')
def test_get_available_products_success(self, mock_get):
    # Mock the API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'id': 'BTC-USD', 'trading_disabled': False},
        {'id': 'ETH-USD', 'trading_disabled': True},  # This product should be filtered out
    ]
    mock_get.return_value = mock_response

    # Call the function
    available_products = get_available_products()

    # Assertions to verify function behavior
    self.assertIn('BTC-USD', available_products)
    self.assertNotIn('ETH-USD', available_products)  # ETH-USD should not be in the list because trading is disabled



if __name__ == '__main__':
    unittest.main()
