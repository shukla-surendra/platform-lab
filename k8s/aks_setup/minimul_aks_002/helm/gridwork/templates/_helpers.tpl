{{/*
Release-scoped resource name prefix, e.g. "personal-assistant".
*/}}
{{- define "pa.fullname" -}}
{{- .Release.Name -}}
{{- end -}}

{{/*
Common labels applied to every resource this chart creates.
*/}}
{{- define "pa.labels" -}}
app.kubernetes.io/part-of: personal-assistant
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}
