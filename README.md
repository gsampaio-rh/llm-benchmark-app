# 🚀 Universal LLM Engine Benchmarking Tool

A Python-based benchmarking framework for evaluating the runtime performance of **Ollama**, **vLLM**, and **HuggingFace Text Generation Inference (TGI)**.

**✨ Features beautiful, guided Python scripts with step-by-step instructions and rich visual feedback.**

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

### 4️⃣ Discover Models
Explore available models across all engines:
```bash
python scripts/discover_models.py
```
**What it does:** Scan engines, list models by family, show availability

## 📚 Complete Documentation

See **[scripts/README.md](scripts/README.md)** for detailed documentation on each script.

## ✨ What's Implemented

### Engine Connectivity ✅
- **Ollama**: REST API integration with health checks and model discovery
- **vLLM**: OpenAI-compatible API support with streaming
- **TGI**: HuggingFace Inference API integration

### Interactive Scripts ✅
- **check_engines.py** - Engine health and connectivity checker
- **discover_models.py** - Model discovery and exploration
- **test_request.py** - Single request tester with automatic metrics export
- **run_benchmark.py** - Comprehensive benchmark runner with real-time results

### Metrics Collection ✅
- Raw engine metrics collection
- Standardized metrics parsing (52.4% coverage)
- Per-request runtime metrics (100% for Ollama & vLLM)
- JSON/CSV export functionality
- Aggregate statistics (p50, p95, p99)

## 📊 Supported Metrics

| Category | Metric | Description |
|----------|--------|-------------|
| **Runtime** | Load Duration | Setup time before prompt evaluation |
| **Tokens** | Prompt Eval Count | Number of input tokens processed |
| **Timing** | Prompt Eval Duration | Time spent processing input tokens |
| **Throughput** | Response Token Rate | Output tokens per second |
| **Latency** | Total Duration | End-to-end request runtime |

## 🔧 Configuration

Engine configurations are stored in `configs/engines/`:

```yaml
# configs/engines/ollama.yaml
name: "ollama"
engine_type: "ollama"
base_url: "http://localhost:11434"
timeout: 300
health_endpoint: "/api/tags"
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
├── core/           # Core framework components
├── adapters/       # Engine-specific adapters
├── models/         # Data models and schemas
└── config/         # Configuration management

scripts/            # 🌟 Interactive guided scripts
├── check_engines.py       # Engine health checker
├── discover_models.py     # Model discovery
├── test_request.py        # Single request tester
├── run_benchmark.py       # Benchmark runner
└── README.md             # Scripts documentation

configs/
├── engines/        # Engine configuration files
│   ├── ollama.yaml
│   ├── vllm.yaml
│   └── tgi.yaml
└── scenarios/      # Test scenario definitions

benchmark_results/  # Exported metrics and results

tests/
├── unit/           # Unit tests (75 tests, 100% passing)
└── integration/    # Integration tests

helm/               # Kubernetes/OpenShift deployment charts
├── ollama/
├── vllm/
└── tgi/
```

## 📝 License

Apache 2.0 License - see LICENSE file for details.

## 👨‍💻 Author

**Gabriel Sampaio** - gab@redhat.com

