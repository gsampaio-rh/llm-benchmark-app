"""
Benchmarking Utilities for vLLM vs TGI vs Ollama
Advanced load testing and TTFT measurement following clean UX pattern
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import statistics

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

from api_clients import (
    UnifiedAPIClient, GenerationRequest, GenerationResponse, 
    create_chat_request, create_completion_request, TokenMetrics
)

console = Console()

@dataclass
class BenchmarkConfig:
    """Configuration for benchmark tests"""
    name: str = "default"
    concurrent_users: int = 5
    duration_seconds: int = 30
    prompt_type: str = "quick_response"
    max_tokens: int = 100
    temperature: float = 0.7
    include_ttft: bool = True
    target_ttft_ms: float = 100.0
    target_p95_ms: float = 1000.0

@dataclass 
class ServiceBenchmarkResult:
    """Results for a single service benchmark"""
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    
    # Timing metrics (milliseconds)
    response_times: List[float] = field(default_factory=list)
    ttft_times: List[float] = field(default_factory=list)
    tokens_per_second: List[float] = field(default_factory=list)
    
    # Calculated statistics
    mean_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    
    mean_ttft: float = 0.0
    p50_ttft: float = 0.0
    p95_ttft: float = 0.0
    p99_ttft: float = 0.0
    
    mean_tokens_per_sec: float = 0.0
    
    errors: List[str] = field(default_factory=list)

@dataclass
class BenchmarkResults:
    """Complete benchmark results for all services"""
    config: BenchmarkConfig
    services: Dict[str, ServiceBenchmarkResult] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time
    
    def get_winner(self) -> Optional[str]:
        """Determine the winning service based on P95 latency"""
        valid_services = {name: result for name, result in self.services.items() 
                         if result.successful_requests > 0}
        
        if not valid_services:
            return None
            
        return min(valid_services.keys(), 
                  key=lambda name: valid_services[name].p95_response_time)

class TTFTBenchmark:
    """Time To First Token benchmark using streaming responses"""
    
    def __init__(self, client: UnifiedAPIClient):
        self.client = client
        
    async def measure_ttft_single(self, service_name: str, request: GenerationRequest) -> Tuple[float, str]:
        """Measure TTFT for a single request"""
        try:
            service_client = self.client.clients[service_name]
            
            start_time = time.time()
            first_token_time = None
            content = ""
            
            async for token in service_client.generate_stream(request):
                if first_token_time is None:
                    first_token_time = time.time()
                content += token
                
                # Break after first token for TTFT measurement
                if len(content.strip()) > 0:
                    break
            
            if first_token_time:
                ttft_ms = (first_token_time - start_time) * 1000
                return ttft_ms, content
            else:
                return float('inf'), ""
                
        except Exception as e:
            console.print(f"[red]❌ TTFT error for {service_name}: {e}[/red]")
            return float('inf'), ""
    
    async def compare_ttft(self, request: GenerationRequest, iterations: int = 5) -> Dict[str, List[float]]:
        """Compare TTFT across all services"""
        results = {service: [] for service in self.client.clients.keys()}
        
        console.print(Panel.fit(
            f"[bold yellow]⚡ TTFT Comparison Test[/bold yellow]\n\n"
            f"Measuring Time To First Token across {len(self.client.clients)} services\n"
            f"Iterations: {iterations} per service\n"
            f"[dim]Lower values indicate better responsiveness[/dim]",
            title="TTFT Benchmark",
            border_style="yellow"
        ))
        
        total_tests = len(self.client.clients) * iterations
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            task = progress.add_task("Measuring TTFT...", total=total_tests)
            
            for service_name in self.client.clients.keys():
                for i in range(iterations):
                    ttft_ms, _ = await self.measure_ttft_single(service_name, request)
                    if ttft_ms != float('inf'):
                        results[service_name].append(ttft_ms)
                    
                    progress.advance(task)
                    progress.update(task, description=f"Testing {service_name.upper()} ({i+1}/{iterations})")
        
        # Display TTFT results table
        self._display_ttft_results(results)
        
        return results
    
    def _display_ttft_results(self, results: Dict[str, List[float]]):
        """Display beautiful TTFT results table"""
        table = Table(title="⚡ Time To First Token (TTFT) Results")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Tests", style="white")
        table.add_column("Mean TTFT", style="green")
        table.add_column("Min TTFT", style="blue")
        table.add_column("Max TTFT", style="red")
        table.add_column("Target Met", style="magenta")
        
        target_ttft = 100.0  # 100ms target
        
        for service_name, ttft_list in results.items():
            if ttft_list:
                mean_ttft = statistics.mean(ttft_list)
                min_ttft = min(ttft_list)
                max_ttft = max(ttft_list)
                target_met = "[green]✅ Yes[/green]" if mean_ttft < target_ttft else "[red]❌ No[/red]"
                
                table.add_row(
                    service_name.upper(),
                    str(len(ttft_list)),
                    f"{mean_ttft:.1f}ms",
                    f"{min_ttft:.1f}ms", 
                    f"{max_ttft:.1f}ms",
                    target_met
                )
            else:
                table.add_row(
                    service_name.upper(),
                    "0",
                    "[red]Failed[/red]",
                    "[red]Failed[/red]",
                    "[red]Failed[/red]",
                    "[red]❌ No[/red]"
                )
        
        console.print(table)
        
        # Find fastest TTFT
        valid_results = {name: ttft_list for name, ttft_list in results.items() if ttft_list}
        if valid_results:
            fastest_service = min(valid_results.keys(), 
                                key=lambda name: statistics.mean(valid_results[name]))
            fastest_ttft = statistics.mean(valid_results[fastest_service])
            console.print(f"\n[bold green]🏆 Fastest TTFT: {fastest_service.upper()} ({fastest_ttft:.1f}ms)[/bold green]")

class LoadTestBenchmark:
    """Advanced load testing with concurrent users"""
    
    def __init__(self, client: UnifiedAPIClient):
        self.client = client
    
    async def run_load_test(self, config: BenchmarkConfig, prompts: List[str]) -> BenchmarkResults:
        """Run comprehensive load test"""
        
        console.print(Panel.fit(
            f"[bold red]🔥 Load Test: {config.name.upper()}[/bold red]\n\n"
            f"Concurrent Users: {config.concurrent_users}\n"
            f"Duration: {config.duration_seconds}s\n"
            f"Target TTFT: < {config.target_ttft_ms}ms\n"
            f"Target P95: < {config.target_p95_ms}ms",
            title="Load Test Configuration",
            border_style="red"
        ))
        
        results = BenchmarkResults(config=config)
        results.start_time = time.time()
        
        # Initialize service results
        for service_name in self.client.clients.keys():
            results.services[service_name] = ServiceBenchmarkResult(service_name=service_name)
        
        # Run tests for each service
        tasks = []
        for service_name in self.client.clients.keys():
            task = self._test_service_load(service_name, config, prompts, results.services[service_name])
            tasks.append(task)
        
        # Run all services concurrently
        await asyncio.gather(*tasks)
        
        results.end_time = time.time()
        
        # Calculate statistics for all services
        for service_result in results.services.values():
            self._calculate_statistics(service_result)
        
        # Display results
        self._display_load_test_results(results)
        
        return results
    
    async def _test_service_load(self, service_name: str, config: BenchmarkConfig, 
                                prompts: List[str], result: ServiceBenchmarkResult):
        """Test load for a specific service"""
        
        end_time = time.time() + config.duration_seconds
        
        # Create tasks for concurrent users
        user_tasks = []
        for user_id in range(config.concurrent_users):
            task = self._simulate_user(service_name, config, prompts, result, end_time, user_id)
            user_tasks.append(task)
        
        # Wait for all users to complete
        await asyncio.gather(*user_tasks, return_exceptions=True)
    
    async def _simulate_user(self, service_name: str, config: BenchmarkConfig, 
                           prompts: List[str], result: ServiceBenchmarkResult, 
                           end_time: float, user_id: int):
        """Simulate a single user making requests"""
        
        try:
            service_client = self.client.clients[service_name]
            prompt_index = 0
            
            while time.time() < end_time:
                # Select prompt
                prompt = prompts[prompt_index % len(prompts)]
                prompt_index += 1
                
                # Create request
                request = create_chat_request(prompt, max_tokens=config.max_tokens)
                request.temperature = config.temperature
                
                # Measure request
                start_time = time.time()
                
                try:
                    if config.include_ttft:
                        # Use streaming for TTFT measurement
                        ttft_measured = False
                        first_token_time = None
                        content = ""
                        
                        async for token in service_client.generate_stream(request):
                            if not ttft_measured and token.strip():
                                first_token_time = time.time()
                                ttft_measured = True
                            content += token
                        
                        end_request_time = time.time()
                        
                        # Record metrics
                        response_time_ms = (end_request_time - start_time) * 1000
                        result.response_times.append(response_time_ms)
                        
                        if first_token_time:
                            ttft_ms = (first_token_time - start_time) * 1000
                            result.ttft_times.append(ttft_ms)
                        
                        # Estimate tokens and tokens/sec
                        tokens = len(content.split())
                        if response_time_ms > 0:
                            tps = (tokens / response_time_ms) * 1000
                            result.tokens_per_second.append(tps)
                        
                        result.total_tokens += tokens
                        result.successful_requests += 1
                        
                    else:
                        # Non-streaming request
                        response = await service_client.generate(request)
                        end_request_time = time.time()
                        
                        if response.error:
                            result.failed_requests += 1
                            result.errors.append(response.error)
                        else:
                            response_time_ms = (end_request_time - start_time) * 1000
                            result.response_times.append(response_time_ms)
                            result.tokens_per_second.append(response.metrics.tokens_per_second)
                            result.total_tokens += response.metrics.tokens_generated
                            result.successful_requests += 1
                    
                    result.total_requests += 1
                    
                except Exception as e:
                    result.failed_requests += 1
                    result.errors.append(str(e))
                    result.total_requests += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)
                
        except Exception as e:
            console.print(f"[red]❌ User {user_id} error for {service_name}: {e}[/red]")
    
    def _calculate_statistics(self, result: ServiceBenchmarkResult):
        """Calculate statistical metrics"""
        if result.response_times:
            result.mean_response_time = statistics.mean(result.response_times)
            result.p50_response_time = statistics.median(result.response_times)
            result.p95_response_time = statistics.quantiles(result.response_times, n=20)[18]  # 95th percentile
            result.p99_response_time = statistics.quantiles(result.response_times, n=100)[98]  # 99th percentile
        
        if result.ttft_times:
            result.mean_ttft = statistics.mean(result.ttft_times)
            result.p50_ttft = statistics.median(result.ttft_times)
            result.p95_ttft = statistics.quantiles(result.ttft_times, n=20)[18]
            result.p99_ttft = statistics.quantiles(result.ttft_times, n=100)[98]
        
        if result.tokens_per_second:
            result.mean_tokens_per_sec = statistics.mean(result.tokens_per_second)
    
    def _display_load_test_results(self, results: BenchmarkResults):
        """Display comprehensive load test results"""
        
        # Summary table
        table = Table(title=f"🔥 Load Test Results: {results.config.name}")
        
        table.add_column("Service", style="cyan", no_wrap=True) 
        table.add_column("Requests", style="white")
        table.add_column("Success Rate", style="green")
        table.add_column("Mean Response", style="blue")
        table.add_column("P95 Response", style="yellow")
        table.add_column("Mean TTFT", style="magenta")
        table.add_column("Tokens/sec", style="green")
        
        for service_name, result in results.services.items():
            success_rate = (result.successful_requests / result.total_requests * 100) if result.total_requests > 0 else 0
            
            # Format values
            requests_str = f"{result.successful_requests}/{result.total_requests}"
            success_str = f"{success_rate:.1f}%"
            mean_resp_str = f"{result.mean_response_time:.0f}ms" if result.mean_response_time > 0 else "N/A"
            p95_resp_str = f"{result.p95_response_time:.0f}ms" if result.p95_response_time > 0 else "N/A"
            mean_ttft_str = f"{result.mean_ttft:.1f}ms" if result.mean_ttft > 0 else "N/A"
            tps_str = f"{result.mean_tokens_per_sec:.1f}" if result.mean_tokens_per_sec > 0 else "N/A"
            
            table.add_row(
                service_name.upper(),
                requests_str,
                success_str,
                mean_resp_str,
                p95_resp_str,
                mean_ttft_str,
                tps_str
            )
        
        console.print(table)
        
        # Winner announcement
        winner = results.get_winner()
        if winner:
            winner_result = results.services[winner]
            console.print(f"\n[bold green]🏆 Performance Winner: {winner.upper()}[/bold green]")
            console.print(f"[green]P95 Latency: {winner_result.p95_response_time:.0f}ms[/green]")
            
            # Check targets
            ttft_target_met = winner_result.mean_ttft < results.config.target_ttft_ms if winner_result.mean_ttft > 0 else False
            p95_target_met = winner_result.p95_response_time < results.config.target_p95_ms
            
            if ttft_target_met and p95_target_met:
                console.print("[bold green]✅ All performance targets met![/bold green]")
            else:
                console.print("[yellow]⚠️ Some performance targets not met[/yellow]")

# Helper functions for notebook usage
async def run_quick_ttft_test(client: UnifiedAPIClient, prompt: str = "What is machine learning?") -> Dict[str, List[float]]:
    """Quick TTFT test for notebook"""
    ttft_benchmark = TTFTBenchmark(client)
    request = create_chat_request(prompt, max_tokens=50)
    return await ttft_benchmark.compare_ttft(request, iterations=3)

async def run_load_test_suite(client: UnifiedAPIClient, prompts: List[str]) -> List[BenchmarkResults]:
    """Run complete load test suite"""
    load_benchmark = LoadTestBenchmark(client)
    
    # Define test configurations
    configs = [
        BenchmarkConfig(
            name="quick_latency",
            concurrent_users=5,
            duration_seconds=30,
            max_tokens=50,
            target_ttft_ms=100.0,
            target_p95_ms=500.0
        ),
        BenchmarkConfig(
            name="standard_load", 
            concurrent_users=15,
            duration_seconds=60,
            max_tokens=100,
            target_ttft_ms=100.0,
            target_p95_ms=1000.0
        ),
        BenchmarkConfig(
            name="stress_test",
            concurrent_users=25,
            duration_seconds=90,
            max_tokens=150,
            target_ttft_ms=150.0,
            target_p95_ms=2000.0
        )
    ]
    
    results = []
    for config in configs:
        console.print(f"\n[bold blue]🚀 Starting {config.name}...[/bold blue]")
        result = await load_benchmark.run_load_test(config, prompts)
        results.append(result)
        
        # Brief pause between tests
        await asyncio.sleep(5)
    
    return results

def load_test_prompts(prompts_file: Path) -> List[str]:
    """Load test prompts from file"""
    try:
        with open(prompts_file, 'r') as f:
            content = f.read()
        
        # Extract prompts (simple parsing)
        prompts = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('==='):
                if '?' in line or len(line) > 10:  # Filter for actual prompts
                    prompts.append(line)
        
        return prompts[:20]  # Limit to first 20 prompts
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not load prompts file: {e}[/yellow]")
        # Return default prompts
        return [
            "What is the capital of France?",
            "Explain machine learning in simple terms.",
            "Write a short poem about technology.",
            "How does photosynthesis work?",
            "What are the benefits of renewable energy?",
            "Describe the water cycle briefly.",
            "What is artificial intelligence?",
            "How do computers process information?",
            "Explain quantum computing basics.",
            "What makes a good software engineer?"
        ]
