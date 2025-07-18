"""
Content prioritization logic for managing token budgets and ensuring
the most important information is included in README generation.

This module implements sophisticated algorithms to prioritize, filter,
and compress content based on importance scores and token constraints.
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from models.project_data import ProjectData, ClassInfo, FunctionInfo, ModuleInfo
from .token_counter import TokenCounter, ContentType, TokenBudget

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels for content."""
    CRITICAL = 10
    HIGH = 8
    MEDIUM = 6
    LOW = 4
    MINIMAL = 2


@dataclass
class PriorityScore:
    """Represents a priority score for a piece of content."""
    
    item_id: str
    item_type: str
    score: float
    token_count: int
    efficiency: float = field(init=False)
    reasons: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate efficiency score (priority per token)."""
        self.efficiency = self.score / max(self.token_count, 1)


class ContentPrioritizer:
    """Advanced content prioritization system."""
    
    def __init__(self, token_counter: Optional[TokenCounter] = None):
        self.token_counter = token_counter or TokenCounter()
        
        # Base priority scores for different content types
        self.base_priorities = {
            'public_class': 10,
            'public_function': 9,
            'main_entry_point': 10,
            'well_documented': 8,
            'has_examples': 9,
            'framework_related': 7,
            'configuration': 6,
            'private_method': 3,
            'test_code': 4,
            'utility_function': 5,
            'property': 6,
            'magic_method': 4,
            'deprecated': 2,
        }
        
        # Keywords that indicate importance
        self.important_keywords = {
            'main', 'init', 'setup', 'configure', 'run', 'execute', 'process',
            'create', 'build', 'generate', 'parse', 'validate', 'authenticate',
            'client', 'server', 'api', 'handler', 'manager', 'controller',
            'service', 'factory', 'builder', 'adapter', 'strategy'
        }
        
        # Framework detection patterns
        self.framework_patterns = {
            'flask': ['flask', 'route', 'blueprint', 'request', 'response'],
            'django': ['django', 'models', 'views', 'urls', 'forms'],
            'fastapi': ['fastapi', 'pydantic', 'basemodel', 'depends'],
            'sqlalchemy': ['sqlalchemy', 'declarative_base', 'session', 'query'],
            'pytest': ['pytest', 'fixture', 'parametrize', 'mark'],
            'click': ['click', 'command', 'option', 'argument'],
            'asyncio': ['asyncio', 'async', 'await', 'coroutine'],
        }
    
    def calculate_priority_scores(self, project_data: ProjectData) -> List[PriorityScore]:
        """
        Calculate priority scores for all content in project data.
        
        Args:
            project_data: Project data to prioritize
            
        Returns:
            List of priority scores sorted by importance
        """
        priority_scores = []
        
        # Process modules
        for module in project_data.structure.modules:
            module_scores = self._score_module(module)
            priority_scores.extend(module_scores)
        
        # Process examples
        for i, example in enumerate(project_data.examples):
            score = self._score_example(example, i)
            priority_scores.append(score)
        
        # Process configuration
        if project_data.configuration:
            config_score = self._score_configuration(project_data.configuration)
            priority_scores.append(config_score)
        
        # Sort by efficiency (priority per token)
        priority_scores.sort(key=lambda x: x.efficiency, reverse=True)
        
        return priority_scores
    
    def _score_module(self, module: ModuleInfo) -> List[PriorityScore]:
        """Score all content in a module."""
        scores = []
        
        # Score classes
        for class_info in module.classes:
            score = self._score_class(class_info, module)
            scores.append(score)
            
            # Score methods
            for method in class_info.methods:
                method_score = self._score_method(method, class_info, module)
                scores.append(method_score)
        
        # Score functions
        for function in module.functions:
            score = self._score_function(function, module)
            scores.append(score)
        
        return scores
    
    def _score_class(self, class_info: ClassInfo, module: ModuleInfo) -> PriorityScore:
        """Calculate priority score for a class."""
        base_score = self.base_priorities['public_class'] if class_info.name and not class_info.name.startswith('_') else 3
        
        reasons = []
        multiplier = 1.0
        
        # Check if well documented
        if class_info.docstring and len(class_info.docstring.strip()) > 50:
            multiplier *= 1.3
            reasons.append("well_documented")
        
        # Check for inheritance (likely important base classes)
        if class_info.inheritance:
            multiplier *= 1.2
            reasons.append("has_inheritance")
        
        # Check for framework patterns
        class_text = f"{class_info.name} {class_info.docstring or ''}"
        framework = self._detect_framework(class_text)
        if framework:
            multiplier *= 1.2
            reasons.append(f"framework_{framework}")
        
        # Check for important keywords
        if any(keyword in class_info.name.lower() for keyword in self.important_keywords):
            multiplier *= 1.3
            reasons.append("important_keyword")
        
        # Check if it's a main entry point
        if module.is_main and class_info.name in ['Main', 'App', 'Application']:
            multiplier *= 1.5
            reasons.append("main_entry_point")
        
        # Penalize private classes
        if class_info.name.startswith('_'):
            multiplier *= 0.5
            reasons.append("private_class")
        
        final_score = base_score * multiplier
        
        # Calculate token count
        content = f"{class_info.name}\n{class_info.docstring or ''}"
        token_count = self.token_counter.count_tokens(content, ContentType.CODE)
        
        return PriorityScore(
            item_id=f"class_{class_info.name}_{module.name}",
            item_type="class",
            score=final_score,
            token_count=token_count,
            reasons=reasons
        )
    
    def _score_method(self, method: FunctionInfo, class_info: ClassInfo, module: ModuleInfo) -> PriorityScore:
        """Calculate priority score for a method."""
        base_score = self.base_priorities['public_function'] if method.is_public else self.base_priorities['private_method']
        
        reasons = []
        multiplier = 1.0
        
        # Check if well documented
        if method.docstring and len(method.docstring.strip()) > 30:
            multiplier *= 1.2
            reasons.append("well_documented")
        
        # Check for special methods
        if method.name.startswith('__') and method.name.endswith('__'):
            base_score = self.base_priorities['magic_method']
            reasons.append("magic_method")
        
        # Check for properties
        if method.is_property:
            base_score = self.base_priorities['property']
            reasons.append("property")
        
        # Check for important keywords
        if any(keyword in method.name.lower() for keyword in self.important_keywords):
            multiplier *= 1.2
            reasons.append("important_keyword")
        
        # Check for framework patterns
        method_text = f"{method.name} {method.docstring or ''}"
        framework = self._detect_framework(method_text)
        if framework:
            multiplier *= 1.1
            reasons.append(f"framework_{framework}")
        
        # Penalize private methods
        if method.name.startswith('_') and not method.name.startswith('__'):
            multiplier *= 0.6
            reasons.append("private_method")
        
        final_score = base_score * multiplier
        
        # Calculate token count
        content = f"{method.signature}\n{method.docstring or ''}"
        token_count = self.token_counter.count_tokens(content, ContentType.CODE)
        
        return PriorityScore(
            item_id=f"method_{method.name}_{class_info.name}_{module.name}",
            item_type="method",
            score=final_score,
            token_count=token_count,
            reasons=reasons
        )
    
    def _score_function(self, function: FunctionInfo, module: ModuleInfo) -> PriorityScore:
        """Calculate priority score for a function."""
        base_score = self.base_priorities['public_function'] if function.is_public else 3
        
        reasons = []
        multiplier = 1.0
        
        # Check if well documented
        if function.docstring and len(function.docstring.strip()) > 30:
            multiplier *= 1.2
            reasons.append("well_documented")
        
        # Check for main entry point
        if function.name == 'main' or module.is_main:
            multiplier *= 1.5
            reasons.append("main_entry_point")
        
        # Check for important keywords
        if any(keyword in function.name.lower() for keyword in self.important_keywords):
            multiplier *= 1.2
            reasons.append("important_keyword")
        
        # Check for framework patterns
        function_text = f"{function.name} {function.docstring or ''}"
        framework = self._detect_framework(function_text)
        if framework:
            multiplier *= 1.1
            reasons.append(f"framework_{framework}")
        
        # Penalize private functions
        if function.name.startswith('_'):
            multiplier *= 0.6
            reasons.append("private_function")
        
        final_score = base_score * multiplier
        
        # Calculate token count
        content = f"{function.signature}\n{function.docstring or ''}"
        token_count = self.token_counter.count_tokens(content, ContentType.CODE)
        
        return PriorityScore(
            item_id=f"function_{function.name}_{module.name}",
            item_type="function",
            score=final_score,
            token_count=token_count,
            reasons=reasons
        )
    
    def _score_example(self, example: Any, index: int) -> PriorityScore:
        """Calculate priority score for an example."""
        base_score = self.base_priorities['has_examples']
        
        reasons = ["code_example"]
        multiplier = 1.0
        
        # Higher priority for basic usage examples
        if hasattr(example, 'example_type') and example.example_type == 'basic_usage':
            multiplier *= 1.3
            reasons.append("basic_usage")
        
        # Higher priority for executable examples
        if hasattr(example, 'is_executable') and example.is_executable:
            multiplier *= 1.1
            reasons.append("executable")
        
        final_score = base_score * multiplier
        
        # Calculate token count
        content = getattr(example, 'code', str(example))
        token_count = self.token_counter.count_tokens(content, ContentType.CODE)
        
        return PriorityScore(
            item_id=f"example_{index}",
            item_type="example",
            score=final_score,
            token_count=token_count,
            reasons=reasons
        )
    
    def _score_configuration(self, config: Any) -> PriorityScore:
        """Calculate priority score for configuration."""
        base_score = self.base_priorities['configuration']
        
        reasons = ["configuration"]
        
        # Calculate token count
        content = str(config)
        token_count = self.token_counter.count_tokens(content, ContentType.JSON)
        
        return PriorityScore(
            item_id="configuration",
            item_type="configuration",
            score=base_score,
            token_count=token_count,
            reasons=reasons
        )
    
    def _detect_framework(self, text: str) -> Optional[str]:
        """Detect framework usage in text."""
        text_lower = text.lower()
        
        for framework, patterns in self.framework_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return framework
        
        return None
    
    def filter_by_budget(self, priority_scores: List[PriorityScore], budget: TokenBudget) -> List[PriorityScore]:
        """
        Filter content to fit within token budget.
        
        Args:
            priority_scores: List of priority scores
            budget: Token budget constraints
            
        Returns:
            Filtered list that fits within budget
        """
        selected_scores = []
        
        # Separate by type for budget allocation
        by_type = {}
        for score in priority_scores:
            if score.item_type not in by_type:
                by_type[score.item_type] = []
            by_type[score.item_type].append(score)
        
        # Allocate budget by type
        type_budgets = {
            'class': budget.api_documentation // 2,
            'method': budget.api_documentation // 3,
            'function': budget.api_documentation // 6,
            'example': budget.examples,
            'configuration': budget.configuration,
        }
        
        for content_type, scores in by_type.items():
            type_budget = type_budgets.get(content_type, 10000)
            selected = self._select_by_budget(scores, type_budget)
            selected_scores.extend(selected)
        
        return selected_scores
    
    def _select_by_budget(self, scores: List[PriorityScore], budget: int) -> List[PriorityScore]:
        """Select items that fit within a specific budget."""
        scores.sort(key=lambda x: x.efficiency, reverse=True)
        
        selected = []
        used_tokens = 0
        
        for score in scores:
            if used_tokens + score.token_count <= budget:
                selected.append(score)
                used_tokens += score.token_count
            else:
                break
        
        return selected
    
    def compress_content(self, content: str, max_tokens: int, content_type: ContentType) -> str:
        """
        Compress content to fit within token limit.
        
        Args:
            content: Content to compress
            max_tokens: Maximum token limit
            content_type: Type of content
            
        Returns:
            Compressed content
        """
        current_tokens = self.token_counter.count_tokens(content, content_type)
        
        if current_tokens <= max_tokens:
            return content
        
        # Different compression strategies by content type
        if content_type == ContentType.CODE:
            return self._compress_code(content, max_tokens)
        elif content_type == ContentType.DOCSTRING:
            return self._compress_docstring(content, max_tokens)
        else:
            return self._compress_text(content, max_tokens)
    
    def _compress_code(self, code: str, max_tokens: int) -> str:
        """Compress code content."""
        lines = code.split('\n')
        
        # Keep important lines (class/function definitions, docstrings)
        important_lines = []
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith(('class ', 'def ', '"""', "'''")) or
                stripped.startswith('#') or
                not stripped):
                important_lines.append(line)
        
        # Add other lines until we hit the token limit
        compressed = '\n'.join(important_lines)
        current_tokens = self.token_counter.count_tokens(compressed, ContentType.CODE)
        
        if current_tokens <= max_tokens:
            return compressed
        
        # If still too long, truncate with ellipsis
        target_length = int(len(compressed) * (max_tokens / current_tokens) * 0.9)
        return compressed[:target_length] + "\n# ... (truncated)"
    
    def _compress_docstring(self, docstring: str, max_tokens: int) -> str:
        """Compress docstring content."""
        # Keep first paragraph and examples
        paragraphs = docstring.split('\n\n')
        
        compressed = paragraphs[0]  # Always keep first paragraph
        
        # Add additional paragraphs if they fit
        for para in paragraphs[1:]:
            test_content = compressed + '\n\n' + para
            if self.token_counter.count_tokens(test_content, ContentType.DOCSTRING) <= max_tokens:
                compressed = test_content
            else:
                break
        
        return compressed
    
    def _compress_text(self, text: str, max_tokens: int) -> str:
        """Compress general text content."""
        sentences = re.split(r'[.!?]+', text)
        
        compressed = sentences[0]
        
        for sentence in sentences[1:]:
            test_content = compressed + '. ' + sentence
            if self.token_counter.count_tokens(test_content, ContentType.TEXT) <= max_tokens:
                compressed = test_content
            else:
                break
        
        return compressed + '...' if len(compressed) < len(text) else compressed


def prioritize_project_data(project_data: ProjectData, token_budget: TokenBudget) -> List[PriorityScore]:
    """
    Prioritize project data content based on importance and token budget.
    
    Args:
        project_data: Project data to prioritize
        token_budget: Token budget constraints
        
    Returns:
        List of prioritized content items
    """
    prioritizer = ContentPrioritizer()
    priority_scores = prioritizer.calculate_priority_scores(project_data)
    return prioritizer.filter_by_budget(priority_scores, token_budget)


def filter_content_by_priority(content_items: List[Any], min_priority: float) -> List[Any]:
    """
    Filter content items by minimum priority score.
    
    Args:
        content_items: List of content items with priority scores
        min_priority: Minimum priority threshold
        
    Returns:
        Filtered list of content items
    """
    return [item for item in content_items if hasattr(item, 'score') and item.score >= min_priority]


def compress_content_for_budget(content: Dict[str, Any], token_budget: TokenBudget) -> Dict[str, Any]:
    """
    Compress content to fit within token budget.
    
    Args:
        content: Content dictionary to compress
        token_budget: Token budget constraints
        
    Returns:
        Compressed content dictionary
    """
    prioritizer = ContentPrioritizer()
    compressed = {}
    
    for key, value in content.items():
        if key == 'api_documentation':
            budget = token_budget.api_documentation
        elif key == 'examples':
            budget = token_budget.examples
        elif key == 'configuration':
            budget = token_budget.configuration
        else:
            budget = token_budget.metadata
        
        if isinstance(value, str):
            compressed[key] = prioritizer.compress_content(value, budget, ContentType.TEXT)
        elif isinstance(value, (dict, list)):
            # Convert to JSON and compress
            json_str = str(value)
            compressed[key] = prioritizer.compress_content(json_str, budget, ContentType.JSON)
        else:
            compressed[key] = value
    
    return compressed
