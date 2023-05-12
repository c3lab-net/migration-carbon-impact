#!/bin/bash

kubectl create -f cockroachdb-statefulset.yaml

# Wait till all are running
kubectl get pods

# Run cockroach init on one of the pods to complete initialization
kubectl exec -it taobench-cockroachdb-0 \
    -- /cockroach/cockroach init \
    --certs-dir=/cockroach/cockroach-certs

# Wait till all are ready
kubectl get pods
