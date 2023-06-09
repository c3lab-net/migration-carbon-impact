#!/usr/bin/env python3

from shutil import rmtree
from subprocess import call

from config import *

# Delete each cluster's special zone-scoped namespace, which transitively
# deletes all resources that were created in the namespace, along with the few
# other resources we created that weren't in that namespace
for zone, context in contexts.items():
    # call(['kubectl', 'delete', 'namespace', zone, '--context', context])
    # TODO: delete individual resources
    call(['kubectl', 'delete', 'secret', 'taobench.cockroachdb.client.root', '--namespace', zone])
    call(['kubectl', 'delete', '-f', 'external-name-svc.yaml', '--namespace', zone])
    # call(['kubectl', 'delete', '-f', 'dns-lb.yaml', '--context', context])
    # call(['kubectl', 'delete', 'configmap', 'kube-dns', '--namespace', 'kube-system', '--context', context])
    # Restart the DNS pods to clear out our stub-domains configuration.
    # call(['kubectl', 'delete', 'pods', '-l', 'k8s-app=kube-dns', '--namespace', 'kube-system', '--context', context])

try:
    rmtree(certs_dir)
except OSError:
    pass
try:
    rmtree(ca_key_dir)
except OSError:
    pass
try:
    rmtree(generated_files_dir)
except OSError:
    pass
