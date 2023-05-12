#!/bin/bash

# Source: https://www.cockroachlabs.com/docs/v22.2/deploy-cockroachdb-with-kubernetes.html?filters=manual

namespace="c3lab"

# On a machine with cockroach installed, or in a docker container:
mkdir certs my-safe-directory
cockroach cert create-ca --certs-dir=certs --ca-key=my-safe-directory/ca.key
cockroach cert create-client root --certs-dir=certs --ca-key=my-safe-directory/ca.key
kubectl create secret generic taobench.cockroachdb.client.root --from-file=certs
cockroach cert create-node \
    localhost 127.0.0.1 \
    taobench-cockroachdb-public \
    taobench-cockroachdb-public.$namespace \
    taobench-cockroachdb-public.$namespace.svc.cluster.local \
    *.taobench-cockroachdb \
    *.taobench-cockroachdb.$namespace \
    *.taobench-cockroachdb.$namespace.svc.cluster.local \
    --certs-dir=certs --ca-key=my-safe-directory/ca.key
kubectl create secret generic taobench.cockroachdb.node --from-file=certs
