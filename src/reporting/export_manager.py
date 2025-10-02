"""
Enhanced export manager for benchmark results.

This module provides comprehensive export functionality with per-engine
separation, summary reports, and multiple output formats.
"""

import json
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from pydantic import BaseModel, Field

from ..models.metrics import MetricsCollection, ParsedMetrics, AggregateMetrics


logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of an export operation."""
    
    export_dir: Path
    files_created: List[Path]
    summary_stats: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class ExportConfig(BaseModel):
    """Configuration for export operations."""
    
    model_config = {"extra": "forbid"}
    
    output_dir: str = Field(
        default="benchmark_results",
        description="Base output directory for exports"
    )
    create_timestamp_dir: bool = Field(
        default=True,
        description="Create timestamped subdirectory (run_YYYYMMDD_HHMMSS)"
    )
    include_raw_metrics: bool = Field(
        default=True,
        description="Include raw metrics in per-engine exports"
    )
    include_parsed_metrics: bool = Field(
        default=True,
        description="Include parsed metrics in exports"
    )
    include_aggregate_metrics: bool = Field(
        default=True,
        description="Include aggregate metrics in exports"
    )
    generate_markdown: bool = Field(
        default=True,
        description="Generate markdown report"
    )
    generate_csv: bool = Field(
        default=True,
        description="Generate CSV exports"
    )
    generate_json: bool = Field(
        default=True,
        description="Generate JSON exports"
    )


class ExportManager:
    """
    Enhanced export manager for benchmark results.
    
    Provides comprehensive export functionality including:
    - Per-engine separation (one JSON + CSV per engine)
    - Cross-engine summary reports
    - Statistical analysis
    - Markdown report generation
    """
    
    def __init__(self, config: Optional[ExportConfig] = None):
        """
        Initialize the export manager.
        
        Args:
            config: Export configuration (uses defaults if None)
        """
        self.config = config or ExportConfig()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Initialized export manager")
    
    def export_collection(
        self,
        collection: MetricsCollection,
        description: Optional[str] = None,
        scenario: Optional[str] = None
    ) -> ExportResult:
        """
        Export a complete metrics collection with per-engine separation.
        
        Args:
            collection: MetricsCollection to export
            description: Optional description for this export
            scenario: Optional scenario name
            
        Returns:
            ExportResult with paths and summary
        """
        try:
            # Create export directory
            export_dir = self._create_export_directory()
            files_created = []
            
            self.logger.info(f"Exporting collection to {export_dir}")
            
            # Group metrics by engine
            metrics_by_engine = self._group_metrics_by_engine(collection)
            
            # Export per-engine results
            for engine_name, engine_metrics in metrics_by_engine.items():
                engine_files = self._export_engine_results(
                    export_dir,
                    engine_name,
                    engine_metrics,
                    scenario
                )
                files_created.extend(engine_files)
            
            # Generate cross-engine summary
            summary_files = self._export_summary(
                export_dir,
                collection,
                metrics_by_engine,
                description,
                scenario
            )
            files_created.extend(summary_files)
            
            # Generate markdown report
            if self.config.generate_markdown:
                markdown_file = self._generate_markdown_report(
                    export_dir,
                    collection,
                    metrics_by_engine,
                    description,
                    scenario
                )
                files_created.append(markdown_file)
            
            # Calculate summary statistics
            summary_stats = self._calculate_summary_stats(metrics_by_engine)
            
            self.logger.info(f"Export completed: {len(files_created)} files created")
            
            return ExportResult(
                export_dir=export_dir,
                files_created=files_created,
                summary_stats=summary_stats,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}", exc_info=True)
            return ExportResult(
                export_dir=Path(),
                files_created=[],
                summary_stats={},
                success=False,
                error_message=str(e)
            )
    
    def _create_export_directory(self) -> Path:
        """Create timestamped export directory."""
        base_dir = Path(self.config.output_dir)
        
        if self.config.create_timestamp_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = base_dir / f"run_{timestamp}"
        else:
            export_dir = base_dir
        
        export_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Created export directory: {export_dir}")
        
        return export_dir
    
    def _group_metrics_by_engine(
        self,
        collection: MetricsCollection
    ) -> Dict[str, List[ParsedMetrics]]:
        """Group parsed metrics by engine name."""
        metrics_by_engine: Dict[str, List[ParsedMetrics]] = {}
        
        for metric in collection.parsed_metrics:
            engine_name = metric.engine_name
            if engine_name not in metrics_by_engine:
                metrics_by_engine[engine_name] = []
            metrics_by_engine[engine_name].append(metric)
        
        return metrics_by_engine
    
    def _export_engine_results(
        self,
        export_dir: Path,
        engine_name: str,
        metrics: List[ParsedMetrics],
        scenario: Optional[str] = None
    ) -> List[Path]:
        """Export results for a single engine."""
        files_created = []
        
        # Sanitize engine name for filename
        safe_name = engine_name.replace("/", "_").replace(" ", "_")
        
        # Export JSON
        if self.config.generate_json:
            json_file = export_dir / f"{safe_name}_results.json"
            self._export_engine_json(json_file, engine_name, metrics, scenario)
            files_created.append(json_file)
        
        # Export CSV
        if self.config.generate_csv:
            csv_file = export_dir / f"{safe_name}_results.csv"
            self._export_engine_csv(csv_file, engine_name, metrics, scenario)
            files_created.append(csv_file)
        
        return files_created
    
    def _export_engine_json(
        self,
        output_file: Path,
        engine_name: str,
        metrics: List[ParsedMetrics],
        scenario: Optional[str] = None
    ) -> None:
        """Export engine results as JSON."""
        successful_metrics = [m for m in metrics if m.success]
        
        # Calculate statistics
        stats = self._calculate_engine_statistics(successful_metrics)
        
        export_data = {
            "engine_name": engine_name,
            "scenario": scenario,
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_requests": len(metrics),
            "successful_requests": len(successful_metrics),
            "failed_requests": len(metrics) - len(successful_metrics),
            "success_rate": len(successful_metrics) / len(metrics) if metrics else 0.0,
            "statistics": stats,
            "metrics": [m.model_dump() for m in metrics]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.debug(f"Exported engine JSON: {output_file}")
    
    def _export_engine_csv(
        self,
        output_file: Path,
        engine_name: str,
        metrics: List[ParsedMetrics],
        scenario: Optional[str] = None
    ) -> None:
        """Export engine results as CSV."""
        if not metrics:
            return
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            headers = [
                "request_id",
                "engine",
                "model",
                "scenario",
                "prompt_tokens",
                "completion_tokens",
                "total_duration_sec",
                "ttft_sec",
                "tokens_per_sec",
                "inter_token_latency_sec",
                "load_duration_sec",
                "prompt_eval_duration_sec",
                "eval_duration_sec",
                "success",
                "error_message",
                "timestamp"
            ]
            writer.writerow(headers)
            
            # Write data rows
            for metric in metrics:
                row = [
                    metric.request_id,
                    engine_name,
                    metric.model_name,
                    scenario or "",
                    metric.prompt_eval_count or "",
                    metric.eval_count or "",
                    metric.total_duration or "",
                    metric.first_token_latency or "",
                    metric.response_token_rate or "",
                    metric.inter_token_latency or "",
                    metric.load_duration or "",
                    metric.prompt_eval_duration or "",
                    metric.eval_duration or "",
                    metric.success,
                    metric.error_message or "",
                    metric.timestamp.isoformat() if metric.timestamp else ""
                ]
                writer.writerow(row)
        
        self.logger.debug(f"Exported engine CSV: {output_file}")
    
    def _export_summary(
        self,
        export_dir: Path,
        collection: MetricsCollection,
        metrics_by_engine: Dict[str, List[ParsedMetrics]],
        description: Optional[str] = None,
        scenario: Optional[str] = None
    ) -> List[Path]:
        """Export cross-engine summary reports."""
        files_created = []
        
        # Export summary JSON
        if self.config.generate_json:
            summary_json = export_dir / "summary.json"
            self._export_summary_json(
                summary_json,
                collection,
                metrics_by_engine,
                description,
                scenario
            )
            files_created.append(summary_json)
        
        # Export summary CSV
        if self.config.generate_csv:
            summary_csv = export_dir / "summary.csv"
            self._export_summary_csv(summary_csv, metrics_by_engine, scenario)
            files_created.append(summary_csv)
        
        return files_created
    
    def _export_summary_json(
        self,
        output_file: Path,
        collection: MetricsCollection,
        metrics_by_engine: Dict[str, List[ParsedMetrics]],
        description: Optional[str] = None,
        scenario: Optional[str] = None
    ) -> None:
        """Export cross-engine summary as JSON."""
        engine_summaries = {}
        
        for engine_name, metrics in metrics_by_engine.items():
            successful = [m for m in metrics if m.success]
            stats = self._calculate_engine_statistics(successful)
            
            engine_summaries[engine_name] = {
                "total_requests": len(metrics),
                "successful_requests": len(successful),
                "failed_requests": len(metrics) - len(successful),
                "success_rate": len(successful) / len(metrics) if metrics else 0.0,
                "statistics": stats
            }
        
        summary_data = {
            "description": description,
            "scenario": scenario,
            "collection_id": collection.collection_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "collection_info": collection.export_summary(),
            "engines": engine_summaries
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        self.logger.debug(f"Exported summary JSON: {output_file}")
    
    def _export_summary_csv(
        self,
        output_file: Path,
        metrics_by_engine: Dict[str, List[ParsedMetrics]],
        scenario: Optional[str] = None
    ) -> None:
        """Export cross-engine summary as CSV."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            headers = [
                "engine",
                "model",
                "scenario",
                "requests",
                "success_rate",
                "mean_latency_sec",
                "p50_latency_sec",
                "p95_latency_sec",
                "p99_latency_sec",
                "mean_ttft_sec",
                "mean_tokens_per_sec",
                "total_input_tokens",
                "total_output_tokens"
            ]
            writer.writerow(headers)
            
            # Write data rows
            for engine_name, metrics in metrics_by_engine.items():
                successful = [m for m in metrics if m.success]
                if not successful:
                    continue
                
                stats = self._calculate_engine_statistics(successful)
                
                # Get primary model (most common)
                models = [m.model_name for m in successful]
                primary_model = max(set(models), key=models.count) if models else ""
                
                row = [
                    engine_name,
                    primary_model,
                    scenario or "",
                    len(metrics),
                    len(successful) / len(metrics) if metrics else 0.0,
                    stats.get("latency", {}).get("mean"),
                    stats.get("latency", {}).get("p50"),
                    stats.get("latency", {}).get("p95"),
                    stats.get("latency", {}).get("p99"),
                    stats.get("ttft", {}).get("mean"),
                    stats.get("throughput", {}).get("mean_tokens_per_sec"),
                    stats.get("tokens", {}).get("total_input"),
                    stats.get("tokens", {}).get("total_output")
                ]
                writer.writerow(row)
        
        self.logger.debug(f"Exported summary CSV: {output_file}")
    
    def _calculate_engine_statistics(
        self,
        metrics: List[ParsedMetrics]
    ) -> Dict[str, Any]:
        """Calculate comprehensive statistics for an engine's metrics."""
        if not metrics:
            return {}
        
        # Extract data arrays
        latencies = [m.total_duration for m in metrics if m.total_duration is not None]
        ttfts = [m.first_token_latency for m in metrics if m.first_token_latency is not None]
        token_rates = [m.response_token_rate for m in metrics if m.response_token_rate is not None]
        inter_token = [m.inter_token_latency for m in metrics if m.inter_token_latency is not None]
        input_tokens = [m.prompt_eval_count for m in metrics if m.prompt_eval_count is not None]
        output_tokens = [m.eval_count for m in metrics if m.eval_count is not None]
        
        stats = {
            "latency": self._calculate_percentile_stats(latencies) if latencies else {},
            "ttft": self._calculate_percentile_stats(ttfts) if ttfts else {},
            "inter_token_latency": self._calculate_percentile_stats(inter_token) if inter_token else {},
            "throughput": {
                "mean_tokens_per_sec": float(np.mean(token_rates)) if token_rates else None,
                "p50_tokens_per_sec": float(np.percentile(token_rates, 50)) if token_rates else None,
                "p95_tokens_per_sec": float(np.percentile(token_rates, 95)) if token_rates else None,
            } if token_rates else {},
            "tokens": {
                "total_input": int(np.sum(input_tokens)) if input_tokens else 0,
                "total_output": int(np.sum(output_tokens)) if output_tokens else 0,
                "mean_input": float(np.mean(input_tokens)) if input_tokens else None,
                "mean_output": float(np.mean(output_tokens)) if output_tokens else None,
            }
        }
        
        return stats
    
    def _calculate_percentile_stats(self, data: List[float]) -> Dict[str, float]:
        """Calculate percentile statistics for a dataset."""
        if not data:
            return {}
        
        return {
            "mean": float(np.mean(data)),
            "std_dev": float(np.std(data)),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "p50": float(np.percentile(data, 50)),
            "p95": float(np.percentile(data, 95)),
            "p99": float(np.percentile(data, 99)),
        }
    
    def _calculate_summary_stats(
        self,
        metrics_by_engine: Dict[str, List[ParsedMetrics]]
    ) -> Dict[str, Any]:
        """Calculate overall summary statistics."""
        summary = {
            "total_engines": len(metrics_by_engine),
            "engines": {}
        }
        
        for engine_name, metrics in metrics_by_engine.items():
            successful = [m for m in metrics if m.success]
            summary["engines"][engine_name] = {
                "total_requests": len(metrics),
                "successful": len(successful),
                "success_rate": len(successful) / len(metrics) if metrics else 0.0
            }
        
        return summary
    
    def _generate_markdown_report(
        self,
        export_dir: Path,
        collection: MetricsCollection,
        metrics_by_engine: Dict[str, List[ParsedMetrics]],
        description: Optional[str] = None,
        scenario: Optional[str] = None
    ) -> Path:
        """Generate human-readable markdown report."""
        report_file = export_dir / "report.md"
        
        lines = []
        lines.append("# Benchmark Results Report")
        lines.append("")
        
        if description:
            lines.append(f"**Description:** {description}")
        if scenario:
            lines.append(f"**Scenario:** {scenario}")
        
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Collection ID:** {collection.collection_id}")
        lines.append("")
        
        lines.append("## Executive Summary")
        lines.append("")
        
        # Summary table
        lines.append("| Engine | Requests | Success Rate | Avg Latency | Avg Throughput |")
        lines.append("|--------|----------|--------------|-------------|----------------|")
        
        for engine_name, metrics in metrics_by_engine.items():
            successful = [m for m in metrics if m.success]
            stats = self._calculate_engine_statistics(successful)
            
            success_rate = len(successful) / len(metrics) if metrics else 0.0
            avg_latency = stats.get("latency", {}).get("mean", 0)
            avg_throughput = stats.get("throughput", {}).get("mean_tokens_per_sec", 0)
            
            lines.append(
                f"| {engine_name} | {len(metrics)} | "
                f"{success_rate:.1%} | "
                f"{avg_latency:.3f}s | "
                f"{avg_throughput:.1f} tok/s |"
            )
        
        lines.append("")
        
        # Detailed results per engine
        lines.append("## Detailed Results")
        lines.append("")
        
        for engine_name, metrics in sorted(metrics_by_engine.items()):
            lines.append(f"### {engine_name}")
            lines.append("")
            
            successful = [m for m in metrics if m.success]
            stats = self._calculate_engine_statistics(successful)
            
            lines.append(f"**Total Requests:** {len(metrics)}")
            lines.append(f"**Successful:** {len(successful)}")
            lines.append(f"**Failed:** {len(metrics) - len(successful)}")
            lines.append(f"**Success Rate:** {len(successful) / len(metrics):.1%}" if metrics else "0%")
            lines.append("")
            
            if stats.get("latency"):
                lines.append("**Latency Statistics:**")
                lat = stats["latency"]
                lines.append(f"- Mean: {lat.get('mean', 0):.3f}s")
                lines.append(f"- p50: {lat.get('p50', 0):.3f}s")
                lines.append(f"- p95: {lat.get('p95', 0):.3f}s")
                lines.append(f"- p99: {lat.get('p99', 0):.3f}s")
                lines.append(f"- Std Dev: {lat.get('std_dev', 0):.3f}s")
                lines.append("")
            
            if stats.get("throughput"):
                lines.append("**Throughput:**")
                thr = stats["throughput"]
                lines.append(f"- Mean: {thr.get('mean_tokens_per_sec', 0):.1f} tokens/sec")
                lines.append(f"- p50: {thr.get('p50_tokens_per_sec', 0):.1f} tokens/sec")
                lines.append(f"- p95: {thr.get('p95_tokens_per_sec', 0):.1f} tokens/sec")
                lines.append("")
            
            if stats.get("ttft"):
                lines.append("**Time to First Token:**")
                ttft = stats["ttft"]
                lines.append(f"- Mean: {ttft.get('mean', 0):.3f}s")
                lines.append(f"- p95: {ttft.get('p95', 0):.3f}s")
                lines.append("")
            
            if stats.get("tokens"):
                lines.append("**Token Statistics:**")
                tok = stats["tokens"]
                lines.append(f"- Total Input: {tok.get('total_input', 0):,}")
                lines.append(f"- Total Output: {tok.get('total_output', 0):,}")
                mean_input = tok.get('mean_input') or 0
                mean_output = tok.get('mean_output') or 0
                lines.append(f"- Mean Input: {mean_input:.1f}")
                lines.append(f"- Mean Output: {mean_output:.1f}")
                lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by LLM Benchmark Tool*")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self.logger.debug(f"Generated markdown report: {report_file}")
        return report_file

