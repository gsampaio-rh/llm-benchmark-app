# vLLM Single-Configuration Helm Chart

This Helm chart deploys a single vLLM instance with configurable optimization settings. Each configuration can be deployed independently using different values files, allowing for modular and flexible vLLM deployments.

## Features

- 🚀 **Single vLLM Instance**: Deploy one vLLM configuration per chart installation
- 🔧 **Pre-configured Optimizations**: Ready-to-use values files for different optimization strategies
- 📊 **Prometheus Metrics**: Built-in monitoring and metrics collection
- 🏗️ **OpenShift Ready**: Includes Routes, SecurityContextConstraints, and OpenShift-specific configs
- 🎯 **Benchmark Ready**: Perfect for performance comparisons when deployed multiple times
- 🔄 **Flexible**: Highly configurable with comprehensive values files

## Prerequisites

- Kubernetes 1.19+ or OpenShift 4.6+
- Helm 3.2.0+
- Persistent storage with ReadWriteOnce access
- GPU nodes (optional but recommended for performance)
- Sufficient storage (20Gi+ per configuration for model caching)

## Quick Start

### 1. Deploy Baseline Configuration

```bash
# Deploy baseline vLLM instance
helm install vllm-baseline ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  --create-namespace -n vllm-benchmark
```

### 2. Deploy Multiple Configurations for Comparison

```bash
# Deploy different optimization configurations
helm install vllm-baseline ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  -n vllm-benchmark

helm install vllm-prefix-cache ./helm/vllm \
  -f ./helm/vllm/values-prefix-cache.yaml \
  -n vllm-benchmark

helm install vllm-chunked-prefill ./helm/vllm \
  -f ./helm/vllm/values-chunked-prefill.yaml \
  -n vllm-benchmark
```

### 3. Deploy Production Configuration

```bash
# Set your HuggingFace token for gated models
export HF_TOKEN="hf_your_token_here"

# Deploy production configuration with larger model
helm install vllm-production ./helm/vllm \
  -f ./helm/vllm/values-production.yaml \
  --set huggingface.token="$HF_TOKEN" \
  -n vllm-production
```

## Available Pre-configured Values Files

| Values File | Description | Optimization | Expected Improvements |
|-------------|-------------|--------------|----------------------|
| `values-baseline.yaml` | Standard vLLM without optimizations | None | N/A (baseline) |
| `values-prefix-cache.yaml` | Prefix caching enabled | `--enable-prefix-caching` | 20-50% improvement for repeated prompts |
| `values-chunked-prefill.yaml` | Chunked prefill optimization | `--enable-chunked-prefill` | 10-30% latency improvement |
| `values-continuous-batch.yaml` | Continuous batching | `--max-num-batched-tokens=8192` | 15-40% throughput improvement |
| `values-tensor-parallel.yaml` | Multi-GPU tensor parallelism | `--tensor-parallel-size=2` | 50-80% throughput improvement |
| `values-quantized-awq.yaml` | AWQ quantization | `--quantization=awq` | Reduced memory usage |
| `values-production.yaml` | Production with combined optimizations | Multiple flags | Production-ready performance |

## Configuration

### Basic Configuration

```yaml
# values-custom.yaml
vllm:
  model: "your/custom-model"
  port: 8000
  args:
    - --model={{ .Values.vllm.model }}
    - --port={{ .Values.vllm.port }}
    - --host=0.0.0.0
    - --your-custom-args

resources:
  limits:
    cpu: "4"
    memory: 24Gi
    nvidia.com/gpu: 1
```

### Advanced Configuration

```yaml
# Custom optimization configuration
nameOverride: "vllm-custom"

config:
  name: "custom-optimization"
  description: "Custom vLLM optimization strategy"

vllm:
  model: "your/model"
  port: 8000
  args:
    - --model={{ .Values.vllm.model }}
    - --port={{ .Values.vllm.port }}
    - --enable-prefix-caching
    - --enable-chunked-prefill
    - --max-num-batched-tokens=4096
    - --gpu-memory-utilization=0.8
  
  env:
    - name: CUSTOM_ENV_VAR
      value: "custom_value"

route:
  enabled: true
  host: "custom-vllm.apps.cluster.com"

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true

nodeSelector:
  nvidia.com/gpu.present: "true"

tolerations:
  - key: "nvidia.com/gpu"
    operator: "Exists"
    effect: "NoSchedule"
```

## Deployment Patterns

### 1. Development/Testing Pattern

Deploy lightweight configurations for development:

```bash
# Quick test with small model
helm install vllm-dev ./helm/vllm \
  --set vllm.model="Qwen/Qwen2.5-0.5B" \
  --set resources.limits.memory="8Gi" \
  --set storage.size="20Gi" \
  -n vllm-dev
```

### 2. Benchmarking Pattern

Deploy multiple configurations for performance comparison:

```bash
# Create namespace
kubectl create namespace vllm-benchmark

# Deploy each configuration
for config in baseline prefix-cache chunked-prefill continuous-batch; do
  helm install vllm-$config ./helm/vllm \
    -f ./helm/vllm/values-$config.yaml \
    -n vllm-benchmark
done
```

### 3. Production Pattern

Deploy with high availability and monitoring:

```bash
# Production deployment with monitoring
helm install vllm-prod ./helm/vllm \
  -f ./helm/vllm/values-production.yaml \
  --set monitoring.serviceMonitor.enabled=true \
  --set podDisruptionBudget.enabled=true \
  --set huggingface.token="$HF_TOKEN" \
  -n vllm-production
```

## Monitoring and Observability

### Prometheus Metrics

Each vLLM instance exposes metrics at `/metrics` endpoint:

```bash
# Check metrics
curl https://vllm-baseline-route.apps.cluster.com/metrics
```

### ServiceMonitor

Enable ServiceMonitor for Prometheus Operator:

```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    labels:
      team: ai-platform
```

## Usage with vLLM Benchmark Tool

Get the route URLs and use them for benchmarking:

```bash
# Get all routes
oc get routes -n vllm-benchmark

# Run single benchmark
vllm-benchmark benchmark \
  --server-url "https://vllm-baseline-route.apps.cluster.com" \
  --model "Qwen/Qwen2.5-0.5B" \
  --scenario stress

# Compare configurations
vllm-benchmark compare \
  --baseline-url "https://vllm-baseline-route.apps.cluster.com" \
  --optimized-url "https://vllm-prefix-cache-route.apps.cluster.com" \
  --model "Qwen/Qwen2.5-0.5B"
```

## Scaling and Resource Management

### GPU Support

For GPU-enabled deployments:

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

### Multi-GPU Support

For tensor parallelism:

```yaml
vllm:
  args:
    - --tensor-parallel-size=2

resources:
  limits:
    nvidia.com/gpu: 2

nodeSelector:
  nvidia.com/gpu.count: "2"
```

### Storage Optimization

Different models require different storage:

```yaml
# Small model (0.5B-1B parameters)
storage:
  size: 20Gi

# Medium model (3B-8B parameters)  
storage:
  size: 50Gi

# Large model (13B+ parameters)
storage:
  size: 200Gi
```

## Troubleshooting

### Common Issues

1. **Pod stuck in Pending**: Check resource availability and node selectors
2. **Model download fails**: Verify HuggingFace token for gated models
3. **OOM errors**: Increase memory limits or reduce GPU memory utilization
4. **Route not accessible**: Check OpenShift router configuration

### Debug Commands

```bash
# Check pod status
kubectl get pods -n vllm-benchmark

# Check pod logs
kubectl logs deployment/vllm-baseline -n vllm-benchmark

# Check pod resources
kubectl describe pod -l app.kubernetes.io/name=vllm -n vllm-benchmark

# Check storage
kubectl get pvc -n vllm-benchmark

# Check routes
oc get routes -n vllm-benchmark
```

### Resource Debugging

```bash
# Check GPU availability
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu

# Check storage classes
kubectl get storageclass

# Check resource usage
kubectl top pods -n vllm-benchmark
```

## Security Considerations

### Service Account

The chart creates a service account with appropriate permissions:

```yaml
serviceAccount:
  create: true
  annotations:
    serviceaccounts.openshift.io/scc: anyuid
```

### Pod Security Context

Configure appropriate security context:

```yaml
podSecurityContext:
  runAsNonRoot: false  # vLLM may need root access
  fsGroup: 0

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

### Network Policies

Consider implementing network policies for production:

```yaml
# Example network policy (not included in chart)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: vllm
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: vllm-benchmark
    ports:
    - protocol: TCP
      port: 8000
```

## Cleanup

```bash
# Uninstall specific configuration
helm uninstall vllm-baseline -n vllm-benchmark

# Uninstall all configurations
helm list -n vllm-benchmark -q | xargs -I {} helm uninstall {} -n vllm-benchmark

# Delete namespace
kubectl delete namespace vllm-benchmark
```

## Migration from Multi-Config Chart

If migrating from the old multi-config chart:

1. **Extract configurations**: Each config becomes a separate values file
2. **Deploy individually**: Use separate `helm install` commands
3. **Update scripts**: Modify benchmark scripts to use new URLs
4. **Update monitoring**: ServiceMonitors are now per-instance

```bash
# Old way (multi-config)
helm install vllm-test ./helm/vllm-multi-config

# New way (single-config)
helm install vllm-baseline ./helm/vllm -f ./helm/vllm/values-baseline.yaml
helm install vllm-optimized ./helm/vllm -f ./helm/vllm/values-prefix-cache.yaml
```

## Examples

See the `examples/` directory for updated scripts that work with the new single-config approach.

## Contributing

When adding new optimization configurations:

1. Create a new `values-{optimization}.yaml` file
2. Document the optimization in this README
3. Update example scripts if needed
4. Test the configuration thoroughly
