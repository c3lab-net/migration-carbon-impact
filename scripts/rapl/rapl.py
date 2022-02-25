#!/usr/bin/env python3

import os
import os.path
from datetime import datetime
import re
import time 
import argparse
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import pandas as pd 

MICROJOULE = 1 #Represents Microjoule
JOULE = 2 #Represents Joule
WATT_HOUR = 3 #Represents watt hour

def read_sysfs_file(path):
    with open(path, "r") as f:
        contents = f.read().strip()
        return contents

def get_domain_info(path):
    name = read_sysfs_file("%s/name" % path)
    energy_uj = int(read_sysfs_file("%s/energy_uj" % path))
    max_energy_range_uj = int(read_sysfs_file("%s/max_energy_range_uj" % path))

    return name, energy_uj, max_energy_range_uj

def walk_rapl_dir(path):
    if not os.path.exists(path):
        raise ValueError(
            "No RAPL directory exists to read from, RAPL CPU power readings may not be supported on this machine."
        )
    regex = re.compile("intel-rapl")
    for dirpath, dirnames, filenames in os.walk(path, topdown=True):
        for d in dirnames:
            if not regex.search(d):
                dirnames.remove(d)
        yield dirpath, dirnames, filenames

class RAPLSample(object):
    # def __init__(self):
    #     self.domains = {}
    #     self.domains_by_id = {}
    #     self.timestamp = datetime.now()

    @classmethod
    def get_power_sample(cls):

        sample = RAPLSample()
        sample.domains = {}
        sample.domains_by_id = {}
        sample.timestamp = datetime.now()

        for dirpath, dirnames, filenames in walk_rapl_dir("/sys/class/powercap/intel-rapl"):
            current = dirpath.split("/")[-1]
            # print("dirpath>", dirpath)
            # print("current>", current)
            splits = current.split(":")

            if len(splits) == 1:
                    continue
            # print("len(splits)>", len(splits))
            # package
            elif len(splits) >= 2:
                domain = RAPLDomain.construct(current, dirpath)
                # print(domain.id)
            #     # catalog all domains here
                sample.domains_by_id[domain.id] = domain
                sample._link_tree(domain)
        return sample

    def _link_tree(self, domain):
        if domain.is_subdomain():
            parent = self.domains_by_id[domain.parent_id()]
            parent.subdomains[domain.name] = domain
        else:
            self.domains[domain.name] = domain

    def __sub__(self, other):
        diff = RAPLDifference()
        diff.domains = {}
        diff.domains_by_id = {}
        diff.duration = (self.timestamp - other.timestamp).total_seconds()

        for id in self.domains_by_id:
            assert id in other.domains_by_id

        for id in self.domains_by_id:
            selfDomain = self.domains_by_id[id]
            otherDomain = other.domains_by_id[id]
            diffDomain = selfDomain - otherDomain

            diff.domains_by_id[id] = diffDomain
            diff._link_tree(diffDomain)

        return diff

    def get_energy(self, package, domain=None, unit=JOULE):
        if not domain:
            e = self.domains[package].values["energy_uj"]
        else:
            e = self.domains[package].subdomains[domain].values["energy_uj"]

        if unit == MICROJOULE:
            return e
        elif unit == JOULE:
            return e / 1000000
        elif unit == WATT_HOUR:
            return e / (1000000 * 3600)

class RAPLDomain(object):
    @classmethod
    def construct(cls, id, path):

        name, energy_uj, max_energy_range_uj = get_domain_info(path)

        domain = RAPLDomain()
        domain.name = name
        domain.id = id
        domain.values = {}
        domain.values["energy_uj"] = energy_uj
        domain.max_values = {}
        domain.max_values["energy_uj"] = max_energy_range_uj
        domain.subdomains = {}
        domain.parent = None

        return domain

    def is_subdomain(self):
        splits = self.id.split(":")
        return len(splits) > 2

    def parent_id(self):
        splits = self.id.split(":")
        return ":".join(splits[0:2])
    
    # take the difference of two domain samples
    def __sub__(self, other):
        assert self.name == other.name and self.id == other.id

        domain = RAPLDomain()
        domain.name = self.name
        domain.id = self.id
        domain.values = {}
        for v in self.values:
            diff = self.values[v] - other.values[v]
            # if there was a rollover
            if diff < 0:
                diff = self.max_values[v] + diff
            domain.values[v] = diff

        domain.subdomains = {}
        domain.parent = None

        return domain

class RAPLDifference(RAPLSample):
    def average_energy(self, package, domain=None):
        # print('duration=', self.duration)
        return self.get_energy(package, domain, unit=JOULE) / self.duration

def is_rapl_compatible():
    return os.path.exists("/sys/class/powercap/intel-rapl")

class RAPLMonitor(object):
    @classmethod
    def sample(cls):
        return RAPLSample.get_power_sample()

def main(args):
    if (not is_rapl_compatible):
        raise ValueError("RAPL is not supported")

    df_energy = pd.DataFrame(columns=['timestamp', 'total_intel_energy', 'total_cpu_energy', 'total_dram_energy', 'total_gpu_energy'])
    df_energy.to_csv(args.log, mode="w", header=True, index=False)
    data = {}
    while(True):
        pw_obj1 = RAPLMonitor.sample()
        time.sleep(1)
        pw_obj2 = RAPLMonitor.sample()
        diff = pw_obj2 - pw_obj1
        total_intel_energy = 0 # Total energy of the sockets (Including DRAM)
        total_dram_energy = 0
        total_cpu_energy = 0
        total_gpu_energy = 0

        for d in diff.domains:
            domain = diff.domains[d]
            # print(domain.name)
            energy = diff.average_energy(package=domain.name)
            # print('energy=', energy)
            if domain.name == "psys":
                # skip SoC aggregate reporting
                continue

            if "package" not in domain.name:
                raise NotImplementedError(
                    "Unexpected top level domain for RAPL package. Not yet supported."
                )
                
            total_intel_energy += energy

            for sd in domain.subdomains:
                subdomain = domain.subdomains[sd]
                power = diff.average_energy(package=domain.name, domain=subdomain.name)
                subdomain = subdomain.name.lower()
                if subdomain == "ram" or subdomain == "dram":
                    total_dram_energy += power
                elif subdomain == "cores" or subdomain == "cpu":
                    total_cpu_energy += power
                elif subdomain == "gpu":
                    total_gpu_energy += power

        data['timestamp'] = pw_obj2.timestamp
        data['total_intel_energy'] = total_intel_energy
        data['total_cpu_energy'] = total_intel_energy - total_dram_energy
        data['total_dram_energy'] = total_dram_energy
        data['total_gpu_energy'] = total_gpu_energy
        print(data)
        # df_energy = df_energy.append(data, True)
        df_energy_new = pd.DataFrame([data])
        df_energy_new.to_csv(args.log, mode="a", header=False, index=False)
        # df_energy = pd.concat([df_energy, df_energy_new], ignore_index=True, axis=0, join='outer')
        # df_energy.to_csv(args.log, mode="a", header=False, index=False)
        # print(pw_obj2.timestamp)
        # print('total_intel_energy=', total_intel_energy)
        # print('total_cpu_energy=', (total_intel_energy - total_dram_energy))
        # print('total_dram_energy=', total_dram_energy)
        # print('total_gpu_energy=', total_gpu_energy)

        # print(pw_obj1.domains_by_id['intel-rapl:0'].name)
        # print(pw_obj1.domains_by_id['intel-rapl:0:0'].name)
        # print(pw_obj1.domains_by_id['intel-rapl:1'].name)
        # print(pw_obj1.domains_by_id['intel-rapl:1:0'].name)
        # for d in pw_obj1.domains_by_id:
        #     print(pw_obj1.domains_by_id)
        # print(pw_obj1.domains['package-0'].subdomains['dram'].subdomains)

def parse_args():
    #Get frequency(duration between samples) and how long to run or the number of iterations
    """Parse commandline arguments"""
    parser = argparse.ArgumentParser(description='Run RAPL Monitor')
    parser.add_argument('--log', '-l', type=str, help='RAPL Log')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    main(args)