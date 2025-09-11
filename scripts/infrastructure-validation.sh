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

# Main validation function
main() {
    echo "========================================"
    echo "vLLM vs TGI Infrastructure Validation"
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
        echo ""
        echo "Ready to proceed with Helm chart deployment testing."
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
