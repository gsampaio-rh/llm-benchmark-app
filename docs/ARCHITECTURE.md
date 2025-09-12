# 🏗️ Architecture Guide

## **System Overview**

The vLLM vs TGI vs Ollama Benchmarking Suite is built with a **modular, enterprise-grade architecture** following FAANG-level design principles. The system underwent a major refactoring in **Phase 1.2** to achieve maintainable, focused components.

### **Design Philosophy**
- **CLI-First Design**: Modern command-line interface built with Python Click and Rich
- **Modular Architecture**: Clean separation of concerns with focused modules (≤400 lines each)
- **Service Discovery**: Smart multi-layer discovery with graceful fallbacks
- **Organized Results**: Clean test_id_datetime structure for easy management
- **Production Ready**: Robust error handling, logging, and deployment automation

---

## 🎯 **Architecture Transformation**

### **Phase 1.2 Refactoring Results**

**Before (Monolithic)**:
- 940-line main CLI file with 15 commands
- Large monolithic modules (600+ lines)
- Overlapping functionality across commands
- Difficult to maintain and test

**After (Modular)**:
- 86-line streamlined CLI with 9 focused commands
- Modular command handlers (150-200 lines each)
- Clean separation of concerns
- FAANG-level architecture with single responsibility principle

### **CLI Command Consolidation**
| Before | After | Change |
|--------|--------|--------|
| `race`, `conversation`, `try-it` | `demo` (unified with modes) | 3 → 1 command |
| `cleanup`, `migrate`, `reprocess` | *(removed)* | Unnecessary maintenance |
| 15 total commands | 9 focused commands | 40% reduction |

---

## 📦 **Modular Architecture**

### **Project Structure** (Phase 1.2 Refactored)
```
vllm-notebooks/
├── vllm_benchmark.py          # 🎯 Main CLI script (86 lines, streamlined!)
├── src/                       # 📦 Modular architecture
│   ├── cli/                   # 🎛️ CLI command modules
│   │   ├── commands/          # Individual command handlers
│   │   │   ├── benchmark_cmd.py    # Core benchmarking (150 lines)
│   │   │   ├── demo_cmd.py         # Unified demo modes (200 lines)
│   │   │   ├── config_cmd.py       # Configuration (80 lines)
│   │   │   ├── service_cmd.py      # Service operations (120 lines)
│   │   │   ├── results_cmd.py      # Results management (100 lines)
│   │   │   └── inspect_cmd.py      # Technical inspection (160 lines)
│   │   └── utils/             # CLI utilities
│   │       ├── console_utils.py    # Rich console helpers
│   │       └── async_utils.py      # Async execution
│   ├── orchestrator.py        # Central coordination
│   ├── race/                  # Performance racing engine
│   ├── analytics/             # Metrics & business impact
│   ├── visualization/         # Modular UI components
│   ├── integrations/          # API adapters & service discovery
│   ├── demo/                  # High-quality simulation
│   ├── conversation/          # Message threading models
│   └── legacy modules...      # Backward compatibility
├── config/                    # 📝 Configuration presets
├── helm/                      # ⚙️ Kubernetes deployment
│   ├── vllm/, tgi/, ollama/   # Service Helm charts
├── results/                   # 📊 Organized test outputs
└── docs/                      # 📚 Documentation
```

---

## 🎛️ **CLI Architecture**

### **Main CLI Entry Point** (`vllm_benchmark.py`)
```python
# Streamlined 86-line main script
@click.group()
def cli():
    """Main CLI entry with header and version"""
    print_header(console)

# Modular command registration
cli.add_command(benchmark)  # from src.cli.commands.benchmark_cmd
cli.add_command(demo)       # from src.cli.commands.demo_cmd
cli.add_command(discover)   # from src.cli.commands.service_cmd
# ... etc
```

### **Command Handler Architecture**
Each command is implemented in a focused module:

#### **Demo Command** (`src/cli/commands/demo_cmd.py`)
```python
@click.command()
@click.option("--mode", type=click.Choice(['race', 'conversation', 'interactive']))
def demo(mode, scenario, prompt, runs, mock, services):
    """Unified demo command consolidating race/conversation/interactive"""
    
    if not mode:
        mode = _show_mode_selector(console)  # Interactive selection
    
    if mode == 'race':
        _run_race_demo(console, prompt, runs, mock, services)
    elif mode == 'conversation':  
        _run_conversation_demo(console, scenario, mock, services)
    elif mode == 'interactive':
        _run_interactive_demo(console, mock, services)
```

#### **Benchmark Command** (`src/cli/commands/benchmark_cmd.py`)
```python
@click.command()
@click.option("--config", help="Configuration file path")
def benchmark(config, namespace, concurrent_users, quick, dry_run):
    """Core benchmarking functionality with async workflow"""
    
    # Load configuration with CLI overrides
    benchmark_config = load_config(config if not quick else "config/quick-test.yaml")
    
    # Apply CLI parameter overrides
    if concurrent_users:
        for test in benchmark_config.load_tests:
            test.concurrent_users = concurrent_users
    
    # Run async benchmarking workflow
    asyncio.run(_run_benchmark(benchmark_config, console))
```

---

## 🔌 **Core Components**

### **1. Service Discovery** (`src/service_discovery.py`)
**Multi-layer discovery strategy** with graceful fallbacks:

```python
async def discover_services(namespace, manual_urls=None):
    """Smart service discovery with multiple strategies"""
    
    # 1. OpenShift Routes (preferred)
    routes = await _discover_openshift_routes(namespace)
    
    # 2. Kubernetes Ingress
    if not routes:
        ingress = await _discover_kubernetes_ingress(namespace)
    
    # 3. NodePort Services with External IP
    if not ingress:
        nodeports = await _discover_nodeport_services(namespace)
    
    # 4. Manual URL Override
    if manual_urls:
        manual_services = _parse_manual_urls(manual_urls)
    
    # Health check all discovered services
    return await _health_check_services(discovered_services)
```

**Features**:
- **TLS Auto-detection**: Automatic HTTPS/HTTP protocol detection
- **Multiple Health Endpoints**: Tests `/health`, `/api/tags`, `/v1/models`
- **External IP Resolution**: For NodePort services in cloud environments
- **Graceful Degradation**: Falls back through discovery methods

### **2. API Clients** (`src/api_clients.py`)
**Unified API abstraction** supporting different service protocols:

```python
class UnifiedAPIClient:
    """Unified interface for vLLM, TGI, and Ollama APIs"""
    
    def __init__(self, service_urls: Dict[str, str]):
        self.clients = {
            'vllm': VLLMClient(service_urls.get('vllm')),
            'tgi': TGIClient(service_urls.get('tgi')),
            'ollama': OllamaClient(service_urls.get('ollama'))
        }
    
    async def generate_comparison(self, request: GenerationRequest):
        """Generate responses from all available services concurrently"""
        tasks = []
        for service_name, client in self.clients.items():
            if client and client.is_healthy:
                tasks.append(self._generate_single(service_name, client, request))
        
        return await asyncio.gather(*tasks, return_exceptions=True)
```

**Service-Specific Implementations**:
- **vLLM**: OpenAI-compatible `/v1/chat/completions` with streaming
- **TGI**: HuggingFace `/generate_stream` endpoint  
- **Ollama**: Native `/api/generate` and `/api/chat` endpoints

### **3. Benchmarking Engine** (`src/benchmarking.py`)
**Scientific performance measurement** with statistical analysis:

#### **TTFT Measurement**
```python
class TTFTBenchmark:
    """Sub-millisecond TTFT measurement via streaming"""
    
    async def measure_ttft(self, client, request):
        """Measure Time To First Token with streaming capture"""
        
        start_time = time.perf_counter()
        
        async for chunk in client.stream_generate(request):
            if self._is_first_token(chunk):
                first_token_time = time.perf_counter()
                ttft_ms = (first_token_time - start_time) * 1000
                return ttft_ms
                
        return None  # No tokens received
```

#### **Load Testing**
```python
class LoadTestBenchmark:
    """Concurrent user simulation with real behavior patterns"""
    
    async def run_concurrent_users(self, num_users, duration_seconds):
        """Simulate realistic user load patterns"""
        
        # Create user sessions with staggered start times
        user_tasks = []
        for user_id in range(num_users):
            delay = random.uniform(0, 10)  # Stagger arrivals
            task = asyncio.create_task(
                self._simulate_user_session(user_id, duration_seconds, delay)
            )
            user_tasks.append(task)
        
        # Collect results with progress tracking
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        return self._aggregate_results(results)
```

### **4. Statistical Analysis** (`src/metrics.py`)
**Comprehensive statistical analysis** with confidence intervals:

```python
class StatisticalAnalyzer:
    """Advanced statistical analysis for performance metrics"""
    
    def analyze_ttft_results(self, ttft_data):
        """Analyze TTFT with percentiles and winner determination"""
        
        analysis = {}
        for service, times in ttft_data.items():
            analysis[service] = {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'p95': numpy.percentile(times, 95),
                'p99': numpy.percentile(times, 99),
                'std_dev': statistics.stdev(times),
                'target_achievement': sum(1 for t in times if t < 100) / len(times)
            }
        
        # Winner determination with multiple criteria
        winner = self._determine_winner(analysis)
        return AnalysisResult(analysis, winner, confidence=0.95)
```

### **5. Visualization System** (`src/visualization/`)
**Modular visualization components** for different chart types:

#### **Component Architecture**
```python
# Core visualization infrastructure
src/visualization/
├── core/
│   ├── base_visualizer.py      # Base chart functionality
│   ├── display_components.py   # Display utilities
│   └── layout_manager.py       # Layout coordination
└── components/
    ├── race_display.py         # Live three-way racing
    ├── three_way_panel.py      # Reusable three-column layout
    ├── service_panel.py        # Individual service display
    ├── statistics_panel.py     # Analytics and metrics
    └── results_panel.py        # Race results and rankings
```

#### **Live Race Visualization**
```python
class RaceDisplay:
    """Live three-way race visualization with real-time updates"""
    
    async def show_live_race(self, race_data):
        """Display live racing with animated progress"""
        
        # Create three-column layout
        three_way_panel = ThreeWayPanel("🔵 VLLM", "🟢 TGI", "🟠 OLLAMA")
        
        # Update panels with real-time data
        for service_name, participant in race_data.participants.items():
            panel = three_way_panel.get_panel(service_name)
            panel.update_progress(participant.progress)
            panel.update_response(participant.current_response)
            panel.update_metrics(participant.ttft, participant.tokens_per_sec)
        
        # Display with Rich console
        self.console.print(three_way_panel.render())
```

---

## 🎭 **Demo System Architecture**

### **Unified Demo Command**
The demo system consolidates three previously separate commands into unified modes:

#### **Mode Selection**
```python
def _show_mode_selector(console: Console) -> str:
    """Interactive mode selection with descriptions"""
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Mode", style="cyan")
    table.add_column("Description", style="white") 
    table.add_column("Best For", style="green")
    
    table.add_row("1. race", "🏁 Live three-way performance race", "Seeing speed differences")
    table.add_row("2. conversation", "💬 Multi-turn conversation analysis", "Context retention")
    table.add_row("3. interactive", "🎮 Try-it-yourself with custom prompts", "Hands-on exploration")
    
    choice = console.input("Enter your choice (1-3): ")
    return {'1': 'race', '2': 'conversation', '3': 'interactive'}.get(choice)
```

#### **Scenario Management**
```python
# Predefined realistic scenarios
CONVERSATION_SCENARIOS = {
    1: {
        "name": "Customer Support",
        "description": "Kubernetes troubleshooting conversation",
        "scenario_key": "customer_support"
    },
    2: {
        "name": "Code Review", 
        "description": "Python function optimization discussion",
        "scenario_key": "code_review"
    },
    # ... 3 more scenarios
}
```

### **Service Personalities**
Each service displays distinct "personality" in demos:

- **🔵 vLLM**: Professional, technical, precise
- **🟢 TGI**: Engineering-focused, systematic, detailed  
- **🟠 Ollama**: Approachable, friendly, conversational

---

## 📊 **Results Organization**

### **Structured Test Management**
```python
class ResultsOrganizer:
    """Manages organized test runs with clean structure"""
    
    def create_test_run(self, test_name: str) -> str:
        """Create organized test directory structure"""
        
        # Generate clean test ID: test_{name}_{YYYYMMDD}_{HHMMSS}
        clean_name = re.sub(r'[^\w\-_]', '', test_name.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_id = f"test_{clean_name}_{timestamp}"
        
        # Create structured directories
        test_path = Path("results") / test_id
        test_path.mkdir(parents=True, exist_ok=True)
        
        # Service-specific directories
        for service in ["vllm", "tgi", "ollama"]:
            (test_path / service).mkdir(exist_ok=True)
        
        # Charts directory
        (test_path / "charts").mkdir(exist_ok=True)
        
        return test_id
```

### **Directory Structure**
```
results/
└── test_quicklatency_20250912_132000/    # Clean test_id_datetime format
    ├── comparison.json                   # Main benchmark results
    ├── summary.csv                       # Metrics summary  
    ├── executive_report.html             # Executive summary
    ├── detailed_analysis.json            # Technical analysis
    ├── test_manifest.json               # Test metadata
    ├── charts/                          # Interactive visualizations
    │   ├── ttft_analysis.html
    │   ├── load_dashboard.html
    │   └── performance_radar.html
    ├── vllm/                            # vLLM-specific data
    │   └── performance_log.csv
    ├── tgi/                             # TGI-specific data
    │   └── performance_log.csv
    └── ollama/                          # Ollama-specific data
        └── error_log.txt
```

---

## ⚙️ **Configuration System**

### **YAML Configuration Architecture**
```python
@dataclass
class BenchmarkConfig:
    """Main benchmark configuration with validation"""
    name: str = "vLLM vs TGI vs Ollama"
    description: str = "Low-latency chat benchmarking"
    model: str = "Qwen/Qwen2.5-7B"
    
    services: ServiceConfig = field(default_factory=ServiceConfig)
    ttft_test: TTFTTestConfig = field(default_factory=TTFTTestConfig)
    load_tests: List[LoadTestConfig] = field(default_factory=list)
    output: OutputConfig = field(default_factory=OutputConfig)
```

### **Configuration Presets**
- **`config/default.yaml`** - Standard benchmarking (30 min)
- **`config/quick-test.yaml`** - Quick demo (5 min)  
- **`config/stress-test.yaml`** - Production validation (60+ min)

### **CLI Override System**
```python
# Configuration hierarchy: CLI args > config file > defaults
if concurrent_users and benchmark_config.load_tests:
    for test in benchmark_config.load_tests:
        test.concurrent_users = concurrent_users  # CLI override

if duration and benchmark_config.load_tests:
    for test in benchmark_config.load_tests:
        test.duration_seconds = duration  # CLI override
```

---

## 🔧 **Error Handling & Resilience**

### **Comprehensive Error Classification**
```python
@dataclass 
class ErrorDetails:
    """Structured error information for user guidance"""
    error_type: str
    user_message: str
    technical_details: str
    suggested_actions: List[str]
    recovery_possible: bool

def handle_error(exception: Exception, context: str, component: str) -> ErrorDetails:
    """Classify errors and provide helpful guidance"""
    
    if isinstance(exception, ConnectionError):
        return ErrorDetails(
            error_type="connection_error",
            user_message="Unable to connect to AI service",
            technical_details=str(exception),
            suggested_actions=[
                "Check if services are running: kubectl get pods -n vllm-benchmark",
                "Verify network connectivity", 
                "Try using manual URLs with --manual-urls option"
            ],
            recovery_possible=True
        )
    # ... handle other error types
```

### **Graceful Degradation**
- **Service Discovery**: Falls back through multiple discovery methods
- **Demo Mode**: Automatically switches to simulation when services unavailable
- **Partial Results**: Continues with available services if some fail
- **Health Checks**: Continuous monitoring with automatic retry logic

---

## 🚀 **Deployment Architecture**

### **Kubernetes/OpenShift Integration**
```yaml
# Helm chart values with anti-affinity rules
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values: ["vllm", "tgi", "ollama"]
        topologyKey: kubernetes.io/hostname
```

### **Resource Management**
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    memory: "32Gi"
    cpu: "8"
  requests:
    nvidia.com/gpu: 1
    memory: "16Gi" 
    cpu: "4"
```

### **Service Discovery Integration**
- **OpenShift Routes**: Automatic HTTPS termination and load balancing
- **Kubernetes Ingress**: Standard ingress controller integration
- **NodePort Services**: External IP resolution for cloud environments
- **Manual Override**: Configuration-based URL specification

---

## 📈 **Monitoring & Observability**

### **Native Metrics Integration**
```python
# Service-specific metrics collection
NATIVE_METRICS = {
    'vllm': [
        'vllm:e2e_request_latency_seconds',
        'vllm:time_to_first_token_seconds',
        'vllm:request_queue_time_seconds'
    ],
    'tgi': [
        'tgi_request_duration',
        'tgi_request_inference_duration', 
        'tgi_queue_size'
    ],
    'ollama': [
        'total_duration',
        'eval_duration',
        'load_duration'
    ]
}
```

### **Real-Time Monitoring**
- **Health Check Monitoring**: Continuous service availability tracking
- **Performance Metrics**: Real-time TTFT, latency, throughput monitoring
- **Resource Utilization**: GPU, memory, CPU usage tracking
- **Error Rate Monitoring**: Success/failure rate tracking with alerting

---

## 🔮 **Future Architecture Enhancements**

### **Advanced Metrics & Analytics** (Phase 2)
- **Time-series visualizations**: Line charts showing performance trends
- **Distribution analysis**: Histograms and violin plots for statistical insight
- **Enhanced radar charts**: 8-dimensional performance comparison
- **Real-time dashboards**: Live monitoring with auto-refresh

### **Executive Intelligence** (Phase 3)
- **Automated insights engine**: AI-powered analysis and recommendations
- **Business intelligence integration**: Export to Tableau, PowerBI
- **Predictive analytics**: Forecast future performance based on trends
- **ROI calculators**: Cost-benefit analysis tools

### **Enterprise Integration** (Phase 4)
- **Prometheus/Grafana integration**: Standard monitoring stack
- **JIRA integration**: Automated ticket creation for performance issues
- **Slack/Teams notifications**: Real-time alerts to team channels
- **API endpoints**: REST APIs for programmatic access

---

## 🏗️ **Design Principles**

### **FAANG-Level Architecture Guidelines**
1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Injection**: Clean interfaces and testable components
3. **Error Handling**: Comprehensive error classification with user guidance
4. **Observability**: Structured logging, metrics, and tracing
5. **Scalability**: Designed for growth and extension
6. **Maintainability**: Code organization optimized for long-term maintenance

### **Performance & Reliability**
1. **Async-First**: All I/O operations are asynchronous
2. **Circuit Breakers**: Automatic failure detection and recovery
3. **Graceful Degradation**: System continues operation with partial failures
4. **Resource Management**: Proper cleanup and resource lifecycle management
5. **Statistical Rigor**: Scientifically sound performance measurement
6. **Production Ready**: Robust error handling and monitoring

---

**This architecture provides a solid foundation for enterprise-grade AI inference benchmarking while maintaining flexibility for future enhancements and integrations.**
