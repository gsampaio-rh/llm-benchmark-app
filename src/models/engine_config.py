"""
Engine configuration models for the benchmarking tool.

This module defines Pydantic models for validating and managing
engine connection configurations.
"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, HttpUrl, Field, ConfigDict


class EngineConfig(BaseModel):
    """Configuration for a single LLM engine."""
    
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    
    name: str = Field(..., description="Unique name for this engine instance")
    engine_type: Literal["ollama", "vllm", "tgi"] = Field(
        ..., description="Type of engine (ollama, vllm, or tgi)"
    )
    base_url: HttpUrl = Field(..., description="Base URL for the engine API")
    timeout: int = Field(
        default=300, 
        ge=1, 
        le=3600, 
        description="Request timeout in seconds"
    )
    health_endpoint: str = Field(
        ..., description="Endpoint path for health checks"
    )
    models_endpoint: Optional[str] = Field(
        default=None, description="Endpoint path for model discovery"
    )
    auth_token: Optional[str] = Field(
        default=None, description="Authentication token if required"
    )
    custom_headers: Optional[Dict[str, str]] = Field(
        default=None, description="Custom HTTP headers to include in requests"
    )
    retry_attempts: int = Field(
        default=3, 
        ge=0, 
        le=10, 
        description="Number of retry attempts for failed requests"
    )
    retry_delay: float = Field(
        default=1.0, 
        ge=0.1, 
        le=60.0, 
        description="Delay between retry attempts in seconds"
    )
    
    def __str__(self) -> str:
        """String representation of the engine config."""
        return f"{self.name} ({self.engine_type}) @ {self.base_url}"


class EngineHealthStatus(BaseModel):
    """Health status information for an engine."""
    
    model_config = ConfigDict(extra='allow')
    
    engine_name: str = Field(..., description="Name of the engine")
    is_healthy: bool = Field(..., description="Whether the engine is healthy")
    response_time_ms: Optional[float] = Field(
        default=None, description="Health check response time in milliseconds"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if unhealthy"
    )
    engine_version: Optional[str] = Field(
        default=None, description="Engine version if available"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional engine-specific information"
    )


class EngineInfo(BaseModel):
    """Detailed information about an engine."""
    
    model_config = ConfigDict(extra='allow')
    
    engine_name: str = Field(..., description="Name of the engine")
    engine_type: str = Field(..., description="Type of engine")
    version: Optional[str] = Field(default=None, description="Engine version")
    capabilities: Optional[Dict[str, Any]] = Field(
        default=None, description="Engine capabilities and features"
    )
    supported_features: Optional[list[str]] = Field(
        default=None, description="List of supported features"
    )
    model_count: Optional[int] = Field(
        default=None, description="Number of available models"
    )
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional engine-specific information"
    )


class ModelInfo(BaseModel):
    """Information about a specific model."""
    
    model_config = ConfigDict(extra='allow')
    
    name: str = Field(..., description="Model name/identifier")
    engine_name: str = Field(..., description="Engine hosting this model")
    size: Optional[str] = Field(default=None, description="Model size (e.g., '7B', '13B')")
    family: Optional[str] = Field(default=None, description="Model family (e.g., 'llama2', 'mistral')")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Model parameters and configuration"
    )
    context_length: Optional[int] = Field(
        default=None, description="Maximum context length in tokens"
    )
    is_available: bool = Field(default=True, description="Whether the model is currently available")
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional model-specific information"
    )


class BenchmarkConfig(BaseModel):
    """Overall configuration for benchmarking runs."""
    
    model_config = ConfigDict(extra='forbid')
    
    engines: list[EngineConfig] = Field(..., description="List of engine configurations")
    default_model: Optional[str] = Field(
        default=None, description="Default model to use for testing"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )
    output_directory: str = Field(
        default="./benchmark_results", description="Directory for output files"
    )
    export_format: Literal["json", "csv", "both"] = Field(
        default="json", description="Default export format for results"
    )
    
    def get_engine_by_name(self, name: str) -> Optional[EngineConfig]:
        """Get engine configuration by name."""
        for engine in self.engines:
            if engine.name == name:
                return engine
        return None
    
    def get_engines_by_type(self, engine_type: str) -> list[EngineConfig]:
        """Get all engines of a specific type."""
        return [engine for engine in self.engines if engine.engine_type == engine_type]

