"""
TGI (Text Generation Inference) engine adapter implementation.

This module provides the adapter for connecting to HuggingFace TGI engines,
handling TGI-specific API calls and metrics parsing.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.engine_config import EngineHealthStatus, EngineInfo, ModelInfo
from ..models.metrics import ParsedMetrics, RequestResult, RawEngineMetrics
from .base_adapter import BaseAdapter, ConnectionError, ParseError, TimeoutError


logger = logging.getLogger(__name__)


class TGIAdapter(BaseAdapter):
    """
    Adapter for HuggingFace Text Generation Inference (TGI) engine.
    
    Implements TGI-specific API calls and metrics parsing.
    TGI API documentation: https://huggingface.co/docs/text-generation-inference/
    """
    
    async def health_check(self) -> EngineHealthStatus:
        """
        Check TGI engine health using the /health endpoint.
        
        TGI's /health endpoint may return:
        - Empty response with 200 OK (healthy)
        - JSON response with status information
        - Error status codes for unhealthy state
        
        Returns:
            EngineHealthStatus with health information
        """
        start_time = datetime.utcnow()
        
        try:
            # Use helper method to handle both JSON and non-JSON responses
            response, response_data = await self._get_with_optional_json(self.config.health_endpoint)
            
            end_time = datetime.utcnow()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # TGI health endpoint returns 200 OK when healthy
            is_healthy = response.status_code == 200
            
            # Process JSON response if available
            version = None
            additional_info = {
                "endpoint": self.config.health_endpoint,
                "api_type": "tgi_native",
                "status_code": response.status_code
            }
            
            if response_data:
                # Check for any error indicators in JSON
                if "error" in response_data:
                    is_healthy = False
                version = response_data.get("version")
                additional_info["response_data"] = response_data
            elif response.text.strip():
                # Non-JSON response with content
                additional_info["response_type"] = "non_json"
                additional_info["response_text"] = response.text[:100]  # First 100 chars for debugging
            else:
                # Empty response is normal for TGI health endpoint
                additional_info["response_type"] = "empty_body"
            
            return EngineHealthStatus(
                engine_name=self.config.name,
                is_healthy=is_healthy,
                response_time_ms=response_time_ms,
                engine_version=version,
                additional_info=additional_info
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
        Get detailed information about the TGI engine.
        
        Returns:
            EngineInfo with engine details and capabilities
        """
        try:
            # Get engine information from /info endpoint
            info_data = await self._get_json("/info")
            
            # Extract version and model info
            version = info_data.get("version", "unknown")
            model_id = info_data.get("model_id", "unknown")
            model_dtype = info_data.get("model_dtype", "unknown")
            model_device_type = info_data.get("model_device_type", "unknown")
            
            # TGI capabilities
            capabilities = {
                "streaming": True,      # TGI supports streaming
                "embeddings": False,    # TGI primarily for text generation
                "chat": False,         # TGI doesn't have chat format (just completion)
                "completion": True,    # TGI supports text completion
                "batching": True,      # TGI has continuous batching
                "token_streaming": True,  # TGI supports token-by-token streaming
            }
            
            supported_features = [
                "text_generation",
                "streaming_generation", 
                "continuous_batching",
                "token_streaming",
                "custom_stopping_criteria"
            ]
            
            return EngineInfo(
                engine_name=self.config.name,
                engine_type=self.config.engine_type,
                version=version,
                capabilities=capabilities,
                supported_features=supported_features,
                model_count=1,  # TGI typically serves one model
                additional_info={
                    "base_url": str(self.config.base_url),
                    "model_id": model_id,
                    "model_dtype": model_dtype,
                    "model_device_type": model_device_type,
                    "api_endpoints": {
                        "generate": "/generate",
                        "generate_stream": "/generate_stream",
                        "info": "/info",
                        "health": "/health",
                        "metrics": "/metrics"
                    }
                }
            )
            
        except Exception as e:
            raise ConnectionError(f"Failed to get engine info: {e}")
    
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models from TGI.
        
        TGI typically serves a single model, so we get info from /info endpoint.
        
        Returns:
            List of ModelInfo objects (usually just one)
        """
        try:
            # Get model information from /info endpoint
            info_data = await self._get_json("/info")
            
            model_id = info_data.get("model_id", "unknown")
            model_dtype = info_data.get("model_dtype")
            model_device_type = info_data.get("model_device_type")
            
            # Try to extract model family from model ID
            family = None
            if "/" in model_id:
                # Handle HuggingFace model names like "microsoft/DialoGPT-medium"
                family = model_id.split("/")[0]
            elif "-" in model_id:
                # Handle names like "llama2-7b"
                family = model_id.split("-")[0]
            
            # Estimate model size from dtype and other info
            size_info = f"{model_dtype}" if model_dtype else "unknown"
            
            model_info = ModelInfo(
                name=model_id,
                engine_name=self.config.name,
                family=family,
                size=size_info,
                is_available=True,
                additional_info={
                    "model_dtype": model_dtype,
                    "model_device_type": model_device_type,
                    "max_concurrent_requests": info_data.get("max_concurrent_requests"),
                    "max_input_length": info_data.get("max_input_length"),
                    "max_total_tokens": info_data.get("max_total_tokens"),
                    "waiting_served_ratio": info_data.get("waiting_served_ratio"),
                    "max_batch_total_tokens": info_data.get("max_batch_total_tokens")
                }
            )
            
            models = [model_info]
            self.logger.info(f"Found 1 model in TGI: {model_id}")
            return models
            
        except Exception as e:
            raise ConnectionError(f"Failed to list models: {e}")
    
    async def send_single_request(self, prompt: str, model: str, **kwargs) -> RequestResult:
        """
        Send a single generation request to TGI.
        
        Args:
            prompt: Input prompt text
            model: Model name (ignored for TGI as it serves one model)
            **kwargs: Additional parameters (stream, temperature, etc.)
            
        Returns:
            RequestResult with response and metrics
        """
        request_start = datetime.utcnow()
        
        try:
            # Determine if streaming is requested
            stream = kwargs.get("stream", False)
            endpoint = "/generate_stream" if stream else "/generate"
            
            # Prepare request data for TGI
            request_data = {
                "inputs": prompt,
                "parameters": {}
            }
            
            # Add optional parameters to the parameters object
            if "temperature" in kwargs:
                request_data["parameters"]["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                request_data["parameters"]["max_new_tokens"] = kwargs["max_tokens"]
            if "top_p" in kwargs:
                request_data["parameters"]["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                request_data["parameters"]["top_k"] = kwargs["top_k"]
            if "repetition_penalty" in kwargs:
                request_data["parameters"]["repetition_penalty"] = kwargs["repetition_penalty"]
            if "stop_sequences" in kwargs:
                request_data["parameters"]["stop"] = kwargs["stop_sequences"]
            
            # Add TGI-specific parameters
            request_data["parameters"]["return_full_text"] = kwargs.get("return_full_text", False)
            request_data["parameters"]["details"] = True  # Request detailed metrics
            
            # Send request
            if stream:
                # For streaming, we'd need to handle SSE (Server-Sent Events)
                # For now, fall back to non-streaming
                self.logger.warning("Streaming not fully implemented for TGI, using non-streaming")
                endpoint = "/generate"
            
            response_data = await self._post_json(endpoint, request_data)
            
            request_end = datetime.utcnow()
            request_duration_ms = (request_end - request_start).total_seconds() * 1000
            
            # Extract response text from TGI format
            response_text = ""
            if isinstance(response_data, list) and response_data:
                # TGI returns a list with one item
                first_result = response_data[0]
                response_text = first_result.get("generated_text", "")
            elif isinstance(response_data, dict):
                response_text = response_data.get("generated_text", "")
            
            # Check if request was successful
            if isinstance(response_data, dict) and "error" in response_data:
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
        Parse TGI-specific metrics from raw response.
        
        TGI provides detailed metrics in the 'details' field when requested.
        
        Args:
            raw_response: Raw response data from TGI
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
                model_name="tgi_model",  # TGI serves one model
                timestamp=request_start,
                success=True
            )
            
            # Parse TGI response format
            details = None
            if isinstance(raw_response, list) and raw_response:
                # TGI returns a list with one item
                first_result = raw_response[0]
                details = first_result.get("details")
            elif isinstance(raw_response, dict):
                details = raw_response.get("details")
            
            if details:
                # Extract token counts
                metrics.prompt_eval_count = details.get("prefill", [])
                if isinstance(metrics.prompt_eval_count, list):
                    metrics.prompt_eval_count = len(metrics.prompt_eval_count)
                
                # Generated tokens
                generated_tokens = details.get("tokens", [])
                if isinstance(generated_tokens, list):
                    metrics.eval_count = len(generated_tokens)
                
                # Extract timing information if available
                # TGI provides timestamps for each token
                if generated_tokens and isinstance(generated_tokens, list):
                    # Calculate timing from token timestamps
                    first_token_time = None
                    last_token_time = None
                    
                    for token_info in generated_tokens:
                        if isinstance(token_info, dict) and "timestamp" in token_info:
                            timestamp = token_info["timestamp"]
                            if first_token_time is None:
                                first_token_time = timestamp
                            last_token_time = timestamp
                    
                    if first_token_time and last_token_time:
                        # Convert timestamps to durations (assuming they're in seconds)
                        metrics.first_token_latency = first_token_time
                        metrics.eval_duration = last_token_time - first_token_time
            
            # Calculate total duration from request timing
            request_end = datetime.utcnow()
            metrics.total_duration = (request_end - request_start).total_seconds()
            
            # Set completion time
            metrics.completion_time = request_end
            
            # If we don't have detailed timing, estimate
            if not metrics.eval_duration and metrics.total_duration:
                # Rough estimate: 90% of time on generation, 10% on prompt processing
                metrics.eval_duration = metrics.total_duration * 0.9
                metrics.prompt_eval_duration = metrics.total_duration * 0.1
            
            # Calculate derived metrics
            metrics.calculate_derived_metrics()
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to parse metrics: {e}")
            # Return basic metrics on parse failure
            return ParsedMetrics(
                request_id="",
                engine_name=self.config.name,
                engine_type=self.config.engine_type,
                model_name="tgi_model",
                timestamp=request_start,
                success=False,
                error_message=f"Metrics parsing failed: {e}"
            )
    
    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about the model served by TGI.
        
        Args:
            model_name: Name of the model (ignored, TGI serves one model)
            
        Returns:
            Model information dictionary or None if not found
        """
        try:
            # Get model info from /info endpoint
            info_data = await self._get_json("/info")
            return info_data
            
        except Exception as e:
            self.logger.warning(f"Failed to get model info: {e}")
            return None
    
    async def check_model_availability(self, model_name: str) -> bool:
        """
        Check if a specific model is available.
        
        For TGI, we check if the engine is healthy since it serves one model.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available, False otherwise
        """
        try:
            health_status = await self.health_check()
            return health_status.is_healthy
            
        except Exception as e:
            self.logger.error(f"Failed to check model availability: {e}")
            return False
