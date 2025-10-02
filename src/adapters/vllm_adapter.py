"""
vLLM engine adapter implementation.

This module provides the adapter for connecting to vLLM engines,
handling vLLM's OpenAI-compatible API calls and metrics parsing.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

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
        
        vLLM's /health endpoint may return:
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
            
            # vLLM health endpoint returns 200 OK when healthy
            is_healthy = response.status_code == 200
            
            # Process JSON response if available
            version = None
            additional_info = {
                "endpoint": self.config.health_endpoint,
                "api_type": "openai_compatible",
                "status_code": response.status_code
            }
            
            if response_data:
                # Check for any error indicators in JSON
                if "error" in response_data or response_data.get("status") == "error":
                    is_healthy = False
                version = response_data.get("version")
                additional_info["response_data"] = response_data
            elif response.text.strip():
                # Non-JSON response with content
                additional_info["response_type"] = "non_json"
                additional_info["response_text"] = response.text[:100]  # First 100 chars for debugging
            else:
                # Empty response is normal for vLLM health endpoint
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
        first_token_time = None
        prompt_processing_end = None
        
        try:
            # Determine if this should be a chat completion or text completion
            use_chat = kwargs.get("use_chat", False)
            use_streaming = kwargs.get("stream", False)
            
            if use_chat:
                # Use chat completions endpoint
                request_data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": use_streaming,
                }
                endpoint = "/v1/chat/completions"
            else:
                # Use completions endpoint
                request_data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": use_streaming,
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
            
            # Handle streaming vs non-streaming requests
            if use_streaming:
                response_data, first_token_time, prompt_processing_end = await self._handle_streaming_request(
                    endpoint, request_data, request_start
                )
            else:
                response_data = await self._post_json(endpoint, request_data)
                # For non-streaming, estimate prompt processing time based on model loading patterns
                # Typically, model loading + prompt processing takes 10-30% of total time
                prompt_processing_end = request_start + (datetime.utcnow() - request_start) * 0.2
            
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
            
            # Parse metrics with enhanced timing information
            parsed_metrics = self.parse_metrics(
                response_data, 
                request_start, 
                first_token_time=first_token_time,
                prompt_processing_end=prompt_processing_end,
                request_end=request_end
            )
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
    
    async def _handle_streaming_request(
        self, 
        endpoint: str, 
        request_data: Dict[str, Any], 
        request_start: datetime
    ) -> tuple[Dict[str, Any], Optional[datetime], Optional[datetime]]:
        """
        Handle streaming request to capture first token timing.
        
        Args:
            endpoint: API endpoint
            request_data: Request payload
            request_start: When request started
            
        Returns:
            Tuple of (final_response_data, first_token_time, prompt_processing_end)
        """
        try:
            first_token_time = None
            prompt_processing_end = None
            accumulated_text = ""
            token_count = 0
            final_usage = None
            model_name = request_data.get("model", "unknown")
            
            # Make streaming request using client.stream()
            async with self.client.stream("POST", endpoint, json=request_data) as response:
                # Check for errors
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise ConnectionError(f"HTTP {response.status_code}: {error_text.decode()[:200]}")
                
                # Process streaming response
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                        
                    # Remove "data: " prefix from SSE format
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    # Check for end of stream
                    if line.strip() == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(line)
                        
                        # Extract token content
                        choices = chunk_data.get("choices", [])
                        if choices:
                            choice = choices[0]
                            
                            # Handle different response formats
                            delta = choice.get("delta", {})
                            if "content" in delta and delta["content"]:
                                # First token received
                                if first_token_time is None:
                                    first_token_time = datetime.utcnow()
                                    # Estimate prompt processing ended just before first token
                                    prompt_processing_end = first_token_time - timedelta(milliseconds=10)
                                
                                accumulated_text += delta["content"]
                                token_count += 1
                            
                            # Check for finish reason
                            if choice.get("finish_reason"):
                                # Extract usage information if available
                                if "usage" in chunk_data:
                                    final_usage = chunk_data["usage"]
                    
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        self.logger.warning(f"Failed to parse vLLM streaming chunk: {line[:100]}")
                        continue
            
            # Construct final response in OpenAI format
            final_response = {
                "model": model_name,
                "choices": [{
                    "message": {"content": accumulated_text} if "/chat/" in endpoint else None,
                    "text": accumulated_text if "/completions" in endpoint else None,
                    "finish_reason": "stop"
                }],
                "usage": final_usage or {
                    "prompt_tokens": None,  # Will be estimated
                    "completion_tokens": token_count,
                    "total_tokens": None
                }
            }
            
            return final_response, first_token_time, prompt_processing_end
            
        except Exception as e:
            self.logger.error(f"Streaming request failed: {e}")
            # Fallback to non-streaming
            response_data = await self._post_json(endpoint, request_data)
            return response_data, None, None
    
    async def send_streaming_request(
        self,
        prompt: str,
        model: str,
        token_callback: Optional[Any] = None,
        **kwargs
    ) -> RequestResult:
        """
        Send a streaming generation request to vLLM with real-time token delivery.
        
        Args:
            prompt: Input prompt text
            model: Model name to use
            token_callback: Async callback for each token: async def(token: str) -> None
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            RequestResult with complete response and metrics
        """
        request_start = datetime.utcnow()
        first_token_time = None
        prompt_processing_end = None
        
        try:
            # Determine if this should be a chat completion or text completion
            use_chat = kwargs.get("use_chat", False)
            
            if use_chat:
                # Use chat completions endpoint
                request_data = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                }
                endpoint = "/v1/chat/completions"
            else:
                # Use completions endpoint
                request_data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
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
            
            # Make streaming request using client.stream() for proper SSE handling
            accumulated_text = ""
            token_count = 0
            final_usage = None
            model_name = request_data.get("model", "unknown")
            
            # Use streaming context
            async with self.client.stream("POST", endpoint, json=request_data) as response:
                # Check for errors
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise ConnectionError(f"HTTP {response.status_code}: {error_text.decode()[:200]}")
                
                self.logger.info(f"vLLM streaming started, status: {response.status_code}")
                
                # Process streaming response
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    self.logger.debug(f"vLLM streaming line: {line[:200]}")
                    
                    # Remove "data: " prefix from SSE format
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    # Check for end of stream
                    if line.strip() == "[DONE]":
                        self.logger.info("vLLM streaming completed with [DONE]")
                        break
                    
                    try:
                        chunk_data = json.loads(line)
                        
                        # Extract token content
                        choices = chunk_data.get("choices", [])
                        if choices:
                            choice = choices[0]
                            
                            # Handle different response formats
                            delta = choice.get("delta", {})
                            text = choice.get("text", "")  # vLLM might use 'text' instead of 'delta'
                            
                            # Check both delta.content and text field
                            token = None
                            if "content" in delta and delta["content"]:
                                token = delta["content"]
                            elif text:
                                token = text
                            
                            if token:
                                # First token received
                                if first_token_time is None:
                                    first_token_time = datetime.utcnow()
                                    # Estimate prompt processing ended just before first token
                                    prompt_processing_end = first_token_time - timedelta(milliseconds=10)
                                    self.logger.info(f"vLLM first token received: {token[:50]}")
                                
                                accumulated_text += token
                                token_count += 1
                                
                                # Call token callback if provided
                                if token_callback:
                                    await token_callback(token)
                            
                            # Check for finish reason
                            if choice.get("finish_reason"):
                                # Extract usage information if available
                                if "usage" in chunk_data:
                                    final_usage = chunk_data["usage"]
                    
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        self.logger.warning(f"Failed to parse vLLM streaming chunk: {line[:100]}")
                        continue
            
            request_end = datetime.utcnow()
            request_duration_ms = (request_end - request_start).total_seconds() * 1000
            
            # Construct final response in OpenAI format
            final_response = {
                "model": model_name,
                "choices": [{
                    "message": {"content": accumulated_text} if use_chat else None,
                    "text": accumulated_text if not use_chat else None,
                    "finish_reason": "stop"
                }],
                "usage": final_usage or {
                    "prompt_tokens": None,
                    "completion_tokens": token_count,
                    "total_tokens": None
                }
            }
            
            # Extract response text
            response_text = accumulated_text
            
            # Create raw metrics
            raw_metrics = self._create_raw_metrics(
                prompt=prompt,
                response=response_text,
                model_name=model,
                raw_response=final_response,
                request_duration_ms=request_duration_ms
            )
            
            # Parse metrics
            parsed_metrics = self.parse_metrics(
                final_response,
                request_start,
                first_token_time=first_token_time,
                prompt_processing_end=prompt_processing_end,
                request_end=request_end
            )
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
            self.logger.error(f"Streaming request failed: {e}")
            return RequestResult.error_result(
                engine_name=self.config.name,
                model_name=model,
                prompt=prompt,
                error_message=str(e)
            )
    
    def parse_metrics(
        self, 
        raw_response: Dict[str, Any], 
        request_start: datetime,
        first_token_time: Optional[datetime] = None,
        prompt_processing_end: Optional[datetime] = None,
        request_end: Optional[datetime] = None
    ) -> ParsedMetrics:
        """
        Parse vLLM-specific metrics from raw response with enhanced timing.
        
        This enhanced version uses streaming data and timing measurements to provide
        more accurate metrics that match Ollama's completeness.
        
        Args:
            raw_response: Raw response data from vLLM
            request_start: When the request started
            first_token_time: When first token was received (from streaming)
            prompt_processing_end: When prompt processing completed
            request_end: When the request completed
            
        Returns:
            ParsedMetrics with standardized metrics
        """
        try:
            # Use provided request_end or calculate it
            actual_request_end = request_end or datetime.utcnow()
            
            # Create base metrics object
            metrics = ParsedMetrics(
                request_id="",  # Will be set by caller
                engine_name=self.config.name,
                engine_type=self.config.engine_type,
                model_name=raw_response.get("model", "unknown"),
                timestamp=request_start,
                success=True,
                request_start=request_start,
                completion_time=actual_request_end
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
            metrics.total_duration = (actual_request_end - request_start).total_seconds()
            
            # Enhanced timing calculations based on available data
            if first_token_time and prompt_processing_end:
                # We have detailed timing from streaming
                metrics.first_token_time = first_token_time
                metrics.first_token_latency = (first_token_time - request_start).total_seconds()
                
                # Calculate load duration (time before prompt processing)
                # In vLLM, this includes model loading and initial setup
                metrics.load_duration = (prompt_processing_end - request_start).total_seconds()
                
                # Prompt evaluation duration (minimal in vLLM due to parallel processing)
                metrics.prompt_eval_duration = (first_token_time - prompt_processing_end).total_seconds()
                
                # Generation duration (from first token to completion)
                metrics.eval_duration = (actual_request_end - first_token_time).total_seconds()
                
            elif first_token_time:
                # We have first token time but no prompt processing end time
                metrics.first_token_time = first_token_time
                metrics.first_token_latency = (first_token_time - request_start).total_seconds()
                
                # Estimate load + prompt processing time as time to first token
                time_to_first_token = metrics.first_token_latency
                
                # Estimate load duration as 60% of time to first token
                metrics.load_duration = time_to_first_token * 0.6
                
                # Estimate prompt processing as 40% of time to first token
                metrics.prompt_eval_duration = time_to_first_token * 0.4
                
                # Generation duration
                metrics.eval_duration = metrics.total_duration - metrics.first_token_latency
                
            else:
                # No streaming data available - use improved estimates
                if metrics.total_duration:
                    # More sophisticated estimation based on vLLM characteristics
                    # vLLM typically has:
                    # - 10-20% model loading/setup time
                    # - 5-15% prompt processing time (parallel processing is fast)
                    # - 70-85% generation time
                    
                    # Estimate load duration (model setup)
                    metrics.load_duration = metrics.total_duration * 0.15
                    
                    # Estimate prompt processing duration
                    metrics.prompt_eval_duration = metrics.total_duration * 0.10
                    
                    # Estimate generation duration
                    metrics.eval_duration = metrics.total_duration * 0.75
                    
                    # Estimate first token latency (load + prompt processing + small delay)
                    metrics.first_token_latency = metrics.load_duration + metrics.prompt_eval_duration + 0.05
            
            # Calculate derived metrics (token rates, inter-token latency, etc.)
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
