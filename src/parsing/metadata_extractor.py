# src/parsing/metadata_extractor.py

import ast
import configparser
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        tomllib = None


def extract_project_name(setup_file: str) -> Optional[str]:
    """
    Extracts the project name from setup.py or pyproject.toml files.
    
    Args:
        setup_file: Path to the setup file.
    
    Returns:
        The project name if found, None otherwise.
    """
    file_path = Path(setup_file)
    
    if not file_path.exists():
        return None
    
    if file_path.name == "pyproject.toml":
        toml_data = parse_pyproject_toml(setup_file)
        return toml_data.get("project", {}).get("name") or toml_data.get("tool", {}).get("poetry", {}).get("name")
    
    elif file_path.name == "setup.py":
        metadata = extract_setup_metadata(setup_file)
        return metadata.get("name")
    
    elif file_path.name == "setup.cfg":
        return _extract_name_from_setup_cfg(setup_file)
    
    return None


def parse_dependencies(requirements_file: str) -> List[str]:
    """
    Parses dependencies from a requirements.txt file.
    
    Args:
        requirements_file: Path to the requirements file.
    
    Returns:
        A list of dependency strings.
    """
    dependencies = []
    
    try:
        with open(requirements_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Skip git URLs and local file paths
                if line.startswith(('git+', 'http', 'https', '-e', '.')):
                    continue
                
                # Extract package name (remove version specifiers)
                package_name = re.split(r'[><=!~]', line)[0].strip()
                if package_name:
                    dependencies.append(package_name)
    
    except (FileNotFoundError, IOError):
        pass  # File doesn't exist or can't be read
    
    return dependencies


def extract_setup_metadata(setup_file: str) -> Dict[str, Any]:
    """
    Extracts metadata from a setup.py file using AST parsing.
    
    Args:
        setup_file: Path to the setup.py file.
    
    Returns:
        A dictionary containing extracted metadata.
    """
    metadata = {}
    
    try:
        with open(setup_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (hasattr(node.func, 'id') and node.func.id == 'setup') or \
                   (hasattr(node.func, 'attr') and node.func.attr == 'setup'):
                    
                    # Extract keyword arguments from setup() call
                    for keyword in node.keywords:
                        if keyword.arg in ['name', 'version', 'description', 'author', 'author_email', 'license']:
                            if isinstance(keyword.value, ast.Constant):
                                metadata[keyword.arg] = keyword.value.value
                            elif isinstance(keyword.value, ast.Str):  # For older Python versions
                                metadata[keyword.arg] = keyword.value.s
                    
                    # Extract install_requires for dependencies
                    for keyword in node.keywords:
                        if keyword.arg == 'install_requires':
                            deps = _extract_list_from_ast(keyword.value)
                            if deps:
                                metadata['dependencies'] = deps
    
    except (FileNotFoundError, SyntaxError, IOError):
        pass  # File doesn't exist, has syntax errors, or can't be read
    
    return metadata


def parse_pyproject_toml(toml_file: str) -> Dict[str, Any]:
    """
    Parses a pyproject.toml file and extracts relevant metadata.
    
    Args:
        toml_file: Path to the pyproject.toml file.
    
    Returns:
        A dictionary containing the parsed TOML data.
    """
    if tomllib is None:
        return {}
    
    try:
        with open(toml_file, 'rb') as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError, IOError):
        return {}


def extract_license_info(root_path: str) -> Optional[str]:
    """
    Extract license information from various sources.
    
    Args:
        root_path: Root directory path of the project
        
    Returns:
        License type/name if detected, None otherwise
    """
    license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt", "LICENSE.rst"]
    
    for license_file in license_files:
        file_path = Path(root_path) / license_file
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8')[:500]  # First 500 chars
                license_type = detect_license_type(content)
                if license_type:
                    return license_type
            except (IOError, UnicodeDecodeError):
                continue
    
    # Check setup.py for license info
    setup_file = Path(root_path) / "setup.py"
    if setup_file.exists():
        metadata = extract_setup_metadata(str(setup_file))
        license_info = metadata.get('license')
        if license_info:
            return license_info
    
    # Check pyproject.toml for license info
    pyproject_file = Path(root_path) / "pyproject.toml"
    if pyproject_file.exists():
        toml_data = parse_pyproject_toml(str(pyproject_file))
        license_info = (toml_data.get("project", {}).get("license", {}).get("text") or
                       toml_data.get("tool", {}).get("poetry", {}).get("license"))
        if license_info:
            return license_info
    
    return None


def detect_license_type(content: str) -> Optional[str]:
    """
    Detect license type from license file content.
    
    Args:
        content: License file content
        
    Returns:
        License type if detected, None otherwise
    """
    content_lower = content.lower()
    
    # Common license patterns
    license_patterns = {
        "MIT License": ["mit license", "permission is hereby granted", "mit"],
        "Apache License 2.0": ["apache license", "version 2.0", "apache software foundation"],
        "GNU General Public License v3.0": ["gnu general public license", "version 3", "gpl-3"],
        "GNU General Public License v2.0": ["gnu general public license", "version 2", "gpl-2"],
        "BSD 3-Clause License": ["bsd 3-clause", "redistribution and use in source and binary"],
        "BSD 2-Clause License": ["bsd 2-clause", "redistribution and use in source and binary"],
        "GNU Lesser General Public License": ["gnu lesser general public license", "lgpl"],
        "Mozilla Public License 2.0": ["mozilla public license", "version 2.0", "mpl-2.0"],
        "ISC License": ["isc license", "permission to use, copy, modify"],
        "Unlicense": ["unlicense", "this is free and unencumbered software"]
    }
    
    for license_name, patterns in license_patterns.items():
        if any(pattern in content_lower for pattern in patterns):
            return license_name
    
    return None


def extract_version_info(root_path: str, setup_file: Optional[str] = None) -> Optional[str]:
    """
    Extract version information from multiple sources.
    
    Args:
        root_path: Root directory path of the project
        setup_file: Optional path to setup file
        
    Returns:
        Version string if found, None otherwise
    """
    # Check __init__.py for __version__
    version = _extract_version_from_init(root_path)
    if version:
        return version
    
    # Check setup.py/pyproject.toml
    if setup_file:
        version = _extract_version_from_setup(setup_file)
        if version:
            return version
    
    # Check VERSION file
    version = _extract_version_from_version_file(root_path)
    if version:
        return version
    
    # Check git tags
    version = _extract_version_from_git_tags(root_path)
    if version:
        return version
    
    return None


def _extract_version_from_init(root_path: str) -> Optional[str]:
    """Extract version from __init__.py files."""
    init_paths = [
        Path(root_path) / "__init__.py",
        Path(root_path) / "src" / "__init__.py",
    ]
    
    # Also check package directories
    for item in Path(root_path).iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            init_paths.append(item / "__init__.py")
    
    # Check src/ subdirectories
    src_dir = Path(root_path) / "src"
    if src_dir.exists():
        for item in src_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                init_paths.append(item / "__init__.py")
    
    version_patterns = [
        r"__version__\s*=\s*['\"]([^'\"]+)['\"]",
        r"VERSION\s*=\s*['\"]([^'\"]+)['\"]",
        r"version\s*=\s*['\"]([^'\"]+)['\"]"
    ]
    
    for init_path in init_paths:
        if init_path.exists():
            try:
                content = init_path.read_text(encoding='utf-8')
                for pattern in version_patterns:
                    match = re.search(pattern, content, re.MULTILINE)
                    if match:
                        return match.group(1)
            except (IOError, UnicodeDecodeError):
                continue
    
    return None


def _extract_version_from_setup(setup_file: str) -> Optional[str]:
    """Extract version from setup.py or pyproject.toml."""
    file_path = Path(setup_file)
    
    if file_path.name == "setup.py":
        metadata = extract_setup_metadata(setup_file)
        return metadata.get("version")
    
    elif file_path.name == "pyproject.toml":
        toml_data = parse_pyproject_toml(setup_file)
        return (toml_data.get("project", {}).get("version") or
                toml_data.get("tool", {}).get("poetry", {}).get("version"))
    
    return None


def _extract_version_from_version_file(root_path: str) -> Optional[str]:
    """Extract version from VERSION file."""
    version_files = ["VERSION", "VERSION.txt", "version.txt"]
    
    for version_file in version_files:
        file_path = Path(root_path) / version_file
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8').strip()
                # Simple version validation
                if re.match(r'^\d+\.\d+(\.\d+)?', content):
                    return content
            except (IOError, UnicodeDecodeError):
                continue
    
    return None


def _extract_version_from_git_tags(root_path: str) -> Optional[str]:
    """Extract version from git tags."""
    try:
        # Get the latest git tag
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            cwd=root_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            tag = result.stdout.strip()
            # Clean up common tag prefixes
            if tag.startswith('v'):
                tag = tag[1:]
            if re.match(r'^\d+\.\d+(\.\d+)?', tag):
                return tag
    
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return None


def parse_configuration_files(root_path: str) -> Dict[str, Any]:
    """
    Parse additional configuration files.
    
    Args:
        root_path: Root directory path of the project
        
    Returns:
        Dictionary containing parsed configuration data
    """
    config_info = {}
    
    # Parse INI-style configuration files
    config_files = [
        "tox.ini", "pytest.ini", ".flake8", "mypy.ini", "setup.cfg",
        ".coveragerc", ".pylintrc", "pyproject.toml"
    ]
    
    for config_file in config_files:
        file_path = Path(root_path) / config_file
        if file_path.exists():
            if config_file == "pyproject.toml":
                config_info[config_file] = parse_pyproject_toml(str(file_path))
            else:
                parsed_config = parse_ini_file(str(file_path))
                if parsed_config:
                    config_info[config_file] = parsed_config
    
    # Parse JSON configuration files
    json_config_files = [".eslintrc.json", "tsconfig.json", "package.json"]
    
    for json_file in json_config_files:
        file_path = Path(root_path) / json_file
        if file_path.exists():
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_info[json_file] = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
    
    # Parse YAML configuration files
    yaml_config_files = [".github/workflows", ".travis.yml", ".circleci/config.yml", "docker-compose.yml"]
    
    for yaml_file in yaml_config_files:
        file_path = Path(root_path) / yaml_file
        if file_path.exists():
            config_info[yaml_file] = {"exists": True, "type": "yaml"}
    
    return config_info


def parse_ini_file(file_path: str) -> Dict[str, Any]:
    """
    Parse INI-style configuration file.
    
    Args:
        file_path: Path to the INI file
        
    Returns:
        Dictionary containing parsed INI data
    """
    try:
        config = configparser.ConfigParser()
        config.read(file_path, encoding='utf-8')
        
        result = {}
        for section_name in config.sections():
            result[section_name] = dict(config.items(section_name))
        
        return result
    
    except (configparser.Error, IOError, UnicodeDecodeError):
        return {}


def extract_dependencies_from_pyproject(toml_data: Dict[str, Any]) -> List[str]:
    """
    Extracts dependencies from parsed pyproject.toml data.
    
    Args:
        toml_data: Parsed TOML data from pyproject.toml.
    
    Returns:
        A list of dependency names.
    """
    dependencies = []
    
    # Standard Python packaging format
    project_deps = toml_data.get("project", {}).get("dependencies", [])
    dependencies.extend([dep.split()[0] for dep in project_deps])
    
    # Poetry format
    poetry_deps = toml_data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    for dep_name, dep_spec in poetry_deps.items():
        if dep_name != "python":  # Skip Python version constraint
            dependencies.append(dep_name)
    
    return dependencies


def _extract_name_from_setup_cfg(setup_cfg_file: str) -> Optional[str]:
    """
    Extracts the project name from a setup.cfg file.
    
    Args:
        setup_cfg_file: Path to the setup.cfg file.
    
    Returns:
        The project name if found, None otherwise.
    """
    try:
        config = configparser.ConfigParser()
        config.read(setup_cfg_file)
        
        if config.has_section('metadata') and config.has_option('metadata', 'name'):
            return config.get('metadata', 'name')
    
    except (FileNotFoundError, configparser.Error):
        pass
    
    return None


def _extract_list_from_ast(node: ast.AST) -> List[str]:
    """
    Extracts a list of strings from an AST node.
    
    Args:
        node: The AST node to extract from.
    
    Returns:
        A list of strings extracted from the node.
    """
    if isinstance(node, ast.List):
        items = []
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                items.append(element.value)
            elif isinstance(element, ast.Str):  # For older Python versions
                items.append(element.s)
        return items
    
    return []


def extract_project_metadata_comprehensive(root_path: str) -> Dict[str, Any]:
    """
    Extract comprehensive project metadata from all available sources.
    
    Args:
        root_path: Root directory path of the project
        
    Returns:
        Dictionary containing all extracted metadata
    """
    metadata = {
        "name": None,
        "version": None,
        "description": None,
        "author": None,
        "license": None,
        "dependencies": [],
        "configuration": {},
        "has_tests": False,
        "has_docs": False,
    }
    
    # Extract from setup files
    setup_files = [
        Path(root_path) / "setup.py",
        Path(root_path) / "pyproject.toml",
        Path(root_path) / "setup.cfg"
    ]
    
    for setup_file in setup_files:
        if setup_file.exists():
            if setup_file.name == "setup.py":
                setup_metadata = extract_setup_metadata(str(setup_file))
                metadata.update({k: v for k, v in setup_metadata.items() if v})
            elif setup_file.name == "pyproject.toml":
                toml_data = parse_pyproject_toml(str(setup_file))
                project_data = toml_data.get("project", {})
                metadata["name"] = metadata["name"] or project_data.get("name")
                metadata["version"] = metadata["version"] or project_data.get("version")
                metadata["description"] = metadata["description"] or project_data.get("description")
                metadata["license"] = metadata["license"] or project_data.get("license", {}).get("text")
            break
    
    # Extract version from multiple sources
    metadata["version"] = metadata["version"] or extract_version_info(root_path)
    
    # Extract license information
    metadata["license"] = metadata["license"] or extract_license_info(root_path)
    
    # Extract dependencies
    requirements_file = Path(root_path) / "requirements.txt"
    if requirements_file.exists():
        metadata["dependencies"] = parse_dependencies(str(requirements_file))
    
    # Parse configuration files
    metadata["configuration"] = parse_configuration_files(root_path)
    
    # Check for tests and documentation
    metadata["has_tests"] = any(
        path.exists() for path in [
            Path(root_path) / "tests",
            Path(root_path) / "test",
            Path(root_path) / "pytest.ini",
            Path(root_path) / "tox.ini"
        ]
    )
    
    metadata["has_docs"] = any(
        path.exists() for path in [
            Path(root_path) / "docs",
            Path(root_path) / "doc",
            Path(root_path) / "README.md",
            Path(root_path) / "README.rst"
        ]
    )
    
    return metadata
