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
      echo "Starting Ollama server in background..."
      ollama serve &
      OLLAMA_PID=$!
      
      echo "Waiting for Ollama server to be ready..."
      until ollama list &> /dev/null; do
        echo "Waiting for Ollama server..."
        sleep 5
      done
      
      echo "Pulling primary model: {{ .Values.ollama.model }}"
      ollama pull {{ .Values.ollama.model }}
      
      {{- range .Values.ollama.modelPull.additionalModels }}
      echo "Pulling additional model: {{ . }}"
      ollama pull {{ . }}
      {{- end }}
      
      echo "Model pull completed. Stopping Ollama server..."
      kill $OLLAMA_PID || true
      wait $OLLAMA_PID || true
      
      echo "Models ready!"
  env:
    {{- toYaml .Values.ollama.env | nindent 4 }}
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
      cpu: "2"
      memory: 8Gi
    requests:
      cpu: "1"
      memory: 4Gi
{{- end }}
{{- end }}
