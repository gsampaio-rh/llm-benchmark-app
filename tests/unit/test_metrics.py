"""Unit tests for metrics models."""

import pytest
from datetime import datetime, timedelta
from src.models.metrics import (
    RawEngineMetrics, 
    ParsedMetrics, 
    AggregateMetrics, 
    MetricsCollection,
    RequestResult
)


class TestRawEngineMetrics:
    """Test cases for RawEngineMetrics model."""
    
    def test_create_raw_metrics(self):
        """Test creating raw engine metrics."""
        raw_response = {
            "model": "llama2",
            "response": "Hello, world!",
            "total_duration": 1500000000,  # nanoseconds
            "load_duration": 100000000,
            "prompt_eval_count": 5,
            "prompt_eval_duration": 200000000,
            "eval_count": 3,
            "eval_duration": 300000000
        }
        
        metrics = RawEngineMetrics(
            engine_name="test-ollama",
            engine_type="ollama",
            model_name="llama2",
            prompt="Hello",
            response="Hello, world!",
            raw_response=raw_response
        )
        
        assert metrics.engine_name == "test-ollama"
        assert metrics.engine_type == "ollama"
        assert metrics.model_name == "llama2"
        assert metrics.prompt == "Hello"
        assert metrics.response == "Hello, world!"
        assert metrics.raw_response == raw_response
        assert metrics.request_id is not None
        assert isinstance(metrics.timestamp, datetime)
    
    def test_string_representation(self):
        """Test string representation of raw metrics."""
        metrics = RawEngineMetrics(
            engine_name="test-engine",
            engine_type="ollama",
            model_name="test-model",
            prompt="test",
            response="response",
            raw_response={}
        )
        
        str_repr = str(metrics)
        assert "test-engine" in str_repr
        assert "test-model" in str_repr
        assert metrics.request_id[:8] in str_repr


class TestParsedMetrics:
    """Test cases for ParsedMetrics model."""
    
    def test_create_parsed_metrics(self):
        """Test creating parsed metrics."""
        now = datetime.utcnow()
        
        metrics = ParsedMetrics(
            request_id="test-123",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=now,
            prompt_eval_count=10,
            prompt_eval_duration=0.5,
            eval_count=5,
            eval_duration=0.3,
            total_duration=1.0
        )
        
        assert metrics.request_id == "test-123"
        assert metrics.engine_name == "test-engine"
        assert metrics.prompt_eval_count == 10
        assert metrics.eval_count == 5
        assert metrics.success is True  # default
    
    def test_calculate_derived_metrics(self):
        """Test calculation of derived metrics."""
        metrics = ParsedMetrics(
            request_id="test-123",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=datetime.utcnow(),
            prompt_eval_count=10,
            prompt_eval_duration=0.5,  # 0.5 seconds
            eval_count=5,
            eval_duration=0.25,  # 0.25 seconds
        )
        
        metrics.calculate_derived_metrics()
        
        # Check calculated rates
        assert metrics.prompt_token_rate == 20.0  # 10 tokens / 0.5 seconds
        assert metrics.response_token_rate == 20.0  # 5 tokens / 0.25 seconds
        assert metrics.inter_token_latency == 0.05  # 0.25 seconds / 5 tokens
    
    def test_calculate_first_token_latency(self):
        """Test calculation of first token latency from timestamps."""
        start_time = datetime.utcnow()
        first_token_time = start_time + timedelta(milliseconds=150)
        
        metrics = ParsedMetrics(
            request_id="test-123",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=start_time,
            request_start=start_time,
            first_token_time=first_token_time
        )
        
        metrics.calculate_derived_metrics()
        
        assert abs(metrics.first_token_latency - 0.15) < 0.001  # ~150ms
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ParsedMetrics(
            request_id="test-123",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=datetime.utcnow(),
            total_duration=1.5
        )
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["request_id"] == "test-123"
        assert metrics_dict["engine_name"] == "test-engine"
        assert metrics_dict["total_duration"] == 1.5
        # None values should be excluded
        assert "load_duration" not in metrics_dict


class TestAggregateMetrics:
    """Test cases for AggregateMetrics model."""
    
    def test_create_aggregate_metrics(self):
        """Test creating aggregate metrics."""
        metrics = AggregateMetrics(
            engine_name="test-engine",
            engine_type="ollama",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            success_rate=0.95,
            latency_p50=0.5,
            latency_p95=1.2,
            latency_p99=2.0
        )
        
        assert metrics.engine_name == "test-engine"
        assert metrics.total_requests == 100
        assert metrics.success_rate == 0.95
        assert metrics.latency_p50 == 0.5
        assert isinstance(metrics.aggregation_timestamp, datetime)


class TestMetricsCollection:
    """Test cases for MetricsCollection model."""
    
    def test_create_empty_collection(self):
        """Test creating an empty metrics collection."""
        collection = MetricsCollection()
        
        assert collection.collection_id is not None
        assert isinstance(collection.created_at, datetime)
        assert len(collection.raw_metrics) == 0
        assert len(collection.parsed_metrics) == 0
        assert len(collection.aggregate_metrics) == 0
    
    def test_add_metrics(self):
        """Test adding metrics to collection."""
        collection = MetricsCollection()
        
        # Add raw metrics
        raw_metrics = RawEngineMetrics(
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            prompt="test",
            response="response",
            raw_response={}
        )
        collection.add_raw_metrics(raw_metrics)
        
        # Add parsed metrics
        parsed_metrics = ParsedMetrics(
            request_id="test-123",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=datetime.utcnow()
        )
        collection.add_parsed_metrics(parsed_metrics)
        
        assert len(collection.raw_metrics) == 1
        assert len(collection.parsed_metrics) == 1
    
    def test_get_metrics_by_engine(self):
        """Test filtering metrics by engine."""
        collection = MetricsCollection()
        
        # Add metrics for different engines
        metrics1 = ParsedMetrics(
            request_id="test-1",
            engine_name="engine1",
            engine_type="ollama",
            model_name="llama2",
            timestamp=datetime.utcnow()
        )
        metrics2 = ParsedMetrics(
            request_id="test-2",
            engine_name="engine2",
            engine_type="vllm",
            model_name="llama2",
            timestamp=datetime.utcnow()
        )
        
        collection.add_parsed_metrics(metrics1)
        collection.add_parsed_metrics(metrics2)
        
        engine1_metrics = collection.get_metrics_by_engine("engine1")
        assert len(engine1_metrics) == 1
        assert engine1_metrics[0].engine_name == "engine1"
    
    def test_get_successful_and_failed_metrics(self):
        """Test filtering by success status."""
        collection = MetricsCollection()
        
        # Add successful metrics
        success_metrics = ParsedMetrics(
            request_id="success-1",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=datetime.utcnow(),
            success=True
        )
        
        # Add failed metrics
        failed_metrics = ParsedMetrics(
            request_id="failed-1",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=datetime.utcnow(),
            success=False,
            error_message="Test error"
        )
        
        collection.add_parsed_metrics(success_metrics)
        collection.add_parsed_metrics(failed_metrics)
        
        successful = collection.get_successful_metrics()
        failed = collection.get_failed_metrics()
        
        assert len(successful) == 1
        assert len(failed) == 1
        assert successful[0].success is True
        assert failed[0].success is False
    
    def test_export_summary(self):
        """Test exporting collection summary."""
        collection = MetricsCollection(description="Test collection")
        
        # Add some metrics
        metrics = ParsedMetrics(
            request_id="test-1",
            engine_name="test-engine",
            engine_type="ollama",
            model_name="llama2",
            timestamp=datetime.utcnow(),
            success=True
        )
        collection.add_parsed_metrics(metrics)
        
        summary = collection.export_summary()
        
        assert summary["collection_id"] == collection.collection_id
        assert summary["description"] == "Test collection"
        assert summary["total_parsed_metrics"] == 1
        assert summary["success_rate"] == 1.0
        assert "test-engine" in summary["engines"]
        assert "llama2" in summary["models"]


class TestRequestResult:
    """Test cases for RequestResult model."""
    
    def test_success_result(self):
        """Test creating a successful request result."""
        result = RequestResult.success_result(
            engine_name="test-engine",
            model_name="llama2",
            prompt="Hello",
            response="Hello, world!"
        )
        
        assert result.success is True
        assert result.engine_name == "test-engine"
        assert result.model_name == "llama2"
        assert result.prompt == "Hello"
        assert result.response == "Hello, world!"
        assert result.error_message is None
    
    def test_error_result(self):
        """Test creating a failed request result."""
        result = RequestResult.error_result(
            engine_name="test-engine",
            model_name="llama2",
            prompt="Hello",
            error_message="Connection failed"
        )
        
        assert result.success is False
        assert result.engine_name == "test-engine"
        assert result.error_message == "Connection failed"
        assert result.response is None

