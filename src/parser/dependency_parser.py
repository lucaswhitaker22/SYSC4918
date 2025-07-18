"""
Dependency parser for extracting project dependencies and requirements.

This module parses dependencies from requirements.txt, pyproject.toml, setup.py,
and other dependency specification files commonly found in Python projects.
"""

import os
import re
import ast
import configparser
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import logging

from models.project_data import DependencyInfo
from utils.file_utils import read_file_safely, FileInfo

logger = logging.getLogger(__name__)

# Try to import TOML parsers
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        tomllib = None


class DependencyParser:
    """Parser for extracting project dependencies from various sources."""
    
    def __init__(self):
        self.requirement_patterns = {
            'basic': re.compile(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])'),
            'versioned': re.compile(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])\s*([<>=!~]+.*)?'),
            'extras': re.compile(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])\[([^\]]+)\]'),
            'git': re.compile(r'^git\+https?://'),
            'url': re.compile(r'^https?://'),
            'file': re.compile(r'^file://'),
            'editable': re.compile(r'^-e\s+(.+)'),
            'constraint': re.compile(r'^-c\s+(.+)'),
            'requirement': re.compile(r'^-r\s+(.+)'),
        }
        
        # Development dependency indicators
        self.dev_indicators = {
            'test', 'testing', 'dev', 'development', 'docs', 'documentation',
            'lint', 'linting', 'format', 'formatting', 'quality', 'qa',
            'build', 'deploy', 'ci', 'cd', 'coverage', 'profiling'
        }
    
    def parse(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> DependencyInfo:
        """
        Parse project dependencies from various sources.
        
        Args:
            project_path: Path to project root
            project_files: Dictionary of categorized project files
            
        Returns:
            DependencyInfo object with extracted dependencies
        """
        dependency_info = DependencyInfo()
        
        # Parse from different sources
        sources_parsed = []
        
        # 1. Parse pyproject.toml (modern standard)
        if self._parse_pyproject_toml(project_path, dependency_info):
            sources_parsed.append('pyproject.toml')
        
        # 2. Parse requirements.txt files
        req_files_parsed = self._parse_requirements_files(project_path, dependency_info)
        sources_parsed.extend(req_files_parsed)
        
        # 3. Parse setup.py
        if self._parse_setup_py(project_path, dependency_info):
            sources_parsed.append('setup.py')
        
        # 4. Parse setup.cfg
        if self._parse_setup_cfg(project_path, dependency_info):
            sources_parsed.append('setup.cfg')
        
        # 5. Parse Pipfile (if present)
        if self._parse_pipfile(project_path, dependency_info):
            sources_parsed.append('Pipfile')
        
        # 6. Detect Python version requirements
        self._detect_python_version(project_path, dependency_info)
        
        # 7. Clean and deduplicate dependencies
        self._clean_dependencies(dependency_info)
        
        logger.info(f"Parsed dependencies from sources: {sources_parsed}")
        return dependency_info
    
    def _parse_pyproject_toml(self, project_path: Path, dependency_info: DependencyInfo) -> bool:
        """Parse dependencies from pyproject.toml file."""
        if not tomllib:
            logger.warning("TOML parser not available, skipping pyproject.toml")
            return False
        
        pyproject_file = project_path / 'pyproject.toml'
        if not pyproject_file.exists():
            return False
        
        try:
            content = read_file_safely(str(pyproject_file))
            if not content:
                return False
            
            data = tomllib.loads(content)
            
            # Parse [project] section (PEP 621)
            if 'project' in data:
                project_data = data['project']
                
                # Main dependencies
                if 'dependencies' in project_data:
                    deps = project_data['dependencies']
                    dependency_info.production.extend(self._normalize_dependencies(deps))
                
                # Optional dependencies
                if 'optional-dependencies' in project_data:
                    optional_deps = project_data['optional-dependencies']
                    for group_name, deps in optional_deps.items():
                        normalized_deps = self._normalize_dependencies(deps)
                        if self._is_dev_dependency_group(group_name):
                            dependency_info.development.extend(normalized_deps)
                        else:
                            dependency_info.optional[group_name] = normalized_deps
                
                # Python version requirement
                if 'requires-python' in project_data:
                    dependency_info.python_requires = project_data['requires-python']
            
            # Parse [tool.poetry] section
            if 'tool' in data and 'poetry' in data['tool']:
                poetry_data = data['tool']['poetry']
                
                # Main dependencies
                if 'dependencies' in poetry_data:
                    deps = poetry_data['dependencies']
                    # Remove python version requirement from dependencies
                    python_req = deps.pop('python', None)
                    if python_req and not dependency_info.python_requires:
                        dependency_info.python_requires = python_req
                    
                    # Convert Poetry format to standard format
                    poetry_deps = self._convert_poetry_dependencies(deps)
                    dependency_info.production.extend(poetry_deps)
                
                # Development dependencies
                if 'group' in poetry_data:
                    groups = poetry_data['group']
                    for group_name, group_data in groups.items():
                        if 'dependencies' in group_data:
                            deps = self._convert_poetry_dependencies(group_data['dependencies'])
                            if self._is_dev_dependency_group(group_name):
                                dependency_info.development.extend(deps)
                            else:
                                dependency_info.optional[group_name] = deps
                
                # Legacy dev-dependencies
                if 'dev-dependencies' in poetry_data:
                    dev_deps = self._convert_poetry_dependencies(poetry_data['dev-dependencies'])
                    dependency_info.development.extend(dev_deps)
            
            # Parse [tool.pdm] section
            if 'tool' in data and 'pdm' in data['tool']:
                pdm_data = data['tool']['pdm']
                
                if 'dev-dependencies' in pdm_data:
                    dev_groups = pdm_data['dev-dependencies']
                    for group_name, deps in dev_groups.items():
                        normalized_deps = self._normalize_dependencies(deps)
                        if self._is_dev_dependency_group(group_name):
                            dependency_info.development.extend(normalized_deps)
                        else:
                            dependency_info.optional[group_name] = normalized_deps
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")
            return False
    
    def _parse_requirements_files(self, project_path: Path, dependency_info: DependencyInfo) -> List[str]:
        """Parse various requirements.txt files."""
        files_parsed = []
        
        # Common requirements file patterns
        req_patterns = [
            'requirements.txt',
            'requirements-dev.txt',
            'requirements-test.txt',
            'requirements-docs.txt',
            'requirements-build.txt',
            'dev-requirements.txt',
            'test-requirements.txt',
            'docs-requirements.txt',
        ]
        
        for pattern in req_patterns:
            req_file = project_path / pattern
            if req_file.exists():
                try:
                    deps = self._parse_requirements_file(str(req_file))
                    if deps:
                        # Categorize based on filename
                        if any(indicator in pattern.lower() for indicator in self.dev_indicators):
                            dependency_info.development.extend(deps)
                        else:
                            dependency_info.production.extend(deps)
                        files_parsed.append(pattern)
                except Exception as e:
                    logger.error(f"Error parsing {pattern}: {e}")
        
        return files_parsed
    
    def _parse_requirements_file(self, file_path: str) -> List[str]:
        """Parse a single requirements.txt file."""
        content = read_file_safely(file_path)
        if not content:
            return []
        
        dependencies = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Handle different requirement formats
            if line.startswith('-r '):
                # Reference to another requirements file
                # TODO: Could recursively parse referenced files
                continue
            elif line.startswith('-c '):
                # Constraint file
                continue
            elif line.startswith('-e '):
                # Editable install
                editable_match = self.requirement_patterns['editable'].match(line)
                if editable_match:
                    dep_spec = editable_match.group(1)
                    dependencies.append(dep_spec)
            elif line.startswith('-'):
                # Other pip options, skip
                continue
            else:
                # Regular dependency
                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()
                
                if line:
                    dependencies.append(line)
        
        return dependencies
    
    def _parse_setup_py(self, project_path: Path, dependency_info: DependencyInfo) -> bool:
        """Parse dependencies from setup.py file."""
        setup_file = project_path / 'setup.py'
        if not setup_file.exists():
            return False
        
        try:
            content = read_file_safely(str(setup_file))
            if not content:
                return False
            
            # Parse setup.py as AST
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Name) and node.func.id == 'setup') or \
                       (isinstance(node.func, ast.Attribute) and node.func.attr == 'setup'):
                        
                        # Extract dependency-related arguments
                        for keyword in node.keywords:
                            self._extract_setup_dependencies(keyword, dependency_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing setup.py: {e}")
            return False
    
    def _parse_setup_cfg(self, project_path: Path, dependency_info: DependencyInfo) -> bool:
        """Parse dependencies from setup.cfg file."""
        setup_cfg_file = project_path / 'setup.cfg'
        if not setup_cfg_file.exists():
            return False
        
        try:
            content = read_file_safely(str(setup_cfg_file))
            if not content:
                return False
            
            config = configparser.ConfigParser()
            config.read_string(content)
            
            # Parse [options] section
            if 'options' in config:
                options = config['options']
                
                # Install requires
                if 'install_requires' in options:
                    deps = self._parse_multiline_deps(options['install_requires'])
                    dependency_info.production.extend(deps)
                
                # Python requires
                if 'python_requires' in options:
                    dependency_info.python_requires = options['python_requires']
            
            # Parse [options.extras_require] section
            if 'options.extras_require' in config:
                extras = config['options.extras_require']
                for extra_name, deps_str in extras.items():
                    deps = self._parse_multiline_deps(deps_str)
                    if self._is_dev_dependency_group(extra_name):
                        dependency_info.development.extend(deps)
                    else:
                        dependency_info.extras_require[extra_name] = deps
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing setup.cfg: {e}")
            return False
    
    def _parse_pipfile(self, project_path: Path, dependency_info: DependencyInfo) -> bool:
        """Parse dependencies from Pipfile."""
        if not tomllib:
            return False
        
        pipfile = project_path / 'Pipfile'
        if not pipfile.exists():
            return False
        
        try:
            content = read_file_safely(str(pipfile))
            if not content:
                return False
            
            data = tomllib.loads(content)
            
            # Parse [packages] section
            if 'packages' in data:
                packages = data['packages']
                deps = self._convert_pipfile_dependencies(packages)
                dependency_info.production.extend(deps)
            
            # Parse [dev-packages] section
            if 'dev-packages' in data:
                dev_packages = data['dev-packages']
                deps = self._convert_pipfile_dependencies(dev_packages)
                dependency_info.development.extend(deps)
            
            # Parse [requires] section for Python version
            if 'requires' in data:
                requires = data['requires']
                if 'python_version' in requires:
                    dependency_info.python_requires = f">={requires['python_version']}"
                elif 'python_full_version' in requires:
                    dependency_info.python_requires = f">={requires['python_full_version']}"
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing Pipfile: {e}")
            return False
    
    def _detect_python_version(self, project_path: Path, dependency_info: DependencyInfo) -> None:
        """Detect Python version requirements from various sources."""
        if dependency_info.python_requires:
            return  # Already detected
        
        # Check for .python-version file
        python_version_file = project_path / '.python-version'
        if python_version_file.exists():
            try:
                content = read_file_safely(str(python_version_file))
                if content:
                    version = content.strip()
                    dependency_info.python_requires = f">={version}"
                    return
            except Exception:
                pass
        
        # Check for runtime.txt (Heroku)
        runtime_file = project_path / 'runtime.txt'
        if runtime_file.exists():
            try:
                content = read_file_safely(str(runtime_file))
                if content:
                    match = re.search(r'python-(\d+\.\d+\.\d+)', content)
                    if match:
                        version = match.group(1)
                        dependency_info.python_requires = f">={version}"
                        return
            except Exception:
                pass
        
        # Check for GitHub Actions workflow files
        github_workflows = project_path / '.github' / 'workflows'
        if github_workflows.exists():
            try:
                for workflow_file in github_workflows.glob('*.yml'):
                    content = read_file_safely(str(workflow_file))
                    if content:
                        # Look for python-version in matrix
                        python_versions = re.findall(r'python-version:.*?[\[\'"]([\d.]+)', content)
                        if python_versions:
                            min_version = min(python_versions)
                            dependency_info.python_requires = f">={min_version}"
                            return
            except Exception:
                pass
    
    def _normalize_dependencies(self, deps: List[str]) -> List[str]:
        """Normalize dependency specifications."""
        normalized = []
        
        for dep in deps:
            if isinstance(dep, str):
                # Clean up the dependency string
                dep = dep.strip()
                if dep:
                    normalized.append(dep)
            elif isinstance(dep, dict):
                # Handle dict format (from some TOML files)
                if 'name' in dep:
                    dep_str = dep['name']
                    if 'version' in dep:
                        dep_str += dep['version']
                    normalized.append(dep_str)
        
        return normalized
    
    def _convert_poetry_dependencies(self, deps: Dict[str, Any]) -> List[str]:
        """Convert Poetry dependency format to standard format."""
        dependencies = []
        
        for name, spec in deps.items():
            if isinstance(spec, str):
                # Simple version specification
                if spec == '*':
                    dependencies.append(name)
                else:
                    dependencies.append(f"{name}{spec}")
            elif isinstance(spec, dict):
                # Complex specification
                dep_str = name
                
                if 'version' in spec:
                    version = spec['version']
                    if version != '*':
                        dep_str += version
                
                if 'extras' in spec:
                    extras = spec['extras']
                    if isinstance(extras, list):
                        extras_str = ','.join(extras)
                        dep_str = f"{name}[{extras_str}]"
                        if 'version' in spec and spec['version'] != '*':
                            dep_str += spec['version']
                
                dependencies.append(dep_str)
        
        return dependencies
    
    def _convert_pipfile_dependencies(self, deps: Dict[str, Any]) -> List[str]:
        """Convert Pipfile dependency format to standard format."""
        dependencies = []
        
        for name, spec in deps.items():
            if isinstance(spec, str):
                # Simple version specification
                if spec == '*':
                    dependencies.append(name)
                else:
                    dependencies.append(f"{name}{spec}")
            elif isinstance(spec, dict):
                # Complex specification
                dep_str = name
                
                if 'version' in spec:
                    version = spec['version']
                    if version != '*':
                        dep_str += version
                
                dependencies.append(dep_str)
        
        return dependencies
    
    def _extract_setup_dependencies(self, keyword: ast.keyword, dependency_info: DependencyInfo) -> None:
        """Extract dependencies from setup() call arguments."""
        try:
            arg_name = keyword.arg
            
            if arg_name == 'install_requires':
                deps = self._extract_list_from_ast(keyword.value)
                dependency_info.production.extend(deps)
            
            elif arg_name == 'extras_require':
                if isinstance(keyword.value, ast.Dict):
                    for key, value in zip(keyword.value.keys, keyword.value.values):
                        if isinstance(key, ast.Constant):
                            extra_name = key.value
                            deps = self._extract_list_from_ast(value)
                            if self._is_dev_dependency_group(extra_name):
                                dependency_info.development.extend(deps)
                            else:
                                dependency_info.extras_require[extra_name] = deps
            
            elif arg_name == 'python_requires':
                if isinstance(keyword.value, ast.Constant):
                    dependency_info.python_requires = keyword.value.value
        
        except Exception as e:
            logger.debug(f"Error extracting setup dependencies for {keyword.arg}: {e}")
    
    def _extract_list_from_ast(self, node: ast.AST) -> List[str]:
        """Extract list of strings from AST node."""
        if isinstance(node, ast.List):
            result = []
            for item in node.elts:
                if isinstance(item, ast.Constant):
                    result.append(item.value)
            return result
        elif isinstance(node, ast.Constant):
            return [node.value]
        else:
            return []
    
    def _parse_multiline_deps(self, deps_str: str) -> List[str]:
        """Parse multiline dependency string from setup.cfg."""
        deps = []
        for line in deps_str.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                deps.append(line)
        return deps
    
    def _is_dev_dependency_group(self, group_name: str) -> bool:
        """Check if a dependency group is for development."""
        return any(indicator in group_name.lower() for indicator in self.dev_indicators)
    
    def _clean_dependencies(self, dependency_info: DependencyInfo) -> None:
        """Clean and deduplicate dependencies."""
        # Remove duplicates while preserving order
        dependency_info.production = list(dict.fromkeys(dependency_info.production))
        dependency_info.development = list(dict.fromkeys(dependency_info.development))
        
        # Clean optional dependencies
        for group_name in dependency_info.optional:
            dependency_info.optional[group_name] = list(dict.fromkeys(dependency_info.optional[group_name]))
        
        # Clean extras_require
        for extra_name in dependency_info.extras_require:
            dependency_info.extras_require[extra_name] = list(dict.fromkeys(dependency_info.extras_require[extra_name]))
        
        # Remove empty groups
        dependency_info.optional = {k: v for k, v in dependency_info.optional.items() if v}
        dependency_info.extras_require = {k: v for k, v in dependency_info.extras_require.items() if v}


# Convenience functions
def extract_dependencies(project_path: str, project_files: Dict[str, List[FileInfo]]) -> DependencyInfo:
    """
    Extract dependencies from a project directory.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        DependencyInfo object
    """
    parser = DependencyParser()
    return parser.parse(Path(project_path), project_files)


def parse_requirements_file(file_path: str) -> List[str]:
    """
    Parse a single requirements.txt file.
    
    Args:
        file_path: Path to requirements file
        
    Returns:
        List of dependency specifications
    """
    parser = DependencyParser()
    return parser._parse_requirements_file(file_path)


def detect_python_version(project_path: str) -> Optional[str]:
    """
    Detect Python version requirements for a project.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Python version requirement string or None
    """
    parser = DependencyParser()
    dependency_info = DependencyInfo()
    parser._detect_python_version(Path(project_path), dependency_info)
    return dependency_info.python_requires
