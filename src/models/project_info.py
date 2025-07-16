# src/models/project_info.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


@dataclass
class ProjectInfo:
    """
    Enhanced data class to store comprehensive information about a parsed Python project.
    
    This object holds all metadata, structural details, and LLM-optimized content
    extracted by the parsing engine for README generation using models like Gemini 2.5 Flash.
    """
    # Core project information
    root_path: str
    name: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    main_modules: List[str] = field(default_factory=list)
    project_structure: Dict[str, List[str]] = field(default_factory=dict)
    setup_file: Optional[str] = None
    requirements_file: Optional[str] = None
    
    # Enhanced metadata for README generation
    version: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    license_info: Optional[str] = None
    
    # LLM-specific content extraction
    docstrings: List[str] = field(default_factory=list)
    function_signatures: List[Dict[str, Any]] = field(default_factory=list)
    class_hierarchy: Dict[str, List[str]] = field(default_factory=dict)
    usage_examples: List[str] = field(default_factory=list)
    
    # Content categorization for prioritization
    core_modules: List[str] = field(default_factory=list)
    utility_modules: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    example_files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    
    # Framework and project type detection
    detected_frameworks: List[str] = field(default_factory=list)
    project_domain: Optional[str] = None
    deployment_patterns: List[str] = field(default_factory=list)
    
    # Token management and optimization (critical for 1M context window)
    estimated_tokens: int = 0
    priority_score: float = 0.0
    file_importance_scores: Dict[str, float] = field(default_factory=dict)
    
    # Advanced project analysis
    import_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    api_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    design_patterns: List[str] = field(default_factory=list)
    configuration_options: Dict[str, Any] = field(default_factory=dict)
    
    # Function comment extraction (new enhancement)
    function_comments: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    file_docstrings: Dict[str, str] = field(default_factory=dict)
    class_comments: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    parsed_files: List[str] = field(default_factory=list)
    
    def calculate_token_estimate(self, model: str = "gemini-2.5-flash") -> int:
        """
        Calculate estimated token count for LLM context based on project content.
        Optimized for Gemini 2.5 Flash's 1M token context window.
        
        Args:
            model: The target LLM model for token estimation
            
        Returns:
            Estimated token count for the project content
        """
        try:
            import tiktoken
            # Map model names to appropriate tokenizers
            model_mapping = {
                "gemini-2.5-flash": "cl100k_base",  # Approximate tokenizer
                "gpt-4": "cl100k_base",
                "gpt-4o": "o200k_base",
                "claude-sonnet": "cl100k_base",
            }
            
            encoding_name = model_mapping.get(model, "cl100k_base")
            encoding = tiktoken.get_encoding(encoding_name)
        except (ImportError, KeyError):
            # Fallback estimation: roughly 1.3 tokens per word
            return self._fallback_token_estimate()
        
        total_tokens = 0
        
        # Count tokens from various content sources
        content_sources = [
            "\n".join(self.docstrings),
            "\n".join(self.usage_examples),
            str(self.function_signatures),
            str(self.class_hierarchy),
            str(self.project_structure),
            self.description or "",
            str(self.function_comments),
            str(self.file_docstrings),
        ]
        
        for content in content_sources:
            if content:
                total_tokens += len(encoding.encode(content))
        
        self.estimated_tokens = total_tokens
        return total_tokens
    
    def _fallback_token_estimate(self) -> int:
        """Fallback token estimation when tiktoken is not available."""
        total_chars = 0
        
        # Estimate based on character count
        text_sources = [
            "\n".join(self.docstrings),
            "\n".join(self.usage_examples),
            str(self.function_signatures),
            str(self.class_hierarchy),
            self.description or "",
            str(self.function_comments),
            str(self.file_docstrings),
        ]
        
        for text in text_sources:
            total_chars += len(text)
        
        # Rough estimation: 4 characters per token
        estimated_tokens = total_chars // 4
        self.estimated_tokens = estimated_tokens
        return estimated_tokens
    
    def calculate_priority_score(self) -> float:
        """
        Calculate overall priority score for content optimization.
        
        Returns:
            Priority score (0.0 to 10.0) indicating content importance
        """
        score = 0.0
        
        # Project completeness indicators
        if self.name:
            score += 1.0
        if self.description:
            score += 1.0
        if self.version:
            score += 0.5
        if self.author:
            score += 0.5
        
        # Documentation quality
        if self.docstrings:
            score += min(2.0, len(self.docstrings) * 0.2)
        
        # Function comments quality
        if self.function_comments:
            score += min(1.0, len(self.function_comments) * 0.1)
        
        # Usage examples availability
        if self.usage_examples:
            score += min(2.0, len(self.usage_examples) * 0.5)
        
        # Project structure complexity
        if self.main_modules:
            score += min(1.0, len(self.main_modules) * 0.3)
        
        # Framework detection bonus
        if self.detected_frameworks:
            score += 1.0
        
        # API endpoints (for web projects)
        if self.api_endpoints:
            score += 1.0
        
        self.priority_score = min(10.0, score)
        return self.priority_score
    
    def get_high_priority_content(self, max_tokens: int = 1000000) -> Dict[str, Any]:
        """
        Extract high-priority content optimized for LLM context window.
        Default max_tokens set to 1M for Gemini 2.5 Flash.
        
        Args:
            max_tokens: Maximum number of tokens to include
            
        Returns:
            Dictionary of optimized content for LLM processing
        """
        # Calculate current token estimate
        current_tokens = self.calculate_token_estimate()
        
        high_priority_content = {
            "project_metadata": {
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "author": self.author,
                "license": self.license_info,
            },
            "project_structure": self._get_summarized_structure(),
            "dependencies": self.dependencies[:50],  # Increased for larger context
            "main_modules": self.main_modules,
            "entry_points": self.entry_points,
            "frameworks": self.detected_frameworks,
            "domain": self.project_domain,
            "deployment_patterns": self.deployment_patterns,
        }
        
        # Add content based on available token budget
        remaining_tokens = max_tokens - self._estimate_metadata_tokens()
        
        if remaining_tokens > 50000:
            high_priority_content["docstrings"] = self._get_top_docstrings(20000)
        
        if remaining_tokens > 30000:
            high_priority_content["function_comments"] = self._get_top_function_comments(15000)
        
        if remaining_tokens > 20000:
            high_priority_content["usage_examples"] = self.usage_examples[:10]
        
        if remaining_tokens > 15000:
            high_priority_content["function_signatures"] = self.function_signatures[:50]
        
        if remaining_tokens > 10000:
            high_priority_content["api_endpoints"] = self.api_endpoints[:20]
        
        if remaining_tokens > 5000:
            high_priority_content["design_patterns"] = self.design_patterns
        
        return high_priority_content
    
    def _get_summarized_structure(self) -> Dict[str, int]:
        """Get summarized project structure with file counts."""
        summarized = {}
        for directory, files in self.project_structure.items():
            python_files = [f for f in files if f.endswith('.py')]
            if python_files:
                summarized[directory] = len(python_files)
        return summarized
    
    def _get_top_docstrings(self, max_chars: int) -> List[str]:
        """Get top docstrings up to character limit."""
        selected_docstrings = []
        char_count = 0
        
        for docstring in self.docstrings:
            if char_count + len(docstring) <= max_chars:
                selected_docstrings.append(docstring)
                char_count += len(docstring)
            else:
                break
        
        return selected_docstrings
    
    def _get_top_function_comments(self, max_chars: int) -> Dict[str, List[Dict[str, Any]]]:
        """Get top function comments up to character limit."""
        selected_comments = {}
        char_count = 0
        
        for file_path, comments in self.function_comments.items():
            file_content = str(comments)
            if char_count + len(file_content) <= max_chars:
                selected_comments[file_path] = comments
                char_count += len(file_content)
            else:
                break
        
        return selected_comments
    
    def _estimate_metadata_tokens(self) -> int:
        """Estimate tokens used by basic metadata."""
        metadata_text = f"{self.name} {self.description} {self.version} {self.author}"
        return len(metadata_text.split()) * 1.3  # Rough estimation
    
    def add_docstring(self, docstring: str, source_file: str = ""):
        """Add a docstring with optional source file tracking."""
        if docstring and docstring.strip():
            # Avoid duplicates
            if docstring not in self.docstrings:
                self.docstrings.append(docstring)
    
    def add_usage_example(self, example: str, source_file: str = ""):
        """Add a usage example with optional source file tracking."""
        if example and example.strip():
            if example not in self.usage_examples:
                self.usage_examples.append(example)
    
    def add_function_signature(self, signature: Dict[str, Any]):
        """Add a function signature to the collection."""
        if signature not in self.function_signatures:
            self.function_signatures.append(signature)
    
    def set_file_importance_score(self, filepath: str, score: float):
        """Set importance score for a specific file."""
        self.file_importance_scores[filepath] = score
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the project."""
        total_python_files = sum(
            len([f for f in files if f.endswith('.py')])
            for files in self.project_structure.values()
        )
        
        return {
            "total_directories": len(self.project_structure),
            "total_python_files": total_python_files,
            "total_dependencies": len(self.dependencies),
            "total_docstrings": len(self.docstrings),
            "total_usage_examples": len(self.usage_examples),
            "total_function_signatures": len(self.function_signatures),
            "total_function_comments": len(self.function_comments),
            "total_parsed_files": len(self.parsed_files),
            "estimated_tokens": self.estimated_tokens,
            "priority_score": self.priority_score,
            "detected_frameworks": len(self.detected_frameworks),
            "api_endpoints": len(self.api_endpoints),
        }
    
    def is_within_context_window(self, max_tokens: int = 1000000) -> bool:
        """
        Check if project content fits within the specified context window.
        
        Args:
            max_tokens: Maximum token limit (default: 1M for Gemini 2.5 Flash)
            
        Returns:
            True if content fits within limits, False otherwise
        """
        return self.calculate_token_estimate() <= max_tokens
    
    def get_cost_estimate(self, model: str = "gemini-2.5-flash") -> float:
        """
        Estimate API cost based on token count and model pricing.
        
        Args:
            model: LLM model name
            
        Returns:
            Estimated cost in USD
        """
        tokens = self.calculate_token_estimate(model)
        
        # Pricing per 1M tokens (input) based on research
        pricing = {
            "gemini-2.5-flash": 0.30,  # $0.30 per 1M tokens
            "gpt-4o-mini": 0.15,       # $0.15 per 1M tokens
            "claude-sonnet": 3.00,     # $3.00 per 1M tokens
        }
        
        price_per_token = pricing.get(model, 0.30) / 1000000
        return tokens * price_per_token
    
    def optimize_for_cost(self, target_cost: float = 0.01) -> Dict[str, Any]:
        """
        Optimize content to stay within cost budget.
        
        Args:
            target_cost: Maximum cost in USD
            
        Returns:
            Optimized content dictionary
        """
        current_cost = self.get_cost_estimate()
        
        if current_cost <= target_cost:
            return self.get_high_priority_content()
        
        # Calculate reduction ratio needed
        reduction_ratio = target_cost / current_cost
        max_tokens = int(self.estimated_tokens * reduction_ratio)
        
        return self.get_high_priority_content(max_tokens)
