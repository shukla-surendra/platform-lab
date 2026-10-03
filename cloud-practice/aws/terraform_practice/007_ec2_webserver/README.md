# 007 – EC2 web server with user_data

Creates a t3.micro Ubuntu instance in the default VPC. `user_data` installs nginx on first boot; a security group opens port 80.

```
terraform init
terraform apply
# wait ~1 min after apply for user_data to finish, then:
curl $(terraform output -raw url)
terraform destroy
```

No SSH key / port 22 is opened — the lesson is only user_data + security group.
