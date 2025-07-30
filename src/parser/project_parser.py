from pathlib import Path
from typing import Any, Dict, List
from .metadata_parser import parse_metadata
from .dependency_parser import parse_dependencies
from .structure_parser import parse_structure
from .example_parser import parse_examples
from .code_parser import parse_code_file
from .entry_point_parser import parse_entry_points

def _is_test_file(file_path: str) -> bool:
        """Check if a file is a test file based on naming conventions."""
        path = Path(file_path)
        
        # Check if file is in a test directory
        if any(part.lower() in ('test', 'tests') for part in path.parts[:-1]):
            return True
        
        # Check if filename suggests it's a test
        name = path.stem.lower()
        if name.startswith('test_') or name.endswith('_test') or name == 'test':
            return True
        
        return False


def parse_project(
    project_path: str,
    include_tests: bool = False,
    include_private: bool = False
) -> Dict[str, Any]:
    """
    Orchestrate comprehensive parsing of Python project including entry points.
    """
    project_path = Path(project_path).resolve()

    # Parse project-level information
    metadata = parse_metadata(str(project_path))
    dependencies = parse_dependencies(str(project_path))
    entry_points = parse_entry_points(str(project_path))
    
    # Get basic file structure
    structure = parse_structure(str(project_path))

    # Filter test files if requested
    if not include_tests:
        structure = [
            mod for mod in structure
            if not _is_test_file(mod["file"])
        ]

    # Parse detailed code information for each module
    detailed_modules = []
    all_examples = []
    
    # Determine which files are entry points (should include full source)
    entry_point_files = set()
    for ep_category in entry_points.values():
        if isinstance(ep_category, list):
            for ep in ep_category:
                if 'file' in ep:
                    entry_point_files.add(ep['file'])
    
    for module_basic in structure:
        file_path = module_basic["file"]
        
        # Extract full code for entry points
        is_entry_point = file_path in entry_point_files or _is_likely_entry_point(file_path)
        
        # Get detailed code information
        code_details = parse_code_file(file_path, extract_full_code=is_entry_point)
        
        if code_details:
            detailed_modules.append(code_details)
        else:
            detailed_modules.append(module_basic)
        
        # Extract examples from this file
        file_examples = parse_examples(file_path)
        all_examples.extend(file_examples)

    # Calculate comprehensive stats
    total_classes = sum(len(mod.get("classes", [])) for mod in detailed_modules)
    total_functions = sum(len(mod.get("functions", [])) for mod in detailed_modules)
    total_methods = sum(
        sum(len(cls.get("methods", [])) for cls in mod.get("classes", []))
        for mod in detailed_modules
    )

    return {
        "success": True,
        "project_metadata": metadata,
        "dependencies": dependencies,
        "entry_points": entry_points,  # New: Entry point information
        "modules": detailed_modules,
        "examples": all_examples,
        "stats": {
            "files_processed": len(detailed_modules),
            "examples_found": len(all_examples),
            "classes_found": total_classes,
            "functions_found": total_functions,
            "methods_found": total_methods,
            "entry_points_found": sum(len(eps) if isinstance(eps, list) else 0 for eps in entry_points.values()),
        }
    }

def _is_likely_entry_point(file_path: str) -> bool:
    """Check if a file is likely an entry point based on naming patterns."""
    file_name = Path(file_path).name
    entry_patterns = [
        "main.py", "cli.py", "__main__.py", "run.py", "app.py", 
        "start.py", "launch.py", "execute.py"
    ]
    return any(file_name == pattern or file_name.endswith(f"_{pattern}") for pattern in entry_patterns)

# Test harness
if __name__ == "__main__":
    import sys
    import json
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    result = parse_project(project_root)
    print(json.dumps(result, indent=2))
