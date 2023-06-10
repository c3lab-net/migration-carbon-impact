#!/usr/bin/env python3

# Before running the script, fill in appropriate values for all the parameters
# above the dashed line.

# Fill in the `contexts` map with the zones of your clusters and their
# corresponding kubectl context names.
#
# To get the names of your kubectl "contexts" for each of your clusters, run:
#   kubectl config get-contexts
#
# example:
# contexts = {
#     'us-central1-a': 'gke_cockroach-alex_us-central1-a_my-cluster',
#     'us-central1-b': 'gke_cockroach-alex_us-central1-b_my-cluster',
#     'us-west1-b': 'gke_cockroach-alex_us-west1-b_my-cluster',
# }
contexts = {
    'c3lab-region1': 'nautilus',
    'c3lab-region2': 'nautilus',
    'c3lab-region3': 'nautilus',
}

# Fill in the `regions` map with the zones and corresponding regions of your
# clusters.
#
# Setting regions is optional, but recommended, because it improves cockroach's
# ability to diversify data placement if you use more than one zone in the same
## region. If you aren't specifying regions, just leave the map empty.
#
# example:
# regions = {
#     'us-central1-a': 'us-central1',
#     'us-central1-b': 'us-central1',
#     'us-west1-b': 'us-west1',
# }
regions = {
    'c3lab-region1': 'us-west',
    'c3lab-region2': 'us-central',
    'c3lab-region3': 'us-east',
}

# Paths to directories in which to store certificates and generated YAML files.
certs_dir = './cert-data/certs'
ca_key_dir = './cert-data/my-safe-directory'
generated_files_dir = './cert-data/generated'

# Path to the cockroach binary on your local machine that you want to use
# generate certificates. Defaults to trying to find cockroach in your PATH.
cockroach_path = 'cockroach'
