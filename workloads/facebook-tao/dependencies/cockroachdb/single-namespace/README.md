# Setting up CockroachDB required by TAOBench

## On Nautilus (Kubernetes)

Because Nautilus manages multiple regions in a single cluster, we can use single-cluster deployment as describe [here](https://www.cockroachlabs.com/docs/v22.2/deploy-cockroachdb-with-kubernetes.html?filters=manual#initialize-the-cluster).
- Skip step 1, as this only applies to cloud-based kubernetes deployment.
- Follow step 2 and change namespace as needed, as included in the scripts.
- Follow step 3 and 4 to interact with the database.
- Follow step 5 to delete all resources created.
