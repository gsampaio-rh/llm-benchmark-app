# TGI (Text Generation Inference) Deployment Guide

This Helm chart deploys HuggingFace's Text Generation Inference server as a competitor for vLLM benchmarking.

## Quick Start

### 1. Deploy TGI Competitor

```bash
# Deploy TGI with default settings (Qwen/Qwen2.5-0.5B model)
helm install tgi-competitor ./helm/tgi \
  --create-namespace \
  --namespace vllm-benchmark

# Or deploy with custom model
helm install tgi-competitor ./helm/tgi \
  --set tgi.model="microsoft/DialoGPT-medium" \
  --create-namespace \
  --namespace vllm-benchmark
```

### 2. Enable OpenShift Route (for external access)

```bash
helm upgrade tgi-competitor ./helm/tgi \
  --set route.enabled=true \
  --set route.tls.termination=edge \
  --namespace vllm-benchmark
```

### 3. Check Deployment Status

```bash
# Check pod status
kubectl get pods -n vllm-benchmark -l app.kubernetes.io/name=tgi

# Check service
kubectl get svc -n vllm-benchmark -l app.kubernetes.io/name=tgi

# Check route (OpenShift)
oc get routes -n vllm-benchmark

# Check logs
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=tgi -f
```

## Configuration Options

### Model Configuration

```yaml
tgi:
  model: "Qwen/Qwen2.5-0.5B"  # Model to serve
  port: 8080                   # Server port
  
  # TGI-specific parameters
  args:
    - --max-concurrent-requests=128
    - --max-batch-prefill-tokens=4096
    - --max-batch-total-tokens=8192
    - --max-input-length=1024
    - --max-total-tokens=2048
```

### Resource Allocation

```yaml
resources:
  limits:
    cpu: "4"
    memory: 24Gi
    nvidia.com/gpu: 1  # Enable GPU support
  requests:
    cpu: "2" 
    memory: 16Gi
    nvidia.com/gpu: 1
```

### Storage

```yaml
storage:
  enabled: true
  size: 50Gi
  accessModes:
    - ReadWriteOnce
  storageClass: ""  # Use default
```

## Advanced Configurations

### GPU Support

For GPU acceleration, uncomment the GPU resource limits:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
  requests:
    nvidia.com/gpu: 1

nodeSelector:
  nvidia.com/gpu.present: "true"

tolerations:
  - key: "nvidia.com/gpu"
    operator: "Exists"
    effect: "NoSchedule"
```

### HuggingFace Token (for gated models)

```yaml
huggingface:
  token: "hf_your_token_here"
```

### High Availability

```yaml
replicaCount: 3

podDisruptionBudget:
  enabled: true
  maxUnavailable: 1

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/name: tgi
        topologyKey: kubernetes.io/hostname
```

## Monitoring

### Enable Prometheus Metrics

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    scrapeTimeout: 10s
```

## Benchmarking Usage

Once deployed, the TGI server will be available for benchmarking:

```bash
# Get the service URL
TGI_URL=$(oc get route tgi-competitor -n vllm-benchmark -o jsonpath='{.spec.host}')

# Run vLLM benchmark comparison
vllm-benchmark tutorial run low_latency_chat \
  --server-url "https://vllm-dev-vllm-benchmark.apps.cluster.com" \
  --competitor-url "https://${TGI_URL}" \
  --user-level intermediate
```

## Troubleshooting

### Common Issues

1. **Pod Stuck in Pending**
   ```bash
   kubectl describe pod -n vllm-benchmark -l app.kubernetes.io/name=tgi
   ```
   - Check resource availability
   - Verify GPU node selector/tolerations

2. **Model Download Issues**
   ```bash
   kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=tgi
   ```
   - Check HuggingFace token for gated models
   - Verify network connectivity
   - Ensure sufficient storage space

3. **Health Check Failures**
   ```bash
   kubectl get events -n vllm-benchmark
   ```
   - Increase startup probe timeout for large models
   - Check memory/GPU allocation

### Performance Tuning

For optimal benchmarking performance:

```yaml
tgi:
  args:
    - --max-concurrent-requests=256      # Higher concurrency
    - --max-batch-prefill-tokens=8192    # Larger batches
    - --max-batch-total-tokens=16384     # More total tokens
    - --waiting-served-ratio=0.8         # Faster serving
    - --max-waiting-tokens=50            # Queue management
```

## Cleanup

```bash
# Remove TGI deployment
helm uninstall tgi-competitor -n vllm-benchmark

# Remove namespace (if empty)
kubectl delete namespace vllm-benchmark
```
