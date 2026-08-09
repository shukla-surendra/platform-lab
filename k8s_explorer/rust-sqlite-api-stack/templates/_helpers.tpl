{{- define "rust-sqlite-api-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "rust-sqlite-api-stack.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "rust-sqlite-api-stack.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{ include "rust-sqlite-api-stack.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "rust-sqlite-api-stack.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rust-sqlite-api-stack.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "rust-sqlite-api-stack.image" -}}
{{- printf "%s:%s" .Values.image.repository (default .Chart.AppVersion .Values.image.tag) -}}
{{- end -}}

{{/*
Refuse to render above one replica.

Failing at template time is the point. A silently-accepted replicaCount: 3
produces three pods, three PersistentVolumeClaims, three unrelated databases,
and a Service that load-balances queries across them — so roughly two thirds of
your telemetry appears to vanish, intermittently, with nothing in any log to
explain it. That is far more expensive to diagnose than this error is to read.
*/}}
{{- define "rust-sqlite-api-stack.validateReplicas" -}}
{{- if gt (int .Values.replicaCount) 1 -}}
{{- fail (printf "replicaCount is %d, but rust-sqlite-api cannot be scaled horizontally.\n\nThe database is a SQLite file on each pod's own volume. Extra replicas do not share it, so they do not distribute load — they partition your telemetry across %d disconnected databases and queries return whichever fraction happens to be routed to. Keep replicaCount: 1, or move to a store designed for horizontal scale." (int .Values.replicaCount) (int .Values.replicaCount)) -}}
{{- end -}}
{{- end -}}
