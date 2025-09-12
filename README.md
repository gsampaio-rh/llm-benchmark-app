# 🚀 vLLM vs TGI vs Ollama Benchmarking Suite

[![OpenShift](https://img.shields.io/badge/Platform-OpenShift-red)](https://www.redhat.com/en/technologies/cloud-computing/openshift)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.19+-blue)](https://kubernetes.io/)
[![Python](https://img.shields.io/badge/Python-3.9+-green)](https://python.org/)
[![CLI](https://img.shields.io/badge/Interface-CLI-yellow)](https://click.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

**Enterprise-grade CLI benchmarking suite** that provides comprehensive performance analysis for AI inference engines in low-latency chat applications.

> **🆕 Phase 1.2 Refactoring Complete!** The CLI has been streamlined from 15 commands to 9 focused commands, with the main script reduced from 940 lines to 86 lines. All functionality preserved in a modular, maintainable architecture.

## 🎯 **What This Tool Does**

Compares **vLLM**, **TGI** (Text Generation Inference), and **Ollama** across critical performance metrics:

- ⚡ **Time To First Token (TTFT)** - Sub-100ms target for responsive UX
- 📊 **Load Performance** - Concurrent user handling and throughput
- 🎯 **Statistical Analysis** - P50/P95/P99 percentiles with winner determination
- 📈 **Interactive Visualizations** - Professional charts and executive reports
- 📁 **Organized Results** - Clean test_id_datetime structure for easy management

---

## 🚀 **Quick Start**

### **1. Install & Setup**

```bash
# Clone repository
git clone https://github.com/your-org/vllm-notebooks.git
cd vllm-notebooks

# Install dependencies
pip install -r requirements.txt

# Initialize configuration
python vllm_benchmark.py init
```

### **2. Deploy Services** (using Helm charts)

```bash
# Create namespace
kubectl create namespace vllm-benchmark

# Deploy inference engines
helm install vllm-dev ./helm/vllm --namespace vllm-benchmark
helm install tgi-test ./helm/tgi --namespace vllm-benchmark
helm install ollama-test ./helm/ollama --namespace vllm-benchmark

# Verify deployment
kubectl get pods -n vllm-benchmark
```

### **3. Run Benchmarks**

```bash
# Quick 5-minute test
python vllm_benchmark.py benchmark --quick

# Standard comprehensive test (30 minutes)
python vllm_benchmark.py benchmark

# Custom configuration
python vllm_benchmark.py benchmark --config config/stress-test.yaml --users 50
```

### **4. View Results**

```bash
# List organized test runs
python vllm_benchmark.py results

# View specific test details
ls results/test_quicklatency_20250911_105623/
```

### **5. 🎭 Interactive Demonstrations** (UNIFIED!)

```bash
# Interactive mode selector
python vllm_benchmark.py demo

# Live performance race with real-time comparison
python vllm_benchmark.py demo --mode race --prompt "Explain AI" --runs 3

# Multi-turn conversation showing context retention
python vllm_benchmark.py demo --mode conversation --scenario 1

# Try-it-yourself interactive mode
python vllm_benchmark.py demo --mode interactive

# Technical payload inspection
python vllm_benchmark.py inspect --scenario 1
```

---

## 🎛️ **Command Reference**

### **Core Commands**
```bash
# Benchmarking
python vllm_benchmark.py benchmark [--quick|--config PATH|--users N]

# Interactive Demos
python vllm_benchmark.py demo [--mode race|conversation|interactive]

# Service Management
python vllm_benchmark.py discover [--namespace NAME]
python vllm_benchmark.py test [--prompt TEXT]

# Results & Visualization
python vllm_benchmark.py results [--test-id ID]
python vllm_benchmark.py visualize RESULTS_FILE [--output-dir DIR]

# Configuration
python vllm_benchmark.py config [CONFIG_FILE]
python vllm_benchmark.py init

# Technical Inspection
python vllm_benchmark.py inspect [--scenario N|--prompt TEXT]
```

### **Demo Modes**
- **`race`** - Live three-way performance race with real-time comparison
- **`conversation`** - Multi-turn conversation showing context retention (5 scenarios)
- **`interactive`** - Try-it-yourself mode where you control the prompts

---

## 📊 **Performance Metrics**

### **Primary Targets**
| Metric | Target | Description |
|--------|--------|-------------|
| **TTFT** | < 100ms | Time To First Token |
| **P95 Latency** | < 1 second | 95th percentile end-to-end latency |
| **Throughput** | 50+ concurrent users | Sustained user load |
| **Success Rate** | > 95% | Request success percentage |

### **Key Features**
- **Sub-millisecond TTFT measurement** via streaming token capture
- **Statistical analysis** with P50/P95/P99 percentiles and confidence intervals
- **Winner determination algorithms** with multi-dimensional scoring
- **Service personalities** in demos (Professional, Technical, Friendly)
- **Real-time visualizations** with business impact analysis

---

## 🛠️ **Requirements**

- **Python 3.9+** with asyncio support
- **Kubernetes/OpenShift** cluster with GPU nodes (recommended)
- **Helm 3.2+** for service deployment
- **Persistent Storage** (ReadWriteOnce, 50Gi+ per service)

### **Key Dependencies**
```bash
pip install -r requirements.txt
# Key packages: click, rich, plotly, httpx, pyyaml, kubernetes
```

---

## 📈 **Roadmap**

### **Completed ✅**
- **Phase 1.2**: Streamlined CLI architecture (940 → 86 lines)
- **Modular command structure** with focused handlers
- **Unified demo command** consolidating race/conversation/interactive modes
- CLI-based architecture with organized results
- Interactive visualization and reporting
- Production-ready configuration system
- Comprehensive service discovery
- Executive and technical analysis

### **In Development 🚧**
- **Advanced Metrics** - Service-specific metrics collection
- Token-level performance analysis
- Request lifecycle visualization
- Enhanced bottleneck identification

### **Future Enhancements 📋**
- Real-time monitoring dashboard
- Integration with Prometheus/Grafana
- Container-based deployment
- Multi-cluster benchmarking

---

## 🎯 **Use Cases**

### **For ML Engineers**
- **Performance Optimization** - Identify bottlenecks and configuration improvements
- **A/B Testing** - Compare different model configurations and deployment strategies
- **Capacity Planning** - Understand throughput limits and scaling requirements

### **For Product Teams**
- **User Experience Analysis** - Measure impact of latency on user satisfaction
- **Service Selection** - Data-driven decisions for inference engine adoption
- **Performance Monitoring** - Track regression and improvements over time

### **For DevOps/SRE**
- **Infrastructure Validation** - Verify deployment performance and reliability
- **Resource Planning** - Optimize GPU, memory, and compute allocation
- **SLA Monitoring** - Ensure performance targets are consistently met

### **For Leadership**
- **Executive Dashboards** - High-level performance insights and trends
- **ROI Analysis** - Quantify infrastructure investments and optimizations
- **Competitive Analysis** - Benchmark against industry standards

---

## 🤝 **Contributing**

We welcome contributions! Please see our [Architecture Guide](ARCHITECTURE.md) for development guidelines.

### **Development Setup**
```bash
git clone https://github.com/your-org/vllm-notebooks.git
cd vllm-notebooks
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **Running Tests**
```bash
# Validate Helm charts
helm lint ./helm/vllm ./helm/tgi ./helm/ollama

# Test CLI commands
python vllm_benchmark.py --help
python vllm_benchmark.py config config/default.yaml
```

---

## 🚨 **Troubleshooting**

### **No Services Found**
```bash
# Check deployment status
kubectl get pods -n vllm-benchmark
kubectl get svc -n vllm-benchmark

# Use manual URLs if auto-discovery fails
python vllm_benchmark.py benchmark --config config/manual-urls.yaml
```

### **Memory/GPU Issues**
```bash
# Check resource usage
kubectl top pods -n vllm-benchmark
kubectl describe pod <pod-name> -n vllm-benchmark

# Adjust resource limits in Helm values
helm upgrade vllm-dev ./helm/vllm --set resources.limits.memory="32Gi"
```

### **Debug Commands**
```bash
# Verbose logging and service health check
python vllm_benchmark.py discover --namespace vllm-benchmark
python vllm_benchmark.py test --prompt "test" --namespace vllm-benchmark

# Configuration validation
python vllm_benchmark.py config config/default.yaml
```

---

## 📄 **Documentation**

- **[Architecture Guide](ARCHITECTURE.md)** - Detailed system design and component overview
- **[Implementation Plan](docs/IMPLEMENTATION-PLAN.md)** - Development roadmap and progress tracking
- **[Refactoring Plan](REFACTOR-PLAN-1.2.md)** - Phase 1.2 modular architecture transformation

---

## 📄 **License**

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙋 **Support**

- **Issues**: [GitHub Issues](https://github.com/your-org/vllm-notebooks/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/vllm-notebooks/discussions)

---

**Built with ❤️ by the AI Platform Team for enterprise AI inference benchmarking**

*Delivering data-driven insights for optimal AI infrastructure decisions*