#!/usr/bin/env python3
"""
Main entry point for the README Generator application.

This script provides the primary entry point for the command-line interface
of the README generator, which automatically creates comprehensive README files
for Python projects using LLM APIs.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

# Now import the CLI module
try:
    from cli import main as cli_main
except ImportError as e:
    print(f"Error importing CLI module: {e}", file=sys.stderr)
    print("Please ensure all dependencies are installed: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point for the README generator."""
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
