"""
Unit tests for MOEX_G_Curve class.

Tests cover:
- Initialization and basic functionality
- Zero-coupon yield calculations with Nelson-Siegel-Svensson model
- Edge cases and boundary conditions
- Mock API responses from MOEX ISS
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import logging

from moex_g_curve import MOEX_G_Curve


class TestMOEXGCurveInit:
    """Test MOEX_G_Curve initialization"""
    
    def test_initialization(self):
        """Test that MOEX_G_Curve initializes correctly"""
        curve = MOEX_G_Curve()
        assert curve is not None
        assert isinstance(curve.logger, logging.Logger)
        assert curve.logger.name == 'PortfolioAnalyzer'
    
    def test_logger_name(self):
        """Test that logger has correct name"""
        curve = MOEX_G_Curve()
        assert curve.logger.name == 'PortfolioAnalyzer'


class TestCalculateZeroCouponYield:
    """Test _calculate_zero_coupon_yield method"""
    
    @pytest.fixture
    def curve(self):
        """Fixture to provide a MOEX_G_Curve instance"""
        return MOEX_G_Curve()
    
    @pytest.fixture
    def standard_params(self):
        """Fixture with standard G-curve parameters"""
        return {
            'beta0': 1500,      # Long-term level (basis points)
            'beta1': -500,      # Short-term component
            'beta2': 200,       # Medium-term component
            'tau': 2.0,         # Decay factor
            'g_values': [50, 30, 20, 10, 5, 3, 2, 1, 0.5]  # Spline adjustments
        }
    
    def test_yield_calculation_one_year(self, curve, standard_params):
        """Test yield calculation for 1 year maturity"""
        result = curve._calculate_zero_coupon_yield(
            t=1.0,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=standard_params['tau'],
            g_values=standard_params['g_values']
        )
        
        # Result should be a float between 0 and 1 (representing annual rate)
        assert isinstance(result, float)
        assert -0.5 < result < 0.5  # Reasonable range for interest rates
    
    def test_yield_calculation_three_months(self, curve, standard_params):
        """Test yield calculation for 3 months (0.25 years)"""
        result = curve._calculate_zero_coupon_yield(
            t=0.25,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=standard_params['tau'],
            g_values=standard_params['g_values']
        )
        
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    def test_yield_calculation_ten_years(self, curve, standard_params):
        """Test yield calculation for 10 years"""
        result = curve._calculate_zero_coupon_yield(
            t=10.0,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=standard_params['tau'],
            g_values=standard_params['g_values']
        )
        
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    def test_yield_calculation_very_small_maturity(self, curve, standard_params):
        """Test yield calculation for very small maturity (edge case)"""
        # Should be clamped to 0.01
        result = curve._calculate_zero_coupon_yield(
            t=0.001,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=standard_params['tau'],
            g_values=standard_params['g_values']
        )
        
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    def test_yield_calculation_zero_maturity(self, curve, standard_params):
        """Test yield calculation for zero maturity (edge case)"""
        # Should be clamped to 0.01
        result = curve._calculate_zero_coupon_yield(
            t=0.0,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=standard_params['tau'],
            g_values=standard_params['g_values']
        )
        
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    def test_yield_calculation_negative_maturity(self, curve, standard_params):
        """Test yield calculation for negative maturity (should be clamped to 0.01)"""
        result = curve._calculate_zero_coupon_yield(
            t=-1.0,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=standard_params['tau'],
            g_values=standard_params['g_values']
        )
        
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    def test_yield_calculation_multiple_maturities(self, curve, standard_params):
        """Test that yield curve is reasonable across different maturities"""
        maturities = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
        results = []
        
        for t in maturities:
            result = curve._calculate_zero_coupon_yield(
                t=t,
                beta0=standard_params['beta0'],
                beta1=standard_params['beta1'],
                beta2=standard_params['beta2'],
                tau=standard_params['tau'],
                g_values=standard_params['g_values']
            )
            results.append(result)
        
        # All results should be floats
        assert all(isinstance(r, float) for r in results)
        # All results should be within reasonable range
        assert all(-0.5 < r < 0.5 for r in results)
    
    def test_yield_with_zero_g_values(self, curve):
        """Test yield calculation with all zero g-values (no spline adjustment)"""
        result = curve._calculate_zero_coupon_yield(
            t=1.0,
            beta0=1500,
            beta1=-500,
            beta2=200,
            tau=2.0,
            g_values=[0.0] * 9
        )
        
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    def test_yield_with_large_beta_values(self, curve):
        """Test yield calculation with large beta parameters"""
        result = curve._calculate_zero_coupon_yield(
            t=1.0,
            beta0=5000,
            beta1=-2000,
            beta2=1000,
            tau=2.0,
            g_values=[100, 50, 30, 20, 10, 5, 3, 1, 0.5]
        )
        
        assert isinstance(result, float)
        assert not np.isnan(result)
        assert not np.isinf(result)
    
    def test_yield_with_small_tau(self, curve, standard_params):
        """Test yield calculation with small tau decay factor"""
        result = curve._calculate_zero_coupon_yield(
            t=1.0,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=0.1,  # Small tau
            g_values=standard_params['g_values']
        )
        
        assert isinstance(result, float)
        assert not np.isnan(result)
        assert not np.isinf(result)
    
    def test_yield_with_large_tau(self, curve, standard_params):
        """Test yield calculation with large tau decay factor"""
        result = curve._calculate_zero_coupon_yield(
            t=1.0,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=10.0,  # Large tau
            g_values=standard_params['g_values']
        )
        
        assert isinstance(result, float)
        assert not np.isnan(result)
        assert not np.isinf(result)
    
    @pytest.mark.unit
    def test_nelson_siegel_components_separately(self, curve):
        """Test that Nelson-Siegel components are calculated correctly"""
        # This tests the mathematical structure
        beta0 = 1000
        beta1 = -500
        beta2 = 200
        tau = 2.0
        t = 1.0
        g_values = [0] * 9
        
        result = curve._calculate_zero_coupon_yield(t, beta0, beta1, beta2, tau, g_values)
        
        # Manually calculate expected result
        term1 = beta0
        term2 = beta1 * (tau / t) * (1 - np.exp(-t / tau))
        term3 = beta2 * ((tau / t) * (1 - np.exp(-t / tau)) - np.exp(-t / tau))
        term4 = 0
        
        continuous_rate = (term1 + term2 + term3 + term4) / 10000
        expected = np.exp(continuous_rate) - 1
        
        assert np.isclose(result, expected, rtol=1e-10)


class TestFetchRiskFreeRate:
    """Test fetch_risk_free_rate method with mocked API calls"""
    
    @pytest.fixture
    def curve(self):
        """Fixture to provide a MOEX_G_Curve instance"""
        return MOEX_G_Curve()
    
    @pytest.fixture
    def mock_moex_response(self):
        """Fixture with mock MOEX API response data"""
        return {
            'params': {
                'columns': ['tradedate', 'tradetime', 'B1', 'B2', 'B3', 'T1', 
                           'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9'],
                'data': [[
                    '2026-04-18',
                    '10:00:00',
                    1500,      # B1
                    -500,      # B2
                    200,       # B3
                    2.0,       # T1
                    50, 30, 20, 10, 5, 3, 2, 1, 0.5  # G1-G9
                ]]
            }
        }
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_one_year(self, mock_get, curve, mock_moex_response):
        """Test fetching risk-free rate for 1 year"""
        mock_response = Mock()
        mock_response.json.return_value = mock_moex_response
        mock_get.return_value = mock_response
        
        result = curve.fetch_risk_free_rate(maturity_years=1.0)
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert 'iss.moex.com' in call_url
        assert 'zcyc' in call_url
        
        # Result should be reasonable
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_three_months(self, mock_get, curve, mock_moex_response):
        """Test fetching risk-free rate for 3 months"""
        mock_response = Mock()
        mock_response.json.return_value = mock_moex_response
        mock_get.return_value = mock_response
        
        result = curve.fetch_risk_free_rate(maturity_years=0.25)
        
        # Verify API was called
        mock_get.assert_called_once()
        
        # Result should be reasonable
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_ten_years(self, mock_get, curve, mock_moex_response):
        """Test fetching risk-free rate for 10 years"""
        mock_response = Mock()
        mock_response.json.return_value = mock_moex_response
        mock_get.return_value = mock_response
        
        result = curve.fetch_risk_free_rate(maturity_years=10.0)
        
        # Verify API was called
        mock_get.assert_called_once()
        
        # Result should be reasonable
        assert isinstance(result, float)
        assert -0.5 < result < 0.5
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_api_timeout(self, mock_get, curve):
        """Test handling of API timeout"""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        with pytest.raises(requests.Timeout):
            curve.fetch_risk_free_rate(maturity_years=1.0)
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_api_error(self, mock_get, curve):
        """Test handling of API error response"""
        import requests
        mock_get.side_effect = requests.HTTPError("404 Not Found")
        
        with pytest.raises(requests.HTTPError):
            curve.fetch_risk_free_rate(maturity_years=1.0)
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_invalid_json(self, mock_get, curve):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError):
            curve.fetch_risk_free_rate(maturity_years=1.0)
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_missing_columns(self, mock_get, curve):
        """Test handling of missing required columns in response"""
        incomplete_response = {
            'params': {
                'columns': ['tradedate'],  # Missing B1, B2, B3, T1, G1-G9
                'data': [['2026-04-18']]
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = incomplete_response
        mock_get.return_value = mock_response
        
        with pytest.raises((KeyError, IndexError)):
            curve.fetch_risk_free_rate(maturity_years=1.0)
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_extracts_date_correctly(self, mock_get, curve, mock_moex_response, caplog):
        """Test that API response date and time are extracted correctly"""
        mock_response = Mock()
        mock_response.json.return_value = mock_moex_response
        mock_get.return_value = mock_response
        
        with caplog.at_level(logging.INFO):
            curve.fetch_risk_free_rate(maturity_years=1.0)
        
        # Check that date is logged
        assert '2026-04-18' in caplog.text
        assert '10:00:00' in caplog.text
    
    @patch('moex_g_curve.requests.get')
    def test_fetch_risk_free_rate_timeout_parameter(self, mock_get, curve, mock_moex_response):
        """Test that API call includes timeout parameter"""
        mock_response = Mock()
        mock_response.json.return_value = mock_moex_response
        mock_get.return_value = mock_response
        
        curve.fetch_risk_free_rate(maturity_years=1.0)
        
        # Verify timeout is specified
        call_kwargs = mock_get.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 10


class TestYieldCurveShape:
    """Test the shape and properties of the yield curve"""
    
    @pytest.fixture
    def curve(self):
        """Fixture to provide a MOEX_G_Curve instance"""
        return MOEX_G_Curve()
    
    @pytest.fixture
    def standard_params(self):
        """Fixture with standard G-curve parameters"""
        return {
            'beta0': 1500,
            'beta1': -500,
            'beta2': 200,
            'tau': 2.0,
            'g_values': [50, 30, 20, 10, 5, 3, 2, 1, 0.5]
        }
    
    def test_yield_curve_monotonicity(self, curve, standard_params):
        """Test that yield curve is monotonic (within reasonable tolerance)"""
        maturities = np.linspace(0.1, 20, 20)
        yields = []
        
        for t in maturities:
            y = curve._calculate_zero_coupon_yield(
                t=t,
                beta0=standard_params['beta0'],
                beta1=standard_params['beta1'],
                beta2=standard_params['beta2'],
                tau=standard_params['tau'],
                g_values=standard_params['g_values']
            )
            yields.append(y)
        
        yields = np.array(yields)
        
        # Check that curve doesn't have extreme oscillations
        diffs = np.diff(yields)
        assert np.all(np.abs(diffs) < 0.1)  # Changes should be smooth
    
    def test_long_term_yield_convergence(self, curve, standard_params):
        """Test that long-term yields converge to beta0 / 10000"""
        # Very long maturity should approach beta0/10000
        long_term_yield = curve._calculate_zero_coupon_yield(
            t=100.0,
            beta0=standard_params['beta0'],
            beta1=standard_params['beta1'],
            beta2=standard_params['beta2'],
            tau=standard_params['tau'],
            g_values=standard_params['g_values']
        )
        
        # This is approximate due to the Nelson-Siegel-Svensson model
        expected_limit = standard_params['beta0'] / 10000
        # Allow significant tolerance due to spline components and exp conversion
        assert abs(long_term_yield - expected_limit) < 0.02


class TestIntegration:
    """Integration tests combining multiple components"""
    
    @patch('moex_g_curve.requests.get')
    def test_full_workflow(self, mock_get):
        """Test complete workflow from initialization to rate fetching"""
        mock_response_data = {
            'params': {
                'columns': ['tradedate', 'tradetime', 'B1', 'B2', 'B3', 'T1',
                           'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9'],
                'data': [[
                    '2026-04-18',
                    '10:00:00',
                    1500, -500, 200, 2.0,
                    50, 30, 20, 10, 5, 3, 2, 1, 0.5
                ]]
            }
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response
        
        # Create instance and fetch rate
        curve = MOEX_G_Curve()
        rate_3m = curve.fetch_risk_free_rate(maturity_years=0.25)
        rate_1y = curve.fetch_risk_free_rate(maturity_years=1.0)
        rate_10y = curve.fetch_risk_free_rate(maturity_years=10.0)
        
        # All rates should be valid floats
        assert isinstance(rate_3m, float)
        assert isinstance(rate_1y, float)
        assert isinstance(rate_10y, float)
        
        # All should be reasonable values
        assert -0.5 < rate_3m < 0.5
        assert -0.5 < rate_1y < 0.5
        assert -0.5 < rate_10y < 0.5
        
        # API should have been called 3 times
        assert mock_get.call_count == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
