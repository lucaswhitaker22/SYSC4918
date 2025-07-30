import ast
import re
from pathlib import Path
from typing import List, Dict, Any

def parse_dependencies(project_path: str) -> List[str]:
    """
    Extract dependencies from multiple sources:
    - pyproject.toml (PEP 621 and Poetry)
    - setup.py (install_requires)
    - setup.cfg (options.install_requires)  
    - requirements.txt files (and variants)
    - Pipfile (pipenv)
    - environment.yml (conda)
    """
    project_path = Path(project_path).resolve()
    dependencies = []
    
    # Try each source in order of preference
    deps_sources = [
        _parse_pyproject_dependencies,
        _parse_setup_py_dependencies,
        _parse_setup_cfg_dependencies,
        _parse_requirements_files,
        _parse_pipfile_dependencies,
        _parse_conda_dependencies,
    ]
    
    for parse_func in deps_sources:
        deps = parse_func(project_path)
        if deps:
            dependencies.extend(deps)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_deps = []
    for dep in dependencies:
        if dep not in seen:
            seen.add(dep)
            unique_deps.append(dep)
    
    return unique_deps

def _parse_pyproject_dependencies(project_path: Path) -> List[str]:
    """Parse dependencies from pyproject.toml (PEP 621 and Poetry)."""
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return []
    
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return []
    
    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        
        dependencies = []
        
        # PEP 621 project dependencies
        project = data.get("project", {})
        if "dependencies" in project:
            dependencies.extend(project["dependencies"])
        
        # Optional dependencies
        if "optional-dependencies" in project:
            for group_deps in project["optional-dependencies"].values():
                dependencies.extend(group_deps)
        
        # Poetry dependencies
        poetry = data.get("tool", {}).get("poetry", {})
        if "dependencies" in poetry:
            poetry_deps = poetry["dependencies"]
            for name, spec in poetry_deps.items():
                if name != "python":  # Skip Python version
                    if isinstance(spec, str):
                        dependencies.append(f"{name}{spec}")
                    elif isinstance(spec, dict) and "version" in spec:
                        dependencies.append(f"{name}{spec['version']}")
                    else:
                        dependencies.append(name)
        
        if "dev-dependencies" in poetry:
            dev_deps = poetry["dev-dependencies"]
            for name, spec in dev_deps.items():
                if isinstance(spec, str):
                    dependencies.append(f"{name}{spec}")
                elif isinstance(spec, dict) and "version" in spec:
                    dependencies.append(f"{name}{spec['version']}")
                else:
                    dependencies.append(name)
        
        return dependencies
        
    except Exception:
        return []

def _parse_setup_py_dependencies(project_path: Path) -> List[str]:
    """Parse dependencies from setup.py."""
    setup_py = project_path / "setup.py"
    if not setup_py.exists():
        return []
    
    try:
        with open(setup_py, "r", encoding="utf-8") as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
            return _extract_setup_dependencies_ast(tree)
        except:
            return _extract_setup_dependencies_regex(content)
            
    except Exception:
        return []

def _extract_setup_dependencies_ast(tree: ast.AST) -> List[str]:
    """Extract dependencies from setup() call using AST."""
    dependencies = []
    
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) 
            and getattr(node.func, "id", "") == "setup"):
            
            for kw in node.keywords:
                if kw.arg in ("install_requires", "requires"):
                    if isinstance(kw.value, (ast.List, ast.Tuple)):
                        for elt in kw.value.elts:
                            if isinstance(elt, ast.Constant):
                                dependencies.append(elt.value)
                            elif isinstance(elt, ast.Str):  # Python < 3.8
                                dependencies.append(elt.s)
    
    return dependencies

def _extract_setup_dependencies_regex(content: str) -> List[str]:
    """Extract dependencies using regex patterns."""
    dependencies = []
    
    # Look for install_requires
    install_requires_pattern = r'install_requires\s*=\s*\[(.*?)\]'
    match = re.search(install_requires_pattern, content, re.DOTALL)
    if match:
        deps_str = match.group(1)
        # Extract quoted strings
        dep_pattern = r'["\']([^"\']+)["\']'
        dependencies.extend(re.findall(dep_pattern, deps_str))
    
    return dependencies

def _parse_setup_cfg_dependencies(project_path: Path) -> List[str]:
    """Parse dependencies from setup.cfg."""
    setup_cfg = project_path / "setup.cfg"
    if not setup_cfg.exists():
        return []
    
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read(setup_cfg)
        
        dependencies = []
        if 'options' in config and 'install_requires' in config['options']:
            deps_str = config['options']['install_requires']
            # Split by newlines and clean up
            deps = [dep.strip() for dep in deps_str.split('\n') if dep.strip()]
            dependencies.extend(deps)
        
        return dependencies
    except Exception:
        return []

def _parse_requirements_files(project_path: Path) -> List[str]:
    """Parse dependencies from requirements files."""
    dependencies = []
    
    # Common requirements file patterns
    req_patterns = [
        "requirements.txt",
        "requirements*.txt", 
        "reqs.txt",
        "deps.txt",
        "dependencies.txt",
        "dev-requirements.txt",
        "test-requirements.txt"
    ]
    
    req_files = []
    for pattern in req_patterns:
        req_files.extend(list(project_path.glob(pattern)))
        req_files.extend(list(project_path.glob(f"**/{pattern}")))
    
    for req_file in req_files:
        if req_file.is_file():
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#') and not line.startswith('-'):
                            # Remove inline comments
                            dep = line.split('#')[0].strip()
                            if dep:
                                dependencies.append(dep)
            except Exception:
                continue
    
    return dependencies

def _parse_pipfile_dependencies(project_path: Path) -> List[str]:
    """Parse dependencies from Pipfile."""
    pipfile = project_path / "Pipfile"
    if not pipfile.exists():
        return []
    
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return []
    
    try:
        with open(pipfile, "rb") as f:
            data = tomllib.load(f)
        
        dependencies = []
        
        # Regular packages
        if "packages" in data:
            for name, spec in data["packages"].items():
                if isinstance(spec, str):
                    dependencies.append(f"{name}{spec}")
                else:
                    dependencies.append(name)
        
        # Dev packages
        if "dev-packages" in data:
            for name, spec in data["dev-packages"].items():
                if isinstance(spec, str):
                    dependencies.append(f"{name}{spec}")
                else:
                    dependencies.append(name)
        
        return dependencies
        
    except Exception:
        return []

def _parse_conda_dependencies(project_path: Path) -> List[str]:
    """Parse dependencies from conda environment files."""
    dependencies = []
    
    env_files = list(project_path.glob("environment*.yml")) + list(project_path.glob("environment*.yaml"))
    
    for env_file in env_files:
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple parsing for dependencies section
            in_deps = False
            for line in content.split('\n'):
                line = line.strip()
                if line == "dependencies:":
                    in_deps = True
                    continue
                elif in_deps:
                    if line.startswith('- ') and not line.startswith('- pip:'):
                        dep = line[2:].strip()
                        if dep:
                            dependencies.append(dep)
                    elif not line.startswith(' ') and not line.startswith('-'):
                        in_deps = False
        except Exception:
            continue
    
    return dependencies
