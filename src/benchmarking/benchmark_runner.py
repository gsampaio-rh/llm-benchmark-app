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
                        # Accumulated response for real-time streaming
                        accumulated_response = []
                        
                        # Define token callback for real-time updates
                        async def token_callback(token: str) -> None:
                            accumulated_response.append(token)
                            current_text = "".join(accumulated_response)
                            
                            # Update display with streaming tokens
                            live.update(self.dashboard.create_display(
                                targets_dict, engine_metrics, start_time,
                                total_requests, completed_requests,
                                current_engine=f"{engine_name} ({model_name})",
                                current_prompt=prompt,
                                current_response=current_text
                            ))
                        
                        # Send streaming request with real-time token delivery
                        result = await metrics_collector.collect_streaming_request_metrics(
                            engine_name,
                            prompt,
                            model_name,
                            token_callback=token_callback,
                            max_tokens=config.max_tokens,
                            temperature=config.temperature
                        )
                        
                        if result.success:
                            engine_metrics[engine_name].completed += 1
                            
                            # Show final response briefly
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
    
    async def run_parallel(
        self,
        metrics_collector: Any,
        targets: List[BenchmarkTarget],
        prompts: List[str],
        config: BenchmarkConfig
    ) -> Dict[str, EngineStats]:
        """
        Run benchmark with all engines in parallel with real-time per-token streaming.
        
        All engines stream tokens simultaneously in a multi-column view,
        providing 3x faster execution with live visual comparison.
        
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
        
        # Shared state for tracking progress and current responses
        completed_requests = 0
        completed_lock = asyncio.Lock()
        
        # Track current streaming responses for each engine
        current_responses = {target.engine_name: "" for target in targets}
        current_prompts = {target.engine_name: "" for target in targets}
        responses_lock = asyncio.Lock()
        
        # Convert targets to dict format for dashboard
        targets_dict = [t.to_dict() for t in targets]
        
        # Start time
        start_time = time.time()
        
        # Track which engines are actively streaming
        active_engines = set()
        active_lock = asyncio.Lock()
        
        # Define engine execution function
        async def run_engine_requests(target: BenchmarkTarget) -> None:
            """Run all requests for a single engine with real-time token streaming."""
            nonlocal completed_requests
            engine_name = target.engine_name
            model_name = target.model_name
            
            for i, prompt in enumerate(prompts[:config.num_requests_per_target]):
                try:
                    # Mark engine as active
                    async with active_lock:
                        active_engines.add(engine_name)
                    
                    # Set current prompt
                    async with responses_lock:
                        current_prompts[engine_name] = prompt[:100] + "..." if len(prompt) > 100 else prompt
                        current_responses[engine_name] = ""
                    
                    # Accumulated response for this request
                    accumulated_response = []
                    
                    # Define token callback for real-time per-token updates
                    async def token_callback(token: str) -> None:
                        accumulated_response.append(token)
                        # Update shared state with new token
                        async with responses_lock:
                            current_responses[engine_name] = "".join(accumulated_response)
                    
                    # Send streaming request with real-time token delivery
                    result = await metrics_collector.collect_streaming_request_metrics(
                        engine_name,
                        prompt,
                        model_name,
                        token_callback=token_callback,
                        max_tokens=config.max_tokens,
                        temperature=config.temperature
                    )
                    
                    if result.success:
                        engine_metrics[engine_name].completed += 1
                        self._update_engine_metrics(engine_metrics[engine_name], result)
                    else:
                        engine_metrics[engine_name].failed += 1
                        # Show error briefly
                        async with responses_lock:
                            current_responses[engine_name] = f"❌ {result.error_message[:100]}"
                    
                    # Update global counter
                    async with completed_lock:
                        completed_requests += 1
                    
                    # Clear current response after completion
                    await asyncio.sleep(0.5)  # Brief pause to show final state
                    async with responses_lock:
                        current_responses[engine_name] = ""
                        current_prompts[engine_name] = ""
                    
                except Exception as e:
                    engine_metrics[engine_name].failed += 1
                    async with completed_lock:
                        completed_requests += 1
                    # Show error
                    async with responses_lock:
                        current_responses[engine_name] = f"❌ {str(e)[:100]}"
                    await asyncio.sleep(0.5)
                
                finally:
                    # Mark engine as inactive if done
                    if i == config.num_requests_per_target - 1:
                        async with active_lock:
                            active_engines.discard(engine_name)
        
        # Run with live display
        with Live(
            self.dashboard.create_display(
                targets_dict, engine_metrics, start_time, total_requests, completed_requests,
                current_responses=current_responses,
                current_prompts=current_prompts
            ),
            console=self.console,
            refresh_per_second=10  # Higher refresh rate for smooth streaming
        ) as live:
            # Create tasks for all engines
            engine_tasks = [asyncio.create_task(run_engine_requests(target)) for target in targets]
            
            # Continuous update loop while any task is running
            while not all(task.done() for task in engine_tasks):
                # Update display with current state
                async with responses_lock:
                    live.update(self.dashboard.create_display(
                        targets_dict, engine_metrics, start_time,
                        total_requests, completed_requests,
                        current_responses=dict(current_responses),
                        current_prompts=dict(current_prompts)
                    ))
                await asyncio.sleep(0.1)  # Update every 100ms
            
            # Wait for all engines to complete
            await asyncio.gather(*engine_tasks)
            
            # Final update
            live.update(self.dashboard.create_display(
                targets_dict, engine_metrics, start_time,
                total_requests, completed_requests
            ))
        
        return engine_metrics
    
    def _update_engine_metrics(self, stats: EngineStats, result: Any) -> None:
        """Update engine statistics from result with enhanced metrics."""
        if not result.parsed_metrics:
            return
        
        # Track token count
        if result.parsed_metrics.eval_count:
            stats.total_tokens += result.parsed_metrics.eval_count
            # Track tokens per response for averaging
            stats.tokens_per_response.append(result.parsed_metrics.eval_count)
        
        # Track word count for token/word ratio
        if result.response:
            word_count = len(result.response.split())
            stats.words_per_response.append(word_count)
        
        # Track token rate
        if result.parsed_metrics.response_token_rate:
            stats.token_rates.append(result.parsed_metrics.response_token_rate)
            # Calculate running average
            stats.avg_tps = sum(stats.token_rates) / len(stats.token_rates)
        
        # Track TTFT (Time to First Token)
        if result.parsed_metrics.first_token_latency:
            stats.ttft_values.append(result.parsed_metrics.first_token_latency)
        
        # Track inter-token latency
        if result.parsed_metrics.inter_token_latency:
            stats.inter_token_latencies.append(result.parsed_metrics.inter_token_latency * 1000)  # Convert to ms
        
        # Track total response duration
        if result.parsed_metrics.total_duration:
            stats.response_durations.append(result.parsed_metrics.total_duration)

