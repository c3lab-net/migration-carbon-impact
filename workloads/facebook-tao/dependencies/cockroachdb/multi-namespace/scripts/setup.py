#!/usr/bin/env python3

import os
from subprocess import check_call,check_output
from sys import exit
from time import sleep

from config import *

# ------------------------------------------------------------------------------

# First, do some basic input validation.
if len(contexts) == 0:
    exit("must provide at least one Kubernetes cluster in the `contexts` map at the top of the script")

if len(regions) != 0 and len(regions) != len(contexts):
    exit("regions not specified for all kubectl contexts (%d regions, %d contexts)" % (len(regions), len(contexts)))

try:
    check_call(["which", cockroach_path])
except:
    exit("no binary found at provided path '" + cockroach_path + "'; please put a cockroach binary in your path or change the cockroach_path variable")

for zone, context in contexts.items():
    try:
        check_call(['kubectl', 'get', 'pods', '--namespace', zone])
    except:
        exit("unable to make basic API call using kubectl context '%s' for cluster in zone '%s'; please check if the context is correct and your Kubernetes cluster is working" % (context, zone))

# Set up the necessary directories and certificates.
os.makedirs(certs_dir, exist_ok=True)
os.makedirs(ca_key_dir, exist_ok=True)
os.makedirs(generated_files_dir, exist_ok=True)

print("Generating certificates ...")
check_call([cockroach_path, 'cert', 'create-ca', '--certs-dir', certs_dir, '--ca-key', ca_key_dir+'/ca.key'])
check_call([cockroach_path, 'cert', 'create-client', 'root', '--certs-dir', certs_dir, '--ca-key', ca_key_dir+'/ca.key'])

# For each cluster, create secrets containing the node and client certificates.
# Note that we create the root client certificate in both the zone namespace
# and the default namespace so that it's easier for clients in the default
# namespace to use without additional steps.
#
# Also create a load balancer to each cluster's DNS pods.
print("Creating secrets ...")
for zone, context in contexts.items():
    print(zone, context)
    # check_call(['kubectl', 'create', 'namespace', zone, '--context', context])
    check_call(['kubectl', 'create', 'secret', 'generic', 'taobench.cockroachdb.client.root', '--from-file', certs_dir, '--namespace', zone])
    check_call([cockroach_path, 'cert', 'create-node', '--certs-dir', certs_dir, '--ca-key', ca_key_dir+'/ca.key', 'localhost', '127.0.0.1', 'taobench-cockroachdb-public', 'taobench-cockroachdb-public.default', 'taobench-cockroachdb-public.'+zone, 'taobench-cockroachdb-public.%s.svc.cluster.local' % (zone), '*.taobench-cockroachdb', '*.taobench-cockroachdb.'+zone, '*.taobench-cockroachdb.%s.svc.cluster.local' % (zone)])
    check_call(['kubectl', 'create', 'secret', 'generic', 'taobench.cockroachdb.node', '--namespace', zone, '--from-file', certs_dir, '--context', context])
    check_call('rm %s/node.*' % (certs_dir), shell=True)

    # check_call(['kubectl', 'apply', '-f', 'dns-lb.yaml', '--context', context])

"""
# Set up each cluster to forward DNS requests for zone-scoped namespaces to the
# relevant cluster's DNS server, using load balancers in order to create a
# static IP for each cluster's DNS endpoint.
dns_ips = dict()
for zone, context in contexts.items():
    external_ip = ''
    while True:
        external_ip = check_output(['kubectl', 'get', 'svc', 'kube-dns-lb', '--namespace', 'kube-system', '--context', context, '--template', '{{range .status.loadBalancer.ingress}}{{.ip}}{{end}}'])
        if external_ip:
            break
        print  'Waiting for DNS load balancer IP in %s...' % (zone)
        sleep(10)
    print 'DNS endpoint for zone %s: %s' % (zone, external_ip)
    dns_ips[zone] = external_ip
"""

'''
# Update each cluster's DNS configuration with an appropriate configmap. Note
# that we have to leave the local cluster out of its own configmap to avoid
# infinite recursion through the load balancer IP. We then have to delete the
# existing DNS pods in order for the new configuration to take effect.
for zone, context in contexts.items():
    remote_dns_ips = dict()
    for z, ip in dns_ips.items():
        if z == zone:
            continue
        remote_dns_ips[z+'.svc.cluster.local'] = [ip]
    config_filename = '%s/dns-configmap-%s.yaml' % (generated_files_dir, zone)
    with open(config_filename, 'w') as f:
        f.write("""\
apiVersion: v1
kind: ConfigMap
metadata:
  name: kube-dns
  namespace: kube-system
data:
  stubDomains: |
    %s
""" % (json.dumps(remote_dns_ips)))
    check_call(['kubectl', 'apply', '-f', config_filename, '--namespace', 'kube-system', '--context', context])
    check_call(['kubectl', 'delete', 'pods', '-l', 'k8s-app=kube-dns', '--namespace', 'kube-system', '--context', context])
'''

# Create a cockroachdb-public service in the default namespace in each cluster.
print("Creating public services ...")
for zone, context in contexts.items():
    print(zone, context)
    yaml_file = '%s/external-name-svc-%s.yaml' % (generated_files_dir, zone)
    with open(yaml_file, 'w') as f:
        check_call(['sed', 's/NAMESPACE/%s/g' % (zone), 'external-name-svc.yaml'], stdout=f)
    check_call(['kubectl', 'apply', '-f', yaml_file, '--context', context])

# Generate the join string to be used.
join_addrs = []
for zone in contexts:
    for i in range(3):
        join_addrs.append('taobench-cockroachdb-%d.taobench-cockroachdb.%s' % (i, zone))
join_str = ','.join(join_addrs)

# Create the cockroach long-lived resources in each cluster.
print("Creating long-lived resources ...")
for zone, context in contexts.items():
    print(zone, context)
    yaml_file = '%s/cockroachdb-cockroachdb-roles_accounts_services-%s.yaml' % (generated_files_dir, zone)
    with open(yaml_file, 'w') as f:
        check_call(['sed', 's/NAMESPACE/%s/g' % zone, 'cockroachdb-roles_accounts_services.yaml'], stdout=f)
    check_call(['kubectl', 'apply', '-f', yaml_file, '--namespace', zone, '--context', context])

# Create the cockroach statefulsets in each cluster.
print("Creating statefulsets ...")
for zone, context in contexts.items():
    print(zone, context)
    if zone in regions:
        locality = 'region=%s,zone=%s' % (regions[zone], zone)
    else:
        locality = 'zone=%s' % (zone)
    yaml_file = '%s/cockroachdb-statefulset-%s.yaml' % (generated_files_dir, zone)
    with open(yaml_file, 'w') as f:
        check_call(['sed', 's/JOINLIST/%s/g;s/LOCALITYLIST/%s/g' % (join_str, locality), 'cockroachdb-statefulset.yaml'], stdout=f)
    check_call(['kubectl', 'apply', '-f', yaml_file, '--namespace', zone, '--context', context])

# Finally, initialize the cluster.
print('Waiting till all stateful sets are running')
for zone, context in contexts.items():
    check_call(['kubectl', 'wait', 'pod', '--for=jsonpath={.status.phase}=Running', '-l', 'app=taobench-cockroachdb', '--namespace', zone, '--context', context])

for zone, context in contexts.items():
    check_call(['kubectl', 'create', '-f', 'cockroachdb-cluster-init.yaml', '--namespace', zone, '--context', context])
    # We only need run the init command in one zone given that all the zones are
    # joined together as one cluster.
    break
