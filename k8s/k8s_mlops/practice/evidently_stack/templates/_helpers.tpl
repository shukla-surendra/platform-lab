{{- define "evidently-stack.evidently-server.fullname" -}}
{{ .Release.Name }}-evidently-server
{{- end }}

{{- define "evidently-stack.jupyter-client.fullname" -}}
{{ .Release.Name }}-jupyter-client
{{- end }}

{{- define "evidently-stack.labels" -}}
app.kubernetes.io/part-of: evidently-stack
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
