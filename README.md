# vLLM vs TGI Low-Latency Chat Benchmarking

[![OpenShift](https://img.shields.io/badge/Platform-OpenShift-red)](https://www.redhat.com/en/technologies/cloud-computing/openshift)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.19+-blue)](https://kubernetes.io/)
[![Helm](https://img.shields.io/badge/Helm-v3.2+-blue)](https://helm.sh/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

An interactive benchmarking suite that demonstrates vLLM's superior performance for low-latency chat applications compared to Text Generation Inference (TGI), with plans to include Ollama for comprehensive comparison.

## 🎯 Project Overview

This project provides a complete benchmarking environment to compare inference engines for low-latency chat applications. It includes:

- **Interactive Jupyter Notebook** with step-by-step benchmarking workflow
- **Production-ready Helm Charts** for vLLM, TGI, and Ollama deployment
- **Automated Performance Testing** with real-world metrics
- **Visual Analytics** comparing TTFT, ITL, and E2E latency
- **OpenShift/Kubernetes Native** deployment and scaling

### Key Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **TTFT** | < 100ms | Time To First Token |
| **P95 Latency** | < 1 second | 95th percentile end-to-end latency |
| **Throughput** | 50+ concurrent users | Sustained user load |
| **Demo Time** | < 20 minutes | Complete benchmark execution |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenShift Cluster                       │
├──────────────────────┬──────────────────────┬───────────────┤
│     vLLM Service     │     TGI Service      │ Ollama Service│
│   (Port 8000)       │    (Port 8080)       │  (Port 11434) │
│                      │                      │               │
│ • Qwen/Qwen2.5-7B    │ • Qwen/Qwen2.5-7B    │ • qwen2.5:7b  │
│ • Low-latency config │ • Baseline config    │ • CPU/GPU     │
│ • GPU acceleration   │ • Standard batching  │ • Local model │
│ • Anti-affinity      │ • Anti-affinity      │ • Anti-affinity│
└──────────────────────┴──────────────────────┴───────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│              Jupyter Notebook Benchmarking Suite           │
├─────────────────────────────────────────────────────────────┤
│ 1. Introduction & Architecture                              │
│ 2. Environment Check & Service Discovery                    │
│ 3. Configuration & Optimization                             │
│ 4. Load Generation & Traffic Simulation                     │
│ 5. Metrics Collection & Processing                          │
│ 6. Visualization & Analysis                                 │
│ 7. Summary & Recommendations                                │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **OpenShift 4.6+** or **Kubernetes 1.19+**
- **Helm 3.2+**
- **GPU Nodes** (recommended for production workloads)
- **Persistent Storage** (ReadWriteOnce, 50Gi+ per service)
- **Network Access** for model downloads

### 1. Clone Repository

```bash
git clone https://github.com/your-org/vllm-notebooks.git
cd vllm-notebooks
```

### 2. Infrastructure Validation

```bash
# Make script executable
chmod +x scripts/infrastructure-validation.sh

# Run validation
./scripts/infrastructure-validation.sh
```

Expected output:
```
✅ Cluster access: OK
✅ Storage: OK  
✅ Helm: OK
✅ Namespace: OK
Ready to proceed with Helm chart deployment testing.
```

### 3. Deploy Services

```bash
# Create namespace
kubectl create namespace vllm-benchmark

# Deploy vLLM
helm install vllm-dev ./helm/vllm \
  --namespace vllm-benchmark

# Deploy TGI
helm install tgi-test ./helm/tgi \
  --namespace vllm-benchmark

# Deploy Ollama (coming soon)
helm install ollama-test ./helm/ollama \
  --namespace vllm-benchmark
```

### 4. Verify Deployments

```bash
# Check pod status
kubectl get pods -n vllm-benchmark -o wide

# Check routes (OpenShift)
oc get routes -n vllm-benchmark

# Check services
kubectl get svc -n vllm-benchmark
```

Expected deployment:
```
NAME                         NODE                           STATUS
vllm-test-xxx               ip-10-0-109-102.ec2.internal   Running
tgi-test-xxx                ip-10-0-13-36.ec2.internal     Running  
ollama-test-xxx             ip-10-0-16-134.ec2.internal    Running
```

## 📊 Benchmarking

### Launch Jupyter Notebook

```bash
# Install dependencies
pip install -r requirements.txt

# Start Jupyter Lab
jupyter lab notebooks/low_latency_chat.ipynb
```

### Notebook Sections

1. **Introduction** - Project overview and goals
2. **Environment Check** - Validate service connectivity  
3. **vLLM Configuration** - Low-latency optimization
4. **Load Generation** - Concurrent user simulation
5. **Metrics Capture** - TTFT, ITL, E2E measurement
6. **Visualization** - Interactive performance charts
7. **Summary** - Results and recommendations

## 🛠️ Configuration

### Model Selection

Both services use the same model for fair comparison:

```yaml
# Default: Qwen/Qwen2.5-7B
model: "Qwen/Qwen2.5-7B"
```

Supported models:
- `Qwen/Qwen2.5-7B` (default)
- `microsoft/DialoGPT-medium` (lightweight)
- `RedHatAI/Llama-3.1-8B-Instruct` (advanced)

### Resource Configuration

```yaml
resources:
  limits:
    cpu: "4"
    memory: 24Gi
    nvidia.com/gpu: 1
  requests:
    cpu: "2" 
    memory: 16Gi
    nvidia.com/gpu: 1
```

### Anti-Affinity Rules

Services automatically spread across different nodes:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/name: [other-service]
        topologyKey: kubernetes.io/hostname
```

## 📈 Performance Tuning

### vLLM Optimizations

```yaml
vllm:
  args:
    - --max-num-batched-tokens=2048
    - --max-num-seqs=64  
    - --gpu-memory-utilization=0.92
    - --max-model-len=4096
```

### TGI Optimizations

```yaml
tgi:
  args:
    - --max-concurrent-requests=128
    - --max-batch-prefill-tokens=4096
    - --max-batch-total-tokens=8192
    - --waiting-served-ratio=1.2
```

## 🔧 Development

### Project Structure

```
vllm-notebooks/
├── README.md                    # This file
├── PRD                         # Product Requirements Document  
├── implementation-plan.md      # Development roadmap
├── requirements.txt           # Python dependencies
├── scripts/
│   └── infrastructure-validation.sh
├── helm/                      # Helm charts
│   ├── vllm/                 # vLLM deployment
│   ├── tgi/                  # TGI deployment  
│   └── ollama/               # Ollama deployment (WIP)
├── notebooks/                # Jupyter notebooks (WIP)
│   └── low_latency_chat.ipynb
├── data/                     # Test data and prompts
└── docs/                     # Documentation
```

### Development Environment

```bash
# Create Python environment
python3.9 -m venv vllm-notebook-env
source vllm-notebook-env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Jupyter kernel
python -m ipykernel install --user --name=vllm-notebook
```

### Running Tests

```bash
# Validate Helm charts
helm lint ./helm/vllm
helm lint ./helm/tgi

# Test deployments  
helm install test-vllm ./helm/vllm --dry-run
helm install test-tgi ./helm/tgi --dry-run

# Infrastructure validation
./scripts/infrastructure-validation.sh
```

## 🐛 Troubleshooting

### Common Issues

#### Pods Stuck in Pending
```bash
# Check resource constraints
kubectl describe pod -l app.kubernetes.io/name=vllm -n vllm-benchmark

# Check node availability
kubectl get nodes -o wide

# Check PVC status
kubectl get pvc -n vllm-benchmark
```

#### Model Download Issues
```bash
# Check logs for download errors
kubectl logs -f deployment/vllm-dev -n vllm-benchmark

# For gated models, set HuggingFace token
kubectl create secret generic hf-token \
  --from-literal=token=hf_your_token_here \
  -n vllm-benchmark
```

#### Out of Memory Errors
```bash
# Check memory usage
kubectl top pods -n vllm-benchmark

# Increase memory limits
helm upgrade vllm-dev ./helm/vllm \
  --set resources.limits.memory="32Gi" \
  -n vllm-benchmark
```

#### Route/Ingress Issues
```bash
# Check route status (OpenShift)
oc get routes -n vllm-benchmark
oc describe route vllm-dev -n vllm-benchmark

# Test connectivity
curl -k https://$(oc get route vllm-dev -n vllm-benchmark -o jsonpath='{.spec.host}')/health
```

### Debug Commands

```bash
# Comprehensive status check
kubectl get all -n vllm-benchmark

# Pod diagnostics
kubectl describe pod -l app.kubernetes.io/name=vllm -n vllm-benchmark
kubectl logs -f deployment/vllm-dev -n vllm-benchmark --previous

# Resource usage
kubectl top pods -n vllm-benchmark
kubectl top nodes

# Network diagnostics
kubectl get svc,routes,ingress -n vllm-benchmark
```

## 📚 Documentation

- [Product Requirements Document](PRD) - Project goals and requirements
- [Implementation Plan](implementation-plan.md) - Development roadmap
- [vLLM Deployment Guide](helm/vllm/DEPLOYMENT.md) - vLLM setup instructions
- [TGI Deployment Guide](helm/tgi/DEPLOYMENT.md) - TGI setup instructions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow the staged implementation plan
- Update documentation for new features
- Test on OpenShift before submitting PRs
- Include performance impact analysis
- Maintain backward compatibility

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/vllm-notebooks/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/vllm-notebooks/discussions)
- **Documentation**: [Project Wiki](https://github.com/your-org/vllm-notebooks/wiki)

## 🏆 Acknowledgments

- [vLLM Project](https://github.com/vllm-project/vllm) - High-performance inference engine
- [Text Generation Inference](https://github.com/huggingface/text-generation-inference) - HuggingFace inference server
- [Ollama](https://github.com/ollama/ollama) - Local LLM deployment
- [OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift) - Enterprise Kubernetes platform

---

**Built with ❤️ for the AI/ML community**
