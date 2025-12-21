#!/usr/bin/env python3
"""
Test runner script for Viral Researcher & Scripter tests.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --unit       # Run only unit tests
    python run_tests.py --cov        # Run with coverage report
    python run_tests.py --fast       # Skip slow tests
    python run_tests.py services     # Run tests in specific directory
"""

import sys
import subprocess
from pathlib import Path


def run_tests(args=None):
    """Run pytest with specified arguments."""
    base_cmd = ["pytest"]

    if args:
        # Parse custom arguments
        if "--unit" in args:
            base_cmd.extend(["-m", "unit"])
            args.remove("--unit")

        if "--fast" in args:
            base_cmd.extend(["-m", "not slow"])
            args.remove("--fast")

        if "--cov" in args:
            base_cmd.extend([
                "--cov=app",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov"
            ])
            args.remove("--cov")

        # Add remaining args
        base_cmd.extend(args)

    # Run pytest
    print(f"Running: {' '.join(base_cmd)}")
    result = subprocess.run(base_cmd)

    return result.returncode


if __name__ == "__main__":
    # Get arguments (skip script name)
    args = sys.argv[1:] if len(sys.argv) > 1 else None

    # Ensure we're in the right directory
    project_root = Path(__file__).parent

    # Run tests
    exit_code = run_tests(args)

    sys.exit(exit_code)
