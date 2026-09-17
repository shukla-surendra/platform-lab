#!/usr/bin/env bash
#
# Demonstrates 10-error-handling-and-debugging.md: what `set -euo
# pipefail` actually catches. Safe to run — nothing here deletes
# anything; the "rm -rf" danger is shown with an intentionally-guarded
# command, not a real unguarded one.

echo "=== without 'set -u': an unset variable is silently empty ==="
bash -c '
unset missing_var
echo "value: [$missing_var]"
echo "this line still runs even though the variable was unset"
'

echo
echo "=== with 'set -u': referencing it is a hard error ==="
bash -c '
set -u
unset missing_var
echo "value: [$missing_var]"
echo "this line never runs"
' || echo "(caught: exited nonzero because of the unset variable, as expected)"

echo
echo "=== the unquoted rm danger ==="
echo "if \$dir is empty and unquoted: rm -rf \$dir/*  ->  can become rm -rf /*"
echo "the safe version quotes AND requires a value:  rm -rf \"\${dir:?dir must be set}\"/*"
bash -c 'dir=""; rm -rf "${dir:?dir must be set}"/*' 2>&1 \
  || echo "(caught: bash refused because \$dir was empty, as expected)"

echo
echo "=== pipefail ==="
set -o pipefail
false | true
echo "with pipefail:    'false | true' exit code = $?"
set +o pipefail
false | true
echo "without pipefail: 'false | true' exit code = $?"
