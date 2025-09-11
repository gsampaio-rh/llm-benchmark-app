#!/bin/bash

# vLLM vs TGI vs Ollama - Development Environment Setup
# Phase 1.2: Project Structure Setup Complete
# This script sets up the development environment for the benchmarking project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [[ ! -f "requirements.txt" ]] || [[ ! -d "helm" ]]; then
    error "Please run this script from the vllm-notebooks project root directory"
    exit 1
fi

log "Starting development environment setup..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"

if [[ $(echo "$PYTHON_VERSION >= $REQUIRED_VERSION" | bc -l) -eq 1 ]]; then
    success "Python $PYTHON_VERSION detected (>= $REQUIRED_VERSION required)"
else
    error "Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    log "Creating Python virtual environment..."
    python3 -m venv venv
    success "Virtual environment created"
else
    success "Virtual environment already exists"
fi

# Activate virtual environment
log "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
log "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
log "Installing Python dependencies..."
pip install -r requirements.txt

# Install Jupyter kernel
log "Installing Jupyter kernel..."
python -m ipykernel install --user --name=vllm-benchmark --display-name="vLLM Benchmark"

# Install Jupyter extensions
log "Installing Jupyter extensions..."
jupyter contrib nbextension install --user || warning "Jupyter extensions not installed (optional)"
jupyter nbextensions_configurator enable --user || warning "Jupyter configurator not enabled (optional)"

# Verify key packages
log "Verifying key package installations..."
python -c "import pandas; print(f'✅ pandas {pandas.__version__}')"
python -c "import plotly; print(f'✅ plotly {plotly.__version__}')"
python -c "import jupyter; print(f'✅ jupyter installed')"
python -c "import rich; print(f'✅ rich console available')"

# Set up results directory structure
log "Setting up results directory structure..."
mkdir -p results/{raw_logs/{vllm,tgi,ollama},processed_data,visualizations,reports,configurations}
success "Results directory structure created"

# Create configuration files
log "Creating default configuration files..."

cat > results/configurations/default_config.json << EOF
{
  "benchmark_config": {
    "services": ["vllm", "tgi", "ollama"],
    "namespace": "vllm-benchmark",
    "model": "Qwen/Qwen2.5-7B",
    "test_types": ["quick_latency", "standard_load", "stress_test"]
  },
  "load_test_configs": {
    "quick_latency": {
      "concurrent_users": 5,
      "duration_seconds": 30,
      "prompt_type": "quick_response"
    },
    "standard_load": {
      "concurrent_users": 25,
      "duration_seconds": 60,
      "prompt_type": "medium_complexity"
    },
    "stress_test": {
      "concurrent_users": 50,
      "duration_seconds": 120,
      "prompt_type": "mixed"
    }
  },
  "target_metrics": {
    "ttft_target_ms": 100,
    "p95_latency_target_ms": 1000,
    "min_throughput_req_per_sec": 50
  }
}
EOF

success "Default configuration created"

# Create .env file template
log "Creating environment configuration template..."

cat > .env.template << EOF
# vLLM vs TGI vs Ollama Benchmarking Environment Configuration
# Copy this file to .env and customize for your environment

# Kubernetes/OpenShift Configuration
KUBECONFIG=~/.kube/config
NAMESPACE=vllm-benchmark

# Service URLs (will be auto-discovered if empty)
VLLM_URL=
TGI_URL=
OLLAMA_URL=

# HuggingFace Configuration (for gated models)
HF_TOKEN=

# Benchmark Configuration
DEFAULT_MODEL=Qwen/Qwen2.5-7B
RESULTS_RETENTION_DAYS=30

# Development Settings
DEBUG=false
LOG_LEVEL=INFO
EOF

success "Environment template created (.env.template)"

# Display final status
echo ""
echo "========================================"
success "Development environment setup complete!"
echo "========================================"
echo ""
echo "📁 Project Structure:"
echo "   ├── 📓 notebooks/          # Jupyter notebooks"
echo "   ├── 📊 data/               # Test prompts and datasets"
echo "   ├── 📋 docs/               # Documentation (PRD, implementation plan)"
echo "   ├── ⚙️  helm/               # Kubernetes deployment charts"
echo "   ├── 📈 results/            # Benchmark results and analysis"
echo "   ├── 🔧 scripts/            # Automation scripts"
echo "   └── 🐍 venv/               # Python virtual environment"
echo ""
echo "🚀 Next Steps:"
echo "   1. Copy .env.template to .env and configure your environment"
echo "   2. Ensure your OpenShift/Kubernetes cluster is accessible"
echo "   3. Run infrastructure validation: ./scripts/infrastructure-validation.sh"
echo "   4. Deploy services: helm install vllm-test ./helm/vllm -n vllm-benchmark"
echo "   5. Launch Jupyter: jupyter lab notebooks/low_latency_chat.ipynb"
echo ""
echo "📖 Documentation:"
echo "   • Project overview: README.md"
echo "   • Requirements: docs/PRD.md"
echo "   • Implementation plan: docs/IMPLEMENTATION-PLAN.md"
echo ""
success "Ready to proceed with Phase 2: Core Implementation!"
