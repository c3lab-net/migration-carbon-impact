#!/bin/bash

set -e

kubectl create -f cockroachdb-statefulset.yaml

kubectl get pods

# Wait till all are running
sleep 15

# Run cockroach init on one of the pods to complete initialization
kubectl exec -it taobench-cockroachdb-0 \
    -- /cockroach/cockroach init \
    --certs-dir=/cockroach/cockroach-certs

# Wait till all are ready
kubectl wait pods --for=condition=ready -l app=taobench-cockroachdb

kubectl get pods
