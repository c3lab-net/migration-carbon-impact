#!/bin/zsh

# s3 config: https://docs.pacificresearchplatform.org/userdocs/storage/ceph-s3/
rclone_conf="$(rclone config file | grep rclone.conf$)"
kubectl create secret generic cephs3-rclone-conf --from-file=rclone.conf="$rclone_conf"
