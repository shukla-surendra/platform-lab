ENV ?= dev
DIR  = envs/$(ENV)

.PHONY: fmt validate init plan apply destroy validate-all
fmt:           ; terraform fmt -recursive
init:          ; terraform -chdir=$(DIR) init
plan: init     ; terraform -chdir=$(DIR) plan -out=tfplan
apply:         ; terraform -chdir=$(DIR) apply tfplan
destroy:       ; terraform -chdir=$(DIR) destroy
# Offline check of every env (no AWS creds / backend needed)
validate-all:
	@for e in dev qa stage prod; do \
	  echo "== $$e"; terraform -chdir=envs/$$e init -backend=false -input=false >/dev/null && \
	  terraform -chdir=envs/$$e validate || exit 1; done
