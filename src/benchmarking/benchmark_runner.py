"""
Benchmark runner with live updates.

Provides reusable benchmark execution with real-time visualization
and metrics collection.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from pydantic import BaseModel, Field

from .live_dashboard import LiveDashboard, DashboardConfig, EngineStats
from .target_selector import BenchmarkTarget


class BenchmarkConfig(BaseModel):
    """Configuration for benchmark execution."""
    
    model_config = {"extra": "forbid"}
    
    description: str = Field(..., description="Benchmark description")
    scenario_name: str = Field(..., description="Scenario name")
    num_requests_per_target: int = Field(..., description="Requests per target", ge=1)
    max_tokens: int = Field(default=500, description="Max completion tokens")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    show_streaming_effect: bool = Field(
        default=True,
        description="Show progressive response reveal"
    )
    streaming_chunks: int = Field(
        default=3,
        description="Number of chunks for streaming effect"
    )
    chunk_delay: float = Field(
        default=0.15,
        description="Delay between streaming chunks"
    )


class BenchmarkRunner:
    """
    Benchmark runner with live visualization.
    
    Executes benchmarks with real-time dashboard updates and metrics collection.
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        dashboard_config: Optional[DashboardConfig] = None
    ):
        """
        Initialize benchmark runner.
        
        Args:
            console: Rich console instance
            dashboard_config: Dashboard configuration
        """
        self.console = console or Console()
        self.dashboard = LiveDashboard(config=dashboard_config, console=self.console)
    
    async def run(
        self,
        metrics_collector: Any,
        targets: List[BenchmarkTarget],
        prompts: List[str],
        config: BenchmarkConfig
    ) -> Dict[str, EngineStats]:
        """
        Run benchmark with live updates.
        
        Args:
            metrics_collector: Metrics collector instance
            targets: List of benchmark targets
            prompts: List of prompts to test
            config: Benchmark configuration
            
        Returns:
            Dictionary of engine statistics
        """
        # Start metrics collection
        metrics_collector.start_collection(config.description)
        
        total_requests = len(targets) * config.num_requests_per_target
        
        # Initialize engine metrics
        engine_metrics = {}
        for target in targets:
            engine_metrics[target.engine_name] = EngineStats(
                target=config.num_requests_per_target,
                start_time=time.time()
            )
        
        # Run with live display
        start_time = time.time()
        completed_requests = 0
        
        # Convert targets to dict format for dashboard
        targets_dict = [t.to_dict() for t in targets]
        
        with Live(
            self.dashboard.create_display(
                targets_dict, engine_metrics, start_time, total_requests, completed_requests
            ),
            console=self.console,
            refresh_per_second=4
        ) as live:
            
            for target in targets:
                engine_name = target.engine_name
                model_name = target.model_name
                
                for i, prompt in enumerate(prompts[:config.num_requests_per_target]):
                    # Update display - sending request
                    live.update(self.dashboard.create_display(
                        targets_dict, engine_metrics, start_time, total_requests, completed_requests,
                        current_engine=f"{engine_name} ({model_name})",
                        current_prompt=prompt,
                        current_response=None
                    ))
                    
                    try:
                        # Send request
                        result = await metrics_collector.collect_single_request_metrics(
                            engine_name,
                            prompt,
                            model_name,
                            max_tokens=config.max_tokens,
                            temperature=config.temperature
                        )
                        
                        if result.success:
                            engine_metrics[engine_name].completed += 1
                            
                            # Show streaming effect
                            if config.show_streaming_effect and result.response:
                                await self._show_streaming_effect(
                                    live, targets_dict, engine_metrics, start_time,
                                    total_requests, completed_requests,
                                    engine_name, model_name, prompt, result.response,
                                    config
                                )
                            else:
                                # Show complete response immediately
                                live.update(self.dashboard.create_display(
                                    targets_dict, engine_metrics, start_time,
                                    total_requests, completed_requests,
                                    current_engine=f"{engine_name} ({model_name})",
                                    current_prompt=prompt,
                                    current_response=result.response
                                ))
                                await asyncio.sleep(0.3)
                            
                            # Update metrics
                            self._update_engine_metrics(engine_metrics[engine_name], result)
                            
                        else:
                            engine_metrics[engine_name].failed += 1
                            
                            # Show error
                            live.update(self.dashboard.create_display(
                                targets_dict, engine_metrics, start_time,
                                total_requests, completed_requests,
                                current_engine=f"{engine_name} ({model_name})",
                                current_prompt=prompt,
                                current_response=f"❌ Error: {result.error_message[:100]}"
                            ))
                            await asyncio.sleep(0.3)
                        
                        completed_requests += 1
                        
                        # Final update for this request
                        live.update(self.dashboard.create_display(
                            targets_dict, engine_metrics, start_time,
                            total_requests, completed_requests
                        ))
                        
                    except Exception as e:
                        engine_metrics[engine_name].failed += 1
                        completed_requests += 1
                        
                        # Update display with error
                        live.update(self.dashboard.create_display(
                            targets_dict, engine_metrics, start_time,
                            total_requests, completed_requests,
                            current_engine=f"{engine_name} ({model_name})",
                            current_prompt=prompt,
                            current_response=f"❌ Error: {str(e)[:100]}"
                        ))
                        await asyncio.sleep(0.3)
        
        return engine_metrics
    
    async def _show_streaming_effect(
        self,
        live: Live,
        targets: List[Dict],
        engine_metrics: Dict[str, EngineStats],
        start_time: float,
        total_requests: int,
        completed_requests: int,
        engine_name: str,
        model_name: str,
        prompt: str,
        response: str,
        config: BenchmarkConfig
    ) -> None:
        """Show progressive streaming effect for response."""
        if len(response) > 50:
            words = response.split()
            chunks = []
            
            # Create chunks
            for i in range(1, config.streaming_chunks + 1):
                chunk_size = int(len(words) * (i / config.streaming_chunks))
                chunks.append(" ".join(words[:chunk_size]))
            
            # Show each chunk
            for chunk in chunks:
                live.update(self.dashboard.create_display(
                    targets, engine_metrics, start_time, total_requests, completed_requests,
                    current_engine=f"{engine_name} ({model_name})",
                    current_prompt=prompt,
                    current_response=chunk
                ))
                await asyncio.sleep(config.chunk_delay)
        else:
            # Short response, show immediately
            live.update(self.dashboard.create_display(
                targets, engine_metrics, start_time, total_requests, completed_requests,
                current_engine=f"{engine_name} ({model_name})",
                current_prompt=prompt,
                current_response=response
            ))
            await asyncio.sleep(0.3)
    
    def _update_engine_metrics(self, stats: EngineStats, result: Any) -> None:
        """Update engine statistics from result."""
        if not result.parsed_metrics:
            return
        
        # Track token count
        if result.parsed_metrics.eval_count:
            stats.total_tokens += result.parsed_metrics.eval_count
        
        # Track token rate
        if result.parsed_metrics.response_token_rate:
            stats.token_rates.append(result.parsed_metrics.response_token_rate)
            # Calculate running average
            stats.avg_tps = sum(stats.token_rates) / len(stats.token_rates)

