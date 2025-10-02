# 🚀 Universal LLM Engine Benchmarking Tool

A Python-based benchmarking framework for evaluating the runtime performance of **Ollama**, **vLLM**, and **HuggingFace Text Generation Inference (TGI)**.

## 🏗️ Quick Start

### Prerequisites
- Python 3.11+
- At least one LLM engine running (Ollama, vLLM, or TGI)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd vllm-notebooks

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

## 🎪 Phase 1 Features (In Development)

### Engine Connectivity
- **Ollama**: REST API integration with health checks and model discovery
- **vLLM**: OpenAI-compatible API support
- **TGI**: HuggingFace Inference API integration

### CLI Interface
```bash
# Engine management
llm-benchmark engines list
llm-benchmark engines health --engine ollama
llm-benchmark engines info --engine ollama

# Model discovery
llm-benchmark models list --engine ollama

# Single request testing
llm-benchmark test-request --engine ollama --model llama2 --prompt "Hello"

# Metrics inspection
llm-benchmark metrics show --format json
llm-benchmark metrics export --file metrics.json
```

### Metrics Collection
- Raw engine metrics collection
- Standardized metrics parsing
- JSON export functionality
- Per-request timing and token counting

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

## 🧪 Testing

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

## 📁 Project Structure

```
src/
├── core/           # Core framework components
├── adapters/       # Engine-specific adapters
├── models/         # Data models and schemas
├── config/         # Configuration management
└── cli/            # Command-line interface

configs/
├── engines/        # Engine configuration files
└── scenarios/      # Test scenario definitions

tests/
├── unit/           # Unit tests
└── integration/    # Integration tests
```

## 📝 License

Apache 2.0 License - see LICENSE file for details.

## 👨‍💻 Author

**Gabriel Sampaio** - gab@redhat.com

