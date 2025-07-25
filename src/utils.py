import os
import logging
from typing import Optional, Union


def count_tokens_approx(text: str) -> int:
    """
    Approximate the number of tokens in a text string.

    Uses a conservative heuristic assuming 4 characters per token,
    which roughly aligns with many LLM tokenizers.

    Args:
        text (str): Input string.

    Returns:
        int: Approximate token count.
    """
    if not text:
        return 0
    # Remove leading/trailing whitespace and count characters
    return max(1, len(text) // 4)


def read_file(filepath: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    Safely read text from a file.

    Args:
        filepath (str): Path to the file.
        encoding (str): File encoding, default UTF-8.

    Returns:
        Optional[str]: File content or None if error.
    """
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logging.warning(f"Failed to read file {filepath}: {e}")
        return None


def write_file(filepath: str, content: Union[str, bytes], encoding: str = 'utf-8') -> bool:
    """
    Safely write text or bytes content to a file.

    Args:
        filepath (str): Path to the file.
        content (str or bytes): Content to write.
        encoding (str): Encoding for text files.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        mode = 'w'
        if isinstance(content, bytes):
            mode = 'wb'
        with open(filepath, mode, encoding=None if mode == 'wb' else encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        logging.error(f"Failed to write file {filepath}: {e}")
        return False


def ensure_dir_exists(dir_path: str) -> bool:
    """
    Ensure that a directory exists, creating if necessary.

    Args:
        dir_path (str): Directory path.

    Returns:
        bool: True if directory exists or was created, False if error.
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Unable to create directory {dir_path}: {e}")
        return False
