#!/bin/bash

# TODO: split into client and server logs

# TODO: collect detailed CRDB server timestamped metrics

cd "$(dirname "$0")"

set -e

NUM_REGIONS=3

function kn()
{
    region_num="$1"
    shift
    if [ $region_num -eq 0 ]; then
        kubectl --namespace "c3lab" "$@"
    else
        kubectl --namespace "c3lab-region$region_num" "$@"
    fi
}

if [ $NUM_REGIONS -eq 1 ]; then
    function k() { kn 0 "$@"; }
else
    # Client jobs runs in region 2
    function k() { kn 2 "$@"; }
fi

random_name="$(cat /dev/urandom | tr -cd 'a-f0-9' | head -c 6)"
log_dir="$(date +%F).$random_name"

mkdir $log_dir && cd $log_dir

echo "Saving job logs ..."
for jobname in $(k get jobs -o jsonpath="{.items[*].spec.template.metadata.labels['job-name']}"); do
    podname="$(k get pod -l job-name="$jobname" -o jsonpath="{.items[0].metadata.name}")"
    k logs $podname > job.$podname.log
done

echo "Saving CRDB logs ..."
if [ $NUM_REGIONS -eq 1 ]; then
    for podname in $(k get pods -l app=taobench-cockroachdb -o jsonpath="{.items[*].metadata.name}"); do
        k logs $podname > crdb.$podname.log
    done
else
    for n in $(seq 1 $NUM_REGIONS); do
        for podname in $(kn $n get pods -l app=taobench-cockroachdb -o jsonpath="{.items[*].metadata.name}"); do
            kn $n logs $podname > crdb.region$n.$podname.log
        done
    done
fi

echo "Deleting jobs and CRDB deployment ..."
if [ $NUM_REGIONS -eq 1 ]; then
    k delete jobs taobench-app-1-schema-setup taobench-app-2-configure-params taobench-app-3-load-data taobench-app-4-run-experiments
    k delete statefulsets.apps taobench-cockroachdb
    k wait --timeout=-1 job --for=delete -l app=taobench-cockroachdb
    k wait --timeout=-1 pod --for=delete -l app=taobench-cockroachdb
else
    k delete job taobench-cluster-init
    k delete job taobench-app-1-schema-setup taobench-app-2-configure-params taobench-app-3-load-data taobench-app-4-run-experiments
    for n in $(seq 1 $NUM_REGIONS); do
        kn $n delete statefulsets.apps taobench-cockroachdb
    done
    k wait --timeout=-1 job --for=delete -l app=taobench-cockroachdb
    for n in $(seq 1 $NUM_REGIONS); do
        kn $n wait --timeout=-1 pod --for=delete -l app=taobench-cockroachdb
    done
fi