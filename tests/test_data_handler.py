import unittest
from unittest.mock import patch

import pandas as pd

from ai_trader.data_handler import DataHandler


class DataHandlerTestCase(unittest.TestCase):
    @patch("requests.Session.get")
    def test_fetch_candles(self, mock_get):
        mock_get.return_value.json.return_value = {
            "data": [
                ["1", "10", "12", "8", "11", "100"],
                ["2", "11", "13", "9", "12", "110"],
            ]
        }
        mock_get.return_value.raise_for_status.return_value = None

        handler = DataHandler("BTCUSDT")
        df = handler.fetch_candles(limit=2)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("close", df.columns)


if __name__ == "__main__":
    unittest.main()
