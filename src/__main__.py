"""
CLI entry point for the README generator package.

This module provides the main entry point when the package is run as a module
using 'python -m readme_generator'. It handles command-line argument parsing
and delegates to the appropriate CLI functions.
"""

import sys
import os
import logging
from pathlib import Path

# Add the package to Python path if running as script
if __name__ == "__main__":
    # Get the directory containing this file
    current_dir = Path(__file__).parent
    # Add parent directory to path so we can import the package
    sys.path.insert(0, str(current_dir.parent))

from cli import main


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        print(f"You are using Python {sys.version}")
        sys.exit(1)


def handle_exceptions():
    """Set up global exception handling."""
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            print("\nOperation cancelled by user.")
            sys.exit(1)
        else:
            # Log the exception
            logging.error(
                "Uncaught exception", 
                exc_info=(exc_type, exc_value, exc_traceback)
            )
            print(f"An unexpected error occurred: {exc_value}")
            sys.exit(1)
    
    sys.excepthook = exception_handler


def entry_point():
    """Main entry point for the CLI application."""
    try:
        # Check Python version compatibility
        check_python_version()
        
        # Set up global exception handling
        handle_exceptions()
        
        # Parse arguments and determine verbosity early
        verbose = '--verbose' in sys.argv or '-v' in sys.argv
        
        # Set up logging
        setup_logging(verbose)
        
        # Log startup information
        logger = logging.getLogger(__name__)
        logger.info(f"Starting README Generator v{get_version()}")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Command line arguments: {sys.argv}")
        
        # Run the main CLI function
        main()
        
    except Exception as e:
        print(f"Failed to start README Generator: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Import version info
    try:
        from readme_generator import get_version
    except ImportError:
        def get_version():
            return "0.1.0"
    
    entry_point()
