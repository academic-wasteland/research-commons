#!/bin/sh
# gc rcp validate <document.jsonld> [--manifest <manifest.json>]
set -eu
[ $# -ge 1 ] || { echo "usage: gc rcp validate <document.jsonld> [--manifest <manifest.json>]" >&2; exit 64; }
DOC="$1"; shift
research-commons validate-structure "$DOC"
research-commons validate-shacl "$DOC"
if [ "${1:-}" = "--manifest" ]; then
  research-commons validate-semantics "$DOC" --manifest "$2"
fi
