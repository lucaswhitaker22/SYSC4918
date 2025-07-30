"""
Parser for identifying and extracting entry points and main scripts.
These are crucial for generating usage instructions in READMEs.
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Any

def parse_entry_points(project_path: str) -> Dict[str, Any]:
    """
    Identify and extract entry points including CLI scripts, main modules, and setup.py scripts.
    """
    project_path = Path(project_path).resolve()
    
    entry_points = {
        "main_modules": [],
        "cli_scripts": [],
        "setup_scripts": [],
        "package_entry_points": []
    }
    
    # Find main modules (__main__.py files)
    main_files = list(project_path.glob("**/__main__.py"))
    for main_file in main_files:
        entry_info = _extract_main_module_info(main_file)
        if entry_info:
            entry_points["main_modules"].append(entry_info)
    
    # Find CLI scripts (common patterns)
    cli_patterns = ["cli.py", "main.py", "*_cli.py", "run.py", "app.py"]
    for pattern in cli_patterns:
        cli_files = list(project_path.glob(f"**/{pattern}"))
        for cli_file in cli_files:
            # Skip if already found as __main__.py
            if cli_file.name == "__main__.py":
                continue
            entry_info = _extract_cli_script_info(cli_file)
            if entry_info:
                entry_points["cli_scripts"].append(entry_info)
    
    # Extract setup.py console scripts and entry points
    setup_py = project_path / "setup.py"
    if setup_py.exists():
        setup_entry_points = _extract_setup_entry_points(setup_py)
        entry_points["setup_scripts"].extend(setup_entry_points)
    
    # Extract pyproject.toml entry points
    pyproject_toml = project_path / "pyproject.toml"
    if pyproject_toml.exists():
        pyproject_entry_points = _extract_pyproject_entry_points(pyproject_toml)
        entry_points["package_entry_points"].extend(pyproject_entry_points)
    
    return entry_points

def _extract_main_module_info(main_file: Path) -> Dict[str, Any]:
    """Extract information from __main__.py files."""
    try:
        with open(main_file, 'r', encoding='utf-8') as f:
            source = f.read()
        
        return {
            "type": "main_module",
            "file": str(main_file),
            "usage": f"python -m {_get_package_name_from_main(main_file)}",
            "source_code": source,
            "docstring": _extract_module_docstring(source),
            "description": "Main module entry point"
        }
    except Exception:
        return None

def _extract_cli_script_info(cli_file: Path) -> Dict[str, Any]:
    """Extract information from CLI script files."""
    try:
        with open(cli_file, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Check if this looks like a CLI script
        if not _is_cli_script(source):
            return None
        
        return {
            "type": "cli_script",
            "file": str(cli_file),
            "usage": f"python {cli_file.name}",
            "source_code": source,
            "docstring": _extract_module_docstring(source),
            "description": "Command-line interface script",
            "argument_parser": _extract_argument_parser_info(source)
        }
    except Exception:
        return None

def _extract_setup_entry_points(setup_file: Path) -> List[Dict[str, Any]]:
    """Extract console scripts and entry points from setup.py."""
    entry_points = []
    
    try:
        with open(setup_file, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and 
                getattr(node.func, "id", "") == "setup"):
                
                for kw in node.keywords:
                    if kw.arg == "entry_points":
                        # Extract entry points
                        entry_points.extend(_parse_entry_points_dict(kw.value))
                    elif kw.arg == "scripts":
                        # Extract script files
                        entry_points.extend(_parse_scripts_list(kw.value))
    except Exception:
        pass
    
    return entry_points

def _extract_pyproject_entry_points(pyproject_file: Path) -> List[Dict[str, Any]]:
    """Extract entry points from pyproject.toml."""
    entry_points = []
    
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return entry_points
    
    try:
        with open(pyproject_file, "rb") as f:
            data = tomllib.load(f)
        
        # Check project.scripts
        project = data.get("project", {})
        if "scripts" in project:
            for script_name, entry_point in project["scripts"].items():
                entry_points.append({
                    "type": "console_script",
                    "name": script_name,
                    "entry_point": entry_point,
                    "usage": script_name,
                    "description": f"Console script: {script_name}"
                })
        
        # Check project.entry-points
        if "entry-points" in project:
            for group, entries in project["entry-points"].items():
                for name, entry_point in entries.items():
                    entry_points.append({
                        "type": "entry_point",
                        "group": group,
                        "name": name,
                        "entry_point": entry_point,
                        "usage": name if group == "console_scripts" else f"{group}:{name}",
                        "description": f"Entry point: {group}.{name}"
                    })
    
    except Exception:
        pass
    
    return entry_points

def _get_package_name_from_main(main_file: Path) -> str:
    """Get package name from __main__.py file path."""
    parts = main_file.parts
    if "__main__.py" in parts:
        main_index = parts.index("__main__.py")
        if main_index > 0:
            return parts[main_index - 1]
    return main_file.parent.name

def _extract_module_docstring(source: str) -> str:
    """Extract module-level docstring."""
    try:
        tree = ast.parse(source)
        return ast.get_docstring(tree) or ""
    except Exception:
        return ""

def _is_cli_script(source: str) -> bool:
    """Check if source code looks like a CLI script."""
    cli_indicators = [
        "argparse",
        "ArgumentParser",
        "if __name__ == '__main__':",
        "sys.argv",
        "click",
        "@click.command",
        "typer"
    ]
    return any(indicator in source for indicator in cli_indicators)

def _extract_argument_parser_info(source: str) -> Dict[str, Any]:
    """Extract information about argument parser from CLI script."""
    try:
        tree = ast.parse(source)
        
        # Look for ArgumentParser creation and argument definitions
        parser_info = {
            "program_name": None,
            "description": None,
            "arguments": []
        }
        
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                node.func.attr == "ArgumentParser"):
                
                # Extract ArgumentParser arguments
                for kw in node.keywords:
                    if kw.arg == "prog" and isinstance(kw.value, ast.Constant):
                        parser_info["program_name"] = kw.value.value
                    elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                        parser_info["description"] = kw.value.value
        
        return parser_info
    except Exception:
        return {}

def _parse_entry_points_dict(node) -> List[Dict[str, Any]]:
    """Parse entry_points dictionary from setup.py AST node."""
    # This would need more sophisticated AST parsing
    # For now, return empty list
    return []

def _parse_scripts_list(node) -> List[Dict[str, Any]]:
    """Parse scripts list from setup.py AST node."""
    scripts = []
    if isinstance(node, (ast.List, ast.Tuple)):
        for item in node.elts:
            if isinstance(item, ast.Constant):
                scripts.append({
                    "type": "script_file",
                    "file": item.value,
                    "usage": f"python {item.value}",
                    "description": f"Script file: {item.value}"
                })
    return scripts
