## CockroachDB-provided workloads

This directory contains the job definitions to run [Cockroach-provided workloads](https://www.cockroachlabs.com/docs/stable/cockroach-workload.html#workloads).
This includes:
- ycsb
- kv
- bank
- movr
- tpcc

The corrsponding container image is defined in `scripts/docker/images/cockroach-workload` directory.

The job/container is designed to handle multiple concurrent runs, where the 0-index pod will initialize the database and initiate an `MPI_barrier()`-like synchronization mechanism prior to each run. Each run will have an increasing level of parallelism (for one pod), as defined in the container script.
