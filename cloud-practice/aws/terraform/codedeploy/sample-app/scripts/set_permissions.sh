#!/bin/bash
# AfterInstall: fix ownership on the files CodeDeploy just copied in.
chown -R apache:apache /var/www/html
