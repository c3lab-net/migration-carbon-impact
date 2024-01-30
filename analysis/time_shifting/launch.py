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


workloads = {"nw-bound": Workload(
    runtime=timedelta()
    ),}



def make_api_call(region, t, runtime, max_delay):
    print(region, t, runtime, max_delay)
    response = requests.get(CARBON_API_URL, json=Workload(
        runtime=runtime,
        schedule=WorkloadSchedule(
            start_time=t,
            max_delay=max(max_delay - runtime, timedelta()),
        ),
        dataset=Dataset(
            input_size_gb=250,
            output_size_gb=250
        ),
        core_count=100,
        original_location=region,
        candidate_providers=["AWS"],
        inter_region_route_source=InterRegionRouteSource.ITDK_AND_IGDB_WITH_POPS,
    ).asdict())
    d = response.json(parse_float=lambda s: float('%.6g' % float(s)))
    series = pd.Series(d)
    try:
        series.to_pickle(f"results_uniform_time/{region}_{t.isoformat()}_{runtime}_{max_delay}.pkl")
    except:
        print("problem with: " + f"results_uniform_time/{region}_{t.isoformat()}_{runtime}_{max_delay}.pkl")

start_times = [datetime(year=2023, month=m, day=1, hour=h, tzinfo=timezone.utc) for m in range(1,13) for h in range(0,24,6)]


if __name__ == "__main__":

    start_times = pd.date_range(
        start=pd.to_datetime("6/1/2023").tz_localize("UTC"),
        end=pd.to_datetime("6/29/2023").tz_localize("UTC"),
        freq="1h",
    )

    args = []

    for region in ["AWS:us-west-1", "AWS:eu-west-2", "AWS:eu-central-1"]:
        for t in start_times:
            for runtime in [timedelta(hours=h) for h in range(2, 5, 2)]:
                for max_delay in [timedelta(hours=h) for h in range(0, 25, 4)]:
                    args.append((region, t, runtime, max_delay))


    with Pool(processes=16) as pool:
        pool.starmap(make_api_call, args)



