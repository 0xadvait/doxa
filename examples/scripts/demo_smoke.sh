#!/usr/bin/env bash
set -euo pipefail

DOXA_BIN="${DOXA_BIN:-doxa}"

"$DOXA_BIN" demo
"$DOXA_BIN" query "self-reliance and conformity" --top 2
"$DOXA_BIN" query "examined life" --answer
"$DOXA_BIN" eval --config examples/demo/doxa.yaml
