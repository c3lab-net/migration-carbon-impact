#!/bin/zsh

cd "$(dirname "$0")" || exit 1

set -e
set -x

n=1
while [ $n -le 16 ]; do
    for workload in $(tail +2 cockroach-workloads.csv | cut -f 1 -d','); do
            ./run.sh create $workload $n
            k.wait_for_job_finish.sh crdb-$workload-"$n"x && true
            # ./run.sh delete $workload $n
    done
    n=$((n * 2))
done
