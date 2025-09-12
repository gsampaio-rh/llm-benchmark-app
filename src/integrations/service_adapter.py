"""
Service Adapter for service discovery integration.

This module provides a clean adapter layer for service discovery,
abstracting away Kubernetes/OpenShift complexity and providing
a consistent interface for service location and health checking.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..service_discovery import ServiceInfo, discover_services
from ..race.models import EngineInfo


@dataclass
class DiscoveryResult:
    """Result from service discovery operation"""
    services: Dict[str, ServiceInfo]
    healthy_services: List[str]
    discovery_time_ms: float
    errors: List[str]


class BaseDiscoveryProvider(ABC):
    """Abstract base for service discovery providers"""
    
    @abstractmethod
    async def discover_services(self, namespace: str, manual_urls: Optional[Dict[str, str]] = None) -> Dict[str, ServiceInfo]:
        """Discover available services"""
        pass
    
    @abstractmethod
    async def health_check_service(self, service_info: ServiceInfo) -> bool:
        """Check health of a specific service"""
        pass


class ServiceAdapter:
    """Adapter for service discovery with enhanced error handling and caching"""
    
    def __init__(self, discovery_provider: Optional[BaseDiscoveryProvider] = None):
        """Initialize the service adapter
        
        Args:
            discovery_provider: Optional custom discovery provider
        """
        self.discovery_provider = discovery_provider or DefaultDiscoveryProvider()
        self._cached_services: Optional[Dict[str, ServiceInfo]] = None
        self._cache_timestamp: float = 0
        self._cache_ttl_seconds = 300  # 5 minutes
    
    async def discover_services_with_retry(self, 
                                         namespace: str = "vllm-benchmark",
                                         manual_urls: Optional[Dict[str, str]] = None,
                                         max_retries: int = 3,
                                         retry_delay: float = 2.0) -> DiscoveryResult:
        """Discover services with retry logic and comprehensive error handling
        
        Args:
            namespace: Kubernetes namespace to search
            manual_urls: Optional manual URL overrides
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Discovery result with services and metadata
        """
        import time
        start_time = time.time()
        errors = []
        
        for attempt in range(max_retries + 1):
            try:
                services = await self.discovery_provider.discover_services(namespace, manual_urls)
                
                # Perform health checks
                healthy_services = await self._check_service_health(services)
                
                discovery_time = (time.time() - start_time) * 1000
                
                # Cache successful discovery
                self._cached_services = services
                self._cache_timestamp = time.time()
                
                return DiscoveryResult(
                    services=services,
                    healthy_services=healthy_services,
                    discovery_time_ms=discovery_time,
                    errors=errors
                )
                
            except Exception as e:
                error_msg = f"Discovery attempt {attempt + 1} failed: {str(e)}"
                errors.append(error_msg)
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
        
        # All attempts failed
        discovery_time = (time.time() - start_time) * 1000
        return DiscoveryResult(
            services={},
            healthy_services=[],
            discovery_time_ms=discovery_time,
            errors=errors
        )
    
    async def get_cached_services(self) -> Optional[Dict[str, ServiceInfo]]:
        """Get cached services if still valid
        
        Returns:
            Cached services or None if cache is invalid
        """
        if not self._cached_services:
            return None
        
        import time
        if time.time() - self._cache_timestamp > self._cache_ttl_seconds:
            return None
        
        return self._cached_services
    
    async def refresh_service_cache(self, namespace: str = "vllm-benchmark",
                                  manual_urls: Optional[Dict[str, str]] = None) -> DiscoveryResult:
        """Force refresh of service cache
        
        Args:
            namespace: Kubernetes namespace to search
            manual_urls: Optional manual URL overrides
            
        Returns:
            Fresh discovery result
        """
        # Clear cache
        self._cached_services = None
        self._cache_timestamp = 0
        
        return await self.discover_services_with_retry(namespace, manual_urls)
    
    async def _check_service_health(self, services: Dict[str, ServiceInfo]) -> List[str]:
        """Check health of all discovered services concurrently
        
        Args:
            services: Dictionary of discovered services
            
        Returns:
            List of healthy service names
        """
        health_tasks = []
        service_names = []
        
        for service_name, service_info in services.items():
            task = asyncio.create_task(self.discovery_provider.health_check_service(service_info))
            health_tasks.append(task)
            service_names.append(service_name)
        
        # Wait for all health checks with timeout
        try:
            health_results = await asyncio.wait_for(
                asyncio.gather(*health_tasks, return_exceptions=True),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            health_results = [False] * len(health_tasks)
        
        # Collect healthy services
        healthy_services = []
        for i, result in enumerate(health_results):
            if isinstance(result, bool) and result:
                healthy_services.append(service_names[i])
            elif not isinstance(result, Exception):
                # Handle other truthy values
                if result:
                    healthy_services.append(service_names[i])
        
        return healthy_services
    
    async def get_service_by_name(self, service_name: str, 
                                namespace: str = "vllm-benchmark",
                                manual_urls: Optional[Dict[str, str]] = None) -> Optional[ServiceInfo]:
        """Get specific service by name
        
        Args:
            service_name: Name of the service to find
            namespace: Kubernetes namespace to search
            manual_urls: Optional manual URL overrides
            
        Returns:
            ServiceInfo if found, None otherwise
        """
        # Try cache first
        cached_services = await self.get_cached_services()
        if cached_services and service_name in cached_services:
            return cached_services[service_name]
        
        # Discover services
        discovery_result = await self.discover_services_with_retry(namespace, manual_urls)
        return discovery_result.services.get(service_name)
    
    async def wait_for_services(self, required_services: List[str],
                              namespace: str = "vllm-benchmark",
                              manual_urls: Optional[Dict[str, str]] = None,
                              timeout_seconds: float = 60.0,
                              check_interval: float = 5.0) -> DiscoveryResult:
        """Wait for required services to become available
        
        Args:
            required_services: List of required service names
            namespace: Kubernetes namespace to search
            manual_urls: Optional manual URL overrides
            timeout_seconds: Maximum time to wait
            check_interval: Interval between checks
            
        Returns:
            Discovery result when all services are available or timeout
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            result = await self.discover_services_with_retry(namespace, manual_urls)
            
            # Check if all required services are healthy
            missing_services = set(required_services) - set(result.healthy_services)
            
            if not missing_services:
                return result
            
            # Wait before next check
            await asyncio.sleep(check_interval)
        
        # Timeout reached - return last result
        return result
    
    def create_service_info(self, service_name: str, url: str, 
                          status: str = "manual", response_time: float = 0) -> ServiceInfo:
        """Create a ServiceInfo object for manual service configuration
        
        Args:
            service_name: Name of the service
            url: Service URL
            status: Service status
            response_time: Response time in seconds
            
        Returns:
            ServiceInfo object
        """
        return ServiceInfo(
            name=service_name,
            url=url,
            status=status,
            response_time=response_time,
            service_type="manual"
        )


class DefaultDiscoveryProvider(BaseDiscoveryProvider):
    """Default discovery provider using the existing service discovery module"""
    
    async def discover_services(self, namespace: str, manual_urls: Optional[Dict[str, str]] = None) -> Dict[str, ServiceInfo]:
        """Discover services using the existing discovery module"""
        return await discover_services(namespace=namespace, manual_urls=manual_urls)
    
    async def health_check_service(self, service_info: ServiceInfo) -> bool:
        """Check health of a specific service"""
        # For now, use the status from discovery
        # In a full implementation, we'd make an actual health check request
        return service_info.status in ["healthy", "responding"]


class MockDiscoveryProvider(BaseDiscoveryProvider):
    """Mock discovery provider for testing"""
    
    def __init__(self, mock_services: Optional[Dict[str, ServiceInfo]] = None):
        """Initialize with optional mock services
        
        Args:
            mock_services: Dictionary of mock services to return
        """
        self.mock_services = mock_services or self._create_default_mock_services()
    
    async def discover_services(self, namespace: str, manual_urls: Optional[Dict[str, str]] = None) -> Dict[str, ServiceInfo]:
        """Return mock services"""
        # Simulate discovery delay
        await asyncio.sleep(0.1)
        return self.mock_services.copy()
    
    async def health_check_service(self, service_info: ServiceInfo) -> bool:
        """Mock health check - always returns True for healthy services"""
        await asyncio.sleep(0.05)  # Simulate health check delay
        return service_info.status == "healthy"
    
    def _create_default_mock_services(self) -> Dict[str, ServiceInfo]:
        """Create default mock services for testing"""
        return {
            "vllm": ServiceInfo(
                name="vllm",
                url="https://vllm-test.example.com",
                status="healthy",
                response_time=0.120,
                service_type="mock"
            ),
            "tgi": ServiceInfo(
                name="tgi",
                url="https://tgi-test.example.com",
                status="healthy",
                response_time=0.350,
                service_type="mock"
            ),
            "ollama": ServiceInfo(
                name="ollama",
                url="https://ollama-test.example.com",
                status="healthy",
                response_time=0.650,
                service_type="mock"
            )
        }
    
    def add_service(self, service_name: str, service_info: ServiceInfo):
        """Add a service to the mock provider"""
        self.mock_services[service_name] = service_info
    
    def remove_service(self, service_name: str):
        """Remove a service from the mock provider"""
        self.mock_services.pop(service_name, None)
    
    def set_service_status(self, service_name: str, status: str):
        """Update a service's status"""
        if service_name in self.mock_services:
            self.mock_services[service_name].status = status
