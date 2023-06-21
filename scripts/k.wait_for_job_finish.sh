#!/bin/bash

[ $# -ge 1 ] || { echo >&2 "Usage: $0 job-name"; exit 2; }

jobname="$1"
shift

# set -x

# Source: https://stackoverflow.com/a/60286538

kubectl wait --for=condition=complete --timeout=-1s "job/$jobname" "$@" &
completion_pid=$!

# wait for failure as background process - capture PID
kubectl wait --for=condition=failed --timeout=-1s job/$jobname "$@" && exit 1 &
failure_pid=$! 

# capture exit code of the first subprocess to exit
wait -n $completion_pid $failure_pid

# store exit code in variable
exit_code=$?

if (( $exit_code == 0 )); then
  echo "Job completed"
else
  echo "Job failed with exit code ${exit_code}, exiting..."
fi

exit $exit_code
