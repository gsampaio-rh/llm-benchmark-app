"""
Unit tests for ExportManager.

Tests the enhanced export functionality including per-engine separation,
summary reports, and markdown generation.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
import pytest
from typing import List

from src.reporting.export_manager import ExportManager, ExportConfig, ExportResult
from src.models.metrics import (
    MetricsCollection,
    ParsedMetrics,
    RawEngineMetrics
)


@pytest.fixture
def sample_parsed_metrics() -> List[ParsedMetrics]:
    """Create sample parsed metrics for testing."""
    metrics = []
    
    # Ollama metrics
    for i in range(3):
        metrics.append(ParsedMetrics(
            request_id=f"ollama-{i}",
            engine_name="ollama",
            engine_type="ollama",
            model_name="llama3.2:3b",
            timestamp=datetime.utcnow(),
            load_duration=0.1,
            prompt_eval_count=10 + i,
            prompt_eval_duration=0.05,
            prompt_token_rate=200.0,
            eval_count=50 + i * 10,
            eval_duration=1.0 + i * 0.1,
            response_token_rate=50.0 + i * 5,
            total_duration=1.5 + i * 0.1,
            first_token_latency=0.12,
            inter_token_latency=0.02,
            success=True
        ))
    
    # vLLM metrics
    for i in range(3):
        metrics.append(ParsedMetrics(
            request_id=f"vllm-{i}",
            engine_name="vllm",
            engine_type="vllm",
            model_name="Qwen2.5-7B",
            timestamp=datetime.utcnow(),
            prompt_eval_count=12 + i,
            prompt_eval_duration=0.04,
            eval_count=60 + i * 10,
            eval_duration=0.8 + i * 0.1,
            response_token_rate=75.0 + i * 5,
            total_duration=1.2 + i * 0.1,
            first_token_latency=0.08,
            inter_token_latency=0.013,
            success=True
        ))
    
    # Add one failed request
    metrics.append(ParsedMetrics(
        request_id="failed-1",
        engine_name="ollama",
        engine_type="ollama",
        model_name="llama3.2:3b",
        timestamp=datetime.utcnow(),
        success=False,
        error_message="Connection timeout",
        error_type="timeout"
    ))
    
    return metrics


@pytest.fixture
def sample_collection(sample_parsed_metrics: List[ParsedMetrics]) -> MetricsCollection:
    """Create a sample metrics collection."""
    collection = MetricsCollection(
        description="Test benchmark run",
        metadata={"test": True}
    )
    
    for metric in sample_parsed_metrics:
        collection.add_parsed_metrics(metric)
        
        # Add corresponding raw metrics
        raw_metric = RawEngineMetrics(
            request_id=metric.request_id,
            engine_name=metric.engine_name,
            engine_type=metric.engine_type,
            model_name=metric.model_name,
            timestamp=metric.timestamp,
            prompt="Test prompt",
            response="Test response",
            raw_response={"test": "data"},
            request_duration_ms=1500.0
        )
        collection.add_raw_metrics(raw_metric)
    
    return collection


@pytest.fixture
def export_manager(tmp_path: Path) -> ExportManager:
    """Create an ExportManager with temporary output directory."""
    config = ExportConfig(
        output_dir=str(tmp_path / "exports"),
        create_timestamp_dir=True,
        generate_markdown=True,
        generate_csv=True,
        generate_json=True
    )
    return ExportManager(config)


def test_export_manager_initialization() -> None:
    """Test ExportManager initialization."""
    config = ExportConfig()
    manager = ExportManager(config)
    
    assert manager.config == config
    assert manager.logger is not None


def test_export_manager_default_config() -> None:
    """Test ExportManager with default configuration."""
    manager = ExportManager()
    
    assert manager.config.output_dir == "benchmark_results"
    assert manager.config.create_timestamp_dir is True
    assert manager.config.generate_markdown is True
    assert manager.config.generate_csv is True
    assert manager.config.generate_json is True


def test_export_collection_success(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test successful export of a metrics collection."""
    result = export_manager.export_collection(
        collection=sample_collection,
        description="Test Export",
        scenario="test_scenario"
    )
    
    assert result.success is True
    assert result.export_dir.exists()
    assert len(result.files_created) > 0
    assert result.error_message is None
    
    # Check that summary stats are included
    assert "total_engines" in result.summary_stats
    assert "engines" in result.summary_stats
    assert "ollama" in result.summary_stats["engines"]
    assert "vllm" in result.summary_stats["engines"]


def test_export_creates_timestamped_directory(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test that export creates timestamped directory."""
    result = export_manager.export_collection(sample_collection)
    
    assert result.success is True
    assert result.export_dir.name.startswith("run_")
    assert len(result.export_dir.name) == 19  # run_YYYYMMDD_HHMMSS


def test_export_per_engine_files(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test that per-engine files are created."""
    result = export_manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Check for ollama files
    ollama_json = result.export_dir / "ollama_results.json"
    ollama_csv = result.export_dir / "ollama_results.csv"
    assert ollama_json.exists()
    assert ollama_csv.exists()
    
    # Check for vllm files
    vllm_json = result.export_dir / "vllm_results.json"
    vllm_csv = result.export_dir / "vllm_results.csv"
    assert vllm_json.exists()
    assert vllm_csv.exists()


def test_export_summary_files(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test that summary files are created."""
    result = export_manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Check for summary files
    summary_json = result.export_dir / "summary.json"
    summary_csv = result.export_dir / "summary.csv"
    assert summary_json.exists()
    assert summary_csv.exists()


def test_export_markdown_report(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test that markdown report is created."""
    result = export_manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Check for markdown report
    report_md = result.export_dir / "report.md"
    assert report_md.exists()
    
    # Check content
    content = report_md.read_text()
    assert "# Benchmark Results Report" in content
    assert "## Executive Summary" in content
    assert "## Detailed Results" in content
    assert "ollama" in content
    assert "vllm" in content


def test_engine_json_content(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test content of per-engine JSON export."""
    result = export_manager.export_collection(sample_collection)
    
    ollama_json = result.export_dir / "ollama_results.json"
    with open(ollama_json, 'r') as f:
        data = json.load(f)
    
    # Check structure
    assert "engine_name" in data
    assert data["engine_name"] == "ollama"
    assert "export_timestamp" in data
    assert "total_requests" in data
    assert "successful_requests" in data
    assert "failed_requests" in data
    assert "success_rate" in data
    assert "statistics" in data
    assert "metrics" in data
    
    # Check statistics
    stats = data["statistics"]
    assert "latency" in stats
    assert "throughput" in stats
    assert "tokens" in stats
    
    # Check latency stats
    assert "mean" in stats["latency"]
    assert "p50" in stats["latency"]
    assert "p95" in stats["latency"]
    assert "p99" in stats["latency"]
    assert "std_dev" in stats["latency"]


def test_engine_csv_content(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test content of per-engine CSV export."""
    result = export_manager.export_collection(sample_collection)
    
    ollama_csv = result.export_dir / "ollama_results.csv"
    with open(ollama_csv, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Check that we have rows
    assert len(rows) > 0
    
    # Check headers
    first_row = rows[0]
    assert "request_id" in first_row
    assert "engine" in first_row
    assert "model" in first_row
    assert "scenario" in first_row
    assert "prompt_tokens" in first_row
    assert "completion_tokens" in first_row
    assert "total_duration_sec" in first_row
    assert "ttft_sec" in first_row
    assert "tokens_per_sec" in first_row
    assert "success" in first_row


def test_summary_json_content(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test content of summary JSON export."""
    result = export_manager.export_collection(
        sample_collection,
        description="Test Summary",
        scenario="test_scenario"
    )
    
    summary_json = result.export_dir / "summary.json"
    with open(summary_json, 'r') as f:
        data = json.load(f)
    
    # Check structure
    assert "description" in data
    assert data["description"] == "Test Summary"
    assert "scenario" in data
    assert data["scenario"] == "test_scenario"
    assert "collection_id" in data
    assert "export_timestamp" in data
    assert "engines" in data
    
    # Check engine summaries
    engines = data["engines"]
    assert "ollama" in engines
    assert "vllm" in engines
    
    # Check ollama summary
    ollama = engines["ollama"]
    assert "total_requests" in ollama
    assert "successful_requests" in ollama
    assert "failed_requests" in ollama
    assert "success_rate" in ollama
    assert "statistics" in ollama


def test_summary_csv_content(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test content of summary CSV export."""
    result = export_manager.export_collection(sample_collection)
    
    summary_csv = result.export_dir / "summary.csv"
    with open(summary_csv, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Check that we have rows for each engine
    assert len(rows) >= 2  # At least ollama and vllm
    
    # Check headers
    first_row = rows[0]
    assert "engine" in first_row
    assert "model" in first_row
    assert "scenario" in first_row
    assert "requests" in first_row
    assert "success_rate" in first_row
    assert "mean_latency_sec" in first_row
    assert "p50_latency_sec" in first_row
    assert "p95_latency_sec" in first_row
    assert "p99_latency_sec" in first_row
    assert "mean_tokens_per_sec" in first_row


def test_statistical_calculations(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test that statistical calculations are correct."""
    result = export_manager.export_collection(sample_collection)
    
    # Load ollama JSON to check stats
    ollama_json = result.export_dir / "ollama_results.json"
    with open(ollama_json, 'r') as f:
        data = json.load(f)
    
    stats = data["statistics"]
    
    # Check that percentiles are in order
    latency = stats["latency"]
    assert latency["min"] <= latency["p50"]
    assert latency["p50"] <= latency["p95"]
    assert latency["p95"] <= latency["p99"]
    assert latency["p99"] <= latency["max"]
    
    # Check that std_dev is non-negative
    assert latency["std_dev"] >= 0


def test_export_without_markdown(
    tmp_path: Path,
    sample_collection: MetricsCollection
) -> None:
    """Test export without markdown generation."""
    config = ExportConfig(
        output_dir=str(tmp_path / "exports"),
        create_timestamp_dir=True,
        generate_markdown=False,
        generate_csv=True,
        generate_json=True
    )
    manager = ExportManager(config)
    
    result = manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Check that markdown is not created
    report_md = result.export_dir / "report.md"
    assert not report_md.exists()


def test_export_without_csv(
    tmp_path: Path,
    sample_collection: MetricsCollection
) -> None:
    """Test export without CSV generation."""
    config = ExportConfig(
        output_dir=str(tmp_path / "exports"),
        create_timestamp_dir=True,
        generate_markdown=True,
        generate_csv=False,
        generate_json=True
    )
    manager = ExportManager(config)
    
    result = manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Check that CSV files are not created
    csv_files = list(result.export_dir.glob("*.csv"))
    assert len(csv_files) == 0


def test_export_without_json(
    tmp_path: Path,
    sample_collection: MetricsCollection
) -> None:
    """Test export without JSON generation."""
    config = ExportConfig(
        output_dir=str(tmp_path / "exports"),
        create_timestamp_dir=True,
        generate_markdown=True,
        generate_csv=True,
        generate_json=False
    )
    manager = ExportManager(config)
    
    result = manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Check that JSON files are not created
    json_files = list(result.export_dir.glob("*.json"))
    assert len(json_files) == 0


def test_export_handles_failed_requests(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test that export properly handles failed requests."""
    result = export_manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Load ollama JSON
    ollama_json = result.export_dir / "ollama_results.json"
    with open(ollama_json, 'r') as f:
        data = json.load(f)
    
    # Check that failed requests are counted
    assert data["failed_requests"] > 0
    assert data["success_rate"] < 1.0
    
    # Check that failed request is in metrics
    metrics = data["metrics"]
    failed_metrics = [m for m in metrics if not m["success"]]
    assert len(failed_metrics) == 1
    assert failed_metrics[0]["error_message"] == "Connection timeout"


def test_export_empty_collection(
    export_manager: ExportManager
) -> None:
    """Test export with empty collection."""
    empty_collection = MetricsCollection(description="Empty test")
    
    result = export_manager.export_collection(empty_collection)
    
    # Should still succeed but with no engine-specific files
    assert result.success is True
    assert result.export_dir.exists()


def test_export_without_timestamp_dir(
    tmp_path: Path,
    sample_collection: MetricsCollection
) -> None:
    """Test export without timestamped directory."""
    config = ExportConfig(
        output_dir=str(tmp_path / "exports"),
        create_timestamp_dir=False
    )
    manager = ExportManager(config)
    
    result = manager.export_collection(sample_collection)
    
    assert result.success is True
    assert result.export_dir == Path(config.output_dir)
    assert not result.export_dir.name.startswith("run_")


def test_export_result_structure() -> None:
    """Test ExportResult dataclass structure."""
    result = ExportResult(
        export_dir=Path("/tmp/test"),
        files_created=[Path("/tmp/test/file1.json")],
        summary_stats={"test": "data"},
        success=True
    )
    
    assert result.export_dir == Path("/tmp/test")
    assert len(result.files_created) == 1
    assert result.summary_stats == {"test": "data"}
    assert result.success is True
    assert result.error_message is None


def test_export_config_validation() -> None:
    """Test ExportConfig validation."""
    # Test valid config
    config = ExportConfig(
        output_dir="test_dir",
        create_timestamp_dir=True,
        generate_markdown=True,
        generate_csv=True,
        generate_json=True
    )
    
    assert config.output_dir == "test_dir"
    assert config.create_timestamp_dir is True
    
    # Test that extra fields are not allowed
    with pytest.raises(Exception):
        ExportConfig(invalid_field="test")


def test_export_sanitizes_engine_names(
    export_manager: ExportManager,
    sample_collection: MetricsCollection
) -> None:
    """Test that engine names are sanitized for filenames."""
    # Add a metric with special characters in engine name
    special_metric = ParsedMetrics(
        request_id="special-1",
        engine_name="engine/with spaces",
        engine_type="test",
        model_name="test-model",
        timestamp=datetime.utcnow(),
        success=True
    )
    sample_collection.add_parsed_metrics(special_metric)
    
    result = export_manager.export_collection(sample_collection)
    
    assert result.success is True
    
    # Check that special characters are replaced
    special_files = [f for f in result.files_created if "engine_with_spaces" in str(f)]
    assert len(special_files) > 0

