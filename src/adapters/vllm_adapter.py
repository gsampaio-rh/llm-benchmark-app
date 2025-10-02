"""
vLLM engine adapter implementation.

This module provides the adapter for connecting to vLLM engines,
handling vLLM's OpenAI-compatible API calls and metrics parsing.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.engine_config import EngineHealthStatus, EngineInfo, ModelInfo
from ..models.metrics import ParsedMetrics, RequestResult, RawEngineMetrics
from .base_adapter import BaseAdapter, ConnectionError, ParseError, TimeoutError


logger = logging.getLogger(__name__)


class VLLMAdapter(BaseAdapter):
    """
    Adapter for vLLM LLM engine.
    
    Implements vLLM-specific API calls using OpenAI-compatible endpoints.
    vLLM API documentation: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
    """
    
    async def health_check(self) -> EngineHealthStatus:
        """
        Check vLLM engine health using the /health endpoint.
        
        Returns:
            EngineHealthStatus with health information
        """
        start_time = datetime.utcnow()
        
        try:
            # Use /health endpoint for health check
            response_data = await self._get_json(self.config.health_endpoint)
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # vLLM health endpoint typically returns simple status
            is_healthy = True
            if isinstance(response_data, dict):
                # Check for any error indicators
                if "error" in response_data or response_data.get("status") == "error":
                    is_healthy = False
            
            # Try to get version info if available
            version = None
            if isinstance(response_data, dict):
                version = response_data.get("version")
            
            return EngineHealthStatus(
                engine_name=self.config.name,
                is_healthy=is_healthy,
                response_time_ms=response_time_ms,
                engine_version=version,
                additional_info={
                    "endpoint": self.config.health_endpoint,
                    "api_type": "openai_compatible"
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
        Get detailed information about the vLLM engine.
        
        Returns:
            EngineInfo with engine details and capabilities
        """
        try:
            # Get model information from /v1/models
            models_data = await self._get_json("/v1/models")
            
            model_count = 0
            if isinstance(models_data, dict) and "data" in models_data:
                model_count = len(models_data["data"])
            
            # Try to get version info from health endpoint
            version = "unknown"
            try:
                health_data = await self._get_json("/health")
                if isinstance(health_data, dict):
                    version = health_data.get("version", "unknown")
            except Exception:
                pass  # Health endpoint might not provide version
            
            # vLLM capabilities
            capabilities = {
                "streaming": True,      # vLLM supports streaming
                "embeddings": False,    # vLLM primarily for text generation
                "chat": True,          # vLLM supports chat completion
                "completion": True,    # vLLM supports text completion
                "batching": True,      # vLLM has continuous batching
                "speculative_decoding": True,  # vLLM supports speculative decoding
            }
            
            supported_features = [
                "text_generation",
                "streaming_generation", 
                "chat_completion",
                "continuous_batching",
                "speculative_decoding",
                "openai_compatible_api"
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
                        "completions": "/v1/completions",
                        "chat": "/v1/chat/completions", 
                        "models": "/v1/models",
                        "health": "/health"
                    },
                    "api_compatibility": "openai"
                }
            )
            
        except Exception as e:
            raise ConnectionError(f"Failed to get engine info: {e}")
    
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models from vLLM.
        
        Returns:
            List of ModelInfo objects
        """
        try:
            # Get models from /v1/models (OpenAI-compatible endpoint)
            models_data = await self._get_json("/v1/models")
            
            models = []
            if isinstance(models_data, dict) and "data" in models_data:
                for model_data in models_data["data"]:
                    # Extract model information
                    model_id = model_data.get("id", "unknown")
                    created = model_data.get("created")
                    owned_by = model_data.get("owned_by", "vllm")
                    
                    # Try to extract model family from ID
                    family = None
                    if "/" in model_id:
                        # Handle HuggingFace model names like "microsoft/DialoGPT-medium"
                        family = model_id.split("/")[0]
                    elif "-" in model_id:
                        # Handle names like "llama2-7b"
                        family = model_id.split("-")[0]
                    
                    model_info = ModelInfo(
                        name=model_id,
                        engine_name=self.config.name,
                        family=family,
                        is_available=True,
                        additional_info={
                            "created": created,
                            "owned_by": owned_by,
                            "object": model_data.get("object", "model"),
                            "permission": model_data.get("permission", [])
                        }
                    )
                    models.append(model_info)
            
            self.logger.info(f"Found {len(models)} models in vLLM")
            return models
            
        except Exception as e:
            raise ConnectionError(f"Failed to list models: {e}")
    
    async def send_single_request(self, prompt: str, model: str, **kwargs) -> RequestResult:
        """
        Send a single generation request to vLLM using OpenAI-compatible API.
        
        Args:
            prompt: Input prompt text
            model: Model name to use
            **kwargs: Additional parameters (stream, temperature, etc.)
            
        Returns:
            RequestResult with response and metrics
        """
        request_start = datetime.utcnow()
        
        try:
            # Determine if this should be a chat completion or text completion
            use_chat = kwargs.get("use_chat", False)
            
            if use_chat:
                # Use chat completions endpoint
                request_data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": kwargs.get("stream", False),
                }
                endpoint = "/v1/chat/completions"
            else:
                # Use completions endpoint
                request_data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": kwargs.get("stream", False),
                }
                endpoint = "/v1/completions"
            
            # Add optional parameters
            if "temperature" in kwargs:
                request_data["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                request_data["max_tokens"] = kwargs["max_tokens"]
            if "top_p" in kwargs:
                request_data["top_p"] = kwargs["top_p"]
            if "frequency_penalty" in kwargs:
                request_data["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                request_data["presence_penalty"] = kwargs["presence_penalty"]
            
            # Send request
            response_data = await self._post_json(endpoint, request_data)
            
            request_end = datetime.utcnow()
            request_duration_ms = (request_end - request_start).total_seconds() * 1000
            
            # Extract response text based on endpoint used
            response_text = ""
            if use_chat:
                # Chat completion response format
                if "choices" in response_data and response_data["choices"]:
                    choice = response_data["choices"][0]
                    if "message" in choice:
                        response_text = choice["message"].get("content", "")
            else:
                # Text completion response format
                if "choices" in response_data and response_data["choices"]:
                    choice = response_data["choices"][0]
                    response_text = choice.get("text", "")
            
            # Check if request was successful
            if "error" in response_data:
                return RequestResult.error_result(
                    engine_name=self.config.name,
                    model_name=model,
                    prompt=prompt,
                    error_message=response_data["error"].get("message", "Unknown error")
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
            parsed_metrics = self.parse_metrics(response_data, request_start)
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
    
    def parse_metrics(self, raw_response: Dict[str, Any], request_start: datetime) -> ParsedMetrics:
        """
        Parse vLLM-specific metrics from raw response.
        
        vLLM uses OpenAI-compatible format, so metrics are limited compared to Ollama.
        We extract what we can from the usage field and calculate timing.
        
        Args:
            raw_response: Raw response data from vLLM
            request_start: When the request started
            
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
            
            # Parse usage information if available
            usage = raw_response.get("usage", {})
            if usage:
                # OpenAI format provides token counts
                metrics.prompt_eval_count = usage.get("prompt_tokens")
                metrics.eval_count = usage.get("completion_tokens")
                
                # Total tokens is usually prompt + completion
                total_tokens = usage.get("total_tokens")
                if total_tokens and metrics.prompt_eval_count and metrics.eval_count:
                    # Verify total matches sum
                    expected_total = metrics.prompt_eval_count + metrics.eval_count
                    if abs(total_tokens - expected_total) > 1:
                        self.logger.warning(f"Token count mismatch: {total_tokens} vs {expected_total}")
            
            # Calculate total duration from request timing
            request_end = datetime.utcnow()
            metrics.total_duration = (request_end - request_start).total_seconds()
            
            # Set completion time
            metrics.completion_time = request_end
            
            # vLLM doesn't provide detailed timing like Ollama, so we estimate
            # Assume most time is spent on generation
            if metrics.total_duration and metrics.eval_count:
                # Rough estimate: 80% of time on generation, 20% on prompt processing
                metrics.eval_duration = metrics.total_duration * 0.8
                metrics.prompt_eval_duration = metrics.total_duration * 0.2
            
            # Calculate derived metrics
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
            # vLLM doesn't have a specific model info endpoint like Ollama
            # We can get basic info from the models list
            models_data = await self._get_json("/v1/models")
            
            if isinstance(models_data, dict) and "data" in models_data:
                for model_data in models_data["data"]:
                    if model_data.get("id") == model_name:
                        return model_data
            
            return None
            
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
