"""
Ollama engine adapter implementation.

This module provides the adapter for connecting to Ollama engines,
handling Ollama-specific API calls and metrics parsing.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..models.engine_config import EngineHealthStatus, EngineInfo, ModelInfo
from ..models.metrics import ParsedMetrics, RequestResult, RawEngineMetrics
from .base_adapter import BaseAdapter, ConnectionError, ParseError, TimeoutError


logger = logging.getLogger(__name__)


class OllamaAdapter(BaseAdapter):
    """
    Adapter for Ollama LLM engine.
    
    Implements Ollama-specific API calls and metrics parsing.
    Ollama API documentation: https://github.com/ollama/ollama/blob/main/docs/api.md
    """
    
    async def health_check(self) -> EngineHealthStatus:
        """
        Check Ollama engine health using the /api/tags endpoint.
        
        Returns:
            EngineHealthStatus with health information
        """
        start_time = datetime.utcnow()
        
        try:
            # Use /api/tags as health check - it's lightweight and always available
            response_data = await self._get_json(self.config.health_endpoint)
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Check if response has expected structure
            if not isinstance(response_data, dict) or "models" not in response_data:
                return EngineHealthStatus(
                    engine_name=self.config.name,
                    is_healthy=False,
                    response_time_ms=response_time_ms,
                    error_message="Invalid response format from Ollama"
                )
            
            # Extract version if available
            version = None
            if isinstance(response_data.get("models"), list) and response_data["models"]:
                # Try to get version from first model or other sources
                # Ollama doesn't always provide version in /api/tags
                pass
            
            return EngineHealthStatus(
                engine_name=self.config.name,
                is_healthy=True,
                response_time_ms=response_time_ms,
                engine_version=version,
                additional_info={
                    "model_count": len(response_data.get("models", [])),
                    "endpoint": self.config.health_endpoint
                }
            )
            
        except (ConnectionError, TimeoutError) as e:
            return EngineHealthStatus(
                engine_name=self.config.name,
                is_healthy=False,
                error_message=str(e)
            )
        except Exception as e:
            self.logger.error(f"Unexpected error during health check: {e}")
            return EngineHealthStatus(
                engine_name=self.config.name,
                is_healthy=False,
                error_message=f"Health check failed: {e}"
            )
    
    async def get_engine_info(self) -> EngineInfo:
        """
        Get detailed information about the Ollama engine.
        
        Returns:
            EngineInfo with engine details and capabilities
        """
        try:
            # Get model information from /api/tags
            tags_data = await self._get_json("/api/tags")
            
            models = tags_data.get("models", [])
            model_count = len(models)
            
            # Try to get version info (Ollama doesn't have a dedicated version endpoint)
            version = "unknown"
            
            # Extract capabilities and features
            capabilities = {
                "streaming": True,  # Ollama supports streaming
                "embeddings": True,  # Ollama supports embeddings
                "chat": True,       # Ollama supports chat format
                "completion": True, # Ollama supports completion format
            }
            
            supported_features = [
                "text_generation",
                "streaming_generation", 
                "model_management",
                "embeddings",
                "chat_completion"
            ]
            
            return EngineInfo(
                engine_name=self.config.name,
                engine_type=self.config.engine_type,
                version=version,
                capabilities=capabilities,
                supported_features=supported_features,
                model_count=model_count,
                additional_info={
                    "base_url": str(self.config.base_url),
                    "api_endpoints": {
                        "generate": "/api/generate",
                        "chat": "/api/chat", 
                        "tags": "/api/tags",
                        "show": "/api/show",
                        "embeddings": "/api/embeddings"
                    }
                }
            )
            
        except Exception as e:
            raise ConnectionError(f"Failed to get engine info: {e}")
    
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models from Ollama.
        
        Returns:
            List of ModelInfo objects
        """
        try:
            # Get models from /api/tags
            tags_data = await self._get_json("/api/tags")
            models_data = tags_data.get("models", [])
            
            models = []
            for model_data in models_data:
                # Extract model information
                name = model_data.get("name", "unknown")
                size = model_data.get("size")
                modified_at = model_data.get("modified_at")
                
                # Try to extract model family from name (e.g., "llama2:7b" -> "llama2")
                family = None
                if ":" in name:
                    family = name.split(":")[0]
                
                # Convert size to human-readable format if it's a number
                size_str = None
                if isinstance(size, int):
                    # Convert bytes to human-readable format
                    for unit in ['B', 'KB', 'MB', 'GB']:
                        if size < 1024.0:
                            size_str = f"{size:.1f}{unit}"
                            break
                        size /= 1024.0
                    else:
                        size_str = f"{size:.1f}TB"
                
                model_info = ModelInfo(
                    name=name,
                    engine_name=self.config.name,
                    size=size_str,
                    family=family,
                    is_available=True,
                    additional_info={
                        "modified_at": modified_at,
                        "raw_size": size,
                        "digest": model_data.get("digest"),
                        "details": model_data.get("details", {})
                    }
                )
                models.append(model_info)
            
            self.logger.info(f"Found {len(models)} models in Ollama")
            return models
            
        except Exception as e:
            raise ConnectionError(f"Failed to list models: {e}")
    
    async def send_single_request(self, prompt: str, model: str, **kwargs) -> RequestResult:
        """
        Send a single generation request to Ollama.
        
        Args:
            prompt: Input prompt text
            model: Model name to use
            **kwargs: Additional parameters (stream, temperature, etc.)
            
        Returns:
            RequestResult with response and metrics
        """
        request_start = datetime.utcnow()
        first_token_time = None
        
        try:
            # Prepare request data
            request_data = {
                "model": model,
                "prompt": prompt,
                "stream": kwargs.get("stream", False),  # Default to non-streaming
                "options": {}
            }
            
            # Add optional parameters
            if "temperature" in kwargs:
                request_data["options"]["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                request_data["options"]["num_predict"] = kwargs["max_tokens"]
            if "top_p" in kwargs:
                request_data["options"]["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                request_data["options"]["top_k"] = kwargs["top_k"]
            
            # Send request to /api/generate
            # For non-streaming, we can't capture first token time precisely
            # but we can estimate it from the response timing
            response_data = await self._post_json("/api/generate", request_data)
            
            request_end = datetime.utcnow()
            request_duration_ms = (request_end - request_start).total_seconds() * 1000
            
            # Estimate first token time based on Ollama metrics
            # First token typically comes after prompt processing + small generation delay
            if "prompt_eval_duration" in response_data:
                # Convert nanoseconds to seconds and add small generation delay
                prompt_eval_seconds = response_data["prompt_eval_duration"] * 1e-9
                # Estimate first token comes ~100ms after prompt processing
                first_token_time = request_start + timedelta(seconds=prompt_eval_seconds + 0.1)
            
            # Extract response text
            response_text = response_data.get("response", "")
            
            # Check if request was successful
            if "error" in response_data:
                return RequestResult.error_result(
                    engine_name=self.config.name,
                    model_name=model,
                    prompt=prompt,
                    error_message=response_data["error"]
                )
            
            # Create raw metrics
            raw_metrics = self._create_raw_metrics(
                prompt=prompt,
                response=response_text,
                model_name=model,
                raw_response=response_data,
                request_duration_ms=request_duration_ms
            )
            
            # Parse metrics
            parsed_metrics = self.parse_metrics(response_data, request_start, first_token_time)
            parsed_metrics.request_id = raw_metrics.request_id
            
            return RequestResult.success_result(
                engine_name=self.config.name,
                model_name=model,
                prompt=prompt,
                response=response_text,
                raw_metrics=raw_metrics,
                parsed_metrics=parsed_metrics
            )
            
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return RequestResult.error_result(
                engine_name=self.config.name,
                model_name=model,
                prompt=prompt,
                error_message=str(e)
            )
    
    def parse_metrics(self, raw_response: Dict[str, Any], request_start: datetime, first_token_time: Optional[datetime] = None) -> ParsedMetrics:
        """
        Parse Ollama-specific metrics from raw response.
        
        Ollama returns metrics in nanoseconds, we convert to seconds.
        
        Args:
            raw_response: Raw response data from Ollama
            request_start: When the request started
            first_token_time: When the first token was received (estimated)
            
        Returns:
            ParsedMetrics with standardized metrics
        """
        try:
            # Create base metrics object
            metrics = ParsedMetrics(
                request_id="",  # Will be set by caller
                engine_name=self.config.name,
                engine_type=self.config.engine_type,
                model_name=raw_response.get("model", "unknown"),
                timestamp=request_start,
                success=True
            )
            
            # Parse Ollama-specific timing metrics (all in nanoseconds)
            # Convert nanoseconds to seconds for standardization
            NS_TO_SECONDS = 1e-9
            
            if "load_duration" in raw_response:
                metrics.load_duration = raw_response["load_duration"] * NS_TO_SECONDS
            
            if "prompt_eval_count" in raw_response:
                metrics.prompt_eval_count = raw_response["prompt_eval_count"]
            
            if "prompt_eval_duration" in raw_response:
                metrics.prompt_eval_duration = raw_response["prompt_eval_duration"] * NS_TO_SECONDS
            
            if "eval_count" in raw_response:
                metrics.eval_count = raw_response["eval_count"]
            
            if "eval_duration" in raw_response:
                metrics.eval_duration = raw_response["eval_duration"] * NS_TO_SECONDS
            
            if "total_duration" in raw_response:
                metrics.total_duration = raw_response["total_duration"] * NS_TO_SECONDS
            
            # Set timing information
            if metrics.total_duration:
                metrics.completion_time = request_start + timedelta(seconds=metrics.total_duration)
            
            # Set first token timing
            if first_token_time:
                metrics.first_token_time = first_token_time
                metrics.request_start = request_start
                # Calculate first token latency
                metrics.first_token_latency = (first_token_time - request_start).total_seconds()
            
            # Calculate derived metrics (this will calculate token rates and inter-token latency)
            metrics.calculate_derived_metrics()
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to parse metrics: {e}")
            # Return basic metrics on parse failure
            model_name = "unknown"
            if raw_response and isinstance(raw_response, dict):
                model_name = raw_response.get("model", "unknown")
            
            return ParsedMetrics(
                request_id="",
                engine_name=self.config.name,
                engine_type=self.config.engine_type,
                model_name=model_name,
                timestamp=request_start,
                success=False,
                error_message=f"Metrics parsing failed: {e}"
            )
    
    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information dictionary or None if not found
        """
        try:
            # Use /api/show endpoint to get model details
            request_data = {"name": model_name}
            model_data = await self._post_json("/api/show", request_data)
            
            return model_data
            
        except Exception as e:
            self.logger.warning(f"Failed to get model info for {model_name}: {e}")
            return None
    
    async def check_model_availability(self, model_name: str) -> bool:
        """
        Check if a specific model is available.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available, False otherwise
        """
        try:
            models = await self.list_models()
            available_names = [model.name for model in models]
            return model_name in available_names
            
        except Exception as e:
            self.logger.error(f"Failed to check model availability: {e}")
            return False
