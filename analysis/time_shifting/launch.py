#!/usr/bin/env python3

import json
import csv
import re
import requests
import matplotlib.pyplot as plt
from matplotlib.dates import *
from matplotlib.ticker import *
import pandas as pd
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
import numpy as np

from enum import Enum

from collections import defaultdict
from typing import Optional

from multiprocessing import Pool

import geopandas


class ScheduleType(str, Enum):
    UNIFORM_RANDOM = "uniform-random"
    POISSON = "poisson"
    ONETIME = "onetime"

class CarbonAccountingMode(str, Enum):
    ComputeOnly = "compute-only"
    ComputeAndNetwork = "compute-and-network"

class CarbonDataSource(str, Enum):
    C3Lab = "c3lab"
    Azure = "azure"
    EMap = "emap"

class InterRegionRouteSource(str, Enum):
    ITDK = "itdk"
    IGDB_NO_POPS = "igdb.no-pops"
    IGDB_WITH_POPS = "igdb.with-pops"
    ITDK_AND_IGDB_NO_POPS = "itdk+igdb.no-pops"
    ITDK_AND_IGDB_WITH_POPS = "itdk+igdb.with-pops"

@dataclass
class Dataset:
    input_size_gb: float
    output_size_gb: float

@dataclass
class WorkloadSchedule:
    start_time: datetime
    type: Optional[ScheduleType] = ScheduleType.ONETIME
    max_delay: Optional[timedelta] = timedelta()

    def asdict(self) -> dict:
        d = asdict(self)
        d["start_time"] = self.start_time.isoformat()
        d["type"] = self.type.value
        d["max_delay"] = self.max_delay.total_seconds()
        return d

@dataclass
class Workload:
    runtime: timedelta
    schedule: WorkloadSchedule
    dataset: Dataset

    original_location: str


    carbon_data_source: CarbonDataSource = CarbonDataSource.EMap
    use_prediction: bool = field(default=False)
    optimize_carbon: bool = field(default=True)

    watts_per_core: float = field(default=5.0)
    core_count: float = field(default=1.0)

    use_new_optimization: bool = field(default=True)
    carbon_accounting_mode: CarbonAccountingMode = CarbonAccountingMode.ComputeAndNetwork
    candidate_providers: Optional[list[str]] = None
    candidate_locations: Optional[list[str]] = None
    # desired_renewable_ratio: Optional[float] = 1.0

    def asdict(self) -> dict:
        d = asdict(self)
        d["schedule"] = self.schedule.asdict()
        d["runtime"] = self.runtime.total_seconds()
        d["carbon_accounting_mode"] = self.carbon_accounting_mode.value
        d["carbon_data_source"] = self.carbon_data_source.value
        return d

    inter_region_route_source: InterRegionRouteSource = InterRegionRouteSource.ITDK





def get_best_region(original_region: str, raw_scores: dict) -> str:
    min_co2e = raw_scores[original_region]["carbon-emission"]
    min_region = original_region
    for region, scores in raw_scores.items():
        if scores["carbon-emission"] < min_co2e:
            min_co2e = scores["carbon-emission"]
            min_region = region

    return min_region


CARBON_API_URL='http://yak-03.sysnet.ucsd.edu/carbon-aware-scheduler/'






def make_api_call(region, t, max_delay, runtime, name, input_size_gb, output_size_gb, core_count, watts_per_core):

    wl =  Workload(
                        runtime=runtime,
                        schedule=WorkloadSchedule(
                            start_time=t,
                            max_delay=max(max_delay - runtime, timedelta()),
                        ),
                        dataset=Dataset(
                            input_size_gb=input_size_gb,
                            output_size_gb=output_size_gb,
                        ),
                        core_count=core_count,
                        original_location=region,
                        candidate_providers=["AWS"],
                        watts_per_core=watts_per_core,
                        inter_region_route_source=InterRegionRouteSource.ITDK_AND_IGDB_WITH_POPS,
                    ).asdict()


    response = requests.get(CARBON_API_URL, json=wl)
    d = response.json(parse_float=lambda s: float('%.6g' % float(s)))
    series = pd.Series(d)
    path = f"results_workload/{name}_{region}_{t.isoformat()}_{max_delay}.pkl"
    try:
        series.to_pickle(path)
    except:
        print("problem with: " + path)



#def make_api_call(region, t, max_delay):
#    print(region, t, runtime, max_delay)
#    response = requests.get(CARBON_API_URL, json=Workload(
#        runtime=runtime,
#        schedule=WorkloadSchedule(
#            start_time=t,
#            max_delay=max(max_delay - runtime, timedelta()),
#        ),
#        dataset=Dataset(
#            input_size_gb=250,
#            output_size_gb=250
#        ),
#        core_count=100,
#        original_location=region,
#        candidate_providers=["AWS"],
#        inter_region_route_source=InterRegionRouteSource.ITDK_AND_IGDB_WITH_POPS,
#    ).asdict())
#    d = response.json(parse_float=lambda s: float('%.6g' % float(s)))
#    series = pd.Series(d)
#    try:
#        series.to_pickle(f"results_uniform_time/{region}_{t.isoformat()}_{runtime}_{max_delay}.pkl")
#    except:
#        print("problem with: " + f"results_uniform_time/{region}_{t.isoformat()}_{runtime}_{max_delay}.pkl")


if __name__ == "__main__":
    with open('../workloads.csv', newline='') as csvfile:
        workloads = list(csv.DictReader(csvfile))

    print([w["\ufeffname"] for w in workloads])
    
    start_times = pd.date_range(
        start=pd.to_datetime("6/1/2023").tz_localize("UTC"),
        end=pd.to_datetime("6/29/2023").tz_localize("UTC"),
        freq="1h",
    )
    regions = ["AWS:us-west-1", "AWS:eu-central-1"]
    delays = [timedelta(hours=h) for h in (0, 4, 24)]

    args = []

    for region in regions:
        for t in start_times:
            for max_delay in delays:
                for workload in workloads:
                    runtime = timedelta(seconds=float(workload["runtime_s"]))
                    name = workload["\ufeffname"]
                    input_size_gb = float(workload["input_gb"])
                    output_size_gb = float(workload["output_gb"])
                    core_count = float(workload["core_count"])
                    watts_per_core = float(workload["watts/core"])
                    args.append((region, t, max_delay, runtime, name, input_size_gb, output_size_gb, core_count, watts_per_core))


    with Pool(processes=32) as pool:
        pool.starmap(make_api_call, args)



