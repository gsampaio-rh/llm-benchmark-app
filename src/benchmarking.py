"""
Benchmarking Engine for vLLM vs TGI vs Ollama
Core benchmarking functionality including TTFT measurement and load testing
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from statistics import mean, median, stdev
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

from .api_clients import UnifiedAPIClient, GenerationRequest, GenerationResponse, create_chat_request
from .config import BenchmarkConfig, TTFTTestConfig, LoadTestConfig

console = Console()

@dataclass
class TTFTResult:
    """Single TTFT measurement result"""
    service_name: str
    ttft_ms: float
    total_time_ms: float
    success: bool
    error: Optional[str] = None
    tokens_generated: int = 0
    iteration: int = 0

@dataclass
class TTFTBenchmarkResult:
    """Complete TTFT benchmark results for all services"""
    service_results: Dict[str, List[TTFTResult]] = field(default_factory=dict)
    target_ms: int = 100
    
    def get_statistics(self, service_name: str) -> Dict[str, float]:
        """Get statistics for a specific service"""
        results = self.service_results.get(service_name, [])
        successful_results = [r for r in results if r.success and r.ttft_ms > 0]
        
        if not successful_results:
            return {
                "count": 0,
                "success_rate": 0.0,
                "mean_ttft": 0.0,
                "median_ttft": 0.0,
                "p95_ttft": 0.0,
                "p99_ttft": 0.0,
                "std_dev": 0.0,
                "target_achieved": False
            }
        
        ttft_values = [r.ttft_ms for r in successful_results]
        ttft_values.sort()
        
        success_rate = len(successful_results) / len(results) if results else 0.0
        mean_ttft = mean(ttft_values)
        median_ttft = median(ttft_values)
        
        # Calculate percentiles
        p95_index = int(0.95 * len(ttft_values))
        p99_index = int(0.99 * len(ttft_values))
        p95_ttft = ttft_values[min(p95_index, len(ttft_values) - 1)]
        p99_ttft = ttft_values[min(p99_index, len(ttft_values) - 1)]
        
        std_dev = stdev(ttft_values) if len(ttft_values) > 1 else 0.0
        target_achieved = mean_ttft < self.target_ms
        
        return {
            "count": len(successful_results),
            "success_rate": success_rate,
            "mean_ttft": mean_ttft,
            "median_ttft": median_ttft,
            "p95_ttft": p95_ttft,
            "p99_ttft": p99_ttft,
            "std_dev": std_dev,
            "target_achieved": target_achieved
        }
    
    def get_winner(self) -> Optional[str]:
        """Determine the winner based on mean TTFT"""
        service_means = {}
        
        for service_name in self.service_results:
            stats = self.get_statistics(service_name)
            if stats["count"] > 0:
                service_means[service_name] = stats["mean_ttft"]
        
        if not service_means:
            return None
        
        return min(service_means.keys(), key=lambda x: service_means[x])

class TTFTBenchmark:
    """TTFT (Time To First Token) benchmarking with streaming-based measurement"""
    
    def __init__(self, config: TTFTTestConfig):
        self.config = config
        self.console = console
        
    async def run_benchmark(self, api_client: UnifiedAPIClient) -> TTFTBenchmarkResult:
        """Run TTFT benchmark against all available services"""
        self.console.print("\n[bold blue]⚡ TTFT Benchmark Starting[/bold blue]")
        
        # Get available services
        available_services = list(api_client.clients.keys())
        if not available_services:
            self.console.print("[red]❌ No services available for TTFT testing[/red]")
            return TTFTBenchmarkResult()
        
        self.console.print(f"[cyan]Testing services:[/cyan] {', '.join(available_services).upper()}")
        self.console.print(f"[cyan]Iterations per service:[/cyan] {self.config.iterations}")
        self.console.print(f"[cyan]Target TTFT:[/cyan] < {self.config.target_ms}ms")
        
        # Run warmup requests if configured
        if self.config.warmup_requests > 0:
            await self._run_warmup(api_client, available_services)
        
        # Create test request
        test_request = create_chat_request(
            "Hello! Please respond with a brief greeting.",
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        # Run TTFT measurements
        result = TTFTBenchmarkResult(target_ms=self.config.target_ms)
        
        # Initialize results dict
        for service_name in available_services:
            result.service_results[service_name] = []
        
        total_tests = len(available_services) * self.config.iterations
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            
            task = progress.add_task("Running TTFT measurements...", total=total_tests)
            
            # Run tests for each service
            for service_name in available_services:
                service_client = api_client.clients[service_name]
                
                for iteration in range(self.config.iterations):
                    progress.update(task, description=f"Testing {service_name.upper()} (iteration {iteration + 1})")
                    
                    ttft_result = await self._measure_ttft(service_client, service_name, test_request, iteration + 1)
                    result.service_results[service_name].append(ttft_result)
                    
                    progress.advance(task)
                    
                    # Small delay between iterations to avoid overwhelming services
                    await asyncio.sleep(0.1)
        
        # Display results
        self._display_ttft_results(result)
        
        return result
    
    async def _run_warmup(self, api_client: UnifiedAPIClient, services: List[str]):
        """Run warmup requests to prepare services"""
        self.console.print(f"[yellow]🔥 Running {self.config.warmup_requests} warmup requests...[/yellow]")
        
        warmup_request = create_chat_request("Hello", max_tokens=10, temperature=0.7)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("Warming up services..."),
            console=self.console,
        ) as progress:
            task = progress.add_task("", total=self.config.warmup_requests * len(services))
            
            for _ in range(self.config.warmup_requests):
                # Run warmup for all services concurrently
                tasks = []
                for service_name in services:
                    client = api_client.clients[service_name]
                    tasks.append(client.generate(warmup_request))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                progress.advance(task, len(services))
    
    async def _measure_ttft(self, client, service_name: str, request: GenerationRequest, iteration: int) -> TTFTResult:
        """Measure TTFT for a single request using streaming"""
        try:
            start_time = time.time()
            first_token_time = None
            tokens_count = 0
            
            # Use streaming to capture first token timing
            async for token in client.generate_stream(request):
                if first_token_time is None:
                    first_token_time = time.time()
                tokens_count += 1
                
                # We only need the first few tokens for TTFT measurement
                if tokens_count >= 5:
                    break
            
            total_time = time.time() - start_time
            
            if first_token_time is not None:
                ttft_ms = (first_token_time - start_time) * 1000
                return TTFTResult(
                    service_name=service_name,
                    ttft_ms=ttft_ms,
                    total_time_ms=total_time * 1000,
                    success=True,
                    tokens_generated=tokens_count,
                    iteration=iteration
                )
            else:
                return TTFTResult(
                    service_name=service_name,
                    ttft_ms=0.0,
                    total_time_ms=total_time * 1000,
                    success=False,
                    error="No tokens received",
                    iteration=iteration
                )
                
        except Exception as e:
            return TTFTResult(
                service_name=service_name,
                ttft_ms=0.0,
                total_time_ms=0.0,
                success=False,
                error=str(e),
                iteration=iteration
            )
    
    def _display_ttft_results(self, result: TTFTBenchmarkResult):
        """Display beautiful TTFT results table"""
        self.console.print("\n[bold yellow]⚡ TTFT Benchmark Results[/bold yellow]")
        
        table = Table(title="Time To First Token Comparison")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Success Rate", style="green")
        table.add_column("Mean TTFT", style="yellow")
        table.add_column("Median TTFT", style="yellow")
        table.add_column("P95 TTFT", style="orange1")
        table.add_column("Target Met", style="magenta")
        table.add_column("Std Dev", style="blue")
        
        services_stats = []
        
        for service_name in result.service_results:
            stats = result.get_statistics(service_name)
            
            if stats["count"] > 0:
                # Format values
                success_rate = f"{stats['success_rate']:.1%}"
                mean_ttft = f"{stats['mean_ttft']:.1f}ms"
                median_ttft = f"{stats['median_ttft']:.1f}ms"
                p95_ttft = f"{stats['p95_ttft']:.1f}ms"
                target_met = "✅ Yes" if stats["target_achieved"] else "❌ No"
                std_dev = f"{stats['std_dev']:.1f}ms"
                
                # Color code based on performance
                if stats["target_achieved"]:
                    mean_ttft = f"[green]{mean_ttft}[/green]"
                else:
                    mean_ttft = f"[red]{mean_ttft}[/red]"
                
                services_stats.append((service_name, stats["mean_ttft"]))
            else:
                success_rate = "0%"
                mean_ttft = "[red]Failed[/red]"
                median_ttft = "N/A"
                p95_ttft = "N/A"
                target_met = "❌ No"
                std_dev = "N/A"
            
            table.add_row(
                service_name.upper(),
                success_rate,
                mean_ttft,
                median_ttft,
                p95_ttft,
                target_met,
                std_dev
            )
        
        self.console.print(table)
        
        # Display winner
        winner = result.get_winner()
        if winner and services_stats:
            # Sort by performance
            services_stats.sort(key=lambda x: x[1])
            
            self.console.print(f"\n[bold green]🏆 TTFT Winner: {winner.upper()} ({services_stats[0][1]:.1f}ms)[/bold green]")
            
            # Show performance comparison
            if len(services_stats) > 1:
                improvement = ((services_stats[1][1] - services_stats[0][1]) / services_stats[1][1]) * 100
                self.console.print(f"[dim]Performance improvement: {improvement:.1f}% faster than {services_stats[1][0].upper()}[/dim]")

@dataclass
class LoadTestResult:
    """Single load test measurement result"""
    service_name: str
    response_time_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: float = 0.0
    tokens_generated: int = 0
    user_id: int = 0

@dataclass 
class ServiceBenchmarkResult:
    """Complete benchmark results for a service across a load test"""
    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time_seconds: float = 0.0
    response_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    target_p95_ms: int = 1000
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        return (self.successful_requests / self.total_requests) * 100 if self.total_requests > 0 else 0.0
    
    @property 
    def requests_per_second(self) -> float:
        """Calculate requests per second"""
        return self.total_requests / self.total_time_seconds if self.total_time_seconds > 0 else 0.0
    
    def get_percentiles(self) -> Dict[str, float]:
        """Calculate response time percentiles"""
        if not self.response_times:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}
        
        sorted_times = sorted(self.response_times)
        n = len(sorted_times)
        
        return {
            "p50": sorted_times[int(0.50 * n)],
            "p95": sorted_times[int(0.95 * n)],
            "p99": sorted_times[int(0.99 * n)],
            "mean": mean(sorted_times)
        }
    
    @property
    def target_achieved(self) -> bool:
        """Check if P95 target was achieved"""
        percentiles = self.get_percentiles()
        return percentiles["p95"] < self.target_p95_ms

class LoadTestBenchmark:
    """Concurrent load testing with user simulation"""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.console = console
        
    async def run_benchmark(self, api_client: UnifiedAPIClient) -> Dict[str, ServiceBenchmarkResult]:
        """Run load test against all available services"""
        self.console.print(f"\n[bold blue]📊 Load Test: {self.config.name}[/bold blue]")
        
        available_services = list(api_client.clients.keys())
        if not available_services:
            self.console.print("[red]❌ No services available for load testing[/red]")
            return {}
        
        self.console.print(f"[cyan]Testing services:[/cyan] {', '.join(available_services).upper()}")
        self.console.print(f"[cyan]Concurrent users:[/cyan] {self.config.concurrent_users}")
        self.console.print(f"[cyan]Duration:[/cyan] {self.config.duration_seconds}s")
        self.console.print(f"[cyan]Target P95:[/cyan] < {self.config.target_p95_ms}ms")
        
        # Initialize results
        results = {}
        for service_name in available_services:
            results[service_name] = ServiceBenchmarkResult(
                service_name=service_name,
                target_p95_ms=self.config.target_p95_ms
            )
        
        # Run load tests for each service
        for service_name in available_services:
            self.console.print(f"\n[yellow]🚀 Testing {service_name.upper()}...[/yellow]")
            service_result = await self._run_service_load_test(api_client.clients[service_name], service_name)
            results[service_name] = service_result
        
        # Display results
        self._display_load_test_results(results)
        
        return results
    
    async def _run_service_load_test(self, client, service_name: str) -> ServiceBenchmarkResult:
        """Run load test for a single service"""
        result = ServiceBenchmarkResult(
            service_name=service_name,
            target_p95_ms=self.config.target_p95_ms
        )
        
        # Create test prompts
        test_prompts = [
            "Hello! How are you today?",
            "What's the weather like?", 
            "Tell me a short joke.",
            "Explain quantum computing briefly.",
            "What's your favorite color?",
            "How do computers work?",
            "Write a haiku about technology.",
            "What is artificial intelligence?"
        ]
        
        start_time = time.time()
        
        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            
            task = progress.add_task(f"Load testing {service_name.upper()}", total=100)
            
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(self.config.concurrent_users)
            
            # Track active tasks
            active_tasks = []
            user_counter = 0
            
            # Run for specified duration
            while time.time() - start_time < self.config.duration_seconds:
                # Update progress
                elapsed = time.time() - start_time
                progress_pct = (elapsed / self.config.duration_seconds) * 100
                progress.update(task, completed=min(progress_pct, 100))
                
                # Create user request task
                user_counter += 1
                prompt = random.choice(test_prompts)
                request = create_chat_request(
                    prompt,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )
                
                task_coro = self._simulate_user_request(
                    client, request, user_counter, semaphore
                )
                active_tasks.append(asyncio.create_task(task_coro))
                
                # Clean up completed tasks
                active_tasks = [t for t in active_tasks if not t.done()]
                
                # Collect completed results
                for task_obj in [t for t in active_tasks if t.done()]:
                    try:
                        load_result = await task_obj
                        result.total_requests += 1
                        
                        if load_result.success:
                            result.successful_requests += 1
                            result.response_times.append(load_result.response_time_ms)
                        else:
                            result.failed_requests += 1
                            if load_result.error:
                                result.errors.append(load_result.error)
                    except Exception as e:
                        result.failed_requests += 1
                        result.errors.append(str(e))
                
                # Think time between requests (simulate real users)
                await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # Wait for remaining tasks to complete
            if active_tasks:
                progress.update(task, description=f"Finishing {service_name.upper()} requests...")
                remaining_results = await asyncio.gather(*active_tasks, return_exceptions=True)
                
                for load_result in remaining_results:
                    if isinstance(load_result, LoadTestResult):
                        result.total_requests += 1
                        if load_result.success:
                            result.successful_requests += 1
                            result.response_times.append(load_result.response_time_ms)
                        else:
                            result.failed_requests += 1
                            if load_result.error:
                                result.errors.append(load_result.error)
                    elif isinstance(load_result, Exception):
                        result.failed_requests += 1
                        result.errors.append(str(load_result))
        
        result.total_time_seconds = time.time() - start_time
        return result
    
    async def _simulate_user_request(self, client, request: GenerationRequest, 
                                   user_id: int, semaphore: asyncio.Semaphore) -> LoadTestResult:
        """Simulate a single user request with proper throttling"""
        async with semaphore:
            try:
                start_time = time.time()
                response = await client.generate(request)
                response_time = (time.time() - start_time) * 1000
                
                if response.error:
                    return LoadTestResult(
                        service_name=client.service_type.value,
                        response_time_ms=response_time,
                        success=False,
                        error=response.error,
                        timestamp=start_time,
                        user_id=user_id
                    )
                else:
                    return LoadTestResult(
                        service_name=client.service_type.value,
                        response_time_ms=response_time,
                        success=True,
                        timestamp=start_time,
                        tokens_generated=response.metrics.tokens_generated,
                        user_id=user_id
                    )
                    
            except Exception as e:
                return LoadTestResult(
                    service_name=client.service_type.value,
                    response_time_ms=0.0,
                    success=False,
                    error=str(e),
                    timestamp=time.time(),
                    user_id=user_id
                )
    
    def _display_load_test_results(self, results: Dict[str, ServiceBenchmarkResult]):
        """Display beautiful load test results"""
        self.console.print(f"\n[bold yellow]📊 Load Test Results: {self.config.name}[/bold yellow]")
        
        table = Table(title="Load Test Performance Comparison")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Success Rate", style="green")
        table.add_column("RPS", style="yellow")
        table.add_column("Mean", style="blue")
        table.add_column("P95", style="orange1")
        table.add_column("P99", style="red")
        table.add_column("Target Met", style="magenta")
        
        service_scores = []
        
        for service_name, result in results.items():
            percentiles = result.get_percentiles()
            
            success_rate = f"{result.success_rate:.1f}%"
            rps = f"{result.requests_per_second:.1f}"
            mean_time = f"{percentiles['mean']:.0f}ms"
            p95_time = f"{percentiles['p95']:.0f}ms"
            p99_time = f"{percentiles['p99']:.0f}ms"
            target_met = "✅ Yes" if result.target_achieved else "❌ No"
            
            # Color code P95 based on target
            if result.target_achieved:
                p95_time = f"[green]{p95_time}[/green]"
            else:
                p95_time = f"[red]{p95_time}[/red]"
            
            table.add_row(
                service_name.upper(),
                success_rate,
                rps,
                mean_time,
                p95_time,
                p99_time,
                target_met
            )
            
            # Calculate composite score for ranking
            score = result.success_rate + (10000 / max(percentiles['p95'], 1))  # Higher success rate, lower latency = higher score
            service_scores.append((service_name, score, percentiles['p95']))
        
        self.console.print(table)
        
        # Display winner
        if service_scores:
            service_scores.sort(key=lambda x: x[1], reverse=True)  # Sort by score, highest first
            winner = service_scores[0]
            
            self.console.print(f"\n[bold green]🏆 Load Test Winner: {winner[0].upper()} (P95: {winner[2]:.0f}ms)[/bold green]")
            
            # Show comparison with second place
            if len(service_scores) > 1:
                second = service_scores[1]
                improvement = ((second[2] - winner[2]) / second[2]) * 100
                self.console.print(f"[dim]P95 latency improvement: {improvement:.1f}% better than {second[0].upper()}[/dim]")
