#!/bin/bash

kubectl create -f cockroachdb-client.yaml

kubectl exec -it taobench-cockroachdb-client-secure \
    -- ./cockroach sql \
    --certs-dir=/cockroach-certs \
    --host=taobench-cockroachdb-public
