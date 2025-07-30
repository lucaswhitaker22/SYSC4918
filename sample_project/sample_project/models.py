"""
Data models and schemas for the Sample Project.

This module defines the core data structures, validation logic,
and serialization methods used throughout the application.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union, Type
from enum import Enum, auto
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.timestamp = time.time()


class ProcessingStatus(Enum):
    """Enumeration of processing status values."""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class Priority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BaseModel:
    """
    Base class for all data models with common functionality.
    
    Provides validation, serialization, and utility methods
    that are inherited by all specific model classes.
    """
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> bool:
        """
        Validate the model instance.
        
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        # Update the updated_at timestamp
        self.updated_at = datetime.now()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary representation.
        
        Returns:
            Dictionary representation of the model
        """
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert model to JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Create model instance from dictionary.
        
        Args:
            data: Dictionary containing model data
            
        Returns:
            New model instance
        """
        # Filter only fields that exist in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """
        Create model instance from JSON string.
        
        Args:
            json_str: JSON string containing model data
            
        Returns:
            New model instance
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
    
    def update(self, **kwargs) -> None:
        """
        Update model fields with new values.
        
        Args:
            **kwargs: Field values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def copy(self) -> 'BaseModel':
        """Create a copy of the model instance."""
        return self.__class__.from_dict(self.to_dict())


@dataclass
class DataModel(BaseModel):
    """
    Primary data model for representing business entities.
    
    This model represents the core data structure used throughout
    the application for processing and storage.
    
    Attributes:
        name: Entity name (required)
        value: Numeric value associated with the entity
        description: Optional description text
        tags: List of tags for categorization
        metadata: Additional metadata as key-value pairs
        is_active: Whether the entity is currently active
        priority: Priority level for processing
        
    Example:
        >>> model = DataModel(
        ...     name="test_entity",
        ...     value=42,
        ...     description="A test entity",
        ...     tags=["test", "example"]
        ... )
        >>> model.validate()
        True
        >>> model.name
        'test_entity'
    """
    name: str
    value: Union[int, float] = 0
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    priority: Priority = Priority.NORMAL
    
    def validate(self) -> bool:
        """
        Validate DataModel instance.
        
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        super().validate()
        
        # Name validation
        if not self.name or not isinstance(self.name, str):
            raise ValidationError("Name is required and must be a string", "name", self.name)
        
        if len(self.name.strip()) == 0:
            raise ValidationError("Name cannot be empty", "name", self.name)
        
        if len(self.name) > 100:
            raise ValidationError("Name must be 100 characters or less", "name", self.name)
        
        # Value validation
        if not isinstance(self.value, (int, float)):
            raise ValidationError("Value must be numeric", "value", self.value)
        
        # Tags validation
        if not isinstance(self.tags, list):
            raise ValidationError("Tags must be a list", "tags", self.tags)
        
        for tag in self.tags:
            if not isinstance(tag, str):
                raise ValidationError("All tags must be strings", "tags", tag)
        
        # Metadata validation
        if not isinstance(self.metadata, dict):
            raise ValidationError("Metadata must be a dictionary", "metadata", self.metadata)
        
        return True
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the model."""
        if isinstance(tag, str) and tag not in self.tags:
            self.tags.append(tag)
            self.update()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the model."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.update()
    
    def has_tag(self, tag: str) -> bool:
        """Check if model has a specific tag."""
        return tag in self.tags
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata key-value pair."""
        self.metadata[key] = value
        self.update()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value by key."""
        return self.metadata.get(key, default)
    
    def calculate_score(self) -> float:
        """
        Calculate a composite score based on model attributes.
        
        Returns:
            Calculated score as float
        """
        base_score = float(self.value)
        
        # Priority multiplier
        priority_multiplier = {
            Priority.LOW: 0.8,
            Priority.NORMAL: 1.0,
            Priority.HIGH: 1.2,
            Priority.CRITICAL: 1.5
        }
        
        score = base_score * priority_multiplier.get(self.priority, 1.0)
        
        # Tag bonus
        tag_bonus = len(self.tags) * 0.1
        score += tag_bonus
        
        # Active bonus
        if self.is_active:
            score *= 1.1
        
        return round(score, 2)


@dataclass
class ResultModel(BaseModel):
    """
    Model for representing processing results.
    
    This model encapsulates the results of data processing operations,
    including success status, content, and metadata.
    
    Attributes:
        success: Whether the operation was successful
        content: The processed content/data
        error: Error message if operation failed
        metadata: Additional metadata about the operation
        status: Processing status
        execution_time: Time taken for processing (seconds)
        
    Example:
        >>> result = ResultModel(
        ...     success=True,
        ...     content="Processed data",
        ...     metadata={"processor": "SampleProcessor"}
        ... )
        >>> result.success
        True
    """
    success: bool
    content: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ProcessingStatus = ProcessingStatus.COMPLETED
    execution_time: Optional[float] = None
    
    def validate(self) -> bool:
        """Validate ResultModel instance."""
        super().validate()
        
        # If not successful, should have error message
        if not self.success and not self.error:
            raise ValidationError("Failed results must include an error message")
        
        # If successful, should have content (unless explicitly None)
        if self.success and self.content is None and self.status == ProcessingStatus.COMPLETED:
            logger.warning("Successful result has None content")
        
        return True
    
    def is_success(self) -> bool:
        """Check if the result represents a successful operation."""
        return self.success and self.status != ProcessingStatus.FAILED
    
    def get_content_summary(self, max_length: int = 100) -> str:
        """
        Get a summary of the content.
        
        Args:
            max_length: Maximum length of summary
            
        Returns:
            Content summary string
        """
        if self.content is None:
            return "No content"
        
        content_str = str(self.content)
        if len(content_str) <= max_length:
            return content_str
        
        return content_str[:max_length] + "..."
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata key-value pair."""
        self.metadata[key] = value
        self.update()


@dataclass
class ConfigModel(BaseModel):
    """
    Model for configuration settings.
    
    This model represents configuration options that can be
    persisted and loaded for application settings.
    
    Attributes:
        debug: Debug mode flag
        max_items: Maximum number of items to process
        max_size: Maximum size limit for data
        timeout: Timeout in seconds
        cache_enabled: Whether caching is enabled
        log_level: Logging level
        custom_settings: Additional custom settings
        
    Example:
        >>> config = ConfigModel(debug=True, max_items=50)
        >>> config.debug
        True
        >>> config.get_log_level()
        'INFO'
    """
    debug: bool = False
    max_items: int = 100
    max_size: int = 10000
    timeout: int = 30
    cache_enabled: bool = True
    log_level: str = "INFO"
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate ConfigModel instance."""
        super().validate()
        
        if self.max_items <= 0:
            raise ValidationError("max_items must be positive", "max_items", self.max_items)
        
        if self.max_size <= 0:
            raise ValidationError("max_size must be positive", "max_size", self.max_size)
        
        if self.timeout <= 0:
            raise ValidationError("timeout must be positive", "timeout", self.timeout)
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ValidationError(
                f"log_level must be one of {valid_log_levels}", 
                "log_level", 
                self.log_level
            )
        
        return True
    
    def get_log_level(self) -> str:
        """Get the log level in uppercase."""
        return self.log_level.upper()
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug or self.get_log_level() == "DEBUG"
    
    def set_custom_setting(self, key: str, value: Any) -> None:
        """Set a custom configuration setting."""
        self.custom_settings[key] = value
        self.update()
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Get a custom configuration setting."""
        return self.custom_settings.get(key, default)


@dataclass
class TaskModel(BaseModel):
    """
    Model for representing processing tasks.
    
    This model represents individual tasks that can be queued,
    processed, and tracked through their lifecycle.
    
    Attributes:
        id: Unique task identifier
        name: Task name/description
        data: Task input data
        status: Current task status
        priority: Task priority level
        result: Task processing result
        error_count: Number of processing errors
        max_retries: Maximum retry attempts
        
    Example:
        >>> task = TaskModel(
        ...     id="task_123",
        ...     name="Process data",
        ...     data={"key": "value"}
        ... )
        >>> task.can_retry()
        True
    """
    id: str
    name: str
    data: Any = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    priority: Priority = Priority.NORMAL
    result: Optional[ResultModel] = None
    error_count: int = 0
    max_retries: int = 3
    
    def validate(self) -> bool:
        """Validate TaskModel instance."""
        super().validate()
        
        if not self.id or not isinstance(self.id, str):
            raise ValidationError("Task ID is required", "id", self.id)
        
        if not self.name or not isinstance(self.name, str):
            raise ValidationError("Task name is required", "name", self.name)
        
        if self.error_count < 0:
            raise ValidationError("Error count cannot be negative", "error_count", self.error_count)
        
        if self.max_retries < 0:
            raise ValidationError("Max retries cannot be negative", "max_retries", self.max_retries)
        
        return True
    
    def can_retry(self) -> bool:
        """Check if the task can be retried."""
        return (
            self.status == ProcessingStatus.FAILED and 
            self.error_count < self.max_retries
        )
    
    def mark_in_progress(self) -> None:
        """Mark task as in progress."""
        self.status = ProcessingStatus.IN_PROGRESS
        self.update()
    
    def mark_completed(self, result: ResultModel) -> None:
        """Mark task as completed with result."""
        self.status = ProcessingStatus.COMPLETED
        self.result = result
        self.update()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark task as failed with error."""
        self.status = ProcessingStatus.FAILED
        self.error_count += 1
        if not self.result:
            self.result = ResultModel(success=False, error=error_message)
        else:
            self.result.error = error_message
        self.update()
    
    def get_priority_score(self) -> int:
        """Get numeric priority score for sorting."""
        return self.priority.value


# Model registry for dynamic model creation
MODEL_REGISTRY: Dict[str, Type[BaseModel]] = {
    'data': DataModel,
    'result': ResultModel,
    'config': ConfigModel,
    'task': TaskModel,
}


def create_model(model_type: str, **kwargs) -> BaseModel:
    """
    Factory function to create model instances by type.
    
    Args:
        model_type: Type of model to create
        **kwargs: Model initialization parameters
        
    Returns:
        New model instance
        
    Raises:
        ValueError: If model_type is unknown
        
    Example:
        >>> model = create_model('data', name='test', value=42)
        >>> isinstance(model, DataModel)
        True
    """
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model type: {model_type}")
    
    model_class = MODEL_REGISTRY[model_type]
    return model_class(**kwargs)


def validate_models(models: List[BaseModel]) -> List[ValidationError]:
    """
    Validate multiple models and return any validation errors.
    
    Args:
        models: List of models to validate
        
    Returns:
        List of validation errors (empty if all valid)
    """
    errors = []
    
    for i, model in enumerate(models):
        try:
            model.validate()
        except ValidationError as e:
            e.model_index = i
            e.model_type = type(model).__name__
            errors.append(e)
    
    return errors


def serialize_models(models: List[BaseModel]) -> List[Dict[str, Any]]:
    """
    Serialize a list of models to dictionaries.
    
    Args:
        models: List of models to serialize
        
    Returns:
        List of model dictionaries
    """
    return [model.to_dict() for model in models]


# Utility functions for model manipulation
def filter_models_by_status(models: List[TaskModel], status: ProcessingStatus) -> List[TaskModel]:
    """Filter task models by status."""
    return [model for model in models if model.status == status]


def sort_models_by_priority(models: List[TaskModel], descending: bool = True) -> List[TaskModel]:
    """Sort task models by priority."""
    return sorted(models, key=lambda x: x.get_priority_score(), reverse=descending)


def find_model_by_id(models: List[TaskModel], task_id: str) -> Optional[TaskModel]:
    """Find a task model by ID."""
    return next((model for model in models if model.id == task_id), None)
