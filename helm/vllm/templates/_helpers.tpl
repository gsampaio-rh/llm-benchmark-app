{{/*
Expand the name of the chart.
*/}}
{{- define "vllm.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "vllm.fullname" -}}
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
{{- define "vllm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "vllm.labels" -}}
helm.sh/chart: {{ include "vllm.chart" . }}
{{ include "vllm.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Values.config.name }}
vllm.config/name: {{ .Values.config.name }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "vllm.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vllm.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "vllm.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "vllm.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the namespace name
*/}}
{{- define "vllm.namespace" -}}
{{- default .Release.Namespace .Values.namespace }}
{{- end }}

{{/*
Generate the vLLM server arguments
*/}}
{{- define "vllm.serverArgs" -}}
{{- range .Values.vllm.args }}
- {{ tpl . $ | quote }}
{{- end }}
{{- end }}

{{/*
Generate resource limits and requests
*/}}
{{- define "vllm.resources" -}}
{{- if .Values.resources }}
{{- toYaml .Values.resources }}
{{- end }}
{{- end }}

{{/*
Generate volume mounts
*/}}
{{- define "vllm.volumeMounts" -}}
- name: model-cache
  mountPath: /models
- name: dshm
  mountPath: /dev/shm
{{- if .Values.vllm.additionalVolumeMounts }}
{{- toYaml .Values.vllm.additionalVolumeMounts }}
{{- end }}
{{- end }}

{{/*
Generate volumes
*/}}
{{- define "vllm.volumes" -}}
- name: model-cache
  persistentVolumeClaim:
    claimName: {{ include "vllm.fullname" . }}-cache
- name: dshm
  emptyDir:
    medium: Memory
    sizeLimit: {{ .Values.storage.shmSize | default "2Gi" }}
{{- if .Values.vllm.additionalVolumes }}
{{- toYaml .Values.vllm.additionalVolumes }}
{{- end }}
{{- end }}
