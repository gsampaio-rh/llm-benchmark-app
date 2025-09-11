# TGI (Text Generation Inference) Competitor

This directory contains Helm charts for deploying HuggingFace's Text Generation Inference (TGI) server as a competitor for vLLM benchmarking.

## 🎯 **Purpose**

Deploy TGI alongside vLLM to enable **real side-by-side benchmarking** in the Apple Store-style tutorial scenarios. This allows for authentic performance comparisons rather than simulated data.

## 🚀 **Quick Start**

### 1. Deploy TGI Competitor

```bash
# Deploy TGI with same model as your vLLM server
./scripts/deploy-competitors.sh --model "Qwen/Qwen2.5-0.5B"

# Or deploy with GPU support
./scripts/deploy-competitors.sh --model "Qwen/Qwen2.5-0.5B" --gpu
```

### 2. Get TGI Server URL

```bash
# Get the route URL (OpenShift)
TGI_URL=$(oc get route tgi-competitor -n vllm-benchmark -o jsonpath='{.spec.host}')
echo "TGI URL: https://$TGI_URL"

# Or port-forward for local testing
kubectl port-forward -n vllm-benchmark svc/tgi-competitor 8081:8080
TGI_URL="http://localhost:8081"
```

### 3. Run vLLM vs TGI Comparison

```bash
# Run tutorial with real competitor comparison
vllm-benchmark tutorial run low_latency_chat \
  --server-url "https://vllm-dev-vllm-benchmark.apps.cluster.com" \
  --competitor-url "https://$TGI_URL" \
  --competitor-name "HuggingFace TGI" \
  --model "Qwen/Qwen2.5-0.5B" \
  --user-level intermediate
```

## 📊 **Expected Results**

When running the comparison, you should see:

- **vLLM Performance**: Optimized TTFT, higher throughput
- **TGI Performance**: Baseline comparison metrics  
- **Side-by-Side Charts**: Visual performance comparison
- **"Why vLLM Wins"**: Real data showing vLLM advantages

## 🔧 **Advanced Configuration**

### GPU Support

```bash
./scripts/deploy-competitors.sh \
  --model "microsoft/DialoGPT-medium" \
  --gpu \
  --namespace vllm-benchmark
```

### Custom TGI Settings

```yaml
# values-custom.yaml
tgi:
  args:
    - --max-concurrent-requests=256
    - --max-batch-prefill-tokens=8192
    - --max-batch-total-tokens=16384

resources:
  limits:
    cpu: "8"
    memory: 32Gi
    nvidia.com/gpu: 1
```

```bash
helm upgrade tgi-competitor ./helm/tgi -f values-custom.yaml
```

## 🛠 **Development**

### Test Locally

```bash
# Deploy locally with port-forward
helm install tgi-test ./helm/tgi --set route.enabled=false
kubectl port-forward svc/tgi-test 8081:8080

# Test TGI server
curl http://localhost:8081/health
curl http://localhost:8081/v1/models
```

### Monitor Performance

```bash
# Watch TGI logs
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=tgi -f

# Check resource usage
kubectl top pods -n vllm-benchmark -l app.kubernetes.io/name=tgi
```

## 🧹 **Cleanup**

```bash
# Remove TGI deployment
helm uninstall tgi-competitor -n vllm-benchmark

# Or use the script
./scripts/deploy-competitors.sh --cleanup
```

## 🤔 **Troubleshooting**

### Common Issues

1. **Model Download Slow**
   - Increase startup probe timeout
   - Check network connectivity
   - Verify storage space

2. **GPU Not Available**
   - Check node GPU resources
   - Verify tolerations/node selectors
   - Review resource limits

3. **Comparison Fails**
   - Verify both servers use same model
   - Check network connectivity between pods
   - Review timeout settings

### Health Checks

```bash
# Check TGI server health
TGI_URL=$(oc get route tgi-competitor -n vllm-benchmark -o jsonpath='{.spec.host}')
curl -f "https://$TGI_URL/health"
curl -f "https://$TGI_URL/v1/models"

# Test generation
curl -X POST "https://$TGI_URL/v1/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-0.5B", "prompt": "Hello", "max_tokens": 10}'
```

## 📈 **Performance Tuning**

For optimal benchmark results:

```yaml
tgi:
  args:
    - --max-concurrent-requests=128
    - --max-batch-prefill-tokens=4096
    - --max-batch-total-tokens=8192
    - --waiting-served-ratio=1.2

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

This ensures TGI runs at optimal settings for fair comparison with vLLM.
