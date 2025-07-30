"""
JSON serialization utilities for project data output.

This module provides functions to serialize Python dict/list project data
to JSON files with proper formatting and error handling.
"""

import json
from typing import Any, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def serialize_project_data(data: Any) -> Any:
    """
    Serialize project data; mono pass-through for MVP.
    This can be extended if richer processing is required.
    """
    return data

def format_json_output(data: Any, indent: int = 2) -> str:
    """
    Format data as pretty JSON string.
    """
    try:
        return json.dumps(data, indent=indent, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to format JSON output: {e}")
        return "{}"

def save_json_to_file(data: Any, file_path: str, indent: int = 2) -> bool:
    """
    Save data as JSON to the given filepath.
    Returns True on success, False on failure.
    """
    try:
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        json_text = format_json_output(data, indent=indent)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_text)
        logger.info(f"Saved JSON data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False

def load_json_from_file(file_path: str) -> Optional[Dict]:
    """
    Load and parse JSON file to dict.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        return None
