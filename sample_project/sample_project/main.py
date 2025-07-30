"""
Core business logic and main processing classes.

This module contains the primary functionality of the sample project,
including data processors, business logic, and core algorithms.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .config import Config, DEFAULT_CONFIG
from .models import DataModel, ResultModel, ValidationError
from .utils import validate_input, timing_decorator, format_output

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Raised when data processing fails."""
    
    def __init__(self, message: str, error_code: int = 500, details: Optional[Dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = time.time()


class BaseProcessor(ABC):
    """
    Abstract base class for all data processors.
    
    This class defines the interface that all processors must implement
    and provides common functionality for error handling and logging.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the processor with configuration.
        
        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or Config()
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._setup_processor()
    
    def _setup_processor(self) -> None:
        """Set up processor-specific configuration."""
        if self.config.debug:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug(f"Initialized {self.__class__.__name__} in debug mode")
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """
        Process input data and return results.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data
            
        Raises:
            ProcessingError: If processing fails
        """
        pass
    
    @abstractmethod
    def validate_input(self, data: Any) -> bool:
        """
        Validate input data format and content.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processor status."""
        return {
            "class": self.__class__.__name__,
            "config": self.config.to_dict(),
            "debug": self.config.debug,
            "timestamp": time.time()
        }


class SampleProcessor(BaseProcessor):
    """
    Main processor class for handling various data processing tasks.
    
    This processor can handle different types of input data and apply
    various transformations based on configuration settings.
    
    Attributes:
        processed_count: Number of items processed
        error_count: Number of processing errors
        
    Example:
        >>> config = Config(debug=True, max_items=100)
        >>> processor = SampleProcessor(config)
        >>> result = processor.process("Hello World")
        >>> print(result.content)
        Processed: Hello World
    """
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.processed_count = 0
        self.error_count = 0
        self._cache = {}
        self._processors = self._initialize_processors()
    
    def _initialize_processors(self) -> Dict[str, Callable]:
        """Initialize specialized processors for different data types."""
        return {
            'string': self._process_string,
            'number': self._process_number,
            'list': self._process_list,
            'dict': self._process_dict,
            'model': self._process_data_model,
        }
    
    def process(self, data: Any) -> ResultModel:
        """
        Process input data and return a ResultModel.
        
        Args:
            data: Input data of any supported type
            
        Returns:
            ResultModel containing processed data and metadata
            
        Raises:
            ProcessingError: If processing fails
            ValidationError: If input validation fails
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(data):
                raise ValidationError(f"Invalid input data: {type(data)}")
            
            # Check cache if enabled
            if self.config.cache_enabled:
                cache_key = self._generate_cache_key(data)
                if cache_key in self._cache:
                    self.logger.debug(f"Returning cached result for key: {cache_key}")
                    return self._cache[cache_key]
            
            # Determine data type and process
            data_type = self._determine_data_type(data)
            processor_func = self._processors.get(data_type, self._process_generic)
            
            processed_data = processor_func(data)
            
            # Create result model
            result = ResultModel(
                success=True,
                content=processed_data,
                metadata={
                    'input_type': data_type,
                    'processor': self.__class__.__name__,
                    'processing_time': time.time() - start_time,
                    'config': self.config.to_dict()
                }
            )
            
            # Cache result if enabled
            if self.config.cache_enabled:
                self._cache[cache_key] = result
            
            self.processed_count += 1
            return result
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Processing failed: {e}")
            raise ProcessingError(f"Failed to process data: {e}")
    
    def process_data_model(self, model: DataModel) -> ResultModel:
        """
        Process a DataModel instance with specialized handling.
        
        Args:
            model: DataModel instance to process
            
        Returns:
            ResultModel with processed model data
        """
        return self.process(model)
    
    async def process_async(self, data: Any) -> ResultModel:
        """
        Asynchronously process data.
        
        Args:
            data: Input data to process
            
        Returns:
            ResultModel containing processed data
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process, data)
    
    def process_batch(self, data_list: List[Any]) -> List[ResultModel]:
        """
        Process multiple items in batch.
        
        Args:
            data_list: List of data items to process
            
        Returns:
            List of ResultModel instances
        """
        results = []
        max_items = self.config.max_items
        
        for i, data in enumerate(data_list[:max_items]):
            try:
                result = self.process(data)
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to process item {i}: {e}")
                # Add failed result
                results.append(ResultModel(
                    success=False,
                    error=str(e),
                    metadata={'item_index': i}
                ))
        
        return results
    
    def validate_input(self, data: Any) -> bool:
        """Validate input data."""
        if data is None:
            return False
        
        # Check size limits for collections
        if isinstance(data, (list, dict, str)):
            if len(data) > self.config.max_size:
                return False
        
        return True
    
    def _determine_data_type(self, data: Any) -> str:
        """Determine the type category of input data."""
        if isinstance(data, str):
            return 'string'
        elif isinstance(data, (int, float)):
            return 'number'
        elif isinstance(data, list):
            return 'list'
        elif isinstance(data, dict):
            return 'dict'
        elif isinstance(data, DataModel):
            return 'model'
        else:
            return 'generic'
    
    def _process_string(self, data: str) -> str:
        """Process string data."""
        if self.config.uppercase:
            data = data.upper()
        return f"Processed: {data}"
    
    def _process_number(self, data: Union[int, float]) -> Union[int, float]:
        """Process numeric data."""
        if self.config.multiply_factor:
            data *= self.config.multiply_factor
        return data
    
    def _process_list(self, data: List[Any]) -> List[Any]:
        """Process list data."""
        processed = []
        for item in data[:self.config.max_items]:
            if isinstance(item, str):
                processed.append(self._process_string(item))
            else:
                processed.append(item)
        return processed
    
    def _process_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dictionary data."""
        processed = {}
        for key, value in data.items():
            if isinstance(value, str):
                processed[key] = self._process_string(value)
            else:
                processed[key] = value
        return processed
    
    def _process_data_model(self, data: DataModel) -> Dict[str, Any]:
        """Process DataModel instances."""
        return {
            'name': self._process_string(data.name),
            'value': self._process_number(data.value),
            'metadata': data.metadata,
            'processed_timestamp': time.time()
        }
    
    def _process_generic(self, data: Any) -> str:
        """Generic processor for unknown data types."""
        return f"Generic processing: {str(data)}"
    
    def _generate_cache_key(self, data: Any) -> str:
        """Generate a cache key for input data."""
        return f"{type(data).__name__}_{hash(str(data))}"
    
    @timing_decorator
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'cache_size': len(self._cache),
            'success_rate': (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0 else 0.0
            )
        }
    
    def clear_cache(self) -> None:
        """Clear the processing cache."""
        self._cache.clear()
        self.logger.info("Processing cache cleared")
    
    def reset_counters(self) -> None:
        """Reset processing counters."""
        self.processed_count = 0
        self.error_count = 0
        self.logger.info("Processing counters reset")


class DataProcessor(BaseProcessor):
    """
    Specialized processor for structured data operations.
    
    This processor focuses on transforming structured data formats
    and provides utilities for data validation and conversion.
    """
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.supported_formats = ['json', 'yaml', 'xml', 'csv']
    
    def process(self, data: Any) -> Dict[str, Any]:
        """Process structured data."""
        if not self.validate_input(data):
            raise ValidationError("Invalid structured data")
        
        return {
            'original': data,
            'processed': self._transform_data(data),
            'format': self._detect_format(data),
            'timestamp': time.time()
        }
    
    def validate_input(self, data: Any) -> bool:
        """Validate structured data input."""
        return isinstance(data, (dict, list)) and len(str(data)) <= self.config.max_size
    
    def _transform_data(self, data: Any) -> Any:
        """Apply data transformations."""
        if isinstance(data, dict):
            return {k.upper() if isinstance(k, str) else k: v for k, v in data.items()}
        elif isinstance(data, list):
            return [item.upper() if isinstance(item, str) else item for item in data]
        return data
    
    def _detect_format(self, data: Any) -> str:
        """Detect the format of structured data."""
        if isinstance(data, dict):
            return 'json-like'
        elif isinstance(data, list):
            return 'array-like'
        return 'unknown'


# Factory function for creating processors
def create_processor(processor_type: str = "sample", config: Optional[Config] = None) -> BaseProcessor:
    """
    Factory function to create different types of processors.
    
    Args:
        processor_type: Type of processor to create ("sample", "data")
        config: Configuration for the processor
        
    Returns:
        Processor instance
        
    Raises:
        ValueError: If processor_type is unknown
        
    Example:
        >>> processor = create_processor("sample", Config(debug=True))
        >>> isinstance(processor, SampleProcessor)
        True
    """
    processors = {
        'sample': SampleProcessor,
        'data': DataProcessor,
    }
    
    if processor_type not in processors:
        raise ValueError(f"Unknown processor type: {processor_type}")
    
    return processors[processor_type](config)


# Convenience function for quick processing
def quick_process(data: Any, processor_type: str = "sample", **config_kwargs) -> ResultModel:
    """
    Quickly process data with default configuration.
    
    Args:
        data: Data to process
        processor_type: Type of processor to use
        **config_kwargs: Configuration options
        
    Returns:
        Processing result
    """
    config = Config(**config_kwargs)
    processor = create_processor(processor_type, config)
    return processor.process(data)
