"""Unit tests for engine configuration models."""

import pytest
from pydantic import ValidationError
from src.models.engine_config import EngineConfig, EngineHealthStatus, EngineInfo, ModelInfo, BenchmarkConfig


class TestEngineConfig:
    """Test cases for EngineConfig model."""
    
    def test_valid_engine_config(self):
        """Test creating a valid engine configuration."""
        config = EngineConfig(
            name="test-ollama",
            engine_type="ollama",
            base_url="http://localhost:11434",
            health_endpoint="/api/tags"
        )
        
        assert config.name == "test-ollama"
        assert config.engine_type == "ollama"
        assert str(config.base_url) == "http://localhost:11434/"
        assert config.health_endpoint == "/api/tags"
        assert config.timeout == 300  # default value
        assert config.retry_attempts == 3  # default value
    
    def test_invalid_engine_type(self):
        """Test that invalid engine types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EngineConfig(
                name="test",
                engine_type="invalid",
                base_url="http://localhost:8080",
                health_endpoint="/health"
            )
        
        assert "Input should be 'ollama', 'vllm' or 'tgi'" in str(exc_info.value)
    
    def test_invalid_url(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EngineConfig(
                name="test",
                engine_type="ollama",
                base_url="not-a-url",
                health_endpoint="/health"
            )
        
        assert "URL" in str(exc_info.value)
    
    def test_timeout_validation(self):
        """Test timeout field validation."""
        # Valid timeout
        config = EngineConfig(
            name="test",
            engine_type="ollama",
            base_url="http://localhost:8080",
            health_endpoint="/health",
            timeout=60
        )
        assert config.timeout == 60
        
        # Invalid timeout (too low)
        with pytest.raises(ValidationError):
            EngineConfig(
                name="test",
                engine_type="ollama",
                base_url="http://localhost:8080",
                health_endpoint="/health",
                timeout=0
            )
        
        # Invalid timeout (too high)
        with pytest.raises(ValidationError):
            EngineConfig(
                name="test",
                engine_type="ollama",
                base_url="http://localhost:8080",
                health_endpoint="/health",
                timeout=4000
            )
    
    def test_string_representation(self):
        """Test string representation of engine config."""
        config = EngineConfig(
            name="test-engine",
            engine_type="vllm",
            base_url="http://localhost:8000",
            health_endpoint="/health"
        )
        
        expected = "test-engine (vllm) @ http://localhost:8000/"
        assert str(config) == expected


class TestEngineHealthStatus:
    """Test cases for EngineHealthStatus model."""
    
    def test_healthy_status(self):
        """Test creating a healthy status."""
        status = EngineHealthStatus(
            engine_name="test-engine",
            is_healthy=True,
            response_time_ms=150.5,
            engine_version="1.0.0"
        )
        
        assert status.engine_name == "test-engine"
        assert status.is_healthy is True
        assert status.response_time_ms == 150.5
        assert status.engine_version == "1.0.0"
        assert status.error_message is None
    
    def test_unhealthy_status(self):
        """Test creating an unhealthy status."""
        status = EngineHealthStatus(
            engine_name="test-engine",
            is_healthy=False,
            error_message="Connection refused"
        )
        
        assert status.engine_name == "test-engine"
        assert status.is_healthy is False
        assert status.error_message == "Connection refused"
        assert status.response_time_ms is None


class TestBenchmarkConfig:
    """Test cases for BenchmarkConfig model."""
    
    def test_valid_benchmark_config(self):
        """Test creating a valid benchmark configuration."""
        engine_config = EngineConfig(
            name="test-engine",
            engine_type="ollama",
            base_url="http://localhost:11434",
            health_endpoint="/api/tags"
        )
        
        config = BenchmarkConfig(engines=[engine_config])
        
        assert len(config.engines) == 1
        assert config.engines[0].name == "test-engine"
        assert config.log_level == "INFO"  # default
        assert config.export_format == "json"  # default
    
    def test_get_engine_by_name(self):
        """Test getting engine by name."""
        engine1 = EngineConfig(
            name="engine1",
            engine_type="ollama",
            base_url="http://localhost:11434",
            health_endpoint="/api/tags"
        )
        engine2 = EngineConfig(
            name="engine2",
            engine_type="vllm",
            base_url="http://localhost:8000",
            health_endpoint="/health"
        )
        
        config = BenchmarkConfig(engines=[engine1, engine2])
        
        found_engine = config.get_engine_by_name("engine1")
        assert found_engine is not None
        assert found_engine.name == "engine1"
        
        not_found = config.get_engine_by_name("nonexistent")
        assert not_found is None
    
    def test_get_engines_by_type(self):
        """Test getting engines by type."""
        ollama_engine = EngineConfig(
            name="ollama1",
            engine_type="ollama",
            base_url="http://localhost:11434",
            health_endpoint="/api/tags"
        )
        vllm_engine = EngineConfig(
            name="vllm1",
            engine_type="vllm",
            base_url="http://localhost:8000",
            health_endpoint="/health"
        )
        
        config = BenchmarkConfig(engines=[ollama_engine, vllm_engine])
        
        ollama_engines = config.get_engines_by_type("ollama")
        assert len(ollama_engines) == 1
        assert ollama_engines[0].name == "ollama1"
        
        tgi_engines = config.get_engines_by_type("tgi")
        assert len(tgi_engines) == 0

