#!/bin/zsh

cwd=$(pwd)

SCRIPT_DIR="$(dirname "$0")"

MAXJOBS=1
SLEEP=10
name="default"

parallel_args=""
for arg in "$@"
do
case $arg in
    -j|--maxjobs)
        shift
        MAXJOBS=$1
        shift
        ;;
    -n|--name)
        shift
        name=$1
        shift
        ;;
    -N|--no-args)
        # without this, one needs to consume the argument via {}
        shift
        parallel_args+="-N "
        ;;
    -S|--sleep)
        shift
        SLEEP=$1
        shift
        ;;
esac
done

cmd="$@"

# set -e
# set -x

sudo $SCRIPT_DIR/rapl/rapl.py --quiet --log /tmp/$name.rapl.csv &
sleep 1
pid_rapl=$(echo $(ps --ppid $! -o pid=))

$SCRIPT_DIR/usage/record-cpu-mem-usage.sh --quiet /tmp/$name.usage.csv &
pid_usage=$(echo $!)

sleep $SLEEP
if [[ $MAXJOBS -gt 1 ]]; then
    $SCRIPT_DIR/parallel/run-multiple-instances.sh $(echo "$parallel_args") -j $MAXJOBS "$@"
    exitcode=$?
else
    "$@"
    exitcode=$?
fi
sleep $SLEEP
sudo kill $pid_rapl $pid_usage
sleep 1

sudo chown $(id -u):$(id -g) /tmp/$name.{rapl,usage}.csv
mv /tmp/$name.{rapl,usage}.csv "$cwd/"

return $exitcode

