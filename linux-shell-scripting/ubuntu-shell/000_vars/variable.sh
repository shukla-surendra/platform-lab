#!/bin/bash



MY_SHELL="bash"
echo "I love $MY_SHELL"

echo "I love ${MY_SHELL}"

# $MY_SHELLing No such variable exists
# it will be ignored unless "set -euo pipefail"
echo "I love $MY_SHELLing"

HOST_NAME="$(hostname)"
echo "I love $HOST_NAME"

HOST_NAME=`hostname` # Older way of command substitution
echo "I love $HOST_NAME"