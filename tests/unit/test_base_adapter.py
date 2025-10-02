"""Unit tests for base adapter framework."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import httpx

from src.models.engine_config import EngineConfig, EngineHealthStatus, EngineInfo, ModelInfo
from src.models.metrics import RequestResult, ParsedMetrics
from src.adapters.base_adapter import (
    BaseAdapter, 
    AdapterError, 
    ConnectionError, 
    AuthenticationError, 
    TimeoutError, 
    ParseError
)


class MockAdapter(BaseAdapter):
    """Mock adapter implementation for testing."""
    
    async def health_check(self) -> EngineHealthStatus:
        return EngineHealthStatus(
            engine_name=self.config.name,
            is_healthy=True,
            response_time_ms=100.0
        )
    
    async def get_engine_info(self) -> EngineInfo:
        return EngineInfo(
            engine_name=self.config.name,
            engine_type=self.config.engine_type,
            version="1.0.0"
        )
    
    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                name="test-model",
                engine_name=self.config.name
            )
        ]
    
    async def send_single_request(self, prompt: str, model: str, **kwargs) -> RequestResult:
        return RequestResult.success_result(
            engine_name=self.config.name,
            model_name=model,
            prompt=prompt,
            response="Test response"
        )
    
    def parse_metrics(self, raw_response: dict, request_start: datetime) -> ParsedMetrics:
        return ParsedMetrics(
            request_id="test-123",
            engine_name=self.config.name,
            engine_type=self.config.engine_type,
            model_name="test-model",
            timestamp=request_start
        )


class TestBaseAdapter:
    """Test cases for BaseAdapter functionality."""
    
    @pytest.fixture
    def engine_config(self):
        """Create a test engine configuration."""
        return EngineConfig(
            name="test-engine",
            engine_type="ollama",
            base_url="http://localhost:11434",
            health_endpoint="/api/tags",
            timeout=30,
            retry_attempts=2,
            retry_delay=0.1
        )
    
    @pytest.fixture
    def adapter(self, engine_config):
        """Create a test adapter instance."""
        return MockAdapter(engine_config)
    
    def test_adapter_initialization(self, adapter, engine_config):
        """Test adapter initialization."""
        assert adapter.config == engine_config
        assert adapter.client is not None
        assert adapter.client.base_url == str(engine_config.base_url)
    
    def test_string_representations(self, adapter):
        """Test string representations of adapter."""
        str_repr = str(adapter)
        assert "MockAdapter" in str_repr
        assert "test-engine" in str_repr
        
        repr_str = repr(adapter)
        assert "MockAdapter" in repr_str
        assert "test-engine" in repr_str
        assert "ollama" in repr_str
        assert "localhost" in repr_str
    
    @pytest.mark.asyncio
    async def test_context_manager(self, engine_config):
        """Test async context manager functionality."""
        async with MockAdapter(engine_config) as adapter:
            assert adapter.client is not None
        # Client should be closed after context exit
    
    @pytest.mark.asyncio
    async def test_close(self, adapter):
        """Test adapter cleanup."""
        await adapter.close()
        # Should not raise an exception
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, adapter):
        """Test successful HTTP request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        
        with patch.object(adapter.client, 'request', return_value=mock_response) as mock_request:
            response = await adapter._make_request("GET", "/test")
            
            assert response == mock_response
            mock_request.assert_called_once_with("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_authentication_error(self, adapter):
        """Test authentication error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch.object(adapter.client, 'request', return_value=mock_response):
            with pytest.raises(AuthenticationError):
                await adapter._make_request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_http_error(self, adapter):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_response.text = "Server error"
        
        with patch.object(adapter.client, 'request', return_value=mock_response):
            with pytest.raises(ConnectionError) as exc_info:
                await adapter._make_request("GET", "/test")
            
            assert "HTTP 500" in str(exc_info.value)
            assert "Internal server error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_make_request_timeout_with_retry(self, adapter):
        """Test timeout handling with retry logic."""
        with patch.object(adapter.client, 'request', side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(TimeoutError):
                await adapter._make_request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_connection_error_with_retry(self, adapter):
        """Test connection error handling with retry logic."""
        with patch.object(adapter.client, 'request', side_effect=httpx.ConnectError("Connection failed")):
            with pytest.raises(ConnectionError):
                await adapter._make_request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_retry_success(self, adapter):
        """Test successful request after retry."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        # First call fails, second succeeds
        side_effects = [httpx.ConnectError("Connection failed"), mock_response]
        
        with patch.object(adapter.client, 'request', side_effect=side_effects):
            response = await adapter._make_request("GET", "/test")
            assert response == mock_response
    
    @pytest.mark.asyncio
    async def test_get_json_success(self, adapter):
        """Test successful JSON GET request."""
        expected_data = {"key": "value"}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        
        with patch.object(adapter.client, 'request', return_value=mock_response):
            data = await adapter._get_json("/test")
            assert data == expected_data
    
    @pytest.mark.asyncio
    async def test_get_json_parse_error(self, adapter):
        """Test JSON parsing error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with patch.object(adapter.client, 'request', return_value=mock_response):
            with pytest.raises(ParseError):
                await adapter._get_json("/test")
    
    @pytest.mark.asyncio
    async def test_post_json_success(self, adapter):
        """Test successful JSON POST request."""
        request_data = {"input": "test"}
        response_data = {"output": "result"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        
        with patch.object(adapter.client, 'request', return_value=mock_response) as mock_request:
            data = await adapter._post_json("/test", request_data)
            
            assert data == response_data
            mock_request.assert_called_once_with("POST", "/test", json=request_data)
    
    def test_create_raw_metrics(self, adapter):
        """Test creation of raw metrics."""
        raw_response = {"status": "success", "tokens": 10}
        
        metrics = adapter._create_raw_metrics(
            prompt="Test prompt",
            response="Test response",
            model_name="test-model",
            raw_response=raw_response,
            request_duration_ms=150.5
        )
        
        assert metrics.engine_name == "test-engine"
        assert metrics.engine_type == "ollama"
        assert metrics.model_name == "test-model"
        assert metrics.prompt == "Test prompt"
        assert metrics.response == "Test response"
        assert metrics.raw_response == raw_response
        assert metrics.request_duration_ms == 150.5
        assert metrics.request_id is not None
    
    @pytest.mark.asyncio
    async def test_abstract_methods_implemented(self, adapter):
        """Test that all abstract methods are implemented in mock adapter."""
        # These should not raise NotImplementedError
        health_status = await adapter.health_check()
        assert isinstance(health_status, EngineHealthStatus)
        
        engine_info = await adapter.get_engine_info()
        assert isinstance(engine_info, EngineInfo)
        
        models = await adapter.list_models()
        assert isinstance(models, list)
        
        result = await adapter.send_single_request("test", "model")
        assert isinstance(result, RequestResult)
        
        parsed_metrics = adapter.parse_metrics({}, datetime.utcnow())
        assert isinstance(parsed_metrics, ParsedMetrics)


class TestAdapterErrors:
    """Test cases for adapter error handling."""
    
    def test_adapter_error_hierarchy(self):
        """Test that all adapter errors inherit from AdapterError."""
        assert issubclass(ConnectionError, AdapterError)
        assert issubclass(AuthenticationError, AdapterError)
        assert issubclass(TimeoutError, AdapterError)
        assert issubclass(ParseError, AdapterError)
    
    def test_error_messages(self):
        """Test error message handling."""
        connection_error = ConnectionError("Connection failed")
        assert str(connection_error) == "Connection failed"
        
        auth_error = AuthenticationError("Invalid token")
        assert str(auth_error) == "Invalid token"
        
        timeout_error = TimeoutError("Request timed out")
        assert str(timeout_error) == "Request timed out"
        
        parse_error = ParseError("Invalid response format")
        assert str(parse_error) == "Invalid response format"

