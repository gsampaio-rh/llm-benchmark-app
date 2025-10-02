# 🚀 Universal LLM Engine Benchmarking Tool

A Python-based benchmarking framework for evaluating the runtime performance of **Ollama**, **vLLM**, and **HuggingFace Text Generation Inference (TGI)**.

## 🎯 Project Status: Phase 1 - Platform Foundation

**Current Sprint:** Sprint 1 - Foundation & Core Connectivity  
**Phase Goal:** Establish reliable engine connectivity and metrics collection foundation

### ✅ Completed Features
- [x] Project structure and development environment
- [ ] Configuration management system
- [ ] Base adapter framework
- [ ] Ollama engine connection
- [ ] Metrics data models

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

## 🚧 Development Roadmap

### Phase 1: Platform Foundation (Current)
- [x] Project structure and development environment
- [ ] Engine connectivity framework
- [ ] Basic metrics collection
- [ ] CLI interface for engine management

### Phase 2: Multi-Engine Benchmarking
- [ ] Concurrent request handling
- [ ] Workload scenario framework
- [ ] Comparative analysis
- [ ] Advanced metrics aggregation

### Phase 3: Advanced Features
- [ ] Load testing capabilities
- [ ] Streaming vs non-streaming benchmarks
- [ ] Resource utilization monitoring
- [ ] Performance regression detection

## 🤝 Contributing

This project follows agile development practices with 1-week sprints. See `docs/PHASE1_AGILE_PLAN.md` for current sprint details.

### Development Workflow
1. Check current sprint backlog in agile plan
2. Pick up user stories in priority order
3. Follow acceptance criteria and definition of done
4. Submit PR with tests and documentation

### Code Quality Standards
- Type hints required for all functions
- >85% test coverage for new code
- Black formatting and isort import sorting
- Mypy type checking passes
- All tests pass

## 📄 Documentation

- [Product Requirements Document](docs/PRD.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Phase 1 Agile Plan](docs/PHASE1_AGILE_PLAN.md)
- [User Stories](docs/USER_STORIES.md)
- [Metrics Specification](docs/METRICS.md)

## 📝 License

Apache 2.0 License - see LICENSE file for details.

## 👨‍💻 Author

**Gabriel Sampaio** - gab@redhat.com

---

**Status**: 🚧 Active Development - Phase 1 Sprint 1

