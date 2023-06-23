#!/bin/bash

cd "$(dirname "$0")"

kubectl create -f 0.experiments.pvc.yaml

