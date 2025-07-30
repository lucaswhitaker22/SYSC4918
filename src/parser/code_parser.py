import ast
from pathlib import Path
from typing import Optional, Dict, Any, List

def parse_code_file(file_path: str, extract_full_code: bool = False) -> Optional[Dict[str, Any]]:
    """
    Parse a Python file and extract detailed information including full code for entry points.
    
    Args:
        file_path: Path to the Python file
        extract_full_code: Whether to include full source code (for entry points)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return None

    module_name = Path(file_path).stem
    module_info = {
        "name": module_name,
        "file": file_path,
        "docstring": ast.get_docstring(tree),
        "classes": [],
        "functions": [],
        "imports": [],
        "constants": []
    }
    
    # Include full source code for entry points
    if extract_full_code:
        module_info["source_code"] = source

    # Parse module-level nodes
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "docstring": ast.get_docstring(node),
                "methods": [],
                "bases": [_get_name_from_node(base) for base in node.bases],
                "decorators": [_get_name_from_node(dec) for dec in node.decorator_list]
            }
            
            # Parse class methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_info = {
                        "name": item.name,
                        "docstring": ast.get_docstring(item),
                        "decorators": [_get_name_from_node(dec) for dec in item.decorator_list],
                        "args": [arg.arg for arg in item.args.args]
                    }
                    class_info["methods"].append(method_info)
            
            module_info["classes"].append(class_info)
            
        elif isinstance(node, ast.FunctionDef):
            function_info = {
                "name": node.name,
                "docstring": ast.get_docstring(node),
                "decorators": [_get_name_from_node(dec) for dec in node.decorator_list],
                "args": [arg.arg for arg in node.args.args]
            }
            module_info["functions"].append(function_info)
            
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module_info["imports"].append(alias.name)
                
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                import_str = f"from {module_name} import {alias.name}" if module_name else f"import {alias.name}"
                module_info["imports"].append(import_str)

    return module_info

def _get_name_from_node(node) -> str:
    """Helper to extract name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name_from_node(node.value)}.{node.attr}"
    elif isinstance(node, ast.Constant):
        return str(node.value)
    else:
        return str(node)
