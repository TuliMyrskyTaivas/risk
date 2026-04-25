# Risk Analysis for Portfolio
import numpy as np
from typing import Dict
from scipy import stats
from dataclasses import dataclass, field

@dataclass
class ConfidenceLevelMetrics:
    percentage: float
    value: float

@dataclass
class RiskMetrics:
    volatility: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    value_at_risk: Dict[str, ConfidenceLevelMetrics] = field(default_factory=dict[str, ConfidenceLevelMetrics])
    expected_shortfall: Dict[str, ConfidenceLevelMetrics] = field(default_factory=dict[str, ConfidenceLevelMetrics])

def calculate_risk_metrics(        
        returns_data: np.ndarray,
        risk_free_rate: float,
        total_value: float,
        confidence_levels: list[float] = [0.90, 0.95, 0.99]) -> RiskMetrics:
    
    """Calculate all risk metrics"""
    if returns_data.size == 0:
        raise ValueError("Returns data is empty")
    
    result : RiskMetrics = RiskMetrics()
    # Calculate VaR and Expected Shortfall for each confidence level
    for conf in confidence_levels:
        # VaR
        var = np.percentile(returns_data, (1 - conf) * 100)
        result.value_at_risk[f'VaR_{int(conf*100)}'] = ConfidenceLevelMetrics(
            percentage=var * 100,
            value=total_value * abs(var)
        )

        # Expected Shortfall    
        var_threshold = np.percentile(returns_data, (1 - conf) * 100)
        tail_returns = returns_data[returns_data <= var_threshold]
        es = tail_returns.mean() if len(tail_returns) > 0 else var_threshold
        result.expected_shortfall[f'ES_{int(conf*100)}'] = ConfidenceLevelMetrics(
            percentage=es * 100,
            value=total_value * abs(es)
        )
        
    # Statistics
    result.volatility = np.std(returns_data) * np.sqrt(252)
    result.skewness = float(stats.skew(returns_data))
    result.kurtosis = float(stats.kurtosis(returns_data))

    # Sharpe ratio (using Russian risk-free rate - approximate)
    mean_daily_return = np.mean(returns_data)
    result.sharpe_ratio = (mean_daily_return - risk_free_rate) / np.std(returns_data) * np.sqrt(252)     

    # Maximum drawdown
    cumulative_returns = np.cumprod(1 + returns_data)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - running_max) / running_max    
    result.max_drawdown = drawdown.min() * 100
                
    return result