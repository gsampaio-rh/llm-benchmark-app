# Ollama Deployment Fixes

## Issues Fixed

The Ollama Helm chart had several critical issues that prevented proper model deployment:

### 🔧 **Fixed Issues:**

1. **Init Container Environment Variables** 
   - **Problem**: Environment variables weren't properly formatted for Kubernetes
   - **Fix**: Changed from `toYaml` to proper env variable iteration with forced `OLLAMA_HOST` override

2. **Model Pull Script Reliability**
   - **Problem**: Insufficient timeout and error handling during model downloads
   - **Fix**: Added comprehensive error handling, 5-minute timeout, and model verification

3. **Volume Mount Race Condition**
   - **Problem**: Both emptyDir and PVC volumes were created, causing conflicts
   - **Fix**: Conditional volume creation - only create the volume type that's needed

4. **Resource Constraints**
   - **Problem**: Init container had insufficient resources for large model downloads
   - **Fix**: Increased init container resources and added GPU allocation when available

5. **Health Check Timing**
   - **Problem**: Health checks started too early, before models were loaded
   - **Fix**: Adjusted timing - startup probe allows 20 minutes, readiness increased delays

6. **Main Container Model Loading**
   - **Problem**: Main container didn't pre-load models, causing slow first requests
   - **Fix**: Added model pre-loading during startup to ensure models are ready

## Quick Deployment Test

### 1. Deploy with Fixes
```bash
# Create namespace if needed
kubectl create namespace vllm-benchmark

# Deploy Ollama with the fixed chart
helm install ollama-test ./helm/ollama --namespace vllm-benchmark

# Monitor deployment
watch kubectl get pods -n vllm-benchmark -l app.kubernetes.io/name=ollama
```

### 2. Validate Deployment
```bash
# Run comprehensive validation
./scripts/validate-ollama-deployment.sh

# Or check specific aspects
./scripts/validate-ollama-deployment.sh logs     # Check logs only
./scripts/validate-ollama-deployment.sh api      # Test API only
```

### 3. Monitor Model Pull Progress
```bash
# Watch init container logs (model download)
kubectl logs -f -n vllm-benchmark -l app.kubernetes.io/name=ollama -c model-pull

# Watch main container startup
kubectl logs -f -n vllm-benchmark -l app.kubernetes.io/name=ollama -c ollama
```

## Expected Timeline

| Phase | Duration | What's Happening |
|-------|----------|------------------|
| Init Container | 5-15 minutes | Model download (depends on network) |
| Main Container Startup | 2-5 minutes | Server start + model pre-loading |
| Health Checks | 1-2 minutes | Readiness verification |
| **Total** | **8-22 minutes** | **Full deployment ready** |

## Success Indicators

### ✅ Healthy Deployment Signs:
- Init container completes with "Models ready!" message
- Main container shows "Ollama Server fully ready"
- Pod status shows `1/1 Running`
- API responds to `/api/tags` with model list
- Model generation works via `/api/generate`

### ❌ Common Failure Patterns:
- Init container stuck: Check network connectivity and storage
- Main container CrashLoopBackOff: Check resource allocation and GPU availability
- API not responding: Check port configuration and health checks

## Testing API

```bash
# Port forward to test
kubectl port-forward -n vllm-benchmark svc/ollama-test 11434:11434

# Check available models
curl http://localhost:11434/api/tags

# Test generation
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "prompt": "Hello, how are you?",
    "stream": false
  }'
```

## Configuration Options

### Faster Deployment (Smaller Model)
```yaml
ollama:
  model: "qwen2.5:0.5b"  # Much smaller, faster download
```

### Multiple Models
```yaml
ollama:
  model: "qwen2.5:7b"
  modelPull:
    enabled: true
    additionalModels:
      - "qwen2.5:0.5b"
      - "llama3.1:8b"
```

### CPU-Only Mode (No GPU Required)
```yaml
resources:
  limits:
    cpu: "8"
    memory: 32Gi
  requests:
    cpu: "4"
    memory: 16Gi

nodeSelector: {}
```

## Troubleshooting Commands

```bash
# Check all resources
kubectl get all -n vllm-benchmark -l app.kubernetes.io/name=ollama

# Describe pod for events
kubectl describe pod -n vllm-benchmark -l app.kubernetes.io/name=ollama

# Check resource usage
kubectl top pod -n vllm-benchmark -l app.kubernetes.io/name=ollama

# Check storage
kubectl get pvc -n vllm-benchmark

# Force restart if needed
kubectl rollout restart deployment/ollama-test -n vllm-benchmark
```

## Next Steps

After successful deployment:
1. Verify all three services (vLLM, TGI, Ollama) are running on different nodes
2. Run the benchmark notebooks to compare performance
3. Monitor resource usage and adjust limits as needed
