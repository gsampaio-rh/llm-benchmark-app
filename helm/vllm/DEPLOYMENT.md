# vLLM Single-Config Deployment Guide

This guide provides step-by-step instructions for deploying vLLM instances using the single-configuration Helm chart approach.

## Overview

The new single-config approach allows you to:

- Deploy each vLLM configuration independently
- Use separate values files for different optimizations
- Scale and manage configurations individually
- Compare real performance differences between optimizations

## Prerequisites

### Infrastructure Requirements

- **Kubernetes**: 1.19+ or OpenShift 4.6+
- **Helm**: 3.2.0+
- **Storage**: Persistent storage with ReadWriteOnce access
- **GPU**: Recommended for production workloads
- **Memory**: Minimum 16Gi per instance (varies by model size)
- **CPU**: Minimum 2 cores per instance

### Cluster Preparation

```bash
# Verify cluster access
kubectl cluster-info

# Check available storage classes
kubectl get storageclass

# Check GPU nodes (if using GPU)
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu

# Create namespace
kubectl create namespace vllm-benchmark
```

## Deployment Scenarios

### Scenario 1: Development and Testing

Quick deployment for development with small models.

```bash
# Deploy lightweight baseline configuration
helm install vllm-dev ./helm/vllm \
  --set vllm.model="Qwen/Qwen2.5-0.5B" \
  --set resources.limits.memory="8Gi" \
  --set resources.requests.memory="4Gi" \
  --set storage.size="20Gi" \
  --set route.enabled=true \
  -n vllm-benchmark

# Verify deployment
kubectl get pods -n vllm-benchmark
kubectl get routes -n vllm-benchmark  # OpenShift
kubectl get ingress -n vllm-benchmark # Kubernetes
```

### Scenario 2: Performance Benchmarking

Deploy multiple configurations for comparison.

```bash
# Create dedicated namespace
kubectl create namespace vllm-benchmark

# Deploy baseline configuration
helm install vllm-baseline ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  -n vllm-benchmark

# Deploy prefix caching configuration
helm install vllm-prefix-cache ./helm/vllm \
  -f ./helm/vllm/values-prefix-cache.yaml \
  -n vllm-benchmark

# Deploy chunked prefill configuration
helm install vllm-chunked-prefill ./helm/vllm \
  -f ./helm/vllm/values-chunked-prefill.yaml \
  -n vllm-benchmark

# Deploy continuous batching configuration
helm install vllm-continuous-batch ./helm/vllm \
  -f ./helm/vllm/values-continuous-batch.yaml \
  -n vllm-benchmark

# Check all deployments
kubectl get pods -n vllm-benchmark
kubectl get routes -n vllm-benchmark
```

### Scenario 3: Production Deployment

Production-ready deployment with monitoring and high availability.

```bash
# Set HuggingFace token for gated models
export HF_TOKEN="hf_your_token_here"

# Create production namespace
kubectl create namespace vllm-production

# Deploy production configuration
helm install vllm-production ./helm/vllm \
  -f ./helm/vllm/values-production.yaml \
  --set huggingface.token="$HF_TOKEN" \
  --set monitoring.serviceMonitor.enabled=true \
  --set podDisruptionBudget.enabled=true \
  -n vllm-production

# Verify production deployment
kubectl get pods -n vllm-production -w
```

## Step-by-Step Deployment

### Step 1: Choose Configuration

Select the appropriate values file based on your needs:

```bash
# List available configurations
ls ./helm/vllm/values-*.yaml

# Preview configuration
cat ./helm/vllm/values-baseline.yaml
```

### Step 2: Customize Configuration (Optional)

Create a custom values file or override specific values:

```bash
# Create custom values file
cat > custom-values.yaml << EOF
nameOverride: "my-vllm"
vllm:
  model: "microsoft/DialoGPT-medium"
  port: 8000
resources:
  limits:
    memory: "16Gi"
route:
  enabled: true
  host: "my-vllm.apps.cluster.com"
EOF
```

### Step 3: Deploy

```bash
# Deploy with predefined values file
helm install my-vllm ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  -n vllm-benchmark

# Or deploy with custom values
helm install my-vllm ./helm/vllm \
  -f custom-values.yaml \
  -n vllm-benchmark

# Or deploy with command-line overrides
helm install my-vllm ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  --set vllm.model="your/model" \
  --set resources.limits.memory="32Gi" \
  -n vllm-benchmark
```

### Step 4: Verify Deployment

```bash
# Check pod status
kubectl get pods -n vllm-benchmark

# Check pod logs
kubectl logs -f deployment/my-vllm -n vllm-benchmark

# Check services and routes
kubectl get svc -n vllm-benchmark
kubectl get routes -n vllm-benchmark  # OpenShift

# Test health endpoint
curl -k https://$(kubectl get route my-vllm -n vllm-benchmark -o jsonpath='{.spec.host}')/health
```

## Configuration Management

### Environment-Specific Deployments

Deploy different configurations for different environments:

```bash
# Development
helm install vllm-dev ./helm/vllm \
  --set vllm.model="Qwen/Qwen2.5-0.5B" \
  --set resources.limits.memory="8Gi" \
  -n vllm-dev

# Staging
helm install vllm-staging ./helm/vllm \
  -f ./helm/vllm/values-prefix-cache.yaml \
  --set resources.limits.memory="24Gi" \
  -n vllm-staging

# Production
helm install vllm-prod ./helm/vllm \
  -f ./helm/vllm/values-production.yaml \
  --set huggingface.token="$HF_TOKEN" \
  -n vllm-production
```

### GitOps Integration

For GitOps workflows with ArgoCD or Flux:

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: vllm-baseline
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/vllm-benchmark
    targetRevision: HEAD
    path: helm/vllm
    helm:
      valueFiles:
        - values-baseline.yaml
      parameters:
        - name: huggingface.token
          value: "$HF_TOKEN"
  destination:
    server: https://kubernetes.default.svc
    namespace: vllm-benchmark
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## GPU Configuration

### Single GPU Setup

```bash
# Deploy with GPU support
helm install vllm-gpu ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  --set resources.limits.nvidia\.com/gpu=1 \
  --set resources.requests.nvidia\.com/gpu=1 \
  --set nodeSelector.nvidia\.com/gpu\.present="true" \
  -n vllm-benchmark
```

### Multi-GPU Setup

```bash
# Deploy tensor parallel configuration
helm install vllm-tensor-parallel ./helm/vllm \
  -f ./helm/vllm/values-tensor-parallel.yaml \
  -n vllm-benchmark

# Verify GPU allocation
kubectl describe pod -l app.kubernetes.io/name=vllm -n vllm-benchmark | grep -A 5 -B 5 "nvidia.com/gpu"
```

## Monitoring Setup

### Enable Prometheus Monitoring

```bash
# Deploy with monitoring enabled
helm install vllm-monitored ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  --set monitoring.enabled=true \
  --set monitoring.serviceMonitor.enabled=true \
  -n vllm-benchmark

# Verify metrics endpoint
kubectl port-forward svc/vllm-monitored 8000:8000 -n vllm-benchmark &
curl http://localhost:8000/metrics
```

### ServiceMonitor Configuration

```yaml
# Enable ServiceMonitor with custom labels
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      team: ai-platform
      environment: production
    interval: 30s
    scrapeTimeout: 10s
```

## High Availability

### Pod Disruption Budget

```bash
# Deploy with PDB enabled
helm install vllm-ha ./helm/vllm \
  -f ./helm/vllm/values-production.yaml \
  --set podDisruptionBudget.enabled=true \
  --set podDisruptionBudget.maxUnavailable=1 \
  -n vllm-production
```

### Multi-Zone Deployment

```yaml
# Anti-affinity configuration
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/name: vllm
        topologyKey: topology.kubernetes.io/zone
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Pod Stuck in Pending

```bash
# Check resource constraints
kubectl describe pod -l app.kubernetes.io/name=vllm -n vllm-benchmark

# Check node availability
kubectl get nodes -o wide

# Check PVC status
kubectl get pvc -n vllm-benchmark
```

#### 2. Model Download Issues

```bash
# Check HuggingFace token
kubectl get secret -n vllm-benchmark
kubectl describe secret vllm-baseline-hf-token -n vllm-benchmark

# Check pod logs for download errors
kubectl logs -f deployment/vllm-baseline -n vllm-benchmark
```

#### 3. Out of Memory Errors

```bash
# Check memory usage
kubectl top pods -n vllm-benchmark

# Increase memory limits
helm upgrade vllm-baseline ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  --set resources.limits.memory="32Gi" \
  -n vllm-benchmark
```

#### 4. Route/Ingress Issues

```bash
# Check route status (OpenShift)
oc get routes -n vllm-benchmark
oc describe route vllm-baseline -n vllm-benchmark

# Test connectivity
curl -k https://$(oc get route vllm-baseline -n vllm-benchmark -o jsonpath='{.spec.host}')/health
```

### Debug Commands

```bash
# Comprehensive status check
kubectl get all -n vllm-benchmark

# Pod diagnostics
kubectl describe pod -l app.kubernetes.io/name=vllm -n vllm-benchmark
kubectl logs -f deployment/vllm-baseline -n vllm-benchmark --previous

# Resource usage
kubectl top pods -n vllm-benchmark
kubectl top nodes

# Storage diagnostics
kubectl get pvc -n vllm-benchmark
kubectl describe pvc -n vllm-benchmark

# Network diagnostics
kubectl get svc,routes,ingress -n vllm-benchmark
```

## Scaling Operations

### Horizontal Scaling

```bash
# Scale deployment
kubectl scale deployment vllm-baseline --replicas=3 -n vllm-benchmark

# Or via Helm upgrade
helm upgrade vllm-baseline ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  --set replicaCount=3 \
  -n vllm-benchmark
```

### Vertical Scaling

```bash
# Increase resources
helm upgrade vllm-baseline ./helm/vllm \
  -f ./helm/vllm/values-baseline.yaml \
  --set resources.limits.memory="48Gi" \
  --set resources.limits.cpu="8" \
  -n vllm-benchmark
```

## Backup and Recovery

### Configuration Backup

```bash
# Backup Helm values
helm get values vllm-baseline -n vllm-benchmark > vllm-baseline-backup.yaml

# Backup Kubernetes resources
kubectl get all,pvc,secrets,routes -n vllm-benchmark -o yaml > vllm-benchmark-backup.yaml
```

### Disaster Recovery

```bash
# Restore from backup
helm install vllm-baseline ./helm/vllm \
  -f vllm-baseline-backup.yaml \
  -n vllm-benchmark

# Verify restoration
kubectl get pods -n vllm-benchmark -w
```

## Performance Tuning

### Model-Specific Optimizations

```bash
# Small models (< 1B parameters)
helm install vllm-small ./helm/vllm \
  --set vllm.model="Qwen/Qwen2.5-0.5B" \
  --set resources.limits.memory="16Gi" \
  --set storage.size="20Gi" \
  -n vllm-benchmark

# Large models (> 7B parameters)
helm install vllm-large ./helm/vllm \
  --set vllm.model="meta-llama/Meta-Llama-3.1-8B-Instruct" \
  --set resources.limits.memory="64Gi" \
  --set resources.limits.nvidia\.com/gpu=2 \
  --set storage.size="200Gi" \
  -n vllm-benchmark
```

### Optimization-Specific Tuning

```bash
# Prefix caching optimization
helm install vllm-prefix ./helm/vllm \
  -f ./helm/vllm/values-prefix-cache.yaml \
  --set vllm.args[4]="--gpu-memory-utilization=0.8" \
  -n vllm-benchmark

# Throughput optimization
helm install vllm-throughput ./helm/vllm \
  -f ./helm/vllm/values-continuous-batch.yaml \
  --set vllm.args[4]="--max-num-seqs=512" \
  -n vllm-benchmark
```

## Cleanup

### Remove Single Configuration

```bash
# Uninstall specific deployment
helm uninstall vllm-baseline -n vllm-benchmark

# Clean up PVCs (if needed)
kubectl delete pvc -l app.kubernetes.io/instance=vllm-baseline -n vllm-benchmark
```

### Remove All Configurations

```bash
# List all Helm releases
helm list -n vllm-benchmark

# Uninstall all releases
helm list -n vllm-benchmark -q | xargs -I {} helm uninstall {} -n vllm-benchmark

# Delete namespace
kubectl delete namespace vllm-benchmark
```

## Next Steps

After deployment:

1. **Test connectivity**: Verify all endpoints are accessible
2. **Run benchmarks**: Use the vLLM benchmark tool to test performance
3. **Set up monitoring**: Configure Prometheus/Grafana dashboards
4. **Documentation**: Document your specific configurations and optimizations
5. **Automation**: Set up CI/CD pipelines for automated deployments

For benchmark testing, see the updated examples in the `examples/` directory.
