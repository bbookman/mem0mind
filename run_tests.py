#!/usr/bin/env python3
"""
Test runner script for the unified memory application.

This script provides convenient ways to run different test suites:
- All tests
- Specific test modules
- Tests with coverage reporting
- Tests with different verbosity levels

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --module memory    # Run only memory manager tests
    python run_tests.py --verbose          # Run with verbose output
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """
    Run a command and handle the result.
    
    Args
    ----
    cmd: Command to run as a list
    description: Description of what the command does
    
    Returns
    -------
    True if command succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Command not found: {cmd[0]}")
        print("Make sure pytest is installed: pip install pytest")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test runner for unified memory application",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Run tests with coverage reporting')
    parser.add_argument('--module', '-m', choices=['memory', 'markdown', 'app', 'integration', 'logging'],
                       help='Run tests for specific module only')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Run tests with verbose output')
    parser.add_argument('--fast', '-f', action='store_true',
                       help='Run tests in parallel for faster execution')
    parser.add_argument('--markers', '-k',
                       help='Run tests matching specific markers (e.g., "unit" or "integration")')
    parser.add_argument('--unit-only', action='store_true',
                       help='Run only unit tests (no external services required)')
    parser.add_argument('--integration-only', action='store_true',
                       help='Run only integration tests (requires Qdrant + Ollama)')
    parser.add_argument('--with-cleanup', action='store_true',
                       help='Include cleanup verification tests')
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path('tests').exists():
        print("❌ Tests directory not found. Please run from the project root directory.")
        sys.exit(1)
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add test path based on module selection
    if args.module == 'memory':
        cmd.append('tests/test_memory_manager.py')
        description = "Memory Manager tests"
    elif args.module == 'markdown':
        cmd.append('tests/test_markdown_processor.py')
        description = "Markdown Processor tests"
    elif args.module == 'app':
        cmd.append('tests/test_memory_app.py')
        description = "Main Application tests"
    elif args.module == 'integration':
        cmd.append('tests/test_integration.py')
        description = "Integration tests"
    elif args.module == 'logging':
        cmd.append('tests/test_logging_system.py')
        description = "Logging system tests"
    else:
        cmd.append('tests/')
        description = "All tests"

    # Add marker-based filtering
    if args.unit_only:
        cmd.extend(['-m', 'not integration'])
        description += " (unit tests only)"
    elif args.integration_only:
        cmd.extend(['-m', 'integration'])
        description += " (integration tests only)"
    elif args.with_cleanup:
        cmd.extend(['-m', 'cleanup or unit or integration'])
        description += " (with cleanup tests)"
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(['--cov=.', '--cov-report=html', '--cov-report=term-missing'])
        description += " with coverage"
    
    # Add verbosity
    if args.verbose:
        cmd.append('-vv')
    
    # Add parallel execution
    if args.fast:
        cmd.extend(['-n', 'auto'])
    
    # Add marker filtering
    if args.markers:
        cmd.extend(['-m', args.markers])
    
    # Run the tests
    success = run_command(cmd, description)
    
    if args.coverage and success:
        print(f"\n📊 Coverage report generated in htmlcov/index.html")
    
    # Print summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests completed successfully!")
        print("\nNext steps:")
        print("- Review any test output above")
        if args.coverage:
            print("- Open htmlcov/index.html to view detailed coverage report")
        print("- Run 'python memory_app.py --help' to test the application")
    else:
        print("💥 Some tests failed!")
        print("\nTroubleshooting:")
        print("- Check the error messages above")
        print("- Ensure all dependencies are installed: pip install -r requirements-test.txt")
        print("- Make sure Qdrant and Ollama services are running if testing with real services")
        sys.exit(1)
    
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
