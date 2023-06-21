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
        echo "Working on $jobname ..."
        echo "Deleting existing job/service definition ..."
        ./run.sh delete $workload $n && true
        retry_count=0
        while [ $retry_count -le 2 ]; do
            (set -x;
                ./run.sh create $workload $n;
                k.wait_for_job_finish.sh crdb-$workload-"$n"x;) && break
            echo "Workload $jobname failed. Restarting ..."
            (set -x; ./run.sh delete $workload $n;)
            retry_count=$((retry_count + 1))
        done
    done
    n=$((n * 2))
done
