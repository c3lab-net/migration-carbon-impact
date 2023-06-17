#!/bin/bash

cd "$(dirname "$0")" || exit 1

set -e
set -o pipefail

action="${1:-"create"}"
name="${2:-"ycsb-b"}"
parallelism="${3:-"1"}"

# set -x
cat ./cockroach-workload.yaml | ./substitute-vars.sh "$name" "$parallelism" | kubectl $action -f -
