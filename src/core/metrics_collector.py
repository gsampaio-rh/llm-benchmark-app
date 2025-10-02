"""
Metrics collection system for the benchmarking tool.

This module provides centralized metrics collection, aggregation,
and export functionality across all engine adapters.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import csv
from pathlib import Path

from ..models.metrics import (
    RawEngineMetrics, 
    ParsedMetrics, 
    AggregateMetrics, 
    MetricsCollection,
    RequestResult
)
from ..adapters.base_adapter import BaseAdapter
from .connection_manager import ConnectionManager


logger = logging.getLogger(__name__)


class MetricsCollectionError(Exception):
    """Raised when metrics collection operations fail."""
    pass


class MetricsCollector:
    """
    Centralized metrics collection and aggregation system.
    
    Provides functionality to collect metrics from single requests,
    aggregate results, and export in various formats.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the metrics collector.
        
        Args:
            connection_manager: Connection manager instance for engine access
        """
        self.connection_manager = connection_manager
        self.current_collection: Optional[MetricsCollection] = None
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Initialized metrics collector")
    
    def start_collection(self, description: Optional[str] = None) -> str:
        """
        Start a new metrics collection session.
        
        Args:
            description: Optional description for this collection
            
        Returns:
            Collection ID
        """
        self.current_collection = MetricsCollection(description=description)
        self.logger.info(f"Started metrics collection: {self.current_collection.collection_id}")
        return self.current_collection.collection_id
    
    async def collect_single_request_metrics(
        self, 
        engine_name: str, 
        prompt: str, 
        model: str,
        **kwargs
    ) -> RequestResult:
        """
        Collect metrics from a single request to an engine.
        
        Args:
            engine_name: Name of the engine to use
            prompt: Input prompt text
            model: Model name to use
            **kwargs: Additional engine-specific parameters
            
        Returns:
            RequestResult with response and metrics
            
        Raises:
            MetricsCollectionError: If collection fails
        """
        if not self.current_collection:
            raise MetricsCollectionError("No active collection. Call start_collection() first.")
        
        try:
            # Get adapter for the engine
            adapter = self.connection_manager.get_adapter(engine_name)
            if not adapter:
                raise MetricsCollectionError(f"Engine not found: {engine_name}")
            
            # Send request and collect metrics
            self.logger.debug(f"Collecting metrics for {engine_name} with prompt: {prompt[:50]}...")
            result = await adapter.send_single_request(prompt, model, **kwargs)
            
            # Add metrics to collection
            if result.raw_metrics:
                self.current_collection.add_raw_metrics(result.raw_metrics)
            
            if result.parsed_metrics:
                self.current_collection.add_parsed_metrics(result.parsed_metrics)
            
            self.logger.info(f"Collected metrics for {engine_name}: success={result.success}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics from {engine_name}: {e}")
            raise MetricsCollectionError(f"Failed to collect metrics from {engine_name}: {e}")
    
    async def collect_streaming_request_metrics(
        self,
        engine_name: str,
        prompt: str,
        model: str,
        token_callback: Optional[Any] = None,
        **kwargs
    ) -> RequestResult:
        """
        Collect metrics from a streaming request to an engine with real-time token delivery.
        
        Args:
            engine_name: Name of the engine to use
            prompt: Input prompt text
            model: Model name to use
            token_callback: Async callback for each token: async def(token: str) -> None
            **kwargs: Additional engine-specific parameters
            
        Returns:
            RequestResult with response and metrics
            
        Raises:
            MetricsCollectionError: If collection fails
        """
        if not self.current_collection:
            raise MetricsCollectionError("No active collection. Call start_collection() first.")
        
        try:
            # Get adapter for the engine
            adapter = self.connection_manager.get_adapter(engine_name)
            if not adapter:
                raise MetricsCollectionError(f"Engine not found: {engine_name}")
            
            # Send streaming request and collect metrics
            self.logger.debug(f"Collecting streaming metrics for {engine_name} with prompt: {prompt[:50]}...")
            result = await adapter.send_streaming_request(prompt, model, token_callback, **kwargs)
            
            # Add metrics to collection
            if result.raw_metrics:
                self.current_collection.add_raw_metrics(result.raw_metrics)
            
            if result.parsed_metrics:
                self.current_collection.add_parsed_metrics(result.parsed_metrics)
            
            self.logger.info(f"Collected streaming metrics for {engine_name}: success={result.success}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to collect streaming metrics from {engine_name}: {e}")
            raise MetricsCollectionError(f"Failed to collect streaming metrics from {engine_name}: {e}")
    
    async def collect_concurrent_metrics(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[RequestResult]:
        """
        Collect metrics from multiple concurrent requests.
        
        Args:
            requests: List of request dictionaries with keys:
                     - engine_name: str
                     - prompt: str  
                     - model: str
                     - kwargs: dict (optional)
            max_concurrent: Maximum number of concurrent requests
            
        Returns:
            List of RequestResult objects
            
        Raises:
            MetricsCollectionError: If collection fails
        """
        if not self.current_collection:
            raise MetricsCollectionError("No active collection. Call start_collection() first.")
        
        if not requests:
            return []
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def _collect_single(request_info: Dict[str, Any]) -> RequestResult:
            async with semaphore:
                return await self.collect_single_request_metrics(
                    engine_name=request_info["engine_name"],
                    prompt=request_info["prompt"],
                    model=request_info["model"],
                    **request_info.get("kwargs", {})
                )
        
        # Execute all requests concurrently
        self.logger.info(f"Starting concurrent collection of {len(requests)} requests")
        tasks = [_collect_single(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Request {i} failed: {result}")
                # Create error result
                req_info = requests[i]
                error_result = RequestResult.error_result(
                    engine_name=req_info["engine_name"],
                    model_name=req_info["model"],
                    prompt=req_info["prompt"],
                    error_message=str(result)
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        successful = sum(1 for r in processed_results if r.success)
        self.logger.info(f"Concurrent collection completed: {successful}/{len(requests)} successful")
        
        return processed_results
    
    def aggregate_metrics(self, engine_name: Optional[str] = None) -> List[AggregateMetrics]:
        """
        Aggregate collected metrics by engine.
        
        Args:
            engine_name: Optional engine name to filter by
            
        Returns:
            List of AggregateMetrics objects
            
        Raises:
            MetricsCollectionError: If no collection is active
        """
        if not self.current_collection:
            raise MetricsCollectionError("No active collection. Call start_collection() first.")
        
        # Get metrics to aggregate
        if engine_name:
            metrics_by_engine = {engine_name: self.current_collection.get_metrics_by_engine(engine_name)}
        else:
            # Group by engine
            metrics_by_engine = {}
            for metric in self.current_collection.parsed_metrics:
                engine = metric.engine_name
                if engine not in metrics_by_engine:
                    metrics_by_engine[engine] = []
                metrics_by_engine[engine].append(metric)
        
        aggregate_results = []
        
        for engine, metrics_list in metrics_by_engine.items():
            if not metrics_list:
                continue
            
            # Filter successful metrics for calculations
            successful_metrics = [m for m in metrics_list if m.success]
            
            if not successful_metrics:
                # Create aggregate for failed requests only
                aggregate = AggregateMetrics(
                    engine_name=engine,
                    engine_type=metrics_list[0].engine_type,
                    total_requests=len(metrics_list),
                    successful_requests=0,
                    failed_requests=len(metrics_list),
                    success_rate=0.0
                )
                aggregate_results.append(aggregate)
                continue
            
            # Calculate aggregate statistics
            latencies = [m.total_duration for m in successful_metrics if m.total_duration]
            input_tokens = [m.prompt_eval_count for m in successful_metrics if m.prompt_eval_count]
            output_tokens = [m.eval_count for m in successful_metrics if m.eval_count]
            
            # Calculate percentiles
            import numpy as np
            latency_p50 = np.percentile(latencies, 50) if latencies else None
            latency_p95 = np.percentile(latencies, 95) if latencies else None
            latency_p99 = np.percentile(latencies, 99) if latencies else None
            latency_mean = np.mean(latencies) if latencies else None
            latency_std = np.std(latencies) if latencies else None
            
            # Calculate throughput
            total_duration = sum(latencies) if latencies else 0
            total_output_tokens = sum(output_tokens) if output_tokens else 0
            aggregate_tps = total_output_tokens / total_duration if total_duration > 0 else None
            
            # Time range
            timestamps = [m.timestamp for m in successful_metrics]
            start_time = min(timestamps) if timestamps else None
            end_time = max(timestamps) if timestamps else None
            duration_seconds = (end_time - start_time).total_seconds() if start_time and end_time else None
            
            # Requests per second
            requests_per_second = len(successful_metrics) / duration_seconds if duration_seconds and duration_seconds > 0 else None
            
            # Error breakdown
            failed_metrics = [m for m in metrics_list if not m.success]
            error_breakdown = {}
            for failed_metric in failed_metrics:
                error_type = failed_metric.error_type or "unknown"
                error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1
            
            aggregate = AggregateMetrics(
                engine_name=engine,
                engine_type=successful_metrics[0].engine_type,
                total_requests=len(metrics_list),
                successful_requests=len(successful_metrics),
                failed_requests=len(failed_metrics),
                success_rate=len(successful_metrics) / len(metrics_list),
                aggregate_tps=aggregate_tps,
                requests_per_second=requests_per_second,
                latency_p50=latency_p50,
                latency_p95=latency_p95,
                latency_p99=latency_p99,
                latency_mean=latency_mean,
                latency_std=latency_std,
                total_input_tokens=sum(input_tokens) if input_tokens else None,
                total_output_tokens=sum(output_tokens) if output_tokens else None,
                mean_input_tokens=np.mean(input_tokens) if input_tokens else None,
                mean_output_tokens=np.mean(output_tokens) if output_tokens else None,
                error_breakdown=error_breakdown if error_breakdown else None,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds
            )
            
            # Add to collection
            self.current_collection.add_aggregate_metrics(aggregate)
            aggregate_results.append(aggregate)
        
        self.logger.info(f"Aggregated metrics for {len(aggregate_results)} engines")
        return aggregate_results
    
    def export_metrics(
        self, 
        output_path: str, 
        format: str = "json",
        include_raw: bool = True,
        include_parsed: bool = True,
        include_aggregate: bool = True
    ) -> Path:
        """
        Export collected metrics to file.
        
        Args:
            output_path: Path to output file
            format: Export format ("json" or "csv")
            include_raw: Whether to include raw metrics
            include_parsed: Whether to include parsed metrics
            include_aggregate: Whether to include aggregate metrics
            
        Returns:
            Path to exported file
            
        Raises:
            MetricsCollectionError: If export fails
        """
        if not self.current_collection:
            raise MetricsCollectionError("No active collection. Call start_collection() first.")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format.lower() == "json":
                self._export_json(output_file, include_raw, include_parsed, include_aggregate)
            elif format.lower() == "csv":
                self._export_csv(output_file, include_raw, include_parsed, include_aggregate)
            else:
                raise MetricsCollectionError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Exported metrics to {output_file}")
            return output_file
            
        except Exception as e:
            raise MetricsCollectionError(f"Failed to export metrics: {e}")
    
    def _export_json(
        self, 
        output_file: Path, 
        include_raw: bool, 
        include_parsed: bool, 
        include_aggregate: bool
    ) -> None:
        """Export metrics in JSON format."""
        export_data = {
            "collection_info": self.current_collection.export_summary(),
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_options": {
                "include_raw": include_raw,
                "include_parsed": include_parsed,
                "include_aggregate": include_aggregate
            }
        }
        
        if include_raw:
            export_data["raw_metrics"] = [
                metric.model_dump() for metric in self.current_collection.raw_metrics
            ]
        
        if include_parsed:
            export_data["parsed_metrics"] = [
                metric.model_dump() for metric in self.current_collection.parsed_metrics
            ]
        
        if include_aggregate:
            export_data["aggregate_metrics"] = [
                metric.model_dump() for metric in self.current_collection.aggregate_metrics
            ]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    def _export_csv(
        self, 
        output_file: Path, 
        include_raw: bool, 
        include_parsed: bool, 
        include_aggregate: bool
    ) -> None:
        """Export metrics in CSV format."""
        # For CSV, we'll export parsed metrics as the main data
        if not include_parsed or not self.current_collection.parsed_metrics:
            raise MetricsCollectionError("CSV export requires parsed metrics")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            headers = [
                "request_id", "engine_name", "engine_type", "model_name", "timestamp",
                "success", "total_duration", "load_duration", "prompt_eval_count", 
                "prompt_eval_duration", "prompt_token_rate", "eval_count", "eval_duration", 
                "response_token_rate", "first_token_latency", "inter_token_latency",
                "queueing_time", "error_message"
            ]
            writer.writerow(headers)
            
            # Write data rows
            for metric in self.current_collection.parsed_metrics:
                row = [
                    metric.request_id,
                    metric.engine_name,
                    metric.engine_type,
                    metric.model_name,
                    metric.timestamp.isoformat() if metric.timestamp else "",
                    metric.success,
                    metric.total_duration,
                    metric.load_duration,
                    metric.prompt_eval_count,
                    metric.prompt_eval_duration,
                    metric.prompt_token_rate,
                    metric.eval_count,
                    metric.eval_duration,
                    metric.response_token_rate,
                    metric.first_token_latency,
                    metric.inter_token_latency,
                    metric.queueing_time,
                    metric.error_message or ""
                ]
                writer.writerow(row)
    
    def get_collection_summary(self) -> Dict[str, Any]:
        """
        Get summary of current collection.
        
        Returns:
            Dictionary with collection summary
            
        Raises:
            MetricsCollectionError: If no collection is active
        """
        if not self.current_collection:
            raise MetricsCollectionError("No active collection. Call start_collection() first.")
        
        return self.current_collection.export_summary()
    
    def clear_collection(self) -> None:
        """Clear the current collection."""
        if self.current_collection:
            collection_id = self.current_collection.collection_id
            self.current_collection = None
            self.logger.info(f"Cleared metrics collection: {collection_id}")
        else:
            self.logger.warning("No active collection to clear")


# Global metrics collector instance (will be initialized with connection manager)
metrics_collector: Optional[MetricsCollector] = None


def initialize_metrics_collector(connection_manager: ConnectionManager) -> MetricsCollector:
    """Initialize the global metrics collector instance."""
    global metrics_collector
    metrics_collector = MetricsCollector(connection_manager)
    return metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance."""
    return metrics_collector
