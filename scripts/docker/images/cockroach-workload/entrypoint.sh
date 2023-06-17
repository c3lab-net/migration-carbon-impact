#!/bin/bash

check_vars()
{
    name="$1"
    value="${!name}"
    if [ -z "$value" ]; then { echo >&2 "$name is not defined!"; exit 3; } fi
}

check_vars WORKLOAD
check_vars INIT_ARGS
check_vars RUN_ARGS
check_vars CRDB_CONNECTION_STRING
check_vars JOB_COMPLETION_INDEX
check_vars TIMESTAMP
check_vars SLEEP_TIME
check_vars JOB_NAME
check_vars SERVICE_NAME
check_vars NODENAME

JOB_INDEX=$JOB_COMPLETION_INDEX

outfile="/experiments/crdb.workload.$JOB_NAME.$TIMESTAMP.client$JOB_INDEX.txt";

BASE_PORT=10000

wait_for_others()
{
    echo >&2 "Waiting for others jobs to come online ..."
    for n in $(seq 1 $((PARALLELISM - 1))); do
        nc -l -p $((BASE_PORT + $n)) &
    done
    wait
    sleep 5
    echo >&2 "Done"
}

broadcast_start_ts()
{
    local start_ts=$1
    echo >&2 "Broadcasting starting time of $(date -d @$start_ts) ..."
    for n in $(seq 1 $((PARALLELISM - 1))); do
        host="$JOB_NAME-$n.$SERVICE_NAME"
        port="$((BASE_PORT + $n))"
        echo $start_ts | nc $host $port &
    done
    wait
    echo >&2 "Done"
}

sleep_till()
{
    local target=$1
    echo >&2 "Sleeping until $(date -d @$target) ..."
    diff=$(($target - $(date +%s)))
    if [ $diff -lt 0 ]; then { echo >&2 "Target timestamp is in the past, aborting ..."; exit 3; } fi
    sleep $diff
    echo >&2 "Woke up for a target timestamp $(date -d @$target) at $(date)."
}

wait_for_client0()
{
    echo >&2 "Waiting for start time from client0 ..."
    host="$JOB_NAME-0.$SERVICE_NAME"
    port="$((BASE_PORT + $JOB_INDEX))"
    local retry_count=0
    while ! nc -z $host $port; do
        echo >&2 "Server not up yet, sleeping for 60s ..."
        sleep 30
        retry_count=$((retry_count + 1))
        if [ $retry_count -gt 10 ]; then
            echo >&2 "Server still not up after $retry_count retries. Aborting ..."
            exit 3;
        fi
    done
    echo "$(nc -l $port)"
    echo >&2 "Done"
}

barrier()
{
    if [ $PARALLELISM -eq 1 ]; then return; fi

    if [ $JOB_INDEX -eq 0 ]; then
        wait_for_others
        start_ts=$(($(date +%s) + $SLEEP_TIME))
        broadcast_start_ts $start_ts
        sleep_till $start_ts
    else
        start_ts=$(wait_for_client0)
        sleep_till $start_ts
    fi
}

log_and_run() {
    set -o pipefail;
    echo -e "Time: $(date +%s)\n+ $@" | tee "$outfile";
    /usr/bin/time -v "$@" 2>&1 | tee -a "$outfile";
}

run_up_to_threads() {
    c_max=$1
    c=4
    while [ $c -le $c_max ]; do
        barrier
        log_and_run /cockroach/cockroach workload run $WORKLOAD --concurrency $c $RUN_ARGS "$CRDB_CONNECTION_STRING";
        # sleep $SLEEP_TIME;    # Moved inside barrier call
        c=$((c * 4));
    done
}

main()
{
    echo "Job $JOB_INDEX running on $NODENAME ..." | tee -a "$outfile";
    if [ $JOB_INDEX -eq 0 ]; then
        log_and_run /cockroach/cockroach workload init $WORKLOAD $INIT_ARGS "$CRDB_CONNECTION_STRING";
    fi

    run_up_to_threads 1024
}

set -e
# set -x

main
