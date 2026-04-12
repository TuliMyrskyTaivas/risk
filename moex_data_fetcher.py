from moexalgo import Ticker
from datetime import datetime, timedelta
from typing import Optional
import requests
import pandas as pd
import numpy as np
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

    def _cache_price(self, ticker: str, date: str, price: float) -> None:
        self.logger.debug(f"Caching price for {ticker} on {date}: {price} RUB")
        cursor = self._connection.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (ticker, date, price) VALUES (?, ?, ?)",
            (ticker, date, price),
        )
        self._connection.commit()
        cursor.close()

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

            df : Optional[pd.DataFrame] = ticker_obj.candles(start=start, end=end, period="1D")
            if df is not None and not df.empty:
                latest_price = df.iloc[-1]["close"]
                now_iso = datetime.now().strftime("%Y-%m-%d")
                self._cache_price(ticker, now_iso, float(latest_price))
                return float(latest_price)
            return None
        except Exception as e:
            self.logger.error(f"Error fetching price for {ticker} from MOEX: {e}")
            return None

    def get_historical_prices(self, ticker: str, days: int = 252) -> Optional[pd.Series]:
        self.logger.debug(f"Requesting historical prices for {ticker} for the last {days} days")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 30)
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
            return self._get_cached_historical_prices(ticker, start_date, end_date)
        
    def fetch_russian_risk_free_rate(self, maturity_years : float = 1.0) -> float:
        """
        Fetch the current Russian risk-free rate (OFZ zero-coupon yield) from MOEX.
    
        Parameters:
        -----------
        maturity_years : float
            Time to maturity in years (e.g., 0.25 for 3 months, 1 for 1 year, 3 for 3 years)
            Available maturities: up to 30 years (limited by G1-G9 parameters)
    
        Returns:
        --------
        float : Risk-free rate as a decimal (e.g., 0.15 for 15%)
        """
    
        # URL for MOEX Zero-Coupon Yield Curve (G-Curve) API
        url = "https://iss.moex.com/iss/engines/stock/zcyc/securities.json"
    
        # Fetch data from MOEX ISS API
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract curve parameters from the response
        columns = data['params']['columns']
        values = data['params']['data']
        
        # Convert to DataFrame for easier handling
        df = pd.DataFrame(values, columns=columns)
        
        # Extract the Nelson-Siegel parameters [citation:1][citation:3]
        beta0 = float(df['B1'].values[0])   # Long-term level
        beta1 = float(df['B2'].values[0])   # Short-term component
        beta2 = float(df['B3'].values[0])   # Medium-term component
        tau = float(df['T1'].values[0])     # Decay factor
        
        # Extract G parameters (for the spline adjustment term)
        g_values : list[float] = []
        for i in range(1, 10):
            g_values.append(float(df[f'G{i}'].values[0]))
        
        # Get the date of this data
        trade_date = df['tradedate'].values[0]
        trade_time = df['tradetime'].values[0]
                        
        # Calculate the yield for the specified maturity
        risk_free_rate = self.calculate_zero_coupon_yield(
            maturity_years, beta0, beta1, beta2, tau, g_values
        )

        self.logger.info(f"Risk-free rate data from MOEX as of {trade_date} {trade_time} is {risk_free_rate}")        
        return risk_free_rate
    
    def calculate_zero_coupon_yield(self, t : float, beta0 : float, beta1 : float, beta2 : float, tau : float, g_values : list) -> float:
        """
        Calculate the zero-coupon yield using the MOEX G-Curve methodology.
        Based on the Nelson-Siegel-Svensson model with spline adjustment.
    
        Returns the continuously compounded rate, then converts to annual percentage.
        """
    
        # Handle t=0 edge case
        if t <= 0.01:
            t = 0.01
    
        # Nelson-Siegel-Svensson core components [citation:3]
        # Term 1: Long-term level component
        term1 = beta0
    
        # Term 2: Short-term component (exponential decay)
        if t > 0:
            term2 = beta1 * (tau / t) * (1 - np.exp(-t / tau))
        else:
            term2 = beta1
    
        # Term 3: Medium-term component (hump-shaped)
        if t > 0:
            term3 = beta2 * ((tau / t) * (1 - np.exp(-t / tau)) - np.exp(-t / tau))
        else:
            term3 = 0
    
        # Term 4: Spline adjustment for the G-curve (up to 9 knots)
        # Pre-calculated a_i and b_i values per MOEX methodology
        a_values : list[float] = [0, 0.6, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]  # Simplified
        b_values : list[float] = [0.6, 0.96, 1.536, 2.4576, 3.93216, 6.291456, 10.0663296, 16.10612736, 25.769803776]
    
        term4 : float = 0
        for i in range(9):
            term4 += g_values[i] * np.exp(-((t - a_values[i])**2) / (b_values[i]**2))
    
        # Combine all components
        # Note: MOEX divides by 10000 because values are stored in basis points [citation:3]
        continuous_rate : float = (term1 + term2 + term3 + term4) / 10000
    
        # Convert to annual percentage rate (effective annual yield)
        annual_rate = np.exp(continuous_rate) - 1
    
        return annual_rate