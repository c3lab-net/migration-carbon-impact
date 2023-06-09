#!/bin/bash

set -e
set -x

kubectl create -f cockroachdb-statefulset.yaml

# Wait till all are running
kubectl wait pod --for=jsonpath='{.status.phase}'=Running -l app=taobench-cockroachdb

kubectl get pods -l app=taobench-cockroachdb

# Run cockroach init on one of the pods to complete initialization
kubectl exec -it taobench-cockroachdb-0 \
    -- /cockroach/cockroach init \
    --certs-dir=/cockroach/cockroach-certs

# Wait till all are ready
kubectl wait pods --for=condition=ready -l app=taobench-cockroachdb

kubectl get pods
