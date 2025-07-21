"""
Basic dependency parser for extracting essential project dependencies.

This simplified module focuses on core dependency extraction from common sources
like requirements.txt, setup.py, and basic pyproject.toml for MVP implementation.
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from models.project_data import DependencyInfo
from utils.file_utils import read_file_safely, FileInfo

logger = logging.getLogger(__name__)

# Try to import TOML parser
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        tomllib = None


class BasicDependencyParser:
    """Simplified dependency parser for MVP implementation."""
    
    def __init__(self):
        # Basic requirement patterns
        self.requirement_patterns = {
            'basic': re.compile(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])'),
            'versioned': re.compile(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9])\s*([<>=!~]+.*)?'),
            'editable': re.compile(r'^-e\s+(.+)'),
        }
        
        # Simple development dependency indicators
        self.dev_indicators = {
            'test', 'dev', 'docs', 'lint', 'build', 'coverage'
        }
    
    def parse(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> DependencyInfo:
        """
        Parse basic project dependencies from common sources.
        
        Args:
            project_path: Path to project root
            project_files: Dictionary of categorized project files
            
        Returns:
            DependencyInfo object with extracted dependencies
        """
        dependency_info = DependencyInfo()
        
        # Parse in priority order for MVP
        sources_parsed = []
        
        # 1. Parse requirements.txt (most common)
        if self._parse_requirements_txt(project_path, dependency_info):
            sources_parsed.append('requirements.txt')
        
        # 2. Parse basic pyproject.toml
        if self._parse_basic_pyproject_toml(project_path, dependency_info):
            sources_parsed.append('pyproject.toml')
        
        # 3. Parse basic setup.py
        if self._parse_basic_setup_py(project_path, dependency_info):
            sources_parsed.append('setup.py')
        
        # 4. Detect Python version
        self._detect_python_version(project_path, dependency_info)
        
        # 5. Clean up dependencies
        self._clean_dependencies(dependency_info)
        
        if sources_parsed:
            logger.info(f"Parsed dependencies from: {', '.join(sources_parsed)}")
        else:
            logger.warning("No dependency files found")
        
        return dependency_info
    
    def _parse_requirements_txt(self, project_path: Path, dependency_info: DependencyInfo) -> bool:
        """Parse dependencies from requirements.txt files."""
        found_any = False
        
        # Check common requirements file patterns
        req_files = [
            ('requirements.txt', 'production'),
            ('requirements-dev.txt', 'development'),
            ('requirements-test.txt', 'development'),
            ('dev-requirements.txt', 'development'),
        ]
        
        for filename, dep_type in req_files:
            req_file = project_path / filename
            if req_file.exists():
                try:
                    deps = self._parse_single_requirements_file(str(req_file))
                    if deps:
                        if dep_type == 'production':
                            dependency_info.production.extend(deps)
                        else:
                            dependency_info.development.extend(deps)
                        found_any = True
                        logger.debug(f"Found {len(deps)} dependencies in {filename}")
                except Exception as e:
                    logger.error(f"Error parsing {filename}: {e}")
        
        return found_any
    
    def _parse_single_requirements_file(self, file_path: str) -> List[str]:
        """Parse a single requirements.txt file."""
        content = read_file_safely(file_path)
        if not content:
            return []
        
        dependencies = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines, comments, and pip options
            if not line or line.startswith('#') or line.startswith('-'):
                continue
            
            # Remove inline comments
            if '#' in line:
                line = line.split('#')[0].strip()
            
            # Skip if empty after comment removal
            if not line:
                continue
            
            # Basic validation - must start with letter/number
            if re.match(r'^[a-zA-Z0-9]', line):
                dependencies.append(line)
        
        return dependencies
    
    def _parse_basic_pyproject_toml(self, project_path: Path, dependency_info: DependencyInfo) -> bool:
        """Parse basic dependencies from pyproject.toml."""
        if not tomllib:
            return False
        
        pyproject_file = project_path / 'pyproject.toml'
        if not pyproject_file.exists():
            return False
        
        try:
            content = read_file_safely(str(pyproject_file))
            if not content:
                return False
            
            data = tomllib.loads(content)
            found_deps = False
            
            # Parse [project] section (PEP 621 - modern standard)
            if 'project' in data:
                project_data = data['project']
                
                # Main dependencies
                if 'dependencies' in project_data:
                    deps = project_data['dependencies']
                    if isinstance(deps, list):
                        clean_deps = [dep for dep in deps if isinstance(dep, str)]
                        dependency_info.production.extend(clean_deps)
                        found_deps = True
                
                # Optional dependencies (simplified)
                if 'optional-dependencies' in project_data:
                    optional_deps = project_data['optional-dependencies']
                    if isinstance(optional_deps, dict):
                        for group_name, deps in optional_deps.items():
                            if isinstance(deps, list):
                                clean_deps = [dep for dep in deps if isinstance(dep, str)]
                                if self._is_dev_dependency_group(group_name):
                                    dependency_info.development.extend(clean_deps)
                                found_deps = True
                
                # Python version requirement
                if 'requires-python' in project_data:
                    dependency_info.python_requires = project_data['requires-python']
            
            return found_deps
            
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")
            return False
    
    def _parse_basic_setup_py(self, project_path: Path, dependency_info: DependencyInfo) -> bool:
        """Parse basic dependencies from setup.py."""
        setup_file = project_path / 'setup.py'
        if not setup_file.exists():
            return False
        
        try:
            content = read_file_safely(str(setup_file))
            if not content:
                return False
            
            # Parse as AST to find setup() calls
            tree = ast.parse(content)
            found_deps = False
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check if this is a setup() call
                    if ((isinstance(node.func, ast.Name) and node.func.id == 'setup') or
                        (isinstance(node.func, ast.Attribute) and node.func.attr == 'setup')):
                        
                        # Extract dependency arguments
                        for keyword in node.keywords:
                            if self._extract_setup_dependency(keyword, dependency_info):
                                found_deps = True
            
            return found_deps
            
        except Exception as e:
            logger.error(f"Error parsing setup.py: {e}")
            return False
    
    def _extract_setup_dependency(self, keyword: ast.keyword, dependency_info: DependencyInfo) -> bool:
        """Extract dependencies from setup() keyword arguments."""
        try:
            arg_name = keyword.arg
            found_deps = False
            
            if arg_name == 'install_requires':
                deps = self._extract_list_from_ast(keyword.value)
                if deps:
                    dependency_info.production.extend(deps)
                    found_deps = True
            
            elif arg_name == 'python_requires':
                if isinstance(keyword.value, ast.Constant):
                    dependency_info.python_requires = keyword.value.value
                    found_deps = True
            
            elif arg_name == 'extras_require':
                # Simplified extras parsing
                if isinstance(keyword.value, ast.Dict):
                    for key, value in zip(keyword.value.keys, keyword.value.values):
                        if isinstance(key, ast.Constant):
                            extra_name = key.value
                            deps = self._extract_list_from_ast(value)
                            if deps and self._is_dev_dependency_group(extra_name):
                                dependency_info.development.extend(deps)
                                found_deps = True
            
            return found_deps
            
        except Exception as e:
            logger.debug(f"Error extracting setup dependency {keyword.arg}: {e}")
            return False
    
    def _extract_list_from_ast(self, node: ast.AST) -> List[str]:
        """Extract list of strings from AST node."""
        try:
            if isinstance(node, ast.List):
                result = []
                for item in node.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        result.append(item.value)
                return result
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                return [node.value]
            else:
                return []
        except Exception:
            return []
    
    def _detect_python_version(self, project_path: Path, dependency_info: DependencyInfo) -> None:
        """Detect Python version requirements from common sources."""
        if dependency_info.python_requires:
            return  # Already detected
        
        # Check .python-version file
        python_version_file = project_path / '.python-version'
        if python_version_file.exists():
            try:
                content = read_file_safely(str(python_version_file))
                if content:
                    version = content.strip()
                    # Simple validation
                    if re.match(r'^\d+\.\d+', version):
                        dependency_info.python_requires = f">={version}"
                        return
            except Exception:
                pass
        
        # Check runtime.txt (common in deployed apps)
        runtime_file = project_path / 'runtime.txt'
        if runtime_file.exists():
            try:
                content = read_file_safely(str(runtime_file))
                if content:
                    match = re.search(r'python-(\d+\.\d+(?:\.\d+)?)', content)
                    if match:
                        version = match.group(1)
                        dependency_info.python_requires = f">={version}"
                        return
            except Exception:
                pass
    
    def _is_dev_dependency_group(self, group_name: str) -> bool:
        """Check if a dependency group is for development."""
        if not isinstance(group_name, str):
            return False
        return any(indicator in group_name.lower() for indicator in self.dev_indicators)
    
    def _clean_dependencies(self, dependency_info: DependencyInfo) -> None:
        """Clean and deduplicate dependencies."""
        # Remove duplicates while preserving order
        dependency_info.production = self._deduplicate_list(dependency_info.production)
        dependency_info.development = self._deduplicate_list(dependency_info.development)
        
        # Basic validation - remove empty strings
        dependency_info.production = [dep for dep in dependency_info.production if dep and dep.strip()]
        dependency_info.development = [dep for dep in dependency_info.development if dep and dep.strip()]
    
    def _deduplicate_list(self, items: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result


# Convenience functions
def extract_basic_dependencies(project_path: str, project_files: Dict[str, List[FileInfo]]) -> DependencyInfo:
    """
    Extract basic dependencies from a project directory.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        DependencyInfo object
    """
    parser = BasicDependencyParser()
    return parser.parse(Path(project_path), project_files)


def parse_requirements_file(file_path: str) -> List[str]:
    """
    Parse a single requirements.txt file.
    
    Args:
        file_path: Path to requirements file
        
    Returns:
        List of dependency specifications
    """
    parser = BasicDependencyParser()
    return parser._parse_single_requirements_file(file_path)


def detect_python_version(project_path: str) -> Optional[str]:
    """
    Detect Python version requirements for a project.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Python version requirement string or None
    """
    parser = BasicDependencyParser()
    dependency_info = DependencyInfo()
    parser._detect_python_version(Path(project_path), dependency_info)
    return dependency_info.python_requires


def get_all_dependencies(project_path: str) -> Dict[str, List[str]]:
    """
    Get all dependencies categorized by type.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Dictionary with 'production' and 'development' dependency lists
    """
    parser = BasicDependencyParser()
    dependency_info = parser.parse(Path(project_path), {})
    
    return {
        'production': dependency_info.production,
        'development': dependency_info.development,
        'python_requires': dependency_info.python_requires
    }
