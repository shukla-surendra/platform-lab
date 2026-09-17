#!/bin/bash
# BeforeInstall: stop httpd if it's running so the file copy doesn't race a live process.
systemctl stop httpd || true
