# Ollama Deployment Guide

This guide provides detailed instructions for deploying Ollama as part of the vLLM vs TGI benchmarking suite.

## Prerequisites

- **OpenShift 4.6+** or **Kubernetes 1.19+**
- **Helm 3.2+**
- **GPU Nodes** (recommended for optimal performance)
- **100Gi+ Storage** per Ollama instance
- **Network Access** for model downloads

## Deployment Steps

### 1. Validate Environment

Run the infrastructure validation script:
```bash
./scripts/infrastructure-validation.sh
```

Expected output should include GPU node detection.

### 2. Deploy Ollama

#### Basic Deployment
```bash
# Create namespace (if not exists)
kubectl create namespace vllm-benchmark

# Deploy Ollama
helm install ollama-test ./helm/ollama \
  --namespace vllm-benchmark
```

#### Production Deployment
```bash
# Deploy with production settings
helm install ollama-prod ./helm/ollama \
  --namespace vllm-benchmark \
  --set route.enabled=true \
  --set route.tls.termination=edge \
  --set monitoring.enabled=true \
  --set storage.size=200Gi \
  --set resources.limits.memory=64Gi
```

### 3. Verify Deployment

#### Check Pod Status
```bash
kubectl get pods -n vllm-benchmark -l app.kubernetes.io/name=ollama -o wide
```

Expected output:
```
NAME                     READY   STATUS    RESTARTS   AGE   NODE
ollama-test-xxx          1/1     Running   0          5m    ip-10-0-xxx
```

#### Check Service
```bash
kubectl get svc -n vllm-benchmark -l app.kubernetes.io/name=ollama
```

#### Check Route (OpenShift)
```bash
oc get routes -n vllm-benchmark
```

#### Verify Model Loading
```bash
# Check init container logs for model pull
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=ollama -c model-pull

# Check main container logs
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=ollama -c ollama -f
```

### 4. Test API Connectivity

#### Internal Testing
```bash
# Port forward for testing
kubectl port-forward -n vllm-benchmark svc/ollama-test 11434:11434

# Test health endpoint
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

#### External Testing (OpenShift Route)
```bash
# Get route URL
OLLAMA_URL=$(oc get route ollama-test -n vllm-benchmark -o jsonpath='{.spec.host}')

# Test via route
curl -k https://$OLLAMA_URL/api/tags
```

## Configuration Options

### Model Configuration

#### Single Model (Default)
```yaml
ollama:
  model: "qwen2.5:7b"
  modelPull:
    enabled: true
```

#### Multiple Models
```yaml
ollama:
  model: "qwen2.5:7b"  # Primary model
  modelPull:
    enabled: true
    additionalModels:
      - "qwen2.5:0.5b"  # Lightweight model
      - "llama3.1:8b"   # Alternative model
```

### Resource Scaling

#### GPU Configuration
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
  requests:
    nvidia.com/gpu: 1

nodeSelector:
  nvidia.com/gpu.present: "true"
```

#### CPU-Only Mode
```yaml
# Remove GPU requirements
resources:
  limits:
    cpu: "8"
    memory: 32Gi
  requests:
    cpu: "4"
    memory: 16Gi

# Remove GPU node selector
nodeSelector: {}
```

### Storage Configuration

#### Large Model Storage
```yaml
storage:
  enabled: true
  size: 200Gi  # For multiple large models
  storageClass: "fast-ssd"
```

#### Network Storage
```yaml
storage:
  enabled: true
  size: 100Gi
  accessModes:
    - ReadWriteMany  # For shared storage
```

## Anti-Affinity Verification

The chart automatically configures anti-affinity to ensure Ollama runs on different nodes from vLLM and TGI.

### Verify Node Distribution
```bash
# Check all pods and their nodes
kubectl get pods -n vllm-benchmark -o wide

# Should show:
# vllm-xxx    on node-1
# tgi-xxx     on node-2  
# ollama-xxx  on node-3
```

### Manual Anti-Affinity Override
```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          app.kubernetes.io/name: vllm
      topologyKey: kubernetes.io/hostname
    - labelSelector:
        matchLabels:
          app.kubernetes.io/name: tgi
      topologyKey: kubernetes.io/hostname
```

## Performance Tuning

### Ollama Optimization
```yaml
ollama:
  env:
    - name: OLLAMA_NUM_PARALLEL
      value: "4"           # Parallel request handling
    - name: OLLAMA_MAX_LOADED_MODELS
      value: "2"           # Keep multiple models in memory
    - name: OLLAMA_KEEP_ALIVE
      value: "10m"         # Keep models loaded longer
```

### GPU Memory Optimization
```yaml
ollama:
  env:
    - name: OLLAMA_GPU_LAYERS
      value: "32"          # Number of layers on GPU
    - name: OLLAMA_MAIN_GPU
      value: "0"           # Primary GPU ID
```

## Monitoring Setup

### Enable Prometheus Monitoring
```yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
    labels:
      team: ml-platform
```

### Custom Metrics
Ollama exposes metrics at `/metrics` endpoint for:
- Request latency
- Model loading time
- GPU utilization
- Memory usage

## Troubleshooting

### Common Issues

#### 1. Pod Stuck in Init
```bash
# Check model pull logs
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=ollama -c model-pull

# Common causes:
# - Network connectivity issues
# - Insufficient storage
# - Model not found
```

#### 2. Out of Memory
```bash
# Check resource usage
kubectl top pods -n vllm-benchmark

# Solutions:
# - Increase memory limits
# - Use smaller model
# - Enable model offloading
```

#### 3. GPU Not Available
```bash
# Check GPU allocation
kubectl describe pods -n vllm-benchmark -l app.kubernetes.io/name=ollama

# Check node GPU capacity
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
```

#### 4. API Not Responding
```bash
# Check service endpoints
kubectl get endpoints -n vllm-benchmark ollama-test

# Check pod logs
kubectl logs -n vllm-benchmark -l app.kubernetes.io/name=ollama -c ollama --tail=100
```

### Recovery Procedures

#### Restart with Clean State
```bash
# Delete and recreate deployment
helm uninstall ollama-test -n vllm-benchmark
kubectl delete pvc ollama-test-pvc -n vllm-benchmark
helm install ollama-test ./helm/ollama -n vllm-benchmark
```

#### Model Corruption Recovery
```bash
# Access pod and clear model cache
kubectl exec -it -n vllm-benchmark deployment/ollama-test -- rm -rf /root/.ollama/models/*

# Restart pod to trigger model re-pull
kubectl rollout restart deployment/ollama-test -n vllm-benchmark
```

## Integration Testing

### Three-Service Validation
```bash
# Test all three services are running
kubectl get pods -n vllm-benchmark -o wide

# Test all APIs respond
curl http://vllm-service:8000/health
curl http://tgi-service:8080/health  
curl http://ollama-service:11434/api/tags
```

### Benchmark Preparation
```bash
# Verify all services are on different nodes
kubectl get pods -n vllm-benchmark -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName

# Test concurrent access
for service in vllm tgi ollama; do
  echo "Testing $service..."
  kubectl port-forward -n vllm-benchmark svc/$service-service 8000:8000 &
done
```

## Cleanup

### Remove Ollama Only
```bash
helm uninstall ollama-test -n vllm-benchmark
kubectl delete pvc ollama-test-pvc -n vllm-benchmark
```

### Complete Cleanup
```bash
# Remove all benchmarking services
helm uninstall vllm-test -n vllm-benchmark
helm uninstall tgi-test -n vllm-benchmark  
helm uninstall ollama-test -n vllm-benchmark

# Remove namespace
kubectl delete namespace vllm-benchmark
```

---

**Next Steps**: After successful deployment, proceed to the Jupyter notebook for three-way performance benchmarking.
