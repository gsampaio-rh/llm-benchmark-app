"""
Metrics data models for the benchmarking tool.

This module defines Pydantic models for collecting, parsing, and standardizing
metrics from different LLM engines.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


class RawEngineMetrics(BaseModel):
    """Raw metrics data collected from an engine response."""
    
    model_config = ConfigDict(extra='allow')
    
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    engine_name: str = Field(..., description="Name of the engine that generated this response")
    engine_type: str = Field(..., description="Type of engine (ollama, vllm, tgi)")
    model_name: str = Field(..., description="Name of the model used")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the request was made")
    prompt: str = Field(..., description="The input prompt")
    response: str = Field(..., description="The generated response")
    raw_response: Dict[str, Any] = Field(..., description="Complete raw response from the engine")
    request_duration_ms: Optional[float] = Field(default=None, description="Total request duration in milliseconds")
    
    def __str__(self) -> str:
        """String representation of raw metrics."""
        return f"RawMetrics({self.engine_name}, {self.model_name}, {self.request_id[:8]})"


class ParsedMetrics(BaseModel):
    """Standardized metrics parsed from engine responses."""
    
    model_config = ConfigDict(extra='forbid')
    
    request_id: str = Field(..., description="Unique request identifier")
    engine_name: str = Field(..., description="Name of the engine")
    engine_type: str = Field(..., description="Type of engine")
    model_name: str = Field(..., description="Name of the model used")
    timestamp: datetime = Field(..., description="When the request was made")
    
    # Per-Request Runtime Metrics (from METRICS.md)
    load_duration: Optional[float] = Field(
        default=None, 
        description="Setup time before prompt evaluation (seconds)"
    )
    prompt_eval_count: Optional[int] = Field(
        default=None, 
        description="Number of input tokens processed"
    )
    prompt_eval_duration: Optional[float] = Field(
        default=None, 
        description="Time spent processing input tokens (seconds)"
    )
    prompt_token_rate: Optional[float] = Field(
        default=None, 
        description="Input tokens processed per second"
    )
    eval_count: Optional[int] = Field(
        default=None, 
        description="Number of output tokens generated"
    )
    eval_duration: Optional[float] = Field(
        default=None, 
        description="Time spent generating output tokens (seconds)"
    )
    response_token_rate: Optional[float] = Field(
        default=None, 
        description="Output tokens per second"
    )
    total_duration: Optional[float] = Field(
        default=None, 
        description="Total request runtime (seconds)"
    )
    
    # Latency Metrics
    first_token_latency: Optional[float] = Field(
        default=None, 
        description="Time to first output token (seconds)"
    )
    inter_token_latency: Optional[float] = Field(
        default=None, 
        description="Average time per generated token (seconds)"
    )
    
    # Additional metrics from METRICS.md
    queueing_time: Optional[float] = Field(
        default=None,
        description="Time request waits before execution (seconds)"
    )
    
    # Request Timing
    request_start: Optional[datetime] = Field(
        default=None, 
        description="When the request started"
    )
    first_token_time: Optional[datetime] = Field(
        default=None, 
        description="When the first token was received"
    )
    completion_time: Optional[datetime] = Field(
        default=None, 
        description="When the request completed"
    )
    
    # Success/Error Information
    success: bool = Field(default=True, description="Whether the request succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if request failed")
    error_type: Optional[str] = Field(default=None, description="Type of error if request failed")
    
    def calculate_derived_metrics(self) -> None:
        """Calculate derived metrics from base measurements."""
        # Calculate token rates if we have the data
        if self.prompt_eval_count and self.prompt_eval_duration and self.prompt_eval_duration > 0:
            self.prompt_token_rate = self.prompt_eval_count / self.prompt_eval_duration
        
        if self.eval_count and self.eval_duration and self.eval_duration > 0:
            self.response_token_rate = self.eval_count / self.eval_duration
        
        # Calculate inter-token latency
        if self.eval_count and self.eval_duration and self.eval_count > 0:
            self.inter_token_latency = self.eval_duration / self.eval_count
        
        # Calculate first token latency from timestamps if not already set
        if not self.first_token_latency and self.request_start and self.first_token_time:
            delta = self.first_token_time - self.request_start
            self.first_token_latency = delta.total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return self.model_dump(exclude_none=True)


class AggregateMetrics(BaseModel):
    """Aggregated metrics across multiple requests."""
    
    model_config = ConfigDict(extra='forbid')
    
    engine_name: str = Field(..., description="Name of the engine")
    engine_type: str = Field(..., description="Type of engine")
    model_name: Optional[str] = Field(default=None, description="Model name if single model")
    aggregation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When aggregation was performed")
    
    # Request Statistics
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    success_rate: float = Field(..., description="Success rate (0.0 to 1.0)")
    
    # Throughput Metrics
    aggregate_tps: Optional[float] = Field(
        default=None, 
        description="Total tokens per second across all requests"
    )
    requests_per_second: Optional[float] = Field(
        default=None, 
        description="Requests per second"
    )
    
    # Latency Distribution
    latency_p50: Optional[float] = Field(default=None, description="50th percentile latency (seconds)")
    latency_p95: Optional[float] = Field(default=None, description="95th percentile latency (seconds)")
    latency_p99: Optional[float] = Field(default=None, description="99th percentile latency (seconds)")
    latency_mean: Optional[float] = Field(default=None, description="Mean latency (seconds)")
    latency_std: Optional[float] = Field(default=None, description="Standard deviation of latency")
    
    # Token Statistics
    total_input_tokens: Optional[int] = Field(default=None, description="Total input tokens processed")
    total_output_tokens: Optional[int] = Field(default=None, description="Total output tokens generated")
    mean_input_tokens: Optional[float] = Field(default=None, description="Mean input tokens per request")
    mean_output_tokens: Optional[float] = Field(default=None, description="Mean output tokens per request")
    
    # Error Breakdown
    error_breakdown: Optional[Dict[str, int]] = Field(
        default=None, 
        description="Count of errors by type"
    )
    timeout_count: int = Field(default=0, description="Number of timeout errors")
    
    # Time Range
    start_time: Optional[datetime] = Field(default=None, description="Start of measurement period")
    end_time: Optional[datetime] = Field(default=None, description="End of measurement period")
    duration_seconds: Optional[float] = Field(default=None, description="Total measurement duration")


class MetricsCollection(BaseModel):
    """Collection of metrics for export and analysis."""
    
    model_config = ConfigDict(extra='forbid')
    
    collection_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique collection identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When collection was created")
    description: Optional[str] = Field(default=None, description="Description of this metrics collection")
    
    raw_metrics: List[RawEngineMetrics] = Field(default_factory=list, description="Raw metrics data")
    parsed_metrics: List[ParsedMetrics] = Field(default_factory=list, description="Parsed metrics data")
    aggregate_metrics: List[AggregateMetrics] = Field(default_factory=list, description="Aggregated metrics")
    
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    def add_raw_metrics(self, metrics: RawEngineMetrics) -> None:
        """Add raw metrics to the collection."""
        self.raw_metrics.append(metrics)
    
    def add_parsed_metrics(self, metrics: ParsedMetrics) -> None:
        """Add parsed metrics to the collection."""
        self.parsed_metrics.append(metrics)
    
    def add_aggregate_metrics(self, metrics: AggregateMetrics) -> None:
        """Add aggregate metrics to the collection."""
        self.aggregate_metrics.append(metrics)
    
    def get_metrics_by_engine(self, engine_name: str) -> List[ParsedMetrics]:
        """Get all parsed metrics for a specific engine."""
        return [m for m in self.parsed_metrics if m.engine_name == engine_name]
    
    def get_successful_metrics(self) -> List[ParsedMetrics]:
        """Get only successful metrics."""
        return [m for m in self.parsed_metrics if m.success]
    
    def get_failed_metrics(self) -> List[ParsedMetrics]:
        """Get only failed metrics."""
        return [m for m in self.parsed_metrics if not m.success]
    
    def export_summary(self) -> Dict[str, Any]:
        """Export a summary of the metrics collection."""
        return {
            "collection_id": self.collection_id,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "total_raw_metrics": len(self.raw_metrics),
            "total_parsed_metrics": len(self.parsed_metrics),
            "total_aggregate_metrics": len(self.aggregate_metrics),
            "engines": list(set(m.engine_name for m in self.parsed_metrics)),
            "models": list(set(m.model_name for m in self.parsed_metrics)),
            "success_rate": (
                len(self.get_successful_metrics()) / len(self.parsed_metrics)
                if self.parsed_metrics else 0.0
            ),
            "metadata": self.metadata
        }


class RequestResult(BaseModel):
    """Result of a single request to an engine."""
    
    model_config = ConfigDict(extra='allow')
    
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    engine_name: str = Field(..., description="Name of the engine")
    model_name: str = Field(..., description="Name of the model used")
    prompt: str = Field(..., description="The input prompt")
    response: Optional[str] = Field(default=None, description="The generated response")
    success: bool = Field(..., description="Whether the request succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if request failed")
    raw_metrics: Optional[RawEngineMetrics] = Field(default=None, description="Raw metrics from the engine")
    parsed_metrics: Optional[ParsedMetrics] = Field(default=None, description="Parsed and standardized metrics")
    
    @classmethod
    def success_result(
        cls, 
        engine_name: str, 
        model_name: str, 
        prompt: str, 
        response: str,
        raw_metrics: Optional[RawEngineMetrics] = None,
        parsed_metrics: Optional[ParsedMetrics] = None
    ) -> "RequestResult":
        """Create a successful request result."""
        return cls(
            engine_name=engine_name,
            model_name=model_name,
            prompt=prompt,
            response=response,
            success=True,
            raw_metrics=raw_metrics,
            parsed_metrics=parsed_metrics
        )
    
    @classmethod
    def error_result(
        cls, 
        engine_name: str, 
        model_name: str, 
        prompt: str, 
        error_message: str
    ) -> "RequestResult":
        """Create a failed request result."""
        return cls(
            engine_name=engine_name,
            model_name=model_name,
            prompt=prompt,
            success=False,
            error_message=error_message
        )

