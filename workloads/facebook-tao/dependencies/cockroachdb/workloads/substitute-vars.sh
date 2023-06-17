#!/usr/bin/env -S -i bash

[ $# -eq 2 ] || { echo >&2 "Usage: $0 name parallelism"; exit 2; }

export name="$1"
export parallelism="$2"

row=$(grep -E "^$name," cockroach-workloads.csv)

[ -z "$row" ] && { echo >&2 "Workload $name not defined. Aborting ..."; exit 2; }

export timestamp="$(date --utc +%Y%m%d_%H%M%SZ)"
export workload=$(echo "$row" | cut -f 2 -d ',')
export init_args=$(echo "$row" | cut -f 3 -d ',')
export run_args=$(echo "$row" | cut -f 4 -d ',')

# echo >&2 $workload $parallelism $timestamp $init_args $run_args
envsubst '$name $workload $parallelism $timestamp $init_args $run_args'
