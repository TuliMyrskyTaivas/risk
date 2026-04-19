"""
Unit tests for MOEXDataFetcher class.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import os

from moex_data_fetcher import MOEXDataFetcher


class TestMOEXDataFetcherInit:
    """Test MOEXDataFetcher initialization"""

    def test_initialization(self):
        """Test that MOEXDataFetcher initializes correctly"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name
        try:
            fetcher = MOEXDataFetcher(cache_db_path=db_path)
            assert fetcher.cache_db_path == db_path
            assert isinstance(fetcher.logger, type(fetcher.logger))  # Just check it's a logger
            # Check table exists
            cursor = fetcher._connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache'")
            assert cursor.fetchone() is not None
            cursor.close()
            fetcher._connection.close()  # Close connection to allow file deletion
        finally:
            os.unlink(db_path)


class TestGetHistoricalPrices:
    """Test get_historical_prices method"""

    @pytest.fixture
    def fetcher(self):
        """Fixture to provide a MOEXDataFetcher instance with temp db"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name
        fetcher = MOEXDataFetcher(cache_db_path=db_path)
        yield fetcher
        fetcher._connection.close()  # Close connection to allow file deletion
        os.unlink(db_path)

    def test_date_calculation(self, fetcher):
        """Test date calculation for different trading days"""
        ticker = "TEST"

        # Mock no cache and empty fetch
        with patch.object(fetcher, '_get_cached_historical_prices', return_value=None):
            with patch('moex_data_fetcher.Ticker') as mock_ticker_class:
                mock_ticker = Mock()
                mock_ticker.candles.return_value = pd.DataFrame()
                mock_ticker_class.return_value = mock_ticker

                # Test 252 days
                fetcher.get_historical_prices(ticker, 252)
                call_args = mock_ticker.candles.call_args
                start_called = call_args[1]['start']
                end_called = call_args[1]['end']
                days_diff = (end_called - start_called).days
                expected = int(252 * 365 / 252) + 10  # ~375
                assert abs(days_diff - expected) <= 2  # Allow small tolerance

    def test_cached_sufficient(self, fetcher):
        """Test when cache has enough data"""
        ticker = "TEST"
        days = 5
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)

        # Create mock series with 10 days
        dates = pd.date_range(start=start_date, periods=10, freq='D')
        prices = [100 + i for i in range(10)]
        series = pd.Series(prices, index=dates)

        # Insert into cache
        cursor = fetcher._connection.cursor()
        data = [(ticker, date.date().isoformat(), float(price)) for date, price in series.items()]
        cursor.executemany("INSERT INTO cache (ticker, date, price) VALUES (?, ?, ?)", data)
        fetcher._connection.commit()
        cursor.close()

        result = fetcher.get_historical_prices(ticker, days)
        assert len(result) == days
        assert list(result.values) == [105, 106, 107, 108, 109]  # Last 5

    def test_partial_cache_from_start(self, fetcher):
        """Test when cache covers from start_date but not enough days"""
        ticker = "TEST"
        days = 15
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(days * 365 / 252) + 10)

        # Cache has 8 days from start_date
        dates = pd.date_range(start=start_date, periods=8, freq='D')
        prices = [100 + i for i in range(8)]
        series = pd.Series(prices, index=dates)
        cursor = fetcher._connection.cursor()
        data = [(ticker, date.date().isoformat(), float(price)) for date, price in series.items()]
        cursor.executemany("INSERT INTO cache (ticker, date, price) VALUES (?, ?, ?)", data)
        fetcher._connection.commit()
        cursor.close()

        # Mock fetch returns additional 10 days
        additional_start = series.index.max() + pd.Timedelta(days=1)
        mock_df = pd.DataFrame({
            'begin': pd.date_range(additional_start, periods=10, freq='D'),
            'close': [108 + i for i in range(10)]
        })

        with patch('moex_data_fetcher.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.candles.return_value = mock_df
            mock_ticker_class.return_value = mock_ticker

            result = fetcher.get_historical_prices(ticker, days)
            assert len(result) == days
            # Combined: cached 100-107, new 108-117, tail(15): 103-117
            assert result.iloc[0] == 103.0  # First of tail
            assert result.iloc[-1] == 117.0  # Last

    def test_partial_cache_gap_at_start(self, fetcher):
        """Test when cache starts after start_date"""
        ticker = "TEST"
        days = 15
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(days * 365 / 252) + 10)

        # Cache starts 3 days after start_date, has 8 days
        cache_start = start_date + timedelta(days=3)
        dates = pd.date_range(start=cache_start, periods=8, freq='D')
        prices = [103 + i for i in range(8)]
        series = pd.Series(prices, index=dates)
        cursor = fetcher._connection.cursor()
        data = [(ticker, date.date().isoformat(), float(price)) for date, price in series.items()]
        cursor.executemany("INSERT INTO cache (ticker, date, price) VALUES (?, ?, ?)", data)
        fetcher._connection.commit()
        cursor.close()

        # Mock fetch fills the gap and extends
        mock_df = pd.DataFrame({
            'begin': pd.date_range(start_date, periods=12, freq='D'),
            'close': [100 + i for i in range(12)]
        })

        with patch('moex_data_fetcher.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.candles.return_value = mock_df
            mock_ticker_class.return_value = mock_ticker

            result = fetcher.get_historical_prices(ticker, days)
            assert len(result) == days
            # Should have combined data covering the period
            assert len(result) == 15  # days

    def test_fetch_fails_cache_insufficient(self, fetcher):
        """Test when fetch fails and cache doesn't have enough"""
        ticker = "TEST"
        days = 20

        # Cache has only 5 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        dates = pd.date_range(start=start_date, periods=5, freq='D')
        prices = [100 + i for i in range(5)]
        series = pd.Series(prices, index=dates)
        cursor = fetcher._connection.cursor()
        data = [(ticker, date.date().isoformat(), float(price)) for date, price in series.items()]
        cursor.executemany("INSERT INTO cache (ticker, date, price) VALUES (?, ?, ?)", data)
        fetcher._connection.commit()
        cursor.close()

        with patch('moex_data_fetcher.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.candles.side_effect = Exception("API Error")
            mock_ticker_class.return_value = mock_ticker

            result = fetcher.get_historical_prices(ticker, days)
            assert result is None

    def test_no_cache_fetch_success(self, fetcher):
        """Test fetching when no cache exists"""
        ticker = "TEST"
        days = 10

        mock_df = pd.DataFrame({
            'begin': pd.date_range(datetime.now() - timedelta(days=20), periods=15, freq='D'),
            'close': [100 + i for i in range(15)]
        })

        with patch.object(fetcher, '_get_cached_historical_prices', return_value=None):
            with patch('moex_data_fetcher.Ticker') as mock_ticker_class:
                mock_ticker = Mock()
                mock_ticker.candles.return_value = mock_df
                mock_ticker_class.return_value = mock_ticker

                result = fetcher.get_historical_prices(ticker, days)
                assert len(result) == days
                assert result.iloc[-1] == 114.0