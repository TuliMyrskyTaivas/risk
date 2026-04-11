"""
Unit tests for portfolio_analyzer.py

Tests the load_portfolio function and related functionality.
"""

import pytest
import pandas as pd
import numpy as np
import os
import sys
from unittest.mock import Mock, patch, MagicMock, mock_open
from io import BytesIO
import logging

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portfolio_analyzer import PortfolioAnalyzer


class TestPortfolioAnalyzerInit:
    """Test PortfolioAnalyzer initialization"""
    
    def test_init_with_password(self):
        """Test initialization with password set in environment"""
        with patch.dict(os.environ, {'PORTFOLIO_PASSWORD': 'test_password'}):
            analyzer = PortfolioAnalyzer('test.xlsx')
            assert analyzer.excel_path == 'test.xlsx'
            assert analyzer.password == 'test_password'
            assert analyzer.returns_data is None
            assert analyzer.report_data == {}
    
    def test_init_without_password(self):
        """Test initialization fails without password"""
        with patch.dict(os.environ, {}, clear=True):
            # Remove PORTFOLIO_PASSWORD if it exists
            os.environ.pop('PORTFOLIO_PASSWORD', None)
            with pytest.raises(ValueError, match="PORTFOLIO_PASSWORD environment variable not set"):
                PortfolioAnalyzer('test.xlsx')    
    
    def test_logger_initialized(self):
        """Test that logger is properly initialized"""
        with patch.dict(os.environ, {'PORTFOLIO_PASSWORD': 'test_password'}):
            analyzer = PortfolioAnalyzer('test.xlsx')
            assert analyzer.logger is not None
            assert isinstance(analyzer.logger, logging.Logger)


class TestLoadPortfolio:
    """Test load_portfolio method"""
    
    @pytest.fixture
    def analyzer(self):
        """Create an analyzer instance for testing"""
        with patch.dict(os.environ, {'PORTFOLIO_PASSWORD': 'test_password'}):
            analyzer = PortfolioAnalyzer('test.xlsx')
            yield analyzer
    
    def test_load_portfolio_with_excel_table(self, analyzer):
        """Test loading portfolio from Excel table"""
        # Mock the file operations and msoffcrypto
        mock_decrypted_content = BytesIO()
        
        # Create mock workbook
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_cell = MagicMock()
        
        # Setup sheet names
        mock_workbook.sheetnames = ['Assets']
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        
        # Setup Excel table
        mock_table = MagicMock()
        mock_table.ref = 'A1:E5'
        mock_sheet.tables = {'Assets': mock_table}
        
        # Setup sheet cells
        headers = ['Name', 'Code', 'Amount', 'Current price', 'Type']
        data_rows = [
            ['Asset1', 'ASSET1', '100', '500.5', 'Stock'],
            ['Asset2', 'ASSET2', '50', '1000.0', 'Bond'],
        ]
        
        all_cells = [headers] + data_rows
        
        def mock_cell_func(row, column):
            cell = MagicMock()
            if row <= len(all_cells) and column <= len(all_cells[0]):
                cell.value = all_cells[row - 1][column - 1]
            else:
                cell.value = None
            return cell
        
        mock_sheet.cell = mock_cell_func
        
        with patch('builtins.open', mock_open()):
            with patch('portfolio_analyzer.msoffcrypto.OfficeFile') as mock_office_file:
                with patch('openpyxl.load_workbook', return_value=mock_workbook):
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            # Setup msoffcrypto mock
                            mock_office = MagicMock()
                            mock_office_file.return_value = mock_office
                            
                            result = analyzer.load_portfolio()
                            
                            assert result == True
                            assert analyzer.portfolio_data is not None
                            assert isinstance(analyzer.portfolio_data, pd.DataFrame)
                            assert len(analyzer.portfolio_data) >= 1
    
    def test_load_portfolio_with_named_range(self, analyzer):
        """Test loading portfolio from named range"""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        
        # Setup sheet names
        mock_workbook.sheetnames = ['Assets']
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        
        # Setup sheet with no tables
        mock_sheet.tables = {}
        
        # Setup defined names (named ranges)
        mock_defined_name = MagicMock()
        mock_defined_name.name = 'Assets'
        mock_defined_name.destinations = [('Assets', 'A1:C3')]
        mock_workbook.defined_names = [mock_defined_name]
        
        # Setup sheet cells
        headers = ['Name', 'Code', 'Amount']
        data_rows = [
            ['Asset1', 'ASSET1', '100'],
            ['Asset2', 'ASSET2', '50'],
        ]
        
        all_cells = [headers] + data_rows
        
        def mock_cell_func(row, column):
            cell = MagicMock()
            if row <= len(all_cells) and column <= len(all_cells[0]):
                cell.value = all_cells[row - 1][column - 1]
            else:
                cell.value = None
            return cell
        
        mock_sheet.cell = mock_cell_func
        
        with patch('builtins.open', mock_open()):
            with patch('portfolio_analyzer.msoffcrypto.OfficeFile') as mock_office_file:
                with patch('openpyxl.load_workbook', return_value=mock_workbook):
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            mock_office = MagicMock()
                            mock_office_file.return_value = mock_office
                            
                            result = analyzer.load_portfolio()
                            
                            assert result == True
                            assert analyzer.portfolio_data is not None
                            assert isinstance(analyzer.portfolio_data, pd.DataFrame)
    
    def test_load_portfolio_missing_assets_sheet(self, analyzer):
        """Test loading fails when Assets sheet is missing"""
        mock_workbook = MagicMock()
        mock_workbook.sheetnames = ['Portfolio', 'Settings']  # No Assets sheet
        
        with patch('builtins.open', mock_open()):
            with patch('portfolio_analyzer.msoffcrypto.OfficeFile') as mock_office_file:
                with patch('openpyxl.load_workbook', return_value=mock_workbook):
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            mock_office = MagicMock()
                            mock_office_file.return_value = mock_office
                            
                            result = analyzer.load_portfolio()
                            
                            assert result == False
    
    def test_load_portfolio_missing_named_table_and_range(self, analyzer):
        """Test loading fails when neither table nor named range exists"""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        
        mock_workbook.sheetnames = ['Assets']
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        
        # No tables
        mock_sheet.tables = {}
        
        # No defined names with 'Assets'
        mock_workbook.defined_names = []
        
        with patch('builtins.open', mock_open()):
            with patch('portfolio_analyzer.msoffcrypto.OfficeFile') as mock_office_file:
                with patch('openpyxl.load_workbook', return_value=mock_workbook):
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            mock_office = MagicMock()
                            mock_office_file.return_value = mock_office
                            
                            result = analyzer.load_portfolio()
                            
                            assert result == False
    
    def test_load_portfolio_file_not_found(self, analyzer):
        """Test loading fails when file doesn't exist"""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            result = analyzer.load_portfolio()
            assert result == False
    
    def test_load_portfolio_decryption_error(self, analyzer):
        """Test loading fails when decryption error occurs"""
        with patch('builtins.open', mock_open()):
            with patch('portfolio_analyzer.msoffcrypto.OfficeFile') as mock_office_file:
                mock_office = MagicMock()
                mock_office.load_key.side_effect = Exception("Invalid password")
                mock_office_file.return_value = mock_office
                
                result = analyzer.load_portfolio()
                assert result == False
    
    def test_load_portfolio_empty_data(self, analyzer):
        """Test loading handles empty data correctly"""
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        
        mock_workbook.sheetnames = ['Assets']
        mock_workbook.__getitem__ = MagicMock(return_value=mock_sheet)
        
        # Setup Excel table
        mock_table = MagicMock()
        mock_table.ref = 'A1:C1'  # Only headers, no data
        mock_sheet.tables = {'Assets': mock_table}
        
        # Setup sheet with only headers
        headers = ['Name', 'Code', 'Amount']
        all_cells = [headers]
        
        def mock_cell_func(row, column):
            cell = MagicMock()
            if row <= len(all_cells) and column <= len(all_cells[0]):
                cell.value = all_cells[row - 1][column - 1]
            else:
                cell.value = None
            return cell
        
        mock_sheet.cell = mock_cell_func
        
        with patch('builtins.open', mock_open()):
            with patch('portfolio_analyzer.msoffcrypto.OfficeFile'):
                with patch('openpyxl.load_workbook', return_value=mock_workbook):
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove'):
                            result = analyzer.load_portfolio()
                            
                            assert result == False  # Should fail due to no data rows


class TestCleanData:
    """Test _clean_data method"""
    
    @pytest.fixture
    def analyzer_with_data(self):
        """Create analyzer with test data"""
        with patch.dict(os.environ, {'PORTFOLIO_PASSWORD': 'test_password'}):
            analyzer = PortfolioAnalyzer('test.xlsx')
            
            # Create test dataframe
            analyzer.portfolio_data = pd.DataFrame({
                'Name': ['Asset1', 'Asset2', 'Asset3'],
                'Code': ['ASS1', 'ASS2', 'ASS3'],
                'Type': ['Stock', 'Bond', 'Stock'],
                'Amount': [100, 50, 200],
                'Current price': [500.5, 1000.0, 250.75],
                'Book value': [35000, 45000, 40000],
                'Return': [15000, 5000, 2000],
                'Currency': ['RUB', 'RUB', 'RUB']
            })
            return analyzer
    
    def test_clean_data_numeric_conversion(self, analyzer_with_data):
        """Test that numeric columns are converted properly"""
        analyzer = analyzer_with_data
        
        # Set numeric columns as strings with various formats
        analyzer.portfolio_data['Amount'] = ['100,50', '50', '200']
        
        analyzer._clean_data()
        
        # Check that numeric conversion worked
        assert analyzer.portfolio_data['Amount'].dtype in [np.float64, np.int64]
        assert analyzer.portfolio_data['Amount'].iloc[0] == pytest.approx(100.5)
    
    def test_clean_data_calculates_current_value(self, analyzer_with_data):
        """Test that current value is calculated"""
        analyzer = analyzer_with_data
        analyzer._clean_data()
        
        assert 'Current value' in analyzer.portfolio_data.columns
        expected_value = analyzer.portfolio_data['Amount'] * analyzer.portfolio_data['Current price']
        np.testing.assert_array_almost_equal(
            analyzer.portfolio_data['Current value'].values,
            expected_value.values
        )
    
    def test_clean_data_calculates_weights(self, analyzer_with_data):
        """Test that weights are calculated"""
        analyzer = analyzer_with_data
        analyzer._clean_data()
        
        assert 'Weight' in analyzer.portfolio_data.columns
        total_weight = analyzer.portfolio_data['Weight'].sum()
        assert total_weight == pytest.approx(1.0, abs=0.01)
    
    def test_clean_data_calculates_returns(self, analyzer_with_data):
        """Test that return percentages are calculated from RUB returns"""
        analyzer = analyzer_with_data
        analyzer._clean_data()
        
        assert 'Return %' in analyzer.portfolio_data.columns
        # Calculate expected values
        expected_return_pct = (analyzer.portfolio_data['Return'] / 
                              analyzer.portfolio_data['Book value'] * 100)
        np.testing.assert_array_almost_equal(
            analyzer.portfolio_data['Return %'].values,
            expected_return_pct.values,
            decimal=1
        )
    
    def test_clean_data_strips_column_names(self, analyzer_with_data):
        """Test that column names are stripped of whitespace"""
        analyzer = analyzer_with_data
        analyzer.portfolio_data.columns = [col + ' ' for col in analyzer.portfolio_data.columns]
        
        analyzer._clean_data()
        
        # Check that whitespace is removed
        assert not any(col.endswith(' ') for col in analyzer.portfolio_data.columns)
    
    def test_clean_data_sets_currency(self, analyzer_with_data):
        """Test that currency is set to RUB"""
        analyzer = analyzer_with_data
        analyzer._clean_data()
        
        assert 'Currency' in analyzer.portfolio_data.columns
        assert all(analyzer.portfolio_data['Currency'] == 'RUB')
    
    def test_clean_data_stores_summary_data(self, analyzer_with_data):
        """Test that summary data is stored in report_data"""
        analyzer = analyzer_with_data
        analyzer._clean_data()
        
        assert 'total_value' in analyzer.report_data
        assert 'total_book_value' in analyzer.report_data
        assert 'n_assets' in analyzer.report_data
        assert analyzer.report_data['n_assets'] == 3
    
    def test_clean_data_handles_missing_columns(self, analyzer_with_data):
        """Test that clean_data handles missing columns gracefully"""
        analyzer = analyzer_with_data
        # Remove a column
        analyzer.portfolio_data = analyzer.portfolio_data.drop('Return', axis=1)
        
        # Should not raise an error
        analyzer._clean_data()
        assert analyzer.portfolio_data is not None


class TestIntegration:
    """Integration tests for the analyzer"""
    
    def test_full_workflow_with_mock_data(self):
        """Test complete workflow with mocked data"""
        with patch.dict(os.environ, {'PORTFOLIO_PASSWORD': 'test_password'}):
            analyzer = PortfolioAnalyzer('test.xlsx')
            
            # Create test data
            analyzer.portfolio_data = pd.DataFrame({
                'Name': ['Asset1', 'Asset2'],
                'Code': ['ASS1', 'ASS2'],
                'Type': ['Stock', 'Bond'],
                'Amount': [100, 50],
                'Current price': [500.5, 1000.0],
                'Book value': [35000, 45000],
                'Return': [15000, 5000],
                'Currency': ['RUB', 'RUB']
            })
            
            # Mock MOEX fetcher
            analyzer.moex = MagicMock()
            analyzer.moex.get_current_price = MagicMock(return_value=500.0)
            
            # Clean data
            analyzer._clean_data()
            
            # Generate returns data
            with patch.object(analyzer.moex, 'get_historical_prices', return_value=None):
                returns = analyzer.generate_returns_data(n_simulations=100)
                assert returns is not None
                assert len(returns) == 100
    
    def test_risk_metrics_calculation_with_test_data(self):
        """Test risk metrics calculation with test data"""
        with patch.dict(os.environ, {'PORTFOLIO_PASSWORD': 'test_password'}):
            analyzer = PortfolioAnalyzer('test.xlsx')
            
            # Create test data
            analyzer.portfolio_data = pd.DataFrame({
                'Name': ['Asset1'],
                'Type': ['Stock'],
                'Amount': [100],
                'Current price': [500.0],
                'Weight': [1.0]
            })
            
            analyzer.report_data = {'total_value': 50000}
            
            # Create synthetic returns data
            np.random.seed(42)
            analyzer.returns_data = np.random.normal(0.001, 0.02, 1000)
            
            # Calculate risk metrics
            risk_metrics = analyzer.calculate_risk_metrics()
            
            assert 'VaR_90' in risk_metrics
            assert 'VaR_95' in risk_metrics
            assert 'VaR_99' in risk_metrics
            assert 'ES_90' in risk_metrics
            assert 'statistics' in risk_metrics


class TestMOEXDataFetcher:
    """Tests for MOEX data fetcher integration"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer for testing"""
        with patch.dict(os.environ, {'PORTFOLIO_PASSWORD': 'test_password'}):
            return PortfolioAnalyzer('test.xlsx')
    
    def test_update_prices_from_moex(self, analyzer):
        """Test updating prices from MOEX"""
        analyzer.portfolio_data = pd.DataFrame({
            'Code': ['SBER', 'GAZP', 'LUKOIL'],
            'Current price': [300.0, 150.0, 5000.0]
        })
        
        # Mock MOEX fetcher
        analyzer.moex.get_current_price = MagicMock(side_effect=[310.0, 155.0, 5100.0])
        
        analyzer._update_prices_from_moex()
        
        assert analyzer.portfolio_data['Current price'].iloc[0] == 310.0
        assert analyzer.portfolio_data['Current price'].iloc[1] == 155.0
        assert analyzer.portfolio_data['Current price'].iloc[2] == 5100.0
    
    def test_update_prices_handles_invalid_tickers(self, analyzer):
        """Test that invalid tickers are handled gracefully"""
        analyzer.portfolio_data = pd.DataFrame({
            'Code': ['VALID', 'INVALID', 'VALID2'],
            'Current price': [100.0, 100.0, 100.0]
        })
        
        # Mock MOEX fetcher to return None for invalid ticker
        analyzer.moex.get_current_price = MagicMock(side_effect=[110.0, None, 120.0])
        
        analyzer._update_prices_from_moex()
        
        # Should still have original price for invalid ticker
        assert analyzer.portfolio_data['Current price'].iloc[0] == 110.0
        assert analyzer.portfolio_data['Current price'].iloc[1] == 100.0  # Unchanged
        assert analyzer.portfolio_data['Current price'].iloc[2] == 120.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
