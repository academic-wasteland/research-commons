#!/bin/sh
# gc rcp to-bead <document.jsonld>...  : validate and import RCP messages as beads in this rig
set -eu
[ $# -ge 1 ] || { echo "usage: gc rcp to-bead <document.jsonld>..." >&2; exit 64; }
research-commons to-bead --prefix "${GC_BEADS_PREFIX:-rcp}" "$@" | bd import -
