#!/usr/bin/env bash
#
# Demonstrates 06-scripting-basics.md: variables, double-quoting,
# command substitution, arithmetic, and $1/$#.
#
# Usage: ./06_hello.sh [name]

name="${1:-world}"
today=$(date +%F)
count=$#
echo "Hello, $name — today is $today, you passed $count argument(s)"
