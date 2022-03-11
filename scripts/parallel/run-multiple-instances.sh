#!/bin/zsh

MAXJOBS=1

parallel_args=""
for arg in "$@"
do
case $arg in
    -j|--maxjobs)
        shift
        MAXJOBS=$1
        shift
        ;;
    -N|--no-args)
        # without this, one can use {} to access the argument
        shift
        parallel_args+="-N0 "
esac
done

set -e
# set -x
seq $MAXJOBS | parallel $(echo "$parallel_args") "$@"
