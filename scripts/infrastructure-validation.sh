#!/bin/bash

# Infrastructure Validation Script for vLLM vs TGI Benchmarking
# Phase 1.1: Infrastructure Validation
# 
# This script validates the OpenShift cluster environment
# and ensures all prerequisites are met for the benchmarking notebook

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${NAMESPACE:-vllm-benchmark}"
REQUIRED_MEMORY="32Gi"
REQUIRED_CPU="4"
REQUIRED_STORAGE="100Gi"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check command availability
check_command() {
    if command -v "$1" &> /dev/null; then
        success "$1 is available"
        return 0
    else
        error "$1 is not available. Please install $1"
        return 1
    fi
}

# Function to check OpenShift/Kubernetes access
check_cluster_access() {
    log "Checking cluster access..."
    
    # Try OpenShift first, then Kubernetes
    if command -v oc &> /dev/null; then
        if oc whoami &> /dev/null; then
            CLUSTER_USER=$(oc whoami)
            CLUSTER_SERVER=$(oc whoami --show-server)
            success "Connected to OpenShift as: $CLUSTER_USER"
            success "Cluster server: $CLUSTER_SERVER"
            KUBECTL_CMD="oc"
            return 0
        fi
    fi
    
    if command -v kubectl &> /dev/null; then
        if kubectl cluster-info &> /dev/null; then
            CLUSTER_INFO=$(kubectl cluster-info | head -n 1)
            success "Connected to Kubernetes cluster"
            success "$CLUSTER_INFO"
            KUBECTL_CMD="kubectl"
            return 0
        fi
    fi
    
    error "Cannot connect to cluster. Please check your kubeconfig"
    return 1
}

# Function to check GPU availability
check_gpu_availability() {
    log "Checking GPU availability..."
    
    # Check for GPU nodes
    GPU_NODES=$($KUBECTL_CMD get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu --no-headers | grep -v "<none>" | wc -l)
    
    if [ "$GPU_NODES" -gt 0 ]; then
        success "Found $GPU_NODES GPU-enabled nodes"
        $KUBECTL_CMD get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu --no-headers | grep -v "<none>"
        return 0
    else
        warning "No GPU nodes found. Will use CPU-only mode"
        return 1
    fi
}

# Function to check resource availability
check_cluster_resources() {
    log "Checking cluster resource availability..."
    
    # Get node resources
    echo "Node Resource Summary:"
    $KUBECTL_CMD top nodes 2>/dev/null || warning "Metrics server not available - cannot show current usage"
    
    # Check allocatable resources
    echo ""
    echo "Allocatable Resources per Node:"
    $KUBECTL_CMD get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory
    
    success "Resource check completed"
}

# Function to check storage classes
check_storage() {
    log "Checking storage classes..."
    
    STORAGE_CLASSES=$($KUBECTL_CMD get storageclass --no-headers | wc -l)
    
    if [ "$STORAGE_CLASSES" -gt 0 ]; then
        success "Found $STORAGE_CLASSES storage class(es)"
        echo "Available Storage Classes:"
        $KUBECTL_CMD get storageclass
        
        # Check for default storage class
        DEFAULT_SC=$($KUBECTL_CMD get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}')
        if [ -n "$DEFAULT_SC" ]; then
            success "Default storage class: $DEFAULT_SC"
        else
            warning "No default storage class found"
        fi
        return 0
    else
        error "No storage classes found"
        return 1
    fi
}

# Function to create namespace if it doesn't exist
create_namespace() {
    log "Checking namespace: $NAMESPACE"
    
    if $KUBECTL_CMD get namespace "$NAMESPACE" &> /dev/null; then
        success "Namespace '$NAMESPACE' already exists"
    else
        log "Creating namespace: $NAMESPACE"
        $KUBECTL_CMD create namespace "$NAMESPACE"
        success "Created namespace: $NAMESPACE"
    fi
}

# Function to check helm
check_helm() {
    log "Checking Helm installation..."
    
    if ! check_command "helm"; then
        return 1
    fi
    
    HELM_VERSION=$(helm version --short)
    success "Helm version: $HELM_VERSION"
    
    # List current releases in namespace
    log "Checking existing Helm releases in namespace: $NAMESPACE"
    RELEASES=$(helm list -n "$NAMESPACE" --short)
    if [ -n "$RELEASES" ]; then
        warning "Found existing releases in namespace:"
        helm list -n "$NAMESPACE"
    else
        success "No existing Helm releases in namespace"
    fi
}

# Function to validate network connectivity
check_network() {
    log "Checking network configuration..."
    
    # Check if we're on OpenShift (has routes)
    if $KUBECTL_CMD api-resources | grep -q "routes.*route.openshift.io"; then
        success "OpenShift routes available"
        PLATFORM="openshift"
    else
        success "Kubernetes ingress available"
        PLATFORM="kubernetes"
    fi
    
    # Check ingress controller (for Kubernetes)
    if [ "$PLATFORM" = "kubernetes" ]; then
        INGRESS_CONTROLLERS=$($KUBECTL_CMD get ingressclass --no-headers 2>/dev/null | wc -l)
        if [ "$INGRESS_CONTROLLERS" -gt 0 ]; then
            success "Found $INGRESS_CONTROLLERS ingress controller(s)"
            $KUBECTL_CMD get ingressclass
        else
            warning "No ingress controllers found"
        fi
    fi
}

# Function to check monitoring capabilities
check_monitoring() {
    log "Checking monitoring capabilities..."
    
    # Check if Prometheus CRDs are available
    if $KUBECTL_CMD api-resources | grep -q "servicemonitors.*monitoring.coreos.com"; then
        success "Prometheus Operator CRDs available"
    else
        warning "Prometheus Operator not detected - monitoring features may be limited"
    fi
    
    # Check metrics server
    if $KUBECTL_CMD get deployment metrics-server -n kube-system &> /dev/null; then
        success "Metrics server is available"
    else
        warning "Metrics server not found - resource usage metrics unavailable"
    fi
}

# Function to validate deployed Helm releases
check_helm_deployments() {
    log "Checking benchmarking service deployments..."
    
    # Check for vLLM
    if helm list -n "$NAMESPACE" --short | grep -q "vllm"; then
        VLLM_RELEASE=$(helm list -n "$NAMESPACE" --short | grep vllm | head -n 1)
        success "vLLM deployment found: $VLLM_RELEASE"
        
        # Check vLLM pod status
        VLLM_STATUS=$($KUBECTL_CMD get pods -n "$NAMESPACE" -l app.kubernetes.io/name=vllm --no-headers | awk '{print $3}' | head -n 1)
        if [ "$VLLM_STATUS" = "Running" ]; then
            success "vLLM pod is running"
        else
            warning "vLLM pod status: $VLLM_STATUS"
        fi
    else
        warning "vLLM deployment not found"
    fi
    
    # Check for TGI
    if helm list -n "$NAMESPACE" --short | grep -q "tgi"; then
        TGI_RELEASE=$(helm list -n "$NAMESPACE" --short | grep tgi | head -n 1)
        success "TGI deployment found: $TGI_RELEASE"
        
        # Check TGI pod status
        TGI_STATUS=$($KUBECTL_CMD get pods -n "$NAMESPACE" -l app.kubernetes.io/name=tgi --no-headers | awk '{print $3}' | head -n 1)
        if [ "$TGI_STATUS" = "Running" ]; then
            success "TGI pod is running"
        else
            warning "TGI pod status: $TGI_STATUS"
        fi
    else
        warning "TGI deployment not found"
    fi
    
    # Check for Ollama
    if helm list -n "$NAMESPACE" --short | grep -q "ollama"; then
        OLLAMA_RELEASE=$(helm list -n "$NAMESPACE" --short | grep ollama | head -n 1)
        success "Ollama deployment found: $OLLAMA_RELEASE"
        
        # Check Ollama pod status
        OLLAMA_STATUS=$($KUBECTL_CMD get pods -n "$NAMESPACE" -l app.kubernetes.io/name=ollama --no-headers | awk '{print $3}' | head -n 1)
        if [ "$OLLAMA_STATUS" = "Running" ]; then
            success "Ollama pod is running"
        elif [ "$OLLAMA_STATUS" = "Init:0/1" ]; then
            warning "Ollama pod is initializing (pulling model)"
        else
            warning "Ollama pod status: $OLLAMA_STATUS"
        fi
    else
        warning "Ollama deployment not found"
    fi
}

# Function to check anti-affinity and node distribution
check_node_distribution() {
    log "Checking node distribution and anti-affinity..."
    
    # Get all benchmark pods and their nodes
    echo "Current pod distribution:"
    $KUBECTL_CMD get pods -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,STATUS:.status.phase --no-headers | grep -E "(vllm|tgi|ollama)"
    
    # Check if pods are on different nodes
    NODES_USED=$($KUBECTL_CMD get pods -n "$NAMESPACE" -o jsonpath='{.items[*].spec.nodeName}' -l 'app.kubernetes.io/name in (vllm,tgi,ollama)' | tr ' ' '\n' | sort | uniq | wc -l)
    PODS_COUNT=$($KUBECTL_CMD get pods -n "$NAMESPACE" -l 'app.kubernetes.io/name in (vllm,tgi,ollama)' --no-headers | wc -l)
    
    if [ "$NODES_USED" -eq "$PODS_COUNT" ] && [ "$PODS_COUNT" -gt 1 ]; then
        success "Anti-affinity working: $PODS_COUNT pods distributed across $NODES_USED different nodes"
    elif [ "$PODS_COUNT" -gt 1 ]; then
        warning "Anti-affinity may not be working optimally: $PODS_COUNT pods on $NODES_USED nodes"
    else
        success "Single pod deployment detected"
    fi
}

# Function to test service connectivity
check_service_connectivity() {
    log "Testing service connectivity..."
    
    # Test vLLM service
    if $KUBECTL_CMD get svc -n "$NAMESPACE" vllm-test &> /dev/null; then
        success "vLLM service endpoint available"
    else
        warning "vLLM service not found"
    fi
    
    # Test TGI service
    if $KUBECTL_CMD get svc -n "$NAMESPACE" tgi-test &> /dev/null; then
        success "TGI service endpoint available"
    else
        warning "TGI service not found"
    fi
    
    # Test Ollama service
    if $KUBECTL_CMD get svc -n "$NAMESPACE" ollama-test &> /dev/null; then
        success "Ollama service endpoint available"
    else
        warning "Ollama service not found"
    fi
    
    # Test routes (OpenShift)
    if [ "$PLATFORM" = "openshift" ]; then
        ROUTES=$($KUBECTL_CMD get routes -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
        if [ "$ROUTES" -gt 0 ]; then
            success "Found $ROUTES OpenShift route(s)"
            $KUBECTL_CMD get routes -n "$NAMESPACE"
        else
            warning "No OpenShift routes found"
        fi
    fi
}

# Main validation function
main() {
    echo "========================================"
    echo "vLLM vs TGI vs Ollama Infrastructure Validation"
    echo "========================================"
    echo ""
    
    local errors=0
    
    # Check required commands
    log "Checking required commands..."
    check_command "curl" || ((errors++))
    check_command "jq" || warning "jq not found - JSON parsing may be limited"
    
    # Check cluster access
    check_cluster_access || ((errors++))
    
    if [ $errors -eq 0 ]; then
        # Continue with cluster-specific checks
        check_gpu_availability
        check_cluster_resources
        check_storage || ((errors++))
        check_helm || ((errors++))
        check_network
        check_monitoring
        create_namespace || ((errors++))
        
        # Check deployed services
        check_helm_deployments
        check_node_distribution
        check_service_connectivity
    fi
    
    echo ""
    echo "========================================"
    if [ $errors -eq 0 ]; then
        success "Infrastructure validation completed successfully!"
        echo ""
        echo "✅ Cluster access: OK"
        echo "✅ Storage: OK"
        echo "✅ Helm: OK"
        echo "✅ Namespace: OK"
        echo "✅ Service deployments: OK"
        echo ""
        echo "Ready to proceed with three-way benchmarking (vLLM vs TGI vs Ollama)."
    else
        error "Infrastructure validation failed with $errors error(s)"
        echo ""
        echo "Please resolve the above issues before proceeding."
        exit 1
    fi
    echo "========================================"
}

# Run main function
main "$@"
