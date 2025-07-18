"""
Project metadata parser for extracting information from various configuration files.

This module extracts project metadata from setup.py, pyproject.toml, setup.cfg,
and other configuration files commonly found in Python projects.
"""

import os
import re
import ast
import configparser
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging

from models.project_data import ProjectMetadata, ProjectType, LicenseType
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

# Try to import git for repository information
try:
    import git
except ImportError:
    git = None


class MetadataParser:
    """Parser for extracting project metadata from various configuration files."""
    
    def __init__(self):
        self.license_patterns = {
            'MIT': ['mit', 'mit license'],
            'Apache-2.0': ['apache', 'apache license', 'apache-2.0', 'apache 2.0'],
            'GPL-3.0': ['gpl', 'gpl-3.0', 'gpl v3', 'gnu general public license'],
            'BSD-3-Clause': ['bsd', 'bsd license', 'bsd-3-clause'],
            'Unlicense': ['unlicense', 'public domain'],
        }
        
        # Common project type indicators
        self.project_type_patterns = {
            ProjectType.CLI_TOOL: ['cli', 'command', 'tool', 'script'],
            ProjectType.WEB_APPLICATION: ['web', 'webapp', 'django', 'flask', 'fastapi'],
            ProjectType.API: ['api', 'rest', 'graphql', 'endpoint'],
            ProjectType.LIBRARY: ['library', 'lib', 'package', 'module'],
            ProjectType.APPLICATION: ['app', 'application', 'gui', 'desktop'],
        }
    
    def parse(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectMetadata:
        """
        Parse project metadata from various configuration files.
        
        Args:
            project_path: Path to project root
            project_files: Dictionary of categorized project files
            
        Returns:
            ProjectMetadata object with extracted information
        """
        metadata = ProjectMetadata(project_name=project_path.name)
        
        # Parse from different sources in order of preference
        sources_parsed = []
        
        # 1. Try pyproject.toml first (modern standard)
        if self._parse_pyproject_toml(project_path, metadata):
            sources_parsed.append('pyproject.toml')
        
        # 2. Try setup.py
        if self._parse_setup_py(project_path, metadata):
            sources_parsed.append('setup.py')
        
        # 3. Try setup.cfg
        if self._parse_setup_cfg(project_path, metadata):
            sources_parsed.append('setup.cfg')
        
        # 4. Try package __init__.py files
        self._parse_package_init(project_path, metadata, project_files)
        
        # 5. Extract git information
        self._extract_git_info(project_path, metadata)
        
        # 6. Detect project type
        metadata.project_type = self._detect_project_type(metadata, project_files)
        
        # 7. Find license information
        metadata.license = self._detect_license(project_path, metadata)
        
        logger.info(f"Parsed metadata from sources: {sources_parsed}")
        return metadata
    
    def _parse_pyproject_toml(self, project_path: Path, metadata: ProjectMetadata) -> bool:
        """Parse metadata from pyproject.toml file."""
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
            
            # Parse TOML content
            data = tomllib.loads(content)
            
            # Extract project metadata from [project] section
            if 'project' in data:
                project_data = data['project']
                
                metadata.project_name = project_data.get('name', metadata.project_name)
                metadata.description = project_data.get('description')
                metadata.version = project_data.get('version')
                metadata.python_version = project_data.get('requires-python')
                
                # Handle authors
                if 'authors' in project_data:
                    authors = project_data['authors']
                    if isinstance(authors, list) and authors:
                        author_info = authors[0]
                        if isinstance(author_info, dict):
                            metadata.author = author_info.get('name')
                            metadata.author_email = author_info.get('email')
                        else:
                            metadata.author = str(author_info)
                
                # Handle maintainers as fallback
                if not metadata.author and 'maintainers' in project_data:
                    maintainers = project_data['maintainers']
                    if isinstance(maintainers, list) and maintainers:
                        maintainer_info = maintainers[0]
                        if isinstance(maintainer_info, dict):
                            metadata.author = maintainer_info.get('name')
                            metadata.author_email = maintainer_info.get('email')
                
                # Handle URLs
                if 'urls' in project_data:
                    urls = project_data['urls']
                    metadata.homepage = urls.get('homepage') or urls.get('Home')
                    metadata.repository = urls.get('repository') or urls.get('Repository')
                
                # Handle license
                if 'license' in project_data:
                    license_info = project_data['license']
                    if isinstance(license_info, dict):
                        if 'text' in license_info:
                            metadata.license = self._parse_license_string(license_info['text'])
                        elif 'file' in license_info:
                            license_file = project_path / license_info['file']
                            if license_file.exists():
                                license_content = read_file_safely(str(license_file))
                                if license_content:
                                    metadata.license = self._parse_license_string(license_content)
                    else:
                        metadata.license = self._parse_license_string(str(license_info))
                
                # Handle keywords and classifiers
                metadata.keywords = project_data.get('keywords', [])
                metadata.classifiers = project_data.get('classifiers', [])
            
            # Extract build system info
            if 'build-system' in data:
                build_system = data['build-system']
                if 'requires' in build_system:
                    # This could help determine project type
                    build_requires = build_system['requires']
                    if any('setuptools' in req for req in build_requires):
                        # Traditional setuptools project
                        pass
            
            # Extract tool-specific metadata
            if 'tool' in data:
                self._parse_tool_metadata(data['tool'], metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")
            return False
    
    def _parse_setup_py(self, project_path: Path, metadata: ProjectMetadata) -> bool:
        """Parse metadata from setup.py file."""
        setup_file = project_path / 'setup.py'
        if not setup_file.exists():
            return False
        
        try:
            content = read_file_safely(str(setup_file))
            if not content:
                return False
            
            # Parse setup.py as AST to extract setup() call arguments
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Name) and node.func.id == 'setup') or \
                       (isinstance(node.func, ast.Attribute) and node.func.attr == 'setup'):
                        
                        # Extract arguments from setup() call
                        for keyword in node.keywords:
                            self._extract_setup_argument(keyword, metadata, content)
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing setup.py: {e}")
            return False
    
    def _parse_setup_cfg(self, project_path: Path, metadata: ProjectMetadata) -> bool:
        """Parse metadata from setup.cfg file."""
        setup_cfg_file = project_path / 'setup.cfg'
        if not setup_cfg_file.exists():
            return False
        
        try:
            content = read_file_safely(str(setup_cfg_file))
            if not content:
                return False
            
            config = configparser.ConfigParser()
            config.read_string(content)
            
            # Extract metadata from [metadata] section
            if 'metadata' in config:
                metadata_section = config['metadata']
                
                metadata.project_name = metadata_section.get('name', metadata.project_name)
                metadata.version = metadata_section.get('version', metadata.version)
                metadata.description = metadata_section.get('description', metadata.description)
                metadata.author = metadata_section.get('author', metadata.author)
                metadata.author_email = metadata_section.get('author_email', metadata.author_email)
                metadata.homepage = metadata_section.get('url', metadata.homepage)
                
                # Handle license
                license_str = metadata_section.get('license')
                if license_str:
                    metadata.license = self._parse_license_string(license_str)
                
                # Handle classifiers
                classifiers_str = metadata_section.get('classifiers')
                if classifiers_str:
                    metadata.classifiers = [c.strip() for c in classifiers_str.split('\n') if c.strip()]
                
                # Handle keywords
                keywords_str = metadata_section.get('keywords')
                if keywords_str:
                    metadata.keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing setup.cfg: {e}")
            return False
    
    def _parse_package_init(self, project_path: Path, metadata: ProjectMetadata, 
                           project_files: Dict[str, List[FileInfo]]) -> None:
        """Parse metadata from package __init__.py files."""
        try:
            # Look for __init__.py files in the project
            init_files = []
            for file_info in project_files.get('python', []):
                if file_info.path.endswith('__init__.py'):
                    init_files.append(file_info.path)
            
            # Find the main package __init__.py
            main_init = None
            for init_file in init_files:
                rel_path = os.path.relpath(init_file, project_path)
                # Look for the shortest path (likely main package)
                if main_init is None or len(rel_path.split(os.sep)) < len(os.path.relpath(main_init, project_path).split(os.sep)):
                    main_init = init_file
            
            if main_init:
                content = read_file_safely(main_init)
                if content:
                    # Extract version from __version__ variable
                    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                    if version_match and not metadata.version:
                        metadata.version = version_match.group(1)
                    
                    # Extract author from __author__ variable
                    author_match = re.search(r'__author__\s*=\s*["\']([^"\']+)["\']', content)
                    if author_match and not metadata.author:
                        metadata.author = author_match.group(1)
                    
                    # Extract description from docstring
                    if not metadata.description:
                        docstring_match = re.search(r'"""([^"]+)"""', content)
                        if docstring_match:
                            metadata.description = docstring_match.group(1).strip()
        
        except Exception as e:
            logger.error(f"Error parsing package __init__.py: {e}")
    
    def _extract_git_info(self, project_path: Path, metadata: ProjectMetadata) -> None:
        """Extract repository information from git."""
        if not git:
            return
        
        try:
            repo = git.Repo(project_path)
            
            # Get remote URL
            if repo.remotes:
                remote_url = repo.remotes.origin.url
                if remote_url:
                    # Clean up git URL
                    if remote_url.startswith('git@'):
                        # Convert SSH to HTTPS
                        remote_url = remote_url.replace('git@github.com:', 'https://github.com/')
                        remote_url = remote_url.replace('.git', '')
                    elif remote_url.endswith('.git'):
                        remote_url = remote_url[:-4]
                    
                    if not metadata.repository:
                        metadata.repository = remote_url
                    if not metadata.homepage:
                        metadata.homepage = remote_url
        
        except Exception as e:
            logger.debug(f"Could not extract git info: {e}")
    
    def _detect_project_type(self, metadata: ProjectMetadata, 
                           project_files: Dict[str, List[FileInfo]]) -> ProjectType:
        """Detect project type based on metadata and file structure."""
        # Check description and name for keywords
        text_to_check = f"{metadata.description or ''} {metadata.project_name}".lower()
        
        for project_type, keywords in self.project_type_patterns.items():
            if any(keyword in text_to_check for keyword in keywords):
                return project_type
        
        # Check file structure
        python_files = project_files.get('python', [])
        
        # Look for specific patterns
        has_main = any('main.py' in f.path for f in python_files)
        has_cli = any('cli' in f.path.lower() for f in python_files)
        has_webapp_files = any(any(framework in f.path.lower() for framework in ['django', 'flask', 'fastapi']) 
                              for f in python_files)
        
        if has_cli or has_main:
            return ProjectType.CLI_TOOL
        elif has_webapp_files:
            return ProjectType.WEB_APPLICATION
        elif len(python_files) > 5:  # Larger projects likely libraries
            return ProjectType.LIBRARY
        else:
            return ProjectType.APPLICATION
    
    def _detect_license(self, project_path: Path, metadata: ProjectMetadata) -> Optional[LicenseType]:
        """Detect license from license files or metadata."""
        # If already detected from metadata, return it
        if metadata.license:
            return metadata.license
        
        # Look for license files
        license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING', 'COPYING.txt']
        
        for license_file in license_files:
            file_path = project_path / license_file
            if file_path.exists():
                content = read_file_safely(str(file_path))
                if content:
                    detected_license = self._parse_license_string(content)
                    if detected_license:
                        return detected_license
        
        return None
    
    def _parse_license_string(self, license_str: str) -> Optional[LicenseType]:
        """Parse license string to determine license type."""
        license_lower = license_str.lower()
        
        for license_type, patterns in self.license_patterns.items():
            if any(pattern in license_lower for pattern in patterns):
                return LicenseType(license_type)
        
        return None
    
    def _extract_setup_argument(self, keyword: ast.keyword, metadata: ProjectMetadata, content: str) -> None:
        """Extract argument from setup() call."""
        try:
            arg_name = keyword.arg
            
            if arg_name == 'name' and isinstance(keyword.value, ast.Constant):
                metadata.project_name = keyword.value.value
            elif arg_name == 'version' and isinstance(keyword.value, ast.Constant):
                metadata.version = keyword.value.value
            elif arg_name == 'description' and isinstance(keyword.value, ast.Constant):
                metadata.description = keyword.value.value
            elif arg_name == 'author' and isinstance(keyword.value, ast.Constant):
                metadata.author = keyword.value.value
            elif arg_name == 'author_email' and isinstance(keyword.value, ast.Constant):
                metadata.author_email = keyword.value.value
            elif arg_name == 'url' and isinstance(keyword.value, ast.Constant):
                metadata.homepage = keyword.value.value
            elif arg_name == 'license' and isinstance(keyword.value, ast.Constant):
                metadata.license = self._parse_license_string(keyword.value.value)
            elif arg_name == 'classifiers' and isinstance(keyword.value, ast.List):
                classifiers = []
                for item in keyword.value.elts:
                    if isinstance(item, ast.Constant):
                        classifiers.append(item.value)
                metadata.classifiers = classifiers
            elif arg_name == 'keywords' and isinstance(keyword.value, ast.List):
                keywords = []
                for item in keyword.value.elts:
                    if isinstance(item, ast.Constant):
                        keywords.append(item.value)
                metadata.keywords = keywords
        
        except Exception as e:
            logger.debug(f"Error extracting setup argument {keyword.arg}: {e}")
    
    def _parse_tool_metadata(self, tool_data: Dict[str, Any], metadata: ProjectMetadata) -> None:
        """Parse tool-specific metadata from pyproject.toml."""
        # Handle Poetry metadata
        if 'poetry' in tool_data:
            poetry_data = tool_data['poetry']
            
            if not metadata.project_name:
                metadata.project_name = poetry_data.get('name', metadata.project_name)
            if not metadata.version:
                metadata.version = poetry_data.get('version')
            if not metadata.description:
                metadata.description = poetry_data.get('description')
            if not metadata.author:
                authors = poetry_data.get('authors', [])
                if authors and isinstance(authors, list):
                    # Parse "Name <email>" format
                    author_str = authors[0]
                    if '<' in author_str:
                        name, email = author_str.split('<', 1)
                        metadata.author = name.strip()
                        metadata.author_email = email.strip('>')
                    else:
                        metadata.author = author_str
            if not metadata.homepage:
                metadata.homepage = poetry_data.get('homepage')
            if not metadata.repository:
                metadata.repository = poetry_data.get('repository')
            if not metadata.license:
                license_str = poetry_data.get('license')
                if license_str:
                    metadata.license = self._parse_license_string(license_str)
            if not metadata.keywords:
                metadata.keywords = poetry_data.get('keywords', [])
            if not metadata.classifiers:
                metadata.classifiers = poetry_data.get('classifiers', [])


# Convenience functions
def extract_project_metadata(project_path: str, project_files: Dict[str, List[FileInfo]]) -> ProjectMetadata:
    """
    Extract project metadata from a project directory.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        ProjectMetadata object
    """
    parser = MetadataParser()
    return parser.parse(Path(project_path), project_files)


def detect_project_type(project_path: str, project_files: Dict[str, List[FileInfo]]) -> ProjectType:
    """
    Detect the type of a Python project.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        ProjectType enum value
    """
    parser = MetadataParser()
    metadata = parser.parse(Path(project_path), project_files)
    return metadata.project_type


def find_license_info(project_path: str) -> Optional[LicenseType]:
    """
    Find license information for a project.
    
    Args:
        project_path: Path to project root
        
    Returns:
        LicenseType enum value or None
    """
    parser = MetadataParser()
    metadata = ProjectMetadata(project_name="temp")
    return parser._detect_license(Path(project_path), metadata)
