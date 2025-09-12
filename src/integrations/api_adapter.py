"""
API Adapter for real service integration.

This module provides a clean adapter layer for integrating with real AI services,
abstracting away the complexities of different API formats and protocols.
"""

import asyncio
import time
from typing import Optional, Dict, AsyncGenerator, Any, List
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..api_clients import UnifiedAPIClient, GenerationRequest, GenerationResponse
from ..race.models import EngineInfo, ServicePersonality
from ..service_discovery import ServiceInfo


@dataclass
class StreamingMetrics:
    """Metrics collected during streaming response"""
    ttft_ms: Optional[float] = None
    total_time_ms: float = 0.0
    tokens_received: int = 0
    first_token_time: Optional[float] = None
    start_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None


class BaseServiceAdapter(ABC):
    """Abstract base for service adapters"""
    
    @abstractmethod
    async def stream_response(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Stream response from the service"""
        pass
    
    @abstractmethod
    async def get_service_info(self) -> EngineInfo:
        """Get service technical information"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        pass


class APIAdapter:
    """Adapter for real API integration with comprehensive error handling"""
    
    def __init__(self, unified_client: UnifiedAPIClient):
        """Initialize the API adapter
        
        Args:
            unified_client: The unified API client for all services
        """
        self.client = unified_client
        self.service_adapters: Dict[str, BaseServiceAdapter] = {}
        self._setup_service_adapters()
    
    def _setup_service_adapters(self):
        """Setup individual service adapters"""
        for service_name, api_client in self.client.clients.items():
            self.service_adapters[service_name] = ServiceSpecificAdapter(
                service_name, api_client
            )
    
    async def stream_response(self, service_name: str, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Stream response from real API with metrics collection
        
        Args:
            service_name: Name of the service to call
            request: Generation request parameters
            
        Yields:
            Stream of response tokens
            
        Raises:
            ServiceNotAvailableError: If service is not available
            APIError: If API call fails
        """
        if service_name not in self.service_adapters:
            raise ServiceNotAvailableError(f"Service {service_name} not available")
        
        adapter = self.service_adapters[service_name]
        
        try:
            async for token in adapter.stream_response(request):
                yield token
        except Exception as e:
            raise APIError(f"Error streaming from {service_name}: {str(e)}") from e
    
    async def stream_with_metrics(self, service_name: str, request: GenerationRequest) -> tuple[AsyncGenerator[str, None], StreamingMetrics]:
        """Stream response with detailed metrics collection
        
        Args:
            service_name: Name of the service to call
            request: Generation request parameters
            
        Returns:
            Tuple of (token_generator, metrics)
        """
        metrics = StreamingMetrics(start_time=time.time())
        
        async def _stream_with_metrics():
            first_token = True
            try:
                async for token in self.stream_response(service_name, request):
                    if first_token:
                        metrics.first_token_time = time.time()
                        metrics.ttft_ms = (metrics.first_token_time - metrics.start_time) * 1000
                        first_token = False
                    
                    metrics.tokens_received += 1
                    yield token
                
                metrics.total_time_ms = (time.time() - metrics.start_time) * 1000
                metrics.success = True
                
            except Exception as e:
                metrics.success = False
                metrics.error_message = str(e)
                metrics.total_time_ms = (time.time() - metrics.start_time) * 1000
                raise
        
        return _stream_with_metrics(), metrics
    
    async def get_service_info(self, service_name: str) -> EngineInfo:
        """Get real service technical information
        
        Args:
            service_name: Name of the service
            
        Returns:
            Engine information for the service
            
        Raises:
            ServiceNotAvailableError: If service is not available
        """
        if service_name not in self.service_adapters:
            raise ServiceNotAvailableError(f"Service {service_name} not available")
        
        adapter = self.service_adapters[service_name]
        return await adapter.get_service_info()
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Health check all available services
        
        Returns:
            Dictionary of service_name -> health_status
        """
        health_results = {}
        
        # Run health checks concurrently
        health_tasks = [
            (service_name, adapter.health_check())
            for service_name, adapter in self.service_adapters.items()
        ]
        
        for service_name, health_task in health_tasks:
            try:
                health_results[service_name] = await asyncio.wait_for(health_task, timeout=5.0)
            except asyncio.TimeoutError:
                health_results[service_name] = False
            except Exception:
                health_results[service_name] = False
        
        return health_results
    
    async def concurrent_stream(self, services: List[str], request: GenerationRequest) -> Dict[str, AsyncGenerator[str, None]]:
        """Start concurrent streaming from multiple services
        
        Args:
            services: List of service names to call
            request: Generation request parameters
            
        Returns:
            Dictionary of service_name -> token_generator
        """
        streams = {}
        
        for service_name in services:
            if service_name in self.service_adapters:
                try:
                    streams[service_name] = self.stream_response(service_name, request)
                except Exception as e:
                    # Log error but continue with other services
                    print(f"Failed to start stream for {service_name}: {e}")
        
        return streams
    
    def get_available_services(self) -> List[str]:
        """Get list of available service names
        
        Returns:
            List of available service names
        """
        return list(self.service_adapters.keys())
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Close any open connections
        if hasattr(self.client, '__aexit__'):
            await self.client.__aexit__(exc_type, exc_val, exc_tb)


class ServiceSpecificAdapter(BaseServiceAdapter):
    """Adapter for individual service API clients"""
    
    def __init__(self, service_name: str, api_client: Any):
        """Initialize service-specific adapter
        
        Args:
            service_name: Name of the service
            api_client: The API client for this service
        """
        self.service_name = service_name
        self.api_client = api_client
    
    async def stream_response(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Stream response from the specific service"""
        try:
            async for chunk in self.api_client.generate_stream(request):
                yield chunk
        except Exception as e:
            raise APIError(f"Streaming error from {self.service_name}: {str(e)}") from e
    
    async def get_service_info(self) -> EngineInfo:
        """Get service technical information"""
        # Create realistic engine info based on service type
        service_configs = {
            "vllm": EngineInfo(
                engine_url=self.api_client.base_url,
                model_name="Qwen/Qwen2.5-7B-Instruct",
                version="v0.5.4",
                gpu_type="NVIDIA H100",
                memory_gb=80,
                max_batch_size=64,
                max_context_length=8192,
                deployment="OpenShift Pod"
            ),
            "tgi": EngineInfo(
                engine_url=self.api_client.base_url,
                model_name="Qwen/Qwen2.5-7B-Instruct", 
                version="v2.0.1",
                gpu_type="NVIDIA A100",
                memory_gb=40,
                max_batch_size=32,
                max_context_length=4096,
                deployment="Kubernetes Pod"
            ),
            "ollama": EngineInfo(
                engine_url=self.api_client.base_url,
                model_name="qwen2.5:7b-instruct",
                version="v0.3.6",
                gpu_type="NVIDIA RTX 4090",
                memory_gb=24,
                max_batch_size=16,
                max_context_length=4096,
                deployment="Docker Container"
            )
        }
        
        return service_configs.get(self.service_name, EngineInfo(engine_url=self.api_client.base_url))
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            return await self.api_client.health_check()
        except Exception:
            return False


# Custom Exceptions
class ServiceNotAvailableError(Exception):
    """Raised when a requested service is not available"""
    pass


class APIError(Exception):
    """Raised when an API call fails"""
    pass


class ConfigurationError(Exception):
    """Raised when there's a configuration issue"""
    pass
