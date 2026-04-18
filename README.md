# Personal Portfolio Risk Analysis Tool

A portfolio risk analysis and reporting tool that integrates real-time market data from the Moscow Exchange (MOEX) with advanced risk metrics calculations.

## Overview

This project analyzes investment portfolio risks using:
- **Real-time market data** from MOEX (Moscow Exchange)
- **Statistical risk metrics**: Value at Risk (VaR), Expected Shortfall (ES), volatility
- **Advanced models**: Nelson-Siegel-Svensson yield curve for risk-free rate calculations
- **Professional PDF reports** with visualizations and comparative analysis
- **Automated testing** with comprehensive unit and integration tests

The tool is designed for financial analysts, portfolio managers, and risk officers who need detailed portfolio risk assessment with market benchmarking.

## Features

### Core Analysis
- **Portfolio Metrics**: Asset allocation, P&L analysis, returns distribution
- **Risk Calculations**: VaR (90%, 95%, 99%), Expected Shortfall, volatility, skewness, kurtosis, Sharpe ratio
- **Yield Curve**: MOEX G-Curve risk-free rate calculations using Nelson-Siegel-Svensson model
- **Market Benchmarking**: Portfolio volatility vs IMOEX index comparison

### Data Integration
- **Caching System**: SQLite-based price caching to minimize API calls
- **MOEX Data**: Historical and current prices, indices, yield curves
- **Excel Integration**: Support for password-protected Excel portfolio files

### Reporting
- **PDF Generation**: Professional multi-page reports with charts and tables
- **Visualizations**: Asset allocation pie charts, returns distribution, P&L analysis, volatility comparison
- **Unicode Support**: Full support for Russian text and special characters

## Getting Started

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **Environment variable**: `PORTFOLIO_PASSWORD` (for encrypted Excel files)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd risk
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-test.txt
   ```

4. **Set environment variables**
   ```bash
   # Windows PowerShell:
   $env:PORTFOLIO_PASSWORD = "your_excel_password"
   
   # Windows CMD:
   set PORTFOLIO_PASSWORD=your_excel_password
   
   # macOS/Linux:
   export PORTFOLIO_PASSWORD="your_excel_password"
   ```

