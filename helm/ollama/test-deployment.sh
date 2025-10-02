#!/bin/bash
# Quick test script for Ollama deployment after fixes

set -e

NAMESPACE="${NAMESPACE:-vllm-benchmark}"
RELEASE_NAME="${RELEASE_NAME:-ollama-test}"

echo "🧪 Testing Ollama Deployment Fix"
echo "================================"
echo "Namespace: $NAMESPACE"
echo "Release: $RELEASE_NAME"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check if namespace exists
echo "Step 1: Checking namespace..."
if kubectl get namespace $NAMESPACE &> /dev/null; then
    print_status 0 "Namespace $NAMESPACE exists"
else
    print_warning "Namespace $NAMESPACE doesn't exist. Create it with:"
    echo "  kubectl create namespace $NAMESPACE"
    exit 1
fi

# 2. Check if release is installed
echo ""
echo "Step 2: Checking Helm release..."
if helm list -n $NAMESPACE | grep -q $RELEASE_NAME; then
    print_status 0 "Release $RELEASE_NAME found"
    echo ""
    echo "To upgrade with fixes:"
    echo "  helm upgrade $RELEASE_NAME ./helm/ollama --namespace $NAMESPACE"
else
    print_warning "Release $RELEASE_NAME not found"
    echo ""
    echo "To install:"
    echo "  helm install $RELEASE_NAME ./helm/ollama --namespace $NAMESPACE"
    exit 0
fi

# 3. Check pod status
echo ""
echo "Step 3: Checking pod status..."
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=ollama -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$POD_NAME" ]; then
    print_warning "No pods found. Deployment may still be creating resources."
    exit 0
fi

echo "Pod: $POD_NAME"
POD_STATUS=$(kubectl get pod -n $NAMESPACE $POD_NAME -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
print_status 0 "Pod status: $POD_STATUS"

# 4. Check init container status
echo ""
echo "Step 4: Checking init container..."
INIT_STATUS=$(kubectl get pod -n $NAMESPACE $POD_NAME -o jsonpath='{.status.initContainerStatuses[0].state}' 2>/dev/null || echo "{}")

if echo "$INIT_STATUS" | grep -q "running"; then
    print_status 0 "Init container is running (pulling models)"
    echo ""
    echo "📋 View init container logs:"
    echo "  kubectl logs -f -n $NAMESPACE $POD_NAME -c model-pull"
elif echo "$INIT_STATUS" | grep -q "terminated"; then
    INIT_EXIT_CODE=$(kubectl get pod -n $NAMESPACE $POD_NAME -o jsonpath='{.status.initContainerStatuses[0].state.terminated.exitCode}' 2>/dev/null || echo "unknown")
    if [ "$INIT_EXIT_CODE" == "0" ]; then
        print_status 0 "Init container completed successfully"
    else
        print_status 1 "Init container failed with exit code: $INIT_EXIT_CODE"
        echo ""
        echo "📋 Check logs:"
        echo "  kubectl logs -n $NAMESPACE $POD_NAME -c model-pull"
    fi
else
    print_warning "Init container status: $INIT_STATUS"
fi

# 5. Check main container
echo ""
echo "Step 5: Checking main container..."
if [ "$POD_STATUS" == "Running" ]; then
    print_status 0 "Main container is running"
    echo ""
    echo "📋 View main container logs:"
    echo "  kubectl logs -f -n $NAMESPACE $POD_NAME -c ollama"
else
    print_warning "Pod not yet running (status: $POD_STATUS)"
fi

# 6. Check service
echo ""
echo "Step 6: Checking service..."
SVC_NAME=$(kubectl get svc -n $NAMESPACE -l app.kubernetes.io/name=ollama -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$SVC_NAME" ]; then
    print_status 0 "Service $SVC_NAME exists"
    SVC_PORT=$(kubectl get svc -n $NAMESPACE $SVC_NAME -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "")
    echo "  Port: $SVC_PORT"
else
    print_warning "Service not found"
fi

# 7. Quick diagnostics if pod is failing
echo ""
if [ "$POD_STATUS" != "Running" ] && [ "$POD_STATUS" != "Pending" ]; then
    echo "Step 7: Running diagnostics..."
    echo ""
    echo "📊 Pod Events:"
    kubectl describe pod -n $NAMESPACE $POD_NAME | grep -A 10 "Events:"
fi

echo ""
echo "================================"
echo "🔍 Useful Commands:"
echo ""
echo "Watch pod status:"
echo "  watch kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=ollama"
echo ""
echo "Get all logs:"
echo "  kubectl logs -n $NAMESPACE $POD_NAME --all-containers"
echo ""
echo "Describe pod:"
echo "  kubectl describe pod -n $NAMESPACE $POD_NAME"
echo ""
echo "Test API (requires port-forward):"
echo "  kubectl port-forward -n $NAMESPACE svc/$SVC_NAME 11434:11434"
echo "  curl http://localhost:11434/api/tags"
echo ""

