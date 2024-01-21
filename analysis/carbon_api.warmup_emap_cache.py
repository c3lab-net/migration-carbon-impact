#!/usr/bin/env python3

import argparse
import json
from multiprocessing import Pool
import time
from typing import Optional
import requests

CLOUD_PROVIDERS = ['AWS', 'gcloud']
CARBON_API_HOST = 'http://yak-03.sysnet.ucsd.edu'
# CARBON_API_HOST = 'http://localhost:8082'
CARBON_API_URL=f'{CARBON_API_HOST}/carbon-aware-scheduler/'

def parse_args():
    parser = argparse.ArgumentParser(description='Process TSV files and add columns.')
    parser.add_argument('--inter-region-route-source', type=str, required=True,
                        help='The inter-region route source',
                        choices=[
                            'itdk',
                            'igdb.no-pops',
                            'igdb.with-pops',
                            'itdk+igdb.no-pops',
                            'itdk+igdb.with-pops',
                            ])
    parser.add_argument('-P', '--parallelism', type=int, help='The number of parallel processes to use', default=1)
    parser.add_argument('-G', '--group-by', required=True, choices=['src-region', 'region-pair'])
    parser.add_argument('-C', '--completed-pairs', type=argparse.FileType('r'),
                        help='The file containing the list of completed pairs')
    args = parser.parse_args()

    return args

def get_cloud_regions(cloud_provider: str) -> list[str]:
    """Get a list of regions for a given cloud provider.
    
        Args:
            cloud_provider: The cloud provider name.
    """
    response = requests.get(f"{CARBON_API_HOST}/metadata/cloud-location/locations/{cloud_provider}/")
    assert response.ok, f"Error: API call failed with status code {response.status_code}: {response.text}"
    regions = response.json()
    return list(regions)

def get_input_list(group_by: str) -> list[tuple[str, Optional[str]]]:
    cloud_regions_by_provider: dict[str, list[str]] = {}

    for cloud_provider in CLOUD_PROVIDERS:
        cloud_regions = get_cloud_regions(cloud_provider)
        cloud_regions_by_provider[cloud_provider] = cloud_regions
        print(f"{cloud_provider}: {len(cloud_regions)} regions")

    all_region_ids = []
    for cloud in CLOUD_PROVIDERS:
        for region in cloud_regions_by_provider[cloud]:
            all_region_ids.append(f"{cloud}:{region}")

    input_list = []
    if group_by == 'region-pair':
        for src in all_region_ids:
            for dst in all_region_ids:
                input_list.append((src, dst))
    else:
        for src in all_region_ids:
            input_list.append((src, None))
    return input_list

PAYLOAD = {'runtime': 3600.0, 'schedule': {'type': 'onetime', 'start_time': '2022-04-10T00:00:00+00:00', 'max_delay': 82800.0}, 'dataset': {'input_size_gb': 1, 'output_size_gb': 1}, 'candidate_locations': [], 'use_prediction': False, 'carbon_data_source': 'emap', 'watts_per_core': 0, 'core_count': 1, 'original_location': 'AWS:us-east-1', 'optimize_carbon': False, 'carbon_accounting_mode': 'compute-and-network', 'inter_region_route_source': 'itdk+igdb.no-pops'}

def get_completed_pairs(file) -> list[tuple[str, str]]:
    """Get a list of (src, dst) pairs that have already been completed.
    
        Args:
            filename: The name of the file containing the list of completed pairs.
    """
    completed_pairs = []
    with file as f:
        for line in f:
            src, dst = line.strip().split('\t')
            completed_pairs.append((src, dst))
    return completed_pairs

completed_pairs: list[tuple[str, str]] = []

# Make the API call
def call_carbon_api(region_pair: tuple[str, str]):
    if region_pair in completed_pairs:
        # print(f"[DEBUG] Skipping {region_pair} because it's already been completed", flush=True)
        return

    # print(f"[DEBUG] Processing {region_pair}", flush=True)
    src, dst = region_pair

    t_start = time.time()

    PAYLOAD['original_location'] = src
    if dst:
        if 'candidate_providers' in PAYLOAD:
            del PAYLOAD['candidate_providers']
        PAYLOAD['candidate_locations'] = [{'id': dst}]
    else:
        if 'candidate_locations' in PAYLOAD:
            del PAYLOAD['candidate_locations']
        PAYLOAD['candidate_providers'] = ['AWS', 'gcloud']
    response = requests.get(CARBON_API_URL, json=PAYLOAD, timeout=300)

    t_end = time.time()
    print(f"[INFO] {src} -> {dst}: {t_end - t_start:.2f} seconds", flush=True)

    if not response.ok:
        print(f"[ERROR] {src} -> {dst}: {response.status_code}")
    # data = response.json(parse_float=lambda s: float('%.6g' % float(s)))
    # print(json.dumps(data, indent=4))


def main():
    args = parse_args()

    if args.completed_pairs:
        global completed_pairs
        completed_pairs = get_completed_pairs(args.completed_pairs)
        print('completed pairs:', len(completed_pairs))
        # for completed_pair in completed_pairs:
        #     print(completed_pair)

    global PAYLOAD
    PAYLOAD['inter_region_route_source'] = args.inter_region_route_source

    all_region_pairs = get_input_list(args.group_by)
    with Pool(args.parallelism) as pool:
        _ = pool.map(call_carbon_api, all_region_pairs)

if __name__ == '__main__':
    main()
