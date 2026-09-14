#!/bin/sh
# Exec check for the `package` step: the contribution must validate and address the gated task.
set -eu
TASK="${RCP_TASK_FILE:-rcp/task.jsonld}"
CONTRIBUTION="${RCP_CONTRIBUTION_FILE:-rcp/contribution.jsonld}"
MANIFEST="${RCP_MANIFEST:?set RCP_MANIFEST to the trusted contract manifest}"
research-commons validate-structure "$CONTRIBUTION" >/dev/null
research-commons validate-shacl "$CONTRIBUTION" >/dev/null
python3 - "$TASK" "$CONTRIBUTION" <<'PY'
import json, sys
task, contribution = (json.load(open(path)) for path in sys.argv[1:3])
if contribution.get("addresses") != task["@id"]:
    sys.exit("contribution does not address the gated task")
PY
research-commons check-contribution "$CONTRIBUTION" --manifest "$MANIFEST" ${RCP_KM_BIN:+--km-bin "$RCP_KM_BIN"} >/dev/null
