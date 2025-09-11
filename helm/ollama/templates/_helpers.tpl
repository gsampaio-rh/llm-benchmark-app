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
      export OLLAMA_HOST=0.0.0.0:11434
      ollama serve &
      OLLAMA_PID=$!
      
      # Enhanced readiness check with timeout
      echo "Waiting for Ollama server to be ready..."
      TIMEOUT=300  # 5 minutes timeout
      ELAPSED=0
      until ollama list &> /dev/null; do
        if [ $ELAPSED -ge $TIMEOUT ]; then
          echo "ERROR: Ollama server failed to start within $TIMEOUT seconds"
          kill $OLLAMA_PID || true
          exit 1
        fi
        echo "Waiting for Ollama server... (${ELAPSED}s elapsed)"
        sleep 5
        ELAPSED=$((ELAPSED + 5))
      done
      
      echo "Ollama server is ready! Pulling models..."
      
      # Pull primary model with error handling
      echo "Pulling primary model: {{ .Values.ollama.model }}"
      if ! ollama pull {{ .Values.ollama.model }}; then
        echo "ERROR: Failed to pull primary model {{ .Values.ollama.model }}"
        kill $OLLAMA_PID || true
        exit 1
      fi
      echo "Successfully pulled primary model: {{ .Values.ollama.model }}"
      
      {{- range .Values.ollama.modelPull.additionalModels }}
      # Pull additional model with error handling
      echo "Pulling additional model: {{ . }}"
      if ! ollama pull {{ . }}; then
        echo "WARNING: Failed to pull additional model {{ . }}, continuing..."
      else
        echo "Successfully pulled additional model: {{ . }}"
      fi
      {{- end }}
      
      # Verify models are available
      echo "Verifying pulled models..."
      ollama list
      
      echo "Model pull completed. Stopping Ollama server..."
      kill $OLLAMA_PID || true
      wait $OLLAMA_PID || true
      
      echo "=== Models ready! Init container completed successfully ==="
  env:
    {{- range .Values.ollama.env }}
    - name: {{ .name }}
      value: {{ .value | quote }}
    {{- end }}
    # Override for init container to ensure proper binding
    - name: OLLAMA_HOST
      value: "0.0.0.0:11434"
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
{{- end }}
{{- end }}
