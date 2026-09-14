#!/bin/sh
# Exec check for the `gate` step: passes only when the task validates at every layer.
set -eu
TASK="${RCP_TASK_FILE:-rcp/task.jsonld}"
MANIFEST="${RCP_MANIFEST:?set RCP_MANIFEST to the trusted contract manifest}"
research-commons validate-structure "$TASK" >/dev/null
research-commons validate-shacl "$TASK" >/dev/null
research-commons validate-semantics "$TASK" --manifest "$MANIFEST" ${RCP_KM_BIN:+--km-bin "$RCP_KM_BIN"} > rcp/report.json
python3 -c 'import json,sys; sys.exit(0 if json.load(open("rcp/report.json"))["status"] == "entailed" else 1)'
