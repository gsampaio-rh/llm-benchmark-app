"""Unit tests for Ollama adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.models.engine_config import EngineConfig, EngineHealthStatus, EngineInfo, ModelInfo
from src.models.metrics import RequestResult, ParsedMetrics
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.base_adapter import ConnectionError


class TestOllamaAdapter:
    """Test cases for OllamaAdapter."""
    
    @pytest.fixture
    def engine_config(self):
        """Create a test Ollama engine configuration."""
        return EngineConfig(
            name="test-ollama",
            engine_type="ollama",
            base_url="http://localhost:11434",
            health_endpoint="/api/tags",
            models_endpoint="/api/tags",
            timeout=30
        )
    
    @pytest.fixture
    def adapter(self, engine_config):
        """Create a test Ollama adapter instance."""
        return OllamaAdapter(engine_config)
    
    @pytest.fixture
    def mock_tags_response(self):
        """Mock response from /api/tags endpoint."""
        return {
            "models": [
                {
                    "name": "llama2:7b",
                    "size": 3825819519,
                    "digest": "sha256:1a838c1e519d",
                    "modified_at": "2023-12-07T09:32:18.757212583Z",
                    "details": {
                        "format": "gguf",
                        "family": "llama",
                        "families": ["llama"],
                        "parameter_size": "7B",
                        "quantization_level": "Q4_0"
                    }
                },
                {
                    "name": "mistral:7b",
                    "size": 4109865159,
                    "digest": "sha256:2ae6f6dd7a3d",
                    "modified_at": "2023-12-06T14:32:18.757212583Z"
                }
            ]
        }
    
    @pytest.fixture
    def mock_generate_response(self):
        """Mock response from /api/generate endpoint."""
        return {
            "model": "llama2:7b",
            "created_at": "2023-12-12T14:13:43.416799Z",
            "response": "Hello! How can I help you today?",
            "done": True,
            "total_duration": 5191566416,
            "load_duration": 2154458,
            "prompt_eval_count": 26,
            "prompt_eval_duration": 383809000,
            "eval_count": 298,
            "eval_duration": 4799921000
        }
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter, mock_tags_response):
        """Test successful health check."""
        with patch.object(adapter, '_get_json', return_value=mock_tags_response) as mock_get:
            health_status = await adapter.health_check()
            
            assert health_status.engine_name == "test-ollama"
            assert health_status.is_healthy is True
            assert health_status.response_time_ms is not None
            assert health_status.response_time_ms > 0
            assert health_status.additional_info["model_count"] == 2
            
            mock_get.assert_called_once_with("/api/tags")
    
    @pytest.mark.asyncio
    async def test_health_check_invalid_response(self, adapter):
        """Test health check with invalid response format."""
        invalid_response = {"invalid": "format"}
        
        with patch.object(adapter, '_get_json', return_value=invalid_response):
            health_status = await adapter.health_check()
            
            assert health_status.is_healthy is False
            assert "Invalid response format" in health_status.error_message
    
    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, adapter):
        """Test health check with connection error."""
        with patch.object(adapter, '_get_json', side_effect=ConnectionError("Connection failed")):
            health_status = await adapter.health_check()
            
            assert health_status.is_healthy is False
            assert "Connection failed" in health_status.error_message
    
    @pytest.mark.asyncio
    async def test_get_engine_info(self, adapter, mock_tags_response):
        """Test getting engine information."""
        with patch.object(adapter, '_get_json', return_value=mock_tags_response):
            engine_info = await adapter.get_engine_info()
            
            assert engine_info.engine_name == "test-ollama"
            assert engine_info.engine_type == "ollama"
            assert engine_info.model_count == 2
            assert engine_info.capabilities["streaming"] is True
            assert engine_info.capabilities["chat"] is True
            assert "text_generation" in engine_info.supported_features
            assert "streaming_generation" in engine_info.supported_features
    
    @pytest.mark.asyncio
    async def test_list_models(self, adapter, mock_tags_response):
        """Test listing available models."""
        with patch.object(adapter, '_get_json', return_value=mock_tags_response):
            models = await adapter.list_models()
            
            assert len(models) == 2
            
            # Check first model
            model1 = models[0]
            assert model1.name == "llama2:7b"
            assert model1.engine_name == "test-ollama"
            assert model1.family == "llama2"
            assert model1.size == "3.6GB"  # Converted from bytes
            assert model1.is_available is True
            
            # Check second model
            model2 = models[1]
            assert model2.name == "mistral:7b"
            assert model2.family == "mistral"
    
    @pytest.mark.asyncio
    async def test_list_models_empty(self, adapter):
        """Test listing models when no models available."""
        empty_response = {"models": []}
        
        with patch.object(adapter, '_get_json', return_value=empty_response):
            models = await adapter.list_models()
            
            assert len(models) == 0
    
    @pytest.mark.asyncio
    async def test_send_single_request_success(self, adapter, mock_generate_response):
        """Test successful single request."""
        with patch.object(adapter, '_post_json', return_value=mock_generate_response):
            result = await adapter.send_single_request("Hello", "llama2:7b")
            
            assert result.success is True
            assert result.engine_name == "test-ollama"
            assert result.model_name == "llama2:7b"
            assert result.prompt == "Hello"
            assert result.response == "Hello! How can I help you today?"
            assert result.raw_metrics is not None
            assert result.parsed_metrics is not None
    
    @pytest.mark.asyncio
    async def test_send_single_request_with_options(self, adapter, mock_generate_response):
        """Test single request with additional options."""
        with patch.object(adapter, '_post_json', return_value=mock_generate_response) as mock_post:
            result = await adapter.send_single_request(
                "Hello", 
                "llama2:7b",
                temperature=0.7,
                max_tokens=100,
                top_p=0.9
            )
            
            # Check that options were passed correctly
            call_args = mock_post.call_args
            request_data = call_args[0][1]  # Second argument (data)
            
            assert request_data["options"]["temperature"] == 0.7
            assert request_data["options"]["num_predict"] == 100
            assert request_data["options"]["top_p"] == 0.9
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_send_single_request_error_response(self, adapter):
        """Test single request with error response."""
        error_response = {"error": "Model not found"}
        
        with patch.object(adapter, '_post_json', return_value=error_response):
            result = await adapter.send_single_request("Hello", "nonexistent")
            
            assert result.success is False
            assert result.error_message == "Model not found"
    
    @pytest.mark.asyncio
    async def test_send_single_request_exception(self, adapter):
        """Test single request with exception."""
        with patch.object(adapter, '_post_json', side_effect=ConnectionError("Network error")):
            result = await adapter.send_single_request("Hello", "llama2:7b")
            
            assert result.success is False
            assert "Network error" in result.error_message
    
    def test_parse_metrics_success(self, adapter, mock_generate_response):
        """Test successful metrics parsing."""
        request_start = datetime.utcnow()
        
        metrics = adapter.parse_metrics(mock_generate_response, request_start)
        
        assert metrics.engine_name == "test-ollama"
        assert metrics.engine_type == "ollama"
        assert metrics.model_name == "llama2:7b"
        assert metrics.success is True
        
        # Check converted timing metrics (nanoseconds to seconds)
        assert metrics.total_duration == pytest.approx(5.191566416, rel=1e-6)
        assert metrics.load_duration == pytest.approx(0.002154458, rel=1e-6)
        assert metrics.prompt_eval_count == 26
        assert metrics.prompt_eval_duration == pytest.approx(0.383809, rel=1e-6)
        assert metrics.eval_count == 298
        assert metrics.eval_duration == pytest.approx(4.799921, rel=1e-6)
        
        # Check calculated derived metrics
        assert metrics.prompt_token_rate == pytest.approx(26 / 0.383809, rel=1e-3)
        assert metrics.response_token_rate == pytest.approx(298 / 4.799921, rel=1e-3)
    
    def test_parse_metrics_minimal_response(self, adapter):
        """Test metrics parsing with minimal response data."""
        minimal_response = {
            "model": "test-model",
            "response": "test response"
        }
        request_start = datetime.utcnow()
        
        metrics = adapter.parse_metrics(minimal_response, request_start)
        
        assert metrics.engine_name == "test-ollama"
        assert metrics.model_name == "test-model"
        assert metrics.success is True
        # Optional fields should be None
        assert metrics.total_duration is None
        assert metrics.load_duration is None
    
    def test_parse_metrics_exception(self, adapter):
        """Test metrics parsing with exception."""
        invalid_response = None  # This will cause an exception
        request_start = datetime.utcnow()
        
        metrics = adapter.parse_metrics(invalid_response, request_start)
        
        assert metrics.success is False
        assert "Metrics parsing failed" in metrics.error_message
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, adapter):
        """Test getting detailed model information."""
        model_info_response = {
            "license": "LLAMA 2 COMMUNITY LICENSE AGREEMENT",
            "modelfile": "# Modelfile generated by \"ollama show\"",
            "parameters": "temperature 0.7\ntop_p 0.9",
            "template": "{{ .System }}\n{{ .Prompt }}",
            "details": {
                "format": "gguf",
                "family": "llama",
                "parameter_size": "7B"
            }
        }
        
        with patch.object(adapter, '_post_json', return_value=model_info_response):
            info = await adapter.get_model_info("llama2:7b")
            
            assert info is not None
            assert info["details"]["family"] == "llama"
            assert info["details"]["parameter_size"] == "7B"
    
    @pytest.mark.asyncio
    async def test_get_model_info_not_found(self, adapter):
        """Test getting model info for non-existent model."""
        with patch.object(adapter, '_post_json', side_effect=ConnectionError("Model not found")):
            info = await adapter.get_model_info("nonexistent")
            
            assert info is None
    
    @pytest.mark.asyncio
    async def test_check_model_availability(self, adapter, mock_tags_response):
        """Test checking model availability."""
        with patch.object(adapter, 'list_models') as mock_list:
            # Mock the list_models method to return test models
            mock_list.return_value = [
                ModelInfo(name="llama2:7b", engine_name="test-ollama"),
                ModelInfo(name="mistral:7b", engine_name="test-ollama")
            ]
            
            # Test existing model
            available = await adapter.check_model_availability("llama2:7b")
            assert available is True
            
            # Test non-existent model
            available = await adapter.check_model_availability("nonexistent")
            assert available is False
    
    @pytest.mark.asyncio
    async def test_check_model_availability_error(self, adapter):
        """Test model availability check with error."""
        with patch.object(adapter, 'list_models', side_effect=ConnectionError("Connection failed")):
            available = await adapter.check_model_availability("llama2:7b")
            assert available is False

