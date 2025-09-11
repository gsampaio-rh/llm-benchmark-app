"""
Configuration Management for vLLM Benchmarking
YAML-based configuration with validation and defaults
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel

console = Console()

@dataclass
class ServiceConfig:
    """Service-specific configuration"""
    namespace: str = "vllm-benchmark"
    manual_urls: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    health_check_retries: int = 3

@dataclass
class TTFTTestConfig:
    """TTFT (Time to First Token) test configuration"""
    enabled: bool = True
    iterations: int = 5
    target_ms: int = 100
    warmup_requests: int = 2
    max_tokens: int = 50
    temperature: float = 0.7

@dataclass
class LoadTestConfig:
    """Load test scenario configuration"""
    name: str = "default"
    concurrent_users: int = 10
    duration_seconds: int = 60
    target_p95_ms: int = 1000
    ramp_up_seconds: int = 5
    max_tokens: int = 256
    temperature: float = 0.7

@dataclass
class BenchmarkConfig:
    """Main benchmark configuration"""
    name: str = "vLLM vs TGI vs Ollama"
    description: str = "Low-latency chat benchmarking"
    model: str = "Qwen/Qwen2.5-7B"
    
    # Sub-configurations
    services: ServiceConfig = field(default_factory=ServiceConfig)
    ttft_test: TTFTTestConfig = field(default_factory=TTFTTestConfig)
    load_tests: List[LoadTestConfig] = field(default_factory=list)
    
    # Output configuration
    output_dir: str = "results"
    save_raw_data: bool = True
    generate_charts: bool = True
    generate_report: bool = True
    
    def __post_init__(self):
        """Initialize default load tests if none provided"""
        if not self.load_tests:
            self.load_tests = [
                LoadTestConfig(
                    name="quick_latency",
                    concurrent_users=5,
                    duration_seconds=30,
                    target_p95_ms=500
                ),
                LoadTestConfig(
                    name="standard_load",
                    concurrent_users=25,
                    duration_seconds=60,
                    target_p95_ms=1000
                ),
                LoadTestConfig(
                    name="stress_test",
                    concurrent_users=50,
                    duration_seconds=120,
                    target_p95_ms=2000
                )
            ]

class ConfigManager:
    """Configuration management with YAML support"""
    
    def __init__(self):
        self.config_dir = Path("config")
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self, config_path: Optional[str] = None) -> BenchmarkConfig:
        """Load configuration from YAML file or use defaults"""
        if config_path:
            config_file = Path(config_path)
        else:
            # Try default locations
            default_configs = [
                self.config_dir / "default.yaml",
                self.config_dir / "benchmark.yaml",
                Path("benchmark.yaml")
            ]
            
            config_file = None
            for candidate in default_configs:
                if candidate.exists():
                    config_file = candidate
                    break
        
        if config_file and config_file.exists():
            console.print(f"[blue]📄 Loading configuration from: {config_file}[/blue]")
            return self._load_from_yaml(config_file)
        else:
            console.print("[yellow]⚠️ No configuration file found, using defaults[/yellow]")
            return BenchmarkConfig()
    
    def _load_from_yaml(self, config_file: Path) -> BenchmarkConfig:
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            return self._dict_to_config(data)
            
        except Exception as e:
            console.print(f"[red]❌ Error loading config file: {e}[/red]")
            console.print("[yellow]Using default configuration[/yellow]")
            return BenchmarkConfig()
    
    def _dict_to_config(self, data: Dict[str, Any]) -> BenchmarkConfig:
        """Convert dictionary to BenchmarkConfig"""
        # Extract main benchmark settings
        benchmark_data = data.get("benchmark", {})
        
        # Extract services configuration
        services_data = data.get("services", {})
        services_config = ServiceConfig(
            namespace=services_data.get("namespace", "vllm-benchmark"),
            manual_urls=services_data.get("manual_urls", {}),
            timeout_seconds=services_data.get("timeout_seconds", 30),
            health_check_retries=services_data.get("health_check_retries", 3)
        )
        
        # Extract test scenarios
        test_scenarios = data.get("test_scenarios", {})
        
        # TTFT test configuration
        ttft_data = test_scenarios.get("ttft", {})
        ttft_config = TTFTTestConfig(
            enabled=ttft_data.get("enabled", True),
            iterations=ttft_data.get("iterations", 5),
            target_ms=ttft_data.get("target_ms", 100),
            warmup_requests=ttft_data.get("warmup_requests", 2),
            max_tokens=ttft_data.get("max_tokens", 50),
            temperature=ttft_data.get("temperature", 0.7)
        )
        
        # Load test configurations
        load_tests_data = test_scenarios.get("load_tests", [])
        load_tests = []
        for test_data in load_tests_data:
            load_test = LoadTestConfig(
                name=test_data.get("name", "default"),
                concurrent_users=test_data.get("concurrent_users", 10),
                duration_seconds=test_data.get("duration_seconds", 60),
                target_p95_ms=test_data.get("target_p95_ms", 1000),
                ramp_up_seconds=test_data.get("ramp_up_seconds", 5),
                max_tokens=test_data.get("max_tokens", 256),
                temperature=test_data.get("temperature", 0.7)
            )
            load_tests.append(load_test)
        
        # Extract output configuration
        output_data = data.get("output", {})
        
        return BenchmarkConfig(
            name=benchmark_data.get("name", "vLLM vs TGI vs Ollama"),
            description=benchmark_data.get("description", "Low-latency chat benchmarking"),
            model=benchmark_data.get("model", "Qwen/Qwen2.5-7B"),
            services=services_config,
            ttft_test=ttft_config,
            load_tests=load_tests,
            output_dir=output_data.get("directory", "results"),
            save_raw_data=output_data.get("save_raw_data", True),
            generate_charts=output_data.get("generate_charts", True),
            generate_report=output_data.get("generate_report", True)
        )
    
    def save_config(self, config: BenchmarkConfig, config_path: str):
        """Save configuration to YAML file"""
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert config to dictionary
        config_dict = self._config_to_dict(config)
        
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            console.print(f"[green]✅ Configuration saved to: {config_file}[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error saving config file: {e}[/red]")
    
    def _config_to_dict(self, config: BenchmarkConfig) -> Dict[str, Any]:
        """Convert BenchmarkConfig to dictionary"""
        return {
            "benchmark": {
                "name": config.name,
                "description": config.description,
                "model": config.model
            },
            "services": {
                "namespace": config.services.namespace,
                "manual_urls": config.services.manual_urls,
                "timeout_seconds": config.services.timeout_seconds,
                "health_check_retries": config.services.health_check_retries
            },
            "test_scenarios": {
                "ttft": {
                    "enabled": config.ttft_test.enabled,
                    "iterations": config.ttft_test.iterations,
                    "target_ms": config.ttft_test.target_ms,
                    "warmup_requests": config.ttft_test.warmup_requests,
                    "max_tokens": config.ttft_test.max_tokens,
                    "temperature": config.ttft_test.temperature
                },
                "load_tests": [
                    {
                        "name": test.name,
                        "concurrent_users": test.concurrent_users,
                        "duration_seconds": test.duration_seconds,
                        "target_p95_ms": test.target_p95_ms,
                        "ramp_up_seconds": test.ramp_up_seconds,
                        "max_tokens": test.max_tokens,
                        "temperature": test.temperature
                    }
                    for test in config.load_tests
                ]
            },
            "output": {
                "directory": config.output_dir,
                "save_raw_data": config.save_raw_data,
                "generate_charts": config.generate_charts,
                "generate_report": config.generate_report
            }
        }
    
    def create_example_configs(self):
        """Create example configuration files"""
        configs = {
            "default.yaml": self._get_default_config(),
            "quick-test.yaml": self._get_quick_test_config(),
            "stress-test.yaml": self._get_stress_test_config()
        }
        
        for filename, config_dict in configs.items():
            config_file = self.config_dir / filename
            
            if not config_file.exists():
                try:
                    with open(config_file, 'w') as f:
                        yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                    console.print(f"[green]✅ Created example config: {config_file}[/green]")
                except Exception as e:
                    console.print(f"[red]❌ Error creating {filename}: {e}[/red]")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration dictionary"""
        return {
            "benchmark": {
                "name": "vLLM vs TGI vs Ollama - Default",
                "description": "Standard benchmarking configuration",
                "model": "Qwen/Qwen2.5-7B"
            },
            "services": {
                "namespace": "vllm-benchmark",
                "manual_urls": {
                    # "vllm": "https://vllm-route.apps.cluster.com",
                    # "tgi": "https://tgi-route.apps.cluster.com",
                    # "ollama": "https://ollama-route.apps.cluster.com"
                },
                "timeout_seconds": 30,
                "health_check_retries": 3
            },
            "test_scenarios": {
                "ttft": {
                    "enabled": True,
                    "iterations": 5,
                    "target_ms": 100,
                    "warmup_requests": 2,
                    "max_tokens": 50,
                    "temperature": 0.7
                },
                "load_tests": [
                    {
                        "name": "quick_latency",
                        "concurrent_users": 5,
                        "duration_seconds": 30,
                        "target_p95_ms": 500,
                        "ramp_up_seconds": 5,
                        "max_tokens": 256,
                        "temperature": 0.7
                    },
                    {
                        "name": "standard_load",
                        "concurrent_users": 25,
                        "duration_seconds": 60,
                        "target_p95_ms": 1000,
                        "ramp_up_seconds": 10,
                        "max_tokens": 256,
                        "temperature": 0.7
                    }
                ]
            },
            "output": {
                "directory": "results",
                "save_raw_data": True,
                "generate_charts": True,
                "generate_report": True
            }
        }
    
    def _get_quick_test_config(self) -> Dict[str, Any]:
        """Get quick test configuration"""
        config = self._get_default_config()
        config["benchmark"]["name"] = "vLLM vs TGI vs Ollama - Quick Test"
        config["benchmark"]["description"] = "Fast latency test for demo purposes"
        
        # Reduce test scenarios for speed
        config["test_scenarios"]["ttft"]["iterations"] = 3
        config["test_scenarios"]["load_tests"] = [
            {
                "name": "demo_test",
                "concurrent_users": 3,
                "duration_seconds": 15,
                "target_p95_ms": 500,
                "ramp_up_seconds": 2,
                "max_tokens": 100,
                "temperature": 0.7
            }
        ]
        
        return config
    
    def _get_stress_test_config(self) -> Dict[str, Any]:
        """Get stress test configuration"""
        config = self._get_default_config()
        config["benchmark"]["name"] = "vLLM vs TGI vs Ollama - Stress Test"
        config["benchmark"]["description"] = "Comprehensive stress testing with high load"
        
        # Increase test intensity
        config["test_scenarios"]["ttft"]["iterations"] = 10
        config["test_scenarios"]["load_tests"] = [
            {
                "name": "moderate_load",
                "concurrent_users": 25,
                "duration_seconds": 120,
                "target_p95_ms": 1000,
                "ramp_up_seconds": 15,
                "max_tokens": 256,
                "temperature": 0.7
            },
            {
                "name": "high_load",
                "concurrent_users": 50,
                "duration_seconds": 180,
                "target_p95_ms": 2000,
                "ramp_up_seconds": 30,
                "max_tokens": 256,
                "temperature": 0.7
            },
            {
                "name": "extreme_load",
                "concurrent_users": 100,
                "duration_seconds": 300,
                "target_p95_ms": 5000,
                "ramp_up_seconds": 60,
                "max_tokens": 512,
                "temperature": 0.7
            }
        ]
        
        return config
    
    def display_config(self, config: BenchmarkConfig):
        """Display configuration in a beautiful format"""
        config_text = f"""[bold blue]Benchmark Configuration[/bold blue]

[cyan]Name:[/cyan] {config.name}
[cyan]Description:[/cyan] {config.description}
[cyan]Model:[/cyan] {config.model}

[yellow]Services Configuration:[/yellow]
• Namespace: {config.services.namespace}
• Timeout: {config.services.timeout_seconds}s
• Manual URLs: {len(config.services.manual_urls or {})} configured

[yellow]TTFT Test:[/yellow]
• Enabled: {config.ttft_test.enabled}
• Iterations: {config.ttft_test.iterations}
• Target: < {config.ttft_test.target_ms}ms

[yellow]Load Tests:[/yellow]"""

        for test in config.load_tests:
            config_text += f"""
• {test.name}: {test.concurrent_users} users, {test.duration_seconds}s"""
        
        config_text += f"""

[yellow]Output Configuration:[/yellow]
• Directory: {config.output_dir}
• Raw Data: {config.save_raw_data}
• Charts: {config.generate_charts}
• Reports: {config.generate_report}"""
        
        console.print(Panel.fit(config_text, title="📋 Configuration", border_style="blue"))

# Helper functions for easy usage
def load_config(config_path: Optional[str] = None) -> BenchmarkConfig:
    """Load configuration from file or defaults"""
    manager = ConfigManager()
    return manager.load_config(config_path)

def create_example_configs():
    """Create example configuration files"""
    manager = ConfigManager()
    manager.create_example_configs()

def display_config(config: BenchmarkConfig):
    """Display configuration"""
    manager = ConfigManager()
    manager.display_config(config)
