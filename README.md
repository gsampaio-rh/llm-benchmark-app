# 🚀 Universal LLM Engine Benchmarking Tool

A Python-based benchmarking framework for evaluating the runtime performance of **Ollama**, **vLLM**, and **HuggingFace Text Generation Inference (TGI)**.

**✨ Features beautiful, guided Python scripts with step-by-step instructions and rich visual feedback.**

---

**📊 Current Status:** Phase 1 Complete + Phase 2 In Progress (52.4% metrics coverage)  
**🎉 Latest:** Parallel execution mode, Kubernetes/OpenShift integration, enhanced 8-column metrics dashboard  
**🚀 New:** Real token-by-token streaming from all engines, scenario-based benchmarking

## 🏗️ Quick Start

### Prerequisites
- Python 3.11+
- At least one LLM engine running (Ollama, vLLM, or TGI)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd llm-benchmark-app

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## 🎯 How to Use

This tool provides **interactive Python scripts** instead of CLI commands. Each script guides you through the process with beautiful visualizations.

### 1️⃣ Check Engine Health
Verify that your LLM engines are running and accessible:
```bash
python scripts/check_engines.py
```
**What it does:** Tests connectivity, measures response times, lists available models

### 2️⃣ Test a Single Request
Send a test prompt to any engine and model:
```bash
python scripts/test_request.py
```
**What it does:** Interactive model selection, sends request, shows detailed metrics, auto-exports to JSON

### 3️⃣ Run Full Benchmark
Execute comprehensive benchmarks across engines:
```bash
python scripts/run_benchmark.py
```
**What it does:** Configure test parameters, run multiple requests, display results, auto-export to JSON

### 4️⃣ Creative Writing Benchmark
Run scenario-based benchmark for story generation and creative writing:
```bash
python scripts/benchmark_creative_writing.py
```
**What it does:** 
- Tests short prompt → long completion scenarios
- **Parallel execution** - test all engines simultaneously (3x faster!)
- Real-time token streaming with multi-column view
- Enhanced metrics dashboard with p95/p99 percentiles
- Auto-exports comprehensive results (JSON/CSV/Markdown)

### 5️⃣ Discover Models
Explore available models across all engines:
```bash
python scripts/discover_models.py
```
**What it does:** Scan engines, list models by family, show availability

## 📚 Complete Documentation

See **[scripts/README.md](scripts/README.md)** for detailed documentation on each script.

## 🌟 Key Features & Highlights

### ⚡ Parallel Execution Mode
Test all engines **simultaneously** instead of sequentially:
- **3x faster** benchmark completion
- Multi-column real-time view showing all engines side-by-side
- Live token streaming from all engines at once
- Immediate visual performance comparison

### 🎬 Real Token-by-Token Streaming
- **True streaming** from all engines (Ollama, vLLM, TGI) - not simulated!
- Real-time dashboard updates as tokens arrive
- Accurate TTFT (Time to First Token) measurement
- Streaming smoothness tracking (inter-token latency)

### 🐳 Kubernetes/OpenShift Integration
- Auto-discovers pod metadata from OpenShift routes
- Displays CPU/Memory/GPU resource allocation
- Helm chart-based pod identification
- Shows which backend instance you're testing
- Zero-configuration setup

### 📊 Enhanced Metrics Dashboard
**8-column comprehensive view:**
- Throughput (avg ± σ) - with variance tracking
- TTFT (avg · p95) - Time to First Token with percentiles
- Duration (avg · p95) - Total response time
- Inter-token latency - streaming smoothness
- Tokens/Response - consistency metric
- Token/Word ratio - tokenizer efficiency (color-coded)
- Total tokens generated
- Live percentile calculations (p50, p95, p99)

### 🎯 Scenario-Based Benchmarking
- YAML-driven test configurations
- Pre-built scenarios for common use cases:
  - Short prompt → Long completion (creative writing)
  - Long prompt → Short completion (RAG/Q&A)
  - Long prompt → Long completion (document analysis)
  - Short prompt → Short completion (chat/interactive)
- Parameterized prompt templates
- Reproducible, version-controlled benchmarks

## ✨ What's Implemented

### Engine Connectivity ✅
- **Ollama**: REST API integration with health checks and model discovery
- **vLLM**: OpenAI-compatible API support with streaming
- **TGI**: HuggingFace Inference API integration
- **Kubernetes/OpenShift Integration**: Auto-discovers pod metadata, CPU/Memory/GPU resources

### Interactive Scripts ✅
- **check_engines.py** - Engine health and connectivity checker
- **discover_models.py** - Model discovery and exploration
- **test_request.py** - Single request tester with automatic metrics export
- **run_benchmark.py** - Comprehensive benchmark runner with real-time results
- **benchmark_creative_writing.py** - Scenario-based benchmark with parallel execution

### Real-Time Streaming ✅
- **True token-by-token streaming** from all engines (not simulated!)
- Real-time dashboard updates as tokens arrive
- **Parallel execution mode** - test all engines simultaneously (3x faster)
- Multi-column view with side-by-side streaming
- Live metrics updates (10 Hz refresh rate)

### Scenario-Based Benchmarking ✅
- **YAML-based scenario configurations**
- Pre-built scenarios (short→long, long→short, long→long, short→short)
- Parameterized prompt templates
- Parallel or sequential execution modes
- Comprehensive test case expansion

### Metrics Collection ✅
- Raw engine metrics collection (100%)
- Standardized metrics parsing (52.4% coverage)
- Per-request runtime metrics (100% for Ollama & vLLM)
- **Enhanced 8-column metrics dashboard**:
  - Throughput (avg ± σ) with variance tracking
  - TTFT (avg · p95) - Time to First Token
  - Duration (avg · p95) - Total response time
  - Inter-token latency (streaming smoothness)
  - Tokens/Response (consistency metric)
  - Token/Word ratio (tokenizer efficiency)
- JSON/CSV/Markdown export functionality
- Aggregate statistics (p50, p95, p99, mean, std dev)

### Infrastructure Monitoring ✅
- **Pod metadata extraction** from OpenShift/Kubernetes
- CPU/Memory/GPU resource allocation display
- Helm chart-based pod discovery
- OpenShift route parsing
- Graceful degradation for local development

## 📊 Supported Metrics

### Per-Request Runtime Metrics (100% for Ollama & vLLM)
| Metric | Description | Engines |
|--------|-------------|---------|
| **Load Duration** | Setup time before prompt evaluation | Ollama, vLLM |
| **Prompt Eval Count** | Number of input tokens processed | All |
| **Prompt Eval Duration** | Time spent processing input tokens | Ollama, vLLM |
| **Prompt Token Rate** | Input tokens per second | Ollama, vLLM |
| **Response Token Count** | Number of output tokens generated | All |
| **Response Generation Time** | Time spent generating output | Ollama, vLLM |
| **Response Token Rate** | Output tokens per second | All |
| **Total Duration** | End-to-end request runtime | All |

### Latency Metrics (67% coverage)
| Metric | Description | Engines |
|--------|-------------|---------|
| **Time to First Token (TTFT)** | Latency before first token | Ollama, vLLM, TGI |
| **Inter-Token Latency** | Average time between tokens | Ollama, vLLM, TGI |
| **End-to-End Latency** | Total request duration | All |

### Aggregate Statistics
- **Percentiles**: p50, p95, p99 for all latency metrics
- **Variance**: Standard deviation (σ) for throughput consistency
- **Efficiency Metrics**: Token/word ratio, tokens per response
- **Reliability**: Success rate, error rate, timeout count

## 🔧 Configuration

### Engine Configuration
Engine configurations are stored in `configs/engines/`:

```yaml
# configs/engines/ollama.yaml
name: "ollama"
engine_type: "ollama"
base_url: "http://localhost:11434"
timeout: 300
health_endpoint: "/api/tags"
```

### Scenario Configuration
Scenario configurations are stored in `configs/scenarios/`:

```yaml
# configs/scenarios/short_prompt_long_completion.yaml
scenario:
  name: "short_prompt_long_completion"
  description: "Creative writing expansion"
  use_case: "creative_writing"
  parallel_execution: true  # Run engines simultaneously (3x faster!)
  
  prompt:
    template: "Write a detailed story about {topic}"
    min_tokens: 5
    max_tokens: 20
    length_category: "short"
  
  completion:
    max_tokens: 500
    temperature: 0.7
    length_category: "long"
  
  test_cases:
    - topic: "a robot learning to paint"
    - topic: "time travel paradox"
    - topic: "life on Mars colony"
```

## 🧪 Testing & Development

### Run Tests
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests (requires running engines)
pytest tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html
```

### Development Tools
```bash
# Format code
black src/ tests/ scripts/
isort src/ tests/ scripts/

# Type checking
mypy src/

# Linting
flake8 src/ tests/ scripts/
```

## 📁 Project Structure

```
src/
├── adapters/          # Engine-specific adapters (Ollama, vLLM, TGI)
├── benchmarking/      # Benchmark execution & orchestration
│   ├── benchmark_runner.py    # Core runner with parallel execution
│   ├── live_dashboard.py      # Real-time metrics dashboard
│   └── target_selector.py     # Interactive target selection
├── config/            # Configuration management
│   ├── config_manager.py      # Engine config loader
│   ├── scenario_loader.py     # YAML scenario loader
│   └── scenario_models.py     # Scenario data models
├── core/              # Core framework components
│   ├── connection_manager.py  # Engine connection pooling
│   └── metrics_collector.py   # Metrics collection
├── models/            # Pydantic data models
│   ├── engine_config.py       # Engine configuration models
│   └── metrics.py             # Metrics data models
├── reporting/         # Export & reporting
│   └── export_manager.py      # JSON/CSV/Markdown export
├── utils/             # Utility modules
│   └── k8s_metadata.py        # Kubernetes/OpenShift integration
└── visualization/     # Terminal UI components
    └── live_display.py        # Streaming visualization

scripts/               # 🌟 Interactive guided scripts
├── check_engines.py           # Engine health checker
├── discover_models.py         # Model discovery
├── test_request.py            # Single request tester
├── run_benchmark.py           # Basic benchmark runner
├── benchmark_creative_writing.py  # Scenario benchmark with parallel execution
├── demo_parallel_race.py      # Parallel streaming demo
└── README.md                  # Scripts documentation

configs/
├── engines/           # Engine configuration files
│   ├── ollama.yaml
│   ├── vllm.yaml
│   └── tgi.yaml
└── scenarios/         # YAML scenario definitions
    ├── short_prompt_long_completion.yaml
    ├── long_prompt_short_completion.yaml
    ├── long_prompt_long_completion.yaml
    └── short_prompt_short_completion.yaml

benchmark_results/     # Exported metrics and results
└── run_YYYYMMDD_HHMMSS/
    ├── summary.json           # Cross-engine comparison
    ├── summary.csv            # Spreadsheet-ready
    ├── {engine}_results.json  # Per-engine complete data
    ├── {engine}_results.csv   # Per-engine tabular
    └── report.md              # Human-readable summary

tests/
├── unit/              # Unit tests (75+ tests, 100% passing)
└── integration/       # Integration tests

helm/                  # Kubernetes/OpenShift Helm charts
├── ollama/            # Ollama deployment
├── vllm/              # vLLM deployment
└── tgi/               # TGI deployment
```

## 📝 License

Apache 2.0 License - see LICENSE file for details.

## 👨‍💻 Author

**Gabriel Sampaio** - gab@redhat.com

