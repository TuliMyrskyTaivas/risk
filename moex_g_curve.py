import numpy as np
import pandas as pd
import requests
import logging

class MOEX_G_Curve:
    def __init__(self):
        self.logger = logging.getLogger('PortfolioAnalyzer')
    
    def fetch_risk_free_rate(self, maturity_years : float = 1.0) -> float:
        """
        Fetch the current risk-free rate (OFZ zero-coupon yield) from MOEX.
    
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
        risk_free_rate = self._calculate_zero_coupon_yield(
            maturity_years, beta0, beta1, beta2, tau, g_values
        )

        self.logger.info(f"Risk-free rate data from MOEX as of {trade_date} {trade_time} is {risk_free_rate}")        
        return risk_free_rate
    
    def _calculate_zero_coupon_yield(self, t : float, beta0 : float, beta1 : float, beta2 : float, tau : float, g_values : list[float]) -> float:
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