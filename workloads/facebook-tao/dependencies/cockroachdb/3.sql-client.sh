#!/bin/bash

kubectl create -f cockroachdb-client.yaml

CRDB_DB="taobench"
# CRDB_USER="taouser"
# CRDB_PASSWORD="insert-password-here"

kubectl exec -it taobench-cockroachdb-client \
    -- ./cockroach sql \
    --certs-dir=/cockroach-certs \
    --host=taobench-cockroachdb-public \
    --execute="\l;"
    # --execute="CREATE DATABASE \"$CRDB_DB\";" \
    # --execute="CREATE USER \"$CRDB_USER\" WITH PASSWORD '$CRDB_PASSWORD';" \
    # --execute="GRANT admin TO \"$CRDB_USER\";"

kubectl create secret generic taobench-cockroachdb-client \
    --from-literal=CRDB_DB="$CRDB_DB" #\
    # --from-literal=CRDB_USER="$CRDB_USER" \
    # --from-literal=CRDB_PASSWORD="$CRDB_PASSWORD"

kubectl delete -f cockroachdb-client.yaml
