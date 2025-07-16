# src/parsing/file_scanner.py

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Enhanced ignore patterns for better project scanning
IGNORE_DIRS: Set[str] = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "venv",
    ".venv",
    "env",
    ".env",
    "build",
    "dist",
    "node_modules",
    ".coverage",
    "htmlcov",
    ".egg-info",
    "wheels",
}

IGNORE_PATTERNS: Set[str] = {
    "*.egg-info",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "__pycache__",
}

IGNORE_FILES: Set[str] = {
    ".DS_Store",
    "Thumbs.db",
    ".gitkeep",
    ".gitignore",
    ".pytest_cache",
}

# Framework detection patterns
FRAMEWORK_INDICATORS = {
    "flask": {
        "files": ["app.py", "wsgi.py", "flask_app.py"],
        "imports": ["flask", "Flask"],
        "patterns": ["@app.route", "Flask(__name__)"]
    },
    "django": {
        "files": ["manage.py", "settings.py", "urls.py", "wsgi.py", "asgi.py"],
        "imports": ["django", "Django"],
        "patterns": ["DJANGO_SETTINGS_MODULE", "django.setup()"]
    },
    "fastapi": {
        "files": ["main.py", "app.py", "api.py"],
        "imports": ["fastapi", "FastAPI"],
        "patterns": ["FastAPI()", "@app.get", "@app.post"]
    },
    "streamlit": {
        "files": ["streamlit_app.py", "app.py"],
        "imports": ["streamlit"],
        "patterns": ["st.", "streamlit."]
    },
    "pytest": {
        "files": ["conftest.py", "pytest.ini"],
        "imports": ["pytest"],
        "patterns": ["def test_", "class Test"]
    },
    "sphinx": {
        "files": ["conf.py", "make.bat", "Makefile"],
        "directories": ["_build", "_static", "_templates"],
        "patterns": ["sphinx"]
    }
}


def should_ignore_path(path: Path) -> bool:
    """
    Enhanced path filtering with better pattern matching.
    
    Args:
        path: The pathlib.Path object to check
        
    Returns:
        True if the path should be ignored, False otherwise
    """
    if path.name in IGNORE_FILES:
        return True
    
    # Check for ignored directory names
    if any(part in IGNORE_DIRS for part in path.parts):
        return True
    
    # Check for ignored patterns
    if any(path.match(pattern) for pattern in IGNORE_PATTERNS):
        return True
    
    # Check for temporary files
    if path.name.startswith('.') and path.name not in {'.gitignore', '.env', '.flake8'}:
        return True
    
    # Check for backup files
    if path.name.endswith(('.bak', '.tmp', '.temp', '~')):
        return True
    
    return False


def is_python_file(filepath: str) -> bool:
    """
    Enhanced Python file detection.
    
    Args:
        filepath: Path to check
        
    Returns:
        True if it's a Python file, False otherwise
    """
    path = Path(filepath)
    
    # Standard Python files
    if path.suffix.lower() == '.py':
        return True
    
    # Python files without extension (scripts)
    if not path.suffix and path.is_file():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#!') and 'python' in first_line.lower():
                    return True
        except Exception:
            pass
    
    return False


def calculate_file_importance(filepath: str, file_structure: Dict[str, List[str]]) -> float:
    """
    Calculate importance score for LLM context prioritization.
    
    Args:
        filepath: Path to the file
        file_structure: Complete project structure
        
    Returns:
        Importance score (0.0 to 10.0)
    """
    score = 0.0
    path = Path(filepath)
    filename = path.name.lower()
    
    # Main module patterns get highest priority
    main_patterns = ["main.py", "app.py", "__init__.py", "__main__.py", "run.py", "cli.py"]
    if any(pattern in filename for pattern in main_patterns):
        score += 10.0
    
    # Setup and configuration files
    setup_patterns = ["setup.py", "pyproject.toml", "requirements.txt", "pipfile", "poetry.lock"]
    if any(pattern in filename for pattern in setup_patterns):
        score += 9.0
    
    # Example files are valuable for usage demonstration
    example_keywords = ["example", "demo", "sample", "tutorial", "guide"]
    if any(keyword in filename for keyword in example_keywords):
        score += 8.0
    
    # API and web framework entry points
    web_patterns = ["wsgi.py", "asgi.py", "server.py", "api.py"]
    if any(pattern in filename for pattern in web_patterns):
        score += 7.5
    
    # Django specific files
    django_patterns = ["models.py", "views.py", "urls.py", "settings.py", "manage.py"]
    if any(pattern in filename for pattern in django_patterns):
        score += 7.0
    
    # Configuration files
    config_patterns = ["config.py", "settings.py", "conf.py", ".env", "constants.py"]
    if any(pattern in filename for pattern in config_patterns):
        score += 6.5
    
    # Test files (important for understanding usage)
    if "test" in filename or filename.startswith("test_"):
        score += 6.0
    
    # Documentation files
    doc_patterns = ["readme", "changelog", "license", "contributing", "authors"]
    if any(pattern in filename for pattern in doc_patterns):
        score += 5.5
    
    # Utility and helper files
    util_patterns = ["utils.py", "helpers.py", "common.py", "base.py", "core.py"]
    if any(pattern in filename for pattern in util_patterns):
        score += 5.0
    
    # Files in root directory get bonus
    if str(path.parent) in [".", "./"]:
        score += 2.0
    
    # Files in src/ directory get bonus
    if "src" in path.parts:
        score += 1.5
    
    # Python files get base score
    if is_python_file(filepath):
        score += 1.0
    
    # Penalty for deeply nested files
    if len(path.parts) > 4:
        score -= 1.0
    
    # Penalty for very long filenames (likely auto-generated)
    if len(filename) > 50:
        score -= 0.5
    
    return max(0.0, min(10.0, score))


def detect_framework_files(file_structure: Dict[str, List[str]]) -> List[str]:
    """
    Identify framework-specific files and patterns.
    
    Args:
        file_structure: Dictionary mapping directories to file lists
        
    Returns:
        List of detected frameworks
    """
    detected_frameworks = []
    all_files = []
    
    # Flatten file structure for analysis
    for directory, files in file_structure.items():
        for file in files:
            all_files.append(os.path.join(directory, file).replace("\\", "/"))
    
    all_files_str = " ".join(all_files).lower()
    
    for framework, indicators in FRAMEWORK_INDICATORS.items():
        framework_score = 0
        
        # Check for specific files
        for file_pattern in indicators.get("files", []):
            if any(file_pattern.lower() in file.lower() for file in all_files):
                framework_score += 3
        
        # Check for directories
        for dir_pattern in indicators.get("directories", []):
            if any(dir_pattern.lower() in directory.lower() for directory in file_structure.keys()):
                framework_score += 2
        
        # Basic pattern matching in filenames
        for pattern in indicators.get("patterns", []):
            if pattern.lower() in all_files_str:
                framework_score += 1
        
        # If score is high enough, consider framework detected
        if framework_score >= 2:
            detected_frameworks.append(framework)
    
    return detected_frameworks


def identify_example_files(file_structure: Dict[str, List[str]]) -> List[str]:
    """
    Identify example and demo files in the project.
    
    Args:
        file_structure: Dictionary mapping directories to file lists
        
    Returns:
        List of example file paths
    """
    example_files = []
    example_keywords = ["example", "demo", "sample", "tutorial", "guide", "test"]
    
    for directory, files in file_structure.items():
        for file in files:
            filename_lower = file.lower()
            
            # Check if filename contains example keywords
            if any(keyword in filename_lower for keyword in example_keywords):
                example_files.append(os.path.join(directory, file))
            
            # Check if directory name suggests examples
            directory_lower = directory.lower()
            if any(keyword in directory_lower for keyword in ["example", "demo", "sample"]):
                if is_python_file(file):
                    example_files.append(os.path.join(directory, file))
    
    return example_files


def categorize_files(file_structure: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Categorize files by their purpose and importance.
    
    Args:
        file_structure: Dictionary mapping directories to file lists
        
    Returns:
        Dictionary with categorized file lists
    """
    categories = {
        "core_modules": [],
        "utility_modules": [],
        "test_files": [],
        "example_files": [],
        "config_files": [],
        "documentation": [],
        "web_framework": [],
        "data_science": [],
    }
    
    for directory, files in file_structure.items():
        for file in files:
            filepath = os.path.join(directory, file)
            filename_lower = file.lower()
            
            # Core modules
            if any(pattern in filename_lower for pattern in 
                   ["main.py", "app.py", "__init__.py", "core.py", "base.py"]):
                categories["core_modules"].append(filepath)
            
            # Utility modules
            elif any(pattern in filename_lower for pattern in 
                     ["utils.py", "helpers.py", "common.py", "tools.py"]):
                categories["utility_modules"].append(filepath)
            
            # Test files
            elif ("test" in filename_lower or filename_lower.startswith("test_") or
                  "test" in directory.lower()):
                categories["test_files"].append(filepath)
            
            # Example files
            elif any(keyword in filename_lower for keyword in 
                     ["example", "demo", "sample", "tutorial"]):
                categories["example_files"].append(filepath)
            
            # Configuration files
            elif any(pattern in filename_lower for pattern in 
                     ["config", "settings", "conf", ".env", "constants"]):
                categories["config_files"].append(filepath)
            
            # Documentation
            elif any(pattern in filename_lower for pattern in 
                     ["readme", "doc", "changelog", "license", "contributing"]):
                categories["documentation"].append(filepath)
            
            # Web framework files
            elif any(pattern in filename_lower for pattern in 
                     ["views.py", "models.py", "urls.py", "wsgi.py", "asgi.py", "api.py"]):
                categories["web_framework"].append(filepath)
            
            # Data science files
            elif any(pattern in filename_lower for pattern in 
                     ["analysis", "model", "train", "predict", "data"]) and file.endswith(".py"):
                categories["data_science"].append(filepath)
    
    return categories


def scan_directory(root_path: str) -> Dict[str, List[str]]:
    """
    Enhanced directory scanning with better structure mapping.
    
    Args:
        root_path: Root directory path to scan
        
    Returns:
        Dictionary mapping directory paths to file lists
    """
    project_structure: Dict[str, List[str]] = {}
    
    try:
        root = Path(root_path).resolve()
    except (FileNotFoundError, OSError):
        print(f"Error: Cannot access directory '{root_path}'")
        return {}
    
    if not root.exists() or not root.is_dir():
        print(f"Error: '{root_path}' is not a valid directory")
        return {}
    
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current_dir_path = Path(dirpath)
        
        # Prune ignored directories early for efficiency
        dirnames[:] = [d for d in dirnames if not should_ignore_path(current_dir_path / d)]
        
        # Skip processing if current directory should be ignored
        if should_ignore_path(current_dir_path):
            continue
        
        # Filter and sort files
        filtered_files = []
        for filename in filenames:
            file_path = current_dir_path / filename
            if not should_ignore_path(file_path):
                filtered_files.append(filename)
        
        # Only include directories that have files
        if filtered_files:
            relative_dir_path = os.path.relpath(dirpath, root)
            
            # Normalize path representation
            if relative_dir_path == ".":
                key = "./"
            else:
                key = str(Path(relative_dir_path).as_posix()) + "/"
            
            # Sort files for consistent output
            project_structure[key] = sorted(filtered_files)
    
    return project_structure


def get_file_statistics(file_structure: Dict[str, List[str]]) -> Dict[str, any]:
    """
    Generate statistics about the project file structure.
    
    Args:
        file_structure: Dictionary mapping directories to file lists
        
    Returns:
        Dictionary with project statistics
    """
    stats = {
        "total_directories": len(file_structure),
        "total_files": sum(len(files) for files in file_structure.values()),
        "python_files": 0,
        "test_files": 0,
        "config_files": 0,
        "documentation_files": 0,
        "max_directory_depth": 0,
        "largest_directory": "",
        "largest_directory_file_count": 0,
    }
    
    for directory, files in file_structure.items():
        # Count Python files
        python_files_in_dir = sum(1 for f in files if is_python_file(f))
        stats["python_files"] += python_files_in_dir
        
        # Count test files
        test_files_in_dir = sum(1 for f in files if "test" in f.lower())
        stats["test_files"] += test_files_in_dir
        
        # Count config files
        config_files_in_dir = sum(1 for f in files if any(
            pattern in f.lower() for pattern in ["config", "settings", ".env", "requirements"]
        ))
        stats["config_files"] += config_files_in_dir
        
        # Count documentation files
        doc_files_in_dir = sum(1 for f in files if any(
            pattern in f.lower() for pattern in ["readme", "doc", "changelog", "license"]
        ))
        stats["documentation_files"] += doc_files_in_dir
        
        # Track directory depth
        depth = directory.count("/")
        stats["max_directory_depth"] = max(stats["max_directory_depth"], depth)
        
        # Track largest directory
        if len(files) > stats["largest_directory_file_count"]:
            stats["largest_directory"] = directory
            stats["largest_directory_file_count"] = len(files)
    
    return stats


def prioritize_files_for_llm(file_structure: Dict[str, List[str]], 
                            max_files: int = 50) -> List[Tuple[str, float]]:
    """
    Prioritize files for LLM processing based on importance scores.
    
    Args:
        file_structure: Dictionary mapping directories to file lists
        max_files: Maximum number of files to return
        
    Returns:
        List of (filepath, importance_score) tuples, sorted by importance
    """
    file_scores = []
    
    for directory, files in file_structure.items():
        for file in files:
            filepath = os.path.join(directory, file)
            importance_score = calculate_file_importance(filepath, file_structure)
            
            # Only include files with reasonable importance
            if importance_score > 0.5:
                file_scores.append((filepath, importance_score))
    
    # Sort by importance score (descending) and limit results
    file_scores.sort(key=lambda x: x[1], reverse=True)
    return file_scores[:max_files]
