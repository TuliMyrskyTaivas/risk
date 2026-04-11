#!/usr/bin/env python
"""
Test runner script for portfolio_analyzer tests

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --verbose          # Run with verbose output
    python run_tests.py --specific TestLoadPortfolio  # Run specific test class
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(args):
    """Run pytest with specified arguments"""
    
    cmd = ['pytest', 'test_portfolio_analyzer.py']
    
    # Verbosity
    if args.verbose:
        cmd.append('-vv')
    else:
        cmd.append('-v')
    
    # Coverage
    if args.coverage:
        cmd.extend(['--cov=portfolio_analyzer', '--cov-report=html', '--cov-report=term-missing'])
        print("📊 Running tests with coverage report...")
    else:
        print("✓ Running tests...")
    
    # Specific test
    if args.specific:
        cmd.append(f':::{args.specific}')
    
    # TB format
    if args.short_tb:
        cmd.append('--tb=short')
    else:
        cmd.append('--tb=long')
    
    # Markers
    if args.markers:
        cmd.extend(['-m', args.markers])
    
    # Run pytest
    result = subprocess.run(cmd)
    
    # Print results
    if result.returncode == 0:
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        if args.coverage:
            print("\n📈 Coverage report generated in htmlcov/index.html")
    else:
        print("\n" + "="*60)
        print("❌ Some tests failed!")
        print("="*60)
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description='Run tests for portfolio_analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                              # Run all tests
  python run_tests.py --coverage                   # With coverage report
  python run_tests.py --verbose --specific TestLoadPortfolio  # Specific test class
  python run_tests.py --markers unit               # Run only unit tests
        """
    )
    
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Generate coverage report (HTML and terminal)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--specific', '-s',
        type=str,
        help='Run specific test class or function (e.g., TestLoadPortfolio)'
    )
    
    parser.add_argument(
        '--short-tb',
        action='store_true',
        default=True,
        help='Short traceback format (default: True)'
    )
    
    parser.add_argument(
        '--long-tb',
        action='store_false',
        dest='short_tb',
        help='Long traceback format'
    )
    
    parser.add_argument(
        '--markers', '-m',
        type=str,
        help='Run tests with specific markers (e.g., unit, mock, integration)'
    )
    
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install test dependencies from requirements-test.txt'
    )
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install:
        print("📦 Installing test dependencies...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-test.txt', '-q'])
        if result.returncode != 0:
            print("❌ Failed to install dependencies")
            return 1
        print("✅ Dependencies installed\n")
    
    # Check if test file exists
    if not Path('test_portfolio_analyzer.py').exists():
        print("❌ Error: test_portfolio_analyzer.py not found in current directory")
        return 1
    
    return run_tests(args)


if __name__ == '__main__':
    sys.exit(main())
