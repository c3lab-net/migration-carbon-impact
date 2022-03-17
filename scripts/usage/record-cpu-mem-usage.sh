#!/bin/zsh

QUIET=
for arg in "$@"
do
case $arg in
    -q|--quiet)
        shift
        QUIET="true"
        ;;
esac
done

LOGFILE=${1:-"cpu-mem-usage.log"}
SAMPLE_INTERVAL=1

END_TIME=${2:-86400}

echo >&2 "Recording CPU/memory usage to \"$LOGFILE\" for the next "$END_TIME"s ..."

function write_cpu_mem_usage()
{
    timestamp="$(date +'%Y-%m-%d %H:%M:%S.%6N')"
    line=$(echo -n "$timestamp,")
    cpu_and_mem_line=$(top -n 1 -b | head -n 4 | tail -n 2)
    cpu_line=$(echo "$cpu_and_mem_line" | head -n 1)
    mem_line=$(echo "$cpu_and_mem_line" | tail -n 1)
    # 2: (un-niced) user, 4: system, 6: niced user, 8: idle
    line+=$(echo $cpu_line | awk '{printf "%.1f,%.1f,%.1f,", $2+$6, $4, $8}')
    # 8: used, 6: free
    line+=$(echo $mem_line | awk '{printf "%.1f,%.1f\n", $8, $6}')
    if [[ $QUIET == "true" ]]; then
        echo $line | tee -a $LOGFILE > /dev/null
    else
        echo $line | tee -a $LOGFILE
    fi
}

echo "timestamp,cpu-user,cpu-kernel,cpu-idle,mem-used,mem-free" > $LOGFILE
for ((i=0; i < $END_TIME; i++))
do
    write_cpu_mem_usage &
    sleep $SAMPLE_INTERVAL
    wait
done
# wait
