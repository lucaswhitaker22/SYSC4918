import sys
import os
from pathlib import Path

# Get the directory containing this file (tests directory)
tests_dir = Path(__file__).parent
# Get project root (parent of tests directory)  
project_root = tests_dir.parent
# Get src directory
src_dir = project_root / "src"

# Add both project root and src directory to Python path
for path in [str(project_root), str(src_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Verify paths were added
print(f"Added to sys.path: {project_root}, {src_dir}")
