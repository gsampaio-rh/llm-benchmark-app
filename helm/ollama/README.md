# Ollama Helm Chart

This Helm chart deploys [Ollama](https://github.com/ollama/ollama) as a third competitor for vLLM and TGI benchmarking.

## Overview

Ollama is a tool designed to run large language models locally with a simple API. This chart integrates Ollama into the vLLM vs TGI benchmarking suite to provide a three-way comparison.

## Features

- **Local Model Management**: Automatic model pulling and caching
- **GPU Support**: NVIDIA GPU acceleration when available
- **Anti-Affinity**: Automatic separation from vLLM and TGI pods
- **Health Checks**: Comprehensive readiness and liveness probes
- **OpenShift Routes**: Native OpenShift route support
- **Monitoring**: Optional Prometheus ServiceMonitor integration
- **Storage**: Persistent storage for model caching

## Quick Start

### Basic Deployment

```bash
# Deploy Ollama with default settings
helm install ollama-test ./helm/ollama \
  --create-namespace \
  --namespace vllm-benchmark
```

### With Custom Model

```bash
# Deploy with a specific model
helm install ollama-test ./helm/ollama \
  --set ollama.model="llama3.1:8b" \
  --namespace vllm-benchmark
```

### Enable Route (OpenShift)

```bash
helm upgrade ollama-test ./helm/ollama \
  --set route.enabled=true \
  --set route.tls.termination=edge \
  --namespace vllm-benchmark
```

## Configuration

### Model Configuration

```yaml
ollama:
  model: "qwen2.5:7b"  # Primary model to serve
  modelPull:
    enabled: true
    additionalModels:
      - "qwen2.5:0.5b"
      - "llama3.1:8b"
```

### Resource Configuration

```yaml
resources:
  limits:
    cpu: "4"
    memory: 32Gi
    nvidia.com/gpu: 1
  requests:
    cpu: "2"
    memory: 16Gi
    nvidia.com/gpu: 1
```

### Anti-Affinity (Automatic)

The chart automatically configures anti-affinity rules to:
- Avoid nodes running vLLM pods (weight: 100)
- Avoid nodes running TGI pods (weight: 100)
- Spread Ollama instances across nodes (weight: 50)

## API Usage

Once deployed, Ollama provides a REST API compatible with OpenAI's format:

### Health Check
```bash
curl http://ollama-service:11434/api/tags
```

### Generate Completion
```bash
curl -X POST http://ollama-service:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "prompt": "What is the capital of France?",
    "stream": false
  }'
```

### Chat Completion
```bash
curl -X POST http://ollama-service:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'
```

## Monitoring

Enable Prometheus monitoring:

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
```

## Troubleshooting

### Model Pull Issues

Check model pull logs:
```bash
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=ollama -c model-pull
```

### Service Not Ready

Check pod status and logs:
```bash
kubectl get pods -n vllm-benchmark -l app.kubernetes.io/name=ollama
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=ollama -f
```

### GPU Issues

Verify GPU availability:
```bash
kubectl describe nodes | grep nvidia.com/gpu
```

## Integration with Benchmarking

This chart is designed to work seamlessly with the vLLM vs TGI benchmarking notebook. The Ollama service will be automatically discovered and included in performance comparisons.

### Benchmark Endpoints

- **vLLM**: `http://vllm-service:8000`
- **TGI**: `http://tgi-service:8080`
- **Ollama**: `http://ollama-service:11434`

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ollama.model` | Primary model to serve | `qwen2.5:7b` |
| `ollama.port` | Service port | `11434` |
| `storage.size` | Persistent storage size | `100Gi` |
| `resources.limits.memory` | Memory limit | `32Gi` |
| `route.enabled` | Enable OpenShift route | `true` |
| `nodeSelector` | Node selector for GPU nodes | `nvidia.com/gpu.present: "true"` |

For a complete list of values, see [values.yaml](./values.yaml).
