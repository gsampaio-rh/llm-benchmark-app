{{/*
Expand the name of the chart.
*/}}
{{- define "ollama.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ollama.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ollama.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ollama.labels" -}}
helm.sh/chart: {{ include "ollama.chart" . }}
{{ include "ollama.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: inference-server
app.kubernetes.io/part-of: vllm-benchmark
benchmark.ai/competitor: ollama
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ollama.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ollama.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ollama.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ollama.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get the namespace
*/}}
{{- define "ollama.namespace" -}}
{{- if .Values.namespace }}
{{- .Values.namespace }}
{{- else }}
{{- .Release.Namespace }}
{{- end }}
{{- end }}

{{/*
Generate Ollama server arguments
*/}}
{{- define "ollama.serverArgs" -}}
{{- if .Values.ollama.args }}
{{- toYaml .Values.ollama.args }}
{{- else }}
- serve
{{- end }}
{{- end }}

{{/*
Generate init container for model pulling
*/}}
{{- define "ollama.modelPullInitContainer" -}}
{{- if .Values.ollama.modelPull.enabled }}
- name: model-pull
  image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  command:
    - /bin/sh
    - -c
    - |
      set -e
      echo "=== Ollama Model Pull Init Container Starting ==="
      echo "Model to pull: {{ .Values.ollama.model }}"
      {{- range .Values.ollama.modelPull.additionalModels }}
      echo "Additional model: {{ . }}"
      {{- end }}
      
      # Start Ollama server in background
      echo "Starting Ollama server in background..."
      ollama serve &
      OLLAMA_PID=$!
      
      # Function to cleanup on exit
      cleanup() {
        echo "Cleaning up..."
        if [ ! -z "$OLLAMA_PID" ]; then
          kill $OLLAMA_PID 2>/dev/null || true
          wait $OLLAMA_PID 2>/dev/null || true
        fi
      }
      trap cleanup EXIT INT TERM
      
      # Enhanced readiness check with timeout
      echo "Waiting for Ollama server to be ready..."
      TIMEOUT=120  # 2 minutes should be enough for server startup
      ELAPSED=0
      
      # Wait for the server to be responsive
      while ! ollama list > /dev/null 2>&1; do
        if [ $ELAPSED -ge $TIMEOUT ]; then
          echo "ERROR: Ollama server failed to become ready within $TIMEOUT seconds"
          echo "Diagnostics:"
          echo "Process list:"
          ps aux | grep ollama || true
          echo "Port check:"
          netstat -tlnp 2>/dev/null | grep 11434 || ss -tlnp 2>/dev/null | grep 11434 || true
          echo "Environment:"
          env | grep OLLAMA || true
          exit 1
        fi
        echo "Waiting for Ollama server... (${ELAPSED}s elapsed)"
        sleep 3
        ELAPSED=$((ELAPSED + 3))
      done
      
      echo "Ollama server is ready!"
      ollama list || true
      
      echo "Pulling models..."
      
      # Pull primary model with retry logic
      echo "Pulling primary model: {{ .Values.ollama.model }}"
      RETRY_COUNT=0
      MAX_RETRIES=3
      until ollama pull {{ .Values.ollama.model }}; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
          echo "ERROR: Failed to pull primary model {{ .Values.ollama.model }} after $MAX_RETRIES attempts"
          echo "Network diagnostics:"
          echo "DNS resolution test:"
          nslookup registry.ollama.ai || nslookup ollama.com || true
          echo "Connectivity test:"
          curl -v https://registry.ollama.ai 2>&1 || true
          exit 1
        fi
        echo "Retry $RETRY_COUNT/$MAX_RETRIES for {{ .Values.ollama.model }}..."
        sleep 10
      done
      echo "Successfully pulled primary model: {{ .Values.ollama.model }}"
      
      {{- range .Values.ollama.modelPull.additionalModels }}
      # Pull additional model with retry logic
      echo "Pulling additional model: {{ . }}"
      RETRY_COUNT=0
      until ollama pull {{ . }}; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge 2 ]; then
          echo "WARNING: Failed to pull additional model {{ . }} after 2 attempts, continuing..."
          break
        fi
        echo "Retry $RETRY_COUNT for {{ . }}..."
        sleep 10
      done
      {{- end }}
      
      # Verify models are available
      echo "Verifying pulled models..."
      ollama list || true
      
      echo "=== Model pull completed successfully ==="
  env:
    # Critical: Init container must use 127.0.0.1 for localhost server
    - name: OLLAMA_HOST
      value: "127.0.0.1:11434"
    {{- if .Values.ollama.env }}
    {{- range .Values.ollama.env }}
    {{- if ne .name "OLLAMA_HOST" }}
    - name: {{ .name }}
      value: {{ .value | quote }}
    {{- end }}
    {{- end }}
    {{- end }}
    # Ensure we can reach external registries
    - name: HTTPS_PROXY
      value: ""
    - name: HTTP_PROXY
      value: ""
    - name: NO_PROXY
      value: ""
  volumeMounts:
    {{- if .Values.storage.enabled }}
    - name: ollama-storage
      mountPath: /root/.ollama
    {{- else }}
    - name: ollama-data
      mountPath: /root/.ollama
    {{- end }}
    {{- with .Values.ollama.additionalVolumeMounts }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
  resources:
    limits:
      cpu: "4"
      memory: 16Gi
      {{- if .Values.resources.limits }}
      {{- if index .Values.resources.limits "nvidia.com/gpu" }}
      nvidia.com/gpu: {{ index .Values.resources.limits "nvidia.com/gpu" }}
      {{- end }}
      {{- end }}
    requests:
      cpu: "2"
      memory: 8Gi
      {{- if .Values.resources.requests }}
      {{- if index .Values.resources.requests "nvidia.com/gpu" }}
      nvidia.com/gpu: {{ index .Values.resources.requests "nvidia.com/gpu" }}
      {{- end }}
      {{- end }}
  securityContext:
    {{- toYaml .Values.securityContext | nindent 4 }}
{{- end }}
{{- end }}
