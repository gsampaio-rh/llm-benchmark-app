"""
Configuration management for the benchmarking tool.

This module handles loading, validating, and managing configuration files
with support for YAML files and environment variable overrides.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
import yaml
from pydantic import ValidationError

from ..models.engine_config import BenchmarkConfig, EngineConfig


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files.
                       Defaults to ./configs relative to project root.
        """
        if config_dir is None:
            # Default to configs directory relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "configs"
        
        self.config_dir = Path(config_dir)
        self.engines_dir = self.config_dir / "engines"
        self.scenarios_dir = self.config_dir / "scenarios"
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.engines_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
    
    def load_engine_config(self, config_file: Union[str, Path]) -> EngineConfig:
        """
        Load and validate a single engine configuration.
        
        Args:
            config_file: Path to the engine configuration file
            
        Returns:
            Validated EngineConfig instance
            
        Raises:
            ConfigurationError: If loading or validation fails
        """
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = self.engines_dir / config_path
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ConfigurationError(f"Empty configuration file: {config_path}")
            
            # Apply environment variable overrides
            config_data = self._apply_env_overrides(config_data)
            
            # Validate and create EngineConfig
            engine_config = EngineConfig(**config_data)
            logger.info(f"Loaded engine configuration: {engine_config}")
            return engine_config
            
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Invalid configuration in {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration {config_path}: {e}")
    
    def load_all_engine_configs(self) -> list[EngineConfig]:
        """
        Load all engine configurations from the engines directory.
        
        Returns:
            List of validated EngineConfig instances
            
        Raises:
            ConfigurationError: If any configuration fails to load
        """
        engine_configs = []
        
        if not self.engines_dir.exists():
            logger.warning(f"Engines directory does not exist: {self.engines_dir}")
            return engine_configs
        
        yaml_files = list(self.engines_dir.glob("*.yaml")) + list(self.engines_dir.glob("*.yml"))
        
        if not yaml_files:
            logger.warning(f"No YAML configuration files found in {self.engines_dir}")
            return engine_configs
        
        for config_file in yaml_files:
            try:
                engine_config = self.load_engine_config(config_file)
                engine_configs.append(engine_config)
            except ConfigurationError as e:
                logger.error(f"Failed to load {config_file}: {e}")
                # Continue loading other configs, but collect errors
                raise
        
        return engine_configs
    
    def load_benchmark_config(self, config_file: Optional[Union[str, Path]] = None) -> BenchmarkConfig:
        """
        Load the main benchmark configuration.
        
        Args:
            config_file: Path to benchmark config file. If None, loads all engine configs.
            
        Returns:
            Validated BenchmarkConfig instance
            
        Raises:
            ConfigurationError: If loading or validation fails
        """
        if config_file:
            # Load from specific file
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = self.config_dir / config_path
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                config_data = self._apply_env_overrides(config_data)
                return BenchmarkConfig(**config_data)
                
            except Exception as e:
                raise ConfigurationError(f"Error loading benchmark config {config_path}: {e}")
        else:
            # Load all engine configs and create benchmark config
            engine_configs = self.load_all_engine_configs()
            
            benchmark_config_data = {
                "engines": [config.model_dump() for config in engine_configs],
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "output_directory": os.getenv("OUTPUT_DIR", "./benchmark_results"),
                "export_format": os.getenv("EXPORT_FORMAT", "json")
            }
            
            return BenchmarkConfig(**benchmark_config_data)
    
    def save_engine_config(self, engine_config: EngineConfig, filename: Optional[str] = None) -> Path:
        """
        Save an engine configuration to a YAML file.
        
        Args:
            engine_config: EngineConfig instance to save
            filename: Optional filename. Defaults to {engine_name}.yaml
            
        Returns:
            Path to the saved configuration file
        """
        if filename is None:
            filename = f"{engine_config.name}.yaml"
        
        config_path = self.engines_dir / filename
        
        # Convert to dict and remove None values for cleaner YAML
        config_dict = engine_config.model_dump(exclude_none=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Saved engine configuration to {config_path}")
            return config_path
            
        except Exception as e:
            raise ConfigurationError(f"Error saving configuration to {config_path}: {e}")
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration data.
        
        Environment variables should be prefixed with BENCHMARK_ and use
        double underscores to separate nested keys.
        
        Example: BENCHMARK_BASE_URL=http://localhost:8080
                BENCHMARK_TIMEOUT=600
        """
        env_prefix = "BENCHMARK_"
        
        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue
            
            # Remove prefix and convert to lowercase
            config_key = key[len(env_prefix):].lower()
            
            # Handle nested keys (double underscore separator)
            if "__" in config_key:
                # For now, only support one level of nesting
                parts = config_key.split("__", 1)
                if len(parts) == 2:
                    parent_key, child_key = parts
                    if parent_key in config_data and isinstance(config_data[parent_key], dict):
                        config_data[parent_key][child_key] = self._convert_env_value(value)
            else:
                config_data[config_key] = self._convert_env_value(value)
        
        return config_data
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type."""
        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def create_default_configs(self) -> None:
        """Create default configuration files if they don't exist."""
        default_configs = [
            {
                "filename": "ollama.yaml",
                "config": EngineConfig(
                    name="ollama",
                    engine_type="ollama",
                    base_url="http://localhost:11434",
                    health_endpoint="/api/tags",
                    models_endpoint="/api/tags",
                    timeout=300
                )
            },
            {
                "filename": "vllm.yaml", 
                "config": EngineConfig(
                    name="vllm",
                    engine_type="vllm",
                    base_url="http://localhost:8000",
                    health_endpoint="/health",
                    models_endpoint="/v1/models",
                    timeout=300
                )
            },
            {
                "filename": "tgi.yaml",
                "config": EngineConfig(
                    name="tgi",
                    engine_type="tgi",
                    base_url="http://localhost:8080",
                    health_endpoint="/health",
                    models_endpoint="/info",
                    timeout=300
                )
            }
        ]
        
        for config_info in default_configs:
            config_path = self.engines_dir / config_info["filename"]
            if not config_path.exists():
                self.save_engine_config(config_info["config"], config_info["filename"])
                logger.info(f"Created default configuration: {config_path}")


# Global config manager instance
config_manager = ConfigManager()

