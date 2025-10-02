# TGI Deployment Fixes

## Issues Fixed

The TGI (Text Generation Inference) Helm chart had several critical scheduling issues that prevented pod deployment:

### 🔧 **Fixed Issues:**

1. **Node Affinity/Selector Too Restrictive**
   - **Problem**: Hard requirement for `nvidia.com/gpu.present: "true"` label, but nodes may not have this exact label
   - **Fix**: Changed to flexible `nodeSelector: {}` with preferred node affinity for GPU nodes

2. **Missing GPU Taint Tolerations**
   - **Problem**: GPU nodes have `nvidia.com/gpu: True` taint but no tolerations configured
   - **Fix**: Added toleration for `nvidia.com/gpu` taint with `Exists` operator

3. **Master Node Taint Handling**
   - **Problem**: Master nodes have `node-role.kubernetes.io/master` taint, reducing available nodes
   - **Fix**: Added commented toleration option for master nodes (can be enabled if needed)

4. **Improved Node Affinity Strategy**
   - **Problem**: All-or-nothing approach to GPU node selection
   - **Fix**: Prefer GPU nodes but allow fallback to CPU nodes with multiple GPU detection strategies

## Scheduling Strategy

The new configuration uses a **flexible, preference-based approach**:

### 🎯 **Node Selection Priority:**
1. **Prefer GPU nodes** (weight: 100) - nodes with `nvidia.com/gpu.present: "true"`
2. **Prefer known GPU types** (weight: 90) - nodes with specific accelerator labels
3. **Prefer GPU instance types** (weight: 80) - nodes with GPU-optimized instance types
4. **Allow CPU fallback** - if no GPU nodes available, can schedule on CPU nodes
5. **Avoid conflicts** - prefer nodes without vLLM pods, spread TGI instances

### 🔧 **Taint Tolerations:**
- ✅ Tolerates `nvidia.com/gpu: True` (NoSchedule)
- 🔄 Optional master node toleration (commented out by default)

## Quick Deployment Test

### 1. Deploy with Fixes
```bash
# Create namespace if needed
kubectl create namespace vllm-benchmark

# Deploy TGI with the fixed chart
helm install tgi-test ./helm/tgi --namespace vllm-benchmark

# Monitor deployment
watch kubectl get pods -n vllm-benchmark -l app.kubernetes.io/name=tgi
```

### 2. Check Node Scheduling
```bash
# See which node the pod was scheduled on
kubectl get pods -n vllm-benchmark -l app.kubernetes.io/name=tgi -o wide

# Check node labels and taints
kubectl describe nodes | grep -A 5 -B 5 "nvidia.com/gpu\|Taints"
```

### 3. Validate Deployment
```bash
# Check pod events for scheduling information
kubectl describe pod -n vllm-benchmark -l app.kubernetes.io/name=tgi

# Check if GPU is detected (if on GPU node)
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=tgi | grep -i gpu

# Test API endpoint
kubectl port-forward -n vllm-benchmark svc/tgi-test 8080:8080
curl http://localhost:8080/health
```

## Expected Timeline

| Phase | Duration | What's Happening |
|-------|----------|------------------|
| Pod Scheduling | 10-30 seconds | Finding suitable node and pulling image |
| Model Loading | 2-6 minutes | Downloading and loading model weights |
| Health Checks | 1-2 minutes | Startup and readiness verification |
| **Total** | **3-8 minutes** | **Full deployment ready** |

## Success Indicators

### ✅ Healthy Deployment Signs:
- Pod status shows `1/1 Running`
- No scheduling errors in pod events
- Startup probe succeeds within timeout
- API responds to `/health` endpoint
- Model generation works via TGI API

### ❌ Common Failure Patterns Fixed:
- ~~Pod stuck in `Pending` state~~ → Now schedules flexibly
- ~~"0/8 nodes available" errors~~ → Tolerations handle taints
- ~~Node affinity conflicts~~ → Preference-based selection

## Configuration Options

### Force GPU-Only Deployment
```yaml
nodeSelector:
  nvidia.com/gpu.present: "true"
```

### Allow Master Node Scheduling
```yaml
tolerations:
  - key: "nvidia.com/gpu"
    operator: "Exists"
    effect: "NoSchedule"
  - key: "node-role.kubernetes.io/master"
    operator: "Exists"
    effect: "NoSchedule"
```

### CPU-Only Mode (No GPU Required)
```yaml
resources:
  limits:
    cpu: "8"
    memory: 32Gi
    # Remove nvidia.com/gpu: 1
  requests:
    cpu: "4"
    memory: 16Gi
    # Remove nvidia.com/gpu: 1

nodeSelector: {}
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: node-role.kubernetes.io/worker
          operator: Exists
```

## Troubleshooting Commands

### Check Scheduling Issues
```bash
# View scheduling events
kubectl get events -n vllm-benchmark --sort-by='.lastTimestamp'

# Check node capacity and allocations
kubectl describe nodes | grep -A 5 "Allocated resources"

# View pod scheduling details
kubectl describe pod -n vllm-benchmark -l app.kubernetes.io/name=tgi | grep -A 10 "Events"
```

### Check Node Labels and Taints
```bash
# List all node labels
kubectl get nodes --show-labels

# Check specific GPU-related labels
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.metadata.labels.'nvidia\.com/gpu\.present',ACCELERATOR:.metadata.labels.accelerator

# View node taints
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints
```

### Resource Monitoring
```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n vllm-benchmark

# Check GPU usage (if GPU monitoring is available)
kubectl get pods -n vllm-benchmark -o wide
```

## TGI-Specific Configuration

### Model Loading Optimization
```yaml
tgi:
  args:
    - "--model-id={{ .Values.tgi.model }}"
    - "--port={{ .Values.tgi.port }}"
    - "--hostname=0.0.0.0"
    - "--max-concurrent-requests=128"
    - "--max-input-length=1024"
    - "--max-total-tokens=2048"
    - "--huggingface-hub-cache=/data"
    - "--weights-cache-override=/data"
```

### Environment Variables for Performance
```yaml
tgi:
  env:
    - name: CUDA_VISIBLE_DEVICES
      value: "0"
    - name: TRANSFORMERS_CACHE
      value: "/data"
    - name: HF_HUB_CACHE
      value: "/data"
    - name: HF_HOME
      value: "/data"
```

## Next Steps

After successful deployment:
1. ✅ Verify TGI pod is running and healthy
2. 🧪 Test API endpoints for functionality
3. 📊 Compare with vLLM and Ollama deployments
4. 🏃 Run benchmark comparisons across all three engines
5. 📈 Monitor resource usage and adjust requests/limits as needed

## Integration with Benchmark Suite

The fixes applied here enable TGI to be part of the comprehensive benchmark suite:
- **vLLM Chart**: ✅ Already fixed with similar approach
- **Ollama Chart**: May need similar GPU taint tolerations
- **Benchmark Jobs**: Will benefit from similar scheduling flexibility

## API Compatibility

TGI provides OpenAI-compatible endpoints:
- `GET /health` - Health check
- `POST /generate` - Text generation
- `POST /generate_stream` - Streaming generation
- `GET /info` - Model information
- `GET /metrics` - Prometheus metrics (if enabled)
