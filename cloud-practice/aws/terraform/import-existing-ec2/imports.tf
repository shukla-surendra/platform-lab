##############################################################################
# Import blocks (Terraform >= 1.5). Two resources here, two blocks -- see
# README "One import block per resource" for why a single instance's worth
# of manually-created infra almost never means a single import block.
#
# Workflow (full detail in README.md):
#   1. terraform plan -generate-config-out=generated.tf
#      -> drafts resource blocks for both targets below from live AWS state
#   2. clean up generated.tf, merge into main.tf, delete generated.tf
#   3. terraform plan   (expect "No changes", or fix main.tf until it is)
#   4. terraform apply  (THIS writes the resources into state)
##############################################################################

import {
  to = aws_security_group.imported
  id = var.security_group_id
}

import {
  to = aws_instance.imported
  id = var.instance_id
}

# Elastic IP import id is the ALLOCATION id (eipalloc-...), not the public
# IP string itself and not the association id.
import {
  to = aws_eip.imported
  id = var.eip_allocation_id
}
