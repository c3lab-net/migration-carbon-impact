#!/bin/bash

set -e

kubectl create -f cockroachdb-client.yaml

# This script creates user for connecting to dashboard.
# Password is not needed from pods, as client certificate is used instead.

# Uncomment this on first run to create the secret.
: '
CRDB_USER="taouser"
CRDB_PASSWORD="insert-password-here"

kubectl create secret generic taobench-cockroachdb-client \
    --from-literal=CRDB_USER="$CRDB_USER" \
    --from-literal=CRDB_PASSWORD="$CRDB_PASSWORD"
#'

function get_k8s_secret_literal()
{
    secret_name="$1"
    secret_key="$2"
    kubectl get secret "$secret_name" --template={{.data."$secret_key"}} | base64 -d
}

CRDB_USER="$(get_k8s_secret_literal "taobench-cockroachdb-client" "CRDB_USER")"
CRDB_PASSWORD="$(get_k8s_secret_literal "taobench-cockroachdb-client" "CRDB_PASSWORD")"

kubectl wait --for=condition=ready pod taobench-cockroachdb-client --timeout=3m
kubectl exec -it taobench-cockroachdb-client \
    -- ./cockroach sql \
    --certs-dir=/cockroach-certs \
    --host=taobench-cockroachdb-public \
    --execute="CREATE USER \"$CRDB_USER\" WITH PASSWORD '$CRDB_PASSWORD';" \
    --execute="GRANT admin TO \"$CRDB_USER\";"

kubectl delete -f cockroachdb-client.yaml
