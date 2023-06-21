#!/bin/zsh

cd "$(dirname "$0")" || exit 1

set -e

n=1
while [ $n -le 16 ]; do
    for workload in $(tail +2 cockroach-workloads.csv | cut -f 1 -d','); do
        jobname="crdb-$workload-${n}x"
        if kubectl get job "$jobname" > /dev/null 2>&1; then
            echo "Job $jobname already exists. Skipping ..."
            continue
        fi
        while :; do
            set -x
            ./run.sh delete $workload $n && true
            ./run.sh create $workload $n
            k.wait_for_job_finish.sh crdb-$workload-"$n"x && break
            ./run.sh delete $workload $n
            set +x
        done
    done
    n=$((n * 2))
done
