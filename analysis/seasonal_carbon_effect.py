#!/usr/bin/env python3
import re
import requests
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timezone, timedelta
from matplotlib_helper import *
import time
import numpy as np
import argparse
import os
from concurrent.futures import ProcessPoolExecutor
import concurrent
# Metadata

metadata = {
    'emission_rates': {
        'ylabel': 'gCO2/s',
        'title': 'Instantaneous emission rates'
    },
    'emission_integral': {
        'ylabel': 'gCO2',
        'title': 'Emission integral over its duration'
    },
}

d_timing_labels = {
    "input_transfer_start": "Input transfer",
    # "input_transfer_start": "Start of input transfer",
    # "input_transfer_end": "End of input transfer",
    "compute_start": "Compute",
    # "compute_start": "Start of compute",
    # "compute_end": "End of compute",
    "output_transfer_start": "Output transfer",
    # "output_transfer_start": "Start of output transfer",
    # "output_transfer_end": "End of output transfer",
}

d_events = {
    'input_transfer': {
        'interval_keys': ("input_transfer_start", "input_transfer_end"),
        'label': 'Input transfer',
    },
    'compute': {
        'interval_keys': ("compute_start", "compute_end"),
        'label': 'Compute',
    },
    'output_transfer': {
        'interval_keys': ("output_transfer_start", "output_transfer_end"),
        'label': 'Output transfer',
    },
}

def get_max_value(data_details: dict, series_name: str):
    max_value = 0
    for region in data_details:
        compute_data = data_details[region][series_name]["compute"]
        transfer_data = data_details[region][series_name]["transfer"]
        max_value = max(max_value, max(compute_data.values(), default=0), max(transfer_data.values(), default=0))
    return max_value

def resample_timeseries(df: pd.DataFrame, interval: str):
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df.set_index("Timestamp", inplace=True)
    df_resampled = df.resample(interval).ffill().reset_index()
    return df_resampled

def create_dataframe_for_plotting(timeseries: dict[str, float], min_start: datetime, max_end: datetime) -> pd.DataFrame:
    """Convert a time series data to a dataframe, while removing out of bound timestamps.
    
        Args:
            timeseries: A dictionary of timestamp strings and values.
            min_start: The minimum cutoff time for the timeseries.
            max_end: The maximum cutoff time for the timeseries.
    """
    timeseries_in_datatime = {datetime.fromisoformat(key): value for key, value in timeseries.items()}
    df = pd.DataFrame(list(timeseries_in_datatime.items()), columns=["Timestamp", "Value"])
    if df.empty:
        return df
    resampled = resample_timeseries(df, "30s")
    mask = (resampled["Timestamp"] >= pd.to_datetime(min_start)) & (resampled["Timestamp"] <= pd.to_datetime(max_end))
    return resampled[mask]

def add_timing(ax, name: str, time: pd.Timestamp, max_value: float, color: str):
    if 'start' in name:
        ax.vlines(time, ymin=0, ymax=max_value, color='gray', alpha=0.5, linestyles="solid" if 'compute' in name else "dashed")
        if 'input' in name:
            ha = 'right'
            rotation = -30
        elif 'output' in name:
            ha = 'left'
            rotation = 30
        else:
            ha = 'center'
            rotation = 0
        ax.text(time, max_value, d_timing_labels[name], color=color, alpha=0.95, ha=ha, va="bottom", rotation=rotation)
        

runtime_s = timedelta(seconds=3600).total_seconds()

# See parameter definition in class `Workload` at https://github.com/c3lab-net/energy-data/blob/master/api/models/workload.py
payload = {
    "runtime": runtime_s,
    "schedule": {
        "type": "onetime",
        "start_time": "2022-01-02T00:00:00-00:00",
        "max_delay": timedelta(days=30).total_seconds() - runtime_s
    },
    "dataset": {
        "input_size_gb": 1024,
        "output_size_gb": 1024,
    },
    # Provide EITHER candidate_providers OR candidate_locations
    # "candidate_providers": [
    #     "AWS",
    #     "gcloud"
    # ],
    "candidate_locations": [
        {
            "id": "AWS:us-west-1"
        }
        # {
        #     "id": "AWS:us-west-1"
        # },
        # {
        #     "id": "AWS:us-east-2"
        # },
    ],
    "use_prediction": False,
    # emap has the most coverage worldwide
    "carbon_data_source": "emap",
    "watts_per_core": 0,
    "core_count": 20,
    "original_location": "AWS:us-west-1",
    # Note: turn off optimize_carbon if you don't need the timing information, e.g. just raw timeseries carbon data
    "optimize_carbon": False,
    # "use_new_optimization": True,   # defaults value, can ignore
    # Most of the case we consider both compute and network
    "carbon_accounting_mode": "compute-and-network",
    # Accepted values are defined in enum `InterRegionRouteSource` at https://github.com/c3lab-net/energy-data/blob/master/api/models/cloud_location.py
    "inter_region_route_source": "itdk",
}

# Get all regions that we cover

CLOUD_PROVIDERS = ['AWS', 'gcloud']

cloud_regions_by_provider: dict[str, list[str]] = {}

def get_cloud_regions(cloud_provider: str) -> list[str]:
    """Get a list of regions for a given cloud provider.
    
        Args:
            cloud_provider: The cloud provider name.
    """
    CARBON_API_HOST = 'http://yak-03.sysnet.ucsd.edu'
    response = requests.get(f"{CARBON_API_HOST}/metadata/cloud-location/locations/{cloud_provider}/")
    assert response.ok, f"Error: API call failed with status code {response.status_code}: {response.text}"
    regions = response.json()
    return list(regions)

for cloud_provider in CLOUD_PROVIDERS:
    cloud_regions_by_provider[cloud_provider] = get_cloud_regions(cloud_provider)


CARBON_API_URL='http://yak-03.sysnet.ucsd.edu/carbon-aware-scheduler/'


def get_all_orginal_pos():
    all_original_pos = []
    for item in get_cloud_regions("AWS"):
        all_original_pos.append("AWS:" + item)
    for item in get_cloud_regions("gcloud"):
        all_original_pos.append("gcloud:" + item)
        
    # sort to ensure the order is always the same
    all_original_pos = sorted(all_original_pos)
    all_original_pos_pair = [(src, dst) for src in all_original_pos for dst in all_original_pos if src != dst]
    return all_original_pos, all_original_pos_pair


def get_monthly_info(data: dict, cidt_type):
    monthly_max_dict = {}
    monthly_min_dict = {}
    monthly_avg_dict = {}
    error_region = []
    
    original_pos = data["original-region"]
    for key, _ in data["warnings"].items():
        error_region.append((data["original-region"], key))
    
    # Extract emission integral data
    for series_name in ["emission_rates", "emission_integral"]:
        if series_name == 'emission_integral':
            continue

        for region in data['details']:
            region_array = []
            transfer_data = data["details"][region][series_name][cidt_type]
            timings = data["details"][region]['timings'][0] # Assume single occurence per job
            min_start = datetime.fromisoformat(timings['min_start'])
            max_end = datetime.fromisoformat(timings['max_end'])

            # Convert timestamp strings to datetime objects
            transfer_df = create_dataframe_for_plotting(transfer_data, min_start, max_end)

            transfer_df['Timestamp'] = pd.to_datetime(transfer_df['Timestamp'])

            # Create a new column for the date (ignoring time)
            transfer_df['Date'] = transfer_df['Timestamp'].dt.date
            transfer_df['Hour'] = transfer_df['Timestamp'].dt.hour

            # Group the DataFrame by the "Date" column and calculate the minimum value for each group
            max_data = transfer_df.groupby('Hour')['Value'].max()
            min_data = transfer_df.groupby('Hour')['Value'].min()
            avg_data = transfer_df.groupby('Hour')['Value'].mean()
            
            
            if avg_data.values.size == 0:
                continue
            else:
                return avg_data.values

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-year', required=True, type=int, help='The year to start the simulation')
    parser.add_argument('--original-pos', required=True, type=str, help='The original pos to run the simulation')
    parser.add_argument('--dst-pos', required=True, type=str, help='The destination pos to run the simulation')
    parser.add_argument('--inter-region-route-source', required=True, type=str, help='The inter region route source to run the simulation')
    args = parser.parse_args()

    return args

    
def fetch_data(payload):
    """
    Function to make an API call with the given payload.
    Returns the JSON response or None if the call fails.
    """
    try:
        response = requests.get(CARBON_API_URL, json=payload)
        if response.ok:
            return response.json(parse_float=lambda s: float('%.6g' % float(s)))
        else:
            print(f"Error: API call failed with status code {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred during API call: {e}")
        return None

def fig_plot(data, original_pos, dst_pos, cidt_type):
    # Create a list of months for labeling
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    # Create a list of linestyle for labeling
    linestyles = ['solid', 'solid', 'solid', 'dashed', 'dashed', 'dashdot', 'dashdot', 'dashed', 'dashdot', 'solid', 'solid', 'solid']

    # Create a list of colors
    colors = ['#006400', '#008000', '#228B22', '#FF4500', '#FF0000', '#FF1493', '#FF69B4', '#FFA500', '#FFD700', '#0000FF', '#000080', '#008080']

    plt.tight_layout()
    plt.figure(figsize=(13, 6))  # Adjust width and height as needed
    

    # Create x-axis values (hours from 0 to 23)
    hours = list(range(24))

    # Set x-axis ticks every 4 units
    plt.xticks(range(0, 24, 4))

    # Plot each month's data with marker
    for i, month_data in enumerate(data):
        plt.plot(hours, month_data, label=months[i], color=colors[i], linestyle=linestyles[i], marker='.')

    # Set labels and title
    plt.xlabel('Hours')
    plt.xlim(0, 23)
    plt.ylim(0, 0.04)
    plt.ylabel('gCO2/Gb')
    plt.title(f'{original_pos} to {dst_pos} monthly {cidt_type} CIDT')
    
    
    fig_name = original_pos + "_" + dst_pos + "_" + cidt_type + ".png"

    # Add a legend
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

    # Show the plot
    plt.show()

    plt.savefig(f"{original_pos}-{dst_pos}-CIDT/{fig_name}")

def main():
    args = parse_args()     
    
    init_time = time.time()
    month_epoch_start_time = time.time()
    datetime_object = datetime.fromtimestamp(init_time)

    # Format datetime object into a string
    readable_format = datetime_object.strftime('%Y-%m-%d %H:%M:%S')

    all_original_pos, all_original_pos_pair = get_all_orginal_pos()
    
    all_original_pos = [args.original_pos]
    
    cidt_type_list = ["transfer.network", "transfer.endpoint", "transfer"]
    os.makedirs(f"{args.original_pos}-{args.dst_pos}-CIDT", exist_ok=True)
    
    for cidt_type in cidt_type_list:
        year_data = []
    
        for inter_region_route_source in [args.inter_region_route_source]:
            
            
            payload["inter_region_route_source"] = inter_region_route_source
            

            time_range = range(1, 13)
                
            
            for month in time_range: 
                

                args.start_year = int(args.start_year)
                        
                start_time = datetime(args.start_year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
                # start_time += timedelta(seconds=random.randint(0, 3600 * 24))

                payload['schedule']['start_time'] = start_time.isoformat()
                
                with ProcessPoolExecutor(max_workers=128) as executor:
                    future_to_payload = {executor.submit(fetch_data, dict(payload, original_location=original_pos)): original_pos for original_pos in all_original_pos}
                    
                    for future in concurrent.futures.as_completed(future_to_payload):
                        original_pos = future_to_payload[future]
                        try:
                            data = future.result()
                            if data:
                                monthly_data = get_monthly_info(data, cidt_type)
                                year_data.append(monthly_data)
                        except Exception as e:
                            print(f"Exception in main processing loop: {e}")
                            
                    month_epoch_start_time = time.time()
                
                
            
            fig_plot(year_data, args.original_pos, args.dst_pos, cidt_type)

            
            

if __name__ == "__main__":
    main()