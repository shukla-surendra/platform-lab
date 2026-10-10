ENV ?= dev

.PHONY: fmt init ws plan apply destroy validate-all
fmt:  ; terraform fmt -recursive
init: ; terraform init
# select the workspace, creating it on first use
ws: init
	terraform workspace select $(ENV) || terraform workspace new $(ENV)
plan: ws
	terraform plan -var-file=vars/$(ENV).tfvars -out=tfplan
apply:
	terraform apply tfplan
destroy: ws
	terraform destroy -var-file=vars/$(ENV).tfvars
validate-all:
	terraform init -backend=false -input=false >/dev/null && terraform validate
