#!/usr/bin/env python3
import re
import requests
import random
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timezone, timedelta
from matplotlib_helper import *
from dataclasses import dataclass
import time
import numpy as np
import argparse
import math
import calendar
import os
import ast

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
        
# Plotting

def plot_carbon_api_response(data: dict, show_events=True, show_transfer_breakdown = True, show_compute=True, show_transfer=True):
    fig, axes = plt.subplots(1, 1, figsize=(12, 6))

    d_region_colors = {}
    for region in data['details']:
        d_region_colors[region] = get_next_color()

    # Extract emission integral data
    for (ax, series_name) in zip([axes], ["emission_rates", "emission_integral"]):
        if series_name == 'emission_integral':
            continue
        # # Get max value for y-axis
        # max_y_value = get_max_value(data['details'], series_name)

        for region in data['details']:
            # if region == 'Azure:eastus':
            #     continue
            print(f"Plotting {region} - {series_name}")
            compute_data = data["details"][region][series_name]["compute"]
            transfer_data = data["details"][region][series_name]["transfer"]
            transfer_network_data = data["details"][region][series_name]["transfer.network"]
            transfer_endpoint_data = data["details"][region][series_name]["transfer.endpoint"]
            timings = data["details"][region]['timings'][0] # Assume single occurence per job
            min_start = datetime.fromisoformat(timings['min_start'])
            max_end = datetime.fromisoformat(timings['max_end'])
            carbon_emissions_compute = data['raw-scores'][region]['carbon-emission-from-compute']
            carbon_emissions_transfer = data['raw-scores'][region]['carbon-emission-from-migration']

            # Convert timestamp strings to datetime objects
            compute_df = create_dataframe_for_plotting(compute_data, min_start, max_end)
            transfer_df = create_dataframe_for_plotting(transfer_data, min_start, max_end)
            transfer_network_df = create_dataframe_for_plotting(transfer_network_data, min_start, max_end)
            transfer_endpoint_df = create_dataframe_for_plotting(transfer_endpoint_data, min_start, max_end)

            # Plot timeseries data as step functions
            color = d_region_colors[region]
            if show_compute:
                compute_time = pd.to_timedelta(timings['compute_duration']).floor('s').to_pytimedelta()
                label_compute = f"{region} - Compute ({carbon_emissions_compute:.3f} gCO2 over {compute_time})"
                ax.step(compute_df["Timestamp"], compute_df["Value"], label=label_compute, color=color, linestyle="solid")
            if show_transfer and not transfer_df.empty:
                hop_count = data["details"][region]["route.hop_count"]
                carbon_route_raw_strings = data["details"][region]['route']
                router_hop_isos = '|'.join(filter(lambda x: x is not None, map(lambda x: parse_carbon_route(x, "region"), carbon_route_raw_strings)))
                total_transfer_time = pd.to_timedelta(timings['total_transfer_time']).floor('s').to_pytimedelta()
                if show_events:
                    label_transfer = f"{region} - Transfer ({carbon_emissions_transfer:.3f} gCO2 over {total_transfer_time})"
                else:
                    label_transfer = f"{region} - Transfer ({hop_count} hops: {router_hop_isos})"
                ax.step(transfer_df["Timestamp"], transfer_df["Value"], label=label_transfer, color=color, linestyle="dashed")
                if show_transfer_breakdown:
                    ax.step(transfer_network_df["Timestamp"], transfer_network_df["Value"], label=f"{region} - Transfer (network)", color=color, linestyle="dotted")
                    ax.step(transfer_endpoint_df["Timestamp"], transfer_endpoint_df["Value"], label=f"{region} - Transfer (endpoint)", color=color, linestyle="dashdot")

            # Add events based on the timings
            max_y_value = max(compute_df["Value"].max(), transfer_df["Value"].max())
            for event in d_events if show_events else []:
                df = compute_df if event == 'compute' else transfer_df
                if df.empty:
                    continue
                # Vertical lines and texts
                for name in d_events[event]['interval_keys']:
                    add_timing(ax, name, pd.to_datetime(timings[name]), max_y_value, color=d_region_colors[region])
                # Fill area for events under the curve
                (start_event, end_event) = d_events[event]['interval_keys']
                mask = (df['Timestamp'] >= pd.to_datetime(timings[start_event])) & (df['Timestamp'] <= pd.to_datetime(timings[end_event]))
                alpha = 0.5 if 'compute' in event else 0.25
                ax.fill_between(x=df['Timestamp'], y1=df['Value'], where=mask, color=color, alpha=alpha)

        ax.set_title(metadata[series_name]['title'])
        ax.set_xlabel("Time")
        ax.set_ylabel(metadata[series_name]['ylabel'])
        ax.grid(True)

    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.show()

def parse_carbon_route(route: str, output="coordinates"):
    # route = "Router at (39.0127, -77.5342) (emap:US-MIDA-PJM)"
    regex = r"Router at \((?P<lat>-?\d+\.\d+), (?P<lon>-?\d+\.\d+)\) \(emap:(?P<region>.+)\)"
    match = re.match(regex, route)
    if match:
        if output == "coordinates":
            return (float(match.group("lat")), float(match.group("lon")))
        elif output == "region":
            return match.group("region")
        elif output is None:
            return match.groupdict()
        else:
            raise ValueError(f"Invalid output type: {output}")
    else:
        return None

runtime_s = timedelta(seconds=3600).total_seconds()

# See parameter definition in class `Workload` at https://github.com/c3lab-net/energy-data/blob/master/api/models/workload.py
payload = {
    "runtime": runtime_s,
    "schedule": {
        "type": "onetime",
        "start_time": "2022-01-02T00:00:00-00:00",
        "max_delay": 24*3600 - runtime_s
    },
    "dataset": {
        "input_size_gb": 1024,
        "output_size_gb": 1024,
    },
    # Provide EITHER candidate_providers OR candidate_locations
    "candidate_providers": [
        "AWS",
        "gcloud"
    ],
    # "candidate_locations": [
    #     {
    #         "id": "AWS:us-east-1"
    #     },
    #     {
    #         "id": "AWS:us-west-1"
    #     },
    #     {
    #         "id": "AWS:eu-central-1"
    #     },
    # ],
    "use_prediction": False,
    # emap has the most coverage worldwide
    "carbon_data_source": "emap",
    "watts_per_core": 0,
    "core_count": 20,
    "original_location": "AWS:us-east-1",
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

# pprint.pprint(cloud_regions_by_provider)


CARBON_API_URL='http://yak-03.sysnet.ucsd.edu/carbon-aware-scheduler/'

# # Make the API call
# response = requests.get(CARBON_API_URL, json=payload)

# # Check if the API call was successful (status code 200)
# assert response.ok, f"Error: API call failed with status code {response.status_code}: {response.text}"
# data = response.json(parse_float=lambda s: float('%.6g' % float(s)))
# print(json.dumps(data, indent=4))

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
# Plotting


def plot_cdf(max_data, min_data, avg_data, file_name="cdf.png"):
    max_data = [x for x in max_data if not math.isnan(x)]
    min_data = [x for x in min_data if not math.isnan(x)]
    avg_data = [x for x in avg_data if not math.isnan(x)]

    # Function to calculate and plot CDF
    def calculate_and_plot_cdf(data, label):
        # Convert the list to a numpy array and sort
        data = np.sort(np.array(data))

        # Calculate the CDF values
        cdf = np.arange(1, len(data) + 1) / len(data)

        # Plotting
        plt.plot(data, cdf, marker='.', linestyle='none', label=label, markersize=3)

    # Plot each dataset
    calculate_and_plot_cdf(max_data, 'max')
    calculate_and_plot_cdf(min_data, 'min')
    calculate_and_plot_cdf(avg_data, 'avg')

    # Add labels and title
    plt.xlabel('CIDT (gCO2/Gb)')
    plt.ylabel('Cumulative Distribution')
    plt.title('CDF of Daily Average CIDT across all AWS+GCP region pairs')

    # Add grid and legend
    plt.grid(True)
    plt.legend()
    plt.xlim(0, 0.1)
    plt.ylim(0, 1)
    
    std_max = np.std(max_data)
    std_min = np.std(min_data)
    std_avg = np.std(avg_data)
    
    plt.text(0.05, 0.05, f'Standard Deviations:\nmax: {std_max:.2f}, min: {std_min:.2f}, avg: {std_avg:.2f}',
             fontsize=8, bbox=dict(facecolor='white', alpha=0.5), horizontalalignment='left', verticalalignment='bottom')

    # Save and show the plot
    plt.savefig(file_name)
    plt.show()


def get_single_day_info(data: dict):
    max_result = {}
    min_result = {}
    avg_result = {}
    error_region = []
    
    original_pos = data["original-region"]
    for key, _ in data["warnings"].items():
        error_region.append((data["original-region"], key))
    
    # Extract emission integral data
    for series_name in ["emission_rates", "emission_integral"]:
        if series_name == 'emission_integral':
            continue

        # print("the following is in data", len(data['details']))
        for region in data['details']:
            region_array = []
            transfer_data = data["details"][region][series_name]["transfer"]
            timings = data["details"][region]['timings'][0] # Assume single occurence per job
            min_start = datetime.fromisoformat(timings['min_start'])
            max_end = datetime.fromisoformat(timings['max_end'])

            # Convert timestamp strings to datetime objects
            transfer_df = create_dataframe_for_plotting(transfer_data, min_start, max_end)


            if not transfer_df.empty:
                region_array.append(transfer_df["Value"])
            # else:
            #     # print(f"{region} has no data")
            if region_array:
                max_result[(original_pos, region)] = np.max(region_array)
                min_result[(original_pos, region)] = np.min(region_array)
                avg_result[(original_pos, region)] = np.mean(region_array)
    return max_result, min_result, avg_result, error_region

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--folder-path', required=True, help='The directory to save all datas to')
    parser.add_argument('--inter_region_route_source', required=True)
    args = parser.parse_args()

    return args

def plot_annual_cdf(min_data, file_name="cdf.png"):
    min_data = [x for x in min_data if not math.isnan(x)]

    # Function to calculate and plot CDF
    def calculate_and_plot_cdf(data, label):
        # Convert the list to a numpy array and sort
        data = np.sort(np.array(data))

        # Calculate the CDF values
        cdf = np.arange(1, len(data) + 1) / len(data)

        # Plotting
        plt.plot(data, cdf, marker='.', linestyle='none', label=label, markersize=3)

    # Plot each dataset
    calculate_and_plot_cdf(min_data, 'CIDT')

    # Add labels and title
    plt.xlabel('CIDT (gCO2/Gb)')
    plt.ylabel('Cumulative Distribution')
    plt.title('CDF of daily minimum CIDT across all AWS+GCP region pairs in 2022')

    # Add grid and legend
    plt.grid(True)
    plt.legend()
    plt.xlim(0, 0.1)
    plt.ylim(0, 1)
    

    # Save and show the plot
    plt.savefig(file_name)
    plt.show()
    
def get_annual_figure(folder_path):
    files = os.listdir(folder_path)


    def extract_data(line):
        
        list_regex = r'\[.*?\]'


        # Find all matches in the string
        matches = re.findall(list_regex, line)
        result = []
        for item in matches:
            result += ast.literal_eval(item)
        return result
        
    all_max_list = []
    all_min_list = []
    all_avg_list = []

    for file in files:
        if file.endswith(".txt"):
            with open(os.path.join(folder_path, file), "r") as f:
                max_list, min_list, avg_list = None, None, None
                for line in f:
                    if line.startswith("min"):
                        min_list = extract_data(line)
                        all_min_list += min_list


    plot_annual_cdf(all_min_list, file_name= folder_path + "../third_all_days.png")

def main():
    args = parse_args()    
    
    os.makedirs(args.folder_path, exist_ok=True)
    
    os.makedirs(args.folder_path + "/dict/", exist_ok=True)
    os.makedirs(args.folder_path + "/figure/", exist_ok=True)
    os.makedirs(args.folder_path + "/data/", exist_ok=True)
    

    init_time = time.time()
    month_epoch_start_time = time.time()
    datetime_object = datetime.fromtimestamp(init_time)

    # Format datetime object into a string
    readable_format = datetime_object.strftime('%Y-%m-%d %H:%M:%S')
    print("start time", readable_format)

    all_original_pos, all_original_pos_pair = get_all_orginal_pos()
    
    payload["inter_region_route_source"] = args.inter_region_route_source
    
    for month in range(1, 13): 
        
        monthly_all_region_pair_max_list_dict = {}
        monthly_all_region_pair_min_list_dict = {}
        monthly_all_region_pair_avg_list_dict = {}
        monthly_all_region_pair_max_value = []
        monthly_all_region_pair_min_value = []
        monthly_all_region_pair_avg_value = []
        error_region = []
        
        figure_path = args.folder_path + "/figure/" + str(month) + ".png"
        data_path = args.folder_path + "/data/" + str(month) + ".txt"
        dict_path = args.folder_path + "/dict/" + str(month) + ".txt"
        
        for per_day in calendar.monthrange(2022, month)[1]:
            start_time = datetime(2022, month, 1, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=per_day)
            start_time += timedelta(seconds=random.randint(0, 3600 * 24))

            payload['schedule']['start_time'] = start_time.isoformat()
            for original_pos in all_original_pos:

                payload["original_location"] = original_pos

                response = requests.get(CARBON_API_URL, json=payload)

                # Check if the API call was successful (status code 200)
                # print(f"{response.text}")
                if not response.ok:
                    # print(f"Error: API call failed with status code {response.status_code}: {response.text}")
                    continue
                # assert response.ok, f"Error: API call failed with status code {response.status_code}: {response.text}"
                data = response.json(parse_float=lambda s: float('%.6g' % float(s)))


                daily_max_dict, daily_min_dict, daily_avg_dict, daily_error_region = get_single_day_info(data)

                for key, value in daily_max_dict.items():
                    if key in monthly_all_region_pair_max_list_dict:
                        monthly_all_region_pair_max_list_dict[key].append(value)
                    else:
                        monthly_all_region_pair_max_list_dict[key] = [value]
                for key, value in daily_min_dict.items():
                    if key in monthly_all_region_pair_min_list_dict:
                        monthly_all_region_pair_min_list_dict[key].append(value)
                    else:
                        monthly_all_region_pair_min_list_dict[key] = [value]
                for key, value in daily_avg_dict.items():
                    if key in monthly_all_region_pair_avg_list_dict:
                        monthly_all_region_pair_avg_list_dict[key].append(value)
                    else:
                        monthly_all_region_pair_avg_list_dict[key] = [value]
                error_region += daily_error_region
                    
            print("time cost for one day in minute", (time.time() - month_epoch_start_time)/60)
            month_epoch_start_time = time.time()
        
        # print(error_region)
        
        
        with open(dict_path, 'w') as f:
            f.write(f"max: {monthly_all_region_pair_max_list_dict}\n")
            f.write(f"min: {monthly_all_region_pair_min_list_dict}\n")
            f.write(f"avg: {monthly_all_region_pair_avg_list_dict}\n")
            f.write(f"error_region: {error_region}\n")  
        
        # for key, value in monthly_all_region_pair_max_list_dict.items():
        #     monthly_all_region_pair_max_value.append(np.mean(value))
        # for key, value in monthly_all_region_pair_min_list_dict.items():
        #     monthly_all_region_pair_min_value.append(np.mean(value))
        # for key, value in monthly_all_region_pair_avg_list_dict.items():
        #     monthly_all_region_pair_avg_value.append(np.mean(value))
        
        for region_pair in all_original_pos_pair:
            if region_pair in monthly_all_region_pair_max_list_dict:
                monthly_all_region_pair_max_value.append(np.mean(monthly_all_region_pair_max_list_dict[region_pair]))
            else:
                monthly_all_region_pair_max_value.append(math.nan)
            if region_pair in monthly_all_region_pair_min_list_dict:
                monthly_all_region_pair_min_value.append(np.mean(monthly_all_region_pair_min_list_dict[region_pair]))
            else:
                monthly_all_region_pair_min_value.append(math.nan)
            if region_pair in monthly_all_region_pair_avg_list_dict:
                monthly_all_region_pair_avg_value.append(np.mean(monthly_all_region_pair_avg_list_dict[region_pair]))
            else:
                monthly_all_region_pair_avg_value.append(math.nan)
        
        print("time cost for all", (time.time() - init_time)/60)
        print(len(monthly_all_region_pair_max_value))
        plot_cdf(monthly_all_region_pair_max_value, monthly_all_region_pair_min_value, monthly_all_region_pair_avg_value, figure_path)
        
        with open(data_path, 'w') as f:
            f.write(f"max: {monthly_all_region_pair_max_value}\n")
            f.write(f"min: {monthly_all_region_pair_min_value}\n")
            f.write(f"avg: {monthly_all_region_pair_avg_value}\n")
    get_annual_figure(args.folder_path + "/dict/")

if __name__ == "__main__":
    main()