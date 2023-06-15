#!/bin/bash

kubectl delete statefulsets -l app=taobench-cockroachdb
