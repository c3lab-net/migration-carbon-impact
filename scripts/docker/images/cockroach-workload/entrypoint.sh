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

log()
{
    echo >&2 -e -n "$(date -u +'%FT%T')\t"
    echo >&2 "$@"
}

wait_for_others()
{
    log "Waiting for others jobs to come online ..."
    local pids=""
    for n in $(seq 1 $((PARALLELISM - 1))); do
        timeout 5m nc -l -p $((BASE_PORT + $n)) &
        pids+="$! "
    done
    for pid in $pids; do
        wait $pid
    done
    sleep 5
    log "Done"
}

broadcast_start_ts()
{
    local start_ts=$1
    log "Broadcasting starting time of $(date -u +'%FT%T' -d @$start_ts) ..."
    local pids=""
    for n in $(seq 1 $((PARALLELISM - 1))); do
        host="$JOB_NAME-$n.$SERVICE_NAME"
        port="$((BASE_PORT + $n))"
        echo $start_ts | timeout 5m nc $host $port &
        pids+="$! "
    done
    for pid in $pids; do
        wait $pid
    done
    log "Done"
}

sleep_till()
{
    local target=$1
    log "Sleeping until $(date -u +'%FT%T' -d @$target) ..."
    diff=$(($target - $(date +%s)))
    if [ $diff -lt 0 ]; then { echo >&2 "Target timestamp is in the past, aborting ..."; exit 3; } fi
    sleep $diff
    log "Woke up for a target timestamp $(date -u +'%FT%T' -d @$target) at $(date -u +'%FT%T')."
}

wait_for_client0()
{
    log "Contacting client0 to obtain start time ..."
    host="$JOB_NAME-0.$SERVICE_NAME"
    port="$((BASE_PORT + $JOB_INDEX))"
    local retry_count=0
    while ! timeout 5m nc -z $host $port; do
        log "Server not up yet, sleeping for 30s ..."
        sleep 30
        retry_count=$((retry_count + 1))
        if [ $retry_count -gt 10 ]; then
            log "Server still not up after $retry_count retries. Aborting ..."
            exit 3;
        fi
    done
    log "Waiting for start time from client0 ..."
    echo "$(timeout 5m nc -l $port)"
    log "Done"
}

barrier()
{
    # if [ $PARALLELISM -eq 1 ]; then return; fi

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
    log "+ $@" | tee -a "$outfile";
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
    log "Job $JOB_INDEX running on $NODENAME ..." 2>&1 | tee -a "$outfile";
    if [ $JOB_INDEX -eq 0 ]; then
        log_and_run /cockroach/cockroach workload init $WORKLOAD $INIT_ARGS "$CRDB_CONNECTION_STRING";
    fi

    run_up_to_threads 1024
}

set -e
# set -x

main
