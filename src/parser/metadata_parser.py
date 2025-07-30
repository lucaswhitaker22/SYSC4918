import ast
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional

def parse_metadata(project_path: str) -> Dict[str, Any]:
    """
    Extract project metadata from multiple sources:
    - pyproject.toml
    - setup.py  
    - setup.cfg
    - __init__.py files
    - README files
    - Project directory structure
    """
    project_path = Path(project_path).resolve()
    metadata = {}
    
    # Try pyproject.toml first (most modern)
    metadata.update(_parse_pyproject_toml(project_path))
    
    # Try setup.py (traditional)
    if not metadata:
        metadata.update(_parse_setup_py(project_path))
    
    # Try setup.cfg (setuptools)
    if not metadata:
        metadata.update(_parse_setup_cfg(project_path))
    
    # Extract from __init__.py files
    init_metadata = _parse_init_files(project_path)
    for key, value in init_metadata.items():
        if not metadata.get(key):
            metadata[key] = value
    
    # Extract from README
    readme_metadata = _parse_readme(project_path)
    for key, value in readme_metadata.items():
        if not metadata.get(key):
            metadata[key] = value
    
    # Infer from directory structure if still missing
    if not metadata.get('name'):
        metadata['name'] = project_path.name
    
    return metadata

def _parse_pyproject_toml(project_path: Path) -> Dict[str, Any]:
    """Parse pyproject.toml for project metadata."""
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return {}
    
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}
    
    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        
        project = data.get("project", {})
        metadata = {}
        
        # Standard PEP 621 fields
        for field in ["name", "version", "description", "readme", "license"]:
            if field in project:
                metadata[field] = project[field]
        
        # Authors
        if "authors" in project:
            authors = project["authors"]
            if isinstance(authors, list) and authors:
                metadata["author"] = authors[0].get("name", "")
                metadata["author_email"] = authors[0].get("email", "")
        
        # URLs
        if "urls" in project:
            urls = project["urls"]
            metadata["homepage"] = urls.get("homepage", urls.get("Home", ""))
            metadata["repository"] = urls.get("repository", urls.get("Repository", ""))
        
        return metadata
        
    except Exception:
        return {}

def _parse_setup_py(project_path: Path) -> Dict[str, Any]:
    """Parse setup.py for project metadata."""
    setup_py = project_path / "setup.py"
    if not setup_py.exists():
        return {}
    
    try:
        with open(setup_py, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Try to parse as AST first
        try:
            tree = ast.parse(content)
            return _extract_setup_call_metadata(tree)
        except:
            # Fallback to regex parsing
            return _extract_setup_regex_metadata(content)
            
    except Exception:
        return {}

def _extract_setup_call_metadata(tree: ast.AST) -> Dict[str, Any]:
    """Extract metadata from setup() call in AST."""
    metadata = {}
    
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) 
            and getattr(node.func, "id", "") == "setup"):
            
            for kw in node.keywords:
                if kw.arg in ("name", "version", "description", "author", 
                             "author_email", "url", "license"):
                    if isinstance(kw.value, ast.Constant):
                        metadata[kw.arg] = kw.value.value
                    elif isinstance(kw.value, ast.Str):  # Python < 3.8
                        metadata[kw.arg] = kw.value.s
    
    return metadata

def _extract_setup_regex_metadata(content: str) -> Dict[str, Any]:
    """Extract metadata using regex patterns."""
    metadata = {}
    
    patterns = {
        'name': r'name\s*=\s*["\']([^"\']+)["\']',
        'version': r'version\s*=\s*["\']([^"\']+)["\']',
        'description': r'description\s*=\s*["\']([^"\']+)["\']',
        'author': r'author\s*=\s*["\']([^"\']+)["\']',
        'author_email': r'author_email\s*=\s*["\']([^"\']+)["\']',
        'url': r'url\s*=\s*["\']([^"\']+)["\']',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            metadata[key] = match.group(1)
    
    return metadata

def _parse_setup_cfg(project_path: Path) -> Dict[str, Any]:
    """Parse setup.cfg for project metadata."""
    setup_cfg = project_path / "setup.cfg"
    if not setup_cfg.exists():
        return {}
    
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read(setup_cfg)
        
        metadata = {}
        if 'metadata' in config:
            section = config['metadata']
            for key in ('name', 'version', 'description', 'author', 'author_email', 'url'):
                if key in section:
                    metadata[key] = section[key]
        
        return metadata
    except Exception:
        return {}

def _parse_init_files(project_path: Path) -> Dict[str, Any]:
    """Extract metadata from __init__.py files."""
    metadata = {}
    
    # Look for __init__.py files
    init_files = list(project_path.glob("**/__init__.py"))
    
    for init_file in init_files:
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for common metadata variables
            patterns = {
                'version': r'__version__\s*=\s*["\']([^"\']+)["\']',
                'author': r'__author__\s*=\s*["\']([^"\']+)["\']',
                'description': r'__description__\s*=\s*["\']([^"\']+)["\']',
                'email': r'__email__\s*=\s*["\']([^"\']+)["\']',
            }
            
            for key, pattern in patterns.items():
                if not metadata.get(key):
                    match = re.search(pattern, content)
                    if match:
                        metadata[key] = match.group(1)
        except Exception:
            continue
    
    return metadata

def _parse_readme(project_path: Path) -> Dict[str, Any]:
    """Extract metadata from README files."""
    metadata = {}
    
    # Look for README files
    readme_patterns = ["README*", "readme*", "Readme*"]
    readme_files = []
    
    for pattern in readme_patterns:
        readme_files.extend(list(project_path.glob(pattern)))
    
    for readme_file in readme_files:
        if readme_file.is_file():
            try:
                with open(readme_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract title from first heading
                if not metadata.get('description'):
                    title_match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
                    if title_match:
                        metadata['description'] = title_match.group(1).strip()
                
                break
            except Exception:
                continue
    
    return metadata
