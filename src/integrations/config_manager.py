"""
Configuration management with dependency injection support.

This module provides comprehensive configuration management capabilities
with support for multiple sources, validation, and dependency injection.
"""

import os
import yaml
from typing import Dict, Any, Optional, List, Union, Type, TypeVar
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import BenchmarkConfig, load_config as original_load_config


T = TypeVar('T')


@dataclass
class ConfigSource:
    """Configuration source descriptor"""
    source_type: str  # "file", "env", "dict", "remote"
    location: str
    priority: int = 100  # Higher priority overrides lower
    required: bool = False


@dataclass
class ConfigurationContext:
    """Configuration context for dependency injection"""
    config: BenchmarkConfig
    sources: List[ConfigSource] = field(default_factory=list)
    overrides: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigProvider(ABC):
    """Abstract configuration provider"""
    
    @abstractmethod
    async def load_config(self, source: ConfigSource) -> Dict[str, Any]:
        """Load configuration from source"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration"""
        pass


class FileConfigProvider(ConfigProvider):
    """File-based configuration provider"""
    
    async def load_config(self, source: ConfigSource) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file"""
        file_path = Path(source.location)
        
        if not file_path.exists():
            if source.required:
                raise ConfigurationError(f"Required config file not found: {source.location}")
            return {}
        
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    import json
                    return json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported config file format: {file_path.suffix}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config file {source.location}: {str(e)}")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Basic validation for file configs"""
        return isinstance(config, dict)


class EnvironmentConfigProvider(ConfigProvider):
    """Environment variable configuration provider"""
    
    def __init__(self, prefix: str = "VLLM_BENCHMARK_"):
        """Initialize with environment variable prefix
        
        Args:
            prefix: Prefix for environment variables
        """
        self.prefix = prefix
    
    async def load_config(self, source: ConfigSource) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Convert VLLM_BENCHMARK_SERVICES_NAMESPACE to services.namespace
                config_key = key[len(self.prefix):].lower().replace('_', '.')
                config = self._set_nested_key(config, config_key, value)
        
        return config
    
    def _set_nested_key(self, config: Dict[str, Any], key_path: str, value: str) -> Dict[str, Any]:
        """Set a nested key in the config dictionary"""
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Try to convert value to appropriate type
        final_key = keys[-1]
        current[final_key] = self._convert_value(value)
        
        return config
    
    def _convert_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert string value to appropriate type"""
        # Boolean conversion
        if value.lower() in ['true', 'yes', '1']:
            return True
        elif value.lower() in ['false', 'no', '0']:
            return False
        
        # Numeric conversion
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate environment config"""
        return isinstance(config, dict)


class DictConfigProvider(ConfigProvider):
    """Dictionary-based configuration provider"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize with configuration dictionary
        
        Args:
            config_dict: Configuration dictionary
        """
        self.config_dict = config_dict
    
    async def load_config(self, source: ConfigSource) -> Dict[str, Any]:
        """Return the stored configuration dictionary"""
        return self.config_dict.copy()
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate dictionary config"""
        return isinstance(config, dict)


class ConfigurationManager:
    """Comprehensive configuration management with dependency injection"""
    
    def __init__(self):
        """Initialize the configuration manager"""
        self.providers: Dict[str, ConfigProvider] = {
            "file": FileConfigProvider(),
            "env": EnvironmentConfigProvider(),
            "dict": DictConfigProvider({})
        }
        self._cached_context: Optional[ConfigurationContext] = None
    
    def register_provider(self, source_type: str, provider: ConfigProvider):
        """Register a custom configuration provider
        
        Args:
            source_type: Type identifier for the provider
            provider: Configuration provider instance
        """
        self.providers[source_type] = provider
    
    async def load_configuration(self, sources: List[ConfigSource],
                                overrides: Optional[Dict[str, Any]] = None) -> ConfigurationContext:
        """Load configuration from multiple sources with priority handling
        
        Args:
            sources: List of configuration sources
            overrides: Optional configuration overrides
            
        Returns:
            Configuration context with merged configuration
        """
        # Sort sources by priority (higher priority first)
        sorted_sources = sorted(sources, key=lambda x: x.priority, reverse=True)
        
        merged_config = {}
        loaded_sources = []
        
        # Load from each source
        for source in sorted_sources:
            if source.source_type not in self.providers:
                if source.required:
                    raise ConfigurationError(f"No provider for source type: {source.source_type}")
                continue
            
            try:
                provider = self.providers[source.source_type]
                source_config = await provider.load_config(source)
                
                if provider.validate_config(source_config):
                    # Merge with lower priority configs
                    merged_config = self._deep_merge(source_config, merged_config)
                    loaded_sources.append(source)
                else:
                    if source.required:
                        raise ConfigurationError(f"Invalid configuration from source: {source.location}")
            
            except Exception as e:
                if source.required:
                    raise
                # Log warning for optional sources
                print(f"Warning: Failed to load optional config source {source.location}: {e}")
        
        # Apply overrides
        if overrides:
            merged_config = self._deep_merge(overrides, merged_config)
        
        # Convert to BenchmarkConfig
        try:
            # Use existing config loading logic as fallback
            if not merged_config:
                benchmark_config = original_load_config(None)  # Load default
            else:
                # Create temporary file for loading
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    yaml.dump(merged_config, f)
                    temp_path = f.name
                
                try:
                    benchmark_config = original_load_config(temp_path)
                finally:
                    os.unlink(temp_path)
        
        except Exception as e:
            raise ConfigurationError(f"Failed to create BenchmarkConfig: {str(e)}")
        
        context = ConfigurationContext(
            config=benchmark_config,
            sources=loaded_sources,
            overrides=overrides or {},
            metadata={
                "load_time": "now",
                "source_count": len(loaded_sources)
            }
        )
        
        # Cache the context
        self._cached_context = context
        
        return context
    
    def _deep_merge(self, source: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with source taking priority
        
        Args:
            source: Source dictionary (higher priority)
            target: Target dictionary (lower priority)
            
        Returns:
            Merged dictionary
        """
        result = target.copy()
        
        for key, value in source.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(value, result[key])
            else:
                result[key] = value
        
        return result
    
    async def create_default_context(self, config_file: Optional[str] = None) -> ConfigurationContext:
        """Create a default configuration context
        
        Args:
            config_file: Optional configuration file path
            
        Returns:
            Default configuration context
        """
        sources = []
        
        # Add default config file sources
        default_paths = [
            "config/default.yaml",
            "config/quick-test.yaml",
            os.path.expanduser("~/.vllm-benchmark.yaml")
        ]
        
        if config_file:
            default_paths.insert(0, config_file)
        
        for i, path in enumerate(default_paths):
            sources.append(ConfigSource(
                source_type="file",
                location=path,
                priority=100 - i,  # First file has highest priority
                required=(i == 0 and config_file is not None)  # Only required if explicitly specified
            ))
        
        # Add environment variables
        sources.append(ConfigSource(
            source_type="env",
            location="environment",
            priority=200,  # Environment has highest priority
            required=False
        ))
        
        return await self.load_configuration(sources)
    
    def get_cached_context(self) -> Optional[ConfigurationContext]:
        """Get cached configuration context
        
        Returns:
            Cached context or None if not available
        """
        return self._cached_context
    
    async def reload_configuration(self) -> Optional[ConfigurationContext]:
        """Reload configuration from cached sources
        
        Returns:
            Reloaded configuration context or None if no cache
        """
        if not self._cached_context:
            return None
        
        return await self.load_configuration(
            self._cached_context.sources,
            self._cached_context.overrides
        )
    
    def create_dependency_injector(self, context: ConfigurationContext) -> 'DependencyInjector':
        """Create a dependency injector with the configuration context
        
        Args:
            context: Configuration context
            
        Returns:
            Dependency injector instance
        """
        return DependencyInjector(context)


class DependencyInjector:
    """Simple dependency injection container"""
    
    def __init__(self, config_context: ConfigurationContext):
        """Initialize with configuration context
        
        Args:
            config_context: Configuration context
        """
        self.config_context = config_context
        self._instances: Dict[Type, Any] = {}
        self._factories: Dict[Type, callable] = {}
    
    def register_instance(self, interface: Type[T], instance: T):
        """Register a singleton instance
        
        Args:
            interface: Interface or class type
            instance: Instance to register
        """
        self._instances[interface] = instance
    
    def register_factory(self, interface: Type[T], factory: callable):
        """Register a factory function
        
        Args:
            interface: Interface or class type
            factory: Factory function that creates instances
        """
        self._factories[interface] = factory
    
    def get(self, interface: Type[T]) -> T:
        """Get an instance of the requested type
        
        Args:
            interface: Interface or class type to get
            
        Returns:
            Instance of the requested type
        """
        # Check for registered instance
        if interface in self._instances:
            return self._instances[interface]
        
        # Check for registered factory
        if interface in self._factories:
            factory = self._factories[interface]
            instance = factory(self.config_context)
            self._instances[interface] = instance  # Cache as singleton
            return instance
        
        # Try to create default instance
        try:
            if hasattr(interface, '__init__'):
                instance = interface()
                self._instances[interface] = instance
                return instance
        except Exception:
            pass
        
        raise DependencyError(f"No registration found for type: {interface}")


# Custom Exceptions
class ConfigurationError(Exception):
    """Raised when there's a configuration error"""
    pass


class DependencyError(Exception):
    """Raised when dependency injection fails"""
    pass
