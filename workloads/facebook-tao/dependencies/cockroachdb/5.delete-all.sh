#!/bin/bash

kubectl delete pods,statefulsets,jobs -l app=taobench-cockroachdb
kubectl delete services,poddisruptionbudget,rolebinding,clusterrolebinding,role,clusterrole,serviceaccount,alertmanager,prometheus,prometheusrule,serviceMonitor -l app=taobench-cockroachdb
