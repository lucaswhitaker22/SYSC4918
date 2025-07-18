"""
File system utilities for safe and efficient file operations.

This module provides functions for reading files, detecting encodings,
traversing directories, and handling various file types commonly found
in Python projects.
"""

import os
import re
import chardet
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Generator, Set, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Common file patterns to ignore
IGNORE_PATTERNS = {
    # Version control
    '.git', '.svn', '.hg', '.bzr',
    # Python cache
    '__pycache__', '*.pyc', '*.pyo', '*.pyd',
    # Virtual environments
    'venv', 'env', '.venv', '.env', 'virtualenv',
    # IDE files
    '.vscode', '.idea', '*.swp', '*.swo',
    # Build artifacts
    'build', 'dist', '*.egg-info', '.tox',
    # OS files
    '.DS_Store', 'Thumbs.db',
    # Temporary files
    '*.tmp', '*.temp', '*.log'
}

# Python file extensions
PYTHON_EXTENSIONS = {'.py', '.pyw', '.pyx', '.pyi'}

# Configuration file patterns
CONFIG_FILES = {
    'setup.py', 'setup.cfg', 'pyproject.toml', 'requirements.txt',
    'requirements-dev.txt', 'Pipfile', 'Pipfile.lock', 'poetry.lock',
    'tox.ini', 'pytest.ini', '.flake8', '.pylintrc', 'mypy.ini',
    '.gitignore', '.gitattributes', 'MANIFEST.in', 'LICENSE', 'README.md',
    'README.rst', 'README.txt', 'CHANGELOG.md', 'CHANGELOG.rst'
}


@dataclass
class FileInfo:
    """Information about a file."""
    path: str
    size: int
    encoding: Optional[str] = None
    mime_type: Optional[str] = None
    is_text: bool = False
    is_python: bool = False
    is_config: bool = False


class FileReader:
    """Enhanced file reader with encoding detection and error handling."""
    
    def __init__(self, max_file_size: int = 10 * 1024 * 1024):  # 10MB default
        self.max_file_size = max_file_size
        self._encoding_cache: Dict[str, str] = {}
    
    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read a file with automatic encoding detection.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File content as string, or None if reading fails
        """
        try:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                logger.warning(f"File not found: {file_path}")
                return None
                
            if path.stat().st_size > self.max_file_size:
                logger.warning(f"File too large: {file_path} ({path.stat().st_size} bytes)")
                return None
                
            encoding = self.detect_encoding(file_path)
            if not encoding:
                logger.warning(f"Could not detect encoding for: {file_path}")
                return None
                
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def detect_encoding(self, file_path: str) -> Optional[str]:
        """
        Detect file encoding using chardet.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected encoding or None
        """
        if file_path in self._encoding_cache:
            return self._encoding_cache[file_path]
            
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(8192)  # Read first 8KB for detection
                
            if not raw_data:
                return 'utf-8'
                
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            
            if encoding and result.get('confidence', 0) > 0.7:
                self._encoding_cache[file_path] = encoding
                return encoding
            else:
                # Fallback to common encodings
                for fallback in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=fallback) as f:
                            f.read(1024)  # Try reading some content
                        self._encoding_cache[file_path] = fallback
                        return fallback
                    except UnicodeDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error detecting encoding for {file_path}: {e}")
            
        return None


def read_file_safely(file_path: str, max_size: int = 10 * 1024 * 1024) -> Optional[str]:
    """
    Safely read a file with encoding detection and size limits.
    
    Args:
        file_path: Path to the file
        max_size: Maximum file size in bytes
        
    Returns:
        File content or None if reading fails
    """
    reader = FileReader(max_size)
    return reader.read_file(file_path)


def detect_encoding(file_path: str) -> Optional[str]:
    """
    Detect file encoding.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected encoding or None
    """
    reader = FileReader()
    return reader.detect_encoding(file_path)


def is_python_file(file_path: str) -> bool:
    """
    Check if a file is a Python file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is a Python file
    """
    path = Path(file_path)
    
    # Check extension
    if path.suffix.lower() in PYTHON_EXTENSIONS:
        return True
        
    # Check shebang for extensionless files
    if not path.suffix:
        try:
            with open(file_path, 'rb') as f:
                first_line = f.readline(100).decode('utf-8', errors='ignore')
                if first_line.startswith('#!') and 'python' in first_line:
                    return True
        except Exception:
            pass
            
    return False


def is_text_file(file_path: str) -> bool:
    """
    Check if a file is a text file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is likely a text file
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith('text/'):
        return True
        
    # Check for common text file extensions
    path = Path(file_path)
    text_extensions = {
        '.txt', '.md', '.rst', '.yaml', '.yml', '.json', '.xml',
        '.cfg', '.ini', '.toml', '.conf', '.config', '.env'
    }
    
    return path.suffix.lower() in text_extensions


def should_ignore_file(file_path: str, ignore_patterns: Optional[Set[str]] = None) -> bool:
    """
    Check if a file should be ignored based on patterns.
    
    Args:
        file_path: Path to the file
        ignore_patterns: Custom ignore patterns to use
        
    Returns:
        True if the file should be ignored
    """
    if ignore_patterns is None:
        ignore_patterns = IGNORE_PATTERNS
        
    path = Path(file_path)
    
    # Check if any part of the path matches ignore patterns
    for part in path.parts:
        for pattern in ignore_patterns:
            if '*' in pattern:
                # Handle glob patterns
                import fnmatch
                if fnmatch.fnmatch(part, pattern):
                    return True
            else:
                # Exact match
                if part == pattern:
                    return True
                    
    return False


def find_files_by_pattern(directory: str, pattern: str, recursive: bool = True) -> List[str]:
    """
    Find files matching a pattern in a directory.
    
    Args:
        directory: Directory to search
        pattern: File pattern to match
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
    """
    import fnmatch
    
    matches = []
    directory = Path(directory)
    
    if not directory.exists():
        return matches
        
    search_pattern = "**/" + pattern if recursive else pattern
    
    try:
        for file_path in directory.glob(search_pattern):
            if file_path.is_file() and not should_ignore_file(str(file_path)):
                matches.append(str(file_path))
    except Exception as e:
        logger.error(f"Error finding files with pattern '{pattern}': {e}")
        
    return matches


def get_project_files(project_path: str, include_tests: bool = False) -> Dict[str, List[FileInfo]]:
    """
    Get categorized files from a project directory.
    
    Args:
        project_path: Path to the project root
        include_tests: Whether to include test files
        
    Returns:
        Dictionary of categorized file information
    """
    project_path = Path(project_path)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_path}")
        
    files = {
        'python': [],
        'config': [],
        'documentation': [],
        'tests': [],
        'other': []
    }
    
    try:
        for root, dirs, filenames in os.walk(project_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not should_ignore_file(os.path.join(root, d))]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                
                if should_ignore_file(file_path):
                    continue
                    
                # Skip test files if not requested
                if not include_tests and ('test' in filename.lower() or 'test' in Path(file_path).parent.name.lower()):
                    continue
                    
                file_info = _get_file_info(file_path)
                
                # Categorize files
                if file_info.is_python:
                    files['python'].append(file_info)
                elif file_info.is_config:
                    files['config'].append(file_info)
                elif filename.lower() in ['readme.md', 'readme.rst', 'readme.txt', 'changelog.md', 'changelog.rst']:
                    files['documentation'].append(file_info)
                elif 'test' in filename.lower():
                    files['tests'].append(file_info)
                else:
                    files['other'].append(file_info)
                    
    except Exception as e:
        logger.error(f"Error scanning project files: {e}")
        
    return files


def _get_file_info(file_path: str) -> FileInfo:
    """
    Get detailed information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        FileInfo object with file details
    """
    path = Path(file_path)
    
    try:
        size = path.stat().st_size
        mime_type, _ = mimetypes.guess_type(file_path)
        
        file_info = FileInfo(
            path=str(path),
            size=size,
            mime_type=mime_type,
            is_text=is_text_file(file_path),
            is_python=is_python_file(file_path),
            is_config=path.name in CONFIG_FILES
        )
        
        if file_info.is_text:
            file_info.encoding = detect_encoding(file_path)
            
        return file_info
        
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return FileInfo(path=str(path), size=0)


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes, or 0 if error
    """
    try:
        return Path(file_path).stat().st_size
    except Exception:
        return 0


def create_directory(directory_path: str) -> bool:
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if directory was created or already exists
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False


def get_relative_path(file_path: str, base_path: str) -> str:
    """
    Get relative path from base path.
    
    Args:
        file_path: Full path to file
        base_path: Base path to calculate relative from
        
    Returns:
        Relative path
    """
    try:
        return str(Path(file_path).relative_to(Path(base_path)))
    except ValueError:
        return file_path
