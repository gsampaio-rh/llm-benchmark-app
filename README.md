# 🚀 vLLM vs TGI vs Ollama Benchmarking Suite

[![OpenShift](https://img.shields.io/badge/Platform-OpenShift-red)](https://www.redhat.com/en/technologies/cloud-computing/openshift)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.19+-blue)](https://kubernetes.io/)
[![Python](https://img.shields.io/badge/Python-3.9+-green)](https://python.org/)
[![CLI](https://img.shields.io/badge/Interface-CLI-yellow)](https://click.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

**Enterprise-grade CLI benchmarking suite** that provides comprehensive performance analysis for AI inference engines in low-latency chat applications.

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

### **5. 🎭 Interactive Conversation Demos** (NEW!)

```bash
# Live conversation theater with real-time streaming
python vllm_benchmark.py demo --scenario 1 --live

# Multi-turn conversation showing context retention
python vllm_benchmark.py conversation --scenario 2

# Technical payload inspection
python vllm_benchmark.py inspect --scenario 3

# Show all available scenarios
python vllm_benchmark.py demo
```

---

## 🏗️ **Architecture**

### **CLI-First Design**
Modern command-line interface built with Python Click and Rich for beautiful console output.

### **Organized Results Structure**
```
results/
└── test_quicklatency_20250911_105623/    # test_id_datetime format
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

### **Service Discovery**
Smart multi-layer discovery: OpenShift routes → Kubernetes ingress → NodePort → manual URLs

---

## 🎭 **Human-Centered Conversation Visualization**

Transform abstract API calls into compelling human stories with **real conversations**:

### **Live Conversation Theater** 
- **Real-time streaming**: Watch tokens generate character-by-character
- **Service personalities**: vLLM (Professional 🔵), TGI (Technical 🟢), Ollama (Friendly 🟠)  
- **Performance racing**: See which service responds fastest
- **Token economics**: Cost analysis and efficiency scoring

### **Realistic Scenarios**
| Scenario | Description | User Persona |
|----------|-------------|--------------|
| **Customer Support** | Kubernetes troubleshooting | DevOps Engineer |
| **Code Review** | Python function optimization | Software Developer |
| **Creative Writing** | AI story generation | Content Creator |
| **Technical Docs** | Microservices explanation | Technical Writer |
| **Business Intelligence** | Cloud provider selection | Product Manager |

### **Multi-Turn Context Analysis**
- **4-turn conversations** showing context retention
- **Memory depth scoring** (how many turns each service remembers)
- **Follow-up quality analysis** (how well services build on previous responses)
- **Context retention grades** (A through B+ scoring system)

### **Technical Deep-Dive**
- **Side-by-side API payloads** with JSON syntax highlighting
- **Request/response inspection** for all three services
- **Streaming visualization** showing server-sent events
- **Token-level analysis** with timestamps and efficiency metrics

---

## 🎛️ **Complete Command Reference**

### **Core Benchmarking**
```bash
# Run benchmarks with organized output
python vllm_benchmark.py benchmark [OPTIONS]
  --quick                    # 5-minute quick test
  --config PATH              # Custom configuration file
  --users N                  # Override concurrent users
  --duration N               # Override test duration (seconds)
  --ttft-only               # Run only TTFT tests
  --namespace NAME          # Kubernetes namespace
  --dry-run                 # Validate configuration only
```

### **Results Management**
```bash
# View organized test runs
python vllm_benchmark.py results

# Clean up old tests (keep 10 recent)
python vllm_benchmark.py cleanup --keep 10

# Regenerate charts/reports for existing test
python vllm_benchmark.py reprocess test_id [--charts-only|--reports-only]

# Generate charts from legacy results
python vllm_benchmark.py visualize results_file.json --output-dir charts/
```

### **🎭 Conversation Visualization** (NEW!)
```bash
# Interactive conversation theater with live streaming
python vllm_benchmark.py demo --scenario 1 --live

# Multi-turn conversation with context analysis
python vllm_benchmark.py conversation --scenario 2

# Technical payload inspection and API comparison
python vllm_benchmark.py inspect --scenario 3

# Show all available conversation scenarios
python vllm_benchmark.py demo

# Custom services and prompts
python vllm_benchmark.py demo --scenario code_review --services vllm,tgi --prompt 1
```

### **Service Management**
```bash
# Discover and health check services
python vllm_benchmark.py discover --namespace vllm-benchmark

# Quick test all services
python vllm_benchmark.py test --prompt "Hello AI!" --namespace vllm-benchmark

# View/validate configuration
python vllm_benchmark.py config [CONFIG_FILE]
```

### **Setup & Maintenance**
```bash
# Initialize configuration files
python vllm_benchmark.py init

# Migrate legacy unorganized results
python vllm_benchmark.py migrate
```

---

## ⚙️ **Configuration**

### **Preset Configurations**
- **`config/default.yaml`** - Standard benchmarking (30 min)
- **`config/quick-test.yaml`** - Quick demo (5 min)
- **`config/stress-test.yaml`** - Production validation (60+ min)

### **Example Configuration**
```yaml
benchmark:
  name: "Production Readiness Test"
  model: "Qwen/Qwen2.5-7B"

services:
  namespace: "vllm-benchmark"
  manual_urls:  # Optional override
    vllm: "https://vllm-route.apps.cluster.com"
    tgi: "https://tgi-route.apps.cluster.com" 
    ollama: "https://ollama-route.apps.cluster.com"

test_scenarios:
  ttft:
    enabled: true
    iterations: 5
    target_ms: 100
    
  load_tests:
    - name: "quick_latency"
      concurrent_users: 10
      duration_seconds: 60
      target_p95_ms: 500

output:
  directory: "results"
  save_raw_data: true
  generate_charts: true
  generate_report: true
```

---

## 📊 **Performance Metrics**

### **Primary Metrics**
| Metric | Target | Description |
|--------|--------|-------------|
| **TTFT** | < 100ms | Time To First Token |
| **P95 Latency** | < 1 second | 95th percentile end-to-end latency |
| **Throughput** | 50+ concurrent users | Sustained user load |
| **Success Rate** | > 95% | Request success percentage |

### **Advanced Metrics** (Day 8+)
| Service | Native Metrics | Capabilities |
|---------|---------------|--------------|
| **vLLM** | `vllm:e2e_request_latency_seconds`, `vllm:time_to_first_token_seconds` | Queue time, token generation rate |
| **TGI** | `tgi_request_duration`, `tgi_request_inference_duration` | Request lifecycle, token counts |
| **Ollama** | `total_duration`, `eval_duration`, `load_duration` | Model load time, evaluation metrics |

---

## 🎨 **Visualization & Reporting**

### **Interactive Charts**
- **TTFT Analysis** - Box plots, bar charts, statistical summaries
- **Load Test Dashboard** - 4-panel comprehensive view (latency, throughput, reliability, scores)
- **Performance Radar** - Multi-dimensional comparison across all metrics

### **Executive Reports**
- **Automated Insights** - Winner identification and performance analysis
- **Technical Recommendations** - Configuration optimization suggestions
- **Business Impact** - User experience and ROI analysis

### **Export Formats**
- **HTML** - Interactive reports with embedded charts
- **CSV** - Spreadsheet-compatible metrics
- **JSON** - Programmatic analysis and API integration
- **PNG** - Static charts for presentations

---

## 🛠️ **Development & Deployment**

### **Project Structure**
```
vllm-notebooks/
├── vllm_benchmark.py          # 🎯 Main CLI script
├── src/                       # 📦 Core modules
│   ├── service_discovery.py   # Service discovery & health checks
│   ├── api_clients.py         # Unified API clients
│   ├── benchmarking.py        # TTFT and load testing
│   ├── metrics.py             # Statistical analysis
│   ├── visualization.py       # Interactive charts
│   ├── reporting.py           # HTML/PDF reports
│   ├── results_organizer.py   # Test run management
│   └── config.py              # YAML configuration
├── config/                    # 📝 Configuration presets
├── helm/                      # ⚙️ Kubernetes deployment
│   ├── vllm/, tgi/, ollama/   # Service Helm charts
├── results/                   # 📊 Organized test outputs
└── docs/                      # 📚 Documentation
```

### **Requirements**
- **Python 3.9+** with asyncio support
- **Kubernetes/OpenShift** cluster with GPU nodes (recommended)
- **Helm 3.2+** for service deployment
- **Persistent Storage** (ReadWriteOnce, 50Gi+ per service)

### **Dependencies**
```bash
pip install -r requirements.txt
# Key packages: click, rich, plotly, httpx, pyyaml, kubernetes
```

---

## 🔧 **Advanced Usage**

### **Custom Test Scenarios**
```bash
# High-load stress test
python vllm_benchmark.py benchmark \
  --config config/stress-test.yaml \
  --users 100 \
  --duration 300

# TTFT-focused analysis
python vllm_benchmark.py benchmark \
  --ttft-only \
  --config config/quick-test.yaml

# Service-specific testing
python vllm_benchmark.py benchmark \
  --services vllm,tgi \
  --namespace production
```

### **Results Post-Processing**
```bash
# Regenerate all charts and reports
python vllm_benchmark.py reprocess test_quicklatency_20250911_105623

# Charts only for presentation
python vllm_benchmark.py reprocess test_quicklatency_20250911_105623 --charts-only

# Legacy results conversion
python vllm_benchmark.py visualize old_results.json --output-dir modern_charts/
```

### **Automated Workflows**
```bash
# CI/CD integration
python vllm_benchmark.py benchmark --config ci-validation.yaml --output-dir ci-results/

# Scheduled monitoring
python vllm_benchmark.py benchmark --quick --namespace monitoring
python vllm_benchmark.py cleanup --keep 5  # Maintain recent results only
```

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

## 🚨 **Troubleshooting**

### **Common Issues**

#### **No Services Found**
```bash
# Check deployment status
kubectl get pods -n vllm-benchmark
kubectl get svc -n vllm-benchmark

# Use manual URLs if auto-discovery fails
python vllm_benchmark.py benchmark --config config/manual-urls.yaml
```

#### **Memory/GPU Issues**
```bash
# Check resource usage
kubectl top pods -n vllm-benchmark
kubectl describe pod <pod-name> -n vllm-benchmark

# Adjust resource limits in Helm values
helm upgrade vllm-dev ./helm/vllm --set resources.limits.memory="32Gi"
```

#### **Permission/Access Issues**
```bash
# Verify cluster access
kubectl auth can-i create pods --namespace vllm-benchmark

# Check service connectivity
python vllm_benchmark.py discover --namespace vllm-benchmark
```

### **Debug Commands**
```bash
# Verbose logging
python vllm_benchmark.py benchmark --verbose

# Configuration validation
python vllm_benchmark.py config config/default.yaml

# Service health check
python vllm_benchmark.py test --prompt "test" --namespace vllm-benchmark
```

---

## 📈 **Roadmap**

### **Completed ✅**
- CLI-based architecture with organized results
- Interactive visualization and reporting
- Production-ready configuration system
- Comprehensive service discovery
- Executive and technical analysis

### **In Development 🚧**
- **Day 8: Advanced Metrics** - Service-specific metrics collection
- Token-level performance analysis
- Request lifecycle visualization
- Enhanced bottleneck identification

### **Future Enhancements 📋**
- Real-time monitoring dashboard
- Integration with Prometheus/Grafana
- Container-based deployment
- Multi-cluster benchmarking

---

## 🤝 **Contributing**

We welcome contributions! Please see our [Implementation Plan](docs/IMPLEMENTATION-PLAN.md) for development guidelines.

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

## 📄 **License**

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙋 **Support**

- **Documentation**: [Implementation Plan](docs/IMPLEMENTATION-PLAN.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/vllm-notebooks/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/vllm-notebooks/discussions)

---

**Built with ❤️ by the AI Platform Team for enterprise AI inference benchmarking**

*Delivering data-driven insights for optimal AI infrastructure decisions*