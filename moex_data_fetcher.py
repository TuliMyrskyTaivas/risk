from moexalgo import Ticker
from datetime import datetime, timedelta
from typing import Final, Optional
import pandas as pd
import sqlite3
import logging

class MOEXDataFetcher:
    """Class to fetch data from Moscow Exchange (MOEX)"""

    def __init__(self, cache_db_path: str = "cache.db"):
        self.logger = logging.getLogger('PortfolioAnalyzer')
        self.cache_db_path = cache_db_path        
        self._connection = sqlite3.connect(self.cache_db_path, check_same_thread=False)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            "ticker TEXT NOT NULL,"
            "date TEXT NOT NULL,"
            "price REAL NOT NULL,"
            "PRIMARY KEY(ticker, date)"
            ")"
        )
        self._connection.commit()    

    def _get_latest_cached_price(self, ticker: str) -> Optional[tuple[datetime, float]]:
        cursor = self._connection.cursor()
        cursor.execute(
            "SELECT date, price FROM cache "
            "WHERE ticker = ? "
            "ORDER BY date DESC LIMIT 1",
            (ticker,),
        )
        row = cursor.fetchone()
        cursor.close()
        return (datetime.fromisoformat(row[0]), float(row[1])) if row else None

    def _get_cached_historical_prices(
        self, ticker: str, start_date: datetime, end_date: datetime
    ) -> Optional[pd.Series]:
        cursor = self._connection.cursor()
        cursor.execute(
            "SELECT date, price FROM cache "
            "WHERE ticker = ? AND date BETWEEN ? AND ? "
            "ORDER BY date ASC",
            (
                ticker,
                start_date.date().isoformat(),
                end_date.date().isoformat(),
            ),
        )
        rows = cursor.fetchall()
        cursor.close()
        if not rows:
            return None
        dates = [row[0] for row in rows]
        values = [row[1] for row in rows]
        return pd.Series(values, index=pd.to_datetime(dates))    

    def get_current_price(self, ticker: str) -> Optional[float]:
        cache_entry = self._get_latest_cached_price(ticker)
        if cache_entry is not None and cache_entry[0] >= datetime.now() - timedelta(days=1):  
            self.logger.debug(f"Using cached price for {ticker} from {cache_entry[0].isoformat()}: {cache_entry[1]} RUB")          
            return cache_entry[1]

        try:
            ticker_obj = Ticker(ticker)
            start = datetime.now() - timedelta(days=5)
            end = datetime.now()
            self.logger.debug(f"Fetching current price for {ticker} from MOEX in range {start} to {end}")

            df : pd.DataFrame = ticker_obj.candles(start=start, end=end, period="1D") 
            if not df.empty:
                latest_price = df.iloc[-1]["close"]                
                return float(latest_price)
            return None
        except Exception as e:
            self.logger.error(f"Error fetching price for {ticker} from MOEX: {e}")
            return None

    def get_historical_prices(self, ticker: str, days: int = 252) -> Optional[pd.Series]:
        """Fetch historical prices for a given ticker"""
        self.logger.debug(f"Requesting historical prices for {ticker} for the last {days} days")
        end_date = datetime.now()
        # Calculate calendar days needed to cover the requested trading days
        # Assuming ~252 trading days per year and 365 calendar days
        TRADING_DAYS_PER_YEAR: Final[int] = 252
        CALENDAR_DAYS_PER_YEAR: Final[int] = 365
        calendar_days: Final[int] = int(days * CALENDAR_DAYS_PER_YEAR / TRADING_DAYS_PER_YEAR) + 10  # Add buffer for holidays/weekends
        start_date = end_date - timedelta(days=calendar_days)

        cached_series = self._get_cached_historical_prices(ticker, start_date, end_date)
        if cached_series is not None and len(cached_series) >= days:
            self.logger.debug(f"Using cached historical prices for {ticker} from {cached_series.index.min().date()} to {cached_series.index.max().date()}")
            return cached_series.tail(days)

        # Determine what to fetch
        if cached_series is None or cached_series.empty:
            fetch_start = start_date
        else:
            fetch_start = cached_series.index.max() + pd.Timedelta(days=1)

        # Ensure that cached_series covers the required range
        if cached_series is not None and not cached_series.empty:
            if cached_series.index.min() > start_date:
                fetch_start = start_date
            else:
                fetch_start = cached_series.index.max() + pd.Timedelta(days=1)

        fetch_end = end_date
        self.logger.debug(f"Cached historical prices for {ticker} cover from {cached_series.index.min().date() if cached_series is not None and not cached_series.empty else 'N/A'} to {cached_series.index.max().date() if cached_series is not None and not cached_series.empty else 'N/A'}")
        self.logger.debug(f"Need to fetch historical prices for {ticker} from {fetch_start.date()} to {fetch_end.date()}")

        if fetch_start >= fetch_end:
            # already have enough
            return cached_series.tail(days) if cached_series is not None else None

        # Fetch the missing part
        try:
            ticker_obj = Ticker(ticker)
            df : Optional[pd.DataFrame] = ticker_obj.candles(start=fetch_start, end=fetch_end, period="1D")
            if df is not None and not df.empty:
                df["begin"] = pd.to_datetime(df["begin"])
                df = df.set_index("begin").sort_index()
                new_prices = df["close"]
                # Combine with cached
                if cached_series is not None:
                    combined = pd.concat([cached_series, new_prices]).sort_index()
                    combined = combined[~combined.index.duplicated(keep='last')] # Remove duplicates if any
                else:
                    combined = new_prices

                # Cache the new prices
                data_to_insert = [(ticker, date.date().isoformat(), float(price)) for date, price in new_prices.items()]
                self.logger.debug(f"Caching {len(data_to_insert)} new historical prices for {ticker} from {fetch_start.date()} to {fetch_end.date()}")
                cursor = self._connection.cursor()
                cursor.executemany(
                    "INSERT OR REPLACE INTO cache (ticker, date, price) VALUES (?, ?, ?)",
                    data_to_insert
                )
                self._connection.commit()
                cursor.close()
                return combined.tail(days)
            else:
                return cached_series.tail(days) if cached_series is not None and len(cached_series) >= days else None
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {ticker}: {e}")
            return None