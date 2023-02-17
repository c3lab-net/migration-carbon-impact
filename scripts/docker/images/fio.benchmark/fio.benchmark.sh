#!/bin/sh

# Source: https://cloud.google.com/compute/docs/disks/benchmarking-pd-performance

if [ $# -lt 3 ]; then
    echo >&2 "Usage: $0 <test-directory> <io-size> <num-threads>"
    echo >&2 -e "\tExample: $0 /test-volume 1G 16"
    exit 1
fi

TEST_DIR="$1"
IOSIZE="$2"
NTHREADS="$3"

set -e

echo -e "Running fio throughput and IOPS tests in '$TEST_DIR' ...\n"

mkdir -p $TEST_DIR

echo -e "1. Write throughput test\n"
# Test write throughput by performing sequential writes with multiple parallel streams (16+), using an I/O block size of 1 MB and an I/O depth of at least 64:
fio --name=write_throughput --directory=$TEST_DIR --numjobs="$NTHREADS" \
    --size="$IOSIZE" --time_based --runtime=60s --ramp_time=2s --ioengine=libaio \
    --direct=1 --verify=0 --bs=1M --iodepth=64 --rw=write \
    --group_reporting=1
rm $TEST_DIR/*
echo

echo -e "2. Write IOPS test\n"
# Test write IOPS by performing random writes, using an I/O block size of 4 KB and an I/O depth of at least 256:
fio --name=write_iops --directory=$TEST_DIR --size="$IOSIZE" \
    --time_based --runtime=60s --ramp_time=2s --ioengine=libaio --direct=1 \
    --verify=0 --bs=4K --iodepth=256 --rw=randwrite --group_reporting=1
rm $TEST_DIR/*
echo

echo -e "3. Read throughput test\n"
# Test read throughput by performing sequential reads with multiple parallel streams (16+), using an I/O block size of 1 MB and an I/O depth of at least 64:
fio --name=read_throughput --directory=$TEST_DIR --numjobs="$NTHREADS" \
    --size="$IOSIZE" --time_based --runtime=60s --ramp_time=2s --ioengine=libaio \
    --direct=1 --verify=0 --bs=1M --iodepth=64 --rw=read \
    --group_reporting=1
rm $TEST_DIR/*
echo

echo -e "4. Read IOPS test\n"
# Test read IOPS by performing random reads, using an I/O block size of 4 KB and an I/O depth of at least 256:
fio --name=read_iops --directory=$TEST_DIR --size="$IOSIZE" \
    --time_based --runtime=60s --ramp_time=2s --ioengine=libaio --direct=1 \
    --verify=0 --bs=4K --iodepth=256 --rw=randread --group_reporting=1
echo
