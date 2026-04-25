"""
Unit tests for risk.py

Tests the calculate_risk_metrics function and related risk analysis functionality.
"""

import pytest
import numpy as np
import os
import sys
from unittest.mock import patch

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from risk import calculate_risk_metrics, RiskMetrics, ConfidenceLevelMetrics


class TestConfidenceLevelMetrics:
    """Test ConfidenceLevelMetrics dataclass"""
    
    def test_initialization(self):
        """Test ConfidenceLevelMetrics initialization"""
        metrics = ConfidenceLevelMetrics(percentage=1.5, value=10000)
        assert metrics.percentage == 1.5
        assert metrics.value == 10000
    
    def test_with_negative_values(self):
        """Test ConfidenceLevelMetrics with negative values"""
        metrics = ConfidenceLevelMetrics(percentage=-2.5, value=-5000)
        assert metrics.percentage == -2.5
        assert metrics.value == -5000


class TestRiskMetrics:
    """Test RiskMetrics dataclass"""
    
    def test_initialization_default(self):
        """Test RiskMetrics initialization with defaults"""
        metrics = RiskMetrics()
        assert metrics.volatility == 0.0
        assert metrics.skewness == 0.0
        assert metrics.kurtosis == 0.0
        assert metrics.sharpe_ratio == 0.0
        assert metrics.max_drawdown == 0.0
        assert isinstance(metrics.value_at_risk, dict)
        assert isinstance(metrics.expected_shortfall, dict)
        assert len(metrics.value_at_risk) == 0
        assert len(metrics.expected_shortfall) == 0
    
    def test_initialization_with_values(self):
        """Test RiskMetrics initialization with custom values"""
        var_dict = {"VaR_95": ConfidenceLevelMetrics(percentage=2.5, value=5000)}
        metrics = RiskMetrics(
            volatility=0.15,
            skewness=-0.5,
            kurtosis=3.0,
            sharpe_ratio=1.2,
            max_drawdown=-20.0,
            value_at_risk=var_dict
        )
        assert metrics.volatility == 0.15
        assert metrics.skewness == -0.5
        assert metrics.kurtosis == 3.0
        assert metrics.sharpe_ratio == 1.2
        assert metrics.max_drawdown == -20.0
        assert len(metrics.value_at_risk) == 1


class TestCalculateRiskMetrics:
    """Test calculate_risk_metrics function"""
    
    def test_empty_returns_data_raises_error(self):
        """Test that empty returns data raises ValueError"""
        returns_data = np.array([])
        with pytest.raises(ValueError, match="Returns data is empty"):
            calculate_risk_metrics(returns_data, 0.05, 100000)
    
    def test_single_value_returns(self):
        """Test with single value in returns data"""
        returns_data = np.array([0.01])
        risk_free_rate = 0.05
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        assert isinstance(result, RiskMetrics)
        assert result.volatility == 0.0  # Single value has 0 std dev
        assert np.isnan(result.skewness)  # Single value skewness is NaN
    
    def test_normal_returns_data(self):
        """Test with normal returns data"""
        # Create normal distribution of returns
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 252)  # 1 year of daily returns
        risk_free_rate = 0.05 / 252  # Daily risk-free rate
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        assert isinstance(result, RiskMetrics)
        assert result.volatility > 0
        assert isinstance(result.skewness, float)
        assert isinstance(result.kurtosis, float)
        assert isinstance(result.sharpe_ratio, float)
        assert result.max_drawdown < 0  # Drawdown should be negative
    
    def test_all_positive_returns(self):
        """Test with all positive returns"""
        returns_data = np.array([0.01, 0.02, 0.015, 0.025, 0.03])
        risk_free_rate = 0.05 / 252
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        assert result.max_drawdown == 0.0  # No drawdown with positive returns
        assert result.volatility > 0
    
    def test_all_negative_returns(self):
        """Test with all negative returns"""
        returns_data = np.array([-0.01, -0.02, -0.015, -0.025, -0.03])
        risk_free_rate = 0.05 / 252
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        assert result.max_drawdown < 0  # Should have drawdown
        assert result.volatility > 0
        assert result.skewness == pytest.approx(0.0, abs=1e-10)  # Symmetric data
    
    def test_mixed_returns(self):
        """Test with mixed positive and negative returns"""
        returns_data = np.array([0.02, -0.01, 0.03, -0.02, 0.01, -0.03, 0.015])
        risk_free_rate = 0.05 / 252
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        assert isinstance(result, RiskMetrics)
        assert result.volatility > 0
        assert result.max_drawdown < 0
    
    def test_var_calculations(self):
        """Test VaR calculations"""
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 1000)
        risk_free_rate = 0.05 / 252
        total_value = 100000
        confidence_levels = [0.90, 0.95, 0.99]
        
        result = calculate_risk_metrics(
            returns_data, 
            risk_free_rate, 
            total_value, 
            confidence_levels=confidence_levels
        )
        
        # Check that all VaR values were calculated
        assert len(result.value_at_risk) == 3
        assert 'VaR_90' in result.value_at_risk
        assert 'VaR_95' in result.value_at_risk
        assert 'VaR_99' in result.value_at_risk
        
        # VaR values should be negative (losses)
        for var_key in result.value_at_risk:
            assert result.value_at_risk[var_key].value >= 0
            assert result.value_at_risk[var_key].percentage <= 0
    
    def test_expected_shortfall_calculations(self):
        """Test Expected Shortfall calculations"""
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 1000)
        risk_free_rate = 0.05 / 252
        total_value = 100000
        confidence_levels = [0.90, 0.95, 0.99]
        
        result = calculate_risk_metrics(
            returns_data, 
            risk_free_rate, 
            total_value, 
            confidence_levels=confidence_levels
        )
        
        # Check that all ES values were calculated
        assert len(result.expected_shortfall) == 3
        assert 'ES_90' in result.expected_shortfall
        assert 'ES_95' in result.expected_shortfall
        assert 'ES_99' in result.expected_shortfall
        
        # ES should be more extreme than VaR
        for i, level in enumerate(confidence_levels):
            es_value = result.expected_shortfall[f'ES_{int(level*100)}'].percentage
            var_value = result.value_at_risk[f'VaR_{int(level*100)}'].percentage
            # ES should be <= VaR (more negative or equal)
            assert es_value <= var_value
    
    def test_var_increases_with_confidence_level(self):
        """Test that VaR increases (becomes more negative) with higher confidence levels"""
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 1000)
        risk_free_rate = 0.05 / 252
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        var_90 = result.value_at_risk['VaR_90'].percentage
        var_95 = result.value_at_risk['VaR_95'].percentage
        var_99 = result.value_at_risk['VaR_99'].percentage
        
        # VaR should become more negative (larger loss) with higher confidence
        assert var_90 >= var_95 >= var_99
    
    def test_volatility_calculation(self):
        """Test volatility is annualized correctly"""
        # Create returns with known std dev
        returns_data = np.array([0.01] * 252)  # Constant 1% daily return
        risk_free_rate = 0.05 / 252
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # Std dev of constant should be 0, so volatility should be 0
        assert result.volatility == 0.0
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio is calculated"""
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 252)
        risk_free_rate = 0.0005  # Daily risk-free rate
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # Sharpe ratio should be a number (could be negative for poor returns)
        assert isinstance(result.sharpe_ratio, float)
        # With positive mean returns and positive risk-free rate, should be calculable
        assert not np.isnan(result.sharpe_ratio) or result.volatility == 0
    
    def test_max_drawdown_calculation(self):
        """Test maximum drawdown is calculated correctly"""
        # Create data with clear drawdown
        returns_data = np.array([0.05, 0.05, -0.10, -0.05, 0.02])
        risk_free_rate = 0.0005
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # Should have a drawdown less than -10%
        assert result.max_drawdown < -10
        assert result.max_drawdown < 0
    
    def test_custom_confidence_levels(self):
        """Test with custom confidence levels"""
        returns_data = np.array([0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.015])
        risk_free_rate = 0.05 / 252
        total_value = 100000
        custom_levels = [0.80, 0.85, 0.98]
        
        result = calculate_risk_metrics(
            returns_data, 
            risk_free_rate, 
            total_value, 
            confidence_levels=custom_levels
        )
        
        assert 'VaR_80' in result.value_at_risk
        assert 'VaR_85' in result.value_at_risk
        assert 'VaR_98' in result.value_at_risk
        assert 'ES_80' in result.expected_shortfall
        assert 'ES_85' in result.expected_shortfall
        assert 'ES_98' in result.expected_shortfall
    
    def test_skewness_negative_returns(self):
        """Test skewness with tail on left (negative returns)"""
        # Data with tail to the left
        returns_data = np.array([0.02, 0.02, 0.02, 0.02, 0.02, -0.10])
        risk_free_rate = 0.0005
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # Should have negative skewness
        assert result.skewness < 0
    
    def test_kurtosis_calculation(self):
        """Test kurtosis is calculated"""
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 252)
        risk_free_rate = 0.0005
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        assert isinstance(result.kurtosis, float)
        # Normal distribution should have kurtosis near 0 (excess kurtosis)
        assert -1 < result.kurtosis < 1
    
    def test_large_total_value(self):
        """Test with large total value"""
        returns_data = np.array([0.01, -0.01, 0.02, -0.02, 0.01])
        risk_free_rate = 0.0005
        total_value = 1_000_000_000  # 1 billion
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # VaR value should scale with total value
        var_value = result.value_at_risk['VaR_95'].value
        assert var_value > 0
        assert var_value < total_value
    
    def test_small_total_value(self):
        """Test with small total value"""
        returns_data = np.array([0.01, -0.01, 0.02, -0.02, 0.01])
        risk_free_rate = 0.0005
        total_value = 1000  # 1000 currency units
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        var_value = result.value_at_risk['VaR_95'].value
        assert var_value >= 0
    
    def test_zero_risk_free_rate(self):
        """Test with zero risk-free rate"""
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 252)
        risk_free_rate = 0.0
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # Should calculate without error
        assert isinstance(result.sharpe_ratio, float)
    
    def test_negative_risk_free_rate(self):
        """Test with negative risk-free rate (possible in some markets)"""
        np.random.seed(42)
        returns_data = np.random.normal(0.001, 0.02, 252)
        risk_free_rate = -0.0005
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # Should handle negative rates correctly
        assert isinstance(result.sharpe_ratio, float)
    
    def test_returns_with_extreme_values(self):
        """Test with extreme but valid return values"""
        # Simulate market crash
        returns_data = np.array([0.01, 0.01, -0.50, 0.01, 0.01])
        risk_free_rate = 0.0005
        total_value = 100000
        
        result = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        # Should handle extreme values
        assert result.max_drawdown <= -50
        assert result.volatility > 0.2
    
    def test_confidence_level_edge_cases(self):
        """Test with edge confidence levels"""
        returns_data = np.array([0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.015])
        risk_free_rate = 0.05 / 252
        total_value = 100000
        
        # Test with confidence levels very close to 0 and 1
        result = calculate_risk_metrics(
            returns_data,
            risk_free_rate,
            total_value,
            confidence_levels=[0.01, 0.50, 0.99]
        )
        
        assert len(result.value_at_risk) == 3
        # Lower confidence levels should have less extreme VaR
        var_1 = result.value_at_risk['VaR_1'].percentage
        var_50 = result.value_at_risk['VaR_50'].percentage
        var_99 = result.value_at_risk['VaR_99'].percentage
        
        # VaR becomes more extreme with higher confidence
        assert var_1 >= var_50 >= var_99
    
    def test_deterministic_output(self):
        """Test that same input produces same output"""
        returns_data = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
        risk_free_rate = 0.0005
        total_value = 100000
        
        result1 = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        result2 = calculate_risk_metrics(returns_data, risk_free_rate, total_value)
        
        assert result1.volatility == result2.volatility
        assert result1.sharpe_ratio == result2.sharpe_ratio
        assert result1.max_drawdown == result2.max_drawdown
        assert len(result1.value_at_risk) == len(result2.value_at_risk)


class TestIntegration:
    """Integration tests for risk calculations"""
    
    def test_realistic_portfolio_scenario(self):
        """Test with realistic portfolio returns"""
        # Simulate 1 year of daily returns for a portfolio
        np.random.seed(123)
        returns_data = np.random.normal(0.0005, 0.015, 252)
        
        portfolio_value = 250000  # $250,000 portfolio
        annual_risk_free_rate = 0.04
        daily_risk_free_rate = annual_risk_free_rate / 252
        
        result = calculate_risk_metrics(
            returns_data,
            daily_risk_free_rate,
            portfolio_value,
            confidence_levels=[0.90, 0.95, 0.99]
        )
        
        # Verify all metrics are calculated
        assert result.volatility > 0
        assert result.volatility < 1  # Should be reasonable (< 100% annualized)
        assert result.max_drawdown < 0
        assert len(result.value_at_risk) == 3
        assert len(result.expected_shortfall) == 3
        
        # VaR at 95% should indicate potential daily loss
        var_95_dollars = result.value_at_risk['VaR_95'].value
        assert 0 < var_95_dollars < portfolio_value
