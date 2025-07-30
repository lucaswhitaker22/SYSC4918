"""
File system utilities for safe and efficient file operations.

This module provides functions for reading files, detecting encodings,
and basic directory traversal for Python projects.
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional, Generator
import logging

logger = logging.getLogger(__name__)

IGNORE_FOLDERS = {'.git', 'venv', 'env', '__pycache__', 'build', 'dist', '.tox'}
PYTHON_EXTENSIONS = {'.py', '.pyw', '.pyx', '.pyi'}
TEXT_EXTENSIONS = {
    '.txt', '.md', '.rst', '.yaml', '.yml', '.json', '.xml', '.cfg',
    '.ini', '.toml', '.conf', '.env'
}

def read_file_safely(file_path: str, max_size: int = 10 * 1024 * 1024) -> Optional[str]:
    """Reads file contents if file size is below max_size."""
    try:
        p = Path(file_path)
        if not p.is_file():
            logger.debug(f"Not a file: {file_path}")
            return None
        if p.stat().st_size > max_size:
            logger.warning(f"File too large to read: {file_path}")
            return None
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None

def create_directory(path: str) -> bool:
    """Create directory if it doesn't exist."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False

def find_python_files(project_path: str, include_tests: bool = False) -> Generator[str, None, None]:
    """Yield all Python file paths in project, optionally skipping test folders."""
    root_path = Path(project_path)
    if not root_path.exists():
        logger.warning(f"Project path not found: {project_path}")
        return
    for root, dirs, files in os.walk(project_path):
        # Filter out ignored folders
        dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]
        if not include_tests:
            # Optionally skip any test folder
            dirs[:] = [d for d in dirs if 'test' not in d.lower()]
        for file in files:
            if file.endswith('.py'):
                yield str(Path(root) / file)
