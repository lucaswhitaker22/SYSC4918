"""
Main project parser orchestrator that coordinates all parsing activities.

This module provides the primary interface for parsing Python projects,
managing the parsing workflow, and consolidating results from all sub-parsers.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import traceback

from models.project_data import (
    ProjectData, ProjectMetadata, DependencyInfo, ProjectStructure, 
    ConfigurationInfo, CodeExample, TestInfo, DocumentationInfo
)
from utils.file_utils import get_project_files, FileInfo
from utils.token_counter import TokenCounter, get_token_budget_allocation
from utils.content_prioritizer import ContentPrioritizer, prioritize_project_data
from utils.json_serializer import ProjectDataSerializer

from .metadata_parser import MetadataParser
from .dependency_parser import DependencyParser
from .code_parser import CodeParser
from .structure_parser import StructureParser
from .example_parser import ExampleParser

logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """Custom exception for parsing errors."""
    
    def __init__(self, message: str, parser_name: str = None, file_path: str = None):
        self.message = message
        self.parser_name = parser_name
        self.file_path = file_path
        super().__init__(self.message)


@dataclass
class ParseResult:
    """Result of project parsing operation."""
    
    project_data: ProjectData
    success: bool
    duration: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class ProjectParser:
    """
    Main orchestrator for parsing Python projects.
    
    This class coordinates all sub-parsers and manages the overall parsing workflow,
    including error handling, prioritization, and token management.
    """
    
    def __init__(self, 
                 model_name: str = "gemini_2_5_pro",
                 max_tokens: int = 1_000_000,
                 include_tests: bool = False,
                 include_private: bool = False,
                 enable_caching: bool = True):
        """
        Initialize the project parser.
        
        Args:
            model_name: Target LLM model name for token management
            max_tokens: Maximum token budget
            include_tests: Whether to include test files in parsing
            include_private: Whether to include private methods/classes
            enable_caching: Whether to enable result caching
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.include_tests = include_tests
        self.include_private = include_private
        self.enable_caching = enable_caching
        
        # Initialize components
        self.token_counter = TokenCounter(model_name)
        self.content_prioritizer = ContentPrioritizer(self.token_counter)
        self.serializer = ProjectDataSerializer(self.token_counter)
        
        # Initialize sub-parsers
        self.metadata_parser = MetadataParser()
        self.dependency_parser = DependencyParser()
        self.code_parser = CodeParser(include_private=include_private)
        self.structure_parser = StructureParser()
        self.example_parser = ExampleParser()
        
        # Parsing statistics
        self.stats = {
            'files_processed': 0,
            'lines_processed': 0,
            'classes_found': 0,
            'functions_found': 0,
            'examples_found': 0,
            'errors_encountered': 0,
            'warnings_generated': 0
        }
        
        # Error tracking
        self.parsing_errors = []
        self.parsing_warnings = []
    
    def parse_project(self, project_path: str) -> ParseResult:
        """
        Parse a Python project and extract all relevant information.
        
        Args:
            project_path: Path to the project root directory
            
        Returns:
            ParseResult containing parsed project data and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting to parse project: {project_path}")
            
            # Validate project path
            project_path = Path(project_path).resolve()
            if not project_path.exists():
                raise ParsingError(f"Project path does not exist: {project_path}")
            
            if not project_path.is_dir():
                raise ParsingError(f"Project path is not a directory: {project_path}")
            
            # Initialize project data structure
            project_data = self._initialize_project_data(project_path)
            
            # Get project files
            logger.info("Scanning project files...")
            project_files = get_project_files(str(project_path), include_tests=self.include_tests)
            self.stats['files_processed'] = sum(len(files) for files in project_files.values())
            
            # Parse different aspects of the project
            logger.info("Parsing project metadata...")
            project_data.metadata = self._parse_metadata(project_path, project_files)
            
            logger.info("Parsing project dependencies...")
            project_data.dependencies = self._parse_dependencies(project_path, project_files)
            
            logger.info("Parsing project structure...")
            project_data.structure = self._parse_structure(project_path, project_files)
            
            logger.info("Parsing code information...")
            self._parse_code_information(project_data.structure)
            
            logger.info("Parsing configuration...")
            project_data.configuration = self._parse_configuration(project_path, project_files)
            
            logger.info("Extracting examples...")
            project_data.examples = self._extract_examples(project_data.structure)
            
            logger.info("Parsing test information...")
            project_data.tests = self._parse_tests(project_path, project_files)
            
            logger.info("Parsing documentation...")
            project_data.documentation = self._parse_documentation(project_path, project_files)
            
            # Apply prioritization and token management
            logger.info("Applying content prioritization...")
            project_data = self._apply_prioritization(project_data)
            
            # Set final metadata
            project_data.parsing_errors = self.parsing_errors
            project_data.parsing_timestamp = datetime.now().isoformat()
            
            # Calculate final token count
            serialized_data = self.serializer.serialize(project_data, validate=False)
            project_data.token_count = self.token_counter.count_tokens_in_dict(serialized_data)
            
            duration = time.time() - start_time
            logger.info(f"Project parsing completed in {duration:.2f} seconds")
            
            # Update final statistics
            self.stats['lines_processed'] = project_data.structure.total_lines
            self.stats['classes_found'] = sum(len(module.classes) for module in project_data.structure.modules)
            self.stats['functions_found'] = sum(len(module.functions) for module in project_data.structure.modules)
            self.stats['examples_found'] = len(project_data.examples)
            self.stats['errors_encountered'] = len(self.parsing_errors)
            self.stats['warnings_generated'] = len(self.parsing_warnings)
            
            return ParseResult(
                project_data=project_data,
                success=True,
                duration=duration,
                errors=self.parsing_errors,
                warnings=self.parsing_warnings,
                stats=self.stats
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to parse project: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Create minimal project data for error case
            project_data = ProjectData(
                metadata=ProjectMetadata(project_name=project_path.name),
                dependencies=DependencyInfo(),
                structure=ProjectStructure(root_path=str(project_path)),
                configuration=ConfigurationInfo(),
                parsing_errors=[error_msg],
                parsing_timestamp=datetime.now().isoformat()
            )
            
            return ParseResult(
                project_data=project_data,
                success=False,
                duration=duration,
                errors=[error_msg],
                warnings=self.parsing_warnings,
                stats=self.stats
            )
    
    def _initialize_project_data(self, project_path: Path) -> ProjectData:
        """Initialize the project data structure."""
        return ProjectData(
            metadata=ProjectMetadata(project_name=project_path.name),
            dependencies=DependencyInfo(),
            structure=ProjectStructure(root_path=str(project_path)),
            configuration=ConfigurationInfo()
        )
    
    def _parse_metadata(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectMetadata:
        """Parse project metadata using the metadata parser."""
        try:
            return self.metadata_parser.parse(project_path, project_files)
        except Exception as e:
            error_msg = f"Error parsing metadata: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return ProjectMetadata(project_name=project_path.name)
    
    def _parse_dependencies(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> DependencyInfo:
        """Parse project dependencies using the dependency parser."""
        try:
            return self.dependency_parser.parse(project_path, project_files)
        except Exception as e:
            error_msg = f"Error parsing dependencies: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return DependencyInfo()
    
    def _parse_structure(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectStructure:
        """Parse project structure using the structure parser."""
        try:
            return self.structure_parser.parse(project_path, project_files)
        except Exception as e:
            error_msg = f"Error parsing project structure: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return ProjectStructure(root_path=str(project_path))
    
    def _parse_code_information(self, structure: ProjectStructure) -> None:
        """Parse code information for all modules in the structure."""
        for module in structure.modules:
            try:
                # Parse the Python file and extract code information
                code_info = self.code_parser.parse_file(module.file_path)
                
                # Update module with parsed information
                module.classes = code_info.classes
                module.functions = code_info.functions
                module.constants = code_info.constants
                module.imports = code_info.imports
                module.docstring = code_info.docstring
                
            except Exception as e:
                error_msg = f"Error parsing code in {module.file_path}: {str(e)}"
                logger.error(error_msg)
                self.parsing_errors.append(error_msg)
    
    def _parse_configuration(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ConfigurationInfo:
        """Parse project configuration information."""
        try:
            config_info = ConfigurationInfo()
            
            # Find configuration files
            config_files = []
            for file_info in project_files.get('config', []):
                config_files.append(file_info.path)
            
            config_info.config_files = config_files
            
            # Parse environment variables and settings
            # This would be implemented based on specific configuration file formats
            
            return config_info
            
        except Exception as e:
            error_msg = f"Error parsing configuration: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return ConfigurationInfo()
    
    def _extract_examples(self, structure: ProjectStructure) -> List[CodeExample]:
        """Extract code examples using the example parser."""
        try:
            examples = []
            
            for module in structure.modules:
                module_examples = self.example_parser.extract_from_module(module)
                examples.extend(module_examples)
            
            return examples
            
        except Exception as e:
            error_msg = f"Error extracting examples: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return []
    
    def _parse_tests(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> Optional[TestInfo]:
        """Parse test information."""
        try:
            if not self.include_tests:
                return None
            
            test_files = [file_info.path for file_info in project_files.get('tests', [])]
            
            if not test_files:
                return None
            
            # Detect test framework
            test_framework = self._detect_test_framework(test_files)
            
            return TestInfo(
                test_directories=list(set(os.path.dirname(tf) for tf in test_files)),
                test_files=test_files,
                test_framework=test_framework,
                total_tests=len(test_files)
            )
            
        except Exception as e:
            error_msg = f"Error parsing tests: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return None
    
    def _parse_documentation(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> Optional[DocumentationInfo]:
        """Parse documentation information."""
        try:
            doc_files = [file_info.path for file_info in project_files.get('documentation', [])]
            
            if not doc_files:
                return None
            
            # Find specific documentation files
            readme_file = None
            license_file = None
            changelog_file = None
            
            for file_path in doc_files:
                filename = os.path.basename(file_path).lower()
                if filename.startswith('readme'):
                    readme_file = file_path
                elif filename.startswith('license'):
                    license_file = file_path
                elif filename.startswith('changelog'):
                    changelog_file = file_path
            
            # Check for documentation tools
            has_sphinx = any('sphinx' in str(f).lower() for f in project_path.rglob('*'))
            has_mkdocs = any('mkdocs' in str(f).lower() for f in project_path.rglob('*'))
            
            return DocumentationInfo(
                readme_file=readme_file,
                license_file=license_file,
                changelog_file=changelog_file,
                doc_files=doc_files,
                has_sphinx=has_sphinx,
                has_mkdocs=has_mkdocs
            )
            
        except Exception as e:
            error_msg = f"Error parsing documentation: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return None
    
    def _detect_test_framework(self, test_files: List[str]) -> Optional[str]:
        """Detect the test framework being used."""
        framework_patterns = {
            'pytest': ['pytest', 'conftest.py', '@pytest'],
            'unittest': ['unittest', 'TestCase'],
            'nose': ['nose', 'nosetests'],
            'doctest': ['doctest']
        }
        
        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for framework, patterns in framework_patterns.items():
                    if any(pattern in content for pattern in patterns):
                        return framework
                        
            except Exception:
                continue
        
        return None
    
    def _apply_prioritization(self, project_data: ProjectData) -> ProjectData:
        """Apply content prioritization and token management."""
        try:
            # Get token budget
            token_budget = self.token_counter.get_budget_allocation()
            
            # Calculate current token usage
            serialized_data = self.serializer.serialize(project_data, validate=False)
            current_tokens = self.token_counter.count_tokens_in_dict(serialized_data)
            
            logger.info(f"Current token count: {current_tokens}")
            logger.info(f"Token budget: {token_budget.total_budget}")
            
            # If we're over budget, apply prioritization
            if current_tokens > token_budget.total_budget:
                logger.info("Applying content prioritization to fit token budget")
                
                # Get priority scores
                priority_scores = self.content_prioritizer.calculate_priority_scores(project_data)
                
                # Filter content by budget
                filtered_scores = self.content_prioritizer.filter_by_budget(priority_scores, token_budget)
                
                # Apply filtering to project data
                project_data = self._filter_project_data(project_data, filtered_scores)
                
                # Recalculate token count
                serialized_data = self.serializer.serialize(project_data, validate=False)
                final_tokens = self.token_counter.count_tokens_in_dict(serialized_data)
                
                logger.info(f"Final token count after prioritization: {final_tokens}")
                
                if final_tokens > token_budget.total_budget:
                    warning_msg = f"Token count ({final_tokens}) still exceeds budget ({token_budget.total_budget})"
                    logger.warning(warning_msg)
                    self.parsing_warnings.append(warning_msg)
            
            return project_data
            
        except Exception as e:
            error_msg = f"Error applying prioritization: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return project_data
    
    def _filter_project_data(self, project_data: ProjectData, priority_scores: List[Any]) -> ProjectData:
        """Filter project data based on priority scores."""
        # This would implement the actual filtering logic
        # For now, we'll return the original data
        # In a full implementation, this would remove low-priority content
        return project_data
    
    def get_parsing_summary(self) -> Dict[str, Any]:
        """Get a summary of the parsing operation."""
        return {
            'statistics': self.stats,
            'errors': self.parsing_errors,
            'warnings': self.parsing_warnings,
            'configuration': {
                'model_name': self.model_name,
                'max_tokens': self.max_tokens,
                'include_tests': self.include_tests,
                'include_private': self.include_private,
                'enable_caching': self.enable_caching
            }
        }


# Convenience functions for external use
def parse_project(project_path: str, 
                 model_name: str = "gemini_2_5_pro",
                 max_tokens: int = 1_000_000,
                 include_tests: bool = False,
                 include_private: bool = False) -> ParseResult:
    """
    Parse a Python project and return structured data.
    
    Args:
        project_path: Path to the project root directory
        model_name: Target LLM model name
        max_tokens: Maximum token budget
        include_tests: Whether to include test files
        include_private: Whether to include private methods/classes
        
    Returns:
        ParseResult containing parsed project data
    """
    parser = ProjectParser(
        model_name=model_name,
        max_tokens=max_tokens,
        include_tests=include_tests,
        include_private=include_private
    )
    
    return parser.parse_project(project_path)


def parse_project_to_json(project_path: str,
                         output_path: Optional[str] = None,
                         model_name: str = "gemini_2_5_pro",
                         max_tokens: int = 1_000_000,
                         include_tests: bool = False,
                         include_private: bool = False) -> Tuple[bool, str]:
    """
    Parse a Python project and save results to JSON file.
    
    Args:
        project_path: Path to the project root directory
        output_path: Path to save JSON file (defaults to project_path/parsed_data.json)
        model_name: Target LLM model name
        max_tokens: Maximum token budget
        include_tests: Whether to include test files
        include_private: Whether to include private methods/classes
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Parse project
        result = parse_project(
            project_path=project_path,
            model_name=model_name,
            max_tokens=max_tokens,
            include_tests=include_tests,
            include_private=include_private
        )
        
        if not result.success:
            return False, f"Parsing failed: {'; '.join(result.errors)}"
        
        # Determine output path
        if output_path is None:
            output_path = os.path.join(project_path, "parsed_data.json")
        
        # Serialize and save
        serializer = ProjectDataSerializer()
        serialized_data = serializer.serialize(result.project_data)
        
        from ..utils.json_serializer import save_json_to_file
        success = save_json_to_file(serialized_data, output_path)
        
        if success:
            return True, f"Project parsed successfully. Output saved to: {output_path}"
        else:
            return False, f"Failed to save output to: {output_path}"
            
    except Exception as e:
        return False, f"Error parsing project: {str(e)}"
