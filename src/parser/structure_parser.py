import os
from pathlib import Path

def parse_structure(project_path):
    """
    Traverse project directory and find all Python (.py) files,
    returning a list of dicts with keys: 'file' (full path) and 'name' (module name).
    Ignores folders named __pycache__, venv, build, dist, tests, docs.
    """
    project_path = Path(project_path).resolve()
    ignored_dirs = {"__pycache__", "venv", "build", "dist", "tests", "docs"}

    modules = []

    for root, dirs, files in os.walk(project_path):
        # Filter ignored dirs to avoid descending into them
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for file in files:
            if file.endswith(".py"):
                full_path = Path(root) / file
                modules.append({
                    "file": str(full_path.resolve()),
                    "name": full_path.stem
                })

    return modules
