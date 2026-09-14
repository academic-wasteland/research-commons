#!/bin/sh
# Doctor check: RCP tooling reachable from this rig.
set -eu
status=0
for tool in research-commons bd; do
  if command -v "$tool" >/dev/null 2>&1; then echo "$tool available"; else echo "$tool not found"; status=2; fi
done
if command -v km >/dev/null 2>&1; then echo "km available"; else echo "km not found: semantic checks will return indeterminate"; fi
if command -v dolt >/dev/null 2>&1; then echo "dolt available"; else echo "dolt not found: Wasteland publication disabled"; fi
exit $status
