"""
Base adapter framework for LLM engine connections.

This module provides the abstract base class and common functionality
for all engine adapters.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from httpx import AsyncClient, Timeout, Response

from ..models.engine_config import EngineConfig, EngineHealthStatus, EngineInfo, ModelInfo
from ..models.metrics import RawEngineMetrics, ParsedMetrics, RequestResult


logger = logging.getLogger(__name__)


class AdapterError(Exception):
    """Base exception for adapter errors."""
    pass


class ConnectionError(AdapterError):
    """Raised when connection to engine fails."""
    pass


class AuthenticationError(AdapterError):
    """Raised when authentication fails."""
    pass


class TimeoutError(AdapterError):
    """Raised when request times out."""
    pass


class ParseError(AdapterError):
    """Raised when response parsing fails."""
    pass


class BaseAdapter(ABC):
    """
    Abstract base class for all engine adapters.
    
    This class provides common functionality for connecting to LLM engines,
    handling errors, retries, and parsing responses.
    """
    
    def __init__(self, config: EngineConfig):
        """
        Initialize the adapter with engine configuration.
        
        Args:
            config: Engine configuration containing connection details
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.name}")
        
        # Create HTTP client with timeout configuration
        timeout = Timeout(
            connect=30.0,  # Connection timeout
            read=config.timeout,  # Read timeout
            write=30.0,  # Write timeout
            pool=30.0   # Pool timeout
        )
        
        # Prepare headers
        headers = {
            "User-Agent": "llm-benchmark-tool/0.1.0",
            "Accept": "application/json",
        }
        
        # Add custom headers from config
        if config.custom_headers:
            headers.update(config.custom_headers)
        
        # Add authentication if provided
        if config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"
        
        self.client = AsyncClient(
            base_url=str(config.base_url),
            timeout=timeout,
            headers=headers,
            follow_redirects=True
        )
        
        self.logger.info(f"Initialized adapter for {config.name} ({config.engine_type})")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self.client:
            await self.client.aclose()
            self.logger.debug(f"Closed adapter for {self.config.name}")
    
    @abstractmethod
    async def health_check(self) -> EngineHealthStatus:
        """
        Check if the engine is healthy and responsive.
        
        Returns:
            EngineHealthStatus with health information
            
        Raises:
            ConnectionError: If unable to connect to engine
            TimeoutError: If health check times out
        """
        pass
    
    @abstractmethod
    async def get_engine_info(self) -> EngineInfo:
        """
        Get detailed information about the engine.
        
        Returns:
            EngineInfo with engine details and capabilities
            
        Raises:
            ConnectionError: If unable to connect to engine
            ParseError: If response cannot be parsed
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models on the engine.
        
        Returns:
            List of ModelInfo objects
            
        Raises:
            ConnectionError: If unable to connect to engine
            ParseError: If response cannot be parsed
        """
        pass
    
    @abstractmethod
    async def send_single_request(self, prompt: str, model: str, **kwargs) -> RequestResult:
        """
        Send a single request to the engine.
        
        Args:
            prompt: Input prompt text
            model: Model name to use
            **kwargs: Additional engine-specific parameters
            
        Returns:
            RequestResult with response and metrics
            
        Raises:
            ConnectionError: If unable to connect to engine
            TimeoutError: If request times out
            ParseError: If response cannot be parsed
        """
        pass
    
    @abstractmethod
    def parse_metrics(self, raw_response: Dict[str, Any], request_start: datetime) -> ParsedMetrics:
        """
        Parse engine-specific metrics from raw response.
        
        Args:
            raw_response: Raw response data from engine
            request_start: When the request started
            
        Returns:
            ParsedMetrics with standardized metrics
            
        Raises:
            ParseError: If metrics cannot be parsed
        """
        pass
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Response:
        """
        Make an HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            HTTP response
            
        Raises:
            ConnectionError: If connection fails after retries
            TimeoutError: If request times out
            AuthenticationError: If authentication fails
        """
        last_exception = None
        
        for attempt in range(self.config.retry_attempts + 1):
            try:
                self.logger.debug(f"Making {method} request to {endpoint} (attempt {attempt + 1})")
                
                response = await self.client.request(method, endpoint, **kwargs)
                
                # Check for authentication errors
                if response.status_code == 401:
                    raise AuthenticationError(f"Authentication failed for {self.config.name}")
                
                # Check for other client/server errors
                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code} error from {self.config.name}"
                    try:
                        error_detail = response.json()
                        if isinstance(error_detail, dict) and "error" in error_detail:
                            error_msg += f": {error_detail['error']}"
                    except Exception:
                        error_msg += f": {response.text[:200]}"
                    
                    raise ConnectionError(error_msg)
                
                self.logger.debug(f"Request successful: {response.status_code}")
                return response
                
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(f"Request to {self.config.name} timed out: {e}")
                self.logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
                
            except httpx.ConnectError as e:
                last_exception = ConnectionError(f"Failed to connect to {self.config.name}: {e}")
                self.logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                
            except httpx.RequestError as e:
                last_exception = ConnectionError(f"Request error to {self.config.name}: {e}")
                self.logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                
            except (AuthenticationError, ConnectionError):
                # Don't retry authentication or explicit connection errors
                raise
                
            except Exception as e:
                last_exception = AdapterError(f"Unexpected error with {self.config.name}: {e}")
                self.logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.config.retry_attempts:
                wait_time = self.config.retry_delay * (2 ** attempt)
                self.logger.debug(f"Waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
        
        # All retries exhausted
        self.logger.error(f"All retry attempts exhausted for {self.config.name}")
        if last_exception:
            raise last_exception
        else:
            raise ConnectionError(f"Failed to connect to {self.config.name} after {self.config.retry_attempts} retries")
    
    async def _get_json(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make a GET request and return JSON response.
        
        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments for request
            
        Returns:
            Parsed JSON response
            
        Raises:
            ConnectionError: If request fails
            ParseError: If response is not valid JSON
        """
        try:
            response = await self._make_request("GET", endpoint, **kwargs)
            return response.json()
        except Exception as e:
            if isinstance(e, (ConnectionError, TimeoutError, AuthenticationError)):
                raise
            raise ParseError(f"Failed to parse JSON response from {endpoint}: {e}")
    
    async def _post_json(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Make a POST request with JSON data and return JSON response.
        
        Args:
            endpoint: API endpoint path
            data: JSON data to send
            **kwargs: Additional arguments for request
            
        Returns:
            Parsed JSON response
            
        Raises:
            ConnectionError: If request fails
            ParseError: If response is not valid JSON
        """
        try:
            response = await self._make_request("POST", endpoint, json=data, **kwargs)
            return response.json()
        except Exception as e:
            if isinstance(e, (ConnectionError, TimeoutError, AuthenticationError)):
                raise
            raise ParseError(f"Failed to parse JSON response from {endpoint}: {e}")
    
    async def _get_with_optional_json(self, endpoint: str, **kwargs) -> tuple[Response, Optional[Dict[str, Any]]]:
        """
        Make a GET request and optionally parse JSON response.
        
        This is useful for health check endpoints that may return:
        - Empty responses with just HTTP status codes
        - Plain text responses
        - JSON responses
        
        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments for request
            
        Returns:
            Tuple of (HTTP response, parsed JSON or None)
            
        Raises:
            ConnectionError: If request fails
            TimeoutError: If request times out
            AuthenticationError: If authentication fails
        """
        response = await self._make_request("GET", endpoint, **kwargs)
        
        json_data = None
        if response.text.strip():  # Only try to parse if there's content
            try:
                json_data = response.json()
            except Exception:
                # Non-JSON response is acceptable for some endpoints
                pass
        
        return response, json_data
    
    def _create_raw_metrics(
        self, 
        prompt: str, 
        response: str, 
        model_name: str,
        raw_response: Dict[str, Any],
        request_duration_ms: Optional[float] = None
    ) -> RawEngineMetrics:
        """
        Create RawEngineMetrics from response data.
        
        Args:
            prompt: Input prompt
            response: Generated response
            model_name: Model name used
            raw_response: Raw response from engine
            request_duration_ms: Total request duration in milliseconds
            
        Returns:
            RawEngineMetrics instance
        """
        return RawEngineMetrics(
            engine_name=self.config.name,
            engine_type=self.config.engine_type,
            model_name=model_name,
            prompt=prompt,
            response=response,
            raw_response=raw_response,
            request_duration_ms=request_duration_ms
        )
    
    def __str__(self) -> str:
        """String representation of the adapter."""
        return f"{self.__class__.__name__}({self.config.name})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the adapter."""
        return f"{self.__class__.__name__}(name='{self.config.name}', type='{self.config.engine_type}', url='{self.config.base_url}')"

